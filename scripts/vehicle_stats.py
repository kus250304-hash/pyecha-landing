"""
시군구별 자동차 등록대수 통계 (동·구 페이지를 만드는 순서를 정하는 데 쓴다).

우선순위 기준 (docs/roadmap.md 5·6절):
  1순위  시군구별 차령 10년 이상(노후차) 등록대수가 많은 순     → data/vehicle_stats.json        (basis "old10")
  2순위  노후차 통계가 없으면 시군구별 전체 등록대수가 많은 순  → data/vehicle_stats_total.json  (basis "total")
  3순위  둘 다 없으면 구 페이지가 있는 구 → 동 페이지가 많은 구 순. 매일 보고에 "통계 없음"을 알린다.

저장 형식
  {"basis": "old10", "as_of": "2026년 8월", "source": "국토교통부 자동차등록현황보고(차령별)",
   "url": "https://...", "saved_on": "YYYY-MM-DD",
   "rows": [{"sido": "서울특별시", "sigungu": "종로구", "count": 12345}, ...]}

통계 파일 넣기 (공공데이터포털·국토교통부 통계누리에서 받은 CSV 또는 엑셀 그대로):
  python3 scripts/vehicle_stats.py import 받은파일.csv --basis old10 --as-of "2026년 8월" \\
      --source "국토교통부 자동차등록현황보고(차령별)" --url "https://stat.molit.go.kr/..." --count-col "10년이상"
  - 시도·시군구 칸은 이름으로 찾는다(시도/시·도, 시군구/시·군·구). 숫자 칸은 --count-col 로 고르거나,
    --sum-cols "10년,11년,12년" 처럼 여러 칸을 더한다. 같은 시군구 줄이 여러 개면 더한다.
  - 엑셀(.xlsx)은 openpyxl 이 있을 때만 읽는다. 없으면 CSV 로 저장해서 넣는다.
  - 숫자를 지어내거나 추정해서 넣지 않는다. 받은 파일 그대로만 넣는다.

  python3 scripts/vehicle_stats.py show     # 지금 쓰는 기준과 상위 20개 시군구

옛 이름 통계 맞추기(2026-07-01 행정구역 변경 전 자료):
  - 광주광역시·전라남도 → 전남광주통합특별시, 강원도 → 강원특별자치도, 전라북도 → 전북특별자치도
  - 인천 중구 → 제물포구·영종구, 인천 동구 → 제물포구, 인천 서구 → 서해구·검단구.
    나뉜 구는 옛 구 숫자를 새 구 모두에 그대로 쓰고, 합쳐진 구는 더한다. 순서를 정하는 데만 쓰는 근사값이다.
  - 통계에 '수원시'처럼 시 전체만 있고 구(장안구 등)가 없으면 그 시의 구 모두에 시 전체 숫자를 쓴다(근사).
"""
import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD10_PATH = ROOT / "data" / "vehicle_stats.json"
TOTAL_PATH = ROOT / "data" / "vehicle_stats_total.json"

SIDO_ALIAS = {
    "광주광역시": "전남광주통합특별시", "전라남도": "전남광주통합특별시", "전남광주": "전남광주통합특별시",
    "강원도": "강원특별자치도", "전라북도": "전북특별자치도",
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시", "광주": "전남광주통합특별시",
    "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도", "강원": "강원특별자치도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전북특별자치도", "전남": "전남광주통합특별시",
    "경북": "경상북도", "경남": "경상남도", "제주": "제주특별자치도",
}
# (시도, 옛 시군구) → 새 시군구들
SIGUNGU_ALIAS = {
    ("인천광역시", "중구"): ["제물포구", "영종구"],
    ("인천광역시", "동구"): ["제물포구"],
    ("인천광역시", "서구"): ["서해구", "검단구"],
}


def _key(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load(prefer: str = "old10") -> tuple[str, dict[tuple[str, str], int], dict]:
    """(기준, {(시도, 시군구 공백없음): 등록대수}, 메타). 파일이 없으면 ("none", {}, {})."""
    for basis, path in (("old10", OLD10_PATH), ("total", TOTAL_PATH)):
        if prefer == "total" and basis == "old10":
            continue
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("rows"):
                counts: dict[tuple[str, str], int] = {}
                for r in data["rows"]:
                    k = (r["sido"], _key(r["sigungu"]))
                    counts[k] = counts.get(k, 0) + int(r["count"])
                return data.get("basis", basis), counts, {k: v for k, v in data.items() if k != "rows"}
    return "none", {}, {}


def count_for(counts: dict[tuple[str, str], int], sido: str, sigungu: str) -> int | None:
    """그 시군구의 등록대수. '수원시 장안구' 가 없으면 '수원시' 전체를 쓴다. 없으면 None."""
    k = _key(sigungu)
    if (sido, k) in counts:
        return counts[(sido, k)]
    city = sigungu.split()[0] if " " in sigungu else None
    if city and (sido, _key(city)) in counts:
        return counts[(sido, _key(city))]
    return None


def _read_table(path: Path) -> list[dict]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise SystemExit("엑셀을 읽으려면 openpyxl 이 필요합니다(pip install openpyxl). 아니면 CSV 로 저장해서 넣으세요.")
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).active
        rows = [[("" if c is None else str(c)).strip() for c in row] for row in ws.iter_rows(values_only=True)]
    else:
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "cp949"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        rows = [[c.strip() for c in row] for row in csv.reader(text.splitlines())]
    # 머리줄: 시도·시군구 칸이 모두 있는 첫 줄
    for i, row in enumerate(rows):
        names = [_key(c) for c in row]
        if any(n in ("시도", "시·도") for n in names) and any(n in ("시군구", "시·군·구") for n in names):
            header = [_key(c).replace("·", "") for c in row]
            return [dict(zip(header, r)) for r in rows[i + 1:] if any(r)]
    raise SystemExit("머리줄에서 '시도'와 '시군구' 칸을 찾지 못했습니다. 칸 이름을 확인해 주세요.")


def _num(s: str) -> int:
    s = re.sub(r"[,\s]", "", s or "")
    return int(float(s)) if re.fullmatch(r"-?\d+(\.\d+)?", s) else 0


def cmd_import(args: argparse.Namespace) -> None:
    table = _read_table(Path(args.file))
    cols = [_key(c) for c in (args.sum_cols.split(",") if args.sum_cols else [args.count_col] if args.count_col else [])]
    if not cols:
        raise SystemExit("--count-col 또는 --sum-cols 로 숫자 칸을 골라 주세요. 칸 이름: " + ", ".join(table[0].keys()))
    missing = [c for c in cols if c not in table[0]]
    if missing:
        raise SystemExit(f"없는 칸: {missing}. 칸 이름: {', '.join(table[0].keys())}")
    rows: dict[tuple[str, str], int] = {}
    for r in table:
        sido, sigungu = r.get("시도", ""), r.get("시군구", "")
        if not sido or not sigungu or sigungu in ("계", "합계", "소계") or sido in ("계", "합계", "전국"):
            continue
        sido = SIDO_ALIAS.get(sido, sido)
        n = sum(_num(r.get(c, "")) for c in cols)
        for new in SIGUNGU_ALIAS.get((sido, sigungu), [sigungu]):
            rows[(sido, new)] = rows.get((sido, new), 0) + n
    if not rows:
        raise SystemExit("읽은 줄이 없습니다")
    out = {
        "basis": args.basis, "as_of": args.as_of, "source": args.source, "url": args.url,
        "saved_on": date.today().isoformat(),
        "rows": [{"sido": s, "sigungu": g, "count": n} for (s, g), n in sorted(rows.items(), key=lambda x: -x[1])],
    }
    path = OLD10_PATH if args.basis == "old10" else TOTAL_PATH
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"저장: {path.relative_to(ROOT)} ({len(rows)}개 시군구, 기준 {args.basis}, {args.as_of})")


def cmd_show(_: argparse.Namespace) -> None:
    basis, counts, meta = load()
    if basis == "none":
        print("통계 없음: data/vehicle_stats.json(노후차)·vehicle_stats_total.json(전체) 둘 다 없음 → 동 페이지 많은 구 순으로 뽑음")
        return
    print(f"기준: {'차령 10년 이상 노후차' if basis == 'old10' else '전체'} 등록대수 · {meta.get('as_of')} · {meta.get('source')}")
    for (s, g), n in sorted(counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {s} {g}: {n:,}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import")
    p.add_argument("file")
    p.add_argument("--basis", choices=["old10", "total"], required=True)
    p.add_argument("--as-of", required=True, help='통계 기준 연월, 예: "2026년 8월"')
    p.add_argument("--source", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--count-col")
    p.add_argument("--sum-cols")
    p.set_defaults(func=cmd_import)
    sub.add_parser("show").set_defaults(func=cmd_show)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
