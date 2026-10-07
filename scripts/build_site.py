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
import csv
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

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
LEGAL_DONG_CSV = ROOT / "data" / "legal_dong_list.csv"
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


def case_page_map(regions: list[dict], cases: list[dict], extra_pages: int) -> dict[str, set[str]]:
    """사례별로 보여줄 페이지: 같은 동 페이지 전부 + 같은 시군구(세종은 시 전체)의 다른 동 페이지 최대 extra_pages 곳.
    다른 시군구·시도에는 보이지 않는다. 동 없이 시군구까지만 확인된 사례는 동 페이지에 붙이지 않는다(구 페이지에만)."""
    by_gu: dict[tuple[str, str], list[dict]] = {}
    for r in regions:
        by_gu.setdefault((r["sido"], r["sigungu"]), []).append(r)
    mapping = {}
    for c in cases:
        if not c["dong"]:
            mapping[c["slug"]] = set()
            continue
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


def case_alt(c: dict) -> str:
    """사례 카드 사진 설명(2026-10-08, 네이버 진단 alt 누락): "구미시 송정동 쏘나타 폐차 사례 사진"."""
    region = ((c.get("sigungu") or c.get("sido") or "") + " " + (c.get("dong") or "")).strip()
    return " ".join(x for x in (region, c.get("car") or "", "폐차 사례 사진") if x)


def case_cards_html(picked: list[dict]) -> str:
    """사례 카드 묶음. 동 페이지와 구 페이지가 같이 쓴다. 사례가 없으면 빈 문자열."""
    if not picked:
        return ""
    return '<div class="cases" data-nosnippet>' + "".join(
        f'<a class="case" href="../cases/{esc(c["slug"])}.html">'
        + (f'<img src="../cases/images/{esc(c["thumb"])}" alt="{esc(case_alt(c))}" loading="lazy" width="800" height="600">' if c.get("thumb") else "")
        + f'<div class="body"><span class="region">{esc(((c["sigungu"] or c["sido"]) + " " + c["dong"]).strip())} 작업 사례</span>'
        + f'<h3>{esc(c["title"])}</h3><p>{esc(c.get("summary", ""))}</p></div></a>'
        for c in picked
    ) + "</div>"


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
    # 첫 화면 버튼 두 개: 전화 1600-6011 · 문자 010-9926-7779 (번호를 버튼에 그대로 보인다, 2026-10-01)
    sms_disp = cfg.get("text_reply_display") or sms
    hero_btns = ('<div class="btn-row hero-btns">'
                 f'<a class="btn btn-call" href="tel:{esc(cfg["phone_tel"])}"><svg><use href="#i-phone"/></svg>전화 {esc(cfg["phone_display"])}</a>'
                 + (f'<a class="btn btn-quote" {sms_href}><svg><use href="#i-chat"/></svg>문자 {esc(sms_disp)}</a>' if sms else "")
                 + "</div>")
    return {"SMS_BUTTON": sms_btn, "KAKAO_BUTTON": kakao_btn, "BAR_SECOND": bar_second, "BAR_COLS": bar_cols, "FOOTER_BIZ": footer_biz,
            "HERO_BUTTONS": hero_btns}


def form_parts(cfg: dict, subject_region: str, region_full: str) -> dict:
    """견적 폼 자리(FORM_ACTION·FORM_METHOD·FORM_HIDDEN·REGION_FULL_NAME). 동·구 페이지가 같이 쓴다.
    Web3Forms 로 보내고, 받는 메일 제목에 어느 페이지에서 온 문의인지 보이게 한다."""
    if cfg.get("web3forms_access_key"):
        base = cfg["site_base_url"].rstrip("/")
        hidden = (
            f'<input type="hidden" name="access_key" value="{esc(cfg["web3forms_access_key"])}">'
            f'<input type="hidden" name="subject" value="{esc("[견적문의] " + subject_region)}">'
            f'<input type="hidden" name="from_name" value="폐차 견적 폼">'
            f'<input type="hidden" name="redirect" value="{base}/thanks.html">'
        )
        action, method = WEB3FORMS_URL, "POST"
    else:
        action, method, hidden = "../thanks.html", "GET", ""
    return {"FORM_ACTION": action, "FORM_METHOD": method, "FORM_HIDDEN": hidden, "REGION_FULL_NAME": esc(region_full)}


WEB3FORMS_URL = "https://api.web3forms.com/submit"

SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "전남광주통합특별시": "전남광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
    "경기도": "경기", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}


RENAMED_ON_TEXT = "2026년 7월 1일"  # renamed_on 이 없는 옛 기록용


def is_renamed(r: dict) -> bool:
    return bool(r.get("old_sido") or r.get("old_sigungu") or r.get("old_dong"))


def is_gu_split(r: dict) -> bool:
    """시 안에 구가 새로 생긴 경우(화성시 → 화성시 병점구). 이름이 바뀐 게 아니라 앞에 붙은 것이라 "(옛 …)"을 넣지 않는다."""
    old = r.get("old_sigungu")
    return bool(old and r["sigungu"].startswith(old + " "))


def date_text(iso: str) -> str:
    """'2026-02-01' → '2026년 2월 1일'."""
    y, m, d = iso.split("-")
    return f"{int(y)}년 {int(m)}월 {int(d)}일"


def old_region_name(r: dict) -> str:
    """"(옛 …)" 안에 넣을 옛 이름: 구가 바뀌면 '중구 신포동', 시도만 바뀌면 '광주광역시 동구 계림동'."""
    if r.get("old_sigungu"):
        return f"{r['old_sigungu']} {r['dong']}"
    return " ".join(x for x in (r["old_sido"], r["sigungu"], r["dong"]) if x)


def old_mark(r: dict) -> str:
    """첫 문장·설명문에 한 번 붙는 "(옛 …)". 동 이름이 바뀌면 "(옛 오산동)", 구가 새로 생긴 것뿐이면 붙이지 않는다."""
    if r.get("old_dong"):
        return f"(옛 {r['old_dong']})"
    if is_renamed(r) and not is_gu_split(r):
        return f"(옛 {old_region_name(r)})"
    return ""


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
    sents = []
    if r.get("old_sido") or r.get("old_sigungu"):
        when = date_text(r["renamed_on"]) if r.get("renamed_on") else RENAMED_ON_TEXT
        if is_gu_split(r):
            new_gu = r["sigungu"][len(r["old_sigungu"]) + 1:]
            sents.append(f"{when}부터 {r['old_sigungu']}에 {new_gu}{josa(new_gu, '이', '가')} 생겨 "
                         f"{r['dong']}{josa(r['dong'], '은', '는')} {r['sigungu']}에 속합니다.")
        else:
            old = " ".join(x for x in (r.get("old_sido") or r["sido"], r.get("old_sigungu") or r["sigungu"], r["dong"]) if x)
            new = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
            sents.append(f"{when}부터 {old}{josa(old, '은', '는')} {new}{josa(new, '이', '가')} 되었습니다.")
    if r.get("old_dong"):
        when = date_text(r["dong_renamed_on"]) if r.get("dong_renamed_on") else RENAMED_ON_TEXT
        sents.append(f"{when}부터 {r['old_dong']}{josa(r['old_dong'], '은', '는')} {r['dong']}{josa(r['dong'], '이', '가')} 되었습니다.")
    text = " ".join(sents) + " 옛 주소로 문의하셔도 됩니다."
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


_SHARED_SIGUNGU: set[str] | None = None


def shared_sigungu_names() -> set[str]:
    """전국 법정동 목록에서 두 시도 이상에 있는 시군구 이름(중구·동구·고성군 …). 우리 페이지 수와 상관없이 정해지므로
    구 페이지가 새로 생겨도 이미 있는 구 페이지 주소가 바뀌지 않는다."""
    global _SHARED_SIGUNGU
    if _SHARED_SIGUNGU is None:
        sidos: dict[str, set[str]] = {}
        for row in csv.DictReader(LEGAL_DONG_CSV.open(encoding="utf-8-sig")):
            if row["시군구"]:
                sidos.setdefault(row["시군구"], set()).add(row["시도"])
        _SHARED_SIGUNGU = {name for name, s in sidos.items() if len(s) > 1}
    return _SHARED_SIGUNGU


def gu_file(sido: str, sigungu: str) -> str:
    """구 페이지 파일 이름(한글, 2026-10-01): 종로구-폐차장.html, 용인시-처인구-폐차장.html, 세종-폐차장.html.
    같은 이름의 구가 여러 시도에 있으면 시도 줄임 이름을 앞에 붙인다(부산-중구-폐차장.html).
    gu.json 의 영문 slug 는 데이터 열쇠로 그대로 쓰고, 파일 이름만 이 함수로 정한다."""
    if not sigungu:
        name = SIDO_SHORT[sido]
    elif sigungu in shared_sigungu_names():
        name = f"{SIDO_SHORT[sido]} {sigungu}"
    else:
        name = sigungu
    return name.replace(" ", "-") + "-폐차장.html"


def gu_rel(sido: str, sigungu: str) -> str:
    """sitemap·canonical 에 쓰는 구 페이지 경로(한글은 %인코딩)."""
    return "gu/" + quote(gu_file(sido, sigungu))


# 최종 업데이트 날짜: 그 페이지 내용이 실제로 바뀐 날(한국 시간). 동·구·안내 페이지가 같이 쓴다
KST = timezone(timedelta(hours=9))
UPDATED_MARK = "@@UPDATED_ON@@"
UPDATED_ISO_MARK = "@@UPDATED_ISO@@"
UPDATED_RE = re.compile(r'(<p class="updated">최종 업데이트: )([^<]*)(</p>)')
UPDATED_ISO_RE = re.compile(r'("dateModified": ")(\d{4}-\d{2}-\d{2})(")')


def with_updated_date(new_html: str, old_html: str | None, keep_dates: bool = False) -> str:
    """내용(날짜 빼고)이 예전 파일과 같으면 예전 파일을 그대로, 다르면 오늘 날짜를 넣는다. 날짜만 새로 바꾸지 않는다.
    keep_dates(--keep-dates, 오타 수준 수정용)면 내용이 달라도 예전 파일의 날짜를 그대로 쓴다."""
    if old_html and keep_dates:
        on, iso = UPDATED_RE.search(old_html), UPDATED_ISO_RE.search(old_html)
        if on and iso:
            return new_html.replace(UPDATED_MARK, on.group(2)).replace(UPDATED_ISO_MARK, iso.group(2))
    if old_html:
        masked = UPDATED_RE.sub(lambda m: m.group(1) + UPDATED_MARK + m.group(3), old_html, count=1)
        masked = UPDATED_ISO_RE.sub(lambda m: m.group(1) + UPDATED_ISO_MARK + m.group(3), masked)
        if masked == new_html:
            return old_html
    now = datetime.now(KST)
    return (new_html.replace(UPDATED_MARK, f"{now.year}년 {now.month}월 {now.day}일")
            .replace(UPDATED_ISO_MARK, now.date().isoformat()))


def page_jsonld(name: str, url: str) -> str:
    """수정 날짜(dateModified)를 담은 WebPage 구조화 데이터. 날짜 자리는 with_updated_date 가 채운다."""
    return json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": name, "url": url,
                       "inLanguage": "ko-KR", "dateModified": UPDATED_ISO_MARK}, ensure_ascii=False)


def sido_link(sido: str, prefix: str = "../") -> str | None:
    """시·도 페이지(/si/, 2026-10-02)가 있으면 그 주소, 없으면 None."""
    from build_si import si_file, si_sidos
    return f"{prefix}si/{si_file(sido)}" if sido in si_sidos() else None


def area_links_html(regions: list[dict], gu_data: list[dict], prefix: str = "../",
                    here_dong: dict | None = None, here_gu: dict | None = None, here_si: str | None = None) -> str:
    """모든 페이지 맨 아래 지역 링크 목록(2026-10-01).
    동 페이지: 같은 구의 다른 동 + 그 구 페이지. 구 페이지: 그 시·도 페이지 + 같은 시·도의 다른 구 페이지.
    모든 페이지: 폐차 안내 5장, 시·도 16개(시·도 페이지가 있으면 그 페이지, 없으면 첫 화면의 그 시·도 칸으로 연결)."""
    from build_guide import GUIDES
    from build_index import SIDO_ORDER
    gu_keys = {(g["sido"], g["sigungu"]) for g in gu_data}
    blocks = []

    def block(title: str, links: list[tuple[str, str]]) -> str:
        items = "".join(f'<a href="{esc(h)}">{esc(lbl)}</a>' for h, lbl in links)
        return f'<h2>{esc(title)}</h2><div class="neighbors">{items}</div>'

    if here_dong:
        r = here_dong
        label = r["sigungu"] or SIDO_SHORT[r["sido"]]
        others = sorted((x for x in regions if x["sido"] == r["sido"] and x["sigungu"] == r["sigungu"] and x["slug"] != r["slug"]),
                        key=lambda x: x["dong"])
        links = [(f'{prefix}pages/{x["slug"]}.html', f'{x["dong"]} 폐차') for x in others]
        if (r["sido"], r["sigungu"]) in gu_keys:
            links.insert(0, (f'{prefix}gu/{gu_file(r["sido"], r["sigungu"])}', f"{label} 전체 폐차 상담"))
        if links:
            blocks.append(block(f"{label} 다른 동 폐차 상담", links))
    if here_gu:
        g = here_gu
        others = sorted((x for x in gu_data if x["sido"] == g["sido"] and x["slug"] != g["slug"]), key=lambda x: x["sigungu"])
        links = [(f'{prefix}gu/{gu_file(x["sido"], x["sigungu"])}', f'{x["sigungu"] or SIDO_SHORT[x["sido"]]} 폐차') for x in others]
        si_href = sido_link(g["sido"], prefix) if g["sigungu"] else None
        if si_href:
            links.insert(0, (si_href, f"{SIDO_SHORT[g['sido']]} 전체 폐차 상담"))
        if links:
            blocks.append(block(f"{SIDO_SHORT[g['sido']]} 다른 시·군·구 폐차 상담", links))
    blocks.append(block("폐차 안내", [(f"{prefix}guide/{x['file']}", x["nav"]) for x in GUIDES]))
    blocks.append(block("시·도별 폐차 상담", [(sido_link(s, prefix) or f"{prefix}index.html#sido-{SIDO_SHORT[s]}", SIDO_SHORT[s])
                                         for s in SIDO_ORDER]))
    return ('<nav class="area-links" id="area-links" aria-label="지역·안내 바로가기"><div class="wrap">'
            + "".join(blocks) + "</div></nav>")


def gu_groups(regions: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in regions:
        groups.setdefault(gu_slug(r["sido"], r["sigungu"]), []).append(r)
    return groups


def gu_title_names(groups: dict[str, list[dict]]) -> dict[str, str]:
    """구 슬러그 → 제목에 쓸 시군구 이름. 같은 이름의 구(중구·동구 …)가 여러 시도에 있으면 시도 줄임 이름을 붙인다(부산 중구)."""
    names = {slug: rs[0]["sigungu"] or SIDO_SHORT[rs[0]["sido"]] for slug, rs in groups.items()}
    count = Counter(names.values())
    return {slug: nm if count[nm] <= 1 else f"{SIDO_SHORT[groups[slug][0]['sido']]} {nm}" for slug, nm in names.items()}


def breadcrumb(r: dict, gu_pages: set[str]) -> str:
    """첫 화면 위 길 안내: 서울 › 종로구 › 청운동. 구 페이지가 있으면 구 이름에 링크(세종은 시 이름)."""
    g = gu_slug(r["sido"], r["sigungu"])
    gu_label = r["sigungu"] or SIDO_SHORT[r["sido"]]
    gu_html = f'<a href="../gu/{esc(gu_file(r["sido"], r["sigungu"]))}">{esc(gu_label)}</a>' if g in gu_pages else esc(gu_label)
    si_href = sido_link(r["sido"]) if r["sigungu"] else None
    si_html = f'<a href="{esc(si_href)}">{esc(SIDO_SHORT[r["sido"]])}</a>' if si_href else esc(SIDO_SHORT[r["sido"]])
    items = ([si_html] if r["sigungu"] else []) + [gu_html, esc(r["dong"])]
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
           combo: tuple[int, int, int] = (0, 0, 0), gu_pages: set[str] = frozenset(), gu_data: list[dict] = ()) -> str:
    full = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
    sigungu_dong = " ".join(x for x in (r["sigungu"], r["dong"]) if x)
    title_region = labels[r["slug"]]
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]

    hours = f"<p>전화 응대 {esc(cfg['hours_text'])} · 야간·주말 접수는 문자로 남겨주시면 순서대로 연락드립니다.</p>" if cfg.get("hours_text") else "<p>지금 전화 주시면 순서대로 연결됩니다. 통화가 어려우면 견적 폼으로 남겨주세요.</p>"


    # 지역 FAQ
    local_faqs = pick_local_faqs(r)
    local_faq_html = "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in local_faqs
    )
    # 공통 문장은 여러 벌 중 이 페이지에 배정된 조합(소개, FAQ, 마무리)을 쓴다 (scripts/variants.py)
    intro, closing = V.DONG_INTRO[combo[0]], V.DONG_CLOSING[combo[2]]
    # 공통 질문 4개 + 실제 통화 FAQ 풀에서 이 페이지 몫 3개(2026-10-03)
    common_faqs = list(zip(V.COMMON_FAQ_QUESTIONS, V.DONG_FAQ[combo[1]])) + V.call_faqs(r["slug"], 3)
    common_faq_html = "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in common_faqs)
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in common_faqs + local_faqs
        ],
    }

    # 사례
    c_title, c_sub, picked = cases_for(r, cases, page_map)
    cases_html = case_cards_html(picked)

    # 제목 틀 하나로 고정 (2026-10-01, docs/roadmap.md 1-2절)
    meta_title = f"{title_region} 폐차장 · 폐차 | 폐차 보상금 vs 수출 비교, 출장 견인 상담 · {phone_disp}"
    canonical = f"{base}/pages/{r['slug']}.html"
    mark = old_mark(r)
    hero_sub = f"{title_region}{mark} {intro['hero']}" if mark else intro["hero"]
    lm_html = f'<span class="landmark">{esc(r["landmark_name"])}</span>'
    # 이름 뒤 조사는 글자로 고르고, 랜드마크 이름만 강조 표시로 바꿔 끼운다
    # (fill 에 lm 을 넘기면 자리표시 글자로 조사를 골라 버리므로 {lm} 은 남겨 두고 실제 이름의 받침으로 고른다)
    lead = V.fill(intro["lead"], dong=r["dong"])
    for pair, (a, b) in (("{을를}", ("을", "를")), ("{이가}", ("이", "가")), ("{은는}", ("은", "는"))):
        lead = lead.replace("{lm}" + pair, "\x00" + V.josa(r["landmark_name"], a, b))
    lead = lead.replace("{lm}", "\x00")
    lead = esc(lead).replace("\x00", lm_html)
    if not r["landmark_name"]:  # 동 안에서 확인된 장소가 없어 랜드마크를 비워 둔 동(사실 확인 보류)은 첫 문장 없이 설명만 쓴다
        lead = ""
    parts = r.get("dong_parts") or []
    parts_note = (f'<p style="color:#5E6E70;font-size:14px">이 페이지는 {esc(parts_range(parts))}를 함께 안내합니다.</p>'
                  if parts else "")
    meta_desc = (
        f"{full}{mark} 폐차 전에 폐차 보상금과 수출 시세를 함께 비교해 드립니다. 압류·서류 없음도 상담 가능, "
        f"당일 접수, 견인비는 상담 때 미리 안내. {r['landmark_name'] or r['dong']} 인근 출장 방문. 전화 {phone_disp}"
    )

    values = {
        "META_TITLE": esc(meta_title),
        "TOW_NOTE": esc(V.TOW_NOTE[combo[1]]),
        "META_DESC": esc(meta_desc),
        "CANONICAL": canonical,
        "FAQ_JSONLD": json.dumps(faq_ld, ensure_ascii=False),
        "PAGE_JSONLD": page_jsonld(meta_title, canonical),
        "UPDATED_ON": UPDATED_MARK,
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
        "HOURS_HTML": hours,
        **form_parts(cfg, " ".join(x for x in (SIDO_SHORT[r["sido"]], r["sigungu"], r["dong"]) if x), full),
        **contact_parts(cfg, r["dong"]),
        "LOCAL_FAQ_HTML": local_faq_html,
        "AREA_LINKS": area_links_html(regions, list(gu_data), here_dong=r),
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
    ap.add_argument("--keep-dates", action="store_true", help="동 페이지 최종 업데이트·dateModified 를 예전 날짜 그대로 둠(오타 수준 수정용)")
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

    changed, created = [], []
    for r in targets:
        out_path = OUT / f"{r['slug']}.html"
        old_text = out_path.read_text(encoding="utf-8") if out_path.exists() else None
        html_text = with_updated_date(
            render(r, regions, cfg, cases, template, labels, page_map, combos[r["slug"]], gu_pages, gu_data), old_text,
            keep_dates=args.keep_dates)
        if old_text != html_text:
            out_path.write_text(html_text, encoding="utf-8")
            changed.append(r["slug"])
            if old_text is None:
                created.append(r["slug"])
            print(f"렌더링: pages/{r['slug']}.html")

    # 구 페이지(/gu/)는 동 페이지 목록에 따라 달라지므로 늘 함께 다시 만든다
    from build_gu import render_all as render_gu
    gu_changed, gu_dropped = render_gu(regions, cfg, gu_data, groups, cases)

    # 시·도 페이지(/si/, 2026-10-02): 그 시·도의 구 페이지를 모아 잇는다
    from build_si import render_all as render_si
    si_changed = render_si(regions, cfg, gu_data, cases)

    # 공통 안내 페이지(/guide/, 2026-10-01)
    from build_guide import render_all as render_guides
    guide_changed = render_guides(regions, cfg, gu_data)

    # 사례 페이지(/cases/)도 동·구 페이지 목록에 따라 "○○동 상담 페이지"·"○○구 상담 페이지" 버튼이 달라지므로 함께 다시 만든다
    from build_cases import render_all_cases
    case_changed = render_all_cases(regions, cfg)

    # 내용이 실제로 바뀐 페이지만 sitemap 의 수정일을 갱신한다(--keep-dates 면 새로 만든 동 페이지만 넣고 기존 수정일은 그대로)
    update_sitemap(ROOT, created if args.keep_dates else changed, paths=gu_changed + si_changed + guide_changed + case_changed, drop=gu_dropped)
    print(f"완료: {len(targets)}개 중 {len(changed)}개 페이지 변경, 구 페이지 {len(gu_changed)}개, 시·도 페이지 {len(si_changed)}개 변경, "
          f"안내 페이지 {len(guide_changed)}개 변경, sitemap.xml 갱신")


if __name__ == "__main__":
    main()
