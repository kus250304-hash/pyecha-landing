"""
시군구별 주민등록 인구를 받아 data/population_sigungu.json 에 저장한다. 구 페이지 줄 B(인구 30만 이하 시·군)를 고를 때만 쓴다.

사용법
  python3 scripts/population_stats.py fetch            # 지난달 기준으로 받기
  python3 scripts/population_stats.py fetch 2026 08    # 기준 연월 지정
  python3 scripts/population_stats.py show             # 지금 파일과 30만 이하 시·군 수

출처: 행정안전부 주민등록 인구통계 「행정동별 주민등록 인구 및 세대현황」(https://jumin.mois.go.kr/statMonth.do).
총인구수(거주자·거주불명자·재외국민 포함, 외국인 제외). 사이트가 가끔 응답하지 않으므로 시도마다 몇 번 다시 시도한다.
숫자는 순서를 정하는 데만 쓰고 페이지 글에는 쓰지 않는다. 숫자를 지어내거나 손으로 고치지 않는다.
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "population_sigungu.json"
URL = "https://jumin.mois.go.kr/statMonth.do"
SIDO_CODES = {
    "서울특별시": "1100000000", "전남광주통합특별시": "1200000000", "부산광역시": "2600000000", "대구광역시": "2700000000",
    "인천광역시": "2800000000", "대전광역시": "3000000000", "울산광역시": "3100000000", "세종특별자치시": "3600000000",
    "경기도": "4100000000", "강원특별자치도": "5100000000", "충청북도": "4300000000", "충청남도": "4400000000",
    "전북특별자치도": "5200000000", "경상북도": "4700000000", "경상남도": "4800000000", "제주특별자치도": "5000000000",
}


def fetch_sido(code: str, y: str, m: str, tries: int = 6) -> list[tuple[str, int]]:
    body = urllib.parse.urlencode({
        "sltOrgType": "2", "sltOrgLvl1": code, "sltOrgLvl2": "A", "gender": "gender", "genderPer": "genderPer",
        "generation": "generation", "sltUndefType": "", "searchYearStart": y, "searchMonthStart": m,
        "searchYearEnd": y, "searchMonthEnd": m, "sltOrderType": "1", "sltOrderValue": "ASC",
        "category": "month", "searchYearMonth": "month", "nowYear": y,
    }).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(URL, data=body, headers={"User-Agent": "Mozilla/5.0", "Referer": URL})
            text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
            rows = []
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S):
                cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
                if len(cells) >= 3 and cells[0].isdigit() and re.fullmatch(r"[\d,]+", cells[2]):
                    rows.append((cells[1], int(cells[2].replace(",", ""))))
            if rows:
                return rows
            last = "표가 비어 있음"
        except Exception as e:  # 사이트가 자주 502·시간 초과를 낸다
            last = str(e)
        time.sleep(5 * (i + 1))
    raise SystemExit(f"{code}: 받지 못함 ({last}). 몇 분 뒤 다시 실행하세요")


def cmd_fetch(args: list[str]) -> None:
    if len(args) == 2:
        y, m = args[0], args[1].zfill(2)
    else:
        t = date.today().replace(day=1)
        prev = date(t.year - (t.month == 1), 12 if t.month == 1 else t.month - 1, 1)
        y, m = str(prev.year), f"{prev.month:02d}"
    out = []
    for sido, code in SIDO_CODES.items():
        for name, pop in fetch_sido(code, y, m):
            if name == sido and sido != "세종특별자치시":
                continue  # 시도 합계 줄
            sigungu = "" if name == sido else name
            if not any(r["sido"] == sido and r["sigungu"] == sigungu for r in out):
                out.append({"sido": sido, "sigungu": sigungu, "population": pop})
        print(f"{sido}: 받음")
    OUT.write_text(json.dumps({
        "basis": "주민등록 총인구(외국인 제외)", "as_of": f"{y}년 {int(m)}월",
        "source": "행정안전부 주민등록 인구통계 「행정동별 주민등록 인구 및 세대현황」(jumin.mois.go.kr/statMonth.do)",
        "fetched_on": date.today().isoformat(), "rows": out,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"저장: {OUT.relative_to(ROOT)} ({len(out)}줄, {y}년 {int(m)}월)")


def load() -> tuple[dict[tuple[str, str], int], dict]:
    """({(시도, 시군구): 인구}, 메타). 파일이 없으면 ({}, {})."""
    if not OUT.exists():
        return {}, {}
    data = json.loads(OUT.read_text(encoding="utf-8"))
    return {(r["sido"], r["sigungu"]): r["population"] for r in data["rows"]}, {k: v for k, v in data.items() if k != "rows"}


def city_population(pops: dict[tuple[str, str], int], sido: str, sigungu: str) -> int | None:
    """그 시·군 전체 인구. '천안시 동남구' 는 '천안시' 전체, 세종은 시 전체. 광역시의 자치구는 구 인구."""
    first = sigungu.split()[0] if sigungu else ""
    return pops.get((sido, first)) if first else pops.get((sido, ""))


def is_small_si_gun(pops: dict[tuple[str, str], int], sido: str, sigungu: str, limit: int) -> bool:
    """줄 B 대상: 시·군(광역시 자치구 제외)이고 그 시·군 전체 인구가 limit 이하."""
    first = sigungu.split()[0] if sigungu else ""
    if not first or not first.endswith(("시", "군")):
        return sido == "세종특별자치시" and (pops.get((sido, "")) or limit + 1) <= limit
    n = city_population(pops, sido, sigungu)
    return n is not None and n <= limit


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "fetch":
        cmd_fetch(sys.argv[2:])
    else:
        pops, meta = load()
        if not pops:
            print("인구 통계 없음 → python3 scripts/population_stats.py fetch")
            return
        small = sorted({(s, g.split()[0]) for (s, g) in pops if g and g.split()[0].endswith(("시", "군")) and is_small_si_gun(pops, s, g, 300000)})
        print(f"기준: {meta.get('as_of')} {meta.get('source')} / 30만 이하 시·군 {len(small)}곳")


if __name__ == "__main__":
    main()
