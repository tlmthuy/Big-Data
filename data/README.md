# Data directory

Không lưu raw CSV hoặc Parquet lớn trong Git. Đặt manifest, schema, counts, sampling rule và đường dẫn artifact trong `manifests/`. Xem [AGENTS.md](../AGENTS.md) để biết quy tắc sampling/split.

## Artifact raw đã có trên main — 19/11/2026

| Bước | Script | Đầu ra nhỏ được lưu trong Git |
| --- | --- | --- |
| Audit tháng và tuần | `pipeline/raw_audit.py` | [raw_audit.csv](raw_audit.csv), [raw_audit_manifest.json](manifests/raw_audit_manifest.json) |
| Chọn session gốc | `pipeline/sample_sessions.py` | [session_sampling_manifest.json](manifests/session_sampling_manifest.json) |
| Xuất raw event tuần theo membership | `pipeline/export_raw_subsets.py` | [raw_subset_counts.csv](manifests/raw_subset_counts.csv), [raw_subset_manifest.json](manifests/raw_subset_manifest.json) |

Counts 100%: 8.829.314 event, 1.877.365 session, 957.543 user, 118.333 item. Raw audit tuần có 8.829.315 event; chênh một dòng bị loại vì thiếu session. Các raw subset chưa loại lặp, chưa lọc session tối thiểu hai interaction và chưa cắt sequence.

Danh sách ID tại `data/subset/session_ids/` và raw event tại `data/subset/raw_week/` là artifact lớn ngoài Git; đường dẫn trong manifest lịch sử thuộc máy TV1. Chưa có xác nhận người nhận kiểm tra độc lập. Xem [cách tái tạo và xác nhận](../docs/raw_subsets.md#người-nhận-tái-tạo-và-xác-nhận). SHA-256 phải khớp khi nhận bản sao file gốc; khi tái xuất raw CSV có thứ tự dòng khác, cần đối chiếu nội dung record và số lần xuất hiện, không chỉ tổng dòng.

Seed 42 dùng cho sampling, độc lập với GPU seed 1 dùng chia split ở bước sau. Hash sampling là phần nhóm bổ sung, không phải bước có sẵn của NVIDIA. Các manifest cũ giữ checksum script của lần chạy lịch sử; không thay bằng checksum code mới khi chưa chạy lại.

## Phạm vi preprocessing đã chốt — 19/11/2026

- First-seen lấy trên dữ liệu tháng sau xử lý sơ bộ/loại lặp như notebook 01, trước lọc tuần. Lưu artifact chung và thời gian tạo riêng.
- Từng subset 10/25/50/100% fit workflow/mapping/thống kê feature trên dữ liệu tuần của chính subset trước split; dùng mapping/schema cố định qua các partition.
- Lưu mapping ngược, vocabulary, catalog product ID thực, seed, membership, counts, day_index và mốc tính thực tế theo notebook 02. Không mặc định day_index bằng ngày lịch UTC.
- Token kỹ thuật không phải sản phẩm gợi ý. Model baseline chỉ dùng product ID; các feature có trong Parquet không tự trở thành input model.
- Chi tiết năm quyết định và nguồn: [preprocessing_review.md](../docs/preprocessing_review.md). Manifest phải phân biệt chi phí chung trên tháng với chi phí riêng từng subset cho E2/E5.
