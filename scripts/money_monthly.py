"""
월 숫자(2026-11-05 병한님, 상자 B-1 3번) — 매달 17일 자동 보고 재료.
거래 기록부(운영자 PC 에만 있음)를 달마다 세어

  저장소 data/money_monthly.json : 거래 수 · 안 된 수 · 안 된 이유 상위 3 · 건당 평균의 "구간" · "지난달 대비" — 돈 절대값 없음
  위키 병한-업무위키\\폐차\\거래기록부\\월 숫자.md : 위 칸 + 남는 돈 합계·건당 평균(만원) — 절대값은 여기에만

에 쓴다. 칸 설명은 docs/money-monthly.md. PC 예약 작업 "폐차 사례 가져오기" 2-1 단계가 매일 --write 로 돌린다.

사용법
  python scripts/money_monthly.py           # 저장소에 들어갈 칸만 보여 주기(돈 절대값은 화면에도 안 보임)
  python scripts/money_monthly.py --write   # json + 위키 노트 쓰기(내용이 같으면 그대로)

규칙
  - 달 = 기록부 "날짜"(문의일) 칸의 달. 거래 수 = 거래상태 "완료", 안 된 수 = "종료".
  - 남는 돈 = 판매가 − 매입가 − 탁송견인비(빈칸은 0). 판매가·매입가가 둘 다 숫자인 완료 거래만 셈(돈 기록 건수 money_n).
  - 건당 평균 구간(만원): "10 미만" / "10~40" / "40 이상". 돈 기록이 없으면 "기록 없음".
  - 지난달 대비: 건당 평균이 ±10% 안이면 "비슷", 위면 "올라감", 아래면 "내려감"(어느 달이든 기록 없으면 "비교 못 함").
  - 안 된 이유: 기록부에 "안된이유" 칸이 있으면 그 값, 없으면 메모 낱말로 가름(금액 / 다른 데서 먼저 / 서류·명의 /
    연락 끊김 / 거리·탁송 / 기타). 메모 글은 어디에도 옮기지 않는다.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ledger_read as L  # noqa: E402
from inquiry_log import WIKI_DIR  # noqa: E402
from sitemap_lib import today  # noqa: E402

OUT = ROOT / "data" / "money_monthly.json"
WIKI_NOTE = WIKI_DIR.parent / "거래기록부" / "월 숫자.md"
REASONS = (  # (이름, 메모 낱말) 위에서부터 처음 맞는 것
    ("다른 데서 먼저", r"다른\s*(데|곳|업체)|업체로|먼저\s*(가져|처리|했)|구청 소개"),
    ("금액", r"금액|기대|불만|비싸|싸다|더 받|더 높"),
    ("서류·명의", r"서류|명의|상속|압류|공동"),
    ("연락 끊김", r"연락\s*(없|안|두절|끊)|부재|안 받"),
    ("거리·탁송", r"거리|탁송|멀어|멀다|섬"),
)


def won(v: str) -> int | None:
    v = re.sub(r"[,\s원]", "", v or "")
    return int(v) if v.isdigit() else None


def reason_of(r: dict) -> str:
    if r.get("안된이유"):
        return r["안된이유"].strip()
    memo = r.get("메모", "")
    return next((name for name, pat in REASONS if re.search(pat, memo)), "기타")


def band(avg_man: float | None) -> str:
    if avg_man is None:
        return "기록 없음"
    return "10 미만" if avg_man < 10 else "10~40" if avg_man < 40 else "40 이상"


def compute(folder: Path) -> tuple[dict, dict]:
    """(저장소용 달별 칸, 위키용 절대값 {달: (합계 만원, 건당 평균 만원)})."""
    months: dict[str, dict] = {}
    money: dict[str, list[int]] = {}
    for r in L.records(folder, money=True):
        m = r["날짜"][:7]
        if not re.fullmatch(r"\d{4}-\d{2}", m):
            continue
        row = months.setdefault(m, {"deals": 0, "lost": 0, "reasons": Counter()})
        if r["거래상태"] == "완료":
            row["deals"] += 1
            sell, buy = won(r["판매가"]), won(r["매입가"])
            if sell is not None and buy is not None:
                money.setdefault(m, []).append(sell - buy - (won(r["탁송견인비"]) or 0))
        elif r["거래상태"] == "종료":
            row["lost"] += 1
            row["reasons"][reason_of(r)] += 1
    public, private = {}, {}
    prev_avg = None
    for m in sorted(months):
        vals = money.get(m, [])
        avg = sum(vals) / len(vals) / 10000 if vals else None
        vs = ("비교 못 함" if avg is None or prev_avg is None or prev_avg <= 0
              else "비슷" if abs(avg - prev_avg) <= prev_avg * 0.1 else "올라감" if avg > prev_avg else "내려감")
        row = months[m]
        public[m] = {"deals": row["deals"], "lost": row["lost"],
                     "lost_reasons": [[k, n] for k, n in row["reasons"].most_common(3)],
                     "avg_band": band(avg), "vs_last_month": vs, "money_n": len(vals)}
        private[m] = (round(sum(vals) / 10000) if vals else None, round(avg, 1) if avg is not None else None)
        if avg is not None:
            prev_avg = avg
    return public, private


def wiki_text(public: dict, private: dict) -> str:
    head = ("# 월 숫자\n\n`scripts/money_monthly.py --write`(PC 예약 작업 \"폐차 사례 가져오기\" 2-1)가 매일 다시 씁니다. 손으로 고치지 않습니다.\n"
            "남는 돈 = 판매가 − 매입가 − 탁송견인비(만원, 판매가·매입가가 다 적힌 완료 거래만). 이 노트의 돈 숫자는 저장소에 올리지 않습니다"
            "(저장소 data/money_monthly.json 에는 구간·방향만).\n\n"
            "| 달 | 거래 수 | 안 된 수 | 안 된 이유 상위 3 | 남는 돈 합계(만원) | 건당 평균(만원) | 구간 | 지난달 대비 | 돈 기록 건수 |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
    rows = ""
    for m in sorted(public, reverse=True):
        p, (total, avg) = public[m], private[m]
        reasons = ", ".join(f"{k} {n}" for k, n in p["lost_reasons"]) or "-"
        rows += (f"| {m} | {p['deals']} | {p['lost']} | {reasons} | {'-' if total is None else total} | {'-' if avg is None else avg} "
                 f"| {p['avg_band']} | {p['vs_last_month']} | {p['money_n']} |\n")
    return head + rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dir", default=str(WIKI_DIR))
    args = ap.parse_args()
    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"월 숫자: 거래 기록부 폴더 없음({folder}) → 건너뜀")
        return
    public, private = compute(folder)
    for m in sorted(public, reverse=True)[:3]:
        p = public[m]
        print(f"월 숫자 {m}: 거래 {p['deals']} · 안 된 {p['lost']}"
              + (f"(이유 {', '.join(f'{k} {n}' for k, n in p['lost_reasons'])})" if p["lost_reasons"] else "")
              + f" · 건당 평균 구간 {p['avg_band']} · 지난달 대비 {p['vs_last_month']}")
    if not args.write:
        return
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if old.get("months") != public:
        OUT.write_text(json.dumps({"updated": today(), "source": "병한-업무위키 거래 기록부(scripts/money_monthly.py), 칸 설명 docs/money-monthly.md",
                                   "months": public}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("data/money_monthly.json 씀")
    else:
        print("data/money_monthly.json 그대로")
    WIKI_NOTE.parent.mkdir(parents=True, exist_ok=True)
    text = wiki_text(public, private)
    if not WIKI_NOTE.exists() or WIKI_NOTE.read_text(encoding="utf-8") != text:
        WIKI_NOTE.write_text(text, encoding="utf-8")
        print(f"위키 노트 씀: {WIKI_NOTE}")


if __name__ == "__main__":
    main()
