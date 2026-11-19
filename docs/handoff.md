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

## Đồng bộ split và daily fine-tuning — 19/11/2026

- Branch: `main`; commit thay đổi: `14e4341`.
- Đã fetch và merge origin/main; local đã cập nhật, không có conflict.
- Theo quyết định người dùng: đồng bộ next_item_problem, model_protocol, AGENTS, references và team_tasks sang khoảng 80/10/10 session trong từng ngày; daily fine-tuning train ngày t, validation ngày t+1.
- Kiểm tra: `git diff --check`; tìm quy tắc split cũ trong các tài liệu hiện hành đã sửa; đối chiếu notebook 02/03 trong snapshot. Không sửa upstream.
- Chưa chạy model/benchmark. Session vượt cutoff, lịch test cuối và mapping qua ngày còn cần TV1/TV2 xác nhận. Người nhận chưa xác nhận; chưa đánh dấu Done.

## TV1 task 2 — Đọc preprocessing NVIDIA — 19/11/2026

- Branch: `feature/tv1-data`; commit tài liệu: `6c70594`.
- Output: `docs/preprocessing_review.md`; README đã có link tra cứu.
- Nội dung: sơ đồ raw CSV → Parquet, danh sách bước đúng thứ tự, cell tham chiếu, schema 10 cột đầu ra, ví dụ xử lý lặp và các phần nhóm bổ sung theo protocol hiện hành.
- Kiểm tra: đọc trực tiếp code cell notebook 01; SHA-256 khớp manifest nguồn f0ca2b5343dd1e40b5d2422b942f014b224f5c20; `git diff --check` đạt. Lệnh tái kiểm tra có trong tài liệu.
- Đây là đầu ra thật của task đọc hiểu, không phải log thực thi preprocessing. Tạo Parquet thuộc task sau; không dùng số liệu tutorial như kết quả nhóm.
- Người nhận: TV1/TV2/TV3; chờ xác nhận đã kiểm tra tài liệu, chưa đánh dấu Done chính thức theo AGENTS.md.

## Chốt năm điểm preprocessing theo tutorial — 19/11/2026

- Theo quyết định mới nhất của Thúy: dùng đúng source sort không thêm khóa phụ CSV, giữ 20 item cuối, giữ session qua ngày và day_index theo công thức nguồn, fit workflow/mapping trên tuần của từng subset trước split, tính first-seen trên tháng trước lọc tuần.
- Mục này thay thế các trạng thái chờ chốt session/mapping và quy định train-only trong các bàn giao trước; các mục cũ giữ để tra lịch sử. Lịch test cuối cùng vẫn chờ TV2 xác nhận.
- Đã đồng bộ AGENTS, README, preprocessing_review, model_protocol, next_item_problem, model_comparison, references, team_tasks, experiment_matrix và data/README. Catalog chung dùng product ID thực từ vocabulary tuần; token kỹ thuật không được gợi ý. Popularity là baseline nhóm, chỉ đếm train; model baseline vẫn chỉ dùng product ID.
- Nguồn: snapshot NVIDIA f0ca2b5343dd1e40b5d2422b942f014b224f5c20, notebook 01/02/03, data_utils.py và prediction_task.py; chi tiết code cell trong preprocessing_review.md. Upstream được giữ nguyên.
- Kiểm tra: đối chiếu code cell và checksum manifest; kiểm tra link Markdown local, quy định cũ trong tài liệu hiện hành và git diff --check. Chưa chạy preprocessing, GPU model hoặc benchmark. Chưa có xác nhận nghiệm thu của người nhận.
- Trạng thái Git: cập nhật tài liệu trong working tree, chưa commit/push ở lần bàn giao này; chưa đánh dấu Done chính thức.

## TV1 raw audit trước sampling — 19/11/2026

- Branch: `feature/tv1-data`; commit kết quả và script: `98a60e7`.
- Output: `data/raw_audit.csv`, `data/manifests/raw_audit_manifest.json`; hướng dẫn tại `docs/raw_audit.md`.
- Command: `.venv/bin/python pipeline/raw_audit.py --input /Users/nguyenbaochau/Downloads/2019-Oct.csv`.
- Output thật: 42.448.764 event toàn tháng; 8.829.315 event tuần đầu. Counts distinct, missing 9 cột, event type và ngày trong CSV. Runtime khoảng 148,95 giây; peak process RSS 997.081.088 bytes trên macOS.
- Kiểm tra: tổng event type/ngày bằng tổng dòng; bounds missing/distinct; tuần không vượt tháng; input size/mtime giữ nguyên; SHA-256 input và script trong manifest; `git diff --check` đạt.
- Không commit CSV nguồn, không làm sạch/sampling hoặc tạo sequence. Người nhận TV1/TV2/TV3 chưa xác nhận; chưa đánh dấu Done chính thức.

## TV1 — Chọn session bằng seed cố định — 19/11/2026

- Branch: `feature/tv1-data`; commit kết quả: `277abcf`.
- Script: `pipeline/sample_sessions.py`; command: `.venv/bin/python pipeline/sample_sessions.py --input /Users/nguyenbaochau/Downloads/2019-Oct.csv --seed 42`.
- Manifest: `data/manifests/session_sampling_manifest.json`; tài liệu: `docs/session_sampling.md`.
- Output thật tại `data/subset/session_ids/`: 187.563 / 469.728 / 938.071 / 1.877.365 session cho 10/25/50/100%. Danh sách CSV lớn giữ local theo quy tắc artifact; manifest ghi đường dẫn, seed, hash rule, counts và checksum để tái tạo.
- Kiểm tra PASS: ID không null/trùng, đúng hash threshold, tập lồng nhau, 100% bằng population; bốn checksum output khớp manifest, checksum input khớp raw audit; `git diff --check` đạt.
- Chưa xuất raw event subset hay chạy preprocessing. Người nhận chưa xác nhận; chưa đánh dấu Done chính thức theo AGENTS.md.

## TV1 — Xuất raw subset theo session — 19/11/2026

- Branch: `feature/tv1-data`; commit script/output nhỏ: `45554ea`.
- Đã fetch và merge origin/main cùng origin/feature/tv1-data: không có thay đổi mới hoặc conflict tại lần bàn giao này.
- Command: `.venv/bin/python pipeline/export_raw_subsets.py`.
- Output: raw CSV local tại `data/subset/raw_week/`; manifest `data/manifests/raw_subset_manifest.json`, bảng `data/manifests/raw_subset_counts.csv`, hướng dẫn `docs/raw_subsets.md`.
- Counts event/session/user/item: 10% = 882808/187563/163847/63398; 25% = 2213138/469728/356271/87247; 50% = 4421037/938071/601608/103940; 100% = 8829314/1877365/957543/118333.
- Kiểm tra PASS: input/membership checksums; header 9 cột; counts nguồn/output; số event chính xác theo từng session; không có session ngoài membership; bốn output checksums khớp manifest; `git diff --check` đạt. 100% ít hơn raw-week audit một dòng thiếu session.
- Dữ liệu giữ event lặp và session một event; chưa phải cleaned sequence. Không commit raw CSV lớn. Người nhận chưa xác nhận kiểm tra; chưa đánh dấu Done chính thức.

## Xác nhận của người nhận — Raw subset TV1

Phương án bàn giao là tái tạo từ CSV nguồn cùng SHA-256. Xem [lệnh tái tạo và cách đối chiếu](raw_subsets.md#người-nhận-tái-tạo-và-xác-nhận).

- Tái tạo nội bộ: xuất đủ bốn CSV với đường dẫn counts riêng. SHA-256 raw và danh sách membership khớp bản gốc. Bảng counts khớp từng byte, số event từng session khớp nguồn và tổng kiểm tra băm theo dòng không phụ thuộc thứ tự khớp bản gốc. SHA-256 toàn file CSV khác giữa hai lần xuất.
- Trạng thái: chờ người nhận kiểm tra độc lập.
- Người nhận và ngày kiểm tra:
- SHA-256 raw và bốn danh sách session:
- SHA-256 và counts của bốn CSV:
- Kết quả đối chiếu membership và số event từng session:
- Xác nhận Done:
