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
  web3forms_access_key → 폼이 thanks.html 로만 이동 (전송 안 됨, 시범용)
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

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
REGIONS = ROOT / "data" / "regions.json"
CONFIG = ROOT / "data" / "site_config.json"
CASES_INDEX = ROOT / "cases" / "index.json"
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


def cases_for(r: dict, cases: list[dict], n: int = 4) -> tuple[str, str, list[dict]]:
    """cases/index.json(최신순) 에서 이 지역에 보여줄 사례를 고른다: 같은 동 → 같은 시군구 → 같은 시도 → 전국"""
    same_dong = [c for c in cases if (c.get("sido"), c.get("sigungu"), c.get("dong")) == (r["sido"], r["sigungu"], r["dong"])]
    if same_dong:
        return f"{r['dong']} 폐차 사례", "같은 동에서 진행한 실제 사례입니다", same_dong[:n]
    same_gu = [c for c in cases if (c.get("sido"), c.get("sigungu")) == (r["sido"], r["sigungu"])]
    if same_gu:
        return f"{r['sigungu'] or r['sido']} 폐차 사례", "가까운 지역에서 진행한 실제 사례입니다", same_gu[:n]
    same_sido = [c for c in cases if c.get("sido") == r["sido"]]
    if same_sido:
        return f"{r['sido']} 폐차 사례", "같은 지역에서 진행한 실제 사례입니다", same_sido[:n]
    if cases:
        # 페이지마다 다른 조합이 보이도록 슬러그 해시로 시작점을 돌린다
        start = sum(ord(ch) for ch in r["slug"]) % len(cases)
        rotated = cases[start:] + cases[:start]
        return "최근 폐차 사례", "실제 진행한 사례입니다", rotated[:min(3, n)]
    return "실제 사례 보기", "유튜브와 블로그에서 실제 진행 사례를 보실 수 있습니다", []


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


def render(r: dict, regions: list[dict], cfg: dict, cases: list[dict], template: str, dong_counts: dict) -> str:
    full = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
    sigungu_dong = " ".join(x for x in (r["sigungu"], r["dong"]) if x)
    # 같은 동 이름이 다른 시/군/구에도 있으면 title/description이 겹치지 않도록 구를 붙인다
    title_region = f"{r['sigungu'] or r['sido']} {r['dong']}" if dong_counts[r["dong"]] > 1 else r["dong"]
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]

    # 숫자 타일: 실제 수치가 없는 누적 상담 건수는 지어내지 않고 넣지 않는다
    stats = (
        '<div class="stat"><span class="num display">당일</span><span class="lbl">접수</span></div>'
        '<div class="stat"><span class="num display">최고가</span><span class="lbl">도전</span></div>'
    )

    hours = f"<p>전화 응대 {esc(cfg['hours_text'])} · 야간·주말 접수는 문자로 남겨주시면 순서대로 연락드립니다.</p>" if cfg.get("hours_text") else "<p>지금 전화 주시면 순서대로 연결됩니다. 통화가 어려우면 견적 폼으로 남겨주세요.</p>"

    # 폼
    if cfg.get("web3forms_access_key"):
        form_action, form_method = "https://api.web3forms.com/submit", "POST"
        form_hidden = (
            f'<input type="hidden" name="access_key" value="{esc(cfg["web3forms_access_key"])}">'
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
    common_faqs = [
        ("압류가 있어도 되나요?", "차령이 기준을 넘었다면 압류·저당이 있어도 말소가 되는 경우가 많습니다. 등록원부를 보고 바로 확인해 드립니다."),
        ("서류가 없어도 되나요?", "등록증을 잃어버리셨어도 재발급 없이 진행할 수 있는 방법을 안내해 드립니다. 신분증만 준비해 주세요."),
        ("차가 안 움직여도 되나요?", "시동이 안 걸리거나 사고 차량이어도 견인차가 갑니다. 견인비는 받지 않습니다."),
        ("비용이 나오나요?", "폐차·수출 어느 쪽이든 고객님이 내시는 비용은 없습니다. 예외가 생기면 진행 전에 먼저 말씀드립니다."),
    ]
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
    c_title, c_sub, picked = cases_for(r, cases)
    if picked:
        cases_html = '<div class="cases" data-nosnippet>' + "".join(
            f'<a class="case" href="../cases/{esc(c["slug"])}.html">'
            + (f'<img src="../cases/images/{esc(c["thumb"])}" alt="" loading="lazy" width="800" height="600">' if c.get("thumb") else "")
            + f'<div class="body"><h3>{esc(c["title"])}</h3><p>{esc(c.get("summary", ""))}</p></div></a>'
            for c in picked
        ) + "</div>"
    else:
        cases_html = ""

    meta_title = f"{title_region} 폐차 | 폐차 보상금 vs 수출 시세 비교, 견인비 없음 · {phone_disp}"
    meta_desc = (
        f"{full} 폐차 전에 폐차 보상금과 수출 시세를 함께 비교해 드립니다. 압류·서류 없음도 상담 가능, "
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

    dong_counts = Counter(r["dong"] for r in regions)

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
        html_text = render(r, regions, cfg, cases, template, dong_counts)
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != html_text:
            out_path.write_text(html_text, encoding="utf-8")
            changed.append(r["slug"])
            print(f"렌더링: pages/{r['slug']}.html")

    # 내용이 실제로 바뀐 페이지만 sitemap 의 수정일을 갱신한다
    update_sitemap(ROOT, changed)
    print(f"완료: {len(targets)}개 중 {len(changed)}개 페이지 변경, sitemap.xml 갱신")


if __name__ == "__main__":
    main()
