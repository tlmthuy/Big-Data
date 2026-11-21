# Fit workflow theo từng subset tuần

Input local tại `data/clean/workflow_inputs/`. Các bảng lấy event tuần từ
Parquet tháng đã làm sạch bằng DuckDB, dùng membership seed 42 và cùng
lookup first-seen tháng. Mã session số dùng chung trong tuần, có bảng
`session_mapping.parquet` liên kết với session ID gốc. Chưa chia split.

| Subset | Event | Session | Product |
| --- | ---: | ---: | ---: |
| 10% | 638097 | 187563 | 63398 |
| 25% | 1601084 | 469728 | 87247 |
| 50% | 3197030 | 938071 | 103940 |
| 100% | 6390944 | 1877365 | 118333 |

[Manifest input](../data/manifests/weekly_workflow_inputs.json) ghi checksum.
Nếu cần nguồn theo cuDF, hãy chạy làm sạch và first-seen trên VM, rồi truyền
hai report tương ứng qua `--cleanup` và `--first-seen` khi chuẩn bị input.

```bash
.venv/bin/python pipeline/prepare_workflow_inputs.py --output-dir data/clean/workflow_inputs
```

Trên Ubuntu với Merlin/cuDF/NVTabular đã xác minh, chuyển cả thư mục input
gồm manifest vào workspace. Chạy một tiến trình riêng cho từng subset để
lưu riêng thống kê Categorify, Normalize và JoinGroupby.

```bash
for percent in 10 25 50 100; do
  python pipeline/fit_weekly_workflow.py --inputs data/clean/workflow_inputs \
    --subset "$percent" --output-dir "data/clean/workflows/$percent" || exit 1
done
```

Runner dùng trực tiếp các cell dựng graph của Notebook 02 đã pin và kiểm
SHA-256 trước khi đọc code. Fit trên toàn bộ input tuần của subset rồi lưu
workflow, Parquet/schema, mapping product hai chiều dưới dạng bảng,
vocabulary và catalog JSON theo contract TV2. Các partition dùng cùng
workflow đã fit. Runner kiểm tra padding bằng ListSlice và null/OOV bằng
Categorify đã fit. Manifest chỉ được ghi sau khi các kiểm tra đạt.

## Lần chạy GPU ngày 21/11/2026

VM nhóm chạy Tesla T4, container `big-data-recsys:smoke`, Python 3.10.12,
cuDF 23.04.00, NVTabular 23.08.00. Bốn workflow fit riêng trên toàn bộ
dữ liệu tuần của từng subset trước split. Runtime xác nhận padding 0,
null 1 và OOV 2 cho cả bốn. Input tuần lấy từ Parquet DuckDB local đã ghi
trong manifest và giữ nguyên checksum khi chuyển lên VM.

Trên VM, output nằm tại `~/tv1-weekly-20261121/data/clean/workflows/{10,25,50,100}/`.
Trong mỗi thư mục có workflow, Parquet sequence, schema, mapping, catalog
và manifest. Dùng cùng workflow của subset cho mọi partition sau khi
chia. Kết quả fit được đo riêng với chi phí first-seen tháng.

Đã nạp lại cả bốn workflow, kiểm tra checksum, đối chiếu hai trường
mapping/catalog và đọc toàn bộ sequence để xác nhận ID hợp lệ, padding
phải và độ dài các feature list. Xem [manifest đã xác minh](../data/manifests/weekly_workflows_verified.json).
