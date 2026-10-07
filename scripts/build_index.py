"""
index.html의 지역 목록을 data/regions.json 기준으로 다시 생성한다.

regions.json 이 이미 지역별 sido/sigungu/dong을 갖고 있으므로 페이지 HTML을
스크래핑하지 않고 직접 읽는다(템플릿의 title/badge 형식이 바뀌어도 영향받지 않음).
index.html의 지역 목록 블록과 헤더의 지역 수만 교체하고 나머지는 그대로 둔다.
검색엔진 소유확인 메타 태그(site_config.json 의 naver_site_verification)는 실행할 때마다
<head> 안에 다시 넣으므로 index.html 을 손으로 고쳐도 지워지지 않는다.
사이트 맨 위 폴더의 페이지(index.html·thanks.html·privacy.html)의 <footer> 도 실행할 때마다
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
    INDEX_PATH.write_text(text, encoding="utf-8")

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for page in STATIC_PAGES:
        page.write_text(apply_icon(apply_footer(page.read_text(encoding="utf-8"), cfg, page.name), page.name), encoding="utf-8")
    print(f"index.html 갱신 완료: 총 {total}개 지역, 시도 {len(by_sido)}개 (맨 아래 링크: {', '.join(p.name for p in STATIC_PAGES)})")


if __name__ == "__main__":
    main()
