"""
기존에 생성된 지역 페이지들의 "정직한 서비스 안내" 박스를 완화하는 마이그레이션 스크립트.

- 서비스 소개 섹션의 눈에 띄는 초록색 강조 박스(notice-box)를 제거한다.
- 대신 FAQ 섹션과 푸터 사이에 작은 회색 글씨로 같은 취지의 문구를 자연스럽게 배치한다.
- 문구도 "직접 운영하지 않으며"처럼 단정적으로 부정하는 대신
  "협력업체 네트워크와 함께합니다"처럼 부드럽게 바꾼다.
- 내용을 완전히 삭제하지는 않는다(법적으로 필요한 고지이므로).

templates/region-landing-template.html 은 이미 수동으로 반영했으므로 건드리지 않는다.
이 스크립트는 pages/*.html 처럼 이미 값이 채워진 정적 HTML 파일에만 적용한다.
"""
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = ROOT / "pages"

OLD_NOTICE_RE = re.compile(
    r'\n      <div class="notice-box">\n'
    r'        <strong>정직한 서비스 안내</strong><br>\n'
    r'        저희는 폐차장을 직접 운영하지 않으며, 전국 폐차 협력업체 네트워크와 연계되어\n'
    r'        상담과 연결을 도와드리는 서비스입니다\. 차량 상태와 조건에 따라 폐차와 수출\n'
    r'        비교매입 중 더 적합한 방법을 안내해 드립니다\.\n'
    r'      </div>\n'
)

FINE_PRINT_HTML = (
    '\n<div class="fine-print">\n'
    '  <div class="container">\n'
    '    <p style="color:#6b7280;font-size:12px;margin:0;line-height:1.6;">'
    '본 서비스는 전국 폐차 협력업체 네트워크와 함께합니다. 차량 상태와 조건에 따라 폐차와 수출 '
    '비교매입 중 더 적합한 방법을 안내해 드립니다.</p>\n'
    '  </div>\n'
    '</div>\n'
)

MAIN_FOOTER_RE = re.compile(r'\n</main>\n\n<footer>')


def migrate(text: str) -> tuple[str, bool, bool]:
    new_text, n_removed = OLD_NOTICE_RE.subn("\n", text)
    new_text, n_inserted = MAIN_FOOTER_RE.subn(
        f"\n</main>\n{FINE_PRINT_HTML}\n<footer>", new_text, count=1
    )
    return new_text, n_removed == 1, n_inserted == 1


def main() -> None:
    files = sorted(glob.glob(str(PAGES_DIR / "*.html")))
    ok, missing_notice, missing_anchor = 0, [], []

    for path_str in files:
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")
        new_text, removed_ok, inserted_ok = migrate(text)
        if not removed_ok:
            missing_notice.append(path.name)
        if not inserted_ok:
            missing_anchor.append(path.name)
        if removed_ok and inserted_ok:
            path.write_text(new_text, encoding="utf-8")
            ok += 1

    print(f"총 {len(files)}개 파일 중 {ok}개 변환 완료")
    if missing_notice:
        print("notice-box를 찾지 못한 파일:", missing_notice)
    if missing_anchor:
        print("</main><footer> 위치를 찾지 못한 파일:", missing_anchor)


if __name__ == "__main__":
    main()
