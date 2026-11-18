# Handoff

| Item | Value |
|---|---|
| Commit | Chưa có |
| Run ID | Chưa có |
| Artifact path | Chưa có |
| Command | Chưa có |
| Producer | Chưa phân công |
| Receiver/check | Chưa kiểm tra |

Không ghi secret hoặc credential vào file này. Cập nhật sau mỗi bàn giao có output thật.

## Nguồn NVIDIA và protocol — 19/11/2026

- Branch: `reference/nvidia-transformers4rec`.
- Commit chứa snapshot và hướng dẫn: `2a431b9`.
- Commit NVIDIA: `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`.
- Artifact: `references/nvidia-transformers4rec/`, `docs/NVIDIA_REFERENCE_GUIDE.md`, `docs/model_protocol.md`.
- Cách kiểm tra: đối chiếu SHA-256 của từng file upstream với manifest.json; đọc LICENSE, protocol và hướng dẫn. Script nhập nguồn: `python scripts/fetch_nvidia_reference.py --help`.
- Output thật: đã tải 16 file upstream (856298 bytes); tất cả SHA-256 khớp manifest; kiểm tra cú pháp script và `git diff --check` đạt.
- Chưa chạy: GPU runtime, train/inference hoặc benchmark. Chưa chốt các điểm dữ liệu còn mở với TV1.
- Người nhận: TV1/TV3 và các thành viên triển khai; trạng thái kiểm tra của người nhận: chờ xác nhận. Chưa đánh dấu Done theo quy tắc dự án.

## Hai task đọc model và định nghĩa bài toán — 19/11/2026

- Branch: `reference/nvidia-transformers4rec`; commit tài liệu: `1e0e2ec`.
- Files: `docs/model_comparison.md`, `docs/next_item_problem.md`.
- Đầu ra: bảng ba model, cấu hình tham khảo có nguồn, ví dụ prefix/target/Top-20 và hướng dẫn đọc Notebook 03.
- Kiểm tra: đối chiếu cell cấu hình trong notebook snapshot f0ca2b5; tất cả link local trong hai file tồn tại. Chạy `git show 1e0e2ec --stat` để xem phạm vi bàn giao.
- Giới hạn: tài liệu khái niệm đã soạn; chưa có run model. Các điểm TV1 cần xác nhận giữ nguyên trong protocol và note cá nhân local.
- Người nhận/kiểm tra: Thúy đọc và giải thích lại, TV1 đối chiếu format; chờ xác nhận, chưa đánh dấu Done.
