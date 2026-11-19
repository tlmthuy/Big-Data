# TV1 — Bàn giao ba bước timestamp, cleanup và first-seen

Manifest chung: [tv1_data_handoff.json](../data/manifests/tv1_data_handoff.json).
Đây là dữ liệu trung gian theo tháng, chưa phải Parquet sequence để train.

## TV1 giao những file nào?

| File | Nội dung | Số dòng kỳ vọng | Người nhận |
| --- | --- | --- | --- |
| `data/clean/month_cpu/events_clean.parquet` | Event tháng sau timestamp UTC, bỏ session null và loại lặp liên tiếp | 30.733.288 | TV2 kiểm tra contract dữ liệu; TV3 tiếp nhận artifact cho pipeline thực nghiệm |
| `data/clean/monthly_first_seen/product_first_seen.parquet` | Lookup hai cột `product_id`, `prod_first_event_time_ts`, dùng chung bốn subset | 166.794 | TV2 kiểm tra khóa/feature; TV3 lưu và dùng cho bước preprocessing tiếp theo |

Giao kèm ba file metadata nhỏ đã có trong Git:

- `data/manifests/event_timestamp.json`: UTC, đơn vị giây, counts và lỗi parse.
- `data/manifests/timestamp_session_cleanup.json`: nguồn, checksum, số dòng cleanup.
- `data/manifests/monthly_first_seen.json`: checksum lookup, counts và thời gian chung.

TV1 điền `delivery.shared_location` trong manifest chung bằng vị trí người nhận
truy cập được. Đường dẫn `/Users/nguyenbaochau/...` trong manifest nguồn là
đường dẫn lịch sử máy TV1, không phải link tải. Hai file Parquet lớn chuyển
ngoài Git; người nhận cũng có thể tái tạo theo lệnh trong
[cleanup](timestamp_session_cleanup.md) và [first-seen](monthly_first_seen.md).
Không cần một file Parquet riêng cho timestamp: `event_time_ts` đã nằm trong
`events_clean.parquet`.

## TV2/TV3 kiểm tra và ghi nhận ở đâu?

Mỗi người nhận điền mục `recipient_checks.TV2` hoặc `recipient_checks.TV3`
trong manifest chung sau khi thực sự đọc file trên máy mình:

1. Ghi tên người kiểm tra, thời gian UTC, commit checkout và đường dẫn hai file
   tại máy nhận vào các field tương ứng.
2. Tính SHA-256 trên byte của từng Parquet, ghi `observed_sha256`, đối chiếu
   `artifacts[].sha256`. File nhận nguyên bản phải khớp checksum. Nếu tái tạo
   sinh byte khác, giữ checksum mới và log đối chiếu nội dung logic; không
   sửa checksum nguồn để làm phép kiểm tra có vẻ đạt.
3. Đọc schema và counts thật, ghi `observed_schema`, `observed_rows`. Schema kỳ
   vọng trong manifest được suy ra từ SQL hiện tại: cleanup có chín cột,
   `event_time_ts` int64, tám cột còn lại string; lookup có product string và
   timestamp int64. Kiểm tra theo tên cột, không phụ thuộc thứ tự vật lý.
4. Ghi kết quả kiểm tra null của các cột bắt buộc, min/max timestamp; lookup
   phải có `product_id` duy nhất. Lưu vào `validation_results` theo artifact ID.
   Các count/bounds kỳ vọng được ghi trong manifest chung.
5. Lưu command/output thật tại `data/manifests/tv1_receipt_tv2.log` hoặc
   `data/manifests/tv1_receipt_tv3.log`, ghi đường dẫn vào `log_path`.
   Chỉ đặt `status` thành `passed` sau khi các kiểm tra đạt; lỗi ghi `failed`.
   Các file log này chưa được tạo vì chưa có lần kiểm tra trên máy người nhận.
6. Thêm một dòng xác nhận trong `docs/handoff.md`: người nhận, ngày, artifact
   đã kiểm tra, trạng thái và đường dẫn log; commit/push metadata cùng log nhỏ.

Không sửa kết quả đo lịch sử trong ba manifest nguồn để ghi nghiệm thu.
TV4/TV5 dùng manifest/log này để truy vết khi viết tài liệu, không phải người
nhận dữ liệu để train và không tự xác nhận thay TV2/TV3.

## Giới hạn của lần bàn giao này

Hai artifact trên chưa thay thế bộ sequence/split, mapping/catalog và schema
cuối cùng TV1 cần giao cho model ở task sau. Merge code/docs không có nghĩa
TV2/TV3 đã nhận và kiểm tra hai file lớn. Bản ghi receipt hiện để `pending`.
