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
"""
import json

START = "<!-- analytics:start -->"
END = "<!-- analytics:end -->"
PAGE_TYPES = ("dong", "gu", "si", "guide", "case", "home", "thanks", "privacy")


def _js(v) -> str:
    """<script> 안에 넣을 JSON 값(</script> 로 끊기지 않게)."""
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")


def head_html(cfg: dict, page_type: str, region: str = "") -> str:
    """<head> 에 넣을 측정 태그 묶음. 설정에 ID 가 하나도 없으면 빈 문자열."""
    if page_type not in PAGE_TYPES:
        raise ValueError(f"알 수 없는 page_type: {page_type}")
    ga, naver = (cfg.get("ga4_id") or "").strip(), (cfg.get("naver_analytics_id") or "").strip()
    if not ga and not naver:
        return ""
    out = [START]
    if ga:
        src = "https://www.googletagmanager.com/gtag/js?id=" + ga
        out.append(
            "<script>"
            "window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
            f"gtag('js',new Date());gtag('config',{_js(ga)});"
            f"(function(){{var P={{page_type:{_js(page_type)},region:{_js(region or '전국')}}};"
            # 이벤트 하나 보내기. cb 가 있으면 보낸 뒤(늦어도 1.5초 뒤) 부른다(폼 성공 뒤 thanks.html 로 이동)
            "window.pyechaTrack=function(n,pos,cb){var d=false,f=function(){if(!d){d=true;if(cb)cb();}};"
            "gtag('event',n,{page_type:P.page_type,region:P.region,position:pos,event_callback:f,event_timeout:1500});"
            "if(cb)setTimeout(f,1600);};"
            # 전화(tel:)·문자(sms:) 버튼 클릭: 하단 고정 바 = sticky, 첫 화면(header) = top, 나머지 = bottom
            "document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href^=\"tel:\"],a[href^=\"sms:\"]');"
            "if(!a)return;var pos=a.closest('.bar')?'sticky':a.closest('header')?'top':'bottom';"
            "window.pyechaTrack(a.getAttribute('href').indexOf('tel:')===0?'call_click':'sms_click',pos);},true);"
            # gtag.js 는 load 뒤에 불러 첫 화면을 막지 않는다
            f"function L(){{var s=document.createElement('script');s.async=true;s.src={_js(src)};document.head.appendChild(s);}}"
            "if(document.readyState==='complete')L();else window.addEventListener('load',L);})();"
            "</script>"
        )
    if naver:
        out.append(
            "<script>"
            f"(function(){{function L(){{var s=document.createElement('script');s.async=true;s.src='https://wcs.pstatic.net/wcslog.js';"
            f"s.onload=function(){{if(!window.wcs_add)window.wcs_add={{}};window.wcs_add['wa']={_js(naver)};if(window.wcs)wcs_do();}};"
            "document.head.appendChild(s);}"
            "if(document.readyState==='complete')L();else window.addEventListener('load',L);})();"
            "</script>"
        )
    out.append(END)
    return "\n".join(out)


def region_name(sido_short: str, *parts: str) -> str:
    """이벤트 region 값: "서울 강남구 역삼동"."""
    return " ".join(x for x in (sido_short, *parts) if x)

