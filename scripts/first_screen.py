"""
첫 화면(2026-10-13): 동·구·시 페이지와 첫 화면 홈(index.html)이 같이 쓰는 맨 위 한 화면과,
그 바로 아래 "왜 비교해 드리나" 한 칸.

휴대폰 한 화면(390px) 안에 ①~⑥이 다 들어가게 한다.
  ① 길 안내(시›구›동) + 최종 업데이트 (작게 한 줄)
  ② 한 문장 H1: "{지역명} 폐차, 차 번호만 주시면 폐차·수출 바로 비교해서 연락드립니다"
  ③ 전화 버튼(폼보다 위, 높이 56px) + 바로 아래 안심 한 줄 "{지역명} 어디든 기사가 직접 방문 — 입금 확인 후 차를 가져갑니다"
     (동·구·시 페이지만, 2026-10-16) + "급하시면 전화가 가장 빠릅니다"
  ④ 견적 폼 2칸(차량번호·연락처). 연식·차종 칸은 맨 아래 두 번째 폼에만 있다
  ⑤ 버튼 하나 "차 번호로 두 금액 받기 — 폐차값·수출값 둘 다"(2026-10-28 1+1 뺌)
  ⑥ 문자 한 줄 "문자 010-… · 10분 안에 답"(카카오 채널 주소가 있으면 "· 카톡 상담") + 작은 글씨 한 줄 "{reply_hours} 기준, …"
첫 화면에는 압류·저당·원부 같은 말을 쓰지 않는다(check_pages.py 가 확인). 예전 첫 화면의 뱃지·두 금액 줄·핵심 문장·
안내 줄·비교 안내·신뢰 줄은 지우지 않고 why_block_html 로 폼 바로 아래에 옮긴다.
전환 변경 #3(2026-11-19 설계, docs/fable-2026-11-19/conversion-3b.md): "왜 비교해 드리나" 칸 맨 위(제목 바로 아래)에 누르면 문자 창이
열리는 줄 두 개(EXIT_REPAIR·EXIT_QUOTE). 계약이 안 되는 까닭이 금액과 "고쳐서 탐"이 가장 많다는 병한님 경험(11/19)에 맞춘 출구다.
첫 화면(hero) 안은 건드리지 않는다. 누름은 GA4 이벤트 EXIT_EVENT 로 따로 센다(analytics.py 가 data-exit 값으로 한 번 더 보냄).
모양(CSS)은 templates/region-landing-v2.html 의 /* hero-v3:start */ ~ /* hero-v3:end */ 칸.
"""
from html import escape
from urllib.parse import quote


def esc(s: str) -> str:
    return escape(s, quote=True)


HERO_H1_TAIL = "폐차, 차 번호만 주시면 폐차·수출 바로 비교해서 연락드립니다"
MINI_TITLE = "전화가 부담스러우면 차 번호만 남겨 주세요 — 영업시간엔 10분 안에 전화드립니다"  # 2026-10-28 10분 회신
CONSENT_HTML = '남겨주신 정보는 견적 상담 연락에만 쓰며, 문의 시 <a href="{prefix}privacy.html">개인정보처리방침</a>에 동의한 것으로 봅니다.'
# 전환 변경 #3(2026-11-19): 폼 바로 아래 칸 맨 위의 "견적서 사진만 문자로" 출구 두 줄. 문구는 여기 한 곳에서만 고친다
# (check_pages.CORE_SENTENCES 가 이 두 문장을 그대로 찾는다). 금액 숫자·결과 약속은 쓰지 않는다.
EXIT_REPAIR = "고쳐 탈지 고민이면 수리 견적서 사진만 문자로 보내 주세요 — 차값이랑 같이 견줘 드릴게요"
EXIT_QUOTE = "다른 곳 견적 받으셨으면 금액만 문자로 주세요 — 폐차값·수출값 둘 다 보고 더 높은 쪽으로"
EXIT_REPAIR_SMS = "수리 견적서 사진 보냅니다"       # 문자 창에 미리 적히는 말(뒤에 " / 차번호: ")
EXIT_QUOTE_SMS = "다른 곳 견적 받았습니다"
EXIT_QUOTE_FIELD = "차번호·받은 금액"
EXIT_EVENT = "estimate_sms_click"                 # GA4 이벤트 이름(동·구·시·주제 페이지의 출구 줄)


def nowrap(html_text: str) -> str:
    """제목의 "폐차·수출"이 줄바꿈될 때 "폐차·" / "·수출"로 점이 따로 떨어지지 않게 한 덩어리로 묶는다(2026-10-15, CSS .nw)."""
    return html_text.replace("폐차·수출", '<span class="nw">폐차·수출</span>')


def sms_link(cfg: dict, region: str, what: str = "폐차 문의", field: str = "차번호") -> str:
    """문자 버튼 주소: 휴대폰에서 누르면 문자 창이 열리고 본문이 미리 채워진다.
    "?&body=" 는 아이폰(&body)·안드로이드(?body) 둘 다 읽는 형식. 손님은 끝에 차번호만 적으면 된다.
    what·field 는 출구 줄(2026-11-19)이 "수리 견적서 사진 보냅니다 / 차번호: "처럼 바꿔 쓴다."""
    body = f"{region} {what} / {field}: " if region else f"{what} / {field}: "
    return f"sms:{cfg['sms_number']}?&body={quote(body, safe='')}"


def exit_link_html(cfg: dict, region: str, text: str, what: str, field: str = "차번호", event: str = EXIT_EVENT) -> str:
    """누르면 문자 창이 열리는 출구 줄 하나(<a>). 문자 번호가 없으면 글자만. region 이 "전국"이면 본문에 지역을 넣지 않는다."""
    if not (cfg or {}).get("sms_number"):
        return esc(text)
    href = sms_link(cfg, "" if region == "전국" else region, what, field)
    return f'<a href="{esc(href)}" data-exit="{esc(event)}">{esc(text)}</a>'


def hero_top_html(cfg: dict, region: str, form: dict, crumb: str = "", updated: str = "", prefix: str = "../",
                  h1: str = "", lead: str = "", sms_what: str = "폐차 문의") -> str:
    """<header class="hero hero-v3"> 안쪽. form 은 build_site.form_parts 결과(숨은 칸 Page·PageTitle·Source·Referrer 포함).
    region 은 H1 의 지역명("역삼동", "강남구", "서울", 홈은 "전국"). crumb·updated 가 비면 ① 줄을 넣지 않는다(홈).
    주제 페이지(2026-10-14, scripts/topics.py)는 h1 에 주제 제목, lead 에 그 아래 한 문장을 넘긴다(region 은 문자 본문에만 쓰임).
    sms_what 은 문자 줄을 눌렀을 때 문자 창에 미리 적히는 말(주제 페이지가 바꿔 쓸 수 있음, 2026-11-19)."""
    lines = ['  <div class="wrap">']
    if crumb or updated:
        lines.append('    <div class="hero-meta">' + crumb
                     + (f'<p class="updated">최종 업데이트: {updated}</p>' if updated else "") + "</div>")
    lines += [
        (f'    <h1 class="display">{nowrap(esc(h1))}</h1>\n    <p class="hero-lead">{esc(lead)}</p>' if h1
         else f'    <h1 class="display">{esc(region)} {nowrap(esc(HERO_H1_TAIL))}</h1>'),
        f'    <a class="btn btn-call hero-call" href="tel:{esc(cfg["phone_tel"])}">📞 {esc(cfg["phone_display"])} 지금 전화</a>',
        *([f'    <p class="hero-visit">{esc(region)} 어디든 기사가 직접 방문 — 입금 확인 후 차를 가져갑니다</p>']
          if region and region != "전국" and not h1 else []),  # 동·구·시 페이지만(홈·주제 페이지 제외)
        '    <p class="hero-call-note">급하시면 전화가 가장 빠릅니다</p>',
        '    <div class="quote-card quote-mini" id="quote">',
        f'      <p class="mini-title">{MINI_TITLE}</p>',
        f'      <form class="quote-form" action="{form["FORM_ACTION"]}" method="{form["FORM_METHOD"]}">',
        f'        {form["FORM_HIDDEN"]}',
        f'        <input type="hidden" name="region" value="{form["REGION_FULL_NAME"]}">',
        '        <input type="hidden" name="form" value="상단 견적 폼">',
        '        <input type="checkbox" name="botcheck" class="hidden" style="display:none" tabindex="-1" autocomplete="off">',
        '        <div class="mini-fields">',
        '          <label class="sr-only" for="q1-plate">차량번호</label>'
        '<input id="q1-plate" name="plate" type="text" inputmode="text" placeholder="12가 3456" autocomplete="off">',
        '          <label class="sr-only" for="q1-phone">연락처</label>'
        '<input id="q1-phone" name="phone" type="tel" inputmode="tel" placeholder="010-" maxlength="20" required autocomplete="tel">',
        '        </div>',
        '        <button class="btn btn-call" type="submit">차 번호로 두 금액 받기 <span>— 폐차값·수출값 둘 다</span></button>',
        f'        <p class="fine">{CONSENT_HTML.format(prefix=prefix)}</p>',
        '      </form>',
        '    </div>',
    ]
    links = []
    if cfg.get("sms_number"):
        disp = cfg.get("text_reply_display") or cfg["sms_number"]
        links.append(f'<a href="{esc(sms_link(cfg, "" if region == "전국" else region, sms_what))}">문자 {esc(disp)} · 10분 안에 답</a>')
    if cfg.get("kakao_channel_url"):
        links.append(f'<a href="{esc(cfg["kakao_channel_url"])}" target="_blank" rel="noopener noreferrer">카톡 상담</a>')
    if links:
        lines.append(f'    <p class="hero-sms">{" · ".join(links)}</p>')
        if cfg.get("reply_hours"):  # 2026-10-28 10분 회신 시간
            lines.append(f'    <p class="hero-hours">{esc(cfg["reply_hours"])} 기준, 그 밖 시간은 다음 날 아침 7시 넘어 바로</p>')
    lines.append("  </div>")
    return "\n".join(lines)


def why_block_html(badge: str, hint: str, cfg: dict | None = None, region: str = "") -> str:
    """폼 바로 아래 "왜 비교해 드리나" 한 칸: 예전 첫 화면의 뱃지·두 금액 줄·핵심 문장 2개·안내 한 줄·
    신뢰 3줄(견인비·서류·등록 폐차장)을 묶는다(2026-10-28 1+1 뺌, 견인비 줄 바꿈).
    전환 변경 #3(2026-11-19): 비교 안내 줄("다른 곳 견적 …")을 칸 아래쪽에서 제목 바로 아래로 올리고, "고쳐 탈지 고민이면 …" 줄을
    그 위에 더해 두 줄 모두 누르면 문자 창이 열리게 한다(cfg·region 은 문자 주소용, 뱃지는 그 아래로)."""
    return "\n".join([
        '<section id="why-compare" class="why-compare">',
        '  <div class="wrap">',
        '    <h2 class="sec-title display">왜 비교해 드리나</h2>',
        f'    <p class="compare-note exit">{exit_link_html(cfg, region, EXIT_REPAIR, EXIT_REPAIR_SMS)}</p>',
        f'    <p class="compare-note exit">{exit_link_html(cfg, region, EXIT_QUOTE, EXIT_QUOTE_SMS, EXIT_QUOTE_FIELD)}</p>',
        f'    <span class="badge">{esc(badge)}</span>',
        '    <p class="oneplus">폐차값과 수출값, 둘 다 알려드려요</p>',
        '    <ul class="core"><li>폐차 전에 수출 시세와 비교해서 더 높은 쪽으로 안내합니다</li><li>차량 확인하면 먼저 입금하고, 그 다음에 차를 가져갑니다</li></ul>',
        f'    <p class="hint">{esc(hint)}</p>',
        '    <div class="trust"><span>견인비 따로 없음</span><span>압류·저당·상속·대리인 서류도 상담 가능</span><span>전국 등록 폐차장과 진행</span></div>',
        '  </div>',
        '</section>',
    ])
