"""
지역 글에 나오는 장소 이름(랜드마크·도로·시설)의 사실 확인 기록을 검사한다.

자동생성 루틴은 배치 파일의 각 항목에 fact_check 를 붙인다. 형식:

  "fact_check": {
    "status": "confirmed",            # 확인됨 → 반영 / "held" → 보류 폴더로
    "reason": "",                     # held 일 때 이유(쉬운 말 한 줄)
    "items": [                        # 글에 나오는 장소 이름마다 하나
      {"name": "대동하늘공원",
       "evidence": "대전 동구 대동 산1-68, 동구청 관광명소 소개",   # 그 동(또는 바로 옆)에 있다는 근거
       "url": "https://www.donggu.go.kr/..."}
    ]
  }

사용법
  python3 scripts/fact_check.py data/batches/2026-09-29.json   # 항목별로 확인해야 할 이름 목록과 빠진 기록을 보여 준다
  python3 scripts/fact_check.py --regions                      # 이미 올라간 regions.json 전체에서 장소 이름만 뽑아 본다

import_batch.py 는 이 파일의 problems() 로 확인 기록을 검사하고, 기록이 없는 이름이 있으면 반영하지 않는다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 이런 말로 끝나는 낱말은 장소 이름일 가능성이 높아 확인 기록을 요구한다
PLACE_SUFFIX = (
    "공원|국가정원|정원|시장|대학교|대학|캠퍼스|초등학교|중학교|고등학교|학교|교회|성당|사찰|병원|의료원|광장|"
    "저수지|호수|터미널|법원|검찰청|구청|시청|군청|도청|도서관|박물관|미술관|경기장|체육관|운동장|"
    "오거리|사거리|삼거리|고개|해수욕장|해변|포구|항|산업단지|공단|단지|마을|아파트|역|양관|"
    "천|강|산|봉|교|다리|거리|골목|센터|행정복지센터"
)
# 조사가 붙은 형태까지 한 번에 잡는다 (광교산 쪽, 국제시장 골목 …)
PARTICLE = r"(?:을|를|이|가|은|는|과|와|의|에|에서|으로|로|도|만|까지|부터|처럼|쪽|변)?"
CAND_RE = re.compile(rf"([가-힣0-9]{{1,12}}(?:{PLACE_SUFFIX})){PARTICLE}(?=[\s,.·()]|$)")
# 도로 이름(○○로·○○대로·○○길)은 '장비로', '동네로' 같은 조사 '로'와 구별하려고
# 뒤에 도로에만 붙는 조사나 위치 낱말이 올 때만 잡는다 (인중로를, 유곡로 뒤편, 필운대로에서 …)
ROAD_RE = re.compile(
    r"([가-힣0-9]{1,10}(?:대로|로|길))"
    r"(?:(?:를|을|에서|에|가|이|와|과|의|변|쪽)(?=[\s,.·()]|$)"
    r"|(?=\s(?:뒤편|뒤쪽|앞|옆|쪽|방향|일대|주변|인근|근처|사거리|오거리|삼거리|양쪽|건너편|이면도로|골목|상권|대로변|안쪽)"
    r"(?:에|에서|으로|의|을|를|은|는)?(?:[\s,.·()]|$)))"
)

# 장소 이름처럼 끝나지만 고유명이 아닌 말
STOP = {
    "도로", "큰길", "골목", "골목길", "이면도로", "진입로", "산책로", "둘레길", "등산로", "천변", "둑길", "강변",
    "오르막길", "비탈길", "언덕길", "샛길", "갓길", "차로", "통로", "경로", "대로", "뒷길", "옆길", "안길",
    "찻길", "좁은길", "큰도로", "시장", "공원", "학교", "대학", "대학교", "교회", "병원", "광장", "단지", "마을",
    "아파트", "역", "거리", "센터", "고개", "다리", "항", "산", "강", "천", "길", "로", "교",
    "주민센터", "행정복지센터", "상가", "상점가", "주택가", "원룸촌", "대학가", "먹자골목", "카페거리",
    "패션거리", "벽화골목", "벽화마을", "공업단지", "아파트단지", "주거단지", "전원마을", "농촌마을", "어촌마을",
    "지역", "구역", "영역", "역할", "매역", "유역", "전역", "지하철역", "기차역", "버스터미널", "터미널",
    "그대로", "새로", "따로", "서로", "바로", "주로", "실제로", "별도로", "차례로", "대체로", "뒤로", "위로",
    "아래로", "안으로", "밖으로", "옆으로", "앞으로", "쪽으로", "순서로", "기준으로", "방향으로", "처음으로",
    "마지막으로", "무료로", "전화로", "문자로", "사진으로", "통화로", "한번에로", "직접적으로", "가급적",
    "경사로", "일방통행로", "우회로", "출입로", "주차로", "도로변", "강가", "바닷가", "냇가", "시냇가",
    "운동장", "체육관", "해변", "포구", "산자락", "산기슭", "기슭", "능선", "봉우리",
    "대단지", "뒷골목", "전통시장", "근린공원", "환승역", "해안도로", "교차로", "등하교", "동호수", "호수",
    "세계문화유산", "환승센터", "산업단지", "산복도로", "재래시장", "어린이공원", "소공원", "공영주차장", "주차장", "시장골목", "주택단지", "상업지구",
}
ALLOWED_STATUS = ("confirmed", "held")
SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "전남광주통합특별시": "전남광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}


# 도로명 랜드마크(○○로·○○대로·○○길·○○로12번길)는 새 페이지에 쓰지 않는다. 숲길·둘레길 같은 산책길 이름은 장소로 본다
ROAD_LANDMARK_RE = re.compile(r"(?<!숲)(?<!둘레)(?<!올레)(?<!산책)(?:대로|로|길)(?:\d+번?길)?$|\d+번길$")


def entry_text(e: dict) -> str:
    parts = [e.get("landmark_desc", ""), e.get("service_intro", ""), e.get("meta", "")]
    for qa in e.get("faqs") or []:
        parts.extend(str(x) for x in qa)
    return "\n".join(parts)


def candidate_names(e: dict) -> list[str]:
    """글(랜드마크 설명·방문 안내·FAQ)에서 장소 이름으로 보이는 낱말을 뽑는다. 동·시군구 이름은 뺀다."""
    sido = e.get("sido", "")
    own = {e.get("dong", ""), e.get("sigungu", ""), sido, SIDO_SHORT.get(sido, ""), e.get("old_sido", ""), e.get("old_sigungu", ""), e.get("old_dong", "")}
    own |= set((e.get("sigungu") or "").split())
    found: list[str] = []
    text = entry_text(e)
    for m in sorted(list(CAND_RE.finditer(text)) + list(ROAD_RE.finditer(text)), key=lambda m: m.start()):
        name = m.group(1)
        if name in STOP or name in own or len(name) < 3 or name.endswith(("으로", "권역")):
            continue
        if re.fullmatch(r"[가-힣]+[동읍면리가]\d*가?", name) and name not in (e.get("landmark_name") or ""):
            continue  # 옆 동 이름(○○동)은 legal_dong_list.csv 로 따로 검사한다
        if name not in found:
            found.append(name)
    lm = (e.get("landmark_name") or "").strip()
    if lm and lm not in found:
        found.insert(0, lm)
    return found


def covered(name: str, checked: list[str]) -> bool:
    return any(name in c or c in name for c in checked if c)


def problems(e: dict) -> list[str]:
    """반영할 항목(status=confirmed)의 확인 기록 문제. 빈 목록이면 통과."""
    fc = e.get("fact_check")
    if not isinstance(fc, dict):
        return ["fact_check(사실 확인 기록) 없음"]
    status = fc.get("status")
    if status not in ALLOWED_STATUS:
        return [f"fact_check.status 는 {ALLOWED_STATUS} 중 하나여야 함 (현재 {status!r})"]
    if status == "held":
        return [] if str(fc.get("reason", "")).strip() else ["보류(held) 이유(reason) 없음"]
    out = []
    lm = str(e.get("landmark_name") or "").strip()
    if ROAD_LANDMARK_RE.search(lm):
        out.append(f"랜드마크 '{lm}' 가 도로명임 → 도로명은 랜드마크로 쓰지 않음(2026-09-29부터). "
                   "동 안에서 확인되는 장소로 바꾸거나 held 로 두세요")
    items = fc.get("items") or []
    checked = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            out.append(f"확인 기록 {i}번 형식 오류")
            continue
        name, ev, url = (str(it.get(k, "")).strip() for k in ("name", "evidence", "url"))
        if not name or not ev or not re.match(r"^https?://\S+\.\S+", url):
            out.append(f"확인 기록 {i}번({name or '이름 없음'})에 name·evidence·url(http 주소) 중 빠진 것 있음")
        checked.append(name)
    missing = [n for n in candidate_names(e) if not covered(n, checked)]
    if missing:
        out.append(f"확인 기록이 없는 장소 이름: {', '.join(missing)} → 웹 검색으로 확인해 items 에 넣거나 글에서 빼세요")
    return out


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--regions":
        regions = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
        for r in regions:
            print(f"{r['slug']}\t{' '.join(x for x in (r['sido'], r['sigungu'], r['dong']) if x)}\t{' | '.join(candidate_names(r))}")
        return
    if len(sys.argv) != 2:
        raise SystemExit("사용법: python3 scripts/fact_check.py data/batches/YYYY-MM-DD.json  (또는 --regions)")
    path = Path(sys.argv[1])
    entries = json.loads((path if path.is_absolute() else ROOT / path).read_text(encoding="utf-8"))
    bad = 0
    for e in entries:
        full = " ".join(x for x in (e.get("sido"), e.get("sigungu"), e.get("dong")) if x)
        probs = problems(e)
        state = (e.get("fact_check") or {}).get("status", "기록 없음")
        print(f"- {e.get('slug')} ({full}) [{state}]")
        print(f"    확인할 이름: {', '.join(candidate_names(e)) or '(없음)'}")
        for p in probs:
            print(f"    ✗ {p}")
        bad += bool(probs)
    print(f"확인 기록 문제 있는 항목: {bad}개 / {len(entries)}개")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
