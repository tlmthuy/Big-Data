# Phép đo inference — full_evaluation_wall_v1

Popularity tạo một ranking dùng chung; GRU/XLNet tính điểm theo session/batch. Vì vậy thời gian sort ranking một lần không được đặt cạnh tổng forward neural để kết luận model nào nhanh hơn.

Từ lần cập nhật này, cả ba model dùng cùng `inference_seconds`: wall time từ trước khi đọc tập evaluation (và trước tạo ranking dùng chung của Popularity) đến sau khi đóng predictions JSONL và tổng hợp metric. Phạm vi gồm read/decode, chuẩn bị sequence, chuyển device, dự đoán/Top-20, chuyển ID về CPU, Recall/NDCG và ghi predictions. Neural giữ native testing forward của NVIDIA, gồm masking/label/loss; đây là **thời gian pipeline evaluation**, không phải latency forward thuần.

Audit toàn bộ dữ liệu, khởi tạo model, train/daily validation trước final evaluation, checkpoint và ghi metrics JSON nằm ngoài số đo final inference. Mỗi lần evaluate ghi thời gian riêng; không cộng daily validation vào final inference. Không có warmup riêng hay flush OS cache; ghi đúng giới hạn này khi so sánh run. Collector wall time bao trùm toàn process và được báo riêng.

| Field | Ý nghĩa |
| --- | --- |
| `inference_timing_protocol` | `full_evaluation_wall_v1` |
| `inference_seconds` | Wall time toàn evaluation split như trên |
| `evaluation_with_io_seconds` | Alias của cùng số đo, không cộng hai field với nhau |
| `inference_ms_per_session` | `1000 × inference_seconds / n_sessions` |
| `inference_sessions_per_second` | `n_sessions / inference_seconds` |
| `prediction_compute_seconds` | Diagnostic riêng: neural testing forward + ranking/IDs; Popularity ranking dùng chung một lần |
| `prediction_compute_scope` | Phạm vi diagnostic cụ thể; không dùng để so latency trực tiếp giữa model |
| `ranking_once_seconds` | Diagnostic lịch sử của Popularity, vẫn giữ để truy vết |

So sánh trên cùng membership, target, catalog, K=20, format và nơi lưu predictions, runtime/máy; giữ eval batch cố định 32 cho neural theo runner. Popularity được tái sử dụng ranking dùng chung vì output không phụ thuộc prefix. Báo tổng và số session để không nhầm tập nhỏ với model nhanh. Nhiều lần chạy mới đánh giá được biến thiên; toy run chỉ chứng minh công cụ và protocol hoạt động.

Log GPU smoke trước đây giữ nguyên provenance; `inference_seconds` neural cũ là compute và Popularity chỉ có `ranking_once_seconds`. Không đổi tên số cũ thành số mới. E5 từ chối log thiếu/sai protocol, yêu cầu chạy lại khi cần gộp vào benchmark mới. [Test hồi quy](../../evaluation/tests/test_inference_timing.py) dùng clock giả lập: 21 giây đọc dữ liệu phải được tính ở cả hai pipeline, ranking Popularity chỉ tính một lần.
