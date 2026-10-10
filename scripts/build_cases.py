"""
cases/input/ 에 올린 사례 폴더(사진 + 메모.txt)를 읽어 사례 페이지를 만들고 지역 페이지에 연결한다.

사용법
  python3 scripts/build_cases.py
  python3 scripts/build_cases.py <폴더 이름> …   ← cases/input 안의 그 폴더만

한 사례 = 폴더 하나
  cases/input/2026-09-24-역삼동-그랜저/
    메모.txt          ← 지역·차종·연식·시동 (또는 지역·차종·상황·처리). 형식은 cases/input/README.md
    1.jpg 2.jpg …     ← 번호판·얼굴·서류를 가린 사진 (6장까지)

하는 일
  1. 메모를 읽는다. 금액·시세·결과 약속·수출 단정 표현이나 고객 정보(전화번호·차량번호·상세 주소)가 있으면
     그 사례는 건너뛰고 이유를 출력한다.
  2. 사진을 cases/images/<slug>-N.jpg 로 복사한다 (긴 변 1200px, EXIF·GPS·XMP 를 전부 지운 새 파일).
  3. templates/case.html 로 cases/<slug>.html 을 만들고 cases/index.json 맨 앞에 등록한다.
  4. 처리한 폴더는 cases/done/ 으로 옮긴다.
  5. 지역 페이지를 전부 다시 렌더링해 사례 카드를 반영하고, sitemap 을 갱신하고, check_pages 를 돌린다.

사례 페이지는 build_site.py 가 돌 때마다 render_all_cases() 로 다시 만든다. 그래서 사례를 만든 뒤에
그 동 페이지가 새로 생겨도 사례 페이지의 "○○동 폐차 상담 페이지" 버튼이 자동으로 연결된다.

PC 에서 원본 폴더를 골라 가리고 올리는 단계는 scripts/pc_cases.py (docs/pc-case-import-prompt.md).
"""
import csv
import json
import os
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
MAX_PHOTOS = 6
# 메모 칸 이름 → 표준 이름. 여기 없는 칸(고객명·연락처 등)은 읽지 않고 버린다.
KEY_ALIASES = {
    "지역": "지역", "차종": "차종", "연식": "연식", "날짜": "날짜",
    "시동": "시동", "시동여부": "시동",
    "운행": "운행", "운행여부": "운행", "운행가능여부": "운행",
    "상황": "상황", "처리": "처리",
    "진행": "진행", "실제진행": "진행", "진행방식": "진행",
    "결과": "결과", "한마디": "한마디",
    "youtube": "youtube", "유튜브": "youtube",  # 여러 줄 가능: "youtube: <주소> <짧은 설명>"
}
# 둘 중 한 형식이 다 있어야 한다: PC 원본 메모 형식 / 예전 직접 작성 형식
REQUIRED_SETS = (("지역", "차종", "연식", "시동"), ("지역", "차종", "상황", "처리"))
# 이 칸들의 괄호 "(등록증)", "(사진)" 은 출처 표시라서 읽을 때 지운다
SOURCE_NOTE_KEYS = ("지역", "차종", "연식")
SOURCE_NOTE_RE = re.compile(r"[(（\[][^)）\]]*[)）\]]")
# 상황 칸 → 페이지 문구. "" 은 페이지에 쓰지 않는다. 여기 없는 값은 짧으면 "문의 내용" 으로 쓴다
SITUATION_TEXT = {
    "일반폐차": "",
    "차령초과말소": "차령초과말소로 처리",
    "조기폐차": "조기폐차로 진행",
    "수출": "수출 쪽과 비교해 진행",
}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
# 유튜브 영상(2026-10-08): youtu.be/ID, youtube.com/shorts/ID, youtube.com/watch?v=ID, youtube.com/embed/ID
YOUTUBE_RE = re.compile(r"https?://(?:www\.|m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|embed/|watch\?(?:[^\s]*&)?v=))([A-Za-z0-9_-]{11})\S*")
MONEY_RE = re.compile(r"\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩|시세|견적가|매입가|매입 가격|보상금\s*\d")
PROMISE_RE = re.compile(r"보장|무조건|100%|1위|최저가")
# 이 차가 수출이 된다/안 된다는 단정. 사례 글에는 방식 비교만 쓴다.
EXPORT_CLAIM_RE = re.compile(r"수출\s*(이|은|는|로|으로)?\s*(불가|안\s*(됨|돼|되|된|가|간|감)|못|가능|됨|돼요|됩니다|된다|간다|갑니다|나감|나간)")
# 고객 정보: 휴대폰·전화번호, 차량번호, 상세 주소(번지·동호수·도로명 번호)
CUSTOMER_RE = re.compile(
    r"01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}|0\d{1,2}-\d{3,4}-\d{4}"
    r"|(?<!\d)\d{2,3}\s?[가-힣]\s?\d{4}(?!\d)"
    r"|\d+\s*번지|\d+\s*동\s*\d+\s*호"
    r"|[가-힣\d]+(로|길)\s?\d+(-\d+)?(?!\d|-\d|\s*(층|년|개|대|시|분|일|주|달|건|번|장|명|km|킬로))"
)
LEADING_COMMENT_RE = re.compile(r"<!DOCTYPE html>\s*<!--.*?-->", re.DOTALL)

SIDO_ALIASES = {
    "서울": "서울특별시", "서울시": "서울특별시", "부산": "부산광역시", "부산시": "부산광역시",
    "대구": "대구광역시", "대구시": "대구광역시", "인천": "인천광역시", "인천시": "인천광역시",
    "대전": "대전광역시", "대전시": "대전광역시", "울산": "울산광역시", "울산시": "울산광역시",
    "세종": "세종특별자치시", "세종시": "세종특별자치시",
    "경기": "경기도", "강원": "강원특별자치도", "강원도": "강원특별자치도",
    "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전라북도": "전북특별자치도",
    "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도", "제주도": "제주특별자치도",
    # 2026-07-01 통합: 옛 광주광역시·전라남도
    "광주": "전남광주통합특별시", "광주시": "전남광주통합특별시", "광주광역시": "전남광주통합특별시",
    "전남": "전남광주통합특별시", "전라남도": "전남광주통합특별시", "전남광주": "전남광주통합특별시",
}
# 행정구역 개편으로 사라진 구 이름. 옛 메모에 있어도 무시하고 동 이름으로 찾는다(찾은 결과가 하나일 때만).
OLD_SIGUNGU = {"중구", "동구", "서구"}


def read_text_any(p: Path) -> str:
    """카카오톡으로 받은 메모는 UTF-8 이 아닐 수 있다(윈도우 메모장 CP949)."""
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "cp949", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_memo(text: str) -> dict:
    data: dict[str, str] = {}
    key = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([가-힣A-Za-z ]{1,12}?)\s*[:：]\s*(.*)$", line)
        if m:
            key = KEY_ALIASES.get(m.group(1).replace(" ", ""))  # 모르는 칸이면 None → 그 줄과 이어지는 줄은 버린다
            if key == "youtube":  # 영상은 여러 줄을 모은다(줄마다 하나)
                data[key] = (data.get(key, "") + "\n" + m.group(2).strip()).strip()
                key = None
            elif key:
                data[key] = m.group(2).strip()
        elif key:
            data[key] = (data[key] + " " + line).strip()  # 여러 줄로 쓴 값은 이어 붙인다
    # 지역·차종·연식 끝의 "(등록증)", "(사진)" 같은 괄호는 출처 표시일 뿐이므로 지우고 읽는다
    for k in SOURCE_NOTE_KEYS:
        if k in data:
            data[k] = re.sub(r"\s+", " ", SOURCE_NOTE_RE.sub(" ", data[k])).strip()
    return {k: v for k, v in data.items() if v}


def load_csv_rows() -> list[dict]:
    return [
        {"sido": r["시도"], "sigungu": r["시군구"], "dong": r["읍면동"]}
        for r in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig"))
    ]


def _narrow(cands: list[dict], tokens: list[str], last: str) -> tuple[list[dict] | None, str]:
    """시도·시군구 낱말로 후보를 좁힌다. 시군구 이름을 먼저 본다(경기 '광주시'가 시도 줄임 '광주시'로 읽히지 않게)."""
    for t in tokens:
        f = [r for r in cands if t in r["sigungu"].split()]
        if not f and (t in SIDO_ALIASES or t in {r["sido"] for r in cands}):
            f = [r for r in cands if r["sido"] == SIDO_ALIASES.get(t, t)]
        if f:
            cands = f
        elif t not in OLD_SIGUNGU:
            return None, f"'{t}' 과 '{last}' 이 함께 있는 곳이 법정동 목록에 없습니다"
    return cands, ""


def _where(cands: list[dict]) -> str:
    return ", ".join(" ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x) for r in cands[:5])


def resolve_region(text: str, rows: list[dict]) -> tuple[dict | None, str]:
    """'용인시 처인구 모현읍', '경기 용인시 처인구 모현읍', '서울특별시 강남구 역삼동' 같은 지역 글을
    법정동 목록의 한 줄로 바꾼다. (결과, 문제 설명) — 결과가 None 이면 설명이 이유.
    동 없이 시·군·구까지만 있으면('충주시', '대구 중구') 그 시군구가 한 곳으로 정해질 때 dong 이 "" 인 결과를 돌려준다
    (구 페이지에만 붙는 사례, 2026-10-02). 시·도까지만 있거나('서울') 여러 구와 맞으면('수원시') None."""
    tokens = re.sub(r"[,()]", " ", text).split()
    if not tokens:
        return None, "지역이 비어 있습니다"
    dong = tokens[-1]
    cands = [r for r in rows if r["dong"] == dong]
    if not cands and dong.endswith("면"):  # 면 → 읍 승격(예: 모현면 → 모현읍)
        cands = [r for r in rows if r["dong"] == dong[:-1] + "읍"]
    if cands:
        cands, why = _narrow(cands, tokens[:-1], dong)
        if cands is None:
            return None, why
        if len(cands) > 1:
            return None, f"'{text}' 이 여러 곳과 맞습니다({_where(cands)}). 시도·시군구를 더 적어 주세요"
        return cands[0], ""
    # 동이 없는 지역: 시·군·구 단위로 찾는다
    gus = list({(r["sido"], r["sigungu"]): {"sido": r["sido"], "sigungu": r["sigungu"], "dong": ""} for r in rows}.values())
    sido_only = all(t in SIDO_ALIASES or t in {g["sido"] for g in gus} for t in tokens)
    if sido_only:
        sidos = {SIDO_ALIASES.get(t, t) for t in tokens}
        if sidos == {"세종특별자치시"}:  # 세종은 시군구가 없어 시 전체가 구 페이지 하나
            return {"sido": "세종특별자치시", "sigungu": "", "dong": ""}, ""
        return None, f"지역이 시·도('{text}')까지만 있어 시·군·구를 정할 수 없습니다"
    if not any(dong in g["sigungu"].split() for g in gus):
        return None, f"법정동 목록에 '{dong}' 이 없습니다"
    cands, why = _narrow(gus, tokens, dong)
    if cands is None:
        return None, why
    if len(cands) > 1:
        return None, f"'{text}' 이 여러 시·군·구와 맞습니다({_where(cands)}). 시도·구 이름을 더 적어 주세요"
    return cands[0], ""


def year_of(v: str) -> str:
    if m := re.search(r"(19|20)\d{2}", v):
        return m.group(0)
    if m := re.search(r"(?<!\d)(\d{2})\s*년", v):
        yy = int(m.group(1))
        return str(2000 + yy if yy <= date.today().year % 100 else 1900 + yy)
    return ""


def start_state(v: str) -> str:
    """시동 칸 → '걸림' / '안 걸림' / '' (알 수 없음)"""
    s = v.replace(" ", "")
    if re.search(r"안|불|않|X|x|×|NO|no|불량|꺼짐", s):
        return "안 걸림"
    if re.search(r"됨|된다|가능|걸림|O|o|○|양호|정상|YES|yes|ok|OK", s):
        return "걸림"
    return ""


def drive_state(v: str) -> str:
    s = v.replace(" ", "")
    if not s:
        return ""
    if re.search(r"확인|모름|미정|\?", s):
        return "현장 확인 필요"
    if re.search(r"불|안|못|X|x|×", s):
        return "운행 어려움"
    if re.search(r"가능|됨|O|o|○|양호", s):
        return "운행 가능"
    return ""


def clean_car(v: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\s*[(\[][^)\]]*[)\]]", "", v)).strip()


def parse_videos(value: str) -> tuple[list[dict], str]:
    """메모의 youtube 줄들 → [{"id", "url", "label", "short"}]. 주소를 못 읽으면 ([], 이유)."""
    videos = []
    for line in (value or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = YOUTUBE_RE.search(line)
        if not m:
            return [], f"유튜브 주소를 읽을 수 없습니다: '{line[:60]}'"
        label = (line[:m.start()] + line[m.end():]).strip(" -–—:()（）")
        videos.append({"id": m.group(1), "url": m.group(0), "label": label, "short": "/shorts/" in m.group(0)})
    return videos, ""


def compose(memo: dict) -> tuple[dict | None, str]:
    """메모 → 사례 글 조각. (결과, 이유) — 결과가 None 이면 이유가 건너뛴 까닭."""
    if not any(all(memo.get(k) for k in s) for s in REQUIRED_SETS):
        need = " / ".join("·".join(s) for s in REQUIRED_SETS)
        return None, f"메모에 필수 항목이 없습니다(둘 중 하나가 다 있어야 함: {need})"
    car = clean_car(memo["차종"])
    if not car:
        return None, "차종이 비어 있습니다"
    facts: list[tuple[str, str]] = [("차종", car)]
    year = ""
    if memo.get("연식"):
        year = year_of(memo["연식"])
        if not year:
            return None, f"연식 '{memo['연식']}' 을 읽을 수 없습니다(예: 2008)"
        facts.append(("연식", f"{year}년식"))
    start = ""
    if memo.get("시동"):
        start = start_state(memo["시동"])
        if not start:
            return None, f"시동 '{memo['시동']}' 을 읽을 수 없습니다(예: 시동됨 / 시동안됨)"
        facts.append(("시동", start))
    drive = drive_state(memo.get("운행", ""))
    if drive:
        facts.append(("운행", {"운행 가능": "가능", "운행 어려움": "어려움"}.get(drive, drive)))
    kind, kind_text = memo.get("상황", ""), None
    for word, text in SITUATION_TEXT.items():
        if word in kind.replace(" ", ""):
            kind, kind_text = "", text  # 정해 둔 상황은 정해 둔 문구로만 쓴다("일반폐차"는 쓰지 않음)
            break
    if kind_text:
        facts.append(("진행 내용", kind_text))
    short_kind = kind if kind and len(kind) <= 15 else ""
    if short_kind:
        facts.append(("문의 내용", short_kind))
    # '실제 진행'·'비고' 칸은 글에 쓰지 않는다: "이 차는 수출된다/안 된다"는 단정으로 읽히기 때문

    car_full = f"{year}년식 {car}" if year else car
    parts = [f"{car_full} 차량"]
    if start:
        parts.append("시동은 걸리는 상태였습니다." if start == "걸림" else "시동이 걸리지 않는 상태였습니다.")
    situation = (parts[0] + "으로, " + parts[1]) if len(parts) > 1 else parts[0] + "입니다."
    if drive == "현장 확인 필요":
        situation += " 운행 가능 여부는 현장에서 확인이 필요했습니다."
    elif drive == "운행 어려움":
        situation += " 운행은 어려운 상태였습니다."
    elif drive == "운행 가능":
        situation += " 운행은 가능한 상태였습니다."
    if kind and not short_kind:
        situation = kind if not memo.get("연식") else situation + " " + kind

    if memo.get("처리"):
        method = memo["처리"]
    else:
        method = ("차량 상태와 서류를 상담으로 확인하고, 폐차 처리와 수출 비교매입 중 이 차량 조건에 맞는 방법으로 "
                  "협력업체와 연결해 진행했습니다.")

    videos, why = parse_videos(memo.get("youtube", ""))
    if why:
        return None, why
    out = {
        "car": car_full, "facts": facts, "situation": situation, "method": method,
        "result": memo.get("결과", ""), "quote": memo.get("한마디", ""), "videos": videos,
    }
    text = " ".join([out["situation"], out["method"], out["result"], out["quote"]] + [v for _, v in facts]
                    + [v["label"] for v in videos])
    if m := MONEY_RE.search(text):
        return None, f"금액·시세 표현 '{m.group(0)}' 이 있습니다. 메모에서 금액을 빼 주세요"
    if m := PROMISE_RE.search(text):
        return None, f"결과를 약속하는 표현 '{m.group(0)}' 이 있습니다"
    if m := EXPORT_CLAIM_RE.search(text):
        return None, f"수출이 된다/안 된다는 단정 '{m.group(0)}' 이 있습니다"
    if m := CUSTOMER_RE.search(text):
        return None, f"고객 정보로 보이는 글 '{m.group(0)}' 이 있습니다(전화번호·차량번호·상세 주소 금지)"
    return out, ""


def region_label(c: dict) -> str:
    """사례의 가장 작은 지역 이름: 동이 있으면 동, 동 없는 사례는 시군구(세종은 시 이름)."""
    return c["dong"] or c["sigungu"] or "세종시"


def gu_page_exists(c: dict) -> bool:
    """이 사례의 구 페이지(/gu/)가 지금 있는지. 동 없는 사례는 구 페이지가 생길 때까지 cases/input 에서 기다린다."""
    from build_site import GU_DATA, gu_slug
    return gu_slug(c["sido"], c["sigungu"]) in {g["slug"] for g in load_json(GU_DATA, default=[])}


def page_slugs_by_region() -> dict[tuple[str, str, str], str]:
    return {(r["sido"], r["sigungu"], r["dong"]): r["slug"] for r in load_json(REGIONS_PATH, [])}


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


def first_sentence(text: str, limit: int = 70) -> str:
    s = re.split(r"(?<=[.!?])\s+", text.strip())[0]
    return s if len(s) <= limit else s[: limit - 1] + "…"


def check_folder(folder: Path, rows: list[dict]) -> tuple[dict | None, str]:
    """사례 폴더 하나를 사진 복사 없이 검사한다. PC 쪽(pc_cases.py)도 같은 검사를 쓴다."""
    memo_path = next((folder / n for n in MEMO_NAMES if (folder / n).exists()), None)
    if not memo_path:
        return None, "메모.txt 가 없습니다"
    memo = parse_memo(read_text_any(memo_path))
    if not memo.get("지역"):
        return None, "메모에 지역이 없습니다"
    region, why = resolve_region(memo["지역"], rows)
    if not region:
        return None, why
    body, why = compose(memo)
    if not body:
        return None, why
    photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_EXT)
    if not photos and not body["videos"]:
        return None, "사진(jpg/png/webp)이나 유튜브 영상(youtube: 줄)이 없습니다"
    if len(photos) > MAX_PHOTOS:
        return None, f"사진이 {len(photos)}장입니다. {MAX_PHOTOS}장까지만 올려 주세요"
    case_date = memo.get("날짜") or (m.group(0) if (m := re.match(r"\d{4}-\d{2}-\d{2}", folder.name)) else date.today().isoformat())
    if case_date in ("미상", "모름"):  # PC 원본 메모에 날짜가 없던 건: 날짜를 지어내지 않고 표시하지 않는다
        case_date = ""
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", case_date):
        return None, f"날짜는 2026-09-24 형식으로 적어 주세요 (현재 '{case_date}')"
    return {"memo": memo, "region": region, "body": body, "photos": photos, "date": case_date}, ""


def process_folder(folder: Path, rows: list[dict], page_slugs: dict, used_slugs: set[str]) -> dict | None:
    info, why = check_folder(folder, rows)
    if not info:
        print(f"건너뜀 {folder.name}: {why}")
        return None
    region, body, case_date = info["region"], info["body"], info["date"]

    from build_site import gu_slug
    place = make_slug(region["sido"], region["sigungu"], region["dong"]) if region["dong"] else gu_slug(region["sido"], region["sigungu"])
    base = f"case-{(case_date or date.today().isoformat()).replace('-', '')}-{place}"
    slug, n = base, 2
    while slug in used_slugs:
        slug, n = f"{base}-{n}", n + 1
    used_slugs.add(slug)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    names = [save_photo(p, IMAGES_DIR / f"{slug}-{i}") for i, p in enumerate(info["photos"], 1)]

    return {
        "slug": slug,
        "date": case_date,
        "sido": region["sido"], "sigungu": region["sigungu"], "dong": region["dong"],
        "region_slug": page_slugs.get((region["sido"], region["sigungu"], region["dong"])),
        "car": body["car"],
        "title": f"{region_label(region)} {body['car']} 폐차·수출 비교 상담 사례",
        "summary": first_sentence(body["situation"]),
        "facts": body["facts"],
        "situation": body["situation"], "method": body["method"],
        "result": body["result"], "quote": body["quote"],
        "thumb": names[0] if names else None, "photos": names,
        "videos": body["videos"],
    }


def case_meta_title(c: dict, area: str) -> str:
    """사례 페이지 제목 틀(2026-10-01): "{시군구} {차종} 폐차 사례 | {날짜}". 차종은 메모의 차종 칸(연식 빼고),
    없으면 "{시군구} 폐차 사례". 날짜가 없는 사례는 날짜를 지어내지 않고 뒷부분을 뺀다."""
    car = next((v for k, v in c.get("facts") or [] if k == "차종"), "").strip()
    head = f"{area} {car} 폐차 사례" if car else f"{area} 폐차 사례"
    if c.get("date"):
        y, m, d = (int(x) for x in c["date"].split("-"))
        return f"{head} | {y}년 {m}월 {d}일"
    return head


def render_case(c: dict, cfg: dict, template: str, region_slug: str | None,
                area: str | None = None, gu_page: str | None = None) -> str:
    base = cfg["site_base_url"].rstrip("/")
    full = " ".join(x for x in (c["sido"], c["sigungu"], c["dong"]) if x)
    area = area or c["sigungu"] or c["sido"]
    photos_html = "".join(
        f'<figure><img src="images/{esc(name)}" alt="{esc(c["title"])} 사진 {i}" loading="{"eager" if i == 1 else "lazy"}" width="1200" height="900"></figure>'
        for i, name in enumerate(c["photos"], 1)
    )
    videos = c.get("videos") or []
    if photos_html:
        photos_section = ('  <section>\n    <div class="wrap">\n      <div class="photos">\n        ' + photos_html
                          + '\n      </div>\n      <p class="photo-note">차량 번호와 개인정보는 가린 사진입니다.</p>\n    </div>\n  </section>\n')
    else:
        photos_section = ""
    video_html = ""
    if videos:
        video_html = '<h2>영상으로 보기</h2><div class="videos">' + "".join(
            f'<figure class="video{" short" if v.get("short") else ""}">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{esc(v["id"])}" title="{esc(v.get("label") or c["title"] + " 영상")}" '
            'loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
            f'<figcaption><a href="{esc(v["url"])}" target="_blank" rel="noopener noreferrer">'
            f'{esc(v.get("label") or ("쇼츠" if v.get("short") else "영상"))} — 유튜브에서 보기</a></figcaption></figure>'
            for v in videos) + "</div>"
    story_html = ""
    if c.get("facts"):
        story_html += "<h2>차량 정보</h2><p>" + " · ".join(f"{esc(k)} {esc(v)}" for k, v in c["facts"]) + "</p>"
    story = [("차량 상황", c["situation"]), ("진행 방식", c["method"])]
    if c["result"]:
        story.append(("결과", c["result"]))
    story_html += "".join(f"<h2>{esc(h)}</h2><p>{esc(t)}</p>" for h, t in story)
    if c["quote"]:
        story_html += f"<h2>고객 한마디</h2><blockquote>“{esc(c['quote'])}”</blockquote>"
    if region_slug:
        region_btn = f'<a class="btn btn-quote" href="../pages/{esc(region_slug)}.html" style="background:#fff">{esc(c["dong"])} 폐차 상담 페이지</a>'
    elif not c["dong"] and gu_page:
        region_btn = ""  # 동 없는 사례는 아래 구 페이지 버튼 하나만
    else:
        region_btn = '<a class="btn btn-quote" href="../index.html" style="background:#fff">지역별 상담 페이지 보기</a>'
    # 이 사례의 구 페이지가 있으면 그쪽으로도 연결한다(구 페이지 "폐차 사례" 칸에도 이 사례가 보임)
    gu_btn = (f'<a class="btn btn-quote" href="../gu/{esc(gu_page)}" style="background:#fff">{esc(area)} 폐차 상담 페이지</a>'
              if gu_page else "")
    from build_site import SIDO_SHORT
    import analytics
    values = {
        "ANALYTICS": analytics.head_html(cfg, "case", analytics.region_name(SIDO_SHORT.get(c["sido"], c["sido"]), c["sigungu"], c["dong"])),
        "META_TITLE": esc(case_meta_title(c, area)),
        "GU_BUTTON": gu_btn,
        "META_DESC": esc(f"{full}에서 진행한 {c['car']} 사례. {c['summary']} 폐차와 수출 중 유리한 쪽으로 안내. 전화 {cfg['phone_display']}"),
        "CANONICAL": f"{base}/cases/{c['slug']}.html",
        "OG_IMAGE": (f"{base}/cases/images/{c['thumb']}" if c.get("thumb")
                     else f"https://i.ytimg.com/vi/{videos[0]['id']}/hqdefault.jpg" if videos else f"{base}/favicon.ico"),
        "REGION_FULL_NAME": esc(full),
        "TITLE": esc(c["title"]),
        "DATE_TEXT": "{}년 {}월 {}일 진행".format(*(int(x) for x in c["date"].split("-"))) if c["date"] else "",
        "PHOTOS_SECTION": photos_section,
        "VIDEO_HTML": video_html,
        "STORY_HTML": story_html,
        "REGION_BUTTON": region_btn,
        "PHONE_TEL": cfg["phone_tel"],
        "PHONE_DISPLAY": cfg["phone_display"],
        "YOUTUBE_URL": esc(cfg["youtube_url"]),
        "BLOG_URL": esc(cfg["blog_url"]),
        **contact_parts(cfg, region_label(c)),
    }
    cleaned = LEADING_COMMENT_RE.sub("<!DOCTYPE html>", template, count=1)

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise KeyError(f"템플릿 자리 {key} 에 대응하는 값이 없습니다")
        return values[key]

    return re.sub(r"\{\{(\w+)\}\}", sub, cleaned)


def render_all_cases(regions: list[dict], cfg: dict) -> list[str]:
    """cases/index.json 의 사례 페이지를 지금 동 페이지 목록 기준으로 다시 만든다. 바뀐 파일 경로 목록."""
    index = load_json(INDEX_PATH, default=[])
    if not index:
        return []
    from build_site import GU_DATA, gu_file, gu_groups, gu_slug, gu_title_names
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    slugs = {(r["sido"], r["sigungu"], r["dong"]): r["slug"] for r in regions}
    title_names = gu_title_names(gu_groups(regions))
    gu_pages = {g["slug"] for g in load_json(GU_DATA, default=[])}
    changed = []
    for c in index:
        out = ROOT / "cases" / f"{c['slug']}.html"
        g = gu_slug(c["sido"], c["sigungu"])
        text = render_case(c, cfg, template, slugs.get((c["sido"], c["sigungu"], c["dong"])),
                           area=title_names.get(g), gu_page=gu_file(c["sido"], c["sigungu"]) if g in gu_pages else None)
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            out.write_text(text, encoding="utf-8")
            changed.append(f"cases/{c['slug']}.html")
    return changed


def main() -> None:
    # 폴더 이름을 주면 cases/input 안의 그 폴더만 처리한다(운영자가 특정 건만 먼저 올릴 때). 없으면 전부
    names = sys.argv[1:]
    folders = sorted(p for p in INPUT_DIR.glob("*") if p.is_dir()) if INPUT_DIR.exists() else []
    if names:
        missing = [n for n in names if not (INPUT_DIR / n).is_dir()]
        if missing:
            raise SystemExit(f"cases/input 에 없는 폴더: {', '.join(missing)}")
        folders = [p for p in folders if p.name in names]
    if not folders:
        print("처리할 사례 없음 (cases/input/ 에 폴더가 없습니다)")
        return

    ensure_pillow()
    index: list[dict] = load_json(INDEX_PATH, default=[])
    rows = load_csv_rows()
    page_slugs = page_slugs_by_region()
    used_slugs = {c["slug"] for c in index}

    done, skipped, waiting = [], 0, []
    for folder in folders:
        info, _ = check_folder(folder, rows)
        if info and not info["region"]["dong"] and not gu_page_exists(info["region"]):
            r = info["region"]
            waiting.append(folder.name)
            print(f"대기 {folder.name}: {r['sigungu'] or r['sido']} 사례(동 없음). 구 페이지가 아직 없어 cases/input 에 둡니다. 구 페이지가 생기면 다음 실행 때 자동으로 붙습니다")
            continue
        c = process_folder(folder, rows, page_slugs, used_slugs)
        if not c:
            skipped += 1
            continue
        index.insert(0, c)
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), str(DONE_DIR / folder.name))
        done.append(c)
        print(f"사례 생성: cases/{c['slug']}.html ({((c['sigungu'] or c['sido']) + ' ' + c['dong']).strip()} · {c['car']}, 사진 {len(c['photos'])}장)")

    if done:
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        # build_site.py 가 동 페이지와 함께 사례 페이지(render_all_cases)도 만든다
        subprocess.run([sys.executable, str(SCRIPTS / "build_site.py")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        update_sitemap(ROOT, [], paths=[f"cases/{c['slug']}.html" for c in done])
        print(f"지역 페이지 재렌더링 완료, sitemap 에 사례 {len(done)}건 추가")
        for c in done:
            if not c["dong"]:
                from build_site import gu_file
                print(f"  {c['slug']} → 동 없는 사례: 구 페이지 gu/{gu_file(c['sido'], c['sigungu'])} 에만 표시")
                continue
            shown = [p.stem for p in (ROOT / "pages").glob("*.html") if f"/cases/{c['slug']}.html" in p.read_text(encoding="utf-8")]
            where = ", ".join(sorted(shown)) if shown else "없음(같은 시군구에 동 페이지가 아직 없음. 페이지가 생기면 자동으로 붙음)"
            print(f"  {c['slug']} → 지역 페이지 {len(shown)}곳에 표시: {where}")
        # 기존 페이지 경고는 매번 같으니 오류와 요약 줄만 보여 준다
        result = subprocess.run([sys.executable, str(SCRIPTS / "check_pages.py")], cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        for line in result.stdout.splitlines():
            if not line.startswith("경고:"):
                print(line)
        if result.returncode != 0:
            sys.exit(result.returncode)
    print(f"완료: 사례 {len(done)}건 처리, {skipped}건 건너뜀, {len(waiting)}건 구 페이지 대기")
    if skipped:
        sys.exit(1)


if __name__ == "__main__":
    main()
