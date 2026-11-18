# AGENT.md — Context và instruction chính thức của đồ án

> **Quy tắc đọc:** Đây là context chung chính thức của nhóm. Mọi thành viên/agent phải đọc file này trước khi sửa code, tạo experiment hoặc ghi kết quả vào báo cáo.
>
> **Phạm vi:** Session-based next-item recommendation trên dataset eCommerce Behavior Data from Multi-Category Store.

## 1. Một câu mô tả đồ án

Nhóm dùng lịch sử sản phẩm trong từng phiên mua sắm để dự đoán sản phẩm tiếp theo, so sánh **Popularity, GRU và XLNet**, rồi đo độ chính xác, thời gian, bộ nhớ và khả năng xử lý khi dữ liệu hoặc tài nguyên thay đổi.

## 2. Phạm vi đã chốt

- **Bài toán:** session-based next-item recommendation.
- **Input:** chuỗi sản phẩm trong một `user_session`.
- **Output:** top-20 sản phẩm có khả năng xuất hiện tiếp theo.
- **Model:** Popularity, GRU và XLNet.
- **Evaluation cutoff:** `K = 20`.
- **Metric chính:** `Recall@20` và `NDCG@20`.
- **Demo:** chọn một session, hiển thị lịch sử, top-20 gợi ý và sản phẩm tiếp theo thật.
- Công cụ demo chưa chốt; chọn công cụ đơn giản nhất sau khi inference chạy ổn.
- Feature ablation không nằm trong phạm vi bắt buộc.
- Không thêm model hoặc dịch vụ cloud mới nếu chưa ghi quyết định thay đổi phạm vi.

## 3. Dataset và sampling

### Dataset và phạm vi dữ liệu

- Dataset: **eCommerce Behavior Data from Multi-Category Store**.
- File input: `2019-Oct.csv`.
- Cửa sổ dữ liệu: 7 ngày đầu tháng 10/2019, từ `2019-10-01 00:00:00` đến hết `2019-10-07 23:59:59` UTC.
- Các cột chính: `event_time`, `event_type`, `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`.
- Event giữ lại: `view`, `cart`, `purchase`.

### Quy tắc sampling

1. Đọc raw CSV và kiểm tra schema.
2. Bỏ dòng có `user_session` null.
3. Giới hạn dữ liệu vào 7 ngày đã chốt.
4. Tính stable hash trên `user_session`.
5. Tạo bốn subset ở mức `10%`, `25%`, `50%`, `100%`.
6. Khi một session được chọn, giữ toàn bộ event của session đó.
7. Không lấy ngẫu nhiên từng dòng.
8. Giữ session có ít nhất 2 interaction cho sequence model.
9. Giới hạn độ dài sequence tối đa là 20 item.
10. Lưu hash rule, seed nếu có, manifest và counts của từng subset.

Mỗi subset phải báo cáo số event, session, user, item, category, brand, phân bố event type và phân bố độ dài session. Tỷ lệ session không được gọi là tỷ lệ event nếu chưa đo số event thực tế.

### Chia dữ liệu

Dựa trên ngày của event đầu tiên trong session:

- Ngày 1–5: `train`.
- Ngày 6: `validation`.
- Ngày 7: `test`.

Không dùng event tương lai để tạo input, popularity table, product mapping hoặc feature cho test.

## 4. Repo và tài liệu nguồn được phép tận dụng

Repo nguồn được phép tham khảo là **NVIDIA Merlin Transformers4Rec**:

- Notebook 01 — Preliminary preprocessing: đọc raw data, timestamp, session ID, xử lý event lặp và tạo Parquet sơ bộ.
- Notebook 02 — ETL with NVTabular: categorical features, time/price features, groupby theo session, sequence và Parquet.
- Notebook 03 — Session-based recommendation: GRU, XLNet, next-item prediction và Recall/NDCG.

Nhóm được chỉnh đường dẫn, sampling, split, config, output và cách tích hợp. Mọi code tái sử dụng phải ghi nguồn và license. Kết quả tutorial không được đưa vào báo cáo như kết quả của nhóm.

## 5. Môi trường chạy

Môi trường chính đã chốt:

```text
Public Cloud GPU VM
  → Ubuntu
  → Docker
  → NVIDIA Merlin runtime
  → cuDF / NVTabular
  → PyTorch / Transformers4Rec
```

TV3 phải ghi lại GPU, CPU, RAM, driver, CUDA, Docker image, Python và package versions trong `environment/README.md`.

Raw CSV, Parquet lớn, checkpoint và GPU cache không commit trực tiếp vào Git. Git chỉ lưu code, config, schema, manifest, mapping nhỏ, metrics, logs cần thiết và đường dẫn artifact.

## 6. Quy trình xử lý dữ liệu

```text
2019-Oct.csv
→ kiểm tra schema và missing value
→ bỏ session null
→ giới hạn 7 ngày đầu tháng 10
→ chọn session bằng stable hash
→ giữ toàn bộ event của session
→ sort theo session và event_time
→ xử lý consecutive repeated item
→ tạo timestamp số và feature cần thiết
→ gom thành sequence
→ bỏ session dưới 2 interaction
→ giới hạn sequence length 20
→ chia train/validation/test
→ lưu Parquet, schema, mapping và manifest
```

Mỗi bước phải ghi counts trước/sau, quy tắc áp dụng và output path để có thể tái lập.

## 7. Model và evaluation

### Popularity

Đếm mức độ xuất hiện của sản phẩm trong train data và trả danh sách top-20. Không dùng event validation/test để tạo bảng popularity.

### GRU

Dùng chuỗi product ID trong session để dự đoán next item. Tận dụng phần GRU trong notebook 03 và điều chỉnh input/output path, config, batch size, epoch và seed.

### XLNet

Dùng Transformer block trong notebook 03 cho next-item prediction. Ghi masking, sequence length, batch size và memory requirement. Nếu môi trường không chạy được, giữ log lỗi và ghi limitation.

### Evaluation protocol

Ba model phải dùng cùng:

- Train/validation/test split.
- Ground truth next item.
- Candidate catalog lấy từ train.
- Seen-item rule.
- `K = 20`.
- Cách tổng hợp metric.

`Recall@20` kiểm tra sản phẩm thật có nằm trong 20 gợi ý hay không. `NDCG@20` xem sản phẩm thật đứng ở vị trí nào trong danh sách.

Mỗi run phải lưu model name, subset, config, split, candidate catalog, `run_id`, prediction output, metrics và output path.

## 8. Năm experiment bắt buộc

### E1 — So sánh ba model

Chạy Popularity, GRU và XLNet trên cùng một subset, cùng split, cùng candidate catalog và cùng `K = 20`.

Kết quả cần có: `Recall@20`, `NDCG@20`, training time, inference time và memory nếu đo được.

### E2 — Dữ liệu tăng thì chương trình thay đổi thế nào

Chạy cùng pipeline trên subset `10%`, `25%`, `50%`, `100%`.

Ghi số event/session/user/item, thời gian đọc, thời gian preprocessing, thời gian train và memory.

### E3 — Tài nguyên máy ảnh hưởng thế nào

Giữ model, dữ liệu, split, epoch và sequence length cố định. Chỉ thay một biến, chẳng hạn batch size hoặc giới hạn CPU/RAM.

Ghi runtime, throughput, memory và chi phí nếu có.

### E4 — CSV và Parquet khác nhau thế nào

Dùng cùng nội dung dữ liệu ở hai định dạng. Đo dung lượng file, thời gian đọc, thời gian preprocessing và memory.

### E5 — Scalability khi dữ liệu tăng

Dùng các run E2 để tính runtime trên một triệu event, vẽ đường tăng trưởng và chỉ ra bước chậm nhất. E5 không cần tạo model hoặc API benchmark mới.

## 9. Phân công và cách bàn giao

### TV1 — Dữ liệu

Phụ trách raw audit, sampling, preprocessing, Parquet, split, mapping và manifest.

Bàn giao cho TV2/TV3 gồm data path, schema, mapping, split definition, manifest và counts.

### TV2 — Model, experiment và evaluation

Phụ trách Popularity, GRU, XLNet, ground truth, candidate catalog, metric, experiment matrix, script E1–E5, phân tích và kết luận.

TV2 là người quyết định protocol. TV3 chạy script theo config của TV2.

### TV3 — Môi trường và vận hành run

Phụ trách VM, Docker, runtime, benchmark collector, chạy script, thu runtime/memory/storage/throughput và bàn giao raw logs.

TV3 không tự đổi model, split, metric hoặc experiment protocol.

### TV4 — Demo và tài liệu

Phụ trách demo, README, bảng/hình, report, slide, references, license, AI-use statement và rehearsal.

TV4 dùng metrics đã TV2 xác nhận, không tự thay số liệu hoặc cách tính.

### Hợp đồng bàn giao tối thiểu

Mỗi bàn giao phải có:

- Commit hash.
- `run_id`.
- Command chạy.
- Config và seed.
- Input/output path.
- Schema, counts và metric nếu có.
- Người giao, người nhận và trạng thái kiểm tra.

## 10. Cấu trúc repo

```text
big-data-recsys/
├── app/                  # Demo và inference adapter
├── benchmark/            # Runtime, memory, throughput collector
├── configs/              # Config model, subset, resource, experiment
├── data/
│   └── manifests/        # Schema, counts, sampling rules, mappings nhỏ
├── docs/                 # Protocol, experiment matrix, handoff, references
├── environment/          # Dockerfile, environment.yml, hướng dẫn môi trường
├── evaluation/           # Recall@20, NDCG@20 và lệnh đánh giá
├── metrics/              # Metrics nhỏ và run registry
├── models/               # Popularity, GRU, XLNet
├── pipeline/             # Sampling, preprocessing, split, mapping
├── reports/
│   ├── figures/
│   └── tables/
├── scripts/
│   ├── runs/             # run_e1 đến run_e5
│   └── utils/
├── .gitignore
├── AGENTS.md
├── agent.md
├── README.md
└── requirements.txt
```

Raw CSV, Parquet lớn, checkpoint, GPU cache, secret và credentials không nằm trong Git.

## 11. Quy tắc Git

### Branch model

```text
main
├── feature/tv1-data
├── feature/tv2-model-evaluation
├── feature/tv3-environment-benchmark
└── feature/tv4-demo-documentation
```

### Done gate

Một task chỉ được đánh dấu **Done** khi:

1. Code/config/docs/manifest/log đã tạo.
2. Có command chạy hoặc cách kiểm tra.
3. Có output thật hoặc log lỗi.
4. Đã commit và push lên branch phụ trách.
5. Commit hash được ghi trong `docs/handoff.md` hoặc experiment registry.
6. Người nhận đã kiểm tra output.

Artifact lớn dùng manifest và output path. Không commit raw CSV, Parquet lớn, checkpoint lớn, `.env`, credentials hoặc Docker cache.

## 12. Lịch deadline cuối cùng

| Ngày | Công việc |
|---|---|
| 19/11 | Đọc dữ liệu/repo, dựng environment, chốt protocol |
| 20/11 | Audit, sampling, metric toy test, smoke test |
| 21/11 | Preprocessing, split, script model, dataloader |
| 22/11 | Chạy E1 |
| 23/11 | Chạy E2 |
| 24/11 | Chạy E3 và tính E5 từ E2 |
| 25/11 | Chạy E4, rerun lỗi, bàn giao logs |
| 26/11 | TV2 phân tích E1–E5, TV4 đối chiếu logs |
| 27/11 | Giao metrics chính thức, tích hợp demo |
| 28/11 | Hoàn thiện report/slide, rehearsal và cleanup |

## 13. Sản phẩm cuối

- Code sampling và preprocessing.
- Parquet, schema, mapping và manifest.
- Code Popularity, GRU, XLNet.
- Script evaluation và metrics.
- Raw logs E1–E5.
- Bảng/hình kết quả.
- Demo top-20.
- README chạy lại.
- Report tiếng Anh.
- Slide và script tiếng Anh.
- References, license và AI-use statement.

## Quy tắc cập nhật context

Nếu thay đổi bài toán, dataset window, split, model, metric, experiment, phân công hoặc deadline, phải ghi quyết định thay đổi trước khi sửa code và cập nhật file này cùng `docs/handoff.md`.
