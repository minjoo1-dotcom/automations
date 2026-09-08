"""
광고주별 최근 발송 쿼리 조회 스크립트 (개인 로컬 실행용)

기능
----
'6월 이후 외부광고 조건 정리.csv'(광고주별 발송조건+쿼리+planID 라이브러리)에서
특정 광고주의 발송 건을 발송일 최신순으로 보여준다.

작업 A(대상자수 확인 쿼리 draft)에서, 새 발송 조건(자연어)을 받았을 때
"이 광고주 최근엔 이런 쿼리를 썼고, 직전 planID는 이거였다"를 빠르게 확인해서
새 쿼리 draft의 템플릿/기준으로 쓰기 위한 용도.

사용 예시
--------
python lookup_advertiser_query.py --advertiser 현대캐피탈
python lookup_advertiser_query.py --advertiser 현대캐피탈 --top 3
python lookup_advertiser_query.py --advertiser 현대캐피탈 --top 1 --full-query
"""

import argparse
import csv
import sys

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = r"C:\Users\finda\Documents\Claude Projects\발송광고 자동화\6월 이후 외부광고 조건 정리.csv"


def load_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main():
    parser = argparse.ArgumentParser(description="광고주별 최근 발송 쿼리/조건/planID 조회")
    parser.add_argument("--advertiser", required=True, help="광고주명 (부분 일치)")
    parser.add_argument("--top", type=int, default=1, help="최근 몇 건까지 보여줄지 (기본 1건, 가장 최근)")
    parser.add_argument("--full-query", action="store_true", help="쿼리 전체를 출력 (기본은 조건/planID만)")
    parser.add_argument("--csv-path", default=CSV_PATH, help="라이브러리 CSV 경로 (기본: 실제 사용 파일)")
    args = parser.parse_args()

    rows = load_rows(args.csv_path)
    matched = [r for r in rows if args.advertiser in r.get("광고주명", "")]
    matched.sort(key=lambda r: r.get("발송일", ""), reverse=True)

    if not matched:
        print(f"'{args.advertiser}' 광고주의 발송 이력을 찾지 못했습니다.")
        return

    print(f"\n'{args.advertiser}' 최근 발송 이력 (총 {len(matched)}건 중 상위 {min(args.top, len(matched))}건):\n")

    for r in matched[: args.top]:
        print(f"- id={r.get('id')} / planID={r.get('planID')} / {r.get('발송일')}")
        print(f"    제목: {r.get('제목')}")
        print(f"    조건: {r.get('발송 조건')}")
        print(f"    대상자수: {r.get('대상자수') or '(미기록)'}")
        print(f"    csv 업로드 여부: {r.get('csv 업로드 여부')}")
        if args.full_query:
            print("    --- 쿼리 ---")
            print(r.get("쿼리"))
        print()

    latest = matched[0]
    print(f"직전 발송건(가장 최근) planID: {latest.get('planID')} ({latest.get('발송일')})")
    print("이 planID를 새 쿼리의 dedup 기준으로 쓸지 확인 후 진행하세요.")


if __name__ == "__main__":
    main()
