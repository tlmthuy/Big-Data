# Model protocol

## Quyết định ngày 19/11/2026

Theo yêu cầu của Thúy, áp dụng cách xử lý seen item và ground truth mặc định của tutorial NVIDIA đã kiểm tra. Nguồn và cách đối chiếu: [references.md](../references.md).

- K = 20. Mỗi danh sách chứa tối đa 20 product ID khác nhau, xếp theo điểm giảm dần.
- Candidate catalog: các sản phẩm xuất hiện trong train của subset tương ứng. Padding, unknown và mask token không phải sản phẩm được gợi ý.
- Seen-item rule: cho phép gợi ý lại item đã xuất hiện trong prefix. Áp dụng giống nhau cho Popularity, GRU và XLNet. Xử lý consecutive repeated item ở preprocessing là quy tắc riêng.
- Ground truth khi validation/test: item cuối không phải padding của chuỗi sau preprocessing và truncation. Prefix gồm các item đứng trước target. Mỗi session hợp lệ đóng góp một ví dụ đánh giá.
- Ví dụ A → B → C → A: prefix [A, B, C], target A; A vẫn được phép xuất hiện trong Top-20.
- GRU dùng causal masking, mặc định học các next item dọc chuỗi khi train; XLNet dùng MLM khi train. Cả hai đặt rõ `eval_on_last_item_seq_only=True` khi tích hợp và kiểm tra API ở phiên bản runtime.
- Nếu dùng thư viện tự sinh nhãn, đưa chuỗi đầy đủ vào cơ chế masking; không tách bỏ target hai lần. Item target phải được dịch/che đúng cách để không lộ vào context dự đoán.
- Split theo ngày bắt đầu session UTC: ngày 1–5 train, ngày 6 validation, ngày 7 test. Mapping và popularity chỉ fit trên train. Đây là quy định đồ án, không sao chép vòng daily fine-tuning của tutorial.
- Recall@20 mỗi ví dụ là 1 nếu target nằm trong Top-20, ngược lại 0. NDCG@20 là 1/log2(r+1) nếu target ở hạng r <= 20, ngược lại 0. Lấy trung bình trên cùng tập ví dụ cho ba model.

## Còn cần xác nhận trước benchmark chính thức

- Giữ 20 item đầu hay cuối, cách xử lý timestamp trùng và session vượt ranh giới ngày: phối hợp TV1 để bảo đảm không dùng event tương lai.
- Target ngoài catalog train: cần chốt cách biểu diễn unknown, giữ raw target ID và cách báo tỷ lệ cold-start; chưa âm thầm loại các ví dụ này.
- Pin runtime/version và chạy toy test xác nhận target, masking, padding và metric giống nhau giữa ba model. Chưa có kết quả chạy model thật.
