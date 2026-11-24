"""
PC 상태 기록(2026-11-24 병한님 "알아서 해줘").
캘린더 고장 점검(클로드 예약 작업 "폐차 고장 점검 (아침·저녁)")은 PC 폴더를 읽지 못한다. 그래서 PC가 스스로
아홉 가지 자료 흐름이 '마지막으로 돈 시각'과 성공 여부만 data/pc_health.json 에 적어 올리고, 점검은 그 파일을 읽는다.
PC가 꺼져 있거나 낮 작업이 안 돌면 이 기록이 안 와서, 그게 곧 경보가 된다.

사용법
  python scripts/pc_health.py            읽어서 화면에만 보여 줌(파일 안 씀)
  python scripts/pc_health.py --write    data/pc_health.json 에 씀
  python scripts/pc_health.py --push     PC 예약 작업 "폐차 사례 가져오기" 2-5 단계용: 쓰고 그 파일 하나만 커밋·푸시

- 읽는 것은 시각과 성공/실패뿐이다. 파일 이름·통화 내용·이름·전화번호는 읽어 오지도 쓰지도 않는다.
  json 에 들어가는 것은 시각·참/거짓·건수·아래에 적힌 고정 문구뿐이다(저장소가 공개라서).
- 보는 곳(모두 C:\\Users\\AOMG\\Documents 아래, 시험할 때는 환경 변수 PC_DOCS 로 바꿈)
    통화 인박스      통화녹음백업\\_분석\\통화인박스_log.txt 마지막 줄 시각
    통화 녹음 올리기  통화녹음백업\\_분석\\통화인박스_처리.json 안 "_YYMMDD_HHMMSS" 중 가장 늦은 시각
    문자 백업        같은 파일 안 "sms-YYYYMMDDHHMMSS" 중 가장 늦은 시각
    밤 백업          통화녹음백업\\_분석\\폐차_백업_log.txt 마지막 줄 시각 + "성공"
    영상공장         병한-업무위키\\마케팅\\주간\\영상공장_마지막실행.txt 시각 + "성공"("새 것 없음"도 정상)
    주간 꾸러미      병한-업무위키\\마케팅\\주간\\마지막실행.txt 시각 + "성공"
    FAQ 월간 갱신    통화녹음백업\\_분석\\폐차_FAQ_log.txt 마지막 줄 시각
    캘린더→기록부    병한-업무위키\\폐차\\거래기록부\\_캘린더\\보고_YYYY-MM-DD.md (어제 것이 있는지, "확인 필요 N건")
    블로그 공개      (PC 폴더가 아니라) 블로그 공개 목록(RSS)의 마지막 공개 날짜·최근 7일·28일 편수 + 저장소 초안 가운데 아직 안 나간 것
                     (2026-11-24 병한님 "쌓인 초안 더 자주": 클라우드는 공개 목록을 못 읽어 초안이 나가는지 알 수 없었음.
                      공개된 글의 날짜와 저장소 초안 이름만 적는다. 예약만 걸린 글은 '안 나감'에 들어간다. 못 읽으면 판단 안 함)
- 기준(LIMITS)을 넘으면 problems 에 한 줄씩("무엇 — 마지막 시각 — 할 일"). 통화 인박스가 멈춰 있으면 통화 녹음·문자 백업은
  판단하지 않는다(인박스가 처리한 기록으로 보는 값이라, 인박스가 멈추면 같이 멈춘 것처럼 보임).
- MODE: "observe" 인 동안 고장 점검은 problems 를 고장으로 세지 않는다(기준이 실제 PC 와 맞는지 먼저 보는 기간).
  맞는 것을 확인한 뒤 "alert" 로 바꾼다. 기록이 안 오는 것(written 이 오늘·어제가 아님)은 MODE 와 상관없이 고장이다.
- 같은 날 두 번 돌면(13:40·13:55) 3시간 안에 적은 기록이 있고 problems 가 같으면 다시 쓰지 않는다.
- 실패해도 종료 코드는 0 이다(사례 가져오기를 막지 않음). 커밋·푸시에 실패하면 고친 파일을 되돌려 작업 폴더를 깨끗하게 둔다.
- 손으로 고치지 않는다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pc_health.json"
DOCS = Path(os.environ.get("PC_DOCS", r"C:\Users\AOMG\Documents"))
ANA = DOCS / "통화녹음백업" / "_분석"
WIKI = DOCS / "병한-업무위키"
WEEKLY = WIKI / "마케팅" / "주간"
CAL_DIRS = [WIKI / "폐차" / "거래기록부" / "_캘린더", WIKI / "폐차" / "거래기록" / "_캘린더"]
KST = timezone(timedelta(hours=9))

MODE = "observe"   # "alert" 로 바꾸면 고장 점검이 problems 를 캘린더에 올린다
SKIP_HOURS = 3     # 이 시간 안에 적은 기록이 있고 problems 가 같으면 다시 쓰지 않음
BLOG_NAME = "블로그 공개"   # scripts/blog_drafts.py 의 PC_BLOG_ITEM 과 같은 글자
BLOG_STALE_DAYS = 8         # 일요일 발행을 한 주 건너뛰면 넘는 날 수(새 글이 며칠 받는 자리라, 한 주 쉬면 그 주는 빈칸)
# 기준(시간). 예전 점검 지시문의 기준에 조금 여유를 둠
LIMITS = {
    "통화 인박스": 1.25,        # 15분마다 도는 작업
    "통화 녹음 올리기": 26,
    "문자 백업": 4,
    "밤 백업": 26,              # 매일 밤 11시 40분
    "영상공장": 26,
    "주간 꾸러미": 8 * 24,      # 매주 토요일 밤 9시
    "FAQ 월간 갱신": 35 * 24,   # 매달 첫째 월요일
}
TODO = {
    "통화 인박스": "클로드가 볼게요",
    "통화 녹음 올리기": "병한님: 본폰 통화 녹음 올리기 앱(DriveSync)이 켜져 있는지, 배터리 '제한 없음'인지",
    "문자 백업": "병한님: SMS Backup & Restore 배터리 '제한 없음' 확인",
    "밤 백업": "클로드가 볼게요",
    "영상공장": "클로드가 볼게요",
    "주간 꾸러미": "클로드가 볼게요",
    "FAQ 월간 갱신": "클로드가 볼게요",
    "캘린더→기록부": "클로드가 볼게요",
}
TS_RE = re.compile(r"^\D{0,3}(\d{4})[-./](\d{1,2})[-./](\d{1,2})[ T_](\d{1,2}):(\d{2})(?::(\d{2}))?")
REC_RE = re.compile(r"_(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})(?!\d)")
SMS_RE = re.compile(r"sms-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)")
NEED_RE = re.compile(r"확인 필요\s*(\d+)\s*건")


def now() -> datetime:
    fake = os.environ.get("PC_HEALTH_NOW")  # 시험용: 2026-11-24T13:45
    return datetime.fromisoformat(fake).replace(tzinfo=KST) if fake else datetime.now(KST)


def iso(t: datetime | None) -> str | None:
    return t.astimezone(KST).isoformat(timespec="minutes") if t else None


def short(t: datetime | None) -> str:
    return f"{t.month}/{t.day} {t:%H:%M}" if t else "기록 없음"


def _dt(parts, year_base: int = 0) -> datetime | None:
    try:
        y, mo, d, h, mi, s = (int(p or 0) for p in parts)
        return datetime(y + year_base, mo, d, h, mi, s, tzinfo=KST)
    except ValueError:
        return None


def tail(path: Path, size: int = 8192) -> str:
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - size))
        return f.read().decode("utf-8-sig", errors="replace")


def last_stamp(path: Path) -> tuple[datetime | None, str, str]:
    """(마지막 시각, 마지막 기록 글, 근거). 시각으로 시작하는 마지막 줄부터 끝까지가 '마지막 기록'이다(한 번 실행이
    여러 줄을 남겨도 됨). 그런 줄이 없으면 파일 수정 시각과 끝부분 전체. 파일이 없으면 (None, "", "없음")."""
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, KST)
        lines = [ln.strip() for ln in tail(path).splitlines() if ln.strip()]
    except OSError:
        return None, "", "없음"
    for i in range(len(lines) - 1, max(-1, len(lines) - 41), -1):
        m = TS_RE.match(lines[i])
        if m and (t := _dt(m.groups())):
            return t, "\n".join(lines[i:]), "줄"
    return mtime, "\n".join(lines[-40:]), "수정시각"


def stamps_in(path: Path, day: datetime) -> tuple[list[datetime], list[datetime], bool]:
    """처리 기록 파일 안의 통화 녹음 시각들·문자 백업 시각들(이름은 읽어 오지 않고 시각만 뽑음)."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return [], [], False
    limit = day + timedelta(days=1)
    rec = sorted({t for m in REC_RE.finditer(text) if (t := _dt(m.groups(), 2000)) and t <= limit})
    sms = sorted({t for m in SMS_RE.finditer(text) if (t := _dt(m.groups())) and t <= limit})
    return rec, sms, True


def age_item(name: str, last: datetime | None, day: datetime, by: str, good: bool | None = None) -> dict:
    item = {"last": iso(last), "by": by, "limit_h": LIMITS[name]}
    if last is None:
        item["ok"] = False
        item["why"] = "기록 없음"
    else:
        age = (day - last).total_seconds() / 3600
        item["age_h"] = round(age, 1)
        item["ok"] = age <= LIMITS[name] and good is not False
        if good is not None:
            item["success"] = good
        if not item["ok"]:
            item["why"] = "마지막 실행이 성공이 아님" if (good is False and age <= LIMITS[name]) else "기준 시간 넘음"
    return item


def blog_item(day: datetime) -> dict:
    """블로그 공개 흐름. 못 읽으면 ok=None(고장으로 세지 않음). 이 칸 때문에 다른 칸 기록이 멈추면 안 된다."""
    try:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import blog_drafts as bd
        pub = bd.public_posts()
        if pub is None:
            return {"ok": None, "why": "공개 목록을 못 읽음"}
        rows = bd.stock_rows(pub, bd.load_state())
        today, dates = day.date(), sorted(pub.values())
        last = dates[-1] if dates else None
        it = {"last": last.isoformat() if last else None,
              "count_7d": sum(1 for d in dates if 0 <= (today - d).days < 7),
              "count_28d": sum(1 for d in dates if 0 <= (today - d).days < 28),
              "stock": len(rows), "stock_cap": bd.STOCK_CAP, "waiting": [bd.draft_key(d) for d in rows],
              "limit_d": BLOG_STALE_DAYS}
        # 하루 한 편씩 나가고 있는지 보려고: 최근 14일에 글이 나간 날(날짜만)과, 저장소 초안의 공개 날짜.
        # 공개 날짜는 지우지 않고 쌓는다(2026-11-24): 공개 목록은 최근 50편쯤만 보여서, 석 달쯤 지난 글은 앞선 기록에서 이어받아야
        # '나간 글'인 줄 안다(안 그러면 안 나간 초안으로 다시 세어져 초안 쓰기가 멈춤). 같은 지역 120일 간격도 이 날짜로 센다.
        it["out_14d"] = [d.isoformat() for d in dates if 0 <= (today - d).days < 14]
        seen = {bd.draft_key(d): on.isoformat() for d in bd.all_drafts() if (on := bd.rss_date(d, pub))}
        kept = {k: v.isoformat() for k, v in bd.pc_published().items()}
        it["published"] = dict(sorted({**kept, **seen}.items()))
        it["ok"] = bool(last) and (today - last).days <= BLOG_STALE_DAYS
        if not it["ok"]:
            it["why"] = f"새 글이 {BLOG_STALE_DAYS}일 넘게 없음"
        return it
    except Exception as e:
        return {"ok": None, "why": f"확인 못 함({type(e).__name__})"}


def collect(day: datetime | None = None) -> dict:
    day = day or now()
    items: dict[str, dict] = {}

    t, _, by = last_stamp(ANA / "통화인박스_log.txt")
    items["통화 인박스"] = age_item("통화 인박스", t, day, by)
    inbox_ok = items["통화 인박스"]["ok"]

    rec, sms, found = stamps_in(ANA / "통화인박스_처리.json", day)
    for name, times in (("통화 녹음 올리기", rec), ("문자 백업", sms)):
        it = age_item(name, times[-1] if times else None, day, "처리 기록" if found else "없음")
        if not inbox_ok:  # 인박스가 멈추면 이 값도 같이 멈춘 것처럼 보인다
            it["ok"], it["why"] = None, "통화 인박스가 멈춰 있어 판단 안 함"
        items[name] = it
    # 통화 시각은 저장소(공개)에 분 단위로 남기지 않는다: 시(時)까지만, 건수는 적지 않음
    it = items["통화 녹음 올리기"]
    if rec:
        it["last"] = iso(rec[-1].replace(minute=0, second=0))
        it["age_h"] = round(it["age_h"])
    recent = [t for t in rec if t >= day - timedelta(days=14)]
    if len(recent) >= 2:  # 기준(26시간)이 맞는지 볼 때 쓰는 숫자: 최근 14일에 녹음 사이가 가장 길게 빈 시간
        it["max_gap_h_14d"] = round(max((b - a).total_seconds() for a, b in zip(recent, recent[1:])) / 3600)

    t, rec_text, by = last_stamp(ANA / "폐차_백업_log.txt")
    items["밤 백업"] = age_item("밤 백업", t, day, by, good=("성공" in rec_text and "실패" not in rec_text) if t else None)

    for name, fname in (("영상공장", "영상공장_마지막실행.txt"), ("주간 꾸러미", "마지막실행.txt")):
        t, rec_text, by = last_stamp(WEEKLY / fname)
        fine = "성공" in rec_text or (name == "영상공장" and "새 것 없음" in rec_text)
        items[name] = age_item(name, t, day, by, good=(fine and "실패" not in rec_text) if t else None)

    t, _, by = last_stamp(ANA / "폐차_FAQ_log.txt")
    items["FAQ 월간 갱신"] = age_item("FAQ 월간 갱신", t, day, by)

    cal = next((d for d in CAL_DIRS if d.is_dir()), None)
    today_f = cal / f"보고_{day:%Y-%m-%d}.md" if cal else None
    yest_f = cal / f"보고_{day - timedelta(days=1):%Y-%m-%d}.md" if cal else None
    has_today, has_yest = bool(today_f and today_f.is_file()), bool(yest_f and yest_f.is_file())
    need = 0
    src = today_f if has_today else yest_f if has_yest else None
    if src:
        try:
            m = NEED_RE.search(src.read_text(encoding="utf-8-sig", errors="replace"))
            need = int(m.group(1)) if m else 0
        except OSError:
            need = 0
    items["캘린더→기록부"] = {"folder": bool(cal), "today": has_today, "yesterday": has_yest, "need_check": need,
                         "ok": bool(cal) and has_yest}
    items[BLOG_NAME] = blog_item(day)

    problems = []
    for name, it in items.items():
        if name == "캘린더→기록부":
            if not it["ok"]:
                problems.append(f"캘린더→기록부 — 어제 보고 파일이 없음 — {TODO[name]}")
            if it["need_check"]:
                problems.append(f"기록부 확인 필요 {it['need_check']}건 — 병한님: 저녁 기록부 보고의 '확인 필요' 줄 보기")
        elif name == BLOG_NAME:
            if it["ok"] is False:
                problems.append(f"{name} — 마지막 {it.get('last') or '기록 없음'}({it['why']}) — 병한님: 일요일 발행판에서 블로그 예약")
        elif it["ok"] is False:
            last = datetime.fromisoformat(it["last"]) if it["last"] else None
            problems.append(f"{name} — 마지막 {short(last)}({it['why']}) — {TODO[name]}")
    return {"written": iso(day), "mode": MODE, "version": 1, "items": items, "problems": problems,
            "note": "시각·참거짓·건수·고정 문구만 적는다. scripts/pc_health.py 가 쓰고 손으로 고치지 않는다."}


def first_line(data: dict, tail_msg: str = "") -> str:
    n = len(data["problems"])
    state = "모두 정상" if not n else f"이상 {n}줄"
    watch = "(관찰 중 — 캘린더에는 아직 안 올림)" if data["mode"] != "alert" and n else ""
    line = f"PC 상태: {len(data['items'])}가지 중 {state}{watch}" + (f" — {tail_msg}" if tail_msg else "")
    b = data["items"].get(BLOG_NAME) or {}
    if b.get("ok") is not None:   # 보고에 한 줄 더: 블로그가 실제로 나가고 있는지
        line += (f"\n  블로그: 최근 7일 공개 {b['count_7d']}편 · 마지막 공개 {b.get('last') or '없음'}"
                 f" · 안 나간 초안 {b['stock']}편(한도 {b['stock_cap']}편)")
    return line


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def restore(rel: str, existed: bool) -> None:
    """커밋에 실패했을 때 작업 폴더를 깨끗하게(다음 PC 작업이 '커밋하지 않은 변경'으로 멈추지 않게)."""
    git("reset", "-q", "--", rel)
    if existed:
        git("checkout", "--", rel)
    else:
        OUT.unlink(missing_ok=True)


def push(data: dict) -> str:
    rel = OUT.relative_to(ROOT).as_posix()
    existed = bool(git("ls-files", "--", rel).stdout.strip())
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    git("add", "--", rel)
    day = data["written"][:10]
    r = git("commit", "-m", f"PC health ({day}): 이상 {len(data['problems'])}줄", "--", rel)
    if r.returncode:
        restore(rel, existed)
        return "커밋 실패(파일 되돌림): " + (r.stderr or r.stdout).strip()[:160]
    for _ in range(2):
        if git("push", "origin", "main").returncode == 0:
            return "푸시 " + git("rev-parse", "--short", "HEAD").stdout.strip()
        git("pull", "--rebase", "--autostash", "origin", "main")
    return "푸시 실패(커밋은 남음, 다음 푸시 때 같이 올라감)"


def recent_same(data: dict) -> str:
    """3시간 안에 적은 기록이 있고 problems 가 같으면 그 시각(HH:MM), 아니면 ""."""
    try:
        old = json.loads(OUT.read_text(encoding="utf-8"))
        t = datetime.fromisoformat(old["written"])
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    new = datetime.fromisoformat(data["written"])
    same = old.get("problems") == data["problems"] and old.get("mode") == data["mode"]
    return f"{t:%H:%M}" if same and timedelta(0) <= new - t <= timedelta(hours=SKIP_HOURS) else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()
    try:
        data = collect()
        if (args.write or args.push) and (at := recent_same(data)):
            print(first_line(data, f"오늘 이미 적음({at})"))
        elif args.push:
            print(first_line(data, push(data)))
        elif args.write:
            OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(first_line(data, "data/pc_health.json 에 씀"))
        else:
            print(first_line(data, "화면에만(파일 안 씀)"))
        for p in data["problems"]:
            print("  - " + p)
    except Exception as e:  # 이 기록 때문에 사례 가져오기가 멈추면 안 된다
        print(f"PC 상태: 기록 실패({type(e).__name__}) — 다음 실행 때 다시")
    sys.exit(0)


if __name__ == "__main__":
    main()
