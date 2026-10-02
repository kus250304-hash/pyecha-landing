"""
네이버 검색량 우선순위 목록(data/priority_regions.json)을 읽어 동·구 페이지를 고르는 순서에 쓴다.
목록은 scripts/naver_keywords.py 가 만든다(손으로 고치지 않음). 2026-10-02 병한님 요청.

쓰는 곳
- pick_next_regions.py: 시·군 몫(10개)은 목록에 있는 시·군부터(동 이름으로 검색된 동 먼저), 나머지 20개는 목록 순위대로
  시군구마다 ① 동 이름으로 검색된 동(장안동·정왕동 등)을 먼저, ② 그 시군구의 동 페이지가
  dong_target_per_gu(3, 구 페이지를 만들 수 있는 수)개가 될 때까지 채운다. 목록이 다 차면 등록대수 순.
- pick_next_gu.py: 줄 A·줄 B 모두 목록 순위가 있는 구를 먼저, 그다음 등록대수 순.
하루 개수(30개, 시·군 몫 10개, 구 10개), 구 페이지 조건(동 페이지 3개 이상), 보류 규칙은 바뀌지 않는다.

  python3 scripts/priority_regions.py show   # 목록 기준과 아직 동 페이지가 모자란 상위 20곳
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "priority_regions.json"


class Priority:
    def __init__(self, data: dict | None) -> None:
        self.data = data or {}
        self.entries = self.data.get("gu", [])
        self.rank = {(e["sido"], e["sigungu"]): e["rank"] for e in self.entries}
        self.target = int(self.data.get("dong_target_per_gu", 3))
        # 법정동코드 → (순위, 동 이름)
        self.dong_rank: dict[str, tuple[int, str]] = {}
        for e in self.entries:
            for d in e.get("dongs", []):
                for code in d.get("codes", []):
                    self.dong_rank[code] = (e["rank"], d["dong"])

    def __bool__(self) -> bool:
        return bool(self.entries)

    def rank_of(self, sido: str, sigungu: str) -> int | None:
        return self.rank.get((sido, sigungu))

    def label(self) -> str:
        return f"data/priority_regions.json ({self.data.get('made_on')} 네이버 검색량, {len(self.entries)}곳)"

    def pick_dongs(self, candidates: list[dict], have: dict[tuple[str, str], int], count: int) -> list[dict]:
        """후보(legal_dong_list.csv 줄) 중 목록 순서대로 count 개까지. have = 시군구별 이미 있는(또는 오늘 뽑은) 동 페이지 수."""
        have = dict(have)
        by_gu: dict[tuple[str, str], list[dict]] = {}
        for c in candidates:
            by_gu.setdefault((c["시도"], c["시군구"]), []).append(c)
        picked: list[dict] = []
        taken: set[str] = set()

        def take(c: dict) -> None:
            picked.append(c)
            taken.add(c["법정동코드"])
            key = (c["시도"], c["시군구"])
            have[key] = have.get(key, 0) + 1

        # 순위대로: 그 시군구에서 ① 동 이름으로 검색된 동(장안동 등, 개수와 상관없이) ② 동 페이지가 target 개가 될 때까지
        for e in self.entries:
            key = (e["sido"], e["sigungu"])
            cs = by_gu.get(key, [])
            named = [c for c in cs if c["법정동코드"] in self.dong_rank]  # ○가 묶음은 첫 ○가 코드가 후보이고 그 코드도 목록에 있다
            for c in named + [c for c in cs if c not in named]:
                if len(picked) >= count:
                    return picked
                if c not in named and have.get(key, 0) >= self.target:
                    break
                if c["법정동코드"] not in taken:
                    take(c)
        return picked


def load() -> Priority:
    if not PATH.exists():
        return Priority(None)
    return Priority(json.loads(PATH.read_text(encoding="utf-8")))


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "show":
        print(__doc__)
        return
    p = load()
    if not p:
        print("우선순위 목록 없음 (data/priority_regions.json) → 등록대수 순으로만 고름")
        return
    regions = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
    gu = {(g["sido"], g["sigungu"]) for g in json.loads((ROOT / "data" / "gu.json").read_text(encoding="utf-8"))}
    have: dict[tuple[str, str], int] = {}
    for r in regions:
        have[(r["sido"], r["sigungu"])] = have.get((r["sido"], r["sigungu"]), 0) + 1
    print(f"기준: {p.label()}, 구마다 동 페이지 {p.target}개까지 먼저")
    left = [e for e in p.entries if have.get((e["sido"], e["sigungu"]), 0) < p.target or (e["sido"], e["sigungu"]) not in gu]
    print(f"아직 할 일이 남은 곳 {len(left)}곳 (동 페이지 {p.target}개 미만이거나 구 페이지 없음). 상위 20곳:")
    for e in left[:20]:
        key = (e["sido"], e["sigungu"])
        dongs = ", ".join(d["dong"] for d in e.get("dongs", []))
        print(f"  {e['rank']:>3}. {e['sido']} {e['sigungu']}  검색량 {e['score']}  동 페이지 {have.get(key, 0)}개"
              f"  구 페이지 {'있음' if key in gu else '없음'}" + (f"  (동 키워드: {dongs})" if dongs else ""))


if __name__ == "__main__":
    main()
