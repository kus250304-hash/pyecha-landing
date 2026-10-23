"""
PC(운영자 컴퓨터)에서 돌리는 "사례 가져오기" 도구. 원본 사진은 PC 밖으로 나가지 않고,
가리고·줄이고·숨은 정보를 지운 사진과 정리된 메모만 cases/input/ 에 들어간다.
지시문은 docs/pc-case-import-prompt.md 의 코드 상자.

원본 폴더 (기본값, --src 로 바꿀 수 있음)
  C:\\Users\\AOMG\\Documents\\카카오톡 받은 파일\\폐차사진원본
    우선\\<사례 폴더>\\메모.txt + 사진   ← 먼저
    일반\\<사례 폴더>\\메모.txt + 사진   ← 우선이 다 떨어지면
  "문자백업"이 들어간 폴더와 "제외" 폴더는 목록에서 빼고 절대 들어가지 않는다.
  "반영됨.txt" 가 있는 폴더는 이미 가져간 것이라 건너뛴다.

순서
  python scripts/pc_cases.py scan [--n N]        대상 고르기(기본: 밀린 동안 5건, 아니면 3건) → .cases_staging/scan.json
  python scripts/pc_cases.py prepare              고른 건마다 .cases_staging/cN/ 에 미리보기(p01.jpg…)와 모아보기(sheet1.jpg…)
      → 사람(또는 Claude)이 미리보기를 보고 .cases_staging/cN/select.json 을 쓴다 (형식은 아래)
  python scripts/pc_cases.py mask cN              가리기 적용 → .cases_staging/cN/out/1.jpg… (+ out/check.jpg)
      → out 사진을 다시 보고 번호판·얼굴·서류가 조금이라도 보이면 select.json 을 고쳐 다시 mask
  python scripts/pc_cases.py stage cN             cases/input/<폴더>/ 에 사진 + 정리된 메모.txt 를 넣고 검사
  python scripts/pc_cases.py drop cN "<이유>"     이 건은 오늘 쓰지 않음 (원본에 표시하지 않음)
  python scripts/pc_cases.py scan --more          뺀 만큼 새로 고르기 → 다시 prepare (새로 고른 건만 준비)
  python scripts/pc_cases.py scan --no-dong --n 20  동 없이 시군구까지만 적힌 사례만 고르기
  python scripts/pc_cases.py scan --only 퇴촌면,쌍령동  폴더 이름으로 특정 건만 고르기(운영자가 지정할 때만)

지역이 동 없이 시·군·구까지만 적힌 사례('충주시', '대구 중구')도 그 시군구가 한 곳으로 정해지면 가져온다.
이런 사례는 동 페이지에는 붙지 않고 구 페이지(/gu/)에만 붙으며, 구 페이지가 아직 없으면 cases/input 에서
기다렸다가 구 페이지가 생긴 뒤 build_cases.py 가 처리한다. 시·도까지만('서울') 있거나 여러 구와 맞으면('수원시') 건너뛴다.
  (git commit·push 가 끝난 뒤)
  python scripts/pc_cases.py mark                 stage 한 건마다 원본 폴더에 반영됨.txt 를 만든다
  python scripts/pc_cases.py report               오늘 가져온 건 한 줄 요약 + 사례마다 걱정/고른쪽/걸린 날/끝한줄 4줄
  python scripts/pc_cases.py ledger               거래 기록부 칸 이름과 날짜 칸 매핑(값은 안 보임, 2026-10-23)
  python scripts/pc_cases.py clean                .cases_staging 지우기 (원본 미리보기 삭제)

select.json 형식 (좌표는 미리보기 사진의 비율 0~1: 왼쪽, 위, 오른쪽, 아래)
  {"photos": [
     {"file": "p03.jpg", "boxes": [[0.38, 0.66, 0.62, 0.76]]},   ← 번호판을 가릴 네모
     {"file": "p05.jpg", "boxes": []}                             ← 가릴 것 없음
   ]}
  - 6장까지. 서류(등록증·신분증 등)가 찍힌 사진은 고르지 않는다(가리지 말고 빼기).
  - 네모는 자동으로 조금 넓혀서 모자이크 + 흐림 처리한다.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cases import (  # noqa: E402
    MAX_PHOTOS, MEMO_NAMES, PHOTO_EXT, SPOKEN_NAME, check_folder, compose, ensure_pillow, hidden_info,
    gu_page_exists, load_csv_rows, parse_memo, read_text_any, region_label, resolve_region,
)
from build_site import load_json  # noqa: E402
import case_story  # noqa: E402
from case_story import STORY_KEYS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC_DEFAULT = r"C:\Users\AOMG\Documents\카카오톡 받은 파일\폐차사진원본"
TIERS = ("우선", "일반")
DONE_MARK = "반영됨.txt"
# 메모가 틀렸거나 모자란 건을 운영자가 확인해 준 값으로 바꿔 읽는다(원본 메모는 고치지 않음).
# [{"folder": "일반\<원본 폴더>", "region": "경기도 수원시 권선구", "confirmed": "날짜 누가 확인"}]
#   "region" 대신·함께 "memo": {"날짜": "2023-01-27", ...} 를 쓰면 그 칸을 덮어쓴다(표에 있는 칸만).
#   "hold": "<이유>" 가 있으면 운영자가 답할 때까지 고르지 않는다.
REGION_FIXES = ROOT / "data" / "case_region_fixes.json"
STAGING = ROOT / ".cases_staging"
INPUT_DIR = ROOT / "cases" / "input"
PC_REQUIRED = ("지역", "차종", "연식", "시동")  # 이 넷이 다 채워진 건만 대상
DAILY, BACKLOG_DAILY = 3, 5  # 하루 건수. 밀린 대상이 있는 동안은 5건(2026-10-16 병한님 결정)
PC_MEMO_KEYS = ("날짜", "지역", "차종", "연식", "시동", "운행", "상황", "처리", "결과", "한마디") + STORY_KEYS
# 거래 기록부(2026-10-23 글 틀 v2): 날짜 세 칸(문의일·인수일·말소일)이 비면 차종+시·군이 같고 날짜가 ±14일인 거래가
# 하나뿐일 때만 채운다. 칸 이름은 기록부마다 다를 수 있어 이름 꼴로 고르고(ledger 명령이 보여 줌), 전화·차번호·이름·금액 칸은 읽지 않는다.
from inquiry_log import WIKI_DIR, part_match  # noqa: E402
LEDGER_DAYS = 14
LEDGER_SKIP_RE = re.compile(r"전화|연락|번호|이름|성함|고객|금액|가격|원가|입금|계좌|견적|매입|주소|메모|비고")
LEDGER_FIELD_RES = {  # 칸 이름 꼴 → 우리 칸. 위에서부터 처음 맞는 칸 하나
    "문의일": [re.compile(r"^(문의일|문의\s*날짜|날짜)$")],
    "인수일": [re.compile(r"^(인수|입고|견인|수거)(일|\s*날짜|일자)?$"), re.compile(r"(인수|입고|견인|수거).*(일|날짜|일자)$")],
    "말소일": [re.compile(r"^말소(일|\s*날짜|일자|완료일?)?$"), re.compile(r"말소.*(일|날짜|일자)$")],
    "차종": [re.compile(r"^(차종|차량|차명|모델)$")],
    "지역": [re.compile(r"^지역$")],
}
LEDGER_NAME_RE = re.compile(r"^([^:\n|#>*-][^:\n]{0,14}?)[ \t]*:", re.M)


def load_fixes() -> dict:
    return {f["folder"].replace("/", "\\"): f for f in load_json(REGION_FIXES, default=[]) or []}


def apply_fix(memo: dict, fix: dict | None) -> dict:
    """확인된 메모 칸을 덮어쓴다. 표에 없는 칸(고객명 등)은 받지 않는다."""
    if fix:
        memo.update({k: str(v).strip() for k, v in (fix.get("memo") or {}).items() if k in PC_MEMO_KEYS and str(v).strip()})
    return memo


def blocked(name: str) -> bool:
    return "문자백업" in name or name.startswith("제외")


def assert_allowed(path: Path, src: Path) -> None:
    rel = path.resolve().relative_to(src.resolve())
    if not rel.parts or rel.parts[0] not in TIERS or any(blocked(p) for p in rel.parts):
        raise SystemExit(f"들어가면 안 되는 폴더입니다: {path}")


def case_folders(tier_dir: Path):
    """tier_dir 아래에서 메모.txt 가 있는 폴더. 문자백업·제외 폴더는 들어가지 않는다."""
    for dirpath, dirnames, filenames in os.walk(tier_dir):
        dirnames[:] = sorted(d for d in dirnames if not blocked(d))
        if any(n in filenames for n in MEMO_NAMES):
            yield Path(dirpath)


def photo_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_EXT)


VIDEO_EXT = {".mp4", ".mov", ".3gp", ".m4v"}
FRAME_SKIP_TAIL = 5      # 영상 마지막 5초(지역·차종을 말하는 부분)는 사진으로 쓰지 않는다
FRAME_CANDIDATES = 12    # 영상에서 뽑는 서로 다른 장면 후보 수(Claude 가 이 중 4장을 고름)


def not_spoken(p: Path) -> bool:
    """등록증 사진 목록처럼 대본이 아닌 .txt 인지 첫 줄로 본다."""
    try:
        first = p.read_text(encoding="utf-8-sig", errors="replace").lstrip().splitlines()[:1]
    except OSError:
        return False
    return bool(first) and any(w in first[0] for w in ("등록증", "쓰지 말"))


def spoken_file(folder: Path) -> Path | None:
    """원본 폴더의 대본·녹음용 문장 .txt(2026-10-16 [3]). 메모·반영됨 표시·문자 백업이 아닌 .txt 중
    이름에 대본/문장/멘트/녹음이 들어간 것, 없으면 그런 .txt 가 하나뿐일 때 그것.
    첫 줄에 "등록증"·"쓰지 말"이 있는 .txt(등록증 사진 파일 이름 목록, 2026-10-20)는 대본이 아니다."""
    skip = set(MEMO_NAMES) | {DONE_MARK}
    txts = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".txt"
            and p.name not in skip and not blocked(p.name) and "문자" not in p.name
            and not not_spoken(p)]
    named = [p for p in txts if any(w in p.stem for w in ("대본", "문장", "멘트", "녹음"))]
    return (named or (txts if len(txts) == 1 else [None]))[0]


def video_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)


def video_frames(videos: list[Path], limit: int = FRAME_CANDIDATES):
    """사진이 없는 사례: 영상에서 서로 다른 장면을 골라 PIL 이미지로 돌려준다(2026-10-16 [2]).
    차를 한 바퀴 돌며 찍은 영상이 많아, 쓸 수 있는 구간(마지막 5초 제외)을 장면 수만큼 나눠 구간마다 가장 선명한 한 장을 고르고,
    바로 앞 장면과 색 분포가 거의 같으면 뺀다. 번호판이 보이는 장면은 Claude 가 미리보기에서 고르지 않는다(가리지 말고 건너뜀)."""
    import cv2
    from PIL import Image
    shots = []  # (영상, 프레임 번호 목록)
    for v in videos:
        cap = cv2.VideoCapture(str(v))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        end = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) - int(fps * FRAME_SKIP_TAIL)
        cap.release()
        if end > 0:
            shots.append((v, fps, end))
    total = sum(e for _, _, e in shots)
    picked, last = [], None
    for v, fps, end in shots:
        n = max(1, round(limit * end / total)) if total else 0
        cap = cv2.VideoCapture(str(v))
        step = max(1, int(fps / 4))
        for k in range(n):
            lo, hi = end * k // n, end * (k + 1) // n
            best = None
            for idx in range(lo, hi, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok:
                    break
                sharp = cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
                if best is None or sharp > best[0]:
                    best = (sharp, frame)
            if best is None:
                continue
            hsv = cv2.cvtColor(cv2.resize(best[1], (160, 90)), cv2.COLOR_BGR2HSV)
            h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
            cv2.normalize(h, h)
            if last is not None and cv2.compareHist(h, last, cv2.HISTCMP_BHATTACHARYYA) < 0.03:
                continue
            last = h
            picked.append(Image.fromarray(cv2.cvtColor(best[1], cv2.COLOR_BGR2RGB)))
        cap.release()
    return picked


def ledger_names(text: str) -> list[str]:
    """기록부 한 장의 칸 이름(값은 읽지 않음)."""
    return [m.group(1).strip() for m in LEDGER_NAME_RE.finditer(text)]


def ledger_map(names: list[str]) -> dict[str, str]:
    """우리 칸 → 기록부 칸 이름. 전화·차번호·이름·금액 꼴 칸은 고르지 않는다."""
    out = {}
    for ours, pats in LEDGER_FIELD_RES.items():
        for pat in pats:
            hit = next((n for n in names if pat.search(n) and not LEDGER_SKIP_RE.search(n)), None)
            if hit:
                out[ours] = hit
                break
    return out


def ledger_value(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}[ \t]*:[ \t]*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def ledger_records(folder: Path = WIKI_DIR) -> list[dict]:
    """[{문의일, 인수일, 말소일, 차종, 지역}] — 고른 칸만 읽는다."""
    out = []
    for f in sorted(folder.glob("*.md")) if folder.exists() else []:
        text = f.read_text(encoding="utf-8", errors="replace")
        fields = ledger_map(ledger_names(text))
        out.append({k: ledger_value(text, n) for k, n in fields.items()})
    return out


def car_key(v: str) -> str:
    return re.sub(r"[\s()\[\]\d년식]", "", v or "").lower()


def ledger_dates(memo: dict, region: dict, records: list[dict]) -> tuple[dict, str]:
    """날짜 세 칸이 다 비었을 때 기록부에서 채울 값과 설명. 맞는 거래가 하나뿐일 때만."""
    if any(memo.get(k) for k in case_story.DATE_KEYS):
        return {}, "메모에 날짜 칸이 있어 기록부를 보지 않음"
    day = case_story.parse_day(memo.get("날짜", ""))
    if not day:
        return {}, "사례 날짜가 없어 기록부와 맞춰 보지 않음"
    car = car_key(memo.get("차종", ""))
    city = (region.get("sigungu") or "").split()[0] if region.get("sigungu") else ""
    hits = []
    for r in records:
        rcar = car_key(r.get("차종", ""))
        d = case_story.parse_day(r.get("문의일", ""))
        if not (car and rcar and (car in rcar or rcar in car)) or not d or abs((d - day).days) > LEDGER_DAYS:
            continue
        if city and not any(part_match(city, tok) for tok in (r.get("지역") or "").split()):
            continue
        hits.append(r)
    if len(hits) != 1:
        return {}, f"기록부에서 맞는 거래 {len(hits)}건(하나일 때만 채움)"
    got = {k: hits[0][k] for k in case_story.DATE_KEYS if case_story.parse_day(hits[0].get(k, ""))}
    return got, "기록부에서 채움: " + (", ".join(f"{k} {v}" for k, v in got.items()) or "날짜 칸 없음")


def cmd_ledger(args) -> None:
    """거래 기록부 칸 이름과 우리 칸 매핑을 보여 준다(값은 보이지 않음). 기록부 칸 이름이 바뀌면 LEDGER_FIELD_RES 를 고친다."""
    folder = Path(args.dir) if args.dir else WIKI_DIR
    files = sorted(folder.glob("*.md")) if folder.exists() else []
    if not files:
        raise SystemExit(f"거래 기록부가 없습니다: {folder}")
    from collections import Counter
    names = Counter(n for f in files for n in set(ledger_names(f.read_text(encoding="utf-8", errors="replace"))))
    print(f"거래 기록부 {len(files)}장, 칸 이름(나온 장수): " + ", ".join(f"{n}({k})" for n, k in names.most_common()))
    mapping = ledger_map(list(names))
    for ours in LEDGER_FIELD_RES:
        print(f"  {ours} ← {mapping.get(ours, '(맞는 칸 없음)')}")
    print("  읽지 않는 칸: " + ", ".join(n for n in names if LEDGER_SKIP_RE.search(n)))


def staging_state() -> dict:
    return load_json(STAGING / "scan.json", default={}) or {}


def save_state(state: dict) -> None:
    STAGING.mkdir(exist_ok=True)
    (STAGING / "scan.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_scan(args) -> None:
    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"원본 폴더가 없습니다: {src}")
    rows = load_csv_rows()
    regions = load_json(ROOT / "data" / "regions.json", [])
    dong_pages = {(r["sido"], r["sigungu"], r["dong"]) for r in regions}
    gu_pages = {(r["sido"], r["sigungu"]) for r in regions}

    fixes = load_fixes()
    cands, skipped, marked = [], [], 0
    for ti, tier in enumerate(TIERS):
        tier_dir = src / tier
        if not tier_dir.exists():
            continue
        for folder in case_folders(tier_dir):
            rel = str(folder.relative_to(src))
            if (folder / DONE_MARK).exists():
                marked += 1
                continue
            memo_path = next(folder / n for n in MEMO_NAMES if (folder / n).exists())
            fix = fixes.get(rel.replace("/", "\\"))
            if fix and fix.get("hold"):
                skipped.append((rel, f"보류: {fix['hold']}"))
                continue
            memo = apply_fix(parse_memo(read_text_any(memo_path)), fix)
            missing = [k for k in PC_REQUIRED if not memo.get(k)]
            if missing:
                skipped.append((rel, f"메모에 {'·'.join(missing)} 없음"))
                continue
            # 확인된 지역이 있으면 메모의 지역 대신 쓴다. stage 가 메모.txt 의 지역 칸을 이 결과로 다시 쓴다
            region, why = resolve_region((fix or {}).get("region") or memo["지역"], rows)
            if not region:
                skipped.append((rel, why))
                continue
            body, why = compose(memo)
            if not body:
                skipped.append((rel, why))
                continue
            photos = photo_files(folder) or video_files(folder)  # 사진이 없으면 영상에서 뽑는다
            if not photos:
                skipped.append((rel, "사진·영상 없음"))
                continue
            if args.no_dong and region["dong"]:
                continue
            if args.only and not any(w in rel for w in args.only.split(",")):
                continue
            key = (region["sido"], region["sigungu"], region["dong"])
            if region["dong"]:
                rank = 0 if key in dong_pages else 1 if key[:2] in gu_pages else 2
            else:  # 동 없는 사례(시군구까지만 확인): 구 페이지에만 붙는다. 구 페이지가 없으면 cases/input 에서 기다린다
                rank = 1 if gu_page_exists(region) else 2
            cands.append({
                "tier": tier, "tier_i": ti, "rank": rank, "src": str(folder), "rel": rel,
                "region": region, "car": body["car"], "photos": len(photos),
            })

    # 우선 → 일반. 같은 폴더 안에서는 동 페이지가 있는 건 → 같은 시군구 페이지가 있는 건 → 나머지
    cands.sort(key=lambda c: (c["tier_i"], c["rank"], c["rel"]))
    state = {"date": date.today().isoformat(), "src": str(src), "picks": {}}
    if args.more:  # 뺀(drop) 건을 채우기: 오늘 이미 고른 건은 두고 모자란 만큼만 더 고른다
        old = staging_state()
        if old.get("date") == state["date"]:
            state["picks"] = old.get("picks", {})
    taken = {c["src"] for c in state["picks"].values()}
    n = args.n or (BACKLOG_DAILY if len(cands) > DAILY else DAILY)
    need = n - sum(1 for c in state["picks"].values() if c.get("status") != "dropped")
    picks = [c for c in cands if c["src"] not in taken][: max(0, need)]
    for c in picks:
        state["picks"][f"c{len(state['picks']) + 1}"] = {**c, "status": "picked"}
    save_state(state)

    label = {0: "동 페이지 있음", 1: "같은 시군구 페이지 있음", 2: "붙을 페이지 아직 없음"}
    gu_label = {1: "동 없음 · 구 페이지 있음", 2: "동 없음 · 구 페이지 대기"}
    print(f"대상 {len(cands)}건 (이미 반영됨 {marked}건, 조건 미달 {len(skipped)}건). 새로 고른 {len(picks)}건:")
    for cid, c in state["picks"].items():
        if c.get("status") != "picked":
            continue
        r = c["region"]
        lab = label[c["rank"]] if r["dong"] else gu_label[c["rank"]]
        print(f"  {cid}: [{c['tier']}] {r['sigungu'] or r['sido']} {r['dong']} · {c['car']} · 사진 {c['photos']}장 · {lab}".replace("  ·", " ·"))
    for rel, why in skipped[:15]:
        print(f"  조건 미달: {rel} — {why}")
    if len(skipped) > 15:
        print(f"  … 조건 미달 {len(skipped) - 15}건 더")


def pick_of(cid: str) -> tuple[dict, dict]:
    state = staging_state()
    if cid not in state.get("picks", {}):
        raise SystemExit(f"{cid} 가 없습니다. 먼저 scan 을 실행하세요")
    return state, state["picks"][cid]


def cmd_prepare(args) -> None:
    ensure_pillow()
    from PIL import Image, ImageDraw, ImageOps
    state = staging_state()
    src = Path(state["src"])
    for cid, c in state.get("picks", {}).items():
        if c.get("status") != "picked":
            continue
        folder = Path(c["src"])
        assert_allowed(folder, src)
        d = STAGING / cid
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        previews = []
        if not photo_files(folder) and video_files(folder):
            for i, im in enumerate(video_frames(video_files(folder)), 1):
                im.thumbnail((1600, 1600))
                name = f"p{i:02d}.jpg"
                Image.frombytes("RGB", im.size, im.tobytes()).save(d / name, "JPEG", quality=85)
                previews.append(name)
            c["from_video"] = True
            print(f"  {cid}: 사진이 없어 영상에서 장면 {len(previews)}장을 뽑음(앞·뒤·옆·계기판 4장을 고르고 번호판 보이는 장면은 건너뛰기)")
        for i, p in enumerate(photo_files(folder), 1):
            try:
                with Image.open(p) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((1600, 1600))
                    clean = Image.frombytes("RGB", im.size, im.tobytes())
            except Exception as e:  # 열 수 없는 파일(HEIC 등)은 건너뛴다
                print(f"  {cid}: {p.name} 열 수 없음({type(e).__name__}), 건너뜀")
                continue
            name = f"p{i:02d}.jpg"
            clean.save(d / name, "JPEG", quality=85)
            previews.append(name)
        # 모아보기: 12장씩 한 장에 번호를 붙여서
        for s in range(0, len(previews), 12):
            chunk = previews[s:s + 12]
            cols, cell = 4, 360
            sheet = Image.new("RGB", (cols * cell, ((len(chunk) + cols - 1) // cols) * cell), "white")
            draw = ImageDraw.Draw(sheet)
            for j, name in enumerate(chunk):
                with Image.open(d / name) as im:
                    im.thumbnail((cell - 8, cell - 36))
                    x, y = (j % cols) * cell, (j // cols) * cell
                    sheet.paste(im, (x + 4, y + 32))
                draw.rectangle([x + 4, y + 2, x + 90, y + 28], fill="black")
                draw.text((x + 10, y + 6), name, fill="white")
            sheet.save(d / f"sheet{s // 12 + 1}.jpg", "JPEG", quality=80)
        # 걱정 후보용(2026-10-23): 원본 자료\말.txt 가 있으면 미리보기 폴더로 옮겨 둔다(Claude 는 원본을 직접 열지 않음)
        speech = folder / "자료" / "말.txt"
        if speech.exists():
            (d / "말.txt").write_text(read_text_any(speech), encoding="utf-8")
        c["previews"] = previews
        c["status"] = "prepared"
        print(f"{cid}: 미리보기 {len(previews)}장 → {d.relative_to(ROOT)} (모아보기 sheet*.jpg)")
    save_state(state)


def cmd_mask(args) -> None:
    ensure_pillow()
    from PIL import Image, ImageFilter
    state, c = pick_of(args.cid)
    d = STAGING / args.cid
    sel = load_json(d / "select.json")
    if not sel or not sel.get("photos"):
        raise SystemExit(f"{d / 'select.json'} 이 없거나 비어 있습니다")
    photos = sel["photos"]
    if len(photos) > MAX_PHOTOS:
        raise SystemExit(f"사진은 {MAX_PHOTOS}장까지입니다 (지금 {len(photos)}장)")
    out = d / "out"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    made = []
    for i, ph in enumerate(photos, 1):
        with Image.open(d / ph["file"]) as im:
            im = im.convert("RGB")
            W, H = im.size
            for box in ph.get("boxes", []):
                x1, y1, x2, y2 = (float(v) for v in box)
                if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
                    raise SystemExit(f"{ph['file']}: 좌표 {box} 가 0~1 범위의 (왼쪽, 위, 오른쪽, 아래)가 아닙니다")
                pad_x = max((x2 - x1) * 0.15, 0.02)
                pad_y = max((y2 - y1) * 0.15, 0.02)
                l, t = int(max(0, x1 - pad_x) * W), int(max(0, y1 - pad_y) * H)
                r, b = int(min(1, x2 + pad_x) * W), int(min(1, y2 + pad_y) * H)
                region = im.crop((l, t, r, b))
                small = region.resize((max(1, (r - l) // 24), max(1, (b - t) // 24)), Image.BILINEAR)
                region = small.resize(region.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(6))
                im.paste(region, (l, t))
            im.thumbnail((1200, 1200))
            clean = Image.frombytes("RGB", im.size, im.tobytes())
        dst = out / f"{i}.jpg"
        clean.save(dst, "JPEG", quality=85)
        if hidden_info(dst):
            raise SystemExit(f"{dst}: 숨은 정보가 남았습니다")
        made.append(dst)
    # 확인용 모아보기
    cell = 400
    sheet = Image.new("RGB", (cell * min(3, len(made)), cell * ((len(made) + 2) // 3)), "white")
    for j, p in enumerate(made):
        with Image.open(p) as im:
            im.thumbnail((cell - 8, cell - 8))
            sheet.paste(im, ((j % 3) * cell + 4, (j // 3) * cell + 4))
    sheet.save(out / "check.jpg", "JPEG", quality=80)
    c["status"] = "masked"
    save_state(state)
    print(f"{args.cid}: 가린 사진 {len(made)}장 → {out.relative_to(ROOT)} . 한 장씩 열어 번호판·얼굴·서류가 안 보이는지 확인하세요")


def cmd_stage(args) -> None:
    state, c = pick_of(args.cid)
    if c.get("status") != "masked":
        raise SystemExit(f"{args.cid}: mask 를 먼저 하세요 (지금 상태 {c.get('status')})")
    src_folder = Path(c["src"])
    assert_allowed(src_folder, Path(state["src"]))
    memo_path = next(src_folder / n for n in MEMO_NAMES if (src_folder / n).exists())
    # 표에 있는 칸만 읽힘(고객명·연락처 등은 버려짐). 운영자가 확인해 준 칸은 덮어쓴다
    rel = str(src_folder.relative_to(Path(state["src"])))
    memo = apply_fix(parse_memo(read_text_any(memo_path)), load_fixes().get(rel.replace("/", "\\")))
    r = c["region"]
    memo["지역"] = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
    memo["차종"] = c["car"].split("년식 ", 1)[-1]
    tag = hashlib.sha1(c["src"].encode("utf-8")).hexdigest()[:6]  # 원본 폴더 이름(고객 이름이 있을 수 있음)은 쓰지 않는다
    if not memo.get("날짜"):
        memo["날짜"] = "미상"  # 날짜를 지어내지 않는다(사례 페이지에 날짜를 표시하지 않음)
    # 글 틀 v2(2026-10-23): ① 날짜 세 칸이 비면 거래 기록부에서(맞는 거래가 하나뿐일 때만)
    got, why = ledger_dates(memo, r, ledger_records())
    memo.update(got)
    c["ledger"] = why
    # ② 걱정 후보: Claude 가 말.txt·통화 글자본을 보고 .cases_staging/cN/extra.json 에 {"걱정": "… (통화 요약)"} 을 썼으면 넣는다
    extra = load_json(STAGING / args.cid / "extra.json", default={}) or {}
    if extra.get("걱정") and not memo.get("걱정"):
        memo["걱정"] = str(extra["걱정"]).strip()
    name = f"{memo['날짜'] if memo['날짜'] != '미상' else 'nodate'}-{region_label(r).replace(' ', '-')}-{tag}"
    dest = INPUT_DIR / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    order = PC_MEMO_KEYS
    (dest / "메모.txt").write_text("".join(f"{k}: {memo[k]}\n" for k in order if memo.get(k)), encoding="utf-8")
    for p in sorted((STAGING / args.cid / "out").glob("[0-9]*.jpg"), key=lambda p: int(p.stem)):
        shutil.copy2(p, dest / p.name)
    if sp := spoken_file(src_folder):  # 대본은 문장 그대로 옮긴다(검사는 아래 check_folder 가 함)
        (dest / SPOKEN_NAME).write_text(read_text_any(sp).strip() + "\n", encoding="utf-8")
    info, why = check_folder(dest, load_csv_rows())
    bad = [p.name for p in photo_files(dest) if hidden_info(p)]
    if not info or bad:
        shutil.rmtree(dest)
        raise SystemExit(f"{args.cid}: 검사 실패 — {why or f'숨은 정보 남음 {bad}'}")
    c["status"], c["input"] = "staged", f"cases/input/{name}"
    c["story"] = info["body"]["story"]
    save_state(state)
    print(f"{args.cid}: {c['input']} 준비됨 ({r['sigungu'] or r['sido']} {r['dong']} · {c['car']}, 사진 {len(info['photos'])}장)".replace("  ·", " ·"))
    print(f"  {c['ledger']}")
    for line in case_story.report_lines({"story": c["story"]}):
        print(f"  {line}")


def cmd_drop(args) -> None:
    state, c = pick_of(args.cid)
    c["status"], c["drop_reason"] = "dropped", args.reason
    save_state(state)
    print(f"{args.cid}: 오늘은 쓰지 않음 — {args.reason} (원본에는 표시하지 않음)")


def cmd_mark(args) -> None:
    state = staging_state()
    src = Path(state["src"])
    for cid, c in state.get("picks", {}).items():
        if c.get("status") != "staged":
            continue
        folder = Path(c["src"])
        assert_allowed(folder, src)
        (folder / DONE_MARK).write_text(
            f"{date.today().isoformat()} 홈페이지 사례로 반영함\n저장소 위치: {c['input']}\n", encoding="utf-8")
        c["status"] = "marked"
        print(f"{cid}: {c['rel']} 에 {DONE_MARK} 만듦")
    save_state(state)


def cmd_report(args) -> None:
    state = staging_state()
    done = [c for c in state.get("picks", {}).values() if c.get("status") in ("staged", "marked")]
    items = ", ".join(f"{(c['region']['sigungu'] or c['region']['sido'])} {c['region']['dong']}".strip() + f"·{c['car']}" for c in done)
    print(f"오늘 가져온 사례 {len(done)}건: {items or '없음'}")
    for c in done:  # 글 틀 v2(2026-10-23): 사례마다 4줄
        print(f"  {region_label(c['region'])} · {c['car']}")
        for line in case_story.report_lines({"story": c.get("story") or {}}):
            print(f"    {line}")
    for cid, c in state.get("picks", {}).items():
        if c.get("status") == "dropped":
            print(f"  뺀 건 {cid}: {region_label(c['region'])} · {c['car']} — {c.get('drop_reason')}")


def cmd_clean(args) -> None:
    if STAGING.exists():
        shutil.rmtree(STAGING)
    print(".cases_staging 삭제함")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--src", default=SRC_DEFAULT)
    s.add_argument("--n", type=int, default=0, help="몇 건 고를지. 0(기본)이면 대상이 3건보다 많은 동안(밀림) 5건, 아니면 3건")
    s.add_argument("--more", action="store_true", help="오늘 고른 건은 두고, 뺀 만큼만 더 고른다")
    s.add_argument("--only", default="", help="원본 폴더 이름에 이 글자가 든 건만 고른다(쉼표로 여러 개). 운영자가 특정 건을 지정할 때만")
    s.add_argument("--no-dong", action="store_true", help="동 없이 시군구까지만 적힌 사례만 고른다(밀린 건 한꺼번에 처리할 때)")
    sub.add_parser("prepare")
    for name in ("mask", "stage"):
        sub.add_parser(name).add_argument("cid")
    d = sub.add_parser("drop")
    d.add_argument("cid")
    d.add_argument("reason")
    for name in ("mark", "report", "clean"):
        sub.add_parser(name)
    sub.add_parser("ledger").add_argument("--dir", default="", help="거래 기록부 폴더(기본: 저장소 옆 병한-업무위키\\폐차\\거래기록)")
    args = ap.parse_args()
    {"scan": cmd_scan, "prepare": cmd_prepare, "mask": cmd_mask, "stage": cmd_stage, "drop": cmd_drop,
     "mark": cmd_mark, "report": cmd_report, "clean": cmd_clean, "ledger": cmd_ledger}[args.cmd](args)


if __name__ == "__main__":
    main()
