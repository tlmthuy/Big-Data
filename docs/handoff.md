# Handoff

## Trạng thái hiện hành

### TV2 — Config/collector và inference timing cho mốc 21/11 — kiểm tra 20/11/2026

- Theo phạm vi user xác nhận: tích hợp config/collector, kiểm tra bằng toy; **chưa xác minh trên dữ liệu thật**. Bộ công cụ dùng để chạy benchmark E1–E5 và toy logs dùng tham khảo vận hành/format; chưa dùng số toy làm kết luận eCommerce/scalability.
- Tích hợp `configs/{experiments,site.example,pipeline_metrics.example}.json`, `scripts/runs/run_experiments.py`, `benchmark/{collect,format_io,scalability}.py`, kèm `prepare_toy_site.py`. Matrix 11 run giữ lựa chọn đã chốt: E1=10%, E2/E5=GRU, E3=batch 32/128, E4=CSV/Parquet raw 10%. [Runbook TV3](modeling/experiment_runbook.md), [manifest](../configs/tv2_handoff.json).
- Chốt `full_evaluation_wall_v1`: cả ba model báo wall toàn evaluation làm `inference_seconds`, có ms/session và session/s; sort một lần Popularity và compute neural chỉ là diagnostic. [Phạm vi đo](modeling/inference_timing.md). Regression clock test tái hiện lệch cũ và đạt sau sửa; giữ nguyên log smoke lịch sử. E5 từ chối timing thiếu/khác protocol và không gộp toy logs vào dữ liệu thật.
- **29/29 test PASS**, gồm collector pass/fail, config invariants, toy/real guard, E4 multiset/command binding, E5 tổng hợp log/kiểm tra provenance. **5 run GPU/runtime toy qua collector PASS**: E1 ba model, E3 hai batch. [Command/summary/raw log bản sao](../metrics/tv2-config-collector-smoke/README.md), [test result + checksum](../metrics/tv2-config-collector-smoke/checks.json). Đây không phải full E2/E4 preprocessing run; chưa chạy model trên dữ liệu TV1.
- Bắt đầu benchmark thật sau khi có sequence/split/schema/catalog/version/manifest, TV2 kiểm tra đầu vào và TV3 có runtime chính thức. E2 cần telemetry đo preprocessing; E4 full cần shared CSV/Parquet preprocessing command từ TV1. Code/config không còn chờ để bàn giao; số liệu thật vẫn chưa có.
- Commit tích hợp config/collector và timing được ghi sau khi commit.

### TV2 — Tích hợp riêng GRU/XLNet vào main — 20/11/2026

- Theo yêu cầu của Thúy, chỉ đưa hai task script GRU/XLNet cùng dependency, test, hướng dẫn và bằng chứng GPU lên main. Matrix/config/runner experiment E1–E5 tiếp tục ở nhánh `feature/tv2-model-evaluation`; giữ nguyên dữ liệu/tài liệu TV1 và demo TV4 trên main.
- Nguồn code: `ea717d91b28f252e845aeb1bf97c3cda6baa7ec0`; bằng chứng GPU/verifier: `b2cbb39` trên nhánh TV2. Các file model/runner giữ nguyên byte so với source đã chạy GPU; test neural được tách khỏi test experiment để main chạy độc lập. Loader hỗ trợ lọc partition; fingerprint chung kiểm tra artifact thiếu/rỗng và băm toàn bộ file trong thư mục.
- Output: `models/session_models.py`, `evaluation/run_neural.py`, `evaluation/tests/test_neural.py`, `scripts/runs/verify_neural_smoke.py`, schema toy, requirements local smoke. [Hướng dẫn](modeling/neural_runbook.md), [manifest TV2](../configs/tv2_handoff.json), [metrics/predictions/verification GPU](../metrics/tv2-model-smoke/README.md).
- GPU smoke WSL RTX 3050: GRU/XLNet train/eval và last-item label, target hiding, batch independence đều PASS; môi trường khoảng 4,04 GB trong ngân sách 7 GB. Đây là dữ liệu toy; chưa có benchmark E1–E5, nghiệm thu artifact sequence/split thật hoặc runtime chính thức TV3. Kiểm tra sau tích hợp: `python -m unittest discover -s evaluation/tests -v` → **19/19 PASS**, checksum manifest và link tài liệu đạt; code model/runner khớp byte với source đã smoke GPU.
- User đã yêu cầu tích hợp sau khi xem trạng thái/bằng chứng smoke. TV3 vẫn cần chạy kiểm tra trên runtime của mình trước benchmark. Commit tích hợp hai task: `835a09eb023bfa9451d906b95f5b35f1454e20cf`.

### TV1 — Timestamp, cleanup và first-seen tháng — review 20/11/2026

- Commit sửa tài liệu sau review: `c4391e3`; đã đồng bộ `origin/main` vào
  nhánh TV1 không conflict, giữ cập nhật phân công năm thành viên.
- Commit triển khai đã push trên `feature/tv1-data`: timestamp `064eb4e`,
  cleanup `c0d8afa`, first-seen `1afd27c`. Nguồn: NVIDIA Transformers4Rec
  `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, notebook 01 cell 12, 14, 25,
  28–29 (chỉ số từ 0), Apache-2.0; LICENSE giữ tại
  `docs/vendor/nvidia-transformers4rec/upstream/LICENSE`.
- Điều chỉnh: triển khai ba bước bằng DuckDB CPU, giữ session ID gốc;
  cleanup dùng `lag(product_id)` theo session/timestamp và thứ tự timestamp
  trùng của DuckDB. Quyết định công cụ được người dùng chấp nhận trong chat,
  đã ghi tại `AGENTS.md`; model train/inference vẫn dùng NVIDIA runtime.
- Timestamp: bàn giao code `pipeline/event_timestamp.py` và
  `data/manifests/event_timestamp.json`; cột `event_time_ts` là BIGINT giây
  Unix UTC trong Parquet cleanup. 42.448.764 dòng trước/sau, 0 lỗi parse.
  Người dùng đã yêu cầu ghi nhận bàn giao timestamp sau review code/manifest;
  không yêu cầu xác nhận người nhận đã đọc file thật.
- Cleanup: `pipeline/preprocess_raw_events.py`,
  `data/manifests/timestamp_session_cleanup.json`; bỏ 2 dòng session null,
  11.715.474 event lặp, còn 30.733.288 event tháng. Chênh tổng 13 dòng so
  với output lưu sẵn NVIDIA. Ghi nhận nguyên nhân theo TV1 được người dùng
  chuyển lại ngày 20/11: chênh lệch do thứ tự timestamp trùng. Nguồn là giải
  thích của TV1; chưa có log đối chiếu từng event/session trong repo.
- First-seen: `pipeline/build_monthly_first_seen.py`,
  `data/manifests/monthly_first_seen.json`; 166.794 product, không null,
  chi phí tạo artifact chung 1,516 giây. Đã thu hẹp mô tả kiểm tra về đúng
  counts/khóa/null/bounds trong script; chưa có kiểm tra minimum độc lập từng
  product. Không thay code tính MIN hay kết quả manifest đã ghi.
- Command chạy lại và artifact path/checksum: xem `docs/event_timestamp.md`,
  `docs/timestamp_session_cleanup.md`, `docs/monthly_first_seen.md` và ba
  manifest tương ứng. Danh sách hai artifact cụ thể, schema/counts/checksum,
  đã ghi tại `docs/tv1_data_handoff.md` và
  `data/manifests/tv1_data_handoff.json` để TV2/TV3 tự tra cứu; không yêu cầu
  receipt, log ký nhận hoặc xác nhận đã đọc file.
- Review local: cú pháp ba script và JSON manifest hợp lệ; số dòng cleanup
  nhất quán và checksum liên kết cleanup → first-seen khớp trong manifest;
  `git diff --check` đạt. Không chạy lại CSV/Parquet thật hoặc GPU trong lần
  review này; không phát sinh số benchmark mới.
- Kiểm tra manifest bàn giao và liên kết hướng dẫn sau cập nhật: log
  `data/manifests/tv1_handoff_review.log`; đây là review metadata local,
  không phải kết quả chạy dữ liệu thật của TV2/TV3.
- Commit cập nhật nguyên nhân và manifest bàn giao: `ec26bee`; sau đó theo
  yêu cầu người dùng ngày 20/11/2026, bỏ receipt/gate xác nhận người nhận.
  Ba task được chấp nhận qua review code/docs/manifest, tích hợp vào main
  và xóa nhánh TV1 cũ. Manifest đủ thông tin để thành viên tự tra cứu.
  Không còn yêu cầu đối chiếu cuDF bắt buộc cho bản DuckDB đã chốt; chưa có
  benchmark model hoặc sequence/split cuối trong ba task này.

Năm task TV2 ngày 20/11 đã tích hợp vào main; lịch test cuối đã chốt trong [model_protocol.md](modeling/model_protocol.md). Kiểm chứng dữ liệu thật từ TV1 là task riêng ngày 21/11, trước E1. TV3 nhận script và trạng thái sẵn sàng qua [manifest TV2](../configs/tv2_handoff.json) và [hướng dẫn môi trường](../environment/README.md). Chưa có GPU runtime hoặc gói GRU/XLNet/E1–E4 được xác minh.

## Cập nhật phân công 5 thành viên — 20/11/2026

- Theo ảnh phân công người dùng cung cấp: TV4 phụ trách Demo & hỗ trợ report; TV5 phụ trách Report & Results. Vai trò TV1–TV3 và protocol giữ nguyên.
- Đã đồng bộ `AGENTS.md`, `README.md`, `docs/team_tasks.md`, `docs/experiment_matrix.md` và mục bàn giao này. Lịch TV4/TV5 gồm đủ các mốc trong ảnh; đường dẫn quy về cấu trúc repo: `app/`, `reports/`, `reports/figures/`, `reports/tables/`, `reports/slides/`.
- TV2 gửi metrics package chính thức cho TV4/TV5; TV4 giao figures/caption/references/license/AI statement cho TV5; TV5 đối chiếu logs với TV2 và hoàn thiện nội dung report/slides. Nhánh TV4 giữ `feature/tv4-demo-documentation`; nhánh phụ trách TV5 là `feature/tv5-report-results`.
- Kiểm tra: `git diff --check`; rà tham chiếu TV4/TV5 và số thành viên; đối chiếu đủ 10 dòng deadline trong ảnh cho mỗi vai trò; kiểm tra liên kết Markdown local của các file đã sửa. Đây là cập nhật kế hoạch, chưa tạo demo/report/slides hoặc kết quả experiment.
- Branch tích hợp: `main`; commit cập nhật phân công: `4bc361c`. Kiểm tra phạm vi bằng `git show 4bc361c --stat`. Người nhận TV4/TV5 chờ xác nhận; chưa đánh dấu Done theo quy tắc dự án.

## Bàn giao demo React/Vite — 20/11/2026

**Cập nhật sau review:** Người dùng duyệt tích hợp phần đã làm, giữ UI ở
trạng thái bản nháp. Các mô tả behavior bên dưới là mục tiêu; lỗi ID gốc,
catalog thiếu item, ẩn context khi chọn model chưa có output và xử lý data
rỗng được theo dõi tại [app/TODO.md](../app/TODO.md), không chặn lần tích hợp
này. Chưa nghiệm thu UI hoàn chỉnh hoặc inference thật. Report/slide outline
thuộc TV5 theo phân công cập nhật trên main.

- Commit implementation: `e90b0eb`; commit TODO và phạm vi duyệt bản nháp: `bcc0150` trên `tv4-demo`.
- Người dùng duyệt tích hợp ngày 20/11/2026; giữ tên nhánh thực tế `tv4-demo` cho lần bàn giao này. Kiểm tra độc lập `npm ci` và `npm run build` PASS; `git diff --check` sạch. Chưa kiểm tra tương tác trên trình duyệt; UI tiếp tục theo checklist, không đánh dấu UI hoàn chỉnh.
- Files created/updated:
  - `app/package.json`, `app/package-lock.json`, `app/index.html`
  - `app/src/main.jsx`, `app/src/styles.css`
  - `app/public/demo-data.json`
  - `app/README.md`, `README.md`, `.gitignore`
- Behavior:
  - History là prefix sau khi tách target; actual next item luôn hiển thị riêng kể cả khi ngoài Top-20.
  - Đổi model giữ session, subset, split và catalog; không lọc item đã xuất hiện trong history.
  - Product ID hiển thị dưới dạng ID gốc. GRU/XLNet không tạo ranking giả; UI báo chưa có prediction output.
  - Data bundled là toy TV2 từ `metrics/tv2-toy-day1/predictions.jsonl`, không phải kết quả dataset thật hoặc E1.
- Cách kiểm tra:

```bash
cd app
npm install
npm run dev
npm run build
```

Kết quả kiểm tra đã có: `npm install` PASS, `npm run build` PASS, Vite production bundle được tạo trong `app/dist/` và thư mục này bị ignore. Các output thật cho GRU/XLNet hoặc FastAPI inference vẫn pending cho TV2/TV3; demo không tự thay thế bằng prediction giả.

## Nhật ký bàn giao lịch sử

Các mục dưới giữ nguyên trạng thái tại thời điểm bàn giao. Những câu “chưa chốt lịch test” hoặc “CLI từ chối test” đã được quyết định mới phía trên thay thế; không dùng chúng làm hướng dẫn chạy hiện tại.

## Đồng bộ repo và đầu mối TV3 — 19/11/2026

- Thêm `configs/tv2_handoff.json`: command argv, input/output/expected metrics toy, checksum code/fixture chuẩn hóa LF, trạng thái pending cho data thật, GPU, GRU/XLNet và E1–E5. TV3 bắt đầu từ `environment/README.md`; Dockerfile yêu cầu image Merlin ứng viên cụ thể, chưa khẳng định đã có runtime GPU được pin.
- Giữ Python 3.10 cho môi trường CPU/toy; thay `hashlib.file_digest` bằng hash đọc chunk để bỏ phụ thuộc API Python 3.11. Runtime GPU không bị tự nâng Python. Đồng bộ runbook, README, preprocessing review, experiment matrix và team tasks; tách nhận dữ liệu thật ngày 21/11 khỏi chốt protocol. Giữ nhật ký cũ có nhãn lịch sử.
- Lệnh toy mới ghi vào `metrics/local/` (Git ignore), không trùng output lịch sử. Bỏ `.gitkeep` ở sáu thư mục đã có file; giữ snapshot/LICENSE, manifest và bằng chứng cũ.
- Kiểm tra: 13/13 unittest PASS, manifest checksum/command/expected metrics, cú pháp Python 3.10 và liên kết Markdown local đạt; log `metrics/tv2-environment-sync-tests.txt`. Thực thi local Python 3.13.12; chưa tạo Conda Python 3.10 hoặc build/chạy GPU Docker. Commit code/docs/manifest: `f5df636` trên main; người nhận TV3 chưa nghiệm thu môi trường GPU.

## Tích hợp năm task TV2 vào main — 19/11/2026

- Đã review và merge `feature/tv2-model-evaluation` tại `8b6a392` vào `main`, không conflict. Merge commit: `af280b91765a6e586dfdd20e69b9bab50e8d4e8c`.
- Phạm vi đạt review: chốt split/lịch test, catalog/K=20, Recall@20, NDCG@20 và baseline Popularity. File bàn giao theo từng task tại `docs/modeling/tv2_runbook.md`. Giữ các module nhỏ, không thêm model/dependency; test và output toy được giữ để tái kiểm tra.
- Kiểm tra: 13/13 unittest PASS (gồm Parquet, cumulative train-only, metric tính tay, lịch test cuối và test rỗng), `git diff --check` sạch. Log tại `metrics/tv2-final-test-tests.txt`. Nhánh TV2 đã push; commit này ghi bàn giao trên main.
- Kiểm chứng membership/counts/catalog thật sau TV1 bàn giao là task riêng ngày 21/11 trước E1; chưa có benchmark dataset/GPU hoặc xác nhận người nhận cho dữ liệu thật.

## TV2 — Chốt lịch test cuối sau review — 19/11/2026

- Thúy đã thống nhất: giữ daily train t/validation t+1 theo NVIDIA; sau khi cố định cấu hình bằng validation, test partition D bằng checkpoint sau train 1…D−1. D là day_index cuối thực tế của từng subset, xác minh từ membership đầy đủ; không train D hoặc chọn cấu hình/checkpoint bằng test. Quyết định này thay trạng thái chờ lịch test trong các bàn giao cũ bên dưới.
- Cập nhật protocol, runbook, mô tả bài toán và so sánh model. CLI Popularity cho phép test D với train-through D−1, từ chối test partition khác và báo lỗi khi test D rỗng. Thêm regression test lịch test cuối; nguồn daily training vẫn là notebook 03 NVIDIA tại pin f0ca2b5343dd1e40b5d2422b942f014b224f5c20, Apache-2.0; lịch test cuối là bổ sung của nhóm.
- Task 3 chốt protocol đã đủ nội dung theo bảng task cập nhật. Kiểm chứng cleaned sequence Parquet, catalog/vocabulary tuần, membership split và counts/runtime manifest thật được tách sang task tiếp nhận dữ liệu TV1 ngày 21/11, trước E1. Raw audit/membership sampling/raw subset không thay thế membership train/validation/test sau preprocessing. Chưa chạy GPU/dataset thật hoặc nghiệm thu dữ liệu.
- Kiểm tra cập nhật: `python -m unittest discover -s evaluation/tests -v` → 13/13 PASS; log tại `metrics/tv2-final-test-tests.txt`. Kiểm tra test D, chặn test trước D và test D rỗng; kết quả là toy, không phải benchmark thật. File bàn giao năm task ngày 20/11 được gom tại đầu `docs/modeling/tv2_runbook.md`; code giữ các module nhỏ hiện có.

## TV2 — Protocol, Recall/NDCG và Popularity — 19/11/2026

- Đã `git pull --ff-only origin main`: main tại `56efb2c` đã mới nhất; tạo nhánh phụ trách `feature/tv2-model-evaluation`. Commit code/protocol/test: `04cb5135079707ce4dbdcc09146e7f274b9c3bc7`. Commit bằng chứng/handoff theo sau trên cùng nhánh.
- Output: `docs/modeling/model_protocol.md`, `docs/modeling/tv2_runbook.md`, `evaluation/{data,ranking,run_popularity}.py`, `models/popularity.py`, fixtures/tests trong `evaluation/tests/`; kết quả nhỏ `metrics/tv2-toy-day1/`, test log `metrics/tv2-tests.txt`.
- Protocol split bám notebook 02 và `_save_time_based_splits_gpu`: công thức day_index nguồn sau Groupby, sort user_session, CuPy seed 1 đặt lại trong mỗi partition, ngưỡng ngẫu nhiên khoảng 80/10/10. Audit đọc membership thật và đếm session/item từng split, không thay thuật toán GPU bằng CPU. Candidate catalog từ vocabulary tuần fit trước split, K=20; technical IDs khai báo từ runtime và bị loại. Popularity chỉ đếm retained interactions train 1…t, một lần mỗi partition; điểm 0 cho catalog chưa thấy, tie encoded ID tăng dần.
- Đã giải thích cho TV2: notebook 03 train t, validation t+1 trên cùng model; vòng nguồn không chạy test dù notebook 02 có tạo test split. **TV2 chưa chọn lịch test cuối**; không coi đề xuất rolling test là đã được duyệt. CLI hiện chỉ chạy validation, từ chối test.
- Nguồn đối chiếu: NVIDIA `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, Apache-2.0; notebook 02/03, `transformers4rec/utils/data_utils.py`, `transformers4rec/torch/ranking_metric.py`, `tests/unit/torch/test_ranking_metrics.py`, `tests/unit/utils/test_data_utils.py`. Tree nhánh reference kiểm tra đúng `0cd72aa1d3abd17cd65d46b9c1314b4ea26db9a6`. Không sửa/copy nguyên code upstream; metric viết độc lập theo công thức single-target trên ranked IDs; Popularity/adapter do nhóm viết. LICENSE nguồn giữ nguyên trong snapshot.
- Lệnh thật: `python -m unittest discover -s evaluation/tests -v` → **11/11 PASS**, gồm Parquet layout, cumulative update, không đếm holdout/future train, padding, catalog, membership trùng, target hạng 1/20/21 và trung bình theo session. Python 3.13.12, PyArrow 23.0.1, Windows; không phải runtime GPU đã pin của nhóm.
- Toy run thật tại commit code trên: `python -m evaluation.run_popularity --sessions evaluation/tests/fixtures/sessions.jsonl --catalog evaluation/tests/fixtures/catalog.json --train-through 1 --subset toy --run-id tv2-toy-day1 --output metrics/tv2-toy-day1`. Recall@20 = 0.6666666666666666; NDCG@20 = 0.40922341623231767; 3 validation session. Có prediction output, counts, SHA-256 input/catalog/code và commit. Đây là dữ liệu tổng hợp, **không phải kết quả dataset hoặc E1**. `git diff --check` đạt.
- Còn thiếu: Parquet sequence, mapping/catalog tuần, GPU split membership/counts/runtime manifest thật từ TV1; lịch test TV2; run trên artifact thật và nghiệm thu người nhận. Không đánh dấu cả năm task Done chính thức. TV2/TV3 xem runbook để chạy; người nhận chưa xác nhận.

## Toàn bộ repo NVIDIA trên nhánh reference — 19/11/2026

- Theo yêu cầu của Thúy: nhánh `reference/nvidia-transformers4rec` chứa nguyên cây repo NVIDIA để đọc khi dựng code đồ án. Commit nhập nguồn: `e2859fd819c88875b7d7030478512b776d34f43e`; đã push origin, giữ parent lịch sử cũ `cf4b6043fbc881ab6f25a0fc6aa6e630c8bc97fd` bằng fast-forward, không force-push.
- Nguồn: https://github.com/NVIDIA-Merlin/Transformers4Rec.git tại `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`. Toàn bộ 240 file Git quản lý và LICENSE Apache-2.0 giữ nguyên; tree `0cd72aa1d3abd17cd65d46b9c1314b4ea26db9a6`. Đây là bản đầy đủ file tại commit đã pin, không phải bản sao toàn bộ lịch sử Git upstream, dữ liệu ngoài Git hoặc runtime đã cài.
- Commit hướng dẫn trên `main`: `ed993c0`. `AGENTS.md`, `README.md`, `docs/references.md` hướng dẫn đọc nhánh bằng `git show` hoặc worktree rồi viết code ở nhánh thành viên. Snapshot rút gọn và manifest cũ trên main được giữ để truy vết các đánh giá trước.
- Worktree reference đã được tạo bằng công cụ Codex `create_worktree`, tên `nvidia-reference`, detached tại commit nhập nguồn. Vị trí tùy máy; tìm bằng `git worktree list`. Khi sandbox chỉ cho đọc checkout đồ án, dùng `git show` theo references.
- Kiểm tra thật: `git diff --quiet reference/nvidia-transformers4rec f0ca2b5343dd1e40b5d2422b942f014b224f5c20` trả 0; cả hai tree hash bằng nhau; đếm 240 file; 16/16 SHA-256 của manifest rút gọn khớp file trong worktree đầy đủ; `git status --short` worktree rỗng; `git diff --check` đạt.
- Chưa chạy preprocessing, model hoặc GPU benchmark trong task này. Người nhận chưa xác nhận kiểm tra; chưa đánh dấu Done chính thức theo AGENTS.md.

Không ghi secret hoặc credential vào file này. Cập nhật sau mỗi bàn giao có output thật.

## Nguồn NVIDIA và protocol — 19/11/2026

- Branch: `reference/nvidia-transformers4rec`.
- Commit chứa snapshot và hướng dẫn: `2a431b9`.
- Commit NVIDIA: `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`.
- Artifact: `docs/vendor/nvidia-transformers4rec/`, `docs/references.md`, `docs/modeling/model_protocol.md`.
- Cách kiểm tra: đối chiếu SHA-256 của từng file upstream với manifest.json; đọc LICENSE, protocol và hướng dẫn. Script nhập nguồn: `python scripts/fetch_nvidia_reference.py --help`.
- Output thật: đã tải 16 file upstream (856298 bytes); tất cả SHA-256 khớp manifest; kiểm tra cú pháp script và `git diff --check` đạt.
- Chưa chạy: GPU runtime, train/inference hoặc benchmark. Chưa chốt các điểm dữ liệu còn mở với TV1.
- Người nhận: TV1/TV3 và các thành viên triển khai; trạng thái kiểm tra của người nhận: chờ xác nhận. Chưa đánh dấu Done theo quy tắc dự án.

## Hai task đọc model và định nghĩa bài toán — 19/11/2026

- Branch: `reference/nvidia-transformers4rec`; commit tài liệu: `1e0e2ec`.
- Files: `docs/modeling/model_comparison.md`, `docs/modeling/next_item_problem.md`.
- Đầu ra: bảng ba model, cấu hình tham khảo có nguồn, ví dụ prefix/target/Top-20 và hướng dẫn đọc Notebook 03.
- Kiểm tra: đối chiếu cell cấu hình trong notebook snapshot f0ca2b5; tất cả link local trong hai file tồn tại. Chạy `git show 1e0e2ec --stat` để xem phạm vi bàn giao.
- Giới hạn: tài liệu khái niệm đã soạn; chưa có run model. Các điểm TV1 cần xác nhận giữ nguyên trong protocol và note cá nhân local.
- Người nhận/kiểm tra: Thúy đọc và giải thích lại, TV1 đối chiếu format; chờ xác nhận, chưa đánh dấu Done.

## Dọn repo — 19/11/2026

- Giữ nguyên các thư mục chức năng đã thống nhất; chuyển snapshot nguồn từ root vào `docs/vendor/` và tài liệu model vào `docs/modeling/`.
- Đóng gói nguyên bản 8 tài liệu bối cảnh cũ vào `docs/archive/context-history.zip`; chỉ dùng để tra lịch sử. Yêu cầu môn học giữ ở `docs/course_requirements.txt`; runbook giữ ở `docs/team_tasks.md` và bỏ cột lịch cũ, dùng lịch AGENTS.md.
- Gộp hướng dẫn đối chiếu NVIDIA vào `docs/references.md`; README là mục lục tài liệu hiện hành. Các đường dẫn bàn giao ở mục trước đã cập nhật theo vị trí mới; commit cũ vẫn là lịch sử tạo nội dung.
- Kiểm tra: ZIP đọc được và khớp byte với 8 bản gốc trước khi dọn; 16 checksum upstream giữ nguyên; link Markdown local tồn tại; script nhập nguồn đúng cú pháp. Chưa có benchmark mới.
- Note cá nhân giữ local và vẫn bị .gitignore loại khỏi commit.

## Đồng bộ split và daily fine-tuning — 19/11/2026

- Branch: `main`; commit thay đổi: `14e4341`.
- Đã fetch và merge origin/main; local đã cập nhật, không có conflict.
- Theo quyết định người dùng: đồng bộ next_item_problem, model_protocol, AGENTS, references và team_tasks sang khoảng 80/10/10 session trong từng ngày; daily fine-tuning train ngày t, validation ngày t+1.
- Kiểm tra: `git diff --check`; tìm quy tắc split cũ trong các tài liệu hiện hành đã sửa; đối chiếu notebook 02/03 trong snapshot. Không sửa upstream.
- Chưa chạy model/benchmark. Session vượt cutoff, lịch test cuối và mapping qua ngày còn cần TV1/TV2 xác nhận. Người nhận chưa xác nhận; chưa đánh dấu Done.

## TV1 task 2 — Đọc preprocessing NVIDIA — 19/11/2026

- Branch: `feature/tv1-data`; commit tài liệu: `6c70594`.
- Output: `docs/preprocessing_review.md`; README đã có link tra cứu.
- Nội dung: sơ đồ raw CSV → Parquet, danh sách bước đúng thứ tự, cell tham chiếu, schema 10 cột đầu ra, ví dụ xử lý lặp và các phần nhóm bổ sung theo protocol hiện hành.
- Kiểm tra: đọc trực tiếp code cell notebook 01; SHA-256 khớp manifest nguồn f0ca2b5343dd1e40b5d2422b942f014b224f5c20; `git diff --check` đạt. Lệnh tái kiểm tra có trong tài liệu.
- Đây là đầu ra thật của task đọc hiểu, không phải log thực thi preprocessing. Tạo Parquet thuộc task sau; không dùng số liệu tutorial như kết quả nhóm.
- Người nhận: TV1/TV2/TV3; chờ xác nhận đã kiểm tra tài liệu, chưa đánh dấu Done chính thức theo AGENTS.md.

## Chốt năm điểm preprocessing theo tutorial — 19/11/2026

- Theo quyết định mới nhất của Thúy: dùng đúng source sort không thêm khóa phụ CSV, giữ 20 item cuối, giữ session qua ngày và day_index theo công thức nguồn, fit workflow/mapping trên tuần của từng subset trước split, tính first-seen trên tháng trước lọc tuần.
- Mục này thay thế các trạng thái chờ chốt session/mapping và quy định train-only trong các bàn giao trước; các mục cũ giữ để tra lịch sử. Lịch test cuối cùng vẫn chờ TV2 xác nhận.
- Đã đồng bộ AGENTS, README, preprocessing_review, model_protocol, next_item_problem, model_comparison, references, team_tasks, experiment_matrix và data/README. Catalog chung dùng product ID thực từ vocabulary tuần; token kỹ thuật không được gợi ý. Popularity là baseline nhóm, chỉ đếm train; model baseline vẫn chỉ dùng product ID.
- Nguồn: snapshot NVIDIA f0ca2b5343dd1e40b5d2422b942f014b224f5c20, notebook 01/02/03, data_utils.py và prediction_task.py; chi tiết code cell trong preprocessing_review.md. Upstream được giữ nguyên.
- Kiểm tra: đối chiếu code cell và checksum manifest; kiểm tra link Markdown local, quy định cũ trong tài liệu hiện hành và git diff --check. Chưa chạy preprocessing, GPU model hoặc benchmark. Chưa có xác nhận nghiệm thu của người nhận.
- Trạng thái Git: cập nhật tài liệu trong working tree, chưa commit/push ở lần bàn giao này; chưa đánh dấu Done chính thức.

## TV1 raw audit trước sampling — 19/11/2026

- Branch: `feature/tv1-data`; commit kết quả và script: `98a60e7`.
- Output: `data/raw_audit.csv`, `data/manifests/raw_audit_manifest.json`; hướng dẫn tại `docs/raw_audit.md`.
- Command: `.venv/bin/python pipeline/raw_audit.py --input /Users/nguyenbaochau/Downloads/2019-Oct.csv`.
- Output thật: 42.448.764 event toàn tháng; 8.829.315 event tuần đầu. Counts distinct, missing 9 cột, event type và ngày trong CSV. Runtime khoảng 148,95 giây; peak process RSS 997.081.088 bytes trên macOS.
- Kiểm tra: tổng event type/ngày bằng tổng dòng; bounds missing/distinct; tuần không vượt tháng; input size/mtime giữ nguyên; SHA-256 input và script trong manifest; `git diff --check` đạt.
- Không commit CSV nguồn, không làm sạch/sampling hoặc tạo sequence. Người nhận TV1/TV2/TV3 chưa xác nhận; chưa đánh dấu Done chính thức.

## TV1 — Chọn session bằng seed cố định — 19/11/2026

- Branch: `feature/tv1-data`; commit kết quả: `277abcf`.
- Script: `pipeline/sample_sessions.py`; command: `.venv/bin/python pipeline/sample_sessions.py --input /Users/nguyenbaochau/Downloads/2019-Oct.csv --seed 42`.
- Manifest: `data/manifests/session_sampling_manifest.json`; tài liệu: `docs/session_sampling.md`.
- Output thật tại `data/subset/session_ids/`: 187.563 / 469.728 / 938.071 / 1.877.365 session cho 10/25/50/100%. Danh sách CSV lớn giữ local theo quy tắc artifact; manifest ghi đường dẫn, seed, hash rule, counts và checksum để tái tạo.
- Kiểm tra PASS: ID không null/trùng, đúng hash threshold, tập lồng nhau, 100% bằng population; bốn checksum output khớp manifest, checksum input khớp raw audit; `git diff --check` đạt.
- Chưa xuất raw event subset hay chạy preprocessing. Người nhận chưa xác nhận; chưa đánh dấu Done chính thức theo AGENTS.md.

## TV1 — Xuất raw subset theo session — 19/11/2026

- Branch: `feature/tv1-data`; commit script/output nhỏ: `45554ea`.
- Đã fetch và merge origin/main cùng origin/feature/tv1-data: không có thay đổi mới hoặc conflict tại lần bàn giao này.
- Command: `.venv/bin/python pipeline/export_raw_subsets.py`.
- Output: raw CSV local tại `data/subset/raw_week/`; manifest `data/manifests/raw_subset_manifest.json`, bảng `data/manifests/raw_subset_counts.csv`, hướng dẫn `docs/raw_subsets.md`.
- Counts event/session/user/item: 10% = 882808/187563/163847/63398; 25% = 2213138/469728/356271/87247; 50% = 4421037/938071/601608/103940; 100% = 8829314/1877365/957543/118333.
- Kiểm tra PASS: input/membership checksums; header 9 cột; counts nguồn/output; số event chính xác theo từng session; không có session ngoài membership; bốn output checksums khớp manifest; `git diff --check` đạt. 100% ít hơn raw-week audit một dòng thiếu session.
- Dữ liệu giữ event lặp và session một event; chưa phải cleaned sequence. Không commit raw CSV lớn. Người nhận chưa xác nhận kiểm tra; chưa đánh dấu Done chính thức.

## Xác nhận của người nhận — Raw subset TV1

Phương án bàn giao là tái tạo từ CSV nguồn cùng SHA-256. Xem [lệnh tái tạo và cách đối chiếu](raw_subsets.md#người-nhận-tái-tạo-và-xác-nhận).

- Tái tạo nội bộ: xuất đủ bốn CSV với đường dẫn counts riêng. SHA-256 raw và danh sách membership khớp bản gốc. Bảng counts khớp từng byte, số event từng session khớp nguồn và tổng kiểm tra băm theo dòng không phụ thuộc thứ tự khớp bản gốc. SHA-256 toàn file CSV khác giữa hai lần xuất.
- Trạng thái: chờ người nhận kiểm tra độc lập.
- Người nhận và ngày kiểm tra:
- SHA-256 raw và bốn danh sách session:
- SHA-256 và counts của bốn CSV:
- Kết quả đối chiếu membership và số event từng session:
- Xác nhận Done:

## Tích hợp ba task raw TV1 vào main — 19/11/2026

- Theo yêu cầu của Thúy, merge `origin/feature/tv1-data` tại `f7fce3e51043397f8d93208bc1e036dcc71b2629` vào `main`, không conflict. Merge commit: `d5086ee20c2840d367241a4f682547ccaea6f17e`.
- Phạm vi: raw audit, danh sách session stable hash và raw subset tuần đầu; giữ nguyên các manifest lịch sử và counts TV1 đã commit. Không có raw CSV lớn được thêm vào Git.
- Review code: ba task đạt; RSS được chuẩn hóa cho Linux/macOS, export có `--counts` và chống ghi đè/trùng đường dẫn. Đã kiểm tra counts/manifest/checksum nguồn ở các lần review trước.
- Kiểm tra fix trên dữ liệu nhỏ: 200 session, 501 event hợp lệ; cả bốn subset giữ đúng multiset của chín field, gồm event lặp/session một event. Counts cũ được giữ nguyên khi dùng đường dẫn riêng; đích tồn tại hoặc trùng nhau bị từ chối. Đổi đơn vị RSS kiểm tra bằng giá trị mô phỏng Linux/macOS, không phải đo bộ nhớ thật trên Ubuntu.
- Cập nhật README, data/README và team_tasks để phân biệt membership, raw event subset và sequence; liên kết hướng dẫn tái tạo và trạng thái nghiệm thu.
- Chưa chạy lại toàn bộ raw hoặc truy cập bốn CSV thật trên máy TV1. Hướng dẫn tái tạo và kiểm tra nội bộ của TV1 đã có; xác nhận độc lập của người nhận vẫn để trống. Merge/review code không thay thế bước này; ba task chưa Done chính thức.
- Kiểm tra lại tài liệu: `git diff --check`, cú pháp ba script và các liên kết Markdown local trong tài liệu vừa sửa; trạng thái đồng bộ main kiểm tra qua Git sau khi push.
