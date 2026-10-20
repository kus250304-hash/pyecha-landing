# 구글 서치 콘솔 색인 요청 기록

병한님이 구글 서치 콘솔(왼쪽 "URL 검사" → 주소 붙여 넣기 → "색인 생성 요청")로 손으로 요청한 주소 기록입니다(2026-10-18부터).

- 매일 루틴이 `python3 scripts/pick_index_requests.py --write` 로 그날 요청할 5개(2026-10-20부터, 예전 10개)를 골라 아래에 날짜와 함께 덧붙이고, 아침 보고(오전 6시 55분) 맨 끝 "오늘 구글 색인 요청 5개"에 주소 하나당 코드 상자 하나씩 적습니다.
- 고르는 순서(2026-10-20): ① 아래 "최우선" 칸 주소 중 아직 요청 안 된 것 ② 아래 "문의가 온 페이지"와 같은 시·군의 구·시군 페이지(문의 온 곳이 여럿이면 번갈아) ③ 시·도 페이지 14장 중 아직 요청 안 된 것 ④ 점수표(`docs/region-priority-2026-10-15.md`) 순위 높은 지방 시·군 구 페이지. 동 페이지(/pages/)는 어떤 경우에도 고르지 않습니다. 날짜 칸에 이미 있는 주소는 다시 고르지 않습니다. 단, 바로 앞 날짜 칸 제목에 "요청 못 함"이 있으면(할당량 초과 등) 그 칸의 같은 5개를 다음 날 다시 맨 앞에 올립니다.
- 문의가 온 페이지를 한 줄 더할 때 `python3 scripts/population_stats.py dong <시·군>` 도 돌려 둡니다(그 시·군의 동을 인구 많은 순으로 고르는 데 씀, 매일 루틴의 동 3장 규칙 ①).
- 네이버·공용 IndexNow 자동 전송(`scripts/indexnow.py`)은 이와 따로 그대로 돕니다.

## 최우선 (아직 요청 안 된 것부터 맨 앞)

주제 페이지 6장(/guide/ 압류·차령초과·상속·시동·방치차·저당), 2026-10-19 추가. 날짜 칸에 들어가면 요청한 것으로 칩니다.

- https://pyecha119.com/guide/%EC%95%95%EB%A5%98-%EC%9E%88%EB%8A%94-%EC%B0%A8-%ED%8F%90%EC%B0%A8.html — guide/압류-있는-차-폐차.html (압류)
- https://pyecha119.com/guide/%EC%B0%A8%EB%A0%B9%EC%B4%88%EA%B3%BC-%ED%8F%90%EC%B0%A8.html — guide/차령초과-폐차.html (차령초과)
- https://pyecha119.com/guide/%EC%83%81%EC%86%8D%EC%B0%A8-%EB%B2%95%EC%9D%B8%EC%B0%A8-%EC%84%9C%EB%A5%98.html — guide/상속차-법인차-서류.html (상속)
- https://pyecha119.com/guide/%EC%8B%9C%EB%8F%99-%EC%95%88-%EA%B1%B8%EB%A6%AC%EB%8A%94-%EC%B0%A8.html — guide/시동-안-걸리는-차.html (시동)
- https://pyecha119.com/guide/%EB%B0%A9%EC%B9%98%EC%B0%A8-%EC%98%A4%EB%9E%98-%EC%84%B8%EC%9B%8C%EB%91%94-%EC%B0%A8.html — guide/방치차-오래-세워둔-차.html (방치차)
- https://pyecha119.com/guide/%EC%A0%80%EB%8B%B9%EB%A7%8C-%EC%9E%88%EB%8A%94-%EC%B0%A8.html — guide/저당만-있는-차.html (저당)

## 문의가 온 페이지

문의가 들어오면 날짜·경로와 함께 한 줄씩 더합니다(②의 기준).

- 2026-10-18 오후 12시 42분, 네이버 모바일 검색 → 상단 폼 문의, 30분 만에 거래 성사 — https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%8F%99%ED%83%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (화성시 동탄구)
- 2026-10-14, 네이버 검색 문의 — https://pyecha119.com/gu/%EA%B0%95%EB%A6%89%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (강릉시)

## 2026-10-15

10월 15일에 요청한 점수표 1~10위 구 페이지입니다.

- https://pyecha119.com/gu/%EC%9B%90%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/원주시-폐차장.html
- https://pyecha119.com/gu/%EA%B5%AC%EB%AF%B8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구미시-폐차장.html
- https://pyecha119.com/gu/%EC%A0%9C%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/제주시-폐차장.html
- https://pyecha119.com/gu/%EC%96%91%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/양산시-폐차장.html
- https://pyecha119.com/gu/%EA%B4%91%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/광주시-폐차장.html
- https://pyecha119.com/gu/%EA%B9%80%ED%95%B4%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/김해시-폐차장.html
- https://pyecha119.com/gu/%EC%B2%9C%EC%95%88%EC%8B%9C-%EB%8F%99%EB%82%A8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/천안시-동남구-폐차장.html
- https://pyecha119.com/gu/%EC%B2%9C%EC%95%88%EC%8B%9C-%EC%84%9C%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/천안시-서북구-폐차장.html
- https://pyecha119.com/gu/%EC%95%84%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/아산시-폐차장.html
- https://pyecha119.com/gu/%EA%B0%95%EB%A6%89%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/강릉시-폐차장.html

## 2026-10-18

- https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%8F%99%ED%83%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/화성시-동탄구-폐차장.html (오늘 문의 온 페이지)
- https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%A7%8C%EC%84%B8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/화성시-만세구-폐차장.html (같은 시 구 페이지)
- https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%B3%91%EC%A0%90%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/화성시-병점구-폐차장.html (같은 시 구 페이지)
- https://pyecha119.com/pages/gyeonggi-hwaseong-dongtan-neung.html — pages/gyeonggi-hwaseong-dongtan-neung.html (동탄구 능동)
- https://pyecha119.com/pages/gyeonggi-hwaseong-dongtan-bansong.html — pages/gyeonggi-hwaseong-dongtan-bansong.html (동탄구 반송동)
- https://pyecha119.com/pages/gyeonggi-hwaseong-dongtan-seoku.html — pages/gyeonggi-hwaseong-dongtan-seoku.html (동탄구 석우동)
- https://pyecha119.com/gu/%EB%AA%A9%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/목포시-폐차장.html (점수표 11위)
- https://pyecha119.com/gu/%EC%A0%84%EC%A3%BC%EC%8B%9C-%EB%8D%95%EC%A7%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/전주시-덕진구-폐차장.html (점수표 12위)
- https://pyecha119.com/gu/%EC%A0%84%EC%A3%BC%EC%8B%9C-%EC%99%84%EC%82%B0%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/전주시-완산구-폐차장.html (점수표 13위)
- https://pyecha119.com/gu/%EA%B5%B0%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/군산시-폐차장.html (점수표 14위)
- https://pyecha119.com/gu/%EC%A7%84%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/진주시-폐차장.html (점수표 15위)

## 2026-10-18

- https://pyecha119.com/pages/gyeonggi-hwaseong-manse-saesol.html — pages/gyeonggi-hwaseong-manse-saesol.html (문의 온 곳(화성시 동탄구)과 같은 시·군의 동 페이지)
- https://pyecha119.com/pages/gangwon-gangneung-gyo.html — pages/gangwon-gangneung-gyo.html (문의 온 곳(강릉시)과 같은 시·군의 동 페이지)
- https://pyecha119.com/pages/gyeonggi-hwaseong-manse-ujeong.html — pages/gyeonggi-hwaseong-manse-ujeong.html (문의 온 곳(화성시 동탄구)과 같은 시·군의 동 페이지)
- https://pyecha119.com/gu/%EA%B3%84%EC%96%91%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/계양구-폐차장.html (오늘 새로 만든 구 페이지)
- https://pyecha119.com/gu/%EA%B4%91%EC%A7%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/광진구-폐차장.html (오늘 새로 만든 구 페이지)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-서구-폐차장.html (오늘 새로 만든 구 페이지)
- https://pyecha119.com/gu/%EB%B6%80%EC%82%B0-%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부산-북구-폐차장.html (오늘 새로 만든 구 페이지)
- https://pyecha119.com/gu/%EA%B4%80%EC%95%85%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/관악구-폐차장.html (오늘 새로 만든 구 페이지)
- https://pyecha119.com/gu/%EC%98%81%EB%93%B1%ED%8F%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영등포구-폐차장.html (오늘 새로 만든 구 페이지)
- https://pyecha119.com/gu/%EA%B2%80%EB%8B%A8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/검단구-폐차장.html (오늘 새로 만든 구 페이지)

## 2026-10-19 — 요청 못 함(구글 서치 콘솔 할당량 초과)

오늘은 하루 할당량을 넘겨 색인 요청을 하지 못했습니다. 최우선 칸의 주제 페이지 6장은 10월 20일 목록 맨 앞으로 갑니다.

## 2026-10-19 — 요청 못 함(이날 할당량 초과로 루틴이 고른 목록만 적음, 다음 날 다시 고름)

- https://pyecha119.com/guide/%EC%95%95%EB%A5%98-%EC%9E%88%EB%8A%94-%EC%B0%A8-%ED%8F%90%EC%B0%A8.html — guide/압류-있는-차-폐차.html (최우선 칸)
- https://pyecha119.com/guide/%EC%B0%A8%EB%A0%B9%EC%B4%88%EA%B3%BC-%ED%8F%90%EC%B0%A8.html — guide/차령초과-폐차.html (최우선 칸)
- https://pyecha119.com/guide/%EC%83%81%EC%86%8D%EC%B0%A8-%EB%B2%95%EC%9D%B8%EC%B0%A8-%EC%84%9C%EB%A5%98.html — guide/상속차-법인차-서류.html (최우선 칸)
- https://pyecha119.com/guide/%EC%8B%9C%EB%8F%99-%EC%95%88-%EA%B1%B8%EB%A6%AC%EB%8A%94-%EC%B0%A8.html — guide/시동-안-걸리는-차.html (최우선 칸)
- https://pyecha119.com/guide/%EB%B0%A9%EC%B9%98%EC%B0%A8-%EC%98%A4%EB%9E%98-%EC%84%B8%EC%9B%8C%EB%91%94-%EC%B0%A8.html — guide/방치차-오래-세워둔-차.html (최우선 칸)
- https://pyecha119.com/guide/%EC%A0%80%EB%8B%B9%EB%A7%8C-%EC%9E%88%EB%8A%94-%EC%B0%A8.html — guide/저당만-있는-차.html (최우선 칸)
- https://pyecha119.com/pages/gyeonggi-hwaseong-manse-hyangnam.html — pages/gyeonggi-hwaseong-manse-hyangnam.html (문의 온 곳(화성시 동탄구)과 같은 시·군의 동 페이지)
- https://pyecha119.com/pages/gangwon-gangneung-chodang.html — pages/gangwon-gangneung-chodang.html (문의 온 곳(강릉시)과 같은 시·군의 동 페이지)
- https://pyecha119.com/pages/gyeonggi-hwaseong-byeongjeom-gisan.html — pages/gyeonggi-hwaseong-byeongjeom-gisan.html (문의 온 곳(화성시 동탄구)과 같은 시·군의 동 페이지)
- https://pyecha119.com/gu/%EB%8F%99%EB%9E%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/동래구-폐차장.html (오늘 새로 만든 구 페이지)

## 2026-10-21

- https://pyecha119.com/guide/%EC%95%95%EB%A5%98-%EC%9E%88%EB%8A%94-%EC%B0%A8-%ED%8F%90%EC%B0%A8.html — guide/압류-있는-차-폐차.html (2026-10-19 요청 못 함 → 다시)
- https://pyecha119.com/guide/%EC%B0%A8%EB%A0%B9%EC%B4%88%EA%B3%BC-%ED%8F%90%EC%B0%A8.html — guide/차령초과-폐차.html (2026-10-19 요청 못 함 → 다시)
- https://pyecha119.com/guide/%EC%83%81%EC%86%8D%EC%B0%A8-%EB%B2%95%EC%9D%B8%EC%B0%A8-%EC%84%9C%EB%A5%98.html — guide/상속차-법인차-서류.html (2026-10-19 요청 못 함 → 다시)
- https://pyecha119.com/guide/%EC%8B%9C%EB%8F%99-%EC%95%88-%EA%B1%B8%EB%A6%AC%EB%8A%94-%EC%B0%A8.html — guide/시동-안-걸리는-차.html (2026-10-19 요청 못 함 → 다시)
- https://pyecha119.com/guide/%EB%B0%A9%EC%B9%98%EC%B0%A8-%EC%98%A4%EB%9E%98-%EC%84%B8%EC%9B%8C%EB%91%94-%EC%B0%A8.html — guide/방치차-오래-세워둔-차.html (2026-10-19 요청 못 함 → 다시)
