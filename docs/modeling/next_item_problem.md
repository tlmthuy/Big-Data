# Định nghĩa bài toán dự đoán sản phẩm tiếp theo

## 1. Nhóm cần giải quyết việc gì?

Từ lịch sử sản phẩm trong một phiên mua sắm (session), dự đoán sản phẩm khách sẽ tương tác ngay tiếp theo. Tương tác có thể là view, cart hoặc purchase; target không nhất thiết là sản phẩm được mua.

Mỗi sản phẩm được biểu diễn bằng product ID. Tên Áo, Quần, Giày dưới đây chỉ giúp đọc ví dụ; model của nhóm dùng ID, không đọc các tên này như văn bản.

## 2. Input prefix, target và output

Ví dụ một session sau preprocessing:

```text
Session đầy đủ: 101 (Áo) → 205 (Quần) → 309 (Giày)

Input prefix: [101, 205]  = lịch sử đã biết
Target:        309        = sản phẩm tiếp theo thật, còn gọi ground truth
Output:        [412, 309, 587, ...] = các ID được gợi ý, xếp theo điểm giảm dần
```

Danh sách output có tối đa 20 sản phẩm (K=20); không chỉ trả về một đáp án. Các ID trong output ví dụ được giả định thuộc catalog train. Trong ví dụ, target 309 đứng hạng 2, nên dự đoán có hit và NDCG@20 = 1/log2(3), khoảng 0,631. Đây là minh họa, không phải kết quả model thật.

Model không được nhìn thấy ID 309 tại vị trí target khi tạo dự đoán này. Với thư viện tự tạo nhãn, chuỗi đầy đủ có thể được đưa vào pipeline, nhưng causal shift hoặc masking phải bảo đảm điều đó.

## 3. Điểm dự đoán và catalog

Candidate catalog là tập sản phẩm xuất hiện trong train của subset đang chạy. Mỗi model chấm điểm các sản phẩm trong tập này rồi lấy tối đa 20 item có điểm cao nhất; loại các ID kỹ thuật như padding/unknown/mask. Điểm để xếp hạng không nhất thiết là xác suất đã chuẩn hóa.

Cho phép gợi ý lại sản phẩm từng xuất hiện trong prefix. Ví dụ [101, 205, 309] có target 101 thì 101 vẫn được phép nằm trong output.

## 4. Dữ liệu để học và dữ liệu để kiểm tra

Dataset là 2019-Oct.csv, giới hạn ngày 01–07/10/2019 UTC. Mỗi session được gán split theo ngày event đầu tiên:

| Split | Ngày bắt đầu session | Vai trò |
|---|---|---|
| Train | 01–05/10/2019 | Học tham số model; xây mapping, catalog và bảng popularity |
| Validation | 06/10/2019 | Chọn cấu hình trước khi đánh giá cuối cùng |
| Test | 07/10/2019 | Đo kết quả cuối cùng sau khi chọn cấu hình |

Validation/test mặc định dùng item cuối không phải padding làm target, các item đứng trước làm prefix. Cách tạo nhãn khi train khác nhau: GRU học các bước next item; XLNet MLM học dự đoán item bị che.

TV1 chuẩn bị bốn subset theo stable hash của session: 10%, 25%, 50%, 100%. Giữ event của session được chọn trong phạm vi thời gian đã chốt; xử lý event lặp liên tiếp, loại session dưới 2 interaction và giới hạn sequence 20 item.

## 5. Cách đánh giá

Recall@20 kiểm tra target có nằm trong Top-20 không. NDCG@20 thưởng cao hơn nếu target đứng gần đầu. Ba model phải dùng cùng tập ví dụ, catalog và quy tắc tổng hợp; xem [protocol chính thức](model_protocol.md).

## 6. Các điểm TV1 cần xác nhận

**1. Session dài hơn 20 item**

Giữ **20 item cuối**, giống Notebook 02:

```python
SESSIONS_MAX_LENGTH = 20
nvt.ops.ListSlice(-SESSIONS_MAX_LENGTH, pad=True)
```

Ví dụ có 30 item thì giữ item 11–30; khi đánh giá, item 30 là target, item 11–29 là prefix. **TV1 xác nhận áp dụng cách này.**

**2. Session bắt đầu ngày 5 nhưng kéo sang ngày 6**

**Vấn đề:** Nhóm đang chia ngày 1–5 để train, ngày 6 để validation, ngày 7 để test. Nhưng một session có thể bắt đầu ngày 5 và tiếp tục sang ngày 6. Nếu giữ nguyên session và xếp theo ngày bắt đầu, các event ngày 6 cũng bị đưa vào train. Vì vậy cần thống nhất cách chia dữ liệu và xử lý session qua ngày.

**Đề xuất:** đổi cách chia dữ liệu và train theo repo gốc để tận dụng pipeline có sẵn: gom nguyên session, xếp ngày theo event đầu; trong mỗi ngày chia khoảng 80% session cho train, 10% validation, 10% test. Khi chạy model, train lần lượt trên phần train ngày t rồi đánh giá bằng phần validation ngày t+1:

```python
time_index_train = time_index
time_index_eval = time_index + 1
```

Ví dụ: train ngày 1 → đánh giá ngày 2; tiếp tục train ngày 2 → đánh giá ngày 3. Đây là cách train cập nhật model qua từng ngày trong Notebook 03.

**TV1/TV2 xác nhận có đổi từ split ngày 1–5/6/7 sang cách này không. Chưa chốt.** Nếu đổi, cần cập nhật AGENTS.md và protocol, thống nhất cách dùng test để báo kết quả cuối, đồng thời kiểm tra session kéo sang ngày sau để tránh dùng event tương lai. Giống repo gốc chưa tự bảo đảm điểm cuối này.

**3. Hai event có cùng timestamp**

Repo gốc chỉ sort như sau, chưa ghi cách phân thứ tự khi trùng giờ:

```python
df.sort_values(['user_session', 'event_time_ts'])
```

Đề xuất: nếu trùng timestamp thì dùng thứ tự dòng trong CSV gốc. Đây là phần nhóm bổ sung. **TV1 xác nhận cách làm.**

**4. Target là sản phẩm chưa xuất hiện trong train**

Repo gốc tạo mapping trước khi chia dữ liệu:

```python
workflow.fit_transform(dataset)
```

Nhóm mình yêu cầu mapping chỉ học từ train, nên cần chỉnh chỗ này. **TV1 xác nhận cách mã hóa sản phẩm mới và giữ ID target gốc; TV2 chốt cách tính/báo cáo metric cho các trường hợp đó. Chưa chốt.**

TV1 ghi ngắn cách xử lý đã chọn dưới từng mục để TV2 dùng đúng khi đánh giá.

Nguồn: [Notebook 01 — sort và xử lý lặp](../vendor/nvidia-transformers4rec/upstream/examples/tutorial/01-preprocess.ipynb), [Notebook 02 — Groupby, ListSlice và mapping](../vendor/nvidia-transformers4rec/upstream/examples/tutorial/02-ETL-with-NVTabular.ipynb), [Notebook 03 — model và evaluation](../vendor/nvidia-transformers4rec/upstream/examples/tutorial/03-Session-based-recsys.ipynb), [mã split](../vendor/nvidia-transformers4rec/upstream/transformers4rec/utils/data_utils.py), [hướng dẫn nguồn](../references.md), [AGENTS.md](../../AGENTS.md). Các quy tắc sampling và split là yêu cầu đồ án.
