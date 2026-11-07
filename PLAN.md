# Kế hoạch làm bài — Mining Solar Power Generation Data

Đề tài: **Mining Solar Power Generation Data for Pattern Discovery and Anomaly Detection**
Khung: Specialization *Data Mining Foundations and Practice* (University of Colorado
Boulder, Coursera, qua FPT University), giảng viên Qin (Christine) Lv.
Data: NREL PVDAQ, cả năm 2015, 3 hệ (4 Golden CO, 1278 Las Vegas NV, 1403 Cocoa Beach FL).
Chi tiết nguồn data xem `docs/DATA_SOURCES.md`. Cấu trúc repo và cách chạy xem `README.md`.

## Khung khóa học (để đối chiếu)

| Khóa | Nội dung liên quan trực tiếp tới bài này |
|---|---|
| **Data Mining Pipeline** (DTSA 5504) — W1 Introduction, W2 Data Understanding, W3 Data Preprocessing, W4 Data Warehousing / OLAP | W2–W3 là Phần 1: hiểu data, tiền xử lý, outlier |
| **Data Mining Methods** (DTSA 5505) — M1 Frequent Pattern Analysis (Apriori, FP-Growth), M2 Classification, M3 Clustering, M4 Outlier Analysis | M1 là Phần 3, M3 là Phần 2, M4 là Phần 4 |
| **Data Mining Project** (DTSA 5506) — W1 Introduction / brainstorming, W2 Proposal, W3 Checkpoint, W4 Final Report | W2–W4 là Phần 5: proposal, checkpoint, report cuối |

Đánh giá từ link ChatGPT đã xem (chỉ có 1 phản hồi đánh giá, không có deadline/code):
đề tài khớp tốt vì dùng đủ 3 nhóm kỹ thuật của Methods; điểm yếu là tính mới thấp,
khó nhất là tìm dataset có công suất + thời tiết đồng bộ theo thời gian; anomaly
detection **không có nhãn ground-truth nên không được báo % accuracy** — đánh giá
bằng tính hợp lý của các ca phát hiện được. Không thêm Deep Learning / LSTM.

## Phase 0 — Data (đã xong, 07/11/2026)

- Chọn 3 hệ PVDAQ, kiểm tra Jan+Jul rồi cả năm 2015, đẩy lên GitHub.
- Giữ lại cả thô (`data/raw_full/`, tháng 1+7) và đã xử lý (`data/hourly_full_year/`,
  `data/daily_full_year/`, `data/metadata/`).
- Script: `scripts/read_raw.py`, `scripts/build_hourly_2015.py`,
  `scripts/build_daily_full_year.py`.

## Phase 1 — Tiền xử lý + outlier (đã xong, 07/11/2026)

- Script: `scripts/preprocess.py` → `data/processed/system_<id>_2015_hourly_clean.csv`
  + `outputs/preprocess_report.json`.
- Quy tắc: không xoá outlier tự động, chỉ gắn cờ; nhiệt độ > 80 °C / module > 100 °C
  về NaN; chỉ phân tích ban ngày (bức xạ > 50 W/m²); chuẩn hoá z-score cho clustering.
- Kết quả: System 4: 537/3.736 giờ ban ngày bị gắn cờ IQR (14,4%), trong đó 28 giờ
  bức xạ > 800 nhưng công suất < 10% định mức; System 1278: 405/4.001 (10,1%), 0 giờ
  bức xạ cao/công suất thấp; System 1403: 405/3.818 (10,6%), 8 giờ bức xạ cao/công suất thấp.
  Tỉ lệ IQR cao là do tỉ số công suất/bức xạ dao động theo mây/nhiệt độ — đây là
  **ứng viên**, không phải kết luận anomaly; Phần 4 sẽ kiểm chứng bằng Isolation Forest.

## Phase 2 — Clustering (đã xong, 07/11/2026)

- **Mục tiêu:** phân cụm ngày theo mẫu phát điện.
- **Input:** đặc trưng ngày tính từ `data/processed/` (Phase 1).
- **Phương pháp:** K-Means và GMM (Methods M3), chuẩn hoá trước, thử k = 2–6.
- **Script:** `scripts/clustering.py` → `outputs/clustering_report.json`,
  `outputs/clustering_system_<id>.png` (biểu đồ, tạo local — GitHub chỉ nhận file text
  nên PNG không đẩy lên được qua công cụ hiện tại, chạy lại script là có),
  `data/processed/system_<id>_2015_daily_features.csv`.
- **Kết quả:** K-Means chọn **k = 2 cho cả 3 hệ** (silhouette: System 4: 0,457;
  System 1278: 0,445; System 1403: 0,349; k = 3–6 đều thấp hơn rõ).
  GMM theo BIC thì chọn k = 5–6 — BIC giảm dần theo k, tức GMM chia nhỏ thêm
  theo mùa chứ không tìm ra cụm tách biệt mới, nên vẫn giữ k = 2 của K-Means.
- **Mô tả cụm (K-Means, k = 2):**
  - System 4: cụm cao 274 ngày (4,81 kWh/kW, bức xạ 572 W/m², nắng 10,8 h, 14,5 °C),
    cụm thấp 91 ngày (1,32 kWh/kW, bức xạ 256 W/m², nắng 8,5 h, 2,7 °C) — cụm thấp
    tập trung mùa đông (tháng 1, 2, 12) nhưng vẫn rải rác cả năm, tức do mây/tuyết
    chứ không chỉ do mùa.
  - System 1278: cụm cao 214 ngày (5,16 kWh/kW, bức xạ 692 W/m², 27,2 °C),
    cụm thấp 151 ngày (2,75 kWh/kW, bức xạ 521 W/m², 12,1 °C) — phân tách rõ
    theo mùa: cụm cao gần như toàn tháng 3–10, cụm thấp toàn tháng 11–2.
  - System 1403: cụm cao 251 ngày (4,89 kWh/kW, bức xạ 553 W/m²),
    cụm thấp 114 ngày (2,48 kWh/kW, bức xạ 345 W/m²) — cụm thấp rải đều cả năm,
    nhiều nhất tháng 12 (20 ngày), tức do mây/mưa Florida chứ không chỉ mùa đông.
- **Kiểm chứng:** cụm giải thích được bằng thời tiết (bức xạ + nhiệt độ + tháng);
  các ngày năng lượng thấp dù bức xạ cao (vd System 4 ở bức xạ ~700–800 W/m² mà
  chỉ ~1–2 kWh/kW) là ứng viên anomaly cho Phase 4.
- **Hạn chế ghi vào report:** mẫu ngày là một dải liên tục theo mùa/bức xạ, không
  phải các cụm tách biệt rõ — silhouette 0,35–0,46 là trung bình, k = 2 là lựa
  chọn đơn giản và vững nhất, không nên ép k lớn hơn chỉ để có nhiều cụm.

## Phase 3 — Association rules (đã xong, 07/11/2026)

- **Mục tiêu:** luật thời tiết → phát điện.
- **Input:** `data/processed/` giờ ban ngày.
- **Phương pháp:** rời rạc hoá Low / Medium / High theo phân vị 1/3 và 2/3 riêng
  từng hệ — Apriori và FP-Growth (Methods M1), min_support = 0,05, max_len = 3.
  Hai thuật toán cho cùng tập frequent itemset (đã kiểm tra bằng assert trong code).
- **Script:** `scripts/association.py` → `outputs/association_rules.csv`
  (179 luật), `outputs/association_report.json`.
- **Đánh giá:** chỉ giữ luật Lift > 1, Confidence >= 0,5, Support >= 0,05.
- **Kết quả:** System 4: 26 luật; System 1278: 111 luật (có thêm độ ẩm + gió);
  System 1403: 42 luật. Lift cao nhất ~2,9–3,0.
- **Luật mạnh nhất (consequent là công suất):**
  - Cả 3 hệ: `irr=High => power=High` (conf 0,94–0,95, lift ~2,85) và
    `irr=Low => power=Low` (conf 0,92–0,95, lift ~2,8) — bức xạ quyết định công suất.
  - System 4: `irr=High, temp=Medium => power=High` (conf 0,998, lift 2,99);
    `irr=Medium, temp=High => power=Medium` (conf 0,987) — bức xạ vừa mà trời
    nóng cũng không lên được công suất cao, phù hợp với hiệu ứng nhiệt làm giảm
    hiệu suất pin.
  - System 1278: `humidity=Low, irr=High => power=High` (conf 0,954) — độ ẩm thấp
    là dấu hiệu trời quang ở sa mạc; `irr=High, wind=Medium => power=High`
    (conf 0,949). Đã bỏ 223 giờ ban ngày thiếu nhiệt độ môi trường (chủ yếu tháng 12).
  - System 1403: `irr=Low, temp=Low => power=Low` (conf 0,968, lift 2,90).
- **Lưu ý ghi vào report:** System 1403 dùng `module_temp_c` thay cho
  `ambient_temp_c` (cảm biến môi trường đọc cao); nhiệt độ module nóng lên theo
  bức xạ nên luật có temp ở hệ này một phần là hệ quả của bức xạ, không phải
  nguyên nhân độc lập. System 1278 nhiệt độ môi trường thiếu 719 giờ, chủ yếu tháng 12.

## Phase 4 — Anomaly detection

- **Mục tiêu:** tìm giờ/ngày công suất không khớp với thời tiết.
- **Input:** `data/processed/` giờ ban ngày + cờ outlier từ Phase 1.
- **Phương pháp:** Isolation Forest và One-Class SVM (Methods M4), đặc trưng:
  công suất/kW, bức xạ, nhiệt độ module, tỉ số công suất/bức xạ.
- **Script:** `scripts/anomaly.py` → `outputs/anomaly_report.json`.
- **Case study bắt buộc:** System 1403 ngày 15/06/2015 (inverter 1 = 0 cả ngày),
  System 1278 ngày 03/07/2015 (chỉ 68/96 dòng thô, thiếu nhiều),
  System 4 các giờ bức xạ cao/công suất thấp mùa đông.
- **Đánh giá:** KHÔNG báo % accuracy (không có nhãn). Đánh giá bằng: ca phát hiện
  có khớp với sự cố đã biết không, có giải thích vật lý không, tỉ lệ cảnh báo
  có hợp lý không (không phải 30–40% số giờ).
- **Xong khi:** có danh sách anomaly theo từng hệ + 3–5 ca phân tích chi tiết.

## Phase 5 — Report (Project W2–W4)

- **Proposal (W2):** đề tài, mục tiêu, data, phương pháp — viết từ README + PLAN này.
- **Checkpoint (W3):** kết quả Phase 1–2 + 1–2 kết quả sơ bộ Phase 3–4.
- **Final Report (W4):** cấu trúc gợi ý —
  1. Giới thiệu + câu hỏi nghiên cứu
  2. Nguồn dữ liệu (trích dẫn DOI, xem `docs/DATA_SOURCES.md`)
  3. Tiền xử lý + vấn đề dữ liệu (Phase 1)
  4. Clustering (Phase 2)
  5. Association rules (Phase 3)
  6. Anomaly detection (Phase 4)
  7. Kết luận + hạn chế (múi giờ địa phương, cảm biến lỗi, không có nhãn anomaly)
- **Xong khi:** report nộp được, mọi số liệu trong report đều truy được về
  file trong `data/` hoặc `outputs/`.

## Thứ tự làm

Phase 2 → Phase 3 → Phase 4 → Phase 5. Mỗi phase xong mới sang phase sau,
vì Phase 3–4 đều dùng `data/processed/` của Phase 1.
