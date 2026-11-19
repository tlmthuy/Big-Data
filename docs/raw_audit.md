# Raw audit — 2019-Oct.csv

Script `pipeline/raw_audit.py` chỉ đọc raw CSV, không bỏ session null, không loại lặp, không sampling, không sửa CSV nguồn. Hai scope trong cùng `data/raw_audit.csv`:

- `raw_month`: toàn bộ tháng, không tính dòng header.
- `raw_week`: event UTC từ 01/10/2019 đến trước 08/10/2019, trước làm sạch/sampling.

Distinct là số giá trị khác nhau không gồm NULL. Missing là trường CSV rỗng, không tự quy chuỗi `unknown` hoặc khoảng trắng thành NULL. Đếm riêng category_id/category_code. ID được đọc dạng chuỗi để không mất độ chính xác. CSV reader strict, không chủ động bỏ qua dòng sai cấu trúc. Thời gian không parse được được ghi ở invalid_timestamp_count.

## Chạy lại

Từ gốc repo:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r pipeline/requirements-audit.txt
.venv/bin/python pipeline/raw_audit.py --input /Users/nguyenbaochau/Downloads/2019-Oct.csv
```

Output CSV có cột `scope,metric,column,value,count,denominator,ratio`. `ratio` ở thang 0–1. Các metric: row_count, distinct_count, missing_count, event_type_count, min/max_timestamp_utc, invalid_timestamp_count, daily_event_count.

Manifest `data/manifests/raw_audit_manifest.json` ghi nguồn/checksum, output path, thời gian, dependency, script checksum, Git base commit và peak process RSS. Script giới hạn memory DuckDB ở 1GB, 2 threads, cho phép spill vào `tmp/raw_audit_spill`; đây không phải giới hạn tuyệt đối RSS của toàn tiến trình. Không so memory audit CPU với GPU preprocessing/model.

Kiểm tra tích hợp: tổng event type và ngày bằng số dòng từng scope; missing/distinct hợp lệ; số dòng tuần không vượt tháng; input size/mtime không đổi trong run. Đây là counts raw, không phải counts sau preprocessing; bảng first-seen tháng và fit workflow theo năm quyết định NVIDIA là các task sau.

Nguồn quy tắc: AGENTS.md, docs/preprocessing_review.md và docs/team_tasks.md trong repo. Audit là tiện ích nhóm bổ sung bằng DuckDB, không khẳng định notebook NVIDIA có sẵn script này. Có hỗ trợ AI khi soạn script/tài liệu.

## Kết quả chạy ngày 19/11/2026

| Chỉ số | Toàn tháng | Tuần đầu |
| --- | ---: | ---: |
| Event | 42448764 | 8829315 |
| Loại event | 3 | 3 |
| Session | 9244421 | 1877365 |
| User | 3022290 | 957543 |
| Item | 166794 | 118333 |
| Category ID | 624 | 565 |
| Category code | 126 | 123 |
| Brand | 3445 | 2640 |

Missing từng cột và phân bố event/day nằm trong CSV. Runtime và peak RSS trong manifest; đây là số đo audit CPU thực tế. Commit kết quả: `98a60e7`; trạng thái bàn giao xem `docs/handoff.md`. Người nhận chưa xác nhận kiểm tra.

Peak RSS được lưu bằng bytes. macOS giữ nguyên `ru_maxrss`; Linux (gồm
Ubuntu) nhân với 1024. Manifest từ lần chạy mới ghi hệ điều hành thực tế
và chuỗi platform. Manifest lịch sử trên macOS giữ số đo của lần chạy đó.
