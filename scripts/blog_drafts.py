"""
블로그 지역 글 초안 도우미 (2026-11-20, docs/blog-draft-rules.md · docs/fable-2026-11-20/blog-landing.md).

  python scripts/blog_drafts.py next [--n 3]        # 오늘 쓸 대상(깊은 사례)과 재료
  python scripts/blog_drafts.py check <파일…>       # 초안 검사 — "오류 0건"이어야 올린다
  python scripts/blog_drafts.py stock               # 아직 안 나간 초안 수
  python scripts/blog_drafts.py skip <slug> "<이유>"  # 이 사례는 쓰지 않음(다시 고르지 않게)

무엇을 하나
- 끝난 실제 거래 하나 = 글 하나. 대상은 cases/index.json 의 깊은 사례 가운데 걱정이 적혀 있고, 사진이 1장 이상이고,
  그 시·군 구 페이지가 있고, 아직 초안이 없는 것. 새 거래(14일 안에 붙은 사례) 먼저, 그다음 "○○폐차장" 검색량이 큰 지역 순.
- 초안은 docs/blog-drafts/YYYY-MM-DD/N_지역.md (N 은 한 자리 숫자). 업무위키 `_도구/주간꾸러미.py` 가 토요일 밤에 이 형식을 읽어
  일요일 발행판에 넣는다. 그래서 check 는 꾸러미가 글을 빼는 까닭(사진 없음·다른 글과 같은 문장 4줄 연속·소제목 뼈대 같음·금지 낱말)도 미리 본다.
- 같은 지역은 안 나간 초안이 있거나 공개한 지 28일이 안 됐으면 고르지 않는다. 안 나간 초안이 STOCK_CAP 편이면 그날은 쓰지 않는다.
- 네이버 검색 API 는 쓰지 않는다. 공개 여부는 블로그 공개 목록(RSS)만 본다(못 읽으면 초안 날짜로 어림).
"""
import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_cases  # noqa: E402
import case_story  # noqa: E402
import check_pages  # noqa: E402
from build_site import gu_file  # noqa: E402

DRAFTS = ROOT / "docs" / "blog-drafts"
STATE = ROOT / "data" / "blog_drafts.json"
BLOG_ID = "abh77790"
KST = timezone(timedelta(hours=9))
STOCK_CAP = 20          # 안 나간 초안이 이만큼 쌓이면 새로 쓰지 않음(약 3주치, 2026-11-20 병한님 "많이 만들어 놓고 하루 한 편")
REGION_GAP = 28         # 같은 지역 다시 쓰기까지(일)
NEW_DAYS = 14           # 이 안에 붙은 사례는 "새 거래"로 먼저
CONTACT = "전화 1600-6011 / 문자 010-9926-7779"
METRO = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
         "대전광역시": "대전", "울산광역시": "울산", "광주광역시": "광주"}
FOLD_WORDS = ("고를", "절차", "조기폐차", "압류")   # 주간꾸러미 TOPICS: 이 낱말이 든 소제목이 3개면 2개로 접힘
AGE_SEX_RE = re.compile(r"할머니|할아버지|어르신|아주머니|아저씨|여성분|남성분|여자분|남자분|여자\s*손님|남자\s*손님|노인|고령|연세"
                        r"|[2-9]0대|사모님|사장님")
OUR_PHONES = {"16006011", "01099267779"}
PHONE_RE = re.compile(r"0\d{1,2}[-\s.]?\d{3,4}[-\s.]?\d{4}|1[5-8]\d{2}[-\s.]?\d{4}")
# 금액: "2. 원부"·"원래" 같은 낱말은 빼고 숫자+원만. "수출 시세와 비교" 같은 방향 표현은 막지 않는다
AMOUNT_RE = re.compile(r"\d[\d,]*\s*(?:만\s*원|천\s*원|억\s*원?|원)(?![가-힣])|₩|견적가|매입가|매입 가격|보상금\s*\d")
# 고객 정보: 차량번호·번지·동호수는 오류, 도로명 주소처럼 보이는 글자는 "볼 것"
PLATE_ADDR_RE = re.compile(r"(?<!\d)\d{2,3}\s?[가-힣]\s?\d{4}(?!\d|년)|\d+\s*번지|\d+\s*동\s*\d+\s*호")
ROAD_RE = re.compile(r"[가-힣\d]{2,}(?:로|길)\s?\d+(?:-\d+)?(?:번길)?(?!\d|-\d|\s*(?:층|년|개|대|시|분|일|주|달|건|번|장|명|km|킬로|가지|단계|곳|편|통|차례|줄))")
BAN_WORDS = ["최고가", "보장", "100%", "무조건", "0원", "법인", "보험 견인", "서류 없이", "말소 뒤 수출", "말소 후 수출",
             "말소하고 수출", "보험견인", "응원 이벤트", "응원이벤트"]   # 주간꾸러미 BAN·RISK·EXTRA_BAN 과 같은 글자
# 차령초과말소 차 나이 기준을 틀리게 적는 꼴(2026-11-24, 군산 초안이 "경차는 10년"으로 나갈 뻔함).
# 자동차등록령 제31조 제2항: 승용차 11년(경차도 승용차), 승합차 10년, 경형·소형 화물·특수차 10년, 중형·대형 화물·특수차 12년.
# "경형·소형 승합·화물차 10년"은 맞는 문구라 막지 않고, 차령초과말소를 말하는 글에서만 본다.
_AGE_TAIL = r"10년(?:이|을)?\s*(?:기준|넘|이상|이에요|이고|이며|·)"
AGE_RULE_RE = re.compile(r"(?:경차|승용차)(?:(?!11년)[^\n.?!]){0,14}" + _AGE_TAIL
                         + r"|경형(?!\s*[·ㆍ]\s*소형)(?!\s*및\s*소형)(?:(?!11년)[^\n.?!]){0,10}" + _AGE_TAIL)
PC_HEALTH = ROOT / "data" / "pc_health.json"
PC_BLOG_ITEM = "블로그 공개"   # scripts/pc_health.py 가 PC 에서 공개 목록을 읽어 적는 칸


def today() -> date:
    return datetime.now(KST).date()


def load(p: Path, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def load_state() -> dict:
    s = load(STATE, {}) or {}
    s.setdefault("skip", {})
    s.setdefault("dead_drafts", [])
    return s


def cases() -> list[dict]:
    c = load(ROOT / "cases" / "index.json", [])
    return c if isinstance(c, list) else c.get("cases", [])


def priority() -> dict:
    return {(e["sido"], e["sigungu"]): e for e in (load(ROOT / "data" / "priority_regions.json", {}) or {}).get("gu", [])}


def top_keyword(sido: str, sigungu: str) -> tuple[str, int]:
    """그 시·군·구에서 검색량이 가장 큰 '○○폐차장' 꼴과 그 검색량. 없으면 이름에서 시·군을 뗀 꼴, 0."""
    best = ("", 0)
    for kw in (priority().get((sido, sigungu)) or {}).get("keywords", []):
        m = re.match(r"(\S+?)폐차장\s+(\d+)$", kw)
        if m and "자동차" not in m.group(1) and int(m.group(2)) > best[1]:
            best = (m.group(1), int(m.group(2)))
    if best[0]:
        return best
    name = (sigungu.split()[0] if sigungu else sido)
    short = re.sub(r"(특별자치시|특별자치도|시|군)$", "", name)
    return (short if len(short) >= 2 else name, 0)


def prefix(sido: str, sigungu: str) -> str:
    """제목 맨 앞에 쓸 지역 이름(뒤에 ' 폐차장'을 붙여 씀). 서울·광역시의 구·군은 '서울 금천구'처럼."""
    name, _ = top_keyword(sido, sigungu)
    city = METRO.get(sido) or ("광주" if sido.startswith("전남광주") and sigungu.endswith("구") else "")
    if city and sigungu and " " not in sigungu:
        gu = sigungu if name in (city, "") or not sigungu.startswith(name) else (name if name.endswith(("구", "군")) else sigungu)
        return f"{city} {gu}"
    return name


def is_deep(c: dict) -> bool:
    return not c.get("thin")


def parse_draft(p: Path) -> dict:
    s = p.read_text(encoding="utf-8")
    head, sep, body = s.partition("==========")
    d = {"path": p, "rel": p.relative_to(ROOT).as_posix(), "head": head, "body": body, "has_sep": bool(sep)}
    m = re.search(r"^제목 후보 1:\s*(.+)$", head, re.M)
    d["title"] = m.group(1).strip() if m else ""
    m = re.search(r"^- 사례:\s*(\S+)", head, re.M) or re.search(r"사례:\s*(\S+)", head)
    d["slug"] = m.group(1).strip() if m else ""
    d["photos"] = dict(re.findall(r"사진(\d) = (cases/images/[^\s(]+\.jpg)", head))
    d["region"] = re.sub(r"^\d_", "", p.stem)
    try:
        d["date"] = date.fromisoformat(p.parent.name)
    except ValueError:
        d["date"] = None
    paras = [x.strip("\n") for x in re.split(r"\n\s*\n", body.strip())]
    d["paras"] = [[l.rstrip() for l in para.splitlines() if l.strip()] for para in paras if para.strip()]
    d["headings"] = [ls[0][2:].strip() for ls in d["paras"] if ls and ls[0].startswith("■ ")]
    d["tags"] = next((" ".join(ls) for ls in d["paras"] if ls and all(l.startswith("#") for l in ls)), "")
    lines = []
    for ls in d["paras"]:
        if ls and all(l.startswith("#") for l in ls):
            continue
        for l in ls:
            if re.fullmatch(r"\[사진 \d: .*\]", l):
                continue
            l = re.sub(r"^- ", "• ", l)
            l = re.sub(r"^\[인용구\]\s*", "", l)
            lines.append(l.strip())
    d["lines"] = lines
    d["cmp_lines"] = [l for l in lines if len(l) >= 8]          # 주간꾸러미 lines_of 와 같은 기준
    text = [l for l in lines if not re.match(r"^.+?: https?://\S+$", l) and not l.startswith("전화 1600-6011")]
    d["text"] = "\n".join(text)
    return d


def all_drafts() -> list[dict]:
    out = []
    for p in sorted(DRAFTS.glob("*/[0-9]_*.md")):
        try:
            out.append(parse_draft(p))
        except Exception as e:  # 못 읽는 파일 하나 때문에 멈추지 않는다
            print(f"(못 읽음: {p.name} — {e})", file=sys.stderr)
    return out


def norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", s or "")


def public_posts() -> dict | None:
    """블로그 공개 목록 {제목(글자만): 올린 날}. 못 읽으면 None."""
    try:
        x = urllib.request.urlopen(f"https://rss.blog.naver.com/{BLOG_ID}.xml", timeout=20).read()
        out = {}
        for i in ET.fromstring(x).findall("./channel/item"):
            out[norm(i.findtext("title"))] = parsedate_to_datetime(i.findtext("pubDate")).astimezone(KST).date()
        return out
    except Exception:
        return None


def published_on(d: dict, pub: dict | None) -> date | None:
    if pub is None:
        return None
    t = norm(d["title"])
    for k, v in pub.items():
        if t and (k == t or k.startswith(t[:24]) or t.startswith(k[:24])):
            return v
    return None


def stock_rows(pub: dict | None, state: dict) -> list[dict]:
    """아직 안 나간 초안. 공개 목록을 못 읽으면 최근 21일 초안만 안 나간 것으로 어림."""
    rows = []
    for d in all_drafts():
        if d["rel"] in state["dead_drafts"]:
            continue
        if pub is None:
            if d["date"] and (today() - d["date"]).days <= 21:
                rows.append(d)
        elif not published_on(d, pub):
            rows.append(d)
    return rows


def draft_key(d: dict) -> str:
    """'2026-11-20/1_포천' — pc_health.json 의 waiting 목록과 같은 꼴."""
    return f"{d['path'].parent.name}/{d['path'].stem}"


def pc_record(max_age_days: int = 3) -> dict | None:
    """PC 가 낮에 공개 목록을 읽어 적어 둔 블로그 칸(data/pc_health.json). 없거나 오래됐거나 PC 도 못 읽었으면 None."""
    try:
        data = json.loads(PC_HEALTH.read_text(encoding="utf-8"))
        it = data["items"][PC_BLOG_ITEM]
        written = datetime.fromisoformat(data["written"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if it.get("ok") is None or not isinstance(it.get("waiting"), list):
        return None
    if (datetime.now(KST) - written).days > max_age_days:
        return None
    return {**it, "written": written}


def stock_from_pc(rec: dict, state: dict) -> list[dict]:
    """PC 기록 기준으로 안 나간 초안: 그때 안 나가 있던 것 + 그 뒤에 새로 쓴 것."""
    waiting, day = set(rec["waiting"]), rec["written"].date()
    return [d for d in all_drafts() if d["rel"] not in state["dead_drafts"]
            and (draft_key(d) in waiting or (d["date"] and d["date"] > day))]


def region_of_draft(d: dict, by_slug: dict) -> str:
    c = by_slug.get(d["slug"])
    return prefix(c["sido"], c["sigungu"]) if c else d["region"]


def packet(c: dict) -> dict:
    st = c.get("story") or {}
    days = {k: st.get(k) for k in ("문의일", "인수일", "말소일") if st.get(k)}
    gus = load(ROOT / "data" / "gu.json", [])
    g = next((x for x in gus if (x["sido"], x["sigungu"]) == (c["sido"], c["sigungu"])), None)
    info = [{"label": r.get("label"), "value": r.get("value"), "source": r.get("source")}
            for r in (g or {}).get("public_info", []) if r.get("grade") == "opened"]
    topic_file, topic_label = case_story.similar_topic(c)
    base = load(ROOT / "data" / "site_config.json")["site_base_url"].rstrip("/")
    return {
        "사례": c["slug"], "거래일": c.get("date"), "지역": " ".join(x for x in (c["sido"], c["sigungu"], c.get("dong")) if x),
        "차": c.get("car"), "걱정": st.get("걱정"), "확인": st.get("확인"), "고른쪽": st.get("고른쪽"), "이유": st.get("이유"),
        "날짜": days, "끝한줄": st.get("끝한줄"), "상황": c.get("situation"), "처리": c.get("method"),
        "영상에서 한 말": (c.get("spoken") or "")[:300],
        "사진": [f"cases/images/{p}" for p in c.get("photos", [])][:5],
        "구 페이지 링크": f"{base}/gu/{gu_file(c['sido'], c['sigungu'])}?src=blog",
        "안내 페이지 링크": [topic_label, f"{base}/guide/{topic_file}?src=blog"],
        "그 구의 공공 정보(직접 연 것만)": info,
    }


def cmd_next(n: int) -> None:
    state = load_state()
    cs = cases()
    by_slug = {c["slug"]: c for c in cs}
    drafts = all_drafts()
    pub = public_posts()
    stock = stock_rows(pub, state)
    print(f"쌓인 초안(안 나감) {len(stock)}편 / 한도 {STOCK_CAP}편" + ("" if pub is not None else " — 공개 목록을 못 읽어 최근 21일 초안으로 어림"))
    if len(stock) >= STOCK_CAP:
        print("대상 0건: 한도가 차서 오늘은 쓰지 않습니다.")
        return
    drafted = {d["slug"] for d in drafts if d["slug"]}
    busy = {}   # 지역 → 까닭
    for d in drafts:
        if d["rel"] in state["dead_drafts"]:
            continue
        reg = region_of_draft(d, by_slug)
        on = published_on(d, pub)
        if on is None and (pub is not None or (d["date"] and (today() - d["date"]).days <= 42)):
            busy[reg] = "안 나간 초안 있음"
        elif on and (today() - on).days < REGION_GAP:
            busy[reg] = f"{on} 공개, {REGION_GAP}일 안 지남"
    gu_dir = ROOT / "gu"
    cands, why_not = [], {"깊지 않음": 0, "걱정 없음": 0, "사진 없음": 0, "구 페이지 없음": 0, "이미 초안·건너뜀": 0, "지역 쉬는 중": 0}
    no_photo = []
    for c in cs:
        st = c.get("story") or {}
        if not is_deep(c):
            why_not["깊지 않음"] += 1
        elif c["slug"] in drafted or c["slug"] in state["skip"]:
            why_not["이미 초안·건너뜀"] += 1
        elif not st.get("걱정"):
            why_not["걱정 없음"] += 1
        elif not c.get("photos"):
            why_not["사진 없음"] += 1
            no_photo.append(f"{c['sigungu'] or c['sido']} {c.get('car') or ''}".strip())
        elif not (gu_dir / gu_file(c["sido"], c["sigungu"])).exists():
            why_not["구 페이지 없음"] += 1
        elif prefix(c["sido"], c["sigungu"]) in busy:
            why_not["지역 쉬는 중"] += 1
        else:
            added = c.get("added") or c.get("date") or ""
            fresh = bool(added) and (today() - date.fromisoformat(added[:10])).days <= NEW_DAYS
            cands.append((0 if fresh else 1, "" if not fresh else "".join(chr(255 - ord(ch)) for ch in added),
                          -top_keyword(c["sido"], c["sigungu"])[1], c["slug"], c, fresh))
    cands.sort(key=lambda x: x[:4])
    room = STOCK_CAP - len(stock)
    folder = DRAFTS / today().isoformat()
    used_n = sorted(int(p.name[0]) for p in folder.glob("[0-9]_*.md")) if folder.exists() else []
    start = (used_n[-1] + 1) if used_n else 1
    picks, seen = [], set()
    for _, _, _, _, c, fresh in cands:
        reg = prefix(c["sido"], c["sigungu"])
        if reg in seen:
            continue
        seen.add(reg)
        picks.append((c, fresh, reg))
        if len(picks) >= min(n, room, 10 - start):
            break
    print(f"대상 {len(picks)}건 (쓸 수 있는 사례 {len(cands)}건 · 못 쓰는 까닭: " + ", ".join(f"{k} {v}" for k, v in why_not.items()) + ")")
    if no_photo:
        print("사진 부탁(사연은 깊은데 사진이 없어 글을 못 쓰는 사례): " + " · ".join(no_photo))
    recent = [d for d in sorted(drafts, key=lambda d: (d["date"] or date.min, d["rel"]))[-6:]]
    if recent:
        print("\n[최근 초안 6편 — 제목 꼴·첫 문장·소제목이 이것들과 달라야 함]")
        for d in recent:
            first = next((l for l in d["lines"] if len(l) >= 8), "")
            print(f"- {d['title']}\n  첫 문장: {first[:60]}\n  소제목: {' / '.join(d['headings'])}")
    for i, (c, fresh, reg) in enumerate(picks):
        fn = f"docs/blog-drafts/{today().isoformat()}/{start + i}_{reg.replace(' ', '')}.md"
        vol = top_keyword(c["sido"], c["sigungu"])[1]
        print(f"\n===== 대상 {i + 1}: {'새 거래' if fresh else '깊은 사례'} · 제목 맨 앞 \"{reg} 폐차장\" (한 달 검색 {vol or '적음'}) =====")
        print(f"쓸 파일: {fn}")
        print(json.dumps(packet(c), ensure_ascii=False, indent=1))
    if picks:
        print("\n쓴 뒤: python scripts/blog_drafts.py check <파일> → 오류 0건이어야 올립니다. 규칙: docs/blog-draft-rules.md")


def body_len(d: dict) -> int:
    return len(re.sub(r"\s", "", d["text"]))


def check_one(d: dict, others: list[dict], by_slug: dict) -> tuple[list[str], list[str]]:
    err, warn = [], []
    c = by_slug.get(d["slug"])
    if not d["has_sep"]:
        err.append("'==========' 구분선이 없음")
    if not d["title"]:
        err.append("'제목 후보 1:' 줄이 없음")
    if not d["slug"]:
        err.append("'- 사례: <slug>' 줄이 없음")
    elif not c:
        err.append(f"사례 {d['slug']} 가 cases/index.json 에 없음")
    elif not is_deep(c):
        err.append("깊은 사례가 아님(얇은 사례로는 쓰지 않음)")
    if not re.fullmatch(r"\d_[^_\s]+\.md", d["path"].name):
        err.append("파일 이름은 '한 자리 숫자_지역.md' (주간꾸러미가 이 꼴만 읽음)")
    if c:
        reg = prefix(c["sido"], c["sigungu"])
        head = f"{reg} 폐차장"
        if not d["title"].startswith(head):
            err.append(f"제목이 \"{head}\"로 시작해야 함")
        tag0 = "#" + reg.replace(" ", "") + "폐차장"
        tags = d["tags"].split()
        if not tags:
            err.append("맨 아래 태그 줄이 없음")
        else:
            if tags[0] != tag0:
                err.append(f"첫 태그는 {tag0}")
            if not 8 <= len(tags) <= 10:
                warn.append(f"태그 {len(tags)}개(8~10개 권함)")
        short = reg.split()[-1]
        short = re.sub(r"(시|군|구)$", "", short) if len(short) > 2 else short
        cnt = d["text"].count(short)
        if cnt < 3:
            warn.append(f"본문에 지역 이름 '{short}'이 {cnt}번(3번은 넘게)")
        elif cnt > 12:
            warn.append(f"본문에 지역 이름 '{short}'이 {cnt}번 — 되풀이가 많음(12번 안쪽)")
        # 사례 페이지 문장을 그대로 옮기지 않기
        st = c.get("story") or {}
        src = [st.get("걱정"), st.get("이유"), st.get("끝한줄"), c.get("situation"), c.get("method"), c.get("summary")] + list(st.get("확인") or [])
        flat = re.sub(r"\s+", " ", d["text"])
        for s in src:
            for sent in re.split(r"(?<=[.?!])\s+", (s or "").strip()):
                sent = sent.strip()
                if len(sent) >= 20 and sent in flat:
                    err.append(f"사례 페이지 문장을 그대로 옮김: \"{sent[:30]}…\" (블로그 말투로 다시 쓰기)")
    if len(d["title"]) > 50:
        warn.append(f"제목 {len(d['title'])}자(50자 안쪽 권함)")
    # 사진
    if not d["photos"]:
        err.append("사진이 없음(주간꾸러미가 '사진 없음'으로 뺌)")
    marks = re.findall(r"^\[사진 (\d): .+\]$", d["body"], re.M)
    for k, rel in d["photos"].items():
        if not (ROOT / rel).exists():
            err.append(f"사진{k} 파일이 없음: {rel}")
        if c and Path(rel).name not in c.get("photos", []):
            err.append(f"사진{k} 는 이 사례의 사진이 아님: {rel}")
        if k not in marks:
            err.append(f"본문에 [사진 {k}: 설명] 줄이 없음")
    for k in marks:
        if k not in d["photos"]:
            err.append(f"[사진 {k}] 에 맞는 '사진{k} = cases/images/…' 줄이 머리말에 없음")
    for ls in d["paras"]:
        if ls and ls[0].startswith("[인용구]") and len(ls) > 1:
            err.append("[인용구] 는 한 줄짜리 문단으로(뒤 줄은 꾸러미가 버림)")
    # 소제목
    hs = d["headings"]
    if not 2 <= len(hs) <= 5:
        err.append(f"소제목(■) {len(hs)}개 — 2~5개")
    if sum(any(w in h for w in FOLD_WORDS) for h in hs) >= 3:
        err.append("'고를·절차·조기폐차·압류'가 든 소제목이 3개 이상 — 꾸러미가 2개로 접어 버림(2개까지)")
    # 링크·연락
    links = [re.match(r"^(.+?): (https?://\S+)$", l) for l in d["lines"]]
    links = [(m.group(1), m.group(2)) for m in links if m]
    gu_links = [u for _, u in links if "/gu/" in u]
    if not gu_links:
        err.append("그 지역 구 페이지 링크 줄('○○ 폐차 안내: https://pyecha119.com/gu/…?src=blog')이 없음")
    for _, u in links:
        if "pyecha119.com/" not in u:
            err.append(f"우리 사이트 밖 링크: {u}")
            continue
        if "src=blog" not in u:
            err.append(f"링크에 ?src=blog 가 없음: {u}")
        rel = unquote(u.split("pyecha119.com/", 1)[1].split("?")[0])
        if rel and not (ROOT / rel).exists():
            err.append(f"없는 페이지로 가는 링크: {rel}")
    if CONTACT not in d["lines"]:
        err.append(f"연락 줄이 없음: \"{CONTACT}\" (한 줄 그대로)")
    # 금지 표현
    txt = d["title"] + "\n" + d["text"] + "\n" + d["tags"]
    for name, rx in (("금액", AMOUNT_RE), ("결과 약속", build_cases.PROMISE_RE), ("최고가·1등 류", check_pages.PAGE_BAN_RE),
                     ("견인비는 '견인비는 따로 없어요'·'견인비 따로 없음' 두 꼴만", check_pages.TOW_BAN_RE),
                     ("협력업체·출장 방문 류", check_pages.BODY_BAN_RE),
                     ("매매", case_story.SALE_RE), ("보험 견인", case_story.INSURANCE_TOW_RE), ("개인 상담 사정(법인·서류 없이 등)", case_story.PRIVATE_RE),
                     ("차량번호·번지·동호수", PLATE_ADDR_RE), ("나이·성별", AGE_SEX_RE)):
        m = rx.search(txt)
        if m:
            err.append(f"금지 표현({name}): \"{m.group(0)}\"")
    m = ROAD_RE.search(txt)
    if m:
        warn.append(f"주소처럼 보이는 글자: \"{m.group(0)}\" (도로명·번지는 쓰지 않음)")
    for w in BAN_WORDS:
        if w in txt:
            err.append(f"금지 낱말: \"{w}\" (주간꾸러미가 뺌)")
    if "차령초과" in txt and (m := AGE_RULE_RE.search(txt)):
        err.append(f"차령초과말소 기준을 틀리게 적음: \"{m.group(0)}\" — 승용차는 경차도 11년, 10년은 승합차와 경형·소형 화물차"
                   "(docs/blog-draft-rules.md 5절)")
    for m in PHONE_RE.finditer(txt):
        if re.sub(r"\D", "", m.group(0)) not in OUR_PHONES:
            err.append(f"우리 번호가 아닌 전화번호: {m.group(0)}")
    m = build_cases.EXPORT_CLAIM_RE.search(txt)
    if m:
        warn.append(f"수출 단정처럼 읽힐 수 있음: \"{m.group(0)}\" — 이 차 얘기면 '수출 쪽도 알아봤지만'처럼, 일반 규칙(압류 있는 차)이면 그대로")
    m = case_story.OVERCLAIM_RE.search(txt)
    if m:
        warn.append(f"넓게 단정하는 말: \"{m.group(0)}\"")
    n = body_len(d)
    if n < 900:
        err.append(f"본문 {n}자 — 너무 짧음(공백 빼고 1,100~2,400자)")
    elif not 1100 <= n <= 2400:
        warn.append(f"본문 {n}자(공백 빼고 1,100~2,400자 권함)")
    # 다른 초안과 겹침 (주간꾸러미 shared_run·skeleton 과 같은 기준)
    la = d["cmp_lines"]
    skel = tuple(re.sub(r"[가-힣]+(시|군|구)?\s*폐차장", "○○폐차장", h) for h in hs)
    first = next((l for l in d["lines"] if len(l) >= 8), "")
    for o in others:
        if o["path"] == d["path"]:
            continue
        lb = o["cmp_lines"]
        sb = {tuple(lb[i:i + 4]) for i in range(len(lb) - 3)}
        run = next((la[i:i + 4] for i in range(len(la) - 3) if tuple(la[i:i + 4]) in sb), None)
        if run:
            err.append(f"{o['rel']} 와 같은 문장이 4줄 연속: \"{run[0][:24]}…\" (꾸러미가 한쪽을 뺌)")
        oskel = tuple(re.sub(r"[가-힣]+(시|군|구)?\s*폐차장", "○○폐차장", h) for h in o["headings"])
        if skel and skel == oskel:
            err.append(f"{o['rel']} 와 소제목 뼈대가 같음")
        ofirst = next((l for l in o["lines"] if len(l) >= 8), "")
        if first and first == ofirst:
            err.append(f"{o['rel']} 와 첫 문장이 같음")
    return err, warn


def cmd_check(files: list[str]) -> int:
    by_slug = {c["slug"]: c for c in cases()}
    others = all_drafts()
    total = 0
    for f in files:
        p = Path(f)
        p = p if p.is_absolute() else (ROOT / f)
        if not p.exists():
            print(f"{f}: 파일이 없음")
            total += 1
            continue
        d = parse_draft(p.resolve())
        err, warn = check_one(d, others, by_slug)
        total += len(err)
        print(f"{d['rel']}: 오류 {len(err)}건 · 볼 것 {len(warn)}건 · 본문 {body_len(d)}자 · 소제목 {len(d['headings'])} · 사진 {len(d['photos'])}")
        for e in err:
            print(f"  오류: {e}")
        for w in warn:
            print(f"  볼 것: {w}")
    print(f"오류 {total}건")
    return 1 if total else 0


def cmd_stock() -> None:
    state = load_state()
    pub = public_posts()
    rec = pc_record() if pub is None else None
    if rec:   # 이 컴퓨터는 공개 목록을 못 읽지만 PC 가 낮에 읽어 둔 기록이 있음(클라우드 세션·아침 루틴)
        rows = stock_from_pc(rec, state)
        w = rec["written"]
        note = (f" — PC 기록({w.month}/{w.day} {w:%H:%M}) 기준 · 최근 7일 공개 {rec.get('count_7d', '?')}편"
                f" · 마지막 공개 {rec.get('last') or '없음'} (예약만 걸린 글은 '안 나감'에 들어 있음)")
    else:
        rows = stock_rows(pub, state)
        note = "" if pub is not None else " — 공개 목록을 못 읽어 최근 21일 초안으로 어림(이미 나간 글이 섞여 있을 수 있음)"
    print(f"쌓인 초안(안 나감) {len(rows)}편 / 한도 {STOCK_CAP}편" + note)
    for d in rows:
        print(f"- {d['rel']} · {d['title']}")


def cmd_skip(slug: str, reason: str) -> None:
    state = load_state()
    state["skip"][slug] = f"{today().isoformat()} {reason}"
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"건너뜀으로 적음: {slug} — {reason}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("next"); a.add_argument("--n", type=int, default=3)
    a = sub.add_parser("check"); a.add_argument("files", nargs="+")
    sub.add_parser("stock")
    a = sub.add_parser("skip"); a.add_argument("slug"); a.add_argument("reason")
    args = ap.parse_args()
    if args.cmd == "next":
        cmd_next(args.n)
    elif args.cmd == "check":
        sys.exit(cmd_check(args.files))
    elif args.cmd == "stock":
        cmd_stock()
    else:
        cmd_skip(args.slug, args.reason)


if __name__ == "__main__":
    main()
