# TV3 — Môi trường và nhận script TV2

## Trạng thái hiện tại

- Metric/Popularity đã qua toy test trên Windows, Python 3.13.12; chưa chạy dataset thật hoặc GPU. Code dùng API Python >= 3.10.
- `environment.yml` là môi trường CPU/toy Python 3.10, không cài Merlin/cuDF/NVTabular/PyTorch. Chưa chạy lại trên Python 3.10.
- Dockerfile nhận image Merlin qua build argument. Image `merlin-pytorch:23.12` (digest trong [bản ghi runtime](#bản-ghi-runtime-chính-thức)) đã được chạy trên VM AWS Ubuntu 22.04 với Tesla T4, xác minh ngày 21/11/2026. Build vẫn phải truyền `--build-arg MERLIN_IMAGE=...`; Dockerfile không có image mặc định.
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

## Artifact môi trường

- [`pip_freeze_baseline.txt`](pip_freeze_baseline.txt): 257 dòng `pip freeze` của image `merlin-pytorch:23.12`, trước khi cài thêm package nào.
- Thông tin VM/Docker/GPU: `nvidia-smi`, `docker info`, `nvidia-ctk --version` lấy ngày 21/11/2026 (ghi trong bảng bên dưới).
- Cảnh báo `Tensorflow dtype mappings did not load` khi import Merlin là bình thường: image PyTorch không có TensorFlow và pipeline này không dùng.
- Package cài thêm ngoài image: chưa có. Nếu cài, ghi tên và version vào đây.

## Bản ghi runtime chính thức

| Thông tin | Giá trị xác minh |
| --- | --- |
| GPU, VRAM / CPU / RAM / Ubuntu | Tesla T4 (compute capability 7.5), 15360 MiB / Intel Xeon Platinum 8259CL @ 2.50GHz, 8 vCPU / 30,98 GiB / Ubuntu 22.04.5 LTS, kernel `6.8.0-1036-aws` |
| Driver / CUDA / Docker / NVIDIA Container Toolkit | `570.172.08` / driver hỗ trợ CUDA 12.8 (`nvidia-smi`), CUDA toolkit trong container `12.1.105` / Docker `28.4.0` / `1.20.2` |
| Merlin image tag, digest, local image ID | tag `23.12`; digest `nvcr.io/nvidia/merlin/merlin-pytorch@sha256:63874463e35350fabd873547311963adaf1e25cd12658707345738647cf5cd50`; local image ID `sha256:b61c670bff3e0f3e19b2c45c1687cf169ba9f66c7606de8573d5ead915f90051` |
| Python / PyTorch / Transformers4Rec | `3.10.12` / `2.1.0a0+4136153` (CUDA `12.1`, cuDNN `8902`) / `23.12.00` (transformers `4.27.1`) |
| cuDF / CuPy / NVTabular / Merlin | `23.04.00` / `12.0.0b3` / `23.08.00` / merlin.core `23.08.00`, merlin.models `23.12.00` |
| Commit chạy, command, log path, kết quả smoke | Commit: `5f839a7a081a8d59ed157b4eb1d4e974937dd3bf`; command: ba lệnh `docker run` ở bước 3 (`nvidia-smi`, import test, `unittest`) và `pip freeze` ([`pip_freeze_baseline.txt`](pip_freeze_baseline.txt)); log: thư mục [`environment/logs/`](logs/) gồm `01-nvidia-smi.log`, `02-import-test.log`, `03-unittest.log`, `04-docker-image-inspect.json`, `05-docker-info.log`, `06-nvidia-ctk.log`; kết quả smoke: xem `02-import-test.log` và `03-unittest.log` (chạy ngày 21/11/2026, chưa chạy dữ liệu thật) |

## Trước khi chạy experiment thật

TV1 bàn giao sequence/split/schema/mapping/catalog và manifest, TV2 kiểm tra tiếp nhận; TV2 cung cấp command/config và partition train/eval cho từng run; TV3 chuẩn bị collector và environment snapshot. Chỉ chạy E1–E4 khi các đầu vào này có thật và được bàn giao. E5 tổng hợp log E2, không tạo lần chạy model riêng. Ghi kết quả bàn giao tại [handoff](../docs/handoff.md); TV3 không đổi protocol, model hoặc metric.