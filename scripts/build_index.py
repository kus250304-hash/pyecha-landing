"""
index.html의 지역 목록을 data/regions.json 기준으로 다시 생성한다.

regions.json 이 이미 지역별 sido/sigungu/dong을 갖고 있으므로 페이지 HTML을
스크래핑하지 않고 직접 읽는다(템플릿의 title/badge 형식이 바뀌어도 영향받지 않음).
index.html의 지역 목록 블록과 헤더의 지역 수만 교체하고 나머지는 그대로 둔다.
검색엔진 소유확인 메타 태그(site_config.json 의 naver_site_verification)는 실행할 때마다
<head> 안에 다시 넣으므로 index.html 을 손으로 고쳐도 지워지지 않는다.
사이트 맨 위 폴더의 페이지(index.html·thanks.html·privacy.html·save.html)의 <footer> 도 실행할 때마다
공통 내용(대표번호·개인정보처리방침·블로그·유튜브 링크)으로 다시 채운다.
지역·사례 페이지의 footer 는 templates/ 의 템플릿에 들어 있다.

시·도 칸마다 id="sido-<줄임 이름>" 을 달고, 그 시·도의 구 페이지(/gu/) 목록을 맨 위에 넣는다.
시·도 페이지(/si/, 2026-10-02)가 있는 시·도는 그 칸 맨 위에 시·도 페이지 링크를 넣는다.
시·도 페이지가 없는 시·도는 동·구·안내 페이지 맨 아래 "시·도별 폐차 상담" 링크가 이 칸으로 온다.

배치 생성 스크립트나 build_site.py를 실행한 뒤 이 스크립트를 실행하면 index.html이 최신 상태가 된다.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"
REGIONS_PATH = ROOT / "data" / "regions.json"
CONFIG_PATH = ROOT / "data" / "site_config.json"
INDEX_PATH = ROOT / "index.html"
NAVER_META_RE = re.compile(r'[ \t]*<meta name="naver-site-verification"[^>]*>\n?')
VIEWPORT_RE = re.compile(r'(<meta name="viewport"[^>]*>\n)')
FOOTER_RE = re.compile(r"<footer>.*?</footer>", re.DOTALL)
STATIC_PAGES = [ROOT / "index.html", ROOT / "thanks.html", ROOT / "privacy.html"]
STATIC_PAGE_TYPES = {"index.html": "home", "thanks.html": "thanks", "privacy.html": "privacy"}
# 견적 메일 "바로 저장" 페이지(2026-10-16): footer 만 채우고 통계 코드는 넣지 않는다(주소 # 뒤에 전화번호가 있음)
NO_ANALYTICS_PAGES = [ROOT / "save.html"]


def site_footer(cfg: dict) -> str:
    """맨 위 폴더 페이지 공통 footer. 링크 주소는 site_config.json 에서 가져온다."""
    esc = lambda v: html.escape(v, quote=True)
    ext = 'target="_blank" rel="noopener noreferrer"'
    return (
        "<footer>\n"
        "  <p>전국 폐차 비교매입 상담 · 전국 폐차 협력업체 네트워크 연계 서비스</p>\n"
        f'  <p>대표번호 <a href="tel:{esc(cfg["phone_tel"])}">{esc(cfg["phone_display"])}</a>'
        ' · <a href="privacy.html">개인정보처리방침</a> · <a href="index.html">전체 지역 보기</a></p>\n'
        f'  <p><a href="{esc(cfg["blog_url"])}" {ext}>폐차119 블로그</a>'
        f' · <a href="{esc(cfg["youtube_url"])}" {ext}>유튜브</a></p>\n'
        "</footer>"
    )


def apply_footer(text: str, cfg: dict, name: str) -> str:
    text, n = FOOTER_RE.subn(lambda _: site_footer(cfg), text, count=1)
    if n != 1:
        raise ValueError(f"{name} 에서 <footer> 를 찾지 못했습니다")
    return text


def naver_meta_tag(code: str) -> str:
    return f'<meta name="naver-site-verification" content="{html.escape(code, quote=True)}" />\n'


def naver_codes(cfg: dict) -> list[str]:
    """naver_site_verification 은 문자열 하나 또는 목록(여러 계정 소유확인)."""
    code = cfg.get("naver_site_verification")
    if not code:
        return []
    return [code] if isinstance(code, str) else [c for c in code if c]


ICON_RE = re.compile(r'[ \t]*<link rel="icon"[^>]*>\n?')
ICON_TAG = '<link rel="icon" href="favicon.ico" sizes="any">\n'


def apply_icon(text: str, name: str) -> str:
    """맨 위 폴더 favicon.ico 링크를 viewport 태그 바로 아래에 하나 둔다(2026-10-08, 네이버 진단 favicon 400 오류)."""
    text = ICON_RE.sub("", text)
    text, n = VIEWPORT_RE.subn(lambda m: m.group(1) + ICON_TAG, text, count=1)
    if n != 1:
        raise ValueError(f"{name} 에서 viewport 메타 태그를 찾지 못했습니다")
    return text


def apply_analytics(text: str, cfg: dict, name: str) -> str:
    """방문 측정 태그(GA4·네이버 애널리틱스, scripts/analytics.py)를 viewport 태그 바로 아래에 하나 둔다(2026-10-10)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import analytics
    for start, end in ((analytics.START, analytics.END), (analytics.BODY_START, analytics.BODY_END)):
        text = re.sub(r"[ \t]*" + re.escape(start) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.DOTALL)
    body = analytics.body_end_html(cfg)  # 네이버 애널리틱스는 </body> 바로 앞
    if body:
        if text.count("</body>") != 1:
            raise ValueError(f"{name} 에서 </body> 를 찾지 못했습니다")
        text = text.replace("</body>", body + "\n</body>")
    block = analytics.head_html(cfg, STATIC_PAGE_TYPES[name], "전국")
    if not block:
        return text
    text, n = VIEWPORT_RE.subn(lambda m: m.group(1) + block + "\n", text, count=1)
    if n != 1:
        raise ValueError(f"{name} 에서 viewport 메타 태그를 찾지 못했습니다")
    return text


HOME_START, HOME_END = "<!-- home-hero:start -->", "<!-- home-hero:end -->"
HOME_RE = re.compile(re.escape(HOME_START) + r".*?" + re.escape(HOME_END) + r"\n?", re.DOTALL)
OLD_H1 = "<h1>전국 폐차 비교매입 상담 안내</h1>"
SITE_TITLE = '<p class="site-title">전국 폐차 비교매입 상담 안내</p>'


def apply_home_hero(text: str, cfg: dict) -> str:
    """첫 화면 홈(2026-10-13): 지역 목록 위(<body> 맨 앞)에 동 페이지와 똑같은 첫 화면(scripts/first_screen.py)을 둔다.
    지역명은 "전국", 폼의 숨은 칸 region 은 "첫 화면 홈". 모양·폼 스크립트는 동 페이지 템플릿에서 그대로 가져오고,
    예전 제목 줄(h1)은 글을 그대로 두고 p 로 바꿔 H1 이 하나만 있게 한다. 실행할 때마다 다시 넣으므로 손으로 고치지 않는다."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_site import form_parts
    from first_screen import hero_top_html
    dong_tpl = (ROOT / "templates" / "region-landing-v2.html").read_text(encoding="utf-8")
    font = re.search(r"@font-face\s*\{.*?\}", dong_tpl, flags=re.DOTALL).group(0)
    root_vars = re.search(r":root\s*\{.*?\}", dong_tpl, flags=re.DOTALL).group(0)
    hero_css = re.search(r"/\* hero-v3:start.*?/\* hero-v3:end \*/", dong_tpl, flags=re.DOTALL).group(0)
    script = re.search(r"<script>\s*\(function \(\).*?</script>", dong_tpl, flags=re.DOTALL).group(0)
    script = script.replace("{{PHONE_DISPLAY}}", cfg["phone_display"])
    base = cfg["site_base_url"].rstrip("/")
    title = re.search(r"<title>(.*?)</title>", text).group(1)
    form = form_parts(cfg, "첫 화면 홈", "첫 화면 홈", base + "/", title)
    from build_site import contact_parts
    bar = contact_parts(cfg, "")  # 하단 띠 오른쪽 버튼(문자, 카카오 주소가 있으면 카톡도)
    # 띠 아이콘(전화·문자)은 동 페이지 템플릿의 아이콘 묶음에서 두 개만 가져온다
    sprite = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
              + "".join(re.search(rf'<symbol id="{i}".*?</symbol>', dong_tpl, flags=re.DOTALL).group(0) for i in ("i-phone", "i-chat"))
              + "</svg>")
    block = "\n".join([
        HOME_START,
        "<style>", font, root_vars, hero_css,
        "  .hero-v3 .quote-mini p { opacity: 1; }",
        "  .hero-v3 .display { font-family: \"Jalnan\", \"Apple SD Gothic Neo\", \"Malgun Gothic\", sans-serif; font-weight: 400; }",
        "  header .site-title { margin: 0 0 8px; font-size: 26px; font-weight: 700; opacity: 1; }",
        # 하단 고정 띠(2026-10-15): 지역 페이지와 같은 모양·같은 링크. 클릭은 analytics.py 가 .bar 안이면 position=sticky 로 센다
        "  body { padding-bottom: calc(62px + env(safe-area-inset-bottom, 0px)); }",
        f"  .bar {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 50; display: grid; grid-template-columns: {bar['BAR_COLS']}; gap: 8px;"
        " padding: 8px 10px calc(8px + env(safe-area-inset-bottom, 0px)); background: rgba(245,248,248,.96); backdrop-filter: blur(8px); border-top: 1px solid var(--line); }",
        "  .bar .btn { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 52px; padding: 12px 20px; border-radius: 12px;"
        " font-size: 17px; font-weight: 800; text-decoration: none; line-height: 1.2; font-family: inherit; }",
        "  .bar .btn svg { width: 22px; height: 22px; flex: none; }",
        "  .bar .btn-call { background: var(--coral); color: #fff; box-shadow: 0 6px 18px rgba(229,84,31,.32); }",
        "  .bar .btn-sms { background: var(--teal); color: #fff; }",
        "  .bar .btn-kakao { background: #FEE500; color: #191919; }",
        "</style>",
        sprite,
        '<header class="hero hero-v3">',
        hero_top_html(cfg, "전국", form, prefix=""),
        "</header>",
        '<nav class="bar" aria-label="빠른 문의">',
        f'  <a class="btn btn-call" href="tel:{cfg["phone_tel"]}"><svg><use href="#i-phone"/></svg>{cfg["phone_display"]} 전화</a>',
        f"  {bar['BAR_SECOND']}",
        "</nav>",
        script,
        HOME_END,
    ])
    text = HOME_RE.sub("", text).replace(OLD_H1, SITE_TITLE)
    text, n = re.subn(r"<body>\n", lambda m: m.group(0) + block + "\n", text, count=1)
    if n != 1:
        raise ValueError("index.html 에서 <body> 를 찾지 못했습니다")
    return text


def apply_head_meta(text: str) -> str:
    """네이버 서치어드바이저 소유확인 태그를 viewport 태그 바로 아래에 설정 순서대로 하나씩 둔다."""
    codes = naver_codes(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    text = NAVER_META_RE.sub("", text)
    if not codes:
        return text
    tags = "".join(naver_meta_tag(c) for c in codes)
    text, n = VIEWPORT_RE.subn(lambda m: m.group(1) + tags, text, count=1)
    if n != 1:
        raise ValueError("index.html 에서 viewport 메타 태그를 찾지 못했습니다")
    return text

HOME_OG_RE = re.compile(r"[ \t]*<!-- og:start -->.*?<!-- og:end -->\n?", re.DOTALL)


def apply_home_og(text: str, cfg: dict) -> str:
    """첫 화면 홈 대표 이미지(2026-10-16): og/home.png("전국 / 폐차 / 1600-6011", scripts/og_image.py)와
    og:image 태그를 description 태그 바로 아래에 둔다. 실행할 때마다 다시 넣으므로 손으로 고치지 않는다."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import og_image
    base = cfg["site_base_url"].rstrip("/")
    meta = og_image.parts("home", "전국", base, cfg["phone_display"])["OG_META"]
    text = HOME_OG_RE.sub("", text)
    text, n = re.subn(r'(<meta name="description"[^>]*>\n)', lambda m: m.group(1) + "<!-- og:start -->\n" + meta + "\n<!-- og:end -->\n", text, count=1)
    if n != 1:
        raise ValueError("index.html 에서 description 메타 태그를 찾지 못했습니다")
    return text


SIDO_ORDER = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "전남광주통합특별시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "경상북도",
    "경상남도", "제주특별자치도",
]

GROUPS_RE = re.compile(r'(?<=</div>\n\n)(      <div class="region-group"[^>]*>.*</div>\n)(?=</main>)', re.DOTALL)
COUNT_RE = re.compile(r"(지역별 상담 페이지 \(현재 )\d+(개 지역\))")


def collect_regions() -> dict[str, list[tuple[str, str]]]:
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    existing = {p.stem for p in PAGES_DIR.glob("*.html")}

    by_sido: dict[str, list[tuple[str, str]]] = {}
    for r in regions:
        if r["slug"] not in existing:
            continue  # 아직 렌더링되지 않은 지역은 목록에서 제외
        full_name = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
        by_sido.setdefault(r["sido"], []).append((full_name, f"{r['slug']}.html"))

    unknown = set(by_sido) - set(SIDO_ORDER)
    if unknown:
        raise ValueError(f"SIDO_ORDER에 없는 시도: {sorted(unknown)}")
    return by_sido


def collect_gu() -> dict[str, list[tuple[str, str]]]:
    """시·도 → [(구 이름, 구 페이지 파일)] (data/gu.json 에 있고 파일이 만들어진 구만)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_site import gu_file
    gu_path = ROOT / "data" / "gu.json"
    by_sido: dict[str, list[tuple[str, str]]] = {}
    for g in json.loads(gu_path.read_text(encoding="utf-8")) if gu_path.exists() else []:
        f = gu_file(g["sido"], g["sigungu"])
        if (ROOT / "gu" / f).exists():
            by_sido.setdefault(g["sido"], []).append((g["sigungu"] or g["sido"], f))
    return by_sido


def render_groups(by_sido: dict[str, list[tuple[str, str]]], gu_by_sido: dict[str, list[tuple[str, str]]] | None = None) -> str:
    from build_site import SIDO_SHORT
    gu_by_sido = gu_by_sido or {}
    blocks = []
    for sido in SIDO_ORDER:
        entries = sorted(by_sido.get(sido, []))
        if not entries:
            continue
        items = "\n".join(
            f'        <li><a href="pages/{file_name}">{full_name}</a></li>'
            for full_name, file_name in entries
        )
        from build_si import si_file, si_sidos
        si_line = (f'        <p class="gu-links"><a href="si/{html.escape(si_file(sido), quote=True)}">'
                   f"{SIDO_SHORT[sido]} 전체 폐차 상담 페이지</a></p>\n") if sido in si_sidos() else ""
        gus = sorted(gu_by_sido.get(sido, []))
        gu_line = ("        <p class=\"gu-links\">시·군·구 전체 상담: " + " · ".join(
            f'<a href="gu/{html.escape(f, quote=True)}">{html.escape(name)}</a>' for name, f in gus) + "</p>\n") if gus else ""
        blocks.append(
            f'      <div class="region-group" id="sido-{SIDO_SHORT[sido]}">\n'
            f'        <h2>{sido} <span class="count">({len(entries)})</span></h2>\n'
            f"{si_line}{gu_line}"
            "        <ul>\n"
            f"{items}\n"
            "        </ul>\n"
            "      </div>\n"
        )
    return "".join(blocks)


def main() -> None:
    by_sido = collect_regions()
    total = sum(len(v) for v in by_sido.values())

    text = INDEX_PATH.read_text(encoding="utf-8")
    gu_by_sido = collect_gu()
    text, n_groups = GROUPS_RE.subn(lambda _: render_groups(by_sido, gu_by_sido), text, count=1)
    if n_groups != 1:
        raise ValueError("index.html에서 지역 목록 블록을 찾지 못했습니다")
    text, n_count = COUNT_RE.subn(rf"\g<1>{total}\g<2>", text, count=1)
    if n_count != 1:
        raise ValueError("index.html에서 지역 수 문구를 찾지 못했습니다")
    text = apply_head_meta(text)
    text = apply_home_hero(text, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    text = apply_home_og(text, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    INDEX_PATH.write_text(text, encoding="utf-8")

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for page in STATIC_PAGES:
        text = apply_icon(apply_footer(page.read_text(encoding="utf-8"), cfg, page.name), page.name)
        page.write_text(apply_analytics(text, cfg, page.name), encoding="utf-8")
    for page in NO_ANALYTICS_PAGES:
        page.write_text(apply_icon(apply_footer(page.read_text(encoding="utf-8"), cfg, page.name), page.name), encoding="utf-8")
    print(f"index.html 갱신 완료: 총 {total}개 지역, 시도 {len(by_sido)}개 (맨 아래 링크: {', '.join(p.name for p in STATIC_PAGES)})")


if __name__ == "__main__":
    main()
