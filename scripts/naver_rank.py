"""
네이버 노출 지도(2026-10-22 Fable 설계, 상자 2): 우리 구·시군 페이지가 네이버 검색에서 몇 위로 뜨는지 매일 센다.

  python scripts/naver_rank.py --write   # 조회 + data/naver_rank/YYYY-MM-DD.json·docs/naver-rank.md 저장(같은 날은 덮어씀)
  python scripts/naver_rank.py --dry     # 조회만 하고 요약·표를 화면에

- 키: 저장소 밖 C:\\Users\\AOMG\\naver_search.env 의 NAVER_CLIENT_ID·NAVER_CLIENT_SECRET(naver_searchad.env 와 같은 방식).
  값은 출력·기록하지 않는다. 키 파일이 없으면 아무것도 하지 않고 한 줄만 출력한다(종료 코드 0, PC 예약 작업이 이어서 감).
- 웹문서: data/gu.json 구·시군 페이지 전부 × 검색어 2개("{이름}폐차", "{이름}폐차장"). 이름은 naver_region_kw.variants 의
  변형 규칙 그대로(강릉시 → 강릉, 겹치는 구는 시·도 이름을 앞에). 일반구는 시 이름(천안시 동남구 → 천안폐차·천안폐차장,
  같은 시의 구끼리 결과 공유, 호출은 시마다 1번씩, 2026-10-22). display=30, start=1.
  link 호스트가 pyecha119.com 인 첫 항목의 순위(1~30, 없으면 null)·주소, 참고로 상위 3개 도메인(겹치면 한 번).
- 블로그: docs/index-requests.md "문의가 온 페이지"의 시·군 + data/priority_regions.json 상위 30곳(일반구는 시 이름으로 묶음)만
  "{이름}폐차" 1회씩, blog.naver.com/abh77790 글의 첫 순위.
- 초당 5회 이하, 429·5xx·네트워크 실패는 3번까지 다시(1·2·4초 쉬고). 끝까지 실패한 호출은 순위 대신 "실패"로 적는다.
- 한계: 네이버 웹문서 검색 API 기준이라 휴대폰 통합검색 화면(웹사이트 칸·지도·광고)과 다를 수 있다. 추세용.
  상위 도메인은 경쟁 비교용 기록이며 사이트 글에는 쓰지 않는다.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import CONFIG, GU_DATA, REGIONS, load_json  # noqa: E402
from naver_region_kw import four, variants  # noqa: E402
from pick_index_requests import inquiry_places, inquiry_text  # noqa: E402

ENV = Path(r"C:\Users\AOMG\naver_search.env")
API = "https://naverapihub.apigw.ntruss.com/search/v1/"
OUT_DIR = ROOT / "data" / "naver_rank"
DOC = ROOT / "docs" / "naver-rank.md"
OUR_HOST = "pyecha119.com"
BLOG_ID = "abh77790"
DISPLAY = 30
BLOG_TOP = 30
GAP = 0.21  # 초당 5회 이하
KST = timezone(timedelta(hours=9))


def load_env() -> dict:
    env = {}
    for line in ENV.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class Client:
    def __init__(self, env: dict):
        self.headers = {"X-NCP-APIGW-API-KEY-ID": env.get("NAVER_CLIENT_ID", ""),
                        "X-NCP-APIGW-API-KEY": env.get("NAVER_CLIENT_SECRET", "")}
        self.calls = self.failed = 0
        self.last = 0.0
        self.auth_error = None

    def search(self, kind: str, query: str) -> list[dict] | None:
        """kind = webkr·blog. 결과 items, 끝까지 실패하면 None."""
        url = f"{API}{kind}?" + urllib.parse.urlencode({"query": query, "display": DISPLAY, "start": 1})
        for attempt in range(4):
            wait = self.last + GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.calls += 1
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=self.headers), timeout=30) as r:
                    return json.load(r).get("items", [])
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    self.auth_error = e.code
                    break
                if e.code != 429 and e.code < 500:
                    break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            if attempt < 3:
                time.sleep(2 ** attempt)
        self.failed += 1
        return None


def host(link: str) -> str:
    h = urllib.parse.urlparse(link).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def web_names(sido: str, sigungu: str) -> list[str]:
    """웹문서 검색어 2개: 변형 규칙의 짧은 이름(강릉시 → 강릉) + 폐차·폐차장.
    일반구는 아무도 안 치는 "동남폐차" 대신 시 이름(천안시 동남구 → 천안폐차·천안폐차장, 2026-10-22). 같은 시의 일반구는 결과를 함께 쓴다."""
    if " " in sigungu:
        return four(sigungu.split()[0])[0][-2:]
    return variants(sido, sigungu)[0][-2:]


def blog_name(sido: str, sigungu: str) -> str:
    """블로그 검색어: 일반구는 시 이름으로 묶는다(천안시 동남구 → 천안폐차)."""
    if " " in sigungu:
        return four(sigungu.split()[0])[0][-2]
    return web_names(sido, sigungu)[0]


def priority() -> list[dict]:
    return load_json(ROOT / "data" / "priority_regions.json", default={}).get("gu", [])


def blog_targets() -> list[str]:
    base = load_json(CONFIG)["site_base_url"].rstrip("/")
    keys = inquiry_places(inquiry_text(), base, load_json(REGIONS), load_json(GU_DATA, default=[]))
    keys += [(e["sido"], e["sigungu"]) for e in priority()[:BLOG_TOP]]
    out: list[str] = []
    for k in keys:
        q = blog_name(*k)
        if q not in out:
            out.append(q)
    return out


def web_rank(items: list[dict]) -> dict:
    rank = url = None
    top: list[str] = []
    for i, it in enumerate(items, 1):
        h = host(it.get("link", ""))
        if h not in top and len(top) < 3:
            top.append(h)
        if rank is None and (h == OUR_HOST or h.endswith("." + OUR_HOST)):
            rank, url = i, it["link"]
    return {"rank": rank, "url": url, "top3": top}


def blog_rank(items: list[dict]) -> dict:
    for i, it in enumerate(items, 1):
        if f"blog.naver.com/{BLOG_ID}" in it.get("link", "") or f"blog.naver.com/{BLOG_ID}" in it.get("bloggerlink", ""):
            return {"rank": i, "url": it["link"]}
    return {"rank": None, "url": None}


def collect(client: Client) -> dict:
    ranks = {(e["sido"], e["sigungu"]): e["rank"] for e in priority()}
    regions = []
    done: dict[str, dict] = {}  # 검색어 → 결과(같은 시의 일반구는 한 번만 부름)
    for g in load_json(GU_DATA, default=[]):
        key = (g["sido"], g["sigungu"])
        qs = {}
        for q in web_names(*key):
            if q not in done:
                items = client.search("webkr", q)
                done[q] = web_rank(items) if items is not None else {"rank": None, "url": None, "top3": [], "error": True}
                if client.auth_error:
                    return {}
            qs[q] = done[q]
        regions.append({"sido": g["sido"], "sigungu": g["sigungu"], "priority_rank": ranks.get(key),
                        "web": qs, "blog_query": blog_name(*key)})
    blogs = {}
    for q in blog_targets():
        items = client.search("blog", q)
        blogs[q] = blog_rank(items) if items is not None else {"rank": None, "url": None, "error": True}
        if client.auth_error:
            return {}
    for r in regions:
        r["blog"] = blogs.get(r.pop("blog_query"))
    return {"date": datetime.now(KST).date().isoformat(), "source": f"네이버 검색 API webkr·blog, display={DISPLAY}",
            "calls": client.calls, "failed": client.failed, "regions": regions, "blog": blogs}


def best(r: dict) -> int | None:
    ranks = [x["rank"] for x in r["web"].values() if x.get("rank")]
    return min(ranks) if ranks else None


def failed_all(r: dict) -> bool:
    return all(x.get("error") for x in r["web"].values())


def label(r: dict) -> str:
    return r["sigungu"] or r["sido"]


def previous(day: str) -> dict:
    files = sorted(p for p in OUT_DIR.glob("*.json") if p.stem < day) if OUT_DIR.exists() else []
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else {}


def summary(data: dict, prev: dict) -> tuple[str, list[str]]:
    regs = data["regions"]
    ok = [r for r in regs if not failed_all(r)]
    top10 = [r for r in ok if (best(r) or 99) <= 10]
    top30 = [r for r in ok if best(r)]
    none_ = [r for r in ok if not best(r)]
    blog10 = [q for q, b in data["blog"].items() if (b.get("rank") or 99) <= 10]
    old = {(r["sido"], r["sigungu"]): best(r) for r in prev.get("regions", [])}
    new10 = [label(r) for r in top10 if prev and (old.get((r["sido"], r["sigungu"])) or 99) > 10]
    line = (f"10위 안 {len(top10)}곳 / 30위 안 {len(top30)}곳 / 없음 {len(none_)}곳, 블로그 10위 안 {len(blog10)}곳"
            + (f" (조회 실패 {len(regs) - len(ok)}곳)" if len(ok) != len(regs) else ""))
    return line, new10


def cell(x: dict | None) -> str:
    if not x:
        return "-"
    if x.get("error"):
        return "실패"
    return f"{x['rank']}위" if x.get("rank") else "없음"


def render(data: dict, prev: dict) -> str:
    line, new10 = summary(data, prev)
    old = {(r["sido"], r["sigungu"]): best(r) for r in prev.get("regions", [])}
    regs = sorted(data["regions"], key=lambda r: (r["priority_rank"] or 9999, r["sido"], r["sigungu"]))
    out = [
        "# 네이버 웹문서 순위 (최신)", "",
        f"기준일 {data['date']} · 호출 {data['calls']}회(실패 {data['failed']}회) · `python scripts/naver_rank.py --write` 가 매일 다시 씀(손으로 고치지 않음)", "",
        f"**요약: {line}**", "",
        f"새로 10위 안: {', '.join(new10) if new10 else '없음'}" + ("" if prev else " (어제 기록 없음)"), "",
        "일반구는 시 이름으로 조회(천안시 동남구·서북구 → 천안폐차·천안폐차장, 그 시의 구·시 페이지 중 어느 것이든 pyecha119.com 이 나온 자리를 같이 씀).", "",
        "네이버 웹문서 검색 API 기준이라 휴대폰 통합검색 화면과 다를 수 있음, 추세용. 순위는 상위 30개 안에서 pyecha119.com 이 처음 나온 자리, "
        "블로그는 blog.naver.com/abh77790 글(문의 온 시·군 + 점수표 상위 30곳만 조회, 일반구는 시 이름으로). 어제 대비는 두 검색어 중 좋은 쪽 순위로 셈.", "",
        "| 점수표 순위 | 지역 | 폐차 순위 | 폐차장 순위 | 어제 대비 | 블로그 순위 |",
        "|---|---|---|---|---|---|",
    ]
    for r in regs:
        (q1, a), (q2, b) = list(r["web"].items())
        now, before = best(r), old.get((r["sido"], r["sigungu"]), "x")
        if not prev or before == "x" or failed_all(r):
            diff = "-"
        elif now == before:
            diff = "="
        elif before is None:
            diff = "새로 ↑"
        elif now is None:
            diff = "빠짐 ↓"
        else:
            diff = f"↑{before - now}" if now < before else f"↓{now - before}"
        out.append(f"| {r['priority_rank'] or '-'} | {label(r)} | {q1} {cell(a)} | {q2} {cell(b)} | {diff} | {cell(r['blog'])} |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true", help="조회하고 data/naver_rank/·docs/naver-rank.md 에 저장")
    g.add_argument("--dry", action="store_true", help="조회만 하고 화면에")
    args = ap.parse_args()
    if not ENV.exists():
        print(f"네이버 순위: 키 파일({ENV.name})이 없어 조회하지 않음")
        return
    client = Client(load_env())
    data = collect(client)
    if client.auth_error:
        print(f"네이버 순위: 키 파일 확인 필요(줄바꿈·값 오류) — 응답 {client.auth_error}, 저장하지 않음")
        return
    prev = previous(data["date"])
    line, new10 = summary(data, prev)
    print(f"네이버 순위({data['date']}): {line} · 호출 {data['calls']}회, 실패 {data['failed']}회")
    print(f"새로 10위 안: {', '.join(new10) if new10 else '없음'}")
    if args.dry:
        print(render(data, prev))
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{data['date']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    DOC.write_text(render(data, prev), encoding="utf-8")
    print(f"저장: data/naver_rank/{data['date']}.json, docs/naver-rank.md")


if __name__ == "__main__":
    main()
