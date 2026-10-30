# 구글 색인 확인 설정 (2026-10-30)

구글 색인 요청 목록(`scripts/pick_index_requests.py`)에서 **이미 색인된 주소를 자동으로 빼기** 위한 준비입니다.
PC 예약 작업 "구글 색인 확인 (매일 낮)"이 매일 낮 12시 10분 무렵 `python scripts/gsc_index_check.py --push` 를 돌려
`data/gsc_index_status.json` 만 main 에 올리고, 다음 날 아침 루틴이 그 파일을 읽어 색인된 주소를 뺍니다.
열쇠 파일이 없으면 예약 작업은 "키 없음"만 적고 끝나며, 열쇠를 넣은 다음 날부터 저절로 돕니다.

- 열쇠 파일 자리: `C:\Users\AOMG\gsc-key.json` (저장소 **밖**. 저장소에 넣지 않고, `.gitignore` 가 `*gsc-key*.json` 을 막음)
- 속성: `sc-domain:pyecha119.com`(도메인) 먼저, 안 되면 `https://pyecha119.com/`(URL 접두어)
- 하루 300건 이하, 이미 색인된 주소는 14일에 한 번만 다시 확인
- 결과 파일이 없거나 3일보다 오래되면 구글 목록은 지금처럼 거르지 않고 그대로 나옵니다.

## 병한님이 한 번만 할 일

모두 크롬에서 kus250304@gmail.com(서치 콘솔과 같은 구글 계정)으로 로그인한 채로 합니다.

1. **프로젝트 만들기** — [프로젝트 만들기 화면](https://console.cloud.google.com/projectcreate) 열기 → "프로젝트 이름"에 `pyecha119-gsc` 입력 → "만들기" 누르기 → 오른쪽 위 알림 종에 "만들기 완료"가 뜰 때까지 기다리기.
2. **Search Console API 켜기** — [Search Console API 화면](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com) 열기 → 맨 위 왼쪽 프로젝트 이름이 `pyecha119-gsc` 인지 보기(아니면 눌러서 바꾸기) → 파란 "사용" 버튼 누르기.
3. **서비스 계정 만들기** — [서비스 계정 만들기 화면](https://console.cloud.google.com/iam-admin/serviceaccounts/create) 열기 → "서비스 계정 이름"에 `gsc-index-check` 입력 → "만들고 계속하기" → 다음 두 칸(역할·사용자)은 비워 둔 채 "완료".
4. **열쇠(JSON) 받기** — [서비스 계정 목록](https://console.cloud.google.com/iam-admin/serviceaccounts) 에서 방금 만든 `gsc-index-check@…iam.gserviceaccount.com` 이메일을 누르기 → 위쪽 "키" 탭 → "키 추가" → "새 키 만들기" → "JSON" 고르고 "만들기". 파일이 **다운로드** 폴더에 저절로 받아집니다. ("키 만들기가 사용 중지됨" 같은 글이 뜨면 거기서 멈추고 알려 주세요.)
5. **서비스 계정 이메일 복사** — 같은 목록 화면에서 `gsc-index-check@…iam.gserviceaccount.com` 이메일 옆 복사 아이콘을 누르거나 드래그해서 복사.
6. **서치 콘솔에 사용자 추가** — [서치 콘솔 사용자 및 권한(도메인 속성)](https://search.google.com/search-console/users?resource_id=sc-domain%3Apyecha119.com) 열기 → 오른쪽 위 "사용자 추가" → 복사한 이메일 붙여 넣기 → 권한 "제한됨" 고르고 "추가". (도메인 속성 화면이 안 열리면 [URL 접두어 속성](https://search.google.com/search-console/users?resource_id=https%3A%2F%2Fpyecha119.com%2F) 에 같은 방법으로 추가해도 됩니다.)
7. **열쇠 파일 옮기기** — 파일 탐색기 → 왼쪽 "다운로드" → 방금 받은 `pyecha119-gsc-…json` 파일을 누르고 F2 → 이름을 `gsc-key.json` 으로 바꾸기 → 그 파일을 잘라내기(Ctrl+X) → 탐색기 주소창에 `C:\Users\AOMG` 입력하고 Enter → 붙여 넣기(Ctrl+V). pyecha-landing 폴더 안에는 넣지 않습니다. 다운로드 폴더에 사본이 남지 않게 꼭 "잘라내기"로 옮깁니다.
8. 클로드 채팅에 "키 넣음"이라고 말하면 주소 5개로 시험합니다(`python scripts/gsc_index_check.py --test 5`).

열쇠 파일은 비밀번호와 같습니다. 메신저·메일·저장소에 올리지 않습니다.
