# Big Data Recommender — Session-Based Next-Item Recommendation

Repo khung chính thức cho đồ án Big Data in Cloud Computing của nhóm.

## Phạm vi đã chốt

- Dataset: eCommerce Behavior Data from Multi-Category Store, input baseline `2019-Oct.csv`.
- Bài toán: session-based next-item recommendation theo `user_session`.
- Mô hình: Popularity, GRU và XLNet.
- Đánh giá: cùng split, ground truth, candidate catalog và `K = 20`; báo `Recall@20` và `NDCG@20`.
- Thực nghiệm: E1 model comparison, E2 dataset-size benchmark, E3 resource benchmark, E4 CSV/Parquet comparison, E5 scalability analysis.
- Môi trường dự kiến: public-cloud GPU VM, Ubuntu, Docker, NVIDIA Merlin/Transformers4Rec.

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md) trước khi sửa code hoặc chốt thiết kế.
2. Đọc các tài liệu trong [`docs/context/`](docs/context/) để hiểu phạm vi, yêu cầu môn và quy tắc bàn giao.
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
  context/            Tài liệu bối cảnh và quyết định đã chốt
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

## Trạng thái ban đầu

Repo này là skeleton sạch; chưa tuyên bố pipeline, model, GPU environment hay AWS artifact đã chạy thành công. Mọi kết quả thực nghiệm phải được ghi bằng `run_id`, commit, seed, cấu hình, phần cứng, phiên bản thư viện và đường dẫn output.
