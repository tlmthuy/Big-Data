# Runbook chi tiết cho 4 thành viên

File này bổ sung hướng dẫn thực thi cho bảng giao việc. Mỗi task phải có đúng ba thứ khi bàn giao: **lệnh chạy**, **output thật** và **cách kiểm tra output**.

## Phạm vi sampling dùng chung

Tất cả thành viên dùng cùng phạm vi: `2019-Oct.csv`, 7 ngày đầu từ `2019-10-01` đến hết `2019-10-07` UTC, bỏ `user_session` null trước sampling, giữ `view`, `cart`, `purchase`, chọn session bằng stable hash ở mức 10%, 25%, 50%, 100%, giữ toàn bộ event của session, chỉ giữ sequence có ít nhất 2 tương tác, giới hạn sequence length 20, train ngày 1–5, validation ngày 6, test ngày 7.

## TV1 — Data và preprocessing

| Task | Yêu cầu đầu ra (done gate) | Deadline | Ghi chú thực thi cụ thể |
|---|---|---|---|
| Đọc schema raw và notebook 01 | Có ghi chú input/output, cột và thao tác lọc | 20/11 | Mở [notebook 01](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/01-preprocess.html). Ghi lại 9 cột raw, cách tạo `event_time_ts`, cách bỏ `user_session` null, cách mã hóa session, cách xử lý event lặp và tên file Parquet đầu ra. Không sửa code trước khi ghi lại pipeline gốc. |
| Audit dataset | Có `data/raw_audit.csv` | 21/11 | Chạy script đọc raw và xuất số dòng, số null từng cột, min/max thời gian, số event type, số session, user, item, category, brand. Lưu cả command và timestamp chạy. |
| Sampling theo session | Script tái lập được ở 10%, 25%, 50%, 100% | 21/11 | Tính stable hash trên `user_session`, giữ session nếu hash nằm dưới ngưỡng phần trăm, rồi lọc toàn bộ dòng thuộc session. Kiểm tra mỗi session được giữ đủ event như raw. Không sample từng dòng. |
| Xuất subset và manifest | Có manifest counts | 21/11 | Manifest phải ghi input path, seed, rule chọn session, số session/event/user/item, thời gian tạo và output path. TV2 chỉ được dùng subset có manifest. |
| Chạy preliminary preprocessing | Có Parquet sơ bộ | 22/11 | Chạy lần lượt timestamp conversion, bỏ session null, categorify session, sort theo session/time, bỏ consecutive repeated item nếu giữ bước này, tạo `prod_first_event_time_ts`. Ghi counts trước/sau từng bước. |
| Chạy ETL NVTabular | Có Parquet + schema | 22/11 | Tận dụng [notebook 02](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/02-ETL-with-NVTabular.html). Kiểm tra `Categorify`, time features, price normalization, Groupby theo `user_session`, `ListSlice`, minimum session length. Mở lại Parquet và in schema sau khi export. |
| Tạo split và mapping | Có split files + mapping | 22/11 | Dùng ngày 1–5 train, ngày 6 validation, ngày 7 test theo ngày của session. Không random sau khi tạo target. Lưu counts, product ID train và mapping encoded ID ↔ original `product_id`. |
| Tạo bốn subset | Có 10/25/50/100% manifests | 23/11 | Dùng cùng sampling rule và seed policy. Ghi event/session/user/item thực tế của từng mức. Không gọi 10% user là 10% event nếu chưa đo. |
| Hỗ trợ sửa data/schema | Mọi run đọc cùng schema | 26/11 | Khi TV2 báo lỗi, tái tạo lỗi bằng command của TV2, sửa tại pipeline, tăng version output và gửi lại schema/counts. Không sửa trực tiếp file Parquet bằng tay. |
| Reproduce preprocessing | Thành viên khác chạy lại được | 29/11 | Đưa command raw → sample → Parquet vào README. TV1 không tự chạy một mình, phải nhờ người khác chạy trong thư mục sạch và đối chiếu counts. |

## TV2 — Model, experiment và evaluation

| Task | Yêu cầu đầu ra (done gate) | Deadline | Ghi chú thực thi cụ thể |
|---|---|---|---|
| Đọc notebook 03 | Có model protocol | 20/11 | Đọc [notebook 03](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html). Ghi rõ GRU dùng input nào, XLNet dùng masking nào, dataloader nào, loss nào, training arguments nào và metric nào. |
| Chốt evaluation protocol | Có split/target/catalog/K | 21/11 | Viết một trang quy định: input prefix, next-item target, user/session đủ điều kiện, candidate catalog từ train, seen-item rule, `K=20`, Recall@20 và NDCG@20. Không đổi quy định sau khi nhìn kết quả. |
| Viết metric và Popularity | Toy test đúng | 21/11 | Tạo toy example có target nằm hạng 1, hạng 20 và ngoài top-20. Kiểm tra Recall/NDCG bằng tay. Popularity phải fit trên train rồi trả danh sách top-20 cho test prefix. |
| Viết script GRU/XLNet | Smoke run thành công | 22/11 | Tận dụng model block của repo, chuyển path/schema/config thành arguments. Script phải nhận `--data`, `--split`, `--output`, `--batch-size`, `--epochs`, `--seed`, `--model`. |
| Viết experiment matrix | Có `docs/experiment_matrix.md` | 22/11 | Mỗi dòng matrix phải có run_id, model, subset, input format, batch size, resource config, command, metric output và log output. Không để TV3 tự đoán config. |
| Smoke end-to-end | Có prediction + metric | 22/11 | Chạy raw sample → dataloader → train ít bước → inference → top-20 → Recall/NDCG. Kiểm tra encoded ID được đổi về product ID gốc. |
| Giao script E1 | TV3 chạy ba model | 23/11 | Giao command cụ thể cho Popularity, GRU, XLNet. Ghi rõ cái nào chạy sequential, cái nào cần dọn VRAM/restart kernel. |
| Giao script E2–E4 | TV3 chạy đúng matrix | 25/11 | Đóng gói run scripts hoặc config files. Không yêu cầu TV3 sửa Python để đổi subset/resource. Mọi thay đổi phải quay lại TV2. |
| Phân tích E1–E5 | Có bảng/kết luận/limitations | 26/11 | Từ raw logs, tính mean/std nếu có lặp, so model, tính runtime trên một triệu event, vẽ scaling curve và nêu bottleneck. Không lấy số tutorial làm số nhóm. |
| Chốt metrics cho TV4 | Có metrics package chính thức | 27/11 | Gửi CSV/JSON có run_id, config, metric, source log và ghi chú run bị loại. TV4 chỉ dùng package này để làm report. |
| Reproduce/Q&A | Một command chạy lại được | 29/11 | Nhờ thành viên khác chạy evaluation từ checkpoint hoặc output đã lưu. Chuẩn bị trả lời về ground truth, leakage, K, candidate catalog, GRU và XLNet. |

## TV3 — Môi trường và vận hành run

| Task | Yêu cầu đầu ra (done gate) | Deadline | Ghi chú thực thi cụ thể |
|---|---|---|---|
| Dựng GPU VM/Docker | Import test thành công | 20/11 | Dùng hướng dẫn container trong [notebook 02](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/02-ETL-with-NVTabular.html). Ghi image tag, GPU, driver, CUDA, Python và package versions. Không cài package thủ công mà không ghi lại. |
| Ghi baseline resource | Có environment log | 20/11 | Chạy một lệnh đọc sample và lưu RAM/VRAM trước-sau, wall time, GPU utilization nếu có. Đây là baseline để so E2/E3. |
| Smoke test repo | Đọc data và chạy model step | 21/11 | Chạy một cell/lệnh nhỏ của [notebook 03](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html). Nếu lỗi, ghi command, traceback, package version và cách sửa. |
| Benchmark collector | Có run_id và raw log | 22/11 | Collector phải ghi start/end time, exit code, stdout/stderr path, peak memory, GPU memory, config path và output path. Không chỉ ghi thời gian bằng tay. |
| Chạy E1 | Ba model có raw logs | 23/11 | Đọc đúng script TV2, chạy Popularity/GRU/XLNet theo cùng data/split/K. Sau mỗi model lưu log riêng, checkpoint/output riêng và trạng thái pass/fail. |
| Chạy E2 | Bốn subset có raw logs | 24/11 | Chạy đúng 10/25/50/100%. Trước mỗi run ghi counts từ manifest, sau mỗi run ghi preprocessing/train/memory. Không đổi batch size giữa các subset. |
| Chạy E3 | Hai resource configs | 25/11 | Chỉ thay một biến TV2 chỉ định, ví dụ batch size 32 và 128. Giữ model, data, split, epoch và sequence length cố định. Ghi rõ warm-up/cache. |
| Chạy E4 | CSV/Parquet cùng dữ liệu | 25/11 | Kiểm tra row count và checksum/counts trước khi đo. Đo file size, read time, preprocessing time và memory. Không so CSV raw với Parquet đã lọc khác nội dung. |
| Hoàn tất E5/rerun lỗi | E1–E5 có pass/fail | 26/11 | Tạo bảng run registry gồm pass, fail, OOM, timeout. Rerun chỉ run lỗi có nguyên nhân sửa được. Giữ lại log lỗi, không xóa. |
| Bàn giao logs | TV2 xác nhận đủ | 26/11 | Gửi thư mục logs, raw CSV/JSON, config, environment snapshot và ghi chú cache/warm-up. TV2 phải reply xác nhận thiếu gì trước khi TV3 đóng task. |
| Reproduce/cleanup | Một run chạy lại, cloud dừng | 29/11 | Chạy lại đúng một run chính theo README. Sau khi nhóm xác nhận, stop/terminate resource và lưu cleanup record. |

## TV4 — Demo, tích hợp, report và slide

| Task | Yêu cầu đầu ra (done gate) | Deadline | Ghi chú thực thi cụ thể |
|---|---|---|---|
| Tạo cấu trúc demo/report | Có README khung và outline | 20/11 | Tạo thư mục app, reports, figures, references. Tích hợp nghĩa là nối input session → inference command/file → top-20 output → UI, không sửa model. |
| Chốt prediction contract | Có sample input/output | 22/11 | Nhận từ TV2 tên field session, product ID, score, rank, target thật và model name. Lưu một JSON mẫu được TV2 xác nhận. |
| Tạo template bảng/hình | Có cột, đơn vị, run_id | 23/11 | Tạo template E1–E5 nhưng để trống số liệu. Mỗi hình phải có title, axis unit, legend và source run_id. |
| Theo dõi logs | Có draft caption/figure | 26/11 | Nhận raw logs từ TV3 nhưng không tự kết luận. Chỉ ghi chú nguồn, cấu hình, warm-up và câu hỏi cần TV2 xác nhận. |
| Nhận metrics chính thức | Có metrics package | 27/11 | Chỉ dùng số liệu TV2 đã chốt. Nếu report cần số khác, hỏi TV2 thay vì tự tính một cách khác. |
| Tích hợp inference demo | Session → top-20 → target thật | 28/11 | Dùng checkpoint/output đã bàn giao. Xử lý loading, lỗi, session lạ và mapping product ID. Không retrain trong request. |
| Viết results/limitations | Report draft có phân tích | 28/11 | Mỗi kết luận phải nối được với experiment, bảng/hình, số đo và limitation. Đối chiếu [requirement.txt](C:/Ổ D/big data/big-data-project/requirement.txt). |
| Hoàn thiện report | Report tiếng Anh hoàn chỉnh | 29/11 | Bao gồm dataset/5V, sampling, preprocessing, environment, model, E1–E5, demo, limitations, references, license và AI statement. |
| Hoàn thiện slide/script | Đủ 15 phút + Q&A 5 phút | 29/11 | Mỗi thành viên có phần nói, số liệu trên slide khớp report và metrics package. |
| Rehearsal/fallback | Demo fallback và rehearsal đạt thời lượng | 29/11 | Chuẩn bị video/screenshot hoặc prediction output tĩnh nếu live demo lỗi. |
