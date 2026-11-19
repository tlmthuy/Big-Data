# Model protocol

## Quyết định ngày 19/11/2026

Theo yêu cầu của Thúy, năm điểm preprocessing áp dụng tutorial NVIDIA tại snapshot `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`. Quyết định này thay thế mapping/catalog train-only và khóa phụ theo dòng CSV trước đó. Xem [preprocessing_review.md](../preprocessing_review.md), [references.md](../references.md).

## Preprocessing và split đã chốt

| Điểm | Quy tắc áp dụng |
| --- | --- |
| Timestamp trùng | Sort theo session/timestamp như nguồn; Groupby sort theo timestamp. Không thêm khóa phụ CSV; không khẳng định các event cùng timestamp giữ nguyên thứ tự CSV. |
| Truncation | Sau loại lặp, session cần ít nhất 2 interaction; giữ 20 item cuối bằng `ListSlice(-20, pad=True)`. Độ dài 20 bao gồm target. |
| Session qua ngày | Gom nguyên session trong cửa sổ 01–07/10 trước khi gán partition; không loại theo event cuối vượt cutoff train. Tính `day_index` bằng `(event_time_dt-first - col.min()).dt.days + 1` như notebook 02; không thay bằng ngày lịch UTC. |
| Mapping/OOV | Với từng subset, fit workflow trên toàn dữ liệu tuần trước split, gồm mapping và thống kê feature; dùng cùng mapping/schema qua các partition. Notebook mô tả padding 0, null 1, OOV 2, mã đã biết từ 3; xác minh với runtime đã pin. |
| First-seen | Tính minimum timestamp theo product trên dữ liệu tháng sau xử lý sơ bộ/loại lặp, trước lọc tuần và split. Tạo recency/log/normalization theo notebook 02; baseline GRU/XLNet vẫn chỉ dùng product ID. |

Trong mỗi `day_index`, chia ngẫu nhiên khoảng 80/10/10 theo `save_time_based_splits`; nhánh GPU dùng seed `1`, sort theo `user_session` như lời gọi notebook. Lưu membership, counts và runtime để tái lập. Cùng model tiếp tục train partition t, đánh giá validation partition t+1. Test không dùng chọn cấu hình hoặc cập nhật trọng số; preprocessing trước split có sử dụng dữ liệu tuần gồm cả validation/test, phải ghi rõ trong báo cáo.

## Evaluation chung cho ba model

- K = 20. Output chứa tối đa 20 product ID thực khác nhau, xếp theo điểm giảm dần.
- Candidate catalog: các product ID thực trong vocabulary đã fit trên dữ liệu tuần của subset, gồm cả item chưa có tương tác train. Không lọc catalog về train từng ngày. Padding/null/OOV/mask không phải sản phẩm gợi ý; xuất Top-20 sau khi loại token kỹ thuật. Đây là quy tắc output chung của nhóm; prediction head nguồn có chiều output theo embedding vocabulary, không có bộ lọc train-only.
- Popularity là baseline nhóm tự xây, không có sẵn trong notebook 03. Chỉ đếm train đã dùng ở các bước daily fine-tuning tới hiện tại; item thuộc catalog nhưng chưa được đếm có điểm 0. Khi bằng điểm, dùng encoded ID tăng dần để tái lập. Không dùng event validation/test để tăng điểm popularity.
- Seen-item rule: cho phép gợi ý lại item đã có trong prefix. Áp dụng giống nhau cho Popularity, GRU và XLNet. Loại consecutive repeated item trong preprocessing là quy tắc riêng.
- Ground truth validation/test: item cuối không phải padding của sequence sau preprocessing/truncation. Prefix gồm các item trước target. Mỗi session hợp lệ đóng góp một ví dụ đánh giá.
- Ví dụ A → B → C → A: prefix [A, B, C], target A; A vẫn được phép xuất hiện trong Top-20.
- GRU dùng causal masking; XLNet dùng MLM khi train. Cả hai đặt rõ `eval_on_last_item_seq_only=True`, kiểm tra API runtime. Khi thư viện tự tạo nhãn, đưa sequence đầy đủ; không tách target hai lần và không để lộ target vào context dự đoán.
- Recall@20 mỗi ví dụ là 1 nếu target nằm trong Top-20, ngược lại 0. NDCG@20 là `1/log2(r+1)` nếu target có hạng r <= 20, ngược lại 0. Lấy trung bình trên cùng tập ví dụ của ba model.
- Item chỉ có ở validation/test vẫn có thể có mã nhờ fit trước split; không gọi trường hợp đó là OOV chỉ vì chưa xuất hiện trong train. Lưu mapping ngược để trả product ID gốc. Tutorial không có protocol cold-start riêng; không thêm benchmark OOV vào phạm vi bắt buộc.

## Artifact và kiểm tra trước benchmark

- TV1 bàn giao mapping/schema/vocabulary, catalog product ID thực, split membership, counts, nguồn first-seen tháng và phiên bản workflow. Fit độc lập trên tuần của từng subset 10/25/50/100%; ghi thời gian tạo first-seen chung riêng với preprocessing từng subset.
- TV2 xác nhận lịch test cuối cùng; năm quyết định preprocessing đã chốt, không còn chờ TV1/TV2 chọn lại.
- Pin runtime/version, lưu seed và kiểm tra toy session: source sort, loại lặp, truncation, target, masking, padding và metric. Timestamp bằng nhau phụ thuộc runtime nguồn; không tuyên bố tái lập qua runtime khác nếu chưa kiểm tra.
- Chưa có kết quả train/inference hoặc benchmark thật. Quyết định tài liệu không thay thế smoke run.
