"""
data/regions.json + data/site_config.json + templates/region-landing-v2.html 로
pages/<slug>.html 을 렌더링하고 sitemap.xml 을 갱신한다.

사용법
  python3 scripts/build_site.py                 # 전체 렌더링
  python3 scripts/build_site.py --only a,b,c    # 지정한 슬러그만 (시범 적용)

site_config.json 에서 null 인 값은 해당 요소를 숨기거나 대체 문구로 바꾼다:
  hours_text         → 운영시간 줄 생략
  sms_number         → 문자 버튼 생략, 하단 바 두 번째 버튼은 견적 폼 이동
  kakao_channel_url  → 카카오톡 버튼 생략
  web3forms_access_key → 폼이 thanks.html 로만 이동 (전송 안 됨). 값이 있으면 Web3Forms 로 전송 후 thanks.html
  business.*         → 푸터의 사업자 줄 생략
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sitemap_lib import update_sitemap
from pick_next_regions import GWANGJU_GU, SIDO_PREFIX, romanize
import variants as V

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
REGIONS = ROOT / "data" / "regions.json"
CONFIG = ROOT / "data" / "site_config.json"
CASES_INDEX = ROOT / "cases" / "index.json"
GU_DATA = ROOT / "data" / "gu.json"
OUT = ROOT / "pages"

LEADING_COMMENT_RE = re.compile(r"<!DOCTYPE html>\s*<!--.*?-->", re.DOTALL)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def load_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def local_tokens(r: dict) -> list[str]:
    toks = [r["dong"], r["landmark_name"]] + r["sigungu"].split()
    return [t for t in toks if t]


def pick_local_faqs(r: dict, n: int = 3) -> list[tuple[str, str]]:
    toks = local_tokens(r)
    local = [(q, a) for q, a in r["faqs"] if any(t in q or t in a for t in toks)]
    rest = [qa for qa in r["faqs"] if qa not in local]
    return (local + rest)[:n]


def neighbors_for(r: dict, regions: list[dict], n: int = 6) -> tuple[str, list[dict]]:
    same_gu = [x for x in regions if x["slug"] != r["slug"] and x["sido"] == r["sido"] and x["sigungu"] == r["sigungu"]]
    if len(same_gu) >= 3:
        return f"{r['sigungu'] or r['sido']} 다른 지역 폐차 상담", same_gu[:n]
    same_sido = [x for x in regions if x["slug"] != r["slug"] and x["sido"] == r["sido"] and x not in same_gu]
    picked = (same_gu + same_sido)[:n]
    label = f"{r['sigungu'] or r['sido']} 인근 지역 폐차 상담" if same_gu else f"{r['sido']} 다른 지역 폐차 상담"
    return label, picked


def case_page_map(regions: list[dict], cases: list[dict], extra_pages: int) -> dict[str, set[str]]:
    """사례별로 보여줄 페이지: 같은 동 페이지 전부 + 같은 시군구(세종은 시 전체)의 다른 동 페이지 최대 extra_pages 곳.
    다른 시군구·시도에는 보이지 않는다."""
    by_gu: dict[tuple[str, str], list[dict]] = {}
    for r in regions:
        by_gu.setdefault((r["sido"], r["sigungu"]), []).append(r)
    mapping = {}
    for c in cases:
        group = by_gu.get((c["sido"], c["sigungu"]), [])
        same_dong = {r["slug"] for r in group if r["dong"] == c["dong"]}
        others = sorted(r["slug"] for r in group if r["dong"] != c["dong"])
        mapping[c["slug"]] = same_dong | set(others[:extra_pages])
    return mapping


def cases_for(r: dict, cases: list[dict], page_map: dict[str, set[str]], n: int = 4) -> tuple[str, str, list[dict]]:
    """이 페이지에 보여줄 사례(최신순). 같은 동 사례를 먼저, 그다음 같은 시군구의 다른 동 사례."""
    mine = [c for c in cases if r["slug"] in page_map.get(c["slug"], ())]
    if not mine:
        return "실제 사례 보기", "유튜브와 블로그에서 실제 진행 사례를 보실 수 있습니다", []
    same_dong = [c for c in mine if c["dong"] == r["dong"]]
    others = [c for c in mine if c["dong"] != r["dong"]]
    picked = (same_dong + others)[:n]
    if not others or not any(c in picked for c in others):
        return f"{r['dong']} 작업 사례", "이 동에서 진행한 실제 사례입니다", picked
    area = r["sigungu"] or r["sido"]
    return f"{area} 작업 사례", f"{area} 안 가까운 동에서 진행한 실제 사례입니다. 지역은 카드마다 표시됩니다", picked


def contact_parts(cfg: dict, dong: str) -> dict:
    """문자·카카오 버튼, 하단 바 두 번째 버튼, 푸터 사업자 줄. 지역 페이지와 사례 페이지가 같이 쓴다."""
    sms = cfg.get("sms_number")
    sms_href = f'href="sms:{esc(sms)}?body={esc(dong)}%20폐차%20문의드립니다"' if sms else ""
    sms_btn = f'<a class="btn btn-sms" {sms_href}><svg><use href="#i-chat"/></svg>문자로 문의</a>' if sms else ""
    kakao = cfg.get("kakao_channel_url")
    kakao_btn = f'<a class="btn btn-kakao" href="{esc(kakao)}" target="_blank" rel="noopener noreferrer">카카오톡 채널</a>' if kakao else ""
    if sms:
        bar_second = f'<a class="btn btn-sms" {sms_href}><svg><use href="#i-chat"/></svg>문자</a>'
        bar_cols = "2fr 1fr"
    else:
        bar_second = '<a class="btn btn-quote" href="#quote" style="background:#fff"><svg><use href="#i-chat"/></svg>견적 남기기</a>'
        bar_cols = "3fr 2fr"

    b = cfg.get("business") or {}
    parts = []
    for key, label in (("name", "상호"), ("ceo", "대표"), ("registration_number", "사업자등록번호"), ("address", "주소"), ("email", "이메일")):
        if b.get(key):
            parts.append(f"{label} {esc(b[key])}")
    footer_biz = (" · ".join(parts) + "<br>") if parts else ""
    return {"SMS_BUTTON": sms_btn, "KAKAO_BUTTON": kakao_btn, "BAR_SECOND": bar_second, "BAR_COLS": bar_cols, "FOOTER_BIZ": footer_biz}


WEB3FORMS_URL = "https://api.web3forms.com/submit"

SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "전남광주통합특별시": "전남광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}


RENAMED_ON_TEXT = "2026년 7월 1일"


def is_renamed(r: dict) -> bool:
    return bool(r.get("old_sido") or r.get("old_sigungu"))


def old_region_name(r: dict) -> str:
    """"(옛 …)" 안에 넣을 옛 이름: 구가 바뀌면 '중구 신포동', 시도만 바뀌면 '광주광역시 동구 계림동'."""
    if r.get("old_sigungu"):
        return f"{r['old_sigungu']} {r['dong']}"
    return " ".join(x for x in (r["old_sido"], r["sigungu"], r["dong"]) if x)


def josa(word: str, with_final: str, without_final: str) -> str:
    """앞 낱말 끝 글자의 받침에 맞춰 은/는, 이/가 를 고른다."""
    ch = word[-1]
    if "가" <= ch <= "힣":
        return with_final if (ord(ch) - 0xAC00) % 28 else without_final
    return with_final if ch in "013678" else without_final


def renamed_note(r: dict) -> str:
    """첫 화면 아래 회색 작은 글씨 한 줄. 이름이 바뀌지 않은 지역은 빈 문자열이라 페이지가 그대로다."""
    if not is_renamed(r):
        return ""
    old = " ".join(x for x in (r.get("old_sido") or r["sido"], r.get("old_sigungu") or r["sigungu"], r["dong"]) if x)
    new = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
    text = (f"{RENAMED_ON_TEXT}부터 {old}{josa(old, '은', '는')} {new}{josa(new, '이', '가')} 되었습니다. "
            "옛 주소로 문의하셔도 됩니다.")
    return f'\n<p class="renamed-note" style="margin:10px auto 0;padding:0 18px;max-width:960px;color:#5E6E70;font-size:12px;line-height:1.6">{esc(text)}</p>'


def title_labels(regions: list[dict]) -> dict[str, str]:
    """페이지 제목에 쓸 지역 이름. 겹치지 않을 만큼만 길게 붙인다:
    역삼동 → (동 이름이 겹치면) 강남구 중동 → (구+동도 겹치면) 부산 중구 중앙동1가
    행정구역이 바뀐 지역은 새 이름이 보이도록 늘 시도 줄임 이름부터 붙인다(인천 제물포구 신포동)."""
    dong_counts = Counter(r["dong"] for r in regions)
    pair_counts = Counter((r["sigungu"], r["dong"]) for r in regions)
    labels = {}
    for r in regions:
        if is_renamed(r):
            labels[r["slug"]] = " ".join(x for x in (SIDO_SHORT[r["sido"]], r["sigungu"], r["dong"]) if x)
        elif dong_counts[r["dong"]] == 1:
            labels[r["slug"]] = r["dong"]
        elif pair_counts[(r["sigungu"], r["dong"])] == 1:
            labels[r["slug"]] = f"{r['sigungu'] or r['sido']} {r['dong']}"
        else:
            labels[r["slug"]] = " ".join(x for x in (SIDO_SHORT[r["sido"]], r["sigungu"], r["dong"]) if x)
    return labels


def gu_slug(sido: str, sigungu: str) -> str:
    """구 페이지 파일 이름: 동 페이지 이름의 앞부분과 같은 규칙(서울 종로구 → seoul-jongno, 세종 → sejong).
    이름이 바뀐 구는 새 이름으로 만든다(인천 제물포구 → incheon-jemulpo)."""
    parts = ["gwangju" if sido == "전남광주통합특별시" and sigungu in GWANGJU_GU else SIDO_PREFIX[sido]]
    for tok in sigungu.split():
        parts.append(romanize(tok[:-1] if tok[-1] in "시군구" and len(tok) > 2 else tok))
    return "-".join(p for p in parts if p)


def gu_groups(regions: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in regions:
        groups.setdefault(gu_slug(r["sido"], r["sigungu"]), []).append(r)
    return groups


def breadcrumb(r: dict, gu_pages: set[str]) -> str:
    """첫 화면 위 길 안내: 서울 › 종로구 › 청운동. 구 페이지가 있으면 구 이름에 링크(세종은 시 이름)."""
    g = gu_slug(r["sido"], r["sigungu"])
    gu_label = r["sigungu"] or SIDO_SHORT[r["sido"]]
    gu_html = f'<a href="../gu/{g}.html">{esc(gu_label)}</a>' if g in gu_pages else esc(gu_label)
    items = ([esc(SIDO_SHORT[r["sido"]])] if r["sigungu"] else []) + [gu_html, esc(r["dong"])]
    return '<nav class="crumbs" aria-label="지역 경로">' + " › ".join(items) + "</nav>"


def parts_range(parts: list[str]) -> str:
    """["종로1가", …, "종로6가"] → "종로1가~6가" (번호가 이어지지 않으면 쉼표로 나열)."""
    nums = [re.search(r"(\d+)가$", p) for p in parts]
    if parts and all(nums):
        base = re.sub(r"\d+가$", "", parts[0])
        ns = [int(m.group(1)) for m in nums]
        if all(re.sub(r"\d+가$", "", p) == base for p in parts) and ns == list(range(ns[0], ns[0] + len(ns))):
            return f"{base}{ns[0]}가~{ns[-1]}가"
    return ", ".join(parts)


def render(r: dict, regions: list[dict], cfg: dict, cases: list[dict], template: str, labels: dict, page_map: dict,
           combo: tuple[int, int, int] = (0, 0, 0), gu_pages: set[str] = frozenset()) -> str:
    full = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
    sigungu_dong = " ".join(x for x in (r["sigungu"], r["dong"]) if x)
    title_region = labels[r["slug"]]
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]

    # 숫자 타일: 실제 수치가 없는 누적 상담 건수는 지어내지 않고 넣지 않는다
    stats = (
        '<div class="stat"><span class="num display">당일</span><span class="lbl">접수</span></div>'
        '<div class="stat"><span class="num display">최고가</span><span class="lbl">도전</span></div>'
    )

    hours = f"<p>전화 응대 {esc(cfg['hours_text'])} · 야간·주말 접수는 문자로 남겨주시면 순서대로 연락드립니다.</p>" if cfg.get("hours_text") else "<p>지금 전화 주시면 순서대로 연결됩니다. 통화가 어려우면 견적 폼으로 남겨주세요.</p>"

    # 폼: Web3Forms 로 전송. 받는 메일 제목에 어느 동 페이지에서 온 문의인지 보이게 한다
    form_subject = "[견적문의] " + " ".join(x for x in (SIDO_SHORT[r["sido"]], r["sigungu"], r["dong"]) if x)
    if cfg.get("web3forms_access_key"):
        form_action, form_method = WEB3FORMS_URL, "POST"
        form_hidden = (
            f'<input type="hidden" name="access_key" value="{esc(cfg["web3forms_access_key"])}">'
            f'<input type="hidden" name="subject" value="{esc(form_subject)}">'
            f'<input type="hidden" name="from_name" value="폐차 견적 폼">'
            f'<input type="hidden" name="redirect" value="{base}/thanks.html">'
        )
    else:
        form_action, form_method, form_hidden = "../thanks.html", "GET", ""

    # 지역 FAQ
    local_faqs = pick_local_faqs(r)
    local_faq_html = "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in local_faqs
    )
    # 공통 문장은 여러 벌 중 이 페이지에 배정된 조합(소개, FAQ, 마무리)을 쓴다 (scripts/variants.py)
    intro, closing = V.DONG_INTRO[combo[0]], V.DONG_CLOSING[combo[2]]
    common_faqs = list(zip(V.COMMON_FAQ_QUESTIONS, V.DONG_FAQ[combo[1]]))
    common_faq_html = "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in common_faqs)
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in common_faqs + local_faqs
        ],
    }

    # 이웃 링크
    n_title, neighbors = neighbors_for(r, regions)
    neighbors_html = "".join(
        f'<a href="{esc(x["slug"])}.html">{esc(x["dong"])} 폐차</a>' for x in neighbors
    )

    # 사례
    c_title, c_sub, picked = cases_for(r, cases, page_map)
    if picked:
        cases_html = '<div class="cases" data-nosnippet>' + "".join(
            f'<a class="case" href="../cases/{esc(c["slug"])}.html">'
            + (f'<img src="../cases/images/{esc(c["thumb"])}" alt="" loading="lazy" width="800" height="600">' if c.get("thumb") else "")
            + f'<div class="body"><span class="region">{esc((c["sigungu"] or c["sido"]) + " " + c["dong"])} 작업 사례</span>'
            + f'<h3>{esc(c["title"])}</h3><p>{esc(c.get("summary", ""))}</p></div></a>'
            for c in picked
        ) + "</div>"
    else:
        cases_html = ""

    meta_title = f"{title_region} 폐차 | 폐차 보상금 vs 수출 시세 비교, 견인비 없음 · {phone_disp}"
    old_mark = f"(옛 {old_region_name(r)})" if is_renamed(r) else ""
    hero_sub = f"{title_region}{old_mark} {intro['hero']}" if old_mark else intro["hero"]
    lm_html = f'<span class="landmark">{esc(r["landmark_name"])}</span>'
    # 이름 뒤 조사는 글자로 고르고, 랜드마크 이름만 강조 표시로 바꿔 끼운다
    lead = V.fill(intro["lead"], dong=r["dong"], lm="\x00")
    for pair, (a, b) in (("{을를}", ("을", "를")), ("{이가}", ("이", "가")), ("{은는}", ("은", "는"))):
        lead = lead.replace("\x00" + pair, "\x00" + V.josa(r["landmark_name"], a, b))
    lead = esc(lead).replace("\x00", lm_html)
    parts = r.get("dong_parts") or []
    parts_note = (f'<p style="color:#5E6E70;font-size:14px">이 페이지는 {esc(parts_range(parts))}를 함께 안내합니다.</p>'
                  if parts else "")
    meta_desc = (
        f"{full}{old_mark} 폐차 전에 폐차 보상금과 수출 시세를 함께 비교해 드립니다. 압류·서류 없음도 상담 가능, "
        f"당일 접수, 견인비 없음. {r['landmark_name']} 인근 출장 방문. 전화 {phone_disp}"
    )

    values = {
        "META_TITLE": esc(meta_title),
        "META_DESC": esc(meta_desc),
        "CANONICAL": f"{base}/pages/{r['slug']}.html",
        "FAQ_JSONLD": json.dumps(faq_ld, ensure_ascii=False),
        "REGION_FULL_NAME": esc(full),
        "SIGUNGU_DONG": esc(sigungu_dong),
        "DONG": esc(r["dong"]),
        "H1_REGION": esc(title_region if is_renamed(r) else r["dong"]),
        "HERO_SUB": esc(hero_sub),
        "RENAMED_NOTE": renamed_note(r),
        "BREADCRUMB": breadcrumb(r, gu_pages),
        "LOCAL_SEC_SUB": esc(V.fill(intro["sec"], full=full)),
        "LANDMARK_LEAD": lead,
        "PARTS_NOTE": parts_note,
        "VISIT_TEXT": esc(intro["visit"]),
        "COMMON_FAQ_HTML": common_faq_html,
        "PARTNER_TEXT": esc(V.fill(closing["partner"], dong=r["dong"])),
        "CLOSING_H2": esc(V.fill(closing["h2"], dong=r["dong"])).replace("&lt;br&gt;", "<br>"),
        "CLOSING_LEAD": esc(closing["lead"]),
        "LANDMARK_NAME": esc(r["landmark_name"]),
        "LANDMARK_DESC": esc(r["landmark_desc"]),
        "SERVICE_INTRO": esc(r["service_intro"]),
        "PHONE_TEL": phone_tel,
        "PHONE_DISPLAY": phone_disp,
        "STATS_HTML": stats,
        "HOURS_HTML": hours,
        "FORM_ACTION": form_action,
        "FORM_METHOD": form_method,
        "FORM_HIDDEN": form_hidden,
        **contact_parts(cfg, r["dong"]),
        "LOCAL_FAQ_HTML": local_faq_html,
        "NEIGHBOR_TITLE": esc(n_title),
        "NEIGHBORS_HTML": neighbors_html,
        "CASES_TITLE": esc(c_title),
        "CASES_SUB": esc(c_sub),
        "CASES_HTML": cases_html,
        "YOUTUBE_URL": esc(cfg["youtube_url"]),
        "BLOG_URL": esc(cfg["blog_url"]),
    }

    cleaned = LEADING_COMMENT_RE.sub("<!DOCTYPE html>", template, count=1)

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(f"템플릿 자리 {key} 에 대응하는 값이 없습니다")
        return values[key]

    return re.sub(r"\{\{(\w+)\}\}", sub, cleaned)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="쉼표로 구분한 슬러그 목록")
    args = ap.parse_args()

    regions = load_json(REGIONS)
    cfg = load_json(CONFIG)
    cases = load_json(CASES_INDEX, default=[])
    template = TEMPLATE.read_text(encoding="utf-8")
    OUT.mkdir(exist_ok=True)

    labels = title_labels(regions)
    page_map = case_page_map(regions, cases, int(cfg.get("cases_extra_pages_per_case", 5)))
    groups = gu_groups(regions)
    combos = V.assign_combos({g: [r["slug"] for r in rs] for g, rs in groups.items()})
    gu_data = load_json(GU_DATA, default=[])
    gu_pages = {g["slug"] for g in gu_data}

    targets = regions
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        targets = [r for r in regions if r["slug"] in wanted]
        missing = wanted - {r["slug"] for r in targets}
        if missing:
            raise SystemExit(f"regions.json 에 없는 슬러그: {sorted(missing)}")

    changed = []
    for r in targets:
        out_path = OUT / f"{r['slug']}.html"
        html_text = render(r, regions, cfg, cases, template, labels, page_map, combos[r["slug"]], gu_pages)
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != html_text:
            out_path.write_text(html_text, encoding="utf-8")
            changed.append(r["slug"])
            print(f"렌더링: pages/{r['slug']}.html")

    # 구 페이지(/gu/)는 동 페이지 목록에 따라 달라지므로 늘 함께 다시 만든다
    from build_gu import render_all as render_gu
    gu_changed = render_gu(regions, cfg, gu_data, groups)

    # 내용이 실제로 바뀐 페이지만 sitemap 의 수정일을 갱신한다
    update_sitemap(ROOT, changed, paths=[f"gu/{g}.html" for g in gu_changed])
    print(f"완료: {len(targets)}개 중 {len(changed)}개 페이지 변경, 구 페이지 {len(gu_changed)}개 변경, sitemap.xml 갱신")


if __name__ == "__main__":
    main()
