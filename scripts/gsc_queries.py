"""
구글 서치 콘솔 "노출은 되는데 클릭 없는 검색어"를 매주 뽑는다(2026-10-31 병한님, 이미 있는 노출을 클릭으로).
아침 보고(월요일)·월간 FAQ 갱신·폐차119 블로그 B형 글이 docs/gsc-queries.md 를 재료로 읽는다.

사용법
  python scripts/gsc_queries.py           # 최근 28일 받아 data/gsc_queries.json·docs/gsc-queries.md 저장
  python scripts/gsc_queries.py --push    # PC 예약 작업 "폐차_검색어_주간"용: git pull → 받기 → 두 파일만 커밋·푸시
  python scripts/gsc_queries.py --from-json   # API 없이 저장된 json 으로 docs/gsc-queries.md 만 다시 만듦

- API: searchconsole searchAnalytics.query, 검색어×페이지(dimensions query·page), 국가 KOR, 웹 검색, 최근 28일
  (끝 = 어제, 한국 시간, 아직 확정 안 된 최근 자료 포함 dataState all). 속성은 gsc_index_check 와 같은 순서
  (sc-domain:pyecha119.com → https://pyecha119.com/), 열쇠도 같은 C:\\Users\\AOMG\\gsc-key.json(GSC_KEY), 서명은 gsc_index_check.access_token.
  열쇠 값은 출력·기록하지 않는다. 열쇠가 없거나 API 오류면 "키 없음"/"오류"만 알리고 파일을 바꾸지 않는다.
- 검색어에 전화번호·차량번호·번지·동호수가 보이면 json·md 어디에도 넣지 않는다(구글이 개인 검색어는 원래 숨기지만 한 번 더).
- docs/gsc-queries.md: ① 클릭 0 · 노출 5회 이상 검색어(노출 많은 순, 검색어·노출·평균 순위·뜬 페이지, 100줄까지)
  ② 클릭 있는 검색어 10개(클릭 많은 순) ③ 블로그 제목 후보 5개(B형, ①에서 30자 이내 검색어 그대로).
  "최고가·제일·많이 주는·무료" 같은 말이 든 검색어는 "사실대로 답하는 글 후보"로 표시한다(글에서 금액·최고가를 단정하지 않고
  비교하는 방식 그대로 답하라는 뜻). 평균 순위는 노출로 가중 평균, 뜬 페이지는 노출이 가장 많은 페이지(여러 곳이면 "외 N").
  손으로 고치지 않는다.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gsc_index_check as G  # noqa: E402
from build_cases import CUSTOMER_RE  # noqa: E402

OUT = ROOT / "data" / "gsc_queries.json"
DOC = ROOT / "docs" / "gsc-queries.md"
QUERY_URL = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
DAYS = 28
MIN_IMPRESSIONS = 5
TABLE_MAX = 100
BLOG_MAX_LEN = 30
FACT_RE = re.compile(r"최고가|제일|가장|많이\s*주|비싸게|높게|무료|공짜|최대|1등|1위|보장")
FACT_MARK = "사실대로 답하는 글 후보"


def call(token: str, site: str, body: dict) -> list[dict]:
    body = dict(body, type="web", dataState="all",
                dimensionFilterGroups=[{"filters": [{"dimension": "country", "operator": "equals", "expression": "kor"}]}])
    req = urllib.request.Request(QUERY_URL.format(site=urllib.parse.quote(site, safe="")), data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()).get("rows", [])


def totals(token: str, site: str, start: str, end: str) -> dict:
    """검색어를 나누지 않은 전체 숫자(구글이 숨긴 검색어 포함)."""
    t = (call(token, site, {"startDate": start, "endDate": end}) or [{}])[0]
    return {"clicks": t.get("clicks", 0), "impressions": t.get("impressions", 0), "position": round(t.get("position", 0), 1)}


def fetch(token: str, site: str, start: str, end: str) -> list[dict]:
    rows, start_row = [], 0
    while True:
        got = call(token, site, {"startDate": start, "endDate": end, "dimensions": ["query", "page"],
                                 "rowLimit": 25000, "startRow": start_row})
        rows += [{"query": x["keys"][0], "page": x["keys"][1], "clicks": x["clicks"], "impressions": x["impressions"],
                  "position": round(x["position"], 1)} for x in got]
        if len(got) < 25000:
            return rows
        start_row += 25000


def private(q: str) -> bool:
    return bool(CUSTOMER_RE.search(q))


def by_query(rows: list[dict]) -> list[dict]:
    acc = defaultdict(lambda: {"clicks": 0, "impressions": 0, "pos_sum": 0.0, "pages": defaultdict(int)})
    for r in rows:
        a = acc[r["query"]]
        a["clicks"] += r["clicks"]
        a["impressions"] += r["impressions"]
        a["pos_sum"] += r["position"] * r["impressions"]
        a["pages"][r["page"]] += r["impressions"]
    out = []
    for q, a in acc.items():
        pages = sorted(a["pages"], key=lambda p: -a["pages"][p])
        out.append({"query": q, "clicks": a["clicks"], "impressions": a["impressions"],
                    "position": round(a["pos_sum"] / a["impressions"], 1) if a["impressions"] else 0,
                    "page": pages[0], "more_pages": len(pages) - 1})
    return out


def page_text(x: dict) -> str:
    path = urllib.parse.unquote(urllib.parse.urlsplit(x["page"]).path) or "/"
    return path + (f" 외 {x['more_pages']}" if x["more_pages"] else "")


def cell(s: str) -> str:
    return s.replace("|", "/")


def no_click(qs: list[dict]) -> list[dict]:
    return sorted((x for x in qs if x["clicks"] == 0 and x["impressions"] >= MIN_IMPRESSIONS),
                  key=lambda x: (-x["impressions"], x["position"], x["query"]))


def blog_titles(nc: list[dict]) -> list[dict]:
    """①에서 30자 이내 검색어 그대로, 띄어쓰기만 다른 검색어는 하나만."""
    seen, out = set(), []
    for x in nc:
        key = re.sub(r"\s", "", x["query"])
        if len(x["query"]) > BLOG_MAX_LEN or key in seen:
            continue
        seen.add(key)
        out.append(x)
        if len(out) == 5:
            break
    return out


def write_doc(data: dict) -> tuple[int, int]:
    qs = by_query(data["rows"])
    nc = no_click(qs)
    clicked = sorted((x for x in qs if x["clicks"] > 0), key=lambda x: (-x["clicks"], -x["impressions"]))[:10]
    mark = lambda q: FACT_MARK if FACT_RE.search(q) else ""  # noqa: E731
    L = ["# 서치 콘솔 검색어 (클릭 없는 검색어)", "",
         "`scripts/gsc_queries.py` 가 매주 월요일 낮 12시 25분 무렵(PC 예약 작업 \"폐차_검색어_주간\") 다시 만듭니다. 손으로 고치지 않습니다.",
         "아침 보고(월요일)·월간 FAQ 갱신·폐차119 블로그 B형 글이 읽습니다. 검색어는 손님 말 그대로의 질문 후보이며, 글에서는 금액·최고가를 단정하지 않습니다.", "",
         f"기준: {data['updated']} 받음 · 기간 {data['start']} ~ {data['end']}(28일) · 국가 한국 · 웹 검색 · 속성 {data['site']}",
         f"요약: 검색어 {len(qs)}개 · 클릭 없는 검색어(노출 {MIN_IMPRESSIONS}회 이상) {len(nc)}개 · 클릭 있는 검색어 {sum(x['clicks'] > 0 for x in qs)}개"
         f" · 검색어가 보이는 노출 {sum(x['impressions'] for x in qs)}·클릭 {sum(x['clicks'] for x in qs)}"
         + (f" / 전체 노출 {data['totals']['impressions']}·클릭 {data['totals']['clicks']}·평균 순위 {data['totals']['position']}"
            "(나머지는 구글이 검색 횟수가 적은 검색어를 숨김)" if data.get("totals") else ""), "",
         f"## 클릭 없는 검색어 (클릭 0 · 노출 {MIN_IMPRESSIONS}회 이상, 노출 많은 순)", ""]
    if nc:
        L += ["| # | 검색어 | 노출 | 평균 순위 | 뜬 페이지 | 표시 |", "|---|---|---|---|---|---|"]
        L += [f"| {i} | {cell(x['query'])} | {x['impressions']} | {x['position']} | {cell(page_text(x))} | {mark(x['query'])} |"
              for i, x in enumerate(nc[:TABLE_MAX], 1)]
        if len(nc) > TABLE_MAX:
            L.append(f"\n(나머지 {len(nc) - TABLE_MAX}개는 data/gsc_queries.json)")
    else:
        L.append("없음(자료가 아직 적음)")
    L += ["", "## 클릭 있는 검색어 (클릭 많은 순 10개)", ""]
    if clicked:
        L += ["| # | 검색어 | 클릭 | 노출 | 평균 순위 | 뜬 페이지 |", "|---|---|---|---|---|---|"]
        L += [f"| {i} | {cell(x['query'])} | {x['clicks']} | {x['impressions']} | {x['position']} | {cell(page_text(x))} |"
              for i, x in enumerate(clicked, 1)]
    else:
        L.append("없음")
    L += ["", "## 블로그 제목 후보 (B형 손님 질문 글, 검색어 그대로 · 30자 이내)", "",
          "폐차119 블로그 초안 세션이 읽는 칸입니다. 제목은 검색어 그대로 쓰고, 본문 첫 문장은 \"네/아니요 + 이유\"(얼마·어디 질문은 답 자체),"
          " 금액·시세·최고가·결과 약속은 쓰지 않습니다. \"사실대로 답하는 글 후보\"는 폐차값·수출값 둘 다 보고 더 높은 쪽으로 안내하는 방식 그대로 답합니다.", ""]
    titles = blog_titles(nc)
    L += [f"{i}. {x['query']} — 노출 {x['impressions']} · 순위 {x['position']} · {page_text(x)}" + (f" · {FACT_MARK}" if mark(x["query"]) else "")
          for i, x in enumerate(titles, 1)] or ["없음(자료가 아직 적음)"]
    DOC.write_text("\n".join(L) + "\n", encoding="utf-8")
    return len(qs), len(nc)


def push(day: str, summary: str) -> str:
    rels = [p.relative_to(ROOT).as_posix() for p in (OUT, DOC)]
    if not G.git("status", "--porcelain", "--", *rels).stdout.strip():
        return "바뀐 것 없음(커밋 안 함)"
    G.git("add", "--", *rels)
    r = G.git("commit", "-m", f"GSC queries ({day}): {summary}", "--", *rels)
    if r.returncode:
        return "커밋 실패: " + (r.stderr or r.stdout).strip()[:200]
    for _ in range(2):
        if G.git("push", "origin", "main").returncode == 0:
            return "푸시 " + G.git("rev-parse", "--short", "HEAD").stdout.strip()
        G.git("pull", "--rebase", "--autostash", "origin", "main")
    return "푸시 실패(다음 실행 때 다시)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--from-json", action="store_true")
    args = ap.parse_args()
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    if args.from_json:
        n, nc = write_doc(json.loads(OUT.read_text(encoding="utf-8")))
        print(f"docs/gsc-queries.md 다시 만듦: 검색어 {n}개 · 클릭 없는 검색어 {nc}개")
        return
    day = G.today()
    if args.push:
        G.git("checkout", "main")
        G.git("pull", "--rebase", "--autostash", "origin", "main")
    if not G.KEY.exists():
        print(f"키 없음({G.KEY}) — 건너뜀")
        return
    end = date.fromisoformat(day) - timedelta(days=1)
    start = end - timedelta(days=DAYS - 1)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    sites = [old["site"]] + [s for s in G.SITES if s != old["site"]] if old.get("site") else G.SITES
    try:
        token = G.access_token(json.loads(G.KEY.read_text(encoding="utf-8")))
        rows = site = None
        for i, s in enumerate(sites):
            try:
                rows, site = fetch(token, s, start.isoformat(), end.isoformat()), s
                total = totals(token, s, start.isoformat(), end.isoformat())
                break
            except urllib.error.HTTPError as e:
                if e.code != 403 or i == len(sites) - 1:
                    raise
    except urllib.error.HTTPError as e:
        print(f"오류: 서치 콘솔 응답 HTTP {e.code}" + (" — 서비스 계정 권한 확인" if e.code == 403 else "") + " · 파일 안 바꿈")
        sys.exit(1)
    except (urllib.error.URLError, KeyError, ValueError) as e:
        print(f"오류: 키로 접속 못 함({type(e).__name__}) · 파일 안 바꿈")
        sys.exit(1)
    kept = [r for r in rows if not private(r["query"])]
    data = {"updated": day, "site": site, "start": start.isoformat(), "end": end.isoformat(),
            "totals": total, "dropped_private": len(rows) - len(kept),
            "rows": sorted(kept, key=lambda r: (-r["impressions"], r["query"], r["page"]))}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n, nc = write_doc(data)
    print(f"성공: 검색어×페이지 {len(kept)}줄 · 검색어 {n}개 · 클릭 없는 검색어 {nc}개 · 기간 {data['start']} ~ {data['end']} · 속성 {site}"
          + (f" · 개인정보로 보여 뺀 줄 {data['dropped_private']}" if data["dropped_private"] else ""))
    if args.push:
        print(push(day, f"{n} queries, {nc} no-click"))


if __name__ == "__main__":
    main()
