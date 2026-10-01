"""
오늘 만들 구 페이지(/gu/) 후보를 고른다. 매일 루틴이 동 페이지를 반영한 뒤에 실행한다.

사용법
  python3 scripts/pick_next_gu.py            # data/generation_config.json 의 gu_daily_count 개(기본 10)
  python3 scripts/pick_next_gu.py --count 3

고르는 규칙 (docs/roadmap.md 6절)
- 동 페이지가 3개 이상 있는 시군구만 (세종은 시 전체를 하나로)
- data/gu.json 에 이미 있는 구, data/gu_held.json 에 보류된 구는 뺀다 (매일 같은 구를 다시 뽑지 않게)
- 순서는 동 페이지와 같은 추정 노후 자가용 대수 순(scripts/vehicle_stats.py). 통계가 없으면 동 페이지가 많은 구부터.

출력: 첫 줄에 우선순위 기준, 그다음 후보마다 gu.json 뼈대(JSON)와 그 구 동 페이지의 확인된 랜드마크 목록.
뼈대의 intro·intro_landmarks·faqs·public_info·dropped_info 를 채워 data/gu.json 에 넣는다(규칙은 scripts/build_gu.py 맨 위).
이 스크립트는 파일을 바꾸지 않는다.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vehicle_stats
from build_gu import MIN_DONG_PAGES
from build_site import GU_DATA, REGIONS, gu_groups, load_json

ROOT = Path(__file__).resolve().parent.parent
GU_HELD = ROOT / "data" / "gu_held.json"
GEN_CONFIG = ROOT / "data" / "generation_config.json"


def pick(count: int) -> tuple[str, list[tuple[str, list[dict]]]]:
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
        head = f"우선순위 기준: 시군구별 {label} 등록대수 많은 순 ({meta.get('as_of')}, {meta.get('source')})"
    else:
        def key(item):
            return (-len(item[1]), item[0])
        head = "우선순위 기준: 등록대수 통계 없음 → 동 페이지가 많은 구 순 (보고에 알릴 것)"
    return head, sorted(cands, key=key)[:count]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int)
    args = ap.parse_args()
    count = args.count or int(load_json(GEN_CONFIG, default={}).get("gu_daily_count", 10))

    head, picked = pick(count)
    print(head)
    if not picked:
        print("만들 수 있는 구가 없습니다 (동 페이지 3개 이상인 구가 모두 끝났거나 보류됨)")
        return
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    for slug, rs in picked:
        r0 = rs[0]
        print(f"\n=== {slug} ({r0['sido']} {r0['sigungu']}) 동 페이지 {len(rs)}개")
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
