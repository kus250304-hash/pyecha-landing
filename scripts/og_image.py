"""
동·구·시 페이지 대표 이미지(og:image, 2026-10-10). 네이버·구글 검색 결과 썸네일용.

og/<파일 이름>.png 한 장: 1200×630, 빨간 바탕(#D62828) 흰 굵은 글씨 두 줄 — "{지역명} 폐차"(구는 "… 폐차장"), "1600-6011".
네이버가 가운데를 정사각형으로 자르기도 하므로 글자는 가운데 630×630 안에만 둔다. 지역명이 길면 글자를 줄인다.
글꼴은 저장소의 fonts/Pretendard-Bold.otf(SIL OFL)만 쓴다. 금액·요금 글자는 넣지 않는다.

같은 글자로 이미 만든 파일이 있으면 다시 쓰지 않는다(PNG 안의 og-text 값으로 비교).
그래서 다른 컴퓨터(글꼴 렌더링이 조금 다른 곳)에서 빌드해도 기존 이미지가 바뀌지 않는다.
"""
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "og"
FONT = ROOT / "fonts" / "Pretendard-Bold.otf"
W, H = 1200, 630
BG, FG = "#D62828", "#FFFFFF"
BOX = 630 - 2 * 60  # 가운데 정사각형 안쪽 여백 60px
VERSION = "1"  # 디자인을 바꾸면 올린다(모든 이미지를 다시 만든다)


def _fit(text: str, start: int):
    from PIL import ImageFont
    size = start
    while size > 20:
        font = ImageFont.truetype(str(FONT), size)
        l, t, r, b = font.getbbox(text)
        if r - l <= BOX:
            return font
        size -= 2
    return ImageFont.truetype(str(FONT), size)


def draw(line1: str, line2: str):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f1, f2 = _fit(line1, 120), _fit(line2, 104)
    b1, b2 = f1.getbbox(line1), f2.getbbox(line2)
    h1, h2 = b1[3] - b1[1], b2[3] - b2[1]
    gap = 40
    y = (H - (h1 + gap + h2)) // 2
    for text, font, (l, t, r, b), hh in ((line1, f1, b1, h1), (line2, f2, b2, h2)):
        d.text(((W - (r - l)) // 2 - l, y - t), text, font=font, fill=FG)
        y += hh + gap
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
