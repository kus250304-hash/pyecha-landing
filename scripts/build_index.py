"""
index.html의 지역 목록을 data/regions.json 기준으로 다시 생성한다.

regions.json 이 이미 지역별 sido/sigungu/dong을 갖고 있으므로 페이지 HTML을
스크래핑하지 않고 직접 읽는다(템플릿의 title/badge 형식이 바뀌어도 영향받지 않음).
index.html의 지역 목록 블록과 헤더의 지역 수만 교체하고 나머지는 그대로 둔다.

배치 생성 스크립트나 build_site.py를 실행한 뒤 이 스크립트를 실행하면 index.html이 최신 상태가 된다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"
REGIONS_PATH = ROOT / "data" / "regions.json"
INDEX_PATH = ROOT / "index.html"

SIDO_ORDER = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]

GROUPS_RE = re.compile(r'(?<=</div>\n\n)(      <div class="region-group">.*</div>\n)(?=</main>)', re.DOTALL)
COUNT_RE = re.compile(r"(지역별 상담 페이지 \(현재 )\d+(개 지역\))")


def collect_regions() -> dict[str, list[tuple[str, str]]]:
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    existing = {p.stem for p in PAGES_DIR.glob("*.html")}

    by_sido: dict[str, list[tuple[str, str]]] = {}
    for r in regions:
        if r["slug"] not in existing:
            continue  # 아직 렌더링되지 않은 지역은 목록에서 제외
        full_name = " ".join(x for x in (r["sido"], r["sigungu"], r["dong"]) if x)
        by_sido.setdefault(r["sido"], []).append((full_name, f"{r['slug']}.html"))

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
