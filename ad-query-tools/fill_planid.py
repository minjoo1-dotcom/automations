"""
라이브러리(CSV)에서 planID가 비어있는 행을 찾아 실제 planID로 채워넣기 (개인 로컬 실행용)

append_to_library.py로 추가해둔 draft가 망분리에서 실행되고 실제 planID가 나온 뒤,
그 값을 라이브러리에 반영할 때 쓴다.

사용 예시
--------
python fill_planid.py --advertiser OK저축은행 --planid 8250
(후보가 여러 개면 목록을 보여주고, --pick 번호로 다시 지정)
python fill_planid.py --advertiser OK저축은행 --planid 8250 --pick 0
"""

import argparse
import csv
import sys

sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = r"C:\Users\finda\Documents\Claude Projects\발송광고 자동화\6월 이후 외부광고 조건 정리.csv"


def load_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def main():
    parser = argparse.ArgumentParser(description="planID가 비어있는 라이브러리 행을 채워넣기")
    parser.add_argument("--advertiser", required=True, help="광고주명 (부분 일치)")
    parser.add_argument("--planid", required=True, help="채워넣을 실제 planID")
    parser.add_argument("--pick", type=int, help="후보가 여러 개일 때, 출력되는 번호 중 선택")
    parser.add_argument("--csv-path", default=CSV_PATH, help="라이브러리 CSV 경로 (기본: 실제 사용 파일)")
    args = parser.parse_args()

    rows, fieldnames = load_rows(args.csv_path)
    candidates = [
        (i, r) for i, r in enumerate(rows)
        if args.advertiser in r.get("광고주명", "") and not r.get("planID", "").strip()
    ]

    if not candidates:
        print(f"'{args.advertiser}' 중 planID가 비어있는 행을 못 찾았습니다.")
        return

    if len(candidates) > 1 and args.pick is None:
        print("planID가 비어있는 후보가 여러 개입니다. --pick 번호로 다시 지정해주세요:\n")
        for n, (_, r) in enumerate(candidates):
            print(f"[{n}] 발송일={r.get('발송일') or '(미정)'} / 조건: {r.get('발송 조건')}")
        return

    idx = 0 if args.pick is None else args.pick
    row_index, row = candidates[idx]
    rows[row_index]["planID"] = args.planid

    with open(args.csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"planID={args.planid} 로 채워넣음: {row.get('광고주명')} / {row.get('발송 조건')}")


if __name__ == "__main__":
    main()
