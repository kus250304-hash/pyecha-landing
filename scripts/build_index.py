"""
index.html의 지역 목록을 pages/ 디렉터리 기준으로 다시 생성한다.

각 페이지의 <title>에서 "{시도} {시군구} {동} 폐차 비교매입 상담" 형태의 지역명을
읽어 시도별로 모아, index.html의 지역 목록 블록과 헤더의 지역 수만 교체한다.
스타일이나 안내 문구 등 나머지 내용은 그대로 둔다.

배치 생성 스크립트를 실행한 뒤 이 스크립트를 실행하면 index.html이 최신 상태가 된다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"
INDEX_PATH = ROOT / "index.html"

SIDO_ORDER = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]

TITLE_RE = re.compile(r"<title>(.+?) 폐차 비교매입 상담</title>")
GROUPS_RE = re.compile(r'(?<=</div>\n\n)(      <div class="region-group">.*</div>\n)(?=</main>)', re.DOTALL)
COUNT_RE = re.compile(r"(지역별 상담 페이지 \(현재 )\d+(개 지역\))")


def collect_regions() -> dict[str, list[tuple[str, str]]]:
    by_sido: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(PAGES_DIR.glob("*.html")):
        match = TITLE_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            raise ValueError(f"지역명을 찾을 수 없습니다: {path.name}")
        full_name = match.group(1)
        sido = full_name.split()[0]
        by_sido.setdefault(sido, []).append((full_name, path.name))

    unknown = set(by_sido) - set(SIDO_ORDER)
    if unknown:
        raise ValueError(f"SIDO_ORDER에 없는 시도: {sorted(unknown)}")
    return by_sido


def render_groups(by_sido: dict[str, list[tuple[str, str]]]) -> str:
    blocks = []
    for sido in SIDO_ORDER:
        entries = sorted(by_sido.get(sido, []))
        if not entries:
            continue
        items = "\n".join(
            f'        <li><a href="pages/{file_name}">{full_name}</a></li>'
            for full_name, file_name in entries
        )
        blocks.append(
            '      <div class="region-group">\n'
            f'        <h2>{sido} <span class="count">({len(entries)})</span></h2>\n'
            "        <ul>\n"
            f"{items}\n"
            "        </ul>\n"
            "      </div>\n"
        )
    return "".join(blocks)


def main() -> None:
    by_sido = collect_regions()
    total = sum(len(v) for v in by_sido.values())

    text = INDEX_PATH.read_text(encoding="utf-8")
    text, n_groups = GROUPS_RE.subn(lambda _: render_groups(by_sido), text, count=1)
    if n_groups != 1:
        raise ValueError("index.html에서 지역 목록 블록을 찾지 못했습니다")
    text, n_count = COUNT_RE.subn(rf"\g<1>{total}\g<2>", text, count=1)
    if n_count != 1:
        raise ValueError("index.html에서 지역 수 문구를 찾지 못했습니다")

    INDEX_PATH.write_text(text, encoding="utf-8")
    print(f"index.html 갱신 완료: 총 {total}개 지역, 시도 {len(by_sido)}개")


if __name__ == "__main__":
    main()
