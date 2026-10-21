"""
실제 통화 FAQ 풀(data/faq_pool.json) 관리(2026-10-21, docs/roadmap.md 12절 "첫 실행 전에 할 준비").
월 1회 FAQ 풀 갱신(docs/monthly-faq-refresh-prompt.md)이 쓴다. 페이지 몫은 빌드할 때 variants.call_faqs() 가
풀 전체로 다시 고르므로(동 3개·구·시 4개, 첫 항목은 늘 맨 앞) 이 스크립트는 풀에 넣고 검사·미리 보기만 한다.

사용법
  python3 scripts/faq_pool.py show                       # 풀 목록과 질문마다 붙는 페이지 수(동/구/시)
  python3 scripts/faq_pool.py show --page <동 slug|gu:slug|si:시도>   # 그 페이지에 붙는 통화 FAQ
  python3 scripts/faq_pool.py add new.json [--dry-run]   # new.json: [{"q": "...", "a": "...", "source_month": "2026-11"}]
  python3 scripts/faq_pool.py assign                     # 풀 전체 검사 + 지난 커밋(HEAD) 풀과 비교해 FAQ 칸이 바뀌는 페이지 수

검사(하나라도 걸리면 add 는 아무것도 넣지 않고, assign 은 실패로 끝남)
- 겹침: 풀·공통 질문(variants.COMMON_FAQ_QUESTIONS)·안심 질문(FAR_FAQ_Q)과 뜻이 같아 보이는 질문(띄어쓰기·문장부호를 뺀 글자가 같거나 비슷한 정도 0.75 이상)
- 금지 표현: 결과 약속(보장·무조건·100%·1위·최저가), 최고가·1등·최대·실시간 접수·당일 지급, 견인비 단정(무료 견인 등),
  금액(숫자+원·만원 등)·시세·견적가·매입가, 수출이 된다/안 된다 단정
- 개인정보: 전화번호(1600-6011·010-9926-7779 제외)·차량번호·번지·동호수·도로명 번호
- FAQ 답 첫 문장 규칙(variants.FAQ_ANSWER_RULE 1번)
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import variants as V  # noqa: E402
from build_cases import CUSTOMER_RE, EXPORT_CLAIM_RE  # noqa: E402
from check_pages import AMOUNT_RE, PAGE_BAN_RE, PROMISE_RE, TOW_BAN_RE  # noqa: E402

POOL = V.FAQ_POOL_PATH
OUR_NUMBERS = ("1600-6011", "010-9926-7779")
SIMILAR = 0.75
PRICE_WORD_RE = re.compile(r"시세\s*(는|가|로)?\s*\d|고철값\s*\d")


def today() -> str:
    return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


def load_pool() -> dict:
    return json.loads(POOL.read_text(encoding="utf-8"))


def norm(q: str) -> str:
    return re.sub(r"[\s?!.,·~…\"'()]", "", q)


def text_problems(q: str, a: str) -> list[str]:
    """금지 표현·개인정보·답 첫 문장 규칙."""
    out = []
    both = f"{q} {a}"
    for name, rx in (("결과 약속 표현", PROMISE_RE), ("금지 낱말(최고가·1등·최대 등)", PAGE_BAN_RE), ("견인비 단정", TOW_BAN_RE),
                     ("금액", AMOUNT_RE), ("시세 숫자", PRICE_WORD_RE), ("수출 된다/안 된다 단정", EXPORT_CLAIM_RE)):
        m = rx.search(both)
        if m:
            out.append(f"{name} '{m.group(0)}'")
    scrubbed = both
    for n in OUR_NUMBERS:
        scrubbed = scrubbed.replace(n, "")
    m = CUSTOMER_RE.search(scrubbed)
    if m:
        out.append(f"개인정보로 보이는 글자 '{m.group(0)}'")
    p = V.faq_answer_problem(q, a)
    if p:
        out.append(p)
    return out


def overlap(q: str, others: list[str]) -> str:
    """뜻이 같아 보이는 기존 질문(없으면 빈 문자열)."""
    nq = norm(q)
    for o in others:
        no = norm(o)
        if nq == no or SequenceMatcher(None, nq, no).ratio() >= SIMILAR:
            return o
    return ""


def fixed_questions() -> list[str]:
    return list(V.COMMON_FAQ_QUESTIONS) + [V.FAR_FAQ_Q]


def page_keys() -> list[tuple[str, str, int]]:
    """[(종류, call_faqs key, 개수)] — 빌더(build_site·build_gu·build_si)와 같은 key·개수."""
    regions = json.loads((ROOT / "data" / "regions.json").read_text(encoding="utf-8"))
    gu = json.loads((ROOT / "data" / "gu.json").read_text(encoding="utf-8"))
    si = json.loads((ROOT / "data" / "si.json").read_text(encoding="utf-8"))
    return ([("동", r["slug"], 3) for r in regions] + [("구", "gu:" + g["slug"], 4) for g in gu]
            + [("시", "si:" + s["sido"], 4) for s in si])


def picks(pool: list[tuple[str, str]], key: str, n: int) -> list[str]:
    old = V.CALL_FAQ
    V.CALL_FAQ = pool
    try:
        return [q for q, _ in V.call_faqs(key, n)]
    finally:
        V.CALL_FAQ = old


def cmd_show(args) -> None:
    data = load_pool()
    pool = [(x["q"], x["a"]) for x in data["items"]]
    keys = page_keys()
    if args.page:
        hit = [k for k in keys if k[1] == args.page]
        if not hit:
            sys.exit(f"그런 페이지 열쇠가 없음: {args.page} (동은 slug, 구는 gu:slug, 시는 si:시도 전체 이름)")
        for q in picks(pool, hit[0][1], hit[0][2]):
            print("- " + q)
        return
    used: dict[str, Counter] = {q: Counter() for q, _ in pool}
    for kind, key, n in keys:
        for q in picks(pool, key, n):
            used[q][kind] += 1
    print(f"FAQ 풀 {len(pool)}개 (마지막 갱신 {data.get('last_refresh', '?')}) — 붙는 페이지 수 동/구/시")
    for i, x in enumerate(data["items"], 1):
        c = used[x["q"]]
        pin = " [맨 앞 고정]" if x.get("pinned") else ""
        print(f"{i:>2}. {x['q']}{pin}  ({x.get('source_month', '?')}, {x.get('added', '?')} 추가) — {c['동']}/{c['구']}/{c['시']}")


def cmd_add(args) -> None:
    data = load_pool()
    new = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if isinstance(new, dict):
        new = [new]
    others = [x["q"] for x in data["items"]] + fixed_questions()
    problems, ok = [], []
    for x in new:
        q, a = (x.get("q") or "").strip(), (x.get("a") or "").strip()
        if not q or not a or not re.fullmatch(r"\d{4}-\d{2}", x.get("source_month") or ""):
            problems.append(f"'{q or '(질문 없음)'}': q·a·source_month(YYYY-MM) 가 다 있어야 함")
            continue
        same = overlap(q, others)
        if same:
            problems.append(f"'{q}': 이미 있는 질문과 겹침 → '{same}' (문구를 바꾸려면 그 항목을 고치세요)")
        problems += [f"'{q}': {p}" for p in text_problems(q, a)]
        ok.append({"q": q, "a": a, "source_month": x["source_month"], "added": today()})
        others.append(q)
    if problems:
        print("넣지 않음(하나라도 걸리면 전부 멈춤):")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    if args.dry_run:
        print(f"검사 통과: {len(ok)}개 (--dry-run 이라 넣지 않음)")
        return
    data["items"] += ok
    data["last_refresh"] = today()
    POOL.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"넣음: {len(ok)}개 → 풀 {len(data['items'])}개. 다음: python3 scripts/faq_pool.py assign → build_site.py")
    for x in ok:
        print("  + " + x["q"])


def cmd_assign(_args) -> None:
    data = load_pool()
    items = data["items"]
    problems = []
    if not items or not items[0].get("pinned") or sum(bool(x.get("pinned")) for x in items) != 1:
        problems.append("맨 앞 고정 항목(pinned)은 첫 항목 하나여야 함")
    seen: list[str] = []
    for x in items:
        for k in ("q", "a", "source_month", "added"):
            if not x.get(k):
                problems.append(f"'{x.get('q', '?')}': {k} 칸이 비었음")
        same = overlap(x["q"], seen + fixed_questions())
        if same:
            problems.append(f"'{x['q']}': '{same}' 와 겹침")
        problems += [f"'{x['q']}': {p}" for p in text_problems(x["q"], x["a"])]
        seen.append(x["q"])
    pool = [(x["q"], x["a"]) for x in items]
    try:
        old_raw = subprocess.run(["git", "show", "HEAD:data/faq_pool.json"], cwd=ROOT, capture_output=True, check=True).stdout
        old = [(x["q"], x["a"]) for x in json.loads(old_raw.decode("utf-8"))["items"]]
    except (subprocess.CalledProcessError, ValueError, KeyError):
        old = None
    keys = page_keys()
    if old is None:
        print("지난 커밋에 풀 파일이 없어 비교하지 않음")
    else:
        changed = Counter(kind for kind, key, n in keys
                          if [(q, dict(pool)[q]) for q in picks(pool, key, n)] != [(q, dict(old)[q]) for q in picks(old, key, n)])
        print(f"지난 커밋과 비교해 통화 FAQ 칸이 바뀌는 페이지: 동 {changed['동']} · 구 {changed['구']} · 시 {changed['시']}"
              " (빌드하면 이 페이지들의 최종 업데이트 날짜가 바뀜)")
    print(f"풀 {len(items)}개 검사: 문제 {len(problems)}건")
    for p in problems:
        print("  - " + p)
    if problems:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("--page")
    a = sub.add_parser("add")
    a.add_argument("file")
    a.add_argument("--dry-run", action="store_true")
    sub.add_parser("assign")
    args = ap.parse_args()
    {"show": cmd_show, "add": cmd_add, "assign": cmd_assign}[args.cmd](args)


if __name__ == "__main__":
    main()
