# Config/collector toy validation — 20/11/2026

**Chưa xác minh trên dữ liệu thật.** Đây là kiểm tra công cụ phục vụ benchmark E1–E5 bằng dữ liệu tổng hợp; có thể tham khảo command, cấu trúc log và cách thu số đo.

- E1: Popularity, GRU, XLNet đều exit 0 qua runner + collector, trên cùng Parquet toy. Hai neural model dùng GPU RTX 3050/WSL đã ghi tại `metrics/tv2-model-smoke/environment.json`.
- E3: GRU batch train 32 và 128 đều exit 0, các config còn lại giữ theo matrix. Toy quá nhỏ để rút ra tác động batch size.
- Mỗi model train partition 1–2, validation t+1 và final evaluation partition 3; E1 dùng test, E3 dùng validation. Dữ liệu từ fixture JSONL cộng một test session tổng hợp ở partition 3, được đóng gói thành Parquet. `prepare_toy_site.py` tái tạo được bộ input; không có dữ liệu TV1 hay workflow đã fit.
- `summary.json` tóm tắt 5 run; mỗi thư mục `smoke-*` giữ bản sao run.json, stdout/stderr, metrics và predictions. Checkpoint và input Parquet ở `metrics/local/`, không commit. Command/exit code tại `command.json` và `E3-command.json`. Có nhãn `toy_smoke`, `data_kind=toy`, `subset=toy` trong output.
- E2: test matrix cố định GRU/10–100% và E5 đọc telemetry/log tổng hợp. E4: test cặp CSV/Parquet cùng multiset, giữ event lặp và truyền cùng preprocessing command tới hai format bằng worker fixture. Đây chưa phải lần chạy preprocessing TV1 hoặc benchmark E2/E4 thật. E5 kiểm tra output CSV/SVG, cấu hình/provenance và loại timing cũ/toy logs.
- Phép đo mới: [full_evaluation_wall_v1](../../docs/modeling/inference_timing.md). Cả ba model có `inference_seconds` bằng wall toàn evaluation; riêng compute/ranking chỉ là diagnostic. Không dùng timing GPU smoke cũ để gộp trực tiếp.

Lệnh tái chạy toy và benchmark thật: [experiment runbook](../../docs/modeling/experiment_runbook.md). Các run thực hiện trên working tree dựa từ `17b454b`; model metrics giữ SHA-256 code thực thi, không suy ra code chỉ từ HEAD cũ. Commit chứa bản sửa và chứng cứ được ghi ở `docs/handoff.md`.
