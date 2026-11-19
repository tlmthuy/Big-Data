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

Vị trí chuyển file ngoài Git có thể ghi tại `delivery.shared_location` trong
manifest chung. Đường dẫn `/Users/nguyenbaochau/...` trong manifest nguồn là
đường dẫn lịch sử máy TV1, không phải link tải. Hai file Parquet lớn chuyển
ngoài Git; người nhận cũng có thể tái tạo theo lệnh trong
[cleanup](timestamp_session_cleanup.md) và [first-seen](monthly_first_seen.md).
Không cần một file Parquet riêng cho timestamp: `event_time_ts` đã nằm trong
`events_clean.parquet`.

## TV2/TV3 tự tra cứu

Manifest chung ghi sẵn SHA-256, số dòng, schema kỳ vọng, cột không null,
khóa lookup và khoảng timestamp. TV2/TV3 dùng thông tin này khi nạp dữ liệu;
không yêu cầu điền receipt, tạo log ký nhận hay xác nhận đã đọc file.

Schema kỳ vọng được suy ra từ SQL hiện tại: cleanup có chín cột,
`event_time_ts` int64, tám cột còn lại string; lookup có product string và
timestamp int64. Đây là schema trung gian, chưa mã hóa product cho model.

Checksum là dấu vân tay byte của file. Nếu chuyển nguyên file thì checksum
phải giữ nguyên. Nếu tái tạo sinh byte khác, giữ provenance của lần tạo mới;
không sửa checksum nguồn để làm phép đối chiếu có vẻ đạt.

## Phạm vi hoàn tất

Ba task được chấp nhận qua review code/docs/manifest và merge theo quyết định
người dùng ngày 20/11/2026, không chờ xác nhận người nhận. Hai artifact trên
chưa thay thế bộ sequence/split, mapping/catalog và schema cuối cùng TV1 cần
cung cấp cho model ở task sau. TV4/TV5 dùng metadata này để truy vết tài liệu.
