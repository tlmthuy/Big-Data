# Cấu trúc repo và quy tắc bàn giao

## Cấu trúc thư mục

```text
big-data-recsys/
├── app/                    # Demo UI và inference adapter
├── benchmark/              # Collector đo runtime, memory, throughput
├── configs/                # Config model, subset, resource và experiment
├── data/
│   ├── manifests/          # Manifest, schema, counts, mapping nhỏ
│   └── README.md           # Cách tải raw data và tạo subset
├── docs/
│   ├── model_protocol.md   # Split, ground truth, candidate catalog, K
│   ├── experiment_matrix.md
│   ├── handoff.md
│   ├── references.md
│   └── ai-use-statement.md
├── environment/
│   ├── Dockerfile
│   ├── environment.yml
│   └── README.md
├── evaluation/             # Recall@20, NDCG@20, evaluation commands
├── metrics/                # CSV/JSON metrics và raw run registry
├── models/                 # Popularity, GRU, XLNet code
├── pipeline/               # Sampling, preprocessing, split, mapping
├── reports/
│   ├── figures/
│   └── tables/
├── scripts/
│   ├── runs/               # run_e1.sh, run_e2.sh, ... hoặc PowerShell
│   └── utils/
├── .gitignore
├── README.md
└── requirements.txt
```

Raw CSV, Parquet, checkpoint lớn và GPU logs không đưa trực tiếp vào Git. Repo chỉ giữ manifest, schema, command, metrics nhỏ và đường dẫn artifact.

## Branch và bàn giao

```text
main
├── feature/tv1-data
├── feature/tv2-model-evaluation
├── feature/tv3-environment-benchmark
└── feature/tv4-demo-documentation
```

- Mỗi thành viên làm trên branch của mình.
- Mỗi task Done phải có commit đã push lên branch.
- Handoff phải ghi commit hash, đường dẫn output, command chạy và người nhận.
- Người nhận kiểm tra output rồi mới merge vào `main`.
- Không commit secret, `.env`, credentials, raw dataset, checkpoint lớn hoặc Docker cache.

## Done gate Git dùng cho mọi task

Một task chỉ được đánh dấu Done khi có đủ:

1. File code/config/docs/manifest/log đã tạo.
2. Lệnh chạy hoặc cách kiểm tra đã ghi.
3. Output thật hoặc log lỗi đã lưu.
4. Commit đã push lên branch phụ trách.
5. Commit hash được ghi vào `docs/handoff.md` hoặc experiment registry.
6. Người nhận đã kiểm tra hoặc ghi rõ trạng thái chờ kiểm tra.

Với raw data, Parquet, checkpoint hoặc artifact lớn, Done gate dùng manifest và output path thay cho việc push file lớn vào Git.
