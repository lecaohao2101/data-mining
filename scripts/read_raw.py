"""Đọc và xem data thô PVDAQ trong repo này.

Data thô nằm ở data/raw_full/system_<id>/2015_<mm>/system_<id>__date_<yyyy>_<mm>_<dd>.csv
- System 4, 1403: 1 phút/dòng, 1440 dòng/ngày
- System 1278: 15 phút/dòng, 96 dòng/ngày
- Tên cột thô khác nhau theo từng hệ, dạng <tên>__<mã cảm biến>, ví dụ
  ac_power__315, poa_irradiance__313, ambient_temp__320 (system 4),
  ac_power__3081, ambient_temp_f__3058 (system 1278, nhiệt độ °F),
  inv1_ac_power__4207, inv2_ac_power__4213 (system 1403, không có cột tổng).

Cách dùng (chạy từ thư mục gốc của repo):
    python scripts/read_raw.py --system 4 --date 2015-01-01
    python scripts/read_raw.py --system 1278 --date 2015-07-03 --head 10
    python scripts/read_raw.py --system 1403 --list
    python scripts/read_raw.py --system 4 --list --month 2015-07
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw_full"

# Cột chính cần tìm theo tiền tố, vì hậu tố __<mã> khác nhau theo hệ.
KEY_PREFIXES = {
    "ac_power": ["ac_power__"],
    "poa_irradiance": ["poa_irradiance__"],
    "ambient_temp": ["ambient_temp__", "ambient_temp_f__"],
    "module_temp": ["module_temp_"],
    "dc_power": ["dc_power__"],
}


def raw_path(system_id: int, date: str) -> Path:
    """Trả về đường dẫn file thô của 1 hệ, 1 ngày (yyyy-mm-dd)."""
    year, month, day = date.split("-")
    return (
        RAW_DIR
        / f"system_{system_id}"
        / f"{year}_{month}"
        / f"system_{system_id}__date_{year}_{month}_{day}.csv"
    )


def list_raw_dates(system_id: int, month: str | None = None) -> list[str]:
    """Liệt kê các ngày thô có sẵn của 1 hệ, lọc theo tháng yyyy-mm nếu có."""
    pattern = f"system_{system_id}__date_*.csv"
    files = sorted((RAW_DIR / f"system_{system_id}").rglob(pattern))
    dates = []
    for f in files:
        m = re.search(r"(\d{4})_(\d{2})_(\d{2})\.csv$", f.name)
        if m:
            d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            if month is None or d.startswith(month):
                dates.append(d)
    return dates


def find_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Tìm các cột chính theo tiền tố, trả về dict tên chuẩn -> list cột thô."""
    found: dict[str, list[str]] = {}
    for key, prefixes in KEY_PREFIXES.items():
        cols = [c for c in df.columns if any(c.startswith(p) for p in prefixes)]
        if cols:
            found[key] = cols
    return found


def read_raw(system_id: int, date: str) -> pd.DataFrame:
    """Đọc 1 file thô, parse cột measured_on thành datetime."""
    path = raw_path(system_id, date)
    if not path.exists():
        available = list_raw_dates(system_id)
        raise FileNotFoundError(
            f"Không có file thô: {path}\n"
            f"Ngày có sẵn của system {system_id}: "
            f"{available[0]} .. {available[-1]} ({len(available)} ngày)"
            if available
            else f"Không có file thô nào cho system {system_id}"
        )
    df = pd.read_csv(path, parse_dates=["measured_on"])
    return df


def show(df: pd.DataFrame, head: int = 5) -> None:
    """In tóm tắt 1 file thô: kích thước, cột, khoảng thời gian, 5 dòng đầu,
    thống kê và % thiếu của các cột chính."""
    print(f"Số dòng: {len(df):,} | Số cột: {len(df.columns)}")
    print(f"Khoảng thời gian: {df['measured_on'].min()} -> {df['measured_on'].max()}")
    print("\nCột:")
    for c in df.columns:
        print(f"  - {c}")
    print("\nCột chính tìm được:")
    for key, cols in find_columns(df).items():
        print(f"  {key}: {cols}")
    print(f"\n{head} dòng đầu:")
    print(df.head(head).to_string(index=False))
    print("\nThống kê cột chính (mean / min / max / % thiếu):")
    for key, cols in find_columns(df).items():
        for c in cols:
            s = pd.to_numeric(df[c], errors="coerce")
            print(
                f"  {c:<28} mean={s.mean():10.2f}  min={s.min():10.2f}  "
                f"max={s.max():10.2f}  thiếu={s.isna().mean()*100:5.2f}%"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Đọc và xem data thô PVDAQ")
    parser.add_argument("--system", type=int, required=True, help="System ID: 4, 1278 hoặc 1403")
    parser.add_argument("--date", help="Ngày cần xem, dạng yyyy-mm-dd, ví dụ 2015-01-01")
    parser.add_argument("--head", type=int, default=5, help="Số dòng đầu in ra (mặc định 5)")
    parser.add_argument("--list", action="store_true", help="Chỉ liệt kê các ngày thô có sẵn")
    parser.add_argument("--month", help="Lọc --list theo tháng, dạng yyyy-mm, ví dụ 2015-07")
    args = parser.parse_args()

    if args.list:
        dates = list_raw_dates(args.system, args.month)
        print(f"System {args.system}: {len(dates)} ngày thô có sẵn")
        for d in dates:
            print(f"  {d}")
        return 0

    if not args.date:
        print("Thiếu --date. Ví dụ: python scripts/read_raw.py --system 4 --date 2015-01-01")
        return 2

    try:
        df = read_raw(args.system, args.date)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    print(f"File: {raw_path(args.system, args.date).relative_to(REPO_ROOT)}")
    show(df, head=args.head)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
