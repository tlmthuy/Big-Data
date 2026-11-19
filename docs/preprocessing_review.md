# Task 2 — Review Notebook 01: Preliminary Preprocessing

Ngày đọc: 19/11/2026. Người phụ trách: TV1.

Nguồn chính: [NVIDIA Notebook 01](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/01-preprocess.html).
Bản trong repo nhóm: [01-preprocess.ipynb](https://github.com/tlmthuy/Big-Data/blob/main/docs/vendor/nvidia-transformers4rec/upstream/examples/tutorial/01-preprocess.ipynb).
Đã đọc trực tiếp toàn bộ code cell của bản vendored trong repo nhóm và kiểm tra SHA-256 khớp manifest.

- Commit NVIDIA: `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`.
- SHA-256 notebook 01: `2db1065c530d37536efb939036c7ee6910e5e1e60290109796c1cc06fa3f8ec6`.
- [Notebook local](vendor/nvidia-transformers4rec/upstream/examples/tutorial/01-preprocess.ipynb), [manifest](vendor/nvidia-transformers4rec/manifest.json), [LICENSE](vendor/nvidia-transformers4rec/upstream/LICENSE).
- Chỉ số cell dưới đây bắt đầu từ 0, gồm cả Markdown cell; dùng để đối chiếu trong JSON notebook.

| Cell | Nội dung đã kiểm tra |
| --- | --- |
| 8–10 | Input path, đọc CSV, xem shape |
| 12–16 | Tạo timestamp, kiểm tra null, bỏ session null và event_time |
| 18–19 | NVTabular Categorify cho session |
| 25 | Sort, shift và bỏ consecutive repeated product |
| 28–29 | Groupby lấy item first-seen rồi merge |
| 33–38 | Kiểm tra min/max, lọc tuần đầu, bỏ datetime tạm |
| 41 | Ghi Oct-2019.parquet |

## Sơ đồ raw CSV → Parquet

```text
2019-Oct.csv
  ↓ cuDF đọc dữ liệu
  ↓ event_time → event_time_dt → event_time_ts
  ↓ Kiểm tra null, loại dòng thiếu user_session
  ↓ Bỏ event_time; Categorify user_session
  ↓ Sort theo session và timestamp; bỏ sản phẩm lặp liên tiếp
  ↓ Tính và ghép prod_first_event_time_ts theo product_id
  ↓ Giữ event trước 08/10/2019 trong file tháng 10
  ↓ Bỏ event_time_dt
Oct-2019.parquet
```

## Các bước trong notebook gốc

| Bước | Xử lý | Mục đích |
| --- | --- | --- |
| 1 | Import cuDF, NVTabular và thư viện hỗ trợ | Thiết lập xử lý GPU |
| 2 | Đọc CSV từ INPUT_DATA_DIR | Nạp bảng event |
| 3 | Chuyển thời gian sang datetime rồi số giây Unix | Phục vụ sort và feature thời gian |
| 4 | Kiểm tra null; bỏ dòng thiếu session | Bảo đảm có khóa phiên |
| 5 | Bỏ chuỗi thời gian gốc; mã hóa session thành số | Thuận tiện xử lý nhóm |
| 6 | Sắp theo session/thời gian, so với dòng trước | Loại cùng sản phẩm liên tiếp trong phiên |
| 7 | Lấy timestamp nhỏ nhất từng sản phẩm và merge lại | Chuẩn bị feature recency |
| 8 | Lọc event_time_dt < 2019-10-08 | Lấy tuần đầu của file tháng 10 |
| 9 | Bỏ datetime tạm, ghi Parquet | Bàn giao bảng event cho notebook 02 |

Session ID được mã hóa để xử lý, không phải feature đầu vào model. Đầu ra vẫn có missing category_code/brand. Quy tắc lặp xét session và product, không xét event_type. Merge sau sort không bảo đảm thứ tự cuối cùng; cần sort lại khi gom sequence.

## Đầu ra

Mỗi dòng vẫn là một event; chưa phải một sequence. Có 10 cột:

```text
user_session, event_type, product_id, category_id, category_code,
brand, price, user_id, event_time_ts, prod_first_event_time_ts
```

## Năm điểm đã chốt theo tutorial NVIDIA — 19/11/2026

Theo quyết định mới nhất của Thúy, cả năm điểm áp dụng cách làm trong snapshot NVIDIA `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`. Bảng này thay thế các đề xuất trước đó về khóa phụ theo dòng CSV, mapping/catalog train-only và first-seen chỉ từ train. Đây là quyết định phương pháp; chưa phải kết quả chạy preprocessing.

| Điểm | Cách làm đã chốt | Căn cứ trong snapshot |
| --- | --- | --- |
| 1. Timestamp trùng | Sort theo `user_session`, `event_time_ts`; khi gom session, sort theo `event_time_ts`. Không thêm khóa phụ theo thứ tự CSV. Nguồn không chỉ định thứ tự giữa các event có timestamp bằng nhau, nên dùng hành vi runtime nguồn và không cam kết giữ thứ tự CSV. | Notebook 01 cell 25; notebook 02 cell 37. |
| 2. Sequence dài hơn 20 | Giữ 20 item cuối bằng `ListSlice(-20, pad=True)`, cắt đồng bộ các feature dạng list. Session phải có ít nhất 2 interaction sau loại lặp. Độ dài 20 tính cả target đánh giá. | Notebook 02 cell 40, 42, 48. |
| 3. Session qua ngày/cutoff | Giữ nguyên session trong cửa sổ tuần, gom theo session trước khi gán `day_index`; không kiểm tra/loại theo event cuối vượt cutoff train. Event từ 08/10 bị lọc trước khi gom sequence, nên phần session ngoài tuần không được giữ. Dùng công thức nhóm ngày của nguồn, không tự đổi thành ngày lịch UTC. | Notebook 01 cell 34; notebook 02 cell 37, 44. |
| 4. Mapping/OOV | Fit toàn bộ workflow trên dữ liệu tuần của từng subset trước split, gồm mapping, chuẩn hóa và thống kê feature. Dùng mapping/schema cố định qua các partition của subset. Theo mô tả notebook: padding 0, null 1, OOV 2, mã đã biết từ 3. Item validation/test có trong dữ liệu fit vẫn có mã; chưa thấy trong train không tự có nghĩa là OOV. | Notebook 02 cell 18, 20, 51, 63. |
| 5. First-seen/recency | Trên dữ liệu tháng sau xử lý sơ bộ/loại lặp, lấy `min(event_time_ts)` theo product rồi merge trước khi lọc tuần và split. Notebook 02 tính recency theo ngày, áp dụng log và chuẩn hóa trong workflow fit trước split. | Notebook 01 cell 25, 28–29, 34; notebook 02 cell 28–29, 51. |

Ví dụ truncation: chuỗi 25 item giữ item thứ 6–25; item thứ 25 là target, item thứ 6–24 là prefix. Hai event cùng timestamp không có cam kết A đứng trước B chỉ vì A có dòng CSV nhỏ hơn.

### Chia partition và daily fine-tuning

Giữ đúng công thức notebook 02 cell 44:

```python
day_index = (event_time_dt_first - col.min()).dt.days + 1
```

`event_time_dt-first` là thời gian event đầu trong session trước truncation; biểu thức trên viết lại tên biến cho dễ đọc. `col.min()` được tính trong phép biến đổi nguồn; phải lưu runtime, partition và giá trị mốc thực tế khi chạy. Công thức không có bước chuẩn hóa về 00:00 UTC, nên không mô tả mặc định là ngày lịch UTC.

Notebook 02 cell 63 gọi `save_time_based_splits` với `partition_col='day_index'`, `timestamp_col='user_session'`. Nhánh GPU sort theo cột này, đặt seed `1`, sinh số ngẫu nhiên rồi chia khoảng 80/10/10 trong mỗi partition. Đây không phải lấy 80% session sớm nhất làm train. Lưu membership và counts thực tế.

Theo notebook 03, tiếp tục cùng model trên train partition t rồi đánh giá validation partition t+1. Test giữ riêng khỏi cập nhật trọng số và chọn cấu hình. Preprocessing fit trước split có sử dụng dữ liệu tuần gồm validation/test; không mô tả toàn bộ pipeline là train-only.

### Phần nhóm tích hợp cho đồ án

Những phần dưới đây là quy tắc tích hợp của nhóm, không khẳng định tutorial đã cung cấp sẵn:

- Giữ cửa sổ UTC `[2019-10-01, 2019-10-08)`, event view/cart/purchase; sampling stable hash trên session ID gốc hoặc mapping truy vết được ở 10/25/50/100%. Không sample từng dòng. Ghi counts trước/sau lọc và loại lặp.
- Tạo artifact first-seen tháng theo notebook 01 dùng chung; với mỗi subset, fit workflow riêng trên dữ liệu tuần được chọn trước split. Ghi riêng chi phí tạo artifact tháng và chi phí từng subset cho E2/E5; giữ manifest/checksum nguồn. Không fit một mapping chung của subset 100% rồi gọi đó là fit riêng subset 10%.
- Candidate catalog chung cho Popularity/GRU/XLNet là product ID thực trong vocabulary tuần của subset đã fit, không giới hạn về train từng ngày. Prediction head nguồn có chiều output theo embedding vocabulary, không có bộ lọc train-only. Nhóm loại padding/null/OOV/mask khỏi Top-20 và lưu mapping ngược; không gọi token kỹ thuật là sản phẩm.
- Popularity là baseline nhóm triển khai riêng, chỉ đếm tương tác train đã dùng tới partition hiện tại; item có trong catalog nhưng chưa được đếm có điểm 0, cùng điểm thì encoded ID tăng dần. Không dùng validation/test để tăng điểm popularity.
- Model baseline vẫn chỉ dùng product ID. Tạo first-seen/recency và các feature của workflow không đồng nghĩa thêm side features vào model hoặc mở rộng phạm vi ablation.
- Giữ K=20, seen-item rule, ground truth item cuối và công thức metric trong [model_protocol.md](modeling/model_protocol.md). Chỉ số thời gian t/t+1 hiểu theo partition nguồn. E3 cố định mapping/catalog; E4 so CSV/Parquet cùng nội dung và cùng phạm vi đo.

### Bàn giao và kiểm tra

Năm điểm đã chốt, không còn là câu hỏi mở để TV1/TV2 quyết định lại. TV1 triển khai và bàn giao data path, mapping/schema, vocabulary/catalog, nguồn first-seen tháng, split membership, counts, seed và runtime. TV2 kiểm tra target/masking/metric và catalog dùng chung; TV3 ghi thời gian/bộ nhớ/phạm vi đo. Lịch test cuối đã chốt tại docs/modeling/model_protocol.md: sau khi cố định cấu hình bằng validation, dùng checkpoint sau train 1…D−1 đánh giá test D; D là day_index cuối thực tế của subset.

Trước benchmark cần chạy toy/smoke test kiểm tra source sort, loại lặp, giữ 20 item cuối, session qua ngày, mã kỹ thuật và target. Chưa có code preprocessing/Parquet/log thực thi được xác nhận bởi lần cập nhật tài liệu này.

### Nguồn đối chiếu

Chỉ số cell tính từ 0, gồm cả Markdown cell. Các file đều thuộc snapshot đã pin:

- [Notebook 01](vendor/nvidia-transformers4rec/upstream/examples/tutorial/01-preprocess.ipynb): cell 25, 28–29, 34.
- [Notebook 02](vendor/nvidia-transformers4rec/upstream/examples/tutorial/02-ETL-with-NVTabular.ipynb): cell 18/20, 28–29, 37, 40/42/44/48/51/63.
- [Notebook 03](vendor/nvidia-transformers4rec/upstream/examples/tutorial/03-Session-based-recsys.ipynb): vòng train partition t/validation partition t+1, GRU/XLNet chỉ dùng product ID.
- [data_utils.py](vendor/nvidia-transformers4rec/upstream/transformers4rec/utils/data_utils.py): `_save_time_based_splits_gpu`.
- [prediction_task.py](vendor/nvidia-transformers4rec/upstream/transformers4rec/torch/model/prediction_task.py): `NextItemPredictionTask.build` lấy chiều output từ embedding vocabulary; `forward` chọn nhãn khác padding.
- [manifest](vendor/nvidia-transformers4rec/manifest.json), [LICENSE](vendor/nvidia-transformers4rec/upstream/LICENSE), [protocol nhóm](modeling/model_protocol.md).

## Kiểm tra và trạng thái

Đối chiếu sơ đồ/bảng bước với các mục timestamp, Categorify, removing repeated interactions, item first seen và đoạn ghi Parquet của nguồn. Đặc biệt kiểm tra lọc tuần diễn ra sau bước item first-seen trong notebook gốc.

Đã hoàn tất nội dung đọc hiểu và tạo sơ đồ/bảng bước từ notebook trong repo. Kết quả kiểm tra checksum: PASS; chỉ số cell đã đối chiếu trực tiếp. Commit và bàn giao xem [handoff](handoff.md).

Task này tạo tài liệu mô tả pipeline. Chạy preprocessing và tạo Parquet thuộc task triển khai sau đó, không phải điều kiện nội dung của task đọc notebook. Số đếm/runtime in sẵn trong tutorial không phải kết quả nhóm. Trạng thái người nhận kiểm tra vẫn chờ xác nhận theo AGENTS.md.

Nguồn mang thông báo Copyright 2022 NVIDIA Corporation, Apache License 2.0. Khi tái sử dụng code phải giữ attribution/license phù hợp. Tài liệu này được soạn với hỗ trợ AI và đối chiếu trực tiếp snapshot NVIDIA cùng nguồn HTML chính thức.

## Minh họa quy tắc lặp

Trong cùng session, A(view) → A(cart) → B(view) → A(view) thành A(view) → B(view) → A(view). Điều kiện chỉ so sánh product/session với dòng liền trước sau sort, nên khác event_type vẫn có thể bị loại. Notebook không lọc toàn bộ các lần xuất hiện lại của cùng sản phẩm.

## Cách kiểm tra lại mà không cần GPU

Từ gốc repo, dùng Python đọc JSON notebook và đối chiếu checksum:

```bash
python3 - <<'PYCODE'
import hashlib, json
from pathlib import Path
base = Path("docs/vendor/nvidia-transformers4rec")
manifest = json.loads((base / "manifest.json").read_text())
rel = "examples/tutorial/01-preprocess.ipynb"
p = base / "upstream" / rel
assert hashlib.sha256(p.read_bytes()).hexdigest() == manifest["files"][rel]
nb = json.loads(p.read_text())
for i in [9, 12, 14, 19, 25, 28, 29, 34, 38, 41]:
    print(f"CELL {i}\n" + "".join(nb["cells"][i]["source"]))
print("PASS: notebook checksum matches manifest")
PYCODE
```
