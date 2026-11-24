#!/usr/bin/env python3
"""옛 사례를 어느 지역부터 찾을지 순서 (2026-11-24 병한님 "먼저 들어가야 좋을 지역부터 복사 붙여넣기용으로").

병한님이 옛 휴대폰·자료에서 예전에 한 건을 찾아 "옛 사례:" 한 줄이나 "#번호 걱정: …"으로 주실 때, 어느 지역부터
보면 좋은지를 저장소 자료만으로 줄 세운다. 읽기만 한다(--write 는 docs/old-cases-targets.md 한 파일만 다시 씀).

  python3 scripts/old_case_targets.py                 # 순서 요약(묶음마다 지역 이름과 점수)
  python3 scripts/old_case_targets.py --batch 2       # 그 묶음의 복사용 상자(지역 이름 + 사진만 올라가 있는 차)
  python3 scripts/old_case_targets.py --write         # docs/old-cases-targets.md 다시 씀
  python3 scripts/old_case_targets.py find 원주 포터  # 그 지역·차종의 이미 있는 사례(같은 차를 두 번 만들지 않게)

단위: 시·군(일반구는 시 하나로, 서울·광역시는 구·군, 세종은 시 전체). 구 페이지가 있는 곳만.
대상: 깊은 사례가 한 건도 없는 곳(대기 중인 입력 cases/input 에 깊은 사례가 있으면 뺌).
순서 = 검색 점수 + 반응 점수 (큰 순)
  검색 점수 = 그 시·군의 폐차 검색량 합(data/priority_regions.json, 겹치는 키워드는 한 번만) × 0.075
              × 지방 계수(서울·경기·인천 0.5, 광역시 0.8, 그 밖 1.0), 검색량 합이 100 미만이면 반.
              점수표(docs/region-priority-2026-10-15.md)에서 경쟁 "높음"·광고 10개인 곳의 점수와 같은 크기다.
  반응 점수 = 최근 60일 문의 × 10 + 최근 28일 폼·전화 누름 × 5 + 최근 28일 네이버 방문(구 페이지와 그 동 페이지)
다른 지역과 이름이 겹쳐 검색량을 못 믿는 곳(AMBIGUOUS, 경기 광주시)은 검색 점수를 0으로 둔다.
번호(#)는 옛 사례 기억 노트(docs/print/memory-notebook-*.json)의 번호 그대로다.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "old-cases-targets.md"
BATCH = 10               # 한 묶음에 지역 수
WRITE_BATCHES = 6        # 문서에 적는 묶음 수(그 뒤는 다시 뽑음)
INQ_DAYS, GA_DAYS = 60, 28
W_INQ, W_CLICK, W_VISIT = 10, 5, 1
VOL_UNIT = 0.075
METRO = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
         "대전광역시": "대전", "울산광역시": "울산"}
CAPITAL = ("서울특별시", "경기도", "인천광역시")
AMBIGUOUS = {("경기도", "광주시")}   # "광주폐차장" 검색은 옛 광주광역시 것과 섞여 있음(점수표 비고)
SIDO_SHORT = {"경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북",
              "전남광주통합특별시": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def old_gwangju(sido: str, sigungu: str) -> bool:
    return sido.startswith("전남광주") and sigungu.endswith("구") and " " not in sigungu


def city_key(sido: str, sigungu: str) -> tuple[str, str, str]:
    """(시·도, 시·군 또는 자치구, 짧은 이름)."""
    if not sigungu:
        return sido, "", "세종" if sido.startswith("세종") else sido
    if sido in METRO:
        return sido, sigungu, f"{METRO[sido]} {sigungu}"
    if old_gwangju(sido, sigungu):
        return sido, sigungu, f"광주 {sigungu}"
    city = sigungu.split()[0]
    short = re.sub(r"(시|군)$", "", city)
    return sido, city, short if len(short) >= 2 and city.endswith("시") and city != "제주시" else city


def local_factor(sido: str, sigungu: str) -> float:
    if sido in CAPITAL:
        return 0.5
    return 0.8 if sido in METRO or old_gwangju(sido, sigungu) else 1.0


def notebook_numbers() -> dict[str, int]:
    """사례 slug → 기억 노트 번호(가장 최근 노트)."""
    files = sorted((ROOT / "docs" / "print").glob("memory-notebook-*.json"))
    if not files:
        return {}
    return {slug: int(n) for n, slug in _load(files[-1], {}).get("numbers", {}).items()}


def pending_deep() -> set[tuple[str, str]]:
    """대기 중인 입력(cases/input) 가운데 깊은 사례가 될 것의 (시·도, 시·군)."""
    import build_cases as BC
    import case_story
    out = set()
    if not BC.INPUT_DIR.exists():
        return out
    rows = BC.load_csv_rows()
    for f in sorted(p for p in BC.INPUT_DIR.iterdir() if p.is_dir()):
        memo_path = next((f / n for n in BC.MEMO_NAMES if (f / n).exists()), None)
        if not memo_path:
            continue
        memo = BC.parse_memo(BC.read_text_any(memo_path))
        region, _ = BC.resolve_region(memo.get("지역", ""), rows)
        story, _, _ = case_story.build_story(memo, BC.banned_text)
        if not region or story is None:
            continue
        if len(case_story.depth({"story": story, "method": memo.get("처리", ""), "spoken": ""})) >= case_story.DEPTH_MIN:
            out.add(city_key(region["sido"], region["sigungu"])[:2])
    return out


def ga_pages(days: int = GA_DAYS) -> tuple[dict[str, int], dict[str, int], str, str]:
    """페이지 경로 → 네이버 방문, 페이지 경로 → 폼·전화 누름, 그리고 기간."""
    ga = _load(ROOT / "data" / "ga4_daily.json", {}).get("days", {})
    if not ga:
        return {}, {}, "", ""
    last = max(ga)
    since = (date.fromisoformat(last) - timedelta(days=days - 1)).isoformat()
    visits: dict[str, int] = {}
    clicks: dict[str, int] = {}
    for d, v in ga.items():
        if d < since:
            continue
        for x in v.get("landing", []):
            if x.get("bucket") == "네이버":
                p = unquote(x.get("page", ""))
                visits[p] = visits.get(p, 0) + x.get("sessions", 0)
        for x in v.get("pages", []):
            p = unquote(x.get("page", ""))
            clicks[p] = clicks.get(p, 0) + x.get("quote_submit", 0) + x.get("call_click", 0)
    return visits, clicks, since, last


def cities() -> tuple[list[dict], dict]:
    """구 페이지가 있는 모든 시·군의 칸을 모아 점수 큰 순으로. 둘째 값은 기간 등 머리말에 쓸 것."""
    import deep_gu as DG
    from build_site import gu_file
    gu = _load(ROOT / "data" / "gu.json", [])
    cases = _load(ROOT / "cases" / "index.json", [])
    pri = {(e["sido"], e["sigungu"]): e for e in _load(ROOT / "data" / "priority_regions.json", {}).get("gu", [])}
    regs = _load(ROOT / "data" / "regions.json", [])
    numbers = notebook_numbers()
    visits, clicks, ga_since, ga_last = ga_pages()
    inq, inq_since, inq_last = DG.counts(window=INQ_DAYS)
    pend = pending_deep()

    out: dict[tuple[str, str], dict] = {}
    for g in gu:
        sido, city, name = city_key(g["sido"], g["sigungu"])
        c = out.setdefault((sido, city), {"sido": sido, "city": city, "name": name, "gu": [], "deep": 0, "thin": [],
                                          "inq": 0, "clicks": 0, "visits": 0, "kws": {},
                                          "factor": local_factor(g["sido"], g["sigungu"])})
        c["gu"].append(g["sigungu"] or g["sido"])
        f = gu_file(g["sido"], g["sigungu"])
        c["inq"] += inq.get(f, {}).get("n", 0)
        c["visits"] += visits.get("/gu/" + f, 0)
        c["clicks"] += clicks.get("/gu/" + f, 0)
        for kw in (pri.get((g["sido"], g["sigungu"])) or {}).get("keywords", []):
            if m := re.match(r"(\S+)\s+(\d+)$", kw):
                c["kws"][m.group(1)] = int(m.group(2))
    for r in regs:
        c = out.get(city_key(r["sido"], r.get("sigungu", ""))[:2])
        if c:
            p = f"/pages/{r['slug']}.html"
            c["visits"] += visits.get(p, 0)
            c["clicks"] += clicks.get(p, 0)
    for k in cases:
        c = out.get(city_key(k["sido"], k.get("sigungu", ""))[:2])
        if not c:
            continue
        if k.get("thin"):
            c["thin"].append({"n": numbers.get(k["slug"]), "slug": k["slug"], "date": k.get("date") or "",
                              "dong": k.get("dong") or "", "car": k.get("car") or "", "photos": len(k.get("photos") or [])})
        else:
            c["deep"] += 1
    seen: dict[str, int] = {}
    for c in out.values():
        seen[c["name"]] = seen.get(c["name"], 0) + 1
    for key, c in out.items():
        if seen[c["name"]] > 1 or key in AMBIGUOUS:   # 고성군(강원·경남), 경기 광주처럼 이름이 겹치는 곳은 시·도를 붙임
            c["name"] = f"{SIDO_SHORT.get(c['sido'], c['sido'][:2])} {c['name']}"
        vol = 0 if key in AMBIGUOUS else sum(c["kws"].values())
        c["volume"] = vol
        c["top"] = max(c["kws"].items(), key=lambda x: x[1]) if c["kws"] and vol else ("", 0)
        c["search"] = round(vol * VOL_UNIT * c["factor"] * (0.5 if vol < 100 else 1.0), 1)
        c["react"] = W_INQ * c["inq"] + W_CLICK * c["clicks"] + W_VISIT * c["visits"]
        c["score"] = round(c["search"] + c["react"], 1)
        c["pending"] = key in pend
        c["thin"].sort(key=lambda t: (t["date"] or "9999", t["n"] or 0))
    rows = sorted(out.values(), key=lambda c: (-c["score"], c["name"]))
    return rows, {"ga": f"{ga_since}~{ga_last}", "inq": f"{inq_since}~{inq_last}"}


def targets(rows: list[dict]) -> list[dict]:
    return [c for c in rows if c["deep"] == 0 and not c["pending"]]


def car_line(t: dict) -> str:
    """"2009년식 봉고3 1톤 더블캡" → "봉고3 1톤 더블캡 2009"."""
    m = re.match(r"\s*((?:19|20)\d\d)\s*년식?\s*(.+)$", t["car"])
    car = f"{m.group(2)} {m.group(1)}" if m else (t["car"] or "차종 모름")
    num = f"#{t['n']}" if t["n"] else "#-"
    return " ".join(x for x in (num, t["date"] or "날짜 모름", t["dong"], car) if x)


def batch_box(tg: list[dict], b: int) -> str:
    """b번째 묶음의 복사용 글(지역 이름 한 줄 + 사진만 올라가 있는 차)."""
    part = tg[(b - 1) * BATCH:b * BATCH]
    if not part:
        return ""
    start = (b - 1) * BATCH + 1
    lines = [f"[묶음 {b}] " + " · ".join(f"{start + i} {c['name']}" for i, c in enumerate(part))]
    thin = [c for c in part if c["thin"]]
    if thin:
        lines += ["", "사이트에 사진만 올라가 있는 차 (걱정 / 폐차·수출 — 왜 두 칸만 있으면 됨)"]
        for c in thin:
            lines.append(f"▼ {c['name']}")
            lines += [car_line(t) for t in c["thin"]]
    return "\n".join(lines)


def why(c: dict) -> str:
    parts = []
    if c["inq"]:
        parts.append(f"문의 {c['inq']}")
    if c["clicks"]:
        parts.append(f"폼·전화 누름 {c['clicks']}")
    if c["visits"]:
        parts.append(f"네이버 방문 {c['visits']}")
    if c["top"][0]:
        parts.append(f"{c['top'][0]} 월 {c['top'][1]}회")
    return " · ".join(parts) or "-"


def doc(rows: list[dict], info: dict) -> str:
    tg = targets(rows)
    today = date.today().isoformat()
    out = [f"# 옛 사례 — 어느 지역부터 ({today} 기준)", "",
           "`python3 scripts/old_case_targets.py --write` 가 씁니다(손으로 고치지 않음). 병한님이 옛 휴대폰·자료에서 예전에 한 건을 찾을 때 보는 순서입니다.", "",
           f"- 대상: 구 페이지가 있는 시·군 {len(rows)}곳 가운데 **깊은 사례가 한 건도 없는 {len(tg)}곳** (오늘 들어와 내일 붙을 사례가 있는 곳은 뺌)",
           f"- 순서: 검색 점수(그 시·군 폐차 검색량, 수도권은 반) + 반응 점수(문의 {info['inq']} × {W_INQ} + 폼·전화 누름 × {W_CLICK} + 네이버 방문, 누름·방문은 {info['ga']})",
           "- 번호(#)는 옛 사례 기억 노트 번호입니다. `#번호 걱정: … / 폐차 — 이유` 로 주시면 그 사례에 붙습니다.",
           "- 새로 찾은 차는 `옛 사례:` 한 줄(`docs/old-cases-template.md`). 사진만 올라가 있는 차와 같은 차면 클로드가 새로 만들지 않고 그 사례에 붙입니다.", ""]
    for b in range(1, WRITE_BATCHES + 1):
        part = tg[(b - 1) * BATCH:b * BATCH]
        if not part:
            break
        start = (b - 1) * BATCH + 1
        out += [f"## 묶음 {b} ({start}~{start + len(part) - 1})", "", "```", batch_box(tg, b), "```", "",
                "| 순서 | 지역 | 점수 | 왜 | 사진만 올라간 차 |", "|---:|---|---:|---|---:|"]
        out += [f"| {start + i} | {c['name']} | {c['score']} | {why(c)} | {len(c['thin']) or '-'} |" for i, c in enumerate(part)]
        out.append("")
    more = [c for c in rows if (c["deep"] or c["pending"]) and c["thin"]]
    if more:
        out += ["## 이미 깊은 사례가 있는 곳 (급하지 않음 — 사진만 올라간 차가 남아 있는 곳)", "",
                " · ".join(f"{c['name']} {len(c['thin'])}대" for c in more), ""]
    return "\n".join(out)


def cmd_find(words: list[str]) -> None:
    import ledger_cases as LC
    place, car = words[0], LC.car_key(" ".join(words[1:])) if len(words) > 1 else ""
    numbers = notebook_numbers()
    hit = 0
    for k in _load(ROOT / "cases" / "index.json", []):
        where = f"{k['sido']} {k.get('sigungu', '')} {k.get('dong', '')}"
        if place not in where or (car and car not in LC.car_key(k.get("car"))):
            continue
        hit += 1
        n = numbers.get(k["slug"])
        print(f"{'#' + str(n) if n else '  -'}  {'얇음' if k.get('thin') else '깊음'}  {k.get('date') or '날짜 모름'}  "
              f"{k.get('sigungu') or k['sido']} {k.get('dong') or ''}  {k.get('car') or ''}  사진 {len(k.get('photos') or [])}  {k['slug']}")
    print(f"{hit}건" if hit else "맞는 사례 없음(새 사례로 만들어도 됨)")


def main() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description="옛 사례를 어느 지역부터 찾을지 순서")
    ap.add_argument("cmd", nargs="?", choices=["find"])
    ap.add_argument("words", nargs="*", help="find: 지역 낱말, 차종 낱말")
    ap.add_argument("--batch", type=int, help="이 묶음의 복사용 상자")
    ap.add_argument("--write", action="store_true", help="docs/old-cases-targets.md 다시 씀")
    args = ap.parse_args()
    if args.cmd == "find":
        if not args.words:
            ap.error("find 뒤에 지역 낱말(과 차종 낱말)을 적어 주세요")
        cmd_find(args.words)
        return
    rows, info = cities()
    tg = targets(rows)
    if args.write:
        OUT.write_text(doc(rows, info) + "\n", encoding="utf-8")
        print(f"{OUT.relative_to(ROOT)} 씀 — 대상 {len(tg)}곳, 묶음 {min(WRITE_BATCHES, -(-len(tg) // BATCH))}개")
        return
    if args.batch:
        print(batch_box(tg, args.batch) or "그 묶음은 없습니다")
        return
    print(f"구 페이지가 있는 시·군 {len(rows)}곳 · 깊은 사례 0건 {len(tg)}곳 (문의 {info['inq']}, 누름·방문 {info['ga']})")
    for i, c in enumerate(tg[:BATCH * WRITE_BATCHES], 1):
        if (i - 1) % BATCH == 0:
            print(f"-- 묶음 {(i - 1) // BATCH + 1}")
        print(f"{i:>3} {c['name']:<10} {c['score']:>6} = 검색 {c['search']} + 반응 {c['react']} | {why(c)} | 사진만 {len(c['thin'])}대")


if __name__ == "__main__":
    main()
