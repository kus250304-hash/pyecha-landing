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
- 같은 시군구에서 '숫자+가'만 다른 동(명동1가/명동2가 등)은 하나만 만든다
- 면(面)은 generation_config.json 의 include_myeon 이 true 일 때만 포함
- 시도별로 돌아가며 하나씩 뽑아 하루 분량이 한 지역에 몰리지 않게 한다
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

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
REGIONS_PATH = ROOT / "data" / "regions.json"
CONFIG_PATH = ROOT / "data" / "generation_config.json"
BATCH_DIR = ROOT / "data" / "batches"
KST = timezone(timedelta(hours=9))

SIDO_PREFIX = {
    "서울특별시": "seoul", "부산광역시": "busan", "대구광역시": "daegu", "인천광역시": "incheon",
    "광주광역시": "gwangju", "대전광역시": "daejeon", "울산광역시": "ulsan", "세종특별자치시": "sejong",
    "경기도": "gyeonggi", "강원특별자치도": "gangwon", "충청북도": "chungbuk", "충청남도": "chungnam",
    "전북특별자치도": "jeonbuk", "전라남도": "jeonnam", "경상북도": "gyeongbuk", "경상남도": "gyeongnam",
    "제주특별자치도": "jeju",
}

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
    parts = [SIDO_PREFIX[sido]]
    for tok in sigungu.split():
        # 강남구→gangnam, 남구→namgu (한 글자만 남으면 구/시/군을 붙여 둔다)
        parts.append(romanize(tok[:-1] if tok[-1] in "시군구" and len(tok) > 2 else tok))
    core = dong[:-1] if dong[-1] in "동읍면" and len(dong) > 1 else dong  # 우동→u, 명동1가→myeongdong1ga
    parts.append(romanize(core))
    return "-".join(p for p in parts if p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, help="생성 개수 (기본: generation_config.json 의 daily_count)")
    ap.add_argument("--date", help="배치 파일 날짜 (기본: 오늘, 한국 시간)")
    args = ap.parse_args()

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    count = args.count or int(cfg["daily_count"])
    include_myeon = bool(cfg.get("include_myeon", False))
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))

    date = args.date or datetime.now(KST).strftime("%Y-%m-%d")
    out_path = BATCH_DIR / f"{date}.json"
    if out_path.exists():
        print(f"이미 있음: {out_path.relative_to(ROOT)} — 이 파일을 채워서 import_batch.py 로 넘기세요")
        return

    covered_codes = {r["code"] for r in regions if r.get("code")}
    covered_base = {(r["sido"], r["sigungu"], base_name(r["dong"])) for r in regions}
    used_slugs = {r["slug"] for r in regions}

    queues: dict[str, list[dict]] = {s: [] for s in SIDO_ORDER}
    for r in rows:
        sido, sigungu, dong, code = r["시도"], r["시군구"], r["읍면동"], r["법정동코드"]
        if sido not in queues:
            raise ValueError(f"SIDO_ORDER 에 없는 시도: {sido}")
        if code in covered_codes or (sido, sigungu, base_name(dong)) in covered_base:
            continue
        if dong.endswith("면") and not include_myeon:
            continue
        queues[sido].append(r)

    picked: list[dict] = []
    picked_base: set[tuple[str, str, str]] = set()
    while len(picked) < count and any(queues.values()):
        for sido in SIDO_ORDER:
            q = queues[sido]
            while q:
                r = q.pop(0)
                key = (r["시도"], r["시군구"], base_name(r["읍면동"]))
                if key in picked_base:
                    continue
                picked_base.add(key)
                picked.append(r)
                break
            if len(picked) >= count:
                break

    if not picked:
        print("선택 가능한 동이 없습니다 (전체 완료됨)")
        return

    entries = []
    for r in picked:
        slug = base = make_slug(r["시도"], r["시군구"], r["읍면동"])
        n = 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        entries.append({
            "code": r["법정동코드"], "slug": slug,
            "sido": r["시도"], "sigungu": r["시군구"], "dong": r["읍면동"],
            "landmark_name": "", "landmark_desc": "", "service_intro": "", "faqs": [], "meta": "",
        })

    BATCH_DIR.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"배치 파일: {out_path.relative_to(ROOT)} ({len(entries)}개)")
    for e in entries:
        full = " ".join(x for x in (e["sido"], e["sigungu"], e["dong"]) if x)
        print(f"  {e['slug']}: {full}")


if __name__ == "__main__":
    main()
