"""
17일 판단 보고가 읽을 숫자 한 장(2026-11-13 병한님 상자 공장-2). 저장소 자료만 읽는다(인터넷·열쇠 없음).
돈 숫자·개인정보(이름·전화·차번호·금액)는 없다. 손으로 고치지 않는다.

사용법
  python scripts/judgment_inputs.py            # 화면에만
  python scripts/judgment_inputs.py --write    # docs/judgment-inputs.md 를 다시 씀
  python scripts/judgment_inputs.py --today 2026-11-17   # 기준일 바꿔 보기

ga4_daily.py --push 가 끝날 때 --write 로 돌려 같은 커밋에 넣는다(실패해도 GA4 저장·푸시는 그대로).

읽는 자료
  docs/index-requests.md   "## 문의가 온 페이지" 칸의 날짜 줄("- YYYY-MM-DD, …") = 랜딩 문의, 네이버 날짜 칸 = 네이버에 넣은 주소
  data/form_inquiries.json  폼 문의(scripts/form_inquiries.py)
  data/ga4_daily.json       세션·출처·이벤트·페이지·들어온 페이지(scripts/ga4_daily.py)
  data/regions.json         동 페이지 목록
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pick_index_requests import DATE_HEAD_RE, NOT_DONE, URL_RE, engines, sections  # noqa: E402

KST = timezone(timedelta(hours=9))
LOG = ROOT / "docs" / "index-requests.md"
FORMS = ROOT / "data" / "form_inquiries.json"
GA4 = ROOT / "data" / "ga4_daily.json"
REGIONS = ROOT / "data" / "regions.json"
OUT = ROOT / "docs" / "judgment-inputs.md"
NAVER_MOBILE = "m.search.naver.com / referral"
STOP_DAY = date(2026, 11, 11)  # 아침 색인(구글 15·네이버 50)을 그만둔 날
WEB3FORMS_FREE = 250  # Web3Forms 무료 한도(한 달), 참고값
WEEK = "월화수목금토일"
INQ_LINE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2})", re.M)


def load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def md(d: date) -> str:
    return f"{d.month}/{d.day}"


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weeks(today: date, n: int) -> list[tuple[date, date]]:
    """이번 주(진행 중) 포함 최근 n 주 [(월, 일)], 옛 주 먼저."""
    m = monday(today)
    return [(m - timedelta(weeks=i), m - timedelta(weeks=i) + timedelta(days=6)) for i in range(n - 1, -1, -1)]


def week_label(w: tuple[date, date], today: date) -> str:
    s, e = w
    if e >= today:
        n = (today - s).days  # 어제까지 찬 날 수
        return f"{md(s)}~{md(e)} (이번 주, {n}일 찼음)"
    return f"{md(s)}~{md(e)}"


# ── (1) 요일 맞춘 랜딩 문의·폼 문의 ──
def inquiry_dates() -> list[date]:
    text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    body = next((b for h, b in sections(text) if h.startswith("문의가 온 페이지")), "")
    return [date.fromisoformat(d) for d in INQ_LINE_RE.findall(body)]


def form_dates() -> list[date]:
    rows = load(FORMS, {}).get("rows", [])
    out = []
    for r in rows:
        try:
            out.append(date.fromisoformat(r.get("date", "")[:10]))
        except ValueError:
            pass
    return out


def weekday_table(ds: list[date], ws: list[tuple[date, date]], today: date) -> list[str]:
    lines = ["| 주(월~일) | 월·화 | 수~일 | 주 합 |", "|---|---|---|---|"]
    for w in ws:
        inside = [d for d in ds if w[0] <= d <= w[1] and d < today]
        mt = sum(1 for d in inside if d.weekday() <= 1)
        rest = len(inside) - mt
        lines.append(f"| {week_label(w, today)} | {mt} | {rest} | {len(inside)} |")
    return lines


# ── GA4 ──
def ga4_days() -> dict[str, dict]:
    return load(GA4, {}).get("days", {}) or {}


def naver_mobile(day: dict) -> int:
    return sum(s.get("sessions", 0) for s in day.get("sources", []) if s.get("source") == NAVER_MOBILE)


def ga4_week_table(days: dict, ws: list[tuple[date, date]], today: date) -> list[str]:
    lines = ["| 주(월~일) | GA4 자료 | 세션 | 네이버 휴대폰 검색 | 폼 전송 | 전화 클릭 | 문자 클릭 |", "|---|---|---|---|---|---|---|"]
    for w in ws:
        ks = [(w[0] + timedelta(days=i)).isoformat() for i in range(7)]
        have = [days[k] for k in ks if k in days and k < today.isoformat()]
        if not have:
            lines.append(f"| {week_label(w, today)} | 없음 | - | - | - | - | - |")
            continue
        t = Counter()
        for d in have:
            t.update(d.get("totals", {}))
        nm = sum(naver_mobile(d) for d in have)
        lines.append(f"| {week_label(w, today)} | {len(have)}일치 | {t['sessions']} | {nm} | {t['quote_submit']} | "
                     f"{t['call_click']} | {t['sms_click']} |")
    return lines


def naver_before_after(days: dict, today: date) -> list[str]:
    def avg(start: date, end: date) -> tuple[float | None, int]:
        ks = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
        have = [days[k] for k in ks if k in days and k < today.isoformat()]
        return (sum(naver_mobile(d) for d in have) / len(have) if have else None), len(have)

    b, nb = avg(STOP_DAY - timedelta(days=7), STOP_DAY - timedelta(days=1))
    a, na = avg(STOP_DAY, STOP_DAY + timedelta(days=6))
    fmt = lambda v: "자료 없음" if v is None else f"{v:.1f}"  # noqa: E731
    return [f"- 앞 7일({md(STOP_DAY - timedelta(days=7))}~{md(STOP_DAY - timedelta(days=1))}, {nb}일치): 하루 평균 {fmt(b)}",
            f"- 뒤 7일({md(STOP_DAY)}~{md(STOP_DAY + timedelta(days=6))}, {na}일치{'' if na == 7 else ' — 아직 다 안 참'}): 하루 평균 {fmt(a)}"]


KINDS = [("구·시군", "/gu/"), ("동", "/pages/"), ("시·도", "/si/"), ("안내", "/guide/"), ("사례", "/cases/")]


def page_kind(path: str) -> str:
    p = unquote(path or "")
    if p in ("/", "/index.html", ""):
        return "첫 화면"
    return next((name for name, part in KINDS if p.startswith(part)), "그 밖")


def landing_kind_table(days: dict, ws: list[tuple[date, date]], today: date) -> list[str]:
    cols = [k for k, _ in KINDS] + ["첫 화면", "그 밖"]
    lines = ["| 주(월~일) | 들어온 페이지 자료 | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for w in ws:
        ks = [(w[0] + timedelta(days=i)).isoformat() for i in range(7)]
        have = [days[k] for k in ks if k in days and k < today.isoformat() and "landing" in days[k]]
        c = Counter()
        for d in have:
            for x in d["landing"]:
                c[page_kind(x.get("page", ""))] += x.get("sessions", 0)
        lines.append(f"| {week_label(w, today)} | {len(have)}일치 | " + " | ".join(str(c[k]) for k in cols) + " |")
    return lines


# ── (4) 동 페이지: 네이버에 넣은 묶음 vs 안 넣은 묶음 ──
def dong_compare(days: dict, today: date) -> list[str]:
    regions = load(REGIONS, [])
    all_pages = {f"/pages/{r['slug']}.html" for r in regions}
    text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    secs = sections(text)
    sent: set[str] = set()
    for head, body in secs:
        if DATE_HEAD_RE.match(head) and NOT_DONE not in head and "네이버" in engines(head):
            for u in URL_RE.findall(body):
                path = "/" + unquote(u.split("pyecha119.com/", 1)[-1])
                if path in all_pages:
                    sent.add(path)
    inquiry = next((b for h, b in secs if h.startswith("문의가 온 페이지")), "")
    inq_pages = {"/" + unquote(u.split("pyecha119.com/", 1)[-1]) for u in URL_RE.findall(inquiry)}
    since = (today - timedelta(days=28)).isoformat()
    land, click = Counter(), set()
    for k, d in days.items():
        if not since <= k < today.isoformat():
            continue
        for x in d.get("landing", []):
            land[unquote(x.get("page", ""))] += x.get("sessions", 0)
        for p in d.get("pages", []):
            if p.get("quote_submit") or p.get("call_click"):
                click.add(unquote(p.get("page", "")))
    lines = ["| 묶음 | 페이지 수 | 최근 4주 들어온 방문 합 | 폼·전화 누른 페이지 | 문의가 온 페이지 |", "|---|---|---|---|---|"]
    for name, group in (("네이버 칸에 한 번이라도 오름", sent), ("한 번도 안 오름", all_pages - sent)):
        lines.append(f"| {name} | {len(group)} | {sum(land[p] for p in group)} | {len(group & click)} | {len(group & inq_pages)} |")
    return lines


def build(today: date) -> str:
    days = ga4_days()
    ws6, ws4 = weeks(today, 6), weeks(today, 4)
    month = today.strftime("%Y-%m")
    forms_month = sum(d.get("totals", {}).get("quote_submit", 0) for k, d in days.items() if k.startswith(month))
    out = [
        "# 17일 판단 보고 숫자 한 장",
        "",
        f"만든 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} (기준일 {today.isoformat()}, 어제까지 셈) · `scripts/judgment_inputs.py --write` 가 만듭니다. 손으로 고치지 않습니다.",
        "돈 숫자·개인정보 없음. GA4 는 광고 차단·추적 거부 손님을 못 세므로 실제보다 적습니다(추세용).",
        "",
        "## 1. 요일 맞춘 문의 (최근 6주, 월~일이 한 주)",
        "",
        "읽는 법: **수~일끼리, 월·화끼리 견준다. 높은 이틀과 낮은 닷새를 견주지 않는다.**",
        "",
        "### 랜딩 문의 (docs/index-requests.md \"문의가 온 페이지\" 날짜 줄)",
        "",
        *weekday_table(inquiry_dates(), ws6, today),
        "",
        "### 폼 문의 (data/form_inquiries.json)",
        "",
        *weekday_table(form_dates(), ws6, today),
        "",
        "## 2. GA4 주 합 (최근 6주)",
        "",
        "네이버 휴대폰 검색 = 출처 `m.search.naver.com / referral` 세션.",
        "",
        *ga4_week_table(days, ws6, today),
        "",
        "아침 색인을 그만둔 11/11 앞 7일과 뒤 7일의 네이버 휴대폰 검색 하루 평균:",
        "",
        *naver_before_after(days, today),
        "",
        "## 3. 페이지 종류별 들어온 방문 (최근 4주, 세션이 시작된 페이지)",
        "",
        "날짜마다 세션 많은 50개 (페이지 × 출처) 줄의 합이라, 하루 50줄을 넘는 날은 조금 덜 셉니다.",
        "",
        *landing_kind_table(days, ws4, today),
        "",
        "## 4. 동 페이지 견주기 (네이버에 넣은 묶음 vs 안 넣은 묶음)",
        "",
        "\"오름\" = docs/index-requests.md 의 네이버 날짜 칸(\"요청 못 함\" 칸 빼고)에 한 번이라도 적힌 동 페이지. "
        "방문·누름은 최근 4주(기준일 전 28일), 문의는 \"문의가 온 페이지\" 칸에 그 동 페이지 주소가 적힌 것(대부분 구 페이지 주소로 적혀 0에 가까움).",
        "",
        *dong_compare(days, today),
        "",
        "## 5. 이번 달 폼 전송 (Web3Forms 무료 한도 참고)",
        "",
        f"- {today.year}년 {today.month}월 GA4 폼 전송 {forms_month}건 ÷ {WEB3FORMS_FREE} = {forms_month / WEB3FORMS_FREE:.0%} "
        "(참고값. 실제 사용량은 Web3Forms 화면에 있음)",
        "",
        "---",
        "",
        "네이버 순위는 2026-11-11부터 수집 중단 — '안 돌았음'으로 세지 않는다. 지금 규칙은 docs/current-rules.md",
    ]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--today", help="기준일(YYYY-MM-DD, 기본 오늘 한국 시간)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    today = date.fromisoformat(args.today) if args.today else datetime.now(KST).date()
    text = build(today)
    if args.write:
        OUT.write_text(text, encoding="utf-8")
        print(f"저장: {OUT.relative_to(ROOT).as_posix()}")
    else:
        print(text)


if __name__ == "__main__":
    main()
