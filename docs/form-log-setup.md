# 폼 문의 기록 시트 (2026-11-04 병한님)

견적 폼을 보낼 때마다 구글 시트 "폐차119 폼 문의"에 한 줄(날짜·시간·페이지 주소·src·지역·어디서)이 남습니다.
"어디서"는 처음 들어온 곳의 앞 낱말 하나(네이버·구글·유튜브·다음·카카오·인스타그램·직접, 그 밖은 기타)이고, 들어온 사이트 주소는 보내지 않습니다(2026-11-04 추가).
전화번호·이름·차번호는 사이트가 보내지도 않고 시트에 적지도 않습니다.
기존 캘린더 알림 스크립트(`lead_hook_url`)는 그대로 두고, 이 시트는 따로 붙은 기록 전용 웹 앱(`site_config.json` 의 `form_log_url`)입니다.

- 쓰는 곳: `scripts/form_inquiries.py` 가 이 웹 앱의 GET(`?key=pyecha119`)으로 줄을 받아 `data/form_inquiries.json` 에 합치고, 아침 보고(오전 6시 55분)·PC 작업 "폐차 사례 가져오기" 보고(오후 1시 40분)의 "폼 문의" 칸을 만듭니다. 시트가 생긴 다음 날부터는 거래 기록부 대신 시트 숫자를 씁니다.
- 시트를 지우거나 칸 순서를 바꾸지 않습니다. 시험으로 보낸 줄만 지웁니다.
- 스크립트를 고치면 Apps Script 화면 오른쪽 위 **배포 → 배포 관리 → 연필 → 버전: 새 버전 → 배포**로 같은 주소를 유지합니다("새 배포"를 누르면 주소가 바뀜).

## 설정 순서

1. 크롬에서 sheets.new 를 열어 새 시트를 만들고, 왼쪽 위 제목을 "폐차119 폼 문의"로 바꿉니다.
2. 시트 맨 위 메뉴 **확장 프로그램 → Apps Script** → 새 탭의 편집기에서 `Code.gs` 내용을 모두 지우고 아래 코드 상자를 붙여 넣은 뒤 💾(저장)을 누릅니다.
3. 오른쪽 위 파란 **배포 → 새 배포** → 톱니바퀴 → **웹 앱** → 실행 사용자 "나", 액세스 권한 "모든 사용자" → **배포** → 권한 검토(계정 선택 → 고급 → 안전하지 않음으로 이동 → 허용).
4. 나온 **웹 앱 URL**(https://script.google.com/macros/s/…/exec)을 복사해 Claude 에 보냅니다. Claude 가 `form_log_url` 에 넣고 페이지를 다시 만듭니다.

```javascript
// 폐차119 폼 문의 기록(2026-11-04). 받는 것: 날짜·시간, 페이지 주소, src, 지역, 어디서(네이버·구글·유튜브·다음·카카오·인스타그램·직접·기타). 전화번호·이름·차번호는 받지도 적지도 않는다.
var KEY = 'pyecha119';
var SHEET = '폼문의';

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET);
  if (sh.getLastRow() === 0) {
    sh.getRange('A:F').setNumberFormat('@');
    sh.appendRow(['날짜', '시간', '페이지', 'src', '지역', '어디서']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function clean_(v, n) {
  var s = String(v || '').replace(/[\r\n\t]/g, ' ').trim().slice(0, n);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function doPost(e) {
  var p = (e && e.parameter) || {};
  if (p.key !== KEY || p.botcheck) return ContentService.createTextOutput('no');
  var page = String(p.page || '');
  try { page = decodeURIComponent(page); } catch (err) {}
  var now = new Date();
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    sheet_().appendRow([
      Utilities.formatDate(now, 'Asia/Seoul', 'yyyy-MM-dd'),
      Utilities.formatDate(now, 'Asia/Seoul', 'HH:mm'),
      clean_(page, 200), clean_(p.src, 40), clean_(p.region, 60), clean_(p.ref, 10)
    ]);
  } finally {
    lock.releaseLock();
  }
  return ContentService.createTextOutput('ok');
}

function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.key !== KEY) return ContentService.createTextOutput('no');
  var since = String(p.since || '');
  var rows = sheet_().getDataRange().getDisplayValues().slice(1)
    .filter(function (r) { return r[0] && (!since || r[0] >= since); })
    .map(function (r) { return { date: r[0], time: r[1], page: r[2], src: r[3], region: r[4], ref: r[5] || '' }; });
  return ContentService.createTextOutput(JSON.stringify({ rows: rows }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

## 시험

주소를 넣고 페이지를 다시 만든 뒤 아무 구 페이지 폼에 차번호 "시험"·연락처 010-0000-0000 으로 한 번 보내면 시트에 한 줄이 생깁니다(캘린더 일정·메일도 같이 옵니다). 확인한 뒤 시트의 그 줄과 캘린더 일정을 지웁니다.
