# 발송광고 자동화 도구 사용 가이드

개인 로컬 도구. 실제 쿼리 실행/세팅은 항상 망분리 환경에서 담당자가 수동으로 함.
이 도구들이 하는 일은 **draft(쿼리 초안) 생성까지**.

**→ 처음 이 프로젝트를 맡았다면 이 파일보다 [`HANDOFF.md`](HANDOFF.md)를 먼저 읽을 것.** 쿼리 작성 규칙, 최근 발견된 데이터 이슈, 현재 열려있는 건들이 정리되어 있음.

**→ 아직 Google 인증/라이브러리 CSV를 셋업 안 했다면 [`SETUP.md`](SETUP.md)를 먼저 볼 것.**

Python은 PATH 별칭 문제로 `python` 명령이 안 먹으므로 항상 전체 경로로 실행:
```
C:\Users\finda\AppData\Local\Programs\Python\Python314\python.exe
```
(아래 예시에서는 `python`으로 줄여 씀. 실제로는 위 전체 경로로 바꿔서 실행.)

모든 스크립트는 이 폴더(`발송광고 자동화`)에서 실행.

---

## 1. 캘린더 확인 / 빈 시간 찾기

CRM 캘린더 + 광고 부킹 캘린더에서 지정한 날짜와 **같은 달, 같은 요일에 해당하는 모든 날짜**의 일정을 한꺼번에 보여줌. 부킹 요청이 오면 이걸로 그 요일 패턴(매주 반복되는 일정 포함)을 한 번에 확인.

```
python check_calendar_overlap.py --date 2026-07-23
python check_calendar_overlap.py --date 2026-07-23 --candidate 11:00-11:30   (특정 시간대 겹침 여부까지 체크)
```

## 2. 발송이력 시트에서 광고주 이력 조회 / 특정 행 그대로 가져오기

구글시트(발송이력) 기준으로 특정 광고주의 최근 발송 건 조회.

```
python fetch_send_history.py --advertiser <광고주명> --days <조회기간, 기본 30>
```

실제 세팅 시 시트에서 복붙하는 대신, 시트 id만 주면 그 행 전체(제목/본문/랜딩/발송조건/신청자 등)를 그대로 가져올 수 있음:

```
python fetch_send_history.py --id <시트 id>
```

⚠️ 여기서 나오는 `id`는 시트 내부 순번이고, 실제 쿼리 시스템의 `planID`와는 다름. dedup에 쓰기 전엔 반드시 `planID` 매칭 확인.

## 3. 라이브러리(과거 쿼리 저장소)에서 광고주 쿼리 조회 — **새 draft 작성 전 항상 먼저 실행**

`6월 이후 외부광고 조건 정리.csv`에서 해당 광고주의 최근 발송 건(조건/쿼리/planID)을 최신순으로 보여줌. 새 조건을 받았을 때 템플릿/직전 planID 확인용.

```
python lookup_advertiser_query.py --advertiser <광고주명> [--top N] [--full-query]
```

- `--top`: 몇 건까지 볼지 (기본 1건)
- `--full-query`: 쿼리 전체 텍스트까지 출력

## 4. 새 조건으로 draft 쿼리 작성

Claude와의 채팅에서 자연어 조건을 주면, 위 3번 조회 결과 + `schema_notes.md`(DB 스키마 지식 노트)를 참고해서 SQL draft를 만듦. 이때 항상 지켜지는 규칙:

- **dedup(이전 발송자 제외)은 명시적으로 요청한 경우에만 넣음.** 아무 말 없으면 안 넣음.
- **하루 1건 제한**: 같은 날 다른 캠페인이 부킹돼 있으면, 그 대상자는 무조건 제외 (global 최우선 규칙).
- **날짜 범위**: "N일부터 M일까지"는 `< M+1일`로 변환 (경계일 포함 주의).
- 쿼리 작성 중 새로운 테이블/컬럼/조인 정보가 나오면 `schema_notes.md`에 기록해둠 (다음에 재사용).

## 5. draft 컨펌 → 라이브러리에 즉시 추가

draft가 컨펌되면(아직 망분리 실행 전, planID 모르는 상태) 라이브러리 CSV에 바로 새 행을 추가.

1. 아래 컬럼을 담은 JSON 파일 작성 (모르는 값은 비워도 됨: `id`, `발송일`, `발송 시간`, `제목`, `본문`, `planID`):
   ```json
   {
     "광고주명": "...",
     "발송일": "...",
     "광고종류": "LMS 또는 App Push",
     "발송 시간": "...",
     "제목": "...",
     "본문": "...",
     "발송 조건": "...",
     "쿼리": "SELECT ...",
     "csv 업로드 여부": "0"
   }
   ```
2. 실행:
   ```
   python append_to_library.py --json <json파일 경로>
   ```

## 6. 망분리 실행 후 실제 planID 백필

망분리에서 실제로 쿼리를 돌려서 진짜 planID가 나오면, 라이브러리에서 그 광고주의 빈 planID 행을 찾아 채움.

```
python fill_planid.py --advertiser <광고주명> --planid <실제 planID>
```

- 빈 planID 후보가 여러 개면 자동으로 목록(발송일/조건)을 보여주고 멈춤 → 목록에서 맞는 걸 확인하고 `--pick <번호>`로 재실행:
  ```
  python fill_planid.py --advertiser <광고주명> --planid <실제 planID> --pick <번호>
  ```

## 공통 옵션

`lookup_advertiser_query.py` / `append_to_library.py` / `fill_planid.py` 세 스크립트 모두 `--csv-path <경로>` 옵션으로 실제 파일 대신 다른 CSV(테스트용 복사본 등)를 지정할 수 있음. 운영 파일을 건드리기 전에 테스트하고 싶을 때 사용.

## 파일 위치

- 스크립트: 이 폴더 전체
- 쿼리 라이브러리(운영 파일): 이 폴더의 `6월 이후 외부광고 조건 정리.csv` (예전엔 `Downloads`에 있었으나 2026-07-14에 이 폴더로 이동함)
- DB 스키마 지식 노트: `schema_notes.md`
- 인계 문서(쿼리 규칙/현재 이슈/현황): `HANDOFF.md`
- 구글 OAuth: `credentials.json` / `token.json` (Calendar + Sheets 통합 scope, 이 폴더에 있음). **이 두 파일은 특정 개인 Google 계정에 발급된 것이라 다른 사람이 그대로 못 씀** — 담당자가 바뀌면 새 OAuth 클라이언트를 발급받고 재인증해야 함. 발급 절차는 `SETUP.md` 참고.
