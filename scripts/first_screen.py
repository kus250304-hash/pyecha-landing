"""
첫 화면(2026-10-13): 동·구·시 페이지와 첫 화면 홈(index.html)이 같이 쓰는 맨 위 한 화면과,
그 바로 아래 "왜 비교해 드리나" 한 칸.

휴대폰 한 화면(390px) 안에 ①~⑥이 다 들어가게 한다.
  ① 길 안내(시›구›동) + 최종 업데이트 (작게 한 줄)
  ② 한 문장 H1: "{지역명} 폐차, 차 번호만 주시면 폐차·수출 바로 비교해서 연락드립니다"
  ③ 전화 버튼(폼보다 위, 높이 56px) + "급하시면 전화가 가장 빠릅니다"
  ④ 견적 폼 2칸(차량번호·연락처). 연식·차종 칸은 맨 아래 두 번째 폼에만 있다
  ⑤ 버튼 하나 "차 번호로 비교 견적 받기 — 폐차값·수출값 둘 다 (1+1)"
  ⑥ 문자 한 줄(카카오 채널 주소가 있으면 "· 카톡 상담")
첫 화면에는 압류·저당·원부 같은 말을 쓰지 않는다(check_pages.py 가 확인). 예전 첫 화면의 뱃지·1+1 줄·핵심 문장·
안내 줄·비교 안내·신뢰 줄은 지우지 않고 why_block_html 로 폼 바로 아래에 옮긴다.
모양(CSS)은 templates/region-landing-v2.html 의 /* hero-v3:start */ ~ /* hero-v3:end */ 칸.
"""
from html import escape
from urllib.parse import quote


def esc(s: str) -> str:
    return escape(s, quote=True)


HERO_H1_TAIL = "폐차, 차 번호만 주시면 폐차·수출 바로 비교해서 연락드립니다"
MINI_TITLE = "전화가 부담스러우면 차 번호만 남겨 주세요"
CONSENT_HTML = '남겨주신 정보는 견적 상담 연락에만 쓰며, 문의 시 <a href="{prefix}privacy.html">개인정보처리방침</a>에 동의한 것으로 봅니다.'


def sms_link(cfg: dict, region: str) -> str:
    """문자 버튼 주소: 휴대폰에서 누르면 문자 창이 열리고 본문이 미리 채워진다.
    "?&body=" 는 아이폰(&body)·안드로이드(?body) 둘 다 읽는 형식. 손님은 끝에 차번호만 적으면 된다."""
    body = f"{region} 폐차 문의 / 차번호: " if region else "폐차 문의 / 차번호: "
    return f"sms:{cfg['sms_number']}?&body={quote(body, safe='')}"


def hero_top_html(cfg: dict, region: str, form: dict, crumb: str = "", updated: str = "", prefix: str = "../",
                  h1: str = "", lead: str = "") -> str:
    """<header class="hero hero-v3"> 안쪽. form 은 build_site.form_parts 결과(숨은 칸 Page·PageTitle·Source·Referrer 포함).
    region 은 H1 의 지역명("역삼동", "강남구", "서울", 홈은 "전국"). crumb·updated 가 비면 ① 줄을 넣지 않는다(홈).
    주제 페이지(2026-10-14, scripts/topics.py)는 h1 에 주제 제목, lead 에 그 아래 한 문장을 넘긴다(region 은 문자 본문에만 쓰임)."""
    lines = ['  <div class="wrap">']
    if crumb or updated:
        lines.append('    <div class="hero-meta">' + crumb
                     + (f'<p class="updated">최종 업데이트: {updated}</p>' if updated else "") + "</div>")
    lines += [
        (f'    <h1 class="display">{esc(h1)}</h1>\n    <p class="hero-lead">{esc(lead)}</p>' if h1
         else f'    <h1 class="display">{esc(region)} {HERO_H1_TAIL}</h1>'),
        f'    <a class="btn btn-call hero-call" href="tel:{esc(cfg["phone_tel"])}">📞 {esc(cfg["phone_display"])} 지금 전화</a>',
        '    <p class="hero-call-note">급하시면 전화가 가장 빠릅니다</p>',
        '    <div class="quote-card quote-mini" id="quote">',
        f'      <p class="mini-title">{MINI_TITLE}</p>',
        f'      <form class="quote-form" action="{form["FORM_ACTION"]}" method="{form["FORM_METHOD"]}">',
        f'        {form["FORM_HIDDEN"]}',
        f'        <input type="hidden" name="region" value="{form["REGION_FULL_NAME"]}">',
        '        <input type="hidden" name="form" value="상단 견적 폼">',
        '        <input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off">',
        '        <div class="mini-fields">',
        '          <label class="sr-only" for="q1-plate">차량번호</label>'
        '<input id="q1-plate" name="plate" type="text" inputmode="text" placeholder="12가 3456" autocomplete="off">',
        '          <label class="sr-only" for="q1-phone">연락처</label>'
        '<input id="q1-phone" name="phone" type="tel" inputmode="tel" placeholder="010-" maxlength="13" required autocomplete="tel">',
        '        </div>',
        '        <button class="btn btn-call" type="submit">차 번호로 비교 견적 받기 <span>— 폐차값·수출값 둘 다 (1+1)</span></button>',
        f'        <p class="fine">{CONSENT_HTML.format(prefix=prefix)}</p>',
        '      </form>',
        '    </div>',
    ]
    links = []
    if cfg.get("sms_number"):
        disp = cfg.get("text_reply_display") or cfg["sms_number"]
        links.append(f'<a href="{esc(sms_link(cfg, "" if region == "전국" else region))}">문자 {esc(disp)}</a>')
    if cfg.get("kakao_channel_url"):
        links.append(f'<a href="{esc(cfg["kakao_channel_url"])}" target="_blank" rel="noopener noreferrer">카톡 상담</a>')
    if links:
        lines.append(f'    <p class="hero-sms">{" · ".join(links)}</p>')
    lines.append("  </div>")
    return "\n".join(lines)


def why_block_html(badge: str, hint: str) -> str:
    """폼 바로 아래 "왜 비교해 드리나" 한 칸: 예전 첫 화면의 뱃지·폐차 견적 1+1 줄·핵심 문장 2개·안내 한 줄·
    비교 안내·신뢰 3줄(견인비·서류·전국 협력)을 그대로 옮겨 묶는다."""
    return "\n".join([
        '<section id="why-compare" class="why-compare">',
        '  <div class="wrap">',
        '    <h2 class="sec-title display">왜 비교해 드리나</h2>',
        f'    <span class="badge">{esc(badge)}</span>',
        '    <p class="oneplus">폐차 견적 1+1 — 폐차값과 수출값, 둘 다 알려드려요<small>1+1은 폐차 견적과 수출 견적, 두 가지를 함께 드린다는 뜻입니다.</small></p>',
        '    <ul class="core"><li>폐차 전에 수출 시세와 비교해서 더 높은 쪽으로 안내합니다</li><li>차량 확인하면 먼저 입금하고, 그 다음에 차를 가져갑니다</li></ul>',
        f'    <p class="hint">{esc(hint)}</p>',
        '    <p class="compare-note">다른 곳 견적 받으셨으면 금액 알려주세요. 비교해 드립니다.</p>',
        '    <div class="trust"><span>견인비 대부분 별도 청구 없음</span><span>압류·저당·상속·대리인 서류도 상담 가능</span><span>전국 협력 네트워크</span></div>',
        '  </div>',
        '</section>',
    ])
