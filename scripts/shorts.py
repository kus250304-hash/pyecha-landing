"""
유튜브 쇼츠 → 사례 짝 맞추기와 페이지에 넣는 가벼운 영상 칸(2026-10-16, docs/case-pipeline-2026-10-16.md [4]).

  python3 scripts/shorts.py match     채널 @pecha-export 의 새 영상 목록(RSS)을 읽어 사례와 짝을 맞추고 data/shorts_matches.json 에 쌓는다
  python3 scripts/shorts.py show      지금 짝 목록과 "짝 못 찾음" 목록

짝 맞추기: 쇼츠(/shorts/ 주소)만 본다. 제목·설명에 사례의 차종이 있고, ① 사례의 동 이름이나 시군구 이름이 있거나
② 연식이 같으면서 그 차종·연식 사례가 하나뿐일 때만 짝으로 본다. 맞는 사례가 둘 이상이면 짝 못 찾음.
제목·설명에 금액·결과 약속 표현이 있는 영상은 넣지 않는다(짝 못 찾음, 이유 표시).
사람이 고칠 때는 data/shorts_matches.json 의 그 영상 "case" 에 사례 slug 를 적고 "manual": true 를 넣는다(다시 맞추지 않음).

페이지에는 영상 제목을 쓰지 않는다(제목에 "수출 안 됩니다" 같은 단정이 있을 수 있음). "○○동 ○○ 사례 영상"처럼 우리 문구만 쓴다.
영상은 썸네일을 누를 때만 불러오고(lite embed) 자동재생하지 않는다. VideoObject 구조화 데이터를 함께 넣는다.
"""
import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATCHES = ROOT / "data" / "shorts_matches.json"
CASES_INDEX = ROOT / "cases" / "index.json"
CHANNEL_ID = "UCZrqa9lcMlGWDHHitO0ie0w"  # @pecha-export
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def load_matches() -> dict:
    if MATCHES.exists():
        return json.loads(MATCHES.read_text(encoding="utf-8"))
    return {"videos": {}}


@lru_cache(maxsize=1)
def _by_case() -> dict:
    """사례 slug → 짝 맞춘 쇼츠 하나(가장 최근)."""
    out: dict[str, dict] = {}
    for vid, v in load_matches().get("videos", {}).items():
        if v.get("case"):
            cur = out.get(v["case"])
            if not cur or v.get("published", "") > cur.get("published", ""):
                out[v["case"]] = {"id": vid, **v}
    return out


def short_for(slug: str) -> dict | None:
    return _by_case().get(slug)


def case_label(c: dict) -> str:
    region = " ".join(x for x in ((c.get("sigungu") or c.get("sido") or ""), c.get("dong") or "") if x)
    return f"{region} {c.get('car', '')} 사례 영상".replace("  ", " ").strip()


def video_ld(v: dict, name: str, desc: str, page_url: str = "") -> str:
    data = {
        "@context": "https://schema.org", "@type": "VideoObject",
        "name": name, "description": desc or name,
        "thumbnailUrl": [f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"],
        "uploadDate": v["published"],
        "embedUrl": f"https://www.youtube-nocookie.com/embed/{v['id']}",
        "contentUrl": f"https://www.youtube.com/shorts/{v['id']}",
    }
    if page_url:
        data["url"] = page_url
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


LITE_CSS = (".yt-lite{position:relative;max-width:320px;margin:12px auto 0}"
            ".yt-lite button{display:block;width:100%;aspect-ratio:9/16;padding:0;border:0;border-radius:12px;overflow:hidden;"
            "background:#000;cursor:pointer;position:relative}"
            ".yt-lite img{width:100%;height:100%;object-fit:cover;display:block}"
            ".yt-lite .play{position:absolute;left:50%;top:50%;width:68px;height:48px;margin:-24px 0 0 -34px;border-radius:12px;"
            "background:rgba(230,57,70,.92)}"
            ".yt-lite .play:after{content:'';position:absolute;left:27px;top:14px;border-style:solid;border-width:10px 0 10px 18px;"
            "border-color:transparent transparent transparent #fff}"
            ".yt-lite iframe{display:block;width:100%;aspect-ratio:9/16;border:0;border-radius:12px}"
            ".yt-lite.wide{max-width:560px}.yt-lite.wide button,.yt-lite.wide iframe{aspect-ratio:16/9}"
            ".yt-lite figcaption{padding:6px 2px 0;font-size:14px;text-align:center}")
# 누를 때만 영상을 불러온다. autoplay 를 넣지 않아 저절로 재생되지 않는다
LITE_JS = ("document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.yt-lite button');"
           "if(!b)return;var f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'+b.dataset.id;"
           "f.title=b.getAttribute('aria-label');f.allow='accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share';"
           "f.referrerPolicy='strict-origin-when-cross-origin';f.allowFullscreen=true;b.replaceWith(f);});")


def lite_html(vid: str, label: str, link: bool = True, url: str = "", short: bool = True) -> str:
    url = url or f"https://www.youtube.com/shorts/{vid}"
    return (f'<figure class="yt-lite{"" if short else " wide"}"><button type="button" data-id="{esc(vid)}" aria-label="{esc(label)} 재생">'
            f'<img src="https://i.ytimg.com/vi/{esc(vid)}/hqdefault.jpg" alt="{esc(label)}" loading="lazy" width="480" height="360">'
            '<span class="play"></span></button>'
            + (f'<figcaption><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">'
               f'{esc(label)} — 유튜브에서 보기</a></figcaption>' if link else "")
            + "</figure>")


def lite_assets() -> str:
    return f"<style>{LITE_CSS}</style><script>{LITE_JS}</script>"


def cards_video_html(picked: list[dict], base_url: str = "") -> str:
    """동·구·시·안내 페이지 사례 칸 아래: 보이는 사례 중 짝 맞춘 쇼츠가 있는 첫 사례의 영상 하나(페이지당 1개)."""
    for c in picked:
        v = short_for(c["slug"])
        if v:
            label = case_label(c)
            return ('<div class="case-video">' + lite_html(v["id"], label) + lite_assets()
                    + video_ld(v, label, c.get("summary", ""),
                               f"{base_url.rstrip('/')}/cases/{c['slug']}.html" if base_url else "") + "</div>")
    return ""


# ---- 짝 맞추기 ----
def fetch_rss() -> list[dict]:
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    out = []
    for e in root.findall("a:entry", NS):
        link = e.find("a:link", NS).get("href", "")
        out.append({
            "id": e.find("yt:videoId", NS).text, "short": "/shorts/" in link,
            "title": e.find("a:title", NS).text or "",
            "desc": e.find("media:group/media:description", NS).text or "",
            "published": (e.find("a:published", NS).text or "")[:10],
        })
    return out


def _car_name(c: dict) -> str:
    car = next((v for k, v in c.get("facts") or [] if k == "차종"), "") or re.sub(r"^\d{4}년식\s*", "", c.get("car", ""))
    return car.replace(" ", "")


def _year(c: dict) -> str:
    return next((re.sub(r"\D", "", v) for k, v in c.get("facts") or [] if k == "연식"), "")


def match_case(v: dict, cases: list[dict]) -> tuple[str | None, str]:
    text = (v["title"] + " " + v["desc"]).replace(" ", "")
    by_car = [c for c in cases if _car_name(c) and _car_name(c) in text]
    if not by_car:
        return None, "차종이 맞는 사례 없음"
    strong = [c for c in by_car if (c.get("dong") and c["dong"] in text)
              or (c.get("sigungu") and c["sigungu"].split()[-1] in text)]
    if len(strong) == 1:
        return strong[0]["slug"], "차종·지역"
    if len(strong) > 1:
        return None, f"차종·지역이 맞는 사례가 {len(strong)}건"
    years = [c for c in by_car if _year(c) and (_year(c) + "년식") in text]
    if len(years) == 1:
        return years[0]["slug"], "차종·연식"
    return None, ("차종·연식이 맞는 사례가 여러 건" if years else "지역·연식이 맞는 사례 없음")


# 영상 제목·설명의 금액 표현. "압류 12건, 원부" 의 "원" 을 금액으로 보지 않게 숫자 바로 뒤 "원"(뒤에 한글이 붙지 않은 것)만 본다
VIDEO_MONEY_RE = re.compile(r"\d[\d,.]*\s*(만\s*원|천\s*원|억|원(?![가-힣]))|₩|시세|견적가|매입가")


def cmd_match(args) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_cases import PROMISE_RE
    data = load_matches()
    videos = data.setdefault("videos", {})
    cases = json.loads(CASES_INDEX.read_text(encoding="utf-8")) if CASES_INDEX.exists() else []
    try:
        feed = [v for v in fetch_rss() if v["short"]]
    except Exception as e:  # 네트워크 실패: 있던 짝은 그대로 두고, 쌓아 둔 짝 못 찾음만 다시 맞춰 본다
        print(f"RSS 읽기 실패: {type(e).__name__} — 쌓아 둔 목록만 다시 맞춰 봄")
        feed = []
    today = date.today().isoformat()
    in_memo = {v["id"]: c["slug"] for c in cases for v in c.get("videos") or []}
    # 오늘 RSS 의 쇼츠 + RSS 에서 빠졌어도 아직 짝 못 찾은 쇼츠(사례가 나중에 생기면 그때 맞춰짐)
    todo = {v["id"]: v for v in feed}
    for vid, rec in videos.items():
        if vid not in todo and not rec.get("case") and not rec.get("manual"):
            todo[vid] = {"id": vid, "title": rec["title"], "desc": rec.get("desc", ""), "published": rec["published"]}
    for vid, v in todo.items():
        cur = videos.get(vid, {})
        if cur.get("manual") or cur.get("case"):
            continue
        rec = {"title": v["title"], "desc": v["desc"][:400], "published": v["published"], "checked": today, "case": None}
        text = v["title"] + " " + v["desc"]
        if vid in in_memo:  # 사례 메모에 이미 넣은 영상: 그 사례로(구조화 데이터·지역 페이지 영상 칸에 쓰임)
            rec["case"], rec["why"] = in_memo[vid], "사례 메모에 이미 있음"
        elif m := (VIDEO_MONEY_RE.search(text) or PROMISE_RE.search(text)):
            rec["why"] = f"제목·설명에 '{m.group(0)}' 표현이 있어 넣지 않음"
        else:
            rec["case"], rec["why"] = match_case(v, cases)
        videos[vid] = rec
    MATCHES.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    show(data, today)


def show(data: dict, today: str = "") -> None:
    vids = data.get("videos", {})
    matched = [(k, v) for k, v in vids.items() if v.get("case")]
    missing = [(k, v) for k, v in vids.items() if not v.get("case")]
    print(f"쇼츠 짝: 맞춤 {len(matched)}개, 짝 못 찾음 {len(missing)}개")
    for k, v in sorted(matched, key=lambda x: x[1].get("published", ""), reverse=True):
        new = " (오늘)" if v.get("checked") == today and not v.get("manual") else ""
        print(f"  짝 맞춤{new}: {v['published']} {v['title']} → cases/{v['case']}.html ({v.get('why', '수동')})")
    for k, v in sorted(missing, key=lambda x: x[1].get("published", ""), reverse=True):
        print(f"  짝 못 찾음: {v['published']} {v['title']} — {v.get('why', '')} (https://youtube.com/shorts/{k})")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("match")
    sub.add_parser("show")
    args = ap.parse_args()
    if args.cmd == "match":
        cmd_match(args)
    else:
        show(load_matches(), date.today().isoformat())


if __name__ == "__main__":
    main()
