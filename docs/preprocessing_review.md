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

## Áp dụng cho đồ án

Ưu tiên tận dụng các phép biến đổi nguồn. Nhóm bổ sung raw audit, stable-hash sampling, counts, manifest và log. Sampling phải dựa trên session ID gốc hoặc mapping truy vết được.

Đồ án quy định cửa sổ UTC [2019-10-01, 2019-10-08), event view/cart/purchase và bốn mức session 10/25/50/100%. Đây là yêu cầu nhóm, không phải các bước sampling có sẵn trong notebook 01.

Gom sequence, độ dài 2–20, split và mapping sản phẩm là công việc tiếp theo. Theo protocol cập nhật, chia khoảng 80/10/10 session trong từng ngày bắt đầu UTC và daily fine-tuning trên train ngày t, validation ngày t+1. Product mapping, catalog và popularity chỉ dùng train đã khả dụng ở thời điểm dự đoán, không nhìn trước ngày tương lai. Feature học từ dữ liệu như item first-seen cần kiểm tra phạm vi thống kê, không sao chép tính trên toàn tháng một cách máy móc.

TV1/TV2 còn cần xác nhận chính sách session vượt ranh giới split, timestamp trùng, OOV và truncation. Đề xuất giữ 20 item cuối theo notebook 02 chưa phải quyết định được xác nhận trong tài liệu này.

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
