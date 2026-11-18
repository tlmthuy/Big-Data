# Phạm vi cuối cùng đã chốt

## Dataset

- Dataset: eCommerce Behavior Data from Multi-Category Store.
- Link: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store
- Input dùng cho đồ án: `2019-Oct.csv`.
- Cửa sổ baseline: 7 ngày đầu, từ `2019-10-01 00:00:00` đến hết `2019-10-07 23:59:59` UTC. Cửa sổ cuối cùng sẽ được chốt sau daily audit về event distribution, quy mô, chất lượng và khả năng chạy.

## Sampling

- Bỏ dòng `user_session` null trước sampling.
- Đơn vị sampling là `user_session`, không lấy ngẫu nhiên từng dòng.
- Chọn session bằng stable hash ở các mức 10%, 25%, 50%, 100%.
- Giữ toàn bộ event thuộc session đã chọn.
- Giữ `view`, `cart`, `purchase`.
- Chỉ dùng session có ít nhất 2 interaction cho sequence model.
- Giới hạn sequence length là 20.
- Split theo ngày của event đầu tiên trong session: ngày 1–5 train, ngày 6 validation, ngày 7 test.
- Không chọn cửa sổ chỉ để làm tỷ lệ `view` thấp hơn. Nếu đổi cửa sổ, cập nhật manifest, split và quyết định phạm vi trước khi chạy model chính thức.

## Repo và notebook nguồn

- Repo: https://github.com/NVIDIA-Merlin/Transformers4Rec
- Preliminary preprocessing: https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/01-preprocess.html
- ETL with NVTabular: https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/02-ETL-with-NVTabular.html
- Session-based recommendation: https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html

## Môi trường

- Public Cloud GPU VM.
- Ubuntu.
- Docker.
- NVIDIA Merlin runtime, cuDF, NVTabular, PyTorch và Transformers4Rec.
- Demo UI chưa chốt công cụ.

## Model và evaluation

- Popularity, GRU và XLNet.
- `K = 20`.
- Recall@20 và NDCG@20.
- Cùng split, candidate catalog, ground truth và evaluation protocol cho cả ba model.

## Năm experiment

1. E1: Popularity vs GRU vs XLNet.
2. E2: 10%, 25%, 50%, 100% dữ liệu, đo thời gian và memory.
3. E3: thay đổi một resource variable, chẳng hạn batch size.
4. E4: CSV vs Parquet trên cùng nội dung dữ liệu.
5. E5: phân tích scalability từ các run E2, gồm runtime trên một triệu event và bottleneck.
