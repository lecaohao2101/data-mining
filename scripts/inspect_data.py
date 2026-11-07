"""Xem data đã xử lý trông như thế nào — dùng sau khi chạy pipeline.

In ra cho mỗi file đã xử lý: số dòng/cột, tên cột, 3 dòng đầu, thống kê
(mean/min/max/% thiếu) của các cột chính. Dùng để viết report: mọi con số
trong report đều phải lấy từ output của script này (hoặc từ các file JSON
trong outputs/), không lấy từ trí nhớ.

Cách dùng (chạy từ thư mục gốc của repo):
    python scripts/inspect_data.py
    python scripts/inspect_data.py --only hourly
    python scripts/inspect_data.py --only processed,outputs
"""

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

GROUPS = {
    "hourly": sorted((ROOT / "data" / "hourly_full_year").glob("system_*_2015_hourly.csv")),
    "daily": sorted((ROOT / "data" / "daily_full_year").glob("system_*_2015_daily.csv")),
    "processed": sorted((ROOT / "data" / "processed").glob("system_*_2015_hourly_clean.csv"))
    + sorted((ROOT / "data" / "processed").glob("system_*_2015_daily_features.csv")),
    "outputs": sorted((ROOT / "outputs").glob("*.csv")),
}


def show_csv(path: Path) -> None:
    print(f"\n--- {path.relative_to(ROOT)} ---")
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"    Không đọc được: {e}")
        return
    print(f"    Dòng: {len(df):,} | Cột: {len(df.columns)}")
    print(f"    Cột: {', '.join(df.columns)}")
    print("    3 dòng đầu:")
    print(df.head(3).to_string(index=False).replace("\n", "\n    "))
    num = df.select_dtypes(include="number")
    if not num.empty:
        print("    Thống kê (mean / min / max / % thiếu):")
        for c in num.columns:
            s = num[c]
            print(f"      {c:<28} mean={s.mean():12.2f}  min={s.min():12.2f}  "
                  f"max={s.max():12.2f}  thiếu={s.isna().mean()*100:5.2f}%")


def show_json(path: Path) -> None:
    print(f"\n--- {path.relative_to(ROOT)} ---")
    data = json.loads(path.read_text())
    print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])


def main() -> int:
    parser = argparse.ArgumentParser(description="Xem data đã xử lý")
    parser.add_argument("--only", help="Chỉ xem nhóm này: hourly, daily, processed, outputs")
    args = parser.parse_args()
    groups = [args.only] if args.only else list(GROUPS)
    for g in groups:
        if g not in GROUPS:
            print(f"Nhóm không có: {g}. Các nhóm: {list(GROUPS)}")
            return 2
        for path in GROUPS[g]:
            show_csv(path)
    # Tóm tắt các report JSON (Phase 1-4) — đọc lướt, không in hết.
    for path in sorted((ROOT / "outputs").glob("*_report.json")):
        print(f"\n--- {path.relative_to(ROOT)} (tóm tắt) ---")
        data = json.loads(path.read_text())
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                keys = {k: v for k, v in item.items() if not isinstance(v, (list, dict))}
                print(f"    system {item.get('system_id', '?')}: {keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
