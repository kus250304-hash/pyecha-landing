"""
GA4 로 "어디서 왔나"를 매일 센다(2026-11-04 병한님). 폼 문의가 네이버·구글·유튜브·직접 중 어디서 오는지 보려는 것.
사이트 폼 칸·문구·버튼은 바꾸지 않는다(측정만).

사용법
  python scripts/ga4_daily.py                    # 어제 하루(한국 시간)를 받아 data/ga4_daily.json·docs/ga4-sources.md 저장
  python scripts/ga4_daily.py --since 2026-10-20 # 그날부터 어제까지 받아 합침(과거치 채우기)
  python scripts/ga4_daily.py --push             # PC 예약 작업 "구글 색인 확인 (매일 낮)" 뒤에: git pull → 받기 → 두 파일만 커밋·푸시
  python scripts/ga4_daily.py --from-json        # API 없이 저장된 json 으로 docs/ga4-sources.md 만 다시 만듦
  python3 scripts/ga4_daily.py report [--today YYYY-MM-DD]   # 보고 한 줄(아침 보고·PC 작업 보고, 저장된 json 만 읽음)

- API: GA4 Data API v1beta properties/{속성 ID}:runReport. 속성 ID(숫자)는 data/site_config.json 의 ga4_property_id.
  비어 있으면 아무것도 하지 않고 "GA4 속성 ID 알려 주세요" 한 줄만 알린다. (ga4_id 의 G-… 은 측정 ID 라 API 에 못 씀)
- 열쇠: 서치 콘솔과 같은 서비스 계정 C:\\Users\\AOMG\\gsc-key.json(GSC_KEY), 서명은 gsc_index_check.access_token(범위 analytics.readonly).
  값은 출력·기록하지 않는다. 열쇠가 없으면 "키 없음"만 알리고 파일을 바꾸지 않는다.
  준비(병한님 1회): docs/ga4-setup.md — Google Analytics Data API 사용 + GA4 속성에 서비스 계정 뷰어 추가 + 속성 ID.
- 받는 것 (가) 날짜 × 세션 소스/매체별 세션 수와 이벤트 quote_submit·call_click·sms_click 수
           (나) 날짜 × 페이지 경로별 quote_submit·call_click 수(날짜마다 상위 20).
- 나누기: 소스에 naver → 네이버, google → 구글, youtube·youtu.be → 유튜브, (direct) → 직접, 그 밖 → 기타.
  원래 소스/매체는 날짜마다 세션 많은 15개까지 json 의 sources 에 남긴다(나중에 다시 나눌 수 있게).
- 개인정보 없음: 세션·이벤트 수, 소스 이름, 페이지 경로만. 같은 날짜를 다시 받으면 덮어쓴다. 손으로 고치지 않는다.
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gsc_index_check as G  # noqa: E402

OUT = ROOT / "data" / "ga4_daily.json"
DOC = ROOT / "docs" / "ga4-sources.md"
CONFIG = ROOT / "data" / "site_config.json"
KST = timezone(timedelta(hours=9))
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
RUN_URL = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"
EVENTS = ["quote_submit", "call_click", "sms_click"]
BUCKETS = ["네이버", "구글", "유튜브", "직접", "기타"]
WEEK = "월화수목금토일"
PAGE_TOP = 20
SOURCE_TOP = 15
DOC_DAYS = 60
STALE_DAYS = 3  # report: 마지막 날이 이보다 오래되면 "자료 없음"


def kst_today() -> date:
    return datetime.now(KST).date()


def day_name(d: str) -> str:
    x = date.fromisoformat(d)
    return f"{x.month}/{x.day}({WEEK[x.weekday()]})"


def bucket(source: str) -> str:
    s = (source or "").lower()
    if "naver" in s:
        return "네이버"
    if "google" in s:
        return "구글"
    if "youtube" in s or "youtu.be" in s:
        return "유튜브"
    if s == "(direct)":
        return "직접"
    return "기타"


# ── API ──
def run_report(token: str, pid: str, body: dict) -> list[list[str]]:
    """runReport 를 끝까지(쪽 나눔) 받아 [차원값…, 지표값…] 줄 목록으로."""
    rows, offset = [], 0
    while True:
        req = urllib.request.Request(RUN_URL.format(pid=pid), data=json.dumps({**body, "limit": 10000, "offset": offset}).encode(),
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read())
        for row in res.get("rows", []):
            rows.append([v.get("value", "") for v in row.get("dimensionValues", [])] + [v.get("value", "0") for v in row.get("metricValues", [])])
        offset += 10000
        if offset >= int(res.get("rowCount", 0) or 0):
            return rows


def event_filter(names: list[str]) -> dict:
    return {"filter": {"fieldName": "eventName", "inListFilter": {"values": names}}}


def iso(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def fetch(token: str, pid: str, start: str, end: str) -> dict:
    span = [{"startDate": start, "endDate": end}]
    days: dict[str, dict] = {}
    d = date.fromisoformat(start)
    while d <= date.fromisoformat(end):  # 0건인 날도 "받은 날"로 남긴다
        days[d.isoformat()] = {"sessions": {b: 0 for b in BUCKETS}, "events": {b: {e: 0 for e in EVENTS} for b in BUCKETS},
                               "totals": {"sessions": 0, **{e: 0 for e in EVENTS}}, "sources": [], "pages": []}
        d += timedelta(days=1)
    raw_src: dict[str, Counter] = defaultdict(Counter)
    # (가) 세션
    for dt, src, med, n in run_report(token, pid, {"dateRanges": span, "metrics": [{"name": "sessions"}],
                                                   "dimensions": [{"name": "date"}, {"name": "sessionSource"}, {"name": "sessionMedium"}]}):
        day = days.get(iso(dt))
        if day is None:
            continue
        day["sessions"][bucket(src)] += int(n)
        day["totals"]["sessions"] += int(n)
        raw_src[iso(dt)][f"{src} / {med}"] += int(n)
    # (가) 이벤트
    for dt, src, ev, n in run_report(token, pid, {"dateRanges": span, "metrics": [{"name": "eventCount"}],
                                                  "dimensions": [{"name": "date"}, {"name": "sessionSource"}, {"name": "eventName"}],
                                                  "dimensionFilter": event_filter(EVENTS)}):
        day = days.get(iso(dt))
        if day is None or ev not in EVENTS:
            continue
        day["events"][bucket(src)][ev] += int(n)
        day["totals"][ev] += int(n)
    # (나) 페이지
    pages: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for dt, path, ev, n in run_report(token, pid, {"dateRanges": span, "metrics": [{"name": "eventCount"}],
                                                   "dimensions": [{"name": "date"}, {"name": "pagePath"}, {"name": "eventName"}],
                                                   "dimensionFilter": event_filter(["quote_submit", "call_click"])}):
        if iso(dt) in days:
            pages[iso(dt)][unquote(path)][ev] += int(n)
    for k, day in days.items():
        day["sources"] = [{"source": s, "sessions": n} for s, n in raw_src[k].most_common(SOURCE_TOP)]
        ranked = sorted(pages[k].items(), key=lambda x: (-x[1]["quote_submit"], -x[1]["call_click"], x[0]))[:PAGE_TOP]
        day["pages"] = [{"page": p, "quote_submit": c["quote_submit"], "call_click": c["call_click"]} for p, c in ranked]
    return days


# ── 저장·문서 ──
def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"updated": "", "days": {}}


def save(data: dict) -> None:
    data["days"] = dict(sorted(data["days"].items()))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_doc(data)


def cell(day: dict, b: str) -> str:
    return f"{day['sessions'][b]} ({day['events'][b]['quote_submit']})"


def write_doc(data: dict) -> None:
    days = sorted(data["days"].items(), reverse=True)
    lines = ["# 어디서 왔나 (GA4, 매일 자동)", "",
             "`scripts/ga4_daily.py` 가 PC 예약 작업 \"구글 색인 확인 (매일 낮)\" 뒤에 만듭니다. 손으로 고치지 않습니다.",
             "칸의 숫자는 **방문 세션 수**이고 괄호 안은 그 세션의 **폼 전송(quote_submit) 수**입니다. "
             "네이버·구글·유튜브·직접(주소 직접 입력·앱·즐겨찾기 등) 밖은 기타(다음·카카오·인스타그램·다른 사이트 등).",
             "GA4 는 광고 차단·추적 거부 손님을 못 세므로 실제보다 적게 나옵니다(추세용). 폼 문의 실제 건수는 아침 보고 \"폼 문의\" 칸.",
             f"마지막 갱신: {data.get('updated') or '-'}", ""]
    if not days:
        lines += ["(아직 자료 없음 — docs/ga4-setup.md 의 1회 작업 뒤 생깁니다)", ""]
    else:
        lines += ["| 날짜 | 네이버 | 구글 | 유튜브 | 직접 | 기타 | 합계 세션 (폼 · 전화 클릭 · 문자 클릭) |", "|---|---|---|---|---|---|---|"]
        for k, day in days[:DOC_DAYS]:
            t = day["totals"]
            lines.append(f"| {day_name(k)} | " + " | ".join(cell(day, b) for b in BUCKETS)
                         + f" | {t['sessions']} (폼 {t['quote_submit']} · 전화 {t['call_click']} · 문자 {t['sms_click']}) |")
        recent = [d for _, d in days[:7]]
        agg: dict[str, Counter] = defaultdict(Counter)
        for d in recent:
            for p in d["pages"]:
                agg[p["page"]].update({"quote_submit": p["quote_submit"], "call_click": p["call_click"]})
        top = sorted(agg.items(), key=lambda x: (-x[1]["quote_submit"], -x[1]["call_click"], x[0]))[:10]
        first, last = days[min(6, len(days) - 1)][0], days[0][0]
        lines += ["", f"## 폼 전송 많은 페이지 10개 ({day_name(first)}~{day_name(last)})", ""]
        if top:
            lines += ["| 페이지 | 폼 전송 | 전화 클릭 |", "|---|---|---|"]
            lines += [f"| {p} | {c['quote_submit']} | {c['call_click']} |" for p, c in top]
        else:
            lines.append("(이 기간 폼 전송·전화 클릭 없음)")
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── 보고 ──
def report(today: date) -> None:
    data = load()
    keys = sorted(k for k in data["days"] if k < today.isoformat())
    if not keys or (today - date.fromisoformat(keys[-1])).days > STALE_DAYS:
        print("어디서 왔나: GA4 자료 없음(권한 확인 — docs/ga4-setup.md, PC 예약 작업 '구글 색인 확인 (매일 낮)')")
        return
    k = keys[-1]
    day = data["days"][k]
    when = f"어제 {day_name(k)}" if k == (today - timedelta(days=1)).isoformat() else f"{day_name(k)}, 어제 자료 아직 없음"
    s, t = day["sessions"], day["totals"]
    parts = " · ".join(f"{b} {s[b]}" for b in BUCKETS[:4]) + (f" · 기타 {s['기타']}" if s["기타"] else "")
    print(f"어디서 왔나({when}, 방문 세션): {parts} "
          f"(폼 전송 {t['quote_submit']} · 전화 클릭 {t['call_click']} · 문자 클릭 {t['sms_click']})")
    by = [f"{b} {sum(day['events'][b].values())}" for b in BUCKETS if sum(day["events"][b].values())]
    if by:
        print("  - 누른 곳(폼·전화·문자 합): " + " · ".join(by))
    top = [p for p in day["pages"] if p["quote_submit"] or p["call_click"]][:5]
    if top:
        print("  - 많이 누른 페이지: " + ", ".join(f"{p['page']} 폼 {p['quote_submit']}·전화 {p['call_click']}" for p in top))


# ── git ──
def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def push(summary: str) -> str:
    rels = [OUT.relative_to(ROOT).as_posix(), DOC.relative_to(ROOT).as_posix(), "data/dong_boost.json"]  # 반응 온 동 페이지(2026-11-05)
    if not git("status", "--porcelain", "--", *rels).stdout.strip():
        return "바뀐 것 없음(커밋 안 함)"
    git("add", "--", *rels)
    r = git("commit", "-m", f"GA4 sources ({kst_today().isoformat()}): {summary}", "--", *rels)
    if r.returncode:
        return "커밋 실패: " + (r.stderr or r.stdout).strip()[:200]
    for _ in range(2):
        if git("push", "origin", "main").returncode == 0:
            return "푸시 " + git("rev-parse", "--short", "HEAD").stdout.strip()
        git("pull", "--rebase", "--autostash", "origin", "main")
    return "푸시 실패(다음 실행 때 다시)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="fetch", choices=["fetch", "report"])
    ap.add_argument("--since", help="이 날짜(YYYY-MM-DD)부터 어제까지")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--from-json", action="store_true")
    ap.add_argument("--today", help="report 기준일(YYYY-MM-DD, 기본 오늘 한국 시간)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.cmd == "report":
        report(date.fromisoformat(args.today) if args.today else kst_today())
        return
    if args.from_json:
        write_doc(load())
        print(f"저장: {DOC.relative_to(ROOT).as_posix()}")
        return
    pid = str(json.loads(CONFIG.read_text(encoding="utf-8")).get("ga4_property_id") or "").strip()
    if not pid.isdigit():
        print("GA4 속성 ID 알려 주세요(data/site_config.json 의 ga4_property_id 가 비어 있음, docs/ga4-setup.md ③) — 건너뜀")
        return
    if not G.KEY.exists():
        print(f"키 없음({G.KEY}) — 건너뜀")
        return
    if args.push:
        git("checkout", "main")
        git("pull", "--rebase", "--autostash", "origin", "main")
    end = (kst_today() - timedelta(days=1)).isoformat()
    start = args.since or end
    if start > end:
        print(f"받을 날짜 없음({start} > {end})")
        return
    try:
        token = G.access_token(json.loads(G.KEY.read_text(encoding="utf-8")), SCOPE)
        days = fetch(token, pid, start, end)
    except urllib.error.HTTPError as e:
        why = ""
        try:
            err = json.loads(e.read()).get("error", {})
            why = err.get("status", "") + (" " + next((d.get("reason", "") for d in err.get("details", []) if d.get("reason")), "")).rstrip()
        except Exception:
            pass
        hint = " — docs/ga4-setup.md ①(API 사용)·②(뷰어 추가)·③(속성 ID) 확인" if e.code in (400, 403, 404) else ""
        print(f"실패: GA4 자료 없음(권한 확인) HTTP {e.code} {why}{hint}")
        sys.exit(1)
    except (urllib.error.URLError, KeyError, ValueError) as e:
        print(f"실패: GA4 접속 못 함({type(e).__name__}) — 인터넷·키 파일 확인")
        sys.exit(1)
    data = load()
    data["days"].update(days)
    data["updated"] = datetime.now(KST).isoformat(timespec="minutes")
    save(data)
    t = Counter()
    for d in days.values():
        t.update(d["totals"])
    summary = f"{start}~{end} sessions {t['sessions']}, quote_submit {t['quote_submit']}"
    print(f"성공: {day_name(start)}~{day_name(end)} {len(days)}일 · 세션 {t['sessions']} · 폼 전송 {t['quote_submit']}"
          f" · 전화 클릭 {t['call_click']} · 문자 클릭 {t['sms_click']}")
    report(kst_today())
    # 반응 온 동 페이지 목록(2026-11-05, scripts/proof_blocks.py): 그 동 페이지에 시·군의 최근 진행한 차·후기 칸을 보인다
    import proof_blocks
    proof_blocks.write_boost()
    print(f"반응 온 동 페이지 {len(proof_blocks.compute_boost())}곳(data/dong_boost.json)")
    if args.push:
        print(push(summary))


if __name__ == "__main__":
    main()
