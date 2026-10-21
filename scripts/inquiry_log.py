"""
거래 기록부의 랜딩 문의를 docs/index-requests.md "문의가 온 페이지" 칸에 옮긴다(2026-10-21 병한님 요청).
PC 예약 작업 "폐차 사례 가져오기"(docs/pc-case-import-prompt.md 2-1 단계)가 매일 돌린다. 거래 기록부는 운영자 PC 의
병한-업무위키에만 있어 클라우드 매일 루틴은 볼 수 없다.

사용법
  python scripts/inquiry_log.py           # 더할 줄만 보여 줌(파일 그대로)
  python scripts/inquiry_log.py --write   # index-requests.md 에 덧붙이고, 새 시·군은 population_stats.py dong 도 돌림

규칙
- 읽는 곳: 저장소 옆 병한-업무위키\\폐차\\거래기록\\*.md (--dir 로 바꿈). 칸은 날짜·유입경로·지역·거래상태 넷만 읽고
  전화·차번호·이름·금액 칸은 읽지도 쓰지도 않는다.
- 유입경로에 "랜딩" 또는 "폼"이 들어간 거래만. 지역이 비었거나 시·도만 있으면("서울", "광주") 넣지 않는다.
- 지역 → 그 시·군의 구 페이지(gu/ 파일이 있는 곳). 구가 여러 개인 시에서 구가 안 적혀 있으면 이름순 첫 구
  (같은 시의 다른 구는 pick_index_requests.inquiry_group 이 함께 고름). 구 페이지가 없으면 넣지 않고 알린다.
- 한 줄: "- 날짜, 랜딩 문의(상태: 진행|거래 성사|종료) — 구 페이지 주소(%인코딩) (지역)". 날짜가 새로운 줄이 위.
  거래상태 완료 → 거래 성사, 종료 → 종료, 그 밖(진행중·견적중·재연락·빈칸) → 진행.
- 겹침: (날짜, 시·도, 시) 마다 거래 수와 칸에 이미 있는 줄 수를 비교해 모자란 만큼만 더한다(손으로 적은 줄도 셈).
  이 스크립트 형식의 줄은 거래 기록부의 지금 상태로 고친다(진행 → 거래 성사 등).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import CONFIG, GU_DATA, REGIONS, SIDO_SHORT, gu_file, load_json  # noqa: E402
from pick_index_requests import LOG, URL_RE, inquiry_places, sections  # noqa: E402

WIKI_DIR = ROOT.parent / "병한-업무위키" / "폐차" / "거래기록"
POP_DONG = ROOT / "data" / "population_dong.json"
SECTION = "문의가 온 페이지"
LINE_DATE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2})")
OURS_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}), 랜딩 문의\(상태: ([^)]+)\) — ")
SIDO_ALIAS = {short: full for full, short in SIDO_SHORT.items()} | {full: full for full in SIDO_SHORT} | {
    "전남": "전남광주통합특별시", "광주": "전남광주통합특별시", "전라남도": "전남광주통합특별시", "광주광역시": "전남광주통합특별시",
    "강원도": "강원특별자치도", "전북": "전북특별자치도", "전라북도": "전북특별자치도", "제주도": "제주특별자치도"}


def field(text: str, name: str) -> str:
    m = re.search(rf"^{name}:[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def status_of(raw: str) -> str:
    return "거래 성사" if raw == "완료" else "종료" if raw == "종료" else "진행"


def read_records(folder: Path) -> list[dict]:
    """[{date, region, status, file}] — 유입경로가 랜딩·폼인 거래만, 파일 이름 순."""
    out = []
    for f in sorted(folder.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        route, date = field(text, "유입경로"), field(text, "날짜")
        if ("랜딩" in route or "폼" in route) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            out.append({"date": date, "region": field(text, "지역"), "status": status_of(field(text, "거래상태")), "file": f.name})
    return out


def part_match(part: str, token: str) -> bool:
    return part == token or part in (token + "시", token + "군", token + "구") or (len(token) >= 2 and part.startswith(token))


def find_gu(region: str, gus: list[tuple[str, str]]) -> tuple[str, str] | None:
    """'경기 화성 동탄구' → ('경기도', '화성시 동탄구'). 시·군을 못 정하면 None."""
    tokens = region.split()
    sido = SIDO_ALIAS.get(tokens[0]) if tokens else None
    if sido:
        tokens = tokens[1:]
    if not tokens:
        return None
    cands = [g for g in gus if (not sido or g[0] == sido) and part_match(g[1].split()[0], tokens[0])]
    if len(tokens) > 1:
        narrow = [g for g in cands if len(g[1].split()) > 1 and part_match(g[1].split()[1], tokens[1])]
        cands = narrow or cands
    if len({(s, g.split()[0]) for s, g in cands}) != 1:  # 시·군이 하나로 안 정해짐(없음 또는 여러 시·도)
        return None
    return sorted(cands)[0]


def city_key(date: str, place: tuple[str, str]) -> tuple[str, str, str]:
    return (date, place[0], place[1].split()[0])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dir", default=str(WIKI_DIR), help="거래 기록부 폴더")
    args = ap.parse_args()
    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"문의 기록: 거래 기록부 폴더 없음({folder}) → 건너뜀")
        return
    base = load_json(CONFIG)["site_base_url"].rstrip("/")
    regions, gu_data = load_json(REGIONS), load_json(GU_DATA, default=[])
    gus = [(g["sido"], g["sigungu"]) for g in gu_data if g.get("sigungu") and (ROOT / "gu" / gu_file(g["sido"], g["sigungu"])).exists()]

    groups: dict[tuple, list[tuple[dict, tuple[str, str]]]] = defaultdict(list)
    skipped = []
    for r in read_records(folder):
        place = find_gu(r["region"], gus) if r["region"] else None
        if not place:
            skipped.append(f"{r['date']} {r['region'] or '(지역 빈칸)'}: " + ("지역이 비어 있음" if not r["region"] else "시·군을 정할 수 없거나 구 페이지 없음"))
            continue
        groups[city_key(r["date"], place)].append((r, place))

    text = LOG.read_text(encoding="utf-8")
    head = f"\n## {SECTION}"
    start = text.index(head) + 1
    end = text.find("\n## ", start)
    end = len(text) if end < 0 else end + 1
    lines = text[start:end].split("\n")

    # 칸에 이미 있는 줄 → (날짜, 시·도, 시) 묶음
    existing: dict[tuple, list[int]] = defaultdict(list)
    for i, line in enumerate(lines):
        m = LINE_DATE_RE.match(line)
        places = inquiry_places(line, base, regions, gu_data) if m else []
        if places:
            existing[city_key(m.group(1), places[0])].append(i)

    added, updated, new_cities = [], [], set()
    for key, recs in sorted(groups.items()):
        idxs = existing.get(key, [])
        ours = [i for i in idxs if OURS_RE.match(lines[i])]
        # 앞쪽 거래는 손으로 적은 줄 몫, 그다음 거래가 이 스크립트 형식 줄과 차례로 짝(상태만 고침)
        for i, (r, _) in zip(ours, recs[len(idxs) - len(ours):]):
            old = OURS_RE.match(lines[i]).group(2)
            if old != r["status"]:
                lines[i] = lines[i].replace(f"(상태: {old})", f"(상태: {r['status']})", 1)
                updated.append(f"{r['date']} {r['region']}: {old} → {r['status']}")
        for r, place in recs[len(idxs):]:
            name = gu_file(*place)
            label = name.removesuffix("-폐차장.html").replace("-", " ")  # 천안시 동남구, 서울 강서구
            added.append((r["date"], f"- {r['date']}, 랜딩 문의(상태: {r['status']}) — {base}/gu/{quote(name)} ({label})"))
            new_cities.add((place[0], place[1].split()[0]))

    for date, new in sorted(added, key=lambda x: x[0]):  # 날짜 새로운 줄이 위: 자기보다 오래된 첫 줄 앞에
        pos = next((i for i, l in enumerate(lines) if (m := LINE_DATE_RE.match(l)) and m.group(1) < date), None)
        if pos is None:
            pos = max((i for i, l in enumerate(lines) if LINE_DATE_RE.match(l)), default=len(lines) - 2) + 1
        lines.insert(pos, new)

    print(f"문의 기록: 더함 {len(added)}줄, 상태 고침 {len(updated)}줄, 뺀 거래 {len(skipped)}건")
    for _, new in added:
        print("  + " + unquote(new))
    for u in updated:
        print("  ~ " + u)
    for s in skipped:
        print("  - " + s)
    if not args.write or not (added or updated):
        return
    LOG.write_text(text[:start] + "\n".join(lines) + text[end:], encoding="utf-8")
    print(f"저장: {LOG.relative_to(ROOT).as_posix()}")

    rows = load_json(POP_DONG, default={}).get("rows", {})
    need = sorted(c for s, c in new_cities if not any(k == f"{s} {c}" or k.startswith(f"{s} {c} ") for k in rows))
    if need:
        import population_stats
        try:
            population_stats.cmd_dong(need)
        except Exception as e:  # 인구를 못 받아도 고를 때 그 자리에서 다시 받으므로 멈추지 않음
            print(f"동별 인구 못 받음({', '.join(need)}): {e}")


if __name__ == "__main__":
    main()
