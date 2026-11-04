"""
폼 문의 세기(2026-11-04 병한님 요청). 날짜·페이지·유입별로 센다.

출처는 둘이다.
- 폼 문의 기록 시트(2026-11-04, site_config 의 form_log_url, docs/form-log-setup.md): 폼을 보낼 때마다 날짜·시간·페이지 주소·src·지역
  한 줄. 가장 정확하고 바로 바뀐다. 시트 첫 줄이 생긴 다음 날부터는 이 숫자만 쓴다.
- 그 전 날짜는 거래 기록부에서 "폼"으로 들어온 거래만 골라 센다(아래).

시트 전에 폼 문의가 남던 곳은 넷인데 자동으로 읽을 수 있는 곳은 거래 기록부 하나뿐이었다.
- Web3Forms → 네이버 메일([견적문의] 메일, Page·Source 칸이 있어 가장 정확): 저장소·루틴에서 읽을 수 없음
- Web3Forms 대시보드: 로봇 확인 화면이 있어 자동으로 못 들어감
- 폼 → 캘린더 [견적 전화] 일정(2026-10-28부터): 처리하면 지우므로 다 남지 않음
- 병한-업무위키 거래 기록부: 운영자 PC 에만 있음 → PC 예약 작업 "폐차 사례 가져오기" 2-1 이 --write 로 data/form_inquiries.json 을 올림

그래서 기록부 날짜의 숫자는 "병한님이 기록부에 적은 폼 문의"이고, 전화·문자로 온 문의와 기록부에 안 적힌 폼은 빠진다.
기록부는 "캘린더→기록부" 작업(매일 오후 1시 20분)이 채우므로 마감된 날은 PC 작업이 돈 날의 전날까지다.

사용법
  python scripts/form_inquiries.py [--since 2026-10-14]   # 기록부 + 시트를 세어 표로 보여 줌(PC)
  python scripts/form_inquiries.py --write                # data/form_inquiries.json 저장(PC 2-1)
  python3 scripts/form_inquiries.py report [--today YYYY-MM-DD]   # 보고 칸(시트를 바로 읽고, 못 읽으면 저장된 json. 아침 보고·PC 보고)

규칙
- 폼 문의: 기록부 글에 "폼"(플랫폼 빼고)이 있는 거래. 유입경로가 유튜브여도 홈페이지 폼으로 왔으면 센다.
  유입경로가 "랜딩"인데 "폼"이 없는 거래는 폼인지 전화인지 몰라 따로 센다(landing_unknown).
- 문의 날짜: "폼" 옆에 적힌 월/일(예: "폼(10/15 밤 접수)", "11/3 12:46 폼")이 기록 날짜보다 이르면 그 날, 아니면 기록 날짜.
- 페이지: 지역 → 그 시·군의 구 페이지(inquiry_log.find_gu 와 같은 규칙). 실제로 어느 페이지에서 보냈는지는 기록부에 없다.
- 유입: 유입경로 유튜브 → 유튜브, 폼·유입·검색 줄에 "네이버" → 네이버 검색, 그 밖 → 기록 없음.
- 시트 줄: 페이지 주소 → 이름(구 페이지 "강릉시 구 페이지", 동 페이지 "강릉시 교동 동 페이지", 첫 화면 홈, 시·도·안내 페이지),
  유입 = "src=yt" 처럼 src 그대로(없으면 "src 없음").
  어디서(2026-11-04, 시트 F칸 ref) = 처음 들어온 곳의 앞 낱말(네이버·구글·유튜브·다음·카카오·인스타그램·직접·기타).
  ref 가 "직접"인데 src=yt 면 유튜브 설명란 링크로 온 것이라 유튜브로 센다(유튜브 앱은 referrer 를 안 남기는 일이 많음).
  보고의 "어디서:" 줄은 시트 줄만 센다(기록부 줄에는 이 칸이 없음).
- 이 지역 강화 후보: 최근 7일 같은 페이지(첫 화면 홈 빼고)에서 2건 이상.
- 전화·차번호·이름·금액은 읽어도 어디에도 쓰지 않는다. json·보고에는 날짜·페이지 이름·종류·유입만(시트에도 없음).
"""
import argparse
import json
import re
import sys
import urllib.request
from urllib.parse import unquote
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "form_inquiries.json"
KST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))
WEEK = "월화수목금토일"
FORM_RE = re.compile(r"(?<!플랫)폼")
MD_NEAR_FORM = [re.compile(r"폼[^\n]{0,15}?\b(\d{1,2})/(\d{1,2})\b"), re.compile(r"\b(\d{1,2})/(\d{1,2})\b[^\n/]{0,12}폼")]
VIA_LINE_RE = re.compile(r"폼|유입|검색|랜딩")
CAPITAL = {"서울특별시", "경기도", "인천광역시"}
LEDGER_TYPE = "기록부(페이지 모름)"
REF_MAIN = ["네이버", "구글", "유튜브", "직접"]
REF_WORDS = REF_MAIN + ["다음", "카카오", "인스타그램"]


def kind_of(sido: str, gu: str) -> str:
    if sido in CAPITAL:
        return "수도권"
    if not re.search(r"[시군]( |$)", gu):  # 수영구·광산구처럼 시·군 없는 자치구
        return "광역시 구"
    return "지방 시·군"


def inquiry_date(text: str, recorded: str) -> str:
    rec = date.fromisoformat(recorded)
    best = rec
    for rx in MD_NEAR_FORM:
        for m in rx.finditer(text):
            try:
                d = date(rec.year, int(m.group(1)), int(m.group(2)))
            except ValueError:
                continue
            if d > rec:  # 12월 기록에 1월 날짜 같은 해 넘김은 지난해로
                d = d.replace(year=rec.year - 1)
            if rec - d <= timedelta(days=30) and d < best:
                best = d
    return best.isoformat()


def via_of(text: str, route: str) -> str:
    if route == "유튜브":
        return "유튜브"
    if any("네이버" in line for line in text.splitlines() if VIA_LINE_RE.search(line)):
        return "네이버 검색"
    return "기록 없음"


def collect(folder: Path) -> tuple[list[dict], dict[str, int]]:
    from build_site import GU_DATA, gu_file, load_json  # noqa: E402
    from inquiry_log import field, find_gu  # noqa: E402

    gu_data = load_json(GU_DATA, default=[])
    gus = [(g["sido"], g["sigungu"]) for g in gu_data if g.get("sigungu") and (ROOT / "gu" / gu_file(g["sido"], g["sigungu"])).exists()]
    rows, unknown = [], Counter()
    for f in sorted(folder.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        recorded, route = field(text, "날짜"), field(text, "유입경로")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", recorded):
            continue
        if not FORM_RE.search(text):
            if "랜딩" in route:
                unknown[recorded] += 1
            continue
        region = field(text, "지역")
        place = find_gu(region, gus) if region and "확인" not in region else None
        if place:
            name = gu_file(*place)
            page, label, kind = name, name.removesuffix("-폐차장.html").replace("-", " "), kind_of(*place)
        else:
            page, label, kind = "", "지역 미상", "지역 미상"
        rows.append({"date": inquiry_date(text, recorded), "page": page, "label": label, "kind": kind, "via": via_of(text, route),
                     "type": LEDGER_TYPE, "from": "ledger"})

    # docs/index-requests.md "문의가 온 페이지" 칸에 손으로 "폼"이라 적은 줄(기록부에는 폼 표시가 없는 거래)
    from build_site import CONFIG, REGIONS  # noqa: E402
    from inquiry_log import LINE_DATE_RE, OURS_RE, SECTION  # noqa: E402
    from pick_index_requests import LOG, inquiry_places  # noqa: E402
    base, regions = load_json(CONFIG)["site_base_url"].rstrip("/"), load_json(REGIONS)
    text = LOG.read_text(encoding="utf-8")
    start = text.index(f"\n## {SECTION}") + 1
    end = text.find("\n## ", start)
    for line in text[start:end if end > 0 else None].splitlines():
        m = LINE_DATE_RE.match(line)
        if not m or OURS_RE.match(line) or not FORM_RE.search(line.split(" — ")[0]):
            continue
        places = inquiry_places(line, base, regions, gu_data)
        if not places:
            continue
        name = gu_file(*places[0])
        label = name.removesuffix("-폐차장.html").replace("-", " ")
        if any(r["date"] == m.group(1) and r["label"] == label for r in rows):
            continue
        if unknown.get(m.group(1)):
            unknown[m.group(1)] -= 1  # 같은 거래가 기록부에 "랜딩"으로만 있던 것
        rows.append({"date": m.group(1), "page": name, "label": label, "kind": kind_of(*places[0]),
                     "via": "네이버 검색" if "네이버" in line else "기록 없음", "type": LEDGER_TYPE, "from": "ledger"})
    unknown = +unknown
    rows.sort(key=lambda r: (r["date"], r["label"]))
    return rows, dict(sorted(unknown.items()))


def fetch_sheet() -> list[dict] | None:
    """폼 문의 기록 시트의 줄. 주소가 없거나 못 읽으면 None(그때는 저장된 json·기록부만 쓴다)."""
    from build_site import CONFIG, load_json  # noqa: E402
    url = (load_json(CONFIG).get("form_log_url") or "").strip()
    if not url:
        return None
    try:
        with urllib.request.urlopen(url + "?key=pyecha119", timeout=30) as res:
            raw = json.loads(res.read().decode("utf-8"))["rows"]
    except Exception as e:  # 네트워크·권한·형식 — 숫자를 지어내지 않고 json 으로 넘어감
        print(f"(폼 문의 시트 못 읽음: {type(e).__name__} → 저장된 기록 사용)")
        return None
    return [sheet_row(r) for r in raw if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("date", "")))]


def sheet_row(r: dict) -> dict:
    from build_site import GU_DATA, REGIONS, gu_file, load_json  # noqa: E402
    path = unquote(str(r.get("page") or "").split("?")[0]).lstrip("/")
    folder, _, name = path.rpartition("/")
    stem = name.removesuffix(".html")
    label, typ, kind = path, "기타", "-"
    if not path or path == "index.html":
        label, typ = "첫 화면 홈", "첫 화면 홈"
    elif folder == "gu":
        label, typ = stem.removesuffix("-폐차장").replace("-", " ") + " 구 페이지", "구 페이지"
        g = next((g for g in load_json(GU_DATA, default=[]) if gu_file(g["sido"], g.get("sigungu", "")) == name), None)
        kind = kind_of(g["sido"], g.get("sigungu", "")) if g else "-"
    elif folder == "pages":
        x = next((x for x in load_json(REGIONS, default=[]) if x.get("slug") == stem), None)
        label = f"{x['sigungu']} {x['dong']} 동 페이지".strip() if x else stem + " 동 페이지"
        typ, kind = "동 페이지", kind_of(x["sido"], x["sigungu"]) if x else "-"
    elif folder == "si":
        label, typ = stem.removesuffix("-폐차장") + " 시·도 페이지", "시·도 페이지"
    elif folder == "guide":
        label, typ = "안내: " + stem.replace("-", " "), "안내 페이지"
    elif folder == "cases":
        label, typ = "사례 페이지", "사례 페이지"
    src = str(r.get("src") or "").strip()
    ref = str(r.get("ref") or "").strip()
    ref = ref if ref in REF_WORDS else ("기타" if ref else "")
    if ref == "직접" and src == "yt":
        ref = "유튜브"
    return {"date": r["date"], "time": str(r.get("time") or ""), "page": path, "label": label, "kind": kind,
            "via": f"src={src}" if src else "src 없음", "ref": ref, "type": typ, "from": "sheet"}


def ref_line(rows: list[dict]) -> str:
    """'네이버 n · 구글 n · 유튜브 n · 직접 n'(+ 그 밖은 있을 때만). 시트 줄 중 ref 가 있는 것만, 없으면 빈 글."""
    c = Counter(r["ref"] for r in rows if r.get("ref"))
    if not c:
        return ""
    return " · ".join(f"{k} {c.get(k, 0)}" for k in REF_MAIN) + "".join(f" · {k} {c[k]}" for k in REF_WORDS[4:] + ["기타"] if c.get(k))


def merge(old_rows: list[dict], sheet: list[dict] | None) -> list[dict]:
    """시트 첫 날까지는 기록부, 그다음 날부터는 시트(첫 날은 시트를 단 시각 전 문의가 빠져 있을 수 있어 기록부).
    sheet 가 None 이면 old_rows(저장된 json) 그대로."""
    def key(r):
        return (r["date"], r.get("time", ""), r["label"])
    if not sheet:
        return sorted(old_rows, key=key)
    first = min(r["date"] for r in sheet)
    ledger = [r for r in old_rows if r.get("from", "ledger") == "ledger" and r["date"] <= first]
    return sorted(ledger + [r for r in sheet if r["date"] > first], key=key)


def day_name(d: str) -> str:
    x = date.fromisoformat(d)
    return f"{x.month}/{x.day}({WEEK[x.weekday()]})"


def show(rows: list[dict], unknown: dict[str, int], since: str) -> None:
    rows = [r for r in rows if r["date"] >= since]
    by_day = defaultdict(list)
    for r in rows:
        by_day[r["date"]].append(r)
    start, end = date.fromisoformat(since), datetime.now(KST).date()
    print(f"폼 문의(폼만 셈, 전화·문자 문의 빠짐) {since} ~ {end.isoformat()}: {len(rows)}건")
    print("| 날짜 | 건수 | 문의가 온 지역·페이지 | 유입 |")
    print("|---|---|---|---|")
    d = start
    while d <= end:
        rs = by_day.get(d.isoformat(), [])
        pages = ", ".join(r["label"] for r in rs) or "-"
        vias = ", ".join(f"{v} {n}" for v, n in Counter(r["via"] for r in rs).most_common()) or "-"
        print(f"| {day_name(d.isoformat())} | {len(rs)} | {pages} | {vias} |")
        d += timedelta(days=1)
    weeks = Counter((date.fromisoformat(r["date"]) - start).days // 7 for r in rows)
    print("주별: " + " / ".join(f"{i + 1}주차 {weeks.get(i, 0)}건" for i in range((end - start).days // 7 + 1)))
    print("종류별: " + ", ".join(f"{k} {n}" for k, n in Counter(r["kind"] for r in rows).most_common()))
    print("페이지 종류별: " + ", ".join(f"{k} {n}" for k, n in Counter(r.get("type", LEDGER_TYPE) for r in rows).most_common()))
    print("유입별: " + ", ".join(f"{k} {n}" for k, n in Counter(r["via"] for r in rows).most_common()))
    if ref_line(rows):
        print("어디서(시트 줄만): " + ref_line(rows))
    multi = [k for k, n in Counter(r["label"] for r in rows if r["page"]).items() if n >= 2]
    print("2건 이상 지역: " + (", ".join(multi) or "없음"))
    unk = sum(n for k, n in unknown.items() if k >= since)
    print(f"(참고) 유입경로 랜딩인데 폼인지 전화인지 기록 없는 거래 {unk}건 — 위 숫자에 안 넣음")


def report(today: date) -> None:
    """보고 칸. 시트를 바로 읽으면 어제, 못 읽으면 저장된 json 의 마감된 날(PC 작업이 돈 날의 전날) 기준으로 센다."""
    if not OUT.exists():
        print("폼 문의: 기록 없음(data/form_inquiries.json 없음 — PC 앱 '폐차 사례 가져오기' 2-1 확인)")
        return
    data = json.loads(OUT.read_text(encoding="utf-8"))
    updated = datetime.fromisoformat(data["updated"]).astimezone(KST)
    sheet = fetch_sheet()
    if sheet:
        rows, closed, basis = merge(data["rows"], sheet), today - timedelta(days=1), "시트 지금 읽음"
    else:
        if (today - updated.date()).days > 2:
            print(f"폼 문의: 기록이 오래됨(마지막 {updated:%m/%d %H:%M} — PC 앱 '폐차 사례 가져오기' 2-1 확인)")
            return
        rows, basis = data["rows"], f"PC 기록 {updated:%m/%d %H:%M}"
        closed = min(updated.date() - timedelta(days=1), today - timedelta(days=1))
    if not any(r.get("from") == "sheet" and r["date"] == closed.isoformat() for r in rows):
        basis = "거래 기록부 기준, " + basis
    count = Counter(r["date"] for r in rows)
    day_rows = [r for r in rows if r["date"] == closed.isoformat()]
    week_rows = [r for r in rows if closed - timedelta(days=6) <= date.fromisoformat(r["date"]) <= closed]
    prev_week = sum(count.get((closed - timedelta(days=7 + i)).isoformat(), 0) for i in range(7))
    same_day = count.get((closed - timedelta(days=7)).isoformat(), 0)
    week_pages = Counter(r["label"] for r in week_rows if r["page"] and r["label"] != "첫 화면 홈")
    strong = sorted(k for k, n in week_pages.items() if n >= 2)

    def item(label: str, n: int) -> str:
        return f"{label} {n}건" + (" ← 이 지역 강화 후보" if label in strong else "")

    print(f"폼 문의 {day_name(closed.isoformat())} {len(day_rows)}건 (폼만 셈, 전화·문자 빠짐, {basis})")
    if day_rows:
        print("  - " + ", ".join(item(k, n) for k, n in Counter(r["label"] for r in day_rows).most_common()))
        print("  - 유입: " + ", ".join(f"{k} {n}" for k, n in Counter(r["via"] for r in day_rows).most_common()))
        refs = ref_line(day_rows)
        if refs:
            print("  - 어디서: " + refs)
    diff = len(day_rows) - same_day
    print(f"  - 최근 7일({day_name((closed - timedelta(days=6)).isoformat())}~{day_name(closed.isoformat())}) {len(week_rows)}건"
          f" (그 전 7일 {prev_week}건) · 지난주 같은 요일 {same_day}건 → {'+' if diff > 0 else ''}{diff}")
    if strong:
        print("  - 이 지역 강화 후보(최근 7일 2건 이상): " + ", ".join(f"{k} {week_pages[k]}건" for k in strong))
    later = sorted((d, n) for d, n in count.items() if d > closed.isoformat())
    if later:
        print("  - 아직 마감 전: " + ", ".join(f"{day_name(d)} {n}건" for d, n in later))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="show", choices=["show", "report"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--since", default="2026-10-14")
    ap.add_argument("--today", help="report 기준일(YYYY-MM-DD, 기본 오늘 한국 시간)")
    ap.add_argument("--dir", help="거래 기록부 폴더")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.cmd == "report":
        report(date.fromisoformat(args.today) if args.today else datetime.now(KST).date())
        return
    from inquiry_log import WIKI_DIR  # noqa: E402
    folder = Path(args.dir) if args.dir else WIKI_DIR
    if not folder.is_dir():
        print(f"폼 문의: 거래 기록부 폴더 없음({folder}) → 건너뜀")
        return
    rows, unknown = collect(folder)
    rows = merge(rows, fetch_sheet())
    show(rows, unknown, args.since)
    if args.write:
        data = {"updated": datetime.now(KST).isoformat(timespec="minutes"),
                "source": "폼 문의 기록 시트 + 그 전 날짜는 병한-업무위키 거래 기록부(폼으로 온 거래만), scripts/form_inquiries.py",
                "rows": rows, "landing_unknown": unknown}
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"저장: {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
