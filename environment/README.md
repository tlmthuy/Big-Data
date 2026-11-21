# TV3 — Môi trường và nhận script TV2

## Trạng thái hiện tại

- Metric/Popularity đã qua toy test trên Windows, Python 3.13.12; chưa chạy dataset thật hoặc GPU. Code dùng API Python >= 3.10.
- `environment.yml` là môi trường CPU/toy Python 3.10, không cài Merlin/cuDF/NVTabular/PyTorch. Chưa chạy lại trên Python 3.10.
- Dockerfile nhận image Merlin qua build argument, chưa có image/digest GPU được nhóm xác minh. Không có môi trường GPU sẵn dùng chỉ bằng build mặc định.
- GRU/XLNet đã có CLI trên main và đạt [toy GPU smoke WSL RTX 3050](../metrics/tv2-model-smoke/README.md). Local model runtime chiếm 4,04 GB, [requirements](smoke-models.requirements.txt); runtime này không gồm cuDF/NVTabular và không thay image Docker/cloud chính thức. Config/collector E1–E4 và công cụ E5 đã tích hợp, có [hướng dẫn và lệnh toy](../docs/modeling/experiment_runbook.md), **chưa xác minh trên dữ liệu thật**.

## Nhận bàn giao TV2

TV3 nhận hai artifact trung gian TV1 theo
[hướng dẫn bàn giao dữ liệu](../docs/tv1_data_handoff.md) và tra cứu
[manifest chung](../data/manifests/tv1_data_handoff.json), không cần ký nhận.
Đây là event tháng
và lookup first-seen, chưa phải sequence/split cuối để chạy model.

Từ gốc repo:

```bash
git switch main
git pull --ff-only origin main
git rev-parse HEAD
python -m json.tool configs/tv2_handoff.json
```

Đọc [manifest TV2](../configs/tv2_handoff.json), [lệnh chạy và input/output](../docs/modeling/tv2_runbook.md), [protocol](../docs/modeling/model_protocol.md), rồi [experiment matrix](../docs/experiment_matrix.md). Lưu commit thực tế khi chạy. Command trong manifest là mảng argv chạy từ root; `{run_id}` và `{output_dir}` phải được thay bằng giá trị riêng của run, không chạy nguyên placeholder.

Checksum trong manifest dành cho các file code/fixture đã bàn giao, chuẩn hóa CRLF thành LF trước SHA-256 để checkout Windows/Linux không lệch. Kiểm tra từ root:

```bash
python -c "import hashlib,json,pathlib; m=json.loads(pathlib.Path('configs/tv2_handoff.json').read_text(encoding='utf-8')); assert all(hashlib.sha256(pathlib.Path(p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()==h for p,h in m['files_sha256'].items()); print('PASS: handoff checksums')"
```

Khi TV2 sửa code phải cập nhật manifest. Phần pending chưa có command được phê duyệt: TV3 không tự suy ra cấu hình experiment.

## Kiểm tra CPU/toy

Dùng Python >= 3.10 hiện có; toy JSONL dùng thư viện chuẩn. Muốn tạo môi trường Conda riêng:

```bash
cd environment
conda env create -f environment.yml
conda activate big-data-recsys
cd ..
python -m unittest discover -s evaluation/tests -v
python -m evaluation.run_popularity --sessions evaluation/tests/fixtures/sessions.jsonl --catalog evaluation/tests/fixtures/catalog.json --train-through 1 --subset toy --run-id tv3-local-day1 --output metrics/local/tv3-local-day1
```

Nếu dùng môi trường có sẵn, chạy hai lệnh Python từ root; cần `pyarrow` để test Parquet không bị skip. Kết quả mong đợi: Recall@20 = 2/3, NDCG@20 ≈ 0.4092234162 trên 3 validation session. Đổi run_id/output khi chạy lại; không ghi đè output lịch sử.

## Dựng và xác minh GPU runtime trên Ubuntu

1. TV3 chọn image Merlin ứng viên theo [nguồn NVIDIA đã pin](../docs/references.md), đối chiếu driver/GPU của VM. Image ứng viên chưa được coi là runtime chính thức trước smoke test. Không nâng Python hoặc cài đè stack CUDA/cuDF để khớp môi trường local.
2. Trên VM kiểm tra `nvidia-smi`, `docker --version`, `docker info`; cấu hình NVIDIA Container Toolkit để container nhìn thấy GPU. Ghi lỗi nếu bước này chưa đạt.
3. Từ root, đặt biến `MERLIN_IMAGE` thành image tag/digest thực tế rồi chạy:

```bash
docker build --build-arg MERLIN_IMAGE="$MERLIN_IMAGE" -f environment/Dockerfile -t big-data-recsys:smoke .
docker run --rm --gpus all -v "$PWD:/workspace" -w /workspace big-data-recsys:smoke nvidia-smi
docker run --rm --gpus all -v "$PWD:/workspace" -w /workspace big-data-recsys:smoke python -c "import sys, cudf, cupy, nvtabular, torch, transformers4rec; print(sys.version); print(torch.__version__, torch.version.cuda); print(torch.cuda.is_available()); assert torch.cuda.is_available(); print(cupy.arange(3)); print(cudf.Series([1, 2, 3]).sum())"
docker run --rm --gpus all -v "$PWD:/workspace" -w /workspace big-data-recsys:smoke python -m unittest discover -s evaluation/tests -v
```

Dockerfile chỉ bọc image ứng viên, không tự cài dependencies hoặc đóng gói code; code được mount từ checkout. Không chạy `environment.yml` để thay môi trường trong container. Nếu image thiếu package hoặc Python < 3.10, lưu traceback và phối hợp TV1/TV2 sửa tương thích trước khi pin runtime.

4. Lưu `docker image inspect big-data-recsys:smoke`, `python -m pip freeze`, GPU/CPU/RAM, Ubuntu, driver, CUDA, Docker, Python và package versions trong artifact môi trường; cập nhật bảng bên dưới bằng giá trị thực. Import/toy test đạt chưa thay thế smoke preprocessing và model step khi TV1/TV2 bàn giao code.

## Bản ghi runtime chính thức

| Thông tin | Giá trị xác minh |
| --- | --- |
| GPU, VRAM / CPU / RAM / Ubuntu | Chưa xác minh |
| Driver / CUDA / Docker / NVIDIA Container Toolkit | Chưa xác minh |
| Merlin image tag, digest, local image ID | Chưa chọn/xác minh |
| Python / PyTorch / Transformers4Rec | Chưa xác minh trong GPU runtime |
| cuDF / CuPy / NVTabular / Merlin | Chưa xác minh trong GPU runtime |
| Commit chạy, command, log path, kết quả smoke | Chưa có run GPU |

## Trước khi chạy experiment thật

TV1 bàn giao sequence/split/schema/mapping/catalog và manifest, TV2 kiểm tra tiếp nhận; TV2 cung cấp command/config và partition train/eval cho từng run; TV3 chuẩn bị collector và environment snapshot. Chỉ chạy E1–E4 khi các đầu vào này có thật và được bàn giao. E5 tổng hợp log E2, không tạo lần chạy model riêng. Ghi kết quả bàn giao tại [handoff](../docs/handoff.md); TV3 không đổi protocol, model hoặc metric.

## Dữ liệu TV1 chính thức — 21/11/2026

Dùng [manifest E2](../data/manifests/e2_preprocessing_verified.json) để bind
sessions/schema/catalog/telemetry cùng run tại `data/clean/e2-weekly/<subset>/`.
First-seen tháng dùng chung; bộ DuckDB/workflows/splits-v2 cũ chỉ để đối chiếu.
Lệnh preprocessing CSV/Parquet và xuất telemetry:
[hướng dẫn TV1](../docs/weekly_workflow.md). Chưa có kết quả benchmark model
chính thức chỉ từ việc chấp nhận bộ preprocessing này.
