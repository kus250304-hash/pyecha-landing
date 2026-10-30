"""
구글 서치 콘솔 URL 검사 API 로 구·시군·주제(안내) 페이지가 이미 색인됐는지 확인한다(2026-10-30 병한님).
pick_index_requests.py 가 구글 목록을 고를 때 색인됨인 주소를 빼서, 병한님이 서치 콘솔에서 하나하나 확인하고 건너뛰는 일을 없앤다.

사용법
  python scripts/gsc_index_check.py              # 확인하고 data/gsc_index_status.json 에 저장
  python scripts/gsc_index_check.py --push       # PC 예약 작업용: git pull → 확인 → 그 json 하나만 커밋·푸시
  python scripts/gsc_index_check.py --test 5     # 시험: 5개만 확인(저장도 함)
  python scripts/gsc_index_check.py --dry        # 키 없이 오늘 확인할 주소 수만 보기

- API: searchconsole.urlInspection.index.inspect(하루 2,000건·1분 600건). 속성은 sc-domain:pyecha119.com 먼저, 안 되면 URL 접두어
  https://pyecha119.com/ (권한 있는 쪽을 json 의 site 에 적음).
- 열쇠: 서비스 계정 JSON C:\\Users\\AOMG\\gsc-key.json(GSC_KEY 환경 변수로 바꿀 수 있음, 저장소 밖). 값은 출력·기록하지 않는다.
  키가 없으면 아무것도 하지 않고 "키 없음"만 알리고 끝난다(예약 작업이 키가 생기면 저절로 돌기 시작).
  구글 라이브러리 없이 파이썬 기본 기능만으로 서명한다(RS256, 키의 PKCS#8 PEM 을 직접 읽음).
- 대상: sitemap-core.xml 의 /gu/·/guide/ 주소(구글 목록과 같은 범위, noindex·자동 이동 페이지는 사이트맵에 없음).
- 하루 최대 300건(--limit). 순서: 처음 보는 주소 → 색인 안 됨(마지막 확인이 오래된 것부터, 하루 한 번) → 색인됨인데
  마지막 확인이 14일 넘은 것. 색인됨으로 확인된 주소는 14일에 한 번만 다시 본다.
- 색인됨 = coverageState 에 "indexed" 가 있고 "not indexed" 가 없음("Submitted and indexed", "Indexed, not submitted in sitemap" 등).
- 결과 data/gsc_index_status.json: {"updated": 마지막으로 확인한 날, "site": 속성, "pages": {주소: {"coverageState", "indexed", "checked"}}}.
  사이트맵에서 빠진 주소는 지운다. 손으로 고치지 않는다.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "gsc_index_status.json"
KEY = Path(os.environ.get("GSC_KEY", r"C:\Users\AOMG\gsc-key.json"))
SITES = ["sc-domain:pyecha119.com", "https://pyecha119.com/"]
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
DAILY_LIMIT = 300
RECHECK_INDEXED_DAYS = 14


def today() -> str:
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


def is_indexed(state: str) -> bool:
    s = (state or "").lower()
    return "indexed" in s and "not indexed" not in s


# ── 서비스 계정 서명(RS256)을 기본 기능만으로 ──
def _der(data: bytes, i: int) -> tuple[int, int, int]:
    """(태그, 값 시작, 값 끝)."""
    tag, n = data[i], data[i + 1]
    i += 2
    if n & 0x80:
        k = n & 0x7F
        n, i = int.from_bytes(data[i:i + k], "big"), i + k
    return tag, i, i + n


def _rsa_key(pem: str) -> tuple[int, int]:
    """PKCS#8(BEGIN PRIVATE KEY) 또는 PKCS#1(BEGIN RSA PRIVATE KEY) → (n, d)."""
    der = base64.b64decode("".join(l for l in pem.strip().splitlines() if not l.startswith("-----")))
    _, s, _ = _der(der, 0)  # 바깥 SEQUENCE
    _, s1, e1 = _der(der, s)  # version INTEGER
    tag, s2, e2 = _der(der, e1)
    if tag == 0x30:  # PKCS#8: AlgorithmIdentifier 다음 OCTET STRING 안에 PKCS#1
        _, s3, e3 = _der(der, e2)
        der, (_, s, _) = der[s3:e3], _der(der[s3:e3], 0)
        _, s1, e1 = _der(der, s)
    vals, i = [], e1
    for _ in range(3):  # n, e, d
        _, vs, ve = _der(der, i)
        vals.append(int.from_bytes(der[vs:ve], "big"))
        i = ve
    return vals[0], vals[2]


def _sign(msg: bytes, n: int, d: int) -> bytes:
    k = (n.bit_length() + 7) // 8
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(msg).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(digest_info) - 3) + b"\x00" + digest_info
    return pow(int.from_bytes(em, "big"), d, n).to_bytes(k, "big")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def access_token(key: dict) -> str:
    now = int(time.time())
    token_uri = key.get("token_uri") or "https://oauth2.googleapis.com/token"
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = _b64(json.dumps({"iss": key["client_email"], "scope": SCOPE, "aud": token_uri, "iat": now, "exp": now + 3600}).encode())
    n, d = _rsa_key(key["private_key"])
    jwt = f"{head}.{claims}.{_b64(_sign(f'{head}.{claims}'.encode(), n, d))}"
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}).encode()
    with urllib.request.urlopen(urllib.request.Request(token_uri, data=body), timeout=30) as r:
        return json.loads(r.read())["access_token"]


def inspect(token: str, site: str, url: str) -> dict:
    body = json.dumps({"inspectionUrl": url, "siteUrl": site, "languageCode": "en-US"}).encode()
    req = urllib.request.Request(INSPECT_URL, data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


# ── 대상 고르기·저장 ──
def targets() -> list[str]:
    text = (ROOT / "sitemap-core.xml").read_text(encoding="utf-8")
    return [u for u in re.findall(r"<loc>([^<]+\.html)</loc>", text) if "/gu/" in u or "/guide/" in u]


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"updated": "", "site": "", "pages": {}}


def due(urls: list[str], pages: dict, day: str, limit: int) -> list[str]:
    old = (date.fromisoformat(day) - timedelta(days=RECHECK_INDEXED_DAYS)).isoformat()
    new = [u for u in urls if u not in pages]
    not_idx = sorted((u for u in urls if u in pages and not pages[u].get("indexed") and pages[u].get("checked", "") < day),
                     key=lambda u: pages[u].get("checked", ""))
    idx = sorted((u for u in urls if u in pages and pages[u].get("indexed") and pages[u].get("checked", "") <= old),
                 key=lambda u: pages[u].get("checked", ""))
    return (new + not_idx + idx)[:limit]


def save(data: dict, urls: list[str]) -> None:
    keep = set(urls)
    data["pages"] = {u: data["pages"][u] for u in sorted(data["pages"]) if u in keep}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def push(day: str, summary: str) -> str:
    rel = OUT.relative_to(ROOT).as_posix()
    if not git("status", "--porcelain", "--", rel).stdout.strip():
        return "바뀐 것 없음(커밋 안 함)"
    r = git("commit", "-m", f"GSC index check ({day}): {summary}", "--", rel)
    if r.returncode:
        return "커밋 실패: " + (r.stderr or r.stdout).strip()[:200]
    for _ in range(2):
        if git("push", "origin", "main").returncode == 0:
            return "푸시 " + git("rev-parse", "--short", "HEAD").stdout.strip()
        git("pull", "--rebase", "--autostash", "origin", "main")
    return "푸시 실패(다음 실행 때 다시)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--test", type=int, metavar="N")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=DAILY_LIMIT)
    args = ap.parse_args()
    day = today()
    if args.push:
        git("checkout", "main")
        git("pull", "--rebase", "--autostash", "origin", "main")
    urls, data = targets(), load()
    todo = due(urls, data["pages"], day, min(args.test or args.limit, DAILY_LIMIT))
    if args.dry:
        print(f"오늘 확인할 주소 {len(todo)}개 (대상 {len(urls)}개, 기록 {len(data['pages'])}개)")
        return
    if not KEY.exists():
        print(f"키 없음({KEY}) — 건너뜀. 키 파일을 이 자리에 두면 다음 실행부터 돕니다.")
        return
    if not todo:
        print(f"오늘 확인할 주소 없음(대상 {len(urls)}개 모두 기한 안)")
        return
    try:
        token = access_token(json.loads(KEY.read_text(encoding="utf-8")))
    except (urllib.error.URLError, KeyError, ValueError) as e:
        print(f"실패: 키로 접속 못 함({type(e).__name__}{' ' + str(e.code) if isinstance(e, urllib.error.HTTPError) else ''}) — 키 파일·서비스 계정 확인")
        sys.exit(1)
    sites = [data["site"]] + [s for s in SITES if s != data["site"]] if data.get("site") else SITES
    site, done, errors, stop = None, 0, 0, ""
    for u in todo:
        try:
            if site:
                res = inspect(token, site, u)
            else:  # 처음 한 번: 권한 있는 속성 찾기(도메인 → URL 접두어)
                for i, s in enumerate(sites):
                    try:
                        res, site = inspect(token, s, u), s
                        break
                    except urllib.error.HTTPError as e:
                        if e.code != 403 or i == len(sites) - 1:
                            raise
        except urllib.error.HTTPError as e:
            if e.code == 403 and not site:
                stop = "권한 없음(403) — 서비스 계정 이메일을 서치 콘솔 사용자 및 권한에 추가했는지 확인"
                break
            if e.code == 429:
                stop = "할당량 초과(429) — 내일 이어서"
                break
            errors += 1
            if errors >= 5:
                stop = f"오류가 이어짐(HTTP {e.code})"
                break
            continue
        except urllib.error.URLError:
            errors += 1
            if errors >= 5:
                stop = "인터넷 연결 오류가 이어짐"
                break
            continue
        state = res.get("inspectionResult", {}).get("indexStatusResult", {}).get("coverageState", "")
        data["pages"][u] = {"coverageState": state, "indexed": is_indexed(state), "checked": day}
        done += 1
        if args.test:
            print(f"  {urllib.parse.unquote(u)} — {state or '(빈 값)'}")
        time.sleep(0.2)
    if done:
        data.update({"updated": day, "site": site or data.get("site", "")})
        save(data, urls)
    pages = {u: v for u, v in data["pages"].items() if u in set(urls)}
    n_idx = sum(v["indexed"] for v in pages.values())
    summary = f"checked {done}, indexed {n_idx}/{len(pages)}"
    print(f"{'성공' if done else '실패'}: 오늘 {done}개 확인 · 색인됨 {n_idx}개 / 기록 {len(pages)}개 / 대상 {len(urls)}개"
          + (f" · 오류 {errors}개" if errors else "") + (f" · 멈춤: {stop}" if stop else "") + (f" · 속성 {site}" if site else ""))
    if args.push and done:
        print(push(day, summary))
    if not done:
        sys.exit(1)


if __name__ == "__main__":
    main()
