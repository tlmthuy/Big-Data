# Bảng tham khảo Popularity, GRU và XLNet

Mục tiêu: hiểu ba cách giải cùng [bài toán next-item prediction](next_item_problem.md). Đây là bảng đọc tài liệu, chưa phải kết quả thực nghiệm.

## 1. So sánh cách hoạt động

| Nội dung | Popularity | GRU | XLNet |
|---|---|---|---|
| Vai trò | Baseline đơn giản do nhóm xây | Model chuỗi dùng recurrent neural network | Model chuỗi dùng Transformer |
| Dữ liệu để học | Lượt xuất hiện sản phẩm trong train sau preprocessing đã thống nhất | Chuỗi product ID từ train | Chuỗi product ID từ train |
| Khi đưa ra gợi ý | Dùng bảng đếm train; không dựa vào prefix | Dùng prefix của session hiện tại | Dùng prefix của session hiện tại |
| Cách xử lý | Đếm mỗi sản phẩm xuất hiện bao nhiêu lần, xếp giảm dần | Đọc lần lượt các item, cập nhật trạng thái ghi nhớ của session | Dùng attention để kết hợp thông tin giữa các vị trí trong chuỗi |
| Các khối chính | Bảng đếm → xếp hạng | Item embedding → MLP → GRU → prediction head | Item embedding → MLP → XLNet block → prediction head |
| Cách học trong tutorial | Notebook 03 không cung cấp baseline này | Causal: học đoán item kế tiếp từ lịch sử trước đó | MLM: che một số vị trí trong chuỗi train rồi học đoán item bị che |
| Hàm mục tiêu | Không tối ưu neural loss | Cross-entropy cho item cần dự đoán | Cross-entropy cho item bị che cần dự đoán |
| Output của nhóm | Top-20 item từ bảng popularity | Top-20 item theo điểm model | Top-20 item theo điểm model |
| Điểm cần lưu ý | Mọi session dùng cùng bảng xếp hạng | Cần kiểm tra chiều tensor, thứ tự, padding và causal shift | Cần kiểm tra masking và tài nguyên thực tế; dùng XLNet cho ID sản phẩm, không phải chatbot |

Embedding là cách chuyển một product ID thành vector số để neural model xử lý. Prediction head chuyển biểu diễn model thành điểm trên các sản phẩm. Attention cho phép model học cách các vị trí trong chuỗi liên quan tới nhau.

Ví dụ cùng prefix [Áo, Quần]: Popularity vẫn chọn các sản phẩm phổ biến toàn train; GRU và XLNet có thể thay đổi gợi ý theo lịch sử này. Chưa thể kết luận model nào chính xác hoặc nhanh hơn khi chưa chạy E1.

## 2. Cấu hình tìm thấy trong Notebook 03

Các giá trị dưới đây thuộc ví dụ NVIDIA, dùng để hiểu code. Chưa phải cấu hình tối ưu hay cấu hình runtime đã chạy thành công của nhóm.

| Thông số | GRU | XLNet chỉ dùng product ID |
|---|---|---|
| Sequence length | 20 | 20 |
| Masking | causal | mlm |
| d_model | 128 | 192 |
| Số layer của khối chính | GRU 1 layer | XLNet 2 layers, 4 attention heads |
| Batch train / eval | 256 / 32 | 256 / 32 |
| Epoch | 3 | 3 |
| Learning rate | 0.00071 | 0.000666 |
| Prediction head | NextItemPredictionTask, weight_tying=True | NextItemPredictionTask, weight_tying=True |
| Cutoff metric trong notebook | 10 và 20 | 10 và 20 |

Nhóm báo metric chính ở K=20. Batch size và các tham số cần kiểm tra với GPU/runtime, ghi vào config trước run. Phần thêm side features ở cuối notebook chưa thuộc baseline bắt buộc của nhóm.

## 3. Luật chung của ba model trong đồ án

Áp dụng [model_protocol.md](model_protocol.md): cùng split, ground truth, candidate catalog từ train, cho phép seen items, K=20 và cách tổng hợp metric. Validation/test dùng item cuối làm target; không nhầm với các vị trí được dùng để học khi train.

Các chi tiết dữ liệu còn mở được liệt kê trong protocol. Snapshot nguồn là tài liệu tham khảo; chưa chứng minh tương thích với môi trường GPU dự kiến.

## 4. Đọc Notebook 03 theo thứ tự nào?

Mở [notebook local](../references/nvidia-transformers4rec/upstream/examples/tutorial/03-Session-based-recsys.ipynb), chọn các heading sau; trước mắt có thể bỏ qua log và bảng số liệu đầu ra:

1. **3.1 Training an RNN-based Session-based Recommendation Model**: tìm input schema chỉ dùng product ID; hiểu input → GRU → prediction head.
2. **Defining the input block** và **Connecting the blocks**: tìm sequence_length=20, masking='causal', torch.nn.GRU.
3. **Item Prediction head** và **Metrics**: tìm NextItemPredictionTask, RecallAt, NDCGAt.
4. **3.2.2 XLNet** và **3.2.3 Train XLNET for Next Item Prediction**: tìm masking='mlm' và XLNetConfig.build; so sánh với GRU.

Sau khi đọc, tự giải thích bằng lời ba câu: Popularity đếm gì? GRU nhận lịch sử nào? XLNet che item để học khác việc lấy item cuối để đánh giá ra sao?

## 5. Nguồn và attribution

- NVIDIA Transformers4Rec, commit `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, [manifest](../references/nvidia-transformers4rec/manifest.json).
- Notebook 03: [bản local](../references/nvidia-transformers4rec/upstream/examples/tutorial/03-Session-based-recsys.ipynb).
- Default tạo nhãn: [masking.py](../references/nvidia-transformers4rec/upstream/transformers4rec/torch/masking.py).
- Head, loss và Top-K: [prediction_task.py](../references/nvidia-transformers4rec/upstream/transformers4rec/torch/model/prediction_task.py).
- Mã nguồn NVIDIA giữ [license Apache-2.0](../references/nvidia-transformers4rec/upstream/LICENSE). Tài liệu này diễn giải lại; không dùng metric của tutorial làm kết quả nhóm.
