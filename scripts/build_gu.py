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
소개에 랜드마크 이름이 없음, FAQ 가 3개가 아님, 공공 정보가 비었거나 출처 주소가 없음, 금액·결과 약속 표현,
"최고가"·"1등"·"최대"·"실시간 접수" 같은 단정 표현.

제목·설명 틀은 하나로 고정한다(2026-10-01, docs/roadmap.md 1절). 문장 틀 여러 벌(variants.py)은 본문에만 쓴다.
맨 위 "최종 업데이트" 날짜와 구조화 데이터의 dateModified 는 그 페이지 내용이 실제로 바뀐 날(한국 시간)이다.
내용이 그대로면 예전 날짜를 그대로 둔다(build_site.with_updated_date).

파일 이름은 한글(2026-10-01): gu/종로구-폐차장.html (build_site.gu_file). gu.json 의 영문 slug 는 데이터 열쇠로만 쓴다.
예전 영문 주소(gu/<slug>.html)가 저장소에 있는 구는 그 파일을 새 주소로 넘겨주는 자동 이동 페이지로 바꿔 둔다.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import variants as V

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "gu-landing.html"
DONG_TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
OUT = ROOT / "gu"
MIN_DONG_PAGES = 3
MAX_CASES = 6
BAN_RE = re.compile(r"보장|무조건|100%|1위|1등|최저가|최고가|최대(?!한)|실시간\s*접수|\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩")


def redirect_html(gu: str, new_file: str, new_abs: str) -> str:
    """예전 영문 주소에 남기는 자동 이동 페이지(meta refresh). canonical 은 새 주소."""
    rel = quote(new_file)
    return (
        "<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{gu} 폐차 상담 페이지 주소가 바뀌었습니다</title>\n"
        f"<link rel=\"canonical\" href=\"{new_abs}\">\n"
        f"<meta http-equiv=\"refresh\" content=\"0; url={rel}\">\n"
        f"<script>location.replace(\"{rel}\");</script>\n"
        "</head>\n<body>\n"
        f"<p><a href=\"{rel}\">{gu} 폐차 상담 페이지로 이동</a></p>\n"
        "</body>\n</html>\n"
    )


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


def gu_cases(slug: str, cases: list[dict]) -> list[dict]:
    """이 구(세종은 시 전체)에서 진행한 사례, 최신순."""
    from build_site import gu_slug
    mine = [c for c in cases if gu_slug(c["sido"], c["sigungu"]) == slug]
    return sorted(mine, key=lambda c: c.get("date") or "", reverse=True)


def render_all(regions: list[dict], cfg: dict, gu_data: list[dict], groups: dict[str, list[dict]],
               cases: list[dict] | None = None) -> tuple[list[str], list[str]]:
    """gu.json 의 구 페이지를 모두 렌더링한다. 잘못된 항목이 있으면 멈춘다.
    돌려주는 값: (내용이 바뀐 구 페이지 경로, sitemap 에서 뺄 예전 영문 주소 경로) — 둘 다 "gu/…" 형식."""
    # build_site 가 이 모듈을 부르므로 여기서 가져온다
    from build_site import (SIDO_SHORT, UPDATED_MARK, area_links_html, case_cards_html, contact_parts, esc, gu_file, gu_rel,
                            gu_title_names, page_jsonld, with_updated_date)

    if not gu_data:
        return [], []
    cases = cases or []
    template = TEMPLATE.read_text(encoding="utf-8")
    dong_tpl = DONG_TEMPLATE.read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", dong_tpl, flags=re.DOTALL).group(0)
    sprite = re.search(r'<svg width="0" height="0"[^>]*>.*?</svg>', dong_tpl, flags=re.DOTALL).group(0)  # 아이콘 묶음
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]
    text_disp = cfg.get("text_reply_display") or ""

    # 같은 이름의 구(중구·동구 …)가 여러 시도에 있으면 제목에 시도 줄임 이름을 붙인다
    title_names = gu_title_names(groups)
    order = sorted(g["slug"] for g in gu_data)

    problems = []
    changed = []
    dropped = []
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
        title_name = title_names.get(g["slug"], gu)
        i = order.index(g["slug"])
        v_intro, v_consult, v_close = V.GU_INTRO[i % V.N], V.GU_CONSULT[(i + 2) % V.N], V.GU_CLOSING[(i + 4) % V.N]

        # 제목·설명은 고정 틀 하나 (2026-10-01). 단정 표현·가짜 숫자를 넣지 않는다
        meta_title = f"{title_name} 폐차장 · 폐차 | 당일 말소 가능 · 수출 비교 · 조기폐차 안내 | 전화 {phone_disp}"
        text_part = f" / 문자 {text_disp}" if text_disp else ""
        meta_desc = (f"{title_name} 전 지역 폐차 상담. 폐차 전에 수출과 비교해 유리한 쪽으로 안내합니다. "
                     f"전화 {phone_disp}{text_part}. 금액은 상담 후 확인.")
        canonical = f"{base}/{gu_rel(sido, sigungu)}"

        my_cases = gu_cases(g["slug"], cases)
        if my_cases:
            cases_sub = f"{gu}에서 진행한 실제 사례입니다. 지역은 카드마다 표시됩니다"
        else:
            cases_sub = f"{gu} 사례는 준비 중입니다. 유튜브와 블로그에서 실제 진행 사례를 보실 수 있습니다"

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
            "PAGE_JSONLD": page_jsonld(meta_title, canonical),
            "AREA_LINKS": area_links_html(regions, gu_data, here_gu=g),
            "STYLE": style, "SPRITE": sprite, "BREADCRUMB": crumb_html,
            "GU": esc(gu), "GU_FULL": esc(gu_full), "GU_TOPIC": esc(V.fill("{gu}{은는}", gu=gu)),
            "HERO_SUB": esc(V.fill(v_intro["hero"], gu=gu)),
            "INTRO_HTML": intro_html,
            "LIST_SUB": esc(V.fill(v_intro["list"], gu=gu)),
            "DONG_LIST_HTML": dong_list,
            "FAQ_HTML": faq_html,
            "INFO_ROWS": info_rows,
            "CHECKED_ON": esc(g.get("checked_on", "")),
            "UPDATED_ON": UPDATED_MARK,
            "CASES_SUB": esc(cases_sub),
            "CASES_HTML": case_cards_html(my_cases[:MAX_CASES]),
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
        out = OUT / gu_file(sido, sigungu)
        old_text = out.read_text(encoding="utf-8") if out.exists() else None
        html_text = with_updated_date(html_text, old_text)
        if old_text != html_text:
            out.write_text(html_text, encoding="utf-8")
            changed.append(gu_rel(sido, sigungu))
            print(f"렌더링: gu/{out.name}")

        # 예전 영문 주소가 있으면 새 한글 주소로 넘겨주는 페이지로 둔다(sitemap 에서는 뺀다)
        legacy = OUT / f"{g['slug']}.html"
        if legacy.exists():
            stub = redirect_html(esc(gu), out.name, canonical)
            if legacy.read_text(encoding="utf-8") != stub:
                legacy.write_text(stub, encoding="utf-8")
                print(f"자동 이동: gu/{legacy.name} → gu/{out.name}")
            dropped.append(f"gu/{legacy.name}")
    if problems:
        raise SystemExit("구 페이지를 만들 수 없음:\n  " + "\n  ".join(problems))
    return changed, dropped


def main() -> None:
    from build_site import CASES_INDEX, CONFIG, GU_DATA, REGIONS, gu_groups, load_json
    from sitemap_lib import update_sitemap

    regions = load_json(REGIONS)
    changed, dropped = render_all(regions, load_json(CONFIG), load_json(GU_DATA, default=[]), gu_groups(regions),
                                  load_json(CASES_INDEX, default=[]))
    update_sitemap(ROOT, [], paths=changed, drop=dropped)
    print(f"완료: 구 페이지 {len(changed)}개 변경")


if __name__ == "__main__":
    main()
