"""
광고 부킹 시간 조율 - 캘린더 겹침 체크 스크립트 (개인 로컬 실행용)

기능
----
1. 지정한 날짜(YYYY-MM-DD)의 요일을 기준으로, 같은 달 안에서 동일 요일에 해당하는
   모든 날짜를 찾는다.
2. 그 날짜들에 대해 "CRM 일정 캘린더"와 "광고 부킹 캘린더" 두 곳의 일정을
   모두 가져와서 시간순으로 정리해서 보여준다.
3. (선택) 내가 넣고 싶은 후보 시작/종료 시각을 입력하면, 두 캘린더 일정과
   겹치는지 자동으로 체크해서 알려준다.

사전 준비 (최초 1회)
-------------------
1. https://console.cloud.google.com 에서 프로젝트 생성 (기존 프로젝트 있으면 재사용)
2. "API 및 서비스 > 라이브러리"에서 Google Calendar API 활성화
3. "API 및 서비스 > 사용자 인증 정보"에서 OAuth 클라이언트 ID 생성
   - 애플리케이션 유형: 데스크톱 앱
   - 생성 후 JSON 다운로드 -> 이 스크립트와 같은 폴더에 credentials.json 으로 저장
4. 아래 CONFIG의 캘린더 ID를 본인 캘린더로 교체 (CRM_CALENDAR_IDS는 여러 개 등록 가능한 리스트)
   - 캘린더 ID 찾는 법: 구글 캘린더 좌측에서 해당 캘린더 > 점 3개 > 설정 및 공유
     > "캘린더 통합" 항목의 "캘린더 ID" 값 복사 (본인 기본 캘린더면 gmail 주소 자체가 ID)
5. 라이브러리 설치
   pip install google-auth google-auth-oauthlib google-api-python-client tzdata
6. 최초 실행 시 브라우저 인증 창이 뜨고, 이후에는 token.json이 생성되어 자동 재사용됨
   (인증/스코프는 google_auth.py에서 공통 관리 - fetch_send_history.py와 스코프를 공유함.
    스코프가 바뀐 뒤 처음 실행할 때는 기존 token.json을 지우고 재인증해야 함)

사용 예시
--------
python check_calendar_overlap.py --date 2026-07-15
python check_calendar_overlap.py --date 2026-07-15 --candidate 11:30-12:00
"""

import argparse
import datetime as dt
import sys
from calendar import monthrange
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")

from google_auth import get_service

# ===================== CONFIG (본인 환경에 맞게 수정) =====================
CRM_CALENDAR_IDS = [
    "c_d3ae6236502dd5d6198b004fc32b8cd22d83d233d97f0a4914d6889c96d3aaa2@group.calendar.google.com",
    "c_71ece80fc8d5a278bfc670c9ea3d071f56262a905deefb35295f6b7cd7aec845@group.calendar.google.com",
]
BOOKING_CALENDAR_ID = "c_baeebca59a9ec7724f1e23b697ddc22fe46b5b7d59e18b04d727bd3c4772f69b@group.calendar.google.com"
TIMEZONE = "Asia/Seoul"
# ==========================================================================


def same_weekday_dates_in_month(target_date: dt.date) -> list[dt.date]:
    """target_date와 같은 달, 같은 요일에 해당하는 모든 날짜 리스트."""
    year, month = target_date.year, target_date.month
    weekday = target_date.weekday()
    _, last_day = monthrange(year, month)

    dates = []
    for day in range(1, last_day + 1):
        d = dt.date(year, month, day)
        if d.weekday() == weekday:
            dates.append(d)
    return dates


def recent_weekday_dates(target_date: dt.date, weeks_back: int) -> list[dt.date]:
    """target_date 기준 과거로 weeks_back주 동안의 동일 요일 날짜 리스트 (오래된 순).

    타겟 달이 아직 비어있는 미래 달이라도(=예약이 안 잡혀서 겹침 체크가 무의미할 때),
    최근 몇 주의 반복 패턴(주로 CRM 정기 발송)을 참고할 수 있게 달 경계 없이 조회한다.
    """
    dates = [target_date - dt.timedelta(weeks=i) for i in range(weeks_back, 0, -1)]
    return [d for d in dates if d < target_date]


def fetch_events(service, calendar_id: str, day: dt.date, tz: ZoneInfo) -> list[dict]:
    """해당 날짜 하루(00:00~24:00) 동안의 이벤트 목록 조회."""
    time_min = dt.datetime.combine(day, dt.time.min, tzinfo=tz).isoformat()
    time_max = dt.datetime.combine(day, dt.time.max, tzinfo=tz).isoformat()

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return result.get("items", [])


def format_event_time(event: dict, tz: ZoneInfo) -> str:
    start = event["start"].get("dateTime", event["start"].get("date"))
    end = event["end"].get("dateTime", event["end"].get("date"))
    if "T" not in start:  # 종일 일정
        return "종일"
    start_t = dt.datetime.fromisoformat(start).astimezone(tz).strftime("%H:%M")
    end_t = dt.datetime.fromisoformat(end).astimezone(tz).strftime("%H:%M")
    return f"{start_t}~{end_t}"


def parse_candidate(candidate_str: str, day: dt.date, tz: ZoneInfo):
    """'11:30-12:00' 형식 문자열을 그 날짜 기준 datetime 튜플로 변환."""
    start_s, end_s = candidate_str.split("-")
    start_h, start_m = map(int, start_s.split(":"))
    end_h, end_m = map(int, end_s.split(":"))
    start_dt = dt.datetime.combine(day, dt.time(start_h, start_m), tzinfo=tz)
    end_dt = dt.datetime.combine(day, dt.time(end_h, end_m), tzinfo=tz)
    return start_dt, end_dt


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def main():
    parser = argparse.ArgumentParser(description="CRM/광고 부킹 캘린더 겹침 체크")
    parser.add_argument("--date", required=True, help="확인할 날짜 (YYYY-MM-DD)")
    parser.add_argument("--candidate", help="후보 시간대, 예: 11:30-12:00 (선택)")
    parser.add_argument(
        "--lookback-weeks", type=int, default=8,
        help="과거 몇 주치 동일 요일 CRM 패턴을 참고로 보여줄지 (기본 8주, 0이면 생략). "
             "타겟 달이 아직 비어있는 먼 미래 달일 때 특히 유용함",
    )
    args = parser.parse_args()

    tz = ZoneInfo(TIMEZONE)
    target_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][target_date.weekday()]

    print(f"\n대상 날짜: {target_date} ({weekday_kr}요일)")

    service = get_service("calendar", "v3")

    if args.lookback_weeks > 0:
        lookback_dates = recent_weekday_dates(target_date, args.lookback_weeks)
        if lookback_dates:
            print(f"--- 참고용: 최근 {args.lookback_weeks}주 동일 요일({weekday_kr}) CRM 반복 패턴 (타겟 날짜 자체 아님) ---")
            for day in lookback_dates:
                crm_events = []
                for crm_calendar_id in CRM_CALENDAR_IDS:
                    crm_events.extend(fetch_events(service, crm_calendar_id, day, tz))
                crm_events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")))

                if not crm_events:
                    print(f"  {day}: [CRM] 일정 없음")
                for e in crm_events:
                    time_str = format_event_time(e, tz)
                    print(f"  {day}: [CRM] {time_str}  {e.get('summary', '(제목 없음)')}")
            print()

    dates = same_weekday_dates_in_month(target_date)
    print(f"이번 달 동일 요일({weekday_kr}) 날짜: {[str(d) for d in dates]}\n")

    candidate_range = None
    if args.candidate:
        candidate_range = parse_candidate(args.candidate, target_date, tz)
        print(f"후보 시간: {args.candidate} ({target_date})\n")

    any_conflict = False

    for day in dates:
        crm_events = []
        for crm_calendar_id in CRM_CALENDAR_IDS:
            crm_events.extend(fetch_events(service, crm_calendar_id, day, tz))
        crm_events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")))
        booking_events = fetch_events(service, BOOKING_CALENDAR_ID, day, tz)

        print(f"--- {day} ({weekday_kr}) ---")

        if not crm_events:
            print("  [CRM] 일정 없음")
        for e in crm_events:
            time_str = format_event_time(e, tz)
            print(f"  [CRM] {time_str}  {e.get('summary', '(제목 없음)')}")

        if not booking_events:
            print("  [광고부킹] 일정 없음")
        for e in booking_events:
            time_str = format_event_time(e, tz)
            print(f"  [광고부킹] {time_str}  {e.get('summary', '(제목 없음)')}")

        # 후보 시간이 target_date 당일인 경우에만 실제 겹침 체크
        if candidate_range and day == target_date:
            cand_start, cand_end = candidate_range
            for e in crm_events + booking_events:
                start = e["start"].get("dateTime")
                end = e["end"].get("dateTime")
                if not start or not end:
                    continue
                e_start = dt.datetime.fromisoformat(start).astimezone(tz)
                e_end = dt.datetime.fromisoformat(end).astimezone(tz)
                if overlaps(cand_start, cand_end, e_start, e_end):
                    any_conflict = True
                    print(f"  >>> 겹침! 후보 시간과 '{e.get('summary')}' ({format_event_time(e, tz)}) 충돌")

        print()

    if candidate_range:
        if any_conflict:
            print("결과: 후보 시간이 기존 일정과 겹칩니다. 다른 시간을 검토하세요.")
        else:
            print("결과: 후보 시간에 겹치는 일정이 없습니다.")


if __name__ == "__main__":
    main()
