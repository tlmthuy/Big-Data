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

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md) trước khi sửa code hoặc chốt thiết kế.
2. Đọc [phân công thực thi](docs/team_tasks.md) và [yêu cầu môn học](docs/course_requirements.txt).
3. Tạo môi trường theo [`environment/README.md`](environment/README.md).
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
  vendor/             Snapshot NVIDIA có license và manifest
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
| E1–E5 | [experiment_matrix.md](docs/experiment_matrix.md) |
| Nguồn, license và hướng dẫn đối chiếu NVIDIA | [references.md](docs/references.md) |
| Raw subset theo session | [raw_subsets.md](docs/raw_subsets.md) |
| Chọn session bằng stable hash | [session_sampling.md](docs/session_sampling.md) |
| Thống kê raw trước sampling | [raw_audit.md](docs/raw_audit.md) |
| Mô tả 9 cột dữ liệu | [data_dictionary.md](docs/data_dictionary.md) |
| Năm quyết định preprocessing đã chốt và đối chiếu notebook 01–02 | [preprocessing_review.md](docs/preprocessing_review.md) |
| Bàn giao | [handoff.md](docs/handoff.md) |

Tám bản bối cảnh/đề xuất cũ được giữ nguyên trong [context-history.zip](docs/archive/context-history.zip), chỉ mở khi cần tra lịch sử. Phạm vi và lịch hiện hành lấy từ AGENTS.md.

## Trạng thái ban đầu

Repo này là skeleton sạch; chưa tuyên bố pipeline, model, GPU environment hay AWS artifact đã chạy thành công. Mọi kết quả thực nghiệm phải được ghi bằng `run_id`, commit, seed, cấu hình, phần cứng, phiên bản thư viện và đường dẫn output.
