"""
조기폐차 칸(2026-11-12 병한님, 상자 공장-2a): data/early_scrap_notices.json 에 적힌 지자체 조기폐차 공고를
그 시·도의 구 페이지(gu/)·시·도 페이지(si/)에 "조기폐차 — ○○시 접수 안내" 칸으로, 조기폐차 안내 페이지 맨 위에
"지금 접수가 확인된 곳" 표로 넣는다. 지금은 서울 한 건.

규칙
- 공고 파일에 적힌 사실만 쓴다. 금액·"최대 얼마"는 쓰지 않고 공식 글 링크로 넘긴다. 수출 얘기는 넣지 않는다(조기폐차는 폐차만).
- "신청·성능검사·청구를 대신 해 드립니다"라고 쓰지 않는다. "대상인지, 신청 순서, 차값까지 전화로 같이 봐 드립니다"까지만.
- deadline 이 있으면 마감 다음 날(한국 시간)부터 빌드하는 페이지는 저절로 "접수 마감" 모양으로 바뀐다.
  매일 루틴의 build_site.py 가 그날 다시 그리고, 본문 해시가 바뀐 이 페이지들만 날짜가 바뀐다.
  `python scripts/early_scrap.py refresh` 는 마감 다음 날 이 페이지들만 바뀌었는지 확인하고 올리는 명령(아래 main).
- deadline 이 비면(공고를 직접 못 본 경우) 마감일 줄을 빼고 "지금 접수되는지는 … 에서 확인하세요"를 넣는다.

시험할 때 날짜 바꾸기: 환경 변수 EARLY_SCRAP_TODAY=2026-12-01
"""
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "early_scrap_notices.json"
KST = timezone(timedelta(hours=9))
GUIDE_FILE = "조기폐차-지원-안내.html"
BAN_RE = re.compile(r"보장|무조건|100%|1위|1등|최저가|최고가|최대|24시간|실시간\s*접수|수출|대신\s*해\s*드|\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩")

_CACHE: list[dict] | None = None


def notices() -> list[dict]:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    return _CACHE


def today() -> date:
    forced = os.environ.get("EARLY_SCRAP_TODAY")
    return date.fromisoformat(forced) if forced else datetime.now(KST).date()


def notice_for(sido: str) -> dict | None:
    return next((n for n in notices() if n["sido"] == sido), None)


def is_closed(n: dict) -> bool:
    return bool(n.get("deadline")) and today() > date.fromisoformat(n["deadline"])


def _contacts(n: dict) -> str:
    return " / ".join(f"{c['name']} {c['tel']}" if c["tel"] != "120" else "120 다산콜" for c in n["contacts"])


def faqs(n: dict) -> list[tuple[str, str]]:
    """FAQ 틀(구·시 페이지 FAQ 칸과 FAQPage 구조화 데이터)에 같이 넣는 3개. FAQ_ANSWER_RULE 를 지킨다."""
    agency = n["agency"]
    return [
        ("DPF가 달려 나온 4등급 경유차도 되나요?",
         f"네, {agency}는 2024년부터 DPF가 있든 없든 4등급 경유차를 대상에 넣었습니다. "
         "다만 나라 지원금으로 DPF를 나중에 단 차는 안 됩니다. 올해 조건은 공고에서 한 번 더 확인하세요."),
        ("확인서를 받았는데 언제까지 폐차해야 하나요?",
         f"받은 날부터 {n['claim_months']}개월 안입니다. 이 기간 안에 폐차를 마치고 보조금을 청구해야 합니다."),
        ("지원금을 받으면 차값은 못 받나요?",
         f"아니요, 지원금은 {agency}가 주고 차값은 폐차할 때 따로 받습니다."),
    ]


def _lines(n: dict, cfg: dict) -> list[str]:
    """칸 본문 줄(글자만, esc 전). 마감 뒤에는 맨 위가 바뀌고 신청 조건 줄이 빠진다."""
    agency, short = n["agency"], n["short"]
    g = n["grade_check"]
    closing = (f"조기폐차 대상인지, 신청 순서, 차값까지 전화 한 통으로 같이 봐 드립니다. 전화 {cfg['phone_display']}"
               + (f" / 문자 {cfg['text_reply_display']}" if cfg.get("text_reply_display") else "")
               + (f" ({cfg['reply_hours']})" if cfg.get("reply_hours") else ""))
    support = f"지원금은 {agency}가 주고, 차값은 폐차할 때 따로 받습니다."
    if is_closed(n):
        return [
            f"확인서를 받으셨다면 {n['claim_months']}개월 안에 폐차해야 합니다. 차값과 순서는 전화로 같이 봐 드립니다.",
            f"올해 {agency} 조기폐차 신청은 {n['deadline_text']}에 마감했습니다.",
            f"확인서를 받은 날부터 {n['claim_months']}개월 안에 폐차를 마치고 보조금을 청구해야 합니다. {support}",
            closing,
        ]
    out = [f"{short}에 등록된 배출가스 4등급 경유차와 5등급 차는 {agency} 조기폐차 지원을 신청할 수 있습니다."]
    if n.get("deadline"):
        out.append(f"신청 마감은 {n['deadline_text']}입니다. {n['early_close']}.")
    else:
        out.append(f"지금 접수되는지는 {_contacts(n)}에서 확인하세요.")
    if n.get("grade5_last_year"):
        out.append("5등급 차 지원은 올해가 마지막입니다.")
    out += [
        f"신청일 전 {n['hold_months']}개월 이상 이어서 가지고 있던 차여야 합니다.",
        f"내 차 등급은 {g['site_name']}({g['site']})이나 {g['tel']}에서 확인합니다.",
        f"{support} 확인서를 받으면 {n['claim_months']}개월 안에 폐차를 마치고 보조금을 청구해야 합니다.",
        closing,
    ]
    return out


def section_title(n: dict, area: str) -> str:
    if is_closed(n):
        return f"{area} 조기폐차 — {n['agency']} 접수 마감({n['deadline_text'].split('(')[0]})"
    return f"{area} 조기폐차 — {n['agency']} 접수 안내 (확인일 {n['checked_on']})"


def section_html(n: dict | None, area: str, cfg: dict, esc, tel_text) -> str:
    """구·시 페이지의 조기폐차 칸(지역 FAQ 위). 공고가 없는 시·도는 빈칸."""
    if not n:
        return ""
    from first_screen import sms_link
    items = []
    for line in _lines(n, cfg):
        h = tel_text(esc(line))
        if cfg.get("text_reply_display"):
            h = h.replace(esc(cfg["text_reply_display"]),
                          f'<a href="{esc(sms_link(cfg, area))}">{esc(cfg["text_reply_display"])}</a>', 1)
        items.append(f'<li style="margin-bottom:6px">{h}</li>')
    srcs = " · ".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["name"])}</a>'
                      for s in n["sources"])
    return (
        '  <section id="early-scrap">\n    <div class="wrap">\n'
        f'      <h2 class="sec-title display">{esc(section_title(n, area))}</h2>\n'
        f'      <p class="sec-sub">{esc(n["target"])} · 조기폐차는 폐차로만 진행합니다</p>\n'
        f'      <ul class="es-list" style="margin:14px 0 0;padding-left:20px;line-height:1.75;font-size:16px">{"".join(items)}</ul>\n'
        f'      <p class="note">문의: {esc(_contacts(n))}. 출처: {srcs}. '
        "공고는 바뀔 수 있으니 신청 전에 다시 확인하세요.</p>\n"
        "    </div>\n  </section>\n"
    )


def guide_table_html(esc) -> str:
    """조기폐차 안내 페이지 맨 위 "지금 접수가 확인된 곳" 표(마감 지난 곳은 "접수 마감"으로)."""
    if not notices():
        return ""
    from build_site import sido_link
    rows = []
    for n in notices():
        when = (f"{n['deadline_text'].split('(')[0]} 접수 마감" if is_closed(n)
                else f"{n['deadline_text']}까지 ({n['early_close']})" if n.get("deadline") else "접수 여부 확인 중")
        rows.append(f'<tr><th>{esc(n["short"])}</th><td>{esc(when)}</td><td>{esc(n["target_short"])}</td>'
                    f'<td>{esc(n["checked_on"])}</td><td><a href="{esc(sido_link(n["sido"]))}#gu">{esc(n["short"])} 구 페이지</a></td></tr>')
    open_any = any(not is_closed(n) for n in notices())
    return (
        '  <section id="early-now" style="background:#fff">\n    <div class="wrap">\n'
        f'      <h2 class="sec-title display">{"지금 접수가 확인된 곳" if open_any else "최근 접수 확인 기록"}</h2>\n'
        '      <p class="sec-sub">지자체 공고를 직접 열어 확인한 곳만 적었습니다</p>\n'
        '      <div class="table-wrap"><table class="guide-table"><thead><tr><th>지역</th><th>신청</th><th>대상</th><th>확인일</th><th>페이지</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>\n'
        '      <p class="note">다른 지역은 확인되는 대로 더합니다. 공고는 바뀔 수 있으니 신청 전에 다시 확인하세요.</p>\n'
        "    </div>\n  </section>\n"
    )


def problems() -> list[str]:
    """금지 표현 검사(check_pages 가 부름)."""
    import variants as V
    out = []
    cfg = json.loads((ROOT / "data" / "site_config.json").read_text(encoding="utf-8"))
    for n in notices():
        text = " ".join(_lines(n, cfg) + [x for qa in faqs(n) for x in qa] + [n["target"], n.get("early_close", "")])
        if m := BAN_RE.search(text):
            out.append(f"조기폐차 칸 {n['short']}: 금지 표현 '{m.group(0)}'")
        out += [f"조기폐차 칸 {n['short']}: FAQ '{q}' — {p}" for q, a in faqs(n) if (p := V.faq_answer_problem(q, a))]
        if not n.get("sources") or any(not s["url"].startswith("https://") for s in n["sources"]):
            out.append(f"조기폐차 칸 {n['short']}: 출처 주소 없음")
    return out


def pages() -> list[str]:
    """이 칸이 들어가는 페이지(저장소 기준 경로)."""
    from build_site import gu_file, load_json, GU_DATA
    from build_si import si_file
    sidos = {n["sido"] for n in notices()}
    out = [f"gu/{gu_file(g['sido'], g['sigungu'])}" for g in load_json(GU_DATA, default=[]) if g["sido"] in sidos]
    out += [f"si/{si_file(s)}" for s in sidos if (ROOT / "si" / si_file(s)).exists()]
    return out + [f"guide/{GUIDE_FILE}"]


MAX_CHANGED = 30
SIDE_FILES = ("sitemap.xml", "sitemap-core.xml", "rss.xml", "data/page_hashes.json")


def refresh() -> int:
    """마감 다음 날 한 번(Windows 작업 "폐차_조기폐차_마감", 2026-12-01 오전 0시 20분, 놓치면 켜질 때 바로):
    build_site.py 를 돌린 뒤 이 칸 페이지(pages()) 말고 같이 그려진 페이지는 되돌리고(그 페이지의 해시 기록도 HEAD 대로),
    사이트맵·rss 를 다시 만들어 이 칸 페이지 + 사이트맵·rss·해시만 커밋·push 한다. 30장을 넘거나 검사 오류면 모두 되돌리고 멈춘다.
    이미 바뀌어 있으면(매일 루틴이 먼저 그림) 아무것도 안 한다. 결과는 통화녹음백업\\_분석\\폐차_조기폐차_log.txt(작업이 남김)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    def git(*a):
        return subprocess.run(["git", "-c", "core.quotepath=false", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")

    def status() -> list[str]:
        return [l[3:].strip().strip('"') for l in git("status", "--porcelain", "-uall").stdout.splitlines()]

    if not any(is_closed(n) for n in notices()):
        print("아직 마감 전이라 할 일 없음")
        return 0
    if status():
        print("커밋 안 된 변경이 있어 멈춤")
        return 1
    git("pull", "--ff-only")
    if subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py")], cwd=ROOT).returncode != 0:
        git("checkout", "--", "."); git("clean", "-fdq")
        print("build_site.py 실패, 되돌림")
        return 1
    mine = set(pages())
    allowed = mine | set(SIDE_FILES) | {"sitemap-cases.xml", "sitemap-dong-1.xml", "sitemap-dong-2.xml"}
    others = [f for f in status() if f not in allowed]
    tracked = set(git("ls-files").stdout.splitlines())
    if others:
        back = [f for f in others if f in tracked]
        if back:
            git("checkout", "--", *back)
        for f in others:
            if f not in tracked:
                (ROOT / f).unlink(missing_ok=True)
        head = json.loads(git("show", "HEAD:data/page_hashes.json").stdout)
        hp = ROOT / "data" / "page_hashes.json"
        cur = json.loads(hp.read_text(encoding="utf-8"))
        for f in others:
            if f in head:
                cur[f] = head[f]
            else:
                cur.pop(f, None)
        hp.write_text(json.dumps(cur, ensure_ascii=False, indent=0), encoding="utf-8")
        from sitemap_lib import write_sitemaps
        write_sitemaps(ROOT)
        print(f"이 칸과 무관하게 같이 그려진 {len(others)}개는 되돌림(다음 매일 루틴이 그림)")
    changed = status()
    page_n = len([f for f in changed if f.endswith(".html")])
    if not page_n:
        git("checkout", "--", ".")
        print("바뀐 페이지 없음(이미 반영됨)")
        return 0
    if page_n > MAX_CHANGED or any(f not in allowed for f in changed):
        git("checkout", "--", "."); git("clean", "-fdq")
        print(f"멈춤: 바뀐 페이지 {page_n}장(30장 넘음) 또는 예상 밖 파일")
        return 1
    if subprocess.run([sys.executable, str(ROOT / "scripts" / "check_pages.py")], cwd=ROOT).returncode != 0:
        git("checkout", "--", ".")
        print("check_pages.py 오류, 되돌림")
        return 1
    git("add", *changed)
    git("commit", "-m", f"Early scrap section closed ({today().isoformat()}): {page_n} pages")
    r = git("push")
    print(f"반영: {page_n}장" + ("" if r.returncode == 0 else f" (push 실패: {r.stderr.strip()[:200]})"))
    return r.returncode


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        raise SystemExit(refresh())
    if len(sys.argv) > 1 and sys.argv[1] == "pages":
        print("\n".join(pages()))
        raise SystemExit(0)
    p = problems()
    print("\n".join(p) or f"조기폐차 공고 {len(notices())}건, 문제 없음")
    raise SystemExit(1 if p else 0)
