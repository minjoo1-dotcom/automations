"""
발송이력 구글시트 조회 스크립트 (개인 로컬 실행용)

기능
----
발송이력 시트에서 특정 광고주의 최근 N일 이내 발송 건을 찾아 보여준다.
작업 B(제외조건 쿼리 draft)에서 "최근 N일 이내 발송 대상자 제외" 조건을 반영할 때,
어떤 발송 건(시트 ID)을 제외 대상으로 삼아야 하는지 확인하는 용도.

주의: 여기서 나오는 "id"는 발송이력 시트 자체의 고유번호이고, 실제 Databricks
세그먼트 쿼리에서 dedup에 쓰는 planID와는 다른 값이다. planID로 변환하려면
별도로 정리해둔 매칭 자료를 참고해야 한다.

사전 준비
--------
check_calendar_overlap.py와 동일한 credentials.json을 사용한다 (google_auth.py가 공용).
Sheets 읽기 스코프가 새로 추가됐으므로, 기존에 token.json이 있었다면 삭제하고
아무 스크립트나 한 번 실행해서 재인증(캘린더+시트 권한 한 번에 동의)해야 한다.

사용 예시
--------
python fetch_send_history.py --advertiser 현대캐피탈 --days 30
python fetch_send_history.py --id 99   (시트 id로 특정 행 전체를 그대로 조회 - 세팅 시 복붙 대신 사용)
"""

import argparse
import datetime as dt
import sys

sys.stdout.reconfigure(encoding="utf-8")

from google_auth import get_service

# 발송이력 시트: https://docs.google.com/spreadsheets/d/19PnkXgbpOJ6a9Y6v_XdibJ3EqdOCgzPFpYrihWiiDec/edit?gid=0
SPREADSHEET_ID = "19PnkXgbpOJ6a9Y6v_XdibJ3EqdOCgzPFpYrihWiiDec"
# 컬럼: id, 광고주명, 신청일시, 신청자(email), 발송일, 시간대, 광고종류, 발송 시간,
#       발송 가능, 제목, 본문, 랜딩, 발송 조건, 테스터 id  (A~N)
RANGE = "A:N"


def fetch_rows(service):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=RANGE)
        .execute()
    )
    return result.get("values", [])


def main():
    parser = argparse.ArgumentParser(description="발송이력 시트에서 광고주별 최근 발송 이력 조회")
    parser.add_argument("--advertiser", help="광고주명 (부분 일치)")
    parser.add_argument("--id", help="시트 id로 특정 행 하나를 정확히 조회 (전체 컬럼 출력)")
    parser.add_argument("--days", type=int, default=30, help="최근 며칠 이내 (기본 30일, --advertiser 조회 시)")
    args = parser.parse_args()

    if not args.advertiser and not args.id:
        print("--advertiser 또는 --id 중 하나는 필요합니다.")
        return

    service = get_service("sheets", "v4")
    rows = fetch_rows(service)

    if not rows:
        print("시트에서 데이터를 못 가져왔습니다.")
        return

    header = rows[0]
    col = {name.strip(): i for i, name in enumerate(header)}

    required = ["id", "광고주명", "발송일", "제목", "발송 조건"]
    missing = [c for c in required if c not in col]
    if missing:
        print(f"시트에서 다음 컬럼을 못 찾았습니다: {missing}")
        print(f"실제 헤더: {header}")
        return

    def cell_of(row, name):
        i = col.get(name)
        if i is None:
            return ""
        return row[i] if len(row) > i else ""

    if args.id:
        for row in rows[1:]:
            if cell_of(row, "id") == args.id:
                print(f"\n시트 id={args.id} 원본 행:\n")
                for name in header:
                    if name.strip():
                        print(f"[{name.strip()}]\n{cell_of(row, name.strip())}\n")
                return
        print(f"시트에서 id={args.id} 행을 찾지 못했습니다.")
        return

    cutoff = dt.date.today() - dt.timedelta(days=args.days)

    print(f"\n광고주 '{args.advertiser}' / 최근 {args.days}일({cutoff} 이후) 발송 이력:\n")

    found = 0
    for row in rows[1:]:
        def cell(name):
            i = col[name]
            return row[i] if len(row) > i else ""

        if args.advertiser not in cell("광고주명"):
            continue

        raw_date = cell("발송일")
        try:
            send_date = dt.datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            continue

        if send_date < cutoff:
            continue

        found += 1
        print(f"- id={cell('id')} / {send_date} / {cell('제목')}")
        condition = cell("발송 조건")
        if condition:
            print(f"    조건: {condition}")

    if found == 0:
        print("(해당 조건에 맞는 발송 이력 없음)")
    else:
        print(
            f"\n총 {found}건. 주의: 위 id는 발송이력 시트 고유번호이며, "
            "실제 쿼리 시스템의 planID와는 다릅니다. dedup 쿼리에 넣기 전에 "
            "planID 매칭 자료로 한 번 더 확인하세요."
        )


if __name__ == "__main__":
    main()
