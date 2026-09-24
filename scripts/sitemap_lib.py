"""
sitemap.xml 자동 관리 유틸리티.

build_site.py(지역 페이지)와 build_cases.py(사례 페이지)가 파일을 다 쓴 뒤
update_sitemap()을 호출해 URL을 sitemap.xml에 반영한다.
이미 있는 URL은 lastmod만 오늘 날짜로 갱신하고, 새 URL은 추가한다.
"""
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

SITE_BASE_URL = "https://kus250304-hash.github.io/pyecha-landing"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

ET.register_namespace("", SITEMAP_NS)


def _tag(name: str) -> str:
    return f"{{{SITEMAP_NS}}}{name}"


def update_sitemap(
    root_dir: Path,
    slugs: list[str],
    changefreq: str = "monthly",
    priority: str = "0.8",
    paths: list[str] | None = None,
) -> Path:
    """root_dir/sitemap.xml 에 root_dir/pages/<slug>.html 각각의 절대 URL을
    추가하거나 lastmod를 갱신한다. paths 로는 "cases/xxx.html" 같은 다른 상대 경로도
    넣을 수 있다. 사이트 루트(index.html) 엔트리도 항상 보장한다.
    변경된 sitemap.xml의 경로를 반환한다.
    """
    sitemap_path = root_dir / "sitemap.xml"
    today = date.today().isoformat()

    if sitemap_path.exists():
        tree = ET.parse(sitemap_path)
        urlset = tree.getroot()
    else:
        urlset = ET.Element(_tag("urlset"))
        tree = ET.ElementTree(urlset)

    existing = {}
    for url_el in urlset.findall(_tag("url")):
        loc_el = url_el.find(_tag("loc"))
        if loc_el is not None and loc_el.text:
            existing[loc_el.text] = url_el

    def upsert(loc: str, cf: str, pr: str) -> None:
        if loc in existing:
            url_el = existing[loc]
            lastmod_el = url_el.find(_tag("lastmod"))
            if lastmod_el is None:
                lastmod_el = ET.SubElement(url_el, _tag("lastmod"))
            lastmod_el.text = today
        else:
            url_el = ET.SubElement(urlset, _tag("url"))
            ET.SubElement(url_el, _tag("loc")).text = loc
            ET.SubElement(url_el, _tag("lastmod")).text = today
            ET.SubElement(url_el, _tag("changefreq")).text = cf
            ET.SubElement(url_el, _tag("priority")).text = pr
            existing[loc] = url_el

    upsert(f"{SITE_BASE_URL}/", "weekly", "1.0")
    for slug in slugs:
        upsert(f"{SITE_BASE_URL}/pages/{slug}.html", changefreq, priority)
    for rel in paths or []:
        upsert(f"{SITE_BASE_URL}/{rel.lstrip('/')}", changefreq, priority)

    def sort_key(url_el):
        loc = url_el.find(_tag("loc")).text
        return (loc != f"{SITE_BASE_URL}/", loc)

    ordered = sorted(urlset.findall(_tag("url")), key=sort_key)
    for u in ordered:
        urlset.remove(u)
    for u in ordered:
        urlset.append(u)

    ET.indent(tree, space="  ")
    tree.write(sitemap_path, encoding="UTF-8", xml_declaration=True)
    return sitemap_path
