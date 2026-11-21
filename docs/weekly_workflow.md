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

## Bàn giao Parquet sequence

Cùng lần chạy fit, graph Notebook 02 gom event theo `user_session` và
sort theo `event_time_ts` ở cell 37. Cell 42 giữ 20 vị trí cuối đồng bộ
trên các feature list bằng `ListSlice(-20, pad=True)`. Cell 48 chỉ giữ
session có từ 2 interaction. Sequence dài hơn 20 giữ item mới nhất làm
vị trí cuối, tính cả target. Sequence ngắn hơn 20 dùng padding phải.
Đây là sequence trước split.

Parquet nằm trên VM ở `~/tv1-weekly-20261121/data/clean/workflows/<subset>/processed_nvt/part_0.parquet`.
Dùng schema, mapping và catalog trong cùng thư mục subset. Với timestamp
trùng, graph dùng thứ tự nguồn cuDF/NVTabular theo Notebook 02.

Đối chiếu độc lập với input tuần xác nhận membership và số interaction
của toàn bộ session. Các session có timestamp phân biệt khớp chính xác
dãy tối đa 20 product ID cuối theo timestamp. Các session có timestamp
trùng được đếm riêng và không áp đặt thứ tự phụ. SHA-256 từng Parquet,
số session kiểm tra và đường dẫn log VM có trong manifest xác minh.

## Chia train, validation và test theo day_index

Chạy sau khi fit và xuất sequence. Runner đọc `day_index` đã tính tại
cell 44 và gọi hàm GPU trong snapshot NVIDIA đã pin, như cell 63.
Hàm sort theo `user_session` rồi đặt lại CuPy seed 1 trong mỗi partition
để chia khoảng 80/10/10. Session được giữ nguyên theo partition đã gán,
kể cả khi có event qua ngày. Workflow, schema và catalog dùng chung trong
từng subset. Khi fine-tune, dùng train của partition t và validation của
partition t+1. Xem protocol TV2 để chọn bước đánh giá test cuối.

```bash
for percent in 10 25 50 100; do
  python pipeline/split_weekly_sequences.py \
    --workflow "data/clean/workflows/$percent" \
    --output-dir "data/clean/splits-v2/$percent" || exit 1
done
```

Trên VM, chạy trong container Merlin tại workspace `~/tv1-weekly-20261121`.
Mỗi thư mục split theo mức có `<day_index>/{train,valid,test}.parquet`,
`membership.parquet` và manifest. Counts phân biệt product ID duy nhất
và số interaction sau truncation, đều loại padding. Script kiểm tra mọi
session thuộc đúng day_index, xuất hiện đúng một lần và đủ so với input.

Đã chạy trên Tesla T4 cho đủ bốn subset. Mỗi subset có 7 day_index và
21 Parquet split. [Manifest xác minh](../data/manifests/weekly_splits_verified.json)
ghi checksum sequence đầu vào đã bàn giao, checksum từng split, membership,
counts từng partition và đường dẫn log trên VM. TV2 có thể truyền thư mục
`data/clean/splits-v2/<subset>` làm `--sessions` và dùng catalog/schema
của cùng subset trong `data/clean/workflows/<subset>`.
