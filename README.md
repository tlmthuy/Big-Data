# Big Data Recommender — Session-Based Next-Item Recommendation

Repo khung chính thức cho đồ án Big Data in Cloud Computing của nhóm.

## Phạm vi đã chốt

- Dataset: eCommerce Behavior Data from Multi-Category Store, input baseline `2019-Oct.csv`.
- Bài toán: session-based next-item recommendation theo `user_session`.
- Mô hình: Popularity, GRU và XLNet.
- Đánh giá: cùng split, ground truth, candidate catalog và `K = 20`; báo `Recall@20` và `NDCG@20`.
- Thực nghiệm: E1 model comparison, E2 dataset-size benchmark, E3 resource benchmark, E4 CSV/Parquet comparison, E5 scalability analysis.
- Môi trường dự kiến: public-cloud GPU VM, Ubuntu, Docker, NVIDIA Merlin/Transformers4Rec.

Preprocessing đã chốt theo tutorial NVIDIA ngày 19/11/2026: source sort không thêm khóa phụ CSV, giữ 20 item cuối, session qua ngày giữ nguyên rồi tính day_index theo nguồn, fit workflow trên tuần trước split, first-seen trên tháng trước lọc tuần. Catalog chung lấy từ vocabulary tuần của từng subset; Popularity và trọng số model chỉ học train. Chi tiết và code cell: [preprocessing_review.md](docs/preprocessing_review.md).

Toàn bộ mã nguồn NVIDIA được giữ nguyên trên nhánh `reference/nvidia-transformers4rec` tại commit nguồn đã pin. Khi dựng code đồ án, đọc nguồn bằng `git show` hoặc worktree riêng theo [hướng dẫn tra cứu NVIDIA](docs/references.md#đọc-nguồn-khi-đang-làm-code-đồ-án).

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md) trước khi sửa code hoặc chốt thiết kế.
2. Đọc [phân công thực thi](docs/team_tasks.md) và [yêu cầu môn học](docs/course_requirements.txt).
3. TV3 đọc [`environment/README.md`](environment/README.md), [manifest bàn giao TV2](configs/tv2_handoff.json) và [config/collector E1–E5](docs/modeling/experiment_runbook.md). Đã kiểm tra bằng toy; chưa xác minh trên dữ liệu thật hoặc runtime Docker/cloud chính thức.
4. Kiểm tra manifest và schema trong [`data/manifests/`](data/manifests/) trước khi chạy pipeline.
5. Ghi mọi lần chạy vào [`metrics/`](metrics/) và cập nhật [`docs/handoff.md`](docs/handoff.md).

## Cây repo

```text
app/                  Demo UI và inference adapter
benchmark/            Collector runtime, memory, throughput
configs/              Config model, subset, resource, experiment
data/                 Manifest/schema; raw và Parquet không commit
docs/                 Protocol, experiment matrix, handoff, references
  modeling/           Bài toán, so sánh model và protocol
  vendor/             Snapshot NVIDIA rút gọn có license và manifest
  archive/            Tài liệu lịch sử đã đóng gói
environment/          Dockerfile, environment.yml, hướng dẫn cài đặt
evaluation/           Recall@20, NDCG@20 và lệnh đánh giá
metrics/              Metrics nhỏ, run registry, metadata
models/               Popularity, GRU, XLNet
pipeline/             Sampling, preprocessing, split, mapping
reports/              Report (TV5), figures (TV4), tables và slides (TV5)
scripts/              Run scripts và tiện ích
```

## Quy tắc dữ liệu và Git

Không commit raw CSV, Parquet lớn, checkpoint, GPU log, secret hoặc credentials. Chỉ commit manifest, schema, command, metrics nhỏ và đường dẫn artifact. Mỗi task hoàn thành phải có code/config/docs, lệnh kiểm tra, output hoặc log, commit hash và handoff.

## Tài liệu đang dùng

| Cần tìm | File |
|---|---|
| Phạm vi, lịch, quy tắc chung | [AGENTS.md](AGENTS.md) |
| Nhiệm vụ và cách thực hiện của 5 thành viên, lịch TV4/TV5 | [team_tasks.md](docs/team_tasks.md) |
| Input, target và Top-20 | [next_item_problem.md](docs/modeling/next_item_problem.md) |
| Popularity, GRU và XLNet | [model_comparison.md](docs/modeling/model_comparison.md) |
| Luật đánh giá | [model_protocol.md](docs/modeling/model_protocol.md) |
| Chạy toy test, Recall/NDCG và baseline Popularity TV2 | [tv2_runbook.md](docs/modeling/tv2_runbook.md) |
| TV3 nhận script, kiểm tra môi trường và trạng thái sẵn chạy | [environment/README.md](environment/README.md), [tv2_handoff.json](configs/tv2_handoff.json) |
| E1–E5 | [experiment_matrix.md](docs/experiment_matrix.md) |
| Nguồn, license và hướng dẫn đối chiếu NVIDIA | [references.md](docs/references.md) |
| Raw subset theo session | [raw_subsets.md](docs/raw_subsets.md) |
| Chọn session bằng stable hash | [session_sampling.md](docs/session_sampling.md) |
| Thống kê raw trước sampling | [raw_audit.md](docs/raw_audit.md) |
| Mô tả 9 cột dữ liệu | [data_dictionary.md](docs/data_dictionary.md) |
| Năm quyết định preprocessing đã chốt và đối chiếu notebook 01–02 | [preprocessing_review.md](docs/preprocessing_review.md) |
| Bàn giao | [handoff.md](docs/handoff.md) |

Tám bản bối cảnh/đề xuất cũ được giữ nguyên trong [context-history.zip](docs/archive/context-history.zip), chỉ mở khi cần tra lịch sử. Phạm vi và lịch hiện hành lấy từ AGENTS.md.

## Trạng thái hiện tại — 20/11/2026

Đã tích hợp năm task TV2: protocol split/lịch test cuối, catalog/K=20, Recall@20, NDCG@20 và Popularity. Review code và 13 toy test đạt; file bàn giao từng task tại [TV2 runbook](docs/modeling/tv2_runbook.md). Kiểm tra tiếp nhận dữ liệu thật từ TV1 là task riêng ngày 21/11 trước E1.

Đã tích hợp ba task TV1 vào `main`: audit raw, chọn session bằng stable hash và xuất raw subset tuần đầu ở mức 10/25/50/100%. Code đã qua review và kiểm tra dữ liệu nhỏ; các counts và manifest của lần chạy TV1 được lưu trong Git. Hai lỗi đơn vị RSS trên Ubuntu và ghi đè bảng counts đã được sửa tại `f7fce3e`.

Raw CSV và danh sách session lớn vẫn ở máy TV1. Phương án bàn giao hiện tại là người nhận tái tạo từ raw cùng SHA-256 theo [hướng dẫn](docs/raw_subsets.md#người-nhận-tái-tạo-và-xác-nhận), đối chiếu rồi ghi xác nhận vào [handoff](docs/handoff.md). Ba task chưa được đánh dấu Done chính thức vì còn chờ kiểm tra độc lập trên dữ liệu thật.

Hai task script **GRU và XLNet** đã tích hợp vào main: [CLI](evaluation/run_neural.py), [model](models/session_models.py), [hướng dẫn](docs/modeling/neural_runbook.md), [GPU smoke đạt](metrics/tv2-model-smoke/README.md). Config/collector E1–E4 và công cụ E5 đã tích hợp; [5 run collector toy](metrics/tv2-config-collector-smoke/README.md) đạt. Dùng bộ này để benchmark E1–E5 sau khi bind đầu vào thật; hiện **chưa xác minh trên dữ liệu thật**. [Phép đo inference](docs/modeling/inference_timing.md) đã thống nhất cho ba model.

Chưa có xác nhận sequence/split cuối hoặc benchmark E1–E5 trên dữ liệu thật. Mọi kết quả thực nghiệm phải được ghi bằng `run_id`, commit, seed, cấu hình, phần cứng, phiên bản thư viện và đường dẫn output.

## Demo

UI hiện là bản nháp được duyệt tích hợp để giữ phần đã làm. Xem [app/TODO.md](app/TODO.md) để biết các lỗi ID/catalog, hiển thị model chưa có output và checklist hoàn thiện; phần mô tả dưới đây là hành vi mục tiêu.

Demo React + Vite nằm tại [`app/`](app/). Lịch sử hiển thị là prefix đã tách target; actual next item luôn được hiển thị riêng, kể cả khi nằm ngoài Top-20. Đổi model không đổi session, subset, split hoặc catalog; demo hiển thị product ID gốc và không lọc item đã có trong lịch sử.

```bash
cd app
npm install
npm run dev
```

Production build:

```bash
cd app
npm run build
```

Chi tiết và JSON mẫu: [`app/README.md`](app/README.md).
