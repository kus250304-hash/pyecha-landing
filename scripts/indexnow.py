"""
IndexNow 로 새 페이지·바뀐 페이지 주소를 검색엔진에 알린다 (2026-10-08).

사용법
  python3 scripts/indexnow.py all              # 사이트맵(인덱스의 나눈 파일 전부)의 모든 주소 (처음 한 번)
  python3 scripts/indexnow.py changed          # 마지막 커밋(HEAD)에서 본문이 실제로 바뀐 페이지와 새 페이지만
                                               # (공통 틀·메타 태그·날짜만 바뀐 페이지는 스스로 뺌, 2026-10-22부터 기본)
  python3 scripts/indexnow.py changed <커밋>   # 그 커밋에서 바뀐 것 (기본 HEAD)
  python3 scripts/indexnow.py changed <시작>..<끝>   # 여러 커밋을 합쳐서(시작 커밋 다음부터 끝까지, 2026-11-13. 매일 루틴 10-1)
  --max N                                      # changed 하루 상한(기본 100, 2026-11-11 병한님). 넘으면 반응 온 페이지 →
                                               # 사례 붙은 구·시군 페이지 → 나머지 순으로 N개만 보내고 "상한으로 안 보낸 수 n" 출력
  python3 scripts/indexnow.py changed --all-diff  # 옛 방식: 날짜만 바뀐 페이지만 빼고 바뀐 .html 전부(공통 틀만 바뀐 페이지 포함)
  python3 scripts/indexnow.py new [커밋]       # 그 커밋에서 새로 생긴 .html 의 주소만 (2026-10-16부터 기본으로 쓰는 것)
  --dry-run                                    # 보내지 않고 주소 수와 앞 몇 개만 출력

- 키: data/site_config.json 의 indexnow_key. 사이트 맨 위 폴더 {키}.txt 가 같은 값을 담고 있어야 한다(keyLocation).
- 보내는 곳: 네이버 https://searchadvisor.naver.com/indexnow, 공용 https://api.indexnow.org/indexnow.
  한 번에 최대 10,000개씩 JSON(POST)으로 보낸다. 200·202 가 정상 접수.
- 사이트맵(sitemap.xml 인덱스의 나눈 파일들)에 있는 주소만 보낸다. 예전 주소의 자동 이동 페이지, 검색엔진 소유확인 파일은 sitemap 에 없으므로 빠진다.
- 네트워크 실패나 오류 응답은 멈추지 않고 출력만 한다(종료 코드 0). 매일 루틴이 push 뒤에 changed 를 돌린다(2026-11-11부터, 예전 new).
- 2026-10-16 병한님 결정: 매일 루틴은 new 로 새 주소만 보낸다.
- 2026-10-18 병한님 결정: 제목·본문이 실제로 바뀐 페이지는 changed 로 보내도 되고, 날짜(최종 업데이트·dateModified)만 바뀐 페이지는
  changed 가 스스로 뺀다(date_only_change).
- 2026-10-22 병한님 결정: og:site_name 한 줄만 더한 커밋에서 changed 가 1,171개를 보낸 일 뒤로, changed 는 플래그 없이도
  본문 해시(sitemap_lib.content_hash)가 바뀐 페이지와 새 페이지만 보낸다(--body-only 없앰). 옛 방식은 --all-diff 를 붙여야만 된다.
- 2026-11-11 병한님 결정(docs/current-rules.md): 매일 루틴은 changed(그날 루틴이 올린 커밋 전부)로 보내고, changed 는 하루 100개까지.
  반응 온 페이지 = data/ga4_daily.json 최근 7일 폼·전화·문자 1 이상(pick_index_requests.ga4_reacted),
  사례 붙은 구·시군 = 어제·오늘 사례가 새로 붙은 구·시군 페이지(pick_index_requests.new_cases). all·new 는 상한 없이 그대로.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "site_config.json"
ENDPOINTS = [
    ("네이버", "https://searchadvisor.naver.com/indexnow"),
    ("공용", "https://api.indexnow.org/indexnow"),
]
BATCH = 10_000


def sitemap_urls() -> list[str]:
    """사이트맵 인덱스(sitemap.xml)에 적힌 나눈 파일 전부의 페이지 주소(2026-10-20부터 인덱스 방식, sitemap_lib.py)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import sitemap_lib
    return sitemap_lib.all_locs(ROOT)


DEFAULT_MAX = 100  # changed 하루 상한(2026-11-11 병한님)


def span(rev: str) -> tuple[str, str]:
    """"A..B" → (A, B), 커밋 하나 → (rev~1, rev)."""
    if ".." in rev:
        a, b = rev.split("..", 1)
        return a, b or "HEAD"
    return f"{rev}~1", rev


DATE_RES = [re.compile(r'(<p class="updated">최종 업데이트: )[^<]*(</p>)'), re.compile(r'("dateModified": ")[^"]*(")')]


def date_only_change(rev: str, path: str) -> bool:
    """그 커밋(또는 A..B)에서 이 페이지가 날짜 줄만 바뀌었으면 True."""
    old, new = span(rev)
    def show(r: str) -> str:
        return subprocess.run(["git", "-c", "core.quotepath=false", "show", f"{r}:{path}"], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8").stdout

    def mask(t: str) -> str:
        for rx in DATE_RES:
            t = rx.sub(lambda m: m.group(1) + m.group(2), t)
        return t
    return mask(show(old)) == mask(show(new))


def body_unchanged(rev: str, path: str) -> bool:
    """그 커밋(또는 A..B)에서 이 페이지의 본문 해시(sitemap_lib.content_hash)가 그대로면 True(공통 틀·구조화 데이터·날짜만 바뀜)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import sitemap_lib
    old, new = span(rev)

    def show(r: str) -> str:
        return subprocess.run(["git", "-c", "core.quotepath=false", "show", f"{r}:{path}"], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8").stdout
    return sitemap_lib.content_hash(show(old)) == sitemap_lib.content_hash(show(new))


def changed_urls(base: str, rev: str, kinds: str = "AM", all_diff: bool = False) -> list[str]:
    """그 커밋에서 새로 생기거나(A) 바뀐(M) .html 파일 → sitemap 에 있는 주소. kinds="A" 면 새로 생긴 것만.
    바뀐 페이지는 본문 해시가 바뀐 것만 남긴다(2026-10-22부터 기본). all_diff(--all-diff)면 옛 방식대로
    날짜만 바뀐 페이지만 빼고 공통 틀·메타 태그만 바뀐 페이지도 보낸다."""
    out = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-status", "--no-renames", *span(rev)],
                         cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    rows = [line.split("\t", 1) for line in out.splitlines() if line[:1] in kinds and line.endswith(".html")]
    # 2026-10-18 병한님 결정: 날짜("최종 업데이트"·dateModified)만 바뀐 페이지는 보내지 않는다. 제목·본문이 바뀐 페이지는 보낸다
    paths = [p for st, p in rows if st[:1] == "A" or not date_only_change(rev, p)]
    skipped = len(rows) - len(paths)
    if skipped:
        print(f"IndexNow: 날짜만 바뀐 페이지 {skipped}개는 뺌")
    if not all_diff:
        kept = [p for st, p in rows if p in paths and (st[:1] == "A" or not body_unchanged(rev, p))]
        if len(kept) != len(paths):
            print(f"IndexNow: 본문이 그대로인(공통 틀·메타 태그만 바뀐) 페이지 {len(paths) - len(kept)}개는 뺌 (보내려면 --all-diff)")
        paths = kept
    listed = {unquote(u): u for u in sitemap_urls()}
    urls = []
    for p in paths:
        plain = f"{base}/" if p == "index.html" else f"{base}/{p}"
        if plain in listed:
            urls.append(listed[plain])
    return urls


def cap(base: str, urls: list[str], limit: int) -> tuple[list[str], int]:
    """changed 하루 상한(2026-11-11): 넘으면 반응 온 페이지 → 사례 붙은 구·시군 페이지 → 나머지(원래 순서) 순으로 limit 개.
    돌려주는 것: (보낼 주소, 상한으로 안 보낸 수)."""
    if limit <= 0 or len(urls) <= limit:
        return urls, 0
    sys.path.insert(0, str(ROOT / "scripts"))
    from datetime import datetime, timedelta
    import pick_index_requests as pir
    day = pir.today()
    yday = (datetime.fromisoformat(day) - timedelta(days=1)).date().isoformat()
    rank: dict[str, int] = {}
    for u, _ in pir.ga4_reacted(base, day):
        rank.setdefault(unquote(u), 0)
    for c, _ in pir.new_cases(yday, day):
        rank.setdefault(unquote(f"{base}/gu/{pir.gu_file(c['sido'], c['sigungu'])}"), 1)
    order = sorted(range(len(urls)), key=lambda i: (rank.get(unquote(urls[i]), 2), i))
    keep = [urls[i] for i in order[:limit]]
    return keep, len(urls) - len(keep)


def post(endpoint: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return f"{r.status}"
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode("utf-8", "replace").strip()
        return f"{e.code}" + (f" ({body})" if body else "")
    except Exception as e:  # 네트워크 실패는 멈추지 않는다
        return f"실패 ({type(e).__name__}: {e})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["all", "changed", "new"])
    ap.add_argument("rev", nargs="?", default="HEAD", help="changed·new 일 때 기준 커밋 또는 시작..끝 (기본 HEAD)")
    ap.add_argument("--max", type=int, default=DEFAULT_MAX, help=f"changed 하루 상한(기본 {DEFAULT_MAX}, 0 이면 상한 없음)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all-diff", action="store_true",
                    help="changed 에서 본문 해시가 그대로인 페이지(공통 틀·메타 태그만 바뀐 페이지)까지 보냄(옛 방식, 2026-10-22부터 기본은 뺌)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    key, base = cfg.get("indexnow_key"), cfg["site_base_url"].rstrip("/")
    if not key:
        print("IndexNow: site_config.json 에 indexnow_key 가 없어 보내지 않음")
        return
    if not (ROOT / f"{key}.txt").exists():
        print(f"IndexNow: 맨 위 폴더에 {key}.txt 가 없어 보내지 않음")
        return

    try:
        urls = sitemap_urls() if args.mode == "all" else changed_urls(base, args.rev, "A" if args.mode == "new" else "AM", args.all_diff)
    except subprocess.CalledProcessError as e:
        print(f"IndexNow: 바뀐 파일을 읽지 못함 ({e.stderr.strip()[:200]})")
        return
    if not urls:
        print(f"IndexNow ({args.mode}): 보낼 주소 0개")
        return

    host = urlparse(base).netloc
    if args.mode == "changed":
        urls, over = cap(base, urls, args.max)
        if over:
            print(f"IndexNow (changed): 상한으로 안 보낸 수 {over} (상한 {args.max}, 반응 온 → 사례 붙은 구·시군 → 나머지 순으로 자름)")
    print(f"IndexNow ({args.mode}): 보낼 주소 {len(urls)}개")
    if args.dry_run:
        print("  (dry-run) " + "\n  (dry-run) ".join(urls[:5]))
        return
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i + BATCH]
        payload = {"host": host, "key": key, "keyLocation": f"{base}/{quote(key)}.txt", "urlList": chunk}
        for name, endpoint in ENDPOINTS:
            print(f"  {name} {endpoint}: 응답 {post(endpoint, payload)}, 보낸 주소 {len(chunk)}개")


if __name__ == "__main__":
    main()
