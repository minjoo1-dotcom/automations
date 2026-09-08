"""
발송 쿼리 라이브러리(CSV)에 새로 컨펌된 draft를 즉시 추가 (개인 로컬 실행용)

기능
----
draft 쿼리가 확정되는 시점(망분리에서 아직 실행 전이라 planID는 모름)에
'6월 이후 외부광고 조건 정리.csv'에 새 행을 바로 추가한다.
planID는 비워두고, 나중에 실제 실행 후 fill_planid.py로 채워넣는다.

사용 예시
--------
1. append_row.json 같은 파일을 만든다 (컬럼명은 CSV 헤더와 동일해야 함):
   {
     "광고주명": "OK저축은행",
     "광고종류": "LMS",
     "발송 조건": "연령 30-64, 신용점수 440 이상, 주택보유+아파트보유, 최근 4개월 한도조회 미실행",
     "대상자수": "13만",
     "쿼리": "SELECT ...",
     "csv 업로드 여부": "0"
   }
   (id, 발송일, 발송 시간, 제목, 본문, planID, 대상자수는 모르면 안 넣어도 됨 - 빈 값으로 채워짐)

   csv 업로드 여부를 JSON에 아예 넣지 않으면, 같은 광고주의 가장 최근(발송일 기준) 행 값을
   그대로 이어받는다 (예: 직전 건이 타임아웃 나서 1이었으면 이번 건도 자동으로 1).
   과거와 다르게 처리하고 싶으면 JSON에 명시적으로 값을 넣어서 덮어쓴다.

2. python append_to_library.py --json append_row.json
"""

import argparse
import csv
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = r"C:\Users\finda\Documents\Claude Projects\발송광고 자동화\6월 이후 외부광고 조건 정리.csv"
COLUMNS = [
    "id", "광고주명", "발송일", "광고종류", "발송 시간",
    "제목", "본문", "발송 조건", "대상자수", "planID", "쿼리", "csv 업로드 여부",
]


def find_latest_csv_upload_flag(csv_path, advertiser):
    """같은 광고주의 가장 최근(발송일 기준) 행에서 csv 업로드 여부 값을 가져온다. 없으면 None."""
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    matched = [r for r in rows if r.get("광고주명", "") == advertiser]
    if not matched:
        return None

    matched.sort(key=lambda r: r.get("발송일", ""), reverse=True)
    return matched[0].get("csv 업로드 여부", "")


def main():
    parser = argparse.ArgumentParser(description="라이브러리 CSV에 새 확정 draft 행 추가")
    parser.add_argument("--json", required=True, help="추가할 행 데이터가 담긴 JSON 파일 경로")
    parser.add_argument("--csv-path", default=CSV_PATH, help="라이브러리 CSV 경로 (기본: 실제 사용 파일)")
    args = parser.parse_args()

    with open(args.json, encoding="utf-8") as f:
        data = json.load(f)

    unknown = [k for k in data.keys() if k not in COLUMNS]
    if unknown:
        print(f"경고: CSV에 없는 컬럼은 무시됩니다: {unknown}")

    row = {col: data.get(col, "") for col in COLUMNS}

    if "csv 업로드 여부" not in data and row["광고주명"]:
        latest_flag = find_latest_csv_upload_flag(args.csv_path, row["광고주명"])
        if latest_flag is not None:
            row["csv 업로드 여부"] = latest_flag
            print(f"csv 업로드 여부를 명시하지 않아 '{row['광고주명']}' 최근 이력 기준으로 자동 설정: {latest_flag or '(빈값)'}")

    # 헤더와 실제 파일 컬럼 순서가 다를 수 있으니 실제 헤더를 읽어서 그 순서에 맞춰 append
    with open(args.csv_path, encoding="utf-8-sig", newline="") as f:
        actual_fieldnames = next(csv.reader(f))

    with open(args.csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=actual_fieldnames)
        writer.writerow({col: row.get(col, "") for col in actual_fieldnames})

    print(f"추가 완료: {row['광고주명']} / {row['발송 조건'][:50]}")
    if not row["planID"]:
        print("planID가 비어있습니다. 망분리에서 실행 후 실제 planID를 알려주시면 fill_planid.py로 채워넣을 수 있습니다.")


if __name__ == "__main__":
    main()
