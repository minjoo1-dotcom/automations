---
name: ad-query-drafting
description: Draft targeting SQL queries for Finda's 외부광고(external ad) sends (LMS/App Push) to advertisers like 현대캐피탈, OK저축은행, SBI저축은행, 메리츠화재. Use this whenever the user asks to draft a 발송 대상자 쿼리, check 모수(population count), reconcile dedup between two sends, or register a confirmed query with a planID. Also use when the user mentions uts.user_attributes, fcsdb.la_application, count-check, 마수동, or asks about Databricks vs 발송툴(MySQL) query dialect for ad targeting. This is a network-isolated (망분리) workflow — Claude only drafts queries, never executes them.
---

# 발송광고 타겟팅 쿼리 작성

핀다가 제휴 광고주(현대캐피탈, OK저축은행, SBI저축은행, 메리츠화재 등)에게 보내는 외부광고(LMS/App Push)의 발송 대상자 쿼리를 작성한다. **망분리 환경 제약으로 실제 쿼리 실행/발송툴 등록은 항상 사람이 직접 수동으로 한다 — 이 스킬은 draft(쿼리 초안) 작성까지만 한다.**

## 처리 순서

1. 광고주명 + 자연어 발송조건을 받는다.
2. `references/advertiser-conditions.md`에서 해당 광고주의 최근 발송 패턴(조건 문구, 반복 시리즈, 최근 dedup 관행)을 확인한다 — 이 파일은 자연어 요약이라 실제 쿼리 원문은 없다. 실제 쿼리 원문/과거 planID는 사용자의 로컬 라이브러리 CSV에 있으니(이 스킬엔 포함 안 됨), 있으면 사용자에게 보여달라고 하거나 그쪽 조회 스크립트를 함께 쓴다.
3. dedup 필요 여부는 **사용자가 명시적으로 요청한 경우에만** 넣는다. 아무 말 없으면 안 넣는다.
4. `references/query-rules.md`를 참고해 조건을 SQL로 옮긴다 — 엔진 방언, 컬럼명, 조인 구조 등 이 문서가 다룬다.
5. draft를 제시하고, 모수 확인이 필요하면 count-check 쿼리(항상 Databricks 문법)를 같이 준다.
6. 컨펌 후 planID가 나오면, 사용자의 라이브러리 관리 스크립트(`append_to_library.py` 등, 로컬에 있음)로 기록하도록 안내한다 — 이 스킬 자체에는 그 스크립트가 없다.

## 핵심 원칙 (자세한 근거/사고사례는 `references/query-rules.md` 참고)

- **엔진은 용도에 따라 두 갈래**: CSV 추출/모수 count-check = Databricks 문법, 발송툴 직접등록 = MySQL 문법. **모수 확인은 예외 없이 항상 Databricks로 통일** — 안 그러면 다른 데이터 소스를 조회해 모수가 몇 배씩 어긋날 수 있다.
- **fcsdb 테이블(`la_application` 등)은 발송툴 MySQL과 Databricks 간 데이터가 다를 수 있다.** 이런 조건을 발송툴 직접등록으로 쓸 때는 Databricks count-check와 대조하고, 크게 다르면 CSV 업로드로 우회한다.
- **`uts.user_attributes` 컬럼은 2026-08-12에 대거 개명됐다(DAS-3646)** — 새 쿼리는 반드시 신규 컬럼명을 쓴다. 매핑표는 `references/query-rules.md`.
- **마수동(mkt_agree)은 채널 무관 항상 포함, 디바이스 토큰 조인은 App Push에서만.** 둘을 같은 개념으로 부르지 않는다.
- **날짜 범위 "N일부터 M일까지"는 `< M+1일`로 변환**(경계일 누락 방지).
- **하루 1건 제한**: 같은 날 다른 캠페인이 이미 부킹돼 있으면, 조건 텍스트에 명시가 없어도 그 대상자는 무조건 제외해야 한다(전사 규칙, global 최우선).
- **최종 확정 쿼리엔 주석(`--`) 금지**, 순수 SQL만.
- **대상자수를 사람에게 전달할 때는 절사한 "만" 단위로** (16548 → 1.6만, 반올림 아니라 절사).
- **신용점수 NULL은 저신용이 아니라 KCB 연동 만료** — 하한 조건 걸 때 별도 지시 없으면 `OR credit_score IS NULL`로 통과시키는 게 기본.
- **"한도조회"=`condition_approved`, "실행/약정"=`contract_approved`만**(더 넓은 상태 세트를 "미실행" 판단에 쓰면 안 됨).
- **모수가 뜬금없이 0이면 `update_time_batch` 배치 지연을 1순위로 의심**한다.

## 언제 사용자에게 되물어야 하는가

- dedup 대상 planID가 애매하거나, 요청한 "N일 발송분 제외"가 어느 planID인지 특정이 안 될 때
- 처음 보는 스키마/컬럼을 추측해야 할 때 (모르면 추측하지 말고 사용자에게 확인 — 잘못된 enum/컬럼 값 하나가 모수를 크게 왜곡시킬 수 있다)
- "신용점수 하위 50%" 같은 상대적 표현이 올 때 (핀다 유저 기준 percentile로 판단하면 안 됨, 절대 컷오프를 되물을 것)

## 참고 자료

- `references/query-rules.md` — 엔진 방언, 컬럼 개명표, 조인 패턴, 사고사례 상세 (이 파일이 이 스킬의 핵심 지식)
- `references/advertiser-conditions.md` — 광고주별 자주 나오는 자연어 조건 요약 (실제 쿼리 원문 없음, 패턴 파악용)
