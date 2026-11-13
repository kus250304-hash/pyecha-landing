"""
네이버 수집 요청 후보를 고른다. 2026-11-11 병한님 결정(docs/current-rules.md)부터 아침 색인(구글 15·네이버 50)은 하지 않고,
일요일 저녁 발행판에서 병한님이 네이버 수집 요청 10개까지만 넣는다. 매일 루틴이 커밋 전에 --write 로 돌려 그 후보를
docs/index-requests.md 에 "## 날짜 네이버" 칸으로 쌓아 두고, 일요일 발행판(업무위키 _도구/주간꾸러미.py)이 최근 7일 줄을 읽는다.
구글 목록은 만들지 않는다. 네이버·공용 IndexNow 자동 전송(scripts/indexnow.py)과는 따로다.

사용법
  python3 scripts/pick_index_requests.py           # 고르기만(파일 그대로)
  python3 scripts/pick_index_requests.py --write   # 고른 주소를 docs/index-requests.md 에 "## 날짜 네이버" 칸으로 덧붙임(0개면 칸 없음)

네이버 후보(하루 10개까지, 사이트맵에 있는 페이지만 = noindex·자동 이동 빼기)
  (가) 어제·오늘 사례가 새로 붙은 구·시군 페이지(cases/index.json 의 added)   이유 "바뀜: YYYY-MM-DD 사례가 새로 붙음(시군구)"
  (나) data/ga4_daily.json 최근 7일 pages 에 quote_submit·call_click·sms_click 1 이상   이유 "반응: 최근 7일 …"
  (다) 어제·오늘 본문 해시가 바뀐 구·시·주제·사례 페이지(data/page_hashes.json lastmod)   이유 "바뀜: YYYY-MM-DD 본문 바뀜(…)"
  이 순서로 10개까지. 같은 주소는 7일 안에 다시 넣지 않는다(네이버 칸 기록 기준).
  "요청 못 함" 다시 넣기와 동 페이지로 채우기는 2026-11-11부터 끔(Picker.requeue·dong_order 는 남겨 둠).
  글자 꼴은 바꾸지 않는다(주간꾸러미.py 가 읽음): 칸 제목 "## YYYY-MM-DD 네이버", 줄 "- 주소 — 파일 (이유)",
  이유 속 "YYYY-MM-DD 사례가 새로 붙음"·"YYYY-MM-DD 본문 바뀜"·"내용 바뀜(YYYY-MM-DD)".

기록(docs/index-requests.md 날짜 칸, 2026-10-29)
  제목이 "날짜 구글" / "날짜 네이버" / "날짜 구글·네이버 …"이면 그곳에 넣은 것. 표시가 없는 옛 칸은 2026-10-22부터 둘 다,
  그 전은 구글만. 제목에 "요청 못 함"이 있는 칸은 그곳에 요청 안 한 것. 주소는 %인코딩한 전체 주소.

옛(2026-10-29~11-10, 아침 색인): 구글 15개(⓪ 요청 못 함 → ⓐ 사례 붙은 구 → ① 최우선 → ② 문의 온 시·군 → ②-0 빈 땅 →
  ②-1 지인 공략 → ④ 점수표 지방 시·군, 색인됨 빼기) + 네이버 50개(⓪ 요청 못 함 → ① 바뀐·반응 최대 25 → ② 동 페이지 →
  ③ 안 넣은 구·시·주제·사례). 자세한 옛 규칙은 git 기록(2026-11-12 이전 이 파일)에 있다.
"""
import argparse
from collections import Counter
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_gu import min_dong_pages  # noqa: E402
from build_site import CONFIG, GU_DATA, REGIONS, gu_file, load_json  # noqa: E402

LOG = ROOT / "docs" / "index-requests.md"
COUNT_NAVER = 10  # 2026-11-11 병한님: 일요일 발행판용 후보 하루 10개까지(옛: 2026-10-29 50개, 구글 15개는 없앰)
GSC_STATUS = ROOT / "data" / "gsc_index_status.json"  # 구글 색인 상태(2026-10-30, scripts/gsc_index_check.py)
GSC_MAX_AGE = 3  # 마지막 확인이 이 날수보다 오래면 거르지 않음
NAVER_AGAIN_DAYS = 7  # 네이버: 같은 주소는 7일 안에 다시 넣지 않음(2026-11-05)
NAVER_CHANGED_MAX = 25  # 네이버 ① 바뀐·반응 온 페이지 최대 개수(2026-11-05)
FULL_REBUILD = 300  # 어제·오늘 바뀐 페이지가 이보다 많으면 전체 재빌드 다음 날로 봄
KIND_ORDER = {"gu": 0, "si": 1, "guide": 2, "cases": 3, "pages": 4}
GA4 = ROOT / "data" / "ga4_daily.json"
NAVER_SINCE = "2026-10-22"  # 이날부터 날짜 칸 주소를 네이버 웹 페이지 수집에도 넣음(그 전 칸은 구글만)
PUBLISHED_RE = re.compile(r'"datePublished": "(\d{4}-\d{2}-\d{2})"')
URL_RE = re.compile(r"https://pyecha119\.com/\S+?\.html")


def today() -> str:
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


DATE_HEAD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
NOT_DONE = "요청 못 함"  # 날짜 칸 제목에 이 말이 있으면 그 칸 주소는 요청 안 한 것(2026-10-19)
ENGINE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\s+(구글·네이버|구글|네이버)")  # 날짜 칸 제목의 곳 표시(2026-10-29)


def sections(text: str) -> list[tuple[str, str]]:
    """"## 제목" 칸들 [(제목, 본문)]."""
    return [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1] if "\n" in p else "") for p in text.split("\n## ")[1:]]


def inquiry_places(inquiry: str, base: str, regions: list[dict], gu_data: list[dict]) -> list[tuple[str, str]]:
    """"문의가 온 페이지" 칸 본문의 주소들 → [(시도, 시군구)] (적힌 순서, 겹치면 한 번)."""
    by_file = {gu_file(g["sido"], g["sigungu"]): (g["sido"], g["sigungu"]) for g in gu_data}
    by_slug = {r["slug"]: (r["sido"], r["sigungu"]) for r in regions}
    out: list[tuple[str, str]] = []
    for u in URL_RE.findall(inquiry):
        path = unquote(u[len(base) + 1:])
        key = by_file.get(path[3:]) if path.startswith("gu/") else by_slug.get(path[6:-5]) if path.startswith("pages/") else None
        if key and key not in out:
            out.append(key)
    return out


def inquiry_group(key: tuple[str, str], keys) -> list[tuple[str, str]]:
    """문의 온 시군구와 같은 시·군(일반구면 같은 시의 다른 구까지)에 드는 keys, 문의 온 곳 먼저."""
    sido, sigungu = key
    city = sigungu.split()[0] if " " in sigungu else sigungu
    group = sorted(k for k in keys if k != key and k[0] == sido and " " in sigungu and k[1].startswith(city + " "))
    return ([key] if key in keys else []) + group


def popular_gu(limit: int = 10) -> list[tuple[str, str]]:
    """첫 화면·주제 페이지 "문의 많은 지역"(2026-10-20): 문의가 온 페이지의 구·시군 페이지(적힌 순서) →
    점수표(data/priority_regions.json) 상위 지방 시·군(build_gu.min_dong_pages 가 0)의 구 페이지. 구 페이지 파일이 있는 곳만, limit 개.
    빌드할 때마다 다시 고르므로 문의가 더해지거나 구 페이지가 생기면 저절로 바뀐다."""
    base = load_json(CONFIG)["site_base_url"].rstrip("/")
    gu_data = load_json(GU_DATA, default=[])
    have = {(g["sido"], g["sigungu"]) for g in gu_data if (ROOT / "gu" / gu_file(g["sido"], g["sigungu"])).exists()}
    out = [k for k in inquiry_places(inquiry_text(), base, load_json(REGIONS), gu_data) if k in have]
    for e in load_json(ROOT / "data" / "priority_regions.json", default={}).get("gu", []):
        k = (e["sido"], e["sigungu"])
        if k in have and k not in out and min_dong_pages(*k) == 0:
            out.append(k)
    return out[:limit]


def inquiry_text() -> str:
    text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    return next((body for head, body in sections(text) if head.startswith("문의가 온 페이지")), "")


def new_cases(since: str, until: str) -> list[tuple[dict, str]]:
    """since~until(YYYY-MM-DD) 에 페이지에 붙은 사례 [(사례, 붙은 날)], 최근 것 먼저. 붙은 날은 cases/index.json 의 added,
    없으면(2026-10-28 전에 만든 사례) git 에 cases/<slug>.html 이 처음 들어간 날(한국 시간). git 이 안 되면 added 있는 것만."""
    index = load_json(ROOT / "cases" / "index.json", default=[])
    first: dict[str, str] = {}
    if any(not c.get("added") for c in index):
        try:
            out = subprocess.run(["git", "-c", "core.quotepath=off", "log", "--diff-filter=A", "--name-only", "--format=@%aI",
                                  f"--since={since}T00:00:00+09:00", "--", "cases/*.html"],
                                 cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
        except OSError:
            out = ""
        d = ""
        for line in out.splitlines():  # 최근 커밋부터 나오므로 마지막 값 = 처음 들어간 날
            if line.startswith("@"):
                d = datetime.fromisoformat(line[1:]).astimezone(timezone(timedelta(hours=9))).date().isoformat()
            elif line.startswith("cases/") and line.endswith(".html"):
                first[line[6:-5]] = d
    out_cases = []
    for c in index:
        added = c.get("added") or first.get(c["slug"], "")
        if since <= added <= until:
            out_cases.append((c, added))
    return sorted(out_cases, key=lambda x: x[1], reverse=True)


class Picker:
    """한 곳(구글·네이버)의 요청 기록과 고른 주소. 기록에 있는 주소는 again=True 일 때만 다시 고른다."""

    def __init__(self, secs: list[tuple[str, str]], engine: str, allow) -> None:
        self.engine, self.allow = engine, allow
        self.done: set[str] = set()
        self.last_req: dict[str, str] = {}  # 주소 → 마지막으로 요청한 날
        self.last_pos: dict[str, tuple[str, int]] = {}  # 주소 → (마지막으로 요청한 날, 그 칸의 파일 속 순서)
        for i, (head, body) in enumerate(secs):
            if DATE_HEAD_RE.match(head) and NOT_DONE not in head and engine in engines(head):
                for u in URL_RE.findall(body):
                    self.done.add(u)
                    self.last_req[u] = max(self.last_req.get(u, ""), head[:10])
                    self.last_pos[u] = max(self.last_pos.get(u, ("", -1)), (head[:10], i))
        self.ordered: list[tuple[str, str]] = []
        self._seen: set[str] = set()

    def add(self, url: str, why: str, again: bool = False) -> None:
        if (again or url not in self.done) and url not in self._seen and self.allow(url):
            self.ordered.append((url, why))
            self._seen.add(url)

    def requeue(self, secs: list[tuple[str, str]], day: str) -> None:
        """⓪ "요청 못 함" 칸 주소를 다시(2026-10-29: 바로 앞 날짜만이 아니라 모든 칸, 최근 칸부터. 예전에 요청한 적 있어도
        그 칸 뒤로 요청하지 않았으면 다시 → 하루 개수를 넘어 남은 주소도 다음 날 이어서 나옴).
        "그 칸 뒤" = 더 늦은 날짜 칸, 또는 같은 날이면 파일에서 더 아래에 적힌 칸(2026-10-30: 루틴이 아침에 적은 "날짜 구글" 칸
        주소라도 그 아래 "요청 못 함" 칸에 다시 적혔으면 다시 고름)."""
        failed = [(i, h, b) for i, (h, b) in enumerate(secs)
                  if DATE_HEAD_RE.match(h) and NOT_DONE in h and h[:10] < day and self.engine in engines(h)]
        for i, head, body in sorted(failed, key=lambda x: (x[1][:10], x[0]), reverse=True):
            for u in URL_RE.findall(body):
                if self.last_pos.get(u, ("", -1)) < (head[:10], i):
                    self.add(u, f"{head[:10]} 요청 못 함 → 다시", again=True)

    def not_done_today(self, secs: list[tuple[str, str]], day: str) -> bool:
        return any(h.startswith(day) and NOT_DONE in h and self.engine in engines(h) for h, _ in secs)


def engines(head: str) -> set[str]:
    """날짜 칸 제목 → 그 칸이 기록하는 곳. "2026-10-30 구글" / "2026-10-30 네이버" / "2026-10-29 구글·네이버 …"(2026-10-29부터).
    표시가 없는 옛 칸은 2026-10-22부터 둘 다(같은 주소를 양쪽에 넣었음), 그 전은 구글만."""
    m = ENGINE_RE.match(head)
    if m:
        return {"구글", "네이버"} if "·" in m.group(1) else {m.group(1)}
    return {"구글", "네이버"} if head[:10] >= NAVER_SINCE else {"구글"}


def sitemap_urls(pattern: str) -> list[str]:
    """사이트맵 파일(들)의 .html 주소. 사이트맵에는 noindex·자동 이동 페이지가 없다(scripts/sitemap_lib.py)."""
    out: list[str] = []
    for f in sorted(ROOT.glob(pattern)):
        out += re.findall(r"<loc>([^<]+\.html)</loc>", f.read_text(encoding="utf-8"))
    return out


def inspect_link(base: str, url: str) -> str:
    """구글 서치 콘솔 URL 검사 바로가기(2026-10-29 병한님). 속성은 도메인 속성 sc-domain:pyecha119.com(2026-11-05):
    URL 접두어 속성(https://pyecha119.com/)으로 열면 11/5 아침 병한님 화면에서 "액세스할 수 없음"이 떴고, 색인 확인 API
    (scripts/gsc_index_check.py)가 실제로 쓰는 속성도 sc-domain 이다. data/gsc_index_status.json 의 site 가 있으면 그것을 따른다."""
    site = (load_json(GSC_STATUS, default={}) or {}).get("site") or "sc-domain:" + base.split("//", 1)[-1].strip("/")
    return f"https://search.google.com/search-console/inspect?resource_id={quote(site, safe='')}&id={quote(url, safe='')}"


def dong_order(base: str, regions: list[dict], inquiry: str, gu_data: list[dict], indexable: set[str]) -> list[tuple[str, str]]:
    """네이버 ② 동 페이지 순서(2026-10-29 병한님): 문의 온 시·군(일반구면 같은 시의 모든 구)의 동을 인구 많은 순
    (문의 온 곳이 여럿이면 번갈아) → 점수표(data/priority_regions.json) 순 시·군마다 인구 많은 동 → 나머지.
    인구는 data/population_dong.json(population_stats.py dong 이 저장)에 있는 것만 쓰고, 없는 동은 그 시·군 맨 뒤(법정동코드 순).
    ○가를 묶은 페이지(창인동 = 창인동1가·2가)는 ○가 인구를 합친다."""
    from population_stats import dong_load
    rows = dong_load().get("rows", {})

    def people(r: dict) -> int | None:
        pop = rows.get(f"{r['sido']} {r['sigungu']}".strip(), {})
        if r["dong"] in pop:
            return pop[r["dong"]]
        parts = [n for name, n in pop.items() if re.fullmatch(re.escape(r["dong"]) + r"\d+가", name)]
        return sum(parts) if parts else None

    def ranked(rs: list[dict]) -> list[dict]:
        return sorted(rs, key=lambda r: (people(r) is None, -(people(r) or 0), r.get("code", "")))

    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in regions:
        if f"{base}/pages/{r['slug']}.html" in indexable:
            by_key.setdefault((r["sido"], r["sigungu"]), []).append(r)

    def item(r: dict, why: str) -> tuple[str, str]:
        n = people(r)
        return f"{base}/pages/{r['slug']}.html", f"{why} {r['dong']}" + (f", 인구 {n:,}명" if n else "")

    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    queues: list[list[tuple[str, str]]] = []
    for key in inquiry_places(inquiry, base, regions, gu_data):
        group = [k for k in inquiry_group(key, set(by_key) | {key}) if k not in seen]
        seen |= set(group)
        queues.append([item(r, f"문의 온 시·군({key[1]}) 동") for r in ranked([r for k in group for r in by_key.get(k, [])])])
    while any(queues):
        for q in queues:
            if q:
                out.append(q.pop(0))
    for e in load_json(ROOT / "data" / "priority_regions.json", default={}).get("gu", []):
        k = (e["sido"], e["sigungu"])
        if k not in seen:
            seen.add(k)
            out += [item(r, f"점수표 {e['rank']}위({k[1]}) 동") for r in ranked(by_key.get(k, []))]
    for k in sorted(set(by_key) - seen):
        out += [item(r, f"그 밖의 시·군({k[1]}) 동") for r in ranked(by_key[k])]
    return out


def gsc_indexed(day: str) -> tuple[set[str], str]:
    """구글 목록에서 뺄 "이미 색인됨" 주소(2026-10-30, scripts/gsc_index_check.py 가 PC 에서 매일 쓰는 data/gsc_index_status.json).
    파일이 없거나 마지막 확인이 3일보다 오래면 거르지 않는다(지금처럼 그대로)."""
    data = load_json(GSC_STATUS, default={}) or {}
    updated = data.get("updated", "")
    if not updated:
        return set(), "확인 자료 없음 → 거르지 않음"
    age = (datetime.fromisoformat(day) - datetime.fromisoformat(updated)).days
    if age > GSC_MAX_AGE:
        return set(), f"확인 자료가 {age}일 지남({updated}) → 거르지 않음"
    indexed = {u for u, v in data.get("pages", {}).items() if v.get("indexed")}
    return indexed, f"{updated} 확인 기준 이미 색인된 {len(indexed)}개는 뺌(data/gsc_index_status.json)"


def ga4_reacted(base: str, day: str, days: int = 7) -> list[tuple[str, str]]:
    """data/ga4_daily.json 최근 days 일 pages 에서 quote_submit·call_click·sms_click 이 1 이상인 .html 페이지 주소(많은 순)."""
    data = load_json(GA4, default={}) or {}
    since = (datetime.fromisoformat(day) - timedelta(days=days)).date().isoformat()
    hits: dict[str, dict[str, int]] = {}
    for d, v in (data.get("days") or {}).items():
        if not since <= d <= day:
            continue
        for p in v.get("pages", []):
            page = p.get("page", "")
            if not page.endswith(".html"):
                continue
            h = hits.setdefault(page, {"폼": 0, "전화": 0, "문자": 0})
            h["폼"] += p.get("quote_submit", 0)
            h["전화"] += p.get("call_click", 0)
            h["문자"] += p.get("sms_click", 0)
    out = [(page, h) for page, h in hits.items() if sum(h.values())]
    out.sort(key=lambda x: (-sum(x[1].values()), x[0]))
    return [(f"{base}{quote(page)}", " · ".join(f"{k} {v}" for k, v in h.items() if v)) for page, h in out]


def kind(url: str) -> str:
    return next((name for part, name in (("/gu/", "구·시군"), ("/si/", "시·도"), ("/guide/", "안내"), ("/cases/", "사례"),
                                         ("/pages/", "동")) if part in url), "그 밖")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", help="이 날짜(YYYY-MM-DD)로 고르기(미리 보기용, 기본 오늘 한국 시간)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    base = load_json(CONFIG)["site_base_url"].rstrip("/")
    gu_data = load_json(GU_DATA, default=[])
    text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    secs = sections(text)
    day = args.date or today()

    def gu_url(sido, sigungu):
        return f"{base}/gu/{quote(gu_file(sido, sigungu))}"

    gu_keys = {(g["sido"], g["sigungu"]) for g in gu_data}
    lastmod = {rel: v["lastmod"] for rel, v in load_json(ROOT / "data" / "page_hashes.json", default={}).items()}

    # ── 네이버 후보: 하루 10개까지, 사이트맵에 있는 페이지만(2026-11-11 병한님) ──
    indexable = set(sitemap_urls("sitemap-core.xml")) | set(sitemap_urls("sitemap-cases.xml")) | set(sitemap_urls("sitemap-dong-*.xml"))
    n = Picker(secs, "네이버", lambda u: u in indexable)
    d0 = datetime.fromisoformat(day)
    yday = (d0 - timedelta(days=1)).date().isoformat()

    def add(u: str, why: str) -> None:  # 같은 주소는 7일 안에 다시 넣지 않음
        last = n.last_req.get(u)
        if not last or (d0 - datetime.fromisoformat(last)).days >= NAVER_AGAIN_DAYS:
            n.add(u, why, again=True)

    # (가) 어제·오늘 사례가 새로 붙은 구·시군 페이지
    for c, added in new_cases(yday, day):
        if (c["sido"], c["sigungu"]) in gu_keys:
            add(gu_url(c["sido"], c["sigungu"]), f"바뀜: {added} 사례가 새로 붙음({c['sigungu']})")
    # (나) GA4 최근 7일 폼·전화·문자 반응 온 페이지
    for u, why in ga4_reacted(base, day):
        add(u, f"반응: 최근 7일 {why}")
    # (다) 어제·오늘 본문이 바뀐 구·시·주제·사례 페이지
    changed = sorted((rel for rel, lm in lastmod.items() if yday <= lm <= day and rel.split("/")[0] in ("gu", "si", "guide", "cases")),
                     key=lambda r: (KIND_ORDER.get(r.split("/")[0], 9), r))
    for rel in changed:
        add(f"{base}/{quote(rel)}", f"바뀜: {lastmod[rel]} 본문 바뀜({kind('/' + rel)})")

    picked = n.ordered[:COUNT_NAVER]
    print(f"네이버 후보 {len(picked)}개 — 일요일 저녁 발행판에서 넣을 것(하루 {COUNT_NAVER}개까지, {day}, "
          f"고를 수 있던 것 {len(n.ordered)}개, 7일 안에 넣은 주소는 뺌). 2026-11-11부터 아침 색인·구글 목록 없음")
    if picked:
        print("네이버 이유: " + " · ".join(f"{w} {c}" for w, c in Counter(why.split(":")[0] for _, why in picked).items()))
        for i, (u, why) in enumerate(picked, 1):
            print(f"{i}. {unquote(u)} — {why}")
    if args.write:
        if not picked:
            print("docs/index-requests.md: 후보 0개라 칸을 만들지 않음")
            return
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n## {day} 네이버\n\n" + "".join(f"- {u} — {unquote(u[len(base) + 1:])} ({why})\n" for u, why in picked)
        LOG.write_text(text, encoding="utf-8")
        print(f"docs/index-requests.md 에 네이버 {len(picked)}개 덧붙임")


if __name__ == "__main__":
    main()
