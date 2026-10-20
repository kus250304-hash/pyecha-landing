"""
월요일 아침 보고 끝에 붙이는 "지난주 숫자" 표(2026-10-20 병한님 요청, docs/weekly-check.md).

  python3 scripts/weekly_numbers.py           # 표를 출력만(매일 루틴은 이것만, 파일을 바꾸지 않음)
  python3 scripts/weekly_numbers.py --write   # docs/weekly-check.md 의 표(weekly-table 칸)를 이번 값으로 바꿔 씀(사람이 할 때)
  python3 scripts/weekly_numbers.py --date 2026-10-27   # 그날 아침 보고 기준으로 계산

주: "이번 주" = 보고 날 직전 월~일, "지난주" = 그 앞 월~일(한국 시간).
저장소에서 바로 셀 수 있는 숫자만 채운다. 하루하루 바뀌는 숫자는 그 주 마지막 날 23:59 무렵의 git 기록으로 센다.
  ② 문의가 온 페이지 종류: docs/index-requests.md "문의가 온 페이지" 칸에 그 주 날짜로 적힌 줄을 주소 종류(동/구/시도/주제/첫 화면)로 셈
  ④ 사이트맵별 주소 수(색인 비율의 분모): 그 주 마지막 날의 사이트맵 파일별 주소 수
  ⑦ 사례 붙은 구 페이지 수/전체: data/gu.json 의 구 중 그 구 사례(cases/index.json)가 1건 이상인 곳
GA4·구글 서치 콘솔·네이버 서치어드바이저·Ahrefs·Bing 숫자와 직접 검색 순위는 병한님이 캡처로 주는 칸이라 "캡처 필요"로 둔다.
목표·출처 칸은 docs/weekly-check.md 표에 적힌 것을 그대로 가져온다. 숫자를 지어내지 않는다.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DOC = ROOT / "docs" / "weekly-check.md"
START, END = "<!-- weekly-table:start -->", "<!-- weekly-table:end -->"
KST = timezone(timedelta(hours=9))
NEED = "캡처 필요"
ROWS = [  # (번호, 이름) — docs/weekly-check.md 표와 같은 순서
    ("①", "랜딩 문의 건수(전화 클릭+폼+문자, 유입별)"),
    ("②", "문의가 온 페이지 종류(동/구/시도/주제)"),
    ("③", "직접 검색 표본 10개 순위"),
    ("④", "구글 색인 수·비율(사이트맵별)"),
    ("⑤", "구글 노출·클릭·평균 순위(28일)"),
    ("⑥", "네이버 수집(일 평균)·노출·클릭"),
    ("⑦", "사례 붙은 구 페이지 수/전체"),
    ("⑧", "Ahrefs 건강 점수"),
    ("⑨", "Bing 색인 수"),
]


def git(*args: str) -> str:
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8").stdout


def rev_at(day: date) -> str:
    """그날 23:59:59(한국 시간)까지의 마지막 커밋."""
    return git("rev-list", "-1", f"--before={day.isoformat()} 23:59:59 +0900", "HEAD").strip()


def show(rev: str, path: str) -> str | None:
    out = subprocess.run(["git", "-c", "core.quotepath=false", "show", f"{rev}:{path}"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    return out.stdout if out.returncode == 0 else None


def weeks(report_day: date) -> tuple[tuple[date, date], tuple[date, date]]:
    """(지난주, 이번 주) 각각 (월, 일). 이번 주 = 보고 날 직전에 끝난 월~일."""
    end = report_day - timedelta(days=report_day.isoweekday())  # 직전 일요일
    this = (end - timedelta(days=6), end)
    return (this[0] - timedelta(days=7), this[0] - timedelta(days=1)), this


def sitemap_counts(rev: str) -> str:
    """그 커밋의 사이트맵 파일별 주소 수. 나누기 전(2026-10-20 이전)이면 한 파일을 종류별로 센다."""
    index = show(rev, "sitemap.xml")
    if not index:
        return "사이트맵 없음"
    locs = lambda text: re.findall(r"<loc>\s*(.*?)\s*</loc>", text or "")
    if "<sitemapindex" in index:
        parts = []
        for child in locs(index):
            name = child.rsplit("/", 1)[-1]
            parts.append((name.replace("sitemap-", "").replace(".xml", ""), len(locs(show(rev, name)))))
    else:
        kinds = {"core": 0, "cases": 0, "dong": 0}
        for u in locs(index):
            path = u.split("/", 3)[3] if u.count("/") >= 3 else ""
            kinds["cases" if path.startswith("cases/") else "dong" if path.startswith("pages/") else "core"] += 1
        parts = [(f"{k}(나누기 전)", v) for k, v in kinds.items()]
    total = sum(n for _, n in parts)
    return " · ".join(f"{k} {n:,}" for k, n in parts) + f" (합계 {total:,})"


def gu_with_cases(rev: str) -> str:
    """그 커밋의 구 페이지 중 그 구 사례가 1건 이상인 곳 / 전체."""
    from build_site import gu_slug
    gu = json.loads(show(rev, "data/gu.json") or "[]")
    cases = json.loads(show(rev, "cases/index.json") or "[]")
    have = {gu_slug(c["sido"], c["sigungu"]) for c in cases}
    n = sum(1 for g in gu if g["slug"] in have)
    return f"{n} / {len(gu)}" + (f" ({n / len(gu):.0%})" if gu else "")


KIND = (("pages/", "동"), ("gu/", "구"), ("si/", "시도"), ("guide/", "주제"))


def inquiries(span: tuple[date, date]) -> str:
    """docs/index-requests.md "문의가 온 페이지" 칸에서 그 주 날짜 줄을 페이지 종류별로 셈(적힌 것만)."""
    text = DOC.parent.joinpath("index-requests.md").read_text(encoding="utf-8")
    sec = next((p.split("\n", 1)[1] for p in text.split("\n## ")[1:] if p.startswith("문의가 온 페이지")), "")
    counts: dict[str, int] = {}
    for line in sec.splitlines():
        m = re.match(r"- (\d{4}-\d{2}-\d{2})", line)
        u = re.search(r"https://\S+?\.html|https://pyecha119\.com/(?=\s|$)", line)
        if not m or not u or not (span[0] <= date.fromisoformat(m.group(1)) <= span[1]):
            continue
        path = unquote(u.group(0)).split("/", 3)[3] if u.group(0).count("/") >= 3 else ""
        kind = next((k for p, k in KIND if path.startswith(p)), "첫 화면")
        counts[kind] = counts.get(kind, 0) + 1
    if not counts:
        return "기록 0건"
    return " · ".join(f"{k} {n}" for k, n in counts.items()) + " (기록된 문의 기준)"


def doc_rows() -> dict[str, list[str]]:
    """docs/weekly-check.md 표의 줄 {번호: [번호, 이름, 지난주, 이번 주, 목표, 출처]}."""
    text = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
    block = text.split(START, 1)[1].split(END, 1)[0] if START in text else ""
    rows = {}
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0] in {n for n, _ in ROWS}:
            rows[cells[0]] = cells
    return rows


def table(report_day: date) -> tuple[str, list[str]]:
    """(표 마크다운, 비어 있는(캡처 필요) 칸 이름 목록)."""
    last, this = weeks(report_day)
    rev_last, rev_this = rev_at(last[1]), rev_at(this[1])
    auto = {
        "②": (inquiries(last), inquiries(this)),
        "④": (f"{NEED} / 주소 {sitemap_counts(rev_last)}" if rev_last else NEED,
              f"{NEED} / 주소 {sitemap_counts(rev_this)}" if rev_this else NEED),
        "⑦": (gu_with_cases(rev_last) if rev_last else "기록 없음", gu_with_cases(rev_this) if rev_this else "기록 없음"),
    }
    old = doc_rows()
    lines = [f"주: 지난주 {last[0]:%m/%d}~{last[1]:%m/%d} · 이번 주 {this[0]:%m/%d}~{this[1]:%m/%d} (보고 {report_day.isoformat()})",
             "", "| 번호 | 숫자 이름 | 지난주 | 이번 주 | 목표 | 출처 |", "|---|---|---|---|---|---|"]
    missing = []
    for num, name in ROWS:
        prev, cur = auto.get(num, (NEED, NEED))
        if num == "②":  # 기록된 문의 수에 더해 GA4 유입별 숫자는 캡처
            prev, cur = f"{prev} / GA4 {NEED}", f"{cur} / GA4 {NEED}"
        if NEED in cur:
            missing.append(f"{num} {name}")
        goal, src = (old[num][4], old[num][5]) if num in old else ("", "")
        lines.append(f"| {num} | {name} | {prev} | {cur} | {goal} | {src} |")
    return "\n".join(lines), missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="보고 날(YYYY-MM-DD, 기본 오늘 한국 시간)")
    ap.add_argument("--write", action="store_true", help="docs/weekly-check.md 의 표를 이 값으로 바꿔 씀")
    args = ap.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(KST).date()
    md, missing = table(day)
    print(md)
    print("\n비어 있는 칸(캡처 필요): " + (", ".join(missing) if missing else "없음"))
    if args.write:
        text = DOC.read_text(encoding="utf-8")
        if START not in text or END not in text:
            raise SystemExit("docs/weekly-check.md 에 weekly-table 칸 표시가 없습니다")
        head, rest = text.split(START, 1)
        DOC.write_text(head + START + "\n" + md + "\n" + END + rest.split(END, 1)[1], encoding="utf-8")
        print("docs/weekly-check.md 표를 바꿔 씀")


if __name__ == "__main__":
    main()
