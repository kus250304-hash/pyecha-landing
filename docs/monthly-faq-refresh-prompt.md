# 월 1회 FAQ 풀 갱신 지시문 (매달 첫째 월요일 오후 2시 30분, 운영자 PC)

통화 분석 자료(`C:\Users\AOMG\Documents\통화녹음백업\_분석\`)와 폼·문자 질문 모음은 운영자 PC 에만 있으므로
**PC 의 Windows 작업 스케줄러**로 돌립니다(2026-10-31부터, 병한님 손 없이). 배경과 규칙은 `docs/roadmap.md` 12절.

- 예약 작업: 작업 스케줄러 **"폐차_FAQ_월간갱신"** — 매달 첫째 월요일 오후 2시 30분(12시 10분·오후 1시 40분 예약 작업과 안 겹침), PC 가 꺼져 있던 달은 다음에 켜질 때 바로 실행("놓친 작업은 가능한 한 빨리 실행").
- 실행: `pythonw.exe scripts\pc_faq_refresh.py` (통화 인박스 `병한-업무위키\_도구\통화인박스.py` 와 같은 방식: 창 없이, `claude -p` 를 `--permission-prompts none` + 허용 목록(Read·Write·Edit·Glob·Grep·git·python)으로 부름, 통화 원문·고객 목록 읽기는 막음). 지시는 "docs/monthly-faq-refresh-prompt.md 의 코드 상자 지시문을 처음부터 끝까지 그대로 실행해" 한 줄입니다.
- 로그: `C:\Users\AOMG\Documents\통화녹음백업\_분석\폐차_FAQ_log.txt`(통화인박스_log.txt 옆), claude 마지막 출력 전체는 같은 폴더 `폐차_FAQ_마지막출력.txt`.
- 실행 결과 기록: `docs/faq-refresh-log.md` 맨 위(아침 보고가 이 파일을 읽음).
- 실제 지시문은 **아래 코드 상자 하나**뿐입니다. 바꿀 때는 이 코드 상자 안만 고쳐 main 에 올립니다.
- 준비 완료(2026-10-21): `data/faq_pool.json` 과 `scripts/faq_pool.py` 가 있습니다(roadmap 12절). 문구만 바꿀 때는 `data/faq_pool.json` 의 그 항목 q·a 를 고치고 `faq_pool.py assign` 으로 검사합니다.

```text
너는 pyecha-landing 저장소의 월 1회 FAQ 풀 갱신 담당이다. 저장소의 CLAUDE.md '콘텐츠 원칙'과 docs/roadmap.md 12절을 먼저 읽고 따른다.
PC(Windows)에서는 python3 가 마이크로소프트 스토어 바로가기라 돌지 않으므로, 아래의 python3 는 모두 python 으로 바꿔 실행한다(python 이 안 되면 py). 한글이 깨지면 PYTHONIOENCODING=utf-8 을 붙인다.
저장소 밖 임시 파일은 C:\Users\AOMG\AppData\Local\Temp\pyecha_faq\ 에 쓴다(PC 예약 작업이 이 폴더를 허용해 둠).

1. `git pull origin main` 으로 최신 main 을 받는다.
2. 풀 위치 확인: data/faq_pool.json 과 scripts/faq_pool.py 가 있으면 그것을 쓴다. 없으면 scripts/variants.py 의 CALL_FAQ 목록이 풀이다(이 경우 CALL_FAQ 에 직접 추가한다. 그 밖의 스크립트·템플릿은 고치지 않는다).
3. 새 자료 읽기(읽기만 하고 원본은 고치지 않는다). "지난 갱신 날짜" = docs/faq-refresh-log.md 맨 위 기록의 날짜, 그 파일이 없으면 data/faq_pool.json 의 last_refresh, 그것도 없으면 git log 의 "FAQ pool refresh" 커밋 날짜, 그것도 없으면 2026-10-03.
   - C:\Users\AOMG\Documents\통화녹음백업\_분석\FAQ_30.md, 손님심리지도.md — 파일 날짜가 지난 갱신 날짜보다 새것일 때만.
   - 같은 폴더의 폼문자질문_YYYY-MM.md(지난달) — 있으면.
   - 같은 폴더의 통화질문_YYYY-MM.md — 통화 인박스(병한-업무위키\_도구\통화인박스.py 의 result)가 공개 검사(금액·전화번호·차번호·주소·이름·지역 이름)를 통과한 손님 질문만 한 줄씩 붙이는 파일이다. 지난달 것을 읽고, 이번 달 것도 파일 날짜가 지난 갱신 날짜보다 새것이면 함께 읽는다. 지난 기록(docs/faq-refresh-log.md)에 이미 적힌 질문은 다시 고르거나 다시 보고하지 않는다(아래 "병한님 답" 줄은 예외).
   - docs/faq-refresh-log.md 의 '병한님 답' 줄은 확인된 답으로 보고 그 질문을 넣는다(아직 풀에 없을 때만, 답은 그 줄의 내용대로 4번 규칙에 맞춰 쓴다).
   - transcripts/, 문자/, 통화표.csv, 통화별표시.csv, 원본목록.csv 같은 통화 원문·고객 목록은 열지 않는다.
   - 새 자료가 하나도 없으면 10번 기록만 "새 자료 없음"으로 적고 11번(기록 파일 하나만 커밋·push)·12번 보고로 가서 끝낸다.
4. 후보 고르기: 자료의 질문마다 지금 풀(그리고 scripts/variants.py 의 COMMON_FAQ_QUESTIONS 와 FAR_FAQ_Q)과 뜻이 같은지 본다.
   - 뜻이 같으면 넣지 않는다. 다만 손님 실제 표현이 더 자주 나오고 더 생생하면 기존 질문 문구만 바꾼다(답은 그대로 두거나 규칙에 맞게 다듬는다).
   - 새 질문만 추가한다. 질문은 손님 실제 표현(짧게 다듬기), 답은 상담 말투("~요")로 2~3문장.
   - 답에는 사실 문구만: 견인비는 "견인비는 따로 없어요"(이 꼴만, CLAUDE.md 견인비 줄) / 차량 확인하면 먼저 입금 / 압류·저당·상속·대리인 서류 상담 가능 / 말소증 문자 / 폐차 전에 수출 시세와 비교. 금액·시세 숫자, 경쟁사·플랫폼 이름, "최고가·보장·무조건·100%·1위·1등·최대·실시간 접수·당일 지급", "무료 견인·견인비 없음" 같은 다른 꼴, 수출이 된다/안 된다 단정은 쓰지 않는다. 금액은 "상담 후 확인"이 아니라 "통화 때 바로 말씀드려요"처럼 쓴다(본문 "상담 후 확인"은 2번까지라 늘리지 않는다).
   - 금액 숫자로만 답할 수 있는 질문(예: "고철값 얼마예요?"), 고객 한 사람 사정에만 맞는 질문, 폐차 상담과 상관없는 질문(부품·타이어 구매 등), 이름·전화번호·차량번호·상세주소가 들어간 문장은 넣지 않고 보고에 이유를 적는다.
   - 보통 질문은 지역 이름(시·군·구·동)을 빼고 일반 질문으로 쓴다(풀은 전국 페이지에 나간다).
   - 지역 질문: 그 지역에서만 나오는 질문(배편·섬 견인·눈길·고지대처럼 지역 사정이 질문 자체인 것)은 지역 이름을 빼지 말고, 그 시·군의 구 페이지 지역 FAQ(data/gu.json 의 그 항목 faqs, [질문, 답] 쌍 목록 끝)에만 넣는다. 지역당 한 달 1개까지, 그 시·군 구 페이지가 data/gu.json 에 있을 때만(없으면 넣지 않고 보고에 "구 페이지 없음"), 일반 풀에는 넣지 않는다. 그 구 페이지의 기존 faqs 와 뜻이 같으면 넣지 않는다. 답은 그 페이지 FAQ 말투에 맞추고 위 사실 문구·금지 표현·답 첫 문장 규칙(variants.FAQ_ANSWER_RULE)을 똑같이 지키며, 확인 안 된 장소 이름·배편 시간·요금은 쓰지 않는다.
5. 새 걱정 종류: 손님심리지도.md 에 지금 안내 페이지(scripts/build_guide.py 의 WORRIES)에 없는 걱정이 생겼으면, 맞는 안내 페이지 한 장에 (걱정, 답) 한 줄을 넣는다. 통계 숫자(언급 통화 수·비율)는 넣지 않는다.
6. 추가: data/faq_pool.json 이 있으면 새 질문을 [{"q": …, "a": …, "source_month": "YYYY-MM"}] 꼴 JSON 파일(저장소 밖 임시 폴더)로 써서 `python3 scripts/faq_pool.py add <파일>` 로 넣고(겹침·금지 표현·개인정보 검사를 통과해야 함) `python3 scripts/faq_pool.py assign` 으로 페이지 배정을 다시 한다. 없으면 CALL_FAQ 끝에 붙인다(첫 질문 "몇 년 된 차인데 얼마 정도 나와요?"는 맨 앞에 그대로 둔다).
7. `python3 scripts/build_site.py` → `python3 scripts/build_index.py` → `python3 scripts/check_pages.py` 를 실행한다. 오류가 0건이 될 때까지 문구를 고친다. 세 번 고쳐도 안 되는 질문은 빼고 보고에 적는다.
8. 개인정보 마지막 확인: 바뀐 파일 전체(git diff)에서 사람 이름, 010·지역번호 전화번호(1600-6011·010-9926-7779 제외), 차량번호(예: 12가3456), 번지·동호수 주소가 없는지 본다. 있으면 그 문장을 빼고 다시 7번.
9. 바뀐 페이지 수: `git status --porcelain` 으로 바뀐 pages/(동)·gu/(구)·si/(시)·guide/(안내) .html 개수를 센다.
10. 실행 기록: docs/faq-refresh-log.md 맨 위(제목 줄과 설명 바로 아래, 지난 기록보다 위)에 아래 꼴로 한 칸을 적는다. 사람 이름·전화번호·차번호·주소·금액은 적지 않는다.
    ## YYYY-MM-DD (자료: 읽은 파일 이름들, 없으면 "새 자료 없음")
    요약: 새 질문 N개 · 문구 바꿈 M개 · 지역 질문 K개 · 바뀐 페이지 동 a · 구 b · 시 c · 안내 d · check_pages 오류 E건
    요약2: 새 질문 — "질문1" / "질문2" … (없으면 "새 질문 없음")
    - 새 질문: 질문마다 한 줄
    - 문구 바꾼 질문: 옛 문구 → 새 문구
    - 넣지 않은 질문: 질문 — 이유(겹침: 어느 질문과 / 금액만으로 답 / 상담과 무관 / 한 사람 사정 / 개인정보 / 검사 실패)
    - 지역 질문: 시·군 — 질문 (없으면 "없음")
    - 새 걱정(안내 페이지): (없으면 "없음")
    - check_pages: 결과 줄 그대로
    - 커밋: 커밋 메시지 첫 줄(번호는 `git log -1 -- docs/faq-refresh-log.md` 로 찾음)
11. 커밋: 바뀐 파일 전부와 docs/faq-refresh-log.md 를 같은 커밋에 넣는다. 메시지 첫 줄 "FAQ pool refresh (YYYY-MM): N added, M reworded, K regional"(새 자료가 없으면 "FAQ pool refresh (YYYY-MM): no new material"). `git pull --rebase origin main` 후 `git push origin HEAD:main`(PR 없음). 실패하면 main 에 push 하지 않고 `git push -u origin HEAD:auto/faq-failed-YYYYMMDD` 로 남기고 이유를 보고한다. 강제 push 는 하지 않는다.
12. 보고(짧게, 한국어): 새로 넣은 질문 수와 목록, 문구만 바꾼 기존 질문, 넣지 않은 질문과 이유, 지역 질문, 안내 페이지에 넣은 새 걱정, 바뀐 페이지 수(동/구/시/안내), check_pages.py 결과, 커밋 번호. 마지막 줄은 "FAQ 갱신 끝:"으로 시작하는 한 줄 요약(예: "FAQ 갱신 끝: 새 질문 2 · 바꿈 0 · 지역 0 · 커밋 abc1234")으로 쓴다(PC 로그에 이 줄이 남음).
```
