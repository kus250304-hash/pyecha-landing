# 매일 자동생성 루틴 지시문 (폐차 랜딩 자동생성)

루틴 "폐차 랜딩 자동생성 v3" 의 설정에는 한 줄만 들어 있습니다:
"저장소의 docs/daily-routine-prompt.md 파일을 열어서, 그 안의 코드 상자에 있는 지시문을 처음부터 끝까지 그대로 따라 실행해."

그래서 루틴이 실제로 따르는 지시문은 **아래 코드 상자 하나**뿐입니다. 코드 상자 밖의 글(이 설명)은 지시문이 아닙니다.
지시문을 바꾸려면 이 코드 상자 안만 고쳐서 main 에 올리면 되고(2026-09-29부터 PR 없이 바로 반영), 루틴 설정은 다시 건드리지 않아도 됩니다.
앞으로 할 확장(구 페이지·시도 페이지 등)과 그 조건은 docs/roadmap.md 에 있습니다.
코드 상자는 이 파일에 하나만 둡니다.

```text
pyecha-landing 저장소(kus250304-hash/pyecha-landing)의 지역 폐차 랜딩페이지를 오늘 분량만큼 만들고, 사실 확인과 검사를 모두 통과한 것만 main 에 바로 반영하는 작업이다. PR은 만들지 않는다. 아래 순서와 규칙을 그대로 따른다.

[준비]
0. 현재 작업 디렉터리에 저장소가 없으면(`git rev-parse --show-toplevel` 실패) `git clone https://github.com/kus250304-hash/pyecha-landing` 후 그 디렉터리로 이동한다.
1. `git fetch origin main` 후 `git checkout -B auto/pages-$(TZ=Asia/Seoul date +%Y%m%d) origin/main` 으로 작업 브랜치를 만든다(로컬 작업용).
2. `scripts/publish_gate.py` 와 `scripts/fact_check.py` 가 없으면 아무것도 만들지 말고 "새 반영 파이프라인이 main에 없음"이라고만 보고하고 종료한다.
3. 저장소의 CLAUDE.md를 읽고 '콘텐츠 원칙', '지역 콘텐츠 작성 규칙', '반영 방법', '사실 확인'을 따른다.
3-1. `python3 scripts/build_cases.py` 를 실행한다(cases/input 에 새 사례가 있으면 처리, 없으면 넘어감).

[우선순위 통계]
3-2. `python3 scripts/vehicle_stats.py show` 로 지금 쓰는 등록대수 통계를 본다. "통계 없음"이거나 기준 연월이 2개월보다 오래됐으면 `python3 scripts/vehicle_stats.py molit` 을 실행한다(국토교통부 통계누리에서 최신 월 엑셀을 받아 시군구 자가용 × 시도 노후차 비율로 data/vehicle_stats_old10_est.json 저장. openpyxl 이 없으면 `pip install openpyxl` 후 다시 실행). 접속이 끊기면 몇 분 뒤 한 번 더 해 보고, 그래도 안 되면 넘어가고 보고에 적는다. 숫자를 지어내지 않는다.

[생성]
4. `python3 scripts/pick_next_regions.py` 를 실행한다. 첫 줄의 "우선순위 기준"을 보고에 그대로 옮긴다. 개수는 data/generation_config.json 의 daily_count 를 따르며 여기서 바꾸지 않는다. "선택 가능한 동이 없습니다"가 나오면 "전체 완료됨"이라고 보고하고 종료한다.
5. 만들어진 data/batches/YYYY-MM-DD.json 의 각 항목에서 landmark_name, landmark_desc, service_intro, faqs(질문·답 4~5쌍), meta 를 채운다. 규칙:
   - 지역마다 내용이 달라야 한다. 문장을 복사해 동 이름만 바꾸지 않는다.
   - 랜드마크는 그 동에 실제로 있는 장소만 쓴다. 도로명(○○로·○○길·○○대로)은 랜드마크로 쓰지 않는다. 그 동 안에 있다고 확인되는 장소가 없으면 지어내지 말고 그 동을 held(이유: "동 안에서 확인되는 장소 없음")로 두고 넘어간다. 주민센터는 그 이름의 주민센터가 실제로 있을 때만 쓴다.
   - 뼈대에 dong_parts(예: 종로1가~6가)가 있는 항목은 "○가" 여러 개를 한 페이지로 묶은 것이다. dong 은 묶은 이름(예: 종로)이며, 글에서 "종로1가~6가"처럼 묶인 범위를 한 번 적는다. 랜드마크는 묶인 ○가 중 어느 한 곳 안에 있으면 된다.
   - 사람이 거의 살지 않는 법정동(산업단지·산지·농경지만 있거나 인구가 극히 적은 곳)은 글을 쓰지 않고 held 로 둔다. reason 에 판단 근거를 쉬운 말로 적는다(예: "국가산업단지 부지로 주거지가 없음, 검색 결과 ○○").
   - FAQ 4~5개 중 3개 이상은 질문이나 답에 그 동 이름 또는 랜드마크 이름이 들어가야 한다.
   - 다른 시도의 지역 이름, 시세·금액·경쟁사, 결과를 약속하는 표현("보장", "무조건", "100%", "1위", "최저가")은 쓰지 않는다.

[사실 확인 — 반영 전 필수]
6. `python3 scripts/fact_check.py data/batches/YYYY-MM-DD.json` 을 실행해 지역마다 "확인할 이름"을 본다. 그 이름들과 글에 쓴 모든 장소 이름(랜드마크·역·도로명·시장·학교·공원·관공서·하천·산 등)을 WebSearch 로 하나씩 검색한다(검색어 예: "<시군구> <동> <이름>").
   - 그 장소가 실제로 있고, 그 동 안(또는 글에 쓴 대로 바로 옆)에 있다는 근거가 검색 결과에 있을 때만 확인됨으로 본다. fact_check.items 에 name, evidence(근거 한 줄), url(실제 검색 결과의 주소)을 적는다. 주소나 근거를 지어내지 않는다.
   - 확인되지 않는 이름은 확인되는 다른 장소나 큰 도로로 바꾸고 다시 확인한다. 그래도 확인이 안 되면 그 지역의 fact_check.status 를 "held", reason 에 쉬운 말 이유(예: "랜드마크 위치를 검색으로 확인하지 못함")를 적는다. 애매하면 confirmed 가 아니라 held 로 둔다.
   - 모든 이름이 확인된 지역만 fact_check.status 를 "confirmed" 로 둔다.
   - WebSearch 를 쓸 수 없으면 모든 지역을 held(이유: "웹 검색을 쓸 수 없어 확인 못 함")로 둔다.
   - fact_check.py 를 다시 돌려 "확인 기록 문제 있는 항목: 0개"가 될 때까지 고친다.
7. `python3 scripts/import_batch.py data/batches/YYYY-MM-DD.json` 을 실행한다. 보류 항목은 data/batches/held/ 로, 확인된 항목만 반영·렌더링·검사된다. 오류가 나오면 변경이 자동으로 되돌려지므로 배치 파일을 고치고 다시 실행한다(세 번 고쳐도 안 되는 항목은 held 로 바꾼다). 통과 전에는 커밋하지 않는다.
8. scripts/, templates/, CLAUDE.md, data/generation_config.json, .github/, docs/ 는 수정하지 않는다. 그쪽에 문제가 있으면 보고만 한다.

[반영]
9. 변경된 파일(data/regions.json, data/batches/held/, data/fact_checks/, data/vehicle_stats.json, data/vehicle_stats_old10_est.json, data/vehicle_stats_total.json, pages/, gu/, cases/, index.html, sitemap.xml)만 커밋한다. 메시지: "Add N region pages (YYYY-MM-DD), held M". 반영할 지역이 0개이고 보류만 있으면 보류 파일만 커밋한다(다음 날 다시 뽑히지 않게).
10. `python3 scripts/publish_gate.py` 를 실행한다.
   - "통과"가 나오면 `git push origin HEAD:main` 으로 main 에 반영한다.
   - "통과 못 함"이 나오거나 push 가 거절되면 main 에는 push 하지 않는다. 대신 `git push -u origin HEAD:auto/failed-$(TZ=Asia/Seoul date +%Y%m%d)` 로 작업을 남기고 실패 이유를 보고한다. 강제 push, 게이트 건너뛰기, 스크립트를 고쳐 통과시키는 것은 금지한다.
11. 보고를 쓰기 전에 docs/roadmap.md 를 읽는다. 7절 "조건이 되면 먼저 알릴 것"의 조건에 해당하는 항목이 있으면 보고 맨 위에 먼저 알린다(무엇을 제안하는지 한두 줄).
12. 마지막으로 짧게 보고한다(3시 보고):
   - 반영 N개, 보류 M개(보류된 동 이름과 이유, 사람이 거의 살지 않아 건너뛴 동은 판단 근거 포함)
   - 동 페이지 총 개수(data/regions.json 항목 수)
   - 우선순위 기준(pick_next_regions.py 첫 줄). 추정 노후 자가용 통계를 못 구해 전체 등록대수 순으로 했거나, 통계가 아예 없어 임시 순서로 했으면 그 사실과 이유를 적는다
   - 오늘 만든 구 페이지 목록, 공공 정보 중 확인 못 해서 뺀 항목, 보류한 구와 이유(구 페이지 단계가 루틴에 들어간 뒤부터. 아직이면 "구 페이지: 견본 승인 대기"라고만 적는다)
   - 실패가 있었으면 그 이유
```
