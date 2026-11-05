"""
구 페이지 "손님 후기" 칸 재료(2026-11-05 병한님, 상자 B-1 2번).
병한님이 말소증 문자 끝에 한 줄 후기를 부탁하고, 답장이 오면 캡처해서 구글 드라이브 폐차_인박스에 올린다.
파일 이름이나 폴더 이름에 "후기"가 들어간 것만 이 스크립트가 다룬다(inbox_cases.py 는 이런 파일을 차 묶음에 넣지 않음).

순서(PC 예약 작업 "폐차 사례 가져오기" 3-6 단계)
  python scripts/reviews.py scan        후기 캡처를 .cases_staging/reviews/rN.jpg 미리보기(숨은 정보 지움)와 plan.json 으로
      → Claude 가 미리보기를 보고 .cases_staging/reviews/answer.json 을 쓴다(형식은 아래)
  python scripts/reviews.py apply       검사 → data/reviews.json 에 더하고 원본은 인박스 _후기_반영됨/ 으로 옮김,
                                        못 쓴 것은 docs/reviews-pending.md "확인 필요"에 남김(원본은 인박스에 그대로)
  python scripts/reviews.py report      지금 후기 수·확인 필요 수

answer.json (Claude 가 씀)
  {"r1": {"지역": "경북 구미", "차종": "쏘나타", "후기": "말소증 문자로 바로 와서 편했어요", "월": "2026-11"},
   "r2": {"보류": "확인 필요: 어느 차 손님인지 모름"}}
  - "후기"는 손님이 쓴 문장 한두 개를 그대로(맞춤법만 바로잡지 않음). 이름은 "○○님"으로 바꾸고, 전화·차번호·금액·폐차장 이름·
    주소·날짜 숫자가 든 문장은 빼고 옮긴다. 남는 문장이 없으면 보류.
  - 지역은 캡처 속 대화·파일 이름·병한님 알림에서 시·군까지 확인될 때만. 모르면 보류("확인 필요: 지역을 모름").
  - 월 = 후기를 받은 달(캡처 날짜, 없으면 올린 날).

저장소에는 지역(시·군)·차종·후기 문장·월만 들어간다. 캡처 원본·이름·번호는 PC(드라이브)에만 있다.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ledger_read as L  # noqa: E402
from build_cases import banned_text  # noqa: E402
from sitemap_lib import today  # noqa: E402

INBOX_DEFAULT = r"G:\내 드라이브\폐차_인박스"
DONE_DIR = "_후기_반영됨"
STAGING = ROOT / ".cases_staging" / "reviews"
OUT = ROOT / "data" / "reviews.json"
PENDING = ROOT / "docs" / "reviews-pending.md"
WORD = "후기"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
OK_TITLES = {"기사님", "사장님", "대표님", "실장님", "선생님", "고객님", "손님", "○○님"}


def is_review(p: Path, inbox: Path) -> bool:
    rel = p.relative_to(inbox)
    return (p.is_file() and DONE_DIR not in rel.parts and (p.suffix.lower() in IMAGE_EXT or p.suffix.lower() == ".txt")
            and any(WORD in part for part in rel.parts))


def review_files(inbox: Path) -> list[Path]:
    return sorted((p for p in inbox.rglob("*") if is_review(p, inbox)), key=lambda p: p.stat().st_mtime) if inbox.exists() else []


def text_problem(text: str) -> str:
    text = (text or "").strip()
    if not 4 <= len(text) <= 200:
        return "후기 글이 비었거나 200자를 넘음"
    if why := banned_text(text):
        return why
    if re.search(r"\d{3,}", text):
        return "숫자(전화·차번호·금액으로 보일 수 있음)가 있음"
    for m in re.finditer(r"[가-힣○]{1,3}님", text):
        if m.group(0) not in OK_TITLES and not m.group(0).endswith("○○님"):
            return f"이름으로 보이는 '{m.group(0)}' 이 있음(○○님으로 바꿔 주세요)"
    return ""


def cmd_scan(args) -> None:
    inbox = Path(args.inbox)
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    plan = {"date": today(), "inbox": str(inbox), "items": {}}
    for i, p in enumerate(review_files(inbox), 1):
        rid = f"r{i}"
        item = {"file": p.relative_to(inbox).as_posix(), "time": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
        if p.suffix.lower() == ".txt":
            (STAGING / f"{rid}.txt").write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            item["preview"] = f"{rid}.txt"
        else:
            from inbox_cases import preview_image
            if preview_image(p, STAGING / f"{rid}.jpg"):
                item["preview"] = f"{rid}.jpg"
        plan["items"][rid] = item
    (STAGING / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"후기 캡처 {len(plan['items'])}개 → {STAGING.relative_to(ROOT).as_posix()}"
          + ("" if plan["items"] else " (없음)"))
    for rid, it in plan["items"].items():
        print(f"  {rid}: 올린 시각 {it['time']} · 미리보기 {it.get('preview', '만들지 못함')}")


def load_out() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {
        "rule": "폐차_인박스 후기 캡처에서 뽑은 글자(scripts/reviews.py). 지역은 시·군, 이름·전화·차번호·금액 없음", "reviews": []}


def write_pending(rows: list[tuple[str, str]]) -> None:
    head = ("# 손님 후기 — 확인 필요\n\n`scripts/reviews.py apply` 가 다시 씁니다(손으로 고치지 않음). "
            "원본 캡처는 폐차_인박스에 그대로 있습니다. 지역·어느 차인지 알려 주시면 다음 실행 때 들어갑니다.\n"
            "파일 이름은 적지 않습니다(이름이 들어 있을 수 있음).\n\n")
    body = "| 올린 시각 | 이유 |\n|---|---|\n" + "".join(f"| {t} | {why} |\n" for t, why in rows) if rows else "확인 필요 없음\n"
    PENDING.write_text(head + body, encoding="utf-8")


def cmd_apply(args) -> None:
    plan = json.loads((STAGING / "plan.json").read_text(encoding="utf-8")) if (STAGING / "plan.json").exists() else None
    if not plan:
        raise SystemExit("먼저 scan 을 돌리세요")
    answers = json.loads((STAGING / "answer.json").read_text(encoding="utf-8")) if (STAGING / "answer.json").exists() else {}
    inbox = Path(plan["inbox"])
    out = load_out()
    have = {r["id"] for r in out["reviews"]}
    places = L.gu_places()
    added, pending = 0, []
    for rid, it in plan["items"].items():
        a = answers.get(rid) or {"보류": "확인 필요: answer.json 에 이 캡처 답이 없음"}
        src = inbox / it["file"]
        why = (a.get("보류") or "").strip()
        key = None
        if not why:
            key = L.city_of(a.get("지역", ""), places)
            month = a.get("월", "")
            why = ("확인 필요: 지역을 구 페이지가 있는 시·군으로 못 정함" if not key
                   else "확인 필요: 월이 YYYY-MM 꼴이 아님" if not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", month)
                   else ("확인 필요: " + p) if (p := text_problem(a.get("후기", ""))) else "")
        if why:
            pending.append((it["time"], why))
            continue
        rid_hash = hashlib.sha1(src.read_bytes()).hexdigest()[:12] if src.exists() else rid
        if rid_hash not in have:
            out["reviews"].append({"id": rid_hash, "sido": key[0], "city": key[1], "car": L.car_name(a.get("차종", "")),
                                   "text": a["후기"].strip(), "month": a["월"], "added": today()})
            have.add(rid_hash)
            added += 1
        if src.exists():
            dest = inbox / DONE_DIR / src.name
            dest.parent.mkdir(exist_ok=True)
            shutil.move(str(src), str(dest))
    if added:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_pending(pending)
    print(f"손님 후기: 더함 {added}개 · 확인 필요 {len(pending)}개 · 전체 {len(out['reviews'])}개")
    for t, why in pending:
        print(f"  확인 필요 {t}: {why}")


def cmd_report(args) -> None:
    n = len(load_out()["reviews"])
    pend = PENDING.read_text(encoding="utf-8").count("\n| 20") if PENDING.exists() else 0
    print(f"손님 후기 {n}개 · 확인 필요 {pend}개")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--inbox", default=INBOX_DEFAULT)
    sub.add_parser("apply")
    sub.add_parser("report")
    args = ap.parse_args()
    {"scan": cmd_scan, "apply": cmd_apply, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
