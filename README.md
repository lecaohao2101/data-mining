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

Phạm vi lấy trong repo này: **tháng 1 và tháng 7 năm 2015** (mùa đông + mùa hè, 62 ngày / hệ), 3 hệ thống. File thô gốc là 1 phút (System 4, 1403) hoặc 15 phút (System 1278), dung lượng hàng trăm MB–GB cho cả năm, nên repo chỉ giữ bản **tổng hợp theo giờ** và **đặc trưng theo ngày** đã chuẩn hoá đơn vị, cộng 1 ngày thô mẫu mỗi hệ để đối chiếu.

## 3 hệ thống đã chốt

| System | Tên / địa điểm | Khí hậu | Công suất | Độ phân giải gốc | Cột chính |
|---|---|---|---|---|---|
| 4 | NREL x-Si -1, Golden, CO | BSk — bán khô lạnh | 1,0 kW | 1 phút, 17 cột | ac_power, dc_power, poa_irradiance, ambient_temp (°C), module_temp 1–3 |
| 1278 | Andre Agassi Preparatory Academy — Building D, Las Vegas, NV | BWh — sa mạc nóng | 171,36 kW | 15 phút, 28 cột | ac_power, dc_power, poa_irradiance, ambient_temp (°F → °C), module_temp (°F → °C), relative_humidity, wind_speed (mph → m/s) |
| 1403 | RTC-FSEC-Baseline, Cocoa Beach, FL | Cfa — ẩm cận nhiệt | 6,0 kW | 1 phút, 26 cột | inv1+inv2 ac_power (không có cột tổng), poa_irradiance, ambient_temp (°C), module_temp 1–8 |

Đa dạng cho report: nhiệt độ trung bình Jan+Jul lần lượt 12,4 °C (Golden), 21,0 °C (Las Vegas), 34,3 °C (Cocoa Beach, cảm biến có xu hướng đọc cao — xem dưới); bức xạ trung bình 193 / 268 / 212 W/m²; quy mô hệ chênh nhau 1 kW → 171 kW nên phải chuẩn hoá theo công suất định mức (`ac_power_per_kW`) trước khi so sánh.

## Kết quả kiểm tra (tháng 1 + 7/2015, 62 ngày / hệ)

Xem đầy đủ số liệu trong `data/data_check_report.json`. Tóm tắt:

| System | Dòng mẫu | Ngày thiếu | Thiếu power / bức xạ / nhiệt độ | Tương quan công suất–bức xạ ban ngày (bức xạ > 50) | Công suất max |
|---|---|---|---|---|---|
| 4 | 89.280 | 0 | 0% / 0% / 0% | 0,961 | 1.059 W |
| 1278 | 5.884 | 0 | 1,07% / 1,07% / 1,07% | 0,937 | 141.700 W |
| 1403 | 89.280 | 0 | 0% / 0% / 0% | 0,976 | 6.170 W (tổng 2 inverter) |

Cả 3 đều **đạt** để làm clustering / association / anomaly, với các lưu ý xử lý dưới đây — chính những điểm này là chất liệu cho phần tiền xử lý trong report.

### Vấn đề dữ liệu đã phát hiện — đừng xoá tự động

- **System 4:** bức xạ âm 47,1% số dòng (giá trị ban đêm khoảng −2 W/m², sai số cảm biến). Công suất âm chỉ 0,9%. → Clip bức xạ và công suất âm về 0 khi tính năng lượng, giữ lại để ghi nhận trong report.
- **System 1278:** công suất âm 50,4% số dòng, ban đêm khoảng −400 đến −1.100 W (inverter standby / offset). Nhiệt độ gốc là °F, gió là mph. → Đổi đơn vị, clip công suất đêm về 0, không dùng giá trị âm làm mẫu phát điện.
- **System 1403:** không có cột tổng công suất, phải cộng `inv1_ac_power + inv2_ac_power`. Cảm biến `module_temp_8` bị kẹt ở 3276,7 °C trong một số ngày tháng 7 (ví dụ 21/07/2015) — cảm biến hỏng, không phải nhiệt độ thật. Nhiệt độ môi trường đọc cao bất thường (trung bình 34,3 °C, max 59,1 °C; đêm tháng 1 đã ~27 °C trong khi module ~19 °C). Trong file đã xử lý, `module_temp_C` dùng **trung vị** của 8 cảm biến thay vì trung bình, để một cảm biến hỏng không kéo lệch cả hệ. Hệ này trong danh sách systems của PVDAQ bị gắn QA `fail` ở phạm vi toàn bộ thời gian, nhưng mẫu Jan+Jul 2015 kiểm tra thực tế là 0% thiếu và tương quan cao nhất (0,976) — vẫn dùng được, nhưng phải ghi rõ giới hạn này trong report.
- **Chung:** chỉ phân tích ban ngày (bức xạ > 50 W/m²) cho clustering / association; ban đêm công suất ≈ 0 là bình thường, không phải anomaly.

## Cấu trúc file

```
data/
  hourly/
    system_4_2015_jan_jul_hourly.csv      # 1.488 giờ, Jan+Jul 2015
    system_1278_2015_jan_jul_hourly.csv   # 1.488 giờ, trong đó 1 giờ (03/07/2015 15:00) thiếu dữ liệu gốc
    system_1403_2015_jan_jul_hourly.csv   # 1.488 giờ
  daily/
    system_4_2015_jan_jul_daily.csv       # 62 ngày: năng lượng, peak, mean/max/std, giờ nắng
    system_1278_2015_jan_jul_daily.csv
    system_1403_2015_jan_jul_daily.csv
  metadata/
    system_4_metadata.json
    system_1278_metadata.json
    system_1403_metadata.json
  raw_samples/
    sys4_20150101.csv
    sys1278_20150101.csv
    sys1403_20150101.csv                  # 1 ngày thô gốc mỗi hệ, 01/01/2015
  data_check_report.json
  build_summary.json
```

Cột chung trong file hourly: `timestamp, system_id, ac_power_W, dc_power_W, poa_irradiance_Wm2, ambient_temp_C, module_temp_C, relative_humidity_pct, wind_speed_ms, ac_power_per_kW, poa_irradiance_clipped, ac_power_clipped_W`.

Cột trong file daily: `date, system_id, n_records, energy_kWh, ac_power_mean_W, ac_power_max_W, ac_power_std_W, poa_irradiance_mean_Wm2, poa_irradiance_max_Wm2, ambient_temp_mean_C, ambient_temp_max_C, ambient_temp_min_C, module_temp_mean_C, daytime_hours_irr_gt_50, daytime_ac_power_mean_W, daytime_irr_mean_Wm2`.

Lưu ý về `dc_power_W` của System 1403: tính gần đúng bằng V×I của 2 inverter, không phải cột gốc.

## Cách tái tạo

Tải lại dữ liệu gốc từ S3 public của OEDI theo đường dẫn ở mục Nguồn dữ liệu, tổng hợp theo giờ (trung bình), chuẩn hoá đơn vị như trên, rồi tính đặc trưng ngày. Script kiểm tra và build đã dùng nằm ngoài repo này; dữ liệu trong repo là kết quả đã kiểm tra ngày 07/11/2026.

## Trích dẫn

NREL PVDAQ Public Datasets, DOI 10.25984/1846021, CC BY 4.0.
