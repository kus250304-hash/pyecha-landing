"""
오늘 구글 서치 콘솔에 손으로 색인 요청할 주소 10개를 고른다(2026-10-18 병한님 요청, 2026-10-20 10개 → 5개, 2026-10-22 5개 → 10개). 매일 루틴이 커밋 전에
돌리고, 아침 보고 맨 끝에 "오늘 색인 요청 10개 — 구글 URL 검사와 네이버 웹 페이지 수집에 같은 주소를 넣습니다"로 붙인다(2026-10-22부터 네이버 웹 페이지 수집에도 같은 주소). 네이버·공용 IndexNow 자동 전송(scripts/indexnow.py)과는 따로다.

사용법
  python3 scripts/pick_index_requests.py           # 고르기만(파일 그대로)
  python3 scripts/pick_index_requests.py --write   # 고른 주소를 docs/index-requests.md 에 오늘 날짜로 덧붙임

고르는 순서(2026-10-20 병한님 결정, docs/roadmap.md 13절)
  ⓐ 어제·오늘 사례가 새로 붙은 구·시군 페이지(2026-10-28 병한님, cases/index.json 의 added = 페이지에 붙은 날, 없으면 git 에
     cases/<slug>.html 이 처음 들어간 날). 이미 요청했어도 사례가 붙은 날 뒤로 요청한 적이 없으면 다시 고른다
  ⓪ 바로 앞 날짜 칸 제목에 "요청 못 함"이 있으면(할당량 초과 등) 그 칸 주소를 같은 순서로 다시 맨 앞에(같은 주소들을 다시 올림)
  ① docs/index-requests.md 의 "## 최우선" 칸 주소 중 아직 요청 안 된 것(적힌 순서대로, 지금은 주제 페이지 6장)
  ② 문의가 온 페이지(그 파일의 "문의가 온 페이지" 칸)와 같은 시·군의 구·시군 페이지
     (일반구면 같은 시의 다른 구 페이지까지, 문의 온 곳이 여럿이면 번갈아)
  ②-0 빈 땅(검색어 top3 에 폐차 업체가 없는 구·시군, data/rival_targets.json 의 empty) → ②-1 지인 공략 20곳(같은 파일의 rival,
     scripts/naver_rank.py, 2026-10-25). 둘 다 구 페이지 중 아직 요청 안 된 것,
     또는 마지막 요청 날짜 뒤에 본문 해시 날짜(data/page_hashes.json lastmod)가 바뀐 것(내용이 그대로면 다시 고르지 않음)
  ③ 시·도 페이지(/si/, data/si.json 순서) 중 아직 요청 안 된 것
  ④ 점수표(data/priority_regions.json) 순위 높은 지방 시·군(build_gu.min_dong_pages 가 0)의 구 페이지
  동 페이지(/pages/)는 어떤 경우에도 고르지 않는다. (2026-10-27~28 의 A·B 실험 20곳 빼기는 2026-10-28 실험 취소로 없앰.) 날짜 칸("## 2026-10-18" 등)에 있는 주소는 요청한 것으로 보고 뺀다
  (제목에 "요청 못 함"이 있는 칸은 요청 안 한 것). 주소는 %인코딩한 전체 주소.
  오늘 날짜 칸이 이미 "요청 못 함"으로 적혀 있으면 --write 도 같은 표시를 단 칸으로 덧붙인다.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_gu import min_dong_pages  # noqa: E402
from build_site import CONFIG, GU_DATA, REGIONS, gu_file, load_json  # noqa: E402
from build_si import load_si, si_file  # noqa: E402

LOG = ROOT / "docs" / "index-requests.md"
COUNT = 10  # 2026-10-20 10 → 5, 2026-10-22 5 → 10(병한님: 새 요청 14개 안팎에서 할당량 초과)
PUBLISHED_RE = re.compile(r'"datePublished": "(\d{4}-\d{2}-\d{2})"')
URL_RE = re.compile(r"https://pyecha119\.com/\S+?\.html")


def today() -> str:
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


DATE_HEAD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
NOT_DONE = "요청 못 함"  # 날짜 칸 제목에 이 말이 있으면 그 칸 주소는 요청 안 한 것(2026-10-19)


def sections(text: str) -> list[tuple[str, str]]:
    """"## 제목" 칸들 [(제목, 본문)]."""
    return [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1] if "\n" in p else "") for p in text.split("\n## ")[1:]]


def inquiry_places(inquiry: str, base: str, regions: list[dict], gu_data: list[dict]) -> list[tuple[str, str]]:
    """"문의가 온 페이지" 칸 본문의 주소들 → [(시도, 시군구)] (적힌 순서, 겹치면 한 번)."""
    by_file = {gu_file(g["sido"], g["sigungu"]): (g["sido"], g["sigungu"]) for g in gu_data}
    by_slug = {r["slug"]: (r["sido"], r["sigungu"]) for r in regions}
    out: list[tuple[str, str]] = []
    for u in URL_RE.findall(inquiry):
        path = unquote(u[len(base) + 1:])
        key = by_file.get(path[3:]) if path.startswith("gu/") else by_slug.get(path[6:-5]) if path.startswith("pages/") else None
        if key and key not in out:
            out.append(key)
    return out


def inquiry_group(key: tuple[str, str], keys) -> list[tuple[str, str]]:
    """문의 온 시군구와 같은 시·군(일반구면 같은 시의 다른 구까지)에 드는 keys, 문의 온 곳 먼저."""
    sido, sigungu = key
    city = sigungu.split()[0] if " " in sigungu else sigungu
    group = sorted(k for k in keys if k != key and k[0] == sido and " " in sigungu and k[1].startswith(city + " "))
    return ([key] if key in keys else []) + group


def popular_gu(limit: int = 10) -> list[tuple[str, str]]:
    """첫 화면·주제 페이지 "문의 많은 지역"(2026-10-20): 문의가 온 페이지의 구·시군 페이지(적힌 순서) →
    점수표(data/priority_regions.json) 상위 지방 시·군(build_gu.min_dong_pages 가 0)의 구 페이지. 구 페이지 파일이 있는 곳만, limit 개.
    빌드할 때마다 다시 고르므로 문의가 더해지거나 구 페이지가 생기면 저절로 바뀐다."""
    base = load_json(CONFIG)["site_base_url"].rstrip("/")
    gu_data = load_json(GU_DATA, default=[])
    have = {(g["sido"], g["sigungu"]) for g in gu_data if (ROOT / "gu" / gu_file(g["sido"], g["sigungu"])).exists()}
    out = [k for k in inquiry_places(inquiry_text(), base, load_json(REGIONS), gu_data) if k in have]
    for e in load_json(ROOT / "data" / "priority_regions.json", default={}).get("gu", []):
        k = (e["sido"], e["sigungu"])
        if k in have and k not in out and min_dong_pages(*k) == 0:
            out.append(k)
    return out[:limit]


def inquiry_text() -> str:
    text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    return next((body for head, body in sections(text) if head.startswith("문의가 온 페이지")), "")


def new_cases(since: str, until: str) -> list[tuple[dict, str]]:
    """since~until(YYYY-MM-DD) 에 페이지에 붙은 사례 [(사례, 붙은 날)], 최근 것 먼저. 붙은 날은 cases/index.json 의 added,
    없으면(2026-10-28 전에 만든 사례) git 에 cases/<slug>.html 이 처음 들어간 날(한국 시간). git 이 안 되면 added 있는 것만."""
    index = load_json(ROOT / "cases" / "index.json", default=[])
    first: dict[str, str] = {}
    if any(not c.get("added") for c in index):
        try:
            out = subprocess.run(["git", "-c", "core.quotepath=off", "log", "--diff-filter=A", "--name-only", "--format=@%aI",
                                  f"--since={since}T00:00:00+09:00", "--", "cases/*.html"],
                                 cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
        except OSError:
            out = ""
        d = ""
        for line in out.splitlines():  # 최근 커밋부터 나오므로 마지막 값 = 처음 들어간 날
            if line.startswith("@"):
                d = datetime.fromisoformat(line[1:]).astimezone(timezone(timedelta(hours=9))).date().isoformat()
            elif line.startswith("cases/") and line.endswith(".html"):
                first[line[6:-5]] = d
    out_cases = []
    for c in index:
        added = c.get("added") or first.get(c["slug"], "")
        if since <= added <= until:
            out_cases.append((c, added))
    return sorted(out_cases, key=lambda x: x[1], reverse=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", help="이 날짜(YYYY-MM-DD)로 고르기(미리 보기용, 기본 오늘 한국 시간)")
    args = ap.parse_args()
    base = load_json(CONFIG)["site_base_url"].rstrip("/")
    regions, gu_data = load_json(REGIONS), load_json(GU_DATA, default=[])
    text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    secs = sections(text)
    done = {u for head, body in secs if DATE_HEAD_RE.match(head) and NOT_DONE not in head for u in URL_RE.findall(body)}
    priority = [u for head, body in secs if head.startswith("최우선") for u in URL_RE.findall(body)]
    inquiry = next((body for head, body in secs if head.startswith("문의가 온 페이지")), "")
    day = args.date or today()
    day_not_done = any(head.startswith(day) and NOT_DONE in head for head, _ in secs)

    def gu_url(sido, sigungu):
        return f"{base}/gu/{quote(gu_file(sido, sigungu))}"

    gu_keys = {(g["sido"], g["sigungu"]) for g in gu_data}
    ordered: list[tuple[str, str]] = []

    def add(url: str, why: str, again: bool = False) -> None:
        if (again or url not in done) and "/pages/" not in url and url not in {u for u, _ in ordered}:
            ordered.append((url, why))

    last_req: dict[str, str] = {}  # 주소 → 마지막으로 요청한 날
    for head, body in secs:
        if DATE_HEAD_RE.match(head) and NOT_DONE not in head:
            for u in URL_RE.findall(body):
                last_req[u] = max(last_req.get(u, ""), head[:10])

    # ⓐ 어제·오늘 사례가 새로 붙은 구·시군 페이지(2026-10-28). 사례가 붙은 날 뒤로 요청한 적이 없으면 다시
    since = (datetime.fromisoformat(day) - timedelta(days=1)).date().isoformat()
    for c, added in new_cases(since, day):
        k = (c["sido"], c["sigungu"])
        if k in gu_keys:
            url = gu_url(*k)
            if last_req.get(url, "") < added:
                add(url, f"{added} 사례가 새로 붙음({c['sigungu']} {c.get('car', '')})".replace(" )", ")"), again=True)

    # ⓪ 바로 앞 날짜가 "요청 못 함"이면 그 목록을 그대로 다시
    before = sorted({head[:10] for head, _ in secs if DATE_HEAD_RE.match(head) and head[:10] < day})
    if before:
        for head, body in secs:
            if head.startswith(before[-1]) and NOT_DONE in head:
                for u in URL_RE.findall(body):
                    add(u, f"{before[-1]} 요청 못 함 → 다시")

    # ① 최우선 칸
    for u in priority:
        add(u, "최우선 칸")

    # ② 문의가 온 페이지와 같은 시·군의 구·시군 페이지(문의 온 곳이 여럿이면 번갈아)
    per_inquiry = [[(gu_url(*k), f"문의 온 곳({key[1]})과 같은 시·군의 구 페이지") for k in inquiry_group(key, gu_keys)]
                   for key in inquiry_places(inquiry, base, regions, gu_data)]
    for i in range(max((len(x) for x in per_inquiry), default=0)):
        for x in per_inquiry:
            if i < len(x):
                add(*x[i])

    # ②-0 빈 땅·②-1 지인 공략 20곳(2026-10-25, scripts/naver_rank.py 가 쓰는 data/rival_targets.json)의 구 페이지:
    # (가) 아직 요청 안 된 것, (나) 마지막 요청 날짜 뒤에 본문 해시 날짜(lastmod)가 바뀐 것. 내용이 그대로면 다시 고르지 않는다
    lastmod = {rel: v["lastmod"] for rel, v in load_json(ROOT / "data" / "page_hashes.json", default={}).items()}
    targets = load_json(ROOT / "data" / "rival_targets.json", default={})
    if isinstance(targets, list):  # 2026-10-25 첫 모양(지인 목록만)
        targets = {"rival": targets}

    def add_target(t: dict, label: str) -> None:
        if (t["sido"], t["sigungu"]) not in gu_keys:
            return
        url, rel = gu_url(t["sido"], t["sigungu"]), "gu/" + gu_file(t["sido"], t["sigungu"])
        why = f"{label}({t['sigungu'] or t['sido']} · {t.get('query') or ' · '.join(t.get('queries') or [])})"
        if url not in done:
            add(url, why)
        elif lastmod.get(rel, "") > last_req.get(url, ""):
            add(url, f"{why} · {last_req[url]} 요청 뒤 내용 바뀜({lastmod[rel]})", again=True)

    # ②-0 빈 땅(검색어 top3 에 폐차 업체가 없는 구·시군, 점수표 순) → ②-1 지인 공략 20곳. 고르는 조건은 같다
    for t in targets.get("empty", []):
        add_target(t, "빈 땅")
    for t in targets.get("rival", []):
        add_target(t, "지인 공략")

    # ③ 시·도 페이지
    for si in load_si():
        add(f"{base}/si/{quote(si_file(si['sido']))}", "시·도 페이지")

    # ④ 점수표 순위 높은 지방 시·군의 구 페이지
    for e in load_json(ROOT / "data" / "priority_regions.json", default={}).get("gu", []):
        k = (e["sido"], e["sigungu"])
        if k in gu_keys and min_dong_pages(*k) == 0:
            add(gu_url(*k), f"점수표 {e['rank']}위 지방 시·군")

    picked = ordered[:COUNT]
    print(f"오늘 색인 요청 {len(picked)}개 — 구글 URL 검사와 네이버 웹 페이지 수집에 같은 주소를 넣습니다 ({day}, docs/index-requests.md 에 있던 {len(done)}개는 뺌)")
    for i, (u, why) in enumerate(picked, 1):
        print(f"{i}. {unquote(u)} — {why}\n{u}")
    if args.write and picked:
        if not text.endswith("\n"):
            text += "\n"
        head = f"{day} — {NOT_DONE}(이날 할당량 초과로 루틴이 고른 목록만 적음, 다음 날 다시 고름)" if day_not_done else day
        text += f"\n## {head}\n\n" + "".join(f"- {u} — {unquote(u[len(base) + 1:])} ({why})\n" for u, why in picked)
        LOG.write_text(text, encoding="utf-8")
        print(f"docs/index-requests.md 에 {len(picked)}개 덧붙임")


if __name__ == "__main__":
    main()
