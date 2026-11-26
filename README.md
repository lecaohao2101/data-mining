# Mining Solar Power Generation Data for Pattern Discovery and Anomaly Detection

Mục tiêu: phân cụm mẫu phát điện theo ngày, tìm luật kết hợp giữa thời tiết và hiệu suất phát điện, và phát hiện bất thường khi công suất không khớp với bức xạ.

- Clustering: K-Means / GMM trên đặc trưng ngày
- Association rules: Apriori / FP-Growth sau khi rời rạc hoá thời tiết và công suất (Low / Medium / High), đánh giá bằng Support, Confidence, Lift
- Anomaly detection: Isolation Forest / One-Class SVM trên công suất so với bức xạ

## Dự án này làm gì

Khai phá 1 năm dữ liệu phát điện mặt trời (2015) của 3 hệ quang điện để trả lời 3 câu hỏi: ngày phát điện có mấy dạng, thời tiết nào kéo công suất lên hay xuống, và giờ nào công suất bất thường so với thời tiết — tức dấu hiệu hỏng hóc. Chỉ dùng các phương pháp đã học trong môn, không dùng deep learning.

**Câu hỏi nghiên cứu**

1. **Clustering:** ngày phát điện có những dạng nào lặp lại?
2. **Association rules:** điều kiện thời tiết nào gắn với công suất cao/thấp, và mạnh tới mức nào?
3. **Anomaly detection:** giờ nào công suất không khớp với bức xạ, và có đúng là sự cố thật không?

**Cách làm — pipeline 6 bước, chạy bằng `python scripts/run_pipeline.py`**

1. Tải data thô 2015 từ S3 public của NREL, tổng hợp theo giờ.
2. Tính đặc trưng ngày (năng lượng/kW, công suất đỉnh, giờ ban ngày, bức xạ, nhiệt độ, độ biến động).
3. Tiền xử lý + gắn cờ outlier (Phase 1): clip giá trị âm về 0, loại nhiệt độ bất khả thi, chỉ phân tích giờ ban ngày.
4. Clustering K-Means + GMM, k = 2–6, chọn theo silhouette và BIC (Phase 2).
5. Luật kết hợp Apriori + FP-Growth, rời rạc hoá Low/Medium/High theo tertile từng hệ (Phase 3).
6. Phát hiện bất thường Isolation Forest + One-Class SVM, cả hai cùng gắn cờ 5% giờ ban ngày (Phase 4).

Sau đó xem bằng `python scripts/inspect_data.py` rồi mới viết báo cáo. Mọi data đã xử lý và kết quả đều do code tạo ra, không làm tay.

**Kết quả chính**

- **Clustering: k = 2 ở cả 3 hệ** (silhouette 0,457 / 0,445 / 0,349) — ngày công suất cao và ngày công suất thấp. Ở Las Vegas sự phân chia theo mùa; ở Golden và Cocoa Beach còn do mây.
- **Luật kết hợp: 179 luật** (26 / 111 / 42). Bức xạ cao → công suất cao, confidence 0,92–0,95, lift 2,76–2,86 ở cả 3 hệ. Nhiệt độ cao làm giảm công suất ở Golden; độ ẩm thấp đi kèm trời quang ở Las Vegas.
- **Bất thường: Isolation Forest gắn cờ ~5% giờ ban ngày** (187 / 200 / 191 giờ), đồng thuận với One-Class SVM 94,8–96,3%. Thu hồi đủ 28/28 giờ bức xạ cao/công suất thấp ở Golden. Không báo tỉ lệ chính xác vì không có nhãn ground truth.
- **3 phát hiện mới trong đợt soát lại:** inverter 1 System 1403 chết 11–16/06, mất phát từ 09:00 ngày 04/11 tới 11:00 ngày 06/11, và khối toàn bộ kênh đọc 0 trong 44 giờ ngày 26–28/08.

**Đọc kết quả ở đâu:** báo cáo đầy đủ trong `reports/final_report.md` (bản PDF nộp là `final_report-2026-11-26.pdf`), số liệu trong `outputs/`, kế hoạch từng phase trong `PLAN.md`.

**Giới hạn:** cụm ngày là một dải liên tục nên silhouette chỉ ở mức vừa; luật dùng tertile riêng từng hệ nên "cao" mỗi nơi mỗi khác; System 1403 dùng nhiệt độ module và mang cờ QA `fail`; phân tích chỉ 1 năm 2015, 3 hệ.

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

**Quy tắc của repo này: data thô + code + kết quả + data trung gian đều nằm trong git — tất cả data đã xử lý đều do code tạo ra khi chạy pipeline.**
- **Data đã xử lý cả năm 2015** trong `data/hourly_full_year/` — 3 file theo giờ, 8.760 giờ/hệ (System 1403: 8.730 giờ, thiếu 30 giờ do 2 khoảng trống qua đêm tháng 4 và tháng 6), tổng 2,6 MB; và `data/daily_full_year/` — 3 file đặc trưng ngày, 365 ngày/hệ, tính từ bản theo giờ cả năm. **Các file này do code tạo ra khi chạy pipeline và CÓ trong git** (xem `.gitignore` và mục Cách chạy). Chạy `python scripts/run_pipeline.py` để tạo lại y hệt, rồi xem bằng `python scripts/inspect_data.py` trước khi viết report. **Kết quả cũng có trong git: `outputs/` (4 file report JSON, `association_rules.csv`, 3 file giờ anomaly)**, để người chấm xem trực tiếp mà không cần chạy code; chỉ biểu đồ PNG là không đẩy được lên git (công cụ push chỉ nhận file text) nên chạy lại script để xem. Tên cột là chữ thường (`ac_power_w`, `poa_irradiance_wm2`, …). Chi tiết kiểm tra cả năm, quy tắc làm sạch và các caveat xem trong `data/hourly_full_year/README.md`; script tái tạo bản theo giờ ở `scripts/build_hourly_2015.py`. Timestamp là giờ chuẩn địa phương từng bang (local standard time, không đổi theo DST — từ tháng 3 đến tháng 11 lệch 1 giờ so với giờ đồng hồ địa phương thật), đừng merge 3 hệ theo timestamp khi chưa đổi về chung một múi giờ.
- **Data thô** trong `data/raw_full/` — 186 file ngày gốc PVDAQ tháng 1 và tháng 7/2015, giữ nguyên tên file và nội dung, tổng ~38,4 MB (System 4: 15,4 MB, System 1278: 1,1 MB, System 1403: 22,0 MB). Lưu ý: phần thô trong repo chỉ có tháng 1 + 7, chưa có thô cả năm; bản đã xử lý cả năm đã bao gồm các tháng còn lại.

## Dữ liệu

Dữ liệu là số liệu đo thực tế từ 3 hệ điện mặt trời trong cơ sở dữ liệu công khai NREL PVDAQ. Mỗi dòng là 1 giờ: công suất phát điện, bức xạ mặt trời, nhiệt độ môi trường và nhiệt độ module, kèm số mẫu thô đã tổng hợp thành giờ đó. Phân tích dùng cả năm 2015 (01/01–31/12), timestamp là giờ chuẩn địa phương từng bang (local standard time, không đổi theo DST).

### Các biến chính

| Biến | Ý nghĩa | Ghi chú |
|---|---|---|
| `timestamp` | Giờ đo (giờ chuẩn địa phương từng bang) | 1 dòng = 1 giờ |
| `ac_power_w` | Công suất AC phát ra | System 1403 = tổng 2 inverter (không có cột tổng gốc) |
| `dc_power_w` | Công suất DC | System 1403 không có cột này |
| `poa_irradiance_wm2` | Bức xạ trên mặt phẳng tấm pin (POA) | Biến chính để so với công suất |
| `ambient_temp_c` | Nhiệt độ môi trường (°C) | System 1403 đọc cao bất thường mùa nóng |
| `module_temp_c` | Nhiệt độ module (°C) | Trung vị các cảm biến (8 ở System 1403, 3 ở System 4, 1 ở System 1278) |
| `n_samples` | Số mẫu thô đã tổng hợp thành giờ đó | 60 mẫu (đo 1 phút), 4 mẫu (đo 15 phút) |
| Riêng System 1278 | `relative_humidity_pct`, `wind_speed_ms`, `wind_direction_deg` | Độ ẩm, tốc độ + hướng gió |
| Riêng System 1403 | `poa_refcell_wm2` | Bức xạ đo bằng pin chuẩn |

### Các file dữ liệu trong repo

| Thư mục | Nội dung | Quy mô |
|---|---|---|
| `data/raw_full/` | File thô gốc PVDAQ, tháng 1 + 7/2015 | 186 file, ~38,4 MB |
| `data/hourly_full_year/` | Bản theo giờ cả năm 2015 + README kiểm tra + `systems.csv` | 3 file, 8.760 / 8.760 / 8.730 giờ |
| `data/daily_full_year/` | Đặc trưng ngày (năng lượng, công suất max/trung bình, bức xạ, nhiệt độ) | 3 file, 365 ngày/hệ |
| `data/processed/` | File clean theo giờ (thêm `power_per_kw`, `irr_ratio`, cờ outlier, z-score) + file daily_features (thêm cụm K-Means/GMM) | 3 + 3 file |
| `data/metadata/` | 3 file JSON gốc của PVDAQ (thông tin hệ, cảm biến) | 3 file |
| `outputs/` | Kết quả phân tích: 4 report JSON, `association_rules.csv` (179 luật), 3 file giờ anomaly | Xem mục Cấu trúc file |

### Tổng quan năm 2015

| Hệ | Giờ | Giờ ban ngày (bức xạ > 50 W/m²) | Năng lượng năm | Trung bình/ngày | Tương quan công suất–bức xạ |
|---|---|---|---|---|---|
| 4 | 8.760 | 3.736 | 1.436,8 kWh | 3,94 kWh | 0,942 |
| 1278 | 8.760 | 4.001 | 260.414,4 kWh | 713,46 kWh | 0,980 |
| 1403 | 8.730 | 3.818 | 9.067,6 kWh | 24,84 kWh | 0,964 |

System 1403 thiếu 30 giờ (2 khoảng trống qua đêm tháng 4 và tháng 6); System 1278 thiếu 22 giờ công suất AC. Các số trên tính trực tiếp từ file theo giờ trong repo (đã kiểm chứng lại ngày 25/11/2026). Chi tiết kiểm tra từng giờ và các caveat xem `data/hourly_full_year/README.md`; các vấn đề dữ liệu phát hiện được liệt kê ở mục dưới.

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
- **System 1403:** không có cột tổng công suất, phải cộng `inv1_ac_power + inv2_ac_power`. Cảm biến `module_temp_8` bị kẹt ở 3276,7 °C ngắt quãng từ tháng 3 đến tháng 8/2015 (0 mẫu kẹt ngày 10, 15, 31/07; 372/1.440 mẫu ngày 20/07; 507/1.440 mẫu ngày 25/07) — cảm biến hỏng, không phải nhiệt độ thật; bản cả năm đã loại giá trị trên 100 °C từng cảm biến rồi lấy **trung vị** của 8 cảm biến. Nhiệt độ môi trường đọc cao bất thường trong mùa nóng (tới 58 °C; trung bình giờ 11:00 ngày 08/10/2015 là 122,3 °C do 4 mẫu điên tới 3.006,2 °C, đã loại theo quy tắc >80 °C). Hệ này trong danh sách systems của PVDAQ bị gắn QA `fail`, nhưng kiểm tra cả năm vẫn tương quan công suất–bức xạ 0,964 — vẫn dùng được, nhưng phải ghi rõ giới hạn này trong report.
- **System 1403:** mất phát từ 09:00 ngày 04/11/2015 (08:00 còn 525 W), công suất 0 cả ngày 05/11 (bức xạ tới 978 W/m²) tới 11:00 ngày 06/11 — ca mất phát rõ nhất cả năm, xem §6 trong report.
- **System 1403:** 44 giờ liên tiếp toàn bộ kênh đọc 0, 26/08 15:00 – 28/08 10:00 (cả ngày 27/08 toàn 0) nhưng các dòng vẫn còn (n_samples 59–60/giờ) — logger có vẻ chết nhưng vẫn ghi số 0. Vì bức xạ đọc 0 nên các giờ này không vào tập phân tích ban ngày, mô hình anomaly không thấy được.
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
  clustering.py                        # Phase 2: clustering ngày
  association.py                       # Phase 3: luật kết hợp
  anomaly.py                           # Phase 4: phát hiện bất thường
  run_pipeline.py                      # chạy toàn bộ pipeline theo thứ tự
  inspect_data.py                      # xem tóm tắt mọi data đã xử lý
reports/
  final_report.md                      # báo cáo cuối môn (tiếng Anh, Phase 5)
outputs/
  preprocess_report.json               # báo cáo Phase 1 (số giờ thiếu, outlier...)
  clustering_report.json               # báo cáo Phase 2 (chọn k, mô tả cụm)
  clustering_system_4.png              # biểu đồ elbow/silhouette + cụm (tạo local, xem PLAN.md)
  clustering_system_1278.png
  clustering_system_1403.png
  association_rules.csv                # báo cáo Phase 3 (179 luật, Support/Confidence/Lift)
  association_report.json              # ngưỡng rời rạc hoá + 15 luật mạnh nhất mỗi hệ (System 4: 13 luật power)
  anomaly_report.json                  # báo cáo Phase 4 (IF + OC-SVM, case study)
  anomaly_system_4.csv                 # giờ bị Isolation Forest gắn cờ, System 4
  anomaly_system_1278.csv
  anomaly_system_1403.csv
```

Cột chung trong file hourly cả năm: `timestamp, ac_power_w, dc_power_w, poa_irradiance_wm2, ambient_temp_c, module_temp_c, n_samples` (System 1278 thêm độ ẩm và gió, System 1403 thêm `poa_refcell_wm2`).

Cột trong file daily cả năm: `date, system_id, n_hours, energy_kWh, ac_power_mean_W, ac_power_max_W, ac_power_std_W, poa_irradiance_mean_Wm2, poa_irradiance_max_Wm2, ambient_temp_mean_C, ambient_temp_max_C, ambient_temp_min_C, module_temp_mean_C, daytime_hours_irr_gt_50, daytime_ac_power_mean_W, daytime_irr_mean_Wm2`.

Lưu ý: `ac_power_w` của System 1403 là tổng 2 inverter, không phải cột gốc; `dc_power_w` của System 1403 không có trong bản cả năm.

## Cách chạy
```bash
# 1. Cài đặt 
pip install -r requirements.txt

# 2. Chạy toàn bộ pipeline — tạo ra mọi data đã xử lý + kết quả
python scripts/run_pipeline.py
# Chạy lại từ đầu: xóa data đã xử lý rồi chạy lại, kết quả ra y hệt
# (đã kiểm tra: data theo giờ khớp tới ~1e-12, association/anomaly giống hệt)

# 3. Xem data đã xử lý như thế nào, rồi mới viết report
python scripts/inspect_data.py
```

Pipeline chạy theo thứ tự: build hourly 2015 (tải từ S3 public) → đặc trưng ngày
→ tiền xử lý + outlier (Phase 1) → clustering (Phase 2) → luật kết hợp (Phase 3)
→ anomaly detection (Phase 4).

### Chạy từng bước riêng

```bash
# Xem data thô (tháng 1 + 7/2015 trong data/raw_full/)
python scripts/read_raw.py --system 4 --date 2015-01-01
python scripts/read_raw.py --system 1278 --list --month 2015-07
python scripts/read_raw.py --system 1403 --date 2015-06-15 --head 10

# Từng bước của pipeline (mỗi lệnh chạy độc lập, không cần đối số)
python scripts/build_hourly_2015.py    # data/hourly_full_year/
python scripts/build_daily_full_year.py # data/daily_full_year/
python scripts/preprocess.py           # Phase 1: data/processed/*_hourly_clean.csv
python scripts/clustering.py           # Phase 2: daily features + clustering_report.json
python scripts/association.py          # Phase 3: association_rules.csv
python scripts/anomaly.py              # Phase 4: anomaly_report.json + anomaly_system_*.csv

# Chạy lại chỉ một vài bước (khi đã có data hourly sẵn)
python scripts/run_pipeline.py --skip-hourly
python scripts/run_pipeline.py --only preprocess,clustering
python scripts/run_pipeline.py --only anomaly

# Chỉ xem một nhóm data đã xử lý
python scripts/inspect_data.py --only hourly
python scripts/inspect_data.py --only processed
python scripts/inspect_data.py --only outputs
```

Lộ trình làm từng phần xem `PLAN.md` (Phase 2 clustering, Phase 3 association,
Phase 4 anomaly, Phase 5 report).

## Notebooks — chạy từng phần cho dễ xem và control

Thư mục `notebooks/` có 5 notebook Jupyter, mỗi cái tương ứng một bước:

| Notebook | Nội dung |
|---|---|
| `00_data_overview.ipynb` | Xem data đã xử lý trước khi phân tích |
| `01_preprocessing.ipynb` | Phase 1: tiền xử lý + outlier |
| `02_clustering.ipynb` | Phase 2: clustering ngày |
| `03_association.ipynb` | Phase 3: luật kết hợp |
| `04_anomaly.ipynb` | Phase 4: phát hiện bất thường |

```bash
jupyter notebook   # mở trong trình duyệt, rồi vào thư mục notebooks/
```

Mỗi notebook có một cell chạy script tương ứng rồi xem kết quả ngay dưới mỗi
cell (bảng, số liệu, biểu đồ). Muốn chạy lại một phần thì chỉ chạy lại
notebook đó. Chi tiết xem `notebooks/README.md`.

## Cách tái tạo dữ liệu

Tải lại dữ liệu gốc từ S3 public của OEDI theo đường dẫn ở mục Nguồn dữ liệu, tổng hợp theo giờ (trung bình), chuẩn hoá đơn vị như trên, rồi tính đặc trưng ngày bằng các script trong `scripts/`. Dữ liệu trong repo là kết quả đã kiểm tra ngày 07/11/2026 và kiểm chứng lại ngày 25/11/2026 (tổng năng lượng, số giờ ban ngày, tương quan, 179 luật khớp tới 0,1 kWh; các mâu thuẫn thời gian đã sửa, xem commit mới nhất).

## Trích dẫn

NREL PVDAQ Public Datasets, DOI 10.25984/1846021, CC BY 4.0.
