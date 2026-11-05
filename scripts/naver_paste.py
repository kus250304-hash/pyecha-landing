"""네이버 통합검색 화면 붙여넣기 분석기 (2026-11-05 병한님, 상자 A-2).

병한님이 Claude 코드 탭에 "표본 붙여넣기: 목포 폐차장" 치고 네이버 통합검색 화면 글자를
Ctrl+V 로 붙이면, Claude 가 그 글자를 docs/naver-paste/{날짜}/{검색어}.txt 로 저장하고
이 스크립트를 돌린다.

    python scripts/naver_paste.py "목포 폐차장"                 # 저장된 txt 를 분석
    python scripts/naver_paste.py "목포 폐차장" --file 붙인글.txt # 다른 파일에서 가져와 저장 후 분석
    python scripts/naver_paste.py "목포 폐차장" < 붙인글.txt      # 표준 입력에서 가져와 저장 후 분석
    옵션: --date YYYY-MM-DD(기본 오늘), --debug(칸 나뉜 모양 보기), --no-record(기록 안 함), --push

하는 일
1. 붙인 글자를 저장한다(전화번호 꼴은 ***-****-**** 로 가림).
2. 화면을 칸(파워링크·플레이스·관련질문·블로그·웹사이트 …)으로 나눠 센다.
   파워링크 수 / 플레이스 수 / 관련질문 문장 전부 / 블로그 칸 글 수·우리 블로그(abh77790, 폐차119) 몇 번째 /
   웹사이트 칸 순서(pyecha119 몇 번째, 지인 도메인 몇 번째, kadra, 그 외 도메인) / 당근 프로필 유무.
3. docs/weekly-rank-log.md 맨 위 "0) 표본 붙여넣기" 날짜별 표에 한 줄(같은 날 같은 검색어면 바꿈),
   관련질문 문장은 data/naver_related_questions.json 에 모은다(날짜·검색어·지역·문장·틀).
   틀은 지역 이름을 {지역} 으로 바꾼 문장이라, 구 페이지 관련질문 FAQ(11/10 상자 B-2)의 재료로 쓴다.

화면 글자는 붙이는 기기·네이버 화면 개편에 따라 모양이 달라서 칸 나누기는 어림이다.
처음 보는 모양이면 --debug 로 칸이 어떻게 잡혔는지 보고 HEADERS 를 고친다.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASTE_DIR = ROOT / "docs" / "naver-paste"
LOG_MD = ROOT / "docs" / "weekly-rank-log.md"
QUESTIONS_JSON = ROOT / "data" / "naver_related_questions.json"
KST = timezone(timedelta(hours=9))

OUR_DOMAIN = "pyecha119.com"
OUR_BLOG = ("abh77790", "폐차119")
KADRA = "kadra.or.kr"

# 칸 제목(띄어쓰기·괄호·"더보기" 뺀 꼴) → 칸 종류
HEADERS = {
    "파워링크": "ads",
    "플레이스": "place",
    "관련질문": "questions",
    "연관질문": "questions",
    "함께찾은질문": "questions",
    "함께많이찾는질문": "questions",
    "블로그": "blog",
    "카페": "cafe",
    "웹사이트": "web",
    "웹문서": "web",
    "지식iN": "kin",
    "뉴스": "news",
    "이미지": "image",
    "동영상": "video",
    "클립": "clip",
    "숏폼": "clip",
    "쇼핑": "shop",
    "지식백과": "dict",
    "인플루언서": "influencer",
    "AI브리핑": "ai",
    "당근": "daangn",
    "동네업체": "daangn",
    "연관검색어": "related_kw",
    "함께많이찾는": "related_kw",
    "브랜드콘텐츠": "brand",
    "인기글": "popular",
    "인기주제": "popular",
}
# 제목 뒤에 말이 더 붙어도 칸 제목으로 보는 것("파워링크 '목포 폐차장' 관련 광고입니다")
PREFIX_HEADERS = ("파워링크", "관련질문", "연관질문")

PHONE_RE = re.compile(r"(?<!\d)(0\d{1,2}|1[5-9]\d\d)[-. )]?\d{3,4}[-. ]?\d{4}(?!\d)")
TLD = r"(?:co\.kr|or\.kr|go\.kr|ne\.kr|pe\.kr|re\.kr|ac\.kr|com|net|org|kr|me|io|shop|store|site|xyz|info|biz|app|dev)"
DOMAIN_RE = re.compile(
    r"(?<![\w@.-])(?:https?://)?((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+" + TLD + r")(?![\w-])",
    re.I,
)
DATE_RE = re.compile(r"^(\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.?|\d+\s?(분|시간|일|주|개월)\s?전|어제)$")
ADDR_RE = re.compile(r"^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|전남광주)\S*\s+\S+(시|군|구)")
STATUS_RE = re.compile(r"^(영업\s?중|영업\s?종료|영업\s?전|곧\s?영업|오늘\s?휴무|휴무|24시간\s?영업|브레이크\s?타임)")
QUESTION_RE = re.compile(r"(\?|나요|까요|가요|인가요|있나요|되나요|하나요|할까요|일까요)\s*$")


def today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def norm(line: str) -> str:
    s = re.sub(r"\(.*?\)", "", line)
    s = s.replace("더보기", "").replace("전체보기", "")
    return re.sub(r"\s+", "", s).strip("·|>›:")


def header_kind(line: str) -> str | None:
    s = line.strip()
    if not s or len(s) > 40:
        return None
    n = norm(s)
    if n in HEADERS:
        return HEADERS[n]
    for p in PREFIX_HEADERS:
        if n.startswith(p) and len(n) <= 30 and "?" not in s:
            return HEADERS[p]
    return None


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    """칸 종류 → 그 칸의 줄들. 같은 종류가 여러 번 나오면(맨 위 메뉴 등) 줄이 가장 많은 칸을 쓴다."""
    found: list[tuple[str, int, int]] = []
    cur: tuple[str, int] | None = None
    for i, line in enumerate(lines):
        k = header_kind(line)
        if k:
            if cur:
                found.append((cur[0], cur[1] + 1, i))
            cur = (k, i)
    if cur:
        found.append((cur[0], cur[1] + 1, len(lines)))
    best: dict[str, list[str]] = {}
    for kind, a, b in found:
        body = [x for x in lines[a:b] if x.strip()]
        if len(body) > len(best.get(kind, [])):
            best[kind] = body
    return best


def domains_in(lines: list[str]) -> list[str]:
    """줄마다 처음 보이는 도메인, 바로 앞과 같은 도메인은 한 결과로 친다."""
    out: list[str] = []
    for line in lines:
        m = DOMAIN_RE.search(line)
        if not m:
            continue
        d = m.group(1).lower()
        d = re.sub(r"^(www|m)\.", "", d)
        if out and out[-1] == d:
            continue
        out.append(d)
    return out


def same_site(d: str, site: str) -> bool:
    return d == site or d.endswith("." + site)


def rank_of(doms: list[str], site: str) -> int | None:
    for i, d in enumerate(doms, 1):
        if same_site(d, site):
            return i
    return None


def count_ads(sec: list[str]) -> int:
    doms = []
    for d in domains_in(sec):
        if d not in doms:
            doms.append(d)
    if doms:
        return len(doms)
    return sum(1 for x in sec if x.strip() == "광고")


def count_places(sec: list[str]) -> int:
    addr = sum(1 for x in sec if ADDR_RE.match(x.strip()))
    status = sum(1 for x in sec if STATUS_RE.match(x.strip()))
    review = sum(1 for x in sec if re.match(r"^(방문자\s?)?리뷰\s*[\d,]+", x.strip()))
    return addr or status or review


def questions(sec: list[str] | None, lines: list[str]) -> tuple[list[str], str]:
    def pick(src: list[str], need_word: bool) -> list[str]:
        out: list[str] = []
        for x in src:
            s = x.strip()
            if 8 <= len(s) <= 80 and QUESTION_RE.search(s) and (not need_word or "폐차" in s):
                if s not in out:
                    out.append(s)
        return out

    if sec:
        got = pick(sec, False)
        if got:
            return got, "관련질문 칸"
    return pick(lines, True), "칸 제목 못 찾음 → '폐차' 든 물음 줄 전부"


def blog_info(sec: list[str]) -> tuple[int, int | None]:
    dates = [i for i, x in enumerate(sec) if DATE_RE.match(x.strip())]
    ours = next((i for i, x in enumerate(sec) if any(k in x for k in OUR_BLOG)), None)
    if not dates:
        return 0, (1 if ours is not None else None)
    rank = None
    if ours is not None:
        after = [n for n, i in enumerate(dates, 1) if i >= ours]
        rank = after[0] if after else len(dates)
    return len(dates), rank


def has_daangn(text: str, secs: dict[str, list[str]]) -> bool:
    if "daangn" in text.lower() or secs.get("daangn"):
        return True
    return bool(re.search(r"당근.{0,12}(프로필|비즈|업체)", text))


def analyze(text: str, rivals: list[str]) -> dict:
    lines = [x.rstrip() for x in text.splitlines()]
    secs = split_sections(lines)
    web = domains_in(secs.get("web", []))
    web = [d for d in web if not same_site(d, "naver.com")]
    qs, q_src = questions(secs.get("questions"), lines)
    blog_n, blog_rank = blog_info(secs.get("blog", []))
    known = [OUR_DOMAIN, KADRA, *rivals]
    others: list[str] = []
    for d in web:
        if not any(same_site(d, k) for k in known) and d not in others:
            others.append(d)
    return {
        "sections": {k: len(v) for k, v in secs.items()},
        "ads": count_ads(secs.get("ads", [])) if "ads" in secs else 0,
        "places": count_places(secs.get("place", [])) if "place" in secs else 0,
        "questions": qs,
        "questions_from": q_src,
        "blog_count": blog_n,
        "blog_rank": blog_rank,
        "web_order": web,
        "web_rank": {
            OUR_DOMAIN: rank_of(web, OUR_DOMAIN),
            **{r: rank_of(web, r) for r in rivals},
            KADRA: rank_of(web, KADRA),
        },
        "web_others": others,
        "daangn": has_daangn(text, secs),
    }


# ---------- 지역 ----------

def region_of(query: str) -> str:
    q = re.sub(r"(폐차장|폐차|비교|수출|업체)", " ", query)
    return re.sub(r"\s+", " ", q).strip()


def gu_pages(region: str) -> list[str]:
    """'목포' → ['목포시-폐차장.html'] 처럼 그 지역 구·시군 페이지 파일 이름(있는 것만)."""
    if not region:
        return []
    try:
        gu = json.loads((ROOT / "data" / "gu.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    key = region.replace(" ", "")
    out = []
    for x in gu:
        sg = x.get("sigungu", "") or "세종"
        compact = sg.replace(" ", "")
        city = sg.split()[0] if sg else "세종"
        if compact == key or compact.startswith(key) or re.sub(r"(시|군|구)$", "", city) == key:
            f = (sg.replace(" ", "-") if x.get("sigungu") else "세종") + "-폐차장.html"
            if (ROOT / "gu" / f).exists() and f not in out:
                out.append(f)
    return out


def template(q: str, region: str) -> str:
    t = q
    for name in sorted({region, region.replace(" ", ""), *region.split()}, key=len, reverse=True):
        if len(name) >= 2:
            t = re.sub(re.escape(name) + r"(시|군|구)?", "{지역}", t)
    return t


# ---------- 기록 ----------

SECTION_TITLE = "## 0) 표본 붙여넣기 (네이버 통합검색 화면 글자, `scripts/naver_paste.py`)"
SECTION_NOTE = (
    "병한님이 코드 탭에 \"표본 붙여넣기: {검색어}\" + Ctrl+V 로 붙인 화면을 스크립트가 센 것입니다(PC·휴대폰 화면 그대로, "
    "로그인 여부는 메모에). 원문은 `docs/naver-paste/{날짜}/{검색어}.txt`, 관련질문 문장은 `data/naver_related_questions.json`. "
    "칸 나누기는 어림이라 이상하면 `--debug` 로 확인합니다. 지인 도메인은 내부 기록용입니다."
)


def table_head(rivals: list[str]) -> list[str]:
    cols = ["검색어", "파워링크", "플레이스", "관련질문", "블로그 글 수", "우리 블로그", "웹 우리", *[f"웹 {r.split('.')[0]}" for r in rivals], "웹 kadra", "웹 그 외(순서대로)", "당근"]
    return ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]


def table_row(query: str, r: dict, rivals: list[str]) -> str:
    def rk(v):
        return f"{v}번째" if v else "없음"

    qs = " / ".join(r["questions"]) if r["questions"] else "없음"
    qs = qs.replace("|", "／")
    others = ", ".join(r["web_others"][:8]) or "-"
    cells = [
        query,
        str(r["ads"]),
        str(r["places"]),
        f"{len(r['questions'])}개: {qs}",
        str(r["blog_count"]),
        rk(r["blog_rank"]),
        rk(r["web_rank"][OUR_DOMAIN]),
        *[rk(r["web_rank"][x]) for x in rivals],
        rk(r["web_rank"][KADRA]),
        others,
        "있음" if r["daangn"] else "없음",
    ]
    return "| " + " | ".join(cells) + " |"


def record_md(day: str, query: str, row: str, rivals: list[str]) -> None:
    text = LOG_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    if SECTION_TITLE not in lines:
        at = next((i for i, x in enumerate(lines) if x.startswith("## ")), len(lines))
        lines[at:at] = [SECTION_TITLE, "", SECTION_NOTE, ""]
    s = lines.index(SECTION_TITLE)
    e = next((i for i in range(s + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    head = f"### {day}"
    if head not in lines[s:e]:
        first_day = next((i for i in range(s + 1, e) if lines[i].startswith("### ")), e)
        lines[first_day:first_day] = [head, "", *table_head(rivals), ""]
        e += 4 + 2
    h = lines.index(head, s)
    t0 = h + 2  # 표 머리
    t1 = t0 + 2
    while t1 < len(lines) and lines[t1].startswith("| "):
        t1 += 1
    rows = [x for x in lines[t0 + 2:t1] if not x.startswith(f"| {query} |")]
    rows.append(row)
    lines[t0 + 2:t1] = rows
    LOG_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def record_json(day: str, query: str, region: str, pages: list[str], qs: list[str]) -> None:
    data = {"updated": "", "items": []}
    if QUESTIONS_JSON.exists():
        data = json.loads(QUESTIONS_JSON.read_text(encoding="utf-8"))
    items = [x for x in data.get("items", []) if not (x["date"] == day and x["query"] == query)]
    for q in qs:
        items.append({"date": day, "query": query, "region": region, "gu_pages": pages, "question": q, "template": template(q, region)})
    items.sort(key=lambda x: (x["date"], x["query"]))
    data = {
        "updated": datetime.now(KST).strftime("%Y-%m-%dT%H:%M+09:00"),
        "source": "병한님이 붙인 네이버 통합검색 화면의 관련질문 칸, scripts/naver_paste.py (손으로 고치지 않음)",
        "items": items,
    }
    QUESTIONS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def push(paths: list[Path], query: str, day: str) -> None:
    rel = [str(p.relative_to(ROOT)) for p in paths]
    subprocess.run(["git", "add", "--", *rel], cwd=ROOT, check=True)
    msg = f"Naver paste sample: {query} ({day})\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    subprocess.run(["git", "commit", "-q", "-m", msg, "--", *rel], cwd=ROOT, check=True)
    subprocess.run(["git", "pull", "-q", "--rebase"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-q"], cwd=ROOT, check=True)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="네이버 통합검색 화면 붙여넣기 분석")
    ap.add_argument("query", help='검색어, 예: "목포 폐차장"')
    ap.add_argument("--date", default=today())
    ap.add_argument("--file", help="붙인 글자가 든 파일(없으면 표준 입력 → 그래도 없으면 저장된 txt)")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--no-record", action="store_true")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    query = re.sub(r"\s+", " ", a.query).strip()
    safe = re.sub(r'[\\/:*?"<>|]', "", query)
    out = PASTE_DIR / a.date / f"{safe}.txt"
    text = None
    if a.file:
        text = Path(a.file).read_text(encoding="utf-8-sig")
    elif not sys.stdin.isatty():
        data = sys.stdin.buffer.read()
        if data.strip():
            text = data.decode("utf-8-sig", errors="replace")
    if text is None:
        if not out.exists():
            sys.exit(f"붙인 글자가 없음: {out} 도 없고 --file·표준 입력도 비었음")
        text = out.read_text(encoding="utf-8-sig")
    text = PHONE_RE.sub("***-****-****", text.replace("\r\n", "\n"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    cfg = json.loads((ROOT / "data" / "site_config.json").read_text(encoding="utf-8"))
    rivals = list(cfg.get("rival_domains", []))
    r = analyze(text, rivals)
    region = region_of(query)
    pages = gu_pages(region)

    if a.debug:
        print("칸(줄 수):", json.dumps(r["sections"], ensure_ascii=False))
        print("웹사이트 칸 도메인 순서:", ", ".join(r["web_order"]) or "-")
        print("관련질문 출처:", r["questions_from"])
    row = table_row(query, r, rivals)
    print("\n".join(table_head(rivals)))
    print(row)
    print(f"\n지역: {region or '-'} → 구 페이지: {', '.join(pages) or '없음'}")
    if not r["questions"]:
        print("관련질문: 못 찾음 (화면에 없었거나 칸 제목 모양이 다름 → --debug)")
    if not r["sections"]:
        print("⚠ 칸 제목을 하나도 못 찾음. 화면 글자가 맞는지, --debug 로 확인")
    print(f"원문 저장: {out.relative_to(ROOT)}")

    if a.no_record:
        return
    record_md(a.date, query, row, rivals)
    record_json(a.date, query, region, pages, r["questions"])
    print(f"기록: {LOG_MD.relative_to(ROOT)} · {QUESTIONS_JSON.relative_to(ROOT)}")
    if a.push:
        push([out, LOG_MD, QUESTIONS_JSON], query, a.date)
        print("main 에 올림")


if __name__ == "__main__":
    main()
