"""
data/legal_dong_list.csv 에서 아직 페이지가 없는 동을 골라 오늘 배치의 뼈대 파일을 만든다.

사용법
  python3 scripts/pick_next_regions.py            # data/generation_config.json 의 daily_count 만큼
  python3 scripts/pick_next_regions.py --count 5  # 개수 지정

결과: data/batches/YYYY-MM-DD.json (한국 시간 날짜). 각 항목의 code/slug/sido/sigungu/dong 은
채워져 있고 landmark_name/landmark_desc/service_intro/faqs/meta 는 비어 있다. 이 빈 칸을
채운 뒤 scripts/import_batch.py 로 넘긴다. 오늘 파일이 이미 있으면 새로 만들지 않는다.

선택 규칙
- 법정동코드 기준으로 regions.json 에 이미 있는 동은 제외
- 사실 확인에서 보류된 동(data/batches/held/*.json)도 제외 (매일 같은 동을 다시 뽑지 않게)
- 같은 시군구에서 '숫자+가'만 다른 동(종로1가~6가 등)은 따로 만들지 않고 한 페이지로 묶는다:
  dong 은 "종로", dong_parts 는 ["종로1가", …, "종로6가"], code 는 첫 ○가의 법정동코드.
  그중 하나라도 이미 페이지가 있으면(옛 방식의 ○가 페이지 38개) 그 묶음은 뽑지 않는다.
- 면(面)은 generation_config.json 의 include_myeon 이 true 일 때만 포함
- 우선순위(scripts/vehicle_stats.py): 시군구별 차령 10년 이상 노후차 등록대수가 많은 구부터
  (data/vehicle_stats.json). 없으면 추정 노후 자가용 대수(시군구 자가용 × 시도 노후차 비율,
  data/vehicle_stats_old10_est.json), 그것도 없으면 전체 등록대수(data/vehicle_stats_total.json) 순.
  통계가 둘 다 없으면 구 페이지(data/gu.json)가 있는 구 → 동 페이지가 많은 구 순이고,
  동 페이지가 하나도 없는 구끼리는 시도별로 돌아가며 하나씩 뽑는다. 첫 줄에 어떤 기준을 썼는지 찍는다.
- 사람이 거의 살지 않는 동(산업단지·산지 등)은 여기서 가려내지 않는다. 글을 채울 때 held 로 두고 이유를 적는다.
- 시·군 몫 (2026-10-01): daily_count 중 small_si_gun_daily_count 개(10)는 인구 30만 이하 시·군
  (scripts/population_stats.py, 구 페이지 줄 B 와 같은 기준)에서 먼저 뽑는다. 한 시·군에 동 페이지가
  3개가 되도록 몰아서 뽑아(이미 1~2개 있으면 모자란 만큼만), 3개가 쌓이면 바로 구 페이지 줄 B 후보가 된다.
  거의 다 찬 시·군(모자란 개수가 적은 곳) → 추정 노후 자가용 대수 많은 순. 이미 3개 이상이거나 후보 동을
  다 합쳐도 3개가 안 되는 시·군은 건너뛴다. 남은 칸은 위 우선순위대로 채운다. 이유는 docs/roadmap.md 6절.
- 네이버 검색량 우선순위 목록 (2026-10-02, data/priority_regions.json, scripts/priority_regions.py):
  등록대수 순보다 먼저 쓴다. 시·군 몫은 목록에 있는 시·군을 순위대로 먼저 고르고(그다음 위 순서),
  나머지 칸은 목록 순위대로 시군구마다 ① 동 이름으로 검색된 동 ② 그 시군구 동 페이지가 3개가 될 때까지
  채운 뒤, 남은 칸을 등록대수 순으로 채운다. 하루 개수·시·군 몫 개수·보류 규칙은 그대로다.
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_index import SIDO_ORDER
import population_stats
import priority_regions
import vehicle_stats

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
REGIONS_PATH = ROOT / "data" / "regions.json"
CONFIG_PATH = ROOT / "data" / "generation_config.json"
BATCH_DIR = ROOT / "data" / "batches"
HELD_DIR = BATCH_DIR / "held"
GU_PATH = ROOT / "data" / "gu.json"
KST = timezone(timedelta(hours=9))

SIDO_PREFIX = {
    "서울특별시": "seoul", "부산광역시": "busan", "대구광역시": "daegu", "인천광역시": "incheon",
    "전남광주통합특별시": "jeonnam", "대전광역시": "daejeon", "울산광역시": "ulsan", "세종특별자치시": "sejong",
    "경기도": "gyeonggi", "강원특별자치도": "gangwon", "충청북도": "chungbuk", "충청남도": "chungnam",
    "전북특별자치도": "jeonbuk", "경상북도": "gyeongbuk", "경상남도": "gyeongnam",
    "제주특별자치도": "jeju",
}
# 전남광주통합특별시(2026-07-01) 안의 옛 광주광역시 자치구는 기존 페이지처럼 gwangju- 로 시작한다.
# 인천 제물포구·영종구·검단구·서해구는 구 이름에서 incheon-jemulpo- 처럼 저절로 만들어진다.
GWANGJU_GU = {"동구", "서구", "남구", "북구", "광산구"}

# 국어의 로마자 표기법(음운 변화 미적용). 슬러그용이라 발음 규칙까지는 따르지 않는다.
CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
JONG = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]


def romanize(s: str) -> str:
    syl: list[list[str]] = []  # [초성, 중성, 종성]
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3:
            i = o - 0xAC00
            syl.append([CHO[i // 588], JUNG[(i % 588) // 28], JONG[i % 28]])
        elif ch.isascii() and ch.isalnum():
            syl.append(["", ch.lower(), ""])
    # 자주 나오는 자음동화만 반영: 종로→jongno, 신림→sillim, 설령→seollyeong, 심리→simni
    for prev, cur in zip(syl, syl[1:]):
        if cur[0] == "r" and prev[2] in ("ng", "m"):
            cur[0] = "n"
        elif cur[0] == "r" and prev[2] in ("n", "l"):
            prev[2], cur[0] = "l", "l"
    return "".join("".join(x) for x in syl)


def base_name(dong: str) -> str:
    return re.sub(r"\d+가$", "", dong)


def make_slug(sido: str, sigungu: str, dong: str) -> str:
    parts = ["gwangju" if sido == "전남광주통합특별시" and sigungu in GWANGJU_GU else SIDO_PREFIX[sido]]
    for tok in sigungu.split():
        # 강남구→gangnam, 남구→namgu (한 글자만 남으면 구/시/군을 붙여 둔다)
        parts.append(romanize(tok[:-1] if tok[-1] in "시군구" and len(tok) > 2 else tok))
    core = dong[:-1] if dong[-1] in "동읍면" and len(dong) > 1 else dong  # 우동→u, 명동1가→myeongdong1ga
    parts.append(romanize(core))
    return "-".join(p for p in parts if p)


SMALL_TARGET = 3  # 구 페이지를 만들 수 있는 동 페이지 수(build_gu.MIN_DONG_PAGES)


def pick_small(candidates: list[dict], regions: list[dict], slots: int, limit: int,
               stat_of, rank_of=lambda key: None) -> list[dict]:
    """인구 limit 이하 시·군에서 동 페이지가 3개가 되도록 몰아서 slots 개까지 고른다."""
    pops, meta = population_stats.load()
    if not pops or slots <= 0:
        if slots > 0:
            print("시·군 몫: 인구 통계 없음 → 건너뜀 (python3 scripts/population_stats.py fetch, 보고에 알릴 것)")
        return []
    have: dict[tuple[str, str], int] = {}
    for r in regions:
        have[(r["sido"], r["sigungu"])] = have.get((r["sido"], r["sigungu"]), 0) + 1
    groups: dict[tuple[str, str], list[dict]] = {}
    for c in candidates:
        if population_stats.is_small_si_gun(pops, c["시도"], c["시군구"], limit):
            groups.setdefault((c["시도"], c["시군구"]), []).append(c)
    ready = []
    for key, cs in groups.items():
        need = SMALL_TARGET - have.get(key, 0)
        if need <= 0 or len(cs) < need:
            continue  # 이미 3개 이상이거나, 후보를 다 써도 3개가 안 됨
        ready.append((rank_of(key), need, stat_of(key), key, cs))
    # 네이버 검색량 목록에 있는 시·군을 순위대로 먼저 → 모자란 개수가 적은 곳 → 등록대수
    ready.sort(key=lambda x: (x[0] is None, x[0] or 0, x[1], x[2] is None, -(x[2] or 0), x[3]))
    picked, partial = [], None
    for _, need, _, key, cs in ready:
        if len(picked) + need <= slots:
            picked += cs[:need]
        elif partial is None:
            partial = cs
        if len(picked) == slots:
            break
    if len(picked) < slots and partial:  # 남은 칸은 다음 시·군을 미리 시작(내일 나머지를 채움)
        picked += partial[: slots - len(picked)]
    names = {}
    for c in picked:
        names[c["시군구"]] = names.get(c["시군구"], 0) + 1
    print(f"시·군 몫 {len(picked)}개 (인구 {limit:,}명 이하, {meta.get('as_of')}): "
          + ", ".join(f"{k} {n}" for k, n in names.items()))
    return picked


def pick(regions: list[dict], count: int, include_myeon: bool, small_count: int = 0, small_limit: int = 300000) -> list[dict]:
    """아직 페이지가 없는 후보 가운데 우선순위대로 count 개를 고른다(○가 묶음은 _parts·_dong 을 단다)."""
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    covered_codes = {r["code"] for r in regions if r.get("code")}
    for held_file in sorted(HELD_DIR.glob("*.json")):
        covered_codes |= {h["code"] for h in json.loads(held_file.read_text(encoding="utf-8"))}
    covered_base = {(r["sido"], r["sigungu"], base_name(r["dong"])) for r in regions}

    # 후보: ○가 는 (시도, 시군구, 묶은 이름) 하나로 묶는다
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for r in rows:
        sido, sigungu, dong, code = r["시도"], r["시군구"], r["읍면동"], r["법정동코드"]
        if sido not in SIDO_ORDER:
            raise ValueError(f"SIDO_ORDER 에 없는 시도: {sido}")
        if dong.endswith("면") and not include_myeon:
            continue
        groups.setdefault((sido, sigungu, base_name(dong)), []).append(r)
    candidates = []
    for key, rs in groups.items():
        if key in covered_base or any(r["법정동코드"] in covered_codes for r in rs):
            continue
        gas = sorted((r for r in rs if re.search(r"\d+가$", r["읍면동"])), key=lambda r: int(re.search(r"(\d+)가$", r["읍면동"]).group(1)))
        if gas:
            first = dict(gas[0])
            first["_parts"] = [r["읍면동"] for r in gas]
            first["_dong"] = key[2]
            candidates.append(first)
        for r in rs:
            if not re.search(r"\d+가$", r["읍면동"]):
                candidates.append(r)

    csv_pos = {r["법정동코드"]: i for i, r in enumerate(rows)}
    candidates.sort(key=lambda c: csv_pos[c["법정동코드"]])
    basis, counts, meta = vehicle_stats.load()
    prio = priority_regions.load()
    candidates.sort(key=lambda c: c["법정동코드"] not in prio.dong_rank)  # 동 이름으로 검색된 동을 시·군 몫에서도 먼저

    # 시·군 몫을 먼저 고르고, 나머지 칸을 네이버 검색량 목록 → 원래 순서로 채운다
    small = pick_small(candidates, regions, min(small_count, count), small_limit,
                       lambda key: vehicle_stats.count_for(counts, *key) if basis != "none" else None,
                       lambda key: prio.rank_of(*key))
    small_codes = {c["법정동코드"] for c in small}
    rest = [c for c in candidates if c["법정동코드"] not in small_codes]
    count -= len(small)
    first: list[dict] = []
    if prio:
        have: dict[tuple[str, str], int] = {}
        for r in list(regions) + [{"sido": c["시도"], "sigungu": c["시군구"]} for c in small]:
            have[(r["sido"], r["sigungu"])] = have.get((r["sido"], r["sigungu"]), 0) + 1
        first = prio.pick_dongs(rest, have, count)
        names: dict[str, int] = {}
        for c in first:
            nm = " ".join(x for x in (c["시도"], c["시군구"]) if x)
            names[nm] = names.get(nm, 0) + 1
        print(f"검색량 우선순위 {len(first)}개 ({prio.label()}): " + (", ".join(f"{k} {n}" for k, n in names.items()) or "목록의 곳이 모두 동 페이지 3개 이상 → 등록대수 순"))
        first_codes = {c["법정동코드"] for c in first}
        rest = [c for c in rest if c["법정동코드"] not in first_codes]
        count -= len(first)
    else:
        print("검색량 우선순위: 목록 없음(data/priority_regions.json) → 등록대수 순")
    if basis != "none":
        # 노후차(없으면 전체) 등록대수가 많은 구부터. 통계에 없는 구는 맨 뒤, CSV 순서
        def stat_key(c: dict) -> tuple:
            n = vehicle_stats.count_for(counts, c["시도"], c["시군구"])
            return (n is None, -(n or 0), csv_pos[c["법정동코드"]])
        picked = sorted(rest, key=stat_key)[:count]
        label = vehicle_stats.BASIS_LABEL.get(basis, basis)
        print(f"우선순위 기준: 시군구별 {label} 등록대수 많은 순 ({meta.get('as_of')}, {meta.get('source')})")
    else:
        picked = fallback_order(rest, regions, rows, count)
        print("우선순위 기준: 등록대수 통계 없음 → 구 페이지가 있는 구, 동 페이지가 많은 구 순 (보고에 알릴 것)")
    return small + first + picked


def fallback_order(candidates: list[dict], regions: list[dict], rows: list[dict], count: int) -> list[dict]:
    """등록대수 통계가 없을 때: 구 페이지가 있는 구 → 동 페이지가 많은 구 → (동 페이지가 없는 구) 시도별로 돌아가며."""
    csv_pos = {r["법정동코드"]: i for i, r in enumerate(rows)}
    gu_pages = {(g["sido"], g["sigungu"]) for g in json.loads(GU_PATH.read_text(encoding="utf-8"))} if GU_PATH.exists() else set()
    page_count: dict[tuple[str, str], int] = {}
    for r in regions:
        page_count[(r["sido"], r["sigungu"])] = page_count.get((r["sido"], r["sigungu"]), 0) + 1
    ranked = sorted(
        (c for c in candidates if page_count.get((c["시도"], c["시군구"]))),
        key=lambda c: (-((c["시도"], c["시군구"]) in gu_pages), -page_count[(c["시도"], c["시군구"])], csv_pos[c["법정동코드"]]),
    )
    queues: dict[str, list[dict]] = {s: [] for s in SIDO_ORDER}
    for c in candidates:
        if not page_count.get((c["시도"], c["시군구"])):
            queues[c["시도"]].append(c)

    picked: list[dict] = ranked[:count]
    while len(picked) < count and any(queues.values()):
        for sido in SIDO_ORDER:
            if queues[sido]:
                picked.append(queues[sido].pop(0))
            if len(picked) >= count:
                break
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, help="생성 개수 (기본: generation_config.json 의 daily_count)")
    ap.add_argument("--date", help="배치 파일 날짜 (기본: 오늘, 한국 시간)")
    args = ap.parse_args()

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    count = args.count or int(cfg["daily_count"])
    date = args.date or datetime.now(KST).strftime("%Y-%m-%d")
    out_path = BATCH_DIR / f"{date}.json"
    if out_path.exists():
        print(f"이미 있음: {out_path.relative_to(ROOT)} — 이 파일을 채워서 import_batch.py 로 넘기세요")
        return
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    picked = pick(regions, count, bool(cfg.get("include_myeon", False)),
                  int(cfg.get("small_si_gun_daily_count", 0)), int(cfg.get("gu_line_b_max_population", 300000)))
    used_slugs = {r["slug"] for r in regions}
    if not picked:
        print("선택 가능한 동이 없습니다 (전체 완료됨)")
        return

    entries = []
    for r in picked:
        dong = r.get("_dong") or r["읍면동"]
        slug = base = make_slug(r["시도"], r["시군구"], dong)
        n = 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        entry = {
            "code": r["법정동코드"], "slug": slug,
            "sido": r["시도"], "sigungu": r["시군구"], "dong": dong,
            "landmark_name": "", "landmark_desc": "", "service_intro": "", "faqs": [], "meta": "",
            "fact_check": {"status": "", "reason": "", "items": []},
        }
        if r.get("_parts"):
            entry["dong_parts"] = r["_parts"]
        entries.append(entry)

    BATCH_DIR.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"배치 파일: {out_path.relative_to(ROOT)} ({len(entries)}개)")
    for e in entries:
        full = " ".join(x for x in (e["sido"], e["sigungu"], e["dong"]) if x)
        parts = f" (묶음: {', '.join(e['dong_parts'])})" if e.get("dong_parts") else ""
        print(f"  {e['slug']}: {full}{parts}")


if __name__ == "__main__":
    main()
