# Xuất raw subset theo danh sách session — TV1

Script `pipeline/export_raw_subsets.py` dùng membership đã chọn trong `session_sampling_manifest.json`, không chọn lại session và không random từng dòng.

Phạm vi: `[2019-10-01 00:00:00, 2019-10-08 00:00:00)` UTC, session không null, event view/cart/purchase. Lấy mọi event thuộc các session đã chọn trong phạm vi này. Session qua ngày được giữ; phần ngoài tuần không được lấy. Dữ liệu vẫn giữ interaction lặp, session một event và missing brand/category_code. Không tạo timestamp feature, mapping, truncation, split hoặc sequence. Giữ nguyên giá trị chín cột; định dạng serialize CSV có thể khác file nguồn, không cam kết byte giống nhau.

## Chạy lại

```bash
.venv/bin/python -m pip install -r pipeline/requirements-audit.txt
.venv/bin/python pipeline/export_raw_subsets.py
```

Cần có input CSV và bốn danh sách session tại đường dẫn trong sampling manifest; checksum phải khớp. Nếu chuyển máy, tái tạo sampling manifest và danh sách bằng `pipeline/sample_sessions.py` với cùng input checksum/seed/rule rồi dùng `--sampling-manifest` tương ứng. Script từ chối ghi đè output. Muốn chạy ra nơi khác, chỉ định `--output-dir`, `--manifest` và `--counts` mới. Mặc định counts nằm tại `data/manifests/raw_subset_counts.csv`. Script kiểm tra các đường dẫn trước khi xuất và từ chối nếu bất kỳ đích nào đã tồn tại.

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

Script là tiện ích nhóm bổ sung; không sửa snapshot NVIDIA hay thay đổi năm quyết định preprocessing. Chạy notebook 01/02 và bảng first-seen tháng thuộc các bước tiếp theo. Có hỗ trợ AI khi soạn script/tài liệu. Commit kết quả: `45554ea`; trạng thái Git/bàn giao xem `docs/handoff.md`. Người nhận chưa xác nhận kiểm tra.

## Kết quả chạy ngày 19/11/2026

| Mức | Event | Session | User | Item |
| --- | ---: | ---: | ---: | ---: |
| 10% | 882808 | 187563 | 163847 | 63398 |
| 25% | 2213138 | 469728 | 356271 | 87247 |
| 50% | 4421037 | 938071 | 601608 | 103940 |
| 100% | 8829314 | 1877365 | 957543 | 118333 |

100% có 8.829.314 event, ít hơn raw-week audit một dòng vì dòng đó thiếu user_session. Các checksum/multiplicity checks đều PASS. Counts là raw trước loại lặp/truncation, không phải số sequence cuối cùng.

## Người nhận tái tạo và xác nhận

Dùng một checkout sạch, có đủ chỗ trống cho bốn CSV. Giữ bản manifest
đã commit để làm mốc đối chiếu. Thay đường dẫn raw trong lệnh bằng đường
dẫn trên máy người nhận.

```bash
git show HEAD:data/manifests/session_sampling_manifest.json > /tmp/tv1-sampling-reference.json
git show HEAD:data/manifests/raw_subset_manifest.json > /tmp/tv1-subset-reference.json
python3 -m venv .venv
.venv/bin/python -m pip install -r pipeline/requirements-audit.txt
.venv/bin/python pipeline/sample_sessions.py --input /path/to/2019-Oct.csv --seed 42 --manifest /tmp/tv1-sampling-local.json
.venv/bin/python pipeline/export_raw_subsets.py --sampling-manifest /tmp/tv1-sampling-local.json --manifest /tmp/tv1-subset-local.json --counts /tmp/tv1-counts-local.csv
```

Đối chiếu SHA-256 của raw và bốn danh sách session với manifest đã commit.
Kiểm tra cả bốn dòng PASS của lệnh export. Script đọc lại từng CSV và kiểm
tra membership, số event từng session và counts. Đối chiếu counts và SHA-256
của bốn CSV với manifest tham chiếu. Nếu checksum CSV khác do thứ tự dòng
hoặc cách ghi CSV, ghi rõ khác biệt và kiểm tra nội dung theo session trước
khi xác nhận. Khi nhận bản sao của bốn CSV gốc, checksum phải khớp từng file.

Ghi kết quả vào mục xác nhận trong [handoff](handoff.md) sau khi kiểm tra.
