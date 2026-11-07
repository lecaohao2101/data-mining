"""Tính đặc trưng ngày (365 ngày/hệ) từ bản theo giờ cả năm 2015.

Chạy từ bất cứ đâu:  python scripts/build_daily_full_year.py
Đầu vào:  data/hourly_full_year/system_<id>_2015_hourly.csv
Đầu ra:   data/daily_full_year/system_<id>_2015_daily.csv
"""
import pandas as pd, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
os.makedirs(ROOT / "data" / "daily_full_year", exist_ok=True)
for sid in [4,1278,1403]:
    df=pd.read_csv(ROOT / f"data/hourly_full_year/system_{sid}_2015_hourly.csv", parse_dates=["timestamp"])
    df["date"]=df["timestamp"].dt.date
    rows=[]
    for dt, g in df.groupby("date"):
        day=g[g["poa_irradiance_wm2"]>50]
        rows.append({
            "date": str(dt),
            "system_id": sid,
            "n_hours": int(len(g)),
            "energy_kWh": float(g["ac_power_w"].clip(lower=0).sum()/1000.0),
            "ac_power_mean_W": float(g["ac_power_w"].mean()),
            "ac_power_max_W": float(g["ac_power_w"].max()),
            "ac_power_std_W": float(g["ac_power_w"].std()),
            "poa_irradiance_mean_Wm2": float(g["poa_irradiance_wm2"].mean()),
            "poa_irradiance_max_Wm2": float(g["poa_irradiance_wm2"].max()),
            "ambient_temp_mean_C": float(g["ambient_temp_c"].mean()),
            "ambient_temp_max_C": float(g["ambient_temp_c"].max()),
            "ambient_temp_min_C": float(g["ambient_temp_c"].min()),
            "module_temp_mean_C": float(g["module_temp_c"].mean()),
            "daytime_hours_irr_gt_50": int(len(day)),
            "daytime_ac_power_mean_W": float(day["ac_power_w"].mean()) if len(day) else None,
            "daytime_irr_mean_Wm2": float(day["poa_irradiance_wm2"].mean()) if len(day) else None,
        })
    out=pd.DataFrame(rows)
    out.to_csv(ROOT / f"data/daily_full_year/system_{sid}_2015_daily.csv", index=False)
    print(sid, len(out), out["date"].min(), out["date"].max(), "energy mean kWh", round(out["energy_kWh"].mean(),2))
