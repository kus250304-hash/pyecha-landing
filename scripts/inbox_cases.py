"""
PC "사례 가져오기" 앞 단계: 구글 드라이브 인박스(G:\\내 드라이브\\폐차_인박스)에 휴대폰으로 올린 파일을
한 차씩 묶어 원본 폴더(폐차사진원본\\우선\\날짜_지역_차종)로 옮긴다. 설계는 docs/case-pipeline-2026-10-16.md [1].

순서
  python scripts/inbox_cases.py scan      인박스 파일을 올린 시간으로 묶기(30분 넘게 떨어지면 다른 차)
      → .cases_staging/inbox/gN/ 에 미리보기(위치 정보 지움)·영상 끝 5초 말(말.txt)·plan.json
      → Claude 가 미리보기와 말을 보고 .cases_staging/inbox/gN/answer.json 을 쓴다(형식은 아래)
  python scripts/inbox_cases.py apply gN  지역 검사 → 원본 우선/ 에 폴더 만들고 파일 옮기기, 등록증은 지우기
  python scripts/inbox_cases.py report    오늘 만든 폴더·보류(확인 필요) 요약, cases/input/인박스-확인-필요.md 다시 쓰기

지역 알아내는 순서: ① 영상 마지막 5초의 말 ② 위치 정보(GPS) ③ 등록증 사진(지역만 읽고 파일은 지움).
  - GPS 가 거래처 폐차장·수출 사무실(data/partner_locations.json) 근처면 무시한다.
  - 거래처 주소가 아직 비어 있으면(2026-10-16) GPS 로만 정한 지역은 쓰지 않고 보류한다.
  - GPS 좌표는 PC 안(미리보기 폴더·보고)에만 두고 저장소에 올리지 않는다.

answer.json 형식 (Claude 가 씀)
  {"지역": "전남광주통합특별시 목포시 용해동", "지역근거": "말",          ← 말 / 등록증 / GPS
   "차종": "에쿠스", "연식": "2010", "시동": "시동됨", "운행": "운행 가능",
   "상황": "차령초과말소", "처리": "",
   "차번호": "", "압류": "",                                             ← 간편조회 캡처에서(원본 메모에만 남음)
   "등록증": ["IMG_0003.jpg"], "조회": ["Screenshot_1.png"],              ← 원본 파일 이름
   "보류": ""}                                                            ← 지역을 모르면 "확인 필요: <쉬운 말>"
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cases import load_csv_rows, resolve_region  # noqa: E402
from build_site import load_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INBOX_DEFAULT = r"G:\내 드라이브\폐차_인박스"
SRC_DEFAULT = r"C:\Users\AOMG\Documents\카카오톡 받은 파일\폐차사진원본"
STAGING = ROOT / ".cases_staging" / "inbox"
PARTNERS = ROOT / "data" / "partner_locations.json"
HOLD_MD = ROOT / "cases" / "input" / "인박스-확인-필요.md"
VIDEO_EXT = {".mp4", ".mov", ".3gp", ".m4v"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".amr"}
TEXT_EXT = {".txt"}     # 대본·녹음용 문장(사례 페이지 "영상에서 한 말"로 감, [3])
GROUP_GAP_MIN = 30      # 올린 시간이 이보다 떨어지면 다른 차
TAIL_SEC = 5            # 영상 마지막 몇 초의 말을 읽나
AUDIO_MAX_SEC = 60      # 녹음은 앞 60초만 글로 바꾼다
MEMO_KEYS = ("날짜", "지역", "차종", "연식", "시동", "운행", "상황", "처리", "차번호", "압류")


def kind_of(p: Path) -> str:
    e = p.suffix.lower()
    return ("video" if e in VIDEO_EXT else "image" if e in IMAGE_EXT else "audio" if e in AUDIO_EXT
            else "text" if e in TEXT_EXT else "")


def inbox_files(inbox: Path) -> list[Path]:
    return sorted((p for p in inbox.iterdir() if p.is_file() and kind_of(p)), key=lambda p: p.stat().st_mtime)


def group_files(files: list[Path]) -> list[list[Path]]:
    groups: list[list[Path]] = []
    last = None
    for p in files:
        t = p.stat().st_mtime
        if last is None or t - last > GROUP_GAP_MIN * 60:
            groups.append([])
        groups[-1].append(p)
        last = t
    return groups


# ---- 위치 정보 ----
def _dms(v) -> float:
    d, m, s = (float(x) for x in v)
    return d + m / 60 + s / 3600


def image_gps(p: Path):
    try:
        from PIL import Image
        with Image.open(p) as im:
            g = im.getexif().get_ifd(0x8825)
        if 2 in g and 4 in g:
            lat, lon = _dms(g[2]), _dms(g[4])
            return (-lat if g.get(1) == "S" else lat, -lon if g.get(3) == "W" else lon)
    except Exception:
        pass
    return None


def ffprobe_json(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(p)],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout or "{}").get("format", {})


def video_gps(p: Path):
    tags = ffprobe_json(p).get("tags", {})
    for k, v in tags.items():
        if "location" in k.lower() and (m := re.match(r"([+-]\d+\.\d+)([+-]\d+\.\d+)", v)):
            return float(m.group(1)), float(m.group(2))
    return None


def near_partner(lat: float, lon: float) -> str:
    for pt in load_json(PARTNERS, default=[]) or []:
        if pt.get("lat") is None or pt.get("lon") is None:
            continue
        dy = (lat - pt["lat"]) * 111_000
        dx = (lon - pt["lon"]) * 111_000 * math.cos(math.radians(lat))
        if math.hypot(dx, dy) <= pt.get("radius_m", 700):
            return pt["name"]
    return ""


def partners_ready() -> bool:
    pts = load_json(PARTNERS, default=[]) or []
    return bool(pts) and all(pt.get("lat") is not None for pt in pts)


# ---- 말 → 글 ----
_model = None


def transcribe(audio: Path) -> str:
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("medium", device="cpu", compute_type="int8")
    import wave
    import numpy as np
    with wave.open(str(audio), "rb") as w:  # ffmpeg 가 만든 16kHz 모노 wav 를 직접 읽는다(av 버전 문제 피함)
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    segs, _ = _model.transcribe(pcm, language="ko", vad_filter=True)
    return " ".join(s.text.strip() for s in segs).strip()


def speech_of(p: Path, work: Path) -> str:
    wav = work / f"{p.stem}.wav"
    if kind_of(p) == "video":
        dur = float(ffprobe_json(p).get("duration") or 0)
        start = max(0.0, dur - TAIL_SEC)
        cmd = ["ffmpeg", "-y", "-v", "quiet", "-ss", f"{start:.2f}", "-i", str(p), "-vn", "-ac", "1", "-ar", "16000", str(wav)]
    else:
        cmd = ["ffmpeg", "-y", "-v", "quiet", "-i", str(p), "-t", str(AUDIO_MAX_SEC), "-vn", "-ac", "1", "-ar", "16000", str(wav)]
    if subprocess.run(cmd).returncode != 0 or not wav.exists():
        return ""
    try:
        return transcribe(wav)
    finally:
        wav.unlink(missing_ok=True)


# ---- 미리보기(위치 정보 없는 새 파일) ----
def preview_image(p: Path, out: Path) -> bool:
    from PIL import Image, ImageOps
    try:
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((1400, 1400))
            Image.frombytes("RGB", im.size, im.tobytes()).save(out, "JPEG", quality=85)
        return True
    except Exception:
        return False


def preview_video(p: Path, out: Path) -> bool:
    dur = float(ffprobe_json(p).get("duration") or 0)
    t = max(0.0, (dur - TAIL_SEC) / 2)
    tmp = out.with_suffix(".tmp.jpg")
    r = subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1",
                        "-map_metadata", "-1", str(tmp)])
    if r.returncode != 0 or not tmp.exists():
        return False
    ok = preview_image(tmp, out)
    tmp.unlink(missing_ok=True)
    return ok


# ---- 명령 ----
def cmd_scan(args) -> None:
    inbox = Path(args.inbox)
    if not inbox.exists():
        inbox.mkdir(parents=True)
        print(f"인박스를 만들었습니다: {inbox}")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    groups = group_files(inbox_files(inbox))
    plan = {"date": date.today().isoformat(), "inbox": str(inbox), "groups": {}}
    for gi, files in enumerate(groups, 1):
        gid = f"g{gi}"
        d = STAGING / gid
        d.mkdir()
        items, speech, gps = [], [], []
        for fi, p in enumerate(files, 1):
            k = kind_of(p)
            item = {"file": p.name, "kind": k, "time": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
            if k in ("image", "video"):
                prev = f"{k[0]}{fi:02d}.jpg"
                if (preview_image if k == "image" else preview_video)(p, d / prev):
                    item["preview"] = prev
                pos = image_gps(p) if k == "image" else video_gps(p)
                if pos:
                    item["gps"] = [round(pos[0], 5), round(pos[1], 5)]
                    item["gps_partner"] = near_partner(*pos)
                    if not item["gps_partner"]:
                        gps.append(item["gps"])
            if k in ("video", "audio"):
                text = speech_of(p, d)
                if text:
                    item["speech"] = text
                    speech.append(f"[{p.name}] {text}")
            items.append(item)
        (d / "말.txt").write_text("\n".join(speech) + "\n", encoding="utf-8")
        plan["groups"][gid] = {"files": items, "speech": speech, "gps": gps,
                               "gps_usable": partners_ready(), "status": "scanned"}
    (STAGING / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"인박스 파일 {sum(len(g) for g in groups)}개 → {len(groups)}대로 묶음 ({STAGING.relative_to(ROOT)})")
    for gid, g in plan["groups"].items():
        kinds = {k: sum(1 for i in g["files"] if i["kind"] == k) for k in ("video", "image", "audio")}
        print(f"  {gid}: 영상 {kinds['video']} · 사진 {kinds['image']} · 녹음 {kinds['audio']}, "
              f"{g['files'][0]['time']}~{g['files'][-1]['time']}")
        for s in g["speech"]:
            print(f"     말: {s}")
        if g["gps"]:
            print(f"     위치 정보 {len(g['gps'])}개" + ("" if g["gps_usable"] else " (거래처 주소 미등록이라 지역으로 쓰지 않음)"))
    if not partners_ready():
        print("※ data/partner_locations.json 에 거래처 좌표가 비어 있어 GPS 로만 정한 지역은 보류합니다")


def load_plan() -> dict:
    plan = load_json(STAGING / "plan.json", default=None)
    if not plan:
        raise SystemExit("먼저 scan 을 실행하세요")
    return plan


def save_plan(plan: dict) -> None:
    (STAGING / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "", s)


def cmd_apply(args) -> None:
    plan = load_plan()
    g = plan["groups"].get(args.gid)
    if not g:
        raise SystemExit(f"{args.gid} 가 없습니다")
    ans = load_json(STAGING / args.gid / "answer.json", default=None)
    if not ans:
        raise SystemExit(f"{args.gid}: answer.json 을 먼저 쓰세요")
    inbox = Path(plan["inbox"])
    names = {i["file"] for i in g["files"]}
    for k in ("등록증", "조회"):
        bad = [n for n in ans.get(k, []) if n not in names]
        if bad:
            raise SystemExit(f"{args.gid}: {k} 파일 이름이 이 묶음에 없습니다: {bad}")

    # 등록증은 지역만 읽고 바로 지운다(드라이브 휴지통으로 감, 30일 안에 되살릴 수 있음). 저장소·공개에 넣지 않는다
    for n in ans.get("등록증", []):
        (inbox / n).unlink(missing_ok=True)
    g["files"] = [i for i in g["files"] if i["file"] not in set(ans.get("등록증", []))]

    hold = (ans.get("보류") or "").strip()
    src_kind = ans.get("지역근거", "")
    region, why = (None, "")
    if not hold:
        if src_kind not in ("말", "등록증", "GPS"):
            hold = "확인 필요: 지역근거가 말·등록증·GPS 중 하나가 아님"
        elif src_kind == "GPS" and not partners_ready():
            hold = "확인 필요: 위치 정보로만 지역을 추정함(거래처 주소 미등록)"
        else:
            region, why = resolve_region(ans.get("지역", ""), load_csv_rows())
            if not region:
                hold = f"확인 필요: 지역 '{ans.get('지역', '')}' — {why}"
            elif not ans.get("차종"):
                hold = "확인 필요: 차종 모름"
    if hold:
        g.update(status="held", hold=hold, car=ans.get("차종", ""))
        save_plan(plan)
        print(f"{args.gid}: 보류 — {hold} (파일은 인박스에 그대로 둠)")
        return

    first = min(datetime.strptime(i["time"], "%Y-%m-%d %H:%M") for i in g["files"])
    car = safe_name(ans["차종"])
    year = re.sub(r"\D", "", ans.get("연식", ""))[:4]
    situ = safe_name(ans.get("상황", "")) or "일반폐차"
    base = f"{first:%Y%m%d}_{region['dong'] or region['sigungu'].split()[-1]}_{car}{year}_{situ}"
    src = Path(args.src) / "우선"
    dest, n = src / base, 2
    while dest.exists():
        dest, n = src / f"{base}_{n}", n + 1
    (dest / "자료").mkdir(parents=True)

    memo = {k: (ans.get(k) or "").strip() for k in MEMO_KEYS}
    memo["날짜"] = f"{first:%Y-%m-%d}"
    memo["지역"] = " ".join(x for x in (region["sido"], region["sigungu"], region["dong"]) if x)
    lines = "".join(f"{k}: {memo[k]}\n" for k in MEMO_KEYS if memo[k])
    lines += f"출처: 인박스 {datetime.now():%Y-%m-%d} (지역 근거: {src_kind})\n"
    (dest / "메모.txt").write_text(lines, encoding="utf-8")
    if g["speech"]:
        (dest / "자료" / "말.txt").write_text("\n".join(g["speech"]) + "\n", encoding="utf-8")
    side = set(ans.get("조회", []))
    for i in g["files"]:
        p = inbox / i["file"]
        if not p.exists():
            continue
        # 사진·영상은 폴더 바로 아래(사례 사진 후보), 조회 캡처·녹음은 자료/ (사례 사진으로 뽑히지 않음)
        if i["kind"] == "text":  # 첫 대본은 폴더 바로 아래 대본.txt(사례 페이지로 감), 나머지는 자료/
            to = dest / "대본.txt" if not (dest / "대본.txt").exists() else dest / "자료" / i["file"]
            shutil.move(str(p), str(to))
            continue
        to = dest / "자료" if (i["file"] in side or i["kind"] == "audio") else dest
        shutil.move(str(p), str(to / i["file"]))
    g.update(status="applied", folder=f"우선\\{dest.name}", car=ans["차종"], region=memo["지역"])
    save_plan(plan)
    print(f"{args.gid}: 원본 폴더 만듦 → 우선\\{dest.name} (지역 근거: {src_kind})")


def cmd_report(args) -> None:
    plan = load_json(STAGING / "plan.json", default=None) or {"groups": {}}
    made = [g for g in plan["groups"].values() if g.get("status") == "applied"]
    held = [g for g in plan["groups"].values() if g.get("status") != "applied"]
    print(f"인박스: 폴더 만든 차 {len(made)}대, 보류 {len(held)}대")
    for g in made:
        print(f"  만듦: {g['folder']}")
    rows = []
    for g in held:
        t = g["files"][0]["time"] if g["files"] else ""
        kinds = {k: sum(1 for i in g["files"] if i["kind"] == k) for k in ("video", "image", "audio")}
        reason = g.get("hold") or "확인 필요: answer.json 을 쓰지 않음"
        print(f"  보류: {t} 올린 차({g.get('car') or '차종 모름'}) — {reason}")
        # 저장소에 올라가는 목록: 올린 시각·파일 수·차종·이유만(위치·차번호·말은 넣지 않음)
        rows.append(f"| {t} | 영상 {kinds['video']} · 사진 {kinds['image']} · 녹음 {kinds['audio']} | "
                    f"{g.get('car') or '모름'} | {reason} |")
    HOLD_MD.parent.mkdir(parents=True, exist_ok=True)
    HOLD_MD.write_text(
        "# 인박스 확인 필요 (PC 사례 가져오기가 매일 다시 씀)\n\n"
        "구글 드라이브 `폐차_인박스` 에 올린 차 중 지역·차종을 알아내지 못해 보류한 것입니다. "
        "파일은 인박스에 그대로 있습니다. 영상 끝에 지역을 다시 말해 올리거나 병한님이 알려 주시면 다음 실행 때 들어갑니다.\n\n"
        f"기준: {date.today().isoformat()}\n\n"
        + ("| 올린 시각 | 파일 | 차종 | 이유 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n" if rows else "보류된 차 없음\n"),
        encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--inbox", default=INBOX_DEFAULT)
    a = sub.add_parser("apply")
    a.add_argument("gid")
    a.add_argument("--src", default=SRC_DEFAULT)
    sub.add_parser("report")
    args = ap.parse_args()
    {"scan": cmd_scan, "apply": cmd_apply, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
