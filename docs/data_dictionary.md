# Data Dictionary — 2019-Oct.csv

Ngày ghi nhận: 19/11/2026.



1. **Nguồn dữ liệu:** [https\://www\.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store?select=2019-Oct.csv](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store?select=2019-Oct.csv).  
2. **Bảng mô tả đủ 9 cột:**

| Cột | Ý nghĩa | Kiểu dữ liệu đề xuất khi xử lý |
| :---- | :---- | :---- |
| event\_time | Thời điểm tương tác, múi giờ UTC | Datetime |
| event\_type | Loại tương tác (view, cart, purchase) | String/category |
| product\_id | Mã sản phẩm | Int64 |
| category\_id | Mã danh mục | Int64  |
| category\_code | Đường dẫn danh mục | String |
| brand | Thương hiệu | String |
| price | Giá sản phẩm | Float |
| user\_id | Mã người dùng | Int64 |
| user\_session | Mã phiên truy cập | String |

3. **Minh chứng kiểm tra:**  
   ![][image1]  
4. **Nhận xét ban đầu:** Đã kiểm tra header và ba dòng dữ liệu đầu tiên của 2019-Oct.csv bằng thư viện Python csv, sử dụng dấu phẩy làm ký tự phân cách. Header và cả ba dòng mẫu đều có đủ chín trường theo schema dự kiến. Mẫu có giá trị trống tại category\_code và brand. Chưa thực hiện audit toàn bộ file.

[image1]: images/data_dictionary_evidence.png

Lưu ý: thư viện Python `csv` đọc giá trị dạng chuỗi. Các kiểu trong bảng là schema đề xuất cho bước xử lý tiếp theo; chưa xác nhận khả năng chuyển kiểu trên toàn bộ file. ID là mã định danh, không phải đại lượng số.
