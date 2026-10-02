"""
오늘 만들 구 페이지(/gu/) 후보를 고른다. 매일 루틴이 동 페이지를 반영한 뒤에 실행한다.

사용법
  python3 scripts/pick_next_gu.py            # data/generation_config.json 의 gu_line_a_count + gu_line_b_count 개(5 + 5)
  python3 scripts/pick_next_gu.py --count 4  # 시험용: 줄마다 절반씩

두 줄을 번갈아 뽑는다 (2026-10-01, docs/roadmap.md 6절)
- 줄 A: 추정 노후 자가용 대수 순(scripts/vehicle_stats.py). 큰 도시, 오래 걸려도 해야 하는 곳.
- 줄 B: 인구 30만 이하 시·군(gu_line_b_max_population, scripts/population_stats.py) 중 추정 노후 자가용 대수 순.
  네이버에서 경쟁이 적어 웹사이트 영역에 빨리 뜨는 곳. 광역시 자치구는 넣지 않는다. 구가 있는 시(천안시 동남구)는 시 전체 인구로 본다.
- 같은 구가 양쪽에 걸리면 한 번만(줄 B 로 센다). 한 줄 후보가 모자라면 다른 줄에서 채워 하루 개수를 맞추고, 그 사실을 출력한다.
- 공통: 동 페이지가 3개 이상 있는 구만(세종은 시 전체), data/gu.json·data/gu_held.json 에 있는 구는 뺀다.
- 네이버 검색량 우선순위 목록(2026-10-02, data/priority_regions.json): 두 줄 모두 목록 순위가 있는 구를 순위대로 먼저,
  그다음 위 등록대수 순. 하루 개수와 줄 A/B 나누기는 그대로다.

출력: 첫 줄들에 우선순위 기준, 그다음 후보마다 줄 이름·gu.json 뼈대(JSON)·그 구 동 페이지의 확인된 랜드마크 목록.
이 스크립트는 파일을 바꾸지 않는다.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import population_stats
import priority_regions
import vehicle_stats
from build_gu import MIN_DONG_PAGES
from build_site import GU_DATA, REGIONS, gu_groups, load_json

ROOT = Path(__file__).resolve().parent.parent
GU_HELD = ROOT / "data" / "gu_held.json"
GEN_CONFIG = ROOT / "data" / "generation_config.json"


def ordered_candidates() -> tuple[list[str], list[tuple[str, list[dict]]], list[tuple[str, list[dict]]]]:
    """(기준 설명 줄들, 줄 A 전체 순서, 줄 B 전체 순서)"""
    cfg = load_json(GEN_CONFIG, default={})
    limit = int(cfg.get("gu_line_b_max_population", 300000))
    regions = load_json(REGIONS)
    groups = gu_groups(regions)
    done = {g["slug"] for g in load_json(GU_DATA, default=[])} | {g["slug"] for g in load_json(GU_HELD, default=[])}
    cands = [(slug, rs) for slug, rs in groups.items() if slug not in done and len(rs) >= MIN_DONG_PAGES]

    basis, counts, meta = vehicle_stats.load()
    if basis != "none":
        def key(item):
            n = vehicle_stats.count_for(counts, item[1][0]["sido"], item[1][0]["sigungu"])
            return (n is None, -(n or 0), item[0])
        label = vehicle_stats.BASIS_LABEL.get(basis, basis)
        heads = [f"우선순위 기준: 시군구별 {label} 등록대수 많은 순 ({meta.get('as_of')}, {meta.get('source')})"]
    else:
        def key(item):
            return (-len(item[1]), item[0])
        heads = ["우선순위 기준: 등록대수 통계 없음 → 동 페이지가 많은 구 순 (보고에 알릴 것)"]
    prio = priority_regions.load()
    if prio:
        base_key = key

        def key(item):  # 검색량 목록 순위가 있는 구 먼저
            rank = prio.rank_of(item[1][0]["sido"], item[1][0]["sigungu"])
            return (rank is None, rank or 0, base_key(item))
        heads.insert(0, f"검색량 우선순위: {prio.label()} 에 있는 구를 순위대로 먼저, 그다음 아래 기준")
    line_a = sorted(cands, key=key)

    pops, pmeta = population_stats.load()
    if pops:
        line_b = [c for c in line_a if population_stats.is_small_si_gun(pops, c[1][0]["sido"], c[1][0]["sigungu"], limit)]
        heads.append(f"줄 B 기준: 인구 {limit:,}명 이하 시·군 ({pmeta.get('as_of')}, {pmeta.get('source')})")
    else:
        line_b = []
        heads.append("줄 B 기준: 인구 통계 없음 → 줄 B 를 비우고 줄 A 로 채움 (보고에 알릴 것, scripts/population_stats.py fetch)")
    return heads, line_a, line_b


def pick(count_a: int, count_b: int) -> tuple[list[str], list[tuple[str, str, list[dict]]]]:
    heads, line_a, line_b = ordered_candidates()
    b_slugs = {s for s, _ in line_b}
    a_only = [c for c in line_a if c[0] not in b_slugs]  # 양쪽에 걸리는 구는 줄 B 로만 센다
    take_b, take_a = line_b[:count_b], a_only[:count_a]
    # 한 줄이 모자라면 다른 줄에서 채운다
    short_b, short_a = count_b - len(take_b), count_a - len(take_a)
    if short_b > 0:
        take_a = a_only[:count_a + short_b]
    if short_a > 0:
        take_b = line_b[:count_b + short_a]
    if short_b > 0:
        heads.append(f"줄 B 후보가 {len(line_b[:count_b])}개뿐이라 줄 A 에서 {len(take_a) - min(count_a, len(a_only))}개를 더 채움 (동 페이지 3개 이상인 30만 이하 시·군이 부족)")
    if short_a > 0:
        heads.append(f"줄 A 후보가 {len(a_only[:count_a])}개뿐이라 줄 B 에서 더 채움")
    picked: list[tuple[str, str, list[dict]]] = []
    for i in range(max(len(take_a), len(take_b))):  # A, B 번갈아
        if i < len(take_a):
            picked.append(("A", *take_a[i]))
        if i < len(take_b):
            picked.append(("B", *take_b[i]))
    return heads, picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, help="시험용: 전체 개수(줄마다 절반)")
    args = ap.parse_args()
    cfg = load_json(GEN_CONFIG, default={})
    if args.count:
        count_a, count_b = args.count - args.count // 2, args.count // 2
    else:
        count_a, count_b = int(cfg.get("gu_line_a_count", 5)), int(cfg.get("gu_line_b_count", 5))

    heads, picked = pick(count_a, count_b)
    print("\n".join(heads))
    if not picked:
        print("만들 수 있는 구가 없습니다 (동 페이지 3개 이상인 구가 모두 끝났거나 보류됨)")
        return
    print("오늘 후보: " + ", ".join(f"{line}:{slug}" for line, slug, _ in picked))
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    for line, slug, rs in picked:
        r0 = rs[0]
        print(f"\n=== [줄 {line}] {slug} ({r0['sido']} {r0['sigungu']}) 동 페이지 {len(rs)}개")
        for r in sorted(rs, key=lambda x: x["dong"]):
            print(f"  - {r['slug']}: {r['dong']} / 랜드마크 {r['landmark_name']}")
        skeleton = {
            "slug": slug, "sido": r0["sido"], "sigungu": r0["sigungu"],
            "intro": "", "intro_landmarks": [], "faqs": [], "public_info": [], "dropped_info": [],
            "checked_on": today,
        }
        print(json.dumps(skeleton, ensure_ascii=False))


if __name__ == "__main__":
    main()
