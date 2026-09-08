# 발송광고 자동화 — 인계 문서

이 프로젝트를 담당하던 사람의 Claude 계정/로컬 환경이 삭제될 예정이라, 그동안 대화(memory)로만 쌓여있던 지식을 이 파일에 전부 옮겨 적었다. **새 담당자는 새 Claude 세션으로 시작하게 되므로, 이 문서 + `schema_notes.md` + `README.md`가 유일한 지식 소스다.**

## 이 프로젝트가 하는 일

핀다가 제휴 광고주(현대캐피탈, OK저축은행, SBI저축은행, 메리츠화재 등)의 "외부광고"(LMS/App Push)를 우리 유저 DB 기준으로 타겟팅해서 발송하는 업무를 보조한다. **망분리 환경 제약으로 실제 쿼리 실행/발송툴 등록은 항상 담당자가 직접 수동으로 하고, 이 도구는 "쿼리 draft 작성 + 과거 이력 관리"까지만 한다.**

전체 흐름: 광고주 요청(요청시트) → 조건 확인 → (필요시 모수 count-check) → draft 쿼리 작성 → 담당자가 망분리에서 직접 실행/등록 → 실제 planID 확정 → 라이브러리 CSV에 기록.

## 파일 위치 (전부 이 폴더 `C:\Users\finda\Documents\Claude Projects\발송광고 자동화\`)

- **`6월 이후 외부광고 조건 정리.csv`** — 과거~현재 모든 발송 건의 조건/쿼리/planID를 모아둔 라이브러리(운영 파일, 100행 이상). **주의: `README.md`에는 이 파일 경로가 옛날 `Downloads` 폴더로 잘못 적혀 있음 — 실제로는 이 폴더가 맞다.**
- **`schema_notes.md`** — DB 스키마/컬럼/조인 지식 노트. 새 쿼리 작성 전 항상 먼저 확인.
- **`README.md`** — 스크립트 사용법.
- **`append_to_library.py`** / **`fill_planid.py`** / **`lookup_advertiser_query.py`** / **`fetch_send_history.py`** / **`check_calendar_overlap.py`** — 로컬 파이썬 도구.
- **`credentials.json`** / **`token.json`** — Google OAuth (Calendar + Sheets). **이건 전 담당자 개인 Google 계정에 발급된 것이라 그대로 재사용 불가.** 새 담당자는 본인 Google Cloud 프로젝트에서 OAuth 클라이언트를 새로 발급받고, `google_auth.py`가 이 폴더에서 새 `token.json`을 만들도록 재인증해야 한다.

## 데이터 소스 두 시트 (혼동 주의)

1. **요청/발송이력 구글시트** ("Finda 광고 요청", fileId=`19PnkXgbpOJ6a9Y6v_XdibJ3EqdOCgzPFpYrihWiiDec`) — 광고주가 신청한 원본 요청. `fetch_send_history.py --id <시트id>`로 조회. 이 시트의 **`id`는 내부 순번이고 실제 쿼리 시스템의 `planID`와 무관** — 반드시 구분할 것.
2. **라이브러리 CSV** (`6월 이후 외부광고 조건 정리.csv`) — 세팅이 완료된(컨펌된) 건만 사람이/스크립트가 기록하는 큐레이션 레이어. 이 CSV에도 자체 `id` 컬럼(행 번호)이 있는데, 이것도 요청시트의 `id`나 `planID`와 다른 별개의 값이다. **즉 "id"라는 이름의 값이 세 군데(요청시트 id / 라이브러리 CSV id / 실제 planID)에 각각 존재하고 서로 다르니, 사용자가 그냥 "id 168"이라고만 말하면 어느 시트 기준인지 되물어야 한다.**

요청시트 → 라이브러리 CSV로 반영되는 데는 시차가 있고, 신청은 됐지만 소재(제목/본문)를 아직 안 넣은 건은 라이브러리에 아예 안 나타난다(과거 사고: id=144 사례). 마스터 반영 지연으로 id 시퀀스에 갭(예: 124→127)이 생겨 리마인더가 발송 예정 건을 놓친 사고도 있었다.

## 쿼리 작성 핵심 규칙 (전부 실전에서 사고/피드백으로 확정된 것들)

### 1. 엔진/문법은 용도에 따라 두 갈래
| 용도 | 엔진 | 날짜함수 | 캐스팅 |
|---|---|---|---|
| CSV 추출(대상자 파일 추출, 모수 count-check 포함) | **Databricks** (Spark SQL) | `current_date()`, `add_months(current_date(), -N)`, `date_sub(current_date(), N)` | `CAST(x AS STRING)` |
| 발송툴에 쿼리 그대로 등록(직접등록) | **MySQL** | `CURDATE()`, `DATE_SUB(CURDATE(), INTERVAL N MONTH/DAY)` | `CAST(x AS CHAR)` |

- `WITH`/`UNION`/`EXISTS`/`ROW_NUMBER() OVER(...)`/`LIMIT`는 양쪽 동일.
- **발송툴 직접등록 쿼리는 끝에 세미콜론(`;`) 금지** — 붙이면 등록 에러.
- 라이브러리 CSV의 `csv 업로드 여부` 컬럼이 이 갈래를 구분(1=CSV추출/Databricks, 0=직접등록/MySQL). 광고주/채널로 추론 불가, 건별로 다름 — 헷갈리면 직전 건을 참고하거나 사용자에게 확인.
- **모수 확인(count-check) 쿼리는 예외 없이 항상 Databricks 문법으로 통일할 것.** 중간에 MySQL 문법 하나라도 섞이면 다른 데이터 소스(발송툴쪽 MySQL/StarRocks 환경)를 참조하게 돼서 완전히 다른 모수가 나올 수 있다 — 실제로 2026-08-25에 이 실수로 실제 모수(20.5만)의 8분의 1(2.5만)로 잘못 보고된 사고가 있었다.

### 2. CSV 업로드 방식일 때 dedup은 "발송툴 참조 쿼리"에 넣어야 한다
`csv 업로드 여부=1`일 때 Databricks 추출 쿼리에 dedup(NOT EXISTS 등)을 넣어도 무의미하다 — 추출 시점엔 아직 발송 전이라 로그가 없다. 실제 흐름:
1. Databricks에서 dedup 없이 순수 대상자만 뽑아 CSV로 업로드
2. 업로드된 user_id가 `account.userid_sixth`에 `plan_id`별로 저장됨
3. 발송툴이 자동 생성하는 **참조 쿼리**(`INNER JOIN account.userid_sixth ... AND plan_id=<이 건의 planID>` + mkt_agree 등 기본조건, MySQL)가 실제 발송 시점에 실행됨 — **dedup은 이 참조 쿼리 쪽에 `NOT EXISTS (... plan_id=<제외할 planID>)`로 추가해야** 발송 시점 기준으로 정상 작동한다.
4. **테스터 id도 CSV가 아니라 이 참조 쿼리 쪽에 `UNION SELECT`로 넣어야 한다** — 참조 쿼리 WHERE절에 mkt_agree=1 조건이 있어서, CSV에 테스터를 넣어도 마수동 안 했으면 걸러질 수 있음.
5. 아직 발송 전이라 로그(`account.user_crm_send_log`)가 없는 상태에서 직전 건 제외가 필요하면, 로그 대신 **`account.userid_sixth`에 해당 `plan_id`의 user_id가 있는지**로 판별(그 planID가 CSV 업로드까지는 됐지만 아직 실제 발송 전인 경우에 씀).

### 3. ⚠️ 최근 발견된 중요 이슈 — fcsdb 테이블 발송툴(MySQL) vs Databricks 데이터 불일치
2026-09-01, 완전히 동일한 로직의 쿼리(`fcsdb.la_application` 조인 포함)를 Databricks에서 돌리면 12만, 발송툴 MySQL 환경에서 돌리면 5.5만이 나온 사례가 있었다. **문법 차이로는 설명 안 되는 규모 차이 — 발송툴이 참조하는 fcsdb 테이블 사본이 Databricks와 복제 지연/불완전 상태일 가능성이 높다.** `fcsdb.la_application` 등 원본 로그 테이블을 조인하는 조건을 발송툴 직접등록(MySQL)으로 쓸 때는 **반드시 Databricks count-check 결과와 대조**하고, 크게 다르면 **CSV 업로드 방식으로 우회**할 것. 근본 원인(복제 지연 여부)은 이 세션에서 검증 불가 — DB/인프라팀 확인 필요.

### 4. "주택보유 + N개월 이내 한도조회" 조합 — 정확한 join 구조 (2026-09-01 실측 검증)
`uts.user_attributes.loan_last_application_date`(최근 한도조회일) 컬럼은 **4~6개월치만 채워지는 캡이 있어서**, N=6개월처럼 캡에 걸치는 조건에 이 컬럼을 쓰면 실제보다 훨씬 적게 나온다(실측: 12만이어야 할 게 5.5만으로 나옴). 올바른 방법은 `fcsdb.la_application` 원본 로그 기준으로 **두 조건을 독립적인 EXISTS로 각각** 확인하는 것 — "자가 소유가 찍힌 신청 건이 (시점 무관) 존재하는가"와 "최근 N개월 이내 신청 건이 (주택정보 무관) 존재하는가"를 따로 본다(같은 신청 건일 필요 없음 — 사용자가 "핀다 이용 이력 중 한번이라도 자가로 신청한 적 있고 최근에도 조회했으면"이라고 명시적으로 확인함):
```sql
AND EXISTS (
    SELECT 1 FROM fcsdb.la_application la
    INNER JOIN fcsdb.la_application_userinput lu
        ON lu.application_id = la.id AND lu.houseown_type = '자가'
    WHERE la.user_id = ua.user_id
)
AND EXISTS (
    SELECT 1 FROM fcsdb.la_application la2
    WHERE la2.user_id = ua.user_id
      AND la2.insert_time >= DATE_SUB(CURDATE(), INTERVAL N MONTH)  -- Databricks: add_months(current_date(), -N)
)
```
"대출 미실행" 조건이 같이 필요하면 `uts.user_attributes.loan_last_contract_date IS NULL OR loan_last_contract_date < ...` (윈도우가 4~6개월 이내면 이 컬럼 그대로 써도 됨 — 캡 문제는 "장기 윈도우"에서만 발생).

### 5. uts.user_attributes 컬럼 개명 (DAS-3646, 2026-08-12 라이브 적용) — 신규 쿼리 필수 반영
82개 컬럼이 개명됨. 자주 쓰는 것:
| 구 컬럼명 | 신 컬럼명 |
|---|---|
| `recent_appl_date` | `loan_last_application_date` |
| `recent_contract_date` | `loan_last_contract_date` |
| `credit_score` | `kcb_credit_score` |
| `income_type` | `user_income_type` |
| `is_own_car` | `user_own_car_yn` |
| `houseown_type` | `user_houseown_type` |
| `age` | `user_age` |
| `gender` | `user_gender` |
| `last_comp_loanapplication_date` | `debt_last_competitor_application_date` |

전체 매핑표는 `schema_notes.md`와 원본 DDL(`C:\Users\finda\Downloads\DAS-3646_DDL_v1.0_라이브기준_20260812.sql`, 새 담당자 PC엔 없을 수 있음 — 없으면 schema_notes.md만 믿을 것). **라이브러리 CSV의 과거 쿼리(id 146대 이하)는 전부 구 컬럼명 그대로이며 소급 변환 안 함** — 템플릿으로 재사용할 때 반드시 신규 이름으로 치환.

### 6. 그 외 항상 지켜야 하는 규칙
- **마수동(`mkt_agree=1 AND (mkt_agree_info=1 OR mkt_agree_info IS NULL)`)은 채널 무관 항상 포함.** 디바이스 토큰 조인(`account.user3`+`account.user_device`, `noti_token IS NOT NULL`)은 **App Push에서만** 필요 — LMS는 불필요. 이 둘을 같은 이름("마수동 조인")으로 부르지 말 것, 서로 다른 개념.
- **dedup(이전 발송자 제외)은 명시적으로 요청한 경우에만 넣는다.** 아무 말 없으면 안 넣음.
- **하루 1건 제한(global 최우선)**: 같은 날 다른 캠페인이 이미 부킹돼 있으면, 발송조건 텍스트에 명시가 없어도 그 대상자는 무조건 제외해야 한다(사용자가 "매일 외부광고는 하루 최대 1건만 받게 해야 해서 넣은 로직"이라고 명시 확인).
- **날짜 범위 "N일부터 M일까지"는 `< M+1일`로 변환** (`< M일`로 쓰면 M일 당일이 통째로 빠지는 off-by-one 버그).
- **최종 확정 draft 쿼리엔 `--` 주석 금지**, 순수 SQL만.
- **대상자수를 사람에게 전달할 때는 절사한 "만" 단위로** (16548 → 1.6만, 반올림 아니라 절사). 단 라이브러리 CSV의 "대상자수" 컬럼 기록 관행은 그대로 유지.
- **신용점수 NULL은 저신용이 아니라 KCB 연동 만료**(6개월 이상 앱 미접속 시 리셋)다. 하한 조건(`kcb_credit_score >= N`) 걸 때 별도 지시 없으면 `(kcb_credit_score >= N OR kcb_credit_score IS NULL)`로 NULL을 통과시키는 게 기본값.
- **신용점수 "하위 50%" 같은 상대적 표현은 핀다 유저 기준 percentile로 판단하면 안 됨** — 핀다 유저 자체가 중저신용 비중이 높아 전 국민 기준보다 훨씬 빡빡해짐. 광고주에게 구체적 컷오프를 되물을 것.
- **한도조회=`condition_approved`, 실행(약정)=`contract_approved`만** (더 넓은 세트인 `contract_requested/applied/failed/approved/rejected/retracted`는 "계약 단계 진입 시도"라는 별개 목적 — "미실행" 판단에 잘못 쓰면 실패/거절/철회까지 "실행됨"으로 묶여 모수가 부당히 줄어듦, 실제 2.46배 차이 난 사고 있었음).
- **`update_time_batch` 배치 지연**: 카운트가 뜬금없이 0이면 1순위로 의심. `AND (DATE(update_time_batch)=CURDATE() OR update_time_batch IS NULL)` 조건을 빼고 재확인, 그래도 0이면 `uts.user_attributes` 테이블 자체 배치 지연 의심 (`SELECT MAX(update_time_batch)`로 확인).
- **finda-query-helper MCP는 이 환경에서 KB가 비어있고 쿼리 실행도 안 되므로 쓰지 말 것.**

### 7. 신규 발견 테이블
- **`lms.kcb_user_score_history`**: 유저별 신용점수 변동 로그. 컬럼 `user_id`/`insert_time`/`credit_score`/`pre_credit_score`. 특정 시점 기준 "가장 최근 변동"은 `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY insert_time DESC)`로 구함. 점수 비교 시 `CAST(... AS UNSIGNED)`(MySQL)/`CAST(... AS INT)`(Databricks) 필요.
- **`lms.kcb_biz_total_credit_info`**: 사업자 카드 보유 여부 = `card_open_cnt > 0`, 키는 `user_id`. **단, 이 세션 PC에서 조회 권한이 없어 `uts.user_attributes`와의 실제 조인 정합성을 검증 못한 상태** — 권한 확보 후 검증 필요.

## 자주 쓰는 쿼리 패턴 (라이브러리에서 바로 찾을 키워드)
- 자동차 보유(자담대): `user_own_car_yn = 1`
- 주택 자가 보유: `fcsdb.la_application_userinput.houseown_type = '자가'` (조인키 `application_id`)
- 아파트 보유: `fcsdb.la_application_houseinput.house_type = 'APT'` (조인키 `application_id`, `is_apt` 컬럼은 DAS-3646으로 삭제됨)
- 사업자: `user_income_type = 'PRIVATEBUSINESS'`
- 신용대출 보유 중: `lms.lms_loan_account_info.account_type IN ('3100')` + `exp_date > '0'` + `CAST(exp_date AS STRING/CHAR) > date_format(current_date(),'yyyyMMdd')`(만기 미도래)
- 타사 한도조회: `debt_last_competitor_application_date`
- "가승인 & 미실행" 시리즈(현대캐피탈 자담대/주담대, SBI): `fcsdb.la_loanapply`+`la_application`+`la_product` 3-CTE 패턴(T1=승인군, T2=신청군 제외, target_user=차집합). 라이브러리에서 "가승인" 검색하면 템플릿 다수.

## 현재 열려있는 이슈 (인계 시점, 2026-09-08 기준)
- OK저축은행 "성실상환" 타겟팅: 채무조정/개인회생 인가 상태를 직접 나타내는 컬럼이 없어서, 신용점수 구간+`lms.kcb_user_score_history` 상승이력+`debt_loan_cnt>=1` 조합으로 간접 근사 중. 정확한 매칭이 아님을 광고주도 인지.
- 요청시트 id=167(9/10), id=185(9/16) — 아직 소재 미확정, draft 미착수.
- fcsdb MySQL/Databricks 불일치 근본 원인 미해결 (위 3번 항목) — DB/인프라팀 확인 필요.
- `lms.kcb_biz_total_credit_info` 조인 키 미검증 (위 7번 항목).

## 인수인계 시 반드시 할 일
1. 새 담당자 본인 Google 계정으로 OAuth 재인증 (`credentials.json` 재발급 필요, 절차는 `SETUP.md` 참고).
2. 요청시트/발송이력 구글시트 공유 권한을 새 담당자 계정에 부여.
3. 이 문서 + `schema_notes.md`를 새 Claude 세션에 먼저 읽히고, 실제 요청 1건을 처음부터 끝까지(조회→draft→컨펌→라이브러리 등록) 같이 처리해보며 빠진 내용 확인.
