# GA4 유입 자동 측정 설정 (2026-11-04 병한님)

폼 문의가 네이버·구글·유튜브·직접 중 어디서 오는지 매일 셉니다. PC 예약 작업 "구글 색인 확인 (매일 낮)"이 색인 확인 바로 뒤에
`python scripts/ga4_daily.py --push` 를 돌려 어제 하루를 받고 `data/ga4_daily.json`·`docs/ga4-sources.md` 두 파일만 올립니다.
아침 보고(오전 6시 55분)·PC 작업 "폐차 사례 가져오기" 보고(오후 1시 40분)의 "폼 문의" 칸 아래 "어디서 왔나" 한 줄이 이 파일을 읽습니다.
열쇠는 서치 콘솔과 같은 `C:\Users\AOMG\gsc-key.json`(서비스 계정 `gsc-index-check@…iam.gserviceaccount.com`)이라 새로 받을 것은 없습니다.

## 병한님이 한 번만 할 일

1. 크롬 → [Google Analytics Data API 화면](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com) → 맨 위 프로젝트가 `pyecha119-gsc`(gsc-key 프로젝트)인지 보고 → 파란 "사용" 누르기.
2. 크롬 → GA4(abh777900) → 왼쪽 아래 톱니바퀴 "관리" → 속성 칸 "속성 액세스 관리" → 오른쪽 위 파란 ＋ → "사용자 추가" → `gsc-key.json` 의 client_email(`gsc-index-check@…iam.gserviceaccount.com`, [서비스 계정 목록](https://console.cloud.google.com/iam-admin/serviceaccounts)에서 복사) 붙여 넣기 → 역할 "뷰어" → "추가"("새 사용자에게 이메일로 알림"은 꺼도 됨).
3. GA4 "관리" → 속성 칸 "속성 세부정보"(속성 설정) → 오른쪽 위 **속성 ID 숫자**(9자리 안팎, G-로 시작하는 측정 ID 아님) 복사 → Claude 코드 탭에 "GA4 속성 ID 숫자 123456789" 처럼 보내기.
4. 끝. 이어서 "GA4 키 됨"이라고 하시면 Claude 가 `python scripts/ga4_daily.py --since 2026-10-20` 으로 과거치를 받아 `docs/ga4-sources.md` 를 채우고 11/2~11/3 유입 결론을 한 줄로 보고합니다.

- 속성 ID 는 `data/site_config.json` 의 `ga4_property_id` 에 들어갑니다(비어 있으면 "GA4 속성 ID 알려 주세요"만 나옴).
- 권한이 없거나 API 를 안 켰으면 스크립트가 "실패: GA4 자료 없음(권한 확인) HTTP 403 …"을 내고, 보고에는 "GA4 자료 없음(권한 확인)"이 적힙니다.
- 열쇠 파일은 비밀번호와 같습니다. 메신저·메일·저장소에 올리지 않습니다.
