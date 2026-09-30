# PC 사례 가져오기 지시문 (매일 13:40 무렵, 운영자 PC)

사례 원본(사진·메모)은 운영자 PC의 `C:\Users\AOMG\Documents\카카오톡 받은 파일\폐차사진원본` 에만 있습니다.
오후 2시 클라우드 루틴은 이 폴더를 볼 수 없으므로, **PC의 Claude 앱 예약 작업**이 먼저 3건을 골라 가리고 줄여서
저장소 `cases/input/` 에 올립니다. 그러면 2시 루틴(`docs/daily-routine-prompt.md` 3-1)이 사례 페이지를 만들고 3시 보고에 적습니다.

- 예약 작업의 폴더: PC에 받아 둔 pyecha-landing 저장소 폴더
- 예약 작업의 지시문: "저장소의 docs/pc-case-import-prompt.md 파일을 열어서, 그 안의 코드 상자에 있는 지시문을 처음부터 끝까지 그대로 따라 실행해."
- 실제 지시문은 **아래 코드 상자 하나**뿐입니다. 바꿀 때는 이 코드 상자 안만 고쳐 main 에 올립니다.
- 원본 폴더는 `.claude/settings.json` 에서 Claude 가 직접 읽거나 고치지 못하게 막혀 있습니다. 원본은 `scripts/pc_cases.py` 만 다룹니다.

```text
PC에서 하는 "사례 가져오기" 작업이다. 원본 사진·메모는 이 PC 밖으로 내보내지 않고, 가린 사진과 정리된 메모만 저장소 cases/input/ 에 올린다. 아래 순서와 규칙을 그대로 따른다.

[절대 규칙]
- "문자백업"이 들어간 폴더와 "제외" 폴더는 열지도, 목록을 보지도, 읽지도 않는다.
- 원본 폴더(C:\Users\AOMG\Documents\카카오톡 받은 파일\폐차사진원본)는 직접 열거나 목록을 보지 않는다. 원본은 scripts/pc_cases.py 로만 다룬다. 사진은 저장소 안 .cases_staging/ 의 미리보기만 본다.
- 원본 폴더에는 pc_cases.py mark 가 만드는 반영됨.txt 말고는 아무것도 만들거나 고치거나 옮기거나 지우지 않는다.
- 금액·시세, "수출 된다/안 된다" 같은 단정, 고객 이름·전화번호·차량번호·주소는 어디에도 쓰지 않는다(스크립트가 메모에서 걸러 낸다. 메모를 손으로 고쳐 통과시키지 않는다).
- 하루 3건까지. scripts/, templates/, CLAUDE.md, docs/ 는 고치지 않는다.

[준비]
1. `git rev-parse --show-toplevel` 로 지금 폴더가 pyecha-landing 저장소인지 확인한다. 아니면 멈추고 "저장소 폴더에서 열어 주세요"라고 보고한다.
2. `git checkout main` 후 `git pull origin main`. 커밋하지 않은 변경이 있으면 멈추고 보고한다.
3. `python -m pip install -q pillow` (python 이 안 되면 py 로). 이후 명령도 같은 것으로 실행한다.

[고르기]
4. `python scripts/pc_cases.py scan` 을 실행한다. 우선/ → 일반/ 순서로, 지역·차종·연식·시동이 다 채워지고 반영됨.txt 가 없는 건 중 3건(c1~c3)을 고른다. 0건이면 "가져올 사례 없음"이라고 보고하고 끝낸다.
5. `python scripts/pc_cases.py prepare` 를 실행한다(.cases_staging/cN/ 에 p01.jpg… 미리보기와 sheet*.jpg 모아보기).

[가리기 — 건마다]
6. .cases_staging/cN/sheet*.jpg 를 열어 보고 쓸 사진을 최대 6장 고른다. 순서: 차 전체 모습 → 상태가 보이는 사진 → 견인·작업 장면.
   - 서류(등록증·신분증·계약서·통장·휴대폰 화면 등)가 보이는 사진은 고르지 않는다. 가려서 쓰지 말고 뺀다.
   - 번호판이 안 보이는 사진을 먼저 고른다. 사람 얼굴, 집 번지·상호·전화번호가 적힌 간판이 크게 나온 사진은 되도록 고르지 않는다.
7. 고른 사진(pNN.jpg)을 한 장씩 크게 열어 번호판·얼굴·글씨(서류·전화번호·주소)가 있는 곳을 찾고 .cases_staging/cN/select.json 을 쓴다.
   형식: {"photos": [{"file": "p03.jpg", "boxes": [[왼쪽, 위, 오른쪽, 아래]]}, {"file": "p05.jpg", "boxes": []}]}
   좌표는 사진 너비·높이에 대한 비율(0~1)이다. 네모는 넉넉하게 잡는다. 가릴 것이 없으면 boxes 는 [].
8. `python scripts/pc_cases.py mask cN` 을 실행하고 .cases_staging/cN/out/1.jpg… 를 한 장씩 크게 열어 확인한다. 번호판 글자·얼굴·서류 글씨가 조금이라도 알아볼 수 있으면 네모를 넓혀 다시 mask 한다. 두 번 고쳐도 안 되면 그 사진은 select.json 에서 뺀다.
9. 쓸 사진이 한 장도 안 남거나 가린 것이 확실하지 않으면 `python scripts/pc_cases.py drop cN "<쉬운 말 이유>"` 로 빼고, `python scripts/pc_cases.py scan --more` → `python scripts/pc_cases.py prepare` 로 모자란 만큼 다음 건을 골라 같은 순서(6~8)로 처리한다. 합쳐서 3건이 넘지 않게 한다.
10. `python scripts/pc_cases.py stage cN` 을 실행한다(cases/input/ 에 사진과 정리된 메모.txt 를 넣고 검사). 실패하면 그 건은 drop 하고 이유를 보고에 적는다.

[올리기]
11. `git add cases/input` 후 `git status --short` 로 cases/input/ 밖의 파일이 들어가지 않았는지 확인한다(.cases_staging 은 .gitignore 로 올라가지 않는다).
12. `git commit -m "Add N case inputs (YYYY-MM-DD)"` 후 `git push origin main`. 거절되면 `git pull --rebase origin main` 후 한 번 더 push 한다. 그래도 안 되면 mark 하지 말고 이유를 보고한다. 강제 push 는 하지 않는다.
13. push 가 성공한 뒤에만 `python scripts/pc_cases.py mark` 를 실행한다(가져간 원본 폴더마다 반영됨.txt).
14. `python scripts/pc_cases.py report` 를 실행해 그 줄을 보고에 옮긴 뒤, `python scripts/pc_cases.py clean` 으로 미리보기(원본 사진 사본)를 지운다.

[보고]
- 오늘 가져온 사례 N건: 지역·차종, …
- 뺀 건과 이유, scan 의 "조건 미달" 건수
- "사례 페이지는 오후 2시 루틴이 만들어 3시 보고에 올립니다"
```
