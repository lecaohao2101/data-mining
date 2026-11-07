#!/usr/bin/env python3
"""Build cleaned hourly PVDAQ aggregates for 2015 for 3 validated systems.

Systems (validated 2026-11-07 against OEDI Data Lake + systems_20250729.csv):
  4    NREL x-Si -1, Golden CO, BSk, 1 kW, ground, 1-min, QA pass
  1278 Andre Agassi Prep Academy Bldg D, Las Vegas NV, Bwh, 171.36 kW, roof, 15-min, QA pass
  1403 RTC-FSEC-Baseline, Cocoa Beach FL, Cfa, 6 kW, 1-min, QA FAIL (see README caveats)

Source: NREL PVDAQ, OEDI Data Lake s3://oedi-data-lake/pvdaq/csv/pvdata/
  DOI 10.25984/1846021, CC BY 4.0. All 3 systems have 365/365 day files in 2015
  (checked via S3 ListBucket, 2026-11-07).

Cleaning rules (documented, applied before hourly averaging):
  - irradiance < 0 -> 0 (night sensor offset, sys4: -6..0, sys1403: -1..0)
  - ac/dc power < 0 -> 0 (sys1278 night standby draw -400..-1100 W; sys4 dc noise)
  - sys1278 ambient_temp_f <= 0 -> NaN (sentinel; 2015-10-15 had 14% exact 0.0 and -18.4 F)
  - sys1403 ambient_temp kept as-is but FLAGGED suspect Apr-Jun (up to 56, implausible
    as degC; Jan/Oct look plausible 19-36). Do not use it for association rules
    without an NSRDB cross-check; use module_temp / POA instead.
  - sys1403 ac_power = inv1_ac_power + inv2_ac_power (no system total column).
    2015-06-15 inv1 reads 0 all day while inv2 is normal: a real one-day fault,
    kept in the data as anomaly-detection material (do NOT delete it).
  - hourly value = mean of the sub-hourly samples in that hour; *_n = sample count.
Output: data/hourly/system_{id}_2015_hourly.csv  (8760 rows each, UTC-naive local time
as recorded in PVDAQ `measured_on`; systems are in different US timezones, so do
NOT merge on timestamp without converting to a common timezone first.)
"""
import io, urllib.request, pandas as pd, numpy as np
from concurrent.futures import ThreadPoolExecutor

BASE = "https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/pvdata"
OUT = "/tmp/pvdaq-check/data/hourly"

SYSTEMS = {
    4: dict(
        ac="ac_power__315", dc="dc_power__314", poa="poa_irradiance__313",
        amb="ambient_temp__320", mod=["module_temp_1__321", "module_temp_2__322", "module_temp_3__323"],
    ),
    1278: dict(
        ac="ac_power__3081", dc="dc_power__3080", poa="poa_irradiance__3056",
        amb="ambient_temp_f__3058", mod=["module_temp_f__3059"],
        rh="relative_humidity__3057", wind="wind_speed_mph__3060", winddir="wind_direction__3061",
        amb_f=True, mod_f=True,
    ),
    1403: dict(
        ac=["inv1_ac_power__4207", "inv2_ac_power__4213"], poa="poa_irradiance__4214",
        poa2=["poa_irradiance_refcell1__4215", "poa_irradiance_refcell2__4216"],
        amb="ambient_temp__4217",
        mod=[f"module_temp_{i}__{4217+i}" for i in range(1, 9)],
    ),
}

def fetch_day(sid, y, m, d):
    url = f"{BASE}/system_id={sid}/year={y}/month={m}/day={d}/system_{sid}__date_{y}_{m:02d}_{d:02d}.csv"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return pd.read_csv(io.BytesIO(r.read()), parse_dates=["measured_on"])
    except Exception as e:
        print(f"  !! sys{sid} {y}-{m:02d}-{d:02d} FAILED: {e}")
        return None

def clean_hourly(sid, df):
    spec = SYSTEMS[sid]
    out = pd.DataFrame({"timestamp": pd.to_datetime(df["measured_on"])})
    def get(c):
        return pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
    if isinstance(spec["ac"], list):
        ac = sum(get(c) for c in spec["ac"])
    else:
        ac = get(spec["ac"])
    out["ac_power_w"] = ac.clip(lower=0)
    if "dc" in spec:
        out["dc_power_w"] = get(spec["dc"]).clip(lower=0)
    out["poa_irradiance_wm2"] = get(spec["poa"]).clip(lower=0)
    if "poa2" in spec:
        out["poa_refcell_wm2"] = pd.concat([get(c) for c in spec["poa2"]], axis=1).mean(axis=1).clip(lower=0)
    amb = get(spec["amb"])
    if spec.get("amb_f"):
        amb = (amb - 32) * 5 / 9  # F -> C
        # Las Vegas record low is -13.3C; values below -10C are sensor faults
        # (e.g. exact 0.0F / -18.4F readings on 2015-10-15)
        amb = np.where(amb < -10, np.nan, amb)
    # 1403 ambient has a single 122.3C spike (2015-10-08 11:00); >80C is impossible
    amb = np.where(amb > 80, np.nan, amb)
    out["ambient_temp_c"] = amb
    mods = pd.concat([get(c) for c in spec["mod"]], axis=1)
    # 3276.7C is a failed-sensor sentinel (1403, several sensors at once on
    # 2015-03-02/03): drop per-sensor values >100C before aggregating.
    mods = mods.where(mods <= 100)
    # 1403: module_temp_8 is stuck at 3276.7C Mar-Aug 2015 -> use MEDIAN, not mean
    mods = mods.median(axis=1) if sid == 1403 else mods.mean(axis=1)
    if spec.get("mod_f"):
        mods = (mods - 32) * 5 / 9
    out["module_temp_c"] = mods
    if "rh" in spec:
        out["relative_humidity_pct"] = get(spec["rh"])
    if "wind" in spec:
        out["wind_speed_ms"] = get(spec["wind"]) * 0.44704
        out["wind_direction_deg"] = get(spec["winddir"])
    out["n_samples"] = 1
    rs = out.set_index("timestamp").resample("1h")
    agg = {c: "mean" for c in rs.obj.columns if c != "n_samples"}
    agg["n_samples"] = "sum"
    out = rs.agg(agg)
    return out.reset_index()

def build(sid):
    import os
    os.makedirs(OUT, exist_ok=True)
    import calendar
    days = [(m, d) for m in range(1, 13) for d in range(1, calendar.monthrange(2015, m)[1] + 1)]
    print(f"sys{sid}: fetching {len(days)} days ...", flush=True)
    with ThreadPoolExecutor(max_workers=12) as ex:
        frames = list(ex.map(lambda md: fetch_day(sid, 2015, md[0], md[1]), days))
    ok = [f for f in frames if f is not None]
    print(f"sys{sid}: {len(ok)}/{len(days)} day files OK, {sum(len(f) for f in ok)} raw rows", flush=True)
    hourly = pd.concat([clean_hourly(sid, f) for f in ok], ignore_index=True)
    hourly = hourly.sort_values("timestamp")
    path = f"{OUT}/system_{sid}_2015_hourly.csv"
    hourly.to_csv(path, index=False)
    print(f"sys{sid}: wrote {path} rows={len(hourly)} "
          f"{hourly.timestamp.min()} -> {hourly.timestamp.max()} "
          f"missing ac={hourly.ac_power_w.isna().mean()*100:.1f}% "
          f"daytime_hours={(hourly.poa_irradiance_wm2>50).sum()}", flush=True)
    return path

if __name__ == "__main__":
    for sid in [4, 1278, 1403]:
        build(sid)
