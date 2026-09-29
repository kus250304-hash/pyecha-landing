"""
data/gu.json + data/regions.json 으로 시·군·구 페이지(gu/<slug>.html)를 만든다.

사용법
  python3 scripts/build_gu.py          # gu.json 의 구 페이지 전부 (build_site.py 도 끝에 이 함수를 부른다)

gu.json 항목 (확인된 구만 넣는다. 못 채운 구는 넣지 않고 보고에 이유를 적는다)
  {
    "slug": "seoul-jongno", "sido": "서울특별시", "sigungu": "종로구",
    "intro": "구 소개 2~3문장",
    "intro_landmarks": [{"name": "인왕산", "dong_slug": "seoul-jongno-nusang"}, ...],  # 2~3개, 그 구 동 페이지에서 이미 확인된 랜드마크
    "faqs": [["질문", "답"], ...],                                                    # 3개, 구마다 다르게
    "public_info": [{"label": "...", "value": "...", "source": "...", "url": "https://..."}],  # 확인된 줄만
    "dropped_info": ["확인 못 해 뺀 항목과 이유"],                                   # 보고용, 페이지에는 안 나옴
    "checked_on": "YYYY-MM-DD"
  }

빌더가 막는 것: 동 페이지 3개 미만, 소개에 쓴 랜드마크가 그 구 동 페이지의 확인된 랜드마크가 아님,
소개에 랜드마크 이름이 없음, FAQ 가 3개가 아님, 공공 정보가 비었거나 출처 주소가 없음, 금액·결과 약속 표현.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import variants as V

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "gu-landing.html"
DONG_TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
OUT = ROOT / "gu"
MIN_DONG_PAGES = 3
BAN_RE = re.compile(r"보장|무조건|100%|1위|최저가|\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩")


def validate(g: dict, dongs: list[dict]) -> list[str]:
    errs = []
    if len(dongs) < MIN_DONG_PAGES:
        errs.append(f"동 페이지 {len(dongs)}개 (3개 이상이어야 함)")
    by_slug = {r["slug"]: r for r in dongs}
    lms = g.get("intro_landmarks") or []
    if not 2 <= len(lms) <= 3:
        errs.append("소개 랜드마크는 2~3개")
    for lm in lms:
        r = by_slug.get(lm.get("dong_slug"))
        if not r or r["landmark_name"] != lm.get("name"):
            errs.append(f"소개 랜드마크 '{lm.get('name')}' 가 이 구 동 페이지({lm.get('dong_slug')})의 랜드마크가 아님")
        if lm.get("name") and lm["name"] not in g.get("intro", ""):
            errs.append(f"소개 글에 '{lm.get('name')}' 이 없음")
    if len(re.findall(r"[다요]\.", g.get("intro", ""))) not in (2, 3):
        errs.append("소개는 2~3문장")
    faqs = g.get("faqs") or []
    if len(faqs) != 3 or any(len(qa) != 2 or not all(x.strip() for x in qa) for qa in faqs):
        errs.append("FAQ 는 질문·답 3쌍")
    info = g.get("public_info") or []
    if not info:
        errs.append("공공 정보가 한 줄도 없음 (확인된 줄이 없으면 이 구는 보류)")
    for row in info:
        if not all(str(row.get(k, "")).strip() for k in ("label", "value", "source")) or not re.match(r"^https?://\S+\.\S+", row.get("url", "")):
            errs.append(f"공공 정보 '{row.get('label')}' 에 내용·출처·주소 중 빠진 것 있음")
    text = " ".join([g.get("intro", "")] + [x for qa in faqs for x in qa] + [r.get("value", "") for r in info])
    m = BAN_RE.search(text)
    if m:
        errs.append(f"금액·결과 약속 표현 '{m.group(0)}'")
    return errs


def render_all(regions: list[dict], cfg: dict, gu_data: list[dict], groups: dict[str, list[dict]]) -> list[str]:
    """gu.json 의 구 페이지를 모두 렌더링하고, 내용이 바뀐 구 슬러그 목록을 돌려준다. 잘못된 항목이 있으면 멈춘다."""
    from build_site import SIDO_SHORT, breadcrumb, contact_parts, esc  # build_site 가 이 모듈을 부르므로 여기서 가져온다

    if not gu_data:
        return []
    template = TEMPLATE.read_text(encoding="utf-8")
    dong_tpl = DONG_TEMPLATE.read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", dong_tpl, flags=re.DOTALL).group(0)
    sprite = re.search(r'<svg width="0" height="0"[^>]*>.*?</svg>', dong_tpl, flags=re.DOTALL).group(0)  # 아이콘 묶음
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]

    # 같은 이름의 구(중구·동구 …)가 여러 시도에 있으면 제목에 시도 줄임 이름을 붙인다
    name_count: dict[str, int] = {}
    for slug, rs in groups.items():
        nm = rs[0]["sigungu"] or SIDO_SHORT[rs[0]["sido"]]
        name_count[nm] = name_count.get(nm, 0) + 1
    order = sorted(g["slug"] for g in gu_data)

    problems = []
    changed = []
    OUT.mkdir(exist_ok=True)
    for g in gu_data:
        dongs = sorted(groups.get(g["slug"], []), key=lambda r: r["dong"])
        errs = validate(g, dongs)
        if errs:
            problems.append(f"{g['slug']}: " + "; ".join(errs))
            continue
        sido, sigungu = g["sido"], g["sigungu"]
        gu = sigungu or SIDO_SHORT[sido]
        gu_full = " ".join(x for x in (sido, sigungu) if x)
        title_name = gu if name_count.get(gu, 0) <= 1 else f"{SIDO_SHORT[sido]} {gu}"
        i = order.index(g["slug"])
        v_intro, v_consult, v_close = V.GU_INTRO[i % V.N], V.GU_CONSULT[(i + 2) % V.N], V.GU_CLOSING[(i + 4) % V.N]

        meta_title = f"{title_name} 폐차 | 폐차 보상금 vs 수출 시세 비교"
        meta_desc = (f"{gu_full} 폐차 상담 안내. 동별 출장 방문 안내 {len(dongs)}곳과 폐차 전에 알아두면 좋은 공공 정보, "
                     f"폐차 보상금과 수출 시세 비교 상담. 전화 {phone_disp}")
        canonical = f"{base}/gu/{g['slug']}.html"

        intro_html = f"<p>{esc(g['intro'].strip())}</p>"
        dong_list = "".join(
            f'<a href="../pages/{esc(r["slug"])}.html"><b>{esc(r["dong"])} 폐차</b><span>{esc(r["landmark_name"])}</span></a>'
            for r in dongs
        )
        faq_html = "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in g["faqs"])
        info_rows = "\n        ".join(
            f'<tr><th>{esc(row["label"])}</th><td>{esc(row["value"])}'
            f'<small>출처: <a href="{esc(row["url"])}" target="_blank" rel="noopener noreferrer">{esc(row["source"])}</a></small></td></tr>'
            for row in g["public_info"]
        )
        crumbs = [{"@type": "ListItem", "position": 1, "name": "전체 지역", "item": f"{base}/"}]
        if sigungu:
            crumbs.append({"@type": "ListItem", "position": 2, "name": SIDO_SHORT[sido]})
        crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": gu, "item": canonical})
        jsonld = [
            {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in g["faqs"]]},
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs},
        ]
        # 길 안내: 서울 › 종로구 (구 이름은 이 페이지라 링크 없음)
        crumb_html = '<nav class="crumbs" aria-label="지역 경로">' + " › ".join(
            ([esc(SIDO_SHORT[sido])] if sigungu else []) + [esc(gu)]) + "</nav>"

        values = {
            "META_TITLE": esc(meta_title), "META_DESC": esc(meta_desc), "CANONICAL": canonical,
            "JSONLD": json.dumps(jsonld, ensure_ascii=False),
            "STYLE": style, "SPRITE": sprite, "BREADCRUMB": crumb_html,
            "GU": esc(gu), "GU_FULL": esc(gu_full), "GU_TOPIC": esc(V.fill("{gu}{은는}", gu=gu)),
            "HERO_SUB": esc(V.fill(v_intro["hero"], gu=gu)),
            "INTRO_HTML": intro_html,
            "LIST_SUB": esc(V.fill(v_intro["list"], gu=gu)),
            "DONG_LIST_HTML": dong_list,
            "FAQ_HTML": faq_html,
            "INFO_ROWS": info_rows,
            "CHECKED_ON": esc(g.get("checked_on", "")),
            "CONSULT_TEXT": esc(V.fill(v_consult, phone=phone_disp)),
            "CLOSING_H2": esc(V.fill(v_close, gu=gu)).replace("&lt;br&gt;", "<br>"),
            "PHONE_TEL": phone_tel, "PHONE_DISPLAY": phone_disp,
            "YOUTUBE_URL": esc(cfg["youtube_url"]), "BLOG_URL": esc(cfg["blog_url"]),
            **contact_parts(cfg, gu),
        }
        cleaned = re.sub(r"<!DOCTYPE html>\s*<!--.*?-->", "<!DOCTYPE html>", template, count=1, flags=re.DOTALL)

        def sub(m: re.Match) -> str:
            if m.group(1) not in values:
                raise KeyError(f"구 템플릿 자리 {m.group(1)} 에 대응하는 값이 없습니다")
            return values[m.group(1)]

        html_text = re.sub(r"\{\{(\w+)\}\}", sub, cleaned)
        # 하단 바 칸 비율은 동 페이지 스타일의 {{BAR_COLS}} 자리를 그대로 채운다
        html_text = html_text.replace("{{BAR_COLS}}", contact_parts(cfg, gu)["BAR_COLS"])
        out = OUT / f"{g['slug']}.html"
        if not out.exists() or out.read_text(encoding="utf-8") != html_text:
            out.write_text(html_text, encoding="utf-8")
            changed.append(g["slug"])
            print(f"렌더링: gu/{g['slug']}.html")
    if problems:
        raise SystemExit("구 페이지를 만들 수 없음:\n  " + "\n  ".join(problems))
    return changed


def main() -> None:
    from build_site import CONFIG, GU_DATA, REGIONS, gu_groups, load_json
    from sitemap_lib import update_sitemap

    regions = load_json(REGIONS)
    changed = render_all(regions, load_json(CONFIG), load_json(GU_DATA, default=[]), gu_groups(regions))
    update_sitemap(ROOT, [], paths=[f"gu/{g}.html" for g in changed])
    print(f"완료: 구 페이지 {len(changed)}개 변경")


if __name__ == "__main__":
    main()
