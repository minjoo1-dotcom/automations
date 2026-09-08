# 셋업 가이드 (신규 담당자용)

이 폴더의 스크립트들은 Google Calendar/Sheets API를 개인 OAuth로 호출한다. 전 담당자의 credentials.json/token.json은 그 사람 개인 Google 계정에 발급된 것이라 재사용할 수 없다 - 새로 발급받아야 한다.

## 1. 라이브러리 CSV 준비

이 repo에는 실제 쿼리 라이브러리(6월 이후 외부광고 조건 정리.csv)가 포함되어 있지 않다(과거 발송 조건/쿼리 원문이라 repo에 올리지 않기로 함). 전 담당자에게 파일을 직접 전달받아 이 폴더(또는 원하는 위치)에 두고, 아래 3개 스크립트 상단의 CSV_PATH 상수를 실제 경로로 수정한다:
- lookup_advertiser_query.py
- append_to_library.py
- fill_planid.py

(지금은 전 담당자 PC 경로가 하드코딩되어 있어 그대로 두면 안 돌아간다.)

## 2. Google Cloud OAuth 클라이언트 발급

1. Google Cloud Console(console.cloud.google.com)에서 프로젝트를 새로 만들거나 기존 사내 프로젝트를 사용한다.
2. "API 및 서비스 -> 라이브러리"에서 다음 두 API를 활성화한다:
   - Google Calendar API
   - Google Sheets API
3. "API 및 서비스 -> OAuth 동의 화면"을 설정한다 (내부 사용자용이면 "내부"로, 아니면 "외부" + 테스트 사용자에 본인 계정 추가).
4. "사용자 인증 정보 -> 사용자 인증 정보 만들기 -> OAuth 클라이언트 ID"에서 애플리케이션 유형을 데스크톱 앱으로 선택해 생성한다.
5. 생성된 클라이언트의 JSON을 다운로드해서 이 폴더에 credentials.json이라는 이름으로 저장한다. (google_auth.py가 이 파일명을 그대로 찾는다.)

## 3. 최초 인증 (token.json 자동 생성)

credentials.json을 넣은 상태에서 아무 스크립트나 한 번 실행하면 브라우저가 자동으로 열리고 Google 로그인/동의 화면이 뜬다. 예:
```
python fetch_send_history.py --advertiser 현대캐피탈
```
동의를 완료하면 이 폴더에 token.json이 자동 생성되고, 이후로는 재인증 없이 계속 쓸 수 있다(토큰이 만료되면 자동 갱신됨).

주의: credentials.json/token.json은 개인 인증정보이므로 이 repo(git)에 커밋하지 말 것 - .gitignore에 이미 포함되어 있다.

## 4. 시트/캘린더 접근 권한

전 담당자 또는 팀 관리자에게 아래 항목을 본인 Google 계정 기준으로 공유 요청한다:
- 요청/발송이력 구글시트 ("Finda 광고 요청", fileId=19PnkXgbpOJ6a9Y6v_XdibJ3EqdOCgzPFpYrihWiiDec) - 읽기 권한
- CRM 일정 캘린더, 광고 부킹 캘린더 - 읽기 권한 (check_calendar_overlap.py 상단 CRM_CALENDAR_IDS/BOOKING_CALENDAR_ID에 실제 캘린더 ID가 이미 적혀 있음, 본인 계정에 공유만 받으면 됨)

권한이 없으면 스크립트 실행 시 403 에러가 난다.

## 5. Python 실행 환경

이 폴더의 스크립트는 google-auth, google-auth-oauthlib, google-api-python-client 패키지가 필요하다:
```
pip install google-auth google-auth-oauthlib google-api-python-client
```

이후 사용법은 README.md, 쿼리 작성 규칙/현재 이슈는 HANDOFF.md, DB 스키마 지식은 schema_notes.md를 참고한다.
