"""
사례 글 틀 v2(2026-10-23 Fable 설계)의 계산만 모은 곳. build_cases.py(사례 페이지)·build_site.py(카드)·
build_guide.py(주제 부착)·check_pages.py(검사)·pc_cases.py(PC 보고)가 같이 쓴다. 다른 빌드 모듈을 불러오지 않는다.

메모 새 칸(모두 선택) → cases/index.json 의 "story" 에 그대로(확인은 목록):
  걱정      손님이 처음 걱정한 것(손님 말투 1~2줄)                  → ② 인용 상자, 카드 둘째 줄
  확인      원부·사진·현장에서 확인한 것, "/" 로 나눠 최대 3개       → ③ 목록
  고른쪽    폐차 | 수출 | 비교중                                     → ① 표, ④ 틀 문장(비교중이면 ④ 생략)
  이유      1~2줄                                                    → ④ 틀 문장 다음 줄
  문의일·인수일·말소일  YYYY-MM-DD                                   → ① "걸린 날", ⑤ 진행과 걸린 날
  끝한줄    손님 말이면 따옴표                                       → ⑥
  제목꼬리  16자 이내(띄어쓰기 빼고)                                 → 메타 제목·H1, 카드 둘째 줄(걱정 없을 때)

깊이: 걱정·확인·고른쪽(고른쪽+이유, 또는 처리 칸 글)·걸린 날·끝한줄·영상에서 한 말 여섯 중 2개 이상이면 깊은 사례,
아니면 얇은 사례(noindex, 사이트맵·rss·IndexNow 밖). index.json 의 "depth"·"thin"·"card_line" 은 이 파일이 정한다.
"""
import re
from datetime import date

STORY_KEYS = ("걱정", "확인", "고른쪽", "이유", "문의일", "인수일", "말소일", "끝한줄", "제목꼬리")
DATE_KEYS = ("문의일", "인수일", "말소일")
CHOICES = ("폐차", "수출", "비교중")
CHECK_MAX = 3
TAIL_MAX = 16  # 띄어쓰기 빼고
# 이유·확인·제목꼬리에 있으면 그 사례를 처리하지 않는다(한 건의 사례를 모든 차의 결과처럼 읽히게 하는 말)
OVERCLAIM_RE = re.compile(r"이런 차는|같은 차는|항상|다 됩니다|전부")
OVERCLAIM_KEYS = ("이유", "확인", "제목꼬리")
# 예전 사례 70장에 똑같이 들어간 진행 방식 문장. 더 쓰지 않는다(처리 칸 글로 치지 않음)
OLD_METHOD = ("차량 상태와 서류를 상담으로 확인하고, 폐차 처리와 수출 비교매입 중 이 차량 조건에 맞는 방법으로 "
              "협력업체와 연결해 진행했습니다.")
DEPTH_NAMES = ("걱정", "확인", "고른쪽", "걸린 날", "끝한줄", "영상에서 한 말")
DEPTH_MIN = 2
# ④ 틀 문장과 ⑤ 차령초과말소 한 줄. 여러 사례에 똑같이 들어가는 것이 정상이라 반복 검사에서 뺀다
CHOICE_SENTENCE = "폐차 쪽과 수출 쪽을 같이 알아본 뒤, 이 차는 {} 쪽으로 진행했습니다."
OVER_AGE_NOTE = "말소증은 보통 45~60일 뒤에 나옵니다"
FALLBACK_GUIDE = ("폐차-절차.html", "폐차 절차")


def first_sentence(text: str, limit: int = 70) -> str:
    s = re.split(r"(?<=[.!?])\s+", (text or "").strip())[0]
    return s if len(s) <= limit else s[: limit - 1] + "…"


def parse_day(v: str) -> date | None:
    m = re.fullmatch(r"\s*(\d{4})[-./](\d{1,2})[-./](\d{1,2})\s*", v or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def build_story(memo: dict, banned) -> tuple[dict | None, str, list[str]]:
    """메모(또는 고침 칸)의 새 칸 → story. (story, 처리 안 할 이유, 주의 목록). banned 는 build_cases.banned_text.
    고른쪽 값이 틀리거나 금지 표현이 있으면 story 가 None. 날짜 순서가 틀리면 날짜 세 칸을 비우고 주의만 남긴다."""
    notes: list[str] = []
    s: dict = {}
    for k in STORY_KEYS:
        v = memo.get(k)
        if isinstance(v, list):
            v = " / ".join(str(x) for x in v)
        v = re.sub(r"\s+", " ", str(v or "")).strip()
        if v:
            s[k] = v
    if "고른쪽" in s:
        c = s["고른쪽"].replace(" ", "")
        c = "비교중" if c in ("비교", "비교중", "비교만") else c
        if c not in CHOICES:
            return None, f"고른쪽 '{s['고른쪽']}' 은 폐차 / 수출 / 비교중 중 하나로 적어 주세요", notes
        s["고른쪽"] = c
    if "확인" in s:
        items = [x.strip() for x in s["확인"].split("/") if x.strip()]
        if len(items) > CHECK_MAX:
            notes.append(f"확인이 {len(items)}개라 앞 {CHECK_MAX}개만 씀")
        s["확인"] = items[:CHECK_MAX]
    days = {}
    for k in DATE_KEYS:
        if k in s:
            d = parse_day(s[k])
            if d:
                days[k] = d
                s[k] = d.isoformat()
            else:
                notes.append(f"{k} '{s[k]}' 을 날짜(YYYY-MM-DD)로 읽을 수 없어 뺌")
                del s[k]
    seq = [days[k] for k in DATE_KEYS if k in days]
    if any(b < a for a, b in zip(seq, seq[1:])):
        notes.append("날짜 순서가 맞지 않아(인수일 < 문의일 또는 말소일 < 인수일) 날짜 세 칸을 모두 비움")
        for k in DATE_KEYS:
            s.pop(k, None)
    if "제목꼬리" in s and len(s["제목꼬리"].replace(" ", "")) > TAIL_MAX:
        notes.append(f"제목꼬리 '{s['제목꼬리']}' 가 {TAIL_MAX}자를 넘어 뺌")
        del s["제목꼬리"]
    # 칸마다(확인은 항목마다) 따로 검사한다. 이어 붙이면 "압류 24건" + "2010년식" 이 차번호 꼴로 읽힌다(2026-10-23)
    for k, v in s.items():
        if k in DATE_KEYS:
            continue
        for piece in (v if isinstance(v, list) else [v]):
            if why := banned(piece):
                return None, f"{k} 칸: {why}", notes
    for k in OVERCLAIM_KEYS:
        v = s.get(k)
        text = " ".join(v) if isinstance(v, list) else (v or "")
        if m := OVERCLAIM_RE.search(text):
            return None, f"{k} 칸에 모든 차에 해당하는 것처럼 읽히는 말 '{m.group(0)}' 이 있습니다(이 차 한 대 이야기로 써 주세요)", notes
    return s, "", notes


def method_text(c: dict) -> str:
    """처리 칸 글(예전 공통 문장은 뺌)."""
    m = (c.get("method") or "").strip()
    return "" if m == OLD_METHOD else m


def _days(s: dict) -> dict:
    return {k: d for k in DATE_KEYS if (d := parse_day(s.get(k, "")))}


def day_count_text(n: int) -> str:
    return "당일" if n == 0 else f"{n}일"


def took_parts(s: dict) -> list[str]:
    """① 표 "걸린 날": ["문의→인수 1일", "인수→말소 3일"]. 두 날짜가 있는 구간만."""
    d = _days(s)
    out = []
    if "문의일" in d and "인수일" in d:
        out.append(f"문의→인수 {day_count_text((d['인수일'] - d['문의일']).days)}")
    if "인수일" in d and "말소일" in d:
        out.append(f"인수→말소 {day_count_text((d['말소일'] - d['인수일']).days)}")
    if not out and "문의일" in d and "말소일" in d:
        out.append(f"문의→말소 {day_count_text((d['말소일'] - d['문의일']).days)}")
    return out


def timeline(s: dict) -> str:
    """⑤ "문의 10월 20일 → 다음 날 차 인수 → 3일 뒤 말소". 날짜가 하나도 없으면 ""."""
    d = _days(s)
    parts, prev = [], None
    for k, verb in (("문의일", "문의"), ("인수일", "차 인수"), ("말소일", "말소")):
        if k not in d:
            continue
        if prev is None:
            parts.append(f"{verb} {d[k].month}월 {d[k].day}일")
        else:
            n = (d[k] - prev).days
            parts.append(f"{'당일' if n == 0 else '다음 날' if n == 1 else f'{n}일 뒤'} {verb}")
        prev = d[k]
    return " → ".join(parts)


def over_age(c: dict) -> bool:
    return any(k == "진행 내용" and "차령초과" in v for k, v in c.get("facts") or [])


def depth(c: dict) -> list[str]:
    s = c.get("story") or {}
    have = {
        "걱정": bool(s.get("걱정")),
        "확인": bool(s.get("확인")),
        "고른쪽": (s.get("고른쪽") in ("폐차", "수출") and bool(s.get("이유"))) or bool(method_text(c)),
        "걸린 날": bool(took_parts(s)),
        "끝한줄": bool(s.get("끝한줄")),
        "영상에서 한 말": bool(c.get("spoken")),
    }
    return [k for k in DEPTH_NAMES if have[k]]


def card_line(c: dict) -> str:
    """카드 둘째 줄·META_DESC 앞부분: 걱정 첫 문장(70자) → 제목꼬리 → summary."""
    s = c.get("story") or {}
    if s.get("걱정"):
        return first_sentence(s["걱정"])
    return s.get("제목꼬리") or c.get("summary") or ""


def finalize(c: dict) -> dict:
    """index.json 한 항목의 계산 칸(depth·thin·card_line)을 다시 정하고, 예전 공통 진행 문장을 지운다. 같은 dict 를 돌려준다."""
    if (c.get("method") or "").strip() == OLD_METHOD:
        c["method"] = ""
    c["depth"] = depth(c)
    c["thin"] = len(c["depth"]) < DEPTH_MIN
    c["card_line"] = card_line(c)
    return c


def case_text(c: dict) -> str:
    """주제 낱말을 찾는 글: situation·method·summary·facts("시동 불가"처럼 이름과 값을 붙여)·걱정·확인·이유."""
    s = c.get("story") or {}
    return " ".join([c.get("situation") or "", c.get("method") or "", c.get("summary") or ""]
                    + [f"{k} {v}" for k, v in c.get("facts") or []]
                    + [s.get("걱정", ""), " ".join(s.get("확인") or []), s.get("이유", "")])


def similar_topic(c: dict) -> tuple[str, str]:
    """⑦ 비슷한 차라면: topics.CASE_WORDS 로 맞는 주제 페이지 하나(주제 순서대로 첫 번째), 없으면 폐차 절차. (파일, 이름)"""
    import topics
    text = case_text(c)
    for t in topics.TOPICS:
        if any(w in text for w in topics.CASE_WORDS.get(t["file"], [])):
            return t["file"], t["nav"]
    return FALLBACK_GUIDE


def report_lines(c: dict) -> list[str]:
    """PC·아침 보고용 4줄."""
    s = c.get("story") or {}
    took = " · ".join(took_parts(s)) or "없음"
    return [f"걱정: {s.get('걱정') or '없음'}", f"고른쪽: {s.get('고른쪽') or '없음'}",
            f"걸린 날: {took}", f"끝한줄: {s.get('끝한줄') or '없음'}"]
