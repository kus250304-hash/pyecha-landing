"""
자동생성 루틴이 main 에 바로 push 하기 직전에 돌리는 최종 관문.

사용법 (오늘 작업을 로컬에서 커밋한 뒤, push 전에)
  python3 scripts/publish_gate.py
  python3 scripts/publish_gate.py --base <커밋>   # 시험용: origin/main 대신 다른 기준과 비교(fetch 안 함)

확인하는 것 — 하나라도 실패하면 "통과 못 함"과 이유를 출력하고 종료 코드 1 (그러면 main 에 push 하지 않는다)
  1. 커밋하지 않은 변경이 없는지
  2. 최신 origin/main 위에 쌓은 커밋인지 (git fetch 후 확인)
  3. 바뀐 파일이 페이지 데이터 쪽으로만 한정되는지 (scripts/·templates/·CLAUDE.md·설정은 안 됨)
  4. 기존 regions.json 항목이 그대로인지(지워지거나 바뀐 것 없음), code·slug 중복 없는지
  5. 새로 들어간 지역마다 사실 확인 기록(data/fact_checks/)이 있는지
  6. 다시 렌더링해도 바뀌는 파일이 없는지 (build_site.py, build_index.py)
  7. check_pages.py 전체 검사 오류 0
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_PREFIXES = (
    "data/regions.json", "data/batches/held/", "data/fact_checks/",
    "pages/", "cases/", "index.html", "sitemap.xml",
    "gu/", "data/gu.json",  # 구 페이지(2026-09-29 추가)
    "data/vehicle_stats.json", "data/vehicle_stats_total.json",  # 우선순위용 등록대수 통계
)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="비교 기준 (기본: 최신 origin/main)")
    base = ap.parse_args().base or "origin/main"
    fails: list[str] = []

    if git("status", "--porcelain").strip():
        print("통과 못 함: 커밋하지 않은 변경이 있습니다\n" + git("status", "--short"))
        sys.exit(1)

    if base == "origin/main":
        git("fetch", "-q", "origin", "main")
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=ROOT).returncode != 0:
        print("통과 못 함: 최신 main 위에 쌓은 커밋이 아닙니다 (그사이 main 이 바뀜)")
        sys.exit(1)

    changed = [f for f in git("diff", "--name-only", base, "HEAD").splitlines() if f]
    if not changed:
        print("통과 못 함: main 과 달라진 파일이 없습니다 (반영할 것 없음)")
        sys.exit(1)
    outside = [f for f in changed if not f.startswith(ALLOWED_PREFIXES)]
    if outside:
        fails.append(f"페이지 데이터 밖의 파일이 바뀜: {outside[:10]}")

    old = json.loads(git("show", f"{base}:data/regions.json"))
    new = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
    new_by_code = {r.get("code"): r for r in new}
    touched = [r["slug"] for r in old if new_by_code.get(r.get("code")) != r]
    if touched:
        fails.append(f"기존 지역 항목이 지워지거나 바뀜: {touched[:10]}")
    for key in ("code", "slug"):
        values = [r.get(key) for r in new]
        dups = sorted({v for v in values if values.count(v) > 1})
        if dups:
            fails.append(f"{key} 중복: {dups[:10]}")

    old_codes = {r.get("code") for r in old}
    added = [r for r in new if r.get("code") not in old_codes]
    logged: set[str] = set()
    for f in (ROOT / "data" / "fact_checks").glob("*.json"):
        logged |= {x["code"] for x in json.loads(f.read_text(encoding="utf-8")) if x.get("items")}
    unlogged = [r["slug"] for r in added if r["code"] not in logged]
    if unlogged:
        fails.append(f"사실 확인 기록 없이 들어간 지역: {unlogged}")

    for script in ("build_site.py", "build_index.py"):
        if subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True).returncode != 0:
            fails.append(f"{script} 실행 실패")
    rerender = git("status", "--porcelain").strip()
    if rerender:
        fails.append("다시 렌더링하면 바뀌는 파일이 있음:\n" + rerender[:1000])
        subprocess.run(["git", "checkout", "--", "."], cwd=ROOT)

    check = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_pages.py")], cwd=ROOT, capture_output=True, text=True)
    summary = check.stdout.strip().splitlines()[-1] if check.stdout.strip() else "(출력 없음)"
    if check.returncode != 0:
        errs = [l for l in check.stdout.splitlines() if l.startswith("오류:")]
        fails.append(f"check_pages.py 실패 — {summary}\n" + "\n".join(errs[:20]))

    if fails:
        print("통과 못 함:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"통과: 새 지역 {len(added)}개, 바뀐 파일 {len(changed)}개, {summary}")


if __name__ == "__main__":
    main()
