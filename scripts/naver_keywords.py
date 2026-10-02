"""
네이버 키워드 도구(검색광고 > 키워드 도구)에서 받은 「연관키워드 YYYYMMDD HHMM.xlsx」 여러 개를 합쳐
검색량 표와 동·구 페이지 우선순위 목록(data/priority_regions.json)을 만든다.

사용법
  python3 scripts/naver_keywords.py data/keywords/*.xlsx --date 2026-10-02

만드는 파일 (날짜는 --date)
  data/keywords/naver_keywords_<날짜>.csv   합친 표: 키워드, PC 월간검색수, 모바일 월간검색수, 합계, 경쟁정도
  data/keywords/region_volume_<날짜>.csv    지역 키워드를 시·도 / 시·군·구 / 동 으로 나눈 검색량
  data/keywords/topic_volume_<날짜>.csv     지역 없는 주제 키워드(방치차·시동·상속·압류 …) 검색량
  data/priority_regions.json                앞으로 만들 동·구 페이지 우선순위(scripts/priority_regions.py 가 읽음)

규칙
- 중복 키워드(띄어쓰기만 다른 것 포함)는 하나로, 숫자가 다르면 합계가 큰 줄을 남긴다.
- "< 10" 은 5 로 계산한다(합계 칸). PC·모바일 칸은 원본 글자 그대로 둔다.
- 지역 키워드 = 지역 이름 + 끝말(폐차, 폐차장, 자동차폐차장, 조기폐차, 중고차수출 …). 지역 이름은
  data/legal_dong_list.csv 의 시도·시군구 이름(줄임 이름 포함)과 아래 ALIAS(동·읍·생활권 이름)로만 찾는다.
  업체 이름(○○폐차산업, 가나폐차장 등)처럼 지역으로 풀리지 않는 것은 지역 키워드로 보지 않는다.
- 같은 이름의 시군구가 여러 시도에 있으면(강서구, 북구, 고성 …) "모호" 로 두고 우선순위에 넣지 않는다.
  단 시도 줄임 이름과 겹치면 시도로 본다(광주 → 옛 광주광역시 지역, 경기 광주는 "경기광주"·"광주시"로 따로 검색됨).
- 우선순위 점수 = 그 시군구의 폐차·폐차장 계열 + 조기폐차 계열 검색량. 수출·부품·중고차 끝말은 표에만 싣는다.
  시 이름 키워드(창원 폐차장)는 대표 구(그 구 이름만의 검색량 → 추정 노후 자가용 대수 순) 하나에 전부, 나머지 구에 n분의 1. 시·도 키워드는 /si/ 페이지 몫이라 넣지 않는다.
- 금액·시세 키워드(가격·시세·비용·견적·폐차비·보상금·지원금 …)는 주제 표에 "금액형" 으로 표시만 하고
  추천 문구에는 쓰지 않는다.
"""
import argparse
import csv
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vehicle_stats
from vehicle_stats import SIDO_ALIAS, SIGUNGU_ALIAS

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "legal_dong_list.csv"
KW_DIR = ROOT / "data" / "keywords"
PRIORITY_PATH = ROOT / "data" / "priority_regions.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# 끝말 → 종류. 긴 것부터 맞춘다.
SUFFIX_KIND = {
    "폐차": "폐차", "폐차장": "폐차", "자동차폐차": "폐차", "자동차폐차장": "폐차", "관허폐차장": "폐차",
    "차량폐차": "폐차", "압류폐차": "폐차", "지게차폐차": "폐차", "시폐차": "폐차",
    "조기폐차": "조기폐차", "조기폐차지원금": "조기폐차", "조기폐차보조금": "조기폐차",
    "경유차조기폐차": "조기폐차", "노후경유차조기폐차": "조기폐차",
    "중고차수출": "수출", "자동차수출": "수출", "수출차": "수출",
    "폐차장부품": "부품", "폐차장중고부품": "부품", "자동차부품": "부품", "중고차부품": "부품", "자동차중고부품": "부품",
    "중고차매매": "중고차", "중고차": "중고차",
}
SCORE_KINDS = ("폐차", "조기폐차")

# 시도·시군구 이름만으로는 안 잡히는 동·읍·생활권 이름. (시도, 시군구, 동 또는 "")
# 같은 이름이 여러 곳에 있는 것(온양, 평촌, 비봉, 죽산, 시화 등)은 넣지 않는다.
ALIAS = {
    "장안동": ("서울특별시", "동대문구", "장안동"),
    "장안평": ("서울특별시", "동대문구", ""),
    "장한평": ("서울특별시", "동대문구", ""),
    "성수동": ("서울특별시", "성동구", "성수동"),
    "정왕동": ("경기도", "시흥시", "정왕동"),
    "진접": ("경기도", "남양주시", "진접읍"),
    "곤지암": ("경기도", "광주시", "곤지암읍"),
    "향남": ("경기도", "화성시 만세구", "향남읍"),
    "안중": ("경기도", "평택시", "안중읍"),
    "공도": ("경기도", "안성시", "공도읍"),
    "일산": ("경기도", "고양시 일산동구|고양시 일산서구", ""),
    "분당": ("경기도", "성남시 분당구", ""),
    "마산": ("경상남도", "창원시 마산합포구|창원시 마산회원구", ""),
    "진영": ("경상남도", "김해시", "진영읍"),
    "장유": ("경상남도", "김해시", "장유동"),
    "녹산": ("부산광역시", "강서구", "녹산동"),
    "정관": ("부산광역시", "기장군", "정관읍"),
    "일광": ("부산광역시", "기장군", "일광읍"),
    "언양": ("울산광역시", "울주군", "언양읍"),
    "현풍": ("대구광역시", "달성군", "현풍읍"),
    "왜관": ("경상북도", "칠곡군", "왜관읍"),
    "함창": ("경상북도", "상주시", "함창읍"),
    "신탄진": ("대전광역시", "대덕구", "신탄진동"),
    "조치원": ("세종특별자치시", "", "조치원읍"),
    "오창": ("충청북도", "청주시 청원구", "오창읍"),
    "성환": ("충청남도", "천안시 서북구", "성환읍"),
    "해미": ("충청남도", "서산시", "해미면"),
    "문막": ("강원특별자치도", "원주시", "문막읍"),
    "영종도": ("인천광역시", "영종구", ""),
    "남동공단": ("인천광역시", "남동구", ""),
}
# 시군구 이름처럼 보이지만 지역으로 세지 않을 낱말(업체·도로·생활권 이름)
NOT_REGION = {"자유로", "중부", "경인", "수도권", "전국", "근처", "인터넷", "서울중기"}

# 주제 키워드 (지역 없는 것만). 위에서부터 처음 맞는 주제로 센다.
TOPICS = [
    ("방치차", r"방치"),
    ("시동 안 걸림·고장차", r"시동|고장차|문제차"),
    ("상속·사망자", r"상속|사망자|한정승인"),
    ("압류·저당·체납", r"압류|저당|체납|강제폐차"),
    ("법인차", r"법인"),
    ("차령초과 말소", r"차령초과|차량초과말소|차령폐차|연식폐차"),
    ("조기폐차·노후경유차", r"조기폐차|조기페차|노후경유차|노후차|노후폐차|경유차.*(폐차|지원)|[45]등급|저감장치|경유차등급|폐차(지원금|보조금)"),
    ("수출 비교", r"수출"),
    ("견인", r"견인"),
    ("근처·당일·주말(추가)", r"근처|당일|주말|출장"),
    ("사고·침수차(추가)", r"사고|침수|전손|잔존물|미수선"),
    ("서류·절차·말소(추가)", r"서류|절차|말소|방법|하는법|하기$|하려면|신청|신고|대행|과정|진행|처리"),
]
MONEY = re.compile(r"가격|시세|비용|견적|금액|단가|값|보상|지원금|보조금|지원$|정부지원|대금|많이주는|비$")


def read_xlsx(path: Path) -> list[list[str]]:
    """openpyxl 없이 첫 시트를 읽는다(네이버 키워드 도구 파일은 시트 하나)."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    rows = []
    for r in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(f"{NS}row"):
        cells = {}
        for c in r.findall(f"{NS}c"):
            col = 0
            for ch in re.match(r"[A-Z]+", c.get("r")).group():
                col = col * 26 + ord(ch) - 64
            v, t = c.find(f"{NS}v"), c.get("t")
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{NS}t"))
            elif v is None:
                val = ""
            elif t == "s":
                val = shared[int(v.text)]
            else:
                val = v.text
            cells[col - 1] = val.strip()
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def num(s: str) -> int:
    s = s.replace(",", "").strip()
    if s.startswith("<"):
        return 5
    return int(float(s)) if s else 0


def load_keywords(paths: list[Path]) -> list[dict]:
    best: dict[str, dict] = {}
    for p in paths:
        rows = read_xlsx(p)
        head = rows[1] if len(rows) > 1 else []
        i_pc = head.index("월간검색수(PC)") if "월간검색수(PC)" in head else 1
        i_mo = head.index("월간검색수(모바일)") if "월간검색수(모바일)" in head else 2
        i_comp = rows[0].index("경쟁정도") if "경쟁정도" in rows[0] else 7
        for r in rows[2:]:
            if not r or not r[0]:
                continue
            kw = re.sub(r"\s+", "", r[0])
            row = {"keyword": kw, "pc": r[i_pc], "mobile": r[i_mo],
                   "total": num(r[i_pc]) + num(r[i_mo]), "competition": r[i_comp] if len(r) > i_comp else ""}
            if kw not in best or row["total"] > best[kw]["total"]:
                best[kw] = row
    return sorted(best.values(), key=lambda x: (-x["total"], x["keyword"]))


class RegionIndex:
    def __init__(self) -> None:
        rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
        self.dong_codes: dict[tuple[str, str, str], list[str]] = {}
        self.sigungus: set[tuple[str, str]] = set()
        for r in rows:
            self.sigungus.add((r["시도"], r["시군구"]))
            dong = re.sub(r"\d+가$", "", r["읍면동"])  # 성수동1가·2가 → 성수동
            self.dong_codes.setdefault((r["시도"], r["시군구"], dong), []).append(r["법정동코드"])
        # 시도 이름: 정식 이름, 줄임 이름(vehicle_stats.SIDO_ALIAS), 서울시·부산시 …, 경기도·제주도
        self.sido_names: dict[str, str] = {s: s for s, _ in self.sigungus}
        self.sido_names.update(SIDO_ALIAS)
        for short, full in SIDO_ALIAS.items():
            if len(short) == 2 and full.endswith(("특별시", "광역시", "특별자치시")):
                self.sido_names.setdefault(short + "시", full)
        self.sido_names.update({"경기도": "경기도", "제주도": "제주특별자치도"})
        # 시군구 이름 → [(시도, 시군구)]
        self.sgg_names: dict[str, set[tuple[str, str]]] = {}
        for sido, sgg in self.sigungus:
            if not sgg:
                continue
            toks = sgg.split()
            names = {"".join(toks)}
            for tok in toks:
                names.add(tok)
                if tok[-1] in "시군구" and len(tok) > 2:
                    names.add(tok[:-1])
            if len(toks) == 2:
                names.add(toks[0])
            for n in names:
                self.sgg_names.setdefault(n, set()).add((sido, sgg))
        # 옛 이름(인천 서구 → 서해구·검단구 등)
        for (sido, old), news in SIGUNGU_ALIAS.items():
            for n in (old,):
                self.sgg_names.setdefault(sido[:2] + n, set()).update((sido, x) for x in news)

    def resolve(self, name: str) -> dict:
        """지역 이름 → {"level": "sido|sigungu|dong|ambiguous", "targets": [(시도, 시군구, 동)]}"""
        name = re.sub(r"(지역)$", "", name)
        if not name or name in NOT_REGION:
            return {"level": None, "targets": []}
        if name in ALIAS:
            sido, sggs, dong = ALIAS[name]
            return {"level": "dong" if dong else "sigungu", "targets": [(sido, s, dong) for s in sggs.split("|")]}
        if name == "세종" or name == "세종시":
            return {"level": "sigungu", "targets": [("세종특별자치시", "", "")]}
        if name in self.sido_names and name != "광주시":  # 광주시는 경기 광주시
            return {"level": "sido", "targets": [(self.sido_names[name], "", "")]}
        if name in self.sgg_names:
            return self._sgg(self.sgg_names[name])
        # 시도 이름 + 시군구 이름 (대구달서구, 경기도광주, 부산사상구, 인천서구 …)
        for pre in sorted(self.sido_names, key=len, reverse=True):
            if name.startswith(pre) and len(name) > len(pre):
                rest, sido = name[len(pre):], self.sido_names[pre]
                cands = {x for x in self.sgg_names.get(rest, set()) | self.sgg_names.get(pre[:2] + rest, set()) if x[0] == sido}
                if cands:
                    return self._sgg(cands)
        return {"level": None, "targets": []}

    @staticmethod
    def _sgg(cands: set[tuple[str, str]]) -> dict:
        if len({s for s, _ in cands}) > 1:  # 같은 이름이 여러 시도에 있음
            return {"level": "ambiguous", "targets": sorted((s, g, "") for s, g in cands)}
        return {"level": "sigungu", "targets": sorted((s, g, "") for s, g in cands)}


def split_region(kw: str, idx: RegionIndex):
    norm = kw.replace("페차", "폐차")
    for suf in sorted(SUFFIX_KIND, key=len, reverse=True):
        if norm.endswith(suf) and len(norm) > len(suf):
            res = idx.resolve(norm[: -len(suf)])
            if res["level"]:
                return SUFFIX_KIND[suf], norm[: -len(suf)], res
    return None


def topic_of(kw: str) -> str | None:
    for name, pat in TOPICS:
        if re.search(pat, kw):
            return name
    return None


def label(t: tuple[str, str, str]) -> str:
    return " ".join(x for x in t if x)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    kws = load_keywords([Path(f) for f in args.files])
    idx = RegionIndex()
    KW_DIR.mkdir(parents=True, exist_ok=True)

    with (KW_DIR / f"naver_keywords_{args.date}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["키워드", "PC 월간검색수", "모바일 월간검색수", "합계", "경쟁정도"])
        for k in kws:
            w.writerow([k["keyword"], k["pc"], k["mobile"], k["total"], k["competition"]])

    region_rows, topic_rows = [], []
    for k in kws:
        sp = split_region(k["keyword"], idx)
        if sp:
            kind, name, res = sp
            region_rows.append({**k, "kind": kind, "name": name, "level": res["level"], "targets": res["targets"]})
            continue
        t = topic_of(k["keyword"])
        if t:
            topic_rows.append({**k, "topic": t, "money": bool(MONEY.search(k["keyword"]))})

    with (KW_DIR / f"region_volume_{args.date}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["키워드", "구분", "지역 단위", "지역", "합계", "PC", "모바일", "경쟁정도"])
        for r in region_rows:
            w.writerow([r["keyword"], r["kind"], {"sido": "시·도", "sigungu": "시·군·구", "dong": "동", "ambiguous": "모호"}[r["level"]],
                        " / ".join(label(t) for t in r["targets"]), r["total"], r["pc"], r["mobile"], r["competition"]])
    with (KW_DIR / f"topic_volume_{args.date}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["주제", "키워드", "금액형", "합계", "PC", "모바일", "경쟁정도"])
        for r in sorted(topic_rows, key=lambda r: ([t for t, _ in TOPICS].index(r["topic"]), -r["total"])):
            w.writerow([r["topic"], r["keyword"], "예" if r["money"] else "", r["total"], r["pc"], r["mobile"], r["competition"]])

    # 시군구별 점수. 구가 여러 개인 시(창원 폐차장 → 5개 구)의 키워드는 대표 구 하나에 전부, 나머지 구에는 n 분의 1.
    # 대표 구 = 그 구 이름만으로 잡힌 검색량(진해 폐차장 등)이 많은 구 → 추정 노후 자가용 대수가 많은 구.
    scored = [r for r in region_rows if r["level"] in ("sigungu", "dong") and r["kind"] in SCORE_KINDS]
    own: dict[tuple[str, str], int] = {}
    for r in scored:
        if len(r["targets"]) == 1:
            key = r["targets"][0][:2]
            own[key] = own.get(key, 0) + r["total"]
    basis, counts, _ = vehicle_stats.load()

    def lead_key(t: tuple[str, str, str]) -> tuple:
        n = vehicle_stats.count_for(counts, t[0], t[1]) if basis != "none" else None
        return (-own.get(t[:2], 0), -(n or 0), t)

    sgg: dict[tuple[str, str], dict] = {}
    for r in scored:
        lead = min(r["targets"], key=lead_key)
        for sido, g, dong in r["targets"]:
            e = sgg.setdefault((sido, g), {"sido": sido, "sigungu": g, "score": 0, "keywords": [], "dongs": {}})
            share = r["total"] if (sido, g, dong) == lead else round(r["total"] / len(r["targets"]))
            e["score"] += share
            e["keywords"].append(f"{r['keyword']} {r['total']}" + ("" if share == r["total"] else f" (나눠 {share})"))
            if dong:
                d = e["dongs"].setdefault(dong, {"dong": dong, "codes": idx.dong_codes.get((sido, g, dong), []), "score": 0, "keywords": []})
                d["score"] += r["total"]
                d["keywords"].append(r["keyword"])
    ranked = sorted((e for e in sgg.values() if e["score"] > 0), key=lambda e: (-e["score"], e["sido"], e["sigungu"]))
    out = []
    for i, e in enumerate(ranked, 1):
        out.append({"rank": i, "sido": e["sido"], "sigungu": e["sigungu"], "score": e["score"],
                    "keywords": e["keywords"],
                    "dongs": sorted(e["dongs"].values(), key=lambda d: -d["score"])})
    sido_vol: dict[str, int] = {}
    for r in region_rows:
        if r["level"] == "sido" and r["kind"] in SCORE_KINDS:
            sido_vol[r["targets"][0][0]] = sido_vol.get(r["targets"][0][0], 0) + r["total"]
    priority = {
        "_comment": "앞으로 만들 동·구 페이지 우선순위(네이버 검색량 순). scripts/naver_keywords.py 가 만들고 "
                    "scripts/priority_regions.py 를 거쳐 pick_next_regions.py·pick_next_gu.py 가 읽는다. 손으로 고치지 않는다.",
        "made_on": args.date,
        "source": f"data/keywords/naver_keywords_{args.date}.csv (네이버 키워드 도구 연관키워드, 월간검색수 PC+모바일, '< 10'은 5)",
        "score": "그 시군구 이름이 들어간 '폐차·폐차장·자동차폐차장·조기폐차' 키워드 검색량 합. 구가 여러 개인 시의 키워드(창원 폐차장)는 대표 구 하나에 전부, 나머지 구에는 n분의 1.",
        "dong_target_per_gu": 3,
        "gu": out,
        "sido_keywords": [{"sido": s, "score": v} for s, v in sorted(sido_vol.items(), key=lambda x: -x[1])],
    }
    PRIORITY_PATH.write_text(json.dumps(priority, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    amb = [r["keyword"] for r in region_rows if r["level"] == "ambiguous"]
    print(f"키워드 {len(kws)}개 (중복 제거 후), 지역 키워드 {len(region_rows)}개, 주제 키워드 {len(topic_rows)}개")
    print(f"우선순위 시군구 {len(out)}곳 → {PRIORITY_PATH.relative_to(ROOT)}")
    print("모호해서 뺀 키워드: " + ", ".join(amb))


if __name__ == "__main__":
    main()
