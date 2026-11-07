# Nguồn dữ liệu

## Nguồn chính — NREL PVDAQ

- **Tên đầy đủ:** Photovoltaic Data Acquisition (PVDAQ) Public Datasets
- **Tổ chức:** National Renewable Energy Laboratory (NREL), U.S. Department of Energy
- **DOI:** `10.25984/1846021`
- **Giấy phép:** CC BY 4.0 (ghi công khi sử dụng)
- **Landing page:** https://data.openei.org/submissions/4568
- **Trang giới thiệu:** https://www.nrel.gov/pv/pvdaq.html (ngày 07/11/2026 trang này
  không truy cập được do lỗi DNS, nên thông tin nguồn được xác minh qua Data.gov,
  OpenEI và tài liệu OpenEDI — xem ghi chú dưới)
- **Data.gov:** "Photovoltaic Data Acquisition (PVDAQ) Public Datasets",
  cập nhật lần cuối 31/07/2025
- **Data lake (S3, public, không cần đăng nhập):**
  `s3://oedi-data-lake/pvdaq/csv/pvdata/system_id=<id>/year=<yyyy>/month=<m>/day=<d>/`
  `https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/pvdata/...`
- **Danh sách hệ thống:** `https://oedi-data-lake.s3.amazonaws.com/pvdaq/csv/systems_20250729.csv`
- **Metadata từng hệ:** `pvdaq/csv/system_metadata/<id>_system_metadata.json`
- **Tài liệu:** https://github.com/openEDI/documentation/blob/main/pvdaq.md ,
  https://openei.org/wiki/PVDAQ
- **Ngày truy cập / tải dữ liệu:** 07/11/2026
- **Trích dẫn:** NREL PVDAQ Public Datasets, DOI 10.25984/1846021, CC BY 4.0.

## 3 hệ thống đã chọn

| System | Tên / địa điểm | Khí hậu | Công suất | Độ phân giải gốc | QA trong systems list |
|---|---|---|---|---|---|
| 4 | NREL x-Si -1, Golden, CO (39.7406, -105.1774) | BSk — bán khô lạnh | 1,0 kW | 1 phút, 17 cột | pass |
| 1278 | Andre Agassi Preparatory Academy — Building D, Las Vegas, NV (36.1952, -115.1582) | BWh — sa mạc nóng | 171,36 kW | 15 phút, 28 cột | pass |
| 1403 | RTC-FSEC-Baseline, Cocoa Beach, FL (28.405, -80.7709) | Cfa — ẩm cận nhiệt | 6,0 kW | 1 phút, 26 cột | fail — dùng thận trọng, ghi rõ trong report |

## Phạm vi dữ liệu trong repo

- **Cả năm 2015, đã xử lý:** `data/hourly_full_year/` (8.760 giờ/hệ, System 1403:
  8.730 giờ) và `data/daily_full_year/` (365 ngày/hệ). Đây là bộ chính để phân tích.
- **Data thô:** `data/raw_full/` chỉ có **tháng 1 và tháng 7/2015** (186 file, 31 ngày/tháng/hệ,
  ~38,4 MB, giữ nguyên nội dung gốc). Chưa có data thô cả năm trong repo; bản đã xử lý
  cả năm được tái tạo từ S3 public bằng `scripts/build_hourly_2015.py`.
- **Metadata:** `data/metadata/` — 3 file JSON gốc của PVDAQ cho 3 hệ.
- **Lưu ý múi giờ:** timestamp là giờ địa phương từng bang (Golden / Las Vegas /
  Cocoa Beach khác nhau). Đừng merge 3 hệ theo timestamp khi chưa đổi về chung
  một múi giờ.

## Các hệ đã loại (để khỏi làm lại)

- **System 1300, St Petersburg, FL:** QA fail, có đợt mất dữ liệu dài — không dùng làm hệ chính.
- **System 1199, Hunt Valley, MD:** file thô chỉ có kênh điện của inverter, không có
  bức xạ / nhiệt độ / độ ẩm / gió — không đủ cho luật kết hợp thời tiết–phát điện.
- **NIST 4901–4903:** mẫu tháng 6 có sentinel -999 và POA sai thang đo (max 12,1),
  QA cảnh báo tương quan < 0,5.

## Đề tài và khung chương trình

- **Đề tài:** "Mining Solar Power Generation Data for Pattern Discovery and
  Anomaly Detection" — đã chốt ngày 07/11/2026.
- **Khung chương trình:** Specialization *Data Mining Foundations and Practice*,
  University of Colorado Boulder, Coursera (qua FPT University), giảng viên
  Qin (Christine) Lv. Gồm 3 khóa: Data Mining Pipeline (DTSA 5504),
  Data Mining Methods (DTSA 5505), Data Mining Project (DTSA 5506).
  Chi tiết từng phần và lộ trình làm việc xem `PLAN.md`.
