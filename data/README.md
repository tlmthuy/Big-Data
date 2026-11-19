# Data directory

Không lưu raw CSV hoặc Parquet lớn trong Git. Đặt manifest, schema, counts, sampling rule và đường dẫn artifact trong `manifests/`. Xem [AGENTS.md](../AGENTS.md) để biết quy tắc sampling/split.

## Phạm vi preprocessing đã chốt — 19/11/2026

- First-seen lấy trên dữ liệu tháng sau xử lý sơ bộ/loại lặp như notebook 01, trước lọc tuần. Lưu artifact chung và thời gian tạo riêng.
- Từng subset 10/25/50/100% fit workflow/mapping/thống kê feature trên dữ liệu tuần của chính subset trước split; dùng mapping/schema cố định qua các partition.
- Lưu mapping ngược, vocabulary, catalog product ID thực, seed, membership, counts, day_index và mốc tính thực tế theo notebook 02. Không mặc định day_index bằng ngày lịch UTC.
- Token kỹ thuật không phải sản phẩm gợi ý. Model baseline chỉ dùng product ID; các feature có trong Parquet không tự trở thành input model.
- Chi tiết năm quyết định và nguồn: [preprocessing_review.md](../docs/preprocessing_review.md). Manifest phải phân biệt chi phí chung trên tháng với chi phí riêng từng subset cho E2/E5.
