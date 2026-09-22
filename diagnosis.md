# 기존 페이지 진단서 (diagnosis.md)

- 점검 대상: `pages/*.html` 168개 (index.html 제외)
- 방식: 스크립트 `scripts/diagnose_pages.py`로 읽기 전용 분석. 페이지는 수정하지 않았음
- 중복도 계산 시 각 페이지의 시도·시군구·동 이름, 랜드마크 이름, 그리고 전국 법정동명(3자 이상)을 모두 `▣`로 가린 뒤 비교했음 (= "지역명만 다른" 상태를 그대로 측정)

## 1. 페이지 간 본문 중복도

### 1-1. 구조적 사실
- 한 페이지 평균 본문 1325자(공백 제외) 중 **템플릿 고정 문구 804자(61%)**, 지역별로 달라지는 부분 522자(39%)
- 고정 문구에는 히어로 카피, 출장 방문 안내, 폐차 절차 4단계, 고정 FAQ 2개, 하단 고지, 푸터가 포함됨

### 1-2. 지역명·랜드마크명을 가린 뒤 페이지 쌍 유사도
- 비교한 쌍: 14,028쌍
- 3-gram 자카드 유사도 평균 **0.31**, 중앙값 0.27, 최대 0.89
- 문장 단위로 80% 이상 겹치는 쌍(= 지역명만 다르고 나머지가 같은 수준): **6쌍**
- 문장 단위로 60~80% 겹치는 쌍: 0쌍
- 페이지별 '이 페이지에만 있는 문장' 비율 평균 **43%** (최소 6%, 최대 79%)

### 1-3. 지역명만 다르고 나머지가 같은 페이지 쌍 (문장 겹침 80% 이상, 상위 40쌍)

| 문장 겹침 | 3-gram 유사도 | 페이지 A | 페이지 B |
|---|---|---|---|
| 83% | 0.89 | busan-geumjeong-jangjeon | gwangju-bukgu-yongbong |
| 83% | 0.86 | busan-geumjeong-jangjeon | daegu-bukgu-sangyeok |
| 83% | 0.84 | daegu-bukgu-sangyeok | gwangju-bukgu-yongbong |
| 83% | 0.83 | chungnam-seosan-dongmun | jeonbuk-jeongeup-suseong |
| 83% | 0.80 | gyeongbuk-pohang-namgu-daejam | gyeonggi-gimpo-sawoo |
| 83% | 0.69 | gangwon-wonju-musil | gyeonggi-gimpo-sawoo |

### 1-4. 여러 페이지에 그대로 반복되는 문장 상위 20개

| 등장 페이지 수 | 문장(지역명은 ▣) |
|---|---|
| 166 | ▣ ▣ ▣ 일대는 전국 폐차 협력업체 네트워크와 연계되어 상담과 방문 처리가 가능한 지역입니다. |
| 161 | ▣이 실제 방문 가능한 지역인가요? |
| 161 | ▣은 실제 서비스 가능 지역입니다. |
| 152 | 네, 가능합니다. |
| 88 | 전화 상담부터 방문까지 절차가 명확했습니다. |
| 78 | 필요한 서류를 미리 준비해 주시면 방문 당일 대부분의 절차를 함께 진행할 수 있습니다. |
| 77 | 서류 처리는 방문 당일 바로 되나요? |
| 71 | 인근 ▣, ▣에서도 방문 상담이 가능합니다. |
| 46 | 네, 혼잡한 시간대를 피해 방문을 원하시면 전화로 편한 시간을 말씀해 주세요. |
| 43 | 인근 ▣, ▣, ▣에서도 출장 방문 상담이 가능합니다. |
| 33 | 골목이 좁은 경우 인근 큰길 위치를 함께 안내해 주시면 원활합니다. |
| 30 | 단지 관리사무소 안내가 필요한 경우 미리 확인 후 방문 일정을 잡습니다. |
| 29 | 정확한 주차 위치를 알려주시면 방문 일정에 맞춰 찾아갑니다. |
| 24 | ▣ 근처 상가 주차장도 방문되나요? |
| 20 | 출입 절차가 있는 경우 미리 확인해 주시면 됩니다. |
| 19 | 아파트 단지 지하주차장에서도 처리가 가능한가요? |
| 17 | 편하신 시간을 전화로 말씀해 주시면 일정에 맞춰 방문합니다. |
| 17 | 상권 특성상 혼잡한 시간대가 있어 전화로 방문 시간을 조율해 드립니다. |
| 15 | ▣ 근처 관공서 주차장에서 진행했는데 출입 절차까지 미리 확인해 주셨습니다. |
| 15 | ▣ 근처 관공서 주차장도 방문되나요? |

- 후기 문장 504개 중 다른 페이지와 똑같은(지역명만 다른) 후기: **181개**
- 참고: 모든 후기는 실제 고객 후기가 아니라 생성 시 작성한 예시 문구임(이름은 'O' 마스킹). 실제 사례로 교체하기 전까지는 신뢰 요소로 쓰기 어려움

## 2. 분량 부족 · 랜드마크/지역 후기/지역 FAQ 누락

- 본문 글자 수(공백 제외): 평균 1325자, 최소 1271자, 최대 1487자
- 지역별 가변 부분: 평균 522자, 최소 470자, 최대 685자
- 본문 1,600자(공백 제외) 미만인 페이지: **168개 / 168개 — 전 페이지가 얇은 편**. 지역별 고유 내용이 500자 안팎이라 검색엔진 입장에서는 '같은 글에 지역명만 바꾼 페이지'로 묶일 위험이 큼
- 지역별 고유 분량이 가장 적은 15개:
  - incheon-bupyeong-bupyeong (본문 1271자 / 가변 470자)
  - gyeongbuk-gyeongsan-jungbang (본문 1274자 / 가변 480자)
  - gyeonggi-pyeongtaek-bijeon (본문 1274자 / 가변 484자)
  - gyeongnam-gimhae-buwon (본문 1281자 / 가변 485자)
  - chungbuk-chungju-yeonsu (본문 1285자 / 가변 486자)
  - seoul-gangbuk-mia (본문 1289자 / 가변 486자)
  - gyeonggi-seongnam-sujeong-taepyeong (본문 1298자 / 가변 487자)
  - gyeonggi-paju-geumchon (본문 1278자 / 가변 489자)
  - gyeongbuk-yeongju-hucheon (본문 1284자 / 가변 490자)
  - chungnam-nonsan-chwiam (본문 1287자 / 가변 492자)
  - gyeonggi-icheon-changjeon (본문 1281자 / 가변 492자)
  - jeonnam-gwangyang-jung (본문 1280자 / 가변 493자)
  - daegu-seogu-naedang (본문 1288자 / 가변 494자)
  - gyeongbuk-gyeongju-hwangnam (본문 1289자 / 가변 494자)
  - gyeonggi-yangju-deokjeong (본문 1283자 / 가변 494자)
- 랜드마크 이름이 비어 있는 페이지: **0개** []
- 지역 FAQ(5개) 중 동/랜드마크/구 이름이 들어간 문항이 3개 미만인 페이지: **152개**
  - busan-bukgu-hwamyeong (지역 FAQ 2/5)
  - busan-donggu-choryang (지역 FAQ 2/5)
  - busan-dongnae-oncheon (지역 FAQ 2/5)
  - busan-geumjeong-jangjeon (지역 FAQ 1/5)
  - busan-haeundae-u (지역 FAQ 2/5)
  - busan-junggu-nampo1ga (지역 FAQ 1/5)
  - busan-namgu-daeyeon (지역 FAQ 1/5)
  - busan-saha-hadan (지역 FAQ 1/5)
  - busan-sasang-gwaebeop (지역 FAQ 1/5)
  - busan-suyeong-gwangan (지역 FAQ 1/5)
  - busan-yeongdo-dongsam (지역 FAQ 2/5)
  - busan-yeonje-yeonsan (지역 FAQ 2/5)
  - chungbuk-cheongju-heungdeok-bongmyeong (지역 FAQ 2/5)
  - chungbuk-cheongju-sangdang-yongam (지역 FAQ 2/5)
  - chungbuk-cheongju-seowon-sachang (지역 FAQ 1/5)
  - chungbuk-chungju-yeonsu (지역 FAQ 2/5)
  - chungbuk-eumseong-eumseong (지역 FAQ 2/5)
  - chungbuk-jecheon-hwasan (지역 FAQ 2/5)
  - chungnam-asan-oncheon (지역 FAQ 2/5)
  - chungnam-cheonan-dongnam-sinbu (지역 FAQ 2/5)
  - chungnam-cheonan-seobuk-buldang (지역 FAQ 2/5)
  - chungnam-dangjin-eumnae (지역 FAQ 1/5)
  - chungnam-gongju-sanseong (지역 FAQ 2/5)
  - chungnam-nonsan-chwiam (지역 FAQ 2/5)
  - chungnam-seosan-dongmun (지역 FAQ 2/5)
  - daegu-bukgu-sangyeok (지역 FAQ 1/5)
  - daegu-dalseo-duryu (지역 FAQ 2/5)
  - daegu-dalseong-dasa (지역 FAQ 2/5)
  - daegu-donggu-sincheon (지역 FAQ 2/5)
  - daegu-junggu-dongseongno1ga (지역 FAQ 2/5)
- 후기 3개 중 동/랜드마크/구 이름이 하나도 없는 페이지: **26개**
  - busan-dongnae-oncheon
  - busan-geumjeong-jangjeon
  - busan-gijang-gijang
  - busan-saha-hadan
  - chungbuk-cheongju-seowon-sachang
  - daegu-bukgu-sangyeok
  - gwangju-bukgu-yongbong
  - gwangju-gwangsan-suwan
  - gyeonggi-ansan-sangnok-sa
  - gyeonggi-bucheon-wonmi-sang
  - gyeonggi-gimpo-gurae
  - gyeonggi-seongnam-jungwon-sangdaewon
  - gyeonggi-suwon-yeongtong-yeongtong
  - gyeonggi-yongin-suji-jukjeon
  - jeonbuk-jeonju-wansan-pungnam1ga
  - jeonnam-naju-bitgaram
  - seoul-dongdaemun-hoegi
  - seoul-gwangjin-guui
  - seoul-junggu-myeongdong1ga
  - seoul-mapo-hapjeong
  - seoul-seodaemun-sinchon
  - seoul-seongbuk-anam5ga
  - seoul-yeongdeungpo-dangsan
  - seoul-yeongdeungpo-yeongdeungpo4ga
  - ulsan-junggu-seongnam
  - ulsan-namgu-samsan
- 실제 '지역 사례'(사진·진행 과정이 있는 사례 글)는 **168개 전부 없음**. 현재 후기 섹션은 예시 후기 3개로만 구성됨

## 3. 다른 지역 이름·키워드가 섞인 페이지

- 수정 대상(법정동 목록에 없는 동명, 다른 시도명·시군구명, 다른 시도 랜드마크, 이웃 목록의 비(非)법정동 이름): **18개**
  - 이 중 대부분은 행정동 이름(예: 우장산동, 영종동)이나 시설명(킨텍스, 명지오션시티)이라 독자에게 틀린 말은 아님. 다만 사이트가 법정동 단위라 해당 이름으로는 페이지가 없어 내부 링크를 걸 수 없고, 광주 용봉동의 '용운동'처럼 실제 존재 여부가 불확실한 이름도 섞여 있음
- 검토 권장(같은 시도의 다른 구/군 동명·랜드마크 언급 — 대부분 이웃 언급이라 오류 아님): 16개
- 자기 시군구 안의 이웃 동 언급('인근 대치동, 삼성동에서도…')은 정상으로 보고 제외했음

### 3-1. 수정 대상

- **busan-gangseo-myeongji** (부산광역시 강서구 명지동)
  - '인근 …에서도' 이웃 목록의 '명지오션시티' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **busan-yeonje-yeonsan** (부산광역시 연제구 연산동)
  - '인근 …에서도' 이웃 목록의 '토곡동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **chungnam-asan-oncheon** (충청남도 아산시 온천동)
  - '인근 …에서도' 이웃 목록의 '온양동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **daegu-dalseong-dasa** (대구광역시 달성군 다사읍)
  - '인근 …에서도' 이웃 목록의 '성서 지역' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **daegu-namgu-daemyeong** (대구광역시 남구 대명동)
  - '인근 …에서도' 이웃 목록의 '앞산동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **gangwon-samcheok-gyo** (강원특별자치도 삼척시 교동)
  - '인근 …에서도' 이웃 목록의 '정라동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **gangwon-taebaek-hwangji** (강원특별자치도 태백시 황지동)
  - '인근 …에서도' 이웃 목록의 '문곡소도동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
  - '인근 …에서도' 이웃 목록의 '황연동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **gwangju-bukgu-yongbong** (광주광역시 북구 용봉동)
  - 법정동 목록상 자기 시도에 없는 동명 '용운동' (법정동으로는 대전광역시 동구에 있음 — 행정동 이름이면 표기는 맞으나 페이지 연결 불가)
- **gyeonggi-goyang-ilsanseo-daehwa** (경기도 고양시 일산서구 대화동)
  - '인근 …에서도' 이웃 목록의 '킨텍스' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
  - 법정동 목록상 자기 시도에 없는 동명 '송포동' (법정동으로는 경상남도 사천시에 있음 — 행정동 이름이면 표기는 맞으나 페이지 연결 불가)
- **gyeongnam-geoje-gohyeon** (경상남도 거제시 고현동)
  - '인근 …에서도' 이웃 목록의 '수양동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **gyeongnam-jinju-bonseong** (경상남도 진주시 본성동)
  - '인근 …에서도' 이웃 목록의 '성지동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **incheon-junggu-unseo** (인천광역시 중구 운서동)
  - '인근 …에서도' 이웃 목록의 '영종동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
  - '인근 …에서도' 이웃 목록의 '용유동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **jeju-seogwipo-donghong** (제주특별자치도 서귀포시 동홍동)
  - '인근 …에서도' 이웃 목록의 '정방동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **jeonnam-yeosu-jungang** (전라남도 여수시 중앙동)
  - 법정동 목록상 자기 시도에 없는 동명 '동문동' (법정동으로는 경상북도 안동시, 대구광역시 중구에 있음 — 행정동 이름이면 표기는 맞으나 페이지 연결 불가)
- **seoul-gangbuk-mia** (서울특별시 강북구 미아동)
  - '인근 …에서도' 이웃 목록의 '송중동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **seoul-gangseo-hwagok** (서울특별시 강서구 화곡동)
  - '인근 …에서도' 이웃 목록의 '우장산동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **seoul-guro-guro** (서울특별시 구로구 구로동)
  - '인근 …에서도' 이웃 목록의 '구로3동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음
- **seoul-gwanak-sillim** (서울특별시 관악구 신림동)
  - '인근 …에서도' 이웃 목록의 '서원동' — 법정동이 아님(행정동·시설·지역 통칭). 페이지가 없어 내부 링크로 이을 수 없음

### 3-2. 검토 권장 (이웃 구/군 언급)

- busan-donggu-choryang: 같은 시도 다른 구/군의 동명 '중앙동'(중구) — 이웃 언급이면 문제 없음
- busan-namgu-daeyeon: 같은 시도 다른 구/군의 동명 '광안동'(수영구) — 이웃 언급이면 문제 없음
- chungbuk-cheongju-heungdeok-bongmyeong: 같은 시도 다른 구/군의 동명 '사창동'(청주시 서원구) — 이웃 언급이면 문제 없음
- chungbuk-cheongju-sangdang-yongam: 같은 시도 다른 구/군의 동명 '산남동'(청주시 서원구) — 이웃 언급이면 문제 없음
- chungnam-cheonan-seobuk-buldang: 같은 시도 다른 구/군의 동명 '신방동'(천안시 동남구) — 이웃 언급이면 문제 없음
- daegu-donggu-sincheon: 같은 시도 다른 구/군의 동명 '범어동'(수성구) — 이웃 언급이면 문제 없음
- daegu-seogu-naedang: 같은 시도 다른 구/군의 동명 '두류동'(달서구) — 이웃 언급이면 문제 없음 / 다른 구/군 페이지의 랜드마크 '두류공원'(대구광역시 달서구) — 이웃 명소 언급이면 문제 없음
- gyeonggi-goyang-deogyang-hwajeong: 같은 시도 다른 구/군의 동명 '능곡동'(시흥시) — 이웃 언급이면 문제 없음
- gyeonggi-goyang-ilsandong-baekseok: 같은 시도 다른 구/군의 동명 '일산동'(고양시 일산서구) — 이웃 언급이면 문제 없음
- gyeonggi-suwon-paldal-ingye: 같은 시도 다른 구/군의 동명 '매탄동'(수원시 영통구) — 이웃 언급이면 문제 없음
- gyeonggi-yongin-suji-jukjeon: 같은 시도 다른 구/군의 동명 '보정동'(용인시 기흥구) — 이웃 언급이면 문제 없음
- gyeongnam-gimhae-buwon: 같은 시도 다른 구/군의 동명 '회현동'(창원시 진해구) — 이웃 언급이면 문제 없음
- seoul-gwanak-bongcheon: 같은 시도 다른 구/군의 동명 '사당동'(동작구) — 이웃 언급이면 문제 없음
- seoul-seodaemun-hongeun: 같은 시도 다른 구/군의 동명 '녹번동'(은평구) — 이웃 언급이면 문제 없음
- seoul-seongbuk-anam5ga: 같은 시도 다른 구/군의 동명 '제기동'(동대문구) — 이웃 언급이면 문제 없음
- seoul-yangcheon-mok: 같은 시도 다른 구/군의 동명 '대치동'(강남구) — 이웃 언급이면 문제 없음

## 4. title · description

- title 누락: 0개, description 누락: 0개
- title 중복: 0건, description 중복: 0건
- title이 40자를 넘는 페이지: 0개 (예: -)
- h1 개수 분포: {1: 168}
- canonical 태그 없음: 168개, Open Graph 태그 없음: 168개
- 모든 title이 `{지역} 폐차 비교매입 상담`, description이 `{지역} 폐차 비교매입 상담 및 출장 방문 서비스 안내 페이지입니다.` 한 가지 틀임. 중복은 아니지만 검색 결과에서 클릭을 유도하는 문구(비교·무료견인·당일 등)가 전혀 없음

## 5. sitemap.xml · 내부 링크

- sitemap.xml URL 수: 169 (루트 1 + 페이지 168)
- sitemap에 빠진 페이지: **0개** []
- sitemap에 있으나 파일이 없는 URL: 0개 []
- index.html 목록에 빠진 페이지: 0개 []
- 유효한 내부 링크가 하나도 없는 페이지: **168개** / 168 (동 페이지 → 다른 동/인덱스로 가는 링크가 전혀 없음. index → 동 페이지 방향만 존재)
- 깨진 내부 링크:
  - `/privacy-policy.html` : 168개 페이지 (파일 없음. 게다가 절대경로라 GitHub Pages 프로젝트 사이트에서는 `kus250304-hash.github.io/privacy-policy.html`로 가서 항상 404)
- sitemap의 lastmod가 생성일 기준으로 몰려 있음(내용 갱신 신호로 쓰이지 않음)
- robots.txt 없음(sitemap 위치를 검색엔진에 알려주는 줄이 없음)

## 6. 모바일 전화 버튼 (정적 검사)

이 환경에서는 실제 기기·브라우저를 열 수 없어 코드 기준으로만 확인했음.
- `href="tel:16006011"` 링크가 상단 버튼 + 하단 고정 버튼 2곳에 있는 페이지: 168/168 → 탭하면 다이얼러가 열림(정상)
- viewport 메타 태그: 168/168, 하단 고정 CTA(`.sticky-cta`): 168/168
- 하단 고정 버튼 높이: 글자 16px + 상하 패딩 12px ≈ 40px → 권장 터치 영역(44px)보다 약간 작음. 링크 영역이 글자 폭만큼이라 좌우 여백을 누르면 반응 없음
- 상단 버튼(글자 18px + 패딩 14px ≈ 50px)은 충분함
- 전화번호가 `tel:16006011`(하이픈 없음)로 통일되어 있어 iOS/Android 모두 문제 없음
- 문자(sms:)·카카오톡 버튼은 없음. 전화가 부담스러운 사용자를 받을 통로가 없음
- 견적 폼 없음 → 전화 외 전환 수단 0개

## 7. 결과를 약속하는 표현

- 검사어: 보장, 무조건, 100%, 1위, 최고, 최저가, 확실히, 반드시, 무료
- 검출된 페이지: **0개**
- 본문에서는 검출되지 않음(CSS의 `100%`는 문구가 아니므로 제외). 단, 현재 문구가 '약속'을 피하느라 전환 유도도 약함

## 8. 그 밖에 눈에 띈 것

- 페이지 파일 크기 평균 13.6KB (CSS 인라인, 외부 JS·이미지 없음) → 속도는 좋음
- 후기 이름이 '김O현'식 마스킹이라 실제 후기처럼 보이지 않고, 별점만 있고 날짜·차종·사진이 없음
- 히어로 문구가 '알아보세요' 수준으로 약함. 숫자(누적 상담, 당일 접수)·신뢰 문구·견적 폼이 없음
- '폐차 절차' 4단계가 모든 페이지에서 동일하고 폐차 유형(일반/차령초과/조기/상속)·서류·기간 안내가 없음
- 하단 고지·푸터에 사업자 정보(상호·대표·주소·사업자번호)가 없음
- 유튜브·블로그 링크가 히어로에도 있어 첫 화면에서 이탈 경로가 됨
- 자동 생성 루틴(`폐차 랜딩페이지 자동 생성`, 매일 05:02 UTC)이 지금 템플릿으로 매일 50~100개씩 추가 중 → 새 템플릿 확정 전까지는 재작업 대상이 계속 늘어남

## 부록. 페이지별 요약표

가변 = 지역별로 달라지는 본문 글자 수. 최유사 = 문장 겹침이 가장 높은 페이지와 그 비율. 지역FAQ = 5개 중 지역명이 들어간 문항 수. 지역후기 = 3개 중 지역명이 들어간 후기 수.

| 페이지 | 본문 | 가변 | 최유사(겹침) | 지역FAQ | 지역후기 | 지역키워드 의심 | 내부링크 |
|---|---|---|---|---|---|---|---|
| busan-bukgu-hwamyeong | 1324 | 527 | jeonnam-suncheon-jorye (78%) | 2/5 | 1/3 | 0 | 0 |
| busan-donggu-choryang | 1329 | 535 | gyeonggi-seongnam-jungwon-sangdaewon (33%) | 2/5 | 1/3 | 1 | 0 |
| busan-dongnae-oncheon | 1323 | 521 | daejeon-yuseong-bongmyeong (33%) | 2/5 | 0/3 | 0 | 0 |
| busan-gangseo-myeongji | 1311 | 507 | chungnam-cheonan-seobuk-buldang (56%) | 3/5 | 2/3 | 1 | 0 |
| busan-geumjeong-jangjeon | 1313 | 510 | gwangju-bukgu-yongbong (83%) | 1/5 | 0/3 | 0 | 0 |
| busan-gijang-gijang | 1345 | 543 | gyeongbuk-yeongju-hucheon (29%) | 3/5 | 0/3 | 0 | 0 |
| busan-haeundae-u | 1406 | 607 | seoul-guro-guro (22%) | 2/5 | 2/3 | 0 | 0 |
| busan-junggu-nampo1ga | 1339 | 523 | jeonnam-yeosu-jungang (39%) | 1/5 | 1/3 | 0 | 0 |
| busan-namgu-daeyeon | 1318 | 521 | gyeonggi-goyang-deogyang-hwajeong (37%) | 1/5 | 1/3 | 1 | 0 |
| busan-saha-hadan | 1315 | 512 | seoul-jungnang-myeonmok (39%) | 1/5 | 0/3 | 0 | 0 |
| busan-sasang-gwaebeop | 1331 | 522 | incheon-michuhol-juan (50%) | 1/5 | 1/3 | 0 | 0 |
| busan-suyeong-gwangan | 1396 | 591 | busan-junggu-nampo1ga (22%) | 1/5 | 1/3 | 0 | 0 |
| busan-yeongdo-dongsam | 1324 | 523 | gangwon-samcheok-gyo (22%) | 2/5 | 2/3 | 0 | 0 |
| busan-yeonje-yeonsan | 1307 | 504 | chungnam-seosan-dongmun (78%) | 2/5 | 2/3 | 1 | 0 |
| chungbuk-cheongju-heungdeok-bongmyeong | 1327 | 510 | gyeonggi-hwaseong-byeongjeom (67%) | 2/5 | 1/3 | 1 | 0 |
| chungbuk-cheongju-sangdang-yongam | 1324 | 507 | gyeonggi-gimpo-gurae (39%) | 2/5 | 1/3 | 1 | 0 |
| chungbuk-cheongju-seowon-sachang | 1340 | 522 | seoul-seodaemun-sinchon (67%) | 1/5 | 0/3 | 0 | 0 |
| chungbuk-chungju-yeonsu | 1285 | 486 | incheon-gyeyang-gyesan (67%) | 2/5 | 2/3 | 0 | 0 |
| chungbuk-eumseong-eumseong | 1293 | 497 | chungnam-seosan-dongmun (67%) | 2/5 | 2/3 | 0 | 0 |
| chungbuk-jecheon-hwasan | 1302 | 503 | ulsan-ulju-beomseo (50%) | 2/5 | 1/3 | 0 | 0 |
| chungnam-asan-oncheon | 1313 | 517 | gyeongbuk-gyeongju-hwangnam (50%) | 2/5 | 2/3 | 1 | 0 |
| chungnam-cheonan-dongnam-sinbu | 1334 | 514 | incheon-michuhol-juan (67%) | 2/5 | 1/3 | 0 | 0 |
| chungnam-cheonan-seobuk-buldang | 1350 | 532 | gwangju-gwangsan-suwan (56%) | 2/5 | 1/3 | 1 | 0 |
| chungnam-dangjin-eumnae | 1296 | 500 | gyeonggi-seongnam-jungwon-sangdaewon (39%) | 1/5 | 1/3 | 0 | 0 |
| chungnam-gongju-sanseong | 1301 | 506 | gyeongbuk-gyeongju-hwangnam (67%) | 2/5 | 1/3 | 0 | 0 |
| chungnam-nonsan-chwiam | 1287 | 492 | gyeongbuk-yeongju-hucheon (24%) | 2/5 | 2/3 | 0 | 0 |
| chungnam-seosan-dongmun | 1298 | 502 | jeonbuk-jeongeup-suseong (83%) | 2/5 | 1/3 | 0 | 0 |
| daegu-bukgu-sangyeok | 1317 | 521 | busan-geumjeong-jangjeon (83%) | 1/5 | 0/3 | 0 | 0 |
| daegu-dalseo-duryu | 1384 | 582 | incheon-namdong-guwol (28%) | 2/5 | 1/3 | 0 | 0 |
| daegu-dalseong-dasa | 1337 | 536 | gyeonggi-paju-geumchon (32%) | 2/5 | 1/3 | 1 | 0 |
| daegu-donggu-sincheon | 1321 | 526 | seoul-yeongdeungpo-yeongdeungpo4ga (24%) | 2/5 | 1/3 | 1 | 0 |
| daegu-junggu-dongseongno1ga | 1317 | 503 | gyeonggi-suwon-paldal-ingye (39%) | 2/5 | 1/3 | 0 | 0 |
| daegu-namgu-daemyeong | 1306 | 508 | incheon-michuhol-juan (61%) | 2/5 | 2/3 | 1 | 0 |
| daegu-seogu-naedang | 1288 | 494 | gyeonggi-anyang-dongan-pyeongchon (33%) | 1/5 | 2/3 | 2 | 0 |
| daegu-suseong-beomeo | 1329 | 526 | gwangju-seogu-chipyeong (61%) | 2/5 | 1/3 | 0 | 0 |
| daejeon-daedeok-ojeong | 1328 | 522 | gyeonggi-ansan-sangnok-sa (33%) | 1/5 | 1/3 | 0 | 0 |
| daejeon-donggu-panam | 1304 | 510 | jeonnam-suncheon-jorye (72%) | 2/5 | 1/3 | 0 | 0 |
| daejeon-junggu-eunhaeng | 1303 | 506 | gyeonggi-uijeongbu-uijeongbu (67%) | 2/5 | 1/3 | 0 | 0 |
| daejeon-seogu-dunsan | 1316 | 519 | gyeonggi-gimpo-sawoo (78%) | 2/5 | 1/3 | 0 | 0 |
| daejeon-yuseong-bongmyeong | 1395 | 593 | busan-dongnae-oncheon (33%) | 3/5 | 2/3 | 0 | 0 |
| daejeon-yuseong-doryong | 1316 | 515 | gyeongnam-yangsan-jungbu (29%) | 1/5 | 1/3 | 0 | 0 |
| gangwon-chuncheon-geunhwa | 1335 | 517 | incheon-michuhol-juan (56%) | 2/5 | 2/3 | 0 | 0 |
| gangwon-donghae-cheongok | 1326 | 512 | jeonbuk-jeongeup-suseong (78%) | 3/5 | 2/3 | 0 | 0 |
| gangwon-gangneung-chodang | 1328 | 511 | gangwon-chuncheon-geunhwa (50%) | 2/5 | 1/3 | 0 | 0 |
| gangwon-hongcheon-hongcheon | 1314 | 501 | gyeongbuk-yeongju-hucheon (29%) | 2/5 | 1/3 | 0 | 0 |
| gangwon-samcheok-gyo | 1322 | 518 | gyeongnam-tongyeong-mujeon (28%) | 2/5 | 1/3 | 1 | 0 |
| gangwon-sokcho-joyang | 1362 | 546 | seoul-yangcheon-mok (61%) | 2/5 | 2/3 | 0 | 0 |
| gangwon-taebaek-hwangji | 1324 | 510 | daegu-seogu-naedang (22%) | 2/5 | 1/3 | 2 | 0 |
| gangwon-wonju-musil | 1335 | 521 | gyeonggi-gimpo-sawoo (83%) | 2/5 | 2/3 | 0 | 0 |
| gwangju-bukgu-unam | 1314 | 519 | gyeonggi-uijeongbu-howon (33%) | 2/5 | 1/3 | 0 | 0 |
| gwangju-bukgu-yongbong | 1308 | 512 | busan-geumjeong-jangjeon (83%) | 1/5 | 0/3 | 1 | 0 |
| gwangju-donggu-gyerim | 1398 | 602 | busan-geumjeong-jangjeon (33%) | 2/5 | 2/3 | 0 | 0 |
| gwangju-gwangsan-suwan | 1327 | 525 | jeonbuk-gunsan-naun (61%) | 1/5 | 0/3 | 0 | 0 |
| gwangju-namgu-bongseon | 1298 | 504 | gyeonggi-suwon-yeongtong-yeongtong (33%) | 2/5 | 1/3 | 0 | 0 |
| gwangju-seogu-chipyeong | 1318 | 523 | seoul-geumcheon-gasan (72%) | 2/5 | 1/3 | 0 | 0 |
| gyeongbuk-andong-unheung | 1298 | 503 | gyeonggi-osan-osan (61%) | 2/5 | 1/3 | 0 | 0 |
| gyeongbuk-gumi-wonpyeong | 1296 | 501 | gyeonggi-uijeongbu-uijeongbu (67%) | 2/5 | 2/3 | 0 | 0 |
| gyeongbuk-gyeongju-hwangnam | 1289 | 494 | chungnam-gongju-sanseong (67%) | 2/5 | 1/3 | 0 | 0 |
| gyeongbuk-gyeongsan-jungbang | 1274 | 480 | gyeonggi-ansan-sangnok-sa (33%) | 2/5 | 1/3 | 0 | 0 |
| gyeongbuk-pohang-namgu-daejam | 1328 | 518 | gyeonggi-gimpo-sawoo (83%) | 2/5 | 2/3 | 0 | 0 |
| gyeongbuk-yeongju-hucheon | 1284 | 490 | gangwon-hongcheon-hongcheon (29%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-ansan-danwon-gojan | 1317 | 506 | gangwon-donghae-cheongok (67%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-ansan-sangnok-sa | 1326 | 518 | gyeongbuk-gyeongsan-jungbang (33%) | 1/5 | 0/3 | 0 | 0 |
| gyeonggi-anseong-bongsan | 1287 | 497 | jeonbuk-jeongeup-suseong (78%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-anyang-dongan-pyeongchon | 1317 | 507 | gwangju-namgu-bongseon (33%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-bucheon-wonmi-jung | 1312 | 510 | seoul-yangcheon-mok (56%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-bucheon-wonmi-sang | 1305 | 502 | daegu-donggu-sincheon (24%) | 2/5 | 0/3 | 0 | 0 |
| gyeonggi-gimpo-gurae | 1303 | 510 | chungbuk-cheongju-sangdang-yongam (39%) | 1/5 | 0/3 | 0 | 0 |
| gyeonggi-gimpo-sawoo | 1303 | 513 | gyeongbuk-pohang-namgu-daejam (83%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-goyang-deogyang-hwajeong | 1308 | 498 | busan-namgu-daeyeon (37%) | 2/5 | 1/3 | 1 | 0 |
| gyeonggi-goyang-ilsandong-baekseok | 1353 | 533 | gyeonggi-hanam-sinjang (61%) | 2/5 | 1/3 | 1 | 0 |
| gyeonggi-goyang-ilsanseo-daehwa | 1345 | 528 | seoul-yangcheon-mok (67%) | 2/5 | 2/3 | 2 | 0 |
| gyeonggi-gunpo-sanbon | 1307 | 514 | gyeonggi-hanam-sinjang (67%) | 3/5 | 2/3 | 0 | 0 |
| gyeonggi-guri-inchang | 1286 | 497 | incheon-gyeyang-jakjeon (37%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-gwangmyeong-cheolsan | 1295 | 506 | incheon-michuhol-juan (56%) | 3/5 | 1/3 | 0 | 0 |
| gyeonggi-hanam-sinjang | 1303 | 511 | gyeonggi-gunpo-sanbon (67%) | 3/5 | 2/3 | 0 | 0 |
| gyeonggi-hwaseong-byeongjeom | 1310 | 518 | chungbuk-cheongju-heungdeok-bongmyeong (67%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-icheon-changjeon | 1281 | 492 | seoul-gwanak-sillim (56%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-namyangju-dasan | 1310 | 512 | busan-gangseo-myeongji (50%) | 1/5 | 1/3 | 0 | 0 |
| gyeonggi-osan-osan | 1298 | 509 | gyeongbuk-andong-unheung (61%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-paju-geumchon | 1278 | 489 | jeonbuk-namwon-cheongeo (37%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-pyeongtaek-bijeon | 1274 | 484 | chungnam-seosan-dongmun (72%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-seongnam-bundang-jeongja | 1401 | 587 | daegu-suseong-beomeo (44%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-seongnam-jungwon-sangdaewon | 1332 | 509 | chungnam-dangjin-eumnae (39%) | 1/5 | 0/3 | 0 | 0 |
| gyeonggi-seongnam-sujeong-taepyeong | 1298 | 487 | gyeonggi-anseong-bongsan (50%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-siheung-jeongwang | 1290 | 501 | gyeonggi-ansan-danwon-gojan (56%) | 3/5 | 1/3 | 0 | 0 |
| gyeonggi-suwon-jangan-jowon | 1309 | 495 | daegu-seogu-naedang (33%) | 1/5 | 1/3 | 0 | 0 |
| gyeonggi-suwon-paldal-ingye | 1325 | 512 | daejeon-junggu-eunhaeng (56%) | 3/5 | 2/3 | 1 | 0 |
| gyeonggi-suwon-yeongtong-yeongtong | 1337 | 527 | gwangju-namgu-bongseon (33%) | 2/5 | 0/3 | 0 | 0 |
| gyeonggi-uijeongbu-howon | 1300 | 504 | gwangju-bukgu-unam (33%) | 1/5 | 1/3 | 0 | 0 |
| gyeonggi-uijeongbu-uijeongbu | 1302 | 495 | gyeonggi-yangju-deokjeong (67%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-yangju-deokjeong | 1283 | 494 | gyeonggi-uijeongbu-uijeongbu (67%) | 2/5 | 2/3 | 0 | 0 |
| gyeonggi-yongin-giheung-singal | 1323 | 511 | daejeon-yuseong-doryong (24%) | 2/5 | 1/3 | 0 | 0 |
| gyeonggi-yongin-suji-jukjeon | 1332 | 515 | chungbuk-cheongju-seowon-sachang (61%) | 1/5 | 0/3 | 1 | 0 |
| gyeongnam-changwon-seongsan-sangnam | 1318 | 499 | incheon-michuhol-juan (67%) | 2/5 | 2/3 | 0 | 0 |
| gyeongnam-geoje-gohyeon | 1305 | 509 | chungbuk-eumseong-eumseong (61%) | 2/5 | 1/3 | 1 | 0 |
| gyeongnam-gimhae-buwon | 1281 | 485 | chungnam-seosan-dongmun (67%) | 3/5 | 2/3 | 1 | 0 |
| gyeongnam-jinju-bonseong | 1292 | 497 | chungnam-gongju-sanseong (61%) | 2/5 | 2/3 | 1 | 0 |
| gyeongnam-tongyeong-mujeon | 1320 | 519 | busan-namgu-daeyeon (33%) | 1/5 | 1/3 | 0 | 0 |
| gyeongnam-yangsan-jungbu | 1297 | 502 | gyeonggi-paju-geumchon (33%) | 2/5 | 1/3 | 0 | 0 |
| incheon-bupyeong-bupyeong | 1271 | 470 | gyeongnam-changwon-seongsan-sangnam (41%) | 3/5 | 1/3 | 0 | 0 |
| incheon-gyeyang-gyesan | 1302 | 501 | chungbuk-chungju-yeonsu (67%) | 2/5 | 2/3 | 0 | 0 |
| incheon-gyeyang-jakjeon | 1320 | 519 | gyeonggi-guri-inchang (37%) | 2/5 | 1/3 | 0 | 0 |
| incheon-junggu-sinpo | 1310 | 513 | daegu-namgu-daemyeong (44%) | 2/5 | 1/3 | 0 | 0 |
| incheon-junggu-unseo | 1325 | 528 | gyeonggi-ansan-sangnok-sa (22%) | 2/5 | 1/3 | 2 | 0 |
| incheon-michuhol-juan | 1308 | 500 | seoul-gangdong-cheonho (72%) | 2/5 | 2/3 | 0 | 0 |
| incheon-namdong-guwol | 1411 | 605 | incheon-michuhol-juan (33%) | 2/5 | 1/3 | 0 | 0 |
| incheon-namdong-nonhyeon | 1320 | 518 | gyeonggi-goyang-deogyang-hwajeong (33%) | 2/5 | 1/3 | 0 | 0 |
| incheon-seogu-cheongna | 1329 | 532 | incheon-yeonsu-songdo (61%) | 2/5 | 1/3 | 0 | 0 |
| incheon-yeonsu-songdo | 1335 | 530 | incheon-seogu-cheongna (61%) | 2/5 | 1/3 | 0 | 0 |
| jeju-jeju-nohyeong | 1413 | 598 | busan-saha-hadan (28%) | 3/5 | 2/3 | 0 | 0 |
| jeju-seogwipo-donghong | 1329 | 508 | gangwon-samcheok-gyo (24%) | 2/5 | 1/3 | 1 | 0 |
| jeonbuk-gunsan-naun | 1338 | 522 | jeonnam-suncheon-jorye (78%) | 2/5 | 2/3 | 0 | 0 |
| jeonbuk-iksan-changin | 1320 | 507 | seoul-gwanak-sillim (67%) | 2/5 | 2/3 | 0 | 0 |
| jeonbuk-jeongeup-suseong | 1308 | 494 | chungnam-seosan-dongmun (83%) | 2/5 | 1/3 | 0 | 0 |
| jeonbuk-jeonju-wansan-pungnam1ga | 1379 | 522 | chungnam-gongju-sanseong (56%) | 2/5 | 0/3 | 0 | 0 |
| jeonbuk-namwon-cheongeo | 1310 | 496 | gyeonggi-paju-geumchon (37%) | 2/5 | 1/3 | 0 | 0 |
| jeonnam-gwangyang-jung | 1280 | 493 | gyeonggi-gimpo-gurae (24%) | 1/5 | 1/3 | 0 | 0 |
| jeonnam-mokpo-yonghae | 1312 | 516 | jeonnam-suncheon-jorye (72%) | 3/5 | 2/3 | 0 | 0 |
| jeonnam-naju-bitgaram | 1353 | 544 | gyeonggi-gimpo-sawoo (56%) | 1/5 | 0/3 | 0 | 0 |
| jeonnam-suncheon-jorye | 1318 | 520 | busan-bukgu-hwamyeong (78%) | 2/5 | 2/3 | 0 | 0 |
| jeonnam-yeosu-jungang | 1293 | 496 | gyeongnam-jinju-bonseong (61%) | 2/5 | 2/3 | 1 | 0 |
| sejong-eojin | 1323 | 528 | daejeon-seogu-dunsan (72%) | 2/5 | 1/3 | 0 | 0 |
| sejong-hansol | 1296 | 504 | chungbuk-cheongju-sangdang-yongam (33%) | 2/5 | 1/3 | 0 | 0 |
| seoul-dobong-chang | 1314 | 523 | seoul-yangcheon-mok (61%) | 2/5 | 2/3 | 0 | 0 |
| seoul-dongdaemun-cheongnyangni | 1337 | 518 | seoul-jungnang-myeonmok (39%) | 2/5 | 1/3 | 0 | 0 |
| seoul-dongdaemun-hoegi | 1359 | 544 | gyeonggi-suwon-paldal-ingye (28%) | 1/5 | 0/3 | 0 | 0 |
| seoul-dongjak-noryangjin | 1324 | 509 | incheon-michuhol-juan (56%) | 2/5 | 1/3 | 0 | 0 |
| seoul-eunpyeong-bulgwang | 1320 | 518 | gyeongbuk-gumi-wonpyeong (61%) | 2/5 | 1/3 | 0 | 0 |
| seoul-gangbuk-mia | 1289 | 486 | chungbuk-chungju-yeonsu (61%) | 2/5 | 2/3 | 1 | 0 |
| seoul-gangdong-cheonho | 1327 | 521 | incheon-michuhol-juan (72%) | 2/5 | 1/3 | 0 | 0 |
| seoul-gangnam-daechi | 1397 | 596 | seoul-yangcheon-mok (28%) | 2/5 | 1/3 | 0 | 0 |
| seoul-gangnam-samseong | 1420 | 619 | busan-donggu-choryang (28%) | 2/5 | 1/3 | 0 | 0 |
| seoul-gangnam-yeoksam | 1487 | 685 | seoul-dongdaemun-cheongnyangni (28%) | 3/5 | 2/3 | 0 | 0 |
| seoul-gangseo-banghwa | 1342 | 541 | gyeongbuk-yeongju-hucheon (24%) | 3/5 | 1/3 | 0 | 0 |
| seoul-gangseo-hwagok | 1320 | 519 | gyeonggi-osan-osan (61%) | 2/5 | 2/3 | 1 | 0 |
| seoul-geumcheon-gasan | 1313 | 508 | seoul-guro-guro (78%) | 2/5 | 1/3 | 0 | 0 |
| seoul-guro-guro | 1337 | 532 | seoul-geumcheon-gasan (78%) | 2/5 | 1/3 | 1 | 0 |
| seoul-gwanak-bongcheon | 1344 | 543 | busan-namgu-daeyeon (32%) | 2/5 | 1/3 | 1 | 0 |
| seoul-gwanak-sillim | 1307 | 506 | jeonbuk-iksan-changin (67%) | 2/5 | 1/3 | 1 | 0 |
| seoul-gwangjin-guui | 1368 | 562 | gyeonggi-goyang-deogyang-hwajeong (32%) | 2/5 | 0/3 | 0 | 0 |
| seoul-jongno-jongno1ga | 1365 | 554 | gyeonggi-seongnam-sujeong-taepyeong (22%) | 2/5 | 1/3 | 0 | 0 |
| seoul-junggu-myeongdong1ga | 1318 | 513 | daegu-junggu-dongseongno1ga (33%) | 1/5 | 0/3 | 0 | 0 |
| seoul-jungnang-myeonmok | 1298 | 496 | incheon-gyeyang-gyesan (61%) | 2/5 | 1/3 | 0 | 0 |
| seoul-jungnang-sangbong | 1337 | 536 | gyeonggi-goyang-deogyang-hwajeong (28%) | 2/5 | 1/3 | 0 | 0 |
| seoul-mapo-hapjeong | 1345 | 540 | gyeonggi-goyang-deogyang-hwajeong (28%) | 1/5 | 0/3 | 0 | 0 |
| seoul-mapo-seogyo | 1424 | 618 | daejeon-yuseong-bongmyeong (28%) | 2/5 | 2/3 | 0 | 0 |
| seoul-nowon-gongneung | 1351 | 548 | seoul-dongdaemun-cheongnyangni (33%) | 2/5 | 2/3 | 0 | 0 |
| seoul-nowon-sanggye | 1331 | 530 | seoul-yangcheon-mok (61%) | 2/5 | 2/3 | 0 | 0 |
| seoul-seocho-banpo | 1384 | 580 | daegu-donggu-sincheon (24%) | 1/5 | 1/3 | 0 | 0 |
| seoul-seocho-seocho | 1317 | 514 | gyeonggi-pyeongtaek-bijeon (39%) | 2/5 | 2/3 | 0 | 0 |
| seoul-seodaemun-hongeun | 1336 | 528 | gyeonggi-anyang-dongan-pyeongchon (28%) | 1/5 | 1/3 | 1 | 0 |
| seoul-seodaemun-sinchon | 1327 | 517 | busan-geumjeong-jangjeon (72%) | 1/5 | 0/3 | 0 | 0 |
| seoul-seongbuk-anam5ga | 1373 | 545 | seoul-yeongdeungpo-yeongdeungpo4ga (24%) | 1/5 | 0/3 | 1 | 0 |
| seoul-seongbuk-donam | 1342 | 539 | gyeonggi-suwon-jangan-jowon (28%) | 1/5 | 2/3 | 0 | 0 |
| seoul-seongdong-seongsu1ga | 1353 | 532 | daegu-junggu-dongseongno1ga (28%) | 2/5 | 1/3 | 0 | 0 |
| seoul-songpa-jamsil | 1335 | 533 | chungnam-cheonan-seobuk-buldang (50%) | 3/5 | 1/3 | 0 | 0 |
| seoul-songpa-munjeong | 1387 | 583 | gyeonggi-guri-inchang (28%) | 2/5 | 1/3 | 0 | 0 |
| seoul-yangcheon-mok | 1306 | 513 | gyeonggi-goyang-ilsanseo-daehwa (67%) | 2/5 | 2/3 | 1 | 0 |
| seoul-yeongdeungpo-dangsan | 1361 | 552 | daegu-suseong-beomeo (28%) | 1/5 | 0/3 | 0 | 0 |
| seoul-yeongdeungpo-yeongdeungpo4ga | 1399 | 560 | daegu-donggu-sincheon (24%) | 2/5 | 0/3 | 0 | 0 |
| seoul-yeongdeungpo-yeouido | 1358 | 538 | seoul-geumcheon-gasan (39%) | 2/5 | 1/3 | 0 | 0 |
| seoul-yongsan-itaewon | 1332 | 520 | gyeonggi-seongnam-sujeong-taepyeong (33%) | 2/5 | 2/3 | 0 | 0 |
| ulsan-bukgu-yangjeong | 1300 | 506 | gyeonggi-goyang-deogyang-hwajeong (33%) | 1/5 | 1/3 | 0 | 0 |
| ulsan-donggu-ilsan | 1317 | 521 | gyeongnam-tongyeong-mujeon (33%) | 2/5 | 1/3 | 0 | 0 |
| ulsan-junggu-seongnam | 1306 | 507 | daejeon-junggu-eunhaeng (50%) | 1/5 | 0/3 | 0 | 0 |
| ulsan-namgu-samsan | 1310 | 514 | incheon-michuhol-juan (56%) | 2/5 | 0/3 | 0 | 0 |
| ulsan-ulju-beomseo | 1307 | 502 | chungbuk-eumseong-eumseong (61%) | 1/5 | 1/3 | 0 | 0 |
