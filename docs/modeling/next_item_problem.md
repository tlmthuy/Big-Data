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

Danh sách output có tối đa 20 sản phẩm (K=20); không chỉ trả về một đáp án. Các ID trong output ví dụ được giả định thuộc catalog của subset. Trong ví dụ, target 309 đứng hạng 2, nên dự đoán có hit và NDCG@20 = 1/log2(3), khoảng 0,631. Đây là minh họa, không phải kết quả model thật.

Model không được nhìn thấy ID 309 tại vị trí target khi tạo dự đoán này. Với thư viện tự tạo nhãn, chuỗi đầy đủ có thể được đưa vào pipeline, nhưng causal shift hoặc masking phải bảo đảm điều đó.

## 3. Điểm dự đoán và catalog

Candidate catalog là các product ID thực trong vocabulary đã fit trên dữ liệu tuần của subset trước split, gồm cả item chưa xuất hiện trong train. Mỗi model chấm điểm các sản phẩm trong tập này rồi lấy tối đa 20 item có điểm cao nhất; loại các ID kỹ thuật như padding/unknown/mask. Điểm để xếp hạng không nhất thiết là xác suất đã chuẩn hóa.

Cho phép gợi ý lại sản phẩm từng xuất hiện trong prefix. Ví dụ [101, 205, 309] có target 101 thì 101 vẫn được phép nằm trong output.

## 4. Dữ liệu để học và dữ liệu để kiểm tra

Dataset là 2019-Oct.csv, giới hạn ngày 01–07/10/2019 UTC. Theo notebook 02, gom nguyên session rồi tính `day_index = (event_time_dt-first - col.min()).dt.days + 1`; trong mỗi partition chia ngẫu nhiên khoảng 80% train, 10% validation, 10% test, GPU seed 1. Không mặc định day_index là ngày lịch UTC. Đây là quyết định cập nhật ngày 19/11/2026.

Model được daily fine-tuning trên train partition t rồi đánh giá validation partition t+1, tiếp tục từ trạng thái model đã học. Test không dùng chọn cấu hình hoặc cập nhật trọng số; Lịch test cuối đã chốt: sau khi cố định cấu hình bằng validation, dùng checkpoint sau train 1…D−1 đánh giá test D; D là day_index cuối thực tế của subset, không train D trước test. Workflow/mapping fit trên tuần trước split; first-seen tính trên tháng trước lọc tuần. Popularity chỉ đếm train đã dùng, dù catalog chung lấy từ vocabulary tuần.

Validation/test mặc định dùng item cuối không phải padding làm target, các item đứng trước làm prefix. Cách tạo nhãn khi train khác nhau: GRU học các bước next item; XLNet MLM học dự đoán item bị che.

TV1 chuẩn bị bốn subset theo stable hash của session: 10%, 25%, 50%, 100%. Giữ event của session được chọn trong phạm vi thời gian đã chốt; xử lý event lặp liên tiếp, loại session dưới 2 interaction và giới hạn sequence 20 item.

## 5. Cách đánh giá

Recall@20 kiểm tra target có nằm trong Top-20 không. NDCG@20 thưởng cao hơn nếu target đứng gần đầu. Ba model phải dùng cùng tập ví dụ, catalog và quy tắc tổng hợp; xem [protocol chính thức](model_protocol.md).

## 6. Năm quyết định preprocessing đã chốt

Theo yêu cầu mới nhất của Thúy ngày 19/11/2026, áp dụng đúng cách làm tutorial NVIDIA đã pin:

1. **Timestamp trùng:** chỉ sort session/timestamp như notebook 01 và Groupby theo timestamp như notebook 02; không thêm khóa phụ theo dòng CSV, không bảo đảm thứ tự CSV khi timestamp bằng nhau.
2. **Sequence dài hơn 20:** giữ 20 item cuối, tính cả target. Ví dụ có 30 item thì giữ item 11–30; target là item 30, prefix là item 11–29.
3. **Session qua ngày:** giữ nguyên trong cửa sổ tuần rồi gán day_index theo công thức nguồn; không kiểm tra/loại session theo event cuối vượt cutoff train. Phần event ngoài tuần vẫn bị lọc trước khi gom sequence.
4. **Mapping/OOV:** fit toàn bộ workflow trên tuần của từng subset trước split, giữ mapping/schema cố định qua các partition. Notebook mô tả padding 0, null 1, OOV 2, mã đã biết từ 3; cần xác minh runtime. Item chỉ xuất hiện ở validation/test nhưng có trong dữ liệu fit vẫn có mã, không tự coi là OOV.
5. **First-seen:** tính timestamp nhỏ nhất theo product trên dữ liệu tháng sau xử lý sơ bộ/loại lặp, trước lọc tuần và split; tạo recency/log/normalization như nguồn. Baseline model vẫn chỉ dùng product ID.

Đây là đánh giá offline với preprocessing fit trước split; không mô tả toàn bộ pipeline là train-only. Năm điểm trên thay thế các đề xuất cũ, không còn chờ xác nhận lựa chọn; triển khai và smoke test vẫn chưa chạy. Chi tiết code cell, catalog và bàn giao xem [preprocessing_review.md](../preprocessing_review.md) và [model_protocol.md](model_protocol.md).

Nguồn: [Notebook 01](../vendor/nvidia-transformers4rec/upstream/examples/tutorial/01-preprocess.ipynb), [Notebook 02](../vendor/nvidia-transformers4rec/upstream/examples/tutorial/02-ETL-with-NVTabular.ipynb), [Notebook 03](../vendor/nvidia-transformers4rec/upstream/examples/tutorial/03-Session-based-recsys.ipynb), [mã split](../vendor/nvidia-transformers4rec/upstream/transformers4rec/utils/data_utils.py), [AGENTS.md](../../AGENTS.md).
