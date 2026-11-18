# Handoff

Không ghi secret hoặc credential vào file này. Cập nhật sau mỗi bàn giao có output thật.

## Nguồn NVIDIA và protocol — 19/11/2026

- Branch: `reference/nvidia-transformers4rec`.
- Commit chứa snapshot và hướng dẫn: `2a431b9`.
- Commit NVIDIA: `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`.
- Artifact: `docs/vendor/nvidia-transformers4rec/`, `docs/references.md`, `docs/modeling/model_protocol.md`.
- Cách kiểm tra: đối chiếu SHA-256 của từng file upstream với manifest.json; đọc LICENSE, protocol và hướng dẫn. Script nhập nguồn: `python scripts/fetch_nvidia_reference.py --help`.
- Output thật: đã tải 16 file upstream (856298 bytes); tất cả SHA-256 khớp manifest; kiểm tra cú pháp script và `git diff --check` đạt.
- Chưa chạy: GPU runtime, train/inference hoặc benchmark. Chưa chốt các điểm dữ liệu còn mở với TV1.
- Người nhận: TV1/TV3 và các thành viên triển khai; trạng thái kiểm tra của người nhận: chờ xác nhận. Chưa đánh dấu Done theo quy tắc dự án.

## Hai task đọc model và định nghĩa bài toán — 19/11/2026

- Branch: `reference/nvidia-transformers4rec`; commit tài liệu: `1e0e2ec`.
- Files: `docs/modeling/model_comparison.md`, `docs/modeling/next_item_problem.md`.
- Đầu ra: bảng ba model, cấu hình tham khảo có nguồn, ví dụ prefix/target/Top-20 và hướng dẫn đọc Notebook 03.
- Kiểm tra: đối chiếu cell cấu hình trong notebook snapshot f0ca2b5; tất cả link local trong hai file tồn tại. Chạy `git show 1e0e2ec --stat` để xem phạm vi bàn giao.
- Giới hạn: tài liệu khái niệm đã soạn; chưa có run model. Các điểm TV1 cần xác nhận giữ nguyên trong protocol và note cá nhân local.
- Người nhận/kiểm tra: Thúy đọc và giải thích lại, TV1 đối chiếu format; chờ xác nhận, chưa đánh dấu Done.

## Dọn repo — 19/11/2026

- Giữ nguyên các thư mục chức năng đã thống nhất; chuyển snapshot nguồn từ root vào `docs/vendor/` và tài liệu model vào `docs/modeling/`.
- Đóng gói nguyên bản 8 tài liệu bối cảnh cũ vào `docs/archive/context-history.zip`; chỉ dùng để tra lịch sử. Yêu cầu môn học giữ ở `docs/course_requirements.txt`; runbook giữ ở `docs/team_tasks.md` và bỏ cột lịch cũ, dùng lịch AGENTS.md.
- Gộp hướng dẫn đối chiếu NVIDIA vào `docs/references.md`; README là mục lục tài liệu hiện hành. Các đường dẫn bàn giao ở mục trước đã cập nhật theo vị trí mới; commit cũ vẫn là lịch sử tạo nội dung.
- Kiểm tra: ZIP đọc được và khớp byte với 8 bản gốc trước khi dọn; 16 checksum upstream giữ nguyên; link Markdown local tồn tại; script nhập nguồn đúng cú pháp. Chưa có benchmark mới.
- Note cá nhân giữ local và vẫn bị .gitignore loại khỏi commit.
