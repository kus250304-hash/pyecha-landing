"""
동·구·시 페이지 대표 이미지(og:image). 네이버·구글 검색 결과 썸네일용.

og/<파일 이름>.png 한 장: 1200×630, 빨간 바탕(#D62828), 안쪽 40px 에 흰 테두리 선.
맨 위 작은 흰 글씨 띠 "폐차 상담 · 당일 접수", 가운데 흰 글씨 "{지역명} 폐차"(구는 "… 폐차장"),
그 아래 노란(#FFD60A) "1600-6011".
- 지역명은 가로폭의 80%(960px)를 채운다(2026-10-10 2차). 높이가 모자라면 함께 줄인다.
- 전화번호는 지역명보다 10% 큰 글자로 쓰되 테두리 안(가로 1000px)에 들어가게 줄인다.
  그래서 "서울 폐차"처럼 짧은 지역명은 전화번호 글자 크기가 지역명보다 작아진다(가로폭은 전화번호가 더 넓음).
- 지역명이 가로를 채우므로 네이버가 가운데 정사각형으로 자르면 글자 양끝이 잘릴 수 있다.
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
REGION_W = int(W * 0.8)              # 지역명 가로 목표 960px
PHONE_MAX_W = W - 2 * INSET - 120    # 전화번호 최대 가로 1000px
TOP, BOTTOM = 128, H - INSET - 36    # 띠 아래 ~ 테두리 위 글자 영역
VERSION = "2"  # 디자인을 바꾸면 올린다(모든 이미지를 다시 만든다)


def _font(size: float):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONT), max(10, int(size)))


def _width(text: str, size: float) -> int:
    l, t, r, b = _font(size).getbbox(text)
    return r - l


def _height(text: str, size: float) -> int:
    l, t, r, b = _font(size).getbbox(text)
    return b - t


def _sizes(line1: str, line2: str) -> tuple[int, int]:
    s1 = 100 * REGION_W / _width(line1, 100)
    s2 = min(s1 * 1.1, 100 * PHONE_MAX_W / _width(line2, 100))
    gap = 34
    total = _height(line1, s1) + gap + _height(line2, s2)
    if total > BOTTOM - TOP:  # 높이가 넘치면 둘 다 같은 비율로 줄인다
        k = (BOTTOM - TOP - gap) / (total - gap)
        s1, s2 = s1 * k, s2 * k
    return int(s1), int(s2)


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
    s1, s2 = _sizes(line1, line2)
    f1, f2 = _font(s1), _font(s2)
    gap = 34
    h1, h2 = _height(line1, s1), _height(line2, s2)
    y = TOP + (BOTTOM - TOP - (h1 + gap + h2)) // 2
    center(line1, f1, y, FG)
    center(line2, f2, y + h1 + gap, PHONE)
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
