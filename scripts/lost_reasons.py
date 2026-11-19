"""
문의 결과 정리와 안 된 이유 세기(2026-11-19 병한님 "1 2 3").

1) 잠듦: docs/index-requests.md "문의가 온 페이지" 칸에서 상태가 "진행"인데 문의한 날부터 SLEEP_DAYS(21)일이 넘은 줄은
   숫자에서 "잠듦"으로 따로 센다. 병한님 경험(11/19): "새 차 나오면·며칠 뒤" 같은 말은 대부분 예의상 거절이고,
   진짜 이유는 금액이 마음에 안 들거나 고쳐서 타는 것이 가장 많다. 거래 기록부는 고치지 않는다(보고·판단 숫자만).
2) 안 된 이유: 종료·잠듦 문의마다 이유 하나를 data/lost_reasons.json 에 남긴다. PC 예약 작업(docs/pc-case-import-prompt.md 2-2)이
   거래 기록부 메모와 통화표(통화녹음백업\\_분석\\통화표.csv)를 읽고 확신할 때만 고르고, 아니면 "모름". 병한님께 묻지 않는다.
   저장하는 것은 날짜·구 페이지 이름(이미 공개된 칸)·상태·이유·근거 종류뿐이다. 이름·전화·차번호·금액은 넣지 않는다.

python3 scripts/lost_reasons.py report           # 문의 결과(성사·종료·진행·잠듦)와 안 된 이유 합계
python3 scripts/lost_reasons.py todo --n 10      # 이유를 아직 안 적은 종료·잠듦 문의(오래된 것부터)
python3 scripts/lost_reasons.py set 2026-11-03 강릉시 수리·계속탐 --src 통화표 [--nth 2]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUESTS = ROOT / "docs" / "index-requests.md"
OUT = ROOT / "data" / "lost_reasons.json"
SECTION = "문의가 온 페이지"
SLEEP_DAYS = 21
LINE_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}), 랜딩 문의\(상태: ([^)]+)\) — \S+(?: \(([^)]+)\))?")
REASONS = ("금액", "수리·계속탐", "다른데서먼저", "나중에", "서류·명의", "연락끊김", "거리·탁송", "모름")
REASON_NOTE = {
    "금액": "금액이 마음에 안 듦(다른 곳이 더 준다는 말 포함, 거래가 어디서 됐는지 모를 때)",
    "수리·계속탐": "고쳐서 타거나 더 타기로 함",
    "다른데서먼저": "다른 곳에서 이미 처리했다고 함",
    "나중에": "새 차 나오면·며칠 뒤처럼 미룸(진짜 이유를 모를 때만)",
    "서류·명의": "서류가 안 되거나 본인 차가 아님",
    "연락끊김": "첫 통화 뒤 연락이 닿지 않음",
    "거리·탁송": "거리·탁송 사정",
    "모름": "자료로 확신할 수 없음",
}
SRCS = ("통화표", "기록부", "통화표·기록부", "모름")


def kst_today() -> date:
    return datetime.now(timezone(timedelta(hours=9))).date()


def inquiries(today: date | None = None) -> list[dict]:
    """문의가 온 페이지 칸의 줄을 위에서부터 읽는다. 같은 날·같은 곳 줄은 nth(1부터)로 나눈다."""
    today = today or kst_today()
    text = REQUESTS.read_text(encoding="utf-8")
    rows, inside, seen = [], False, Counter()
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().startswith(SECTION)
            continue
        m = LINE_RE.match(line) if inside else None
        if not m:
            continue
        d, status, place = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        seen[(d, place)] += 1
        sleeping = status == "진행" and (today - date.fromisoformat(d)).days > SLEEP_DAYS
        rows.append({"date": d, "place": place, "nth": seen[(d, place)], "status": status,
                     "result": "잠듦" if sleeping else status})
    return rows


def key(r: dict) -> str:
    return f"{r['date']}|{r['place']}|{r['nth']}"


def load() -> dict:
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"note": "안 된 이유(2026-11-19, scripts/lost_reasons.py). 손으로 고치지 않음. 이름·전화·차번호·금액 없음",
                "rows": {}}


def save(data: dict) -> None:
    data["updated"] = kst_today().isoformat()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def summary(today: date | None = None, since: str = "") -> dict:
    rows = [r for r in inquiries(today) if r["date"] >= since]
    got = load()["rows"]
    res = Counter(r["result"] for r in rows)
    lost = [r for r in rows if r["result"] in ("종료", "잠듦")]
    reasons = Counter(got[key(r)]["reason"] for r in lost if key(r) in got)
    decided = res["거래 성사"] + res["종료"] + res["잠듦"]
    return {"rows": len(rows), "result": res, "decided": decided,
            "rate": (res["거래 성사"] / decided) if decided else None,
            "reasons": reasons, "lost": len(lost), "unset": sum(1 for r in lost if key(r) not in got)}


def report_lines(today: date | None = None, since: str = "") -> list[str]:
    s = summary(today, since)
    r = s["result"]
    rate = "-" if s["rate"] is None else f"{s['rate'] * 100:.0f}%"
    head = (f"문의 결과{f'({since}부터)' if since else ''}: 성사 {r['거래 성사']} · 종료 {r['종료']} · 잠듦 {r['잠듦']}"
            f"({SLEEP_DAYS}일 넘은 진행) · 진행 {r['진행']} — 성사율 {rate}(성사 ÷ 성사·종료·잠듦)")
    why = " · ".join(f"{k} {n}" for k, n in s["reasons"].most_common()) or "아직 없음"
    return [head, f"  - 안 된 이유(종료·잠듦 {s['lost']}건 중 적은 것): {why} / 아직 안 적음 {s['unset']}건"]


def cmd_report(args) -> None:
    for line in report_lines(since=args.since):
        print(line)


def cmd_todo(args) -> None:
    got = load()["rows"]
    todo = [r for r in inquiries() if r["result"] in ("종료", "잠듦") and key(r) not in got]
    todo.sort(key=lambda r: r["date"])
    print(f"이유를 안 적은 종료·잠듦 문의 {len(todo)}건, 오늘 {min(args.n, len(todo))}건:")
    for r in todo[: args.n]:
        print(f"  {r['date']} | {r['place'] or '지역 없음'} | nth {r['nth']} | {r['result']}")
    print("이유는 하나만: " + " / ".join(f"{k}({REASON_NOTE[k]})" for k in REASONS))


def cmd_set(args) -> None:
    if args.reason not in REASONS:
        sys.exit(f"이유는 {', '.join(REASONS)} 중 하나")
    if args.src not in SRCS:
        sys.exit(f"근거는 {', '.join(SRCS)} 중 하나")
    match = [r for r in inquiries() if r["date"] == args.date and r["place"] == args.place and r["nth"] == args.nth]
    if not match:
        sys.exit("그 날짜·곳의 문의 줄이 없음(todo 출력 그대로 쓰기)")
    data = load()
    data["rows"][key(match[0])] = {"result": match[0]["result"], "reason": args.reason, "src": args.src,
                                   "on": kst_today().isoformat()}
    save(data)
    print(f"적음: {args.date} {args.place} → {args.reason}({args.src})")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("--since", default="")
    td = sub.add_parser("todo")
    td.add_argument("--n", type=int, default=10)
    st = sub.add_parser("set")
    st.add_argument("date")
    st.add_argument("place")
    st.add_argument("reason")
    st.add_argument("--src", default="통화표")
    st.add_argument("--nth", type=int, default=1)
    args = ap.parse_args()
    {"report": cmd_report, "todo": cmd_todo, "set": cmd_set}[args.cmd](args)


if __name__ == "__main__":
    main()
