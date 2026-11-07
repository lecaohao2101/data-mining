# Mining Solar Power Generation Data for Pattern Discovery and Anomaly Detection

**Course:** Data Mining Project (DTSA 5506 / CSCA 5522) — Specialization *Data Mining
Foundations and Practice*, University of Colorado Boulder (Coursera, via FPT University)
**Author:** Hao Le Cao
**Date:** 7 November 2026
**Data:** NREL PVDAQ Public Datasets, DOI 10.25984/1846021, CC BY 4.0
**Repository:** https://github.com/lecaohao2101/data-mining (code, data and all
intermediate results referenced below)

## Abstract

This project mines one year (2015) of solar power generation data from three
photovoltaic systems in the NREL PVDAQ database to (1) cluster days by generation
pattern, (2) discover association rules between weather and power output, and
(3) detect hours when power output does not match the weather. The three systems
span three climates and three orders of magnitude in size: Golden, Colorado
(1 kW, cold semi-arid), Las Vegas, Nevada (171.36 kW, hot desert) and Cocoa Beach,
Florida (6 kW, humid subtropical). K-Means clustering finds two day types per
system — high-output and low-output days — with silhouette scores of 0.35–0.46.
Association rule mining (Apriori and FP-Growth, which agree exactly) finds 179
rules; the strongest is that high irradiance implies high power
(confidence 0.92–0.95, lift 2.76–2.86) in all three systems. Isolation Forest and
One-Class SVM, both set to flag 5% of daytime hours, agree on 94.8–96.3% of hours
and recover all 28 known high-irradiance/low-power hours in Golden, 7 of 12
daytime hours of a known one-inverter failure in Cocoa Beach, and part of a
known data-gap day in Las Vegas. Because anomaly detection has no ground-truth
labels, no accuracy percentage is reported; anomalies are evaluated by whether
they match known incidents and have a physical explanation. All numbers in this
report are traceable to files in `data/` and `outputs/` in the repository.

## 1. Introduction

Solar power is variable by nature: the same panel produces very different output
on a clear summer day and on a cloudy winter day. Operators need to know which
days behave alike, which weather conditions drive output, and when output is
abnormally low for the weather — because that is when something may be broken.
This project answers three research questions, one per method taught in the
Data Mining Methods course:

1. **Clustering:** What recurring day types exist in solar generation patterns?
2. **Association rules:** Which weather conditions are associated with high or
   low power output, and how strong are those associations?
3. **Anomaly detection:** Which hours produce power that does not match the
   weather, and do those hours correspond to real faults?

The project deliberately uses only the methods from the course — K-Means and
Gaussian Mixture Models, Apriori and FP-Growth, Isolation Forest and One-Class
SVM — and no deep learning. The main difficulty, identified at the proposal
stage, was finding a public dataset in which power and weather are synchronised
in time; NREL PVDAQ provides exactly that.

## 2. Data

### 2.1 Source

**NREL PVDAQ — Photovoltaic Data Acquisition, Public Datasets.** National
Renewable Energy Laboratory (NREL), U.S. Department of Energy. DOI
`10.25984/1846021`, licence CC BY 4.0. Landing page:
https://data.openei.org/submissions/4568. Public S3 data lake:
`s3://oedi-data-lake/pvdaq/csv/pvdata/`. System list:
`https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv`.
Data accessed and downloaded on 7 November 2026. Full provenance, including
systems that were examined and rejected, is in `docs/DATA_SOURCES.md`.

### 2.2 Systems

| System | Site | Climate | Capacity | Raw resolution | QA flag in PVDAQ list |
|---|---|---|---|---|---|
| 4 | NREL x-Si -1, Golden, CO | BSk, cold semi-arid | 1.0 kW | 1 min, 17 columns | pass |
| 1278 | Andre Agassi Preparatory Academy, Building D, Las Vegas, NV | BWh, hot desert | 171.36 kW | 15 min, 28 columns | pass |
| 1403 | RTC-FSEC-Baseline, Cocoa Beach, FL | Cfa, humid subtropical | 6.0 kW | 1 min, 26 columns | fail — used with caution, see §3 |

The three systems were chosen for diversity: three climates and capacities from
1 kW to 171 kW, so any comparison must normalise by rated capacity (W/kW).

### 2.3 Scope and files

The analysis uses the full year 2015. Hourly aggregates (8,760 hours per system;
System 1403 has 8,730, missing 30 hours) are in `data/hourly_full_year/`, daily
features (365 days per system) in `data/daily_full_year/`, system metadata in
`data/metadata/`. Raw daily files are kept only for January and July 2015
(186 files, `data/raw_full/`); the full-year hourly data were rebuilt from the
public S3 lake with `scripts/build_hourly_2015.py`. Annual energy totals in
2015 were 1,436.8 kWh (System 4), 260,414.4 kWh (System 1278) and 9,067.6 kWh
(System 1403); mean daily energy was 3.94, 713.46 and 24.84 kWh respectively.
Daytime (irradiance > 50 W/m²) correlation between AC power and irradiance was
0.942 (System 4), 0.980 (System 1278) and 0.964 (System 1403) — high, as
expected, which is precisely why deviations from that relationship are
informative. **Timezone warning:** timestamps are each site's local time
(Golden, Las Vegas and Cocoa Beach differ); the three systems were never merged
on timestamp without conversion.

## 3. Data understanding and preprocessing

Preprocessing followed the Data Mining Pipeline course (Weeks 2–3) and is
implemented in `scripts/preprocess.py`; its report is
`outputs/preprocess_report.json` and its output is
`data/processed/system_<id>_2015_hourly_clean.csv`.

**Rules applied, and why.** Negative irradiance and power values were clipped
to zero at the hourly build stage (night sensor offsets: System 4 irradiance
≈ −2 W/m² at night; System 1278 night standby draw −400 to −1,100 W).
Temperatures that are physically impossible were set to missing, not deleted:
ambient temperature above 80 °C and module temperature above 100 °C
(no such hours remained in the hourly files, because the build script had
already removed the one 122.3 °C spike of 8 October 2015 in System 1403).
Only daytime hours (irradiance > 50 W/m²) were analysed for clustering,
association and anomaly detection; at night power ≈ 0 is normal, not an anomaly.
Features were standardised (z-scores) before clustering, and power was
normalised per kW before any cross-system comparison.

**Outliers were flagged, not deleted.** An IQR rule on the daytime
power-per-kW / irradiance ratio flagged 537 of 3,736 daytime hours in System 4
(14.4%), 405 of 4,001 in System 1278 (10.1%) and 405 of 3,818 in System 1403
(10.6%). The rate is high because the ratio varies with clouds and temperature,
so these are *candidates*, not conclusions; §6 tests them with two independent
models. A stricter, physically defined flag — irradiance above 800 W/m² while
power is below 10% of rated capacity — marked 28 hours in System 4, 0 in
System 1278 and 8 in System 1403.

**Data problems found (and kept as evidence, not silently fixed).**

| Problem | System | Evidence |
|---|---|---|
| Module temperature sensor 8 stuck at 3,276.7 °C | 1403 | March–August 2015; fixed by masking values above 100 °C per sensor and taking the median of 8 sensors, not the mean |
| Ambient temperature reads implausibly high in hot season (up to 58 °C) | 1403 | Use module temperature, not ambient temperature, for association rules on this system |
| Ambient temperature missing 719 hours (8.2%), mostly December | 1278 | Raw temperature in °F, wind in mph (converted); 223 daytime hours dropped from association mining for this reason |
| Two overnight gaps, 16 h (16–17 Apr) and 14 h (4–5 Jun) | 1403 | 30 hours absent as rows, not NaN |
| Inverter 1 reads 0 all day while inverter 2 is normal | 1403, 15 Jun 2015 | Kept as anomaly-detection material (§6) |
| Raw file of 3 Jul 2015 has only 68 of 96 15-minute rows; power missing 25%, irradiance/temperature missing 33.8% | 1278 | Found with `scripts/read_raw.py`; see §6 |

System 1403 carries a QA `fail` flag in the PVDAQ systems list for its full
time range, but its 2015 daytime power–irradiance correlation is 0.964, so it
was kept with this limitation stated explicitly.

## 4. Clustering days by generation pattern

**Method.** Daily features were computed from the cleaned hourly data
(`scripts/clustering.py`): energy per kW, peak power per kW, daytime hours,
mean daytime irradiance, mean ambient temperature, and variability
(daytime power standard deviation divided by its mean). Each system was
clustered separately on standardised features. K-Means and Gaussian Mixture
Models were run for k = 2–6; k was chosen by silhouette score (K-Means) and BIC
(GMM). Output: `data/processed/system_<id>_2015_daily_features.csv`,
`outputs/clustering_report.json`, figures in `outputs/clustering_system_<id>.png`.

**Result: k = 2 for all three systems.**

| System | Silhouette, k = 2 | k = 3 | k = 4 | k = 5 | k = 6 | GMM best k by BIC |
|---|---|---|---|---|---|---|
| 4 | **0.457** | 0.309 | 0.297 | 0.297 | 0.275 | 6 |
| 1278 | **0.445** | 0.323 | 0.307 | 0.279 | 0.322 | 5 |
| 1403 | **0.349** | 0.310 | 0.294 | 0.309 | 0.303 | 5 |

Silhouette falls sharply after k = 2, so k = 2 is the data-driven choice. GMM's
BIC keeps decreasing up to k = 5–6, which means it splits further by season
rather than finding new, well-separated patterns, so the K-Means choice was kept.

| System | High-output cluster | Low-output cluster |
|---|---|---|
| 4 | 274 days, 4.81 kWh/kW, irradiance 572 W/m², 10.8 h sun, 14.5 °C | 91 days, 1.32 kWh/kW, irradiance 256 W/m², 8.5 h sun, 2.7 °C |
| 1278 | 214 days, 5.16 kWh/kW, irradiance 692 W/m², 27.2 °C | 151 days, 2.75 kWh/kW, irradiance 521 W/m², 12.1 °C |
| 1403 | 251 days, 4.89 kWh/kW, irradiance 553 W/m² | 114 days, 2.48 kWh/kW, irradiance 345 W/m² |

**Validation against real weather.** The clusters are explainable by weather,
not just by numbers. In Las Vegas the split is strongly seasonal: the
high-output cluster is almost entirely March–October and the low-output cluster
almost entirely November–February. In Golden and Cocoa Beach the low-output
cluster is spread through the whole year (most common in December, but present
in summer too), i.e. driven by clouds as well as by season. The scatter of
energy against irradiance also shows days with high irradiance but very low
energy — the anomaly candidates examined in §6.

**Limitation.** Daily patterns form a continuum driven by season and irradiance,
not sharply separated groups; silhouette scores of 0.35–0.46 are moderate.
k = 2 is the simplest robust choice; forcing a larger k would manufacture
clusters the data does not support.

## 5. Association rules: weather → power

**Method.** Daytime hours only, from `data/processed/`
(`scripts/association.py`). Each continuous variable was discretised into
Low / Medium / High by its own tertiles per system (thresholds are in
`outputs/association_report.json`). Variables: irradiance, temperature and
power per kW for all systems; System 1278 additionally used relative humidity
and wind speed. For System 1403, module temperature replaced ambient
temperature (see §3). Apriori and FP-Growth were both run with minimum support
0.05 and maximum itemset length 3; the two algorithms produced identical
frequent itemsets (verified by assertion in the code). Rules were kept when
lift > 1 and confidence ≥ 0.5. Output: `outputs/association_rules.csv`
(179 rules), `outputs/association_report.json`.

**Result: 179 rules** — 26 for System 4, 111 for System 1278, 42 for System 1403;
lift ranges from 1.51 to 3.00. The strongest rules are the same in all three
systems:

| Rule | System | Support | Confidence | Lift |
|---|---|---|---|---|
| irradiance High → power High | 4 / 1278 / 1403 | 0.32 / 0.31 / 0.31 | 0.95 / 0.92 / 0.94 | 2.86 / 2.76 / 2.83 |
| irradiance Low → power Low | 4 / 1278 / 1403 | 0.31 / 0.32 / 0.32 | 0.92 / 0.95 / 0.95 | 2.76 / 2.84 / 2.86 |
| irradiance High, temperature Medium → power High | 4 | 0.116 | 0.998 | 2.99 |
| irradiance Low, wind Low → power Low | 1278 | 0.125 | 0.967 | 2.90 |
| humidity Low, irradiance High → power High | 1278 | 0.149 | 0.954 | 2.86 |
| irradiance Low, temperature Low → power Low | 1403 | 0.266 | 0.968 | 2.90 |

**Two findings worth reporting.** First, a temperature effect in Golden:
`irradiance Medium, temperature High → power Medium` (support 0.124,
confidence 0.987, lift 2.96) — at medium irradiance, hot hours do *not* reach
high power, consistent with heat reducing panel efficiency. Second, in Las
Vegas low humidity strengthens the high-irradiance → high-power rule, which
makes physical sense: low humidity marks clear desert skies. A caveat for
System 1403: because temperature there is module temperature, which heats up
with irradiance, temperature rules on that system are partly a consequence of
irradiance, not an independent cause.

## 6. Anomaly detection: power that does not match the weather

**Method.** Daytime hours only, from `data/processed/`
(`scripts/anomaly.py`). Features, standardised per system: power per kW,
irradiance, module temperature and the power/irradiance ratio. Ambient
temperature was not used (unreliable in System 1403, missing in System 1278).
Two models, both set to flag 5% of hours: Isolation Forest
(200 trees) and One-Class SVM (RBF kernel, nu = 0.05). Output:
`outputs/anomaly_report.json`, `outputs/anomaly_system_<id>.csv`,
figures in `outputs/anomaly_system_<id>.png`.

**No accuracy percentage is reported**, because there are no ground-truth
labels. Anomalies are evaluated by (1) whether they match known incidents,
(2) whether they have a physical explanation, and (3) whether the alert rate
is reasonable.

**Result.** Isolation Forest flagged almost exactly 5% of daytime hours in
each system — 187 hours in System 4 (5.01%), 200 in System 1278 (5.01%) and
191 in System 1403 (5.00%). One-Class SVM flagged 185, 204 and 191 hours.
The two models agreed on 94.8–96.3% of hours, and both flagged the same
88, 128 and 118 hours respectively. Only 27–37% of the broad IQR outliers
from §3 were flagged by Isolation Forest, confirming that the IQR rule was
the looser of the two.

**Case studies (known incidents).**

| Case | What happened | Isolation Forest | One-Class SVM |
|---|---|---|---|
| System 4: 28 hours with irradiance > 800 W/m² but power < 10% of capacity | Multi-hour events, largest 17 Feb (5 h); also 2 Mar, 29 Jun, 28 Nov, 30 Nov 2015 | **28 / 28 flagged** | 24 / 28 |
| System 1403, 15 Jun 2015: inverter 1 = 0 all day, inverter 2 normal | Power about half normal | 7 / 12 daytime hours | 5 / 12 |
| System 1278, 3 Jul 2015: raw file only 68 of 96 rows | Much of the day missing entirely | 3 / 12 daytime hours present | 5 / 12 |

The Golden case is a clean recovery: every known high-irradiance/low-power
hour was flagged, including the most extreme hour, 2 March 12:00 — irradiance
1,244 W/m² with only 70 W/kW (ratio 0.057). Note that irradiance above
1,200 W/m² is itself very high and may reflect cloud-edge enhancement or a
sensor effect, which the report records rather than hides. The Cocoa Beach
inverter failure was only partly detected, because with one inverter still
running, power was about half normal and some hours stayed inside the normal
distribution. The clearest outages of the whole year were in fact in Cocoa
Beach on 5–6 November: on 5 November power was 0 all day while irradiance
reached 978 W/m² at midday, and on 6 November power stayed 0 through 11:00
(irradiance 968 W/m²) before partly recovering from 12:00, plus 9 March 14:00
(0 W/kW at 861 W/m²). The Las Vegas case
shows a genuine limitation: hours that are missing entirely cannot be flagged
by a model that only sees present rows — missingness itself is the anomaly,
and it must be caught by the completeness checks in §3, not by Isolation Forest.

**Limitation.** Isolation Forest flags both tails of the distribution: hours
with power far too low for the irradiance (likely faults) *and* hours with an
unusually high power/irradiance ratio, such as 07:00–08:00 hours in
November–December in Las Vegas (ratio ≈ 0.9–1.07 at low irradiance), which are
probably sunrise hours rather than faults. Flagged hours therefore need the
physical review done above; the model alone does not distinguish a fault from
an edge of the distribution.

## 7. Conclusion

1. **Days fall into two types** — high-output and low-output — in all three
   systems (K-Means, k = 2, silhouette 0.35–0.46). In Las Vegas the split is
   seasonal; in Golden and Cocoa Beach it is driven by clouds as well as season.
2. **Irradiance dominates power output.** High irradiance implies high power
   with confidence 0.92–0.95 and lift 2.76–2.86 in every system; low irradiance
   implies low power with similar strength. Temperature and humidity refine the
   picture (heat limits output at medium irradiance in Golden; low humidity
   marks clear skies in Las Vegas) but do not overturn it.
3. **Anomalies are real and checkable.** Isolation Forest and One-Class SVM
   agree on ~95% of hours at a 5% flag rate, recover all 28 known
   high-irradiance/low-power hours in Golden, and expose complete midday
   outages in Cocoa Beach (5–6 November) that were not in the original case list.

**Limitations.** (a) Daily patterns are a continuum, so clustering quality is
moderate (silhouette 0.35–0.46). (b) Association rules use per-system tertiles,
so "High" means something different in each climate; thresholds are recorded
in the report JSON. (c) For System 1403, temperature rules use module
temperature, which partly follows irradiance. (d) Anomaly detection has no
ground-truth labels, so no accuracy is claimed; missing data cannot be flagged
by the models and must be caught by completeness checks. (e) Timestamps are
local time per site; cross-system comparison on timestamp was avoided.
(f) System 1403 carries a PVDAQ QA `fail` flag. (g) The analysis covers one
year, 2015, and three systems; results may not generalise to other years or
climates.

**What to do next.** Extend the same pipeline to a second year to test whether
the clusters and rules are stable; add a completeness-based anomaly score for
missing data (the Las Vegas 3 July case); and, for operations, turn the
Isolation Forest flag plus the physical rule "irradiance > 800 W/m² and power
< 10% of capacity" into a daily monitoring alert.

## References

1. NREL PVDAQ Public Datasets. DOI 10.25984/1846021, CC BY 4.0.
   https://data.openei.org/submissions/4568. Accessed 7 November 2026.
2. Data Mining Pipeline (DTSA 5504 / CSCA 5502), Data Mining Methods
   (DTSA 5505 / CSCA 5512), Data Mining Project (DTSA 5506 / CSCA 5522),
   *Data Mining Foundations and Practice*, University of Colorado Boulder,
   Coursera. Instructor: Qin (Christine) Lv.
3. Full data provenance: `docs/DATA_SOURCES.md` in the repository.

## Appendix — Reproducibility

| Step | Script | Output |
|---|---|---|
| Inspect one raw file | `scripts/read_raw.py --system 4 --date 2015-01-01` | terminal summary |
| Run the whole pipeline | `scripts/run_pipeline.py` | all generated data + `outputs/` |
| Inspect processed data | `scripts/inspect_data.py` | terminal summary of every generated file |
| Rebuild hourly data (2015) | `scripts/build_hourly_2015.py` | `data/hourly_full_year/` |
| Daily features | `scripts/build_daily_full_year.py` | `data/daily_full_year/` |
| Phase 1 preprocessing + outlier flags | `scripts/preprocess.py` | `data/processed/*_hourly_clean.csv`, `outputs/preprocess_report.json` |
| Phase 2 clustering | `scripts/clustering.py` | `data/processed/*_daily_features.csv`, `outputs/clustering_report.json`, `outputs/clustering_system_<id>.png` |
| Phase 3 association rules | `scripts/association.py` | `outputs/association_rules.csv`, `outputs/association_report.json` |
| Phase 4 anomaly detection | `scripts/anomaly.py` | `outputs/anomaly_report.json`, `outputs/anomaly_system_<id>.csv`, `outputs/anomaly_system_<id>.png` |

Run from the repository root after `pip install -r requirements.txt`
(pandas, numpy, scikit-learn, mlxtend, matplotlib). The single entry point is
`python scripts/run_pipeline.py`, which runs every step in order; afterwards
`python scripts/inspect_data.py` prints a summary of every generated file,
and the report numbers should be taken from that output or from the JSON files
in `outputs/`, not from memory.

**What is stored in git.** Data thô (`data/raw_full/`, `data/metadata/`), code
(`scripts/`), documentation, this report, all intermediate data
(`data/hourly_full_year/*.csv`, `data/daily_full_year/`, `data/processed/`)
and all results (`outputs/*.json`, `outputs/*.csv`) are stored in git, so a
reviewer can inspect every number without running code. All of those files
were generated by running `python scripts/run_pipeline.py` from the code in
this repository — rerun it to recreate them. Figures (PNG) are generated
locally by the scripts but are not stored on GitHub (the push tool only
accepts UTF-8 text files). Every number in §§2–6 comes from the files in the
table above, as generated by the pipeline.
