"""
사이트 전체 SEO 점검(2026-10-20 병한님 요청). 빌드된 페이지(index, /si/, /gu/, /pages/, /guide/, /cases/)를 돌며
아래 항목을 검사하고 docs/audit/audit-YYYY-MM-DD.md 에 표(항목 / 문제 페이지 수 / 예시 주소 3개 / 심각도)로 쓴다.
고치지 않고 목록만 만든다. 매달 1일 새벽 루틴이 돌리고 결과 표를 그날 보고 맨 위에 붙인다(docs/daily-routine-prompt.md).

  python3 scripts/site_audit.py                 # 오늘 날짜로 docs/audit/audit-YYYY-MM-DD.md 를 씀
  python3 scripts/site_audit.py --no-network    # www 넘어가기 검사(인터넷)를 건너뜀
  python3 scripts/site_audit.py --stdout        # 파일을 쓰지 않고 표만 출력

검사 대상에서 빼는 것: 자동 이동 페이지(옛 영문 구 주소·si/세종, http-equiv="refresh")는 "자기 자신으로 가는 리디렉션"과
"내부 링크가 자동 이동 페이지로 감"만 본다. thanks.html·privacy.html(noindex)은 링크 대상으로만 센다.
금지어는 check_pages.py 와 같은 기준(PROMISE_RE·PAGE_BAN_RE·GUIDE_BAN_RE, 동 페이지 지역 칸의 '최대'는 봐 줌)이다.
"""
import argparse
import html as htmllib
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import sitemap_lib  # noqa: E402
from check_pages import GUIDE_BAN_RE, PAGE_BAN_RE, PROMISE_RE  # noqa: E402

KST = timezone(timedelta(hours=9))
OUT_DIR = ROOT / "docs" / "audit"
DIRS = ("si", "gu", "pages", "guide", "cases")
LINK_RE = re.compile(r'<a\b[^>]*\bhref="([^"]*)"', re.I)
LDJSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
SEVERITY_ORDER = {"상": 0, "중": 1, "하": 2}


def rel_of(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def url_of(rel: str, base: str) -> str:
    return f"{base}/" if rel == "index.html" else f"{base}/{quote(rel)}"


def load_pages() -> tuple[dict[str, str], dict[str, str]]:
    """({경로: html} 검사할 페이지, {경로: html} 자동 이동 페이지)."""
    pages, redirects = {}, {}
    for p in [ROOT / "index.html"] + [f for d in DIRS for f in sorted((ROOT / d).glob("*.html"))]:
        text = p.read_text(encoding="utf-8")
        (redirects if 'http-equiv="refresh"' in text else pages)[rel_of(p)] = text
    return pages, redirects


def internal_targets(rel: str, text: str) -> tuple[set[str], list[str]]:
    """(사이트 안 링크가 가리키는 파일 경로, 파일이 없는 링크 목록). 외부·tel·sms·#만 있는 링크는 뺀다."""
    found, broken = set(), []
    base_dir = rel.rsplit("/", 1)[0] + "/" if "/" in rel else ""
    for href in LINK_RE.findall(text):
        href = htmllib.unescape(href).split("#", 1)[0].split("?", 1)[0]
        if not href or re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith("//"):
            if href.startswith("https://pyecha119.com/"):
                path = unquote(href[len("https://pyecha119.com/"):]) or "index.html"
            else:
                continue
        else:
            path = unquote(urljoin("/" + base_dir, href).lstrip("/")) or "index.html"
        if path.endswith("/"):
            path += "index.html"
        if (ROOT / path).is_file():
            found.add(path)
        else:
            broken.append(path)
    return found, broken


def visible_text(text: str) -> str:
    body = text.split("<body", 1)[-1]
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S | re.I)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", body)))


def audit(network: bool = True) -> list[dict]:
    cfg = json.loads((ROOT / "data" / "site_config.json").read_text(encoding="utf-8"))
    base = cfg["site_base_url"].rstrip("/")
    phone, sms = cfg["phone_display"], cfg.get("text_reply_display") or ""
    pages, redirects = load_pages()
    findings: dict[str, dict] = {}

    def add(key: str, sev: str, rel: str) -> None:
        f = findings.setdefault(key, {"item": key, "severity": sev, "pages": []})
        if rel not in f["pages"]:
            f["pages"].append(rel)

    def declare(key: str, sev: str) -> None:  # 문제 0건이어도 표에 줄이 나오게
        findings.setdefault(key, {"item": key, "severity": sev, "pages": []})

    keys = [  # (항목, 심각도) — 표 순서
        ("제목(title)이 다른 페이지와 완전히 같음", "중"), ("설명(meta description)이 다른 페이지와 완전히 같음", "중"),
        ("제목 60자 넘음", "하"), ("설명 160자 넘음", "하"), ("본문 1,500자 미만(공백 제외)", "중"),
        ("고아 페이지(사이트 안 어디서도 링크 안 됨)", "중"), ("첫 화면에서 3클릭 안에 못 감", "중"),
        ("끊긴 내부 링크(파일 없음)", "상"), ("내부 링크가 자동 이동 페이지로 감", "하"), ("자기 자신으로 가는 리디렉션", "상"),
        ("canonical 이 자기 주소가 아님", "상"),
        ("사이트맵에 있는데 파일 없음", "상"), ("파일은 있는데 사이트맵에 없음", "상"), ("사이트맵 lastmod 가 미래이거나 비어 있음", "중"),
        ("구조화 데이터(JSON-LD) 문법 오류", "상"), ("FAQ 질문·답 빈칸", "중"), ("BreadcrumbList 칸에 item 없음", "상"),
        ("og:image 없음 또는 파일 없음", "중"), ("h1 없음 또는 2개 이상", "상"), ("이미지 alt 없음·빈칸", "하"),
        (f"전화 {phone} 표기 없음", "상"), (f"문자 {sms} 표기 없음", "중"),
        ("금지어(check_pages.py 기준)", "상"), ("같은 시·군구 안 랜드마크 문장이 같은 동 페이지 쌍(도어웨이 위험)", "상"),
        ("www.pyecha119.com 이 pyecha119.com 으로 안 넘어감", "상"),
        ("시·도 링크가 시·도 페이지(si/)가 아님(#sido 앵커 등)", "중"),
    ]
    for k, s in keys:
        declare(k, s)
    K = dict(keys)

    # 제목·설명 중복과 길이
    titles, descs = defaultdict(list), defaultdict(list)
    for rel, t in pages.items():
        m = re.search(r"<title>(.*?)</title>", t, re.S)
        title = htmllib.unescape(m.group(1).strip()) if m else ""
        m = re.search(r'<meta name="description" content="([^"]*)"', t)
        desc = htmllib.unescape(m.group(1).strip()) if m else ""
        titles[title].append(rel)
        descs[desc].append(rel)
        if len(title) > 60:
            add("제목 60자 넘음", K["제목 60자 넘음"], rel)
        if len(desc) > 160:
            add("설명 160자 넘음", K["설명 160자 넘음"], rel)
        if len(re.sub(r"\s", "", sitemap_lib.content_text(t))) < 1500:
            add("본문 1,500자 미만(공백 제외)", "중", rel)
    for group, key in ((titles, "제목(title)이 다른 페이지와 완전히 같음"), (descs, "설명(meta description)이 다른 페이지와 완전히 같음")):
        for value, rels in group.items():
            if value and len(rels) > 1:
                for rel in rels:
                    add(key, K[key], rel)

    # 링크: 끊긴 링크, 자동 이동 페이지로 가는 링크, 고아, 첫 화면에서 클릭 수
    graph: dict[str, set[str]] = {}
    inbound: dict[str, set[str]] = defaultdict(set)
    for rel, t in pages.items():
        targets, broken = internal_targets(rel, t)
        graph[rel] = targets
        for b in broken:
            add("끊긴 내부 링크(파일 없음)", "상", rel)
        for tgt in targets:
            if tgt in redirects:
                add("내부 링크가 자동 이동 페이지로 감", "하", rel)
            if tgt != rel:
                inbound[tgt].add(rel)
    for rel in pages:
        if rel != "index.html" and not inbound.get(rel):
            add("고아 페이지(사이트 안 어디서도 링크 안 됨)", "중", rel)
    depth = {"index.html": 0}
    q = deque(["index.html"])
    while q:
        cur = q.popleft()
        for nxt in graph.get(cur, ()):
            if nxt in pages and nxt not in depth:
                depth[nxt] = depth[cur] + 1
                q.append(nxt)
    for rel in pages:
        if depth.get(rel, 99) > 3:
            add("첫 화면에서 3클릭 안에 못 감", "중", rel)

    # 자동 이동 페이지가 자기 자신으로 가는지
    for rel, t in redirects.items():
        m = re.search(r'http-equiv="refresh" content="\d+;\s*url=([^"]+)"', t)
        target = unquote(urljoin("/" + rel, m.group(1)).lstrip("/")) if m else ""
        if target == rel:
            add("자기 자신으로 가는 리디렉션", "상", rel)

    # canonical
    for rel, t in pages.items():
        m = re.search(r'<link rel="canonical" href="([^"]+)"', t)
        if not m or m.group(1) != url_of(rel, base):
            add("canonical 이 자기 주소가 아님", "상", rel)

    # 사이트맵
    entries = sitemap_lib.all_entries(ROOT)
    listed = {u for _, _, u in sitemap_lib.listed_pages(ROOT)}
    today = datetime.now(KST).date().isoformat()
    for u, lm in entries.items():
        path = unquote(u[len(base) + 1:]) or "index.html"
        if not (ROOT / path).is_file():
            add("사이트맵에 있는데 파일 없음", "상", path)
        if not lm or lm > today:
            add("사이트맵 lastmod 가 미래이거나 비어 있음", "중", path)
    for u in listed - set(entries):
        add("파일은 있는데 사이트맵에 없음", "상", unquote(u[len(base) + 1:]) or "index.html")

    # 구조화 데이터·og:image·h1·alt·연락처·금지어
    for rel, t in pages.items():
        for blk in LDJSON_RE.findall(t):
            try:
                data = json.loads(blk)
            except ValueError:
                add("구조화 데이터(JSON-LD) 문법 오류", "상", rel)
                continue
            for obj in data if isinstance(data, list) else [data]:
                if not isinstance(obj, dict):
                    continue
                if obj.get("@type") == "FAQPage":
                    for qa in obj.get("mainEntity", []):
                        ans = (qa.get("acceptedAnswer") or {}).get("text", "")
                        if not str(qa.get("name", "")).strip() or not str(ans).strip():
                            add("FAQ 질문·답 빈칸", "중", rel)
                if obj.get("@type") == "BreadcrumbList":
                    if any(not isinstance(it.get("item"), str) or not it.get("item") for it in obj.get("itemListElement", [])):
                        add("BreadcrumbList 칸에 item 없음", "상", rel)
        og = re.findall(r'<meta property="og:image" content="([^"]+)"', t)
        if not og or not all(u.startswith(base + "/") and (ROOT / unquote(u.split("?", 1)[0][len(base) + 1:])).is_file() for u in og):
            add("og:image 없음 또는 파일 없음", "중", rel)
        if len(re.findall(r"<h1[\s>]", t)) != 1:
            add("h1 없음 또는 2개 이상", "상", rel)
        for img in re.findall(r"<img\b[^>]*>", t):
            m = re.search(r'\balt="([^"]*)"', img)
            if not m or not m.group(1).strip():
                add("이미지 alt 없음·빈칸", "하", rel)
        text = visible_text(t)
        if phone not in text:
            add(f"전화 {phone} 표기 없음", "상", rel)
        if sms and sms not in text:
            add(f"문자 {sms} 표기 없음", "중", rel)
        body = re.sub(r"<style>.*?</style>|<script[^>]*>.*?</script>", "", t, flags=re.S)
        local = re.search(r'<section id="local".*?</section>', body, flags=re.S) if rel.startswith("pages/") else None
        bans = list(PROMISE_RE.finditer(body)) + list((GUIDE_BAN_RE if rel.startswith("guide/") else PAGE_BAN_RE).finditer(body))
        for m in bans:
            if m.group(0).startswith("최대") and local and local.start() <= m.start() < local.end():
                continue  # 동 페이지 지역 칸의 장소 설명("국내 최대 규모의 ○○")은 check_pages 와 같이 봐 준다
            add("금지어(check_pages.py 기준)", "상", rel)
            break

    # 도어웨이 위험: 같은 시·군구 안 랜드마크 문장(landmark_desc)이 완전히 같은 동 페이지 쌍
    regions = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
    same: dict[tuple, list[str]] = defaultdict(list)
    for r in regions:
        if r.get("landmark_desc", "").strip() and f"pages/{r['slug']}.html" in pages:
            same[(r["sido"], r["sigungu"], r["landmark_desc"].strip())].append(f"pages/{r['slug']}.html")
    for rels in same.values():
        if len(rels) > 1:
            for rel in rels:
                add("같은 시·군구 안 랜드마크 문장이 같은 동 페이지 쌍(도어웨이 위험)", "상", rel)

    # 시·도 링크 통일(2026-10-22 눈가리개 감사 3번): #sido 앵커 링크가 없고 "시·도별 폐차 상담" 링크는 si/(세종만 gu/세종-폐차장.html)
    for rel, text in pages.items():
        bad = bool(re.search(r'href="[^"]*#sido', text))
        for block in re.findall(r'<h2>시·도별 폐차 상담</h2><div class="neighbors">(.*?)</div>', text, flags=re.S):
            bad = bad or any(not re.search(r"(^|/)si/[^/]+\.html$|(^|/)gu/세종-폐차장\.html$", h) for h in re.findall(r'href="([^"]+)"', block))
        if bad:
            add("시·도 링크가 시·도 페이지(si/)가 아님(#sido 앵커 등)", "중", rel)

    # www 호스트가 같은 주소의 pyecha119.com 으로 넘어가는지(첫 화면·구 페이지 하나, 넘어가기만 확인)
    key = "www.pyecha119.com 이 pyecha119.com 으로 안 넘어감"
    if network:
        import urllib.error
        import urllib.request

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        host = urlparse(base).netloc
        for rel in ("index.html", next((r for r in pages if r.startswith("gu/")), "index.html")):
            path = "/" if rel == "index.html" else "/" + quote(rel)
            for scheme in ("http", "https"):
                try:
                    opener.open(urllib.request.Request(f"{scheme}://www.{host}{path}", method="HEAD"), timeout=20)
                    loc, code = "", 200
                except urllib.error.HTTPError as e:
                    loc, code = e.headers.get("Location", ""), e.code
                except Exception:
                    loc, code = "", 0
                if code not in (301, 308) or loc != f"https://{host}{path}":
                    add(key, "상", f"{scheme}://www.{host}{path} → {code} {loc or '(이동 없음)'}")
    else:
        findings[key]["skipped"] = True
    return sorted(findings.values(), key=lambda f: (SEVERITY_ORDER[f["severity"]], [k for k, _ in keys].index(f["item"])))


def report(findings: list[dict], day: str, pages_count: int) -> str:
    cfg = json.loads((ROOT / "data" / "site_config.json").read_text(encoding="utf-8"))
    base = cfg["site_base_url"].rstrip("/")
    high = sum(1 for f in findings if f["severity"] == "상" and f["pages"])
    lines = [f"# 사이트 점검 {day}", "",
             f"`python3 scripts/site_audit.py` 결과. 검사한 페이지 {pages_count}장(index·/si/·/gu/·/pages/·/guide/·/cases/, 자동 이동 페이지 제외). "
             "고치지 않고 목록만 적습니다.", "",
             f"**심각도 상 문제 항목 {high}개**" + (" — 확인 필요" if high else ""), "",
             "| 항목 | 문제 페이지 수 | 예시 주소 3개 | 심각도 |", "|---|---|---|---|"]
    for f in findings:
        ex = []
        for p in f["pages"][:3]:
            ex.append(p if p.startswith("http") else f"{base}/" + ("" if p == "index.html" else p))
        n = "건너뜀(--no-network)" if f.get("skipped") else str(len(f["pages"]))
        lines.append(f"| {f['item']} | {n} | {'<br>'.join(ex) if ex else '—'} | {f['severity']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--date", help="파일 이름 날짜(기본 오늘 한국 시간)")
    args = ap.parse_args()
    day = args.date or datetime.now(KST).date().isoformat()
    findings = audit(network=not args.no_network)
    pages, _ = load_pages()
    md = report(findings, day, len(pages))
    high = sum(len(f["pages"]) for f in findings if f["severity"] == "상")
    if args.stdout:
        print(md)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"audit-{day}.md"
        out.write_text(md, encoding="utf-8")
        print(md)
        print(f"저장: {out.relative_to(ROOT).as_posix()}")
    print(f"심각도 상 {high}건" + (f" — 보고 첫 줄에 \"감사 상 {high}건 — 확인 필요\"" if high else ""))


if __name__ == "__main__":
    main()
