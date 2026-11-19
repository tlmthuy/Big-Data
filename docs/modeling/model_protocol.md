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

### Chi tiết split để TV1 triển khai và TV2 kiểm tra

- Sau Groupby, tính `day_index = (event_time_dt-first - col.min()).dt.days + 1` theo LambdaOp của notebook 02, trên workflow của từng subset. Lưu minimum timestamp thực tế và runtime; không thay bằng ngày lịch, không tự thay phép tính distributed của nguồn bằng công thức khác.
- Gọi `save_time_based_splits(data=nvt.Dataset(sessions_gdf), output_dir=..., partition_col='day_index', timestamp_col='user_session', test_size=0.1, val_size=0.1, cpu=False)`. Dùng thư mục output mới: mặc định hàm nguồn có thể xóa output cũ khi `overwrite=True`.
- Trong **mỗi partition**, nhánh GPU đọc Parquet, sort `user_session`, gọi lại `cupy.random.seed(1)` rồi `cupy.random.rand(len(df))`. Train: `u <= train_size` với `train_size = 1 - val_size - test_size`; validation: `train_size < u <= train_size + val_size`; test: `u > 1 - test_size`. Giữ biểu thức float của nguồn. Đây là chia theo ngưỡng ngẫu nhiên, không phải ép đủ số lượng 80/10/10.
- Không thay bằng NumPy, sklearn hoặc seed sampling `42`: không đảm bảo cùng membership với CuPy. Phiên bản runtime và thứ tự session ảnh hưởng tái lập; membership đã lưu là đầu vào chung cho ba model.
- TV1 lưu `user_session` gốc/encoded có mapping, `day_index`, split; đảm bảo mỗi session thuộc đúng một partition/split. Lưu số session và distinct real item cho từng cặp `(day_index, split)`, cùng tổng counts, checksum artifact, seed `1`, lời gọi hàm và phiên bản cuDF/CuPy/NVTabular/Merlin/Python. Không điền counts ước lượng vào báo cáo.
- `evaluation.data.audit_sessions` kiểm tra membership không trùng, sequence/catalog hợp lệ và xuất session/item counts từ artifact có sẵn. Hàm này **không tạo lại split**, không xác minh RNG hay day_index khi thiếu timestamp; cần đối chiếu manifest preprocessing của TV1.

### Daily fine-tuning và lịch test

Notebook 03 khởi tạo model trước vòng lặp; với `range(1, 4)`, train partition 1/2/3 và lần lượt đánh giá **validation** partition 2/3/4. Cùng trọng số model được tiếp tục cập nhật, có reset LR scheduler mỗi bước; không khởi tạo lại model mỗi ngày. Với dữ liệu nhóm, dùng các cặp `t, t+1` thực có, không sao chép giới hạn 4 của tutorial một cách mặc định.

Notebook 02 tạo `test.parquet`, nhưng vòng lặp notebook 03 không đánh giá test. Lịch test cuối của nhóm **chưa chốt**; đề xuất rolling test chưa được TV2 phê duyệt và không phải protocol nguồn. Hiện chạy train/validation để kiểm tra; CLI Popularity từ chối test cho đến khi protocol này được cập nhật. Không đánh dấu task split hoàn tất trước khi có counts/membership thật và quyết định lịch test.

## Evaluation chung cho ba model

- K = 20. Output chứa tối đa 20 product ID thực khác nhau, xếp theo điểm giảm dần.
- Candidate catalog: các product ID thực trong vocabulary đã fit trên dữ liệu tuần của subset, gồm cả item chưa có tương tác train. Không lọc catalog về train từng ngày. Padding/null/OOV/mask không phải sản phẩm gợi ý; xuất Top-20 sau khi loại token kỹ thuật. Đây là quy tắc output chung của nhóm; prediction head nguồn có chiều output theo embedding vocabulary, không có bộ lọc train-only.
- Popularity là baseline nhóm tự xây, không có sẵn trong notebook 03. Chỉ đếm train đã dùng ở các bước daily fine-tuning tới hiện tại; item thuộc catalog nhưng chưa được đếm có điểm 0. Khi bằng điểm, dùng encoded ID tăng dần để tái lập. Không dùng event validation/test để tăng điểm popularity.
- Seen-item rule: cho phép gợi ý lại item đã có trong prefix. Áp dụng giống nhau cho Popularity, GRU và XLNet. Loại consecutive repeated item trong preprocessing là quy tắc riêng.
- Ground truth validation/test: item cuối không phải padding của sequence sau preprocessing/truncation. Prefix gồm các item trước target. Mỗi session hợp lệ đóng góp một ví dụ đánh giá.
- Ví dụ A → B → C → A: prefix [A, B, C], target A; A vẫn được phép xuất hiện trong Top-20.
- GRU dùng causal masking; XLNet dùng MLM khi train. Cả hai đặt rõ `eval_on_last_item_seq_only=True`, kiểm tra API runtime. Khi thư viện tự tạo nhãn, đưa sequence đầy đủ; không tách target hai lần và không để lộ target vào context dự đoán.
- Recall@20 mỗi ví dụ là 1 nếu target nằm trong Top-20, ngược lại 0. NDCG@20 là `1/log2(r+1)` nếu target có hạng r <= 20, ngược lại 0. Lấy trung bình trên cùng tập ví dụ của ba model.
- Tổng hợp bằng tổng điểm từng session / tổng số session hợp lệ; không trung bình đều các batch hoặc ngày có kích thước khác nhau. Một target nên IDCG = 1. Nếu tổng hợp nhiều partition, cộng `recall_sum`, `ndcg_sum`, `n_sessions` rồi chia. Tập rỗng báo lỗi; dự đoán rỗng là miss. Không âm thầm bỏ session khó hoặc target chưa xuất hiện trong train. Sequence sai schema, token kỹ thuật, target ngoài catalog hoặc membership trùng phải sửa artifact, không tự bỏ khỏi mẫu số.
- Popularity đếm **toàn bộ interaction thực trong train sequence sau preprocessing/truncation**, gồm item cuối của train session, bỏ right padding; mỗi train partition được đếm một lần, không nhân theo số epoch. Các bước sau cộng thêm train partition mới. GRU/XLNet có objective train riêng theo notebook, nhưng cùng tập train membership và ví dụ evaluation.
- Item chỉ có ở validation/test vẫn có thể có mã nhờ fit trước split; không gọi trường hợp đó là OOV chỉ vì chưa xuất hiện trong train. Lưu mapping ngược để trả product ID gốc. Tutorial không có protocol cold-start riêng; không thêm benchmark OOV vào phạm vi bắt buộc.

## Artifact và kiểm tra trước benchmark

- TV1 bàn giao mapping/schema/vocabulary, catalog product ID thực, split membership, counts, nguồn first-seen tháng và phiên bản workflow. Fit độc lập trên tuần của từng subset 10/25/50/100%; ghi thời gian tạo first-seen chung riêng với preprocessing từng subset.
- TV2 xác nhận lịch test cuối cùng; năm quyết định preprocessing đã chốt, không còn chờ TV1/TV2 chọn lại.
- Pin runtime/version, lưu seed và kiểm tra toy session: source sort, loại lặp, truncation, target, masking, padding và metric. Timestamp bằng nhau phụ thuộc runtime nguồn; không tuyên bố tái lập qua runtime khác nếu chưa kiểm tra.
- Chưa có kết quả train/inference hoặc benchmark thật. Quyết định tài liệu không thay thế smoke run.

## Code TV2 và bằng chứng kiểm tra

Lệnh chạy, schema catalog và artifact: [tv2_runbook.md](tv2_runbook.md). Metric tại `evaluation/ranking.py`, Popularity tại `models/popularity.py`, CLI tại `evaluation/run_popularity.py`. Toy test có expected tính tay, kiểm tra cumulative train-only, item chưa thấy điểm 0, tie-break, padding, membership và Parquet layout. Kết quả toy không phải kết quả eCommerce hoặc E1.

Nguồn đối chiếu trên nhánh reference tại `f0ca2b5343dd1e40b5d2422b942f014b224f5c20` (Apache-2.0): notebook 02/03; `transformers4rec/utils/data_utils.py::save_time_based_splits`, `_save_time_based_splits_gpu`; `transformers4rec/torch/ranking_metric.py::RankingMetric`, `RecallAt`, `DCGAt`, `NDCGAt`; `tests/unit/torch/test_ranking_metrics.py`, `tests/unit/utils/test_data_utils.py`. Tests nguồn không cung cấp test membership GPU (file utils chủ yếu kiểm tra loại lặp/first-seen); kiểm tra GPU thực tế vẫn thuộc smoke run. Code metric của nhóm viết độc lập trên ranked ID bằng thư viện chuẩn, dùng công thức single-target tương đương; không sao chép tensor implementation hoặc kết quả tutorial. Popularity và artifact validation do nhóm viết riêng; bản nguồn/LICENSE không bị sửa.
