# Timestamp UTC và làm sạch session

Đối chiếu Notebook 01 trong snapshot NVIDIA `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, cell 12, 14 và 25 theo chỉ số từ 0. SHA-256 notebook khớp manifest nguồn.

Chạy trên CSV toàn tháng để đếm được dòng thiếu session. Raw subset tuần đã lọc các dòng này từ trước. Script chuyển `event_time` thành `event_time_ts` dạng số nguyên giây Unix UTC, dừng và ghi báo cáo nếu có timestamp lỗi. Sau đó bỏ dòng không có `user_session`. Với mỗi session, sắp theo timestamp và bỏ event nếu product bằng event liền trước, kể cả khi event type khác. Timestamp bằng nhau dùng thứ tự do engine cung cấp, không có khóa phụ CSV. Thứ tự vật lý trong Parquet không phải cam kết thứ tự sequence.

```bash
.venv/bin/python -m pip install -r pipeline/requirements-audit.txt
.venv/bin/python pipeline/preprocess_raw_events.py \
  --input /path/to/2019-Oct.csv --output-dir data/clean/month_cpu
```

Dùng thư mục đích mới khi chạy lại. Parquet và log đầy đủ nằm tại thư mục đích. Báo cáo nhỏ bàn giao tại `data/manifests/timestamp_session_cleanup.json`.

Lần chạy trên macOS arm64 dùng DuckDB CPU. Quyết định ngày 20/11/2026
chấp nhận DuckDB cho timestamp, cleanup và first-seen tháng, xem
[AGENTS.md](../AGENTS.md). Giữ ID session gốc để truy vết; timestamp trùng
theo hành vi DuckDB, không thêm khóa phụ CSV. Không cam kết output tương
đương cuDF. Train/inference model vẫn dùng NVIDIA runtime trên GPU.
Parquet này là bảng event tháng trung gian, chưa phải dữ liệu sequence/split
cuối cùng. First-seen được tạo từ bảng này ở task riêng; Categorify, lọc tuần
và gom sequence thuộc các bước tiếp theo.

## Đối chiếu bổ sung trên runtime NVIDIA (tùy chọn)

Đối chiếu cuDF là kiểm tra bổ sung, không phải điều kiện bắt buộc để dùng
bản DuckDB đã chốt. Không gọi số local là kết quả chạy cuDF.

Trên VM có cuDF/NVTabular đã qua smoke test theo
[environment/README.md](../environment/README.md), đặt `INPUT_DATA_DIR` trỏ
đến thư mục chứa `2019-Oct.csv` có SHA-256 khớp raw audit. Chạy tuần tự
Notebook 01 từ đầu đến hết cell 25, gồm bước mã hóa session ở cell 19.
Ghi số dòng raw, sau cell 14, trước và sau cell 25, cùng phiên bản cuDF
và log thật của lần chạy. Hiệu giữa hai số ở cell 25 là số event lặp
bị loại. Dùng nguyên hai khóa sort của cell 25 để xử lý timestamp trùng.

## Đối chiếu DuckDB với output cuDF lưu trong Notebook 01

Cả hai báo 42.448.762 dòng trước khi loại lặp. DuckDB local loại 11.715.474
event, còn 30.733.288 dòng. Output cuDF lưu trong cell 25 loại 11.715.461
event, còn 30.733.301 dòng. DuckDB loại nhiều hơn 13 event.

Ghi nhận nguyên nhân theo TV1, được người dùng chuyển lại ngày 20/11/2026:
“Cùng 42.448.762 dòng đầu vào, DuckDB local loại 11.715.474 event lặp,
nhiều hơn 13 event so với output cuDF lưu sẵn trong Notebook 01.
Chênh lệch do thứ tự timestamp trùng.”

Nguồn giải thích là xác nhận của TV1; repo chưa có log đối chiếu từng
event/session giữa hai engine. Số cuDF là output lưu sẵn của NVIDIA.
