# Session sampling — TV1

Chọn session ID gốc bằng SHA-256 với seed sampling cố định `42`. Seed này độc lập với GPU seed `1` dùng chia split của NVIDIA.

## Phạm vi và quy tắc

- Đọc raw `2019-Oct.csv`, lấy session không null có event view/cart/purchase trong UTC `[2019-10-01, 2019-10-08)`.
- Hash UTF-8 của `str(seed) + ':' + user_session`, không sửa nội dung ID. Lấy 8 byte đầu SHA-256 thành số nguyên không dấu big-endian `h`.
- Với mức p%, chọn `h < floor(p * 2^64 / 100)`. 100% chọn mọi session hợp lệ.
- Cùng seed và ngưỡng tạo các tập lồng nhau 10% ⊆ 25% ⊆ 50% ⊆ 100%. Đây là tỷ lệ kỳ vọng theo session, không phải quota chính xác và không phải tỷ lệ event.
- Sort ID trong danh sách chỉ để artifact ổn định, không dùng làm khóa phụ sắp event khi preprocessing.

Đây là membership raw trước xử lý sequence. Không bỏ session một event ở bước này; điều kiện ≥2 interaction sau loại lặp và giữ 20 item cuối thực hiện sau, theo quyết định NVIDIA trong repo. Có thể áp membership này lên event sau preprocessing bằng liên kết ID gốc, không hash lại encoded ID. First-seen vẫn tạo trên tháng theo notebook 01, không tính riêng chỉ từ các session đã sample.

## Chạy lại

```bash
.venv/bin/python -m pip install -r pipeline/requirements-audit.txt
.venv/bin/python pipeline/sample_sessions.py --input /Users/nguyenbaochau/Downloads/2019-Oct.csv --seed 42
```

Script từ chối ghi đè output tồn tại. Khi kiểm tra lần khác, chỉ định cả `--output-dir` và `--manifest` mới. Danh sách nhiều ID là artifact local, không commit trực tiếp; manifest nhỏ ghi đường dẫn, counts, rule, seed và checksum để tái tạo.

Output:

- `data/subset/session_ids/sessions_010.csv`
- `data/subset/session_ids/sessions_025.csv`
- `data/subset/session_ids/sessions_050.csv`
- `data/subset/session_ids/sessions_100.csv`
- `data/manifests/session_sampling_manifest.json`

Mỗi CSV có duy nhất cột `user_session`. Kiểm tra: ID không null/không trùng, tất cả thỏa hash threshold, tập lồng nhau, 100% bằng population, input không đổi size/mtime. SHA-256 nguồn được tính và lưu để đối chiếu raw audit.

Bước này chưa xuất raw event subset. Bước kế tiếp phải join theo danh sách session và giữ toàn bộ event hợp lệ của session trong cửa sổ tuần; không random từng dòng. Counts sau loại lặp, user/item/category/brand, event type và session length sẽ báo ở bước xuất/preprocessing, không coi counts membership là số sequence cuối cùng.

Đây là script sampling nhóm bổ sung bằng CPU DuckDB/Python; không thay cách sort, workflow fit, day_index hoặc split NVIDIA. Có hỗ trợ AI khi triển khai. Trạng thái Git và bàn giao xem `docs/handoff.md`; người nhận chưa xác nhận kiểm tra.

## Kết quả chạy ngày 19/11/2026

Population: 1.877.365 session. SHA-256 input khớp raw audit.

| Mức | Số session thực tế | Tỷ lệ thực tế |
| --- | ---: | ---: |
| 10% | 187563 | 9.9908% |
| 25% | 469728 | 25.0206% |
| 50% | 938071 | 49.9674% |
| 100% | 1877365 | 100.0000% |

Các kiểm tra membership đều PASS. Đây là counts raw membership, chưa phải counts sau preprocessing.
