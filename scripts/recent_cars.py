"""
구 페이지 "최근 ○○에서 진행한 차" 칸 재료(2026-11-05 병한님, 상자 B-1 1번).
거래 기록부(운영자 PC 에만 있음)에서 입고 완료·말소 완료 거래만 골라 시·군마다 최근 5건을
data/recent_cars.json 에 쓴다. PC 예약 작업 "폐차 사례 가져오기" 2-1 단계가 매일 --write 로 돌리고 올린다.

사용법
  python scripts/recent_cars.py           # 무엇이 들어갈지 보여 주기만(파일 그대로)
  python scripts/recent_cars.py --write   # data/recent_cars.json 다시 쓰기(내용이 같으면 그대로)

한 건 = {월, 차종, 연식, 시동(가능/불가), 고른쪽(폐차/수출)} 뿐. 그 밖의 칸(이름·전화·차번호·금액·폐차장·동·날짜)은 없다.
모르는 칸은 비워 두고 페이지에서 그 부분을 빼고 보인다(지어내지 않음).
시·군 = 구 페이지가 있는 곳(일반구는 시 하나, 예: 고양시 → 일산동구·일산서구·덕양구 페이지 모두에 보임).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ledger_read as L  # noqa: E402
from inquiry_log import WIKI_DIR  # noqa: E402
from sitemap_lib import today  # noqa: E402

OUT = ROOT / "data" / "recent_cars.json"
PER_PLACE = 5


def build(folder: Path) -> tuple[list[dict], list[str]]:
    places = L.gu_places()
    groups: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    skipped = []
    for r in L.records(folder):
        if not L.arrived(r):
            continue
        day = r["입고일"] if L.is_day(r["입고일"]) else r["날짜"]
        car = L.car_name(r["차종"])
        key = L.city_of(r["지역"], places)
        if not (key and car and L.is_day(day)):
            skipped.append(f"{r['file'][:10]}: " + ("지역을 구 페이지로 못 정함" if not key else "차종 없음·쓸 수 없는 글자" if not car else "날짜 없음"))
            continue
        groups.setdefault(key, []).append((day, {"month": day[:7], "car": car, "year": L.model_year(r["연식"]),
                                                 "start": L.start_state(r["차상태"]), "side": L.chosen_side(r)}))
    out = []
    for (sido, city), items in sorted(groups.items()):
        items.sort(key=lambda x: x[0], reverse=True)
        out.append({"sido": sido, "city": city, "cars": [c for _, c in items[:PER_PLACE]]})
    return out, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dir", default=str(WIKI_DIR))
    args = ap.parse_args()
    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"최근 진행한 차: 거래 기록부 폴더 없음({folder}) → 건너뜀")
        return
    places, skipped = build(folder)
    n = sum(len(p["cars"]) for p in places)
    print(f"최근 진행한 차: {len(places)}곳 {n}건" + (f", 뺀 거래 {len(skipped)}건" if skipped else ""))
    for p in places:
        print(f"  {p['city']}: " + " / ".join(f"{c['month']} {c['year']} {c['car']} {c['start']} {c['side']}".replace("  ", " ") for c in p["cars"]))
    for s in skipped:
        print(f"  뺌 {s}")
    if args.write:
        old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
        if old.get("places") == places:
            print("data/recent_cars.json 그대로(바뀐 것 없음)")
            return
        data = {"updated": today(), "source": "병한-업무위키 거래 기록부, 입고 완료·말소 완료 거래만(scripts/recent_cars.py)",
                "rule": "시·군마다 최근 5건, 칸은 월·차종·연식·시동·고른쪽뿐(이름·전화·차번호·금액 없음)", "places": places}
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("data/recent_cars.json 씀")


if __name__ == "__main__":
    main()
