"""
채워진 배치 파일(data/batches/YYYY-MM-DD.json)을 regions.json 에 넣고 렌더링·검사까지 한 번에 한다.

사용법
  python3 scripts/import_batch.py data/batches/2026-09-24.json

순서
  1. 배치 항목 형식 검사(빈 칸, FAQ 개수, code 가 legal_dong_list.csv 와 맞는지, slug 형식·중복)
  2. regions.json 에 추가 (같은 code 가 이미 있으면 그 항목을 교체하므로 고친 뒤 다시 실행해도 된다)
  3. build_site.py --only, build_index.py 실행 (sitemap.xml 도 갱신됨)
  4. check_pages.py --only 실행. 실패하면 배치 파일을 남겨 두고 종료 코드 1
  5. 성공하면 배치 파일을 지운다
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGIONS_PATH = ROOT / "data" / "regions.json"
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
SCRIPTS = ROOT / "scripts"
FIELDS = ("code", "slug", "sido", "sigungu", "dong", "landmark_name", "landmark_desc", "service_intro", "faqs", "meta")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def validate(entries: list[dict], regions: list[dict]) -> list[str]:
    csv_rows = {r["법정동코드"]: r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig"))}
    slug_to_code = {r["slug"]: r.get("code") for r in regions}
    problems = []
    seen_slugs: set[str] = set()
    for i, e in enumerate(entries, 1):
        tag = f"{i}번 {e.get('slug') or '(slug 없음)'}"
        missing = [k for k in FIELDS if k not in e]
        if missing:
            problems.append(f"{tag}: 항목 없음 {missing}")
            continue
        row = csv_rows.get(e["code"])
        if not row:
            problems.append(f"{tag}: code {e['code']} 가 legal_dong_list.csv 에 없음")
        elif (row["시도"], row["시군구"], row["읍면동"]) != (e["sido"], e["sigungu"], e["dong"]):
            problems.append(f"{tag}: code {e['code']} 의 지역명이 CSV 와 다름 "
                            f"(CSV: {row['시도']} {row['시군구']} {row['읍면동']})")
        if not SLUG_RE.match(e["slug"]):
            problems.append(f"{tag}: slug 형식 오류")
        if e["slug"] in seen_slugs:
            problems.append(f"{tag}: 배치 안에서 slug 중복")
        seen_slugs.add(e["slug"])
        if e["slug"] in slug_to_code and slug_to_code[e["slug"]] != e["code"]:
            problems.append(f"{tag}: slug 가 다른 지역(code {slug_to_code[e['slug']]})에 이미 쓰임")
        for key in ("landmark_name", "landmark_desc", "service_intro", "meta"):
            if not str(e[key]).strip():
                problems.append(f"{tag}: {key} 비어 있음")
        faqs = e["faqs"]
        if not isinstance(faqs, list) or len(faqs) < 4 or any(
            not (isinstance(qa, list) and len(qa) == 2 and str(qa[0]).strip() and str(qa[1]).strip()) for qa in faqs
        ):
            problems.append(f"{tag}: faqs 는 [질문, 답] 쌍 4개 이상이어야 함")
    return problems


def run(script: str, *args: str) -> int:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=ROOT).returncode


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("사용법: python3 scripts/import_batch.py data/batches/YYYY-MM-DD.json")
    batch_path = Path(sys.argv[1])
    if not batch_path.is_absolute():
        batch_path = ROOT / batch_path
    entries = json.loads(batch_path.read_text(encoding="utf-8"))
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))

    problems = validate(entries, regions)
    if problems:
        print("배치 파일 오류:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    by_code = {r["code"]: i for i, r in enumerate(regions) if r.get("code")}
    added = replaced = 0
    for e in entries:
        clean = {k: e[k] for k in FIELDS}
        if e["code"] in by_code:
            regions[by_code[e["code"]]] = clean
            replaced += 1
        else:
            by_code[e["code"]] = len(regions)
            regions.append(clean)
            added += 1
    REGIONS_PATH.write_text(json.dumps(regions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"regions.json: {added}개 추가, {replaced}개 교체")

    slugs = ",".join(e["slug"] for e in entries)
    if run("build_site.py", "--only", slugs) != 0 or run("build_index.py") != 0:
        sys.exit(1)
    if run("check_pages.py", "--only", slugs) != 0:
        print(f"검사 실패: {batch_path.relative_to(ROOT)} 를 고친 뒤 다시 실행하세요")
        sys.exit(1)

    batch_path.unlink()
    print(f"완료: {len(entries)}개 페이지 생성·검사 통과, 배치 파일 삭제")


if __name__ == "__main__":
    main()
