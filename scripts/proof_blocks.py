"""
구 페이지(그리고 반응 온 동 페이지)의 "최근 ○○에서 진행한 차"·"손님 후기" 칸(2026-11-05 병한님, 상자 B-1 1·2·7번).

재료(모두 PC 예약 작업이 만들어 올림, 손으로 고치지 않음)
  data/recent_cars.json  scripts/recent_cars.py — 거래 기록부의 입고·말소 완료 거래, 시·군마다 최근 5건
  data/reviews.json      scripts/reviews.py     — 폐차_인박스 후기 캡처에서 뽑은 글자(이름은 "○○님")
  data/dong_boost.json   이 파일의 `boost` 명령 — data/ga4_daily.json 최근 30일 quote_submit·call_click 1 이상인 동 페이지

규칙
  - 시·군 단위(일반구는 시 하나). 기록 0건이면 칸을 그리지 않는다(빈 문자열).
  - 동 페이지에는 넣지 않는다. 예외: data/dong_boost.json 에 있는 동 페이지만 그 시·군의 두 칸을 보인다.
  - 금액·전화·차번호·결과 약속이 섞인 글은 빌드에서 버린다(build_cases.banned_text). 후기는 최신 3개까지.

사용법
  python scripts/proof_blocks.py boost        # data/dong_boost.json 다시 쓰기(ga4_daily.py --push 도 부름)
  python scripts/proof_blocks.py show         # 칸이 보일 구·동 페이지 수
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

RECENT = ROOT / "data" / "recent_cars.json"
REVIEWS = ROOT / "data" / "reviews.json"
BOOST = ROOT / "data" / "dong_boost.json"
GA4 = ROOT / "data" / "ga4_daily.json"
MAX_REVIEWS = 3
BOOST_DAYS = 30
SIDES = {"폐차", "수출"}
STARTS = {"가능": "시동 가능", "불가": "시동 불가"}
NAME_RE = re.compile(r"[가-힣]\*{1,2}[가-힣]?")  # 가린 이름 "김*수" → ○○님(실명은 reviews.py 가 받을 때 막음)


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def city_key(sido: str, sigungu: str) -> tuple[str, str]:
    return sido, (sigungu.split()[0] if sigungu else "")


def _bad(text: str) -> bool:
    from build_cases import banned_text
    return bool(banned_text(text))


@lru_cache(maxsize=1)
def recent_map() -> dict[tuple[str, str], list[dict]]:
    out = {}
    for p in _load(RECENT, {}).get("places", []):
        cars = [c for c in p.get("cars", []) if c.get("car") and re.fullmatch(r"\d{4}-\d{2}", c.get("month", ""))
                and not _bad(c["car"])]
        if cars:
            out[(p["sido"], p["city"])] = cars
    return out


@lru_cache(maxsize=1)
def review_map() -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = {}
    for r in _load(REVIEWS, {}).get("reviews", []):
        text = (r.get("text") or "").strip()
        if not text or len(text) > 200 or _bad(text) or re.search(r"\d{3,}", text):
            continue
        if r.get("car") and _bad(r["car"]):
            continue
        out.setdefault((r["sido"], r["city"]), []).append(r)
    for k in out:
        out[k].sort(key=lambda r: (r.get("month", ""), r.get("added", "")), reverse=True)
    return out


@lru_cache(maxsize=1)
def boost_slugs() -> frozenset:
    return frozenset(p["slug"] for p in _load(BOOST, {}).get("pages", []))


def _month(m: str) -> str:
    y, mo = m.split("-")
    return f"{int(mo)}월" if y == str(date.today().year) else f"{y}년 {int(mo)}월"


def _esc(s: str) -> str:
    from build_site import esc
    return esc(s)


def car_line(c: dict) -> str:
    """"11월 · 2006년식 아반떼XD · 시동 가능 · 폐차"."""
    parts = [_month(c["month"]), (f"{c['year']}년식 " if c.get("year") else "") + c["car"]]
    if STARTS.get(c.get("start", "")):
        parts.append(STARTS[c["start"]])
    if c.get("side") in SIDES:
        parts.append(c["side"])
    return " · ".join(parts)


H3 = 'style="margin:22px 0 6px;font-size:17px"'
UL = 'style="list-style:none;margin:0;padding:0"'
LI = 'style="padding:10px 0;border-bottom:1px solid var(--line)"'


def recent_html(sido: str, sigungu: str) -> str:
    key = city_key(sido, sigungu)
    cars = recent_map().get(key)
    if not cars:
        return ""
    from build_site import SIDO_SHORT
    place = key[1] or SIDO_SHORT[sido]
    return (f'<div id="recent-cars"><h3 {H3}>최근 {_esc(place)}에서 진행한 차</h3><ul {UL}>'
            + "".join(f"<li {LI}>{_esc(car_line(c))}</li>" for c in cars)
            + '</ul><p class="note" style="font-size:13px;color:#5E6E70">거래 기록에서 옮겼습니다. 금액·차 번호·손님 정보는 적지 않습니다.</p></div>')


def reviews_html(sido: str, sigungu: str) -> str:
    key = city_key(sido, sigungu)
    revs = review_map().get(key, [])[:MAX_REVIEWS]
    if not revs:
        return ""
    from build_site import SIDO_SHORT
    place = key[1] or SIDO_SHORT[sido]
    items = []
    for r in revs:
        who = " · ".join(x for x in ("○○님", place, r.get("car", ""), _month(r["month"]) if r.get("month") else "") if x)
        text = NAME_RE.sub("○○님", r["text"].strip())
        items.append(f'<li {LI}>“{_esc(text)}”<span style="display:block;font-size:13px;color:#5E6E70">{_esc(who)}</span></li>')
    return (f'<div id="reviews"><h3 {H3}>손님 후기</h3><ul {UL}>' + "".join(items)
            + '</ul><p class="note" style="font-size:13px;color:#5E6E70">손님이 보내 주신 문자를 이름·번호를 빼고 옮겼습니다.</p></div>')


def gu_html(sido: str, sigungu: str) -> str:
    return recent_html(sido, sigungu) + reviews_html(sido, sigungu)


def dong_html(r: dict) -> str:
    return gu_html(r["sido"], r["sigungu"]) if r["slug"] in boost_slugs() else ""


def compute_boost() -> list[dict]:
    """data/ga4_daily.json 최근 30일 pages 에서 quote_submit 또는 call_click 이 1 이상인 /pages/ 동 페이지."""
    days = _load(GA4, {}).get("days", {})
    if not days:
        return []
    last = max(days)
    since = (date.fromisoformat(last) - timedelta(days=BOOST_DAYS - 1)).isoformat()
    hits: dict[str, dict] = {}
    for d, v in days.items():
        if d < since:
            continue
        for p in v.get("pages", []):
            page = p.get("page", "")
            m = re.fullmatch(r"/pages/([a-z0-9\-]+)\.html", page)
            if m and (p.get("quote_submit", 0) or p.get("call_click", 0)):
                h = hits.setdefault(m.group(1), {"slug": m.group(1), "quote_submit": 0, "call_click": 0, "last": ""})
                h["quote_submit"] += p.get("quote_submit", 0)
                h["call_click"] += p.get("call_click", 0)
                h["last"] = max(h["last"], d)
    return sorted(hits.values(), key=lambda h: (-(h["quote_submit"] + h["call_click"]), h["slug"]))


def write_boost() -> bool:
    pages = [p for p in compute_boost() if (ROOT / "pages" / f"{p['slug']}.html").exists()]
    old = _load(BOOST, {})
    if old.get("pages") == pages:
        return False
    BOOST.write_text(json.dumps({"rule": f"data/ga4_daily.json 최근 {BOOST_DAYS}일 quote_submit 또는 call_click 1 이상인 동 페이지"
                                         "(scripts/proof_blocks.py boost)", "pages": pages}, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["boost", "show"])
    args = ap.parse_args()
    if args.cmd == "boost":
        changed = write_boost()
        print(f"반응 온 동 페이지 {len(_load(BOOST, {}).get('pages', []))}곳 — data/dong_boost.json " + ("다시 씀" if changed else "그대로"))
        return
    from build_site import GU_DATA, REGIONS, load_json
    gus = load_json(GU_DATA, default=[])
    print(f"최근 진행한 차 칸이 보일 구 페이지 {sum(1 for g in gus if recent_html(g['sido'], g['sigungu']))}곳, "
          f"후기 칸 {sum(1 for g in gus if reviews_html(g['sido'], g['sigungu']))}곳")
    regs = {r["slug"]: r for r in load_json(REGIONS)}
    for s in sorted(boost_slugs()):
        r = regs.get(s)
        print(f"  반응 온 동 {s}: " + ("칸 보임" if r and dong_html(r) else "그 시·군 기록 없음(칸 없음)"))


if __name__ == "__main__":
    main()
