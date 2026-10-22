"""
동·구·시 페이지 대표 이미지(og:image). 네이버·구글 검색 결과 썸네일용.

og/<파일 이름>.png 한 장: 1200×630 (2026-10-10 4차 디자인)
- 바탕: 왼쪽 위 #E63946 → 오른쪽 아래 #9B1C1C 사선 그라데이션, 그 위 오른쪽 아래에 흰색 12% 세단 옆모습
  실루엣(코드로 그린 단순 도형, 가운데 정사각형 폭의 90%).
- 글자는 두 줄만: 흰 "{지역명} 폐차"(구는 "… 폐차장"), 노란(#FFD60A) 검정 외곽선 6px "1600-6011".
- 5차 B안(2026-10-10 확정)의 색·바탕(그라데이션·세단 실루엣)은 그대로 둔다.
- 6차(2026-10-16 병한님 결정): 네이버 모바일이 썸네일을 가운데 정사각형만 잘라 보여 주므로("릉시 폐차 / 00-60")
  글자를 모두 가운데 630×630 안에 세 줄로 놓는다: 1줄 흰 지역명, 2줄 흰 "폐차"(구는 "폐차장"), 3줄 노란 "1600-6011".
  "천안시 동남구"처럼 띄어쓰기가 있는 이름은 지역명을 두 줄로 나누고, 그래도 넓으면 글자를 줄인다.
  글자는 가운데 정사각형 안쪽 폭 TEXT_W(양옆 여백 포함)를 넘지 않고, 세로로 STRETCH 만큼 늘린다(B안처럼 굵고 길쭉하게).
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
SQ = 630                             # 자동차 실루엣 크기 기준(가운데 정사각형 한 변)
TEXT_W = SQ - 2 * 36                 # 글자 폭 최대 558px(가운데 정사각형 안, 양옆 36px)
TOP_C, BOTTOM_C = "#E63946", "#9B1C1C"
FG, PHONE, OUTLINE, STROKE = "#FFFFFF", "#FFD60A", "#000000", 6
NAME_H, NAME2_H = 210, 132          # 지역명 한 줄일 때 / 두 줄일 때 한 줄 최대 높이(px)
WORD_H, PHONE_H = 160, 118           # "폐차" 줄, 전화번호 줄 최대 높이(px)
STRETCH = 1.2                        # 글자를 세로로 늘리는 비율
GAP = 12
BASE_SIZE = 200                      # 이 크기로 그린 뒤 목표 칸으로 늘린다
CAR_ALPHA = round(255 * 0.12)
VERSION = "7"  # 디자인을 바꾸면 올린다(모든 이미지를 다시 만든다)


def _font(size: float):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONT), max(10, int(size)))


def _text_layer(text: str, fill: str, max_h: int, stroke: int = 0):
    """글자를 BASE_SIZE 로 그려 세로로 STRETCH 배 늘린 뒤, 폭 TEXT_W·높이 max_h 안에 들어가게 줄인 투명 그림."""
    from PIL import Image, ImageDraw
    f = _font(BASE_SIZE)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    im = Image.new("RGBA", (r - l, b - t), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((-l, -t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=OUTLINE)
    w, h = im.width, im.height * STRETCH
    k = min(TEXT_W / w, max_h / h)
    return im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)


def split_name(name: str) -> list[str]:
    """띄어쓰기가 있으면 두 줄로(글자 수가 가장 고르게 나뉘는 자리), 없으면 한 줄."""
    words = name.split()
    if len(words) < 2:
        return [name]
    cuts = [(abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))), i) for i in range(1, len(words))]
    i = min(cuts)[1]
    return [" ".join(words[:i]), " ".join(words[i:])]


def _gradient():
    """왼쪽 위 → 오른쪽 아래 사선 그라데이션(가로·세로 그라데이션의 평균)."""
    from PIL import Image
    v = Image.linear_gradient("L").resize((W, H))
    h = Image.linear_gradient("L").rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT).resize((W, H))
    mask = Image.blend(h, v, 0.5)
    return Image.composite(Image.new("RGB", (W, H), BOTTOM_C), Image.new("RGB", (W, H), TOP_C), mask)


# 세단 옆모습(왼쪽이 앞). 가로 0~1, 세로는 가로 길이 기준 비율
CAR_BODY = [(0.00, 0.255), (0.015, 0.20), (0.06, 0.175), (0.25, 0.155), (0.34, 0.075), (0.40, 0.05),
            (0.60, 0.05), (0.70, 0.085), (0.79, 0.15), (0.95, 0.165), (1.00, 0.20), (1.00, 0.255),
            (0.985, 0.29), (0.015, 0.29)]
CAR_WINDOWS = [[(0.32, 0.148), (0.375, 0.082), (0.41, 0.066), (0.495, 0.066), (0.495, 0.148)],
               [(0.515, 0.066), (0.59, 0.066), (0.665, 0.098), (0.735, 0.148), (0.515, 0.148)]]
CAR_WHEELS = (0.215, 0.79)


def _car_mask():
    from PIL import Image, ImageDraw
    cw = SQ * 0.9
    x0 = (W + SQ) / 2 - cw + 40          # 정사각형 오른쪽 아래로 치우치게
    y0 = H - 16 - cw * 0.375           # 바퀴 아래가 잘리지 않게
    pt = lambda x, y: (x0 + x * cw, y0 + y * cw)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.polygon([pt(*p) for p in CAR_BODY], fill=255)
    for w in CAR_WINDOWS:
        d.polygon([pt(*p) for p in w], fill=0)
    for wx in CAR_WHEELS:
        cx, cy = pt(wx, 0.29)
        for r, fill in ((0.098, 0), (0.08, 255), (0.03, 0)):  # 휠 아치 틈 → 바퀴 → 휠
            d.ellipse([cx - r * cw, cy - r * cw, cx + r * cw, cy + r * cw], fill=fill)
    return m.point(lambda v: v * CAR_ALPHA // 255)


def draw(name: str, word: str, phone: str):
    """1200×630, 글자는 모두 가운데 630×630 안: 지역명(1~2줄) / word / 전화번호."""
    from PIL import Image
    img = _gradient()
    img.paste(Image.new("RGB", (W, H), FG), (0, 0), _car_mask())
    lines = split_name(name)
    layers = [_text_layer(x, FG, NAME_H if len(lines) == 1 else NAME2_H) for x in lines]
    layers += [_text_layer(word, FG, WORD_H), _text_layer(phone, PHONE, PHONE_H, STROKE)]
    total = sum(a.height for a in layers) + GAP * (len(layers) - 1)
    y = (H - total) // 2
    for a in layers:
        img.paste(a, ((W - a.width) // 2, y), a)
        y += a.height + GAP
    return img


def ensure(stem: str, name: str, word: str, phone: str) -> bool:
    """og/<stem>.png 를 만든다. 같은 글자로 만든 파일이 이미 있으면 그대로 두고 False."""
    from PIL import Image, PngImagePlugin
    key = f"{VERSION}|{name}|{word}|{phone}"
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
    draw(name, word, phone).save(path, format="PNG", pnginfo=info, optimize=True)
    return True


def url(stem: str, base: str) -> str:
    """대표 이미지의 절대 주소(og:image·구조화 데이터 image 에 같이 쓴다). 끝의 ?v=VERSION 은 네이버 등이 옛 그림을
    캐시해 두는 것을 깨려고 붙인다(2026-10-22). 파일 이름은 그대로라 VERSION 을 올리면 주소만 저절로 새로 바뀐다."""
    return f"{base}/og/{quote(stem)}.png?v={VERSION}"


def parts(stem: str, name: str, base: str, phone_disp: str, suffix: str = "폐차") -> dict:
    """이미지를 만들고 템플릿 자리 OG_META(<head>)·OG_IMG_HTML(사례 칸 옆 작은 카드)를 돌려준다. name 은 지역명."""
    if ensure(stem, name, suffix, phone_disp):
        print(f"대표 이미지: og/{stem}.png")
    from html import escape
    rel = f"og/{quote(stem)}.png"
    meta = (f'<meta property="og:image" content="{url(stem, base)}">\n'
            f'<meta property="og:image:width" content="{W}">\n'
            f'<meta property="og:image:height" content="{H}">\n'
            f'<meta name="twitter:card" content="summary_large_image">')
    alt = escape(f"{name} 폐차 상담 {phone_disp}")
    # "폐차 사례" 칸 옆 작은 카드(모양은 동 페이지 템플릿 <style> 의 .cases-wrap·.og-img, 구·시 페이지도 같은 스타일)
    img = f'<figure class="og-img"><img src="../{rel}" alt="{alt}" width="{W}" height="{H}" loading="lazy"></figure>'
    return {"OG_META": meta, "OG_IMG_HTML": img}
