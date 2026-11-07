# Mining Solar Power Generation Data for Pattern Discovery and Anomaly Detection

Bài tập cuối môn **Data Mining** — Specialization *Data Mining Foundations and Practice* (University of Colorado Boulder, Coursera, qua FPT University).

Mục tiêu: phân cụm mẫu phát điện theo ngày, tìm luật kết hợp giữa thời tiết và hiệu suất phát điện, và phát hiện bất thường khi công suất không khớp với bức xạ.

- Clustering: K-Means / GMM trên đặc trưng ngày
- Association rules: Apriori / FP-Growth sau khi rời rạc hoá thời tiết và công suất (Low / Medium / High), đánh giá bằng Support, Confidence, Lift
- Anomaly detection: Isolation Forest / One-Class SVM trên công suất so với bức xạ

## Nguồn dữ liệu

**NREL PVDAQ — Photovoltaic Data Acquisition, Public Datasets**

- Nguồn: National Renewable Energy Laboratory (NREL), U.S. Department of Energy
- DOI: `10.25984/1846021`
- Giấy phép: CC BY 4.0
- Landing page: https://data.openei.org/submissions/4568
- Data lake (S3, public): `s3://oedi-data-lake/pvdaq/csv/pvdata/system_id=<id>/year=<yyyy>/month=<m>/day=<d>/`
- Systems list: `https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv`
- Ngày truy cập / tải dữ liệu: 07/11/2026
- Nguồn chi tiết (từng hệ, hệ đã loại, cách trích dẫn): xem `docs/DATA_SOURCES.md`

Bộ data chốt để làm bài: **NREL PVDAQ, cả năm 2015, 3 hệ thống**. File thô gốc là 1 phút (System 4, 1403) hoặc 15 phút (System 1278).

Repo chỉ giữ bộ chốt này, cả thô và đã xử lý:
- **Data đã xử lý cả năm 2015** trong `data/hourly_full_year/` — 3 file theo giờ, 8.760 giờ/hệ (System 1403: 8.730 giờ, thiếu 30 giờ do 2 khoảng trống qua đêm tháng 4 và tháng 6), tổng 2,6 MB; và `data/daily_full_year/` — 3 file đặc trưng ngày, 365 ngày/hệ, tính từ bản theo giờ cả năm. Tên cột là chữ thường (`ac_power_w`, `poa_irradiance_wm2`, …). Chi tiết kiểm tra cả năm, quy tắc làm sạch và các caveat xem trong `data/hourly_full_year/README.md`; script tái tạo bản theo giờ ở `scripts/build_hourly_2015.py`. Timestamp là giờ địa phương từng bang, đừng merge 3 hệ theo timestamp khi chưa đổi về chung một múi giờ.
- **Data thô** trong `data/raw_full/` — 186 file ngày gốc PVDAQ tháng 1 và tháng 7/2015, giữ nguyên tên file và nội dung, tổng ~38,4 MB (System 4: 15,4 MB, System 1278: 1,1 MB, System 1403: 22,0 MB). Lưu ý: phần thô trong repo chỉ có tháng 1 + 7, chưa có thô cả năm; bản đã xử lý cả năm đã bao gồm các tháng còn lại.

## 3 hệ thống đã chốt

| System | Tên / địa điểm | Khí hậu | Công suất | Độ phân giải gốc | Cột chính |
|---|---|---|---|---|---|
| 4 | NREL x-Si -1, Golden, CO | BSk — bán khô lạnh | 1,0 kW | 1 phút, 17 cột | ac_power, dc_power, poa_irradiance, ambient_temp (°C), module_temp 1–3 |
| 1278 | Andre Agassi Preparatory Academy — Building D, Las Vegas, NV | BWh — sa mạc nóng | 171,36 kW | 15 phút, 28 cột | ac_power, dc_power, poa_irradiance, ambient_temp (°F → °C), module_temp (°F → °C), relative_humidity, wind_speed (mph → m/s) |
| 1403 | RTC-FSEC-Baseline, Cocoa Beach, FL | Cfa — ẩm cận nhiệt | 6,0 kW | 1 phút, 26 cột | inv1+inv2 ac_power (không có cột tổng), poa_irradiance, ambient_temp (°C), module_temp 1–8 |

Đa dạng cho report: 3 khí hậu BSk / BWh / Cfa, quy mô hệ chênh nhau 1 kW → 171 kW nên phải chuẩn hoá theo công suất định mức trước khi so sánh. Nhiệt độ môi trường System 1403 có xu hướng đọc cao trong mùa nóng — xem caveat trong `data/hourly_full_year/README.md`.

## Kết quả kiểm tra (cả năm 2015)

Xem đầy đủ trong `data/hourly_full_year/README.md`. Tóm tắt:

| System | Giờ cả năm | Thiếu giờ | Tương quan công suất–bức xạ ban ngày | Công suất max ban ngày |
|---|---|---|---|---|
| 4 | 8.760 | 0 | 0,942 | 942 W |
| 1278 | 8.760 | 22 giờ thiếu AC, nhiệt độ môi trường thiếu 719 giờ (8,2%, chủ yếu tháng 12) | 0,980 | 138.225 W |
| 1403 | 8.730 | 30 giờ (2 khoảng trống qua đêm tháng 4 và 6) | 0,964 | 6.168 W |

Cả 3 đều **đạt** để làm clustering / association / anomaly, với các lưu ý xử lý dưới đây — chính những điểm này là chất liệu cho phần tiền xử lý trong report.

### Vấn đề dữ liệu đã phát hiện — đừng xoá tự động

- **System 4:** bức xạ âm 47,1% số dòng (giá trị ban đêm khoảng −2 W/m², sai số cảm biến). Công suất âm chỉ 0,9%. → Clip bức xạ và công suất âm về 0 khi tính năng lượng, giữ lại để ghi nhận trong report.
- **System 1278:** công suất âm 50,4% số dòng, ban đêm khoảng −400 đến −1.100 W (inverter standby / offset). Nhiệt độ gốc là °F, gió là mph. → Đổi đơn vị, clip công suất đêm về 0, không dùng giá trị âm làm mẫu phát điện.
- **System 1403:** không có cột tổng công suất, phải cộng `inv1_ac_power + inv2_ac_power`. Cảm biến `module_temp_8` bị kẹt ở 3276,7 °C từ tháng 3 đến tháng 8/2015 — cảm biến hỏng, không phải nhiệt độ thật; bản cả năm đã loại giá trị trên 100 °C từng cảm biến rồi lấy **trung vị** của 8 cảm biến. Nhiệt độ môi trường đọc cao bất thường trong mùa nóng (tới 58 °C, có 1 spike 122,3 °C ngày 08/10/2015 đã loại theo quy tắc >80 °C). Hệ này trong danh sách systems của PVDAQ bị gắn QA `fail`, nhưng kiểm tra cả năm vẫn tương quan công suất–bức xạ 0,964 — vẫn dùng được, nhưng phải ghi rõ giới hạn này trong report.
- **Chung:** chỉ phân tích ban ngày (bức xạ > 50 W/m²) cho clustering / association; ban đêm công suất ≈ 0 là bình thường, không phải anomaly.

## Cấu trúc file

```
README.md                              # tổng quan, nguồn data, cách chạy
PLAN.md                                # kế hoạch từng phần (Phase 0-5)
requirements.txt                       # pandas, numpy, scikit-learn, mlxtend, matplotlib
docs/
  DATA_SOURCES.md                      # nguồn dữ liệu chi tiết + trích dẫn
data/
  raw_full/                            # data thô tháng 1 + 7/2015, 186 file, ~38,4 MB
    system_4/2015_01/  system_4/2015_07/
    system_1278/2015_01/  system_1278/2015_07/
    system_1403/2015_01/  system_1403/2015_07/
  hourly_full_year/                    # đã xử lý theo giờ, cả năm 2015
    system_4_2015_hourly.csv           # 8.760 giờ
    system_1278_2015_hourly.csv        # 8.760 giờ
    system_1403_2015_hourly.csv        # 8.730 giờ, thiếu 30 giờ
    README.md                          # kiểm tra cả năm + caveat
    systems.csv
  daily_full_year/                     # đặc trưng ngày, 365 ngày/hệ
    system_4_2015_daily.csv
    system_1278_2015_daily.csv
    system_1403_2015_daily.csv
  metadata/                            # 3 file JSON gốc của PVDAQ
    system_4_metadata.json
    system_1278_metadata.json
    system_1403_metadata.json
  processed/                           # đầu ra của scripts/preprocess.py
    system_4_2015_hourly_clean.csv
    system_1278_2015_hourly_clean.csv
    system_1403_2015_hourly_clean.csv
scripts/
  read_raw.py                          # đọc / xem 1 file data thô
  build_hourly_2015.py                 # tái tạo bản theo giờ cả năm từ S3
  build_daily_full_year.py             # tính đặc trưng ngày từ bản theo giờ
  preprocess.py                        # Phase 1: tiền xử lý + gắn cờ outlier
outputs/
  preprocess_report.json               # báo cáo Phase 1 (số giờ thiếu, outlier...)
  clustering_report.json               # báo cáo Phase 2 (chọn k, mô tả cụm)
  clustering_system_4.png              # biểu đồ elbow/silhouette + cụm (tạo local, xem PLAN.md)
  clustering_system_1278.png
  clustering_system_1403.png
```

Cột chung trong file hourly cả năm: `timestamp, ac_power_w, dc_power_w, poa_irradiance_wm2, ambient_temp_c, module_temp_c, n_samples` (System 1278 thêm độ ẩm và gió, System 1403 thêm `poa_refcell_wm2`).

Cột trong file daily cả năm: `date, system_id, n_hours, energy_kWh, ac_power_mean_W, ac_power_max_W, ac_power_std_W, poa_irradiance_mean_Wm2, poa_irradiance_max_Wm2, ambient_temp_mean_C, ambient_temp_max_C, ambient_temp_min_C, module_temp_mean_C, daytime_hours_irr_gt_50, daytime_ac_power_mean_W, daytime_irr_mean_Wm2`.

Lưu ý: `ac_power_w` của System 1403 là tổng 2 inverter, không phải cột gốc; `dc_power_w` của System 1403 không có trong bản cả năm.

## Cách chạy

```bash
pip install -r requirements.txt
python scripts/read_raw.py --system 4 --date 2015-01-01   # xem 1 file data thô
python scripts/preprocess.py                              # Phase 1: tiền xử lý + outlier
python scripts/build_daily_full_year.py                   # tính lại đặc trưng ngày
```

Lộ trình làm từng phần xem `PLAN.md` (Phase 2 clustering, Phase 3 association,
Phase 4 anomaly, Phase 5 report).

## Cách tái tạo dữ liệu

Tải lại dữ liệu gốc từ S3 public của OEDI theo đường dẫn ở mục Nguồn dữ liệu, tổng hợp theo giờ (trung bình), chuẩn hoá đơn vị như trên, rồi tính đặc trưng ngày bằng các script trong `scripts/`. Dữ liệu trong repo là kết quả đã kiểm tra ngày 07/11/2026.

## Trích dẫn

NREL PVDAQ Public Datasets, DOI 10.25984/1846021, CC BY 4.0.
