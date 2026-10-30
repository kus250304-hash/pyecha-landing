# 구글·네이버 색인 요청 기록

병한님이 구글 서치 콘솔(왼쪽 "URL 검사" → 주소 붙여 넣기 → "색인 생성 요청", 2026-10-18부터)과 네이버 서치어드바이저(요청 → 웹 페이지 수집, 2026-10-22부터)에 손으로 요청한 주소 기록입니다.

- 매일 루틴이 `python3 scripts/pick_index_requests.py --write` 로 그날 요청할 주소를 **구글 15개·네이버 50개 따로**(2026-10-29부터, 그 전은 같은 10개를 양쪽에) 골라 아래에 "## 날짜 구글"·"## 날짜 네이버" 칸으로 덧붙이고, 아침 보고(오전 6시 55분) 맨 끝에 구글은 주소마다 코드 상자 + 서치 콘솔 URL 검사 바로가기, 네이버는 코드 상자 하나에 주소 한 줄씩 적습니다.
- 칸 제목의 곳 표시: "날짜 구글"·"날짜 네이버"·"날짜 구글·네이버 …"는 그곳에 넣은 것, 표시 없는 옛 칸은 2026-10-22부터 둘 다·그 전은 구글만입니다. 손으로 넣은 것도 이 표시를 달아 적고, 한 곳만 할당량 초과면 그곳만 "날짜 구글 — 요청 못 함(…)"처럼 적습니다.
- 구글 고르는 순서(구·시군·주제 페이지만): ⓐ 어제·오늘 사례가 새로 붙은 구·시군 페이지 ⓪ 구글 "요청 못 함" 칸 중 그 날짜 뒤로 요청 안 한 주소(최근 칸부터, 예전에 요청했어도 다시) ① 아래 "최우선" 칸 ② 아래 "문의가 온 페이지"와 같은 시·군의 구·시군 페이지(여럿이면 번갈아) ②-0 빈 땅 → ②-1 지인 공략 ④ 점수표 순위 높은 지방 시·군 구 페이지. 동·시·도·사례 페이지는 구글에 고르지 않습니다.
- 네이버 고르는 순서(사이트맵에 있는 페이지만, noindex 빼기): ⓪ 네이버 "요청 못 함" 칸 ① 네이버에 아직 안 넣은 구·시·주제·사례 페이지(최우선 → 문의 온 시·군 → 빈 땅 → 지인 공략 → 시·도 → 점수표 순 구 → 나머지 → 사례 최근 것 먼저) ② 동 페이지(문의 온 시·군의 동 인구 많은 순 → 점수표 순 시·군의 인구 많은 동).
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

문의가 들어오면 날짜·경로와 함께 한 줄씩 더합니다(②의 기준). "랜딩 문의(상태: …)" 줄은 PC 예약 작업 "폐차 사례 가져오기"가 매일 `python scripts/inquiry_log.py --write` 로 병한-업무위키 거래 기록부(`폐차/거래기록`)에서 유입경로가 랜딩·폼인 거래를 옮긴 것입니다(2026-10-21부터, 상태도 거래 기록부대로 고침). 어느 페이지로 들어왔는지 기록이 없어 그 시·군의 구 페이지 주소를 적습니다. 손으로 따로 적지 않아도 됩니다.

- 2026-10-30, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EB%B6%80%ED%8F%89%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (부평구)
- 2026-10-28, 랜딩 문의(상태: 거래 성사) — https://pyecha119.com/gu/%EA%B3%A0%EB%A0%B9%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (고령군)
- 2026-10-28, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EB%8B%A8%EC%96%91%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (단양군)
- 2026-10-28, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EC%B0%BD%EC%9B%90%EC%8B%9C-%EB%A7%88%EC%82%B0%ED%95%A9%ED%8F%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (창원시 마산합포구)
- 2026-10-27, 랜딩 문의(상태: 거래 성사) — https://pyecha119.com/gu/%ED%83%9C%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (태안군)
- 2026-10-27, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EC%84%9C%EC%9A%B8-%EA%B0%95%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (서울 강서구)
- 2026-10-27, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EC%9D%B5%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (익산시)
- 2026-10-26, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EC%99%84%EB%8F%84%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (완도군)
- 2026-10-21, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EA%B5%AC%EB%AF%B8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (구미시)
- 2026-10-21, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EB%AA%A9%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (목포시)
- 2026-10-18 오후 12시 42분, 네이버 모바일 검색 → 상단 폼 문의, 30분 만에 거래 성사 — https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%8F%99%ED%83%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (화성시 동탄구)
- 2026-10-17, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EA%B9%80%ED%95%B4%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (김해시)
- 2026-10-16, 랜딩 문의(상태: 거래 성사) — https://pyecha119.com/gu/%EC%B2%9C%EC%95%88%EC%8B%9C-%EB%8F%99%EB%82%A8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (천안시 동남구)
- 2026-10-14, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EC%88%98%EC%98%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (수영구)
- 2026-10-14, 네이버 검색 문의 — https://pyecha119.com/gu/%EA%B0%95%EB%A6%89%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (강릉시)
- 2026-10-12, 랜딩 문의(상태: 거래 성사) — https://pyecha119.com/gu/%EA%B2%BD%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (경산시)
- 2026-10-09, 랜딩 문의(상태: 거래 성사) — https://pyecha119.com/gu/%EB%AA%A9%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (목포시)
- 2026-10-09, 랜딩 문의(상태: 진행) — https://pyecha119.com/gu/%EC%84%9C%EC%9A%B8-%EA%B0%95%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (서울 강서구)

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

## 2026-10-22

- https://pyecha119.com/guide/%EC%A0%80%EB%8B%B9%EB%A7%8C-%EC%9E%88%EB%8A%94-%EC%B0%A8.html — guide/저당만-있는-차.html (최우선 칸)
- https://pyecha119.com/gu/%EC%88%98%EC%98%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수영구-폐차장.html (문의 온 곳(수영구)과 같은 시·군의 구 페이지)
- https://pyecha119.com/gu/%EA%B2%BD%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/경산시-폐차장.html (문의 온 곳(경산시)과 같은 시·군의 구 페이지)
- https://pyecha119.com/gu/%EC%84%9C%EC%9A%B8-%EA%B0%95%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서울-강서구-폐차장.html (문의 온 곳(강서구)과 같은 시·군의 구 페이지)
- https://pyecha119.com/si/%EC%84%9C%EC%9A%B8-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/서울-폐차장.html (시·도 페이지)

## 2026-10-22 추가 (병한님 직접, 익산시에서 할당량 초과)

10월 22일 병한님이 루틴 5개 뒤에 직접 이어서 요청한 16개입니다(이미 색인돼 있던 주소 포함, 다시 고르지 않게 적음). 다음 순서인 익산시 구 페이지에서 할당량이 넘어 그 뒤(익산시·서산시·거제시·당진시·창원시 진해구·충주시·김천시·포항시 북구·고령군)는 요청하지 못해 적지 않았습니다.

- https://pyecha119.com/si/%EC%A0%84%EB%B6%81-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/전북-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EA%B2%BD%EA%B8%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/경기-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EC%A0%84%EB%82%A8%EA%B4%91%EC%A3%BC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/전남광주-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EA%B0%95%EC%9B%90-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/강원-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EC%B6%A9%EB%82%A8-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/충남-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EA%B2%BD%EB%B6%81-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/경북-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EA%B2%BD%EB%82%A8-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/경남-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EC%B6%A9%EB%B6%81-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/충북-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EB%8C%80%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/대구-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EB%B6%80%EC%82%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/부산-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EC%9D%B8%EC%B2%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/인천-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EB%8C%80%EC%A0%84-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/대전-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EC%9A%B8%EC%82%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/울산-폐차장.html (병한님 직접)
- https://pyecha119.com/si/%EC%A0%9C%EC%A3%BC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — si/제주-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%B6%98%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/춘천시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%84%B8%EC%A2%85-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/세종-폐차장.html (병한님 직접)

## 2026-10-23

- https://pyecha119.com/gu/%EC%9D%B5%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/익산시-폐차장.html (점수표 18위 지방 시·군)
- https://pyecha119.com/gu/%EC%84%9C%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서산시-폐차장.html (점수표 19위 지방 시·군)
- https://pyecha119.com/gu/%EA%B1%B0%EC%A0%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/거제시-폐차장.html (점수표 21위 지방 시·군)
- https://pyecha119.com/gu/%EB%8B%B9%EC%A7%84%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/당진시-폐차장.html (점수표 22위 지방 시·군)
- https://pyecha119.com/gu/%EC%B0%BD%EC%9B%90%EC%8B%9C-%EC%A7%84%ED%95%B4%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/창원시-진해구-폐차장.html (점수표 24위 지방 시·군)
- https://pyecha119.com/gu/%EC%B6%A9%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/충주시-폐차장.html (점수표 25위 지방 시·군)
- https://pyecha119.com/gu/%EA%B9%80%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/김천시-폐차장.html (점수표 27위 지방 시·군)
- https://pyecha119.com/gu/%ED%8F%AC%ED%95%AD%EC%8B%9C-%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/포항시-북구-폐차장.html (점수표 28위 지방 시·군)
- https://pyecha119.com/gu/%EA%B3%A0%EB%A0%B9%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/고령군-폐차장.html (점수표 29위 지방 시·군)
- https://pyecha119.com/gu/%ED%8F%AC%ED%95%AD%EC%8B%9C-%EB%82%A8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/포항시-남구-폐차장.html (점수표 30위 지방 시·군)

## 2026-10-23 추가 (병한님 직접, 청주시 상당구에서 할당량 초과)

10월 23일 밤 병한님이 루틴 10개 뒤에 직접 이어서 구글에 요청한 4개입니다(이미 색인돼 있던 주소 포함, 다시 고르지 않게 적음). 다음 순서인 청주시 상당구 구 페이지에서 할당량이 넘어 그 뒤(청주시 상당구·청원구·흥덕구, 논산시, 제천시, 영천시)는 구글에 요청하지 못해 적지 않았습니다(다음 날 다시 고름). 네이버 웹 페이지 수집에는 루틴 10개 + 이 4개 + 못 한 6개까지 20개를 모두 넣었으므로, 그 6개가 다시 뽑히면 구글만 하면 됩니다.

- https://pyecha119.com/gu/%EA%B2%BD%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/경주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%88%9C%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/순천시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%B2%AD%EC%A3%BC%EC%8B%9C-%EC%84%9C%EC%9B%90%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/청주시-서원구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B4%91%EC%96%91%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/광양시-폐차장.html (병한님 직접)

## 2026-10-24

- https://pyecha119.com/gu/%EC%B2%AD%EC%A3%BC%EC%8B%9C-%EC%83%81%EB%8B%B9%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/청주시-상당구-폐차장.html (점수표 35위 지방 시·군)
- https://pyecha119.com/gu/%EC%B2%AD%EC%A3%BC%EC%8B%9C-%EC%B2%AD%EC%9B%90%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/청주시-청원구-폐차장.html (점수표 36위 지방 시·군)
- https://pyecha119.com/gu/%EC%B2%AD%EC%A3%BC%EC%8B%9C-%ED%9D%A5%EB%8D%95%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/청주시-흥덕구-폐차장.html (점수표 37위 지방 시·군)
- https://pyecha119.com/gu/%EB%85%BC%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/논산시-폐차장.html (점수표 40위 지방 시·군)
- https://pyecha119.com/gu/%EC%A0%9C%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/제천시-폐차장.html (점수표 41위 지방 시·군)

## 2026-10-24 — 요청 못 함(구글 할당량 초과, 제천시까지 요청함)

- https://pyecha119.com/gu/%EC%98%81%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영천시-폐차장.html (점수표 42위 지방 시·군)
- https://pyecha119.com/gu/%EA%B5%AC%EB%A1%80%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구례군-폐차장.html (점수표 43위 지방 시·군)
- https://pyecha119.com/gu/%EC%8B%A0%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/신안군-폐차장.html (점수표 44위 지방 시·군)
- https://pyecha119.com/gu/%EB%82%A8%EC%9B%90%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/남원시-폐차장.html (점수표 45위 지방 시·군)
- https://pyecha119.com/gu/%EC%95%88%EB%8F%99%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안동시-폐차장.html (점수표 46위 지방 시·군)

## 2026-10-25

- https://pyecha119.com/gu/%EC%98%81%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영천시-폐차장.html (2026-10-24 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EA%B5%AC%EB%A1%80%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구례군-폐차장.html (2026-10-24 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%8B%A0%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/신안군-폐차장.html (2026-10-24 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EB%82%A8%EC%9B%90%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/남원시-폐차장.html (2026-10-24 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%95%88%EB%8F%99%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안동시-폐차장.html (2026-10-24 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EA%B3%B5%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/공주시-폐차장.html (점수표 50위 지방 시·군)
- https://pyecha119.com/gu/%EC%82%AC%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/사천시-폐차장.html (점수표 52위 지방 시·군)
- https://pyecha119.com/gu/%EC%B0%BD%EC%9B%90%EC%8B%9C-%EB%A7%88%EC%82%B0%ED%95%A9%ED%8F%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/창원시-마산합포구-폐차장.html (점수표 55위 지방 시·군)
- https://pyecha119.com/gu/%EC%B0%BD%EC%9B%90%EC%8B%9C-%EB%A7%88%EC%82%B0%ED%9A%8C%EC%9B%90%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/창원시-마산회원구-폐차장.html (점수표 56위 지방 시·군)
- https://pyecha119.com/gu/%EC%B0%BD%EC%9B%90%EC%8B%9C-%EC%84%B1%EC%82%B0%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/창원시-성산구-폐차장.html (점수표 57위 지방 시·군)

## 2026-10-25 추가 (병한님 직접)

- https://pyecha119.com/gu/%EC%B0%BD%EC%9B%90%EC%8B%9C-%EC%9D%98%EC%B0%BD%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/창원시-의창구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%B6%80%EC%97%AC%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부여군-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%86%8D%EC%B4%88%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/속초시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%97%AC%EC%88%98%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/여수시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%B6%80%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부안군-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%ED%86%B5%EC%98%81%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/통영시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%84%9C%EA%B7%80%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서귀포시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%83%81%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/상주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%98%81%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%8F%99%ED%95%B4%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/동해시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%ED%99%8D%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/홍성군-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%B0%80%EC%96%91%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/밀양시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B9%80%EC%A0%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/김제시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%82%98%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/나주시-폐차장.html (병한님 직접)

## 2026-10-25 — 요청 못 함(구글 할당량 초과, 나주시까지 요청함)

- https://pyecha119.com/gu/%EC%A0%95%EC%9D%8D%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/정읍시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%ED%83%9C%EB%B0%B1%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/태백시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EB%B3%B4%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/보성군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%98%88%EC%82%B0%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/예산군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%A7%84%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/진천군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%98%88%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/예천군-폐차장.html (구글 할당량 초과)

## 2026-10-26

- https://pyecha119.com/gu/%EC%A0%95%EC%9D%8D%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/정읍시-폐차장.html (2026-10-25 요청 못 함 → 다시)
- https://pyecha119.com/gu/%ED%83%9C%EB%B0%B1%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/태백시-폐차장.html (2026-10-25 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EB%B3%B4%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/보성군-폐차장.html (2026-10-25 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%98%88%EC%82%B0%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/예산군-폐차장.html (2026-10-25 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%A7%84%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/진천군-폐차장.html (2026-10-25 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%98%88%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/예천군-폐차장.html (2026-10-25 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EA%B5%AC%EB%AF%B8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구미시-폐차장.html (빈 땅(구미시 · 구미폐차) · 2026-10-15 요청 뒤 내용 바뀜(2026-10-26))
- https://pyecha119.com/gu/%EB%AA%A9%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/목포시-폐차장.html (빈 땅(목포시 · 목포폐차 · 목포폐차장) · 2026-10-18 요청 뒤 내용 바뀜(2026-10-26))
- https://pyecha119.com/gu/%EC%A7%84%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/진주시-폐차장.html (빈 땅(진주시 · 진주폐차 · 진주폐차장) · 2026-10-18 요청 뒤 내용 바뀜(2026-10-20))
- https://pyecha119.com/gu/%EC%84%B8%EC%A2%85-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/세종-폐차장.html (빈 땅(세종특별자치시 · 세종폐차 · 세종폐차장) · 2026-10-22 요청 뒤 내용 바뀜(2026-10-23))

## 2026-10-27

- https://pyecha119.com/gu/%EA%B5%AC%EB%AF%B8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구미시-폐차장.html (빈 땅(구미시 · 구미폐차) · 2026-10-26 요청 뒤 내용 바뀜(2026-10-27))
- https://pyecha119.com/gu/%EB%AA%A9%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/목포시-폐차장.html (빈 땅(목포시 · 목포폐차 · 목포폐차장) · 2026-10-26 요청 뒤 내용 바뀜(2026-10-27))
- https://pyecha119.com/gu/%EA%B3%A0%EB%A0%B9%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/고령군-폐차장.html (빈 땅(고령군 · 고령폐차) · 2026-10-23 요청 뒤 내용 바뀜(2026-10-25))
- https://pyecha119.com/gu/%EB%85%BC%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/논산시-폐차장.html (빈 땅(논산시 · 논산폐차) · 2026-10-24 요청 뒤 내용 바뀜(2026-10-25))
- https://pyecha119.com/gu/%EC%A0%95%EC%9D%8D%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/정읍시-폐차장.html (빈 땅(정읍시 · 정읍폐차) · 2026-10-26 요청 뒤 내용 바뀜(2026-10-27))
- https://pyecha119.com/gu/%EC%84%9C%ED%95%B4%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서해구-폐차장.html (빈 땅(서해구 · 서해폐차))
- https://pyecha119.com/gu/%EC%B0%BD%EB%85%95%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/창녕군-폐차장.html (빈 땅(창녕군 · 창녕폐차))
- https://pyecha119.com/gu/%EC%B9%A0%EA%B3%A1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/칠곡군-폐차장.html (빈 땅(칠곡군 · 칠곡폐차))
- https://pyecha119.com/gu/%EC%9E%A5%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/장성군-폐차장.html (빈 땅(장성군 · 장성폐차))
- https://pyecha119.com/gu/%ED%95%A8%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/함안군-폐차장.html (빈 땅(함안군 · 함안폐차))

## 2026-10-27 추가 요청(손으로)

- https://pyecha119.com/gu/%ED%8F%89%ED%83%9D%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/평택시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%96%91%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/양주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%ED%8C%8C%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/파주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%95%88%EC%84%B1%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안성시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%95%88%EC%82%B0%EC%8B%9C-%EC%83%81%EB%A1%9D%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안산시-상록구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B9%80%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/김포시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%95%88%EC%82%B0%EC%8B%9C-%EB%8B%A8%EC%9B%90%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안산시-단원구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%82%A8%EC%96%91%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/남양주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%8B%9C%ED%9D%A5%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/시흥시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%98%A4%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/오산시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%9D%B4%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/이천시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%9D%98%EC%A0%95%EB%B6%80%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/의정부시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B5%B0%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/군포시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%95%88%EC%96%91%EC%8B%9C-%EB%8F%99%EC%95%88%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안양시-동안구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%95%88%EC%96%91%EC%8B%9C-%EB%A7%8C%EC%95%88%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안양시-만안구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%88%98%EC%9B%90%EC%8B%9C-%EC%98%81%ED%86%B5%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수원시-영통구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%88%98%EC%9B%90%EC%8B%9C-%EC%9E%A5%EC%95%88%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수원시-장안구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%88%98%EC%9B%90%EC%8B%9C-%EA%B6%8C%EC%84%A0%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수원시-권선구-폐차장.html (병한님 직접)

## 2026-10-27 — 요청 못 함(할당량 초과)

- https://pyecha119.com/gu/%EC%88%98%EC%9B%90%EC%8B%9C-%ED%8C%94%EB%8B%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수원시-팔달구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%ED%8F%AC%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/포천시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%ED%95%98%EB%82%A8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/하남시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EA%B4%91%EB%AA%85%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/광명시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%ED%95%A8%EC%96%91%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/함양군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%A6%9D%ED%8F%89%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/증평군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%9A%A9%EC%9D%B8%EC%8B%9C-%EC%B2%98%EC%9D%B8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/용인시-처인구-폐차장.html (구글 할당량 초과)

## 2026-10-28

- https://pyecha119.com/gu/%EC%98%81%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영천시-폐차장.html (2026-10-28 사례가 새로 붙음(영천시 2001년식 테라칸))
- https://pyecha119.com/gu/%EA%B2%BD%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/경산시-폐차장.html (2026-10-28 사례가 새로 붙음(경산시 2006년식 그랜드 카니발))
- https://pyecha119.com/gu/%EC%95%88%EB%8F%99%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안동시-폐차장.html (2026-10-28 사례가 새로 붙음(안동시 2012년식 제네시스 BH))
- https://pyecha119.com/gu/%EA%B5%B0%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/군산시-폐차장.html (2026-10-28 사례가 새로 붙음(군산시 2009년식 뉴 모닝))
- https://pyecha119.com/gu/%EB%B3%B4%EB%A0%B9%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/보령시-폐차장.html (2026-10-28 사례가 새로 붙음(보령시 2006년식 NF 쏘나타))
- https://pyecha119.com/gu/%EC%83%81%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/상주시-폐차장.html (2026-10-28 사례가 새로 붙음(상주시 2010년식 싼타페 CM))
- https://pyecha119.com/gu/%EC%88%9C%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/순천시-폐차장.html (2026-10-28 사례가 새로 붙음(순천시 2004년식 쏘렌토))
- https://pyecha119.com/gu/%EA%B0%95%EB%A6%89%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/강릉시-폐차장.html (2026-10-28 사례가 새로 붙음(강릉시 2012년식 그랜드 스타렉스))
- https://pyecha119.com/gu/%EC%99%84%EC%A3%BC%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/완주군-폐차장.html (2026-10-27 사례가 새로 붙음(완주군 2010년식 라세티 프리미어))
- https://pyecha119.com/gu/%EC%88%98%EC%9B%90%EC%8B%9C-%ED%8C%94%EB%8B%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수원시-팔달구-폐차장.html (2026-10-27 요청 못 함 → 다시)

## 2026-10-29 구글·네이버

- https://pyecha119.com/gu/%ED%83%9C%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/태안군-폐차장.html (2026-10-29 사례가 새로 붙음(태안군 2010년식 베라크루즈))
- https://pyecha119.com/gu/%EA%B3%A0%EB%A0%B9%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/고령군-폐차장.html (2026-10-29 사례가 새로 붙음(고령군 2004년식 봉고 프런티어))
- https://pyecha119.com/gu/%EC%84%B1%EB%82%A8%EC%8B%9C-%EB%B6%84%EB%8B%B9%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/성남시-분당구-폐차장.html (2026-10-29 사례가 새로 붙음(성남시 분당구 2008년식 SM7 뉴아트))
- https://pyecha119.com/gu/%EC%95%88%EC%82%B0%EC%8B%9C-%EC%83%81%EB%A1%9D%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/안산시-상록구-폐차장.html (2026-10-29 사례가 새로 붙음(안산시 상록구 2014년식 LF쏘나타))
- https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%A7%8C%EC%84%B8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/화성시-만세구-폐차장.html (2026-10-29 사례가 새로 붙음(화성시 만세구 2001년식 아반떼))
- https://pyecha119.com/gu/%EB%85%BC%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/논산시-폐차장.html (2026-10-29 사례가 새로 붙음(논산시 2015년식 투싼ix))
- https://pyecha119.com/gu/%EC%B2%9C%EC%95%88%EC%8B%9C-%EC%84%9C%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/천안시-서북구-폐차장.html (2026-10-29 사례가 새로 붙음(천안시 서북구 2014년식 코란도 투리스모))
- https://pyecha119.com/gu/%EC%99%84%EB%8F%84%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/완도군-폐차장.html (2026-10-29 사례가 새로 붙음(완도군 2006년식 SM5))
- https://pyecha119.com/gu/%EC%B2%9C%EC%95%88%EC%8B%9C-%EB%8F%99%EB%82%A8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/천안시-동남구-폐차장.html (2026-10-29 사례가 새로 붙음(천안시 동남구 2011년식 푸조 3008))
- https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%B3%91%EC%A0%90%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/화성시-병점구-폐차장.html (2026-10-29 사례가 새로 붙음(화성시 병점구 2009년식 포르테))

## 2026-10-29 구글·네이버 추가(손으로)

- https://pyecha119.com/gu/%EB%B6%80%ED%8F%89%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부평구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B9%80%ED%95%B4%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/김해시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B5%AC%EB%AF%B8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구미시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%84%9C%EC%9A%B8-%EA%B0%95%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서울-강서구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%99%84%EC%A3%BC%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/완주군-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%84%9C%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서산시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%8F%99%ED%83%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/화성시-동탄구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%8C%80%EC%A0%84-%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대전-서구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%8B%9C%ED%9D%A5%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/시흥시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%9A%B8%EC%A7%84%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/울진군-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EC%A4%91%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-중구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%8B%AC%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/달성군-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EA%B9%80%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/김포시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%88%98%EC%9B%90%EC%8B%9C-%EA%B6%8C%EC%84%A0%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/수원시-권선구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-북구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%ED%8C%8C%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/파주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%ED%95%B4%EC%9A%B4%EB%8C%80%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/해운대구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%9B%90%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/원주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%AA%A9%ED%8F%AC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/목포시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EB%82%A8%EC%96%91%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/남양주시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%9D%98%EC%99%95%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/의왕시-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%9A%B8%EC%82%B0-%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/울산-북구-폐차장.html (병한님 직접)
- https://pyecha119.com/gu/%EC%98%81%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영주시-폐차장.html (병한님 직접)

## 2026-10-29 구글 — 요청 못 함(할당량 초과)

- https://pyecha119.com/gu/%EC%98%A4%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/오산시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%ED%8F%89%EC%B0%BD%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/평창군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%97%B0%EC%88%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/연수구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-서구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%82%AC%ED%95%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/사하구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%84%B1%EB%8F%99%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/성동구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EB%B6%80%EC%B2%9C%EC%8B%9C-%EC%86%8C%EC%82%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부천시-소사구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%A0%95%EC%84%A0%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/정선군-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EB%8B%AC%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/달서구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%9D%80%ED%8F%89%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/은평구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%98%81%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영천시-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EB%8F%99%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-동구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EC%84%9C%ED%95%B4%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서해구-폐차장.html (구글 할당량 초과)
- https://pyecha119.com/gu/%EB%82%98%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/나주시-폐차장.html (구글 할당량 초과)

## 2026-10-29 네이버 추가(손으로)

- https://pyecha119.com/gu/%EC%98%A4%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/오산시-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%ED%8F%89%EC%B0%BD%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/평창군-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%97%B0%EC%88%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/연수구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-서구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%82%AC%ED%95%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/사하구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%84%B1%EB%8F%99%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/성동구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EB%B6%80%EC%B2%9C%EC%8B%9C-%EC%86%8C%EC%82%AC%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부천시-소사구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%A0%95%EC%84%A0%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/정선군-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EB%8B%AC%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/달서구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%9D%80%ED%8F%89%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/은평구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%98%81%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영천시-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EB%8F%99%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-동구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EC%84%9C%ED%95%B4%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서해구-폐차장.html (병한님 직접, 구글은 할당량 초과)
- https://pyecha119.com/gu/%EB%82%98%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/나주시-폐차장.html (병한님 직접, 구글은 할당량 초과)

## 2026-10-30 구글

- https://pyecha119.com/gu/%EC%A0%84%EC%A3%BC%EC%8B%9C-%EB%8D%95%EC%A7%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/전주시-덕진구-폐차장.html (2026-10-30 사례가 새로 붙음(전주시 덕진구 2007년식 마티즈))
- https://pyecha119.com/gu/%EC%95%84%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/아산시-폐차장.html (2026-10-30 사례가 새로 붙음(아산시 2006년식 그랜저 TG))
- https://pyecha119.com/gu/%EC%98%A5%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/옥천군-폐차장.html (2026-10-30 사례가 새로 붙음(옥천군 2016년식 SM5 노바))
- https://pyecha119.com/gu/%EC%84%9C%ED%95%B4%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서해구-폐차장.html (2026-10-30 사례가 새로 붙음(서해구 2005년식 싼타페))
- https://pyecha119.com/gu/%EC%84%B8%EC%A2%85-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/세종-폐차장.html (2026-10-30 사례가 새로 붙음( 2008년식 모하비))
- https://pyecha119.com/gu/%EC%98%81%EB%8D%95%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영덕군-폐차장.html (2026-10-30 사례가 새로 붙음(영덕군 2011년식 쏘나타))
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EB%8F%99%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-동구-폐차장.html (2026-10-30 사례가 새로 붙음(동구 2009년식 그랜드 스타렉스))
- https://pyecha119.com/gu/%EA%B5%AC%EB%AF%B8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/구미시-폐차장.html (2026-10-30 사례가 새로 붙음(구미시 2007년식 아반떼 HD))
- https://pyecha119.com/gu/%ED%8F%AC%ED%95%AD%EC%8B%9C-%EB%B6%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/포항시-북구-폐차장.html (2026-10-30 사례가 새로 붙음(포항시 북구 2010년식 그랜저 TG))
- https://pyecha119.com/gu/%EC%8B%9C%ED%9D%A5%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/시흥시-폐차장.html (2026-10-30 사례가 새로 붙음(시흥시 2008년식 오피러스))
- https://pyecha119.com/gu/%EC%98%A4%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/오산시-폐차장.html (2026-10-29 요청 못 함 → 다시)
- https://pyecha119.com/gu/%ED%8F%89%EC%B0%BD%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/평창군-폐차장.html (2026-10-29 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%97%B0%EC%88%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/연수구-폐차장.html (2026-10-29 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EB%8C%80%EA%B5%AC-%EC%84%9C%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/대구-서구-폐차장.html (2026-10-29 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%82%AC%ED%95%98%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/사하구-폐차장.html (2026-10-29 요청 못 함 → 다시)

## 2026-10-30 네이버

- https://pyecha119.com/gu/%ED%8F%AC%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/포천시-폐차장.html (2026-10-27 요청 못 함 → 다시)
- https://pyecha119.com/gu/%ED%95%98%EB%82%A8%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/하남시-폐차장.html (2026-10-27 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EA%B4%91%EB%AA%85%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/광명시-폐차장.html (2026-10-27 요청 못 함 → 다시)
- https://pyecha119.com/gu/%ED%95%A8%EC%96%91%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/함양군-폐차장.html (2026-10-27 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%A6%9D%ED%8F%89%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/증평군-폐차장.html (2026-10-27 요청 못 함 → 다시)
- https://pyecha119.com/gu/%EC%9A%A9%EC%9D%B8%EC%8B%9C-%EC%B2%98%EC%9D%B8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/용인시-처인구-폐차장.html (2026-10-27 요청 못 함 → 다시)
- https://pyecha119.com/guide/%EC%95%95%EB%A5%98-%EC%9E%88%EB%8A%94-%EC%B0%A8-%ED%8F%90%EC%B0%A8.html — guide/압류-있는-차-폐차.html (최우선 칸)
- https://pyecha119.com/guide/%EC%B0%A8%EB%A0%B9%EC%B4%88%EA%B3%BC-%ED%8F%90%EC%B0%A8.html — guide/차령초과-폐차.html (최우선 칸)
- https://pyecha119.com/guide/%EC%83%81%EC%86%8D%EC%B0%A8-%EB%B2%95%EC%9D%B8%EC%B0%A8-%EC%84%9C%EB%A5%98.html — guide/상속차-법인차-서류.html (최우선 칸)
- https://pyecha119.com/guide/%EC%8B%9C%EB%8F%99-%EC%95%88-%EA%B1%B8%EB%A6%AC%EB%8A%94-%EC%B0%A8.html — guide/시동-안-걸리는-차.html (최우선 칸)
- https://pyecha119.com/guide/%EB%B0%A9%EC%B9%98%EC%B0%A8-%EC%98%A4%EB%9E%98-%EC%84%B8%EC%9B%8C%EB%91%94-%EC%B0%A8.html — guide/방치차-오래-세워둔-차.html (최우선 칸)
- https://pyecha119.com/gu/%EB%8B%A8%EC%96%91%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/단양군-폐차장.html (문의 온 곳(단양군)과 같은 시·군의 구 페이지)
- https://pyecha119.com/gu/%EB%AC%B4%EC%95%88%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/무안군-폐차장.html (빈 땅(무안군))
- https://pyecha119.com/gu/%ED%99%8D%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/홍천군-폐차장.html (빈 땅(홍천군))
- https://pyecha119.com/gu/%EA%B1%B0%EC%B0%BD%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/거창군-폐차장.html (빈 땅(거창군))
- https://pyecha119.com/gu/%EC%84%B1%EC%A3%BC%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/성주군-폐차장.html (빈 땅(성주군))
- https://pyecha119.com/gu/%EC%98%A5%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/옥천군-폐차장.html (빈 땅(옥천군))
- https://pyecha119.com/gu/%EA%B3%BC%EC%B2%9C%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/과천시-폐차장.html (빈 땅(과천시))
- https://pyecha119.com/gu/%EB%AC%B8%EA%B2%BD%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/문경시-폐차장.html (빈 땅(문경시))
- https://pyecha119.com/gu/%EB%8B%B4%EC%96%91%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/담양군-폐차장.html (빈 땅(담양군))
- https://pyecha119.com/gu/%EC%82%B0%EC%B2%AD%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/산청군-폐차장.html (빈 땅(산청군))
- https://pyecha119.com/gu/%ED%95%A9%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/합천군-폐차장.html (빈 땅(합천군))
- https://pyecha119.com/gu/%EA%B4%B4%EC%82%B0%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/괴산군-폐차장.html (빈 땅(괴산군))
- https://pyecha119.com/gu/%EC%96%91%EC%96%91%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/양양군-폐차장.html (빈 땅(양양군))
- https://pyecha119.com/gu/%EA%B8%B0%EC%9E%A5%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/기장군-폐차장.html (빈 땅(기장군))
- https://pyecha119.com/gu/%EC%96%91%EA%B5%AC%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/양구군-폐차장.html (빈 땅(양구군))
- https://pyecha119.com/gu/%EC%98%81%EB%8D%95%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/영덕군-폐차장.html (빈 땅(영덕군))
- https://pyecha119.com/gu/%EC%82%AC%EC%83%81%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/사상구-폐차장.html (빈 땅(사상구))
- https://pyecha119.com/gu/%EC%9D%98%EB%A0%B9%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/의령군-폐차장.html (빈 땅(의령군))
- https://pyecha119.com/gu/%ED%95%A8%ED%8F%89%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/함평군-폐차장.html (빈 땅(함평군))
- https://pyecha119.com/gu/%ED%95%98%EB%8F%99%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/하동군-폐차장.html (빈 땅(하동군))
- https://pyecha119.com/gu/%EA%B0%95%EC%9B%90-%EA%B3%A0%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/강원-고성군-폐차장.html (빈 땅(고성군))
- https://pyecha119.com/gu/%EC%9E%A5%EC%88%98%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/장수군-폐차장.html (빈 땅(장수군))
- https://pyecha119.com/gu/%EC%95%84%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/아산시-폐차장.html (지인 공략(아산시))
- https://pyecha119.com/gu/%EC%A0%84%EC%A3%BC%EC%8B%9C-%EB%8D%95%EC%A7%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/전주시-덕진구-폐차장.html (지인 공략(전주시 덕진구))
- https://pyecha119.com/gu/%EC%A0%84%EC%A3%BC%EC%8B%9C-%EC%99%84%EC%82%B0%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/전주시-완산구-폐차장.html (지인 공략(전주시 완산구))
- https://pyecha119.com/gu/%EC%A0%9C%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/제주시-폐차장.html (점수표 3위)
- https://pyecha119.com/gu/%EC%96%91%EC%82%B0%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/양산시-폐차장.html (점수표 4위)
- https://pyecha119.com/gu/%EA%B4%91%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/광주시-폐차장.html (점수표 5위)
- https://pyecha119.com/gu/%EA%B3%A0%EC%96%91%EC%8B%9C-%EB%8D%95%EC%96%91%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/고양시-덕양구-폐차장.html (점수표 99위)
- https://pyecha119.com/gu/%EB%B6%80%EC%B2%9C%EC%8B%9C-%EC%98%A4%EC%A0%95%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부천시-오정구-폐차장.html (점수표 101위)
- https://pyecha119.com/gu/%EB%B6%80%EC%B2%9C%EC%8B%9C-%EC%9B%90%EB%AF%B8%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/부천시-원미구-폐차장.html (점수표 102위)
- https://pyecha119.com/gu/%EC%84%9C%EC%B2%9C%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/서천군-폐차장.html (점수표 109위)
- https://pyecha119.com/gu/%EC%9A%A9%EC%9D%B8%EC%8B%9C-%EA%B8%B0%ED%9D%A5%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/용인시-기흥구-폐차장.html (점수표 111위)
- https://pyecha119.com/gu/%EC%9A%A9%EC%9D%B8%EC%8B%9C-%EC%88%98%EC%A7%80%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/용인시-수지구-폐차장.html (점수표 112위)
- https://pyecha119.com/gu/%EC%97%AC%EC%A3%BC%EC%8B%9C-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/여주시-폐차장.html (점수표 113위)
- https://pyecha119.com/gu/%ED%95%B4%EB%82%A8%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/해남군-폐차장.html (점수표 114위)
- https://pyecha119.com/gu/%EA%B0%95%EC%A7%84%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/강진군-폐차장.html (점수표 115위)
- https://pyecha119.com/gu/%EC%9D%8C%EC%84%B1%EA%B5%B0-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/음성군-폐차장.html (점수표 117위)
- https://pyecha119.com/gu/%EA%B3%A0%EC%96%91%EC%8B%9C-%EC%9D%BC%EC%82%B0%EB%8F%99%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html — gu/고양시-일산동구-폐차장.html (점수표 118위)
