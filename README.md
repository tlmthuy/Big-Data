# Big Data Recommender — Session-Based Next-Item Recommendation

Repo khung chính thức cho đồ án Big Data in Cloud Computing của nhóm.

## Phạm vi đã chốt

- Dataset: eCommerce Behavior Data from Multi-Category Store, input baseline `2019-Oct.csv`.
- Bài toán: session-based next-item recommendation theo `user_session`.
- Mô hình: Popularity, GRU và XLNet.
- Đánh giá: cùng split, ground truth, candidate catalog và `K = 20`; báo `Recall@20` và `NDCG@20`.
- Thực nghiệm: E1 model comparison, E2 dataset-size benchmark, E3 resource benchmark, E4 CSV/Parquet comparison, E5 scalability analysis.
- Môi trường dự kiến: public-cloud GPU VM, Ubuntu, Docker, NVIDIA Merlin/Transformers4Rec.

Preprocessing đã chốt theo tutorial NVIDIA ngày 19/11/2026: source sort không thêm khóa phụ CSV, giữ 20 item cuối, session qua ngày giữ nguyên rồi tính day_index theo nguồn, fit workflow trên tuần trước split, first-seen trên tháng trước lọc tuần. Catalog chung lấy từ vocabulary tuần của từng subset; Popularity và trọng số model chỉ học train. Chi tiết và code cell: [preprocessing_review.md](docs/preprocessing_review.md).

Toàn bộ mã nguồn NVIDIA được giữ nguyên trên nhánh `reference/nvidia-transformers4rec` tại commit nguồn đã pin. Khi dựng code đồ án, đọc nguồn bằng `git show` hoặc worktree riêng theo [hướng dẫn tra cứu NVIDIA](docs/references.md#đọc-nguồn-khi-đang-làm-code-đồ-án).

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md) trước khi sửa code hoặc chốt thiết kế.
2. Đọc [phân công thực thi](docs/team_tasks.md) và [yêu cầu môn học](docs/course_requirements.txt).
3. TV3 đọc [`environment/README.md`](environment/README.md) và [manifest bàn giao TV2](configs/tv2_handoff.json): có lệnh toy; GPU runtime và experiment configs còn chờ xác minh/bàn giao.
4. Kiểm tra manifest và schema trong [`data/manifests/`](data/manifests/) trước khi chạy pipeline.
5. Ghi mọi lần chạy vào [`metrics/`](metrics/) và cập nhật [`docs/handoff.md`](docs/handoff.md).

## Cây repo

```text
app/                  Demo UI và inference adapter
benchmark/            Collector runtime, memory, throughput
configs/              Config model, subset, resource, experiment
data/                 Manifest/schema; raw và Parquet không commit
docs/                 Protocol, experiment matrix, handoff, references
  modeling/           Bài toán, so sánh model và protocol
  vendor/             Snapshot NVIDIA rút gọn có license và manifest
  archive/            Tài liệu lịch sử đã đóng gói
environment/          Dockerfile, environment.yml, hướng dẫn cài đặt
evaluation/           Recall@20, NDCG@20 và lệnh đánh giá
metrics/              Metrics nhỏ, run registry, metadata
models/               Popularity, GRU, XLNet
pipeline/             Sampling, preprocessing, split, mapping
reports/              Figures và tables cho báo cáo
scripts/              Run scripts và tiện ích
```

## Quy tắc dữ liệu và Git

Không commit raw CSV, Parquet lớn, checkpoint, GPU log, secret hoặc credentials. Chỉ commit manifest, schema, command, metrics nhỏ và đường dẫn artifact. Mỗi task hoàn thành phải có code/config/docs, lệnh kiểm tra, output hoặc log, commit hash và handoff.

## Tài liệu đang dùng

| Cần tìm | File |
|---|---|
| Phạm vi, lịch, quy tắc chung | [AGENTS.md](AGENTS.md) |
| Nhiệm vụ và cách thực hiện của 4 thành viên | [team_tasks.md](docs/team_tasks.md) |
| Input, target và Top-20 | [next_item_problem.md](docs/modeling/next_item_problem.md) |
| Popularity, GRU và XLNet | [model_comparison.md](docs/modeling/model_comparison.md) |
| Luật đánh giá | [model_protocol.md](docs/modeling/model_protocol.md) |
| Chạy toy test, Recall/NDCG và baseline Popularity TV2 | [tv2_runbook.md](docs/modeling/tv2_runbook.md) |
| Script GRU/XLNet, config E1–E4 và công cụ E5 | [neural_runbook.md](docs/modeling/neural_runbook.md), [experiments.json](configs/experiments.json) |
| TV3 nhận script, kiểm tra môi trường và trạng thái sẵn chạy | [environment/README.md](environment/README.md), [tv2_handoff.json](configs/tv2_handoff.json) |
| E1–E5 | [experiment_matrix.md](docs/experiment_matrix.md) |
| Nguồn, license và hướng dẫn đối chiếu NVIDIA | [references.md](docs/references.md) |
| Raw subset theo session | [raw_subsets.md](docs/raw_subsets.md) |
| Chọn session bằng stable hash | [session_sampling.md](docs/session_sampling.md) |
| Thống kê raw trước sampling | [raw_audit.md](docs/raw_audit.md) |
| Mô tả 9 cột dữ liệu | [data_dictionary.md](docs/data_dictionary.md) |
| Năm quyết định preprocessing đã chốt và đối chiếu notebook 01–02 | [preprocessing_review.md](docs/preprocessing_review.md) |
| Bàn giao | [handoff.md](docs/handoff.md) |

Tám bản bối cảnh/đề xuất cũ được giữ nguyên trong [context-history.zip](docs/archive/context-history.zip), chỉ mở khi cần tra lịch sử. Phạm vi và lịch hiện hành lấy từ AGENTS.md.

## Trạng thái hiện tại — 19/11/2026

Đã tích hợp năm task TV2: protocol split/lịch test cuối, catalog/K=20, Recall@20, NDCG@20 và Popularity. Review code và 13 toy test đạt; file bàn giao từng task tại [TV2 runbook](docs/modeling/tv2_runbook.md). Kiểm tra tiếp nhận dữ liệu thật từ TV1 là task riêng ngày 21/11 trước E1.

Đã tích hợp ba task TV1 vào `main`: audit raw, chọn session bằng stable hash và xuất raw subset tuần đầu ở mức 10/25/50/100%. Code đã qua review và kiểm tra dữ liệu nhỏ; các counts và manifest của lần chạy TV1 được lưu trong Git. Hai lỗi đơn vị RSS trên Ubuntu và ghi đè bảng counts đã được sửa tại `f7fce3e`.

Raw CSV và danh sách session lớn vẫn ở máy TV1. Phương án bàn giao hiện tại là người nhận tái tạo từ raw cùng SHA-256 theo [hướng dẫn](docs/raw_subsets.md#người-nhận-tái-tạo-và-xác-nhận), đối chiếu rồi ghi xác nhận vào [handoff](docs/handoff.md). Ba task chưa được đánh dấu Done chính thức vì còn chờ kiểm tra độc lập trên dữ liệu thật.

Chưa có xác nhận chạy preprocessing NVIDIA, sequence/split, GPU model hoặc E1–E5. Mọi kết quả thực nghiệm phải được ghi bằng `run_id`, commit, seed, cấu hình, phần cứng, phiên bản thư viện và đường dẫn output.

Bốn task TV2 tiếp theo đã có code/config trên nhánh TV2: GRU/XLNet, matrix 11 run, collector E1–E4 và E5 tổng hợp log. Xem [runbook](docs/modeling/neural_runbook.md); model NVIDIA chưa chạy đầy đủ vì local thiếu Merlin/Transformers4Rec; có RTX 3050 4GB nhưng chưa có runtime GPU tương thích. E2 cần telemetry, E4 full cần command preprocessing chung từ TV1. Chưa có kết quả experiment thật.
