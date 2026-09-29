# 2026-07-01 행정구역 개편 확인 (2026-09-29)

## 확인한 내용

| 항목 | 결과 | 출처 |
|---|---|---|
| 인천 중구·동구 | 중구 내륙 44개 동 + 동구 7개 동 → **제물포구**, 중구 영종·용유·무의 8개 동(중산·운남·운서·운북·을왕·남북·덕교·무의동) → **영종구** | [경기일보](https://www.kyeonggi.com/article/20240109580184), [입법예고](https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/2216372/detailRP), [영종구(위키백과)](https://ko.wikipedia.org/wiki/%EC%98%81%EC%A2%85%EA%B5%AC) |
| (b) 운서동 | 영종구 맞음 | 위 영종구 자료 |
| 인천 서구 | 아라뱃길 북쪽 10개 동(마전·당하·원당·불로·대곡·금곡·오류·왕길·백석·시천동) → **검단구**, 남은 서구는 같은 날 이름이 **서해구**로 바뀜(2026-05-07 법률 의결) | [인천투데이](https://www.incheontoday.com/news/articleView.html?idxno=246573), [검단구(위키백과)](https://ko.wikipedia.org/wiki/%EA%B2%80%EB%8B%A8%EA%B5%AC), [인천시 소식](https://www.incheon.go.kr/moo/MOO020101/3032647), [경향신문](https://www.khan.co.kr/article/202605071726001/) |
| (a) 청라동 | 아라뱃길 남쪽이라 검단구가 아니라 **서해구**(옛 서구) | 위 서구·검단구 자료 |
| 옛 인천 중구청 | 제물포구청 **신포청사**(신포로27번길 80, 관동1가) | [제물포구청](https://www.jemulpo.go.kr/main/introduce/guide/office-sinpo.jsp) |
| 광주광역시 + 전라남도 | 2026-07-01 **전남광주통합특별시** 출범(특별법 제21446호) | [국가법령정보센터](https://www.law.go.kr/lsInfoP.do?lsiSeq=284111), [서울신문](https://www.seoul.co.kr/news/society/2026/07/01/20260701500018) |
| (c) 통합시 안 표기 | 옛 광주 5개 자치구·전남 22개 시군 이름은 그대로: "전남광주통합특별시 동구", "전남광주통합특별시 목포시". 행정코드 순서는 전남 5개 시 → 광주 5개 구 → 전남 17개 군 | [동구(전남광주통합특별시)/행정](https://namu.wiki/w/%EB%8F%99%EA%B5%AC(%EC%A0%84%EB%82%A8%EA%B4%91%EC%A3%BC%ED%86%B5%ED%95%A9%ED%8A%B9%EB%B3%84%EC%8B%9C)/%ED%96%89%EC%A0%95), [노컷뉴스](https://www.nocutnews.co.kr/news/6509514), [아시아경제](https://view.asiae.co.kr/article/2026042815344348165) |
| (d) 짧은 이름 | 법률상 약칭은 "광주특별시". 두세 글자 공식 줄임말은 없어, 페이지 제목·문의 메일 제목에는 옛 광주 구와 전남 시군 모두에 맞는 **"전남광주"** 를 씀 | [오마이뉴스](https://www.ohmynews.com/NWS_Web/View/at_pg.aspx?CNTN_CD=A0003202072), [전남광주통합특별시(위키백과)](https://ko.wikipedia.org/wiki/%EC%A0%84%EB%82%A8%EA%B4%91%EC%A3%BC%ED%86%B5%ED%95%A9%ED%8A%B9%EB%B3%84%EC%8B%9C) |

## 새 법정동코드: 아직 반영 못 함

- 새 법정동코드 목록(행정안전부 행정표준코드, 국토교통부 전국 법정동)은 이 작업 환경에서 `www.code.go.kr`, `www.data.go.kr`, `business.juso.go.kr` 접속이 막혀 내려받지 못했고, 웹 검색 결과에는 동 단위 코드가 나오지 않았습니다.
- 그래서 `legal_dong_list.csv` 703줄(인천 80 + 광주·전남 623)과 `regions.json` 38개 항목은 **시도·시군구 이름만 새 것으로 바꾸고 코드는 옛 코드 그대로** 두었습니다(지어낸 코드 없음). 이름과 코드가 같이 움직이므로 `pick_next_regions.py`·`import_batch.py` 중복 검사는 그대로 맞습니다.
- 공식 파일을 받을 수 있게 되면: CSV 의 해당 703줄 코드를 새 코드로 바꾸고, `regions.json` 38개 항목의 `code` 를 새 코드로, 옛 코드를 `old_code` 로 옮깁니다.
  - 공식 파일: [행정표준코드관리시스템 전체 다운로드](https://www.code.go.kr/stdcodesrch/codeAllDownloadL.do), [국토교통부 전국 법정동](https://www.data.go.kr/data/15063424/fileData.do), [주소기반산업지원서비스 행정구역 코드 변경안내](https://business.juso.go.kr/addrlink/CommonPageLink.do?link=/sportPolicy/standard/intrlStd/info_etc8)
