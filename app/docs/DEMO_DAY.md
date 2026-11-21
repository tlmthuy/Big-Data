# Demo TV4 trong ba phút

## Chuẩn bị

- [ ] Render URL: <https://demo-big-data.onrender.com/>.
- [ ] Mở bản offline từ thư mục demo với `npm run build && npm run preview`.
- [ ] Sau khi build, chạy `node scripts/capture_screens.mjs` với Google Chrome đã cài. Ảnh PNG tiếng Anh và tiếng Việt cho desktop và điện thoại nằm trong `screenshots/en/` và `screenshots/vi/`.
- [ ] Mở sẵn `#recommendation`, `#data` và `#experiments-e1`.

English talk track and Q&A: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Trình tự

1. **Phút đầu**. Mở tab Gợi ý sản phẩm và chỉ lịch sử cùng sản phẩm thực tế. Chọn lần lượt các phiên `rank1`, `rank20` và `miss`.
2. **Phút thứ hai**. Mở Dữ liệu. Giải thích sự kiện, phiên, phạm vi tuần đầu tháng 10 và các bước tạo chuỗi. Chỉ vào nguồn dưới bảng số liệu.
3. **Phút cuối**. Mở Thí nghiệm, giải thích Dự kiến và Thực tế, rồi chỉ phần toy dùng để kiểm tra công cụ.

Khi thấy “Chưa có”, nói “Artifact nguồn chưa cung cấp giá trị cho mục này.” Chỉ rõ phạm vi của artifact trước khi so sánh số liệu.
