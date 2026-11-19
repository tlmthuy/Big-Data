# Context và instruction chính thức của đồ án

## 1\. Một câu mô tả đồ án

Nhóm dùng lịch sử sản phẩm trong từng phiên mua sắm để dự đoán sản phẩm tiếp theo, so sánh Popularity, GRU và XLNet, rồi đo độ chính xác, thời gian, bộ nhớ và khả năng xử lý khi dữ liệu hoặc tài nguyên thay đổi.

File này là context chung cho cả nhóm. Các thành viên đọc file này trước khi sửa code, tạo experiment hoặc ghi kết quả vào báo cáo.

## 2\. Phạm vi đã chốt

- Bài toán: session-based next-item recommendation.  
- Input: chuỗi sản phẩm trong một `user_session`.  
- Output: top-20 sản phẩm có khả năng xuất hiện tiếp theo.  
- Model: Popularity, GRU và XLNet.  
- Evaluation cutoff: `K = 20`.  
- Metric chính: `Recall@20` và `NDCG@20`.  
- Demo: chọn một session, hiển thị lịch sử, top-20 gợi ý và sản phẩm tiếp theo thật.  
- Demo tool chưa chốt. Chọn công cụ đơn giản nhất sau khi inference chạy ổn.  
- Feature ablation không nằm trong phạm vi bắt buộc.  
- Không thêm model hoặc dịch vụ cloud mới nếu chưa ghi quyết định thay đổi phạm vi.

## 3\. Dataset và sampling

Dataset dùng trong đồ án là [eCommerce Behavior Data from Multi-Category Store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store).

### Phạm vi dữ liệu

- File input: `2019-Oct.csv`.  
- Thời gian: 7 ngày đầu tháng 10/2019, từ `2019-10-01 00:00:00` đến hết `2019-10-07 23:59:59` UTC.  
- Cột chính: `event_time`, `event_type`, `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`.  
- Event giữ lại: `view`, `cart`, `purchase`.

### Quy tắc sampling

1. Đọc raw CSV và kiểm tra schema.  
2. Bỏ dòng có `user_session` null.  
3. Giới hạn dữ liệu vào 7 ngày đã chốt.  
4. Tính stable hash trên `user_session`.  
5. Tạo bốn subset ở mức 10%, 25%, 50%, 100%.  
6. Khi một session được chọn, giữ toàn bộ event của session đó.  
7. Không lấy ngẫu nhiên từng dòng.  
8. Giữ các session có ít nhất 2 interaction cho sequence model.  
9. Giới hạn độ dài sequence tối đa là 20 item.  
10. Lưu rule hash, seed nếu có, manifest và counts của từng subset.

Mỗi subset phải báo cáo số event, session, user, item, category, brand, phân bố event type và phân bố độ dài session. Tỷ lệ session không được gọi là tỷ lệ event nếu chưa đo số event thực tế.

### Chia dữ liệu

Quyết định cập nhật ngày 19/11/2026: theo notebook 02 NVIDIA, gom session trước rồi tính `day_index = (event_time_dt-first - col.min()).dt.days + 1`; timestamp ở UTC. Trong mỗi partition `day_index`, chia ngẫu nhiên khoảng 80% session train, 10% validation, 10% test bằng hàm nguồn; GPU seed `1`, sort theo `user_session` trước khi sinh số ngẫu nhiên. Lưu seed, membership, phiên bản runtime và counts thực tế. `day_index` là chỉ số theo công thức nguồn, không mặc định là ngày lịch bắt đầu lúc 00:00 UTC.

Daily fine-tuning: tiếp tục cập nhật cùng model trên train partition t, đánh giá validation partition t+1 theo notebook 03. Test không dùng chọn cấu hình hoặc cập nhật trọng số model; preprocessing được fit trước split như bên dưới. Lịch test cuối cùng cần TV2 xác nhận trước benchmark.

Năm điểm preprocessing đã chốt theo snapshot NVIDIA `f0ca2b5343dd1e40b5d2422b942f014b224f5c20` ngày 19/11/2026; quyết định này thay thế các đề xuất train-only và khóa phụ CSV trước đó:

1. Sort theo `user_session`, `event_time_ts`; không thêm khóa phụ theo dòng CSV và không cam kết giữ thứ tự CSV. Cập nhật 20/11/2026: bước làm sạch event tháng dùng hành vi timestamp trùng của DuckDB theo quyết định công cụ bên dưới; bước Groupby/gom sequence vẫn theo runtime nguồn đã chốt.
2. Giữ 20 item cuối bằng `ListSlice(-20, pad=True)`; lọc session có ít nhất 2 interaction sau loại lặp.
3. Giữ session nguyên khối trong cửa sổ tuần, gom theo session trước khi gán `day_index`; không kiểm tra/loại theo event cuối vượt cutoff train. Event ngoài cửa sổ tuần vẫn bị lọc trước khi gom sequence.
4. Fit toàn bộ workflow notebook 02, gồm mapping và thống kê feature, trên dữ liệu tuần của từng subset trước split; cố định mapping/schema qua các partition của subset đó. Theo mô tả nguồn: padding `0`, null `1`, OOV `2`, mã đã biết từ `3`; kiểm tra lại giá trị với runtime đã pin. Candidate catalog dùng các product ID thực có trong vocabulary đã fit của subset, không giới hạn item xuất hiện trong train; ba model dùng chung catalog, loại token kỹ thuật khi xuất Top-20. Popularity vẫn chỉ đếm tương tác train đã dùng để cập nhật model.
5. Tính first-seen theo product trên dữ liệu tháng sau xử lý sơ bộ/loại lặp như notebook 01, trước lọc tuần và trước split; notebook 02 tạo recency, log và chuẩn hóa như nguồn. First-seen tháng có thể dùng chung cho bốn subset; ghi chi phí tạo artifact chung riêng với chi phí từng subset. Baseline model vẫn chỉ dùng product ID; tạo feature không tự mở rộng input model.

Chi tiết code cell, nguồn và phần nhóm điều chỉnh cho sampling/E1–E5: `docs/preprocessing_review.md`. Đây là đánh giá offline có preprocessing fit trước split, không mô tả toàn bộ pipeline là train-only. Số thứ tự dòng CSV có thể lưu để truy vết nhưng không dùng làm khóa phụ sort theo quyết định mới.

## 4\. Repo và tài liệu nguồn được phép tận dụng

Repo nguồn là [NVIDIA Merlin Transformers4Rec](https://github.com/NVIDIA-Merlin/Transformers4Rec).

- [Notebook 01 — Preliminary preprocessing](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/01-preprocess.html): đọc raw data, timestamp, session ID, xử lý event lặp và tạo Parquet sơ bộ.  
- [Notebook 02 — ETL with NVTabular](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/02-ETL-with-NVTabular.html): categorical features, time/price features, Groupby theo session, sequence và Parquet.  
- [Notebook 03 — Session-based recommendation](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html): GRU, XLNet, next-item prediction và Recall/NDCG.

Nhóm được chỉnh đường dẫn, sampling, split, config, output và cách tích hợp. Mọi code được tái sử dụng phải ghi nguồn và license. Kết quả tutorial không được đưa vào báo cáo như kết quả của nhóm.

## 5\. Môi trường chạy

Khi dựng hoặc sửa preprocessing, GRU, XLNet hay evaluation, đọc `docs/references.md` và đối chiếu notebook, mã thư viện, test liên quan trong toàn bộ repo NVIDIA trên nhánh `reference/nvidia-transformers4rec` tại commit nguồn đã pin. Dùng `git show` hoặc worktree reference theo hướng dẫn trong tài liệu; code đồ án viết trên nhánh phụ trách ở `pipeline/`, `models/`, `evaluation/`, `configs/`. Ghi commit nguồn, đường dẫn, license và thay đổi so với NVIDIA trong phần bàn giao. Các quy định dataset, sampling, split và catalog của đồ án trong file này có ưu tiên cao hơn tutorial.

Môi trường chính đã chốt:

```
Public Cloud GPU VM
→ Ubuntu
→ Docker
→ NVIDIA Merlin runtime
→ cuDF / NVTabular
→ PyTorch / Transformers4Rec
```

Quyết định công cụ cập nhật 20/11/2026: dùng DuckDB CPU cho ba bước đã triển khai của TV1: chuyển timestamp UTC, bỏ session null/loại sản phẩm lặp liên tiếp và tạo first-seen toàn tháng. Đây là bản triển khai điều chỉnh từ notebook 01; thứ tự timestamp trùng ở bước cleanup theo DuckDB, không cam kết tương đương cuDF. Chi tiết chênh lệch và giới hạn tại `docs/timestamp_session_cleanup.md`. Không yêu cầu chạy lại ba bước này bằng cuDF để chấp nhận bản DuckDB. Các bước ETL tiếp theo phải tuân thủ mapping/schema/split đã chốt và được kiểm tra tương thích riêng. Train/inference GRU, XLNet vẫn dùng PyTorch/Transformers4Rec trong môi trường NVIDIA trên GPU.

TV3 chạy script thực nghiệm theo config TV2; khi đo preprocessing, ghi đúng engine, máy chạy và phạm vi đo của từng bước. Log local TV1 là bằng chứng xử lý dữ liệu, không tự trở thành số benchmark E2/E4/E5. TV3 phải ghi lại GPU, CPU, RAM, driver, CUDA, Docker image, Python và package versions trong `environment/README.md`.

Raw CSV, Parquet lớn, checkpoint và GPU cache không commit trực tiếp vào Git. Git chỉ lưu code, config, schema, manifest, mapping nhỏ, metrics, logs cần thiết và đường dẫn artifact.

## 6\. Quy trình xử lý dữ liệu

```
2019-Oct.csv
→ kiểm tra schema và missing value
→ bỏ session null
→ tạo timestamp số và mã hóa session, giữ liên kết với session ID gốc để sampling
→ trên dữ liệu tháng: sort, loại lặp liên tiếp và tạo bảng first-seen theo notebook 01
→ giới hạn 7 ngày đầu tháng 10
→ chọn session bằng stable hash
→ giữ toàn bộ event của session
→ ghép first-seen tháng, fit workflow/mapping/feature của từng subset trước split
→ sort lại theo timestamp khi gom session thành sequence
→ bỏ session dưới 2 interaction
→ giới hạn sequence length 20
→ tạo day_index theo công thức NVIDIA và chia train/validation/test trong mỗi partition
→ lưu Parquet, schema, mapping và manifest
```

## 7\. Model và evaluation

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
- Candidate catalog gồm product ID thực trong vocabulary tuần của subset đã fit trước split; dùng chung cho ba model, loại token kỹ thuật khỏi Top-20.
- Seen-item rule.  
- `K = 20`.  
- Cách tổng hợp metric.

`Recall@20` kiểm tra sản phẩm thật có nằm trong 20 gợi ý hay không. `NDCG@20` xem sản phẩm thật đứng ở vị trí nào trong danh sách.

Mỗi run phải lưu model name, subset, config, split, candidate catalog, `run_id`, prediction output, metrics và output path.

## 8\. Năm experiment bắt buộc

### E1 — So sánh ba model

Chạy Popularity, GRU và XLNet trên cùng một subset, cùng split, cùng candidate catalog và cùng `K = 20`.

Kết quả cần có Recall@20, NDCG@20, training time, inference time và memory nếu đo được.

### E2 — Dữ liệu tăng thì chương trình thay đổi thế nào

Chạy cùng pipeline trên subset 10%, 25%, 50%, 100%.

Ghi số event/session/user/item, thời gian đọc, thời gian preprocessing, thời gian train và memory.

### E3 — Tài nguyên máy ảnh hưởng thế nào

Giữ model, dữ liệu, split, epoch và sequence length cố định. Chỉ thay một biến, chẳng hạn batch size hoặc giới hạn CPU/RAM.

Ghi runtime, throughput, memory và chi phí nếu có.

### E4 — CSV và Parquet khác nhau thế nào

Dùng cùng nội dung dữ liệu ở hai định dạng. Đo dung lượng file, thời gian đọc, thời gian preprocessing và memory.

### E5 — Scalability khi dữ liệu tăng

Dùng các run E2 để tính runtime trên một triệu event, vẽ đường tăng trưởng và chỉ ra bước chậm nhất. E5 không cần tạo model hoặc API benchmark mới.

## 9\. Phân công và cách bàn giao

### TV1 — Dữ liệu

TV1 phụ trách raw audit, sampling, preprocessing, Parquet, split, mapping và manifest.

Bàn giao cho TV2/TV3 gồm data path, schema, mapping, split definition, manifest và counts.

### TV2 — Model, experiment và evaluation

TV2 phụ trách Popularity, GRU, XLNet, ground truth, candidate catalog, metric, experiment matrix, script E1–E5, phân tích và kết luận.

TV2 là người quyết định protocol. TV3 chạy script theo config của TV2.

### TV3 — Môi trường và vận hành run

TV3 phụ trách VM, Docker, runtime, benchmark collector, chạy script, thu runtime/memory/storage/throughput và bàn giao raw logs.

TV3 không tự đổi model, split, metric hoặc experiment protocol.

### TV4 — Demo & hỗ trợ report

TV4 phụ trách demo, README demo, prediction contract với TV2, script/template và figures chính thức, caption kỹ thuật, demo fallback và Q&A kỹ thuật. TV4 chuẩn hóa references, dataset/repo/license, AI-use statement và thiết kế hình minh họa cho slides.

### TV5 — Report & Results

TV5 phụ trách report/slide outline, cấu trúc metric và bảng E1–E5, table captions, truy vết nguồn log, đối chiếu logs với TV2, kiểm tra metrics package, viết results/limitations/reproducibility, hoàn thiện report tiếng Anh và nội dung slides, thuyết trình kết quả và Q&A học thuật.

TV2 bàn giao metrics package chính thức cho cả TV4 và TV5. TV4 tạo figures; TV5 tạo bảng và nội dung report/slides từ cùng package đã TV2 xác nhận. Cả hai không tự thay số liệu hoặc cách tính; số liệu bổ sung phải được TV2 xác nhận. TV4 bàn giao figures/caption/references/license/AI statement cho TV5 tích hợp. Lịch chi tiết theo ảnh phân công cập nhật ngày 20/11/2026: `docs/team_tasks.md`.

## 10\. Cấu trúc repo

```
big-data-recsys/
├── app/
├── benchmark/
├── configs/
├── data/manifests/
├── docs/
├── environment/
├── evaluation/
├── metrics/
├── models/
├── pipeline/
├── reports/figures/
├── reports/tables/
├── reports/slides/
├── scripts/runs/
├── .gitignore
├── README.md
└── requirements.txt
```

## 11\. Quy tắc Git

Branch:

```
main
├── feature/tv1-data
├── feature/tv2-model-evaluation
├── feature/tv3-environment-benchmark
├── feature/tv4-demo-documentation
└── feature/tv5-report-results
```

Một task chỉ được đánh dấu Done khi:

1. Code/config/docs/manifest/log đã tạo.  
2. Có command chạy hoặc cách kiểm tra.  
3. Có output thật hoặc log lỗi.  
4. Đã commit và push lên branch phụ trách.  
5. Commit hash được ghi trong `docs/handoff.md` hoặc experiment registry.  
6. Người nhận đã kiểm tra output.

Artifact lớn dùng manifest và output path. Không commit raw CSV, Parquet lớn, checkpoint lớn, `.env`, credentials hoặc Docker cache.

## 12\. Lịch deadline cuối cùng

- 19/11: đọc dữ liệu/repo, dựng environment, chốt protocol.  
- 20/11: audit, sampling, metric toy test, smoke test.  
- 21/11: preprocessing, split, script model, dataloader.  
- 22/11: chạy E1.  
- 23/11: chạy E2.  
- 24/11: chạy E3 và tính E5 từ E2.  
- 25/11: chạy E4, rerun lỗi, bàn giao logs.  
- 26/11: TV2 phân tích E1–E5; TV5 đối chiếu logs với TV2, TV4 hỗ trợ kiểm tra run_id và đầu vào figures.
- 27/11: TV2 giao metrics chính thức cho TV4/TV5; TV4 tích hợp inference/UI và kiểm thử demo, TV5 kiểm tra E1–E5.
- 28/11: TV4 tạo figures chính thức, chuẩn hóa references/license/AI statement, chuẩn bị và tập demo/fallback; TV5 viết results/limitations/reproducibility, hoàn thiện report tiếng Anh và nội dung slides, tập thuyết trình kết quả/Q&A; cả nhóm rehearsal và cleanup.

## 13\. Sản phẩm cuối

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
