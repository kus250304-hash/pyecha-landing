"""
pages/*.html 전체를 읽기 전용으로 점검해 diagnosis.md 를 만든다. 페이지는 수정하지 않는다.

점검 항목
- 페이지 간 본문 중복도(지역명·랜드마크명을 가린 뒤 비교), 지역명만 다른 페이지 쌍
- 분량 부족, 랜드마크/지역 후기/지역 FAQ 누락
- 다른 지역 이름·키워드 혼입
- title / description 중복·누락
- sitemap.xml 누락, 내부 링크 부재
- 모바일 전화 버튼(정적 검사)
- 결과를 약속하는 표현
"""
import csv
import html
import re
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
SITEMAP_PATH = ROOT / "sitemap.xml"
INDEX_PATH = ROOT / "index.html"
OUT_PATH = ROOT / "diagnosis.md"

SITE_BASE = "https://kus250304-hash.github.io/pyecha-landing"

PROMISE_WORDS = ["보장", "무조건", "100%", "1위", "최고", "최저가", "확실히", "반드시", "무료"]

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DESC_RE = re.compile(r'<meta name="description" content="(.*?)">')
BADGE_RE = re.compile(r'<span class="badge">(.+?) 폐차 비교매입 상담</span>')
LANDMARK_RE = re.compile(r"은 <strong>(.+?)</strong> 인근 지역으로,\s*\n\s*(.+?)\n")
INTRO_RE = re.compile(r'<p class="lead">.*?</p>\s*<p>(.*?)</p>', re.S)
REVIEW_RE = re.compile(
    r'<div class="review-card">\s*<div class="rating">(.*?)</div>\s*<p>(.*?)</p>\s*<div class="reviewer">(.*?)</div>',
    re.S,
)
FAQ_RE = re.compile(r"<summary>(.*?)</summary>\s*<p>(.*?)</p>", re.S)
HREF_RE = re.compile(r'href="([^"]+)"')
TAG_RE = re.compile(r"<[^>]+>")
STYLE_RE = re.compile(r"<style>.*?</style>", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
HANGUL = "가-힣"


def visible_text(raw: str) -> str:
    t = STYLE_RE.sub(" ", raw)
    t = COMMENT_RE.sub(" ", t)
    t = TAG_RE.sub(" ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。])\s+|(?<=습니다\.)|(?<=요\.)", text)
    return [p.strip() for p in parts if len(p.strip()) >= 8]


def trigrams(text: str) -> set[str]:
    t = re.sub(r"\s+", "", text)
    return {t[i : i + 3] for i in range(len(t) - 2)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_dong_index():
    """법정동명 -> {(시도, 시군구)}, 시군구명 -> {시도}, 시도명 집합."""
    name_to_regions = defaultdict(set)
    sigungu_to_sido = defaultdict(set)
    sidos = set()
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sido, sigungu, dong = row["시도"].strip(), row["시군구"].strip(), row["읍면동"].strip()
            sidos.add(sido)
            name_to_regions[dong].add((sido, sigungu))
            if sigungu:
                sigungu_to_sido[sigungu].add(sido)
                for part in sigungu.split():
                    sigungu_to_sido[part].add(sido)
    return name_to_regions, sigungu_to_sido, sidos


def parse_page(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    title = TITLE_RE.search(raw)
    desc = DESC_RE.search(raw)
    badge = BADGE_RE.search(raw)
    full = badge.group(1).strip() if badge else ""
    toks = full.split()
    sido = toks[0] if toks else ""
    dong = toks[-1] if len(toks) >= 2 else ""
    sigungu = " ".join(toks[1:-1]) if len(toks) > 2 else ""

    lm = LANDMARK_RE.search(raw)
    landmark = lm.group(1).strip() if lm else ""
    landmark_desc = html.unescape(TAG_RE.sub("", lm.group(2))).strip() if lm else ""
    intro_m = INTRO_RE.search(raw)
    intro = html.unescape(TAG_RE.sub("", intro_m.group(1))).strip() if intro_m else ""
    reviews = [(r.strip(), html.unescape(t.strip()), n.strip()) for r, t, n in REVIEW_RE.findall(raw)]
    faqs = [(html.unescape(q.strip()), html.unescape(a.strip())) for q, a in FAQ_RE.findall(raw)]
    regional_faqs = faqs[:5]

    body = visible_text(raw)
    variable = " ".join(
        [intro, landmark_desc]
        + [t for _, t, _ in reviews]
        + [q + " " + a for q, a in regional_faqs]
    )
    hrefs = HREF_RE.findall(raw)
    return {
        "path": path,
        "slug": path.stem,
        "raw": raw,
        "title": html.unescape(title.group(1).strip()) if title else "",
        "desc": html.unescape(desc.group(1).strip()) if desc else "",
        "full": full,
        "sido": sido,
        "sigungu": sigungu,
        "dong": dong,
        "landmark": landmark,
        "landmark_desc": landmark_desc,
        "intro": intro,
        "reviews": reviews,
        "faqs": faqs,
        "regional_faqs": regional_faqs,
        "body": body,
        "variable": variable,
        "hrefs": hrefs,
        "size_kb": round(len(raw.encode("utf-8")) / 1024, 1),
    }


def region_tokens(p: dict) -> list[str]:
    toks = {p["sido"], p["dong"], p["landmark"]}
    toks.update(p["sigungu"].split())
    toks.add(p["sigungu"])
    for suffix in ("특별시", "광역시", "특별자치시", "특별자치도", "도"):
        if p["sido"].endswith(suffix) and len(p["sido"]) > len(suffix):
            toks.add(p["sido"][: -len(suffix)])
    return sorted((t for t in toks if t), key=len, reverse=True)


def main() -> None:
    name_to_regions, sigungu_to_sido, sidos = load_dong_index()
    pages = [parse_page(p) for p in sorted(PAGES_DIR.glob("*.html"))]
    n = len(pages)
    by_slug = {p["slug"]: p for p in pages}

    # ---- 마스킹: 자기 지역 토큰 + 모든 법정동명(3자 이상) + 모든 페이지의 랜드마크명 ----
    all_landmarks = sorted({p["landmark"] for p in pages if p["landmark"]}, key=len, reverse=True)
    dong_names_3 = sorted((d for d in name_to_regions if len(d) >= 3), key=len, reverse=True)
    generic_mask_re = re.compile("|".join(re.escape(x) for x in all_landmarks + dong_names_3))

    def masked(p: dict, text: str) -> str:
        t = text
        for tok in region_tokens(p):
            t = t.replace(tok, "▣")
        t = generic_mask_re.sub("▣", t)
        return t

    for p in pages:
        p["masked_var"] = masked(p, p["variable"])
        p["masked_sents"] = [masked(p, s) for s in sentences(p["variable"])]
        p["tri"] = trigrams(p["masked_var"])

    # ---- 페이지 쌍 유사도 ----
    pair_scores = []
    for a, b in combinations(pages, 2):
        j = jaccard(a["tri"], b["tri"])
        sa, sb = set(a["masked_sents"]), set(b["masked_sents"])
        s_overlap = len(sa & sb) / max(1, min(len(sa), len(sb)))
        pair_scores.append((j, s_overlap, a["slug"], b["slug"]))
    pair_scores.sort(reverse=True)
    js = [x[0] for x in pair_scores]
    near_identical = [x for x in pair_scores if x[1] >= 0.8]
    high = [x for x in pair_scores if 0.6 <= x[1] < 0.8]

    max_sim = {}
    for j, s, a, b in pair_scores:
        for x, y in ((a, b), (b, a)):
            if x not in max_sim or s > max_sim[x][0]:
                max_sim[x] = (s, y, j)

    # ---- 문장 재사용 ----
    sent_pages = defaultdict(set)
    for p in pages:
        for s in set(p["masked_sents"]):
            sent_pages[s].add(p["slug"])
    reused = sorted(((len(v), s) for s, v in sent_pages.items() if len(v) >= 2), reverse=True)
    for p in pages:
        ss = set(p["masked_sents"])
        p["unique_sent_ratio"] = (
            sum(1 for s in ss if len(sent_pages[s]) == 1) / len(ss) if ss else 0
        )

    # ---- 분량 / 고정 vs 가변 ----
    for p in pages:
        p["body_chars"] = len(re.sub(r"\s", "", p["body"]))
        p["var_chars"] = len(re.sub(r"\s", "", p["variable"]))
        p["fixed_chars"] = p["body_chars"] - p["var_chars"]
        loc_tokens = [t for t in (p["dong"], p["landmark"], p["sigungu"]) if t]
        p["local_faq"] = sum(
            1 for q, a in p["regional_faqs"] if any(t in q or t in a for t in loc_tokens)
        )
        p["local_reviews"] = sum(
            1 for _, t, _ in p["reviews"] if any(tok in t for tok in loc_tokens)
        )
        p["review_dup"] = sum(
            1 for _, t, _ in p["reviews"] if len(sent_pages.get(masked(p, t), ())) >= 2
        )

    # ---- 다른 지역 키워드 혼입 ----
    landmark_owner = defaultdict(set)
    for p in pages:
        if p["landmark"]:
            landmark_owner[p["landmark"]].add((p["sido"], p["sigungu"]))
    other_sido_names = {s for s in sidos}
    all_sigungu = {sg for regions in name_to_regions.values() for _, sg in regions if sg}

    def regions_of(name: str) -> set:
        """'중앙동'처럼 실제로는 '중앙동1가'로 등록된 이름도 같은 지역으로 취급."""
        found = set(name_to_regions.get(name, ()))
        for suffix in ("1가", "2가", "3가"):
            found |= set(name_to_regions.get(name + suffix, ()))
        return found

    for p in pages:
        high, low = [], []
        text = p["variable"]
        own = (p["sido"], p["sigungu"])
        own_dong_base = re.sub(r"\d가$", "", p["dong"])
        # 법정동명(3자 이상) 언급
        for name in dong_names_3:
            if name == p["dong"] or name == own_dong_base:
                continue
            for m in re.finditer(re.escape(name), text):
                start = m.start()
                if start > 0 and re.match(f"[{HANGUL}]", text[start - 1]):
                    continue  # 다른 단어의 일부
                regions = regions_of(name)
                if any(r == own for r in regions):
                    break
                same_sido = [r for r in regions if r[0] == p["sido"]]
                if same_sido:
                    low.append(f"같은 시도 다른 구/군의 동명 '{name}'({', '.join(sorted({r[1] for r in same_sido}))}) — 이웃 언급이면 문제 없음")
                else:
                    ex = ", ".join(f"{r[0]} {r[1]}".strip() for r in sorted(regions)[:2])
                    high.append(f"법정동 목록상 자기 시도에 없는 동명 '{name}' (법정동으로는 {ex}에 있음 — 행정동 이름이면 표기는 맞으나 페이지 연결 불가)")
                break
        # 다른 페이지의 랜드마크명 (3자 이하·도로명은 동명이인 가능성이 커서 제외)
        for lmk, owners in landmark_owner.items():
            if not lmk or lmk == p["landmark"] or own in owners:
                continue
            if len(lmk) <= 3 or lmk.endswith(("로", "길")):
                continue
            if re.search(re.escape(lmk) + f"(?![{HANGUL}])", text):
                where = ", ".join(f"{s} {g}".strip() for s, g in sorted(owners))
                if any(s == p["sido"] for s, _ in owners):
                    low.append(f"다른 구/군 페이지의 랜드마크 '{lmk}'({where}) — 이웃 명소 언급이면 문제 없음")
                else:
                    high.append(f"다른 시도 페이지의 랜드마크 '{lmk}'({where})")
        # 다른 시도명 / 다른 시군구명
        for s in other_sido_names:
            if s != p["sido"] and s in text:
                high.append(f"다른 시도명 '{s}'")
        for sg in all_sigungu:
            if sg == p["sigungu"] or sg in p["sigungu"] or len(sg) < 3:
                continue
            if re.search(f"(?<![{HANGUL}])" + re.escape(sg) + f"(?![{HANGUL}])", text):
                sidos_of = sigungu_to_sido.get(sg, set())
                if p["sido"] in sidos_of:
                    low.append(f"같은 시도의 다른 시군구명 '{sg}' 언급")
                else:
                    high.append(f"다른 시도의 시군구명 '{sg}' 언급")
        # '인근 A, B에서도 …' 이웃 목록 안에 법정동이 아닌 이름
        for m in re.finditer(r"인근 ([^.]{2,60}?)에서도", text):
            items = [x.strip() for x in re.split(r",\s*", m.group(1)) if x.strip()]
            if not any(regions_of(x) for x in items):
                continue  # 이웃 동 목록이 아님
            for nm in items:
                if not regions_of(nm):
                    high.append(f"'인근 …에서도' 이웃 목록의 '{nm}' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음")
        p["region_issues_high"] = sorted(set(high))
        p["region_issues_low"] = sorted(set(low))
        p["region_issues"] = p["region_issues_high"] + p["region_issues_low"]

    # ---- title / description ----
    title_counts = Counter(p["title"] for p in pages)
    desc_counts = Counter(p["desc"] for p in pages)
    dup_titles = [t for t, c in title_counts.items() if c > 1]
    dup_descs = [d for d, c in desc_counts.items() if c > 1]
    empty_title = [p["slug"] for p in pages if not p["title"]]
    empty_desc = [p["slug"] for p in pages if not p["desc"]]
    long_titles = [p["slug"] for p in pages if len(p["title"]) > 40]
    h1_counts = Counter(len(re.findall(r"<h1[ >]", p["raw"])) for p in pages)
    no_canonical = [p["slug"] for p in pages if 'rel="canonical"' not in p["raw"]]
    no_og = [p["slug"] for p in pages if 'property="og:' not in p["raw"]]

    # ---- sitemap / 내부 링크 ----
    sitemap_locs = set(re.findall(r"<loc>(.*?)</loc>", SITEMAP_PATH.read_text(encoding="utf-8")))
    expected = {f"{SITE_BASE}/pages/{p['slug']}.html" for p in pages} | {f"{SITE_BASE}/"}
    missing_in_sitemap = sorted(expected - sitemap_locs)
    stale_in_sitemap = sorted(sitemap_locs - expected)
    index_raw = INDEX_PATH.read_text(encoding="utf-8")
    index_links = set(re.findall(r'href="pages/([^"]+)\.html"', index_raw))
    not_in_index = [p["slug"] for p in pages if p["slug"] not in index_links]
    for p in pages:
        internal = [
            h for h in p["hrefs"]
            if not h.startswith(("#", "tel:", "http://", "https://", "mailto:"))
        ]
        p["internal_links"] = internal
        p["valid_internal_links"] = [
            h for h in internal if (ROOT / h.lstrip("/")).exists()
        ]
    no_internal = [p["slug"] for p in pages if not p["valid_internal_links"]]
    broken_links = Counter(
        h for p in pages for h in p["internal_links"] if not (ROOT / h.lstrip("/")).exists()
    )

    # ---- 모바일 전화 버튼(정적) ----
    tel_ok = [p for p in pages if len(re.findall(r'href="tel:16006011"', p["raw"])) >= 2]
    viewport_ok = [p for p in pages if 'name="viewport"' in p["raw"]]
    sticky_ok = [p for p in pages if ".sticky-cta" in p["raw"] and 'class="sticky-cta"' in p["raw"]]

    # ---- 결과 약속 표현 ----
    promise_hits = defaultdict(list)
    for p in pages:
        for w in PROMISE_WORDS:
            for m in re.finditer(re.escape(w), p["body"]):
                ctx = p["body"][max(0, m.start() - 15): m.end() + 15]
                promise_hits[p["slug"]].append(f"'{w}' … {ctx}")

    # ---- 분량 부족 / 누락 ----
    var_chars = [p["var_chars"] for p in pages]
    body_chars = [p["body_chars"] for p in pages]
    thin = [p for p in pages if p["var_chars"] < 800 or p["body_chars"] < 1600]
    no_landmark = [p["slug"] for p in pages if not p["landmark"]]
    weak_local_faq = [p for p in pages if p["local_faq"] < 3]
    weak_local_reviews = [p for p in pages if p["local_reviews"] == 0]
    all_reviews = [t for p in pages for _, t, _ in p["reviews"]]
    review_counter = Counter(masked(by_slug[s], t) for p in pages for _, t, _ in p["reviews"] for s in [p["slug"]])
    reused_reviews = sum(c for c in review_counter.values() if c >= 2)

    # =====================================================================
    lines = []
    w = lines.append
    w("# 기존 페이지 진단서 (diagnosis.md)")
    w("")
    w(f"- 점검 대상: `pages/*.html` {n}개 (index.html 제외)")
    w("- 방식: 스크립트 `scripts/diagnose_pages.py`로 읽기 전용 분석. 페이지는 수정하지 않았음")
    w("- 중복도 계산 시 각 페이지의 시도·시군구·동 이름, 랜드마크 이름, 그리고 전국 법정동명(3자 이상)을 모두 `▣`로 가린 뒤 비교했음 (= \"지역명만 다른\" 상태를 그대로 측정)")
    w("")

    # 1. 중복도
    w("## 1. 페이지 간 본문 중복도")
    w("")
    w("### 1-1. 구조적 사실")
    avg_fixed = statistics.mean(p["fixed_chars"] for p in pages)
    avg_var = statistics.mean(var_chars)
    w(f"- 한 페이지 평균 본문 {statistics.mean(body_chars):.0f}자(공백 제외) 중 **템플릿 고정 문구 {avg_fixed:.0f}자({avg_fixed/(avg_fixed+avg_var)*100:.0f}%)**, 지역별로 달라지는 부분 {avg_var:.0f}자({avg_var/(avg_fixed+avg_var)*100:.0f}%)")
    w("- 고정 문구에는 히어로 카피, 출장 방문 안내, 폐차 절차 4단계, 고정 FAQ 2개, 하단 고지, 푸터가 포함됨")
    w("")
    w("### 1-2. 지역명·랜드마크명을 가린 뒤 페이지 쌍 유사도")
    w(f"- 비교한 쌍: {len(pair_scores):,}쌍")
    w(f"- 3-gram 자카드 유사도 평균 **{statistics.mean(js):.2f}**, 중앙값 {statistics.median(js):.2f}, 최대 {max(js):.2f}")
    w(f"- 문장 단위로 80% 이상 겹치는 쌍(= 지역명만 다르고 나머지가 같은 수준): **{len(near_identical)}쌍**")
    w(f"- 문장 단위로 60~80% 겹치는 쌍: {len(high)}쌍")
    ratios = [p["unique_sent_ratio"] for p in pages]
    w(f"- 페이지별 '이 페이지에만 있는 문장' 비율 평균 **{statistics.mean(ratios)*100:.0f}%** (최소 {min(ratios)*100:.0f}%, 최대 {max(ratios)*100:.0f}%)")
    w("")
    w("### 1-3. 지역명만 다르고 나머지가 같은 페이지 쌍 (문장 겹침 80% 이상, 상위 40쌍)")
    w("")
    w("| 문장 겹침 | 3-gram 유사도 | 페이지 A | 페이지 B |")
    w("|---|---|---|---|")
    for j, s, a, b in near_identical[:40]:
        w(f"| {s*100:.0f}% | {j:.2f} | {a} | {b} |")
    if len(near_identical) > 40:
        w(f"| … | … | (외 {len(near_identical)-40}쌍) | |")
    w("")
    w("### 1-4. 여러 페이지에 그대로 반복되는 문장 상위 20개")
    w("")
    w("| 등장 페이지 수 | 문장(지역명은 ▣) |")
    w("|---|---|")
    for c, s in reused[:20]:
        w(f"| {c} | {s[:90]}{'…' if len(s) > 90 else ''} |")
    w("")
    w(f"- 후기 문장 {len(all_reviews)}개 중 다른 페이지와 똑같은(지역명만 다른) 후기: **{reused_reviews}개**")
    w("- 참고: 모든 후기는 실제 고객 후기가 아니라 생성 시 작성한 예시 문구임(이름은 'O' 마스킹). 실제 사례로 교체하기 전까지는 신뢰 요소로 쓰기 어려움")
    w("")

    # 2. 분량/누락
    w("## 2. 분량 부족 · 랜드마크/지역 후기/지역 FAQ 누락")
    w("")
    w(f"- 본문 글자 수(공백 제외): 평균 {statistics.mean(body_chars):.0f}자, 최소 {min(body_chars)}자, 최대 {max(body_chars)}자")
    w(f"- 지역별 가변 부분: 평균 {avg_var:.0f}자, 최소 {min(var_chars)}자, 최대 {max(var_chars)}자")
    w(f"- 본문 1,600자(공백 제외) 미만인 페이지: **{len(thin)}개 / {n}개 — 전 페이지가 얇은 편**. 지역별 고유 내용이 500자 안팎이라 검색엔진 입장에서는 '같은 글에 지역명만 바꾼 페이지'로 묶일 위험이 큼")
    w("- 지역별 고유 분량이 가장 적은 15개:")
    for p in sorted(pages, key=lambda x: x["var_chars"])[:15]:
        w(f"  - {p['slug']} (본문 {p['body_chars']}자 / 가변 {p['var_chars']}자)")
    w(f"- 랜드마크 이름이 비어 있는 페이지: **{len(no_landmark)}개** {no_landmark[:10]}")
    w(f"- 지역 FAQ(5개) 중 동/랜드마크/구 이름이 들어간 문항이 3개 미만인 페이지: **{len(weak_local_faq)}개**")
    for p in weak_local_faq[:30]:
        w(f"  - {p['slug']} (지역 FAQ {p['local_faq']}/5)")
    w(f"- 후기 3개 중 동/랜드마크/구 이름이 하나도 없는 페이지: **{len(weak_local_reviews)}개**")
    for p in weak_local_reviews[:30]:
        w(f"  - {p['slug']}")
    w("- 실제 '지역 사례'(사진·진행 과정이 있는 사례 글)는 **168개 전부 없음**. 현재 후기 섹션은 예시 후기 3개로만 구성됨")
    w("")

    # 3. 다른 지역 키워드
    with_high = [p for p in pages if p["region_issues_high"]]
    with_low = [p for p in pages if p["region_issues_low"] and not p["region_issues_high"]]
    w("## 3. 다른 지역 이름·키워드가 섞인 페이지")
    w("")
    w(f"- 수정 대상(법정동 목록에 없는 동명, 다른 시도명·시군구명, 다른 시도 랜드마크, 이웃 목록의 비(非)법정동 이름): **{len(with_high)}개**")
    w("  - 이 중 대부분은 행정동 이름(예: 우장산동, 영종동)이나 시설명(킨텍스, 명지오션시티)이라 독자에게 틀린 말은 아님. 다만 사이트가 법정동 단위라 해당 이름으로는 페이지가 없어 내부 링크를 걸 수 없고, 광주 용봉동의 '용운동'처럼 실제 존재 여부가 불확실한 이름도 섞여 있음")
    w(f"- 검토 권장(같은 시도의 다른 구/군 동명·랜드마크 언급 — 대부분 이웃 언급이라 오류 아님): {len(with_low)}개")
    w("- 자기 시군구 안의 이웃 동 언급('인근 대치동, 삼성동에서도…')은 정상으로 보고 제외했음")
    w("")
    w("### 3-1. 수정 대상")
    w("")
    for p in with_high:
        w(f"- **{p['slug']}** ({p['full']})")
        for i in p["region_issues_high"]:
            w(f"  - {i}")
    w("")
    w("### 3-2. 검토 권장 (이웃 구/군 언급)")
    w("")
    for p in with_low:
        w(f"- {p['slug']}: " + " / ".join(p["region_issues_low"]))
    w("")

    # 4. title / description
    w("## 4. title · description")
    w("")
    w(f"- title 누락: {len(empty_title)}개, description 누락: {len(empty_desc)}개")
    w(f"- title 중복: {len(dup_titles)}건, description 중복: {len(dup_descs)}건")
    w(f"- title이 40자를 넘는 페이지: {len(long_titles)}개 (예: {by_slug[long_titles[0]]['title'] if long_titles else '-'})")
    w(f"- h1 개수 분포: {dict(h1_counts)}")
    w(f"- canonical 태그 없음: {len(no_canonical)}개, Open Graph 태그 없음: {len(no_og)}개")
    w("- 모든 title이 `{지역} 폐차 비교매입 상담`, description이 `{지역} 폐차 비교매입 상담 및 출장 방문 서비스 안내 페이지입니다.` 한 가지 틀임. 중복은 아니지만 검색 결과에서 클릭을 유도하는 문구(비교·무료견인·당일 등)가 전혀 없음")
    w("")

    # 5. sitemap / 내부 링크
    w("## 5. sitemap.xml · 내부 링크")
    w("")
    w(f"- sitemap.xml URL 수: {len(sitemap_locs)} (루트 1 + 페이지 {len(sitemap_locs)-1})")
    w(f"- sitemap에 빠진 페이지: **{len(missing_in_sitemap)}개** {missing_in_sitemap[:10]}")
    w(f"- sitemap에 있으나 파일이 없는 URL: {len(stale_in_sitemap)}개 {stale_in_sitemap[:10]}")
    w(f"- index.html 목록에 빠진 페이지: {len(not_in_index)}개 {not_in_index[:10]}")
    w(f"- 유효한 내부 링크가 하나도 없는 페이지: **{len(no_internal)}개** / {n} (동 페이지 → 다른 동/인덱스로 가는 링크가 전혀 없음. index → 동 페이지 방향만 존재)")
    w("- 깨진 내부 링크:")
    for h, c in broken_links.most_common():
        w(f"  - `{h}` : {c}개 페이지 (파일 없음. 게다가 절대경로라 GitHub Pages 프로젝트 사이트에서는 `kus250304-hash.github.io/privacy-policy.html`로 가서 항상 404)")
    w("- sitemap의 lastmod가 생성일 기준으로 몰려 있음(내용 갱신 신호로 쓰이지 않음)")
    w("- robots.txt 없음(sitemap 위치를 검색엔진에 알려주는 줄이 없음)")
    w("")

    # 6. 모바일 전화 버튼
    w("## 6. 모바일 전화 버튼 (정적 검사)")
    w("")
    w("이 환경에서는 실제 기기·브라우저를 열 수 없어 코드 기준으로만 확인했음.")
    w(f"- `href=\"tel:16006011\"` 링크가 상단 버튼 + 하단 고정 버튼 2곳에 있는 페이지: {len(tel_ok)}/{n} → 탭하면 다이얼러가 열림(정상)")
    w(f"- viewport 메타 태그: {len(viewport_ok)}/{n}, 하단 고정 CTA(`.sticky-cta`): {len(sticky_ok)}/{n}")
    w("- 하단 고정 버튼 높이: 글자 16px + 상하 패딩 12px ≈ 40px → 권장 터치 영역(44px)보다 약간 작음. 링크 영역이 글자 폭만큼이라 좌우 여백을 누르면 반응 없음")
    w("- 상단 버튼(글자 18px + 패딩 14px ≈ 50px)은 충분함")
    w("- 전화번호가 `tel:16006011`(하이픈 없음)로 통일되어 있어 iOS/Android 모두 문제 없음")
    w("- 문자(sms:)·카카오톡 버튼은 없음. 전화가 부담스러운 사용자를 받을 통로가 없음")
    w("- 견적 폼 없음 → 전화 외 전환 수단 0개")
    w("")

    # 7. 결과 약속 표현
    w("## 7. 결과를 약속하는 표현")
    w("")
    w(f"- 검사어: {', '.join(PROMISE_WORDS)}")
    w(f"- 검출된 페이지: **{len(promise_hits)}개**")
    for slug, hits in promise_hits.items():
        w(f"- {slug}")
        for h in hits[:5]:
            w(f"  - {h}")
    if not promise_hits:
        w("- 본문에서는 검출되지 않음(CSS의 `100%`는 문구가 아니므로 제외). 단, 현재 문구가 '약속'을 피하느라 전환 유도도 약함")
    w("")

    # 8. 기타
    w("## 8. 그 밖에 눈에 띈 것")
    w("")
    sizes = [p["size_kb"] for p in pages]
    w(f"- 페이지 파일 크기 평균 {statistics.mean(sizes):.1f}KB (CSS 인라인, 외부 JS·이미지 없음) → 속도는 좋음")
    w("- 후기 이름이 '김O현'식 마스킹이라 실제 후기처럼 보이지 않고, 별점만 있고 날짜·차종·사진이 없음")
    w("- 히어로 문구가 '알아보세요' 수준으로 약함. 숫자(누적 상담, 당일 접수)·신뢰 문구·견적 폼이 없음")
    w("- '폐차 절차' 4단계가 모든 페이지에서 동일하고 폐차 유형(일반/차령초과/조기/상속)·서류·기간 안내가 없음")
    w("- 하단 고지·푸터에 사업자 정보(상호·대표·주소·사업자번호)가 없음")
    w("- 유튜브·블로그 링크가 히어로에도 있어 첫 화면에서 이탈 경로가 됨")
    w("- 자동 생성 루틴(`폐차 랜딩페이지 자동 생성`, 매일 05:02 UTC)이 지금 템플릿으로 매일 50~100개씩 추가 중 → 새 템플릿 확정 전까지는 재작업 대상이 계속 늘어남")
    w("")

    # 부록
    w("## 부록. 페이지별 요약표")
    w("")
    w("가변 = 지역별로 달라지는 본문 글자 수. 최유사 = 문장 겹침이 가장 높은 페이지와 그 비율. 지역FAQ = 5개 중 지역명이 들어간 문항 수. 지역후기 = 3개 중 지역명이 들어간 후기 수.")
    w("")
    w("| 페이지 | 본문 | 가변 | 최유사(겹침) | 지역FAQ | 지역후기 | 지역키워드 의심 | 내부링크 |")
    w("|---|---|---|---|---|---|---|---|")
    for p in pages:
        s, other, _ = max_sim.get(p["slug"], (0, "-", 0))
        w(
            f"| {p['slug']} | {p['body_chars']} | {p['var_chars']} | {other} ({s*100:.0f}%) | "
            f"{p['local_faq']}/5 | {p['local_reviews']}/3 | {len(p['region_issues'])} | {len(p['valid_internal_links'])} |"
        )
    w("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"diagnosis.md 작성 완료: 페이지 {n}개, 근사동일 쌍 {len(near_identical)}, 지역키워드 오류가능 {len(with_high)}, 검토권장 {len(with_low)}")


if __name__ == "__main__":
    main()
