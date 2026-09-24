"""
cases/input/ 에 올린 사례 폴더(사진 + 메모.txt)를 읽어 사례 페이지를 만들고 지역 페이지에 연결한다.

사용법
  python3 scripts/build_cases.py

한 사례 = 폴더 하나
  cases/input/2026-09-24-역삼동-그랜저/
    메모.txt          ← 지역·차종·상황·처리 (형식은 cases/input/README.md)
    1.jpg 2.jpg …     ← 번호판을 가린 사진

하는 일
  1. 메모를 읽는다. 금액·시세·결과 약속 표현이 있으면 그 사례는 건너뛰고 이유를 출력한다.
  2. 사진을 cases/images/<slug>-N.jpg 로 복사한다 (Pillow 가 있으면 긴 변 1200px 로 줄이고 EXIF 를 지운다).
  3. templates/case.html 로 cases/<slug>.html 을 만들고 cases/index.json 맨 앞에 등록한다.
  4. 처리한 폴더는 cases/done/ 으로 옮긴다.
  5. 지역 페이지를 전부 다시 렌더링해 사례 카드를 반영하고, sitemap 을 갱신하고, check_pages 를 돌린다.
"""
import csv
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site import contact_parts, esc, load_json
from pick_next_regions import make_slug
from sitemap_lib import update_sitemap

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "cases" / "input"
DONE_DIR = ROOT / "cases" / "done"
IMAGES_DIR = ROOT / "cases" / "images"
INDEX_PATH = ROOT / "cases" / "index.json"
TEMPLATE_PATH = ROOT / "templates" / "case.html"
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
REGIONS_PATH = ROOT / "data" / "regions.json"
CONFIG_PATH = ROOT / "data" / "site_config.json"
SCRIPTS = ROOT / "scripts"

MEMO_NAMES = ("메모.txt", "memo.txt")
REQUIRED = ("지역", "차종", "상황", "처리")
OPTIONAL = ("날짜", "결과", "한마디")
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MONEY_RE = re.compile(r"\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩|시세|견적가|매입가|매입 가격|보상금\s*\d")
PROMISE_RE = re.compile(r"보장|무조건|100%|1위|최저가")
LEADING_COMMENT_RE = re.compile(r"<!DOCTYPE html>\s*<!--.*?-->", re.DOTALL)


def parse_memo(text: str) -> dict:
    data: dict[str, str] = {}
    key = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([가-힣A-Za-z]+)\s*[:：]\s*(.*)$", line)
        if m and m.group(1) in REQUIRED + OPTIONAL:
            key = m.group(1)
            data[key] = m.group(2).strip()
        elif key:
            data[key] = (data[key] + " " + line).strip()  # 여러 줄로 쓴 값은 이어 붙인다
    return data


def load_region_index() -> tuple[dict[str, dict], dict[tuple[str, str, str], str]]:
    by_name = {}
    for row in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")):
        full = " ".join(x for x in (row["시도"], row["시군구"], row["읍면동"]) if x)
        by_name[full] = {"sido": row["시도"], "sigungu": row["시군구"], "dong": row["읍면동"]}
    page_slugs = {(r["sido"], r["sigungu"], r["dong"]): r["slug"] for r in load_json(REGIONS_PATH, [])}
    return by_name, page_slugs


def ensure_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], capture_output=True)
        try:
            import PIL  # noqa: F401
        except ImportError:
            raise SystemExit("사진 처리에 Pillow 가 필요합니다. `pip install pillow` 후 다시 실행하세요")


def hidden_info(path: Path) -> list[str]:
    """사진에 남아 있는 숨은 정보(EXIF·GPS·XMP·코멘트) 항목 이름. 비어 있으면 깨끗한 것."""
    from PIL import Image
    with Image.open(path) as im:
        found = []
        exif = im.getexif()
        if len(exif):
            found.append("EXIF")
        if exif and exif.get_ifd(0x8825):
            found.append("GPS")
        for key in ("exif", "xmp", "XML:com.adobe.xmp", "comment", "icc_profile_description"):
            if im.info.get(key):
                found.append(key)
        return found


def save_photo(src: Path, dst_base: Path) -> str:
    """사진을 줄여서 숨은 정보가 전혀 없는 JPEG 로 저장하고 파일 이름을 돌려준다."""
    from PIL import Image, ImageOps
    dst = dst_base.with_suffix(".jpg")
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")  # 회전 정보만 픽셀에 반영
        im.thumbnail((1200, 1200))
        clean = Image.frombytes("RGB", im.size, im.tobytes())  # 픽셀만 새 이미지로 옮겨 EXIF·GPS·XMP 를 전부 버린다
    clean.save(dst, "JPEG", quality=82, optimize=True)
    left = hidden_info(dst)
    if left:
        dst.unlink()
        raise SystemExit(f"{src.name}: 숨은 정보 {left} 를 지우지 못했습니다. 처리를 중단합니다")
    return dst.name


def kind_label(method: str) -> str:
    if "수출" in method:
        return "수출 비교매입 사례"
    if "폐차" in method:
        return "폐차 처리 사례"
    return "폐차·수출 비교 사례"


def first_sentence(text: str, limit: int = 70) -> str:
    s = re.split(r"(?<=[.!?])\s+", text.strip())[0]
    return s if len(s) <= limit else s[: limit - 1] + "…"


def process_folder(folder: Path, by_name: dict, page_slugs: dict, used_slugs: set[str]) -> dict | None:
    memo_path = next((folder / n for n in MEMO_NAMES if (folder / n).exists()), None)
    if not memo_path:
        print(f"건너뜀 {folder.name}: 메모.txt 가 없습니다")
        return None
    memo = parse_memo(memo_path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if not memo.get(k)]
    if missing:
        print(f"건너뜀 {folder.name}: 메모에 {missing} 항목이 없습니다")
        return None
    all_text = " ".join(memo.values())
    if m := MONEY_RE.search(all_text):
        print(f"건너뜀 {folder.name}: 금액·시세 표현 '{m.group(0)}' 이 있습니다. 메모에서 금액을 빼 주세요")
        return None
    if m := PROMISE_RE.search(all_text):
        print(f"건너뜀 {folder.name}: 결과를 약속하는 표현 '{m.group(0)}' 이 있습니다")
        return None
    region_text = re.sub(r"\s+", " ", memo["지역"]).strip()
    region = by_name.get(region_text)
    if not region:
        print(f"건너뜀 {folder.name}: 지역 '{region_text}' 을 찾을 수 없습니다. '서울특별시 강남구 역삼동'처럼 정식 이름으로 적어 주세요")
        return None
    photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_EXT)
    if not photos:
        print(f"건너뜀 {folder.name}: 사진(jpg/png/webp)이 없습니다")
        return None

    case_date = memo.get("날짜") or (m.group(0) if (m := re.match(r"\d{4}-\d{2}-\d{2}", folder.name)) else date.today().isoformat())
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", case_date):
        print(f"건너뜀 {folder.name}: 날짜는 2026-09-24 형식으로 적어 주세요 (현재 '{case_date}')")
        return None

    base = f"case-{case_date.replace('-', '')}-{make_slug(region['sido'], region['sigungu'], region['dong'])}"
    slug, n = base, 2
    while slug in used_slugs:
        slug, n = f"{base}-{n}", n + 1
    used_slugs.add(slug)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    names = [save_photo(p, IMAGES_DIR / f"{slug}-{i}") for i, p in enumerate(photos, 1)]

    return {
        "slug": slug,
        "date": case_date,
        "sido": region["sido"], "sigungu": region["sigungu"], "dong": region["dong"],
        "region_slug": page_slugs.get((region["sido"], region["sigungu"], region["dong"])),
        "car": memo["차종"],
        "title": f"{region['dong']} {memo['차종']} {kind_label(memo['처리'])}",
        "summary": first_sentence(memo["상황"]),
        "situation": memo["상황"], "method": memo["처리"],
        "result": memo.get("결과", ""), "quote": memo.get("한마디", ""),
        "thumb": names[0], "photos": names,
    }


def render_case(c: dict, cfg: dict, template: str) -> str:
    base = cfg["site_base_url"].rstrip("/")
    full = " ".join(x for x in (c["sido"], c["sigungu"], c["dong"]) if x)
    photos_html = "".join(
        f'<figure><img src="images/{esc(name)}" alt="{esc(c["title"])} 사진 {i}" loading="{"eager" if i == 1 else "lazy"}" width="1200" height="900"></figure>'
        for i, name in enumerate(c["photos"], 1)
    )
    story = [("차량 상황", c["situation"]), ("진행 방식", c["method"])]
    if c["result"]:
        story.append(("결과", c["result"]))
    story_html = "".join(f"<h2>{esc(h)}</h2><p>{esc(t)}</p>" for h, t in story)
    if c["quote"]:
        story_html += f"<h2>고객 한마디</h2><blockquote>“{esc(c['quote'])}”</blockquote>"
    if c["region_slug"]:
        region_btn = f'<a class="btn btn-quote" href="../pages/{esc(c["region_slug"])}.html" style="background:#fff">{esc(c["dong"])} 폐차 상담 페이지</a>'
    else:
        region_btn = '<a class="btn btn-quote" href="../index.html" style="background:#fff">지역별 상담 페이지 보기</a>'
    y, mth, d = c["date"].split("-")
    values = {
        "META_TITLE": esc(f"{c['title']} | 폐차 보상금 vs 수출 시세 비교 · {cfg['phone_display']}"),
        "META_DESC": esc(f"{full}에서 진행한 {c['car']} 사례. {c['summary']} 폐차와 수출 중 유리한 쪽으로 안내. 전화 {cfg['phone_display']}"),
        "CANONICAL": f"{base}/cases/{c['slug']}.html",
        "OG_IMAGE": f"{base}/cases/images/{c['thumb']}",
        "REGION_FULL_NAME": esc(full),
        "TITLE": esc(c["title"]),
        "DATE_TEXT": f"{int(y)}년 {int(mth)}월 {int(d)}일 진행",
        "PHOTOS_HTML": photos_html,
        "STORY_HTML": story_html,
        "REGION_BUTTON": region_btn,
        "PHONE_TEL": cfg["phone_tel"],
        "PHONE_DISPLAY": cfg["phone_display"],
        "YOUTUBE_URL": esc(cfg["youtube_url"]),
        "BLOG_URL": esc(cfg["blog_url"]),
        **contact_parts(cfg, c["dong"]),
    }
    cleaned = LEADING_COMMENT_RE.sub("<!DOCTYPE html>", template, count=1)

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(f"템플릿 자리 {key} 에 대응하는 값이 없습니다")
        return values[key]

    return re.sub(r"\{\{(\w+)\}\}", sub, cleaned)


def main() -> None:
    folders = sorted(p for p in INPUT_DIR.glob("*") if p.is_dir()) if INPUT_DIR.exists() else []
    if not folders:
        print("처리할 사례 없음 (cases/input/ 에 폴더가 없습니다)")
        return

    ensure_pillow()
    cfg = load_json(CONFIG_PATH)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    index: list[dict] = load_json(INDEX_PATH, default=[])
    by_name, page_slugs = load_region_index()
    used_slugs = {c["slug"] for c in index}

    done, skipped = [], 0
    for folder in folders:
        c = process_folder(folder, by_name, page_slugs, used_slugs)
        if not c:
            skipped += 1
            continue
        (ROOT / "cases" / f"{c['slug']}.html").write_text(render_case(c, cfg, template), encoding="utf-8")
        index.insert(0, c)
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), str(DONE_DIR / folder.name))
        done.append(c)
        print(f"사례 생성: cases/{c['slug']}.html ({c['title']}, 사진 {len(c['photos'])}장)")

    if done:
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        subprocess.run([sys.executable, str(SCRIPTS / "build_site.py")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        update_sitemap(ROOT, [], paths=[f"cases/{c['slug']}.html" for c in done])
        print(f"지역 페이지 재렌더링 완료, sitemap 에 사례 {len(done)}건 추가")
        for c in done:
            shown = [p.stem for p in (ROOT / "pages").glob("*.html") if f"/cases/{c['slug']}.html" in p.read_text(encoding="utf-8")]
            print(f"  {c['slug']} → 지역 페이지 {len(shown)}곳에 표시: {', '.join(sorted(shown))}")
        # 기존 페이지 경고는 매번 같으니 오류와 요약 줄만 보여 준다
        result = subprocess.run([sys.executable, str(SCRIPTS / "check_pages.py")], cwd=ROOT, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if not line.startswith("경고:"):
                print(line)
        if result.returncode != 0:
            sys.exit(result.returncode)
    print(f"완료: 사례 {len(done)}건 처리, {skipped}건 건너뜀")
    if skipped:
        sys.exit(1)


if __name__ == "__main__":
    main()
