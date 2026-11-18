# Experiment matrix

| ID | Câu hỏi | Biến thay đổi | Kết quả bắt buộc |
|---|---|---|---|
| E1 | Model nào tốt hơn? | Popularity / GRU / XLNet | Recall@20, NDCG@20, train/inference time |
| E2 | Dữ liệu tăng ảnh hưởng thế nào? | 10%, 25%, 50%, 100% session | runtime, memory, bytes, event/user count |
| E3 | Resource ảnh hưởng ra sao? | một resource variable | runtime, throughput, memory, cost nếu có |
| E4 | Định dạng nào hiệu quả hơn? | CSV / Parquet cùng nội dung | size, read time, preprocessing time, memory |
| E5 | Có scale được không? | phân tích các run E2 | runtime/1M event, bottleneck, uncertainty |

Số liệu trống cho tới khi có run thật.
