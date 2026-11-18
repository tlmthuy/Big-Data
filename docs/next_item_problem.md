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

## 5. Cách đánh giá và phần còn mở

Recall@20 kiểm tra target có nằm trong Top-20 không. NDCG@20 thưởng cao hơn nếu target đứng gần đầu. Ba model phải dùng cùng tập ví dụ, catalog và quy tắc tổng hợp; xem [protocol chính thức](model_protocol.md).

Chưa chốt: giữ đầu/cuối khi cắt chuỗi, session qua ranh giới ngày, timestamp trùng và cách biểu diễn/báo cáo target ngoài catalog. Cần thống nhất với TV1 trước khi chạy benchmark. Tài liệu này hoàn thành phần định nghĩa khái niệm, chưa xác nhận pipeline/model đã chạy.

Nguồn: [Notebook 03 trong snapshot NVIDIA](../references/nvidia-transformers4rec/upstream/examples/tutorial/03-Session-based-recsys.ipynb), [hướng dẫn nguồn](NVIDIA_REFERENCE_GUIDE.md), AGENTS.md. Các quy tắc sampling và split là yêu cầu đồ án.
