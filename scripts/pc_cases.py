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
  python scripts/pc_cases.py scan [--n 3]        대상 고르기 → .cases_staging/scan.json
  python scripts/pc_cases.py prepare              고른 건마다 .cases_staging/cN/ 에 미리보기(p01.jpg…)와 모아보기(sheet1.jpg…)
      → 사람(또는 Claude)이 미리보기를 보고 .cases_staging/cN/select.json 을 쓴다 (형식은 아래)
  python scripts/pc_cases.py mask cN              가리기 적용 → .cases_staging/cN/out/1.jpg… (+ out/check.jpg)
      → out 사진을 다시 보고 번호판·얼굴·서류가 조금이라도 보이면 select.json 을 고쳐 다시 mask
  python scripts/pc_cases.py stage cN             cases/input/<폴더>/ 에 사진 + 정리된 메모.txt 를 넣고 검사
  python scripts/pc_cases.py drop cN "<이유>"     이 건은 오늘 쓰지 않음 (원본에 표시하지 않음)
  python scripts/pc_cases.py scan --more          뺀 만큼 새로 고르기 → 다시 prepare (새로 고른 건만 준비)
  (git commit·push 가 끝난 뒤)
  python scripts/pc_cases.py mark                 stage 한 건마다 원본 폴더에 반영됨.txt 를 만든다
  python scripts/pc_cases.py report               오늘 가져온 건 한 줄 요약
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
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cases import (  # noqa: E402
    MAX_PHOTOS, MEMO_NAMES, PHOTO_EXT, check_folder, compose, ensure_pillow, hidden_info,
    load_csv_rows, parse_memo, read_text_any, resolve_region,
)
from build_site import load_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC_DEFAULT = r"C:\Users\AOMG\Documents\카카오톡 받은 파일\폐차사진원본"
TIERS = ("우선", "일반")
DONE_MARK = "반영됨.txt"
STAGING = ROOT / ".cases_staging"
INPUT_DIR = ROOT / "cases" / "input"
PC_REQUIRED = ("지역", "차종", "연식", "시동")  # 이 넷이 다 채워진 건만 대상


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
            memo = parse_memo(read_text_any(memo_path))
            missing = [k for k in PC_REQUIRED if not memo.get(k)]
            if missing:
                skipped.append((rel, f"메모에 {'·'.join(missing)} 없음"))
                continue
            region, why = resolve_region(memo["지역"], rows)
            if not region:
                skipped.append((rel, why))
                continue
            body, why = compose(memo)
            if not body:
                skipped.append((rel, why))
                continue
            photos = photo_files(folder)
            if not photos:
                skipped.append((rel, "사진 없음"))
                continue
            key = (region["sido"], region["sigungu"], region["dong"])
            rank = 0 if key in dong_pages else 1 if key[:2] in gu_pages else 2
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
    need = args.n - sum(1 for c in state["picks"].values() if c.get("status") != "dropped")
    picks = [c for c in cands if c["src"] not in taken][: max(0, need)]
    for c in picks:
        state["picks"][f"c{len(state['picks']) + 1}"] = {**c, "status": "picked"}
    save_state(state)

    label = {0: "동 페이지 있음", 1: "같은 시군구 페이지 있음", 2: "붙을 페이지 아직 없음"}
    print(f"대상 {len(cands)}건 (이미 반영됨 {marked}건, 조건 미달 {len(skipped)}건). 새로 고른 {len(picks)}건:")
    for cid, c in state["picks"].items():
        if c.get("status") != "picked":
            continue
        r = c["region"]
        print(f"  {cid}: [{c['tier']}] {r['sigungu'] or r['sido']} {r['dong']} · {c['car']} · 사진 {c['photos']}장 · {label[c['rank']]}")
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
    memo = parse_memo(read_text_any(memo_path))  # 표에 있는 칸만 읽힘(고객명·연락처 등은 버려짐)
    r = c["region"]
    memo["지역"] = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
    memo["차종"] = c["car"].split("년식 ", 1)[-1]
    tag = hashlib.sha1(c["src"].encode("utf-8")).hexdigest()[:6]  # 원본 폴더 이름(고객 이름이 있을 수 있음)은 쓰지 않는다
    if not memo.get("날짜"):
        memo["날짜"] = "미상"  # 날짜를 지어내지 않는다(사례 페이지에 날짜를 표시하지 않음)
    name = f"{memo['날짜'] if memo['날짜'] != '미상' else 'nodate'}-{r['dong']}-{tag}"
    dest = INPUT_DIR / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    order = ("날짜", "지역", "차종", "연식", "시동", "운행", "상황", "처리", "결과", "한마디")
    (dest / "메모.txt").write_text("".join(f"{k}: {memo[k]}\n" for k in order if memo.get(k)), encoding="utf-8")
    for p in sorted((STAGING / args.cid / "out").glob("[0-9]*.jpg"), key=lambda p: int(p.stem)):
        shutil.copy2(p, dest / p.name)
    info, why = check_folder(dest, load_csv_rows())
    bad = [p.name for p in photo_files(dest) if hidden_info(p)]
    if not info or bad:
        shutil.rmtree(dest)
        raise SystemExit(f"{args.cid}: 검사 실패 — {why or f'숨은 정보 남음 {bad}'}")
    c["status"], c["input"] = "staged", f"cases/input/{name}"
    save_state(state)
    print(f"{args.cid}: {c['input']} 준비됨 ({r['sigungu'] or r['sido']} {r['dong']} · {c['car']}, 사진 {len(info['photos'])}장)")


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
    items = ", ".join(f"{(c['region']['sigungu'] or c['region']['sido'])} {c['region']['dong']}·{c['car']}" for c in done)
    print(f"오늘 가져온 사례 {len(done)}건: {items or '없음'}")
    for cid, c in state.get("picks", {}).items():
        if c.get("status") == "dropped":
            print(f"  뺀 건 {cid}: {c['region']['dong']} · {c['car']} — {c.get('drop_reason')}")


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
    s.add_argument("--n", type=int, default=3)
    s.add_argument("--more", action="store_true", help="오늘 고른 건은 두고, 뺀 만큼만 더 고른다")
    sub.add_parser("prepare")
    for name in ("mask", "stage"):
        sub.add_parser(name).add_argument("cid")
    d = sub.add_parser("drop")
    d.add_argument("cid")
    d.add_argument("reason")
    for name in ("mark", "report", "clean"):
        sub.add_parser(name)
    args = ap.parse_args()
    {"scan": cmd_scan, "prepare": cmd_prepare, "mask": cmd_mask, "stage": cmd_stage, "drop": cmd_drop,
     "mark": cmd_mark, "report": cmd_report, "clean": cmd_clean}[args.cmd](args)


if __name__ == "__main__":
    main()
