"""Chạy toàn bộ pipeline từ đầu đến cuối, chỉ bằng code — không làm tay.

Workflow của project này (theo yêu cầu của người dùng):
  1. Data thô + code nằm trong git (data/raw_full/, data/metadata/, scripts/).
  2. Mọi data đã xử lý và mọi kết quả đều do CODE tạo ra khi chạy script này.
     Chúng KHÔNG nằm trong git (xem .gitignore).
  3. Sau khi chạy, dùng scripts/inspect_data.py để xem data đã xử lý như thế nào,
     rồi mới viết report từ những gì mình đã xem.

Các bước (chạy theo thứ tự, bước sau dùng output của bước trước):
  1. build_hourly_2015.py    — tải data thô 2015 từ S3 public của NREL PVDAQ,
                                tổng hợp theo giờ  -> data/hourly_full_year/
  2. build_daily_full_year.py — đặc trưng ngày      -> data/daily_full_year/
  3. preprocess.py            — tiền xử lý + gắn cờ outlier (Phase 1)
                                -> data/processed/*_hourly_clean.csv
  4. clustering.py            — K-Means + GMM (Phase 2)
  5. association.py           — Apriori + FP-Growth (Phase 3)
  6. anomaly.py               — Isolation Forest + One-Class SVM (Phase 4)
  7. inspect_data.py          — xem tóm tắt mọi data đã xử lý

Cách dùng (chạy từ thư mục gốc của repo):
    python scripts/run_pipeline.py              # chạy hết, bước 1 tải từ S3 (lâu nhất)
    python scripts/run_pipeline.py --skip-hourly
        # bỏ qua bước 1 khi data/hourly_full_year/ đã có sẵn (vd chạy lại Phase 2-4)
    python scripts/run_pipeline.py --only preprocess,clustering
        # chỉ chạy 2 bước đó

Mỗi bước chạy bằng chính script của nó (subprocess, cùng Python interpreter),
nên kết quả giống hệt như chạy từng script riêng lẻ.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

STEPS = [
    ("hourly", "Bước 1/6: build hourly 2015 từ S3 (tải 365 ngày x 3 hệ)", ["build_hourly_2015.py"]),
    ("daily", "Bước 2/6: đặc trưng ngày", ["build_daily_full_year.py"]),
    ("preprocess", "Bước 3/6: tiền xử lý + outlier (Phase 1)", ["preprocess.py"]),
    ("clustering", "Bước 4/6: clustering (Phase 2)", ["clustering.py"]),
    ("association", "Bước 5/6: luật kết hợp (Phase 3)", ["association.py"]),
    ("anomaly", "Bước 6/6: anomaly detection (Phase 4)", ["anomaly.py"]),
]


def run_step(name: str, title: str, argv: list[str]) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}", flush=True)
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / argv[0])] + argv[1:],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        print(f"\n!! Bước '{name}' THẤT BẠI (exit {result.returncode}). Dừng pipeline.", file=sys.stderr)
        raise SystemExit(result.returncode)
    print(f"--> Bước '{name}' xong.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy toàn bộ pipeline xử lý data")
    parser.add_argument("--skip-hourly", action="store_true",
                        help="Bỏ qua bước 1 (khi data/hourly_full_year/ đã có sẵn)")
    parser.add_argument("--only", help="Chỉ chạy các bước này, vd: --only preprocess,clustering")
    args = parser.parse_args()

    wanted = None
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        unknown = wanted - {name for name, _, _ in STEPS}
        if unknown:
            print(f"Bước không có: {sorted(unknown)}. Các bước: {[n for n, _, _ in STEPS]}", file=sys.stderr)
            return 2

    for name, title, argv in STEPS:
        if name == "hourly" and args.skip_hourly:
            print(f"\n-- Bỏ qua bước 1 (hourly) theo --skip-hourly, dùng data/hourly_full_year/ đã có.")
            continue
        if wanted is not None and name not in wanted:
            continue
        run_step(name, title, argv)

    print(f"\n{'=' * 70}\nPipeline xong. Xem data đã xử lý bằng:\n"
          f"    python scripts/inspect_data.py\n{'=' * 70}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
