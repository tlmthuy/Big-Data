# Runbook chi tiết cho 4 thành viên

Lịch và phạm vi chính thức: [AGENTS.md](../AGENTS.md). File này giữ hướng dẫn thực thi; các cột deadline cũ đã bỏ để tránh lệch lịch.

File này bổ sung hướng dẫn thực thi cho bảng giao việc. Mỗi task phải có đúng ba thứ khi bàn giao: **lệnh chạy**, **output thật** và **cách kiểm tra output**.

## Phạm vi sampling dùng chung

Tất cả thành viên dùng cùng phạm vi: `2019-Oct.csv`, 7 ngày đầu từ `2019-10-01` đến hết `2019-10-07` UTC, bỏ `user_session` null trước sampling, giữ `view`, `cart`, `purchase`, chọn session bằng stable hash ở mức 10%, 25%, 50%, 100%, giữ toàn bộ event của session, chỉ giữ sequence có ít nhất 2 tương tác, giới hạn sequence length 20, gom session rồi tính day_index theo công thức notebook 02, chia ngẫu nhiên khoảng 80% train, 10% validation, 10% test trong từng partition; daily fine-tuning train partition t và validation partition t+1. Năm điểm preprocessing đã chốt tại [preprocessing_review.md](preprocessing_review.md); dùng source sort, không thêm khóa phụ CSV.

## TV1 — Data và preprocessing

| Task | Yêu cầu đầu ra (done gate) | Ghi chú thực thi cụ thể |
| --- | --- | --- |
| Đọc schema raw và notebook 01 | Có ghi chú input/output, cột và thao tác lọc | Mở [notebook 01](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/01-preprocess.html). Ghi lại 9 cột raw, cách tạo `event_time_ts`, cách bỏ `user_session` null, cách mã hóa session, cách xử lý event lặp và tên file Parquet đầu ra. Không sửa code trước khi ghi lại pipeline gốc. |
| Audit dataset | Có `data/raw_audit.csv` | Chạy script đọc raw và xuất số dòng, số null từng cột, min/max thời gian, số event type, số session, user, item, category, brand. Lưu cả command và timestamp chạy. |
| Sampling theo session | Bốn danh sách ID và manifest tái lập được ở 10%, 25%, 50%, 100% | Dùng `pipeline/sample_sessions.py`, SHA-256 trên ID session gốc với seed 42; kiểm tra ngưỡng, uniqueness và các tập lồng nhau. Đây mới là membership, chưa xuất event. Xem [session_sampling.md](session_sampling.md). |
| Xuất subset và manifest | Raw CSV tuần đầu và counts event/session/user/item | Dùng `pipeline/export_raw_subsets.py` join membership và giữ toàn bộ event hợp lệ trong tuần, gồm event lặp và session một event. Manifest ghi input/output path/checksum, seed, rule hash, thời gian và counts. Khi chạy riêng phải chọn `--output-dir`, `--manifest`, `--counts` mới. Xem [raw_subsets.md](raw_subsets.md). TV2 chỉ dùng subset có manifest. |
| Chạy preliminary preprocessing | Có Parquet sơ bộ | Theo notebook 01, timestamp conversion, bỏ session null, categorify session, sort theo session/time, loại consecutive repeated item và tính `prod_first_event_time_ts` trên dữ liệu tháng trước lọc tuần. Lưu artifact first-seen chung, mapping truy vết session gốc và counts từng bước; không thêm khóa phụ CSV. |
| Chạy ETL NVTabular | Có Parquet + schema | Tận dụng [notebook 02](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/02-ETL-with-NVTabular.html). Fit workflow riêng trên dữ liệu tuần của từng subset trước split, gồm `Categorify`, feature statistics/normalization và Groupby theo `user_session`; giữ 20 item cuối bằng `ListSlice(-20, pad=True)`, session tối thiểu 2 interaction. Mở lại Parquet và in schema sau export. Baseline model chỉ dùng product ID. |
| Tạo split và mapping | Có split files + mapping | Tính day_index bằng `(event_time_dt-first - col.min()).dt.days + 1` như nguồn, không mặc định ngày lịch UTC; chia ngẫu nhiên khoảng 80/10/10 trong mỗi partition, GPU seed 1, sort theo user_session. Giữ session qua ngày, không loại theo event cuối vượt cutoff train. Mapping/schema đã fit trên tuần trước split và giữ cố định qua partition. Lưu membership/counts, vocabulary, catalog product ID thực, mapping encoded ID ↔ original product_id và phiên bản runtime. |
| Tạo bốn subset | Có 10/25/50/100% manifests | Dùng cùng sampling rule và seed policy. Ghi event/session/user/item thực tế của từng mức. Không gọi 10% user là 10% event nếu chưa đo. |
| Hỗ trợ sửa data/schema | Mọi run đọc cùng schema | Khi TV2 báo lỗi, tái tạo lỗi bằng command của TV2, sửa tại pipeline, tăng version output và gửi lại schema/counts. Không sửa trực tiếp file Parquet bằng tay. |
| Reproduce preprocessing | Thành viên khác chạy lại được | Đưa command raw → sample → Parquet vào README. TV1 không tự chạy một mình, phải nhờ người khác chạy trong thư mục sạch và đối chiếu counts. |

### Trạng thái ba task raw — 19/11/2026

Audit, chọn session và xuất raw subset đã được merge vào `main` từ commit TV1 `f7fce3e`; review code và kiểm tra nhỏ đạt. Bảng counts: [raw_subset_counts.csv](../data/manifests/raw_subset_counts.csv). Đây chưa phải dữ liệu sequence đã làm sạch.

Chưa Done chính thức: người nhận cần tái tạo/nhận artifact thật, xác minh raw checksum, membership và nội dung/counts subset, rồi điền xác nhận trong [handoff.md](handoff.md). Không coi kiểm tra dữ liệu giả lập là nghiệm thu dữ liệu thật.

## TV2 — Model, experiment và evaluation

| Task | Yêu cầu đầu ra (done gate) | Ghi chú thực thi cụ thể |
| --- | --- | --- |
| Đọc notebook 03 | Có model protocol | Đọc [notebook 03](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html). Ghi rõ GRU dùng input nào, XLNet dùng masking nào, dataloader nào, loss nào, training arguments nào và metric nào. |
| Chốt evaluation protocol | Có split/target/catalog/K | Viết một trang quy định: input prefix, next-item target, user/session đủ điều kiện, candidate catalog từ vocabulary tuần của subset đã fit trước split, seen-item rule, `K=20`, Recall@20 và NDCG@20. Không đổi quy định sau khi nhìn kết quả. |
| Viết metric và Popularity | Toy test đúng | Tạo toy example có target nằm hạng 1, hạng 20 và ngoài top-20. Kiểm tra Recall/NDCG bằng tay. Popularity phải fit trên train rồi trả danh sách top-20 cho test prefix. |
| Viết script GRU/XLNet | Smoke run thành công | Tận dụng model block của repo, chuyển path/schema/config thành arguments. Script phải nhận `--data`, `--split`, `--output`, `--batch-size`, `--epochs`, `--seed`, `--model`. |
| Viết experiment matrix | Có `docs/experiment_matrix.md` | Mỗi dòng matrix phải có run_id, model, subset, input format, batch size, resource config, command, metric output và log output. Không để TV3 tự đoán config. |
| Smoke end-to-end | Có prediction + metric | Chạy raw sample → dataloader → train ít bước → inference → top-20 → Recall/NDCG. Kiểm tra encoded ID được đổi về product ID gốc. |
| Giao script E1 | TV3 chạy ba model | Giao command cụ thể cho Popularity, GRU, XLNet. Ghi rõ cái nào chạy sequential, cái nào cần dọn VRAM/restart kernel. |
| Giao script E2–E4 | TV3 chạy đúng matrix | Đóng gói run scripts hoặc config files. Không yêu cầu TV3 sửa Python để đổi subset/resource. Mọi thay đổi phải quay lại TV2. |
| Phân tích E1–E5 | Có bảng/kết luận/limitations | Từ raw logs, tính mean/std nếu có lặp, so model, tính runtime trên một triệu event, vẽ scaling curve và nêu bottleneck. Không lấy số tutorial làm số nhóm. |
| Chốt metrics cho TV4 | Có metrics package chính thức | Gửi CSV/JSON có run_id, config, metric, source log và ghi chú run bị loại. TV4 chỉ dùng package này để làm report. |
| Reproduce/Q&A | Một command chạy lại được | Nhờ thành viên khác chạy evaluation từ checkpoint hoặc output đã lưu. Chuẩn bị trả lời về ground truth, leakage, K, candidate catalog, GRU và XLNet. |

## TV3 — Môi trường và vận hành run

| Task | Yêu cầu đầu ra (done gate) | Ghi chú thực thi cụ thể |
| --- | --- | --- |
| Dựng GPU VM/Docker | Import test thành công | Dùng hướng dẫn container trong [notebook 02](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/02-ETL-with-NVTabular.html). Ghi image tag, GPU, driver, CUDA, Python và package versions. Không cài package thủ công mà không ghi lại. |
| Ghi baseline resource | Có environment log | Chạy một lệnh đọc sample và lưu RAM/VRAM trước-sau, wall time, GPU utilization nếu có. Đây là baseline để so E2/E3. |
| Smoke test repo | Đọc data và chạy model step | Chạy một cell/lệnh nhỏ của [notebook 03](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html). Nếu lỗi, ghi command, traceback, package version và cách sửa. |
| Benchmark collector | Có run_id và raw log | Collector phải ghi start/end time, exit code, stdout/stderr path, peak memory, GPU memory, config path và output path. Không chỉ ghi thời gian bằng tay. |
| Chạy E1 | Ba model có raw logs | Đọc đúng script TV2, chạy Popularity/GRU/XLNet theo cùng data/split/K. Sau mỗi model lưu log riêng, checkpoint/output riêng và trạng thái pass/fail. |
| Chạy E2 | Bốn subset có raw logs | Chạy đúng 10/25/50/100%. Trước mỗi run ghi counts từ manifest, sau mỗi run ghi preprocessing/train/memory. Không đổi batch size giữa các subset. |
| Chạy E3 | Hai resource configs | Chỉ thay một biến TV2 chỉ định, ví dụ batch size 32 và 128. Giữ model, data, split, epoch và sequence length cố định. Ghi rõ warm-up/cache. |
| Chạy E4 | CSV/Parquet cùng dữ liệu | Kiểm tra row count và checksum/counts trước khi đo. Đo file size, read time, preprocessing time và memory. Không so CSV raw với Parquet đã lọc khác nội dung. |
| Hoàn tất E5/rerun lỗi | E1–E5 có pass/fail | Tạo bảng run registry gồm pass, fail, OOM, timeout. Rerun chỉ run lỗi có nguyên nhân sửa được. Giữ lại log lỗi, không xóa. |
| Bàn giao logs | TV2 xác nhận đủ | Gửi thư mục logs, raw CSV/JSON, config, environment snapshot và ghi chú cache/warm-up. TV2 phải reply xác nhận thiếu gì trước khi TV3 đóng task. |
| Reproduce/cleanup | Một run chạy lại, cloud dừng | Chạy lại đúng một run chính theo README. Sau khi nhóm xác nhận, stop/terminate resource và lưu cleanup record. |

## TV4 — Demo, tích hợp, report và slide

| Task | Yêu cầu đầu ra (done gate) | Ghi chú thực thi cụ thể |
| --- | --- | --- |
| Tạo cấu trúc demo/report | Có README khung và outline | Tạo thư mục app, reports, figures, references. Tích hợp nghĩa là nối input session → inference command/file → top-20 output → UI, không sửa model. |
| Chốt prediction contract | Có sample input/output | Nhận từ TV2 tên field session, product ID, score, rank, target thật và model name. Lưu một JSON mẫu được TV2 xác nhận. |
| Tạo template bảng/hình | Có cột, đơn vị, run_id | Tạo template E1–E5 nhưng để trống số liệu. Mỗi hình phải có title, axis unit, legend và source run_id. |
| Theo dõi logs | Có draft caption/figure | Nhận raw logs từ TV3 nhưng không tự kết luận. Chỉ ghi chú nguồn, cấu hình, warm-up và câu hỏi cần TV2 xác nhận. |
| Nhận metrics chính thức | Có metrics package | Chỉ dùng số liệu TV2 đã chốt. Nếu report cần số khác, hỏi TV2 thay vì tự tính một cách khác. |
| Tích hợp inference demo | Session → top-20 → target thật | Dùng checkpoint/output đã bàn giao. Xử lý loading, lỗi, session lạ và mapping product ID. Không retrain trong request. |
| Viết results/limitations | Report draft có phân tích | Mỗi kết luận phải nối được với experiment, bảng/hình, số đo và limitation. Đối chiếu [yêu cầu môn học](course_requirements.txt). |
| Hoàn thiện report | Report tiếng Anh hoàn chỉnh | Bao gồm dataset/5V, sampling, preprocessing, environment, model, E1–E5, demo, limitations, references, license và AI statement. |
| Hoàn thiện slide/script | Đủ 15 phút + Q&A 5 phút | Mỗi thành viên có phần nói, số liệu trên slide khớp report và metrics package. |
| Rehearsal/fallback | Demo fallback và rehearsal đạt thời lượng | Chuẩn bị video/screenshot hoặc prediction output tĩnh nếu live demo lỗi. |
