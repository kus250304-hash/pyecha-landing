"""
공통 안내 페이지 5장(/guide/)을 만든다 (2026-10-01).
  폐차 절차 · 필요 서류 · 조기폐차 지원 안내 · 폐차 vs 수출 비교 · 폐차 금액은 어떻게 정해지나

사용법
  python3 scripts/build_guide.py      # build_site.py 도 끝에 이 함수를 부른다

규칙
- 글은 동 페이지에 이미 있는 진행 순서·서류 안내·유형별 안내를 바탕으로 쓴다. 지역 이름은 쓰지 않는다.
- 금액 숫자를 쓰지 않는다. 금액은 "상담 후 확인". "최고가", "1등", "최대", "보장", "100%", "실시간 접수" 같은 단정 표현도 쓰지 않는다
  (빌더와 check_pages.py 가 막음).
- 연락처는 "전화 1600-6011 / 문자 010-9926-7779"(site_config.json 의 phone_display·text_reply_display).
  문자 버튼은 휴대폰(text_reply_display)으로 보낸다. 대표번호는 문자를 받지 못한다.
- 모든 동·구 페이지 상단 고정 메뉴의 "폐차 안내"가 첫 장(폐차 절차)으로, 맨 아래 지역 링크 목록의 "폐차 안내"가 5장 모두로 연결된다.
- 맨 위 "최종 업데이트"와 dateModified 는 내용이 실제로 바뀐 날만 바뀐다(build_site.with_updated_date).
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "guide.html"
DONG_TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
OUT = ROOT / "guide"
BAN_RE = re.compile(r"보장|무조건|100%|1위|1등|최저가|최고가|최대(?!한)|실시간\s*접수|\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩")

# 글 조각: ("p", 문단) ("steps", [(제목, 설명)]) ("rows", [(이름, 내용)]) ("list", [(굵은 글씨, 설명)]) ("note", 작은 글씨)
GUIDES = [
    {
        "file": "폐차-절차.html",
        "nav": "폐차 절차",
        "title": "폐차 절차 안내",
        "h1": "폐차 절차,<br>전화 한 통부터 말소까지",
        "desc": "폐차는 차를 넘긴 뒤 자동차 등록을 말소해야 끝납니다. 상담부터 방문·인수, 말소까지 진행 순서와 유형별 기간을 정리했습니다.",
        "lead": "폐차는 차를 넘기는 것으로 끝나지 않고 자동차 등록을 말소해야 마무리됩니다. 아래 순서로 진행되며, 차량 상황에 따라 기간이 달라질 수 있습니다.",
        "sections": [
            ("진행 순서", "이렇게 네 단계로 진행됩니다", [
                ("steps", [
                    ("상담", "차종·연식·차 상태(시동이 걸리는지, 사고가 있었는지)와 차가 있는 곳을 알려주시면 폐차와 수출 중 어느 쪽이 나은지 상담 후 확인해 드립니다. 차량번호가 있으면 더 빠릅니다."),
                    ("일정·서류 안내", "방문 날짜와 시간을 정하고, 명의 상황(본인·대리인·법인·상속·압류)에 맞는 서류를 안내해 드립니다."),
                    ("방문·인수", "협력업체가 약속한 날 차가 있는 곳으로 가서 차를 인수합니다. 시동이 안 걸리거나 사고로 움직이지 못하는 차도 견인차가 갑니다."),
                    ("말소 처리", "말소 등록을 진행하고 서류를 전달해 드립니다. 차령초과 말소처럼 기간이 더 걸리는 경우는 미리 알려 드립니다."),
                ]),
            ]),
            ("유형별로 걸리는 기간", "차와 서류 상황에 따라 기간이 다릅니다", [
                ("rows", [
                    ("일반 폐차", "압류·저당이 없는 차량. 견인은 당일·익일 일정으로 잡습니다."),
                    ("차령초과 말소", "차령 기준을 넘겨 압류·저당이 남아 있어도 말소하는 경우. 보통 1~2개월 걸립니다."),
                    ("조기폐차", "노후 경유차 지원 제도로 하는 경우. 지자체 사전 승인을 받은 뒤 진행합니다."),
                    ("상속 폐차", "명의자가 돌아가신 차량. 상속 서류가 준비되면 당일 접수합니다."),
                ]),
                ("note", "처리 기간은 지역·서류 상황에 따라 달라질 수 있습니다."),
            ]),
            ("말소가 끝난 뒤", "남은 정리도 함께 챙기세요", [
                ("p", "말소가 끝나면 서류를 전달해 드립니다. 자동차보험 해지는 말소 뒤에 가입한 보험사에 연락해 진행합니다."),
                ("p", "자동차세처럼 차에 붙는 세금은 말소된 날을 기준으로 정리됩니다. 정산 내용은 관할 관청과 보험사에 확인해 주세요."),
            ]),
        ],
        "faqs": [
            ("차를 직접 가져가야 하나요?", "아닙니다. 차가 있는 곳으로 협력업체가 찾아갑니다. 견인비는 받지 않습니다."),
            ("차가 있는 곳에 제가 없어도 되나요?", "차 위치와 열쇠·서류를 어떻게 전달할지 미리 정하면 방법을 함께 찾습니다. 상담 때 사정을 말씀해 주세요."),
            ("말소가 끝났는지 어떻게 알 수 있나요?", "말소가 끝나면 서류를 전달해 드립니다. 정부24에서 자동차등록원부를 떼어 직접 확인하실 수도 있습니다."),
        ],
    },
    {
        "file": "폐차-필요-서류.html",
        "nav": "필요 서류",
        "title": "폐차 필요 서류 안내 (본인·대리인·법인·상속·압류)",
        "h1": "폐차 필요 서류,<br>상황별로 정리했습니다",
        "desc": "본인 명의, 대리인, 법인 차량, 상속, 압류·저당 차량별로 폐차에 필요한 서류를 정리했습니다. 없는 서류가 있어도 진행 방법을 찾아드립니다.",
        "lead": "명의자가 직접 하는지, 다른 사람이 대신하는지, 법인 차인지, 상속 차인지에 따라 서류가 다릅니다. 없는 서류가 있어도 먼저 전화 주세요.",
        "sections": [
            ("상황별 필요 서류", "정확한 서류는 상담 때 차량 상황에 맞춰 다시 확인해 드립니다", [
                ("rows", [
                    ("본인 명의", "자동차등록증, 신분증. 등록증을 잃어버리셨어도 진행 방법이 있습니다."),
                    ("대리인", "위임장, 명의자 인감증명서(또는 본인서명사실확인서), 대리인 신분증."),
                    ("법인 차량", "사업자등록증, 법인인감증명서, 위임장."),
                    ("상속", "사망자 기본증명서·가족관계증명서, 상속인 신분증, 상속인 동의서."),
                    ("압류·저당", "등록원부로 차령초과 말소가 되는지 먼저 확인해 드립니다."),
                ]),
            ]),
            ("서류를 준비할 때", "미리 알아두면 덜 번거롭습니다", [
                ("list", [
                    ("증명서는 일정이 정해진 뒤에", "인감증명서처럼 발급한 지 오래되면 받지 않는 서류가 있습니다. 방문 날짜가 정해진 뒤 떼시는 편이 좋습니다."),
                    ("상속 차량은 서두르세요", "명의자가 돌아가신 차는 상속인이 정해진 기간 안에 이전하거나 말소해야 하며, 늦으면 과태료가 나올 수 있습니다."),
                    ("압류·저당이 있어도 상담", "차령 기준을 넘긴 차는 압류·저당이 남아 있어도 말소할 수 있는 경우가 많습니다. 보통 1~2개월 걸립니다."),
                    ("서류가 복잡한 차도 상담", "법인 부도 차량, 차는 없어졌는데 서류상 말소가 안 된 차량도 상담해 드립니다."),
                ]),
            ]),
        ],
        "faqs": [
            ("자동차등록증을 잃어버렸어요.", "등록증이 없어도 진행할 수 있는 방법이 있습니다. 신분증만 준비해 주시면 나머지는 안내해 드립니다."),
            ("명의자가 멀리 살아서 직접 못 와요.", "위임장과 명의자 인감증명서(또는 본인서명사실확인서)가 있으면 대리인이 진행할 수 있습니다."),
            ("공동명의 차량은 어떻게 하나요?", "명의자 모두의 서류가 필요할 수 있습니다. 명의 상황을 알려주시면 상담 후 확인해 드립니다."),
        ],
    },
    {
        "file": "조기폐차-지원-안내.html",
        "nav": "조기폐차 지원",
        "title": "노후 경유차 조기폐차 지원 안내",
        "h1": "노후 경유차 조기폐차 지원,<br>이렇게 확인하세요",
        "desc": "배출가스 4·5등급 경유차는 지자체 조기폐차 지원 대상일 수 있습니다. 대상 확인, 사전 신청과 승인, 폐차까지 순서와 주의할 점을 정리했습니다. 지원 금액은 공고와 상담 후 확인.",
        "lead": "배출가스 4·5등급 경유차는 지자체 조기폐차 지원 제도 대상일 수 있습니다. 대상·조건·신청 기간은 지자체 공고마다 다르므로 공고를 먼저 확인해야 합니다.",
        "sections": [
            ("대상인지 먼저 확인하세요", "세 가지를 보면 됩니다", [
                ("list", [
                    ("배출가스 등급", "차의 배출가스 등급이 지원 대상 등급(4·5등급 등)인지 확인합니다."),
                    ("차가 등록된 지역", "지원은 차의 사용본거지가 있는 지자체 공고를 따릅니다."),
                    ("공고의 조건", "보유 기간, 차가 정상적으로 움직이는지 확인하는 절차 등 조건이 공고마다 다릅니다."),
                ]),
            ]),
            ("진행 순서", "승인을 받은 뒤에 폐차합니다", [
                ("steps", [
                    ("공고 확인", "차가 등록된 지자체의 조기폐차 지원 공고에서 대상과 신청 기간을 확인합니다."),
                    ("사전 신청", "공고에 적힌 방법으로 조기폐차를 신청합니다."),
                    ("승인", "지자체에서 대상이 맞는지 확인하고 승인을 알려 줍니다."),
                    ("폐차·말소", "승인 뒤 공고에 정해진 기간 안에 폐차하고 말소 서류를 냅니다. 이 단계부터 함께 진행해 드립니다."),
                ]),
            ]),
            ("주의할 점", "지원을 놓치지 않으려면", [
                ("list", [
                    ("승인 전에 폐차하지 마세요", "승인을 받기 전에 차를 넘기면 지원을 받지 못할 수 있습니다."),
                    ("예산이 끝나면 마감", "지자체 예산이 다 쓰이면 기간 안이라도 접수가 끝날 수 있습니다."),
                    ("금액은 공고마다 다릅니다", "지원 금액은 공고와 차량에 따라 달라 이 페이지에는 적지 않습니다. 공고와 상담 후 확인해 주세요."),
                ]),
                ("p", "구 페이지가 있는 지역은 그 페이지의 공공 정보 표에 확인된 지자체 공고를 함께 적어 두었습니다."),
            ]),
        ],
        "faqs": [
            ("승인 전에 차를 먼저 넘겨도 되나요?", "지원을 받으시려면 승인 뒤에 폐차하셔야 합니다. 승인 전이라면 일정을 먼저 맞춰 드립니다."),
            ("지원 대상이 아니면 어떻게 하나요?", "일반 폐차나 수출 비교 상담으로 진행할 수 있습니다. 차 상태를 알려주시면 상담 후 확인해 드립니다."),
            ("조기폐차와 수출을 같이 할 수 있나요?", "조기폐차 지원은 폐차를 조건으로 하므로 보통 수출과 함께 진행하지 않습니다. 어느 쪽이 나은지 상담 후 확인해 드립니다."),
        ],
    },
    {
        "file": "폐차-수출-비교.html",
        "nav": "폐차 vs 수출",
        "title": "폐차 vs 수출 비교 안내",
        "h1": "폐차와 수출,<br>어느 쪽이 나을까요",
        "desc": "오래되거나 고장 난 차도 해외에서 찾는 차종이면 수출이 나을 수 있습니다. 폐차와 수출의 차이, 어떤 차가 어느 쪽에 맞는지, 비교 방법을 정리했습니다.",
        "lead": "폐차보다 수출이 더 받는 차가 있습니다. 반대로 폐차가 나은 차도 많습니다. 차마다 다르므로 차 상태를 듣고 상담 후 확인합니다.",
        "sections": [
            ("두 방법의 차이", "어느 쪽이든 말소까지 함께 진행합니다", [
                ("rows", [
                    ("폐차", "차를 해체해 재활용하고 말소 등록을 합니다. 폐차 보상금은 차의 재활용 가치와 부품 상태로 정해집니다."),
                    ("수출", "차를 해외로 내보내고 수출 말소를 합니다. 해외에서 그 차종을 얼마나 찾는지가 중요합니다."),
                ]),
            ]),
            ("수출을 함께 볼 만한 차", "이런 차는 수출 시세와 비교해 보세요", [
                ("list", [
                    ("해외에서 많이 찾는 차종", "오래된 차라도 해외 수요가 있는 차종이면 수출 쪽이 나을 수 있습니다."),
                    ("엔진·변속기 상태가 괜찮은 차", "겉이 낡았어도 주요 부품 상태가 괜찮으면 비교해 볼 만합니다."),
                ]),
            ]),
            ("폐차가 나을 수 있는 차", "이런 경우는 폐차 쪽을 먼저 봅니다", [
                ("list", [
                    ("해외 수요가 적은 차종", "수출로 찾는 곳이 적으면 폐차 쪽이 낫습니다."),
                    ("심하게 부서지거나 침수된 차", "상태에 따라 폐차가 맞는 경우가 많습니다."),
                    ("조기폐차 지원을 받으려는 차", "지원 제도는 폐차를 조건으로 합니다."),
                ]),
            ]),
            ("비교는 이렇게 합니다", "한 곳만 보지 않고 둘 다 봅니다", [
                ("p", "차종·연식·차 상태를 들은 뒤 폐차 보상금과 수출 시세를 함께 보고 유리한 쪽을 안내해 드립니다. 어느 쪽으로 정하든 견인비는 받지 않고 말소까지 진행합니다."),
                ("note", "수출이 늘 더 낫다는 뜻은 아닙니다. 차마다 다르므로 상담 후 확인합니다."),
            ]),
        ],
        "faqs": [
            ("시동이 안 걸리는 차도 수출과 비교할 수 있나요?", "차 상태를 들은 뒤 비교해 드립니다. 어느 쪽이 나은지는 상담 후 확인합니다."),
            ("압류나 저당이 있는 차는요?", "압류·저당이 남아 있으면 진행 방법이 달라질 수 있어 등록원부를 먼저 확인해 드립니다."),
            ("비교만 해 보고 안 해도 되나요?", "네. 상담만 받으셔도 됩니다."),
        ],
    },
    {
        "file": "폐차-금액-정하는-방법.html",
        "nav": "폐차 금액",
        "title": "폐차 금액은 어떻게 정해지나",
        "h1": "폐차 금액은<br>어떻게 정해지나요",
        "desc": "폐차 금액은 차마다 달라 한 가지 숫자로 말할 수 없습니다. 금액에 영향을 주는 것과 미리 알려주시면 좋은 정보를 정리했습니다. 정확한 금액은 상담 후 확인.",
        "lead": "폐차 금액은 차마다 달라 한 가지 숫자로 말씀드릴 수 없습니다. 아래 요소를 보고 정해지며, 정확한 금액은 상담 후 확인해 드립니다.",
        "sections": [
            ("금액에 영향을 주는 것", "차마다 이 요소들이 다릅니다", [
                ("list", [
                    ("차종과 무게", "차에서 나오는 철·알루미늄 같은 재활용 자원의 양이 다릅니다."),
                    ("부품 상태", "엔진·변속기처럼 다시 쓸 수 있는 부품의 상태를 봅니다."),
                    ("연식과 운행 상태", "시동이 걸리는지, 움직일 수 있는지를 봅니다."),
                    ("사고·침수 여부", "부서지거나 물에 잠긴 정도에 따라 달라집니다."),
                    ("수출 수요", "해외에서 찾는 차종이면 수출 시세와 함께 비교합니다."),
                    ("서류 상황", "압류·저당, 상속처럼 서류가 복잡하면 진행 방법과 기간이 달라집니다."),
                ]),
            ]),
            ("미리 알려주시면 빨라요", "아래 정보를 알려주시면 더 빠르게 확인해 드립니다", [
                ("rows", [
                    ("차 정보", "차량번호, 차종, 연식"),
                    ("차 상태", "시동이 걸리는지, 사고·침수가 있었는지"),
                    ("차가 있는 곳", "주소나 가까운 큰 건물, 주차 위치(지하주차장 등)"),
                    ("사진", "앞·뒤·옆과 계기판 사진을 문자로 보내 주시면 됩니다"),
                ]),
            ]),
            ("비용이 드나요?", "고객님이 따로 내시는 비용은 없습니다", [
                ("p", "견인비는 받지 않습니다. 폐차든 수출이든 같고, 예외가 생기면 진행 전에 먼저 알려드립니다."),
                ("note", "이 페이지에는 금액 숫자를 적지 않습니다. 차마다 다르므로 상담 후 확인해 드립니다."),
            ]),
        ],
        "faqs": [
            ("전화로 바로 금액을 알 수 있나요?", "차 정보를 들으면 어느 쪽이 나은지 방향을 말씀드리고, 정확한 금액은 상담 후 확인해 드립니다."),
            ("상담 때 들은 금액이 나중에 달라지기도 하나요?", "현장에서 본 차 상태가 상담 때 들은 것과 다르면 달라질 수 있습니다. 처음에 차 상태를 정확히 알려주시면 좋습니다."),
            ("금액을 알아보려면 무엇이 필요한가요?", "차량번호와 차종·연식, 시동 여부, 차가 있는 곳을 알려주시면 됩니다. 사진이 있으면 더 정확합니다."),
        ],
    },
]


def section_html(i: int, h2: str, sub: str, parts: list, esc) -> str:
    body = []
    for kind, val in parts:
        if kind == "p":
            body.append(f'<div class="local"><p>{esc(val)}</p></div>')
        elif kind == "note":
            body.append(f'<p class="note">{esc(val)}</p>')
        elif kind == "steps":
            body.append('<ol class="steps">' + "".join(f"<li><b>{esc(b)}</b><span>{esc(s)}</span></li>" for b, s in val) + "</ol>")
        elif kind == "rows":
            body.append('<div class="docs">' + "".join(f'<div class="row"><b>{esc(b)}</b><span>{esc(s)}</span></div>' for b, s in val) + "</div>")
        elif kind == "list":
            body.append('<ul class="guide-list">' + "".join(f"<li><b>{esc(b)}</b>{esc(s)}</li>" for b, s in val) + "</ul>")
        else:
            raise ValueError(f"모르는 글 조각 {kind}")
    bg = ' style="background:#fff"' if i % 2 == 0 else ""
    return (f'  <section id="part{i + 1}"{bg}>\n    <div class="wrap">\n'
            f'      <h2 class="sec-title display">{esc(h2)}</h2>\n      <p class="sec-sub">{esc(sub)}</p>\n      '
            + "\n      ".join(body) + "\n    </div>\n  </section>\n")


def guide_text(g: dict) -> str:
    out = [g["title"], g["h1"], g["desc"], g["lead"]]
    for h2, sub, parts in g["sections"]:
        out += [h2, sub]
        for kind, val in parts:
            if isinstance(val, str):
                out.append(val)
            else:
                out += [x for pair in val for x in pair]
    out += [x for qa in g["faqs"] for x in qa]
    return " ".join(out)


def render_all(regions: list[dict], cfg: dict, gu_data: list[dict]) -> list[str]:
    """안내 페이지 5장을 렌더링하고, 내용이 바뀐 페이지 경로("guide/…", %인코딩) 목록을 돌려준다."""
    from build_site import UPDATED_MARK, area_links_html, esc, page_jsonld, with_updated_date

    problems = [f"{g['file']}: 금액·단정 표현 '{m.group(0)}'" for g in GUIDES for m in [BAN_RE.search(guide_text(g))] if m]
    if problems:
        raise SystemExit("안내 페이지를 만들 수 없음:\n  " + "\n  ".join(problems))

    template = re.sub(r"<!DOCTYPE html>\s*<!--.*?-->", "<!DOCTYPE html>", TEMPLATE.read_text(encoding="utf-8"), count=1, flags=re.DOTALL)
    dong_tpl = DONG_TEMPLATE.read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", dong_tpl, flags=re.DOTALL).group(0)
    sprite = re.search(r'<svg width="0" height="0"[^>]*>.*?</svg>', dong_tpl, flags=re.DOTALL).group(0)
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]
    text_disp = cfg.get("text_reply_display") or ""
    text_tel = re.sub(r"\D", "", text_disp)
    contact_line = f"전화 {phone_disp}" + (f" / 문자 {text_disp}" if text_disp else "")
    if text_tel:
        sms_href = f'href="sms:{text_tel}?body=폐차%20문의드립니다"'
        sms_btn = f'<a class="btn btn-sms" {sms_href}><svg><use href="#i-chat"/></svg>문자 {esc(text_disp)}</a>'
        bar_second, bar_cols = f'<a class="btn btn-sms" {sms_href}><svg><use href="#i-chat"/></svg>문자</a>', "2fr 1fr"
    else:
        sms_btn, bar_cols = "", "3fr 2fr"
        bar_second = '<a class="btn btn-quote" href="#consult" style="background:#fff"><svg><use href="#i-chat"/></svg>상담 안내</a>'
    area = area_links_html(regions, gu_data)

    OUT.mkdir(exist_ok=True)
    changed = []
    for g in GUIDES:
        canonical = f"{base}/guide/{quote(g['file'])}"
        meta_title = f"{g['title']} | 폐차·수출 비교 상담 · 전화 {phone_disp}"
        meta_desc = f"{g['desc']} {contact_line}."
        nav = "".join(
            f'<a href="{esc(x["file"])}"' + (' aria-current="page"' if x is g else "") + f">{esc(x['nav'])}</a>" for x in GUIDES)
        crumbs = ('<nav class="crumbs" aria-label="경로"><a href="../index.html">전체 지역</a> › '
                  f'<a href="{esc(GUIDES[0]["file"])}">폐차 안내</a> › {esc(g["nav"])}</nav>')
        jsonld = [
            {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in g["faqs"]]},
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "전체 지역", "item": f"{base}/"},
                {"@type": "ListItem", "position": 2, "name": "폐차 안내", "item": f"{base}/guide/{quote(GUIDES[0]['file'])}"},
                {"@type": "ListItem", "position": 3, "name": g["nav"], "item": canonical}]},
        ]
        values = {
            "META_TITLE": esc(meta_title), "META_DESC": esc(meta_desc), "CANONICAL": canonical,
            "JSONLD": json.dumps(jsonld, ensure_ascii=False), "PAGE_JSONLD": page_jsonld(meta_title, canonical),
            "STYLE": style, "SPRITE": sprite, "GUIDE_NAV": nav, "UPDATED_ON": UPDATED_MARK, "BREADCRUMB": crumbs,
            "H1": esc(g["h1"]).replace("&lt;br&gt;", "<br>"), "LEAD": esc(g["lead"]), "CONTACT_LINE": esc(contact_line),
            "SECTIONS_HTML": "".join(section_html(i, h2, sub, parts, esc) for i, (h2, sub, parts) in enumerate(g["sections"])),
            "FAQ_HTML": "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in g["faqs"]),
            "CONSULT_TEXT": esc(f"차 상태와 차가 있는 곳을 알려주시면 폐차와 수출 중 유리한 쪽을 상담 후 확인해 드립니다. "
                                f"전국 어디든 협력업체가 출장 방문합니다. {contact_line}."),
            "SMS_BUTTON": sms_btn, "BAR_SECOND": bar_second,
            "PHONE_TEL": phone_tel, "PHONE_DISPLAY": phone_disp,
            "YOUTUBE_URL": esc(cfg["youtube_url"]), "BLOG_URL": esc(cfg["blog_url"]), "AREA_LINKS": area,
        }

        def sub(m: re.Match) -> str:
            if m.group(1) not in values:
                raise KeyError(f"안내 템플릿 자리 {m.group(1)} 에 대응하는 값이 없습니다")
            return values[m.group(1)]

        html_text = re.sub(r"\{\{(\w+)\}\}", sub, template).replace("{{BAR_COLS}}", bar_cols)
        out = OUT / g["file"]
        old_text = out.read_text(encoding="utf-8") if out.exists() else None
        html_text = with_updated_date(html_text, old_text)
        if old_text != html_text:
            out.write_text(html_text, encoding="utf-8")
            changed.append(f"guide/{quote(g['file'])}")
            print(f"렌더링: guide/{g['file']}")
    return changed


def main() -> None:
    from build_site import CONFIG, GU_DATA, REGIONS, load_json
    from sitemap_lib import update_sitemap

    changed = render_all(load_json(REGIONS), load_json(CONFIG), load_json(GU_DATA, default=[]))
    update_sitemap(ROOT, [], paths=changed)
    print(f"완료: 안내 페이지 {len(changed)}개 변경")


if __name__ == "__main__":
    main()
