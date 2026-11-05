"""
거래 기록부(병한-업무위키\\폐차\\거래기록\\*.md, 운영자 PC 에만 있음)를 읽는 공통 조각(2026-11-05).
recent_cars.py(구 페이지 "최근 진행한 차")·money_monthly.py(월 숫자)·inbox_cases.py(사진 ↔ 입고일 맞추기)가 쓴다.

- 칸은 이름으로 골라 읽는다. 연락처·차번호·이름 칸은 읽지 않는다(FIELDS 에 없음).
- 금액 칸(매입가·판매가·탁송견인비)은 money=True 일 때만 읽고, 그 값은 저장소에 쓰지 않는다(money_monthly.py 가 위키에만 씀).
- 지역 → 구 페이지가 있는 (시·도, 시·군) 은 inquiry_log.find_gu 와 같은 규칙(일반구는 시 하나로 묶음).
"""
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from inquiry_log import WIKI_DIR, field, find_gu  # noqa: E402

FIELDS = ("날짜", "지역", "거래상태", "입고일", "말소상태", "차종", "연식", "차상태", "수출여부", "폐차종류", "유입경로", "안된이유")
MONEY_FIELDS = ("매입가", "판매가", "탁송견인비")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# 차종 칸에 차번호·전화·금액이 섞여 있으면 쓰지 않는다
CAR_BAD_RE = re.compile(r"\d{2,3}\s?[가-힣]\s?\d{4}|\d{3,4}-?\d{4}|만\s?원|\d+\s?원|[,@]")
CAR_OK_RE = re.compile(r"^[가-힣A-Za-z0-9 .·()\-+]{1,24}$")


def records(folder: Path = WIKI_DIR, money: bool = False) -> list[dict]:
    out = []
    for f in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        text = f.read_text(encoding="utf-8", errors="replace")
        r = {k: field(text, k) for k in FIELDS + (MONEY_FIELDS if money else ())}
        r["file"] = f.name
        if not DATE_RE.fullmatch(r["날짜"]):
            m = DATE_RE.match(f.name)
            r["날짜"] = m.group(0) if m else ""
        if money:
            r["메모"] = field(text, "메모")  # 안 된 이유를 낱말로 가르는 데만 쓰고 어디에도 옮기지 않는다
        out.append(r)
    return out


def is_day(v: str) -> bool:
    if not DATE_RE.fullmatch(v or ""):
        return False
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def arrived(r: dict) -> bool:
    """입고 완료 또는 말소 완료인 거래(종료·견적중은 뺌)."""
    if r.get("거래상태") in ("종료", "견적중", "재연락"):
        return False
    return is_day(r.get("입고일", "")) or bool(re.search(r"말소증\s*받|말소\s*완료", r.get("말소상태", "")))


def car_name(v: str) -> str:
    v = re.sub(r"\s+", " ", (v or "").strip())
    return v if v and CAR_OK_RE.fullmatch(v) and not CAR_BAD_RE.search(v) else ""


def model_year(v: str) -> str:
    m = re.search(r"(19[89]\d|20[0-4]\d)", v or "")
    return m.group(1) if m else ""


def start_state(v: str) -> str:
    if re.search(r"시동\s*(불가|안\s*(걸|됨|됌)|X|x|꺼짐|불능)|시동불가", v or ""):
        return "불가"
    if re.search(r"시동\s*(가능|됨|걸림|O|o|잘)", v or ""):
        return "가능"
    return ""


def chosen_side(r: dict) -> str:
    s = r.get("수출여부", "") + " " + r.get("폐차종류", "")
    if "수출" in s:
        return "수출"
    if "폐차" in r.get("수출여부", ""):
        return "폐차"
    return ""


def gu_places() -> list[tuple[str, str]]:
    from build_site import GU_DATA, gu_file, load_json
    return [(g["sido"], g["sigungu"]) for g in load_json(GU_DATA, default=[])
            if g.get("sigungu") and (ROOT / "gu" / gu_file(g["sido"], g["sigungu"])).exists()]


def city_of(region: str, places: list[tuple[str, str]]) -> tuple[str, str] | None:
    """'경기 고양 일산' → ('경기도', '고양시'). 구 페이지가 없거나 시·군을 못 정하면 None."""
    hit = find_gu(region, places) if region else None
    return (hit[0], hit[1].split()[0]) if hit else None
