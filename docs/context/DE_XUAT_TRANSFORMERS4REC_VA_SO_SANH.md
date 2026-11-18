# Phạm vi đã chốt: Session-Based Product Recommendation

Nhóm chốt tận dụng **NVIDIA Merlin Transformers4Rec** để xây dựng bài toán dự đoán sản phẩm tiếp theo trong cùng một `user_session`.

- Mô hình: **Popularity, GRU và XLNet**.
- Môi trường chính: **Public Cloud GPU VM chạy Ubuntu và Docker**; loại cloud/VM cụ thể sẽ được chọn theo tài nguyên và ngân sách.
- Đánh giá: cố định **K = 20**, dùng `Recall@20` và `NDCG@20`.
- Thực nghiệm: so sánh model, tăng kích thước dataset, thay đổi tài nguyên tính toán, so sánh CSV/Parquet và phân tích scalability khi dữ liệu tăng.
- Sampling: chọn các session hoàn chỉnh, giữ toàn bộ event của session, ghi seed và kiểm tra tính đại diện.
- Demo: công cụ chưa chốt, nhưng phải nhận hoặc chọn một session và hiển thị top-20 gợi ý cùng sản phẩm tiếp theo thực tế.

## Bối cảnh lựa chọn hướng

Bản đầy đủ có phân rã công việc, giờ công và lịch nhóm 5 người: [So sánh chi tiết công sức và thời gian](SO_SANH_CHI_TIET_CONG_SUC_THOI_GIAN.md).

**Điểm xuất phát: nhóm chưa có code/pipeline triển khai.** Cả hai phương án đều dùng dataset Kechinov đã chọn. Repo NVIDIA chưa được chạy thử trên tài nguyên nhóm.

| Tiêu chí | Phương án 1 — tự tích hợp theo kế hoạch ban đầu | Phương án 2 — tận dụng Transformers4Rec |
| --- | --- | --- |
| **Làm gì?** | Gợi ý sản phẩm theo lịch sử người dùng | Gợi ý sản phẩm tiếp theo trong cùng phiên mua sắm |
| **Có sẵn gì?** | Thư viện/implementation cho từng mô hình; nhóm chọn và ghép lại | Tutorial dùng đúng dataset, có xử lý dữ liệu, GRU/XLNet và đánh giá |
| **Phải tự làm gì?** | Dựng pipeline, chuẩn hóa dữ liệu giữa các mô hình, thống nhất cách chấm, kết nối demo | Cài môi trường, chỉnh cấu hình và dữ liệu, kiểm tra cách chấm, bổ sung thí nghiệm và demo |
| **Khối lượng theo phạm vi đang bàn** | Lớn: bốn mô hình gợi ý, bài toán phụ, nhiều dịch vụ AWS và sáu thí nghiệm | Gọn hơn nếu chọn Popularity + GRU, demo nhỏ; XLNet làm thêm khi còn thời gian |
| **Tốn thời gian ở đâu?** | Viết phần còn thiếu, ghép các nguồn code, sửa lỗi giữa các phần | Cài GPU/CUDA/NVTabular và điều chỉnh tutorial; thuận lợi thì có thể sớm chạy ra kết quả |
| **Rủi ro chính** | Dựng lâu, nhiều phần phụ thuộc nhau; chạy mẫu nhỏ được nhưng dữ liệu lớn có thể chậm/lỗi | Khó cài môi trường, thiếu GPU/VRAM; code có sẵn vẫn có thể phải sửa |
| **Hiệu năng** | Phải tự đo; chưa bảo đảm tốt | Cũng phải tự đo; không bảo đảm nhanh hơn hoặc chính xác hơn |
| **Khớp yêu cầu môn?** | Có, nếu có triển khai, thực nghiệm và phân tích kết quả | Có, nếu nhóm bổ sung thực nghiệm và phân tích; chỉ chạy tutorial là chưa đủ |

## Hai hướng khác nhau thế nào về thực nghiệm?

**Hướng cũ muốn tìm hiểu cả hệ thống từ đầu đến cuối.** Nhóm sẽ hỏi: cách gợi ý nào tốt hơn; dữ liệu nhiều lên thì chạy lâu hơn bao nhiêu; thêm máy có nhanh hơn không; lưu dữ liệu cách nào hiệu quả hơn; cuối cùng API trả kết quả nhanh đến đâu. Điểm hay là có nhiều thứ để phân tích về Big Data và cloud. Đổi lại, nhóm phải dựng được nhiều phần rồi mới đo đủ các câu hỏi đó, nên dễ tốn thời gian xây hệ thống hơn dự kiến.

**Hướng mới chọn một bài toán gọn hơn để làm kỹ.** Nhóm dùng lịch sử trong một phiên để đoán sản phẩm tiếp theo, rồi so sánh Popularity, GRU và XLNet. Nhóm cũng đo thời gian, bộ nhớ, ảnh hưởng của tài nguyên, định dạng lưu trữ và khả năng mở rộng khi dữ liệu tăng.

Ví dụ câu hỏi khi trình bày:

| Hướng cũ | Hướng mới đề xuất |
| --- | --- |
| “Trong các cách gợi ý đã chọn, cách nào tốt hơn trên cùng cách chấm?” | “Dùng thứ tự các sản phẩm đã xem trong phiên có giúp gợi ý tốt hơn sản phẩm phổ biến không?” |
| “Thêm máy có làm pipeline nhanh hơn và có đáng tiền không?” | “Khi tăng lượng dữ liệu trên cùng máy, thời gian xử lý và bộ nhớ tăng thế nào?” |
| “CSV/Parquet khác nhau ra sao, API trả kết quả nhanh không?” | “Nếu mở rộng: thay batch size lúc dự đoán thì tốc độ và bộ nhớ thay đổi ra sao?” |

**Với môn này, cả hai hướng đều có thể phù hợp.** Hướng cũ bao quát nhiều vấn đề hệ thống hơn; hướng mới thu gọn phạm vi để nhóm có thể tập trung chạy thực nghiệm và phân tích. Tuy nhiên, hướng mới vẫn cần đo phần xử lý dữ liệu/hiệu năng, không chỉ lấy điểm mô hình từ notebook. Đổi batch size cũng không thay thế cho thí nghiệm thêm nhiều máy nếu nhóm muốn chứng minh khả năng mở rộng theo số máy.

## Kết luận để nhóm chọn

**Phạm vi đã chốt là phương án 2 với Popularity + GRU + XLNet, K = 20 và năm nhóm thực nghiệm nêu ở đầu file.** Có code nền dùng đúng dataset nên nhóm tập trung vào sampling, điều chỉnh preprocessing, thiết kế đánh giá, benchmark và phân tích.

Điều kiện: chạy thử thành công trên môi trường GPU nhóm có thể sử dụng. Nếu cài đặt bị chặn hoặc tài nguyên không phù hợp, cân nhắc hướng Spark/ALS gọn hơn thay vì cố làm đủ kế hoạch cũ.

**So sánh này bao gồm cả việc thu gọn phạm vi, không chứng minh riêng thư viện NVIDIA tốt hơn.** Phương án 1 cũng có thể giảm việc nếu chỉ giữ vài mô hình và demo đơn giản.

Top-20 của hướng NVIDIA là **20 ứng viên cho bước tương tác tiếp theo trong cùng phiên**, không phải 20 sản phẩm ở phiên sau.

Nguồn: `requirement.txt`, `Big data in Cloud.docx`, [repo NVIDIA](https://github.com/NVIDIA-Merlin/Transformers4Rec), [tutorial dùng đúng dataset](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/index.html).
