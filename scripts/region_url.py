"""
유튜브·당근 설명란에 넣을 "그 차 지역 페이지" 주소(?src=yt)를 알려 준다(2026-10-16, docs/case-pipeline-2026-10-16.md [5]).

  python scripts/region_url.py "목포시 용해동"
  python scripts/region_url.py "전남광주 목포시 용해동" --src yt

순서: 그 동의 동 페이지 → 그 시군구 구 페이지 → 첫 화면. 한글 주소는 인코딩해서 출력한다(유튜브에서 링크가 끊기지 않게).
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cases import load_csv_rows, resolve_region  # noqa: E402
from build_site import gu_file  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("region", help='"목포시 용해동", "전남광주 목포시", "수원시 장안구 영화동" 처럼')
    ap.add_argument("--src", default="yt")
    args = ap.parse_args()
    cfg = json.loads((ROOT / "data" / "site_config.json").read_text(encoding="utf-8"))
    base = cfg["site_base_url"].rstrip("/")
    tail = f"?src={args.src}" if args.src else ""
    region, why = resolve_region(args.region, load_csv_rows())
    if not region:
        print(f"지역을 정하지 못했습니다: {why}\n첫 화면: {base}/{tail}")
        sys.exit(1)
    regions = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
    gus = json.loads((ROOT / "data" / "gu.json").read_text(encoding="utf-8"))
    dong = next((r for r in regions if (r["sido"], r["sigungu"], r["dong"]) == (region["sido"], region["sigungu"], region["dong"])), None)
    gu = next((g for g in gus if (g["sido"], g["sigungu"]) == (region["sido"], region["sigungu"])), None)
    if dong:
        print(f"동 페이지: {base}/pages/{dong['slug']}.html{tail}")
    elif gu:
        print(f"구 페이지: {base}/gu/{quote(gu_file(gu['sido'], gu['sigungu']))}{tail}")
    else:
        print(f"동·구 페이지 없음 → 첫 화면: {base}/{tail}")


if __name__ == "__main__":
    main()
