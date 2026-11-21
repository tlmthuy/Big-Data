# TV4 demo talk track

## Three-minute walkthrough

### Dataset · about one minute

**English.** Our task is to predict the next item in a shopping session. We keep whole sessions so that we can learn from the order of interactions. A fixed hash selects nested samples from the first week of October 2019. All four cuDF subsets contain views, cart events and purchases. The table shows how many categories, brands, products and users each subset covers.

*Tiếng Việt. Bài toán là dự đoán sản phẩm tiếp theo trong một phiên mua sắm. Nhóm giữ nguyên phiên để học từ thứ tự tương tác. Hàm băm cố định chọn các tập lồng nhau trong tuần đầu tháng 10/2019. Cả bốn tập cuDF đều có lượt xem, thêm giỏ và mua hàng. Bảng cho thấy số danh mục, thương hiệu, sản phẩm và người dùng của mỗi tập.*

**English.** Volume is the size of the raw month. Velocity is the stream of timestamped events used for daily learning. Variety comes from different actions, categories and brands. Veracity means checking missing values, timestamps and repeated events. Value comes from using the session history to suggest the next product.

*Tiếng Việt. Khối lượng là quy mô dữ liệu gốc cả tháng. Tốc độ là dòng sự kiện có dấu thời gian dùng cho việc học theo ngày. Đa dạng đến từ hành động, danh mục và thương hiệu khác nhau. Độ tin cậy đến từ kiểm tra giá trị thiếu, dấu thời gian và sự kiện lặp. Giá trị là dùng lịch sử phiên để gợi ý sản phẩm tiếp theo.*

### Recommendations · about one minute

**English.** I’ll open Recommendations and use the Popularity toy run. In the Session dropdown, I’ll choose `rank1`, `rank20`, then `miss`. The actual item appears at rank 1 in the first session and rank 20 in the second. In `miss`, it is outside the Top-20. These are toy examples while we wait for real predictions. Switching models keeps the same history and actual item on screen.

*Tiếng Việt. Tôi mở tab Gợi ý sản phẩm và dùng lượt chạy toy của Popularity. Trong danh sách Phiên xem, tôi chọn `rank1`, `rank20`, rồi `miss`. Sản phẩm thực tế ở hạng 1 trong phiên đầu và hạng 20 trong phiên thứ hai. Ở phiên `miss`, sản phẩm nằm ngoài Top-20. Đây là các ví dụ toy trong lúc chờ dự đoán thật. Khi đổi model, lịch sử và sản phẩm thực tế vẫn hiển thị.*

### Experiments · about one minute

**English.** Planned shows the experiment setup. Actual shows values from the run artifacts. Toy runs are tool checks only. Dataset preprocessing timings are preliminary. When you see “Not available yet,” the team artifacts have not delivered that value yet.

*Tiếng Việt. Dự kiến cho thấy cấu hình thí nghiệm. Thực tế hiển thị giá trị từ artifact của lượt chạy. Run toy chỉ để kiểm tra công cụ. Số đo tiền xử lý ở tab Dữ liệu là sơ bộ. “Chưa có” nghĩa là artifact của nhóm chưa cung cấp giá trị đó.*

## Likely questions

1. **Why sample whole sessions?** It preserves each shopper’s event order and keeps the context needed for next-item prediction.

   *Vì sao lấy mẫu theo phiên? Cách này giữ thứ tự sự kiện và ngữ cảnh cần cho dự đoán sản phẩm tiếp theo.*

2. **Why use the cuDF set?** The team selected the weekly cuDF cleanup outputs for official experiments. Each subset uses its matching workflow and catalog.

   *Vì sao dùng tập cuDF? Nhóm chốt kết quả làm sạch cuDF theo tuần cho thí nghiệm chính thức. Mỗi tập con dùng đúng workflow và catalog tương ứng.*

3. **Why are scores missing?** The exported predictions contain ranked product IDs only. The demo can show order and rank from those IDs.

   *Vì sao chưa có điểm? Dự đoán xuất ra chỉ chứa mã sản phẩm theo thứ tự xếp hạng. Demo có thể hiển thị thứ tự và hạng từ các mã đó.*

4. **What do Recall@20 and NDCG@20 mean?** Recall@20 measures how often the real item is in the list. NDCG@20 gives more weight when it appears higher up.

   *Recall@20 và NDCG@20 nghĩa là gì? Recall@20 đo số lần sản phẩm thật có trong danh sách theo tỷ lệ. NDCG@20 cho trọng số cao hơn nếu sản phẩm ở hạng cao.*

5. **Why use toy data?** It lets us check the demo with known examples while the team prepares real predictions.

   *Vì sao dùng dữ liệu toy? Dữ liệu toy giúp kiểm tra demo bằng ví dụ có kết quả đã biết trong lúc nhóm chuẩn bị dự đoán thật.*

6. **What does 100% mean?** It means all eligible sessions in the first week of October 2019, UTC.

   *100% nghĩa là gì? Là tất cả phiên đủ điều kiện trong tuần đầu tháng 10/2019 theo UTC.*
