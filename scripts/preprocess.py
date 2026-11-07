"""Phần 1 — Tiền xử lý và xử lý outlier (Data Mining Pipeline, W2–W3).

Đầu vào:  data/hourly_full_year/system_<id>_2015_hourly.csv (đã tổng hợp
            theo giờ, âm đã clip về 0, đơn vị đã chuẩn hoá ở build_hourly_2015.py)
Đầu ra:   data/processed/system_<id>_2015_hourly_clean.csv
          outputs/preprocess_report.json

Nguyên tắc (theo khóa Data Mining Pipeline + đề tài đã chốt):
- KHÔNG xoá outlier tự động. Outlier được gắn cờ để phần Anomaly Detection
  (Phần 4) phân tích sau; chỉ các giá trị vật lý không thể xảy ra mới bị
  đưa về NaN và ghi lại số lượng.
- Chỉ phân tích ban ngày (poa_irradiance_wm2 > 50) cho clustering /
  association; ban đêm công suất ≈ 0 là bình thường, không phải anomaly.

Các bước cho mỗi hệ:
1. Kiểm tra trùng timestamp, sắp xếp thời gian, đếm giờ thiếu so với 8.760 giờ.
2. Nhiệt độ môi trường > 80 °C -> NaN (spike cảm biến, vd System 1403
   122,3 °C ngày 08/10/2015); nhiệt độ module > 100 °C -> NaN.
3. is_daytime = poa_irradiance_wm2 > 50.
4. power_per_kw = ac_power_w / công suất định mức (kW).
   irr_ratio = power_per_kw / poa_irradiance_wm2 (ban ngày), tức W/kW trên
   mỗi W/m² bức xạ — tỉ số này ổn định khi hệ chạy bình thường.
5. Outlier IQR trên irr_ratio ban ngày (ngoài [Q1-1.5*IQR, Q3+1.5*IQR]).
6. Cờ low_power_high_irr: poa > 800 W/m² nhưng ac_power_w < 10% công suất
   định mức — nghi inverter / hệ thống ngừng phát, giữ lại làm mẫu anomaly.
7. Chuẩn hoá (z-score) các cột power_per_kw, poa_irradiance_wm2,
   ambient_temp_c, module_temp_c ban ngày -> cột *_z, phục vụ K-Means/GMM.

Chạy:  python scripts/preprocess.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "hourly_full_year"
OUTPUT_DIR = ROOT / "data" / "processed"
REPORT_PATH = ROOT / "outputs" / "preprocess_report.json"

CAPACITY_KW = {4: 1.0, 1278: 171.36, 1403: 6.0}
EXPECTED_HOURS = 8760


def preprocess_system(sid: int) -> dict:
    df = pd.read_csv(INPUT_DIR / f"system_{sid}_2015_hourly.csv", parse_dates=["timestamp"])
    report: dict = {"system_id": sid, "input_rows": int(len(df))}
    df = df.sort_values("timestamp").reset_index(drop=True)

    dup = int(df["timestamp"].duplicated().sum())
    report["duplicate_timestamps"] = dup
    df = df.drop_duplicates(subset="timestamp")

    # Giờ thiếu so với 8.760 giờ của năm 2015 (không fill, chỉ ghi nhận).
    full = pd.date_range("2015-01-01", "2015-12-31 23:00", freq="h")
    missing_hours = int(len(set(full) - set(df["timestamp"])))
    report["missing_hours_vs_8760"] = missing_hours
    report["missing_values"] = {c: int(df[c].isna().sum()) for c in df.columns}

    # 2. Nhiệt độ vật lý không thể xảy ra -> NaN (ghi số lượng, không xoá dòng).
    amb_bad = int((df["ambient_temp_c"] > 80).sum())
    df.loc[df["ambient_temp_c"] > 80, "ambient_temp_c"] = pd.NA
    mod_bad = int((df["module_temp_c"] > 100).sum())
    df.loc[df["module_temp_c"] > 100, "module_temp_c"] = pd.NA
    report["ambient_temp_gt_80_to_nan"] = amb_bad
    report["module_temp_gt_100_to_nan"] = mod_bad

    # 3-4. Ban ngày + tỉ số công suất / bức xạ.
    df["is_daytime"] = df["poa_irradiance_wm2"] > 50
    df["power_per_kw"] = df["ac_power_w"] / CAPACITY_KW[sid]
    day = df["is_daytime"]
    df["irr_ratio"] = float("nan")
    df.loc[day, "irr_ratio"] = df.loc[day, "power_per_kw"] / df.loc[day, "poa_irradiance_wm2"]
    report["daytime_hours"] = int(day.sum())

    # 5. Outlier IQR trên irr_ratio ban ngày.
    ratio = pd.to_numeric(df.loc[day, "irr_ratio"], errors="coerce").dropna()
    q1, q3 = ratio.quantile(0.25), ratio.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df["outlier_iqr"] = False
    valid = day & df["irr_ratio"].notna()
    df.loc[valid, "outlier_iqr"] = (df.loc[valid, "irr_ratio"] < lo) | (
        df.loc[valid, "irr_ratio"] > hi
    )
    report["irr_ratio_iqr_bounds"] = [float(lo), float(hi)]
    report["outlier_iqr_daytime"] = int(df["outlier_iqr"].sum())

    # 6. Bức xạ cao nhưng công suất thấp — nghi lỗi hệ thống, giữ lại.
    df["outlier_low_power_high_irr"] = (df["poa_irradiance_wm2"] > 800) & (
        df["ac_power_w"] < 0.10 * CAPACITY_KW[sid] * 1000
    )
    report["outlier_low_power_high_irr"] = int(df["outlier_low_power_high_irr"].sum())
    report["outlier_low_power_high_irr_dates"] = sorted(
        df.loc[df["outlier_low_power_high_irr"], "timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist()
    )

    # 7. Z-score ban ngày cho clustering (K-Means/GMM cần chuẩn hoá).
    for col in ["power_per_kw", "poa_irradiance_wm2", "ambient_temp_c", "module_temp_c"]:
        s = pd.to_numeric(df.loc[day, col], errors="coerce")
        df[col + "_z"] = pd.NA
        df.loc[day, col + "_z"] = (s - s.mean()) / s.std(ddof=0)

    df["outlier_any"] = df["outlier_iqr"] | df["outlier_low_power_high_irr"]
    report["outlier_any_daytime"] = int(df["outlier_any"].sum())
    report["outlier_any_pct_daytime"] = round(
        100 * int(df["outlier_any"].sum()) / max(int(day.sum()), 1), 2
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / f"system_{sid}_2015_hourly_clean.csv", index=False)
    report["output_rows"] = int(len(df))
    report["output_columns"] = list(df.columns)
    return report


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs").mkdir(exist_ok=True)
    reports = [preprocess_system(sid) for sid in [4, 1278, 1403]]
    REPORT_PATH.write_text(json.dumps(reports, indent=2, ensure_ascii=False))
    for r in reports:
        print(
            f"System {r['system_id']}: {r['input_rows']} giờ, "
            f"thiếu {r['missing_hours_vs_8760']} giờ, "
            f"ban ngày {r['daytime_hours']} giờ, "
            f"outlier {r['outlier_any_daytime']} giờ ({r['outlier_any_pct_daytime']}%), "
            f"trong đó bức xạ cao/công suất thấp: {r['outlier_low_power_high_irr']}"
        )
    print(f"Report: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
