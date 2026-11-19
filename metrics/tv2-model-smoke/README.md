# GRU/XLNet GPU smoke — 20/11/2026

Cả hai CLI train/eval trên GPU thật và đạt kiểm tra checkpoint. Đây là dữ liệu tổng hợp, không phải kết quả E1–E5 hay kiểm chứng dữ liệu TV1.

| Model | Run output | Kiểm tra checkpoint |
| --- | --- | --- |
| GRU | [metrics](gru-attempt2/metrics.json), [predictions](gru-attempt2/predictions.jsonl) | [passed](gru-attempt2/verification.json) |
| XLNet | [metrics](xlnet-attempt2/metrics.json), [predictions](xlnet-attempt2/predictions.jsonl) | [passed](xlnet-attempt2/verification.json) |

Mỗi model train partition 1 một epoch, batch 2, validation partition 2 gồm 3 session. Giữ nguyên causal masking GRU và MLM XLNet. Verifier đọc checkpoint thật, kiểm tra label item cuối, đổi target giữ prefix cho điểm dự đoán không đổi, và thêm session khác vào batch không làm đổi điểm ngoài sai số float (GRU 1,12e-8; XLNet 7,45e-8).

Môi trường WSL Ubuntu 22.04 riêng: RTX 3050 Laptop 4 GiB, driver 610.78, Python 3.10.12, PyTorch 1.13.1/CUDA 11.7, Merlin 23.8 và Transformers4Rec từ source pin `f0ca2b5343dd1e40b5d2422b942f014b224f5c20` (Apache-2.0). Git archive không có version tag nên package báo `0+unknown`; nguồn được xác định bằng commit và archive SHA trong bản ghi cài đặt. Xem [environment](environment.json), [packages](packages.txt), [pip check](pip-check.txt), [requirements](../../environment/smoke-models.requirements.txt).

Dung lượng môi trường sau chạy: **4.040.455.500 byte (~4,04 GB)**, trong ngân sách **7.000.000.000 byte** người dùng dành để dựng môi trường. Không phải yêu cầu chừa trống 7 GB. Còn khoảng 4,56 GB trên ổ C sau khi dừng Ubuntu; số trống có thể thay đổi theo ứng dụng khác. Docker runtime lớn không được tiếp tục build; không xóa volume/database để dựng môi trường này. Runtime này không cài cuDF/NVTabular, không thay bản Docker/cloud chính thức TV3 phải xác minh.

Lệnh từ root repo trong môi trường đã cài dependencies (đổi `gru` thành `xlnet`, dùng output mới khi chạy lại):

```bash
python -m evaluation.run_neural --model gru --data evaluation/tests/fixtures/sessions.jsonl --schema evaluation/tests/fixtures/schema.pbtxt --catalog evaluation/tests/fixtures/catalog.json --train-through 1 --epochs 1 --batch-size 2 --eval-batch-size 2 --device cuda --split validation --subset toy --run-id gru-gpu-smoke --output metrics/local/gru-gpu-smoke
python -m scripts.runs.verify_neural_smoke --model gru --run-path metrics/local/gru-gpu-smoke
```

Checkpoint ở các thư mục run local, bị Git ignore; tái chạy lệnh để tạo lại. Command/exit code thực tế nằm ở `*-attempt2-command.json`. Commit chạy model: `06ba66e899f400720b44cb1b9b2feacac0590795`; code model/runner không sửa trong lần smoke này. Verifier và runtime pins được bổ sung sau commit đó; xem commit chứa tài liệu này.

Attempt 1 của cả hai model dừng khi import `npy-append-array 0.9.19` với NumPy 1.24.4; giữ failure.json. Pin `npy-append-array==0.9.16` sửa lỗi, không sửa thư viện NVIDIA hoặc đổi model. Thiếu TensorFlow/Triton client chỉ phát cảnh báo cho tính năng tùy chọn; CLI và verifier PyTorch vẫn exit 0.
