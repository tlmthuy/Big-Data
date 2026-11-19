# Xuất raw subset theo danh sách session — TV1

Script `pipeline/export_raw_subsets.py` dùng membership đã chọn trong `session_sampling_manifest.json`, không chọn lại session và không random từng dòng.

Phạm vi: `[2019-10-01 00:00:00, 2019-10-08 00:00:00)` UTC, session không null, event view/cart/purchase. Lấy mọi event thuộc các session đã chọn trong phạm vi này. Session qua ngày được giữ; phần ngoài tuần không được lấy. Dữ liệu vẫn giữ interaction lặp, session một event và missing brand/category_code. Không tạo timestamp feature, mapping, truncation, split hoặc sequence. Giữ nguyên giá trị chín cột; định dạng serialize CSV có thể khác file nguồn, không cam kết byte giống nhau.

## Chạy lại

```bash
.venv/bin/python -m pip install -r pipeline/requirements-audit.txt
.venv/bin/python pipeline/export_raw_subsets.py
```

Cần có input CSV và bốn danh sách session tại đường dẫn trong sampling manifest; checksum phải khớp. Nếu chuyển máy, tái tạo sampling manifest và danh sách bằng `pipeline/sample_sessions.py` với cùng input checksum/seed/rule rồi dùng `--sampling-manifest` tương ứng. Script từ chối ghi đè output. Muốn chạy ra nơi khác, chỉ định cả `--output-dir` và `--manifest` mới. Bảng counts nhỏ luôn được ghi tại `data/manifests/raw_subset_counts.csv`.

## Output

- `data/subset/raw_week/raw_week_010.csv`
- `data/subset/raw_week/raw_week_025.csv`
- `data/subset/raw_week/raw_week_050.csv`
- `data/subset/raw_week/raw_week_100.csv`
- `data/manifests/raw_subset_manifest.json`
- `data/manifests/raw_subset_counts.csv`

Các CSV raw lớn chỉ lưu local theo quy tắc repo. Manifest nhỏ ghi input/output path/checksum, seed 42, rule hash/ngưỡng, cửa sổ UTC, counts event/session/user/item, liên kết và checksum danh sách session. Tỷ lệ session và event là hai đại lượng khác nhau.

## Kiểm tra

- SHA-256 input và membership khớp sampling manifest.
- Đọc lại CSV output bằng parser strict, header đúng 9 cột.
- Event/session/user/item counts khớp truy vấn nguồn theo membership.
- So sánh chính xác số event của từng session giữa nguồn và output; không thiếu/thừa session hoặc multiplicity.
- Input giữ nguyên size/mtime. Không thêm khóa phụ sort khi timestamp bằng nhau.

Script là tiện ích nhóm bổ sung; không sửa snapshot NVIDIA hay thay đổi năm quyết định preprocessing. Chạy notebook 01/02 và bảng first-seen tháng thuộc các bước tiếp theo. Có hỗ trợ AI khi soạn script/tài liệu. Chưa commit/push; người nhận chưa xác nhận bàn giao.

## Kết quả chạy ngày 19/11/2026

| Mức | Event | Session | User | Item |
| --- | ---: | ---: | ---: | ---: |
| 10% | 882808 | 187563 | 163847 | 63398 |
| 25% | 2213138 | 469728 | 356271 | 87247 |
| 50% | 4421037 | 938071 | 601608 | 103940 |
| 100% | 8829314 | 1877365 | 957543 | 118333 |

100% có 8.829.314 event, ít hơn raw-week audit một dòng vì dòng đó thiếu user_session. Các checksum/multiplicity checks đều PASS. Counts là raw trước loại lặp/truncation, không phải số sequence cuối cùng.
