# TV2 — Phân tích kết quả E1–E5 — 24/11/2026

Nguồn tính toán: bản sao raw JSON từ VM, không lấy số từ các summary TV3 làm đầu vào. Danh mục file/SHA-256 tại `metrics/tv2-analysis-20261124/source_manifest.json`; 9 predictions files được tính lại metric trực tiếp trên VM, kiểm tra session không trùng và Top-20 unique/không token 0/1/2. Kết quả tại `prediction_checks.json`. Tất cả số dưới là một lần chạy/config, seed 1; không có mean/std qua các lần lặp.

Lệnh tái tạo: `python -m scripts.analyze_results` từ root, trên output path mới hoặc lưu trữ output cũ trước khi chạy lại. CSV đầy đủ ở `reports/tables/tv2-20261124/`; có run_id và source path. Biểu đồ SVG/CSV/JSON tại `reports/figures/tv2-20261124/scalability/`.

## E1 — So sánh model

Subset 10%, train partitions 1–6, test partition 7, 1.337 session; kiểm tra cùng session/catalog fingerprints và split counts. K=20, cho phép seen items. Thời gian inference là wall toàn evaluation, gồm input/output/metric, không phải forward latency thuần.

| run_id | Recall@20 | NDCG@20 | train_seconds_including_sequence_io | final_evaluation_seconds | eval_ms_per_session |
| --- | --- | --- | --- | --- | --- |
| e1-popularity-010 | 0.086761 | 0.034766 | 6.552077 | 0.075963 | 0.056816 |
| e1-gru-010 | 0.088257 | 0.038043 | 28.132647 | 0.702583 | 0.525492 |
| e1-xlnet-010 | 0.124907 | 0.051332 | 30.654357 | 0.858062 | 0.641782 |

XLNet có Recall/NDCG cao nhất trong ba run; Recall tăng 43.97% tương đối so Popularity. GRU chỉ nhỉnh hơn Popularity trên test này. Popularity có train/evaluation wall thấp nhất. Chênh lệch accuracy chưa có kiểm định hoặc nhiều seed; không kết luận ưu thế tổng quát. Không so inference với ranking một lần hoặc compute diagnostic. Train của neural gồm daily validation ngoài trường train_seconds; process_wall là số riêng bao gồm audit/khởi tạo/checkpoint.

## E2 — Tăng dữ liệu

GRU, train batch 256, eval batch 32, 3 epoch/partition, learning rate 0.00071 và seed 1 cố định; workflow/catalog fit riêng mỗi subset.

| run_id | n_events | n_sessions | Recall@20 | NDCG@20 | raw_read_seconds | preprocessing_seconds | train_seconds_including_sequence_io | final_evaluation_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| e2-gru-010 | 882808 | 1337 | 0.088257 | 0.038043 | 0.172557 | 30.449049 | 27.590926 | 0.701949 |
| e2-gru-025 | 2213138 | 3266 | 0.157379 | 0.071570 | 0.366867 | 34.093408 | 89.228299 | 2.243797 |
| e2-gru-050 | 4421037 | 6427 | 0.274778 | 0.121484 | 0.735025 | 37.860843 | 203.107899 | 5.128254 |
| e2-gru-100 | 8829314 | 13052 | 0.389902 | 0.180376 | 1.359735 | 45.411393 | 432.579236 | 11.888242 |

Accuracy tăng theo mức dữ liệu trong các run này. Các tập test và catalog khác nhau giữa subset, nên đây là kết quả từng kịch bản, chưa cô lập hoàn toàn tác động training data trên một test set cố định. Tỷ lệ subset là tỷ lệ session được sampling; event count là số đo thực. Chi phí first-seen tháng 1.516474s dùng chung được tách riêng.

## E3 — Batch train 32 và 128

Giữ cùng GRU/subset 10%, validation partition 7 gồm 1.324 session; eval batch 32 cố định. Không đặt accuracy validation E3 cạnh test E1 để chọn model tốt nhất.

| run_id | train_batch_size | Recall@20 | NDCG@20 | train_seconds_including_sequence_io | process_wall_seconds | final_evaluation_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| e3-gru-010-b32 | 32 | 0.196375 | 0.090616 | 51.657280 | 65.943116 | 0.715555 |
| e3-gru-010-b128 | 128 | 0.129909 | 0.059083 | 30.592869 | 44.769848 | 0.708310 |

Batch 128 có process wall nhanh hơn khoảng 1.47 lần nhưng Recall/NDCG thấp hơn batch 32. Cùng epoch nhưng số optimizer updates khác nhau nên có tradeoff accuracy/runtime; chưa khẳng định batch lớn luôn tốt hơn. Inference gần nhau vì eval batch không đổi. RSS chỉ mô tả quan sát, không dùng để suy luận tiết kiệm RAM.

## E4 — CSV và Parquet

Cặp full raw subset 10%, 882.808 event, chín cột string và multiplicity-sensitive fingerprint bằng nhau; cùng entrypoint preprocessing/first-seen. Chọn full rerun, loại cặp smoke 19.692 event khỏi bảng chính thức.

| run_id | bytes | read_seconds | preprocessing_wall_seconds_including_read |
| --- | --- | --- | --- |
| e4-full-010-csv | 134004153 | 0.454137 | 34.987557 |
| e4-full-010-parquet | 25382745 | 0.108501 | 33.571249 |

Parquet nhỏ hơn 5.28 lần, timed read nhanh hơn 4.19 lần trong lần đo này. Toàn preprocessing chênh ít hơn nhiều: còn gồm parse/cleanup/fit/groupby/split/write, nên lợi ích read không chuyển nguyên vẹn thành tốc độ cả pipeline. Cache ấm sau verification; conversion/verification ngoài timed read. Preprocessing wall đã gồm lần đọc của pipeline, không cộng thêm standalone read. Chưa có nhiều lần lặp hoặc cold-cache benchmark.

## E5 — Scaling và bottleneck

Tái tính trực tiếp từ bốn successful E2 run bằng `benchmark.scalability`; kiểm tra config hiệu lực/code/environment và không checkpoint replay. Đây là tổng stage ghép: raw_read + preprocessing không gồm raw_read/first-seen + train gồm sequence I/O + final evaluation gồm I/O; không phải wall một process end-to-end. Daily validation/audit/khởi tạo/checkpoint không được gọi là đã bao phủ trong tổng stage.

| run_id | n_events | composed_seconds_excluding_first_seen | seconds_per_million_events | bottleneck |
| --- | --- | --- | --- | --- |
| e2-gru-010 | 882808 | 58.914481 | 66.735328 | preprocessing_excluding_raw_read_and_first_seen |
| e2-gru-025 | 2213138 | 125.932371 | 56.902177 | train_including_sequence_io |
| e2-gru-050 | 4421037 | 246.832022 | 55.831250 | train_including_sequence_io |
| e2-gru-100 | 8829314 | 491.238607 | 55.637234 | train_including_sequence_io |

![Scaling curve](../../figures/tv2-20261124/scalability/scalability.svg)

Event tăng 10.00 lần, tổng stage không gồm first-seen tăng 8.34 lần từ 10% tới 100%. Bottleneck 10% là preprocessing; 25–100% là train gồm sequence I/O. Runtime trên triệu event giảm trong miền khảo sát, phản ánh amortization chi phí cố định; chưa suy ra linearity/asymptotic scaling hoặc hiệu năng ngoài 100%. First-seen được cộng đúng một lần cho từng kịch bản nếu báo tổng có chi phí chung.

## Limitations và phạm vi sử dụng

- Một run/mức, một seed: không có độ lệch chuẩn/confidence interval; không tự tạo mean/std từ session hoặc từ run config khác.
- Preprocessing fit trước split trên tuần mỗi subset theo protocol; đây là offline evaluation, không tuyên bố toàn bộ pipeline train-only. Test không dùng cập nhật model.
- RSS là peak quan sát qua lấy mẫu cây process, có thể đếm trùng shared pages. Truy vấn GPU đồng bộ có thể làm gap vượt 50 ms và bỏ lỡ đỉnh ngắn; không dùng các số này để kết luận RAM khác nhau. Muốn kết luận cần sampler độc lập và rerun liên quan.
- GPU memory sampled, peak CUDA allocated/reserved và total GPU used có scope khác nhau; không hoán đổi. Một GPU Tesla T4, VM 8 vCPU/31 GiB, Docker Merlin; không có kết luận cross-hardware hoặc cost vì chưa có nguồn giá/chi phí đã đo.
- Không warmup riêng, không flush OS cache; E4 cache ấm sau pair verification. Timing thể hiện điều kiện lần chạy, chưa phải SLA latency.
- Chỉ so model trong E1, batch trong E3; E2 thay cả train/eval/catalog. E4 là format raw và preprocessing, không phải tốc độ inference model.
- Gói này hoàn thành phân tích từ logs được kiểm tra; việc bàn giao metrics package chính thức cho TV4/TV5 và người nhận nghiệm thu là task tiếp theo, không tự xác nhận thay người nhận.
