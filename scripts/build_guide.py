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
                    ("방문·입금·인수", "협력업체가 약속한 날 차가 있는 곳으로 갑니다. 차량 확인하면 먼저 입금하고, 그 다음에 차를 가져갑니다. 시동이 안 걸리거나 사고로 움직이지 못하는 차도 견인차가 갑니다."),
                    ("말소 처리", "말소 등록을 진행합니다. 말소 끝나면 말소증을 문자로 보내드립니다. 차령초과 말소처럼 기간이 더 걸리는 경우는 미리 알려 드립니다."),
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
                ("p", "말소 끝나면 말소증을 문자로 보내드립니다. 자동차보험 해지는 말소 뒤에 가입한 보험사에 연락해 진행합니다."),
                ("p", "자동차세처럼 차에 붙는 세금은 말소된 날을 기준으로 정리됩니다. 정산 내용은 관할 관청과 보험사에 확인해 주세요."),
            ]),
        ],
        "faqs": [
            ("차를 직접 가져가야 하나요?", "아니요, 차가 있는 곳으로 협력업체가 찾아갑니다. 견인비는 대부분 따로 받지 않고, 먼 거리처럼 따로 드는 경우는 상담 때 미리 말씀드립니다."),
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
            ("승인 전에 차를 먼저 넘겨도 되나요?", "아니요, 지원을 받으시려면 승인 뒤에 폐차하셔야 합니다. 승인 전이라면 일정을 먼저 맞춰 드립니다."),
            ("지원 대상이 아니면 어떻게 하나요?", "일반 폐차나 수출 비교 상담으로 진행할 수 있습니다. 차 상태를 알려주시면 상담 후 확인해 드립니다."),
            ("조기폐차와 수출을 같이 할 수 있나요?", "아니요, 조기폐차 지원은 폐차를 조건으로 하므로 보통 수출과 함께 진행하지 않습니다. 어느 쪽이 나은지 상담 후 확인해 드립니다."),
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
                ("p", "차종·연식·차 상태를 들은 뒤 폐차 보상금과 수출 시세를 함께 보고 유리한 쪽을 안내해 드립니다. 어느 쪽으로 정하든 말소까지 진행하며, 견인비는 대부분 별도 청구 없이 진행하고 먼 거리·시동 불가 같은 경우는 미리 안내합니다."),
                ("note", "수출이 늘 더 낫다는 뜻은 아닙니다. 차마다 다르므로 상담 후 확인합니다."),
            ]),
        ],
        "faqs": [
            ("시동이 안 걸리는 차도 수출과 비교할 수 있나요?", "네, 시동이 안 걸리는 차도 차 상태를 들은 뒤 비교해 드립니다. 어느 쪽이 나은지는 상담 후 확인합니다."),
            ("압류나 저당이 있는 차는요?", "네, 압류·저당이 있어도 비교 상담은 되고, 진행 방법이 달라질 수 있어 등록원부를 먼저 확인해 드립니다."),
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
            ("비용이 드나요?", "견인비는 대부분 따로 들지 않고, 드는 경우는 미리 안내합니다", [
                ("p", "견인비는 대부분 별도 청구 없이 진행합니다. 차가 멀리 있거나 시동이 안 걸려 견인이 따로 필요한 경우처럼 특수한 때는 상담 때 미리 알려드립니다. 폐차든 수출이든 같습니다."),
                ("note", "이 페이지에는 금액 숫자를 적지 않습니다. 차마다 다르므로 상담 후 확인해 드립니다."),
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
# 답은 사실 문구(견인비 미리 안내·먼저 입금·서류 상담 가능·말소증 문자·수출 비교)로만 쓰고 통계 숫자는 넣지 않는다.
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
        ("금액이 생각보다 낮지 않을까", "왜 그 금액인지 이유를 함께 말씀드립니다. 다른 곳 견적 받으셨으면 금액 알려주세요. 비교해 드립니다. 사진을 보내 주시면 상담 후 확인해 더 정확하게 안내합니다."),
        ("견인비를 따로 물지 않을까", "시동이 안 걸리거나 키가 없어도 견인차가 차가 있는 곳으로 갑니다. 견인비는 보통 따로 받지 않고, 먼 거리·시동 불가처럼 따로 드는 경우는 상담 때 먼저 말씀드립니다."),
    ],
}
for _g in GUIDES:
    _g["sections"].append(("손님이 자주 걱정하는 것", "실제 상담 전화에서 자주 듣는 걱정과 답입니다", [("list", WORRIES[_g["file"]])]))


# 안내 5장의 첫 화면(예전 모양 그대로, 2026-10-14 templates/guide.html 에서 옮김). 주제 페이지는 first_screen.hero_top_html
OLD_HERO = """<header class="hero">
  <div class="wrap">
    <p class="updated">최종 업데이트: {{UPDATED_ON}}</p>
    {{BREADCRUMB}}
    <span class="badge">폐차 안내 · 전국 출장 방문 상담</span>
    <h1 class="display">{{H1}}</h1>
    <p class="oneplus" style="margin:0 0 16px;font-weight:800;font-size:clamp(16px,4.4vw,19px);line-height:1.4">폐차 견적 1+1 — 폐차값과 수출값, 둘 다 알려드려요<small style="display:block;margin-top:4px;font-size:13px;font-weight:400;opacity:.85">1+1은 폐차 견적과 수출 견적, 두 가지를 함께 드린다는 뜻입니다.</small></p>
    <p class="sub">{{LEAD}}</p>
    <a class="btn btn-call" href="tel:{{PHONE_TEL}}"><svg><use href="#i-phone"/></svg>{{PHONE_DISPLAY}} 지금 전화하기</a>
    <p class="hint">{{CONTACT_LINE}}</p>
    <div class="trust"><span>전국 협력 네트워크</span><span>견인비 대부분 별도 청구 없음</span><span>당일 접수</span></div>
  </div>
</header>
"""


# 주제 페이지 5장(2026-10-14, scripts/topics.py). FAQ 는 실제 통화 FAQ 풀(variants.CALL_FAQ)·공통 질문에서 질문으로 가져온다
from topics import TOPICS, GUIDE_CROSS_LINKS  # noqa: E402
import variants as _V  # noqa: E402

_FAQ_POOL = dict(_V.CALL_FAQ) | dict(zip(_V.COMMON_FAQ_QUESTIONS, _V.DONG_FAQ[0]))
for _t in TOPICS:
    _t["faqs"] = [(q, _FAQ_POOL[q]) for q in _t["faq_questions"]] + list(_t["faqs_extra"])
ALL_GUIDES = GUIDES + TOPICS  # 상단 메뉴·맨 아래 "폐차 안내" 링크·유형별 안내 링크는 이 10장


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


def guide_links_html(prefix: str = "../") -> str:
    """동·구·시 페이지 "폐차 유형별 안내" 칸에 넣는 안내 10장 링크 한 줄(2026-10-14)."""
    from build_site import esc
    return ('<p class="type-links"><b>유형별 자세한 안내</b> '
            + " · ".join(f'<a href="{prefix}guide/{esc(x["file"])}">{esc(x["nav"])}</a>' for x in ALL_GUIDES) + "</p>")


def related_html(files: list[str], esc) -> str:
    """안내·주제 페이지 사이 링크 한 줄: "관련 안내: 압류 있는 차 · 차령초과 말소"."""
    nav = {x["file"]: x["nav"] for x in ALL_GUIDES}
    return ('<p class="note related">관련 안내: '
            + " · ".join(f'<a href="{esc(f)}">{esc(nav[f])}</a>' for f in files) + "</p>")


def topic_text(t: dict) -> str:
    out = [t["h1"], t["lead"], t["desc"], t["answer"], t["hook"], t["route"]]
    out += [x for pair in t["pieces"] + t["worries"] + t["faqs"] for x in pair]
    return " ".join(out)


def topic_sections_html(t: dict, n0: int, cases: list[dict], esc) -> str:
    """주제 페이지 본문: 한 줄 답 → 조각("폐차 사전 n/30") + 내 차는 어디로(상담) → 걱정 3개 → 같은 상황 사례(있을 때만)."""
    from build_site import case_cards_html
    total = len(TOPICS) * 6
    pieces = "".join(
        f'<li><span class="piece-no">폐차 사전 {n0 + k}/{total}</span><b>{esc(h)}</b><span>{esc(x)}</span></li>'
        for k, (h, x) in enumerate(t["pieces"]))
    out = [
        '  <section id="answer" style="background:#fff">\n    <div class="wrap">\n'
        '      <h2 class="sec-title display">한 줄로 답하면</h2>\n'
        f'      <div class="local answer"><p><b>{esc(t["answer"])}</b></p><p>{esc(t["hook"])}</p></div>\n'
        f'      {related_html(t["related"], esc)}\n    </div>\n  </section>\n',
        '  <section id="pieces">\n    <div class="wrap">\n'
        '      <h2 class="sec-title display">알아 두면 좋은 조건과 절차</h2>\n'
        '      <p class="sec-sub">규칙은 숨기지 않고 다 적었습니다. 내 차가 어느 쪽인지는 원부와 차 상태를 합쳐 봐야 나옵니다</p>\n'
        f'      <ol class="steps pieces">{pieces}</ol>\n'
        '      <div class="route">\n        <h3>내 차는 어디로?</h3>\n'
        f'        <p>{esc(t["route"])}</p>\n'
        '        <p class="oneplus">폐차 견적 1+1 — 폐차값과 수출값, 둘 다 알려드려요<small>1+1은 폐차 견적과 수출 견적, 두 가지를 함께 드린다는 뜻입니다.</small></p>\n'
        '        <p class="exit">차 번호·지역만 문자 주셔도 됩니다. 답만 받고 안 하셔도 됩니다.</p>\n'
        '      </div>\n    </div>\n  </section>\n',
        '  <section id="worries" style="background:#fff">\n    <div class="wrap">\n'
        '      <h2 class="sec-title display">손님이 자주 걱정하는 것</h2>\n'
        '      <p class="sec-sub">실제 상담 전화에서 자주 듣는 걱정과 답입니다</p>\n'
        '      <ul class="guide-list">' + "".join(f"<li><b>{esc(h)}</b>{esc(x)}</li>" for h, x in t["worries"]) + "</ul>\n"
        '    </div>\n  </section>\n',
    ]
    by_slug = {c["slug"]: c for c in cases}
    picked = [by_slug[x] for x in t["cases"] if x in by_slug]
    if picked:
        out.append('  <section id="cases">\n    <div class="wrap">\n'
                   '      <h2 class="sec-title display">같은 상황의 실제 사례</h2>\n'
                   '      <p class="sec-sub">지역은 카드마다 표시됩니다</p>\n'
                   f'      {case_cards_html(picked)}\n    </div>\n  </section>\n')
    return "".join(out)


def shorts_html(t: dict, esc) -> str:
    """유튜브 쇼츠 자리. 주소가 없으면 칸을 그리지 않고 자리 표시만 남긴다."""
    url = (t.get("shorts") or "").strip()
    m = re.search(r"(?:shorts/|youtu\.be/|v=)([A-Za-z0-9_-]{6,})", url)
    if not m:
        return "<!-- [쇼츠 자리] scripts/topics.py 의 shorts 에 쇼츠 주소를 넣으면 여기에 영상이 들어갑니다 -->\n"
    vid = m.group(1)
    return ('  <section id="shorts" style="background:#fff">\n    <div class="wrap">\n'
            '      <h2 class="sec-title display">영상으로 보기</h2>\n'
            '      <div class="videos"><figure class="video short">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{esc(vid)}" title="{esc(t["nav"])} 쇼츠" loading="lazy" '
            'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
            f'<figcaption><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">유튜브에서 보기</a></figcaption></figure></div>\n'
            '    </div>\n  </section>\n')


BOTTOM_FORM = """      <div class="quote-card" style="margin-top:16px;text-align:left">
        <h3>폐차·수출 견적 1+1 신청</h3>
        <p class="lead">차량번호와 연락처만 남기시면 바로 연락드립니다</p>
        <form class="quote-form" action="{FORM_ACTION}" method="{FORM_METHOD}">
          {FORM_HIDDEN}
          <input type="hidden" name="region" value="{REGION_FULL_NAME}">
          <input type="hidden" name="form" value="하단 견적 폼">
          <input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off">
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
    from build_site import (CASES_INDEX, UPDATED_MARK, area_links_html, esc, form_parts, load_json, page_jsonld,
                            with_updated_date)
    from first_screen import hero_top_html, sms_link
    import og_image

    problems = [f"{g['file']}: 금액·단정 표현 '{m.group(0)}'" for g in GUIDES for m in [BAN_RE.search(guide_text(g))] if m]
    problems += [f"{t['file']}: 금액·단정 표현 '{m.group(0)}'" for t in TOPICS for m in [BAN_RE.search(topic_text(t))] if m]
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
    cross = {}
    for f, idx, files in GUIDE_CROSS_LINKS:
        cross.setdefault(f, {})[idx] = files

    OUT.mkdir(exist_ok=True)
    changed = []
    for n, g in enumerate(ALL_GUIDES):
        topic = n >= len(GUIDES)
        canonical = f"{base}/guide/{quote(g['file'])}"
        title = g["h1"] if topic else g["title"]
        meta_title = f"{title} | 폐차·수출 비교 상담 · 전화 {phone_disp}"
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
        values = {
            "ANALYTICS_BODY": analytics.body_end_html(cfg),
            "ANALYTICS": analytics.head_html(cfg, "guide", "전국"),
            "META_TITLE": esc(meta_title), "META_DESC": esc(meta_desc), "CANONICAL": canonical,
            "JSONLD": json.dumps(jsonld, ensure_ascii=False), "PAGE_JSONLD": page_jsonld(meta_title, canonical),
            "STYLE": style, "SPRITE": sprite, "GUIDE_NAV": nav, "UPDATED_ON": UPDATED_MARK, "BREADCRUMB": crumbs,
            "FAQ_HTML": "\n      ".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in g["faqs"]),
            "CONSULT_TEXT": esc(f"차 상태와 차가 있는 곳을 알려주시면 폐차와 수출 중 유리한 쪽을 상담 후 확인해 드립니다. "
                                f"전국 어디든 협력업체가 출장 방문합니다. {contact_line}."),
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
                "AFTER_FAQ": shorts_html(g, esc),
                "BOTTOM_FORM": BOTTOM_FORM.format(**form),
                "SCRIPT": script.replace("{{PHONE_DISPLAY}}", phone_disp),
                "OG_META": og_image.parts(g["file"][:-5], name, base, phone_disp, suffix=suffix)["OG_META"],
            })
        else:
            parts_by_idx = cross.get(g["file"], {})
            sections = []
            for i, (h2, sub_, parts) in enumerate(g["sections"]):
                extra = [("links", parts_by_idx[i])] if i in parts_by_idx else []
                sections.append(section_html(i, h2, sub_, list(parts) + extra, esc))
            values.update({
                "H1": esc(g["h1"]).replace("&lt;br&gt;", "<br>"), "LEAD": esc(g["lead"]), "CONTACT_LINE": esc(contact_line),
                "SECTIONS_HTML": "".join(sections),
                "AFTER_FAQ": "", "BOTTOM_FORM": "", "SCRIPT": "", "OG_META": "",
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
