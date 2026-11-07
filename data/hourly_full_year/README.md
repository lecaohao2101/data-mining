# Data Mining — Solar Power Generation (PVDAQ, 2015)

Final course project for **Data Mining Foundations and Practice**
(Coursera / University of Colorado Boulder, via FPT University):
**"Mining Solar Power Generation Data for Pattern Discovery and Anomaly Detection"**

Three methods: clustering (K-Means / GMM), association rule mining
(Apriori / FP-Growth), anomaly detection (Isolation Forest / One-Class SVM).

## Data — `data/hourly/`

Cleaned **hourly** aggregates for calendar year **2015**, built from the
NREL PVDAQ public data lake (DOI `10.25984/1846021`, CC BY 4.0).
Raw data: one CSV per system per day at
`s3://oedi-data-lake/pvdaq/csv/pvdata/system_id=<id>/year=2015/month=<m>/day=<d>/`.
All three systems have **365/365 day files in 2015** (verified via S3 listing, 2026-11-07).

| File | System | Site / climate | Size | Resolution (raw) | Rows |
|---|---|---|---|---|---|
| `system_4_2015_hourly.csv` | 4 — NREL x-Si -1 | Golden, CO — BSk (cold semi-arid) | 1 kW, ground, fixed, tilt 40° | 1-min (525,600 rows) | 8,760 |
| `system_1278_2015_hourly.csv` | 1278 — Andre Agassi Prep. Academy Bldg D | Las Vegas, NV — Bwh (hot desert) | 171.36 kW, roof, fixed | 15-min (34,972 rows) | 8,760 |
| `system_1403_2015_hourly.csv` | 1403 — RTC-FSEC-Baseline | Cocoa Beach, FL — Cfa (humid subtropical) | 6 kW | 1-min (523,658 rows) | 8,730 |

Why these three: three different climates (BSk / Bwh / Cfa), three scales
(1 kW / 171 kW / 6 kW), ground vs roof, and a common full year (2015) so
day-profiles can be compared across systems. Systems 4 and 1278 are PVDAQ
QA `pass`; 1403 is QA `fail` — kept deliberately, see caveats below.

Common columns: `timestamp` (local time as recorded by PVDAQ — the three
sites are in different US timezones, so **do not merge on timestamp without
converting to a common timezone**), `ac_power_w`, `poa_irradiance_wm2`,
`ambient_temp_c`, `module_temp_c`, `n_samples` (raw samples in that hour).
System 4 also has `dc_power_w`; 1278 also has `dc_power_w`,
`relative_humidity_pct`, `wind_speed_ms`, `wind_direction_deg`;
1403 also has `poa_refcell_wm2` (mean of 2 reference cells) and its
`ac_power_w` is inv1 + inv2 (no system-total column exists).

## How it was built

`scripts/build_hourly_2015.py` — downloads the 365 day files per system,
selects the canonical channels, applies the cleaning rules below, and
resamples to hourly means. Re-run it to reproduce the files exactly.

Cleaning rules:
- `poa_irradiance < 0` → 0 (night sensor offset; sys4 reads −6…0 at night).
- `ac_power / dc_power < 0` → 0 (sys1278 draws −400…−1100 W at night = standby load).
- Sys1278 `ambient_temp`: °F → °C; values < −10 °C → missing
  (Las Vegas record low is −13.3 °C; the raw file contains 0.0 °F / −18.4 °F
  sentinel readings, e.g. 2015-10-15).
- Sys1403 module temps: per-sensor values > 100 °C → missing first
  (3276.7 °C is a failed-sensor sentinel), then **median** of the 8 sensors.
  A plain mean is wrong here — sensor 8 is stuck at 3276.7 °C Mar–Aug 2015,
  and on 2015-03-02/03 sensors 1–4 stuck simultaneously, so even the median
  fails without the >100 °C mask.
- Sys1403 `ambient_temp` > 80 °C → missing (single spike of 122.3 °C on
  2015-10-08 11:00; the channel still reads high in warm months, see caveat 1).
- Sys1403 `ac_power` = inv1 + inv2 inverter power.

## Validation results (2015, hourly files)

| Check | Sys 4 | Sys 1278 | Sys 1403 |
|---|---|---|---|
| Hourly rows / missing hours | 8,760 / 0 | 8,760 / 0 | 8,730 / **30 missing** |
| Missing `ac_power_w` | 0% | 0.25% (22 h) | 0% |
| Missing `ambient_temp_c` | 0% | **8.2%** (711 h, mostly Dec) | 0% (122.3 °C spike on 2015-10-08 masked per-minute) |
| Missing `poa_irradiance` | 0% | 0.01% | 0% |
| Missing `module_temp_c` | 0% | 0.01% | 0% |
| Daytime hours (POA > 50) | 3,736 | 4,001 | 3,818 |
| Daytime AC max | 942 W | 138,225 W | 6,168 W |
| Daytime POA max | 1,294 W/m² | 1,274 W/m² | 1,133 W/m² |
| Daytime corr. AC vs POA | 0.942 | 0.980 | 0.964 |

## Caveats — read before analysing (these are report material, not reasons to drop the data)

1. **Sys1403 `ambient_temp_c` reads high in warm months** (daytime means
   ~44 °C in Jun–Aug, 1,373 hours above 45 °C, one 122.3 °C spike on
   2015-10-08 11:00, removed by the >80 °C rule). Jan (19–36 °C) and Oct
   look plausible. Use `module_temp_c` (median of 8 sensors, sentinel-masked)
   and POA for weather rules on this system, and cross-check ambient against
   NSRDB if you need it.
2. **Sys1403 module-temperature sensors fail with a 3276.7 °C sentinel:**
   sensor 8 is stuck Mar–Aug 2015, and sensors 1–4 stuck simultaneously on
   2015-03-02 14:00–15:00 and 2015-03-03 10:00. Fixed in this build by
   masking >100 °C per sensor, then taking the median. A plain mean would
   give module temps up to 1,567 °C in March — check any re-run for this.
3. **Sys1403 has two overnight data gaps:** 2015-04-16 16:00 → 2015-04-17 07:00
   (16 h) and 2015-06-04 20:00 → 2015-06-05 09:00 (14 h). Logger downtime,
   not missing days — both are overnight, so daytime analysis is unaffected.
4. **Sys1403, 2015-06-15: inverter 1 reads 0 all day** while inverter 2 is
   normal; on 15 Jan / 15 Apr / 15 Oct both inverters peak at ~2.9 kW each.
   A genuine one-day fault — keep it, it is ideal anomaly-detection material.
   Do not delete it in preprocessing.
5. **Sys1278 ambient temperature degrades in late 2015:** missing by month
   is 1 h (Jul), 16 h (Sep), 67 h (Oct), 128 h (Nov), 499 h (Dec).
   `module_temp_c` stays 99.99% present — prefer it for late-year analysis.
6. **Night values are sensor noise, not generation.** Analyse daytime only
   (e.g. POA > 50 W/m²), normalise power by each system's DC capacity
   (kW/kWp) before comparing systems, and never report anomaly-detection
   accuracy as a percentage — there are no ground-truth labels.

## Rejected candidates (checked, not used)

- **Sys1199, Hunt Valley MD (Cfa, 52.9 kW, 37 channels, QA pass):** the raw
  files contain only inverter electrical channels — **no irradiance, no
  ambient temperature, no humidity, no wind** — so weather association rules
  are impossible without joining an external weather source (NSRDB).
- **NIST systems 4901–4903, Gaithersburg MD (98–121 channels):** full weather
  in principle, but the June-2015 sample has sentinel values (−999 power,
  POA channel reading max 12.1) and QA warnings (correlation < 0.5, wrong
  mounting config). Too messy for this project.
- **Sys1200 / 1202 (MD/NJ, Distributed Sun):** same problem as 1199 —
  inverter-only channels.

## Sources

- PVDAQ public data lake: https://data.openei.org/s3_viewer?bucket=oedi-data-lake&prefix=pvdaq
- System list (2025-07-29): https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv
- Dataset DOI: 10.25984/1846021, licence CC BY 4.0
