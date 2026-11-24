# Runbook chi tiết cho 5 thành viên

Lịch và phạm vi chính thức: [AGENTS.md](../AGENTS.md). File này giữ hướng dẫn thực thi và lịch chi tiết TV4/TV5 theo ảnh phân công cập nhật ngày 20/11/2026.

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
| Kiểm tra tiếp nhận dữ liệu TV1 (21/11, trước E1) | Xác nhận split/counts/catalog thật | Phụ thuộc TV1 bàn giao. Kiểm tra split, counts và catalog theo model_protocol.md; ghi xác nhận vào docs/handoff.md trước E1. |
| Viết metric và Popularity | Toy test đúng | Tạo toy example có target nằm hạng 1, hạng 20 và ngoài top-20. Kiểm tra Recall/NDCG bằng tay. Popularity phải fit trên train rồi trả danh sách top-20 cho test prefix. |
| Viết script GRU/XLNet | Smoke run thành công | Tận dụng model block của repo, chuyển path/schema/config thành arguments. Script phải nhận `--data`, `--split`, `--output`, `--batch-size`, `--epochs`, `--seed`, `--model`. |
| Viết experiment matrix | Có `docs/experiment_matrix.md` | Mỗi dòng matrix phải có run_id, model, subset, input format, batch size, resource config, command, metric output và log output. Không để TV3 tự đoán config. |
| Smoke end-to-end | Có prediction + metric | Chạy raw sample → dataloader → train ít bước → inference → top-20 → Recall/NDCG. Kiểm tra encoded ID được đổi về product ID gốc. |
| Giao script E1 | TV3 chạy ba model | Giao command cụ thể cho Popularity, GRU, XLNet. Ghi rõ cái nào chạy sequential, cái nào cần dọn VRAM/restart kernel. |
| Giao script E2–E4 | TV3 chạy đúng matrix | Đóng gói run scripts hoặc config files. Không yêu cầu TV3 sửa Python để đổi subset/resource. Mọi thay đổi phải quay lại TV2. |
| Phân tích E1–E5 | Có bảng/kết luận/limitations | Từ raw logs, tính mean/std nếu có lặp, so model, tính runtime trên một triệu event, vẽ scaling curve và nêu bottleneck. Không lấy số tutorial làm số nhóm. |
| Chốt metrics cho TV4/TV5 | Có metrics package chính thức | Gửi cả hai CSV/JSON có run_id, config, metric, đơn vị, source log và ghi chú run bị loại. TV4 dùng package để tạo figures; TV5 dùng để tạo bảng và viết report/slides. Số liệu bổ sung phải được TV2 xác nhận. |
| Reproduce/Q&A | Một command chạy lại được | Nhờ thành viên khác chạy evaluation từ checkpoint hoặc output đã lưu. Chuẩn bị trả lời về ground truth, leakage, K, candidate catalog, GRU và XLNet. |

## TV3 — Môi trường và vận hành run

Trạng thái xác nhận ngày 24/11/2026 theo quyết định của Thúy (TV2):

| Task trên sheet | Check | Ghi chú |
| --- | :---: | --- |
| Rerun các run lỗi có nguyên nhân sửa được | TRUE | TV2 xác nhận đóng task; giữ log lỗi và run cũ. |
| Bàn giao toàn bộ raw logs cho TV2 | TRUE | TV2 xác nhận nhận bàn giao; đối chiếu raw logs trên VM khi bắt đầu phân tích. |

Task TV2 ngày 24/11: **Phân tích kết quả E1–E5 = TRUE** (review kỹ thuật đạt); **Giao metrics package cho TV4 = TRUE** (người dùng xác nhận TV4 đã kiểm tra). [Báo cáo](../reports/tables/tv2-20261124/analysis.md) và [metrics package](../metrics/releases/tv2-20261124/README.md) có source/config/checksum. TV5 tiếp nhận cùng package, chưa có xác nhận riêng.

Đầu mối nhận việc: [environment/README.md](../environment/README.md) và [manifest TV2](../configs/tv2_handoff.json). Metric/Popularity toy sẵn chạy; script GRU/XLNet, config E1–E4 và E5 được mô tả tại [neural_runbook.md](modeling/neural_runbook.md), chưa nghiệm thu GPU/dataset thật.

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

## TV4 — Demo & hỗ trợ report

TV4 làm trên `feature/tv4-demo-documentation`. Trong ảnh, `demo/` và `figures/` tương ứng với `app/` và `reports/figures/` của repo. README demo đặt tại `app/README.md`; references và AI statement dùng các file hiện có trong `docs/`.

| Deadline | Task | Yêu cầu đầu ra và cách kiểm tra |
| --- | --- | --- |
| 19/11 | Tạo khung demo, README demo và figures | Khung `app/`, `app/README.md`, `reports/figures/`; mô tả session → inference command/file → top-20 → UI. |
| 20/11 | Đọc output contract | Liệt kê input, prediction, score, rank, target thật, session/product ID và model name; đối chiếu với TV2. |
| 21/11 | Tạo prediction JSON/CSV mẫu | Sample input/output được TV2 xác nhận format; kiểm tra mapping về product ID gốc. |
| 22/11 | Chuẩn bị script/khung code tạo figures | Script đọc metrics package; mỗi hình có title, axis unit, legend và source run_id; chưa điền số liệu giả. |
| 25/11 | Chuẩn bị figure templates và caption kỹ thuật | Template/caption nêu rõ metric, đơn vị, cấu hình và nguồn; gửi TV5 để thống nhất với report. |
| 26/11 | Hỗ trợ kiểm tra run_id và đầu vào figures | Đối chiếu run_id, config, nguồn số liệu với TV2/TV5; liệt kê điểm chưa được TV2 xác nhận. |
| 27/11 | Tích hợp inference, xây dựng UI, kiểm thử | Demo hiển thị history, top-20 và target thật; kiểm tra loading, lỗi, session lạ và mapping; dùng checkpoint/output bàn giao, không retrain trong request. |
| 28/11 | Tạo figures chính thức; chuẩn bị demo fallback | Chỉ dùng metrics TV2 đã chốt; bàn giao figures/caption/source run_id cho TV5; có video/screenshot hoặc prediction output tĩnh dự phòng. |
| 28/11 | Chuẩn hóa references, dataset/repo/license, AI statement; thiết kế hình cho slides | Đối chiếu nguồn và license; gửi references/AI statement cùng hình minh họa cho TV5 tích hợp vào report/slides. |
| 28/11 | Tập live demo, fallback và Q&A kỹ thuật | Chạy thử demo/fallback, chuẩn bị trả lời về input/output, inference và cách chạy lại. |

## TV5 — Report & Results

TV5 làm trên `feature/tv5-report-results`. Trong ảnh, `report/` và `slides/` tương ứng với `reports/` và `reports/slides/`; bảng ở `reports/tables/`. Đây là đường dẫn đầu ra được phân công, không có nghĩa các artifact đã hoàn thành.

| Deadline | Task | Yêu cầu đầu ra và cách kiểm tra |
| --- | --- | --- |
| 19/11 | Tạo khung report/slides và outline | Khung `reports/`, `reports/slides/`, report outline và slide outline; đối chiếu [yêu cầu môn học](course_requirements.txt). |
| 20/11 | Xem yêu cầu E1–E5, xác định cấu trúc metric và bảng | Liệt kê experiment, metric, đơn vị, run_id và nguồn log cần cho report theo [experiment matrix](experiment_matrix.md). |
| 21/11 | Kiểm tra format đầu ra | Đối chiếu output contract/metrics với thông tin cần viết report; gửi TV2 danh sách field thiếu để xác nhận. |
| 22/11 | Tạo template bảng E1–E5 | Có metric, đơn vị, run_id và caption; để trống số liệu tới khi có run thật được xác nhận. |
| 25/11 | Đọc raw logs, chuẩn bị table captions và nguồn log | Ghi source log, config, warm-up/cache và câu hỏi cần TV2 xác nhận; chưa dùng raw logs chưa duyệt làm kết luận chính thức. |
| 26/11 | Đối chiếu logs với TV2 | Liệt kê số liệu cần xác nhận, run lỗi/bị loại; phối hợp TV4 kiểm tra run_id và đầu vào figures. |
| 27/11 | Nhận metrics package chính thức, kiểm tra E1–E5 | Kiểm tra đủ experiment, metric, đơn vị, config và source run_id; chỉ dùng số liệu TV2 chốt, yêu cầu TV2 xác nhận số bổ sung. |
| 28/11 | Viết results, limitations và reproducibility | Mỗi kết luận truy được về experiment, bảng/hình, số đo và limitation; cách chạy lại khớp code/config và log thực tế. |
| 28/11 | Hoàn thiện report tiếng Anh và nội dung slides | Bao gồm dataset/5V, sampling, preprocessing, environment, model, E1–E5, demo và limitations; tích hợp figures/references/license/AI statement từ TV4; số liệu report/slides khớp metrics package. |
| 28/11 | Tập thuyết trình results, limitations và Q&A học thuật | Phối hợp cả 5 thành viên chia phần nói; tổng thuyết trình 15 phút + Q&A 5 phút, gồm phần live demo của TV4. |

### Luồng bàn giao TV2 → TV4/TV5

TV2 chốt protocol, phân tích và metrics package; TV3 cung cấp raw logs và environment snapshot để TV2 xác nhận. TV4 và TV5 cùng dùng một package chính thức: TV4 tạo figures/demo, TV5 tạo bảng và viết report/slides. TV4 chuyển figures/caption/references/license/AI statement cho TV5; TV5 đối chiếu report/slides với package và gửi các điểm cần xác nhận về TV2. Ghi output, command/cách kiểm tra, commit và xác nhận của người nhận vào [handoff.md](handoff.md); lịch trên là kế hoạch, không phải trạng thái Done.
