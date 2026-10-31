"""
PC(운영자 컴퓨터)에서 돌리는 "월 1회 FAQ 풀 갱신" 실행기(2026-10-31). 지시문은 docs/monthly-faq-refresh-prompt.md 의 코드 상자.
작업 스케줄러 "폐차_FAQ_월간갱신"(매달 첫째 월요일 오후 2시 30분, 놓치면 켜질 때 바로)이 pythonw 로 부른다.
통화 인박스(병한-업무위키\\_도구\\통화인박스.py)와 같은 방식: 창 없이, claude -p 를 허용 목록 + --permission-prompts none 으로.

사용법
  pythonw scripts\\pc_faq_refresh.py            예약 작업이 부르는 꼴(이달 기록이 이미 있으면 건너뜀)
  python  scripts\\pc_faq_refresh.py --check    claude 위치·명령만 보여 주고 끝(아무것도 안 함)
  python  scripts\\pc_faq_refresh.py --force    이달 기록이 있어도 다시

- 작업 폴더에 커밋 안 된 변경(다른 PC 예약 작업이 도는 중)이 있으면 5분마다 다시 보고, 90분 지나도 그대로면 건너뛴다
  (그달은 아침 보고가 "안 돌았음"으로 알림).
- 통화 원문·고객 목록(transcripts·문자·통화표·통화별표시·원본목록)은 읽기를 막는다.
- 로그: 통화녹음백업\\_분석\\폐차_FAQ_log.txt (통화인박스_log.txt 옆), claude 출력 전체: 같은 폴더 폐차_FAQ_마지막출력.txt
"""
import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANA = Path(r"C:\Users\AOMG\Documents\통화녹음백업\_분석")
LOG = ANA / "폐차_FAQ_log.txt"
LAST_OUT = ANA / "폐차_FAQ_마지막출력.txt"
LOCK = ANA / "폐차_FAQ.lock"
TEMP_DIR = Path(r"C:\Users\AOMG\AppData\Local\Temp\pyecha_faq")
RECORD = ROOT / "docs" / "faq-refresh-log.md"

PROMPT = "docs/monthly-faq-refresh-prompt.md 의 코드 상자 지시문을 처음부터 끝까지 그대로 실행해."
CLAUDE_TOOLS = ("Read,Write,Edit,Glob,Grep,Bash(git *),Bash(python *),Bash(py *),"
                "PowerShell(git *),PowerShell(python *),PowerShell(py *)")
_ANA = "//c/Users/AOMG/Documents/통화녹음백업/_분석"
BLOCKED = ",".join(f"Read({_ANA}/{p})" for p in ("transcripts/**", "문자/**", "통화표.csv", "통화별표시.csv", "원본목록.csv"))
RUN_TIMEOUT = 90 * 60
CLEAN_WAIT = 90 * 60
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def log(msg):
    ANA.mkdir(parents=True, exist_ok=True)
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if sys.stdout:            # pythonw(창 없이 실행)에서는 None
        print(line, flush=True)


def run_quiet(cmd, timeout, **kw):
    """창 없이: 입력 끊고 출력은 받아서 로그로만."""
    return subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
                          creationflags=NO_WINDOW, **kw)


def claude_exe():
    """통화인박스.py 와 같은 순서: PATH → ~/.local/bin → 데스크톱 앱 안의 가장 새 claude.exe."""
    for c in (shutil.which("claude"), str(Path.home() / ".local" / "bin" / "claude.exe")):
        if c and Path(c).exists():
            return c
    cands = sorted(Path(os.environ.get("LOCALAPPDATA", "")).glob("Claude-Data/*/claude-code/*/*/claude.exe"),
                   key=lambda p: p.stat().st_mtime)
    return str(cands[-1]) if cands else ""


def git_exe():
    return shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"


def this_month_done():
    """docs/faq-refresh-log.md 맨 위 기록이 이달이면 True."""
    if not RECORD.exists():
        return False
    m = re.search(r"^## (\d{4}-\d{2})-\d{2}", RECORD.read_text(encoding="utf-8"), re.M)
    return bool(m) and m.group(1) == f"{dt.date.today():%Y-%m}"


def dirty():
    r = run_quiet([git_exe(), "status", "--porcelain", "--untracked-files=no"], 60, cwd=str(ROOT), text=True)
    return r.returncode != 0 or bool(r.stdout.strip())


def command(exe):
    return [exe, "-p", PROMPT, "--allowedTools", CLAUDE_TOOLS, "--disallowedTools", BLOCKED,
            "--permission-prompts", "none", "--add-dir", str(ANA), "--add-dir", str(TEMP_DIR)]


def refresh(force):
    if this_month_done() and not force:
        log("이달 기록이 이미 있음 → 건너뜀")
        return
    exe = claude_exe()
    if not exe:
        log("claude 명령을 못 찾음 → 이달 FAQ 갱신 안 함 (Claude 앱 설치·로그인 확인)")
        return
    waited = 0
    while dirty():
        if waited >= CLEAN_WAIT:
            log("작업 폴더에 커밋 안 된 변경이 90분째 남아 있음 → 이달 FAQ 갱신 건너뜀 (git status 확인)")
            return
        time.sleep(300)
        waited += 300
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    log("FAQ 갱신 시작" + (f" ({waited // 60}분 기다림)" if waited else ""))
    try:
        p = run_quiet(command(exe), RUN_TIMEOUT, cwd=str(ROOT), text=True, encoding="utf-8", env=env)
    except subprocess.TimeoutExpired:
        log("FAQ 갱신 90분 넘음 → 멈춤 (폐차_FAQ_마지막출력.txt·git status 확인)")
        return
    LAST_OUT.write_text((p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""), encoding="utf-8")
    out = (p.stdout or p.stderr or "").strip().splitlines()
    log(f"FAQ 갱신 → 종료코드 {p.returncode}: {(out[-1] if out else '')[:160]}")
    if "Not logged in" in (p.stdout or "") + (p.stderr or ""):
        log("claude 로그인 필요 → 터미널에서 claude 한 번 실행해 로그인")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="claude 위치·명령만 보여 주고 끝")
    ap.add_argument("--force", action="store_true", help="이달 기록이 있어도 다시")
    a = ap.parse_args()
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    if a.check:
        exe = claude_exe()
        print("claude:", exe or "(못 찾음)")
        print("이달 기록 있음:", this_month_done(), "· 작업 폴더 변경 있음:", dirty())
        print("명령:", subprocess.list2cmdline(command(exe or "claude")))
        return
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3 * 3600:
        log("이미 도는 중 — 건너뜀")
        return
    LOCK.write_text(str(os.getpid()))
    try:
        refresh(a.force)
    except Exception:            # pythonw 라 화면에 안 보이므로 오류는 로그 파일로만
        import traceback
        log("오류:\n" + traceback.format_exc()[-1500:])
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
