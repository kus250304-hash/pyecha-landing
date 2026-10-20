"""
사이트맵 만들기(2026-10-20 병한님 결정: 인덱스 방식 + 정직한 lastmod).

  sitemap.xml          사이트맵 인덱스(sitemapindex). robots.txt 의 Sitemap 줄은 이것 하나
  sitemap-core.xml     첫 화면 + 구·시군(/gu/) + 시·도(/si/) + 안내·주제(/guide/)
  sitemap-cases.xml    사례(/cases/)
  sitemap-dong-N.xml   동 페이지(/pages/)를 법정동코드(시·도 코드) 순으로 나눔. 파일 수 = max(2, ⌈개수/500⌉),
                       고르게 나눠 파일당 500개 안팎(1,000개를 넘으면 -3 이 저절로 생김, 남는 옛 파일은 지움)

넣지 않는 것: 자동 이동 페이지(옛 영문 주소, http-equiv="refresh"), noindex 페이지(thanks·privacy 등).

lastmod: 페이지 본문(제목·H1·본문 글·FAQ·사례 카드·공공정보 표)의 해시(content_hash)를 data/page_hashes.json 에
페이지마다 저장해 두고, 해시가 바뀐 날만 오늘로 바꾼다. 머리글(header)·길 안내·맨 아래 지역 링크(nav)·바닥글·
스크립트·CSS·메타 태그·"최종 업데이트" 날짜·모든 페이지 공통 "이런 차도 됩니다" 링크 묶음은 해시에 넣지 않으므로 공통 틀만 바뀐 빌드에서는 날짜가 그대로다.
조사 교정 같은 오타 수준 수정은 build_site.py --keep-dates 로 돌리면 해시만 새로 적고 날짜는 둔다.
처음 한 번(해시 기록이 없을 때)은 지금 사이트맵에 적힌 날짜를 그대로 쓴다. 동·구·시·안내 페이지의
"최종 업데이트"·dateModified 도 같은 content_hash 로 정한다(build_site.with_updated_date).

  python3 scripts/sitemap_lib.py                # 사이트맵 다시 만들기(빌드 스크립트가 매번 부름)
  python3 scripts/sitemap_lib.py check --live   # 사이트맵의 모든 주소가 실제로 200 인지 사이트에 물어봄(느림)
"""
import hashlib
import html as htmllib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
# 사이트 주소는 data/site_config.json 의 site_base_url 한 곳에서만 관리한다
SITE_BASE_URL = json.loads((ROOT / "data" / "site_config.json").read_text(encoding="utf-8"))["site_base_url"].rstrip("/")
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
HASHES = ROOT / "data" / "page_hashes.json"
INDEX_NAME = "sitemap.xml"
CORE_DIRS = ("gu", "si", "guide")
DONG_PER_FILE = 500
KST = timezone(timedelta(hours=9))

REDIRECT_RE = re.compile(r'http-equiv="refresh"', re.I)
NOINDEX_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*noindex', re.I)
CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]+)"')
MODIFIED_RE = re.compile(r'"dateModified": "(\d{4}-\d{2}-\d{2})"')
LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>(?:\s*<lastmod>\s*(.*?)\s*</lastmod>)?", re.S)
# 해시에서 빼는 것: 공통 틀(머리글·길 안내·지역 링크·바닥글·하단 고정 바)과 화면에 안 보이는 것
STRIP_TAGS = ("script", "style", "noscript", "template", "svg", "header", "nav", "footer", "form")
UPDATED_P_RE = re.compile(r'<p class="updated">.*?</p>', re.S)  # "최종 업데이트: …"(빌드 중에는 @@UPDATED_ON@@ 자리표)
# 모든 동·구·시 페이지에 똑같이 들어가는 "이런 차도 됩니다" 링크 묶음(build_guide.guide_links_html)도 공통 틀로 본다(2026-10-20)
TYPE_LINKS_RE = re.compile(r'<div class="type-links">.*?<p class="type-more">.*?</p></div>', re.S)


def today() -> str:
    return datetime.now(KST).date().isoformat()


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def content_text(page_html: str) -> str:
    """lastmod 를 정하는 본문 글: 제목 + H1 + 본문(공통 틀·스크립트·날짜 줄을 뺀 보이는 글)."""
    title = re.search(r"<title>(.*?)</title>", page_html, re.S)
    body = TYPE_LINKS_RE.sub(" ", UPDATED_P_RE.sub(" ", page_html.split("<body", 1)[-1]))
    h1 = " ".join(_text(x) for x in re.findall(r"<h1\b[^>]*>(.*?)</h1>", body, re.S))
    for tag in STRIP_TAGS:
        body = re.sub(rf"<{tag}\b.*?</{tag}>", " ", body, flags=re.S | re.I)
    return "\n".join([_text(title.group(1)) if title else "", h1, _text(body)])


def content_hash(page_html: str) -> str:
    return hashlib.sha256(content_text(page_html).encode("utf-8")).hexdigest()[:20]


def listed_pages(root: Path = ROOT) -> list[tuple[str, str, str]]:
    """사이트맵에 넣을 페이지 [(종류, 저장소 안 경로, 주소)]. 종류는 core·cases·dong."""
    out = []
    files = [("core", root / "index.html")]
    for d in CORE_DIRS:
        files += [("core", p) for p in sorted((root / d).glob("*.html"))]
    files += [("cases", p) for p in sorted((root / "cases").glob("*.html"))]
    files += [("dong", p) for p in sorted((root / "pages").glob("*.html"))]
    for kind, p in files:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if REDIRECT_RE.search(text) or NOINDEX_RE.search(text):
            continue
        rel = p.relative_to(root).as_posix()
        loc = f"{SITE_BASE_URL}/" if rel == "index.html" else f"{SITE_BASE_URL}/{quote(rel)}"
        out.append((kind, rel, loc))
    return out


def sitemap_files(root: Path = ROOT) -> list[Path]:
    """인덱스에 적힌 사이트맵 파일들(인덱스 자신은 빼고). 인덱스가 아직 옛 urlset 이면 [sitemap.xml]."""
    index = root / INDEX_NAME
    if not index.exists():
        return []
    text = index.read_text(encoding="utf-8")
    if "<sitemapindex" not in text:
        return [index]
    return [root / unquote(u[len(SITE_BASE_URL) + 1:]) for u, _ in LOC_RE.findall(text)]


def all_entries(root: Path = ROOT) -> dict[str, str]:
    """사이트맵 전체의 {주소: lastmod}."""
    out: dict[str, str] = {}
    for f in sitemap_files(root):
        if f.exists():
            out.update({u: lm for u, lm in LOC_RE.findall(f.read_text(encoding="utf-8"))})
    return out


def all_locs(root: Path = ROOT) -> list[str]:
    return list(all_entries(root))


def all_text(root: Path = ROOT) -> str:
    """검사용: 사이트맵 파일 전부를 이어 붙인 글."""
    return "\n".join(f.read_text(encoding="utf-8") for f in [root / INDEX_NAME] + sitemap_files(root) if f.exists())


def _urlset(rows: list[tuple[str, str]]) -> str:
    body = "".join(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{lm}</lastmod>\n  </url>\n" for u, lm in rows)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{NS}">\n{body}</urlset>\n'


def dong_order(root: Path = ROOT) -> dict[str, str]:
    """동 페이지 파일 이름(slug) → 법정동코드(시·도 코드가 앞 2자리). 코드가 없으면 맨 뒤."""
    regions = json.loads((root / "data" / "regions.json").read_text(encoding="utf-8"))
    return {r["slug"]: r.get("code") or "9" * 10 for r in regions}


def write_sitemaps(root: Path = ROOT, keep_dates: bool = False) -> dict[str, int]:
    """사이트맵 인덱스와 나눈 파일들을 다시 만든다. 돌려주는 값: {파일 이름: 주소 수}."""
    old = all_entries(root)
    store = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    new_store: dict[str, dict] = {}
    day = today()
    groups: dict[str, list[tuple[str, str, str]]] = {"core": [], "cases": [], "dong": []}  # (정렬 키, 주소, lastmod)
    codes = dong_order(root)
    for kind, rel, loc in listed_pages(root):
        text = (root / rel).read_text(encoding="utf-8")
        h = content_hash(text)
        prev = store.get(rel)
        if prev is None:  # 처음 보는 페이지: 지금 사이트맵의 날짜 → 페이지의 dateModified → 오늘
            m = MODIFIED_RE.search(text)
            lastmod = old.get(loc) or (m.group(1) if m else day)
        elif prev["hash"] != h and not keep_dates:
            lastmod = day
        else:
            lastmod = prev["lastmod"]
        new_store[rel] = {"hash": h, "lastmod": lastmod}
        key = codes.get(Path(rel).stem, "9" * 10) + rel if kind == "dong" else ("" if rel == "index.html" else rel)
        groups[kind].append((key, loc, lastmod))

    dongs = sorted(groups["dong"])
    n_files = max(2, math.ceil(len(dongs) / DONG_PER_FILE))
    size = math.ceil(len(dongs) / n_files) if dongs else 0
    files: dict[str, list[tuple[str, str, str]]] = {"sitemap-core.xml": sorted(groups["core"]),
                                                    "sitemap-cases.xml": sorted(groups["cases"])}
    for i in range(n_files):
        files[f"sitemap-dong-{i + 1}.xml"] = dongs[i * size:(i + 1) * size]
    for stale in root.glob("sitemap-dong-*.xml"):
        if stale.name not in files:
            stale.unlink()

    index_rows = []
    for name, rows in files.items():
        (root / name).write_text(_urlset([(u, lm) for _, u, lm in rows]), encoding="utf-8")
        index_rows.append((f"{SITE_BASE_URL}/{name}", max((lm for *_, lm in rows), default=day)))
    body = "".join(f"  <sitemap>\n    <loc>{u}</loc>\n    <lastmod>{lm}</lastmod>\n  </sitemap>\n" for u, lm in index_rows)
    (root / INDEX_NAME).write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="{NS}">\n{body}</sitemapindex>\n',
                                   encoding="utf-8")
    if new_store != store:
        HASHES.write_text(json.dumps(dict(sorted(new_store.items())), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    return {name: len(rows) for name, rows in files.items()}


def update_sitemap(root_dir: Path, slugs: list[str] | None = None, changefreq: str = "", priority: str = "",
                   paths: list[str] | None = None, drop: list[str] | None = None, keep_dates: bool = False) -> Path:
    """예전 호출 모양 그대로 둔 입구. 무엇이 바뀌었는지와 상관없이 사이트맵 전체를 다시 만든다(write_sitemaps)."""
    write_sitemaps(root_dir, keep_dates=keep_dates)
    return root_dir / INDEX_NAME


def check(root: Path = ROOT) -> list[str]:
    """사이트맵 검사(check_pages.py 가 부름): 인덱스·파일, 주소 수 = 실제 페이지 수, 주소 = 그 페이지 canonical,
    중복·자동 이동·noindex 없음, lastmod = 해시 기록 = 페이지 dateModified(있을 때), robots.txt 는 인덱스 한 줄."""
    problems = []
    index = root / INDEX_NAME
    if not index.exists() or "<sitemapindex" not in index.read_text(encoding="utf-8"):
        return ["sitemap.xml: 사이트맵 인덱스(sitemapindex)가 아님 (python3 scripts/sitemap_lib.py)"]
    files = sitemap_files(root)
    names = [f.name for f in files]
    for need in ("sitemap-core.xml", "sitemap-cases.xml", "sitemap-dong-1.xml", "sitemap-dong-2.xml"):
        if need not in names:
            problems.append(f"sitemap.xml: {need} 가 인덱스에 없음")
    locs: list[str] = []
    lastmods: dict[str, str] = {}
    for f in files:
        if not f.exists():
            problems.append(f"sitemap.xml: 인덱스에 적힌 {f.name} 파일이 없음")
            continue
        rows = LOC_RE.findall(f.read_text(encoding="utf-8"))
        if f.name.startswith("sitemap-dong-") and len(rows) > 50000:
            problems.append(f"{f.name}: 주소가 50,000개를 넘음")
        for u, lm in rows:
            locs.append(u)
            lastmods[u] = lm
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm or ""):
                problems.append(f"{f.name}: {u} 의 lastmod 가 날짜 꼴이 아님({lm})")
    dup = {u for u in locs if locs.count(u) > 1} if len(locs) != len(set(locs)) else set()
    for u in sorted(dup):
        problems.append(f"사이트맵: {unquote(u)} 가 두 번 이상 들어 있음")
    pages = listed_pages(root)
    want = {loc: rel for _, rel, loc in pages}
    if len(set(locs)) != len(want):
        problems.append(f"사이트맵 주소 수 {len(set(locs))}개 ≠ 실제 페이지 수 {len(want)}개")
    for u in sorted(set(want) - set(locs)):
        problems.append(f"사이트맵에 빠진 페이지: {want[u]}")
    for u in sorted(set(locs) - set(want)):
        problems.append(f"사이트맵에 있으나 넣으면 안 되는 주소(파일 없음·자동 이동·noindex): {unquote(u)}")
    store = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    for loc, rel in want.items():
        text = (root / rel).read_text(encoding="utf-8")
        canon = CANONICAL_RE.search(text)
        if not canon or canon.group(1) != loc:
            problems.append(f"{rel}: canonical({canon.group(1) if canon else '없음'})이 사이트맵 주소({loc})와 다름")
        if loc not in lastmods:
            continue
        rec = store.get(rel)
        if not rec or rec.get("lastmod") != lastmods[loc] or rec.get("hash") != content_hash(text):
            problems.append(f"{rel}: data/page_hashes.json 기록과 사이트맵이 맞지 않음 (python3 scripts/sitemap_lib.py)")
        m = MODIFIED_RE.search(text)
        if m and m.group(1) != lastmods[loc]:
            problems.append(f"{rel}: 사이트맵 lastmod {lastmods[loc]} ≠ 페이지 dateModified {m.group(1)}")
    robots = (root / "robots.txt").read_text(encoding="utf-8") if (root / "robots.txt").exists() else ""
    lines = [x.split(":", 1)[1].strip() for x in robots.splitlines() if x.lower().startswith("sitemap:")]
    if lines != [f"{SITE_BASE_URL}/{INDEX_NAME}"]:
        problems.append(f"robots.txt: Sitemap 줄은 {SITE_BASE_URL}/{INDEX_NAME} 하나만 있어야 함 (지금 {lines})")
    return problems


def check_live(root: Path = ROOT) -> list[str]:
    """사이트맵의 모든 주소(와 사이트맵 파일)가 실제 사이트에서 200 으로 열리는지(따라가지 않고, 이동 응답도 실패)."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)

    def status(u: str) -> tuple[str, int | str]:
        for _ in range(3):
            try:
                req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "pyecha-sitemap-check"})
                return u, opener.open(req, timeout=30).status
            except urllib.error.HTTPError as e:
                return u, e.code
            except Exception as e:  # 잠깐 끊김은 다시
                err = str(e)
        return u, err
    urls = [f"{SITE_BASE_URL}/{INDEX_NAME}"] + [f"{SITE_BASE_URL}/{f.name}" for f in sitemap_files(root)] + all_locs(root)
    with ThreadPoolExecutor(8) as ex:
        bad = [(u, s) for u, s in ex.map(status, urls) if s != 200]
    print(f"실제 사이트 확인: {len(urls)}개 중 200 아닌 것 {len(bad)}개")
    return [f"{unquote(u)}: {s}" for u, s in bad]


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        problems = check() + (check_live() if "--live" in sys.argv else [])
        for p in problems:
            print("오류:", p)
        print(f"사이트맵 검사: 오류 {len(problems)}건")
        sys.exit(1 if problems else 0)
    counts = write_sitemaps(keep_dates="--keep-dates" in sys.argv)
    for name, n in counts.items():
        print(f"{name}: {n}개")
    print(f"합계 {sum(counts.values())}개, 인덱스 {INDEX_NAME}")


if __name__ == "__main__":
    main()
