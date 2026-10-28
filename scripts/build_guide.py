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
import analytics

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "guide.html"
DONG_TEMPLATE = ROOT / "templates" / "region-landing-v2.html"
OUT = ROOT / "guide"
BAN_RE = re.compile(r"보장|무조건|100%|1위|1등|최저가|최고가|최대(?!한)|실시간\s*접수|\d[\d,.]*\s*(원|만원|만 원|천원|억)|₩")
# 법령 과태료·범칙금 금액(2026-10-18 병한님): 같은 문장에 이 낱말이 있으면 안내 페이지에서만 통과(폐차 금액·견적은 여전히 금지)
FINE_WORD_RE = re.compile(r"과태료|범칙금|가산금")


def fine_amount(text: str, start: int, end: int) -> bool:
    """text[start:end] 의 금액이 과태료·범칙금·가산금을 말하는 문장 안에 있는지(문장 끝은 . ! ? 와 태그 꺾쇠로 자른다)."""
    s = max(text.rfind(c, 0, start) for c in ".!?<>\n") + 1
    ends = [i for i in (text.find(c, end) for c in ".!?<>\n") if i != -1]
    return bool(FINE_WORD_RE.search(text[s:min(ends) if ends else len(text)]))


def ban_hits(text: str) -> list[str]:
    """BAN_RE 에 걸린 낱말. 과태료·범칙금 문장의 금액은 뺀다."""
    return [m.group(0) for m in BAN_RE.finditer(text) if not (m.group(1) and fine_amount(text, m.start(), m.end()))]

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
            # 한눈에 보기 표(2026-10-22 Fable): 단계 × 하는 일·소요시간·누가·준비물. 같은 줄로 HowTo 구조화 데이터를 만든다
            ("한눈에 보기", "폐차는 다섯 단계입니다. 단계마다 걸리는 시간·하는 사람·준비물을 정리했습니다", [
                ("table", (("단계", "하는 일", "소요시간", "누가", "준비물"), [
                    ("① 신청", "차량번호·연락처를 남기면 폐차와 수출 중 유리한 쪽을 상담합니다", "신청 당일 연락",
                     "손님 → 저희(상담·연결)", "차량번호, 연락처"),
                    ("② 차량 확인·입금", "기사가 차 상태를 확인하면 먼저 입금합니다", "방문 일정은 상담 때 확인",
                     "확인은 폐차장 기사, 입금은 저희가 손님께 직접", "본인: 신분증·자동차등록증 / 대리인·법인·상속: 필요 서류 안내 참고"),
                    ("③ 견인·방문", "입금 뒤 차를 가져갑니다(시동이 안 걸리는 차도 견인)", "차량 확인 당일",
                     "전국 등록(관허) 폐차장", "차 열쇠(없어도 상담 가능)"),
                    ("④ 말소 등록", "차를 해체하고 자동차 등록을 말소합니다", "압류 없는 보통 폐차는 입고 당일~다음날 / 차령초과 말소는 45~60일",
                     "자동차해체재활용업 등록(관허) 폐차장만 가능, 저희는 가까운 등록(관허) 폐차장으로 연결", "②에서 받은 서류로 진행"),
                    ("⑤ 말소증 문자", "말소증을 문자로 보내드립니다", "말소 끝난 날", "저희 → 손님", "없음"),
                ], "폐차 절차 5단계")),
                ("p", "대리인·법인·상속 차량은 준비물이 다릅니다. 상황별 서류는 아래 안내에 정리했습니다."),
                ("links", ["폐차-필요-서류.html", "상속차-법인차-서류.html"]),
                ("note", "폐차(해체)는 자동차해체재활용업으로 등록된 관허 폐차장만 할 수 있습니다. 저희는 전국 등록 폐차장과 함께 가까운 관허 폐차장으로 연결해 드립니다."),
            ]),
            ("1. 폐차 신청", "차량번호와 연락처만 남기시면 됩니다", [
                ("p", "폐차 신청은 차량번호와 연락처를 남겨 상담을 받는 단계입니다."),
                ("p", "전화나 견적 폼으로 남기시면 바로 연락드립니다. 차종·연식·차 상태(시동이 걸리는지, 사고가 있었는지)와 차가 있는 곳을 듣고, 폐차와 수출 중 어느 쪽이 나은지 통화에서 바로 말씀드립니다. 명의 상황(본인·대리인·법인·상속·압류)에 맞는 서류도 이때 안내해 드립니다."),
            ]),
            ("2. 차량 확인·입금", "차를 보고 먼저 입금합니다", [
                ("p", "차량 확인·입금은 방문한 기사가 차 상태를 확인한 뒤 돈을 먼저 보내드리는 단계입니다."),
                ("p", "차량 확인하면 먼저 입금하고, 그 다음에 차를 가져갑니다. 입금은 저희가 손님께 직접 보내드립니다. 방문 날짜와 시간은 상담 때 정합니다."),
            ]),
            ("3. 견인·방문", "차가 있는 곳으로 갑니다", [
                ("p", "견인은 등록(관허) 폐차장 기사가 차가 있는 곳으로 가서 차를 가져가는 단계입니다."),
                ("p", "시동이 안 걸리거나 사고로 움직이지 못하는 차도 견인차가 갑니다. 지하주차장이나 좁은 골목은 위치를 미리 알려주시면 맞는 차를 보냅니다. 견인비는 따로 없어요. 먼 거리나 시동 안 걸리는 차도 견인차가 직접 갑니다."),
            ]),
            ("4. 말소 등록", "등록을 지워야 폐차가 끝납니다", [
                ("p", "말소 등록은 자동차 등록을 지워 차에 붙는 세금과 과태료가 더 생기지 않게 하는 단계입니다."),
                ("p", "차를 해체하는 일은 자동차해체재활용업으로 등록된 관허 폐차장만 할 수 있고, 말소 등록도 그 폐차장이 대신 신청합니다. 압류 없는 보통 폐차는 입고 당일~다음날 말소되고, 압류·저당이 남아 차령초과 말소로 가는 차는 45~60일 걸립니다. 기간이 더 걸리는 차는 상담 때 미리 알려드립니다."),
            ]),
            ("5. 말소증 문자", "끝났다는 증명을 휴대폰으로 받습니다", [
                ("p", "말소증 문자는 말소가 끝났다는 증명을 휴대폰으로 받아 보시는 단계입니다."),
                ("p", "말소 끝나면 말소증을 문자로 보내드립니다. 책임보험(의무보험)은 말소 전까지 유지하셔야 과태료가 붙지 않고, 해지는 말소증을 가지고 가입한 보험사에 연락해 진행합니다. 자동차세처럼 차에 붙는 세금은 말소된 날을 기준으로 정리되며, 정산 내용은 관할 관청과 보험사에 확인해 주세요."),
            ]),
            ("유형별로 걸리는 기간", "차와 서류 상황에 따라 기간이 다릅니다", [
                ("rows", [
                    ("일반 폐차", "압류·저당이 없는 차량. 방문 일정은 상담 때 정하고, 말소는 입고 당일~다음날입니다."),
                    ("차령초과 말소", "차령 기준을 넘겨 압류·저당이 남아 있어도 말소하는 경우. 45~60일 걸립니다."),
                    ("조기폐차", "노후 경유차 지원 제도로 하는 경우. 지자체 사전 승인을 받은 뒤 진행합니다."),
                    ("상속 폐차", "명의자가 돌아가신 차량. 상속 서류가 준비되면 당일 접수합니다."),
                ]),
                ("note", "처리 기간은 지역·서류 상황에 따라 달라질 수 있습니다."),
            ]),
        ],
        "faqs": [
            ("차를 직접 가져가야 하나요?", "아니요, 차가 있는 곳으로 기사가 찾아갑니다. 견인비는 따로 없어요. 먼 거리에 있는 차도 견인차가 직접 갑니다."),
            ("차가 있는 곳에 제가 없어도 되나요?", "네, 차 위치와 열쇠·서류를 어떻게 전달할지 미리 정하면 안 계셔도 진행할 방법을 함께 찾습니다. 상담 때 사정을 말씀해 주세요."),
            ("말소가 끝났는지 어떻게 알 수 있나요?", "말소 끝나면 말소증을 문자로 보내드립니다. 정부24에서 자동차등록원부를 떼어 직접 확인하실 수도 있습니다."),
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
                    ("압류·저당이 있어도 상담", "차령 기준을 넘긴 차는 압류·저당이 남아 있어도 말소할 수 있는 경우가 많습니다. 45~60일(약 1~2개월) 걸립니다."),
                    ("서류가 복잡한 차도 상담", "법인 부도 차량, 차는 없어졌는데 서류상 말소가 안 된 차량도 상담해 드립니다."),
                ]),
            ]),
        ],
        "faqs": [
            ("자동차등록증을 잃어버렸어요.", "등록증이 없어도 진행할 수 있는 방법이 있습니다. 신분증만 준비해 주시면 나머지는 안내해 드립니다."),
            ("명의자가 멀리 살아서 직접 못 와요.", "위임장과 명의자 인감증명서(또는 본인서명사실확인서)가 있으면 대리인이 진행할 수 있습니다."),
            ("공동명의 차량은 어떻게 하나요?", "명의자 모두의 서류가 필요할 수 있습니다. 명의 상황을 알려주시면 통화 때 바로 말씀드립니다."),
        ],
    },
    {
        "file": "조기폐차-지원-안내.html",
        "nav": "조기폐차 지원",
        # 걱정 칸에 이 낱말이 있는 사례를 "같은 상황의 실제 사례"로 붙인다(2026-10-27 병한님, guide_cases)
        "case_worry_words": ["조기폐차"],
        "case_sub": "조기폐차부터 물어보신 손님 사례입니다. 지역은 카드마다 표시됩니다",
        "title": "노후 경유차 조기폐차 지원 안내",
        "h1": "노후 경유차 조기폐차 지원,<br>이렇게 확인하세요",
        "desc": "배출가스 4·5등급 경유차는 지자체 조기폐차 지원 대상일 수 있습니다. 대상 확인, 사전 신청과 승인, 폐차까지 순서와 주의할 점을 정리했습니다. 지원 금액은 공고와 통화에서 안내.",
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
                    ("금액은 공고마다 다릅니다", "지원 금액은 공고와 차량에 따라 달라 이 페이지에는 적지 않습니다. 공고와 통화로 확인해 주세요."),
                ]),
                ("p", "구 페이지가 있는 지역은 그 페이지의 공공 정보 표에 확인된 지자체 공고를 함께 적어 두었습니다."),
            ]),
        ],
        "faqs": [
            ("승인 전에 차를 먼저 넘겨도 되나요?", "아니요, 지원을 받으시려면 승인 뒤에 폐차하셔야 합니다. 승인 전이라면 일정을 먼저 맞춰 드립니다."),
            ("지원 대상이 아니면 어떻게 하나요?", "일반 폐차나 수출 비교 상담으로 진행할 수 있습니다. 차 상태를 알려주시면 통화에서 말씀드립니다."),
            ("조기폐차와 수출을 같이 할 수 있나요?", "아니요, 조기폐차 지원은 폐차를 조건으로 하므로 보통 수출과 함께 진행하지 않습니다. 어느 쪽이 나은지 통화에서 바로 말씀드립니다."),
        ],
    },
    {
        "file": "폐차-수출-비교.html",
        "nav": "폐차 vs 수출",
        "title": "폐차 vs 수출 비교 안내",
        "h1": "폐차와 수출,<br>어느 쪽이 나을까요",
        "desc": "오래되거나 고장 난 차도 해외에서 찾는 차종이면 수출이 나을 수 있습니다. 폐차와 수출의 차이, 어떤 차가 어느 쪽에 맞는지, 비교 방법을 정리했습니다.",
        "lead": "폐차보다 수출이 더 받는 차가 있습니다. 반대로 폐차가 나은 차도 많습니다. 차마다 다르므로 차 상태를 듣고 통화에서 말씀드립니다.",
        "sections": [
            # 나란히 보기·수출 절차 표(2026-10-22 Fable). 수출 절차 표로 HowTo 구조화 데이터를 만든다
            ("폐차와 수출 나란히 보기", "어느 쪽이든 말소까지 함께 진행합니다", [
                ("table", (("구분", "폐차", "수출"), [
                    ("처리 주체", "자동차해체재활용업 등록(관허) 폐차장", "수출 업체"),
                    ("말소 종류", "폐차 말소(차를 해체하고 등록을 지움)", "수출말소(말소증에 \"수출말소\"로 찍힘)"),
                    ("걸리는 시간", "압류 없는 보통 폐차는 입고 당일~다음날 말소, 차령초과 말소는 45~60일", "차량 확인·입금 후 인수하면 보통 당일, 늦어도 다음날 수출말소(말소증 문자)"),
                    ("유리한 경향", "해외 수요가 적은 차종, 심하게 부서지거나 침수된 차, 조기폐차 지원을 받으려는 차", "해외에서 많이 찾는 차종, 엔진·변속기 상태가 괜찮은 차"),
                    ("압류가 있는 차", "차령초과 말소 등으로 폐차할 수 있는 경우가 많음", "압류가 남아 있으면 수출할 수 없음"),
                ], None)),
                ("note", "수출 여부는 차종만으로 정해지지 않고 시기·나라 사정에 따라 달라집니다. 상담 때 그 시점에 유리한 쪽으로 안내합니다."),
                ("note", "유리한 경향일 뿐 차마다 다릅니다. 폐차 보상금과 수출 시세를 둘 다 본 뒤 그때 유리한 쪽으로 안내합니다."),
            ]),
            ("수출 절차 한눈에 보기", "수출은 다섯 단계입니다. 단계마다 걸리는 시간·하는 사람·준비물을 정리했습니다", [
                ("table", (("단계", "하는 일", "소요시간", "누가", "준비물"), [
                    ("① 사진·차량 정보 확인", "앞·뒤·옆·계기판 사진과 차종·연식·시동 여부를 확인합니다", "신청 당일",
                     "손님 → 저희", "차량번호, 사진 4장(문자로)"),
                    ("② 수출 가능 여부 판단", "해외 수요·차 상태·압류 여부를 보고 수출과 폐차 중 유리한 쪽을 안내합니다", "통화에서 안내",
                     "저희(수출 시세와 폐차 보상금을 함께 봄)", "없음(압류가 남아 있으면 수출 불가)"),
                    ("③ 입금", "차량 확인하면 먼저 입금합니다", "차량 확인 당일",
                     "저희가 손님께 직접", "본인: 신분증·자동차등록증 / 대리인·법인·상속: 필요 서류 안내 참고"),
                    ("④ 차량 인수", "입금 뒤 차를 가져갑니다(시동이 안 걸리는 차도 견인)", "방문 일정은 상담 때 확인",
                     "수출 업체·견인 기사", "차 열쇠(없어도 상담 가능)"),
                    ("⑤ 수출말소", "수출 절차에 맞춰 말소하고, 말소증에 \"수출말소\"로 찍힙니다. 말소증은 문자로 보내드립니다", "차량 확인·입금 후 인수하면 보통 당일, 늦어도 다음날 수출말소(말소증 문자)",
                     "수출 업체", "③에서 받은 서류로 진행"),
                ], "수출 비교매입 절차 5단계")),
                ("p", "대리인·법인·상속 차량은 준비물이 다릅니다. 상황별 서류는 아래 안내에 정리했습니다."),
                ("links", ["폐차-필요-서류.html", "상속차-법인차-서류.html"]),
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
                ("p", "차종·연식·차 상태를 들은 뒤 폐차 보상금과 수출 시세를 함께 보고 유리한 쪽을 안내해 드립니다. 어느 쪽으로 정하든 말소까지 진행합니다. 견인비는 따로 없어요. 먼 거리나 시동 안 걸리는 차도 견인차가 직접 갑니다."),
                ("note", "수출이 늘 더 낫다는 뜻은 아닙니다. 차마다 다르므로 통화에서 말씀드립니다."),
            ]),
        ],
        "faqs": [
            ("시동이 안 걸리는 차도 수출과 비교할 수 있나요?", "네, 시동이 안 걸리는 차도 차 상태를 들은 뒤 비교해 드립니다. 어느 쪽이 나은지는 통화에서 말씀드립니다."),
            ("압류나 저당이 있는 차는요?", "네, 상담은 되지만 압류가 남아 있으면 수출은 할 수 없어 등록원부로 차령초과 말소 같은 폐차 방법을 먼저 확인해 드립니다. 저당만 있는 차는 진행 방법이 달라질 수 있어 함께 확인합니다."),
            ("비교만 해 보고 안 해도 되나요?", "네, 비교 상담만 받으시고 진행하지 않으셔도 됩니다."),
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
            ("비용이 드나요?", "견인비는 따로 없어요", [
                ("p", "견인비는 따로 없어요. 차가 멀리 있거나 시동이 안 걸리는 차도 견인차가 직접 갑니다. 폐차든 수출이든 같습니다."),
                ("note", "이 페이지에는 금액 숫자를 적지 않습니다. 차마다 다르므로 통화에서 말씀드립니다."),
            ]),
        ],
        "faqs": [
            ("전화로 바로 금액을 알 수 있나요?", "아니요, 정확한 금액은 차 상태를 확인해 상담 후 알려드립니다. 전화로는 차 정보를 듣고 어느 쪽이 나은지 방향을 먼저 말씀드립니다."),
            ("상담 때 들은 금액이 나중에 달라지기도 하나요?", "네, 현장에서 본 차 상태가 상담 때 들은 것과 다르면 달라질 수 있습니다. 처음에 차 상태를 정확히 알려주시면 좋습니다."),
            ("금액을 알아보려면 무엇이 필요한가요?", "차량번호와 차종·연식, 시동 여부, 차가 있는 곳을 알려주시면 됩니다. 사진이 있으면 더 정확합니다."),
        ],
    },
]


# 손님이 자주 걱정하는 것(2026-10-03): 상담 통화 손님 심리 지도의 걱정 9가지를 장마다 나눠 싣는다.
# 답은 사실 문구(견인비 따로 없음·먼저 입금·서류 상담 가능·말소증 문자·수출 비교)로만 쓰고 통계 숫자는 넣지 않는다.
WORRIES = {
    "폐차-절차.html": [
        ("세금·과태료가 계속 나오지 않을까", "차에 붙는 세금과 검사 과태료는 말소가 돼야 더 생기지 않습니다. 압류가 있어 말소가 늦어지는 차는 상담 때 기간을 먼저 말씀드리고, 말소 끝나면 말소증을 문자로 보내드립니다."),
        ("오래 걸리지 않을까", "압류가 있다고 재판을 거치는 것은 아닙니다. 기간이 더 걸리는 차는 상담 때 미리 알려드리고, 일반 폐차는 방문 일정부터 바로 잡습니다."),
    ],
    "폐차-필요-서류.html": [
        ("서류가 복잡하지 않을까", "압류·저당·상속·대리인 서류도 상담 가능합니다. 필요한 서류는 문자로 하나씩 정리해 드리고, 폐업한 법인처럼 어려운 경우도 어디서 무엇을 떼면 되는지 알려드립니다."),
        ("명의자가 따로 있는데 괜찮을까", "가족이 대신 연락하셔도 됩니다. 명의자분께 그대로 보여 드릴 수 있게 필요한 서류와 진행 순서를 문자로 보내드립니다."),
    ],
    "조기폐차-지원-안내.html": [
        ("돈을 못 받으면 어쩌나", "차량 확인하면 먼저 입금하고, 그 다음에 차를 가져갑니다. 조기폐차 지원금은 이와 따로 지자체가 명의자에게 직접 넣어 줍니다. 말소 끝나면 말소증을 문자로 보내드립니다."),
    ],
    "폐차-수출-비교.html": [
        ("수출로 하면 더 받지 않을까", "폐차보다 수출이 더 받는 차가 있습니다. 차마다 다르므로 폐차 전에 수출 시세와 비교해서 더 높은 쪽으로 안내합니다. 수출로 가면 수출 말소로 처리되어 나중에 확인할 수 있습니다."),
        ("믿고 맡겨도 될까", "먼저 돈을 보내 달라고 하지 않습니다. 차량 확인하면 먼저 입금하고, 그 다음에 차를 가져갑니다. 말소 끝나면 말소증을 문자로 보내드립니다."),
    ],
    "폐차-금액-정하는-방법.html": [
        ("금액이 생각보다 낮지 않을까", "왜 그 금액인지 이유를 함께 말씀드립니다. 다른 곳 견적 받으셨으면 금액 알려주세요. 비교해 드립니다. 사진을 보내 주시면 통화로 확인해 더 정확하게 안내합니다."),
        ("견인비를 따로 물지 않을까", "시동이 안 걸리거나 키가 없어도 견인차가 차가 있는 곳으로 갑니다. 견인비는 따로 없어요. 먼 거리에 있는 차도 견인차가 직접 갑니다."),
    ],
}
for _g in GUIDES:
    _g["sections"].append(("손님이 자주 걱정하는 것", "실제 상담 전화에서 자주 듣는 걱정과 답입니다", [("list", WORRIES[_g["file"]])]))


# 안내 5장의 첫 화면(예전 모양 그대로, 2026-10-14 templates/guide.html 에서 옮김). 주제 페이지는 first_screen.hero_top_html
OLD_HERO = """<header class="hero">
  <div class="wrap">
    <p class="updated">최종 업데이트: {{UPDATED_ON}}</p>
    {{BREADCRUMB}}
    <span class="badge">폐차 안내 · 전국 어디든 차 있는 자리로</span>
    <h1 class="display">{{H1}}</h1>
    <p class="oneplus" style="margin:0 0 16px;font-weight:800;font-size:clamp(16px,4.4vw,19px);line-height:1.4">폐차값과 수출값, 둘 다 알려드려요</p>
    <p class="sub">{{LEAD}}</p>
    <a class="btn btn-call" href="tel:{{PHONE_TEL}}"><svg><use href="#i-phone"/></svg>{{PHONE_DISPLAY}} 지금 전화하기</a>
    <p class="hint">{{CONTACT_LINE}}</p>
    <div class="trust"><span>전국 등록 폐차장과 진행</span><span>견인비 따로 없음</span><span>당일 접수</span></div>
  </div>
</header>
"""


# 주제 페이지(2026-10-14 5장, 2026-10-18 6장, scripts/topics.py). FAQ 는 실제 통화 FAQ 풀(variants.CALL_FAQ)·공통 질문에서 질문으로 가져온다
from topics import TOPICS, GUIDE_CROSS_LINKS  # noqa: E402
import variants as _V  # noqa: E402

_FAQ_POOL = dict(_V.CALL_FAQ) | dict(zip(_V.COMMON_FAQ_QUESTIONS, _V.DONG_FAQ[0]))
for _t in TOPICS:
    _t["faqs"] = [(q, _FAQ_POOL[q]) for q in _t["faq_questions"]] + list(_t["faqs_extra"])
ALL_GUIDES = GUIDES + TOPICS  # 상단 메뉴·맨 아래 "폐차 안내" 링크·유형별 안내 링크는 이 11장(2026-10-18)


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
        elif kind == "table":  # (머리줄, [줄…], HowTo 이름 또는 None) — HowTo 표는 data-howto 로 표시(2026-10-22)
            head, rows, howto = val
            body.append(table_html((head, rows), esc, howto=bool(howto)).strip())
        elif kind == "links":  # 주제 페이지 링크(2026-10-14)
            body.append(related_html(val, esc))
        elif kind == "list":
            body.append('<ul class="guide-list">' + "".join(f"<li><b>{esc(b)}</b>{esc(s)}</li>" for b, s in val) + "</ul>")
        else:
            raise ValueError(f"모르는 글 조각 {kind}")
    bg = ' style="background:#fff"' if i % 2 == 0 else ""
    return (f'  <section id="part{i + 1}"{bg}>\n    <div class="wrap">\n'
            f'      <h2 class="sec-title display">{esc(h2)}</h2>\n      <p class="sec-sub">{esc(sub)}</p>\n      '
            + "\n      ".join(body) + "\n    </div>\n  </section>\n")


# 5칸 단계 표는 휴대폰에서 글자가 두 자씩 끊기지 않게 최소 폭을 두고 옆으로 밀어 본다(2026-10-22)
HOWTO_STYLE = """
  .guide-table[data-howto] { min-width: 680px; }
  .guide-table[data-howto] tbody th { white-space: nowrap; }
  .guide-table tbody th { min-width: 5.5em; }
  .table-wrap:has(> [data-howto])::after { content: "← 표를 옆으로 밀어 보세요"; display: block; margin-top: 6px; font-size: 12px; color: #5E6E70; }
  @media (min-width: 720px) { .table-wrap:has(> [data-howto])::after { display: none; } }
"""


def howto_jsonld(g: dict) -> dict | None:
    """안내 페이지의 HowTo 표(table 조각에 HowTo 이름이 있는 것) → schema.org HowTo(2026-10-22). 단계 = 표의 줄."""
    for _, _, parts in g.get("sections", []):
        for kind, val in parts:
            if kind == "table" and val[2]:
                head, rows, name = val
                return {"@context": "https://schema.org", "@type": "HowTo", "name": name, "step": [
                    {"@type": "HowToStep", "position": i, "name": re.sub(r"^[①-⑳]\s*", "", r[0]),
                     "text": f"{r[1]}. " + " ".join(f"{h}: {c}." for h, c in zip(head[2:], r[2:]))}
                    for i, r in enumerate(rows, 1)]}
    return None


def guide_text(g: dict) -> str:
    out = [g["title"], g["h1"], g["desc"], g["lead"]]
    for h2, sub, parts in g["sections"]:
        out += [h2, sub]
        for kind, val in parts:
            if isinstance(val, str):
                out.append(val)
            elif kind == "table":
                out += list(val[0]) + [c for r in val[1] for c in r] + ([val[2]] if val[2] else [])
            elif kind == "links":
                continue
            else:
                out += [x for pair in val for x in pair]
    out += [x for qa in g["faqs"] for x in qa]
    return " ".join(out)


# 동·구·시 페이지 "폐차 유형별 안내" 칸 끝(2026-10-19 병한님): "이런 차도 됩니다" 버튼 5개 + 나머지 안내 작은 글자 한 줄.
# 첫 화면(hero)에는 넣지 않는다(압류 같은 낱말이 있어 check_pages 첫 화면 검사에 걸림)
TYPE_BUTTONS = [("압류 있는 차", "압류-있는-차-폐차.html"), ("11년 넘은 차 말소", "차령초과-폐차.html"),
                ("상속·법인차", "상속차-법인차-서류.html"), ("시동 안 걸리는 차", "시동-안-걸리는-차.html"),
                ("오래 세워둔 차", "방치차-오래-세워둔-차.html"), ("저당만 있는 차", "저당만-있는-차.html")]
# 버튼 = 주제 페이지 6장 전부(2026-10-20 저당을 작은 글자에서 버튼으로 옮김), 작은 글자 = 안내 5장
TYPE_MORE = [("폐차 절차", "폐차-절차.html"), ("필요 서류", "폐차-필요-서류.html"),
             ("수출 비교", "폐차-수출-비교.html"), ("금액 정하는 방법", "폐차-금액-정하는-방법.html"), ("조기폐차", "조기폐차-지원-안내.html")]


def guide_links_html(prefix: str = "../") -> str:
    """동·구·시 페이지 "이런 차도 됩니다" 칸에 넣는 안내 11장 링크: 주제 6장 버튼 + 안내 5장 작은 글자 한 줄(2026-10-19, 2026-10-20 버튼 6개)."""
    from build_site import esc
    files = [f for _, f in TYPE_BUTTONS + TYPE_MORE]
    if sorted(files) != sorted(x["file"] for x in ALL_GUIDES):  # 안내 페이지를 새로 만들면 여기 둘 중 한 곳에 넣어야 한다
        raise SystemExit("build_guide.TYPE_BUTTONS·TYPE_MORE 가 안내·주제 페이지 목록과 다름")
    if sorted(f for _, f in TYPE_BUTTONS) != sorted(t["file"] for t in TOPICS):  # 버튼은 주제 페이지 전부(2026-10-20)
        raise SystemExit("build_guide.TYPE_BUTTONS 는 주제 페이지(topics.TOPICS) 전부여야 함")

    def a(label: str, f: str) -> str:
        return f'<a href="{prefix}guide/{esc(f)}">{esc(label)}</a>'
    return ('<div class="type-links"><p class="type-title">이런 차도 됩니다</p>'
            '<div class="type-btns">' + "".join(a(l, f) for l, f in TYPE_BUTTONS) + "</div>"
            '<p class="type-more">다른 안내: ' + " · ".join(a(l, f) for l, f in TYPE_MORE) + "</p></div>")


def related_html(files: list[str], esc) -> str:
    """안내·주제 페이지 사이 링크 한 줄: "관련 안내: 압류 있는 차 · 차령초과 말소"."""
    nav = {x["file"]: x["nav"] for x in ALL_GUIDES}
    return ('<p class="note related">관련 안내: '
            + " · ".join(f'<a href="{esc(f)}">{esc(nav[f])}</a>' for f in files) + "</p>")


def topic_text(t: dict) -> str:
    out = [t["h1"], t["lead"], t["desc"], t["answer"], t["hook"], t["route"], t.get("case_note", "")]
    out += [x for pair in t["pieces"] + t["worries"] + t["faqs"] for x in pair]
    out += [label for label, _ in sources(t)]
    if t.get("table"):
        out += list(t["table"][0]) + [x for row in t["table"][1] for x in row]
    return " ".join(out)


def sources(t: dict) -> list[tuple[str, str]]:
    """hook 뒤 출처: (글, 주소) 한 쌍 또는 여러 쌍 목록(2026-10-18) → 목록으로."""
    src = t.get("hook_source") or []
    return [src] if isinstance(src, tuple) else list(src)


def topic_sections_html(t: dict, n0: int, cases: list[dict], esc) -> str:
    """주제 페이지 본문: 시리즈 한 줄("폐차 사전 N편") → 한 줄 답 → 조각("사전 n번") + 내 차는 어디로(상담) → 걱정 3개 → 같은 상황 사례(있을 때만)."""
    from build_site import case_cards_html
    # 시리즈 표시(2026-10-22 눈가리개 감사 6번): "n/36" 꼬리표 대신 글 맨 위 "폐차 사전 N편 — 압류 있는 차" 한 줄.
    # 조각 번호(주제마다 6개씩 이어지는 번호)는 그대로 두고 "사전 n번"으로 읽히게 쓴다
    part = n0 // 6 + 1
    series = (f'      <p class="series">폐차 사전 {part}편 — {esc(t["nav"])}'
              f' <span>(조각 {n0}~{n0 + len(t["pieces"]) - 1}번)</span></p>\n')
    pieces = "".join(
        f'<li><span class="piece-no">사전 {n0 + k}번</span><b>{esc(h)}</b><span>{esc(x)}</span></li>'
        for k, (h, x) in enumerate(t["pieces"]))
    out = [
        '  <section id="answer" style="background:#fff">\n    <div class="wrap">\n' + series +
        '      <h2 class="sec-title display">한 줄로 답하면</h2>\n'
        f'      <div class="local answer"><p><b>{esc(t["answer"])}</b></p><p>{esc(t["hook"])}</p></div>\n'
        + ('      <p class="note source">출처: ' + " · ".join(
            f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>' for label, url in sources(t))
           + "</p>\n" if sources(t) else "")
        + f'      {related_html(t["related"], esc)}\n    </div>\n  </section>\n',
        '  <section id="pieces">\n    <div class="wrap">\n'
        '      <h2 class="sec-title display">알아 두면 좋은 조건과 절차</h2>\n'
        '      <p class="sec-sub">규칙은 숨기지 않고 다 적었습니다. 내 차가 어느 쪽인지는 원부와 차 상태를 합쳐 봐야 나옵니다</p>\n'
        f'      <ol class="steps pieces">{pieces}</ol>\n'
        + table_html(t.get("table"), esc)
        + '      <div class="route">\n        <h3>내 차는 어디로?</h3>\n'
        f'        <p>{esc(t["route"])}</p>\n'
        '        <p class="oneplus">폐차값과 수출값, 둘 다 알려드려요</p>\n'
        '        <p class="exit">차 번호·지역만 문자 주셔도 됩니다. 답만 받고 안 하셔도 됩니다.</p>\n'
        '      </div>\n    </div>\n  </section>\n',
        '  <section id="worries" style="background:#fff">\n    <div class="wrap">\n'
        '      <h2 class="sec-title display">손님이 자주 걱정하는 것</h2>\n'
        '      <p class="sec-sub">실제 상담 전화에서 자주 듣는 걱정과 답입니다</p>\n'
        '      <ul class="guide-list">' + "".join(f"<li><b>{esc(h)}</b>{esc(x)}</li>" for h, x in t["worries"]) + "</ul>\n"
        '    </div>\n  </section>\n',
    ]
    picked = topic_cases(t, cases)[0][:TOPIC_CASES_MAX]
    note = t.get("case_note", "")  # 사례 칸 바로 위 한 줄(2026-10-18). 카드가 없어도 이 줄만 있으면 칸을 그린다
    if picked or note:
        out.append('  <section id="cases">\n    <div class="wrap">\n'
                   '      <h2 class="sec-title display">같은 상황의 실제 사례</h2>\n'
                   + ('      <p class="sec-sub">지역은 카드마다 표시됩니다</p>\n' if picked else "")
                   + (f'      <p class="note">{esc(note)}</p>\n' if note else "")
                   + (f'      {case_cards_html(picked, video=False)}\n' if picked else "")
                   + '    </div>\n  </section>\n')
    return "".join(out)


def table_html(table, esc, howto: bool = False) -> str:
    """조각 아래 표 하나(2026-10-18, topics.py 의 table = (머리줄, [줄…])). howto 면 HowTo 구조화 데이터와 짝인 표(data-howto)."""
    if not table:
        return ""
    head, rows = table
    return ('      <div class="table-wrap"><table class="guide-table"' + (" data-howto" if howto else "") + ">"
            "<thead><tr>" + "".join(f'<th scope="col">{esc(h)}</th>' for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join((f'<th scope="row">{esc(c)}</th>' if i == 0 else f"<td>{esc(c)}</td>")
                                        for i, c in enumerate(r)) + "</tr>" for r in rows)
            + "</tbody></table></div>\n")


# 주제 페이지 사례·쇼츠 자동 붙이기(2026-10-19 병한님)
TOPIC_CASES_MAX = 4   # 주제마다 사례 카드 최신 4건까지(손으로 고른 cases 가 맨 앞)
TOPIC_SHORTS_MAX = 2  # 쇼츠 최대 2개(check_pages 가 주제 페이지만 2개까지 허용)
# 사례 카드 글자(제목·요약·지역)에 섞이면 그 사례를 뺀다: 전화번호·차번호·금액
CARD_LEAK_RE = re.compile(r"\d{2,4}-\d{3,4}-\d{4}|01[016789]\d{7,8}|\d{2,3}\s?[가-힣]\s?\d{4}|\d[\d,.]*\s*(?:원|만원|만 원|천원|억)|₩")


def case_text(c: dict) -> str:
    """주제 낱말을 찾는 글(case_story.topic_text): situation·method·summary·facts·걱정·확인·이유,
    "압류·저당 없음"처럼 없음·없는·아님 앞 낱말은 뺌(2026-10-25)."""
    import case_story
    return case_story.topic_text(c)


def case_date(c: dict) -> str:
    m = re.search(r"case-(\d{4})(\d{2})(\d{2})", c["slug"])
    return c.get("date") or (f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else "")


def card_leak(c: dict) -> str:
    """카드에 보이는 글자에 전화번호·차번호·금액이 있으면 그 낱말, 없으면 빈 문자열."""
    region = ((c.get("sigungu") or c.get("sido") or "") + " " + (c.get("dong") or "")).strip()
    import case_story
    m = CARD_LEAK_RE.search(" ".join([c.get("title") or "", c.get("summary") or "", case_story.card_line(c), region]))
    return m.group(0) if m else ""


def guide_cases(g: dict, cases: list[dict]) -> list[dict]:
    """안내 페이지 사례(2026-10-27): 걱정 칸에 case_worry_words 낱말이 있는 사례, 최신순 TOPIC_CASES_MAX 건.
    주제 페이지와 같이 카드 글자에 전화번호·차번호·금액이 섞인 사례(card_leak)는 뺀다."""
    words = g.get("case_worry_words") or []
    hits = [c for c in cases if any(w in ((c.get("story") or {}).get("걱정") or "") for w in words) and not card_leak(c)]
    return sorted(hits, key=lambda c: (case_date(c), c["slug"]), reverse=True)[:TOPIC_CASES_MAX]


def guide_cases_html(g: dict, cases: list[dict], esc) -> str:
    """안내 페이지 맨 아래 "같은 상황의 실제 사례" 칸. 붙은 사례가 없으면 칸을 그리지 않는다."""
    from build_site import case_cards_html
    picked = guide_cases(g, cases)
    if not picked:
        return ""
    return ('  <section id="cases">\n    <div class="wrap">\n'
            '      <h2 class="sec-title display">같은 상황의 실제 사례</h2>\n'
            f'      <p class="sec-sub">{esc(g.get("case_sub") or "지역은 카드마다 표시됩니다")}</p>\n'
            f'      {case_cards_html(picked, video=False)}\n'
            '    </div>\n  </section>\n')


def topic_cases(t: dict, cases: list[dict]) -> tuple[list[dict], list[tuple[str, str]]]:
    """주제에 붙는 사례 전부(손으로 고른 것 → 낱말이 맞는 사례 최신순)와 카드 글자 때문에 뺀 사례 [(slug, 이유)]."""
    by_slug = {c["slug"]: c for c in cases}
    manual = [by_slug[x] for x in t["cases"] if x in by_slug]
    words = t.get("case_words") or []
    skip = set(t.get("cases_skip") or [])  # 낱말은 맞지만 그 주제 예시로 어색해 뺀 사례(2026-10-27)
    auto = sorted((c for c in cases if c not in manual and c["slug"] not in skip and any(w in case_text(c) for w in words)),
                  key=lambda c: (case_date(c), c["slug"]), reverse=True)
    picked, skipped = [], []
    for c in manual + auto:
        leak = card_leak(c)
        if leak:
            skipped.append((c["slug"], leak))
        else:
            picked.append(c)
    return picked, skipped


def topic_shorts(t: dict, attached: list[dict]) -> list[dict]:
    """주제 페이지 쇼츠 최대 2개: topics.py 의 shorts 가 먼저, 그다음 붙은 사례 순서대로 그 사례에 짝 맞춘 쇼츠(최근 것부터).
    글자는 영상 제목 대신 우리 문구("○○동 ○○ 사례 영상")만 쓴다."""
    import shorts
    videos = shorts.load_matches().get("videos", {})
    out = []
    m = re.search(r"(?:shorts/|youtu\.be/|v=)([A-Za-z0-9_-]{6,})", (t.get("shorts") or "").strip())
    if m:
        v = videos.get(m.group(1))
        if v and v.get("published"):
            out.append({"id": m.group(1), **v, "label": f"{t['nav']} 영상", "desc": t["answer"], "page": ""})
        else:
            print(f"  주의: {t['file']} 의 shorts {m.group(1)} 은 data/shorts_matches.json 에 올린 날이 없어 넣지 않음")
    for c in attached:
        for vid, v in sorted(videos.items(), key=lambda kv: kv[1].get("published", ""), reverse=True):
            if v.get("case") == c["slug"] and v.get("published") and vid not in {x["id"] for x in out}:
                out.append({"id": vid, **v, "label": shorts.case_label(c), "desc": c.get("summary", ""),
                            "page": f"cases/{c['slug']}.html"})
    out = out[:TOPIC_SHORTS_MAX]
    for i, v in enumerate(out):  # 같은 사례 영상이 둘이면 "… 사례 영상 2"로 구별
        if any(x["label"] == v["label"] for x in out[:i]):
            v["label"] = f"{v['label']} {i + 1}"
    return out


def shorts_html(t: dict, esc, attached: list[dict] = (), base: str = "") -> str:
    """유튜브 쇼츠 칸(2026-10-19): 사례 페이지와 같은 lite embed(누를 때만 불러옴, 자동재생 없음) + VideoObject.
    쇼츠가 없으면 칸을 그리지 않고 자리 표시만 남긴다."""
    import shorts
    picked = topic_shorts(t, list(attached))
    if not picked:
        return "<!-- [쇼츠 자리] scripts/topics.py 의 shorts 에 쇼츠 주소를 넣으면 여기에 영상이 들어갑니다 -->\n"
    return ('  <section id="shorts" style="background:#fff">\n    <div class="wrap">\n'
            '      <h2 class="sec-title display">영상으로 보기</h2>\n'
            '      <div class="topic-videos" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px">'
            + "".join(shorts.lite_html(v["id"], v["label"]) for v in picked) + "</div>\n"
            + "      " + shorts.lite_assets()
            + "".join(shorts.video_ld(v, v["label"], v["desc"], f"{base.rstrip('/')}/{v['page']}" if base and v["page"] else "")
                      for v in picked)
            + "\n    </div>\n  </section>\n")


# 주제 페이지에만 넣는 CSS(2026-10-18): 안내 5장은 내용이 그대로라 템플릿 <style> 끝 {{TOPIC_STYLE}} 은 빈칸
TOPIC_STYLE = """
  /* 조각 아래 표·출처 한 줄(2026-10-18) */
  .table-wrap { margin-top: 16px; overflow-x: auto; }
  .guide-table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 12px; overflow: hidden; font-size: 14px; }
  .guide-table th, .guide-table td { padding: 10px 12px; border-bottom: 1px solid rgba(23,40,43,.08); text-align: left; vertical-align: top; }
  .guide-table thead th { background: var(--teal-deep); color: #fff; font-weight: 700; }
  .guide-table tbody th { color: var(--teal-deep); }
  .note.source a { color: inherit; }"""


BOTTOM_FORM = """      <div class="quote-card" style="margin-top:16px;text-align:left">
        <h3>폐차값·수출값 둘 다 받기</h3>
        <p class="lead">차량번호와 연락처만 남기시면 바로 연락드립니다</p>
        <form class="quote-form" action="{FORM_ACTION}" method="{FORM_METHOD}">
          {FORM_HIDDEN}
          <input type="hidden" name="region" value="{REGION_FULL_NAME}">
          <input type="hidden" name="form" value="하단 견적 폼">
          <input type="checkbox" name="botcheck" class="hidden" style="display:none" tabindex="-1" autocomplete="off">
          <label for="t2-plate">차량번호</label>
          <input id="t2-plate" name="plate" type="text" inputmode="text" placeholder="예: 12가 3456" autocomplete="off">
          <label for="t2-phone">연락처</label>
          <input id="t2-phone" name="phone" type="tel" inputmode="tel" placeholder="010-0000-0000" maxlength="13" required autocomplete="tel">
          <label for="t2-car">연식 또는 차종 (선택)</label>
          <input id="t2-car" name="car" type="text" placeholder="예: 2015 그랜저" autocomplete="off">
          <button class="btn btn-call" type="submit"><svg><use href="#i-chat"/></svg>폐차·수출 비교 견적 받기</button>
          <p class="fine">남겨주신 정보는 견적 상담 연락에만 쓰며, 문의 시 <a href="../privacy.html">개인정보처리방침</a>에 동의한 것으로 봅니다.</p>
        </form>
      </div>"""


def render_all(regions: list[dict], cfg: dict, gu_data: list[dict], keep_dates: bool = False) -> list[str]:
    """안내 페이지 5장과 주제 페이지 5장(2026-10-14)을 렌더링하고, 내용이 바뀐 페이지 경로("guide/…", %인코딩) 목록을 돌려준다."""
    from build_site import (CASES_INDEX, UPDATED_MARK, area_links_html, esc, form_parts, page_script, load_json, page_jsonld,
                            tel_text, with_updated_date)
    from first_screen import hero_top_html, sms_link
    import og_image

    problems = [f"{g['file']}: 금액·단정 표현 '{x}'" for g in GUIDES for x in ban_hits(guide_text(g))]
    problems += [f"{t['file']}: 금액·단정 표현 '{x}'" for t in TOPICS for x in ban_hits(topic_text(t))]
    if problems:
        raise SystemExit("안내 페이지를 만들 수 없음:\n  " + "\n  ".join(problems))

    template = re.sub(r"<!DOCTYPE html>\s*<!--.*?-->", "<!DOCTYPE html>", TEMPLATE.read_text(encoding="utf-8"), count=1, flags=re.DOTALL)
    dong_tpl = DONG_TEMPLATE.read_text(encoding="utf-8")
    style = re.search(r"<style>.*?</style>", dong_tpl, flags=re.DOTALL).group(0)
    sprite = re.search(r'<svg width="0" height="0"[^>]*>.*?</svg>', dong_tpl, flags=re.DOTALL).group(0)
    script = re.search(r"<script>\s*\(function \(\).*?</script>", dong_tpl, flags=re.DOTALL).group(0)
    base = cfg["site_base_url"].rstrip("/")
    phone_tel, phone_disp = cfg["phone_tel"], cfg["phone_display"]
    text_disp = cfg.get("text_reply_display") or ""
    text_tel = re.sub(r"\D", "", text_disp)
    contact_line = f"전화 {phone_disp}" + (f" / 문자 {text_disp}" if text_disp else "")
    kakao = cfg.get("kakao_channel_url")
    kakao_bar = (f'<a class="btn btn-kakao" href="{esc(kakao)}" target="_blank" rel="noopener noreferrer">카톡</a>' if kakao else "")
    if text_tel:
        sms_href = f'href="{esc(sms_link({"sms_number": text_tel}, ""))}"'
        sms_btn = f'<a class="btn btn-sms" {sms_href}><svg><use href="#i-chat"/></svg>문자 {esc(text_disp)}</a>'
        bar_second = f'<a class="btn btn-sms" {sms_href}><svg><use href="#i-chat"/></svg>문자</a>' + kakao_bar
        bar_cols = "2fr 1fr 1fr" if kakao else "2fr 1fr"
    else:
        sms_btn, bar_cols = "", "3fr 2fr"
        bar_second = '<a class="btn btn-quote" href="#consult" style="background:#fff"><svg><use href="#i-chat"/></svg>상담 안내</a>'
    area = area_links_html(regions, gu_data)
    cases = load_json(CASES_INDEX, default=[])
    # 주제 페이지 맨 아래 "최근 문의 지역"(2026-10-20, 2026-10-22 이름 바꿈·본문 해시에서 뺌): 첫 화면과 같은 구·시군 10곳(pick_index_requests.popular_gu)
    from build_site import SIDO_SHORT, gu_file
    from pick_index_requests import popular_gu
    popular = popular_gu(10)
    popular_html = ('  <section id="popular" style="background:#fff">\n    <div class="wrap">\n'
                    '      <h2 class="sec-title display">최근 문의 지역</h2>\n'
                    '      <p class="sec-sub">최근 문의가 온 곳과 상담이 많은 시·군입니다. 차가 있는 곳의 페이지에서 동별 안내를 보실 수 있습니다</p>\n'
                    '      <div class="neighbors">'
                    + "".join(f'<a href="../gu/{esc(gu_file(sd, sg))}">{esc(sg or SIDO_SHORT[sd])} 폐차 안내</a>' for sd, sg in popular)
                    + "</div>\n    </div>\n  </section>") if popular else ""
    cross = {}
    for f, idx, files in GUIDE_CROSS_LINKS:
        cross.setdefault(f, {})[idx] = files

    OUT.mkdir(exist_ok=True)
    changed = []
    for n, g in enumerate(ALL_GUIDES):
        topic = n >= len(GUIDES)
        canonical = f"{base}/guide/{quote(g['file'])}"
        title = g["h1"] if topic else g["title"]
        # 주제 페이지 제목 꼬리(2026-10-18): topics.py 의 tail("원부 확인 상담" / "폐차·수출 비교 상담") + 대표번호
        meta_title = f"{title} | {g.get('tail') or '폐차·수출 비교 상담'} · 전화 {phone_disp}"
        # 설명 글에는 010 번호를 넣지 않는다(네이버가 가림, 2026-10-16). 본문의 contact_line 은 그대로
        meta_desc = f"{g['desc']} 전화 {phone_disp}" + (" · 문자 상담 가능." if text_disp else ".")
        nav = "".join(
            f'<a href="{esc(x["file"])}"' + (' aria-current="page"' if x is g else "") + f">{esc(x['nav'])}</a>" for x in ALL_GUIDES)
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
        howto = howto_jsonld(g)
        if howto:
            jsonld.append(howto)
        values = {
            "ANALYTICS_BODY": analytics.body_end_html(cfg),
            "ANALYTICS": analytics.head_html(cfg, "guide", "전국"),
            "META_TITLE": esc(meta_title), "SITE_NAME": esc(cfg["site_name"]), "META_DESC": esc(meta_desc), "CANONICAL": canonical,
            "JSONLD": json.dumps(jsonld, ensure_ascii=False), "PAGE_JSONLD": page_jsonld(meta_title, canonical),
            "STYLE": style, "SPRITE": sprite, "GUIDE_NAV": nav, "UPDATED_ON": UPDATED_MARK, "BREADCRUMB": crumbs,
            "FAQ_HTML": "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{tel_text(esc(a))}</p></details>" for q, a in g["faqs"]),
            # 압류 페이지(no_export, 2026-10-18)는 수출 비교 대신 원부 확인으로 쓴다
            "CONSULT_SUB": esc("차 번호로 원부부터 같이 봅니다" if g.get("no_export") else "폐차 전에 수출과 비교해서 유리한 쪽으로"),
            "CONSULT_TEXT": tel_text(esc(("차 번호와 차가 있는 곳을 알려주시면 원부를 보고 압류를 풀고 폐차할지, 차령초과말소로 갈지 통화 때 바로 말씀드립니다. "
                                 if g.get("no_export") else
                                 "차 상태와 차가 있는 곳을 알려주시면 폐차와 수출 중 유리한 쪽을 통화 때 바로 말씀드립니다. ")
                                + f"금액은 상담 후 확인해 드립니다. 전국 어디든 기사가 차 있는 자리로 갑니다. {contact_line}.")),
            "SMS_BUTTON": sms_btn, "BAR_SECOND": bar_second,
            "PHONE_TEL": phone_tel, "PHONE_DISPLAY": phone_disp,
            "YOUTUBE_URL": esc(cfg["youtube_url"]), "BLOG_URL": esc(cfg["blog_url"]), "AREA_LINKS": area,
        }
        if topic:
            # 주제 페이지: 동 페이지와 같은 첫 화면·하단 폼·폼 스크립트(숨은 칸 Page·Source 포함), 대표 이미지
            n0 = (n - len(GUIDES)) * 6 + 1
            form = form_parts(cfg, "주제 " + g["nav"], "주제 페이지 " + g["nav"], canonical, meta_title)
            hero = ('<header class="hero hero-v3">\n'
                    + hero_top_html(cfg, "", form, crumb=crumbs, updated=UPDATED_MARK, h1=g["h1"], lead=g["lead"])
                    + "\n</header>")
            name, suffix = g["og"]
            values.update({
                "HERO_HTML": hero,
                "SECTIONS_HTML": topic_sections_html(g, n0, cases, esc),
                "AFTER_FAQ": shorts_html(g, esc, topic_cases(g, cases)[0], base),
                "BOTTOM_FORM": BOTTOM_FORM.format(**form).replace(
                    "폐차·수출 비교 견적 받기", "차 번호로 원부 확인 상담 받기" if g.get("no_export") else "폐차·수출 비교 견적 받기"),
                "SCRIPT": page_script(script, cfg),
                "TOPIC_STYLE": TOPIC_STYLE,
                "POPULAR_HTML": popular_html,
                "OG_META": og_image.parts(g["file"][:-5], name, base, phone_disp, suffix=suffix)["OG_META"],
            })
        else:
            parts_by_idx = cross.get(g["file"], {})
            sections = []
            for i, (h2, sub_, parts) in enumerate(g["sections"]):
                extra = [("links", parts_by_idx[i])] if i in parts_by_idx else []
                sections.append(section_html(i, h2, sub_, list(parts) + extra, esc))
            values.update({
                "H1": esc(g["h1"]).replace("&lt;br&gt;", "<br>"), "LEAD": esc(g["lead"]), "CONTACT_LINE": tel_text(esc(contact_line)),
                "SECTIONS_HTML": "".join(sections) + guide_cases_html(g, cases, esc),
                "AFTER_FAQ": "", "BOTTOM_FORM": "", "SCRIPT": "", "OG_META": "", "POPULAR_HTML": "",
                # 표가 있는 안내 페이지만 표 모양(.guide-table)을 넣는다(2026-10-22, 나머지 안내 페이지는 그대로)
                "TOPIC_STYLE": TOPIC_STYLE + HOWTO_STYLE if any(k == "table" for *_, ps in g["sections"] for k, _ in ps) else "",
            })

        def sub(m: re.Match) -> str:
            if m.group(1) not in values:
                raise KeyError(f"안내 템플릿 자리 {m.group(1)} 에 대응하는 값이 없습니다")
            return values[m.group(1)]

        if not topic:
            values["HERO_HTML"] = re.sub(r"\{\{(\w+)\}\}", sub, OLD_HERO.rstrip("\n"))
        html_text = re.sub(r"\{\{(\w+)\}\}", sub, template).replace("{{BAR_COLS}}", bar_cols)
        out = OUT / g["file"]
        old_text = out.read_text(encoding="utf-8") if out.exists() else None
        html_text = with_updated_date(html_text, old_text, keep_dates=keep_dates, path=out)
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
