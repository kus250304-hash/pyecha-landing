# PC 복구 안내 (2026-11-01)

PC가 고장 나거나 새 PC로 바꿀 때 이 순서대로 되살립니다. 열쇠 값은 이 문서에 쓰지 않습니다.
매일 밤 백업(`scripts/pc_backup.ps1`)이 이 문서 사본도 백업 폴더에 같이 넣으므로, 저장소를 못 열어도 구글 드라이브에서 읽을 수 있습니다.

## 1. 어디에 뭐가 있나

| 무엇 | 어디 | PC가 죽으면 |
|---|---|---|
| 사이트·스크립트·데이터 | GitHub `kus250304-hash/pyecha-landing` (main) | 안 잃음 |
| 매일 자동생성 루틴(오전 6시 2분, 보고 6시 55분) | 클라우드(claude.ai 루틴), 지시문 `docs/daily-routine-prompt.md` | 안 잃음, PC와 상관없이 돎 |
| 병한-업무위키 | `C:\Users\AOMG\Documents\병한-업무위키` | 매일 백업 `업무위키.zip`(영상·녹음 파일 뺌) |
| 통화 분석(FAQ·글자본·로그) | `C:\Users\AOMG\Documents\통화녹음백업\_분석` | 매일 백업 `분석.zip`(녹음 파일 뺌) |
| Windows 예약 작업 3개 | 작업 스케줄러 `폐차_통화인박스`·`폐차_FAQ_월간갱신`·`폐차_백업` | 매일 백업 `예약작업\windows\*.xml` |
| Claude 앱 예약 작업 | `C:\Users\AOMG\.claude\scheduled-tasks\*\SKILL.md` + 앱 안 시간표(아래 4절 표) | 지시문은 매일 백업 `예약작업\claude\`, 시간은 아래 표 보고 다시 만듦 |
| 열쇠·env 4개 | `C:\Users\AOMG\` 의 `gsc-key.json`·`naver_search.env`·`naver_searchad.env`·`daglo.env` | 백업 안 함(이름·수정일만 `열쇠_목록.txt`), 새로 받음 |
| 파이썬 패키지 목록 | — | 매일 백업 `파이썬_패키지.txt` |
| 휴대폰 인박스 | `G:\내 드라이브\폐차_인박스` (구글 드라이브) | 안 잃음 |
| 사례 원본 사진·영상 | `C:\Users\AOMG\Documents\카카오톡 받은 파일\폐차사진원본` | **백업 안 함**(용량·개인정보) — 아직 안 올린 사례는 잃음 |
| 통화 녹음 원본 | `C:\Users\AOMG\Documents\통화녹음백업` (`_분석` 밖) | **백업 안 함** — PC에만 있으면 잃음 |

백업 위치: `G:\내 드라이브\폐차_백업\YYYY-MM-DD\` (14일치만 남김, 지운 것은 드라이브 휴지통에 30일).
백업 로그: `통화녹음백업\_분석\폐차_백업_log.txt` (한 줄: 날짜·크기·성공/실패).

## 2. 멈추지 않게 해 둔 것

| 항목 | 상태 |
|---|---|
| 매일 백업 `폐차_백업` | 매일 밤 11시 40분, 놓치면 켜질 때 바로, 절전이면 깨워서 실행, 2시간 제한 |
| `폐차_통화인박스`(15분마다) | 놓친 작업 바로 실행, 배터리 조건 끔, 2시간 제한, 실행 중이면 새로 안 띄움 |
| `폐차_FAQ_월간갱신` | 놓친 작업 바로 실행, 배터리 조건 끔, 실행 중이면 새로 안 띄움. 제한은 **3시간 그대로**(스크립트가 다른 작업을 90분까지 기다린 뒤 claude 를 90분까지 돌려서, 2시간이면 중간에 끊김) |
| Claude 앱 | 로그인하면 저절로 켜짐(시작프로그램 폴더 `Claude.lnk`). Claude 앱 예약 작업은 앱이 켜져 있어야 돌고, 놓친 것은 앱을 켜면 한 번 돎 |
| 절전 해제 타이머 | 이미 "사용"(전원 연결 시) |
| 아침 보고 경고 | PC 작업 커밋이 36시간 없으면 아침 보고 맨 위에 "⚠ PC 작업이 어제 안 돌았음"(`docs/roadmap.md` 7절) |

병한님이 직접 할 것(관리자 권한·보안 설정이라 자동으로 바꾸지 않음):

1. **절전 끄기(가장 중요, 지금 전원 연결 시 15분 뒤 절전)** — Windows 설정(Win+I) → 왼쪽 "시스템" → "전원" → "화면, 절전 및 최대 절전 시간 제한" 펼치기 → "전원 연결 시 … 장치를 절전 모드로 전환"을 **안 함**, "화면 끄기"는 10분.
2. **업데이트 사용 시간** — Windows 설정 → 왼쪽 "Windows 업데이트" → "고급 옵션" → "사용 시간"을 **수동** → 오전 6시 ~ 오전 12시(자정). (지금은 오전 8시 ~ 새벽 2시)
3. **자동 로그인(선택)** — 정전·업데이트 재시작 뒤에도 작업이 돌게 합니다. 대신 PC를 켜면 누구나 바로 들어올 수 있습니다. Windows 설정 → "계정" → "로그인 옵션" → "보안 향상을 위해 이 디바이스에서 Microsoft 계정에 Windows Hello 로그인만 허용" 끔 → Win+R 에 `netplwiz` → "사용자 이름과 암호를 입력해야 이 컴퓨터를 사용할 수 있음" 체크 해제 → 확인 → 암호 두 번 입력.
4. **정전 뒤 자동 켜짐(선택)** — 메인보드 BIOS 의 "AC Power Recovery / Restore on AC Power Loss"를 Power On. PC마다 화면이 달라 필요하면 따로 안내.

## 3. 새 PC 복구 순서

새 PC의 Windows 사용자 이름을 **AOMG** 로 만들면 경로를 고칠 필요가 없습니다(스크립트·작업이 `C:\Users\AOMG\…` 를 씀).

1. **설치**
   - 구글 드라이브(데스크톱용) → kus250304@gmail.com 로그인 → `G:\내 드라이브` 가 보이는지 확인
   - Git for Windows, Python 3.14(`C:\Users\AOMG\AppData\Local\Programs\Python\Python314`, "Add to PATH" 체크), 크롬, Claude 앱(Microsoft Store)
   - 저장소: `git clone https://github.com/kus250304-hash/pyecha-landing.git C:\Users\AOMG\Documents\pyecha-landing` (GitHub 로그인은 처음 push 때 창이 뜸)
2. **열쇠 4개 다시 받기** — 모두 `C:\Users\AOMG\` 바로 아래에 둡니다(저장소 안에 넣지 않음). 예전 열쇠는 받은 뒤 지웁니다.

   | 파일 | 다시 받는 곳 | 안에 들어갈 이름 |
   |---|---|---|
   | `gsc-key.json` | [구글 클라우드 서비스 계정](https://console.cloud.google.com/iam-admin/serviceaccounts) → `gsc-index-check@…` → 키 → 새 키(JSON). 순서는 `docs/gsc-setup.md` 4·7단계 | (JSON 파일 그대로) |
   | `naver_search.env` | [네이버 개발자센터 내 애플리케이션](https://developers.naver.com/apps/#/list) → 검색 API 앱 → Client ID·Secret | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` |
   | `naver_searchad.env` | [네이버 검색광고](https://manage.searchad.naver.com/) → 도구 → API 사용 관리 | `NAVER_SEARCHAD_CUSTOMER_ID`, `NAVER_SEARCHAD_ACCESS_LICENSE`, `NAVER_SEARCHAD_SECRET_KEY` |
   | `daglo.env` | [다글로 개발자 콘솔](https://developers.daglo.ai/console) → API 토큰 | `DAGLO_TOKEN` |

3. **백업 되살리기** — 파일 탐색기 → `G:\내 드라이브\폐차_백업` → 가장 최근 날짜 폴더
   - `업무위키.zip` → 오른쪽 클릭 "모두 압축 풀기" → `C:\Users\AOMG\Documents\병한-업무위키`
   - `분석.zip` → `C:\Users\AOMG\Documents\통화녹음백업\_분석`
   - `예약작업\claude\scheduled-tasks` 폴더 → `C:\Users\AOMG\.claude\scheduled-tasks` 로 복사
   - 파이썬 패키지: `python -m pip install -r "G:\내 드라이브\폐차_백업\<날짜>\파이썬_패키지.txt"` (안 되면 `pip install pillow opencv-python faster-whisper numpy openpyxl`)
4. **Windows 예약 작업 가져오기** — XML 안의 사용자 번호(SID)가 옛 PC 것이라 새 PC 사용자로 바꿔서 넣습니다. PowerShell 에서:

   ```powershell
   $dir = "G:\내 드라이브\폐차_백업\<날짜>\예약작업\windows"
   Get-ChildItem $dir -Filter *.xml | ForEach-Object {
     $xml = (Get-Content $_.FullName -Raw) -replace '<UserId>.*?</UserId>', "<UserId>$env:USERNAME</UserId>"
     Register-ScheduledTask -TaskName $_.BaseName -Xml $xml -Force
   }
   ```

   (사용자 이름이 같고 XML 을 고칠 필요가 없으면 `schtasks /create /tn "폐차_백업" /xml "<파일>"` 도 됩니다.)
5. **Claude 앱 예약 작업 다시 만들기** — Claude 앱 → 예약 작업 → 새로 만들기. 지시문은 3단계에서 복사한 `SKILL.md` 본문(맨 위 `---` 사이 빼고)을 그대로 붙여 넣습니다.

   | 이름 | 시간 | 지시문 폴더 | 비고 |
   |---|---|---|---|
   | 구글 색인 확인 (매일 낮) | 매일 낮 12시 10분 | `pyecha-gsc-index-check` | `gsc-key.json` 필요, 이어서 GA4 유입(`ga4_daily.py --push`, `site_config.ga4_property_id`·`docs/ga4-setup.md`) |
   | 폐차_검색어_주간 | 매주 일요일 밤 8시 | `pyecha-gsc-queries-weekly` | `gsc-key.json` 필요 |
   | 캘린더→기록부 (매일) | 매일 오후 1시 20분 | `scheduled-task` | 업무위키 `폐차\거래기록부\_캘린더\루틴지시문.md` |
   | 폐차 사례 가져오기 (매일 3건) | 매일 오후 1시 40분·1시 55분 | `3` | `docs/pc-case-import-prompt.md`, 네이버 순위 15단계에 `naver_search.env` 필요 |
   | 폐차장 명단 채우기 | (꺼져 있음) | `pyecha-junkyard-list-fill` | 필요할 때만 |

   이름에 날짜가 붙은 한 번짜리 확인 작업(`…-2026-10-15`, `…-2026-10-16`)은 다시 만들지 않습니다.
6. **멈춤 방지** — 2절의 "병한님이 직접 할 것" 1~3번, 그리고 Claude 앱 자동 실행: Windows 설정 → "앱" → "시작 프로그램" → Claude 켬.
7. **시험**
   - `python scripts/check_pages.py` → 오류 0건
   - `python scripts/gsc_index_check.py --test 5` → 주소 5개 결과가 나옴
   - 작업 스케줄러에서 `폐차_백업` 오른쪽 클릭 → 실행 → `_분석\폐차_백업_log.txt` 마지막 줄 "성공"
   - 다음 날 아침 보고에 "⚠ PC 작업이 어제 안 돌았음"이 없으면 끝

## 4. 잃는 것·안 잃는 것

- **안 잃는 것**: 사이트와 모든 스크립트·데이터(GitHub), 매일 자동생성 루틴(클라우드), 구글 드라이브의 인박스·백업, 유튜브·블로그, 견적 폼 메일(Web3Forms·네이버 메일), 캘린더 알림(Apps Script, 구글 계정), 폼 문의 기록 시트(구글 시트 "폐차119 폼 문의", 코드는 `docs/form-log-setup.md`)
- **하루치까지 잃을 수 있는 것**: 업무위키·통화 분석의 마지막 백업 뒤 바뀐 것(최대 하루)
- **잃는 것**: 사례 원본 사진·영상 중 아직 사례로 안 올린 것, 통화 녹음 원본(PC에만 있으면), 업무위키 안 쇼츠 원본·완성 영상과 녹음 파일(완성본은 유튜브에 있음), 열쇠 4개(새로 받으면 됨), 저장소에서 push 안 한 고친 것
