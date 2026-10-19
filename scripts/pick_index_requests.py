"""
오늘 구글 서치 콘솔에 손으로 색인 요청할 주소 10개를 고른다(2026-10-18 병한님 요청). 매일 루틴이 커밋 전에 돌리고,
3시 보고 맨 끝에 "오늘 구글 색인 요청 10개"로 붙인다. 네이버·공용 IndexNow 자동 전송(scripts/indexnow.py)과는 따로다.

사용법
  python3 scripts/pick_index_requests.py           # 고르기만(파일 그대로)
  python3 scripts/pick_index_requests.py --write   # 고른 주소를 docs/index-requests.md 에 오늘 날짜로 덧붙임

고르는 순서(2026-10-18 병한님 결정: 10개 중 3개는 ②에 먼저 배정, 그다음 ① → 남은 ② → ③)
  ⓪ 맨 앞(2026-10-19 병한님): docs/index-requests.md 의 "## 최우선" 칸 주소 중 아직 요청 안 된 것(적힌 순서대로)
  ① 오늘 새로 만든 구·시 페이지(페이지의 datePublished 가 오늘, 한국 시간)
  ② 문의가 온 페이지(docs/index-requests.md 의 "문의가 온 페이지" 칸)와 같은 시·군의 구·동 페이지
     (일반구면 같은 시의 다른 구 페이지와 그 구들의 동 페이지까지, 구 페이지 → 동 페이지 순)
  ③ docs/region-priority 점수표(data/priority_regions.json) 순위 높은 지방 시·군(build_gu.min_dong_pages 가 0)의 구 페이지
  docs/index-requests.md 의 날짜 칸("## 2026-10-18" 등)에 있는 주소는 요청한 것으로 보고 뺀다. 주소는 %인코딩한 전체 주소.
  날짜 칸 제목에 "요청 못 함"이 있으면(할당량 초과 등) 그 칸 주소는 요청 안 한 것으로 보고 다음 날 다시 고른다.
  오늘 날짜 칸이 이미 "요청 못 함"으로 적혀 있으면 --write 도 같은 표시를 단 칸으로 덧붙인다.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_gu import min_dong_pages  # noqa: E402
from build_site import CONFIG, GU_DATA, REGIONS, gu_file, load_json  # noqa: E402
from build_si import si_file, si_sidos  # noqa: E402

LOG = ROOT / "docs" / "index-requests.md"
COUNT = 10
INQUIRY_FIRST = 3  # 문의 온 시·군 몫(2026-10-18)
PUBLISHED_RE = re.compile(r'"datePublished": "(\d{4}-\d{2}-\d{2})"')
URL_RE = re.compile(r"https://pyecha119\.com/\S+?\.html")


def today() -> str:
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


DATE_HEAD_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
NOT_DONE = "요청 못 함"  # 날짜 칸 제목에 이 말이 있으면 그 칸 주소는 요청 안 한 것(2026-10-19)


def sections(text: str) -> list[tuple[str, str]]:
    """"## 제목" 칸들 [(제목, 본문)]."""
    return [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1] if "\n" in p else "") for p in text.split("\n## ")[1:]]


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

    def dong_url(slug):
        return f"{base}/pages/{slug}.html"

    lists: dict[str, list[tuple[str, str]]] = {"new": [], "inquiry": [], "rank": []}
    bucket = ["new"]

    def add(url: str, why: str) -> None:
        if url not in done and url not in {u for u, _ in lists[bucket[0]]}:
            lists[bucket[0]].append((url, why))

    # ① 오늘 새로 만든 구·시 페이지
    for g in gu_data:
        f = ROOT / "gu" / gu_file(g["sido"], g["sigungu"])
        m = PUBLISHED_RE.search(f.read_text(encoding="utf-8")) if f.exists() else None
        if m and m.group(1) == day:
            add(gu_url(g["sido"], g["sigungu"]), "오늘 새로 만든 구 페이지")
    for sido in sorted(si_sidos()):
        f = ROOT / "si" / si_file(sido)
        m = PUBLISHED_RE.search(f.read_text(encoding="utf-8")) if f.exists() else None
        if m and m.group(1) == day:
            add(f"{base}/si/{quote(si_file(sido))}", "오늘 새로 만든 시·도 페이지")

    # ② 문의가 온 페이지와 같은 시·군의 구·동 페이지
    bucket[0] = "inquiry"
    by_file = {gu_file(g["sido"], g["sigungu"]): (g["sido"], g["sigungu"]) for g in gu_data}
    by_slug = {r["slug"]: (r["sido"], r["sigungu"]) for r in regions}
    gu_keys = {(g["sido"], g["sigungu"]) for g in gu_data}
    per_inquiry: list[list[tuple[str, str]]] = []
    for u in URL_RE.findall(inquiry):
        lists["inquiry"] = []  # 문의 온 곳마다 따로 모았다가 아래에서 번갈아 섞는다
        per_inquiry.append(lists["inquiry"])
        path = unquote(u[len(base) + 1:])
        key = by_file.get(path[3:]) if path.startswith("gu/") else by_slug.get(path[6:-5]) if path.startswith("pages/") else None
        if not key:
            continue
        sido, sigungu = key
        city = sigungu.split()[0] if " " in sigungu else sigungu
        group = sorted(k for k in gu_keys | {(r["sido"], r["sigungu"]) for r in regions}
                       if k[0] == sido and (k[1] == sigungu or (" " in sigungu and k[1].startswith(city + " "))))
        for k in [key] + [k for k in group if k != key]:
            if k in gu_keys:
                add(gu_url(*k), f"문의 온 곳({sigungu})과 같은 시·군의 구 페이지")
        for k in [key] + [k for k in group if k != key]:
            for r in sorted((r for r in regions if (r["sido"], r["sigungu"]) == k), key=lambda r: r["dong"]):
                add(dong_url(r["slug"]), f"문의 온 곳({sigungu})과 같은 시·군의 동 페이지")

    # 문의 온 곳이 여럿이면 번갈아(화성 → 강릉 → 화성 …), 같은 곳 안에서는 구 페이지 → 동 페이지 순
    merged = []
    for i in range(max((len(x) for x in per_inquiry), default=0)):
        merged += [x[i] for x in per_inquiry if i < len(x)]
    lists["inquiry"] = merged

    # ③ 점수표 순위 높은 지방 시·군의 구 페이지
    bucket[0] = "rank"
    for e in load_json(ROOT / "data" / "priority_regions.json", default={}).get("gu", []):
        k = (e["sido"], e["sigungu"])
        if k in gu_keys and min_dong_pages(*k) == 0:
            add(gu_url(*k), f"점수표 {e['rank']}위 지방 시·군")

    # ⓪ 최우선 칸(2026-10-19) → 10개 중 3개는 ②(문의 온 시·군)에 먼저 배정 → ① 새 페이지 → 남은 ② → ③ (2026-10-18)
    first = [(u, "최우선 칸") for u in priority if u not in done]
    picked: list[tuple[str, str]] = []
    for u, why in first + lists["inquiry"][:INQUIRY_FIRST] + lists["new"] + lists["inquiry"][INQUIRY_FIRST:] + lists["rank"]:
        if u not in {x for x, _ in picked} and len(picked) < COUNT:
            picked.append((u, why))
    print(f"오늘 구글 색인 요청 {len(picked)}개 ({day}, docs/index-requests.md 에 있던 {len(done)}개는 뺌)")
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
