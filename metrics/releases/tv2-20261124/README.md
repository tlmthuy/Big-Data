# Metrics package TV2 → TV4/TV5

TV2 đã xác minh số liệu từ raw logs; đây là bộ duy nhất dùng cho figures/tables của báo cáo. Gói được phát hành để người nhận kiểm tra; **TV4 đã kiểm tra theo xác nhận người dùng ngày 24/11/2026; TV5 còn chờ**. Receipt ghi nguồn xác nhận từ chat, không do AI tự suy ra.

- `E1.csv` … `E5.csv`: bảng chính thức được TV2 chọn; `metrics.json` chứa cùng số liệu, có kiểu số và null cho phép đo thiếu.
- `configs.json`: config hiệu lực, command, nguồn log, versions/checksum workflow/mapping/catalog, split counts, runtime và provenance của từng run. E4 có manifest workflow/split và timing. E5 dùng run E2, không phải model mới.
- `run_registry.json`: danh mục các run dùng trong phân tích và smoke E4 bị loại; không phải danh sách mọi lần thất bại trên VM.
- `data_dictionary.json`: đơn vị, phạm vi timing/memory và giới hạn diễn giải. Không biểu diễn GPU chưa đo thành 0; RSS chỉ dùng mô tả.
- `manifest.json`: checksum file, nguồn runtime, báo cáo, source indexes và chỗ ghi nhận TV4/TV5 sau khi họ kiểm tra.

Từ root repo, chạy `python -c "from scripts.package_metrics import verify; print(verify())"` để kiểm tra checksum và CSV/JSON khớp nhau. `python -m scripts.analyze_results` tái tạo phân tích và gói này từ evidence đã lưu. Nguồn raw nằm trong `metrics/tv2-analysis-20261124/evidence/`, checksum byte gốc tại `source_manifest.json`; kiểm tra predictions trên VM tại `prediction_checks.json`.

Báo cáo: `reports/tables/tv2-20261124/analysis.md`; scaling SVG/PNG ở `reports/figures/tv2-20261124/scalability/`. Đọc limitations trước khi dùng số liệu. TV4 tạo figures; TV5 tạo bảng/nội dung từ cùng gói. Không tự chọn số khác; cần TV2 xác nhận mọi bổ sung.

Người nhận kiểm tra: JSON/CSV và checksum, đủ run E1–E5, config/source của số liệu dùng, đúng timing/memory scope; sau đó ghi tên/ngày/kết quả vào handoff và acknowledgements. Việc phát hành trên main không phải bằng chứng người nhận đã thực hiện bước này.
