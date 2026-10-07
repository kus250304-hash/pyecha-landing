"""
IndexNow 로 새 페이지·바뀐 페이지 주소를 검색엔진에 알린다 (2026-10-08).

사용법
  python3 scripts/indexnow.py all              # sitemap.xml 의 모든 주소 (처음 한 번)
  python3 scripts/indexnow.py changed          # 마지막 커밋(HEAD)에서 새로 생기거나 바뀐 .html 의 주소만
  python3 scripts/indexnow.py changed <커밋>   # 그 커밋에서 바뀐 것 (기본 HEAD)
  --dry-run                                    # 보내지 않고 주소 수와 앞 몇 개만 출력

- 키: data/site_config.json 의 indexnow_key. 사이트 맨 위 폴더 {키}.txt 가 같은 값을 담고 있어야 한다(keyLocation).
- 보내는 곳: 네이버 https://searchadvisor.naver.com/indexnow, 공용 https://api.indexnow.org/indexnow.
  한 번에 최대 10,000개씩 JSON(POST)으로 보낸다. 200·202 가 정상 접수.
- sitemap.xml 에 있는 주소만 보낸다. 예전 주소의 자동 이동 페이지, 검색엔진 소유확인 파일은 sitemap 에 없으므로 빠진다.
- 네트워크 실패나 오류 응답은 멈추지 않고 출력만 한다(종료 코드 0). 매일 루틴이 push 뒤에 changed 를 돌린다.
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
SITEMAP = ROOT / "sitemap.xml"
ENDPOINTS = [
    ("네이버", "https://searchadvisor.naver.com/indexnow"),
    ("공용", "https://api.indexnow.org/indexnow"),
]
BATCH = 10_000


def sitemap_urls() -> list[str]:
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", SITEMAP.read_text(encoding="utf-8"))


def changed_urls(base: str, rev: str) -> list[str]:
    """그 커밋에서 새로 생기거나(A) 바뀐(M) 또는 이름이 바뀐(R) .html 파일 → sitemap 에 있는 주소."""
    out = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-status", "--no-renames", f"{rev}~1", rev],
                         cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    paths = [line.split("\t", 1)[1] for line in out.splitlines() if line[:1] in "AM" and line.endswith(".html")]
    listed = {unquote(u): u for u in sitemap_urls()}
    urls = []
    for p in paths:
        plain = f"{base}/" if p == "index.html" else f"{base}/{p}"
        if plain in listed:
            urls.append(listed[plain])
    return urls


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
    ap.add_argument("mode", choices=["all", "changed"])
    ap.add_argument("rev", nargs="?", default="HEAD", help="changed 일 때 기준 커밋 (기본 HEAD)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    key, base = cfg.get("indexnow_key"), cfg["site_base_url"].rstrip("/")
    if not key:
        print("IndexNow: site_config.json 에 indexnow_key 가 없어 보내지 않음")
        return
    if not (ROOT / f"{key}.txt").exists():
        print(f"IndexNow: 맨 위 폴더에 {key}.txt 가 없어 보내지 않음")
        return

    try:
        urls = sitemap_urls() if args.mode == "all" else changed_urls(base, args.rev)
    except subprocess.CalledProcessError as e:
        print(f"IndexNow: 바뀐 파일을 읽지 못함 ({e.stderr.strip()[:200]})")
        return
    if not urls:
        print(f"IndexNow ({args.mode}): 보낼 주소 0개")
        return

    host = urlparse(base).netloc
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
