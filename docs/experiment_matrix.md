# Experiment matrix

**Trạng thái: đã có 11 run config và runner E1–E4; chưa có kết quả experiment thật.** TV3 xem [configs](../configs/experiments.json), [site template](../configs/site.example.json), [runbook model/experiment](modeling/neural_runbook.md) và [manifest TV2](../configs/tv2_handoff.json). GRU/XLNet còn chờ smoke runtime; E2 cần telemetry TV1; E4 full cần entrypoint preprocessing chung CSV/Parquet của TV1.

| ID | Câu hỏi | Biến thay đổi | Kết quả bắt buộc |
|---|---|---|---|
| E1 | Model nào tốt hơn? | Popularity / GRU / XLNet | Recall@20, NDCG@20, train/inference time |
| E2 | Dữ liệu tăng ảnh hưởng thế nào? | 10%, 25%, 50%, 100% session | runtime, memory, bytes, event/user count |
| E3 | Resource ảnh hưởng ra sao? | một resource variable | runtime, throughput, memory, cost nếu có |
| E4 | Định dạng nào hiệu quả hơn? | CSV / Parquet cùng nội dung | size, read time, preprocessing time, memory |
| E5 | Có scale được không? | phân tích các run E2 | runtime/1M event, bottleneck, uncertainty |

Số liệu trống cho tới khi có run thật.

## Quy ước dữ liệu cho E1–E5 — cập nhật 19/11/2026

Theo [preprocessing_review.md](preprocessing_review.md) và [model_protocol.md](modeling/model_protocol.md), fit workflow trước split trên tuần của từng subset; catalog chung là các product ID thực trong vocabulary đó. Mapping không giới hạn về train từng partition. Popularity chỉ đếm train đã dùng; model baseline chỉ dùng product ID.

- E1: ba model cùng catalog tuần của subset, cùng split, target, K và quy tắc loại token kỹ thuật.
- E2/E5: fit workflow riêng từng subset; ghi vocabulary size, event/session counts và thời gian/bộ nhớ thực tế. First-seen tháng là artifact chung: báo chi phí tạo riêng, chi phí mỗi subset riêng; nếu báo end-to-end từ CSV tháng thì cộng/ghi rõ chi phí chung, không âm thầm bỏ khỏi tổng.
- E3: giữ nguyên workflow/schema/mapping/catalog/split giữa các cấu hình tài nguyên.
- E4: CSV và Parquet phải cùng nội dung event và cùng đầu vào feature; không so CSV tháng với Parquet tuần hoặc file session. Dùng cùng artifact first-seen và quy ước cache/phạm vi đo cho hai phía.

Day t/t+1 trong daily fine-tuning là partition day_index theo công thức notebook 02. Test không dùng cập nhật trọng số/chọn cấu hình; preprocessing fit trước split có dùng dữ liệu tuần gồm validation/test, cần ghi đúng trong báo cáo.

## Matrix đã chốt với TV2 — 19/11/2026

E1 subset 10%; E2/E5 GRU; E3 GRU 10%, chỉ batch train 32 ↔ 128. Epoch 3/partition, seed 1, length 20; LR theo notebook 03 (GRU .00071, XLNet .000666). E1/E2 chạy final test D sau khi cấu hình được cố định; E3 đánh giá validation D. Tất cả giữ train 1…D−1 và validation t+1.

| run_id | Model | Subset | Batch train | Input | Eval | Output |
| --- | --- | --- | --- | --- | --- | --- |
| `e1-popularity-010` | popularity | 10% session | — | session Parquet | test D | `metrics/raw/e1-popularity-010` |
| `e1-gru-010` | gru | 10% session | 256 | session Parquet | test D | `metrics/raw/e1-gru-010` |
| `e1-xlnet-010` | xlnet | 10% session | 256 | session Parquet | test D | `metrics/raw/e1-xlnet-010` |
| `e2-gru-010` | gru | 10% session | 256 | session Parquet | test D | `metrics/raw/e2-gru-010` |
| `e2-gru-025` | gru | 25% session | 256 | session Parquet | test D | `metrics/raw/e2-gru-025` |
| `e2-gru-050` | gru | 50% session | 256 | session Parquet | test D | `metrics/raw/e2-gru-050` |
| `e2-gru-100` | gru | 100% session | 256 | session Parquet | test D | `metrics/raw/e2-gru-100` |
| `e3-gru-010-b32` | gru | 10% session | 32 | session Parquet | validation D | `metrics/raw/e3-gru-010-b32` |
| `e3-gru-010-b128` | gru | 10% session | 128 | session Parquet | validation D | `metrics/raw/e3-gru-010-b128` |
| `e4-010-csv` | shared TV1 preprocessing | 10% session | — | csv | —  | `metrics/raw/e4-010-csv` |
| `e4-010-parquet` | shared TV1 preprocessing | 10% session | — | parquet | —  | `metrics/raw/e4-010-parquet` |

Mỗi run có command đầy đủ và resource config trong `configs/experiments.json`. Workflow/mapping/catalog version lấy từ `site.subsets.<subset>` và ghi kèm checksum vào `run.json`; không điền phiên bản giả trước khi TV1 bàn giao. Artifact thực và environment snapshot được bind qua site.local.json, không sửa Python.

```bash
python -m scripts.runs.run_experiments --experiment E1
python -m scripts.runs.run_experiments --run-id e1-gru-010 --site configs/site.local.json --execute
python -m benchmark.scalability --logs metrics/raw --output reports/e5
```

Collector chạy process mới, lưu exit code/stdout/stderr, wall time và sampled process-tree RSS. Neural runner lưu train time (gồm sequence scan), final inference compute/Top-20, evaluation gồm I/O, peak CUDA allocated/reserved và checkpoint. Popularity tạo một ranking dùng chung nên ghi rõ inference scope; không gọi ranking-once là throughput inference toàn pipeline. Không có cloud cost nếu TV3 chưa ghi giá tài nguyên và thời lượng.

E2 gắn raw-read/preprocessing telemetry đã đo của TV1 với model run mới; tổng stage là composed runtime, không phải một wall-clock end-to-end. Chi phí first-seen tháng dùng chung ghi riêng. E4 kiểm tra cùng event values/string schema, cache ấm, conversion Parquet ngoài phép đo; full preprocessing dùng cùng argv TV1. E5 xuất CSV/SVG từ successful E2 logs, báo partial nếu thiếu mức, không có run model riêng. Phạm vi, cache, memory và giới hạn chi tiết trong runbook.
