# TV2 — Config, collector và benchmark E1–E5

Bộ code/config được tích hợp để TV3 chạy benchmark E1–E5. Đã kiểm tra E1/E3 qua collector với model thật trên GPU nhưng **dữ liệu toy**; E2/E4/E5 có regression test bằng fixture/log tổng hợp. **Chưa xác minh trên dữ liệu thật.** Có thể dùng toy run để tham khảo cách vận hành và format log; chưa dùng các thời gian này để kết luận accuracy/scalability trên eCommerce.

## Toy smoke có thể tái chạy

Trong runtime có PyTorch/Transformers4Rec và PyArrow, từ root repo:

```bash
python -m scripts.runs.prepare_toy_site --environment PATH_ENVIRONMENT_SNAPSHOT_JSON --output metrics/local/toy-inputs
python -m scripts.runs.run_experiments --experiment E1 --smoke --site metrics/local/toy-inputs/site.json --execute
python -m scripts.runs.run_experiments --experiment E3 --smoke --site metrics/local/toy-inputs/site.json --execute
python -m unittest discover -s evaluation/tests -v
```

Dùng output mới khi chạy lại (`--output-root`). Toy site dùng `data_kind=toy`, schema/catalog tổng hợp, không fit workflow và không giả mạo TV1 acceptance. Run ID có prefix `smoke-`, metadata có `purpose=toy_smoke`, model metrics có `subset=toy`. Thiếu `--smoke` thì toy site bị từ chối. E2/E4 không dùng model smoke này vì còn phải đo pipeline; test tổng hợp riêng kiểm tra telemetry, command binding CSV/Parquet và E5. [Bằng chứng](../../metrics/tv2-config-collector-smoke/README.md).

## Phép đo inference chung

`inference_seconds` dùng **full_evaluation_wall_v1** cho cả ba model. So sánh trên cùng split, dữ liệu, máy và chuẩn output; đọc [phạm vi đo](inference_timing.md). Collector `elapsed_seconds` đo cả process, không thay cho thời gian inference. E5 từ chối log cũ thiếu protocol này và bỏ qua run có nhãn toy.

## TV3 chạy E1–E4

1. Checkout đúng commit nhánh TV2 và [kiểm tra môi trường](../../environment/README.md). Copy `configs/site.example.json` → `configs/site.local.json` (Git ignore).
2. Điền path thật, D, phiên bản workflow/mapping/catalog, preprocessing manifest và environment snapshot; TV2 kiểm tra dữ liệu rồi đặt `accepted_by_tv2=true`. Sau validation/fix cấu hình, đặt `configuration_frozen=true` cho final test. Không dùng template null như dữ liệu thật.
3. Xem plan và chạy theo matrix:

```bash
python -m scripts.runs.run_experiments --experiment E1
python -m scripts.runs.run_experiments --experiment E1 --site configs/site.local.json --execute
python -m scripts.runs.run_experiments --experiment E2 --site configs/site.local.json --execute
python -m scripts.runs.run_experiments --experiment E3 --site configs/site.local.json --execute
python -m scripts.runs.run_experiments --experiment E4 --site configs/site.local.json --execute
```

Mặc định chạy tuần tự, process mới từng run để giải phóng VRAM. Chạy một run bằng `--run-id` thay `--experiment`. Output `metrics/raw/<run_id>/`: `run.json`, stdout/stderr và `artifacts/`. Output cũ bị từ chối; rerun dùng output-root mới và ghi lý do, không xóa log lỗi. Collector không tự áp CPU/RAM limit; E3 chỉ thay batch đã chốt. Snapshot môi trường phải ghi image/digest, GPU/CPU/RAM, driver/CUDA và package versions thật.

## E2, E4 và E5: phần phụ thuộc TV1

**E2:** mỗi subset fit workflow độc lập, dùng output tương ứng. TV1 bàn giao telemetry; chuyển các số đo thật sang `configs/pipeline_metrics.example.json` ở path ngoài Git hoặc manifest nhỏ đã review: `status=measured`, `n_events` là event tuần thực sau sampling trước tạo sequence; `read_seconds` là raw read; `preprocessing_seconds` gồm fit/features/groupby/split/write, **không gồm raw read hoặc first-seen tháng**. Ghi source log và artifact first-seen chung có thật. Runner thu train mới, gắn checksum/source của stage TV1 đã đo; đây là số đo ghép stage, không phải một process end-to-end được đo lại. Nếu chưa có telemetry, E2 từ chối chạy; TV3 không tự điền thời gian ước lượng.

**E4:** subset 10%, cùng chín field raw và cùng schema string; Parquet Snappy. Tạo cặp trước benchmark nếu chưa có:

```bash
python -m benchmark.format_io --prepare-pair --csv PATH_RAW_SUBSET_10 --parquet PATH_NEW_PARQUET
```

Điền hai path vào `site.e4`; `preprocessing_argv` là **cùng một command TV1** hỗ trợ `{input_path}`, `{input_format}`, `{output_dir}`. TV1 cần bàn giao entrypoint đọc cả CSV/Parquet với cùng first-seen và logic nghiệp vụ, ghi artifact vào output_dir mới. Command này chưa có trong repo; E4 full đang chờ TV1, không dùng hàm đọc file làm giả full preprocessing. Có `--read-only` cho diagnostic riêng, không tính là E4 hoàn tất.

Pair được kiểm tra số event và multiset fingerprint SHA-256 có giữ multiplicity, schema string đồng nhất, ngoài timed read. Đây là kiểm tra xác suất, không phải chứng minh bitwise hai file. Timing đọc gồm decode toàn bộ dữ liệu; cache ấm sau verification cho cả hai phía, không flush cache hệ điều hành. Chi phí tạo Parquet báo riêng, không trộn vào read time. Preprocessing child ghi elapsed/RSS riêng (gồm lần đọc input của chính pipeline); không cộng thêm standalone read vào elapsed của child rồi gọi là end-to-end. Parent RSS gồm cả audit; `peak_read_process_rss_bytes` chỉ lấy mẫu tại batch boundary.

**E5:** không chạy model; lấy successful E2 `run.json` và `artifacts/metrics.json`:

```bash
python -m benchmark.scalability --logs metrics/raw --output reports/e5
```

Xuất CSV, SVG đường tăng trưởng theo **event thực**, summary JSON có bottleneck và giới hạn. Runtime/1M event dùng tổng các stage không chồng lặp đã nêu; first-seen chung báo riêng và thêm vào mỗi kịch bản end-to-end nếu cần. Bỏ run fail, báo `partial` nếu thiếu subset; từ chối cấu hình hiệu lực (gồm LR), checksum code hoặc môi trường khác; từ chối checkpoint replay, lịch train/eval sai và trùng subset chưa chọn run. Báo số partition train thực tế của từng subset. Một run/mức chưa có độ lệch chuẩn/confidence interval.

