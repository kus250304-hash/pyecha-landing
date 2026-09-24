"""
렌더링된 pages/*.html 과 data/regions.json 을 검사한다. 자동 생성 루틴은 이 검사를 통과해야 PR을 올린다.

사용법
  python3 scripts/check_pages.py                  # 전체
  python3 scripts/check_pages.py --only a,b,c     # 지정 슬러그만 (경고도 오류로 취급하는 엄격 모드)

오류
  - 템플릿 자리({{...}}) 잔여, 필수 요소 누락(전화·문자 링크, 문제차 섹션, Jalnan, 전화번호 하이픈,
    하단 고정 바, 협력업체 고지, 서비스 가능 지역 문구, canonical, FAQ 구조화 데이터)
  - 결과를 약속하는 표현(보장/무조건/100%/1위/최저가)
  - title/description 중복, sitemap 누락
  - 지역 데이터: 빈 칸, 너무 짧은 문구, FAQ 4개 미만, code 없음, 다른 시도 이름 등장
경고 (--only 대상에서는 오류)
  - 다른 시도에만 있는 시군구/동 이름이 지역 문구에 등장
  - 해당 동·랜드마크 이름이 들어간 FAQ가 3개 미만
  - 다른 시도의 줄임 이름(부산, 경기 등)이 지역 문구에 등장
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"
REGIONS_PATH = ROOT / "data" / "regions.json"
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
SITE_CONFIG_PATH = ROOT / "data" / "site_config.json"
SITEMAP_PATH = ROOT / "sitemap.xml"

PROMISE_RE = re.compile(r"보장|무조건|100%|1위|최저가")
PLACEHOLDER_RE = re.compile(r"\{\{\w+\}\}")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")
REQUIRED = [
    ('href="tel:', "전화 링크"),
    ('id="problem-cars"', "문제차 상담 섹션"),
    ("Jalnan", "Jalnan 글꼴"),
    ("function formatPhone", "전화번호 하이픈 스크립트"),
    ('class="bar"', "하단 고정 바"),
    ("협력업체 네트워크와 함께합니다", "협력업체 고지"),
    ("실제 출장 방문이 가능한 지역", "서비스 가능 지역 문구"),
    ('rel="canonical"', "canonical"),
    ('"FAQPage"', "FAQ 구조화 데이터"),
]
SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북",
    "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}  # 광주는 경기도 광주시와 겹쳐 제외


def base_name(dong: str) -> str:
    return re.sub(r"\d+가$", "", dong)


def region_text(r: dict) -> str:
    return " ".join([r.get("landmark_name", ""), r.get("landmark_desc", ""), r.get("service_intro", ""),
                     r.get("meta", "")] + [q + " " + a for q, a in r.get("faqs", [])])


# 단어 첫머리에서 시작하는 장소 이름만 잡는다 (지역으로/이면도로 같은 일반 단어 제외)
PLACE_RE = re.compile(
    r"(?<![가-힣])(?:[가-힣A-Za-z0-9]{2,4}?(?:역|공원|시장|대로|대교|사거리|오거리|백화점|대학교|대학|호수|거리|마을|지구|"
    r"캠퍼스|터미널|광장|성곽|해수욕장)|[가-힣]{2}(?:천|강|산|교|궁|항|로|길))"
)
SIDO_SHORT_TAIL = r"(?=[\s,·]|과|와|의|에|로|까지|에서|이|가|은|는|도)"  # 서울대공원·서울숲 같은 고유명사는 제외


def own_tokens(r: dict) -> set[str]:
    toks = {r["dong"], base_name(r["dong"])}
    toks.update(r["sigungu"].split())
    # "한남대교와 유엔빌리지", "강남구청·가구거리" 처럼 묶인 랜드마크는 낱개로 나눠 센다
    for part in re.split(r"[\s·,/()]+", r.get("landmark_name", "")):
        part = re.sub(r"(와|과)$", "", part)
        if len(part) >= 2:
            toks.add(part)
    # 지역 설명에 나온 장소 이름(서리풀공원, 천호대로, 월정교 …)을 언급한 FAQ 도 지역 FAQ 로 친다
    for m in PLACE_RE.finditer(r.get("landmark_desc", "") + " " + r.get("service_intro", "")):
        toks.add(m.group(0))
    return {t for t in toks if t}


def load_name_index() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """시군구 토큰/동 이름(3글자 이상) → 그 이름이 있는 시도 집합"""
    sigungu_sidos: dict[str, set[str]] = defaultdict(set)
    dong_sidos: dict[str, set[str]] = defaultdict(set)
    for row in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")):
        for tok in row["시군구"].split():
            if len(tok) >= 3:
                sigungu_sidos[tok].add(row["시도"])
        if len(row["읍면동"]) >= 3:
            dong_sidos[row["읍면동"]].add(row["시도"])
    return sigungu_sidos, dong_sidos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="쉼표로 구분한 슬러그 목록 (엄격 모드)")
    args = ap.parse_args()

    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    site_cfg = json.loads(SITE_CONFIG_PATH.read_text(encoding="utf-8"))
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8") if SITEMAP_PATH.exists() else ""
    sigungu_sidos, dong_sidos = load_name_index()
    all_sidos = set(SIDO_SHORT) | {"광주광역시"}

    strict = bool(args.only)
    only = {s.strip() for s in args.only.split(",") if s.strip()} if args.only else None
    targets = [r for r in regions if only is None or r["slug"] in only]
    if only:
        missing = only - {r["slug"] for r in targets}
        if missing:
            print(f"regions.json 에 없는 슬러그: {sorted(missing)}")
            sys.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    def warn(msg: str) -> None:
        (errors if strict else warnings).append(msg)

    # 전체 페이지 기준 title/description 중복 (대상 밖 페이지와 겹쳐도 잡는다)
    titles: dict[str, list[str]] = defaultdict(list)
    descs: dict[str, list[str]] = defaultdict(list)
    for r in regions:
        p = PAGES_DIR / f"{r['slug']}.html"
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        m = re.search(r"<title>(.*?)</title>", t)
        d = re.search(r'<meta name="description" content="(.*?)">', t)
        titles[m.group(1) if m else ""].append(r["slug"])
        descs[d.group(1) if d else ""].append(r["slug"])
    target_slugs = {r["slug"] for r in targets}
    for label, table in (("title", titles), ("description", descs)):
        for text, slugs in table.items():
            if len(slugs) > 1 and target_slugs & set(slugs):
                errors.append(f"{label} 중복: {slugs} ← {text[:60]}")

    seen_codes: dict[str, str] = {}
    for r in regions:
        if r.get("code"):
            if r["code"] in seen_codes:
                errors.append(f"{r['slug']}: code {r['code']} 가 {seen_codes[r['code']]} 와 중복")
            seen_codes[r["code"]] = r["slug"]

    for r in targets:
        slug = r["slug"]
        tag = f"{slug} ({r['sido']} {r['sigungu']} {r['dong']})"

        # --- 지역 데이터 ---
        if not SLUG_RE.match(slug):
            errors.append(f"{tag}: slug 형식 오류")
        if not r.get("code"):
            errors.append(f"{tag}: 법정동코드(code) 없음")
        for key, min_len in (("landmark_name", 2), ("landmark_desc", 40), ("service_intro", 80), ("meta", 20)):
            if len((r.get(key) or "").strip()) < min_len:
                errors.append(f"{tag}: {key} 가 비었거나 {min_len}자 미만")
        # 템플릿이 "○○ 인근 출장 방문"처럼 뒤에 말을 붙이므로 랜드마크 이름엔 위치 표현이 들어가면 겹친다
        m = re.search(r"인근|주변|일대|근처", r.get("landmark_name", ""))
        if m:
            warn(f"{tag}: landmark_name 에 위치 표현 '{m.group(0)}' 이 있음 → 장소 이름만 쓰세요 ({r['landmark_name']})")
        faqs = r.get("faqs") or []
        if len(faqs) < 4 or any(len(qa) != 2 or not qa[0].strip() or not qa[1].strip() for qa in faqs):
            errors.append(f"{tag}: FAQ 는 질문·답 쌍으로 4개 이상 필요 (현재 {len(faqs)}개)")

        text = region_text(r)
        mine = own_tokens(r)
        for sido in all_sidos - {r["sido"]}:
            if sido in text:
                errors.append(f"{tag}: 다른 시도 이름 '{sido}' 가 지역 문구에 있음")
        for sido, short in SIDO_SHORT.items():
            if sido != r["sido"] and re.search(short + SIDO_SHORT_TAIL, text):
                # 인접 시도 언급("서울 도봉구와 맞닿은")은 흔해서 엄격 모드에서도 경고로만 둔다
                warnings.append(f"{tag}: 다른 시도 줄임 이름 '{short}' 가 지역 문구에 있음")
        def mentions(name: str) -> bool:  # 압구정동 안의 '구정동'처럼 단어 중간에서 시작하는 건 제외
            return name in text and re.search(r"(?<![가-힣])" + re.escape(name), text) is not None

        for name, sidos in sigungu_sidos.items():
            if name not in mine and r["sido"] not in sidos and mentions(name):
                warn(f"{tag}: 다른 시도의 시군구 '{name}' 가 지역 문구에 있음 ({'/'.join(sorted(sidos))})")
        for name, sidos in dong_sidos.items():
            if name not in mine and r["sido"] not in sidos and mentions(name):
                warn(f"{tag}: 다른 시도의 동 '{name}' 가 지역 문구에 있음 ({'/'.join(sorted(sidos))})")
        local_faqs = sum(1 for q, a in faqs if any(t in q or t in a for t in mine))
        if local_faqs < 3:
            warn(f"{tag}: 동·랜드마크 이름이 들어간 FAQ 가 {local_faqs}개 (3개 이상 권장)")
        if PROMISE_RE.search(text):
            errors.append(f"{tag}: 지역 문구에 결과 약속 표현 → {PROMISE_RE.search(text).group(0)}")

        # --- 렌더링된 페이지 ---
        p = PAGES_DIR / f"{slug}.html"
        if not p.exists():
            errors.append(f"{tag}: pages/{slug}.html 없음 (build_site.py 실행 필요)")
            continue
        html = p.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(html):
            errors.append(f"{tag}: 템플릿 자리 잔여 {PLACEHOLDER_RE.findall(html)[:3]}")
        for needle, label in REQUIRED:
            if needle not in html:
                errors.append(f"{tag}: {label} 없음")
        if site_cfg.get("sms_number") and 'href="sms:' not in html:
            errors.append(f"{tag}: 문자 링크 없음")
        body = re.sub(r"<style>.*?</style>|<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        for m in PROMISE_RE.finditer(body):
            errors.append(f"{tag}: 결과 약속 표현 '{m.group(0)}' → …{body[max(0, m.start()-15):m.end()+15]}…")
        for sido in all_sidos - {r["sido"]}:
            if sido in body:
                errors.append(f"{tag}: 페이지에 다른 시도 이름 '{sido}' 가 있음")
        if f"/pages/{slug}.html" not in sitemap:
            errors.append(f"{tag}: sitemap.xml 에 없음")

    # 사례 페이지: 금액·시세, 결과 약속 표현, 빠진 파일
    cases_index = ROOT / "cases" / "index.json"
    money_re = re.compile(r"\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩|시세|견적가|매입가")
    if cases_index.exists() and (only is None):
        for c in json.loads(cases_index.read_text(encoding="utf-8")):
            page = ROOT / "cases" / f"{c['slug']}.html"
            if not page.exists():
                errors.append(f"사례 {c['slug']}: cases/{c['slug']}.html 없음")
                continue
            body = re.sub(r"<style>.*?</style>|<script[^>]*>.*?</script>", "", page.read_text(encoding="utf-8"), flags=re.DOTALL)
            body = re.sub(r"<title>.*?</title>|<meta[^>]*>", "", body, flags=re.DOTALL)  # 제목·설명의 '수출 시세 비교' 문구는 서비스 설명이라 제외
            for m in money_re.finditer(body):
                errors.append(f"사례 {c['slug']}: 금액·시세 표현 '{m.group(0)}' → …{body[max(0, m.start()-15):m.end()+15]}…")
            for m in PROMISE_RE.finditer(body):
                errors.append(f"사례 {c['slug']}: 결과 약속 표현 '{m.group(0)}'")
            for name in c.get("photos", []):
                if not (ROOT / "cases" / "images" / name).exists():
                    errors.append(f"사례 {c['slug']}: 사진 cases/images/{name} 없음")
            if f"/cases/{c['slug']}.html" not in sitemap:
                errors.append(f"사례 {c['slug']}: sitemap.xml 에 없음")

    for w in warnings:
        print("경고:", w)
    for e in errors:
        print("오류:", e)
    print(f"검사 완료: 대상 {len(targets)}개, 오류 {len(errors)}건, 경고 {len(warnings)}건"
          + (" [엄격 모드]" if strict else ""))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
