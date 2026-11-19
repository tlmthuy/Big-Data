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

Branch tham khảo toàn bộ mã nguồn: `reference/nvidia-transformers4rec`. Cây thư mục tại đầu nhánh giữ nguyên repo NVIDIA ở commit nguồn đã pin; lịch sử nhánh trước lần nhập toàn bộ vẫn được giữ. Đây là nhánh đọc nguồn, code đồ án nằm trên `main` và các nhánh thành viên.
Repo nguồn: https://github.com/NVIDIA-Merlin/Transformers4Rec

### Trạng thái

Commit nguồn cố định: `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`. Nhánh reference chứa toàn bộ file được Git quản lý tại commit này, gồm notebook, thư viện, tests, cấu hình và LICENSE. Commit nhập nguồn của nhóm có cùng tree với commit NVIDIA, nhưng có lịch sử nhánh của nhóm; hai commit hash không giống nhau. Đây là bản tham khảo mã nguồn, không thay package trong runtime. Chưa chạy GPU runtime hoặc huấn luyện model. Trạng thái commit/push và kiểm tra tree xem `docs/handoff.md`.

Snapshot rút gọn trong `docs/vendor/nvidia-transformers4rec/` trên `main` vẫn giữ để đối chiếu các đánh giá cũ bằng manifest SHA-256. Nhánh reference là nơi tra cứu đầy đủ, kể cả file ngoài snapshot rút gọn.

### Đọc nguồn khi đang làm code đồ án

Từ checkout đồ án, lấy nhánh rồi đọc trực tiếp mà không chuyển nhánh:

```powershell
git fetch origin reference/nvidia-transformers4rec:refs/remotes/origin/reference/nvidia-transformers4rec
git ls-tree --name-only origin/reference/nvidia-transformers4rec
git show origin/reference/nvidia-transformers4rec:examples/tutorial/02-ETL-with-NVTabular.ipynb
git show origin/reference/nvidia-transformers4rec:transformers4rec/torch/masking.py
```

Khi cần tìm kiếm nhiều file, mở worktree reference riêng. Trong Codex dùng công cụ `create_worktree` với ref `reference/nvidia-transformers4rec` (hoặc remote ref ở checkout mới); ngoài Codex có thể dùng:

```powershell
git worktree add --detach ../nvidia-transformers4rec-reference origin/reference/nvidia-transformers4rec
git -C ../nvidia-transformers4rec-reference rev-parse HEAD
git -C ../nvidia-transformers4rec-reference status --short
```

Giữ worktree reference nguyên trạng; đọc và tìm kiếm tại đó, sửa code ở checkout đồ án. Đường dẫn worktree phụ thuộc máy, không dùng đường dẫn máy cá nhân trong config dùng chung. Khi checkout mới chưa có local branch, dùng remote ref sau fetch. Nếu môi trường agent chỉ cho đọc workspace hiện tại, dùng `git show` ngay trong checkout đồ án.

Kiểm tra cây nguồn khi Git đã có commit NVIDIA:

```powershell
git rev-parse 'origin/reference/nvidia-transformers4rec^{tree}'
git rev-parse 'f0ca2b5343dd1e40b5d2422b942f014b224f5c20^{tree}'
```

Hai tree hash phải giống nhau và bằng `0cd72aa1d3abd17cd65d46b9c1314b4ea26db9a6` (240 file). Nếu thiếu object nguồn, tải đúng commit bằng `git fetch --no-tags --depth=1 https://github.com/NVIDIA-Merlin/Transformers4Rec.git f0ca2b5343dd1e40b5d2422b942f014b224f5c20`. Khi cập nhật nguồn phải ghi quyết định đổi pin, kiểm tra tương thích và cập nhật bàn giao; không tự chạy theo upstream main.

### Tái tạo snapshot rút gọn (khi cần)

Từ thư mục gốc repo, khi cần lấy snapshot trên một checkout chưa có nguồn:

```powershell
python scripts/fetch_nvidia_reference.py --ref f0ca2b5343dd1e40b5d2422b942f014b224f5c20
```

Script chỉ dùng ở checkout chưa có snapshot: sparse-clone vào thư mục tạm, giữ nguyên notebook 01–03 cùng mã thư viện liên quan trong `docs/vendor/nvidia-transformers4rec/upstream/`, giữ LICENSE/NOTICE nếu có, và tạo `manifest.json` chứa commit nguồn cùng SHA-256 mỗi file. Script từ chối ghi đè snapshot đã tồn tại. Luôn truyền commit đã pin; mặc định cũ của script lấy upstream main. Có thể tái lập bằng:

```powershell
python scripts/fetch_nvidia_reference.py --ref <commit-trong-manifest>
```

### Đối chiếu theo việc cần làm

| Việc | Đường dẫn từ root nhánh/worktree reference |
|---|---|
| Đọc CSV, timestamp, lọc thời gian, event lặp | examples/tutorial/01-preprocess.ipynb |
| Groupby session, sequence, schema và Parquet | examples/tutorial/02-ETL-with-NVTabular.ipynb |
| Dựng GRU/XLNet, dataloader, trainer | examples/tutorial/03-Session-based-recsys.ipynb |
| Nhãn cuối chuỗi và causal/MLM | transformers4rec/torch/masking.py |
| Prediction head, điểm số và Top-K | transformers4rec/torch/model/prediction_task.py |
| Recall và NDCG | transformers4rec/torch/ranking_metric.py |
| Cách tutorial tạo split | transformers4rec/utils/data_utils.py |
| API, hành vi biên, ví dụ sử dụng module | tests/ và mã module tương ứng trong transformers4rec/ |

Kiểm tra file tồn tại bằng `git ls-tree` hoặc trong worktree trước khi đọc; ghi rõ file/class/hàm thực tế đã dùng. Snapshot rút gọn chỉ có các file được liệt kê trong manifest, nên tra nhánh reference khi cần module hoặc test khác.

### Hướng dẫn cho agent khi triển khai

1. Đọc AGENTS.md và docs/modeling/model_protocol.md; lấy nhánh reference và kiểm tra tree tại pin theo hướng dẫn trên. Nếu chưa đọc được nguồn, ghi trạng thái thiếu trước khi khẳng định code bám NVIDIA.
2. Đọc notebook và mã thư viện liên quan trên nhánh/worktree reference, thêm tests khi cần xác minh API hoặc hành vi biên; ghi commit nguồn, đường dẫn, class/hàm được tận dụng. Dùng snapshot rút gọn để kiểm tra checksum các file lịch sử.
3. Dựng code của nhóm ở pipeline/, models/, evaluation/ và configs/ trên nhánh phụ trách. Giữ bản reference nguyên trạng để đối chiếu; chỉ mang phần code cần dùng vào đồ án kèm nguồn/license, không merge toàn bộ nhánh reference vào main.
4. Áp dụng năm quyết định đã chốt trong docs/preprocessing_review.md: source sort không thêm khóa phụ CSV, giữ 20 item cuối, gom session trước day_index theo công thức nguồn, fit workflow/mapping trên tuần của từng subset trước split, first-seen trên tháng trước lọc tuần. Chia khoảng 80/10/10 trong từng partition, daily fine-tuning train partition t/validation partition t+1. Nhóm bổ sung stable-hash session sampling và K=20; catalog chung là product ID thực trong vocabulary tuần, không lọc train-only. Popularity là baseline nhóm triển khai riêng, chỉ đếm train; không khẳng định notebook 03 đã cung cấp model này.
5. Theo NVIDIA: cho phép seen items, đánh giá item cuối; GRU causal và XLNet MLM. Kiểm tra API masking ở package version thực tế, tránh tách target hai lần. Pin snapshot tham khảo không đồng nghĩa runtime đã tương thích.
6. Giữ thông tin bản quyền/license của code tái sử dụng. Ghi phần sửa đổi và nguồn trong code nhóm, references và handoff. Số liệu notebook chỉ là ví dụ nguồn.
7. Kiểm tra bằng toy session và smoke run trước benchmark; lưu command, output/log thật, cấu hình và phiên bản. Báo rõ phần chưa chạy.

### Prompt có thể dùng ở lần làm tiếp

> Đọc AGENTS.md, docs/modeling/model_protocol.md và docs/references.md. Đọc notebook, mã thư viện và tests liên quan từ nhánh reference/nvidia-transformers4rec tại commit nguồn f0ca2b5343dd1e40b5d2422b942f014b224f5c20 bằng git show hoặc worktree reference. Dựng code ở checkout đồ án trên nhánh phụ trách. Theo cách NVIDIA xử lý masking, seen item và ground truth đã chốt; áp dụng sampling của nhóm và năm quyết định preprocessing đã chốt theo tutorial trong docs/preprocessing_review.md, catalog product ID thực từ vocabulary tuần của subset. Ghi rõ preprocessing fit trước split, trọng số model chỉ học từ train. Ghi commit nguồn, phần tái sử dụng, license và các thay đổi. Kiểm tra toy session trước smoke run, không báo kết quả khi chưa có output thật.
