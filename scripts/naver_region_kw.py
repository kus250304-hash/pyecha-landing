"""
전국 시·군·구 폐차 키워드 점수표(2026-10-15). 네이버 검색광고 API 키워드도구(/keywordstool, RelKwdStat)로 지역마다
키워드 변형을 조회하고 점수를 매긴다.

사용법
  python scripts/naver_region_kw.py --date 2026-10-15                    # API 조회 → CSV·점수표
  python scripts/naver_region_kw.py --date 2026-10-15 --offline          # API 없이 저장된 CSV 로 다시 계산
  python scripts/naver_region_kw.py --date 2026-10-15 --offline --write-priority   # + data/priority_regions.json 을 이 순위로
  → data/keywords/region_kw_<날짜>.csv(원본 조회 결과), docs/region-priority-<날짜>.md(점수표)

키는 저장소 밖 C:\\Users\\AOMG\\naver_searchad.env(NAVER_SEARCHAD_CUSTOMER_ID·SECRET_KEY·ACCESS_LICENSE)에서 읽고 출력하지 않는다.

대상: data/regions.json·gu.json 에 있는 시·군·구 전체(일반구 포함).
변형 4개: "{시군구}폐차", "{시군구}폐차장", 시/군/구 글자를 뺀 "{이름}폐차", "{이름}폐차장"(강릉시 → 강릉).
  - 여러 시·도에 같은 이름이 있는 구(중구·동구·고성군 …)는 시·도 이름을 앞에 붙인다(부산중구폐차). 광주 자치구는 "광주".
    앞을 붙이지 않은 "중구폐차"는 어느 지역 검색인지 갈리지 않아 넣지 않는다.
  - 일반구(수원시 영통구)는 구 이름 변형(영통구폐차·영통폐차)에 더해, 시 이름 변형(수원시폐차·수원시폐차장·수원폐차·수원폐차장)을
    시마다 한 번 조회해 그 시의 일반구 개수(legal_dong_list.csv)로 나눠 각 구에 더한다(2026-10-15 병한님 결정).
    이름이 두 글자거나 다른 곳과 겹치는 일반구(포항시 남구)는 시 이름을 붙인다(포항남구폐차).
  - 이름이 두 글자(중구)라 글자를 빼면 한 글자만 남는 곳은 뺀 변형을 만들지 않는다.
연관 키워드: 같은 조회에서 돌아온 키워드 가운데 그 지역 이름(변형의 앞부분)으로 시작하고 "폐차"가 들어간 것
  (강릉폐차비용·강릉시폐차견적·○○폐차보상금 …)을 같은 지역 줄에 더한다.
점수 = (변형+연관 키워드 월간 검색량 합, "< 10" 은 5) × 경쟁 계수(낮음 1.0 / 중간 0.6 / 높음 0.3)
       × 지방 계수(서울·경기·인천 0.5, 광역시 0.8, 그 외 1.0) ÷ (1 + 월평균 노출 광고수)
       × 하한 계수(검색량 합 100 미만은 0.5, 2026-10-15 병한님 결정)
  - 경쟁정도·광고수는 "< 10" 이 아닌 키워드 가운데 검색량이 가장 많은 것의 값.
  - PC·모바일이 모두 "< 10"(또는 결과 없음)인 키워드만 있는 지역은 순위에서 빼고 맨 아래 "검색량 없음" 묶음에
    노후차 추정 대수(vehicle_stats) 순으로 둔다.
--write-priority: data/priority_regions.json 의 gu 목록을 이 순서(순위 → 검색량 없음 → 예전 목록에만 있던 곳)로 바꾼다.
  동 이름으로 검색된 동(dongs)과 시·도 키워드(sido_keywords)는 예전 목록에서 그대로 가져온다.
API 호출은 1초에 1번 이하, 실패하면 3번까지 다시 한다.
"""
import argparse
import base64
import csv
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import SIDO_SHORT, shared_sigungu_names  # noqa: E402
from pick_next_regions import GWANGJU_GU  # noqa: E402
import vehicle_stats  # noqa: E402

ENV = Path(r"C:\Users\AOMG\naver_searchad.env")
API = "https://api.searchad.naver.com"
PRIORITY = ROOT / "data" / "priority_regions.json"
COMP = {"낮음": 1.0, "중간": 0.6, "높음": 0.3}
METRO = {"부산광역시", "대구광역시", "대전광역시", "울산광역시"}
CAPITAL = {"서울특별시", "경기도", "인천광역시"}
FLOOR_VOL, FLOOR_COEF = 100, 0.5
FIELDS = ("monthlyPcQcCnt", "monthlyMobileQcCnt")


def load_env() -> dict:
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


_last = [0.0]


def call(env: dict, hints: list[str]) -> list[dict] | None:
    """키워드도구 한 번(힌트 5개까지). 1초에 1번 이하, 실패하면 3번까지."""
    uri = "/keywordstool"
    q = urllib.parse.urlencode({"hintKeywords": ",".join(hints), "showDetail": "1"})
    for attempt in range(1, 4):
        wait = 1.05 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        ts = str(int(time.time() * 1000))
        sig = base64.b64encode(hmac.new(env["NAVER_SEARCHAD_SECRET_KEY"].encode(), f"{ts}.GET.{uri}".encode(),
                                        hashlib.sha256).digest()).decode()
        req = urllib.request.Request(f"{API}{uri}?{q}", headers={
            "X-Timestamp": ts, "X-API-KEY": env["NAVER_SEARCHAD_ACCESS_LICENSE"],
            "X-Customer": env["NAVER_SEARCHAD_CUSTOMER_ID"], "X-Signature": sig})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("keywordList", [])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"  실패({attempt}/3) {getattr(e, 'code', '')} {hints[0]}", flush=True)
            time.sleep(2 * attempt)
    return None


def cnt(v) -> int:
    """월간 검색량: "< 10" 은 5 로."""
    if isinstance(v, (int, float)):
        return int(v)
    return 5 if "<" in str(v) else int(str(v).replace(",", "") or 0)


def is_real(x: dict | None) -> bool:
    """PC·모바일 둘 중 하나라도 "< 10" 이 아닌 숫자면 실제 검색량이 있는 키워드."""
    return bool(x) and any(str(x.get(f, "")).strip() and "<" not in str(x.get(f, "")) for f in FIELDS)


def region_coef(sido: str, sigungu: str) -> float:
    if sido in CAPITAL:
        return 0.5
    if sido in METRO or (sido == "전남광주통합특별시" and sigungu in GWANGJU_GU):
        return 0.8
    return 1.0


def four(name: str) -> tuple[list[str], list[str]]:
    """"강릉시" → (['강릉시폐차','강릉시폐차장','강릉폐차','강릉폐차장'], ['강릉시','강릉'])."""
    out, prefixes = [f"{name}폐차", f"{name}폐차장"], [name]
    if len(name) > 2 and name[-1] in "시군구":
        short = name[:-1]
        out += [f"{short}폐차", f"{short}폐차장"]
        prefixes.append(short)
    return out, prefixes


def variants(sido: str, sigungu: str) -> tuple[list[str], list[str], str]:
    """(조회할 변형 키워드, 연관 키워드로 셀 지역 이름 앞부분, 비고)."""
    if not sigungu:  # 세종
        return ["세종시폐차", "세종시폐차장", "세종폐차", "세종폐차장"], ["세종"], ""
    gu = sigungu.split()[-1]
    if " " in sigungu:  # 일반구
        city_short = sigungu.split()[0][:-1]
        if len(gu) <= 2 or gu in shared_sigungu_names():
            name = city_short + gu
            return [f"{name}폐차", f"{name}폐차장"], [name], f"일반구 · '{city_short}' 붙여 조회 · 시 이름 검색량 나눠 더함"
        h, p = four(gu)
        return h, p, "일반구 · 시 이름 검색량 나눠 더함"
    if gu in shared_sigungu_names() or (sido == "전남광주통합특별시" and gu in GWANGJU_GU and gu in {"동구", "서구", "남구", "북구"}):
        pre = "광주" if sido == "전남광주통합특별시" and gu in GWANGJU_GU else SIDO_SHORT[sido]
        name = pre + gu
        return [f"{name}폐차", f"{name}폐차장"], [name], f"같은 이름 여러 곳 → '{pre}' 붙여 조회"
    h, p = four(gu)
    note = "'광주'는 다른 지역과 겹칠 수 있음" if gu == "광주시" else ""
    return h, p, note


def gu_count_by_city() -> dict[tuple[str, str], int]:
    """(시도, '수원시') → 그 시의 일반구 개수(전국 법정동 목록 기준)."""
    seen: dict[tuple[str, str], set[str]] = {}
    for row in csv.DictReader((ROOT / "data" / "legal_dong_list.csv").open(encoding="utf-8-sig")):
        sg = row["시군구"]
        if " " in sg:
            city, gu = sg.split(" ", 1)
            seen.setdefault((row["시도"], city), set()).add(gu)
    return {k: len(v) for k, v in seen.items()}


def collect(rows: list[dict], hints: list[str], prefixes: list[str]) -> list[tuple[str, str, dict | None]]:
    got = {x["relKeyword"]: x for x in rows}
    out = [("변형", h, got.get(h)) for h in hints]
    for x in rows:
        k = x["relKeyword"]
        if k not in hints and "폐차" in k and any(k.startswith(p) for p in prefixes):
            out.append(("연관", k, x))
    return out


def raw_row(sido, label, kind, k, x) -> dict:
    return {"시도": sido, "시군구": label, "구분": kind, "키워드": k,
            "PC": x["monthlyPcQcCnt"] if x else "", "모바일": x["monthlyMobileQcCnt"] if x else "",
            "경쟁정도": x.get("compIdx", "") if x else "", "월평균노출광고수": x.get("plAvgDepth", "") if x else "",
            "조회결과": ("있음" if is_real(x) else "있음(< 10)") if x else "없음(0으로 셈)"}


def fetch(targets: list[tuple[str, str]]) -> tuple[dict, dict, list[dict], list]:
    """API 조회 → (지역별 키워드, 시별 키워드, CSV 줄, 실패한 지역)."""
    env = load_env()
    raw, own_kw, city_kw, failed = [], {}, {}, []
    n_gu = gu_count_by_city()
    for sido, city in sorted({(s, g.split()[0]) for s, g in targets if " " in g}):
        hints, prefixes = four(city)
        found = collect(call(env, hints) or [], hints, prefixes)
        city_kw[(sido, city)] = [(k, x) for _, k, x in found]
        raw += [raw_row(sido, city, f"시 이름(구 {n_gu.get((sido, city), 1)}개로 나눔)", k, x) for _, k, x in found]
        print(f"시 {city}: 키워드 {len(found)}개", flush=True)
    for i, (sido, sigungu) in enumerate(targets, 1):
        hints, prefixes, _ = variants(sido, sigungu)
        rows = call(env, hints)
        if rows is None:
            failed.append((sido, sigungu))
            continue
        own = collect(rows, hints, prefixes)
        own_kw[(sido, sigungu)] = [(k, x) for _, k, x in own]
        raw += [raw_row(sido, sigungu or SIDO_SHORT[sido], kind, k, x) for kind, k, x in own]
        print(f"{i}/{len(targets)} {sigungu or sido}", flush=True)
    return own_kw, city_kw, raw, failed


def from_csv(path: Path, targets: list[tuple[str, str]]) -> tuple[dict, dict]:
    """저장된 CSV 로 지역별·시별 키워드를 되살린다(API 없이 다시 계산)."""
    own_kw, city_kw = {}, {}
    label_to_key = {(s, g or SIDO_SHORT[s]): (s, g) for s, g in targets}
    for r in csv.DictReader(path.open(encoding="utf-8-sig")):
        x = None if r["조회결과"].startswith("없음") else {
            "monthlyPcQcCnt": r["PC"], "monthlyMobileQcCnt": r["모바일"], "compIdx": r["경쟁정도"], "plAvgDepth": r["월평균노출광고수"]}
        if r["구분"].startswith("시 이름"):
            city_kw.setdefault((r["시도"], r["시군구"]), []).append((r["키워드"], x))
        else:
            own_kw.setdefault(label_to_key[(r["시도"], r["시군구"])], []).append((r["키워드"], x))
    return own_kw, city_kw


def score_all(targets, own_kw, city_kw, failed) -> list[dict]:
    gu_data = json.loads((ROOT / "data" / "gu.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "cases" / "index.json").read_text(encoding="utf-8"))
    gu_keys = {(g["sido"], g["sigungu"]) for g in gu_data}
    case_keys = {(c["sido"], c["sigungu"]) for c in cases}
    basis, counts, _meta = vehicle_stats.load()
    n_gu = gu_count_by_city()
    table = []
    for sido, sigungu in targets:
        label = sigungu or SIDO_SHORT[sido]
        if (sido, sigungu) in failed or (sido, sigungu) not in own_kw:
            table.append({"sido": sido, "sigungu_key": sigungu, "sigungu": label, "vol": None, "note": "조회 실패"})
            continue
        own = own_kw[(sido, sigungu)]
        vol = sum(cnt(x[f]) for _, x in own if x for f in FIELDS)
        pool = [(k, x) for k, x in own if is_real(x)]
        if " " in sigungu:
            city = sigungu.split()[0]
            div = n_gu.get((sido, city), 1)
            ck = city_kw.get((sido, city), [])
            vol += sum(cnt(x[f]) for _, x in ck if x for f in FIELDS) / div
            pool += [(k, x) for k, x in ck if is_real(x)]
        best = max(pool, key=lambda kx: cnt(kx[1][FIELDS[0]]) + cnt(kx[1][FIELDS[1]]), default=None)
        old = vehicle_stats.count_for(counts, sido, sigungu) if basis != "none" else None
        t = {"sido": sido, "sigungu_key": sigungu, "sigungu": label, "vol": round(vol), "real": best is not None, "old": old,
             "rc": region_coef(sido, sigungu), "note": variants(sido, sigungu)[2],
             "gu": "있음" if (sido, sigungu) in gu_keys else "없음", "case": "있음" if (sido, sigungu) in case_keys else "없음",
             "top": [f"{k} {cnt(x[FIELDS[0]]) + cnt(x[FIELDS[1]])}" for k, x in
                     sorted(pool, key=lambda kx: -(cnt(kx[1][FIELDS[0]]) + cnt(kx[1][FIELDS[1]])))[:8]]}
        if best:
            x = best[1]
            t["comp"] = x.get("compIdx") or "낮음"
            t["depth"] = float(x.get("plAvgDepth") or 0)
            t["floor"] = FLOOR_COEF if vol < FLOOR_VOL else 1.0
            t["score"] = vol * COMP.get(t["comp"], 0.3) * t["rc"] / (1 + t["depth"]) * t["floor"]
        table.append(t)
    return table


def write_report(date: str, table: list[dict]) -> tuple[list, list]:
    failed = [t for t in table if t["vol"] is None]
    ranked = sorted((t for t in table if t["vol"] is not None and t["real"]),
                    key=lambda t: (-t["score"], -t["vol"], t["sido"], t["sigungu"]))
    none_ = sorted((t for t in table if t["vol"] is not None and not t["real"]),
                   key=lambda t: (-(t["old"] or 0), t["sido"], t["sigungu"]))
    lines = [
        f"# 전국 시·군·구 폐차 키워드 점수표 ({date})", "",
        "네이버 검색광고 API 키워드도구로 지역마다 \"{시군구}폐차\"·\"{시군구}폐차장\"·\"{이름}폐차\"·\"{이름}폐차장\" 4개를 조회하고, "
        "같이 돌아온 그 지역의 폐차 연관 키워드(비용·견적·보상금 등)를 더했습니다. 원본은 "
        f"`data/keywords/region_kw_{date}.csv`, 만드는 스크립트는 `scripts/naver_region_kw.py`.", "",
        "- 점수 = 검색량 합(\"< 10\"은 5) × 경쟁 계수(낮음 1.0 / 중간 0.6 / 높음 0.3) × 지방 계수(서울·경기·인천 0.5, 광역시 0.8, 그 외 1.0) "
        f"÷ (1 + 월평균 노출 광고수) × 하한 계수(검색량 합 {FLOOR_VOL} 미만은 {FLOOR_COEF})",
        "- 경쟁정도·광고수는 \"< 10\"이 아닌 키워드 가운데 검색량이 가장 많은 것의 값입니다.",
        "- 일반구는 구 이름 변형에 더해 시 이름 변형(예: 창원시폐차·창원폐차) 검색량을 그 시의 일반구 개수로 나눠 더했습니다.",
        "- PC·모바일이 모두 \"< 10\"인 키워드만 있는 지역은 순위에서 빼고 맨 아래 \"검색량 없음\" 묶음에 노후차 추정 대수 순으로 두었습니다.",
        "- 지방 계수 근거: 지방은 광고·경쟁 페이지가 적고 지역 폐차장 견적이 낮아 우리 금액이 이김(10/14 랜딩 손님 4명 전부 지방).",
        "- 여러 시·도에 같은 이름이 있는 구는 시·도(일반구는 시) 이름을 붙여 조회했습니다(비고 칸). 노후차 추정 대수는 순서를 정하는 데만 씁니다.",
        "- 이 순서가 `data/priority_regions.json` 이 됩니다(순위 → 검색량 없음 → 2026-10-02 목록에만 있던 곳).",
        f"- 대상 {len(table)}곳: 순위 {len(ranked)}곳, 검색량 없음 {len(none_)}곳, 조회 실패 {len(failed)}곳"
        + (" (" + ", ".join(f"{t['sido']} {t['sigungu']}" for t in failed) + ")" if failed else ""), "",
        "| 순위 | 시도 | 시군구 | 검색량 합 | 경쟁정도 | 광고수 | 지방계수 | 하한 | 점수 | 구 페이지 | 사례 | 노후차 추정 | 비고 |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|---|---|---:|---|",
    ]
    for n, t in enumerate(ranked, 1):
        lines.append(f"| {n} | {SIDO_SHORT[t['sido']]} | {t['sigungu']} | {t['vol']} | {t['comp']} | {t['depth']:.1f} | {t['rc']} | "
                     f"{t['floor']} | {t['score']:.1f} | {t['gu']} | {t['case']} | {t['old'] or ''} | {t['note']} |")
    lines += ["", f"## 검색량 없음 ({len(none_)}곳, 노후차 추정 대수 순)", "",
              "| 차례 | 시도 | 시군구 | 검색량 합 | 지방계수 | 구 페이지 | 사례 | 노후차 추정 | 비고 |",
              "|---:|---|---|---:|---:|---|---|---:|---|"]
    for n, t in enumerate(none_, 1):
        lines.append(f"| {n} | {SIDO_SHORT[t['sido']]} | {t['sigungu']} | {t['vol']} | {t['rc']} | {t['gu']} | {t['case']} | {t['old'] or ''} | {t['note']} |")
    (ROOT / "docs" / f"region-priority-{date}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ranked, none_


def write_priority(date: str, ranked: list[dict], none_: list[dict]) -> int:
    """data/priority_regions.json 을 이 순서로. 동 이름 검색(dongs)·시·도 키워드는 예전 목록에서 가져오고,
    예전 목록에만 있던 시군구는 뒤에 예전 순서대로 붙인다."""
    old = json.loads(PRIORITY.read_text(encoding="utf-8")) if PRIORITY.exists() else {}
    old_by = {(e["sido"], e["sigungu"]): e for e in old.get("gu", [])}
    gu, seen = [], set()
    for group, rows in (("순위", ranked), ("검색량 없음", none_)):
        for t in rows:
            key = (t["sido"], t["sigungu_key"])
            seen.add(key)
            gu.append({"rank": len(gu) + 1, "sido": t["sido"], "sigungu": t["sigungu_key"], "group": group,
                       "score": round(t.get("score", 0.0), 1), "volume": t["vol"], "keywords": t["top"],
                       "dongs": old_by.get(key, {}).get("dongs", [])})
    for e in old.get("gu", []):
        if (e["sido"], e["sigungu"]) not in seen:
            gu.append({**e, "rank": len(gu) + 1, "group": "2026-10-02 목록에만 있음"})
    data = {
        "_comment": old.get("_comment", ""),
        "made_on": date,
        "source": f"data/keywords/region_kw_{date}.csv (네이버 검색광고 API 키워드도구, scripts/naver_region_kw.py). "
                  f"점수표 docs/region-priority-{date}.md",
        "score": "검색량 합 × 경쟁 계수 × 지방 계수 ÷ (1 + 월평균 노출 광고수) × 하한 계수(100 미만 0.5). "
                 "순위 → 검색량 없음(노후차 추정 순) → 2026-10-02 목록에만 있던 곳",
        "dong_target_per_gu": old.get("dong_target_per_gu", 3),
        "gu": gu,
        "sido_keywords": old.get("sido_keywords", []),
    }
    PRIORITY.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(gu)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--offline", action="store_true", help="API 없이 저장된 CSV 로 다시 계산")
    ap.add_argument("--write-priority", action="store_true", help="data/priority_regions.json 을 이 순위로 바꿈")
    args = ap.parse_args()
    regions = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
    gu_data = json.loads((ROOT / "data" / "gu.json").read_text(encoding="utf-8"))
    targets = sorted({(r["sido"], r["sigungu"]) for r in regions} | {(g["sido"], g["sigungu"]) for g in gu_data})
    out_csv = ROOT / "data" / "keywords" / f"region_kw_{args.date}.csv"
    if args.offline:
        # CSV 를 만든 날의 대상만 다시 계산(그 뒤 새로 생긴 시군구는 다음 조회 때)
        own_kw, city_kw = from_csv(out_csv, targets)
        targets = [t for t in targets if t in own_kw]
        failed = []
    else:
        own_kw, city_kw, raw, failed = fetch(targets)
        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(raw[0].keys()))
            w.writeheader()
            w.writerows(raw)
    table = score_all(targets, own_kw, city_kw, failed)
    ranked, none_ = write_report(args.date, table)
    msg = f"완료: docs/region-priority-{args.date}.md, 순위 {len(ranked)}곳, 검색량 없음 {len(none_)}곳"
    if args.write_priority:
        msg += f", data/priority_regions.json {write_priority(args.date, ranked, none_)}곳"
    print(msg)


if __name__ == "__main__":
    main()
