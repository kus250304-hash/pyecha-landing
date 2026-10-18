# 구글 서치 콘솔 색인 요청 기록

병한님이 구글 서치 콘솔(왼쪽 "URL 검사" → 주소 붙여 넣기 → "색인 생성 요청")로 손으로 요청한 주소 기록입니다(2026-10-18부터).

- 매일 루틴이 `python3 scripts/pick_index_requests.py --write` 로 그날 요청할 10개를 골라 아래에 날짜와 함께 덧붙이고, 3시 보고 맨 끝 "오늘 구글 색인 요청 10개"에 주소 하나당 코드 상자 하나씩 적습니다.
- 고르는 순서: ① 그날 새로 만든 구·시 페이지 ② 아래 "문의가 온 페이지"와 같은 시·군의 구·동 페이지 ③ 점수표(`docs/region-priority-2026-10-15.md`) 순위 높은 지방 시·군 구 페이지. 이 파일에 이미 있는 주소는 다시 고르지 않습니다.
- 네이버·공용 IndexNow 자동 전송(`scripts/indexnow.py`)은 이와 따로 그대로 돕니다.

## 문의가 온 페이지

문의가 들어오면 날짜·경로와 함께 한 줄씩 더합니다(②의 기준).

- 2026-10-18 오후 12시 42분, 네이버 모바일 검색 → 상단 폼 문의, 30분 만에 거래 확정 — https://pyecha119.com/gu/%ED%99%94%EC%84%B1%EC%8B%9C-%EB%8F%99%ED%83%84%EA%B5%AC-%ED%8F%90%EC%B0%A8%EC%9E%A5.html (화성시 동탄구)
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
