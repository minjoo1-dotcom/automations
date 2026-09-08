# 쿼리 작성 규칙 상세

## 1. 엔진/문법은 용도에 따라 두 갈래

| 용도 | 엔진 | 날짜함수 | 캐스팅 |
|---|---|---|---|
| CSV 추출(대상자 파일 추출, 모수 count-check 포함) | **Databricks** (Spark SQL) | `current_date()`, `add_months(current_date(), -N)`, `date_sub(current_date(), N)` | `CAST(x AS STRING)` |
| 발송툴에 쿼리 그대로 등록(직접등록) | **MySQL** | `CURDATE()`, `DATE_SUB(CURDATE(), INTERVAL N MONTH/DAY)` | `CAST(x AS CHAR)` |

- `WITH`/`UNION`/`EXISTS`/`ROW_NUMBER() OVER(...)`/`LIMIT`는 양쪽 동일.
- **발송툴 직접등록 쿼리는 끝에 세미콜론(`;`) 금지** — 붙이면 등록 에러.
- 어느 쪽인지는 사용자의 라이브러리에 "csv 업로드 여부" 같은 플래그가 있을 수 있음(1=CSV추출/Databricks, 0=직접등록/MySQL). 광고주/채널로 추론 불가, 건별로 다름 — 헷갈리면 사용자에게 확인.
- **모수 확인(count-check) 쿼리는 예외 없이 항상 Databricks 문법으로 통일할 것.** 중간에 MySQL 문법 하나라도 섞이면 다른 데이터 소스(발송툴쪽 MySQL/StarRocks 환경)를 참조하게 돼서 완전히 다른 모수가 나올 수 있다 — 실제 사고: 같은 조건인데 문법을 섞어서 실제 모수(20.5만)의 8분의 1(2.5만)로 잘못 보고된 적이 있음.

## 2. CSV 업로드 방식일 때 dedup은 "발송툴 참조 쿼리"에 넣어야 한다

CSV 업로드 방식일 때 Databricks 추출 쿼리에 dedup(NOT EXISTS 등)을 넣어도 무의미하다 — 추출 시점엔 아직 발송 전이라 로그가 없다. 실제 흐름:
1. Databricks에서 dedup 없이 순수 대상자만 뽑아 CSV로 업로드
2. 업로드된 user_id가 `account.userid_sixth`에 `plan_id`별로 저장됨
3. 발송툴이 자동 생성하는 **참조 쿼리**(`INNER JOIN account.userid_sixth ... AND plan_id=<이 건의 planID>` + mkt_agree 등 기본조건, MySQL)가 실제 발송 시점에 실행됨 — **dedup은 이 참조 쿼리 쪽에 `NOT EXISTS (... plan_id=<제외할 planID>)`로 추가해야** 발송 시점 기준으로 정상 작동한다.
4. **테스터 id도 CSV가 아니라 이 참조 쿼리 쪽에 `UNION SELECT`로 넣어야 한다** — 참조 쿼리 WHERE절에 mkt_agree=1 조건이 있어서, CSV에 테스터를 넣어도 마수동 안 했으면 걸러질 수 있음.
5. dedup 대상 planID가 아직 발송 전이라 로그(`account.user_crm_send_log`)가 없는 상태라면, 로그 대신 **`account.userid_sixth`에 해당 `plan_id`의 user_id가 있는지**로 판별한다.

## 3. ⚠️ fcsdb 테이블 발송툴(MySQL) vs Databricks 데이터 불일치

완전히 동일한 로직의 쿼리(`fcsdb.la_application` 조인 포함)를 Databricks에서 돌리면 12만, 발송툴 MySQL 환경에서 돌리면 5.5만이 나온 실제 사례가 있었다. **문법 차이로는 설명 안 되는 규모 차이 — 발송툴이 참조하는 fcsdb 테이블 사본이 Databricks와 복제 지연/불완전 상태일 가능성이 높다.** `fcsdb.la_application` 등 원본 로그 테이블을 조인하는 조건을 발송툴 직접등록(MySQL)으로 쓸 때는 **반드시 Databricks count-check 결과와 대조**하고, 크게 다르면 **CSV 업로드 방식으로 우회**할 것.

## 4. "주택보유 + N개월 이내 한도조회" 조합 — 정확한 join 구조

`uts.user_attributes`의 최근 한도조회일 컬럼(신규명 `loan_last_application_date`)은 **4~6개월치만 채워지는 캡이 있어서**, N=6개월처럼 캡에 걸치는 조건에 이 컬럼을 쓰면 실제보다 훨씬 적게 나온다(실측: 12만이어야 할 게 5.5만으로 나옴). 올바른 방법은 `fcsdb.la_application` 원본 로그 기준으로 **두 조건을 독립적인 EXISTS로 각각** 확인하는 것 — "자가 소유가 찍힌 신청 건이 (시점 무관) 존재하는가"와 "최근 N개월 이내 신청 건이 (주택정보 무관) 존재하는가"를 따로 본다(같은 신청 건일 필요는 없다는 게 실사용 확인된 정의):

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

"대출 미실행" 조건이 같이 필요하면 `loan_last_contract_date IS NULL OR loan_last_contract_date < ...` (윈도우가 4~6개월 이내면 이 컬럼 그대로 써도 됨 — 캡 문제는 "장기 윈도우"에서만 발생).

## 5. uts.user_attributes 컬럼 개명 (2026-08-12 라이브 적용)

자주 쓰는 것:

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
| `company_enter_month` | `user_company_enter_month` |
| `yearly_income` | `user_yearly_income` |

과거에 작성된 쿼리(개명 이전)를 템플릿으로 재사용할 때는 반드시 신규 컬럼명으로 치환할 것. `is_apt` 컬럼은 이 개명 작업으로 삭제됨(아파트 여부는 `fcsdb.la_application_houseinput.house_type='APT'` 조인으로 판단).

## 6. 그 외 항상 지켜야 하는 규칙

- **마수동(`mkt_agree=1 AND (mkt_agree_info=1 OR mkt_agree_info IS NULL)`)은 채널 무관 항상 포함.** 디바이스 토큰 조인(`account.user3`+`account.user_device`, `noti_token IS NOT NULL`)은 **App Push에서만** 필요 — LMS는 불필요. 이 둘을 같은 이름("마수동 조인")으로 부르지 말 것, 서로 다른 개념.
- **dedup(이전 발송자 제외)은 명시적으로 요청한 경우에만 넣는다.** 아무 말 없으면 안 넣음.
- **하루 1건 제한(global 최우선)**: 같은 날 다른 캠페인이 이미 부킹돼 있으면, 발송조건 텍스트에 명시가 없어도 그 대상자는 무조건 제외해야 한다.
- **날짜 범위 "N일부터 M일까지"는 `< M+1일`로 변환** (`< M일`로 쓰면 M일 당일이 통째로 빠지는 off-by-one 버그).
- **최종 확정 draft 쿼리엔 `--` 주석 금지**, 순수 SQL만.
- **대상자수를 사람에게 전달할 때는 절사한 "만" 단위로** (16548 → 1.6만, 반올림 아니라 절사).
- **신용점수 NULL은 저신용이 아니라 KCB 연동 만료**(6개월 이상 앱 미접속 시 리셋)다. 하한 조건(`kcb_credit_score >= N`) 걸 때 별도 지시 없으면 `(kcb_credit_score >= N OR kcb_credit_score IS NULL)`로 NULL을 통과시키는 게 기본값.
- **신용점수 "하위 50%" 같은 상대적 표현은 핀다 유저 기준 percentile로 판단하면 안 됨** — 핀다 유저 자체가 중저신용 비중이 높아 전 국민 기준보다 훨씬 빡빡해짐. 광고주에게 구체적 컷오프를 되물을 것.
- **한도조회=`condition_approved`, 실행(약정)=`contract_approved`만** (더 넓은 상태 세트 `contract_requested/applied/failed/approved/rejected/retracted`는 "계약 단계 진입 시도"라는 별개 목적 — "미실행" 판단에 잘못 쓰면 실패/거절/철회까지 "실행됨"으로 묶여 모수가 부당히 줄어듦).
- **`update_time_batch` 배치 지연**: 카운트가 뜬금없이 0이면 1순위로 의심. `AND (DATE(update_time_batch)=CURDATE() OR update_time_batch IS NULL)` 조건을 빼고 재확인, 그래도 0이면 `uts.user_attributes` 테이블 자체 배치 지연 의심(`SELECT MAX(update_time_batch)`로 확인).

## 7. 신규 발견 테이블

- **`lms.kcb_user_score_history`**: 유저별 신용점수 변동 로그. 컬럼 `user_id`/`insert_time`/`credit_score`/`pre_credit_score`. 특정 시점 기준 "가장 최근 변동"은 `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY insert_time DESC)`로 구함. 점수 비교 시 `CAST(... AS UNSIGNED)`(MySQL)/`CAST(... AS INT)`(Databricks) 필요.
- **`lms.kcb_biz_total_credit_info`**: 사업자 카드 보유 여부 = `card_open_cnt > 0`, 키는 `user_id`. 이 테이블과 `uts.user_attributes` 간 실제 조인 정합성은 검증 안 된 상태일 수 있으니, 사용해본 적 없다면 먼저 확인할 것.

## 8. 자주 쓰는 쿼리 패턴 키워드

- 자동차 보유(자담대): `user_own_car_yn = 1`
- 주택 자가 보유: `fcsdb.la_application_userinput.houseown_type = '자가'` (조인키 `application_id`)
- 아파트 보유: `fcsdb.la_application_houseinput.house_type = 'APT'` (조인키 `application_id`)
- 사업자: `user_income_type = 'PRIVATEBUSINESS'`
- 신용대출 보유 중: `lms.lms_loan_account_info.account_type IN ('3100')` + `exp_date > '0'` + `CAST(exp_date AS STRING/CHAR) > date_format(current_date(),'yyyyMMdd')`(만기 미도래)
- 타사 한도조회: `debt_last_competitor_application_date`
- "가승인 & 미실행" 시리즈(자담대/주담대/승인후미실행): `fcsdb.la_loanapply`+`la_application`+`la_product` 3-CTE 패턴(승인군 CTE, 신청군 제외 CTE, 차집합으로 최종 타겟 산출). 세부 조건(상품 카테고리 `minor_category`, 은행 코드 `bank_id`, 상품 id 목록 등)은 광고주마다 다르므로 과거 쿼리를 템플릿으로 확인할 것.

## 9. 겹치는 조건 간 "부분집합" 함정

두 발송 조건의 날짜 윈도우가 한쪽이 다른 쪽을 완전히 포함하는 관계이면(예: "3개월 이내"와 "6개월 이내", 나머지 조건 동일), 좁은 쪽 조건의 대상자는 넓은 쪽 조건의 대상자에 거의 다 포함된다. 이럴 때 "먼저 나간 발송분 전체를 제외"하면 나중 발송의 신규 인원이 0에 가깝게 나올 수 있다 — 버그가 아니라 조건 구조상 당연한 결과다. 실제로 이런 상황을 만나면:
- 두 조건의 관계(부분집합인지)를 먼저 확인하고
- "전체 제외"가 맞는지, 아니면 실제 발송 로그(`account.user_crm_send_log`) 기준으로 이미 발송된 사람만 빼는 게 맞는지(둘은 다른 결과를 낳는다 — 먼저 나가는 쪽이 전체 대상자를 다 보내는 게 아니라 LIMIT으로 일부만 보내면, 로그 기준 dedup에는 여유가 생긴다) 사용자와 확인한다.
