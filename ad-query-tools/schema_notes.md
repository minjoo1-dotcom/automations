# 쿼리 작성용 스키마 참고 노트

과거 발송 쿼리에는 안 나왔지만, 새 쿼리 draft 작성 중 채팅으로 확인된 테이블/컬럼/조인 정보를 여기 쌓아둔다.
쿼리 draft 작성 전에 이 파일을 먼저 확인할 것.

## 쿼리 문법: 용도별 두 갈래 (2026-07-27 정정)

**하나로 통일된 게 아니다. 쿼리를 어디에 쓰느냐에 따라 문법이 갈린다.**

| 용도 | 엔진 | 날짜 함수 | 캐스팅 |
|---|---|---|---|
| **CSV 추출** (대상자 파일 추출, 사전 카운트 확인 포함) | Databricks (Spark SQL) | `current_date()`, `add_months(current_date(), -N)`, `date_sub(current_date(), N)` | `CAST(x AS STRING)` |
| **발송툴에 쿼리 그대로 등록** (세그먼트 직접 등록) | MySQL | `CURDATE()`, `DATE_SUB(CURDATE(), INTERVAL N MONTH)`, `DATE_SUB(CURDATE(), INTERVAL N DAY)` | `CAST(x AS CHAR)` |

양쪽 공통(변경 불필요): `WITH`, `UNION`/`UNION ALL`, `EXISTS`/`NOT EXISTS`, `ROW_NUMBER() OVER (...)`, `LIMIT`, `TIMESTAMP '2026-07-17 00:00:00'` 리터럴.

**발송툴 등록용 쿼리는 맨 끝 세미콜론(`;`) 금지** — 붙이면 등록 시 에러. (2026-07-27 사용자 확인) CSV 추출용 Databricks 쿼리는 무관하다. 라이브러리의 과거 쿼리 중 `;`로 끝나는 것들이 있으니(id 126/141 등), 발송툴용 템플릿으로 복사할 때 반드시 떼고 쓸 것.

날짜를 리터럴 문자열(`'2026-07-08 00:00:00'`)로만 박는 쿼리는 두 문법 차이가 아예 없어서 같은 SQL을 양쪽에 그대로 쓸 수 있다 (예: 현대캐피탈 자담대 시리즈).

**어느 쪽인지 판별:** 라이브러리 CSV(`6월 이후 외부광고 조건 정리.csv`)의 `csv 업로드 여부` 컬럼 — `1`이면 CSV 추출 경로(Databricks), `0`이면 발송툴 직접 등록(MySQL). 광고주나 채널로는 추론 불가(같은 광고주도 회차마다 갈림). 애매하면 사용자에게 묻거나 두 버전을 다 줄 것.

**기존 라이브러리 쿼리(59+건, id=146까지)는 전부 MySQL 문법**이고 소급 변환하지 않기로 함(사용자 확인). 과거 쿼리를 템플릿으로 쓸 때는 구조/조건 로직만 가져오고 문법은 용도에 맞게 갈아끼울 것.

**정정 이력:** 2026-07-24에 "실행 엔진이 Trino→Databricks로 교체됨"으로 기록했으나, 2026-07-27 id=137 draft 중 사용자가 "실제 발송툴은 MySQL 환경"이라고 정정 — 용도별로 나뉘는 것이었다. 기존 라이브러리 쿼리들을 "Trino/MySQL 스타일"이라고 부르던 것도 부정확했고, 실제로는 MySQL이다. Databricks 쪽 문법은 아직 실행 검증 전이라 처음 몇 건은 문법 에러 여부를 확인받을 것.

## 용어 정리: 마수동 vs 디바이스 토큰 조인 (별개 개념, 2026-07-16 최종 정정)

- **마수동 = 마케팅 수신동의(법적 요건, 모든 채널 공통)**: `ua.mkt_agree = 1 AND (ua.mkt_agree_info = 1 OR ua.mkt_agree_info IS NULL)`. "마수동"이라는 용어는 **이 조건만** 가리킨다. 채널 상관없이 항상 들어가야 함 — 이미 거의 모든 쿼리에 관행적으로 포함돼 있음.
- **디바이스 토큰 조인 (마수동과는 별개 개념)**: 아래 조인은 앱푸시 발송 가능 여부(디바이스 토큰 보유)를 확인하는 것으로, "마수동"이 아니다. **App Push 채널에서만** 필요하다. LMS는 디바이스 토큰이 있어야 발송 가능한 게 아니므로(문자 발송이라 앱 설치/토큰 여부와 무관) 이 조인을 넣지 않는 게 맞음 — OK저축은행 LMS 쿼리들(id=69,70,78,102,117,118,123 등)이 전부 이 조인 없이 작성된 게 실수가 아니라 정상.

```
INNER JOIN account.user3 AS u3
    ON u3.id = ua.user_id
INNER JOIN account.user_device AS ud
    ON u3.user_device_id = ud.id
   AND (ud.noti_token IS NOT NULL AND ud.noti_token != '')
```

**용어 사용 주의:** 채팅/쿼리 설명에서 이 디바이스 토큰 조인을 "마수동 조인"이라고 부르지 말 것 — "디바이스 토큰 조인" 또는 "앱푸시 발송가능 조인"이라고 부른다. "마수동"은 오직 mkt_agree 조건만 가리킨다.

**정정 이력:** 2026-07-16 초에 "마수동 조인은 채널 무관 항상 넣는다"로 잘못 기록 → 같은 날 "LMS는 디바이스 토큰 조인 불필요"로 1차 정정(개념은 맞았으나 여전히 디바이스 토큰 조인을 "마수동"이라고 잘못 부름) → 사용자가 "마수동은 mkt_agree고, 디바이스 토큰은 마수동이랑 다른거"라고 명시적으로 용어 자체를 정정함. 새 쿼리 짤 때는 **mkt_agree(마수동)는 항상 넣고, 디바이스 토큰 조인은 광고종류가 App Push일 때만 넣는다** — 이 둘을 같은 이름으로 부르지 않는다.

## 주택/부동산 관련

- **아파트 보유 여부**: `fcsdb.la_application_houseinput.house_type = 'APT'`
  - 조인키: `la_application_houseinput.application_id = fcsdb.la_application.id`
  - (2026-07-08 확인, OK저축은행 주담대 draft 작성 중)
- **자가 소유 여부(주택 종류 불문)**: `fcsdb.la_application_userinput.houseown_type = '자가'`
  - 조인키: `la_application_userinput.application_id = fcsdb.la_application.id`
  - (기존 현대캐피탈 주담대 쿼리들에서 확인됨)

## 직업/소득 유형 관련

- **사업자 여부**: `uts.user_attributes.income_type = 'PRIVATEBUSINESS'`
  - (2026-07-16 확인, 현대캐피탈 가계대출총량제 대응 - 사업자 타겟 전환 count draft 작성 중)
- **재직기간(입사월)**: `uts.user_attributes.company_enter_month` (DATE 타입). "N개월 이상 재직"은 `company_enter_month <= add_months(current_date(), -N)`로 판단. id134에서 쓴 "직장명 정보 존재 여부"(`la_application_userinput.company_name IS NOT NULL`)와는 다른 개념이니 혼용하지 말 것 — 전자는 재직 기간, 후자는 그냥 직장명 기재 여부.
  - (2026-08 확인, 신한저축은행 중금리 생활안정대출 draft 중)
- **신용대출 보유 중 여부**: `lms.lms_loan_account_info` 테이블, `account_type IN ('3100')`(신용대출) AND `exp_date > '0'` AND `CAST(exp_date AS STRING) > date_format(current_date(), 'yyyyMMdd')`(만기 미도래 = 현재 보유 중). 현대캐피탈 "신용대출보유" 조건(id76/114)에서도 동일하게 씀.
- **신용점수 "하위 50%"(중저신용자) 관련 — 핀다 유저 기준 percentile로 판단하면 안 됨**: 핀다 유저 자체가 중저신용자 비중이 높아서, 핀다 유저 내 median을 쓰면 전 국민 기준보다 훨씬 빡빡한(더 낮은) 컷오프가 나온다. "하위 50%"처럼 상대적 표현으로 요청이 오면 광고주에게 **구체적인 점수 컷오프**를 되물을 것 — 그동안의 다른 요청들(OK/신한 등)도 전부 "KCB 850이하"류 절대값으로 왔지 percentile로 온 적이 없음.
  - **참고 수치(2026-08 확인)**: 생활안정자금 관련 금융위 자료 기준 '26.6.29일 시점 NICE 889점 / **KCB 875점**이 하위 50% 컷오프라고 광고주(신한저축은행)가 알려줌. 핀다는 KCB 데이터를 쓰므로 이럴 땐 **875점**을 기준으로 사용. 단, 이 수치는 대출 시점에 따라 변동 가능한 외부 기준치이지 고정 상수가 아니므로, 시간이 많이 지난 뒤 재사용할 땐 최신 수치인지 다시 확인할 것.

## 발송 로그 / 세그먼트 쿼리 저장 테이블

- **발송 로그(배치)**: `account.noti_execution` — `plan_id`, `date_cd`(발송일자, DATE 타입) 컬럼 보유. (2026-07-13 확인)
- **유저 세그먼트**: `account.user_segment` — `id` 컬럼이 `noti_execution.plan_id`와 조인키. `query` 컬럼에 해당 세그먼트를 만든 SQL 전문이 텍스트로 저장되어 있음 (DB 엔진: Trino).
  - (2026-07-13 확인, "최근 한달 발송 plan_id → 쿼리에서 사용중인 distinct 테이블 목록" draft 작성 중)

## 타사 한도조회 관련

- **타사 한도조회자**: `uts.user_attributes.last_comp_loanapplication_date` 컬럼 날짜가 최신인지로 확인. "최신" 기준 윈도우는 요청마다 다를 수 있음(고정 규칙 아님) — 2026-07-15 신한저축은행 사잇돌 조합 건에서는 "최근 6개월 이내"로 확인.
  - (2026-07-15 확인, 신한저축은행 타사 한도조회자 + 기존 사잇돌 조건 조합 count draft 작성 중)

## 한도조회/약정(실행) 관련 (2026-08 OK저축은행 주담대 draft 중 확인)

- **`uts.user_attributes.recent_appl_date` = 한도조회일**, **`recent_contract_date` = 약정(대출 실행)일**. 서로 다른 이벤트를 가리키는 별개 컬럼이다 — "미실행" 조건을 걸려면 `recent_contract_date`를 봐야지 `recent_appl_date`로 대체하면 안 된다.
- **`recent_appl_date`는 사실상 최근 4~6개월치만 채워지는 컬럼이다.** 실제 데이터 확인 결과 `older_than_6m`(6개월보다 오래된 값) 카운트가 1건뿐이었음. 그래서 "최근 12개월 내 한도조회"처럼 캡보다 긴 윈도우를 이 컬럼으로 걸면, 사실상 `IS NOT NULL`과 다를 게 없어져서 조건이 아무것도 걸러내지 못하는 착시가 생긴다. 6개월을 넘는 진짜 장기 윈도우가 필요하면 `uts.user_attributes` 대신 `fcsdb.la_application`/`la_loanapply` 원본 로그로 재구성해야 한다.
- **`la_loanapply`로 재구성할 때 상태값 정의 주의 — "한도조회"와 "실행(약정)"에 쓸 status가 다르다:**
  - 한도조회(condition_approved 수준) = `status = 'condition_approved'`
  - 실행/약정 완료 = **`status = 'contract_approved'`만** 해당
  - 자담대 시리즈(id94/132/141)에서 "신청유저(미신청 대상 제외용)"를 정의할 때 쓰던 넓은 세트 `('contract_requested','contract_applied','contract_failed','contract_approved','contract_rejected','contract_retracted')`는 **"계약 단계까지 진행을 시도했는지"(성공/실패 무관)를 보는 별개 목적의 정의**다. 이걸 "미실행" 판단에 그대로 가져다 쓰면 `contract_failed`/`contract_rejected`/`contract_retracted`(실패·거절·철회 = 실행 안 됨)까지 "실행됨"으로 잘못 묶여서 모수가 부당하게 줄어든다. "대출 미실행" 조건엔 `contract_approved`만 실행으로 취급할 것.
  - (실제로 2026-08 OK저축은행 주담대 D조건 draft에서 이 실수로 모수가 34,924→85,862로, 약 2.46배 차이가 났음 — "미실행" 관련 조건 짤 때마다 이 구분을 먼저 확인할 것)
  - **OK저축은행 확인(2026-08):** OK 쪽에서 말하는 "실행"은 대출 약정을 뜻함 — 즉 `contract_approved`만 실행으로 보는 위 정의가 광고주 기준과 일치함이 컨펌됨.
- **`credit_score`가 NULL인 경우는 저신용이 아니라 KCB 연동 만료**(6개월 이상 앱 미접속 시 NULL로 리셋됨)다. 신용점수 하한 조건(`credit_score >= N`)을 걸 때 NULL을 그냥 배제하면 "저신용이라서"가 아니라 "최근에 앱을 안 켜서" 탈락하는 사람이 섞여 들어간다. 별도 지시가 없으면 `(credit_score >= N OR credit_score IS NULL)`로 NULL을 통과시키는 게 기본값에 가깝다 — 단, 요청 쪽에서 신용점수를 엄격히 확인된 값만으로 보고 싶다고 명시하면 NULL을 배제해야 한다.

## CSV 업로드 방식일 때 dedup은 참조 쿼리에 넣어야 함 (2026-08 확인)

**`csv 업로드 여부=1`(Databricks에서 CSV 추출 후 발송툴에 업로드하는 방식)일 때, dedup(같은 날 다른 캠페인 제외 등)을 CSV 추출 쿼리에 넣으면 안 된다 — 아무 효과가 없다.**

- **CSV 추출 시점**엔 아직 해당 plan이 실제로 발송되기 전이라, `account.user_crm_send_log`에 다른 캠페인의 발송 이력이 있어도 이 시점 기준 NOT EXISTS 체크는 무의미하다(추출 시점≠발송 시점이라 발송 시점에 존재할 로그를 미리 걸러낼 수 없음).
- **CSV를 발송툴에 업로드하면, 업로드된 user_id 목록이 `account.userid_sixth` 테이블에 `plan_id`별로 저장**되고, 발송툴은 자동으로 아래 형태의 "참조 쿼리"를 이 plan에 붙인다 (발송 시점에 실행됨):

```sql
SELECT DISTINCT ua.user_id AS id
FROM uts.user_attributes ua
INNER JOIN account.userid_sixth AS us
    ON ua.user_id = us.user_id
    AND us.plan_id = <이 plan의 실제 planID>
WHERE ua.mkt_agree = 1 AND (ua.mkt_agree_info = 1 OR ua.mkt_agree_info IS NULL)
  AND (ua.is_delete = 0 OR ua.is_delete IS NULL)
  AND (ua.is_blocked = 0 OR ua.is_blocked IS NULL)
  AND (DATE(ua.update_time_batch) = CURDATE() OR ua.update_time_batch IS NULL)
```

- **dedup이 필요하면 이 참조 쿼리(자동 생성된 기본형)를 수정해서 `NOT EXISTS (... log.plan_id = <제외할 planID>)`를 추가**해야 한다 — 이 쿼리가 실제 발송 시점에 실행되므로, 그 시점엔 먼저 나간 캠페인의 로그가 이미 쌓여 있어 정상적으로 제외된다.
- 즉 CSV 업로드 케이스는 **쿼리가 두 개로 나뉜다**: (1) Databricks 추출 쿼리 = 순수 대상자 조건만(dedup 없이), (2) 발송툴 참조 쿼리(MySQL) = `userid_sixth` 조인 + mkt_agree 등 기본 조건 + **dedup은 여기에 추가**. 발송툴 직접 등록(`csv 업로드 여부=0`) 케이스는 이런 구분 없이 쿼리 하나에 dedup을 바로 넣으면 된다.
- **테스터 id도 참조 쿼리(2) 쪽에 `UNION SELECT`로 넣어야 한다.** 참조 쿼리 WHERE절에 `mkt_agree=1` 조건이 있어서, CSV(1)에 테스터가 포함돼 있어도 테스터가 마수동을 안 했으면 참조 쿼리 단계에서 걸러질 수 있다 — CSV 쪽 UNION만으로는 최종 발송 보장이 안 됨.
- **참조 쿼리는 `update_time_batch` 조건 줄까지 발송툴이 CSV 업로드 시 자동 생성한다** (plan_id도 자동으로 채워짐) — draft로 줄 때 이 부분을 다시 안 써도 되고, planID도 미리 알 필요 없다. **추가로 필요한 두 부분만 주면 됨**: (1) WHERE절 마지막(update_time_batch) 뒤에 `AND NOT EXISTS (...)` dedup 절, (2) SELECT 문 전체 뒤에 붙는 테스터 `UNION SELECT` 줄들.
- (2026-08-07, 현대캐피탈 id161 자담대 draft 중 확인 — 같은 날 먼저 나가는 SBI id162(planID 8314)를 제외해야 하는데, 161이 CSV 업로드 방식이라 이 구분이 필요했음)

## uts.user_attributes 컬럼 개명 (DAS-3646, 2026-08-12 라이브 적용)

`C:\Users\finda\Downloads\DAS-3646_DDL_v1.0_라이브기준_20260812.sql` 기준 — **2026-08-12부로 이미 라이브 적용된 개명**. 이 날짜 이후 작성하는 모든 신규 쿼리는 새 컬럼명을 써야 한다. 라이브러리 CSV(59+건, id≤146대)의 과거 쿼리들은 옛 컬럼명 그대로 남아있고 소급 변경하지 않는다 — 과거 쿼리를 템플릿으로 복사할 때 컬럼명을 새 이름으로 갈아끼워야 함.

**Databricks/발송툴(MySQL 등록) 양쪽 다 적용됨 (2026-08-25 사용자 확인).** 한때 "발송툴 MySQL 쪽은 별도 환경이라 개명이 반영 안 됐을 수 있다"고 잘못 추측한 적 있었는데(id153이 8/25에 옛 컬럼명으로 문제없이 등록됐던 걸 근거로 삼음), 사용자가 직접 "발송툴 등록 쿼리도 새 컬럼명으로 반영됐다"고 정정함. 즉 id153의 옛 컬럼명 사용은 그 자체가 놓친 부분이었던 것으로 보임 — 엔진(Databricks vs MySQL 등록)과 무관하게 8/12 이후 작성하는 모든 신규 쿼리는 새 컬럼명을 써야 한다.

**이 프로젝트에서 자주 쓰는 컬럼 매핑(구 → 신):**
| 구 컬럼명 | 신 컬럼명 | 비고 |
|---|---|---|
| `recent_appl_date` | `loan_last_application_date` | 한도조회일 |
| `recent_contract_date` | `loan_last_contract_date` | 약정(실행)일 |
| `credit_score` | `kcb_credit_score` | 신용점수 |
| `income_type` | `user_income_type` | 직업/소득유형(`PRIVATEBUSINESS` 등 enum값은 유지) |
| `is_own_car` | `user_own_car_yn` | 자동차 보유여부 |
| `houseown_type` | `user_houseown_type` | 자가 소유여부(`'자가'` 등) |
| `age` | `user_age` | 나이 |
| `gender` | `user_gender` | 성별 |
| `last_comp_loanapplication_date` | `debt_last_competitor_application_date` | 타사 한도조회일 |
| `company_enter_month` | `user_company_enter_month` | 재직 시작월 |
| `yearly_income` | `user_yearly_income` | 연소득 |

전체 개명 82건 목록은 원본 DDL 파일 참조. 신규 컬럼 2건(`dsr_regulation_grade`, `dsr_stressed_regulation_grade`) 추가됨.

**삭제된 컬럼(39건) 중 주의할 것: `is_apt` 컬럼 자체가 삭제됨.** 이 프로젝트는 애초에 이 컬럼을 쓰지 않고 `fcsdb.la_application_houseinput.house_type = 'APT'` 조인으로 아파트 여부를 판단해왔으므로 영향 없음. 그 외 `company_name`, `is_mydata_incomplete` 등도 삭제 — 이 프로젝트 쿼리에서 쓴 적 없음.

## 사업자 카드 보유 여부 (2026-08-25 확인, 신규 광고주 draft 중)

- **사업자 카드 보유**: `lms.kcb_biz_total_credit_info.card_open_cnt > 0`, 유저 식별 컬럼은 `user_id`.
- **블로커: 이 테이블을 Databricks 환경에서 직접 조회할 권한이 없어, `uts.user_attributes`와의 실제 조인 키를 검증하지 못한 상태 (2026-08-25 사용자 확인).** `user_id` 컬럼명은 동일하지만 값 체계(내부 user_id와 1:1인지)가 확인 전이므로, 권한 신청 후 검증 필요. 그 전까지 이 조건이 들어간 쿼리는 draft일 뿐 실행 검증 안 됨을 명시할 것.

## 신용점수 일별 변동 히스토리 (2026-08-31 확인, OK저축은행 성실상환 draft 중)

- **`lms.kcb_user_score_history`**: 유저별 신용점수 변동 로그. 컬럼 `user_id`, `insert_time`(변동 기록 시각), `credit_score`(변동 후 점수), `pre_credit_score`(변동 전 점수).
- 특정 시점 기준 "가장 최근 변동"을 구하려면 `user_id`별 `MAX(insert_time)`으로 최신 행을 잡아야 함(서브쿼리 또는 `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY insert_time DESC)`).
- **점수 컬럼이 문자열일 수 있어 비교 시 `CAST(... AS UNSIGNED)`(MySQL) / `CAST(... AS INT)`(Databricks) 필요** — 사용자가 공유한 참고 쿼리에서 `CAST(ush.credit_score AS UNSIGNED) <= CAST(ush.pre_credit_score AS UNSIGNED)`(유지/하락 판별) 형태로 씀. "상승"은 반대 부등호(`>`).
- `uts.user_attributes`의 `kcb_last_credit_score_diff`/`kcb_credit_score_diff_date`는 **1회성 전일 대비 변동값**만 제공해서 "최근 N개월간 상승 추세"를 못 담는 한계가 있었는데, 이 히스토리 테이블로 특정 기간 내 변동 이력을 제대로 조회 가능.
- 참고로 사용자가 공유한 쿼리 스니펫에는 이 외에도 `debt_loan_cnt >= 1`(기존 채무 보유), `loan_application_7d_cnt = 0`/`loan_contract_3m_cnt = 0`(최근 활동 없음), `loan_last_denied_date`(최근 거절 이력, 90일 밖이거나 NULL) 조건이 함께 쓰였음 — 다른 "저활동/기존채무자" 타겟팅에도 참고할 만한 조합.

## "주택보유 + N개월 이내 한도조회" 조합 시 정확한 join 구조 (2026-09-01 검증 완료, 현대캐피탈 id176 draft 중)

**"핀다 내 대출한도 조회 N개월 이내 + 주택보유"류 조건은, "최근성"을 `uts.user_attributes.loan_last_application_date`(구 `recent_appl_date`) 컬럼으로 판단하면 안 된다.** 이 컬럼은 4~6개월 캡이 있어서([[다른 섹션의 캡 설명 참고]]) N=6개월처럼 캡에 걸치는 윈도우에서 실측치를 크게 밑돈다(실제 검증: 12만이어야 할 게 5.5만으로 나옴).

**올바른 방법**: 두 조건을 `fcsdb.la_application` 원본 로그 기준으로 **독립적인 EXISTS**로 각각 확인한다 — "자가 소유가 찍힌 신청 건이 (시점 무관) 존재하는가"와 "최근 N개월 이내 신청 건이 (주택정보 무관) 존재하는가"를 따로 본다. 같은 신청 건에서 두 조건이 동시에 나올 필요는 없다(그렇게 좁히면 8.3만으로, 실측 12만보다 적게 나와 광고주 의도와 다름 — 사용자가 "이용 이력 중 한번이라도 자가로 신청한 적 있고 최근에도 조회했으면"이라고 명시적으로 컨펌함, 2026-09-01).

```sql
AND EXISTS (
    SELECT 1
    FROM fcsdb.la_application la
    INNER JOIN fcsdb.la_application_userinput lu
        ON lu.application_id = la.id
       AND lu.houseown_type = '자가'
    WHERE la.user_id = ua.user_id
)
AND EXISTS (
    SELECT 1
    FROM fcsdb.la_application la2
    WHERE la2.user_id = ua.user_id
      AND la2.insert_time >= DATE_SUB(CURDATE(), INTERVAL N MONTH)  -- Databricks: add_months(current_date(), -N)
)
```

이 템플릿을 "주택보유 + N개월 한도조회" 조합의 기본형으로 쓸 것. 기존에 쓰던 `ua.loan_last_application_date >= ...` + `la_application ... houseown_type='자가'`(날짜 무관 조인) 조합은 두 조건이 뒤섞여서(자가 신청 시점과 최근 조회 시점이 별개 컬럼) 정확도가 떨어지니 대체한다.

## 주의: update_time_batch / 배치 지연 (카운트가 뜬금없이 0 나올 때 1순위로 의심할 것)

- 라이브러리 쿼리 대부분에 관행적으로 들어있는 `AND (DATE(ua.update_time_batch) = CURDATE() OR ua.update_time_batch IS NULL)` 조건은, 그날 배치가 아직 안 돌았으면(=update_time_batch가 오늘 날짜로 안 갱신됐으면) 전체 결과가 0으로 나올 수 있음.
  - (2026-07-10 확인, 메리츠화재 eligible pool 카운트가 0으로 나와서 원인 추적하다 발견)
  - 카운트/중복 확인 쿼리가 이유 없이 0이나 비정상적으로 적게 나오면, 이 조건부터 빼고 다시 돌려서 배치 지연 때문인지 먼저 확인할 것.
- **위 조건을 WHERE에 아예 안 넣어도, `uts.user_attributes` 테이블 자체의 배치 갱신이 밀려있으면 여전히 0이 나올 수 있음.** 이 테이블의 마지막 실제 갱신일이 (2026-07-24 확인 시점 기준) 6/23이었음 — 즉 "최근 1개월 이내"처럼 오늘 날짜에 바짝 붙은 최신성(recency) 조건(`last_comp_loanapplication_date`, `recent_appl_date` 등 아무 날짜 컬럼이든)을 걸면, 테이블에 그만큼 최신 값 자체가 존재하지 않아 0이 나올 수 있음. 실제로 해당 신호가 없는 게 아니라 배치 지연 때문.
  - (2026-07-24 확인, 신한저축은행 A/B/C 조합 count draft 중 `last_comp_loanapplication_date` 최근 1개월 조건이 0으로 나와서 원인 추적하다 발견)
  - 최신성 조건이 뜬금없이 0이면, `SELECT MAX(해당 날짜 컬럼)` 또는 `SELECT MAX(update_time_batch) FROM uts.user_attributes`로 테이블/컬럼의 실제 최신 값이 언제인지부터 확인할 것. 그 값보다 최근을 요구하는 윈도우는 항상 0이 나옴.
