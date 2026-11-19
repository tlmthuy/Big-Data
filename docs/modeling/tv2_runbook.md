# TV2 — Chạy metric và Popularity

TV3 bắt đầu tại [environment/README.md](../../environment/README.md). Manifest bàn giao hiện tại: [tv2_handoff.json](../../configs/tv2_handoff.json); metric/Popularity đã kiểm tra toy; [GRU/XLNet](neural_runbook.md) đã đạt toy GPU smoke trên WSL laptop. E1–E5 còn chờ runtime chính thức TV3 và artifact TV1.

## File bàn giao theo task ngày 20/11

| Task | File chính | Kiểm tra / bằng chứng |
| --- | --- | --- |
| Chốt split | [model_protocol.md](model_protocol.md#preprocessing-và-split-đã-chốt) | Lịch test tại mục Daily fine-tuning; tiếp nhận artifact thật ngày 21/11 là task riêng |
| Chốt catalog và K | [model_protocol.md](model_protocol.md#evaluation-chung-cho-ba-model), [data.py](../../evaluation/data.py) | Catalog/schema được mô tả bên dưới; K=20 trong ranking.py |
| Recall@20 | [ranking.py](../../evaluation/ranking.py) | [test_tv2.py](../../evaluation/tests/test_tv2.py), [test log](../../metrics/tv2-final-test-tests.txt) |
| NDCG@20 | [ranking.py](../../evaluation/ranking.py) | Cùng toy test: hạng 1/20/ngoài Top-20 và tổng hợp theo session |
| Popularity | [popularity.py](../../models/popularity.py), [CLI](../../evaluation/run_popularity.py) | [Toy output](../../metrics/tv2-toy-day1/metrics.json), test cumulative/train-only/tie-break |

## Kiểm tra nhanh trên dữ liệu toy

Từ root repo, code dùng Python >= 3.10; offline tests trên Python 3.13.12, GPU smoke model trên WSL Python 3.10.12. Runtime Docker chính thức chưa xác minh. Hash file đọc theo chunk, không cần API Python 3.11.

```powershell
python -m unittest discover -s evaluation/tests -v
python -m evaluation.run_popularity --sessions evaluation/tests/fixtures/sessions.jsonl --catalog evaluation/tests/fixtures/catalog.json --train-through 1 --subset toy --run-id tv2-local-day1 --output metrics/local/tv2-local-day1
```

Thư mục output phải chưa tồn tại; khi chạy lại đổi cả run_id và output. `metrics/local/` được Git bỏ qua; kết quả toy đã bàn giao vẫn giữ tại `metrics/tv2-toy-day1/`. Toy dùng thư viện chuẩn; Parquet cần `pyarrow` trong requirements của repo. Test Parquet tự skip khi chưa cài thư viện.

Expected: 3 validation session partition 2; Recall@20 = `2/3`; NDCG@20 = `(1 + 1/log2(21))/3` ≈ `0.4092234162323177`. Train counts = `{3: 2, 4: 1, 5: 1}`; Top-20 là ID 3…22. Target 3 hạng 1, target 22 hạng 20, target 23 ngoài Top-20. Session có target 25 ở holdout và train tương lai không làm tăng popularity tại bước 1.

## Đầu vào thật từ TV1

TV1 bàn giao Parquet sequence, không dùng raw subset CSV làm đầu vào model. CLI nhận đường dẫn root layout nguồn:

```text
sessions_by_day/
  1/train.parquet
  1/valid.parquet
  1/test.parquet
  2/train.parquet
  2/valid.parquet
  2/test.parquet
  ...
```

Parquet phải có `user_session`, `product_id-list` (list encoded int); nếu có `day_index` thì phải khớp thư mục. Pad phải nằm cuối sequence. Script đọc từng batch Parquet, kiểm tra mỗi session xuất hiện đúng một lần và lưu counts cả split rỗng bằng 0. Layout sharded khác cần adapter được đối chiếu schema trước khi chạy.

Định dạng JSONL tương đương cho toy/debug: mỗi dòng có `user_session`, `day_index` (int), `split` (`train`, `validation`, `test`), `product_ids` (list encoded int). Xem `evaluation/tests/fixtures/sessions.jsonl`.

Catalog JSON được **xuất từ vocabulary tuần đã fit của subset**, không tạo bằng unique item train. Mỗi dòng mapping giữ product ID gốc và encoded ID thực tế của runtime; liệt kê token kỹ thuật thật, gồm mask nếu runtime dùng. Ví dụ schema (ID minh họa, không phải catalog dataset):

```json
{
  "technical_ids": {"padding": 0, "null": 1, "oov": 2, "mask": 99},
  "items": [
    {"encoded_id": 3, "product_id": "1000001"},
    {"encoded_id": 4, "product_id": "1000002"}
  ]
}
```

Mọi real product của vocabulary cần có trong `items`, không chỉ các ID ví dụ trên. Catalog ít hơn 20 item trả toàn bộ catalog; không chèn token kỹ thuật để đủ 20. Không suy diễn mask = 99 hoặc real ID luôn bắt đầu từ 3 khi chưa đối chiếu runtime/mapping. Loader kiểm tra một-một, không giao technical IDs; tính đầy đủ và nguồn vocabulary cần được TV1/TV2 đối chiếu manifest.

```powershell
python -m evaluation.run_popularity --sessions data/clean/10/sessions_by_day --catalog data/manifests/catalog_10.json --train-through 1 --subset 10 --run-id popularity-10-day1 --output metrics/popularity-10-day1
```

Đây là **lệnh mẫu cho artifact tương lai**, chưa có các path đó trên checkout. `--train-through t` cộng train partition 1…t đúng một lần và đánh giá validation t+1. Chạy t tiếp theo tái dựng đúng cumulative counts từ đầu, không cần checkpoint; kết quả tương đương cộng dồn, nhưng chi phí đọc lại không được coi là benchmark incremental train. Không đếm lại theo epoch. Lịch test đã chốt: D là day_index cuối của membership đầy đủ; sau khi cố định cấu hình bằng validation, chạy `--train-through D-1 --eval-split test` để đánh giá test D. CLI từ chối test ở partition khác; test D rỗng báo lỗi. Không cắt membership đầu vào để thay đổi D.

## Output và giới hạn

- `predictions.jsonl`: session, prefix, target, top20 encoded ID, product ID gốc theo thứ tự; seen items được phép xuất hiện.
- `popularity.json`: counts train thực, train_days và top20.
- `metrics.json`: Recall/NDCG, tổng điểm, số session, session/distinct-item counts theo split, config, subset, run_id, input/catalog checksums, Python/platform, Git commit và output path.

`train_with_input_scan_seconds` gồm scan dữ liệu; `ranking_once_seconds` chỉ đo tạo danh sách chung một lần. Đây chưa phải phép đo inference throughput/memory E1–E5. Audit giữ session membership và distinct-item sets trong RAM; checksum quét thêm file. Cần benchmark collector/runtime của TV3 và chuẩn đo TV2 trước chạy experiment chính thức. CLI không chứng minh preprocessing/RNG đúng nguồn chỉ bằng đọc output; vẫn cần manifest GPU của TV1.

Protocol: [model_protocol.md](model_protocol.md). Chưa chạy dataset thật; kiểm tra tiếp nhận dữ liệu TV1 là task riêng ngày 21/11. Không coi toy GPU smoke là kết quả E1 hoặc xác nhận split thật.
