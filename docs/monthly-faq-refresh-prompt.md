# 월 1회 FAQ 풀 갱신 지시문 (초안, 매달 첫째 주 월요일, 운영자 PC)

통화 분석 자료(`C:\Users\AOMG\Documents\통화녹음백업\_분석\`)와 폼·문자 질문 모음은 운영자 PC 에만 있으므로
**PC 의 Claude 앱 예약 작업**으로 돌립니다. 배경과 규칙은 `docs/roadmap.md` 12절.

- 예약 작업의 폴더: PC 에 받아 둔 pyecha-landing 저장소 폴더
- 예약 작업의 지시문: "저장소의 docs/monthly-faq-refresh-prompt.md 파일을 열어서, 그 안의 코드 상자에 있는 지시문을 처음부터 끝까지 그대로 따라 실행해."
- 실제 지시문은 **아래 코드 상자 하나**뿐입니다. 바꿀 때는 이 코드 상자 안만 고쳐 main 에 올립니다.
- 초안 상태: `data/faq_pool.json` 과 `scripts/faq_pool.py` 가 아직 없습니다(roadmap 12절 "첫 실행 전에 할 준비"). 없으면 아래 2번의 예외대로 진행합니다.

```text
너는 pyecha-landing 저장소의 월 1회 FAQ 풀 갱신 담당이다. 저장소의 CLAUDE.md '콘텐츠 원칙'과 docs/roadmap.md 12절을 먼저 읽고 따른다.

1. `git pull origin main` 으로 최신 main 을 받는다.
2. 풀 위치 확인: data/faq_pool.json 과 scripts/faq_pool.py 가 있으면 그것을 쓴다. 없으면 scripts/variants.py 의 CALL_FAQ 목록이 풀이다(이 경우 CALL_FAQ 에 직접 추가한다. 그 밖의 스크립트·템플릿은 고치지 않는다).
3. 새 자료 읽기(읽기만 하고 원본은 고치지 않는다):
   - C:\Users\AOMG\Documents\통화녹음백업\_분석\FAQ_30.md, 손님심리지도.md — 파일 날짜가 지난 갱신(data/faq_pool.json 의 last_refresh, 없으면 git log 에서 "FAQ pool refresh" 커밋 날짜, 그것도 없으면 2026-10-03)보다 새것일 때만.
   - 같은 폴더의 폼문자질문_YYYY-MM.md(지난달) — 있으면.
   - transcripts/, 통화별표시.csv, 원본목록.csv 같은 통화 원문·고객 목록은 열지 않는다.
   - 새 자료가 하나도 없으면 "새 자료 없음"이라고 보고하고 끝낸다.
4. 후보 고르기: 자료의 질문마다 지금 풀(그리고 scripts/variants.py 의 COMMON_FAQ_QUESTIONS)과 뜻이 같은지 본다.
   - 뜻이 같으면 넣지 않는다. 다만 손님 실제 표현이 더 자주 나오고 더 생생하면 기존 질문 문구만 바꾼다(답은 그대로 두거나 규칙에 맞게 다듬는다).
   - 새 질문만 추가한다. 질문은 손님 실제 표현(짧게 다듬기), 답은 상담 말투("~요")로 2~3문장.
   - 답에는 사실 문구만: 견인비는 대부분 별도 청구 없이·특수한 경우 상담 때 미리 안내 / 차량 확인하면 먼저 입금 / 압류·저당·상속·대리인 서류 상담 가능 / 말소증 문자 / 폐차 전에 수출 시세와 비교. 금액·시세 숫자, 경쟁사·플랫폼 이름, "최고가·보장·무조건·100%·1위·1등·최대·실시간 접수·당일 지급", "견인비 없음" 같은 단정, 수출이 된다/안 된다 단정은 쓰지 않는다. 금액은 "상담 후 확인".
   - 금액 숫자로만 답할 수 있는 질문(예: "고철값 얼마예요?"), 고객 한 사람 사정에만 맞는 질문, 이름·전화번호·차량번호·상세주소가 들어간 문장은 넣지 않고 보고에 이유를 적는다.
   - 질문 지역 이름(시·군·구·동)은 빼고 일반 질문으로 쓴다(풀은 전국 페이지에 나간다).
5. 새 걱정 종류: 손님심리지도.md 에 지금 안내 페이지(scripts/build_guide.py 의 WORRIES)에 없는 걱정이 생겼으면, 맞는 안내 페이지 한 장에 (걱정, 답) 한 줄을 넣는다. 통계 숫자(언급 통화 수·비율)는 넣지 않는다.
6. 추가: data/faq_pool.json 이 있으면 `python3 scripts/faq_pool.py add` 로 넣고(겹침·금지 표현·개인정보 검사를 통과해야 함) `python3 scripts/faq_pool.py assign` 으로 페이지 배정을 다시 한다. 없으면 CALL_FAQ 끝에 붙인다(첫 질문 "몇 년 된 차인데 얼마 정도 나와요?"는 맨 앞에 그대로 둔다).
7. `python3 scripts/build_site.py` → `python3 scripts/build_index.py` → `python3 scripts/check_pages.py` 를 실행한다. 오류가 0건이 될 때까지 문구를 고친다. 세 번 고쳐도 안 되는 질문은 빼고 보고에 적는다.
8. 개인정보 마지막 확인: 바뀐 파일 전체(git diff)에서 사람 이름, 010·지역번호 전화번호(1600-6011·010-9926-7779 제외), 차량번호(예: 12가3456), 번지·동호수 주소가 없는지 본다. 있으면 그 문장을 빼고 다시 7번.
9. 커밋: 메시지 첫 줄 "FAQ pool refresh (YYYY-MM): N added, M reworded". `git pull --rebase origin main` 후 main 에 push 한다(PR 없음). 실패하면 push 하지 않고 브랜치 auto/faq-failed-YYYYMMDD 에 남긴다.
10. 보고(짧게): 새로 넣은 질문 수와 목록, 문구만 바꾼 기존 질문, 넣지 않은 질문과 이유, 안내 페이지에 넣은 새 걱정, 바뀐 페이지 수(동/구/시/안내), check_pages.py 결과, 커밋 번호.
```
