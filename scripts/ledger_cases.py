"""
끝난 거래를 사진 없이도 사례로 (2026-11-24 병한님 "1 2": 사진·영상이 없는 지역에도 실제 거래로 사례를 채우기).

거래 기록부(병한-업무위키\\폐차\\거래기록\\*.md, 운영자 PC 에만 있음)에서 입고·말소가 끝났는데 아직 사례가 없는 거래를 찾고,
PC 예약 작업 "폐차 사례 가져오기"가 그 거래의 통화표 줄·거래 노트로 사연을 확인해 적어 주면 cases/input/ 에
사진 없는 사례 입력(메모.txt 하나)을 만든다. 사례 페이지는 다음 날 아침 루틴의 build_cases.py 가 만든다.
사진이 나중에 인박스로 오면 그 사례에 붙는다(inbox_cases.py 의 차 폴더 → build_cases.attach_photos). 그때 블로그 초안 대상도 된다.

  python scripts/ledger_cases.py todo [--n 5] [--since YYYY-MM-DD]   # 대상 보기(읽기만)
  python scripts/ledger_cases.py make <id> --answer <파일.json>      # 사례 입력 만들기 + 검사
  python scripts/ledger_cases.py skip <id> "<짧은 이유>"             # 이 거래는 만들지 않음(다시 고르지 않게)
  python scripts/ledger_cases.py status                              # 숫자만

지키는 것
- 기록부에서 읽는 칸은 ledger_read.FIELDS(날짜·지역·거래상태·입고일·말소상태·차종·연식·차상태·수출여부·폐차종류·유입경로·안된이유)와
  말소 날짜 한 칸뿐이다. 이름·전화·차번호·금액·메모 칸은 읽지 않는다.
- 저장소에 남는 것: cases/input/<날짜>-<지역>-<차종>-기록부/메모.txt(사례에 공개되는 칸만)와 data/ledger_cases.json
  (거래 파일 이름을 알아볼 수 없게 바꾼 id, 만든 폴더 이름, 건너뛴 짧은 이유). 기록부 파일 이름은 어디에도 쓰지 않는다.
- 지어내지 않는다: 차종·연식·날짜·시·군은 기록부 값만 쓰고, 사연(상황·처리·걱정·확인·이유…)은 PC 작업이 통화표·거래 노트에서
  이 차라고 확신할 때만 적는다. 사진이 없으므로 사연 칸이 2개보다 적으면 만들지 않는다(build_cases.check_folder).
- 같은 거래로 사례를 두 번 만들지 않는다: 같은 시·군 + 차종이 겹침 + (연식을 둘 다 알면 같음) + 날짜가 MATCH_DAYS 일 안인
  사례(cases/index.json)나 대기 입력(cases/input)이 있으면 "이미 사례 있음"으로 본다. todo 는 그 시·군의 가까운 날짜 사례도
  같이 보여 주므로, 이름이 다르게 적힌 같은 차로 보이면 PC 작업이 skip 으로 넘긴다.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_cases as BC  # noqa: E402
import case_story  # noqa: E402
import ledger_read as L  # noqa: E402
from inquiry_log import SIDO_ALIAS, WIKI_DIR, part_match  # noqa: E402

STATE = ROOT / "data" / "ledger_cases.json"
KST = timezone(timedelta(hours=9))
MATCH_DAYS = 31          # 이 날 수 안의 같은 시·군·같은 차 사례는 같은 거래로 본다
NEAR_DAYS = 45           # todo 가 "그 시·군의 가까운 날짜 사례"로 보여 주는 범위
TAG = "기록부"            # 폴더 이름 끝(어느 길로 들어온 사례인지)
ANSWER_KEYS = ("지역", "상황", "처리", "걱정", "확인", "고른쪽", "이유", "말소일", "끝한줄", "제목꼬리", "결과", "한마디")
NEED_KEYS = ("상황", "처리")   # 사진 없는 사례의 본문 두 칸(build_cases.REQUIRED_SETS 둘째 꼴)
SIDES = ("폐차", "수출", "비교중")
# 손님 나이·성별·형편은 사례에 쓰지 않는다(2026-10-27). blog_drafts.AGE_SEX_RE 와 같은 낱말
AGE_SEX_RE = re.compile(r"할머니|할아버지|어르신|아주머니|아저씨|여성분|남성분|여자분|남자분|여자\s*손님|남자\s*손님|노인|고령|연세"
                        r"|[2-9]0대|사모님|사장님")
CLOSE_DAY_RE = re.compile(r"^말소(?:일|[ \t]*날짜|일자|완료일?)?:[ \t]*(\d{4}-\d{2}-\d{2})[ \t]*$", re.M)
YEAR_IN_CAR_RE = re.compile(r"((?:19[89]|20[0-4])\d)\s*년식?\s*")
SKIP_WHY_MAX = 30


def today() -> date:
    return datetime.now(KST).date()


def rec_id(file_name: str) -> str:
    """기록부 파일 이름 → 알아볼 수 없는 10글자(저장소에는 이것만 남긴다)."""
    return hashlib.sha1(("pyecha-ledger:" + file_name).encode("utf-8")).hexdigest()[:10]


def car_key(v: str) -> str:
    """차 이름을 견줄 때 쓰는 꼴(pc_cases.car_key 와 같음): 숫자·띄어쓰기·'년식'·괄호를 뺀 소문자."""
    return re.sub(r"[\s()\[\]\d년식]", "", v or "").lower()


def day_of(v: str) -> date | None:
    return case_story.parse_day(v or "")


def load_state() -> dict:
    try:
        s = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        s = {}
    s.setdefault("made", {})
    s.setdefault("skip", {})
    return s


def save_state(s: dict) -> None:
    out = {"_comment": "scripts/ledger_cases.py 가 씀(손으로 고치지 않음). 끝난 거래를 사진 없이 사례로 만든 기록. "
                       "id 는 거래 기록부 파일 이름을 알아볼 수 없게 바꾼 글자라 손님 정보가 아님.",
           "made": dict(sorted(s["made"].items())), "skip": dict(sorted(s["skip"].items()))}
    STATE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def region_from_ledger(text: str, sido: str, city: str, rows: list[dict]) -> dict | None:
    """기록부 지역 글이 구(와 동)까지 정해 주면 그 정식 지역. '경기 화성 동탄구' → 경기도 화성시 동탄구, '경북 구미 진평동' → … 진평동.
    줄임말(경기·화성)을 정식 이름으로 바꿔 build_cases.resolve_region 에 맡긴다. 시·군까지만 있거나 여러 곳과 맞으면 None."""
    tokens = re.sub(r"[,()]", " ", text).split()
    if not tokens:
        return None
    if SIDO_ALIAS.get(tokens[0]) == sido:
        tokens[0] = sido
    for i, t in enumerate(tokens):
        if city and t != sido and part_match(city, t):
            tokens[i] = city
            break
    region, _ = BC.resolve_region(" ".join(tokens), rows)
    if region and region["sido"] == sido and region["sigungu"].split()[:1] == ([city] if city else []):
        return region
    return None


def deals(folder: Path, rows: list[dict] | None = None) -> tuple[list[dict], Counter]:
    """끝난 거래(입고 완료·말소 완료) 가운데 사례로 쓸 뼈대가 읽히는 것. 못 쓰는 까닭은 세기만 한다."""
    places = L.gu_places()
    rows = rows if rows is not None else BC.load_csv_rows()
    out, why = [], Counter()
    for r in L.records(folder):
        if not L.arrived(r):
            continue
        asked = r["날짜"] if L.is_day(r["날짜"]) else ""
        got = r["입고일"] if L.is_day(r["입고일"]) else ""
        car_raw = L.car_name(r["차종"])
        year = L.model_year(r["연식"]) or L.model_year(car_raw)
        car = re.sub(r"\s+", " ", YEAR_IN_CAR_RE.sub("", car_raw)).strip()
        try:
            place = L.city_of(r["지역"], places)
        except Exception:  # 세종처럼 시·군 이름이 빈 곳
            place = None
        if not place and r["지역"].strip():  # 줄임말이 아닌 정식 이름·세종: 사례 쪽 규칙으로 한 번 더(구 페이지가 있을 때만)
            reg, _ = BC.resolve_region(r["지역"], rows)
            if reg and BC.gu_page_exists(reg):
                place = (reg["sido"], reg["sigungu"].split()[0] if reg["sigungu"] else "")
        if not (got or asked):
            why["날짜 없음"] += 1
            continue
        if not car or not car_key(car):
            why["차종을 못 읽음"] += 1
            continue
        if not place:
            why["지역을 구 페이지로 못 정함"] += 1
            continue
        closed = ""
        try:
            m = CLOSE_DAY_RE.search((folder / r["file"]).read_text(encoding="utf-8", errors="replace"))
            closed = m.group(1) if m and L.is_day(m.group(1)) else ""
        except OSError:
            pass
        out.append({"id": rec_id(r["file"]), "asked": asked, "got": got, "day": got or asked, "closed": closed,
                    "car": car, "year": year, "start": L.start_state(r["차상태"]), "side": L.chosen_side(r),
                    "region_text": re.sub(r"\s+", " ", r["지역"]).strip(), "sido": place[0], "city": place[1],
                    "region": region_from_ledger(r["지역"], place[0], place[1], rows)})
    return out, why


def known_cases(rows: list[dict]) -> list[dict]:
    """이미 있는 사례와 대기 중인 입력: 같은 거래인지 견줄 칸만."""
    out = []
    for c in json.loads(BC.INDEX_PATH.read_text(encoding="utf-8")) if BC.INDEX_PATH.exists() else []:
        st = c.get("story") or {}
        m = YEAR_IN_CAR_RE.search(c.get("car") or "")
        out.append({"sido": c["sido"], "city": c["sigungu"].split()[0] if c["sigungu"] else "",
                    "car": car_key(c.get("car")), "year": m.group(1) if m else "",
                    "days": [d for v in (c.get("date"), st.get("문의일"), st.get("인수일")) if (d := day_of(v))],
                    "label": f"{c['sigungu'] or c['sido']} {c.get('car') or ''} {c.get('date') or '날짜 모름'}"
                             + ("" if c.get("photos") else " (사진 없음)")})
    for f in sorted(p for p in BC.INPUT_DIR.iterdir() if p.is_dir()) if BC.INPUT_DIR.exists() else []:
        memo_path = next((f / n for n in BC.MEMO_NAMES if (f / n).exists()), None)
        if not memo_path:
            continue
        memo = BC.parse_memo(BC.read_text_any(memo_path))
        region, _ = BC.resolve_region(memo.get("지역", ""), rows)
        if not region:
            continue
        car = memo.get("차종", "")
        m = YEAR_IN_CAR_RE.search(car)
        name_day = re.match(r"\d{4}-\d{2}-\d{2}", f.name)
        out.append({"sido": region["sido"], "city": region["sigungu"].split()[0] if region["sigungu"] else "",
                    "car": car_key(car), "year": L.model_year(memo.get("연식", "")) or (m.group(1) if m else ""),
                    "days": [d for v in (memo.get("날짜"), memo.get("문의일"), memo.get("인수일"),
                                         name_day.group(0) if name_day else "") if (d := day_of(v))],
                    "label": f"{region['sigungu'] or region['sido']} {car} (대기 중인 입력)"})
    return out


def same_place(d: dict, c: dict) -> bool:
    return c["sido"] == d["sido"] and c["city"] == d["city"]


def covered(d: dict, known: list[dict]) -> str:
    """이 거래의 사례가 이미 있으면 그 사례 한 줄, 없으면 ""."""
    dk, ddays = car_key(d["car"]), [x for v in (d["asked"], d["got"]) if (x := day_of(v))]
    for c in known:
        if not same_place(d, c) or not c["car"] or not (c["car"] in dk or dk in c["car"]):
            continue
        if c["year"] and d["year"] and c["year"] != d["year"]:
            continue
        if not c["days"] or any(abs((a - b).days) <= MATCH_DAYS for a in c["days"] for b in ddays):
            return c["label"]
    return ""


def near_cases(d: dict, known: list[dict]) -> list[str]:
    """그 시·군의 가까운 날짜 사례(이름이 다르게 적힌 같은 차인지 PC 작업이 보라고)."""
    ddays = [x for v in (d["asked"], d["got"]) if (x := day_of(v))]
    return [c["label"] for c in known if same_place(d, c)
            and (not c["days"] or any(abs((a - b).days) <= NEAR_DAYS for a in c["days"] for b in ddays))]


def targets(folder: Path, since: str = "") -> tuple[list[dict], dict]:
    rows = BC.load_csv_rows()
    known = known_cases(rows)
    state = load_state()
    all_deals, why = deals(folder, rows)
    counts = {"끝난 거래": len(all_deals) + sum(why.values()), **why, "이미 사례 있음": 0, "만들어 둠": 0, "건너뜀": 0, "기간 밖": 0}
    has_case = Counter((c["sido"], c["city"]) for c in known)
    out = []
    for d in all_deals:
        if d["id"] in state["made"]:
            counts["만들어 둠"] += 1
        elif d["id"] in state["skip"]:
            counts["건너뜀"] += 1
        elif covered(d, known):
            counts["이미 사례 있음"] += 1
        elif since and d["day"] < since:
            counts["기간 밖"] += 1
        else:
            d["near"] = near_cases(d, known)
            d["place_cases"] = has_case[(d["sido"], d["city"])]
            out.append(d)
    # 사례가 하나도 없는 시·군 먼저(첫 사례가 생기는 곳), 그다음 최근 거래 순
    out.sort(key=lambda d: d["day"], reverse=True)
    out.sort(key=lambda d: d["place_cases"] > 0)
    counts["대상"] = len(out)
    return out, counts


def default_region(d: dict, rows: list[dict]) -> dict | None:
    """기록부 지역 글이 구(와 동)까지 정해 주면 그것, 아니면 시·군이 구 하나로 정해질 때(일반구가 없는 시·군, 광역시의 구)
    그 시·군·구. 구가 여럿인데 기록부에 구가 없으면 None."""
    if d.get("region"):
        return d["region"]
    gus = {(r["sido"], r["sigungu"]) for r in rows if r["sido"] == d["sido"] and r["sigungu"].split()[:1] == [d["city"]]}
    if len(gus) == 1:
        sido, sigungu = next(iter(gus))
        return {"sido": sido, "sigungu": sigungu, "dong": ""}
    return None


def cmd_todo(args) -> None:
    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"사진 없는 사례: 거래 기록부 폴더 없음({folder}) → 건너뜀")
        return
    out, counts = targets(folder, args.since)
    print("사진 없는 사례 대상 " + f"{counts['대상']}건 (" + " · ".join(f"{k} {v}" for k, v in counts.items() if k != "대상") + ")")
    rows = BC.load_csv_rows()
    for d in out[:args.n]:
        reg = default_region(d, rows)
        print(json.dumps({
            "id": d["id"], "문의 날짜": d["asked"] or "모름", "입고일": d["got"] or "모름", "말소일": d["closed"] or "모름",
            "기록부 지역": d["region_text"],
            "시·군·구(알면 동)": (" ".join(x for x in (reg["sido"], reg["sigungu"], reg["dong"]) if x) if reg else f"{d['sido']} {d['city']} — 구가 여럿이라 answer 의 \"지역\"에 구(알면 동)까지 적어야 함"),
            "차종": d["car"], "연식": d["year"] or "모름", "시동(기록부)": d["start"] or "모름", "고른쪽(기록부)": d["side"] or "모름",
            "그 시·군의 가까운 날짜 사례(같은 차면 skip)": d["near"] or "없음",
        }, ensure_ascii=False, indent=1))


def find_deal(folder: Path, deal_id: str) -> dict | None:
    return next((d for d in deals(folder)[0] if d["id"] == deal_id), None)  # 한 건 찾는 데는 법정동 목록을 새로 읽어도 됨


def cmd_make(args) -> int:
    folder = Path(args.dir)
    d = find_deal(folder, args.id)
    if not d:
        print(f"만들지 않음: id {args.id} 인 끝난 거래를 기록부에서 못 찾음")
        return 1
    state = load_state()
    rows = BC.load_csv_rows()
    if args.id in state["made"]:
        print(f"만들지 않음: 이미 만든 거래({state['made'][args.id].get('folder')})")
        return 1
    if hit := covered(d, known_cases(rows)):
        print(f"만들지 않음: 이미 사례가 있는 거래로 보임 — {hit}")
        return 1
    try:
        ans = json.loads(Path(args.answer).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        print(f"만들지 않음: answer 파일을 못 읽음({type(e).__name__})")
        return 1
    if not isinstance(ans, dict):
        print("만들지 않음: answer 는 {\"상황\": …, \"처리\": …, …} 모양")
        return 1
    extra = [k for k in ans if k not in ANSWER_KEYS]
    if extra:
        print(f"만들지 않음: answer 에 쓸 수 없는 칸 {extra} (쓸 수 있는 칸: {', '.join(ANSWER_KEYS)}. 차종·연식·문의일·인수일은 기록부 값만 씀)")
        return 1
    ans = {k: (" / ".join(str(x).strip() for x in v) if isinstance(v, list) else str(v).strip()) for k, v in ans.items()}
    ans = {k: v for k, v in ans.items() if v}
    missing = [k for k in NEED_KEYS if not ans.get(k)]
    if missing:
        print(f"만들지 않음: {'·'.join(missing)} 칸이 비었음(사진이 없어 본문 두 칸이 꼭 있어야 함)")
        return 1
    if not (ans.get("걱정") or ans.get("확인")):
        print("만들지 않음: 걱정·확인 칸이 둘 다 비었음 — 통화표·거래 노트에서 이 차의 사연을 확신할 때만 만든다(못 찾으면 skip)")
        return 1
    text = " ".join(ans.values())
    if m := AGE_SEX_RE.search(text):
        print(f"만들지 않음: 손님 나이·성별·호칭으로 읽히는 말 '{m.group(0)}' (걱정만 쓰고 사람 얘기는 뺌)")
        return 1
    # 지역: answer 가 주면 그것(기록부의 시·군과 같은 곳이어야 함), 아니면 기록부 시·군이 구 하나로 정해질 때만
    if ans.get("지역"):
        region, why = BC.resolve_region(ans["지역"], rows)
        if not region:
            print(f"만들지 않음: 지역 — {why}")
            return 1
        if region["sido"] != d["sido"] or region["sigungu"].split()[:1] != [d["city"]]:
            print(f"만들지 않음: answer 의 지역({region['sido']} {region['sigungu']})이 기록부의 시·군({d['sido']} {d['city']})과 다름")
            return 1
    else:
        region = default_region(d, rows)
        if not region:
            print(f"만들지 않음: {d['city']} 은 구가 여럿 — answer 의 \"지역\"에 구(알면 동)까지 적어야 함. 통화·기록부로 확인이 안 되면 skip")
            return 1
    if not BC.gu_page_exists(region):
        print(f"만들지 않음: {region['sigungu'] or region['sido']} 구 페이지가 아직 없음(사례가 붙을 곳이 없음) → skip \"구 페이지 없음\"")
        return 1
    side = ans.get("고른쪽") or d["side"]
    if side and side not in SIDES:
        print(f"만들지 않음: 고른쪽은 {'/'.join(SIDES)} 중 하나")
        return 1
    if ans.get("고른쪽") in ("폐차", "수출") and d["side"] and ans["고른쪽"] != d["side"]:
        print(f"만들지 않음: answer 의 고른쪽({ans['고른쪽']})이 기록부({d['side']})와 다름 — 이 차가 맞는지 다시 보고, 아니면 skip")
        return 1
    closed = d["closed"] or (ans.get("말소일") if L.is_day(ans.get("말소일", "")) else "")
    region_text = " ".join(x for x in (region["sido"], region["sigungu"], region["dong"]) if x)
    lines = [f"지역: {region_text}", f"차종: {d['year'] + '년식 ' if d['year'] else ''}{d['car']}", f"날짜: {d['day']}",
             f"상황: {ans['상황']}", f"처리: {ans['처리']}"]
    lines += [f"{k}: {ans[k]}" for k in ("결과", "한마디", "걱정", "확인") if ans.get(k)]
    if side:
        lines.append(f"고른쪽: {side}")
    if ans.get("이유"):
        lines.append(f"이유: {ans['이유']}")
    lines += [f"{k}: {v}" for k, v in (("문의일", d["asked"]), ("인수일", d["got"]), ("말소일", closed)) if v]
    lines += [f"{k}: {ans[k]}" for k in ("끝한줄", "제목꼬리") if ans.get(k)]
    short = (region["dong"] or (region["sigungu"].split()[-1] if region["sigungu"] else region["sido"]))
    name = re.sub(r"[^0-9A-Za-z가-힣-]", "", f"{d['day']}-{short}-{d['car'].replace(' ', '')}-{TAG}")
    out_dir = BC.INPUT_DIR / name
    if out_dir.exists() or (BC.DONE_DIR / name).exists():
        name += "-" + args.id[:4]
        out_dir = BC.INPUT_DIR / name
    out_dir.mkdir(parents=True)
    (out_dir / "메모.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    checked, why = BC.check_folder(out_dir, rows)
    if not checked:
        shutil.rmtree(out_dir)
        print(f"만들지 않음(검사에서 걸림): {why}")
        return 1
    depth = case_story.depth({"story": checked["body"]["story"], "spoken": ""})
    state["made"][args.id] = {"folder": name, "day": today().isoformat()}
    save_state(state)
    print(f"만듦: cases/input/{name}/메모.txt · {region_text} · {lines[1][4:]} · 사연 칸 {len(depth)}개({'·'.join(depth)})")
    return 0


def cmd_skip(args) -> int:
    why = re.sub(r"\s+", " ", args.why).strip()[:SKIP_WHY_MAX]
    if not why or BC.banned_text(why) or re.search(r"\d{3,}", why):
        print("적지 않음: 이유는 짧은 말로(숫자·이름·번호 없이). 예: \"통화 못 찾음\", \"확신 낮음\", \"쓸 수 없는 사정\", \"이미 사례 있음\"")
        return 1
    if not find_deal(Path(args.dir), args.id):
        print(f"적지 않음: id {args.id} 인 끝난 거래를 기록부에서 못 찾음")
        return 1
    state = load_state()
    state["skip"][args.id] = {"why": why, "day": today().isoformat()}
    save_state(state)
    print(f"건너뜀으로 적음: {args.id} — {why}")
    return 0


def cmd_status(args) -> None:
    folder = Path(args.dir)
    state = load_state()
    if folder.is_dir():
        _, counts = targets(folder, args.since)
        print("사진 없는 사례: " + " · ".join(f"{k} {v}" for k, v in counts.items()))
    else:
        print(f"사진 없는 사례: 만든 것 {len(state['made'])}건 · 건너뜀 {len(state['skip'])}건 (기록부는 이 컴퓨터에 없음)")
    for why, n in Counter(v.get("why", "") for v in state["skip"].values()).most_common():
        print(f"  건너뛴 까닭: {why} {n}건")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(WIKI_DIR), help="거래 기록부 폴더")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("todo", "status"):
        p = sub.add_parser(name)
        p.add_argument("--since", default="", help="이 날짜(YYYY-MM-DD)부터의 거래만(통화표가 시작된 날)")
        if name == "todo":
            p.add_argument("--n", type=int, default=5)
    p = sub.add_parser("make")
    p.add_argument("id")
    p.add_argument("--answer", required=True)
    p = sub.add_parser("skip")
    p.add_argument("id")
    p.add_argument("why")
    args = ap.parse_args()
    if getattr(args, "since", "") and not L.is_day(args.since):
        raise SystemExit("--since 는 YYYY-MM-DD")
    rc = {"todo": cmd_todo, "make": cmd_make, "skip": cmd_skip, "status": cmd_status}[args.cmd](args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
