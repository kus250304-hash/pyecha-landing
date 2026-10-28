"""
index.html 의 첫 화면 아래 링크 칸과 헤더의 지역 수를 다시 만든다.

2026-10-20 병한님 결정: 예전처럼 시·도 14·구 232·동 833을 전부 잇는 목록을 두지 않고 네 칸만 둔다
(render_home_links): 지역별 폐차 상담(시·도 버튼) / 이런 차도 됩니다(주제 6장 버튼 + 안내 5장 작은 글자) /
최근 문의 지역(pick_index_requests.popular_gu 10곳, 매 빌드 갱신) / 최근 폐차 사례(cases/index.json 최신 6건).
구·동은 시·도 페이지의 "구 → 동 목록"으로 간다(첫 화면 → 시·도 → 동 2클릭).
검색엔진 소유확인 메타 태그(site_config.json 의 naver_site_verification)는 실행할 때마다
<head> 안에 다시 넣으므로 index.html 을 손으로 고쳐도 지워지지 않는다.
사이트 맨 위 폴더의 페이지(index.html·thanks.html·privacy.html)의 <footer> 도 실행할 때마다
공통 내용(대표번호·개인정보처리방침·블로그·유튜브 링크)으로 다시 채운다.
지역·사례 페이지의 footer 는 templates/ 의 템플릿에 들어 있다.

시·도 버튼마다 id="sido-<줄임 이름>" 을 단다. 시·도 페이지가 없는 시·도는 버튼 대신 그 시·도의 구(없으면 동) 페이지
링크를 작게 두고, 동·구·안내 페이지 맨 아래 "시·도별 폐차 상담" 링크(index.html#sido-○○)가 그 자리로 온다.

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
    from build_site import form_parts, page_script
    from first_screen import hero_top_html
    dong_tpl = (ROOT / "templates" / "region-landing-v2.html").read_text(encoding="utf-8")
    font = re.search(r"@font-face\s*\{.*?\}", dong_tpl, flags=re.DOTALL).group(0)
    root_vars = re.search(r":root\s*\{.*?\}", dong_tpl, flags=re.DOTALL).group(0)
    hero_css = re.search(r"/\* hero-v3:start.*?/\* hero-v3:end \*/", dong_tpl, flags=re.DOTALL).group(0)
    script = re.search(r"<script>\s*\(function \(\).*?</script>", dong_tpl, flags=re.DOTALL).group(0)
    script = page_script(script, cfg)
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

CANONICAL_RE = re.compile(r'[ \t]*<link rel="canonical"[^>]*>\n?')


def apply_home_canonical(text: str, cfg: dict) -> str:
    """첫 화면 canonical(2026-10-20): 사이트맵 주소({site_base_url}/)와 같게 <title> 바로 아래에 하나."""
    tag = f'<link rel="canonical" href="{html.escape(cfg["site_base_url"].rstrip("/"), quote=True)}/">\n'
    text, n = re.subn(r"(</title>\n)", lambda m: m.group(1) + tag, CANONICAL_RE.sub("", text), count=1)
    if n != 1:
        raise ValueError("index.html 에서 <title> 을 찾지 못했습니다")
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


# 첫 화면 제목·설명(2026-10-22, 네이버 노출 작전 1): 사이트 이름 "폐차119"를 앞에. 설명에는 010 번호를 쓰지 않는다
HOME_TITLE = "{name} | 전국 폐차·수출 비교 상담 · 전화 {phone}"
HOME_DESC = ("차 번호만 남기시면 폐차값·수출값 둘 다 알려드리고 더 높은 쪽으로 안내합니다. "
             "전국 출장 견인 · 견인비 따로 없음 · 말소증 문자 · 전화 {phone} · 문자 상담 가능.")  # 2026-10-25
SITE_NAME_RE = re.compile(r'[ \t]*<meta property="og:site_name"[^>]*>\n?')


def home_title(cfg: dict) -> str:
    return HOME_TITLE.format(name=cfg["site_name"], phone=cfg["phone_display"])


def home_desc(cfg: dict) -> str:
    return HOME_DESC.format(phone=cfg["phone_display"])


def apply_home_title(text: str, cfg: dict) -> str:
    """첫 화면 <title> 과 meta description 을 site_config 값으로 다시 넣는다(index.html 을 손으로 고치지 않음)."""
    text, n1 = re.subn(r"<title>.*?</title>", lambda _: f"<title>{html.escape(home_title(cfg))}</title>", text, count=1, flags=re.S)
    text, n2 = re.subn(r'<meta name="description" content="[^"]*">',
                       lambda _: f'<meta name="description" content="{html.escape(home_desc(cfg), quote=True)}">', text, count=1)
    if n1 != 1 or n2 != 1:
        raise ValueError("index.html 에서 <title> 또는 description 메타 태그를 찾지 못했습니다")
    return text


def apply_site_name(text: str, cfg: dict, name: str) -> str:
    """og:site_name(2026-10-22): og:title 바로 위, og:title 이 없으면 description(없으면 <title>) 바로 아래에 하나."""
    tag = f'<meta property="og:site_name" content="{html.escape(cfg["site_name"], quote=True)}">\n'
    text = SITE_NAME_RE.sub("", text)
    for pat, before in ((r'(?=<meta property="og:title")', True), (r'(<meta name="description"[^>]*>\n)', False),
                        (r"(</title>\n)", False)):
        text, n = re.subn(pat, (lambda m: tag) if before else (lambda m: m.group(1) + tag), text, count=1)
        if n == 1:
            return text
    raise ValueError(f"{name} 에서 og:site_name 을 넣을 자리를 찾지 못했습니다")


SIDO_ORDER = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "전남광주통합특별시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "경상북도",
    "경상남도", "제주특별자치도",
]

COUNT_RE = re.compile(r"(지역별 상담 페이지) \(현재 \d+개 지역\)")


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


HOME_LINKS_RE = re.compile(r'<main class="container">.*?</main>', re.DOTALL)
HOME_LINKS_STYLE = """<style>
  .home-sec { margin: 28px 0; }
  .home-sec h2 { margin: 0 0 6px; font-size: 21px; color: var(--color-primary); }
  .home-sec .sub { margin: 0 0 12px; color: var(--color-muted); font-size: 14px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chips a, .chips .chip-group { display: inline-block; padding: 10px 14px; border: 1px solid #d6dee0; border-radius: 10px;
    background: #fff; color: inherit; text-decoration: none; font-weight: 700; font-size: 15px; }
  .chips a:hover { border-color: var(--color-primary); color: var(--color-primary); }
  .chips .chip-group a { padding: 0; border: 0; font-weight: 400; text-decoration: underline; }
  .chips.big a { padding: 12px 16px; font-size: 16px; }
  .home-sec .more { margin: 10px 0 0; font-size: 13px; color: var(--color-muted); }
  .home-sec .more a { color: inherit; }
  .case-list { list-style: none; margin: 0; padding: 0; }
  .case-list li { padding: 10px 0; border-bottom: 1px solid #e3e8ea; }
  .case-list a { font-weight: 700; color: inherit; }
  .case-list span { display: block; font-size: 13px; color: var(--color-muted); }
  .fine-print { margin: 32px 0 8px; font-size: 13px; color: var(--color-muted); }
</style>"""


def render_home_links(by_sido: dict[str, list[tuple[str, str]]]) -> str:
    """첫 화면 아래 네 칸(2026-10-20 병한님 결정): 지역별 폐차 상담(시·도 버튼) / 이런 차도 됩니다(주제 6장 버튼 + 안내 5장 작은 글자) /
    최근 문의 지역(pick_index_requests.popular_gu, 10곳) / 최근 폐차 사례(cases/index.json 최신 6건).
    예전처럼 구·동 전체 목록은 넣지 않는다(시·도 페이지에 있음). 시·도 페이지가 아직 없는 시·도는 버튼 대신
    그 시·도의 구(없으면 동) 페이지 링크를 작게 두고, 시·도 링크는 build_site.sido_href 하나로 만든다(2026-10-22, #sido 앵커 링크 없음)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_site import SIDO_SHORT, gu_file, sido_href
    from build_si import si_sidos
    from build_guide import GUIDES, TOPICS, TYPE_BUTTONS
    from pick_index_requests import popular_gu
    esc = lambda v: html.escape(v, quote=True)
    sis = si_sidos()
    gu_by_sido = collect_gu()
    chips = []
    for sido in SIDO_ORDER:
        short = SIDO_SHORT[sido]
        if sido in sis or len(gu_by_sido.get(sido, [])) == 1:  # 시·도 페이지, 세종은 구 페이지(공통 조각 sido_href, 2026-10-22)
            chips.append(f'<a id="sido-{esc(short)}" href="{esc(sido_href(sido, ""))}">{esc(short)}</a>')
            continue
        links = ([(n, "gu/" + f) for n, f in sorted(gu_by_sido.get(sido, []))]
                 or [(full.split()[-1], "pages/" + f) for full, f in sorted(by_sido.get(sido, []))])
        if links:
            chips.append(f'<span class="chip-group" id="sido-{esc(short)}">{esc(short)}: '
                         + " · ".join(f'<a href="{esc(h)}">{esc(n)}</a>' for n, h in links) + "</span>")
    label = dict((f, l) for l, f in TYPE_BUTTONS)
    topics = "".join(f'<a href="guide/{esc(t["file"])}">{esc(label.get(t["file"], t["nav"]))}</a>' for t in TOPICS)
    guides = " · ".join(f'<a href="guide/{esc(g["file"])}">{esc(g["nav"])}</a>' for g in GUIDES)
    popular = "".join(f'<a href="gu/{esc(gu_file(sd, sg))}">{esc(sg or SIDO_SHORT[sd])} 폐차 안내</a>' for sd, sg in popular_gu(10))
    cases_path = ROOT / "cases" / "index.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8")) if cases_path.exists() else []
    cases = sorted((c for c in cases if (ROOT / "cases" / f"{c['slug']}.html").exists()),
                   key=lambda c: (c.get("date") or "", c["slug"]), reverse=True)[:6]
    case_items = "".join(
        f'<li><a href="cases/{esc(c["slug"])}.html">{esc(c["title"])}</a>'
        f'<span>{esc(" ".join(x for x in (SIDO_SHORT.get(c["sido"], c["sido"]), c["sigungu"], c["dong"]) if x))}'
        + (f' · {esc(c["date"])}' if c.get("date") else "") + "</span></li>" for c in cases)
    parts = [
        '<main class="container">', HOME_LINKS_STYLE,
        '<section class="home-sec" id="regions"><h2>지역별 폐차 상담</h2>'
        '<p class="sub">시·도를 고르면 시·군·구와 동별 상담 페이지가 나옵니다</p>'
        f'<div class="chips">{"".join(chips)}</div></section>',
        '<section class="home-sec" id="types"><h2>이런 차도 됩니다</h2>'
        '<p class="sub">압류·말소·상속·시동·방치·저당, 상황별로 정리했습니다</p>'
        f'<div class="chips big">{topics}</div><p class="more">폐차 안내: {guides}</p></section>',
        '<section class="home-sec" id="popular"><h2>최근 문의 지역</h2>'
        '<p class="sub">최근 문의가 온 곳과 상담이 많은 시·군입니다</p>'
        f'<div class="chips">{popular}</div></section>',
    ]
    if case_items:
        parts.append('<section class="home-sec" id="recent-cases"><h2>최근 폐차 사례</h2>'
                     '<p class="sub">실제로 진행한 사례입니다. 지역은 사례마다 표시됩니다</p>'
                     f'<ul class="case-list">{case_items}</ul></section>')
    parts += ['<p class="fine-print">본 사이트는 전국 폐차 협력업체 네트워크와 함께 상담과 연결을 도와드리는 서비스입니다. '
              '차량 상태와 조건에 따라 폐차와 수출 비교매입 중 더 적합한 방법을 안내해 드립니다.</p>', "</main>"]
    return "\n".join(parts)


def main() -> None:
    by_sido = collect_regions()
    total = sum(len(v) for v in by_sido.values())

    text = INDEX_PATH.read_text(encoding="utf-8")
    text, n_groups = HOME_LINKS_RE.subn(lambda _: render_home_links(by_sido), text, count=1)
    if n_groups != 1:
        raise ValueError("index.html에서 <main class=\"container\"> 블록을 찾지 못했습니다")
    # 페이지·지역 수를 자랑하는 문구는 넣지 않는다(2026-10-22 눈가리개 감사 1번). 예전 "(현재 N개 지역)"이 남아 있으면 지운다
    text = COUNT_RE.sub(r"\g<1>", text)
    text = apply_head_meta(text)
    text = apply_home_title(text, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    text = apply_home_hero(text, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    text = apply_home_og(text, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    text = apply_home_canonical(text, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    INDEX_PATH.write_text(text, encoding="utf-8")

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for page in STATIC_PAGES:
        text = apply_icon(apply_footer(page.read_text(encoding="utf-8"), cfg, page.name), page.name)
        text = apply_site_name(text, cfg, page.name)
        page.write_text(apply_analytics(text, cfg, page.name), encoding="utf-8")
    print(f"index.html 갱신 완료: 총 {total}개 지역, 시도 {len(by_sido)}개 (맨 아래 링크: {', '.join(p.name for p in STATIC_PAGES)})")

    # 첫 화면 본문(지역 목록)이 바뀌었을 수 있으니 사이트맵도 다시(2026-10-20, 본문 해시가 같으면 날짜 그대로)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sitemap_lib import write_sitemaps
    counts = write_sitemaps(ROOT)
    print("사이트맵: " + ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
