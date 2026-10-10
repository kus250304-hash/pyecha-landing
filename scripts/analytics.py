"""
방문 측정 태그(2026-10-10). 모든 페이지(동·구·시·안내·사례·첫 화면·thanks·privacy) <head> 에 같은 것을 넣는다.

site_config.json
  ga4_id               → Google 애널리틱스 4 측정 ID. 비어 있으면 GA 태그와 이벤트를 넣지 않는다.
  naver_analytics_id   → 네이버 애널리틱스 사이트 ID. 비어 있으면 넣지 않는다(ID 를 받으면 채움).

이벤트(GA4): 전화 버튼 call_click, 문자 버튼 sms_click, 견적 폼 전송 성공 quote_submit.
매개변수: page_type(dong/gu/si/guide/case/home/thanks/privacy), region(페이지 지역 이름, 손님 정보 아님),
position(top = 첫 화면, sticky = 하단 고정 바, bottom = 그 밖의 본문).
quote_submit 은 Web3Forms 가 성공을 돌려준 뒤에만 보낸다(templates/region-landing-v2.html 의 폼 스크립트가
window.pyechaTrack 을 부름). 폼에 적은 전화번호·차량번호는 GA 로 보내지 않는다.

gtag.js 는 페이지가 다 뜬 뒤(load) 불러 첫 화면 속도에 영향을 덜 준다. 그 전에 일어난 이벤트는
dataLayer 에 쌓였다가 gtag.js 가 오면 함께 보내진다.
네이버 애널리틱스(wcslog.js)는 body_end_html 이 </body> 바로 앞에 넣고, 같은 이벤트를 wcs.event(이름, "page_type_position")로도 보낸다.
"""
import json

START = "<!-- analytics:start -->"
END = "<!-- analytics:end -->"
PAGE_TYPES = ("dong", "gu", "si", "guide", "case", "home", "thanks", "privacy")


def _js(v) -> str:
    """<script> 안에 넣을 JSON 값(</script> 로 끊기지 않게)."""
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")


def head_html(cfg: dict, page_type: str, region: str = "") -> str:
    """<head> 에 넣을 측정 태그 묶음(GA4 + 전화·문자·폼 이벤트). 설정에 ID 가 하나도 없으면 빈 문자열.
    이벤트는 GA4(gtag)와 네이버 애널리틱스(wcs.event, 있을 때만) 양쪽으로 보낸다."""
    if page_type not in PAGE_TYPES:
        raise ValueError(f"알 수 없는 page_type: {page_type}")
    ga, naver = (cfg.get("ga4_id") or "").strip(), (cfg.get("naver_analytics_id") or "").strip()
    if not ga and not naver:
        return ""
    js = ["<script>"]
    if ga:
        js.append("window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
                  f"gtag('js',new Date());gtag('config',{_js(ga)});")
    js.append(
        f"(function(){{var P={{page_type:{_js(page_type)},region:{_js(region or '전국')}}};"
        # 이벤트 하나 보내기. cb 가 있으면 보낸 뒤(늦어도 1.5초 뒤) 부른다(폼 성공 뒤 thanks.html 로 이동)
        "window.pyechaTrack=function(n,pos,cb){var d=false,f=function(){if(!d){d=true;if(cb)cb();}};"
        + ("gtag('event',n,{page_type:P.page_type,region:P.region,position:pos,event_callback:f,event_timeout:1500});" if ga else "")
        # 네이버 애널리틱스: wcslog.js 가 </body> 앞에서 불러와진 뒤에만(wcs.event 가 없으면 건너뜀)
        + "try{if(window.wcs&&typeof wcs.event==='function')wcs.event(n,P.page_type+'_'+pos);}catch(e){}"
        + ("if(cb)setTimeout(f,1600);};" if ga else "if(cb)setTimeout(f,300);};")
        # 전화(tel:)·문자(sms:) 버튼 클릭: 하단 고정 바 = sticky, 첫 화면(header) = top, 나머지 = bottom
        + "document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href^=\"tel:\"],a[href^=\"sms:\"]');"
        "if(!a)return;var pos=a.closest('.bar')?'sticky':a.closest('header')?'top':'bottom';"
        "window.pyechaTrack(a.getAttribute('href').indexOf('tel:')===0?'call_click':'sms_click',pos);},true);"
    )
    if ga:
        # gtag.js 는 load 뒤에 불러 첫 화면을 막지 않는다
        src = "https://www.googletagmanager.com/gtag/js?id=" + ga
        js.append(f"function L(){{var s=document.createElement('script');s.async=true;s.src={_js(src)};document.head.appendChild(s);}}"
                  "if(document.readyState==='complete')L();else window.addEventListener('load',L);")
    js.append("})();</script>")
    return "\n".join([START, "".join(js), END])


BODY_START = "<!-- naver-analytics:start -->"
BODY_END = "<!-- naver-analytics:end -->"


def body_end_html(cfg: dict) -> str:
    """</body> 바로 앞에 넣을 네이버 애널리틱스 기본 스크립트(2026-10-10). naver_analytics_id 가 비면 빈 문자열."""
    naver = (cfg.get("naver_analytics_id") or "").strip()
    if not naver:
        return ""
    return "\n".join([BODY_START,
                      # wcslog.js 를 <script src> 로 두면(async 여도) 처음부터 받아 와 모바일 LCP 가 약 1.5초 → 3.2초로 늘어,
                      # 페이지가 다 뜨고(load) 제목 글꼴까지 그려진 뒤 1초 있다가 불러오고, 다 온 뒤 wcs_do() 를 부른다
                      # (load 직후만 기다리면 글꼴 바뀌는 순간과 겹쳐 시뮬레이션 LCP 가 2.45초, 2026-10-10 Lighthouse)
                      f'<script>if(!window.wcs_add)window.wcs_add={{}};wcs_add["wa"]={_js(naver)};'
                      "(function(){function L(){var s=document.createElement('script');s.async=true;s.src='https://wcs.pstatic.net/wcslog.js';"
                      "s.onload=function(){if(window.wcs){wcs_do();}};document.body.appendChild(s);}"
                      "function W(){(document.fonts&&document.fonts.ready?document.fonts.ready:Promise.resolve()).then(function(){setTimeout(L,1000);});}"
                      "if(document.readyState==='complete')W();else window.addEventListener('load',W);})();</script>",
                      BODY_END])


def region_name(sido_short: str, *parts: str) -> str:
    """이벤트 region 값: "서울 강남구 역삼동"."""
    return " ".join(x for x in (sido_short, *parts) if x)

