# Notebooks — chạy từng phần cho dễ xem và control

Mỗi notebook tương ứng một bước của pipeline. Mở notebook, chạy từng cell
(`Shift + Enter`) để xem kết quả ngay dưới mỗi cell: bảng, số liệu, biểu đồ.
Muốn chạy lại một phần thì chỉ cần chạy lại notebook đó, không cần chạy cả
pipeline.

## Thứ tự chạy

| Notebook | Nội dung | Script nó chạy |
|---|---|---|
| `00_data_overview.ipynb` | Xem data đã xử lý trước khi phân tích (theo giờ, theo ngày, tương quan, biểu đồ năng lượng cả năm) | — (chỉ đọc data đã có sẵn trong git) |
| `01_preprocessing.ipynb` | Phase 1: tiền xử lý + gắn cờ outlier | `scripts/preprocess.py` |
| `02_clustering.ipynb` | Phase 2: clustering ngày (K-Means/GMM, chọn k) | `scripts/clustering.py` |
| `03_association.ipynb` | Phase 3: luật kết hợp thời tiết → công suất | `scripts/association.py` |
| `04_anomaly.ipynb` | Phase 4: phát hiện bất thường (Isolation Forest + One-Class SVM) | `scripts/anomaly.py` |

Mỗi notebook (trừ 00) có một cell chạy script tương ứng bằng đúng Python của
kernel đang chạy (`sys.executable`), nên chạy notebook là chạy lại bước đó và
tạo lại file kết quả trong `data/` và `outputs/`. Các cell sau đó đọc kết quả
vừa tạo ra để xem: bảng, số liệu tóm tắt, biểu đồ.

## Cách mở

```bash
pip install -r requirements.txt   # đã có sẵn jupyter (notebook)
jupyter notebook                  # mở trong trình duyệt, rồi vào thư mục notebooks/
# hoặc: jupyter lab
```

Cũng mở được bằng VS Code (mở file `.ipynb`, chọn kernel Python của môi
trường đã cài `requirements.txt`). Kernel gợi ý: `Python (data-mining)`.

## Lưu ý

- Chạy notebook từ đúng thư mục `notebooks/` (mặc định khi mở bằng Jupyter).
  Notebook tự tìm thư mục gốc của repo từ vị trí của nó.
- Notebook đã chạy xong có kèm output (bảng, hình) lưu trong file `.ipynb`,
  mở trên GitHub là xem được ngay không cần chạy lại.
- Muốn chạy toàn bộ một lần thay vì từng phần: `python scripts/run_pipeline.py`
  ở thư mục gốc của repo (xem README chính, mục Cách chạy).
