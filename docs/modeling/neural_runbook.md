# TV2 — Script GRU/XLNet

## Trạng thái

Hai task script GRU/XLNet được tích hợp riêng vào main từ nhánh TV2. Cả hai đã train/eval và đạt kiểm tra checkpoint trên GPU laptop; [bằng chứng](../../metrics/tv2-model-smoke/README.md). Đây là dữ liệu toy; chưa có kết quả eCommerce, benchmark E1–E5 hay xác nhận runtime chính thức TV3.

## Script model

Runner chung: [run_neural.py](../../evaluation/run_neural.py). Chọn `--model gru` hoặc `--model xlnet`; architecture nằm tại [session_models.py](../../models/session_models.py). Chạy từ root:

```bash
python -m evaluation.run_neural --model gru --data data/clean/10/sessions_by_day --schema data/clean/10/schema.pbtxt --catalog data/manifests/catalog_10.json --batch-size 256 --eval-batch-size 32 --epochs 3 --seed 1 --split validation --subset 10 --run-id gru-10-validation --output metrics/local/gru-10-validation
python -m evaluation.run_neural --model xlnet --data data/clean/10/sessions_by_day --schema data/clean/10/schema.pbtxt --catalog data/manifests/catalog_10.json --batch-size 256 --eval-batch-size 32 --epochs 3 --seed 1 --split validation --subset 10 --run-id xlnet-10-validation --output metrics/local/xlnet-10-validation
```

Các path thật trên là ví dụ chờ TV1 bàn giao, không có sẵn trong Git. Schema TF Metadata JSON (`feature`/`intDomain`/`annotation`) hoặc pbtxt phải từ workflow đã fit trước split; chỉ chọn cột `product_id-list`. Catalog phải đầy đủ theo vocabulary tuần. Không tạo mapping/schema mới trong runner. Padding nguồn là 0; runtime khác phải được đối chiếu trước khi đổi code.

Mặc định D lấy từ membership đầy đủ, train 1…D−1; `--train-through t` giới hạn đến t. Sau mỗi train t, đánh giá validation t+1 trên cùng model. Final `--split test --config-frozen` chỉ cho test D bằng checkpoint sau train D−1. Dùng validation để cố định cấu hình trước, không chọn lại sau khi thấy test. Output phải là thư mục mới.

| Tham số cố định ban đầu | GRU | XLNet |
| --- | --- | --- |
| Input | product ID | product ID |
| Sequence length, gồm target | 20 | 20 |
| Masking train / evaluation | causal / last item | MLM 0.15 / last item |
| d_model | 128 | 192 |
| Layers / heads | 1 GRU | 2 / 4 |
| LR | 0.00071 | 0.000666 |
| Epoch mỗi partition / seed | 3 / 1 | 3 / 1 |
| Batch train / eval | 256 / 32 | 256 / 32 |

`--learning-rate` cho phép cấu hình khi thử validation; cấu hình chính thức ghi tại matrix và metrics run. E3 chỉ đổi batch train 32/128. FP32, weight tying, full softmax, gradient clip 1.0, AdamW (betas .9/.999, eps 1e-8, weight decay 0), linear decay reset theo partition. Cùng optimizer/trọng số qua các ngày. Không shuffle, không drop batch cuối. Seed Python/NumPy/Torch; không cam kết bitwise qua runtime/GPU khác.

## Nhãn, catalog và output

- Đưa **sequence đầy đủ** vào model với `training=True` khi train, `testing=True` khi eval. Masking nguồn tạo target đúng một lần. Eval kiểm tra labels trả về khớp item cuối không padding; nếu sai thì dừng.
- GRU dùng `batch_first=True` vì tensor là `[batch, sequence, hidden]`; ngăn trộn các session thành bước thời gian. Causal output tại vị trí prefix không nhìn target phía sau. XLNet MLM che item cuối bằng masked embedding khi evaluation.
- Gather điểm trên real catalog trước Top-20, loại padding/null/OOV/mask và mọi mã không có trong catalog. Cho phép seen item; hòa điểm dùng encoded ID tăng dần. Recall/NDCG dùng metric chung của nhóm và trọng số theo session.
- `validation-dayN.jsonl`, `predictions.jsonl`: prefix/target/top20 và product ID gốc. `metrics.json`: daily history, split counts, config, input/code checksum, runtime/package, train/inference time và CUDA memory. `checkpoint.pt`: final weights/optimizer, model, trained days, input fingerprints. Checkpoint lớn không commit.
- `--checkpoint PATH` chỉ đánh giá lại checkpoint tin cậy của nhóm; kiểm tra model, membership/catalog/schema, originating train config và checksum code rồi bỏ train. Giữ cùng input path/checksum, train config và `--train-through` khi chạy lại; metrics tách config train gốc khỏi các args evaluation.
- `failure.json` giữ traceback/config nếu model runtime lỗi. Không đổi model để che lỗi XLNet/OOM.

## GPU smoke

Ngày 20/11/2026, cả hai CLI đã train/eval thành công trên RTX 3050 qua WSL Ubuntu 22.04, Python 3.10.12, PyTorch 1.13.1/CUDA 11.7 và source NVIDIA đã pin. Môi trường model riêng chiếm 4.040.455.500 byte, trong ngân sách 7 GB. Xem [output và cách kiểm tra](../../metrics/tv2-model-smoke/README.md). Đây là toy GPU integration; runtime Docker/ETL và benchmark chính thức vẫn do TV3 xác minh.

Chạy cả hai model với cùng lệnh sau, lần lượt đổi `--model` và run_id/output:

```bash
python -m evaluation.run_neural --model gru --data evaluation/tests/fixtures/sessions.jsonl --schema evaluation/tests/fixtures/schema.pbtxt --catalog evaluation/tests/fixtures/catalog.json --train-through 1 --epochs 1 --batch-size 2 --eval-batch-size 2 --device cuda --split validation --subset toy --run-id gru-gpu-smoke --output metrics/local/gru-gpu-smoke
```

Schema/IDs trên hoàn toàn tổng hợp. GPU smoke phải tạo prediction, metric và checkpoint; đổi target toy nhưng giữ prefix để kiểm tra prediction không phụ thuộc target trước khi dùng dataset thật. Test tự động offline có kiểm tra masking nguồn và GRU batch independence, không thay GPU integration test.

Sau mỗi run, kiểm tra checkpoint thật bằng `python -m scripts.runs.verify_neural_smoke --model gru --run-path metrics/local/gru-gpu-smoke` (đổi model/path tương ứng cho XLNet). Hai model đã đạt kiểm tra label item cuối, target bị che và độc lập giữa các session trong batch.

XLNet cần bộ nhớ cho activation theo batch × sequence² × layer/head và logits theo số vị trí train × vocabulary; GRU cũng có full-vocabulary logits. Không có số VRAM bảo đảm trước khi chạy. Runner ghi parameter bytes và peak CUDA allocated/reserved; collector ghi sampled process-tree RSS. Nếu batch chuẩn OOM, giữ log, trao đổi TV2 về config mới; không tự thay batch giữa E2 subsets.

## Config và collector

Config/collector/runner E1–E4 và công cụ E5 đã tích hợp cùng [hướng dẫn TV3](experiment_runbook.md). Đã kiểm tra bằng toy data, chưa xác minh trên dữ liệu thật. [Phép đo inference](inference_timing.md) thống nhất thời gian toàn bộ evaluation; `prediction_compute_seconds` là diagnostic riêng mỗi model.

## Nguồn và phần nhóm điều chỉnh

NVIDIA `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, Apache-2.0; [LICENSE giữ nguyên](../vendor/nvidia-transformers4rec/upstream/LICENSE). Đọc notebook 03 cells 20/22/26/33/39 và 62/64/67/73; `torch/features/sequence.py`, `torch/masking.py`, `torch/model/{base,prediction_task}.py`, `torch/block/{base,transformer}.py`, `torch/trainer.py::reset_lr_scheduler`, `merlin_standard_lib/schema/schema.py`; tests nguồn `tests/unit/torch/{test_masking.py,model/test_head.py,model/test_model.py}`.

Tái sử dụng architecture/masking/head và API schema; giữ attribution trong `session_models.py`. Nhóm bổ sung CLI, batch-first GRU, streaming PyArrow/JSONL thay MerlinDataLoader, vòng train PyTorch tường minh thay Trainer, daily LR reset, schema/catalog guard, Top-20 real catalog/metric chung, final-test protocol và checkpoint. Không tuyên bố loop mới bitwise tương đương Trainer. Snapshot pin nguồn không thay việc xác minh package/runtime thật.
