# TV4 — Demo UI đang phát triển

## Trạng thái và phạm vi duyệt — 20/11/2026

Theo quyết định của người dùng, chấp nhận tích hợp nhánh `tv4-demo` để giữ
khung demo và phần UI đã làm. UI React + Vite hiện là bản nháp dùng dữ liệu
toy Popularity; chưa nghiệm thu UI hoàn chỉnh, inference thật hoặc kết quả E1.
Các điểm dưới được giữ làm việc tiếp theo, không chặn lần tích hợp này.

Report outline và slide outline thuộc TV5 theo phân công cập nhật; không
thuộc danh sách việc còn thiếu của TV4.

## Cần sửa trước khi nghiệm thu UI

- [x] Map prefix, target và Top-20 sang product ID gốc bằng catalog của run.
- [x] Xuất đầy đủ 23 item trong catalog toy bằng lệnh trong [README](https://github.com/tlmthuy/Big-Data/blob/5b2df90c099bdafcba9389dab0b09102fef1c28e/app/README.md#prediction-data).
- [x] Luôn giữ history và actual next item khi chọn model chưa có output.
  Hiện chọn GRU/XLNet ẩn cả hai phần; chỉ vùng recommendation nên chuyển
  sang thông báo chưa có prediction.
- [x] Kiểm tra shape dữ liệu trước render; xử lý `sessions: []`, session
  không tồn tại và field bắt buộc bị thiếu, gồm `prefix`, `target`, `top20`.
  Hiện các trường hợp này có thể gây lỗi render.
- [x] Kiểm tra trên trình duyệt: session `rank1`, `rank20`, `miss`; đổi
  model rồi đổi lại; dữ liệu rỗng/lỗi; màn hình hẹp. Giữ nguyên thứ hạng TV2
  và cho phép gợi ý lại item đã nằm trong prefix.
- [x] Cập nhật README và handoff khớp hành vi thực tế sau khi sửa các mục trên.

> Đã xử lý ở repo `tv4-demo-web` (21/11 sample): validate dữ liệu trong `src/data.js` + `tests/`, kiểm tra trình duyệt rank1/rank20/miss, đổi model, file rỗng/hỏng/thiếu field, màn hình 375px.

## Chờ TV2 bàn giao và thống nhất

- [ ] Prediction output thật cho Popularity, GRU, XLNet và prediction
  contract được TV2 xác nhận; không tạo ranking giả cho model chưa có output.
- [ ] Mapping encoded ID ↔ original product ID, catalog đầy đủ và định danh
  catalog; cùng session/subset/split giữa các model được so sánh.
- [ ] Metadata truy vết: `run_id`, model, subset, split/partition, checkpoint
  nếu có, nguồn prediction/catalog và metrics package đã TV2 xác nhận.
- [ ] Thay dữ liệu toy bằng artifact đã bàn giao; không tự đổi protocol,
  tính lại recommendation hoặc dùng kết quả toy như benchmark thật.

Tích hợp inference/UI và kiểm thử demo theo lịch TV4 ngày 27/11; chuẩn bị
fallback và tập demo ngày 28/11. FastAPI chỉ bổ sung nếu cần gọi inference
Python, sau khi thống nhất với TV2/TV3.

## Chạy để tiếp tục phát triển

Từ root repo:

```bash
cd app
npm ci
npm run dev
```

Mở URL Vite in ra. Code chính: `src/main.jsx`, `src/styles.css`; dữ liệu
hiện tại: `public/demo-data.json`.

Kiểm tra build và xem bản build (chạy lần lượt):

```bash
npm run build
npm run preview
```

Review tại implementation `e90b0eb`, handoff `b0700cc`: `npm ci` và
`npm run build` đã PASS độc lập trên Node 24.12.0/npm 11.6.2 (Windows).
Build PASS chưa thay thế kiểm tra tương tác và bố cục trên trình duyệt.
