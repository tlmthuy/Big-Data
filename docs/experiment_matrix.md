# Experiment matrix

**Trạng thái: khung thiết kế, chưa có run config/command E1–E4 được bàn giao.** TV3 xem [manifest TV2](../configs/tv2_handoff.json) và [hướng dẫn nhận script](../environment/README.md). Chỉ metric/Popularity toy hiện sẵn chạy; không coi các dòng dưới là run registry đã phê duyệt.

| ID | Câu hỏi | Biến thay đổi | Kết quả bắt buộc |
|---|---|---|---|
| E1 | Model nào tốt hơn? | Popularity / GRU / XLNet | Recall@20, NDCG@20, train/inference time |
| E2 | Dữ liệu tăng ảnh hưởng thế nào? | 10%, 25%, 50%, 100% session | runtime, memory, bytes, event/user count |
| E3 | Resource ảnh hưởng ra sao? | một resource variable | runtime, throughput, memory, cost nếu có |
| E4 | Định dạng nào hiệu quả hơn? | CSV / Parquet cùng nội dung | size, read time, preprocessing time, memory |
| E5 | Có scale được không? | phân tích các run E2 | runtime/1M event, bottleneck, uncertainty |

Số liệu trống cho tới khi có run thật.

## Bàn giao kết quả cho TV4/TV5

TV2 phân tích và chốt metrics package chính thức từ logs TV3, gửi cả TV4 và TV5; mỗi số liệu cần có run_id, config, metric, đơn vị, nguồn log và ghi chú run bị loại. TV4 tạo figures/caption kỹ thuật từ package; TV5 chuẩn bị bảng/caption, đối chiếu logs với TV2 và viết results/limitations/reproducibility trong report/slides. TV4 bàn giao figures cho TV5 tích hợp. Mọi số liệu bổ sung hoặc thay đổi cách tính cần TV2 xác nhận. Lịch từng ngày: [team_tasks.md](team_tasks.md).

## Quy ước dữ liệu cho E1–E5 — cập nhật 19/11/2026

Theo [preprocessing_review.md](preprocessing_review.md) và [model_protocol.md](modeling/model_protocol.md), fit workflow trước split trên tuần của từng subset; catalog chung là các product ID thực trong vocabulary đó. Mapping không giới hạn về train từng partition. Popularity chỉ đếm train đã dùng; model baseline chỉ dùng product ID.

- E1: ba model cùng catalog tuần của subset, cùng split, target, K và quy tắc loại token kỹ thuật.
- E2/E5: fit workflow riêng từng subset; ghi vocabulary size, event/session counts và thời gian/bộ nhớ thực tế. First-seen tháng là artifact chung: báo chi phí tạo riêng, chi phí mỗi subset riêng; nếu báo end-to-end từ CSV tháng thì cộng/ghi rõ chi phí chung, không âm thầm bỏ khỏi tổng.
- E3: giữ nguyên workflow/schema/mapping/catalog/split giữa các cấu hình tài nguyên.
- E4: CSV và Parquet phải cùng nội dung event và cùng đầu vào feature; không so CSV tháng với Parquet tuần hoặc file session. Dùng cùng artifact first-seen và quy ước cache/phạm vi đo cho hai phía.

Day t/t+1 trong daily fine-tuning là partition day_index theo công thức notebook 02. Test không dùng cập nhật trọng số/chọn cấu hình; preprocessing fit trước split có dùng dữ liệu tuần gồm validation/test, cần ghi đúng trong báo cáo.
