"""
data/si.json + data/gu.json 으로 시·도 페이지(si/<시도 줄임 이름>-폐차장.html)를 만든다(2026-10-02).
역할은 그 시·도의 구 페이지를 모아 잇는 허브다. 랜드마크·소개 문장은 넣지 않는다.

사용법
  python3 scripts/build_si.py              # si.json 의 시·도 페이지 전부 (build_site.py 도 끝에 이 함수를 부른다)
  python3 scripts/build_si.py candidates   # 만들 수 있는데 아직 없는 시·도와 si.json 뼈대 (파일을 바꾸지 않음)

조건: 그 시·도에 구 페이지(data/gu.json)가 3개 이상(MIN_GU_PAGES). 세종은 시 하나가 곧 구 페이지라 만들지 않는다.
si.json·si_held.json 에 있는 시·도는 후보에서 빠진다.

si.json 항목 (확인된 것만 넣는다. 못 채우면 data/si_held.json 에 이유와 함께 보류)
  {
    "sido": "서울특별시",
    "faqs": [["질문", "답"], ...],                       # 3개, 그 시·도 이름이 들어간 주제 문구(docs/keyword-insights-2026-10-02.md 4절)
    "public_info": [{"label", "value", "source", "url"}], # 공식 출처가 있는 줄만(말소등록 관청·조기폐차 공고 등)
    "dropped_info": ["확인 못 해 뺀 항목과 이유"],       # 보고용, 페이지에는 안 나옴
    "checked_on": "YYYY-MM-DD"
  }

페이지 내용: 첫 화면 전화·문자 버튼과 폼(동·구 페이지와 같은 핵심 문장), 그 시·도 구 페이지 목록(있는 구만, "준비 중" 없음),
진행 순서, FAQ 3개(+ 실제 통화 FAQ 4개, variants.call_faqs), 그 시·도 사례 카드(최신 6건), 공공 정보, 협력업체 고지.
제목은 고정 틀 하나: "{시도 줄임} 폐차장 · 폐차 | 시·군·구별 출장 폐차 · 수출 비교 · 조기폐차 안내 | 전화 1600-6011".
빌더가 막는 것: 구 페이지 3개 미만, FAQ 3개가 아님, 공공 정보 없음·출처 주소 없음, 금액·결과 약속·단정 표현.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_gu import BAN_RE

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "si-landing.html"
DONG_TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
OUT = ROOT / "si"
SI_DATA = ROOT / "data" / "si.json"
SI_HELD = ROOT / "data" / "si_held.json"
MIN_GU_PAGES = 3
MAX_CASES = 6


def si_file(sido: str) -> str:
    from build_site import SIDO_SHORT
    return f"{SIDO_SHORT[sido]}-폐차장.html"


def si_rel(sido: str) -> str:
    return "si/" + quote(si_file(sido))


def gu_of(sido: str, gu_data: list[dict]) -> list[dict]:
    """그 시·도의 구 페이지(세종처럼 시군구가 빈 것은 뺀다)."""
    return sorted((g for g in gu_data if g["sido"] == sido and g["sigungu"]), key=lambda g: g["sigungu"])


def load_si() -> list[dict]:
    return json.loads(SI_DATA.read_text(encoding="utf-8")) if SI_DATA.exists() else []


def si_sidos() -> set[str]:
    """시·도 페이지가 있는(si.json 에 있는) 시·도. 길 안내·맨 아래 링크·첫 화면이 이걸 보고 링크를 단다."""
    return {s["sido"] for s in load_si()}


def candidates(gu_data: list[dict]) -> list[str]:
    done = si_sidos() | ({s["sido"] for s in json.loads(SI_HELD.read_text(encoding="utf-8"))} if SI_HELD.exists() else set())
    from build_index import SIDO_ORDER
    return [s for s in SIDO_ORDER if s not in done and len(gu_of(s, gu_data)) >= MIN_GU_PAGES]


def validate(s: dict, gus: list[dict]) -> list[str]:
    errs = []
    if len(gus) < MIN_GU_PAGES:
        errs.append(f"구 페이지 {len(gus)}개 ({MIN_GU_PAGES}개 이상이어야 함)")
    faqs = s.get("faqs") or []
    if len(faqs) != 3 or any(len(qa) != 2 or not all(x.strip() for x in qa) for qa in faqs):
        errs.append("FAQ 는 질문·답 3쌍")
    info = s.get("public_info") or []
    if not info:
        errs.append("공공 정보가 한 줄도 없음 (확인된 줄이 없으면 이 시·도는 보류)")
    for row in info:
        if not all(str(row.get(k, "")).strip() for k in ("label", "value", "source")) or not re.match(r"^https?://\S+\.\S+", row.get("url", "")):
            errs.append(f"공공 정보 '{row.get('label')}' 에 내용·출처·주소 중 빠진 것 있음")
    m = BAN_RE.search(" ".join([x for qa in faqs for x in qa] + [r.get("value", "") for r in info]))
    if m:
        errs.append(f"금액·결과 약속 표현 '{m.group(0)}'")
    return errs


def render_all(regions: list[dict], cfg: dict, gu_data: list[dict], cases: list[dict] | None = None) -> list[str]:
    """si.json 의 시·도 페이지를 모두 렌더링한다. 잘못된 항목이 있으면 멈춘다. 내용이 바뀐 경로("si/…")를 돌려준다."""
    from build_site import (SIDO_SHORT, UPDATED_MARK, area_links_html, case_cards_html, contact_parts, esc, form_parts,
                            gu_file, josa, page_jsonld, with_updated_date)
    import variants as V
    from vehicle_stats import registration_row_sido, with_registration

    si_data = load_si()
    if not si_data:
        return []
    cases = cases or []
    template = TEMPLATE.read_text(encoding="utf-8")
    dong_tpl = DONG_TEMPLATE.read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", dong_tpl, flags=re.DOTALL).group(0)
    sprite = re.search(r'<svg width="0" height="0"[^>]*>.*?</svg>', dong_tpl, flags=re.DOTALL).group(0)
    script = re.search(r"<script>\s*\(function \(\).*?</script>", dong_tpl, flags=re.DOTALL).group(0)
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]
    text_disp = cfg.get("text_reply_display") or ""
    dong_count: dict[tuple[str, str], int] = {}
    for r in regions:
        dong_count[(r["sido"], r["sigungu"])] = dong_count.get((r["sido"], r["sigungu"]), 0) + 1

    problems, changed = [], []
    OUT.mkdir(exist_ok=True)
    for i, s in enumerate(si_data):
        sido = s["sido"]
        gus = gu_of(sido, gu_data)
        errs = validate(s, gus)
        if errs:
            problems.append(f"{sido}: " + "; ".join(errs))
            continue
        si = SIDO_SHORT[sido]
        info = with_registration(s["public_info"], registration_row_sido(sido))  # 등록대수 줄은 통계 파일에서(2026-10-03)
        meta_title = f"{si} 폐차장 · 폐차 | 시·군·구별 출장 폐차 · 수출 비교 · 조기폐차 안내 | 전화 {phone_disp}"
        text_part = f" / 문자 {text_disp}" if text_disp else ""
        meta_desc = (f"{sido} 폐차 상담. 시·군·구별 출장 방문, 폐차 전에 수출과 비교해 유리한 쪽으로 안내합니다. "
                     f"전화 {phone_disp}{text_part}. 금액은 상담 후 확인.")
        canonical = f"{base}/{si_rel(sido)}"

        gu_list = "".join(
            f'<a href="../gu/{esc(gu_file(g["sido"], g["sigungu"]))}"><b>{esc(g["sigungu"])} 폐차장</b>'
            f'<span>동별 상담 페이지 {dong_count.get((g["sido"], g["sigungu"]), 0)}곳</span></a>'
            for g in gus
        )
        my_cases = sorted((c for c in cases if c["sido"] == sido), key=lambda c: c.get("date") or "", reverse=True)
        cases_sub = (f"{si}에서 진행한 실제 사례입니다. 지역은 카드마다 표시됩니다" if my_cases
                     else f"{si} 사례는 준비 중입니다. 유튜브와 블로그에서 실제 진행 사례를 보실 수 있습니다")
        # 시·도마다 다른 질문 3개 + 실제 통화 FAQ 풀에서 4개(2026-10-03)
        faqs = [tuple(qa) for qa in s["faqs"]] + V.call_faqs("si:" + sido, 4)
        faq_html = "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)
        info_rows = "\n        ".join(
            f'<tr><th>{esc(row["label"])}</th><td>{esc(row["value"])}'
            f'<small>출처: <a href="{esc(row["url"])}" target="_blank" rel="noopener noreferrer">{esc(row["source"])}</a></small></td></tr>'
            for row in info
        )
        jsonld = [
            {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "전체 지역", "item": f"{base}/"},
                {"@type": "ListItem", "position": 2, "name": si, "item": canonical}]},
        ]
        values = {
            "META_TITLE": esc(meta_title), "META_DESC": esc(meta_desc), "CANONICAL": canonical,
            "JSONLD": json.dumps(jsonld, ensure_ascii=False), "PAGE_JSONLD": page_jsonld(meta_title, canonical),
            "AREA_LINKS": area_links_html(regions, gu_data, here_si=sido),
            "STYLE": style, "SPRITE": sprite,
            "BREADCRUMB": f'<nav class="crumbs" aria-label="지역 경로"><a href="../index.html">전체 지역</a> › {esc(si)}</nav>',
            "SI": esc(si), "SI_FULL": esc(sido), "SI_JOSA": josa(sido, "은", "는"),
            "GU_LIST_HTML": gu_list, "FAQ_HTML": faq_html, "INFO_ROWS": info_rows,
            "CHECKED_ON": esc(s.get("checked_on", "")), "UPDATED_ON": UPDATED_MARK,
            "CASES_SUB": esc(cases_sub), "CASES_HTML": case_cards_html(my_cases[:MAX_CASES]),
            "CONSULT_TEXT": esc(V.fill(V.GU_CONSULT[i % V.N], phone=phone_disp)),
            "CLOSING_H2": esc(V.fill(V.GU_CLOSING[(i + 2) % V.N], gu=si)).replace("&lt;br&gt;", "<br>"),
            "PHONE_TEL": phone_tel, "PHONE_DISPLAY": phone_disp,
            "YOUTUBE_URL": esc(cfg["youtube_url"]), "BLOG_URL": esc(cfg["blog_url"]),
            **contact_parts(cfg, si),
            **form_parts(cfg, si, sido),
            "SCRIPT": script.replace("{{PHONE_DISPLAY}}", phone_disp),
        }
        cleaned = re.sub(r"<!DOCTYPE html>\s*<!--.*?-->", "<!DOCTYPE html>", template, count=1, flags=re.DOTALL)

        def sub(m: re.Match) -> str:
            if m.group(1) not in values:
                raise KeyError(f"시·도 템플릿 자리 {m.group(1)} 에 대응하는 값이 없습니다")
            return values[m.group(1)]

        html_text = re.sub(r"\{\{(\w+)\}\}", sub, cleaned).replace("{{BAR_COLS}}", values["BAR_COLS"])
        out = OUT / si_file(sido)
        old_text = out.read_text(encoding="utf-8") if out.exists() else None
        html_text = with_updated_date(html_text, old_text)
        if old_text != html_text:
            out.write_text(html_text, encoding="utf-8")
            changed.append(si_rel(sido))
            print(f"렌더링: si/{out.name}")
    if problems:
        raise SystemExit("시·도 페이지를 만들 수 없음:\n  " + "\n  ".join(problems))
    return changed


def main() -> None:
    from build_site import CASES_INDEX, CONFIG, GU_DATA, REGIONS, load_json
    gu_data = load_json(GU_DATA, default=[])
    if len(sys.argv) > 1 and sys.argv[1] == "candidates":
        from datetime import datetime, timedelta, timezone
        cands = candidates(gu_data)
        if not cands:
            print("만들 수 있는 시·도가 없습니다 (구 페이지 3개 이상인 시·도가 모두 끝났거나 보류됨)")
            return
        today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        for sido in cands:
            print(f"\n=== {sido}: 구 페이지 " + ", ".join(g["sigungu"] for g in gu_of(sido, gu_data)))
            print(json.dumps({"sido": sido, "faqs": [], "public_info": [], "dropped_info": [], "checked_on": today}, ensure_ascii=False))
        return
    from sitemap_lib import update_sitemap
    changed = render_all(load_json(REGIONS), load_json(CONFIG), gu_data, load_json(CASES_INDEX, default=[]))
    update_sitemap(ROOT, [], paths=changed)
    print(f"완료: 시·도 페이지 {len(changed)}개 변경")


if __name__ == "__main__":
    main()
