# First-seen sản phẩm trên toàn tháng

Theo Notebook 01 cell 28–29, lấy `MIN(event_time_ts)` theo `product_id`
trên 30.733.288 event tháng 10 sau bỏ session null và loại lặp, trước lọc
tuần, sampling và split. Bảng có 166.794 product ID duy nhất, không có
giá trị thiếu. Đã đọc lại Parquet và đối chiếu minimum cho từng sản phẩm.

Dùng chung `data/clean/monthly_first_seen/product_first_seen.parquet` cho
cả bốn subset 10%, 25%, 50%, 100%. Ghép theo `product_id` và giữ
`prod_first_event_time_ts` dạng giây Unix UTC. Thời gian chung 1,516 giây
gồm đọc Parquet tháng, tính minimum và ghi artifact. Đo riêng thời gian
làm sạch tháng ở bước trước, thời gian kiểm tra/checksum và thời gian
ghép hoặc fit workflow của từng subset.

Chạy lại từ gốc repo với DuckDB trong `pipeline/requirements-audit.txt`:

```bash
.venv/bin/python pipeline/build_monthly_first_seen.py \
  --cleanup-report data/manifests/timestamp_session_cleanup.json \
  --output-dir data/clean/monthly_first_seen
```

Dùng thư mục output mới khi chạy lại. [Manifest](../data/manifests/monthly_first_seen.json)
ghi đường dẫn, checksum và số liệu lần chạy. Nguồn hiện tại là lần làm sạch
DuckDB local. Khi có Parquet làm sạch trên cuDF, dùng report tương ứng để
tạo lại và so sánh lookup trước khi dùng cho benchmark NVIDIA.
