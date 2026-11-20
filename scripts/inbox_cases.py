"""
PC "사례 가져오기" 앞 단계: 구글 드라이브 인박스(G:\\내 드라이브\\폐차_인박스)에 휴대폰으로 올린 파일을
한 차씩 묶어 원본 폴더(폐차사진원본\\우선\\날짜_지역_차종)로 옮긴다. 설계는 docs/case-pipeline-2026-10-16.md [1].

순서
  python scripts/inbox_cases.py scan      인박스 파일을 올린 시간으로 묶기(30분 넘게 떨어지면 다른 차)
      → .cases_staging/inbox/gN/ 에 미리보기(위치 정보 지움)·영상 끝 5초 말(말.txt)·plan.json
      → Claude 가 미리보기와 말을 보고 .cases_staging/inbox/gN/answer.json 을 쓴다(형식은 아래)
  python scripts/inbox_cases.py apply gN  지역 검사 → 원본 우선/ 에 폴더 만들고 파일 옮기기, 등록증은 지우기
  python scripts/inbox_cases.py report    오늘 만든 폴더·보류(확인 필요) 요약, cases/input/인박스-확인-필요.md 다시 쓰기

차 폴더(2026-11-20 병한님): 인박스 안에 카톡 대화방 이름 그대로("탁송기사 대구 북구 02년 아반떼") 폴더를 만들고 사진을 넣으면
  폴더 하나 = 차 한 대(시간 묶음·알림보다 먼저). 폴더 이름에서 지역 낱말(시·군·구·동·읍·면은 빼고 적어도 됨)·연식·차종을 읽어
  ① 이미 만든 사례(cases/index.json)와 하나만 맞으면 answer.json 초안에 "붙일사례": slug(지역근거 "사례") — 새 사례가 아니라
     그 사례에 사진만 붙는다(pc_cases stage → build_cases.attach_photos, 모두 6장까지)
  ② 아니면 새 차: 거래 기록부에서 하나만 맞으면 그 지역(지역근거 "기록부"), 없으면 폴더 이름의 지역(시·군·구까지 정해질 때, "폴더이름")
  ③ 못 정하면 초안 없이 보류("확인 필요: '대구' 만으로는 구를 모름 — 폴더 이름에 구를 넣어 주세요"), 폴더는 인박스에 그대로.
  다 옮긴 폴더는 지운다. 이름에 "후기"가 든 폴더는 reviews.py 몫이라 보지 않는다.

병한님 알림(2026-10-28): 인박스에 _지역알림.json 이 있으면(클로드 채팅이 병한님 "○○ 올림"을 받고 적음)
  ① 시간 묶음보다 먼저 그 "차" 목록으로 나눈다. "파일" 이 이름 목록이면 그 파일만, 글자(예: "그 시각 묶음 전부")면
    "올린 시각"(분까지)에 올라온 시간 묶음을 통째로 그 차로. 남은 파일만 시간으로 묶는다.
  ② 그 차는 scan 이 answer.json 초안(지역·지역근거 "병한님"·차종·연식, 알림에 있으면 걱정·확인·고른쪽·이유도)을 써 둔다. "병한님"은 말·등록증·GPS 와 같은 급.
  ③ apply 로 원본 폴더를 만든 차는 _지역알림.json 에서 뺀다.
  "이름(1).jpg" 처럼 같은 묶음의 원본과 내용이 똑같은 사본은 옮기지 않고 지운다(드라이브 휴지통).

지역 알아내는 순서: ① 영상 마지막 5초의 말 ② 위치 정보(GPS) ③ 등록증 사진(지역만 읽고 파일은 지움).
  기록부(2026-11-05): 알림 없는 묶음의 촬영 날짜(EXIF, 없으면 올린 날) = 거래 기록부 입고일인 거래가 하나뿐이면 그 거래로 answer.json
  초안(지역근거 "기록부"), 둘 이상이면 붙이지 않고 plan.json 의 calendar_ask("[기록부 확인] … 사진 어느 차? 1 ○○ / 2 ○○").
  - GPS 가 거래처 폐차장·수출 사무실(data/partner_locations.json) 근처면 무시한다.
  - 거래처 주소가 아직 비어 있으면(2026-10-16) GPS 로만 정한 지역은 쓰지 않고 보류한다.
  - GPS 좌표는 PC 안(미리보기 폴더·보고)에만 두고 저장소에 올리지 않는다.

answer.json 형식 (Claude 가 씀)
  {"지역": "전남광주통합특별시 목포시 용해동", "지역근거": "말",          ← 말 / 등록증 / GPS / 병한님
   "차종": "에쿠스", "연식": "2010", "시동": "시동됨", "운행": "운행 가능",
   "상황": "차령초과말소", "처리": "",
   "차번호": "", "압류": "",                                             ← 간편조회 캡처에서(원본 메모에만 남음)
   "등록증": ["IMG_0003.jpg"], "조회": ["Screenshot_1.png"],              ← 원본 파일 이름
   "걱정": "", "확인": "", "고른쪽": "", "이유": "", "문의일": "", ...      ← (있을 때만) 사례 글 새 칸, 원본 메모로
   "보류": ""}                                                            ← 지역을 모르면 "확인 필요: <쉬운 말>"
"""
import argparse
import filecmp
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
NOTICE = "_지역알림.json"  # 병한님 "○○ 올림" 알림(클로드 채팅이 씀)
REGION_SOURCES = ("말", "등록증", "GPS", "병한님", "기록부", "폴더이름", "사례")  # 기록부 = 촬영 날짜가 입고일인 거래가 하나뿐(2026-11-05)
# 폴더이름 = 병한님이 붙인 차 폴더 이름(병한님과 같은 급), 사례 = 이미 만든 사례에 사진만 붙임(2026-11-20)
VIDEO_EXT = {".mp4", ".mov", ".3gp", ".m4v"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".amr"}
TEXT_EXT = {".txt"}     # 대본·녹음용 문장(사례 페이지 "영상에서 한 말"로 감, [3])
GROUP_GAP_MIN = 30      # 올린 시간이 이보다 떨어지면 다른 차
TAIL_SEC = 5            # 영상 마지막 몇 초의 말을 읽나
AUDIO_MAX_SEC = 60      # 녹음은 앞 60초만 글로 바꾼다
MEMO_KEYS = ("날짜", "지역", "차종", "연식", "시동", "운행", "상황", "처리", "차번호", "압류",
             # 사례 글 새 칸(case_story.STORY_KEYS): 병한님이 알려 준 사연이 있을 때만 answer.json 에 적는다
             "걱정", "확인", "고른쪽", "이유", "문의일", "인수일", "말소일", "끝한줄", "제목꼬리",
             "붙일사례")  # 이미 만든 사례 slug: 새 사례 대신 그 사례에 사진만 붙인다(build_cases.attach_photos, 2026-11-20)


def kind_of(p: Path) -> str:
    e = p.suffix.lower()
    return ("video" if e in VIDEO_EXT else "image" if e in IMAGE_EXT else "audio" if e in AUDIO_EXT
            else "text" if e in TEXT_EXT else "")


def inbox_files(inbox: Path) -> list[Path]:
    # 이름에 "후기"가 든 캡처는 차 묶음이 아니라 scripts/reviews.py 가 다룬다(2026-11-05)
    return sorted((p for p in inbox.iterdir() if p.is_file() and kind_of(p) and "후기" not in p.name), key=lambda p: p.stat().st_mtime)


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


def upload_time(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def load_notice(inbox: Path) -> dict:
    return load_json(inbox / NOTICE, default=None) or {}


def notice_groups(files: list[Path], cars: list[dict]) -> tuple[list[tuple[dict, list[Path]]], list[Path]]:
    """병한님 알림의 차마다 파일을 먼저 떼어 낸다. ([(차, 파일들)], 남은 파일)"""
    by_name = {p.name: p for p in files}
    time_groups = group_files(files)
    used: set[str] = set()
    out = []
    for car in cars:
        names = car.get("파일")
        if isinstance(names, list):
            picked = [by_name[n] for n in names if n in by_name]
        else:  # "그 시각 묶음 전부(…)": 올린 시각(분까지)에 올라온 파일이 든 시간 묶음 통째로
            at = (car.get("올린 시각") or "").strip()
            picked = next((g for g in time_groups if any(upload_time(p) == at for p in g)), [])
        picked = [p for p in picked if p.name not in used]
        if picked:
            used.update(p.name for p in picked)
            out.append((car, picked))
    return out, [p for p in files if p.name not in used]


# ---- 차 폴더(2026-11-20 병한님): 인박스 안에 "탁송기사 대구 02년 아반떼" 처럼 이름 붙인 폴더 하나 = 차 한 대 ----
FOLDER_DROP_RE = re.compile(r"^(탁송기사|탁송|기사님?|사진|영상)$")
FOLDER_YEAR_RE = re.compile(r"^((?:19|20)?\d{2})(?:년식?|식)?$")
PLACE_SUFFIX = ("시", "군", "구", "동", "읍", "면")
ATTACH_DAYS = 30  # 사진이 있는 사례는 사례 날짜와 촬영 날짜가 이 안일 때만 같은 차로 본다(사진 없는 사례는 날짜를 보지 않음)


def car_folders(inbox: Path) -> list[Path]:
    """인박스 바로 아래 차 폴더. '_'·'.' 로 시작하는 폴더, 문자백업·제외 폴더, 이름에 "후기"가 든 폴더(reviews.py 몫)는 보지 않는다."""
    return sorted(p for p in inbox.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))
                  and not any(w in p.name for w in ("문자백업", "제외", "후기")))


def folder_files(folder: Path) -> list[Path]:
    return sorted((p for p in folder.iterdir() if p.is_file() and kind_of(p)), key=lambda p: p.stat().st_mtime)


def place_names(rows: list[dict]) -> set[str]:
    from build_cases import SIDO_ALIASES
    names = set(SIDO_ALIASES) | {r["sido"] for r in rows} | {r["dong"] for r in rows}
    names |= {t for r in rows for t in r["sigungu"].split()}
    return names


def parse_folder_name(name: str, rows: list[dict], names: set[str] | None = None) -> dict:
    """'탁송기사 대구 02년 아반떼' → {"places": ["대구"], "year": "2002", "car": "아반떼"}.
    지역 낱말은 법정동 목록의 이름(끝의 시·군·구·동·읍·면을 빼고 적어도 됨: 의왕 → 의왕시, 신탄진 → 신탄진동), 나머지는 차종.
    순서는 상관없다. 연식은 '02년'·'2002'·'02년식'."""
    names = names if names is not None else place_names(rows)
    places, car, year = [], [], ""
    text = re.sub(r"\(\d+\)$", "", name.strip())
    # 띄어 쓰지 않은 이름("의왕sm3", "대구02년아반떼")도 한글 ↔ 영문·숫자 사이를 나눠 읽는다("14년"·"02년식"은 붙여 둠)
    text = re.sub(r"(?<=[가-힣])(?=[A-Za-z0-9])|(?<=[A-Za-z])(?=[가-힣])|(?<=\d)(?=[가-힣])(?!년|식)|(?<=년)(?=[가-힣])(?!식)|(?<=식)(?=[가-힣])", " ", text)
    for tok in re.split(r"[\s_\-·,]+", text):
        if not tok or FOLDER_DROP_RE.match(tok):
            continue
        if not year and (m := FOLDER_YEAR_RE.match(tok)):
            y = m.group(1)
            year = y if len(y) == 4 else (f"20{y}" if int(y) <= date.today().year % 100 else f"19{y}")
            continue
        if tok in names:
            places.append(tok)
            continue
        hit = next((tok + s for s in PLACE_SUFFIX if tok + s in names), None)
        if hit and not car:  # 차종 뒤에 오는 낱말은 지역으로 보지 않는다("아반떼 XD")
            places.append(hit)
            continue
        if not car:  # 붙여 쓴 "여주크루즈"·"탁송기사의왕": 앞쪽이 지역 이름이면 떼어 낸다(가장 긴 것부터, 두 글자 이상)
            head = re.sub(r"^(탁송기사|탁송)", "", tok)
            for k in range(len(head), 1, -1):
                pre = head[:k]
                got = pre if pre in names else next((pre + s for s in PLACE_SUFFIX if pre + s in names), None)
                if got:
                    places.append(got)
                    tok = head[k:]
                    break
            else:
                tok = head or tok
            if not tok:
                continue
        car.append(tok)
    return {"places": places, "year": year, "car": " ".join(car)}


def case_year(c: dict) -> str:
    text = " ".join([c.get("car") or ""] + [v for k, v in c.get("facts") or [] if k == "연식"])
    m = re.search(r"((?:19|20)\d{2})\s*년", text)
    return m.group(1) if m else ""


def case_car(c: dict) -> str:
    return re.sub(r"^\s*(?:19|20)\d{2}\s*년식\s*", "", c.get("car") or "").strip()


def place_hit(place: str, c: dict) -> bool:
    """폴더 이름의 지역 낱말 하나가 사례 지역(시·도/시·군·구/동)과 맞나."""
    from build_cases import SIDO_ALIASES
    sido = SIDO_ALIASES.get(place, place)
    return (sido == c.get("sido") or place in (c.get("sigungu") or "").split() or place == c.get("dong"))


def match_cases(parsed: dict, day: str, index: list[dict]) -> list[dict]:
    """폴더 이름(지역·차종·연식)과 맞는 이미 만든 사례. 지역 낱말이 전부 맞고, 차종이 서로 포함되고, 연식이 둘 다 있으면 같아야 한다.
    사진이 이미 있는 사례는 사례 날짜가 촬영 날짜 ±30일 안일 때만(같은 차종의 다른 차에 붙지 않게)."""
    from pc_cases import car_key
    want = car_key(parsed["car"])
    if not want or not parsed["places"]:
        return []
    try:
        d0 = date.fromisoformat(day)
    except ValueError:
        d0 = None
    out = []
    for c in index:
        have = car_key(case_car(c))
        if not have or not (want in have or have in want):
            continue
        if not all(place_hit(p, c) for p in parsed["places"]):
            continue
        cy = case_year(c)
        if parsed["year"] and cy and parsed["year"] != cy:
            continue
        if c.get("photos") and d0:
            try:
                if abs((date.fromisoformat(c.get("date") or "") - d0).days) > ATTACH_DAYS:
                    continue
            except ValueError:
                continue
        out.append(c)
    return out


def ledger_for_folder(parsed: dict, day: str) -> list[dict]:
    """거래 기록부에서 폴더 이름과 맞는 거래(지역 낱말 하나 이상 + 차종, 날짜·입고일이 촬영 날짜 ±30일). [{지역, 차종, 연식}]"""
    import ledger_read as L
    from inquiry_log import WIKI_DIR
    from pc_cases import car_key
    want = car_key(parsed["car"])
    if not want:
        return []
    try:
        d0 = date.fromisoformat(day)
    except ValueError:
        return []
    bases = [re.sub(r"(특별자치시|특별자치도|특별시|광역시|도|시|군|구|동|읍|면)$", "", p) or p for p in parsed["places"]]
    out = []
    for r in L.records(WIKI_DIR):
        if r.get("거래상태") == "종료":
            continue
        days = [x for x in (r.get("입고일"), r.get("날짜")) if L.is_day(x or "")]
        if not days or min(abs((date.fromisoformat(x) - d0).days) for x in days) > ATTACH_DAYS:
            continue
        have = car_key(L.car_name(r.get("차종", "")))
        if not have or not (want in have or have in want):
            continue
        if bases and not any(b and b in (r.get("지역") or "") for b in bases):
            continue
        y = L.model_year(r.get("연식", ""))
        if parsed["year"] and y and parsed["year"] != y:
            continue
        out.append({"지역": r.get("지역", ""), "차종": L.car_name(r.get("차종", "")), "연식": y})
    return out


def folder_region(parsed: dict, rows: list[dict]) -> dict | None:
    """폴더 이름의 지역 낱말만으로 정한 지역(시·군·구까지 정해질 때). '대구'처럼 시·도뿐이면 None."""
    text = " ".join(parsed["places"])
    region, _ = resolve_region(text, rows)
    return region or whole_city(text, rows)


def safe_label(name: str) -> str:
    """보고·저장소 목록에 적을 폴더 이름. 차번호·전화번호 꼴이 섞였으면 이름 대신 '(이름에 번호가 있어 숨김)'."""
    import ledger_read as L
    return "(이름에 번호가 있어 숨김)" if re.search(r"\d{2,3}\s?[가-힣]\s?\d{4}|\d{3,4}-?\d{4}", name) or L.CAR_BAD_RE.search(name) else name


def folder_draft(folder: Path, files: list[Path], rows: list[dict], names: set[str], index: list[dict]) -> tuple[dict | None, dict]:
    """차 폴더 하나 → (answer.json 초안 또는 None, plan 에 적을 칸).
    ① 이미 만든 사례와 하나만 맞으면 그 사례에 사진만 붙인다(붙일사례) ② 아니면 새 차: 기록부에서 하나만 맞으면 그 지역,
    없으면 폴더 이름의 지역(시·군·구까지 정해질 때) ③ 못 정하면 초안 없이 보류 이유만."""
    parsed = parse_folder_name(folder.name, rows, names)
    days = [shot_day(p) for p in files if kind_of(p) in ("image", "video")] or [upload_time(files[0])[:10]]
    day = max(set(days), key=days.count)
    info = {"folder": safe_label(folder.name), "parsed": parsed, "shot_day": day}
    base = {"시동": "", "운행": "", "상황": "", "처리": "", "차번호": "", "압류": "", "등록증": [], "조회": [], "보류": ""}
    if not parsed["car"]:
        info["hold"] = "확인 필요: 폴더 이름에서 차종을 못 찾음 (예: 탁송기사 대구 북구 02년 아반떼)"
        return None, info
    hits = match_cases(parsed, day, index)
    if len(hits) == 1:
        c = hits[0]
        info["attach"] = c["slug"]
        region = " ".join(x for x in (c["sido"], c["sigungu"], c["dong"]) if x)
        return {**base, "지역": region, "지역근거": "사례", "차종": case_car(c), "연식": case_year(c) or parsed["year"],
                "붙일사례": c["slug"]}, info
    if len(hits) > 1:
        info["hold"] = (f"확인 필요: 이미 만든 사례 {len(hits)}건과 맞음 — 폴더 이름에 구·동이나 연식을 더 넣어 주세요")
        return None, info
    led = ledger_for_folder(parsed, day)
    if len(led) == 1:
        h = led[0]
        region, _ = resolve_region(h["지역"], rows)
        if not region:  # 기록부 지역이 '경기 포천' 처럼 줄인 이름이면 폴더 이름 낱말과 합쳐 다시
            region = folder_region(parse_folder_name(h["지역"] + " " + " ".join(parsed["places"]), rows, names) | {"car": ""}, rows)
        if region:
            info["ledger"] = "기록부 1건 맞음"
            return {**base, "지역": " ".join(x for x in (region["sido"], region["sigungu"], region["dong"]) if x),
                    "지역근거": "기록부", "차종": parsed["car"], "연식": parsed["year"] or h["연식"]}, info
    region = folder_region(parsed, rows)
    if region:
        return {**base, "지역": " ".join(x for x in (region["sido"], region["sigungu"], region["dong"]) if x),
                "지역근거": "폴더이름", "차종": parsed["car"], "연식": parsed["year"]}, info
    where = " ".join(parsed["places"]) or "지역 없음"
    info["hold"] = (f"확인 필요: '{where}' 만으로는 구를 모름" + (f"(기록부에 맞는 거래 {len(led)}건)" if led else "")
                    + " — 폴더 이름에 구를 넣어 주세요 (예: 탁송기사 대구 북구 02년 아반떼)")
    return None, info


def duplicate_of(p: Path, names: set[str]) -> str:
    """'사진(1).jpg' 가 같은 묶음의 '사진.jpg' 와 내용이 똑같으면 그 원본 이름"""
    m = re.match(r"(.+?)\s*\(\d+\)(\.[^.]+)$", p.name)
    if not m or (base := m.group(1) + m.group(2)) not in names:
        return ""
    return base if filecmp.cmp(p, p.with_name(base), shallow=False) else ""


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



def shot_day(p: Path) -> str:
    """촬영 날짜(YYYY-MM-DD): 사진 EXIF DateTimeOriginal → DateTime, 영상 creation_time, 없으면 올린 날(2026-11-05)."""
    try:
        if kind_of(p) == "image":
            from PIL import Image
            with Image.open(p) as im:
                ex = im.getexif()
                v = ex.get_ifd(0x8769).get(0x9003) or ex.get(0x0132)
            if v and re.match(r"\d{4}:\d{2}:\d{2}", str(v)):
                return str(v)[:10].replace(":", "-")
        elif kind_of(p) == "video":
            v = ffprobe_json(p).get("tags", {}).get("creation_time", "")
            if re.match(r"\d{4}-\d{2}-\d{2}", v):
                return v[:10]
    except Exception:
        pass
    return upload_time(p)[:10]

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
    noticed, rest = notice_groups(inbox_files(inbox), load_notice(inbox).get("차", []))
    # 차 폴더(2026-11-20): 폴더 하나 = 차 한 대. 시간 묶음·알림보다 먼저, 폴더 안 파일만
    folders = [(f, fs) for f in car_folders(inbox) if (fs := folder_files(f))]
    groups = [({"_folder": f}, fs) for f, fs in folders] + noticed + [(None, files) for files in group_files(rest)]
    rows = load_csv_rows()
    names_all = place_names(rows)
    index = load_json(ROOT / "cases" / "index.json", default=[]) or []
    plan = {"date": date.today().isoformat(), "inbox": str(inbox), "groups": {},
            # 사진이 아직 안 들어간 차 폴더(업로드가 안 됐거나 '스캔'으로 올라감): 보고에 알린다(2026-11-20)
            "empty_folders": [safe_label(f.name) for f in car_folders(inbox) if not folder_files(f)]}
    for gi, (car, files) in enumerate(groups, 1):
        gid = f"g{gi}"
        d = STAGING / gid
        d.mkdir()
        items, speech, gps = [], [], []
        names = {p.name for p in files}
        for fi, p in enumerate(files, 1):
            k = kind_of(p)
            item = {"file": p.name, "kind": k, "time": upload_time(p)}
            if dup := duplicate_of(p, names):
                item["dup"] = dup
                items.append(item)
                continue
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
        if car and car.get("_folder"):
            folder = car["_folder"]
            plan["groups"][gid]["dir"] = folder.name  # 파일은 인박스 안 이 폴더에 있음
            draft, info = folder_draft(folder, files, rows, names_all, index)
            plan["groups"][gid].update(info)
            if draft:
                (d / "answer.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")
        elif car:
            plan["groups"][gid]["notice"] = {k: v for k, v in car.items() if k != "파일"}
            # answer.json 초안: 병한님이 알려 준 지역·차종·연식. 시동·상황 등은 Claude 가 미리보기·말을 보고 채운다
            draft = {"지역": car.get("지역", ""), "지역근거": "병한님", "차종": car.get("차종", ""),
                     "연식": car.get("연식", ""), "시동": "", "운행": "", "상황": "", "처리": "",
                     "차번호": "", "압류": "", "등록증": [], "조회": [], "보류": ""}
            # 병한님이 채팅으로 말한 사연(걱정·확인·고른쪽·이유 등, 2026-11-17)이 알림에 있으면 초안에 그대로 옮긴다
            draft.update({k: car[k] for k in MEMO_KEYS[10:] if str(car.get(k) or "").strip()})
            (d / "answer.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")
        elif files:
            # 사진 ↔ 입고 날짜(2026-11-05): 촬영 날짜(EXIF, 없으면 올린 날) = 기록부 입고일인 거래가 하나뿐이면 그 거래로 초안,
            # 둘 이상이면 붙이지 않고 캘린더 [기록부 확인] 부탁(병한님 알림이 있는 차는 위에서 알림이 먼저)
            days = [shot_day(p) for p in files if kind_of(p) in ("image", "video")] or [upload_time(files[0])[:10]]
            day = max(set(days), key=days.count)
            from pc_cases import ledger_by_arrival
            hits = ledger_by_arrival(day)
            plan["groups"][gid]["shot_day"] = day
            if len(hits) == 1 and hits[0]["지역"]:
                h = hits[0]
                plan["groups"][gid]["ledger"] = "입고일 맞음(1건)"
                draft = {"지역": h["지역"], "지역근거": "기록부", "차종": h["차종"], "연식": h["연식"], "시동": "", "운행": "",
                         "상황": "", "처리": "", "차번호": "", "압류": "", "등록증": [], "조회": [], "보류": ""}
                (d / "answer.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")
            elif len(hits) > 1:
                ask = " / ".join(f"{i} {h['차종'] or '차종 모름'}({h['지역'] or '지역 모름'})" for i, h in enumerate(hits, 1))
                plan["groups"][gid]["ledger"] = f"같은 날 입고 {len(hits)}대 — 붙이지 않음"
                plan["groups"][gid]["calendar_ask"] = f"[기록부 확인] {day} 사진 어느 차? {ask}"
    (STAGING / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"인박스 파일 {sum(len(fs) for _, fs in groups)}개 → {len(groups)}대로 묶음 ({STAGING.relative_to(ROOT)})")
    for gid, g in plan["groups"].items():
        kinds = {k: sum(1 for i in g["files"] if i["kind"] == k) for k in ("video", "image", "audio")}
        print(f"  {gid}: 영상 {kinds['video']} · 사진 {kinds['image']} · 녹음 {kinds['audio']}, "
              f"{g['files'][0]['time']}~{g['files'][-1]['time']}"
              + (f" · 똑같은 사본 {dups}개(옮기지 않고 지움)" if (dups := sum(1 for i in g["files"] if i.get("dup"))) else "")
              + (f" — 병한님 알림 '{g['notice'].get('이름', '')}'(answer.json 초안 씀)" if g.get("notice") else "")
              + (f" — 폴더 '{g['folder']}'" if g.get("folder") else ""))
        if g.get("attach"):
            print(f"     이미 만든 사례 {g['attach']} 에 사진만 붙임(answer.json 초안 씀, 붙일사례)")
        elif g.get("folder") and not g.get("hold"):
            print("     새 차(answer.json 초안 씀, 지역근거 " + ("기록부" if g.get("ledger") else "폴더이름") + ")")
        if g.get("hold"):
            print(f"     {g['hold']} (폴더는 인박스에 그대로 둠)")
        if g.get("ledger"):
            print(f"     기록부(촬영 {g.get('shot_day')}): {g['ledger']}" + (" → answer.json 초안(지역근거 기록부)" if "1건" in g["ledger"] else ""))
        if g.get("calendar_ask"):
            print(f"     캘린더 부탁: {g['calendar_ask']}")
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


def whole_city(text: str, rows: list[dict]) -> dict | None:
    """'경기도 안산시'처럼 일반구가 있는 시까지만 적힌 지역 → {"sido", "sigungu": "안산시", "dong": ""}(구가 한 시 안일 때만)"""
    toks = text.split()
    if not toks:
        return None
    cities = {(r["sido"], r["sigungu"].split()[0]) for r in rows
              if r["sigungu"].split() and r["sigungu"].split()[0] == toks[-1]
              and all(t in r["sido"] or r["sido"].startswith(t) for t in toks[:-1])}
    if len(cities) != 1:
        return None
    sido, city = cities.pop()
    return {"sido": sido, "sigungu": city, "dong": ""}


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
    inbox_root = Path(plan["inbox"])
    inbox = inbox_root / g["dir"] if g.get("dir") else inbox_root  # 차 폴더면 그 폴더 안
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
        if src_kind not in REGION_SOURCES:
            hold = "확인 필요: 지역근거가 말·등록증·GPS·병한님·기록부 중 하나가 아님"
        elif src_kind == "GPS" and not partners_ready():
            hold = "확인 필요: 위치 정보로만 지역을 추정함(거래처 주소 미등록)"
        else:
            rows = load_csv_rows()
            region, why = resolve_region(ans.get("지역", ""), rows)
            if not region and src_kind in ("병한님", "폴더이름", "기록부", "사례"):
                region = whole_city(ans.get("지역", ""), rows)  # "안산시"처럼 구를 모르는 시: 폴더는 만들고 사례는 구가 정해질 때까지 대기
            if not region:
                hold = f"확인 필요: 지역 '{ans.get('지역', '')}' — {why}"
            elif not ans.get("차종"):
                hold = "확인 필요: 차종 모름"
    if hold:
        g.update(status="held", hold=hold, car=ans.get("차종", ""))
        save_plan(plan)
        print(f"{args.gid}: 보류 — {hold} (파일은 인박스에 그대로 둠)")
        return

    # 같은 묶음 원본과 똑같은 '(1)' 사본은 옮기지 않고 지운다(드라이브 휴지통)
    for i in g["files"]:
        if i.get("dup"):
            (inbox / i["file"]).unlink(missing_ok=True)
    g["files"] = [i for i in g["files"] if not i.get("dup")]
    first = min(datetime.strptime(i["time"], "%Y-%m-%d %H:%M") for i in g["files"])
    car = safe_name(ans["차종"])
    year = re.sub(r"\D", "", ans.get("연식", ""))[:4]
    situ = "사진추가" if ans.get("붙일사례") else (safe_name(ans.get("상황", "")) or "일반폐차")
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
    g.update(status="applied", made=f"우선\\{dest.name}", car=ans["차종"], region=memo["지역"])
    save_plan(plan)
    if g.get("dir"):  # 다 옮긴 차 폴더는 지운다(남은 파일이 있으면 그대로 둠)
        try:
            inbox.rmdir()
        except OSError:
            pass
    if g.get("notice"):  # 처리한 차는 병한님 알림에서 뺀다
        data = load_notice(inbox_root)
        if data:
            data["차"] = [c for c in data.get("차", []) if c.get("이름") != g["notice"].get("이름")]
            (inbox_root / NOTICE).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.gid}: 원본 폴더 만듦 → 우선\\{dest.name} (지역 근거: {src_kind})"
          + (f" — 사례 {ans['붙일사례']} 에 사진만 붙일 차" if ans.get("붙일사례") else ""))


def cmd_report(args) -> None:
    plan = load_json(STAGING / "plan.json", default=None) or {"groups": {}}
    made = [g for g in plan["groups"].values() if g.get("status") == "applied"]
    held = [g for g in plan["groups"].values() if g.get("status") != "applied"]
    print(f"인박스: 폴더 만든 차 {len(made)}대, 보류 {len(held)}대")
    for name in plan.get("empty_folders", []):
        print(f"  확인 필요: 폴더 '{name}' — 폴더가 비어 있음(사진이 안 올라감. 폴더 안에서 + → 업로드로 다시 올려 주세요)")
    for g in made:
        print(f"  만듦: {g.get('made') or g.get('folder')}" + (f" (사례 {g['attach']} 에 사진 붙임)" if g.get("attach") else ""))
    rows = []
    for g in held:
        t = g["files"][0]["time"] if g["files"] else ""
        kinds = {k: sum(1 for i in g["files"] if i["kind"] == k) for k in ("video", "image", "audio")}
        reason = g.get("hold") or "확인 필요: answer.json 을 쓰지 않음"
        where = f"폴더 '{g['folder']}'" if g.get("folder") else f"{t} 올린 차"
        print(f"  보류: {where}({g.get('car') or g.get('parsed', {}).get('car') or '차종 모름'}) — {reason}")
        if g.get("folder"):  # 아침 보고 "오늘 병한님이 할 것" 줄
            print(f"  확인 필요: 폴더 '{g['folder']}' — {reason.removeprefix('확인 필요: ')}")
        # 저장소에 올라가는 목록: 올린 시각·파일 수·차종·이유만(위치·차번호·말은 넣지 않음)
        rows.append(f"| {t}" + (f" (폴더 {g['folder']})" if g.get("folder") else "") + f" | 영상 {kinds['video']} · 사진 {kinds['image']} · 녹음 {kinds['audio']} | "
                    f"{g.get('car') or g.get('notice', {}).get('차종') or g.get('parsed', {}).get('car') or '모름'} | {reason} |")
    HOLD_MD.parent.mkdir(parents=True, exist_ok=True)
    HOLD_MD.write_text(
        "# 인박스 확인 필요 (PC 사례 가져오기가 매일 다시 씀)\n\n"
        "구글 드라이브 `폐차_인박스` 에 올린 차 중 지역·차종을 알아내지 못해 보류한 것입니다. "
        "파일은 인박스에 그대로 있습니다. 영상 끝에 지역을 다시 말해 올리거나 병한님이 알려 주시면 다음 실행 때 들어갑니다.\n\n"
        f"기준: {date.today().isoformat()}\n\n"
        + ("| 올린 시각 | 파일 | 차종 | 이유 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n" if rows else "보류된 차 없음\n")
        + "".join(f"\n빈 폴더: '{n}' — 사진이 안 올라갔습니다. 폴더 안에서 + → 업로드로 다시 올려 주세요\n" for n in plan.get("empty_folders", [])),
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
