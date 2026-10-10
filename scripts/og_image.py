"""
동·구·시 페이지 대표 이미지(og:image). 네이버·구글 검색 결과 썸네일용.

og/<파일 이름>.png 한 장: 1200×630, 빨간 바탕(#D62828), 안쪽 40px 에 흰 테두리 선.
맨 위 작은 흰 글씨 띠 "폐차 상담 · 당일 접수", 가운데 흰 글씨 "{지역명} 폐차"(구는 "… 폐차장"),
그 아래 노란(#FFD60A) "1600-6011".
- 네이버가 가운데 정사각형으로 자르기도 하므로(2026-10-10 3차) 글자는 모두 가운데 630×630 안
  (좌우 여백 40px → 가로 550px)에만 둔다. 테두리 선만 가로 전체에 걸친다.
- 지역명은 그 폭에서 될 수 있는 대로 크게. 한 줄로 쓰면 너무 작아지면 낱말 사이에서 두 줄로 나눈다
  (예: "성남시 수정구 폐차장" → "성남시" / "수정구 폐차장"). 더 크게 쓸 수 있는 쪽을 고른다.
- 전화번호는 550px 폭 안에서 최대 크기(높이가 모자라면 지역명과 함께 줄인다).
글꼴은 저장소의 fonts/Pretendard-Black.otf(SIL OFL)만 쓴다. 금액·요금 글자는 넣지 않는다.

같은 글자로 이미 만든 파일이 있으면 다시 쓰지 않는다(PNG 안의 og-text 값으로 비교).
그래서 다른 컴퓨터(글꼴 렌더링이 조금 다른 곳)에서 빌드해도 기존 이미지가 바뀌지 않는다.
"""
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "og"
FONT = ROOT / "fonts" / "Pretendard-Black.otf"
W, H = 1200, 630
BG, FG, PHONE = "#D62828", "#FFFFFF", "#FFD60A"
INSET, LINE = 40, 4                  # 테두리 선: 가장자리에서 40px 안쪽, 두께 4px
BAND = "폐차 상담 · 당일 접수"
BOX_W = 630 - 2 * 40                 # 가운데 정사각형 안 글자 폭 550px
TOP, BOTTOM = 124, H - INSET - 30    # 띠 아래 ~ 테두리 위 글자 영역
MAX_REGION = 150                     # 짧은 지역명이 너무 커지지 않게
TWO_LINES_BELOW = 110                # 한 줄 크기가 이보다 작으면 두 줄을 검토
LINE_GAP, PHONE_GAP = 14, 34
VERSION = "3"  # 디자인을 바꾸면 올린다(모든 이미지를 다시 만든다)


def _font(size: float):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONT), max(10, int(size)))


def _width(text: str, size: float) -> int:
    l, t, r, b = _font(size).getbbox(text)
    return r - l


def _height(text: str, size: float) -> int:
    l, t, r, b = _font(size).getbbox(text)
    return b - t


def _fit(lines: list[str]) -> float:
    return min(MAX_REGION, min(100 * BOX_W / _width(x, 100) for x in lines))


def _layout(line1: str, line2: str) -> tuple[list[str], int, int]:
    """(지역명 줄들, 지역명 크기, 전화번호 크기)."""
    lines, s1 = [line1], _fit([line1])
    words = line1.split()
    if s1 < TWO_LINES_BELOW and len(words) > 1:
        for i in range(1, len(words)):  # 같은 크기면 앞쪽에서 나눈 것("성남시" / "수정구 폐차장")
            cand = [" ".join(words[:i]), " ".join(words[i:])]
            if _fit(cand) > s1 + 0.5:
                lines, s1 = cand, _fit(cand)
    s2 = 100 * BOX_W / _width(line2, 100)
    region_h = sum(_height(x, s1) for x in lines) + LINE_GAP * (len(lines) - 1)
    total = region_h + PHONE_GAP + _height(line2, s2)
    room = BOTTOM - TOP
    if total > room:  # 높이가 넘치면 둘 다 같은 비율로 줄인다
        gaps = LINE_GAP * (len(lines) - 1) + PHONE_GAP
        k = (room - gaps) / (total - gaps)
        s1, s2 = s1 * k, s2 * k
    return lines, int(s1), int(s2)


def draw(line1: str, line2: str):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([INSET, INSET, W - INSET - 1, H - INSET - 1], outline=FG, width=LINE)

    def center(text: str, font, y: int, fill: str) -> int:
        l, t, r, b = font.getbbox(text)
        d.text(((W - (r - l)) // 2 - l, y - t), text, font=font, fill=fill)
        return b - t

    center(BAND, _font(34), INSET + 34, FG)
    lines, s1, s2 = _layout(line1, line2)
    hs = [_height(x, s1) for x in lines]
    h2 = _height(line2, s2)
    total = sum(hs) + LINE_GAP * (len(lines) - 1) + PHONE_GAP + h2
    y = TOP + (BOTTOM - TOP - total) // 2
    f1 = _font(s1)
    for x, hh in zip(lines, hs):
        center(x, f1, y, FG)
        y += hh + LINE_GAP
    center(line2, _font(s2), y - LINE_GAP + PHONE_GAP, PHONE)
    return img


def ensure(stem: str, line1: str, line2: str) -> bool:
    """og/<stem>.png 를 만든다. 같은 글자로 만든 파일이 이미 있으면 그대로 두고 False."""
    from PIL import Image, PngImagePlugin
    key = f"{VERSION}|{line1}|{line2}"
    path = OUT / f"{stem}.png"
    if path.exists():
        try:
            with Image.open(path) as old:
                if old.text.get("og-text") == key and old.size == (W, H):
                    return False
        except OSError:
            pass
    OUT.mkdir(exist_ok=True)
    info = PngImagePlugin.PngInfo()
    info.add_text("og-text", key)
    draw(line1, line2).save(path, format="PNG", pnginfo=info, optimize=True)
    return True


def parts(stem: str, name: str, base: str, phone_disp: str, suffix: str = "폐차") -> dict:
    """이미지를 만들고 템플릿 자리 OG_META(<head>)·OG_IMG_HTML(본문 맨 위)를 돌려준다. name 은 지역명."""
    if ensure(stem, f"{name} {suffix}", phone_disp):
        print(f"대표 이미지: og/{stem}.png")
    from html import escape
    rel = f"og/{quote(stem)}.png"
    meta = (f'<meta property="og:image" content="{base}/{rel}">\n'
            f'<meta property="og:image:width" content="{W}">\n'
            f'<meta property="og:image:height" content="{H}">\n'
            f'<meta name="twitter:card" content="summary_large_image">')
    alt = escape(f"{name} 폐차 상담 {phone_disp}")
    # 모양은 동 페이지 템플릿 <style> 의 .og-img (구·시 페이지도 같은 스타일을 쓴다)
    img = f'<div class="og-img"><div class="wrap"><img src="../{rel}" alt="{alt}" width="{W}" height="{H}"></div></div>'
    return {"OG_META": meta, "OG_IMG_HTML": img}
