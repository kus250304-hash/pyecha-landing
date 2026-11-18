"""
반응 온 구·시군 페이지를 깊게 만드는 틀(2026-11-18, 설계 docs/fable-2026-11-18/deep-gu.md).

어떤 구가 "반응 온 구"인가 (자동으로 셈, 손으로 고치지 않음)
  docs/index-requests.md "문의가 온 페이지" 칸(거래 기록부의 랜딩 문의, scripts/inquiry_log.py)과
  data/form_inquiries.json(폼 문의, scripts/form_inquiries.py)에서, 자료의 마지막 날짜부터 거꾸로 WINDOW_DAYS(30)일 안에
  같은 구 페이지로 문의가 MIN_INQUIRIES(2)건 이상 온 곳. 두 자료는 같은 거래 기록부에서 나와 겹치므로 더하지 않고 큰 쪽을 쓴다.
  어느 페이지인지 모르는 문의(지역 미상)는 세지 않는다.

한 번 켜지면 꺼지지 않는다
  `mark --write` 가 data/gu.json 그 구 항목에 "deep": {"since": 날짜, "inquiries": n, "window": "…"} 를 적는다(이미 있으면 그대로).
  페이지 모양은 이 표시와 채워진 재료로만 정해진다. 문의가 뜸해져도 이미 넣은 글이 빠지지 않아 날짜·색인이 흔들리지 않는다.

깊은 구 페이지에 들어가는 것 (build_gu.py 가 그림. 재료가 없으면 그 칸은 그리지 않는다 — 지어내지 않는다)
  ① 읍·면·동 한 줄      gu.json "area_notes"  동 페이지가 없는 읍·면·동 중 주민 많은 순 AREA_N(5)곳, 사실 확인을 거친 한 문장
                         (재료: data/population_dong.json 순서 + 웹 확인 근거. 매일 루틴이 채움)
  ② 지역에서 받은 질문  gu.json "local_faqs"  그 시·군 손님이 통화·문자에서 실제로 물은 질문 최대 LOCAL_FAQ_N(2)개
                         (재료: PC 의 통화표·거래 기록부. PC 예약 작업이 채움. 병한님께 묻지 않음)
  ③ 가까운 지역 사례    깊은 사례 먼저 + 걱정 한 줄 (재료: cases/index.json, 그 구 사례가 3건보다 적을 때만)
  ④ 최근 진행한 차·사례 카드  이미 있는 칸(proof_blocks·build_gu). 거래가 끝나면 PC 작업이 올려 저절로 붙는다

사용법
  python3 scripts/deep_gu.py show            # 반응 온 구와 칸마다 채워진 정도, 다음에 누가 무엇을 채울지
  python3 scripts/deep_gu.py mark            # 새로 켜질 구 미리 보기
  python3 scripts/deep_gu.py mark --write    # data/gu.json 에 "deep" 표시를 적는다(이미 있는 곳은 건드리지 않음)
  python3 scripts/deep_gu.py todo            # 루틴용 JSON: 깊은 구마다 한 줄이 아직 없는 읍·면·동(주민 많은 순)
  python3 scripts/deep_gu.py check           # data/gu.json 의 깊은 구 재료(area_notes·local_faqs) 검사, 문제가 있으면 1로 끝남
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

INDEX_REQUESTS = ROOT / "docs" / "index-requests.md"
FORM_INQUIRIES = ROOT / "data" / "form_inquiries.json"
POPULATION = ROOT / "data" / "population_dong.json"
WINDOW_DAYS = 30
MIN_INQUIRIES = 2
AREA_N = 5
LOCAL_FAQ_N = 2
LINE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2})[^—]*— \S*/gu/(\S+?\.html)")


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def logged_inquiries() -> list[tuple[str, str]]:
    """docs/index-requests.md "문의가 온 페이지" 칸의 (날짜, 구 페이지 파일 이름)."""
    try:
        text = INDEX_REQUESTS.read_text(encoding="utf-8")
    except OSError:
        return []
    m = re.search(r"^## 문의가 온 페이지\s*$", text, flags=re.M)
    if not m:
        return []
    sec = text[m.end():]
    nxt = re.search(r"^## ", sec, flags=re.M)
    sec = sec[:nxt.start()] if nxt else sec
    out = []
    for line in sec.splitlines():
        mm = LINE_RE.match(line)
        if mm:
            out.append((mm.group(1), unquote(mm.group(2))))
    return out


def form_inquiries() -> list[tuple[str, str]]:
    """data/form_inquiries.json 의 (날짜, 구 페이지 파일 이름). 페이지를 모르는 줄(지역 미상)은 뺀다."""
    return [(r["date"], r["page"]) for r in _load(FORM_INQUIRIES, {}).get("rows", [])
            if r.get("page") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("date", ""))]


def counts(window: int = WINDOW_DAYS) -> tuple[dict[str, dict], str, str]:
    """구 페이지 파일 이름 → {"n": 건수, "dates": 날짜들}, 그리고 세는 기간(시작, 끝).
    끝은 두 자료에 적힌 마지막 날짜(오늘이 아님 — 같은 자료로 다시 돌리면 같은 답이 나온다)."""
    a, b = logged_inquiries(), form_inquiries()
    if not a and not b:
        return {}, "", ""
    last = max(d for d, _ in a + b)
    since = (date.fromisoformat(last) - timedelta(days=window - 1)).isoformat()
    out: dict[str, dict] = {}
    for rows in (a, b):
        per: dict[str, list[str]] = {}
        for d, page in rows:
            if since <= d <= last:
                per.setdefault(page, []).append(d)
        for page, ds in per.items():
            if len(ds) > out.get(page, {"n": 0})["n"]:
                out[page] = {"n": len(ds), "dates": sorted(ds)}
    return out, since, last


def candidates(gu_data: list[dict]) -> list[dict]:
    """반응 온 구(문의 MIN_INQUIRIES건 이상), 문의 많은 순 → 최근 문의 순."""
    from build_site import gu_file
    by_file = {gu_file(g["sido"], g["sigungu"]): g for g in gu_data}
    c, since, last = counts()
    out = []
    for page, v in c.items():
        g = by_file.get(page)
        if g and v["n"] >= MIN_INQUIRIES:
            out.append({"slug": g["slug"], "name": g["sigungu"] or g["sido"], "n": v["n"], "dates": v["dates"],
                        "window": f"{since}~{last}"})
    out.sort(key=lambda x: x["slug"])
    out.sort(key=lambda x: x["dates"][-1], reverse=True)
    out.sort(key=lambda x: x["n"], reverse=True)  # 정렬이 안정적이라 건수 → 최근 문의 → 이름 순
    return out


def is_deep(g: dict) -> bool:
    return isinstance(g.get("deep"), dict) and bool(g["deep"].get("since"))


def mark(gu_data: list[dict]) -> list[dict]:
    """새로 켤 구에 "deep" 표시를 붙인다(이미 있는 곳은 그대로). 돌려주는 값은 새로 켠 후보 목록."""
    by_slug = {g["slug"]: g for g in gu_data}
    new = []
    for c in candidates(gu_data):
        g = by_slug[c["slug"]]
        if not is_deep(g):
            g["deep"] = {"since": c["window"].split("~")[1], "inquiries": c["n"], "window": c["window"]}
            new.append(c)
    return new


def area_targets(g: dict, dongs: list[dict], n: int = AREA_N) -> list[str]:
    """한 줄을 쓸 읍·면·동: 그 시·군·구의 법정 읍·면·동 중 동 페이지가 없는 곳을 주민 많은 순으로 n곳.
    주민 수는 순서를 정하는 데만 쓰고 페이지에는 쓰지 않는다(data/population_dong.json, 행정안전부 법정동별 주민등록 인구)."""
    rows = _load(POPULATION, {}).get("rows", {})
    pop = rows.get(" ".join(x for x in (g["sido"], g["sigungu"]) if x), {})
    covered = {r["dong"] for r in dongs} | {p for r in dongs for p in r.get("dong_parts", [])}
    names = [k for k, _ in sorted(pop.items(), key=lambda kv: (-kv[1], kv[0])) if k not in covered and not re.search(r"\d+가$", k)]
    return names[:n]


def status(g: dict, dongs: list[dict], cases: list[dict]) -> dict:
    """칸마다 채워진 정도."""
    import proof_blocks
    from build_gu import gu_cases
    mine = gu_cases(g["slug"], cases)
    targets = area_targets(g, dongs)
    noted = [a.get("dong") for a in g.get("area_notes") or []]
    return {
        "deep_cases": sum(1 for c in mine if not c.get("thin")), "thin_cases": sum(1 for c in mine if c.get("thin")),
        "recent_cars": len(proof_blocks.recent_map().get(proof_blocks.city_key(g["sido"], g["sigungu"]), [])),
        "area_targets": targets, "area_missing": [t for t in targets if t not in noted], "area_notes": len(noted),
        "local_faqs": len(g.get("local_faqs") or []), "checked_on": g.get("checked_on", ""),
    }


def next_steps(st: dict) -> list[str]:
    out = []
    if st["area_missing"]:
        out.append("루틴(웹 확인): 읍·면·동 한 줄 — " + "·".join(st["area_missing"]))
    if st["local_faqs"] < LOCAL_FAQ_N:
        out.append(f"PC(통화표·기록부): 지역에서 받은 질문 {LOCAL_FAQ_N - st['local_faqs']}개")
    if not st["deep_cases"] and not st["recent_cars"]:
        out.append("PC(거래가 끝나면 저절로): 최근 진행한 차·사례")
    return out


def main() -> None:
    from build_site import CASES_INDEX, GU_DATA, REGIONS, gu_groups, load_json
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["show", "mark", "todo", "check"])
    ap.add_argument("--write", action="store_true", help="mark: data/gu.json 에 적는다")
    args = ap.parse_args()
    gu_data = load_json(GU_DATA, default=[])
    groups = gu_groups(load_json(REGIONS))
    cases = load_json(CASES_INDEX, default=[])

    if args.cmd == "mark":
        new = mark(gu_data)
        for c in new:
            print(f"새로 켬: {c['name']} — 문의 {c['n']}건({c['window']})")
        if not new:
            print("새로 켤 구 없음")
        elif args.write:
            GU_DATA.write_text(json.dumps(gu_data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"data/gu.json 에 deep 표시 {len(new)}곳 적음")
        else:
            print("(미리 보기 — 적으려면 --write)")
        return

    if args.cmd == "check":
        from build_gu import area_note_problems, local_faq_problems
        bad = [f"{g['slug']}: {e}" for g in gu_data
               for e in area_note_problems(g, groups.get(g["slug"], [])) + local_faq_problems(g)]
        for e in bad:
            print("오류:", e)
        print(f"깊은 구 재료 검사: 오류 {len(bad)}건")
        sys.exit(1 if bad else 0)

    # 문의 많았던 곳부터(같으면 이름 순) — 루틴은 todo 맨 앞 1곳만 하루에 채운다
    deep = sorted((g for g in gu_data if is_deep(g)), key=lambda g: (-int(g["deep"].get("inquiries") or 0), g["slug"]))
    if args.cmd == "todo":
        out = []
        for g in deep:
            st = status(g, groups.get(g["slug"], []), cases)
            if st["area_missing"]:
                out.append({"slug": g["slug"], "sido": g["sido"], "sigungu": g["sigungu"], "area_missing": st["area_missing"]})
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return

    c, since, last = counts()
    print(f"세는 기간 {since}~{last} · 같은 구 페이지 문의 {MIN_INQUIRIES}건 이상이면 반응 온 구")
    pending = [x for x in candidates(gu_data) if not is_deep(next(g for g in gu_data if g["slug"] == x["slug"]))]
    for x in pending:
        print(f"  아직 표시 없음: {x['name']} 문의 {x['n']}건 → python3 scripts/deep_gu.py mark --write")
    print(f"깊은 구 {len(deep)}곳")
    for g in deep:
        st = status(g, groups.get(g["slug"], []), cases)
        name = g["sigungu"] or g["sido"]
        print(f"- {name} (켠 날 {g['deep']['since']}, 문의 {g['deep'].get('inquiries', '?')}건): "
              f"깊은 사례 {st['deep_cases']} · 얇은 사례 {st['thin_cases']} · 최근 진행한 차 {st['recent_cars']} · "
              f"읍·면·동 한 줄 {st['area_notes']}/{len(st['area_targets'])} · 지역 질문 {st['local_faqs']}/{LOCAL_FAQ_N}")
        for s in next_steps(st):
            print(f"    다음: {s}")


if __name__ == "__main__":
    main()
