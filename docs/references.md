# References

- Kaggle dataset: https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store
- REES46 datasets: https://rees46.com/en/datasets
- Transformers4Rec: https://github.com/NVIDIA-Merlin/Transformers4Rec
- Tutorial index: https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/index.html

Pin commit and license in this file when external code is adopted.

## NVIDIA tutorial và mã nguồn liên quan

- Notebook 03: https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html
- Masking: https://github.com/NVIDIA-Merlin/Transformers4Rec/blob/main/transformers4rec/torch/masking.py
- Prediction head: https://github.com/NVIDIA-Merlin/Transformers4Rec/blob/main/transformers4rec/torch/model/prediction_task.py
- Tutorial công bố license Apache-2.0; khi nhập nguồn phải giữ LICENSE/NOTICE thực tế của commit tải về.
- Snapshot: `docs/vendor/nvidia-transformers4rec/`; commit `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`. SHA-256 mỗi file trong manifest.json; đã giữ LICENSE Apache-2.0 gốc. Tải ngày 19/11/2026.

## Dựng pipeline theo nguồn NVIDIA

Branch dành cho việc nhập nguồn và hướng dẫn: `reference/nvidia-transformers4rec`.
Repo nguồn: https://github.com/NVIDIA-Merlin/Transformers4Rec

### Trạng thái

Đã nhập nguồn tại commit `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, giữ license Apache-2.0 và kiểm tra checksum trong manifest. Snapshot được tải ngày 19/11/2026. Chưa chạy GPU runtime hoặc huấn luyện model. Trạng thái commit/push xem docs/handoff.md và Git.

### Lấy phần nguồn liên quan

Từ thư mục gốc repo, khi cần lấy snapshot trên một checkout chưa có nguồn:

```powershell
python scripts/fetch_nvidia_reference.py
```

Script sparse-clone vào thư mục tạm, giữ nguyên notebook 01–03 cùng mã thư viện liên quan trong `docs/vendor/nvidia-transformers4rec/upstream/`, giữ LICENSE/NOTICE nếu có, và tạo `manifest.json` chứa commit nguồn cùng SHA-256 mỗi file. Thư mục này là bản tham khảo, không dùng thay package đã cài trong runtime. Mỗi lần tải dùng commit/ref được chỉ định; mặc định lấy main và ghi lại commit thật. Có thể tái lập bằng:

```powershell
python scripts/fetch_nvidia_reference.py --ref <commit-trong-manifest>
```

### Đối chiếu theo việc cần làm

| Việc | Đường dẫn trong upstream |
|---|---|
| Đọc CSV, timestamp, lọc thời gian, event lặp | examples/tutorial/01-preprocess.ipynb |
| Groupby session, sequence, schema và Parquet | examples/tutorial/02-ETL-with-NVTabular.ipynb |
| Dựng GRU/XLNet, dataloader, trainer | examples/tutorial/03-Session-based-recsys.ipynb |
| Nhãn cuối chuỗi và causal/MLM | transformers4rec/torch/masking.py |
| Prediction head, điểm số và Top-K | transformers4rec/torch/model/prediction_task.py |
| Recall và NDCG | transformers4rec/torch/ranking_metric.py |
| Cách tutorial tạo split | transformers4rec/utils/data_utils.py |

Đường dẫn phải được kiểm tra với manifest sau khi tải; nếu upstream đổi cấu trúc, dừng và cập nhật script thay vì đoán API.

### Hướng dẫn cho agent khi triển khai

1. Đọc AGENTS.md và docs/modeling/model_protocol.md; kiểm tra manifest nguồn đã tồn tại. Nếu chưa có, báo trạng thái thiếu và hoàn thành nhập nguồn trước khi khẳng định code bám theo snapshot.
2. Đọc notebook và mã thư viện liên quan trong snapshot; ghi commit, đường dẫn, class/hàm được tận dụng.
3. Dựng code của nhóm ở pipeline/, models/, evaluation/ và configs/. Giữ bản upstream nguyên trạng để đối chiếu.
4. Áp dụng năm quyết định đã chốt trong docs/preprocessing_review.md: source sort không thêm khóa phụ CSV, giữ 20 item cuối, gom session trước day_index theo công thức nguồn, fit workflow/mapping trên tuần của từng subset trước split, first-seen trên tháng trước lọc tuần. Chia khoảng 80/10/10 trong từng partition, daily fine-tuning train partition t/validation partition t+1. Nhóm bổ sung stable-hash session sampling và K=20; catalog chung là product ID thực trong vocabulary tuần, không lọc train-only. Popularity là baseline nhóm triển khai riêng, chỉ đếm train; không khẳng định notebook 03 đã cung cấp model này.
5. Theo NVIDIA: cho phép seen items, đánh giá item cuối; GRU causal và XLNet MLM. Kiểm tra API masking ở package version thực tế, tránh tách target hai lần. Pin snapshot tham khảo không đồng nghĩa runtime đã tương thích.
6. Giữ thông tin bản quyền/license của code tái sử dụng. Ghi phần sửa đổi và nguồn trong code nhóm, references và handoff. Số liệu notebook chỉ là ví dụ nguồn.
7. Kiểm tra bằng toy session và smoke run trước benchmark; lưu command, output/log thật, cấu hình và phiên bản. Báo rõ phần chưa chạy.

### Prompt có thể dùng ở lần làm tiếp

> Đọc AGENTS.md, docs/modeling/model_protocol.md và docs/references.md. Đối chiếu manifest cùng notebook/mã nguồn trong docs/vendor/nvidia-transformers4rec/upstream/ trước khi dựng pipeline và GRU/XLNet. Theo cách NVIDIA xử lý masking, seen item và ground truth đã chốt; áp dụng sampling của nhóm và năm quyết định preprocessing đã chốt theo tutorial trong docs/preprocessing_review.md, catalog product ID thực từ vocabulary tuần của subset. Ghi rõ preprocessing fit trước split, trọng số model chỉ học từ train. Ghi commit nguồn, phần tái sử dụng, license và các thay đổi. Kiểm tra toy session trước smoke run, không báo kết quả khi chưa có output thật.
