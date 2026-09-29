"""
채워진 배치 파일(data/batches/YYYY-MM-DD.json)을 regions.json 에 넣고 렌더링·검사까지 한 번에 한다.

사용법
  python3 scripts/import_batch.py data/batches/2026-09-24.json

순서
  0. 사실 확인 기록(fact_check) 로 나눈다. status 가 "held" 인 항목은 반영하지 않고
     data/batches/held/YYYY-MM-DD.json(보류 폴더)에 모은다. "confirmed" 인 항목만 아래로 간다.
     기록이 없거나 글에 나오는 장소 이름 중 확인 기록이 빠진 것이 있으면 오류(scripts/fact_check.py)
  1. 배치 항목 형식 검사(빈 칸, FAQ 개수, code 가 legal_dong_list.csv 와 맞는지, slug 형식·중복)
  2. regions.json 에 추가 (같은 code 가 이미 있으면 그 항목을 교체하므로 고친 뒤 다시 실행해도 된다)
  3. build_site.py(전체 렌더링, 기존 페이지의 이웃 링크·사례 카드도 갱신), build_index.py 실행 (sitemap.xml 도 갱신됨)
  4. check_pages.py --only 실행. 실패하면 배치 파일을 남겨 두고 종료 코드 1
  5. 성공하면 확인 기록을 data/fact_checks/YYYY-MM-DD.json 에 남기고, 보류 항목을 보류 폴더에 옮기고, 배치 파일을 지운다
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fact_check

ROOT = Path(__file__).resolve().parent.parent
REGIONS_PATH = ROOT / "data" / "regions.json"
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
SITEMAP_PATH = ROOT / "sitemap.xml"
INDEX_PATH = ROOT / "index.html"
PAGES_DIR = ROOT / "pages"
SCRIPTS = ROOT / "scripts"
HELD_DIR = ROOT / "data" / "batches" / "held"
FACT_LOG_DIR = ROOT / "data" / "fact_checks"
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
        for fp in fact_check.problems(e):
            problems.append(f"{tag}: {fp}")
        for key in ("landmark_name", "landmark_desc", "service_intro", "meta"):
            if not str(e[key]).strip():
                problems.append(f"{tag}: {key} 비어 있음")
        faqs = e["faqs"]
        if not isinstance(faqs, list) or len(faqs) < 4 or any(
            not (isinstance(qa, list) and len(qa) == 2 and str(qa[0]).strip() and str(qa[1]).strip()) for qa in faqs
        ):
            problems.append(f"{tag}: faqs 는 [질문, 답] 쌍 4개 이상이어야 함")
    return problems


def merge_json_list(path: Path, items: list[dict]) -> None:
    """path 의 목록에 items 를 code 기준으로 합쳐 쓴다(같은 날 다시 실행해도 겹치지 않게)."""
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    codes = {i["code"] for i in items}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([o for o in old if o.get("code") not in codes] + items, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def run(script: str, *args: str) -> int:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=ROOT).returncode


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("사용법: python3 scripts/import_batch.py data/batches/YYYY-MM-DD.json")
    batch_path = Path(sys.argv[1])
    if not batch_path.is_absolute():
        batch_path = ROOT / batch_path
    all_entries = json.loads(batch_path.read_text(encoding="utf-8"))
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    held = [e for e in all_entries if (e.get("fact_check") or {}).get("status") == "held"]
    entries = [e for e in all_entries if e not in held]
    held_path = HELD_DIR / batch_path.name
    fact_log_path = FACT_LOG_DIR / batch_path.name

    for e in held:
        if not str(e["fact_check"].get("reason", "")).strip():
            print(f"배치 파일 오류: {e.get('slug')} 보류(held) 이유(reason) 없음")
            sys.exit(1)
    if not entries:
        if held:
            merge_json_list(held_path, held)
        batch_path.unlink()
        print(f"반영할 지역 0개, 보류 {len(held)}개 ({held_path.relative_to(ROOT)}). 배치 파일 삭제")
        return

    problems = validate(entries, regions)
    if problems:
        print("배치 파일 오류:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    # 실패하면 되돌릴 수 있도록 손대는 파일을 기억해 둔다
    snapshots = {p: p.read_bytes() for p in (REGIONS_PATH, SITEMAP_PATH, INDEX_PATH) if p.exists()}
    new_pages = [PAGES_DIR / f"{e['slug']}.html" for e in entries if not (PAGES_DIR / f"{e['slug']}.html").exists()]

    def rollback() -> None:
        for p, data in snapshots.items():
            p.write_bytes(data)
        for p in new_pages:
            p.unlink(missing_ok=True)
        run("build_site.py")  # 이웃 링크가 바뀐 기존 페이지도 원래대로
        print("변경 사항을 되돌렸습니다 (regions.json, sitemap.xml, index.html, 새 페이지)")

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
    # 새 지역이 기존 페이지의 이웃 링크·사례 카드에도 반영되도록 전체를 다시 렌더링한다 (몇 초 걸림)
    if run("build_site.py") != 0 or run("build_index.py") != 0:
        rollback()
        sys.exit(1)
    if run("check_pages.py", "--only", slugs) != 0:
        rollback()
        print(f"검사 실패: {batch_path.relative_to(ROOT)} 의 해당 항목을 고치거나 빼고 다시 실행하세요")
        sys.exit(1)

    merge_json_list(fact_log_path, [
        {"code": e["code"], "slug": e["slug"], "items": e["fact_check"]["items"]} for e in entries
    ])
    if held:
        merge_json_list(held_path, held)
    batch_path.unlink()
    print(f"완료: {len(entries)}개 페이지 생성·검사 통과, 보류 {len(held)}개, 배치 파일 삭제")


if __name__ == "__main__":
    main()
