"""Descriptive subset/cleanup audit supporting the instructor's feedback.

All percentages have explicit populations; this does not change the protocol.
"""

import csv
import hashlib
import json
from pathlib import Path

OUT = Path("reports/tables/tv2-20261124")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(name, rows):
    with (OUT / (name + ".csv")).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def md(rows, columns):
    def value(v):
        return f"{v:.4f}" if isinstance(v, float) else str(v)
    return ("| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) +
            " |\n" + "\n".join("| " + " | ".join(value(r[c]) for c in columns) + " |" for r in rows))


def quantile(histogram, fraction):
    total = sum(histogram.values())
    accumulated = 0
    for length in sorted(histogram):
        accumulated += histogram[length]
        if accumulated >= total * fraction:
            return length


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    sampling_path = "data/manifests/session_sampling_manifest.json"
    selected_path = "data/manifests/e2_preprocessing_verified.json"
    raw_path = "data/manifests/raw_subset_counts.csv"
    audit_path = "data/raw_audit.csv"
    sampling, selected = read(sampling_path), read(selected_path)
    raw = {int(r["percent"]): r for r in csv.DictReader(Path(raw_path).open(encoding="utf-8"))}
    baseline = selected["runs"][-1]
    assert baseline["subset"] == 100
    population = sampling["population_sessions"]
    assert population == int(raw[100]["session_count"]) == baseline["profile"]["distinct"]["user_session"]
    hist100 = {int(k): v for k, v in baseline["profile"]["session_length_histogram"].items()}
    n100 = sum(hist100.values())
    rows, distribution, retention = [], [], []
    for run, sample in zip(selected["runs"], sampling["outputs"]):
        subset, profile = run["subset"], run["profile"]
        assert subset == sample["percent"]
        hist = {int(k): v for k, v in profile["session_length_histogram"].items()}
        events, sessions = run["events_after_repeat_removal"], profile["distinct"]["user_session"]
        assert sum(hist.values()) == sessions == sample["session_count"]
        assert sum(k * v for k, v in hist.items()) == events == sum(profile["event_types"].values())
        assert sum(v for k, v in hist.items() if k >= 2) == run["sequence_count"]
        assert run["n_events"] == int(raw[subset]["event_count"])
        rows.append({"subset_session_threshold_pct": subset,
            "raw_sessions": sessions, "actual_raw_session_pct": 100 * sessions / population,
            "raw_events": run["n_events"], "actual_raw_event_pct": 100 * run["n_events"] / baseline["n_events"],
            "raw_users": int(raw[subset]["user_count"]), "catalog_items": run["vocabulary_size"],
            "cleaned_events": events, "cleaned_users": profile["distinct"]["user_id"],
            "model_sequences": run["sequence_count"],
            "cleaned_categories": profile["distinct"]["category_id"],
            "cleaned_brands": profile["distinct"]["brand"],
            "catalog_coverage_of_100_pct": 100 * run["vocabulary_size"] / baseline["vocabulary_size"]})
        lengths = set(hist) | set(hist100)
        tv = .5 * sum(abs(hist.get(k, 0) / sessions - hist100.get(k, 0) / n100) for k in lengths)
        cdf, cdf100, ks = 0., 0., 0.
        for k in sorted(lengths):
            cdf += hist.get(k, 0) / sessions
            cdf100 += hist100.get(k, 0) / n100
            ks = max(ks, abs(cdf - cdf100))
        event_tv = .5 * sum(abs(profile["event_types"].get(k, 0) / events -
            baseline["profile"]["event_types"].get(k, 0) / baseline["events_after_repeat_removal"])
            for k in ("view", "cart", "purchase"))
        distribution.append({"subset": subset,
            **{k + "_pct_clean_events": 100 * profile["event_types"].get(k, 0) / events
               for k in ("view", "cart", "purchase")},
            "mean_clean_session_length": events / sessions,
            "p50_clean_length": quantile(hist, .5), "p90_clean_length": quantile(hist, .9),
            "p95_clean_length": quantile(hist, .95),
            "length_TV_vs_100": tv, "length_max_CDF_gap_vs_100": ks,
            "event_TV_vs_100": event_tv})
        retention.append({"subset": subset,
            "event_removed_pct": 100 * (run["n_events"] - events) / run["n_events"],
            "single_interaction_session_pct": 100 * hist.get(1, 0) / sessions,
            "eligible_sequence_session_pct": 100 * run["sequence_count"] / sessions,
            "eligible_sessions_over_20_pct": 100 * sum(v for k, v in hist.items() if k > 20) / run["sequence_count"],
            "interactions_before_truncation_eligible": sum(k * v for k, v in hist.items() if k >= 2),
            "retained_interactions_after_truncation": sum(min(k, 20) * v for k, v in hist.items() if k >= 2)})
    raw_types = {r["value"]: int(r["count"]) for r in csv.DictReader(Path(audit_path).open(encoding="utf-8"))
                 if r["scope"] == "raw_week" and r["metric"] == "event_type_count"}
    raw_total = sum(raw_types.values())
    event_rows = [{"event_type": kind, "raw_week_count_including_null_session": raw_types[kind],
                   "raw_week_pct": 100 * raw_types[kind] / raw_total,
                   "clean_100_count": baseline["profile"]["event_types"][kind],
                   "clean_100_pct": 100 * baseline["profile"]["event_types"][kind] / baseline["events_after_repeat_removal"]}
                  for kind in ("view", "cart", "purchase")]
    for name, records in [("sampling_population", rows), ("subset_distribution", distribution),
                          ("preprocessing_retention", retention), ("event_mix_before_after", event_rows)]:
        write_csv(name, records)
    max_tv = max(r["length_TV_vs_100"] for r in distribution)
    p = rows[0]
    last = retention[-1]
    # Quantify only already measured stages; distinguish CPU preprocessing from model compute.
    e2 = list(csv.DictReader((OUT / "E2.csv").open(encoding="utf-8")))
    stage, split_rows = [], []
    for r in e2:
        metrics_path = Path(r["source_metrics"])
        metrics = read(metrics_path)
        counts, day = metrics["split_counts"], metrics["eval_day"]
        def split_total(split, predicate=lambda value: True):
            return sum(c["n_sessions"] for c in counts if c["split"] == split and predicate(c["day_index"]))
        split_rows.append({"subset": r["subset"], "last_partition_D": day,
            "saved_train_all_days": split_total("train"), "saved_validation_all_days": split_total("validation"),
            "saved_test_all_days": split_total("test"), "train_used_1_to_Dminus1": split_total("train", lambda d: d < day),
            "validation_used_2_to_D": split_total("validation", lambda d: d >= 2),
            "final_test_D": split_total("test", lambda d: d == day),
            "train_D_not_used": split_total("train", lambda d: d == day)})
        assert split_total("train") + split_total("validation") + split_total("test") == int(r["total_sequence_sessions"])
        total = sum(float(r[k]) for k in ("raw_read_seconds", "preprocessing_seconds",
                                        "train_seconds_including_sequence_io", "final_evaluation_seconds"))
        stage.append({"subset": r["subset"], "raw_read_share_pct": 100 * float(r["raw_read_seconds"]) / total,
            "preprocessing_share_pct": 100 * float(r["preprocessing_seconds"]) / total,
            "train_share_pct": 100 * float(r["train_seconds_including_sequence_io"]) / total,
            "final_eval_share_pct": 100 * float(r["final_evaluation_seconds"]) / total})
    write_csv("stage_shares", stage)
    write_csv("split_population", split_rows)
    text = f'''# Phân tích bổ sung theo góp ý giảng viên — 24/11/2026

## 1. Mẫu số sampling và dòng chảy dữ liệu

10/25/50/100% là ngưỡng chọn **session ID gốc** trong tuần UTC [01/10/2019, 08/10/2019), sau bỏ session null và chỉ giữ view/cart/purchase. Population là **{population:,} session**, **{baseline['n_events']:,} event**; 100% không phải toàn tháng 42.448.764 dòng. Thuật toán SHA-256(seed 42 + ':' + session ID), lấy 64 bit đầu, ngưỡng floor(p × 2^64/100); cùng hash tạo subset lồng nhau. Các tỷ lệ là kỳ vọng theo session, không phải quota chính xác, user sampling hay event sampling. Seed 42 khác seed GPU split 1. Xem `session_sampling_manifest.json` để tái tạo và checksum membership.

Chọn session rồi giữ toàn bộ eligible event **trong cửa sổ tuần**; sau đó cleanup consecutive repeated product, fit workflow, Groupby, bỏ session <2 interaction, giữ 20 item cuối và chia theo day_index. Vì vậy “giữ nguyên session khi sampling” không có nghĩa model dùng tất cả raw event hoặc event ngoài tuần. Cohort cuối còn bị chọn bởi điều kiện độ dài; phải phân biệt counts raw/clean/model.

{md(rows, ['subset_session_threshold_pct', 'raw_sessions', 'actual_raw_session_pct', 'raw_events', 'actual_raw_event_pct', 'raw_users', 'catalog_items', 'cleaned_events', 'model_sequences'])}

Raw user counts lấy từ `raw_subset_counts.csv`; số sau cleanup dùng profile của đúng cuDF run trong `e2_preprocessing_verified.json`, không lấy profile DuckDB cũ. Counts user có thể giảm khi cleanup loại event; không trộn hai giai đoạn. Bảng CSV đầy đủ có cleaned users/category/brand và catalog coverage. Snapshot counts và phân bố là bằng chứng đủ quy mô để thực thi các run này, chưa có power analysis hay learning-curve convergence để tuyên bố số mẫu tối thiểu bảo đảm.

## 2. Subset có đa dạng và đại diện không?

{md(distribution, ['subset', 'view_pct_clean_events', 'cart_pct_clean_events', 'purchase_pct_clean_events', 'mean_clean_session_length', 'p50_clean_length', 'p90_clean_length', 'p95_clean_length', 'length_TV_vs_100', 'event_TV_vs_100'])}

TV = 0,5 × tổng trị tuyệt đối chênh lệch xác suất; 0 là cùng phân bố ở đặc trưng đang đo. Bảng CSV còn có max gap giữa hai CDF độ dài. TV độ dài lớn nhất là **{max_tv:.6f}** so mức 100%; đây là khoảng cách mô tả, không phải p-value/kiểm định độc lập (các subset lồng nhau). Phân bố độ dài và event type gần nhau là bằng chứng quan sát rằng hash không làm lệch mạnh hai đặc trưng này trong dữ liệu đã cleanup.

Subset 10% có {p['catalog_items']:,}/{baseline['vocabulary_size']:,} item, tương đương **{p['catalog_coverage_of_100_pct']:.2f}% vocabulary** của tuần 100%, dù chỉ có khoảng 10% session. Điều này phản ánh nhiều item được chia sẻ giữa session; không có nghĩa đã bao phủ đầy đủ long tail. Session sampling không chọn đều user: user có nhiều session có cơ hội xuất hiện cao hơn, do đó tỷ lệ user/item không bằng tỷ lệ session. Giữ nguyên record trong session bảo vệ chuỗi hành vi, nhưng session dài vẫn đóng góp nhiều event hơn vào train; metric eval hiện lấy trọng số đều theo session hợp lệ.

Phạm vi đại diện chỉ được hỗ trợ ở **quần thể tuần đầu của dataset này** và các phân bố đã thống kê. Chưa kiểm tra product-frequency/head–tail, brand/category frequency, phân bố theo giờ/ngày hoặc từng nhóm user; distinct counts không thay thế distribution. Chưa có bằng chứng cho đại diện toàn tháng, cửa hàng khác, user mới hoặc production traffic. Không dùng câu “hash bảo đảm đại diện” trong report.

## 3. Mất cân bằng event và tác động của cleanup

{md(event_rows, ['event_type', 'raw_week_count_including_null_session', 'raw_week_pct', 'clean_100_count', 'clean_100_pct'])}

Raw-week audit có {raw_total:,} dòng trước bỏ null session, nhiều hơn population sampling đúng một dòng; bảng trước/sau có scope này, không phải phép đối chiếu từng event. Sau cleanup 100%, view chiếm **{distribution[-1]['view_pct_clean_events']:.4f}%**, cart+purchase chỉ còn {baseline['profile']['event_types']['cart'] + baseline['profile']['event_types']['purchase']:,} event. Chênh lệch rất lớn so raw week cho thấy event mix sau xử lý cần được báo riêng, không chỉ viện dẫn mất cân bằng sẵn có của raw dataset.

Code `pipeline/preprocess_weekly.py` loại consecutive repeated **product_id** trong cùng session, không xét event_type. Vì vậy chuỗi view(A) → cart(A) → purchase(A) có thể bị rút thành một sản phẩm A; event type của dòng được giữ phụ thuộc thứ tự nguồn, nhất là timestamp trùng. Đây là cơ chế có thể làm suy giảm event mua/giỏ sau một lượt xem cùng sản phẩm; chưa audit từng event bị bỏ nên không quy toàn bộ chênh lệch cho một nguyên nhân duy nhất. Quyết định hiện tại giữ preprocessing đã chốt, không cân bằng/oversample từng event làm vỡ session hoặc lặp target.

Baseline chỉ dùng product ID và metric gộp mọi session target. Do đó mục tiêu được đo là next-product trong chuỗi hành vi sau cleanup, chịu ảnh hưởng mạnh của browsing; **không phải purchase prediction, conversion rate hay doanh thu**. Tỷ lệ view trên cleaned events cũng **không phải** tỷ lệ event_type của target cuối tập test: cần join provenance event/target để đo con số đó. Chưa có Recall/NDCG riêng cho view/cart/purchase, nên không tuyên bố hiệu quả mua hàng.

Để kiểm chứng thêm sau này: giữ liên kết event_type của final target khi xử lý sequence, báo support và metric theo từng loại target; audit event type của các dòng bị loại; nếu thử giữ event type trong dedup key phải tạo protocol/artifact/version mới và chạy lại so sánh, không sửa ngược kết quả hiện hành. Đây là đề xuất chưa chạy.

## 4. Selection bias do độ dài và truncation

{md(retention, ['subset', 'event_removed_pct', 'single_interaction_session_pct', 'eligible_sequence_session_pct', 'eligible_sessions_over_20_pct'])}

Ở mức 100%, **{last['single_interaction_session_pct']:.2f}% session** có một interaction sau cleanup và không đi vào model/evaluation. Kết quả vì vậy áp dụng cho multi-interaction sessions, chưa bao phủ single-click/cold-session traffic. Trong các session đủ điều kiện, **{last['eligible_sessions_over_20_pct']:.2f}%** dài hơn 20; chỉ giữ 20 item cuối gồm target, nên đánh giá ưu tiên phần cuối session và không đo lợi ích của toàn lịch sử dài. Counts interactions trước/sau truncation nằm trong `preprocessing_retention.csv`.

Giới hạn này giúp giải thích bài toán và chi phí: chuỗi tối đa 20 làm bounded sequence compute, còn vocabulary và số session vẫn tăng. Không suy từ time/event mà nói mọi độ dài session đều scale tương tự.

## 5. Audit leakage và hiệu lực so sánh

Counts dưới lấy từ split_counts của raw E2 model metrics, không suy ra bằng phép nhân 80/10/10. Ba cột saved là toàn bộ membership đã lưu; các cột used là đúng phần protocol dùng. Với D=7, train 1–6, daily validation 2–7 và final test 7; train D và test trước D không được đưa vào final benchmark. Validation partition 1 vẫn tồn tại nhưng không có train partition 0 để ghép.

{md(split_rows, ['subset', 'saved_train_all_days', 'saved_validation_all_days', 'saved_test_all_days', 'train_used_1_to_Dminus1', 'validation_used_2_to_D', 'final_test_D', 'train_D_not_used'])}

| Điểm | Kiểm soát/giới hạn hiện tại | Kết luận được phép |
| --- | --- | --- |
| Session membership | Gom trước split; train/validation/test không trùng session; giữ hash/counts | Tránh trùng nguyên session; không chứng minh split theo user |
| Mapping/thống kê feature | Fit trên tuần từng subset trước split, gồm holdout; cố định qua partition | Có preprocessing nhìn phân bố holdout; không gọi pipeline train-only hoặc đánh giá online inductive |
| Catalog | Real items từ vocabulary tuần, có item chưa xuất hiện train | Ba model E1 cùng catalog; không loại item khó khỏi test bằng train-only catalog |
| Target | Eval item cuối sau truncation; masking/check last label của runner | Trọng số model không nhận target đó trong prefix dự đoán; không xoá giới hạn preprocessing phía trên |
| Thời gian | day_index theo first timestamp của session; cùng model train t, validation t+1 | Không phải cutoff ngày lịch; session nguyên khối có thể kéo dài qua cutoff, chưa strict event-time replay |
| User | Session-based split, không user-disjoint | Có thể có cùng user ở nhiều split; không tuyên bố new-user generalization |
| First-seen | Min timestamp toàn tháng dùng chung; với item trong tuần, min không muộn hơn lần xuất hiện đó | Không gọi mọi feature là chỉ fit train; kiểm tra invariant first_seen <= event_time, không tự suy rằng min tạo future target |
| Test/freeze | Test partition cuối; config freeze trước test theo protocol/log flags | Log/config cho truy vết, không tự chứng minh mọi quyết định thủ công chưa từng nhìn test |

Đây là đánh giá offline có dùng thông tin phân bố từ toàn tuần ở preprocessing; tách rõ leakage target trực tiếp với quyền truy cập covariate/vocabulary của holdout. Các kiểm soát session/masking không đủ để tuyên bố không có mọi dạng leakage. Với triển khai online cần thiết kế temporal replay/fit preprocessing từ quá khứ và đánh giá lại, không gắn nhãn đó lên số hiện tại.

## 6. E2/E5 trả lời câu hỏi nào của đồ án?

**Câu hỏi chính hiện tại:** khi mở rộng quần thể session trong cùng tuần, chi phí đọc/preprocessing/train/evaluation của pipeline thay đổi thế nào? E2/E5 trả lời được theo số event thực, mapping fit riêng, cùng model/resource config và phạm vi đo đã khai báo. Accuracy giữa các subset chỉ mô tả các kịch bản khác nhau vì train, test, catalog đều đổi; **không xác lập quan hệ nhân quả “chỉ thêm train làm tăng accuracy”**.

Thí nghiệm train-size accuracy sạch hơn (đề xuất, chưa chạy): dùng một split nền được lưu membership; khóa validation/test, catalog và mapping cho mọi mức; trong từng train partition chọn các session train bằng cùng stable hash để tạo các mức lồng nhau, giữ nguyên chuỗi; giữ optimizer/epoch/LR/seed schedule đã công bố; eval trên đúng một tập và catalog cố định. Nếu chọn fit preprocessing train-only phải fit một lần trên train nền và ghi rõ vocabulary có thể dùng thông tin từ các train subset lớn hơn; nếu fit riêng từng mức thì phải giải thích catalog/OOV thay đổi, không gọi chỉ thay train size. Báo actual counts, nhiều seed/repeat nếu đủ tài nguyên. Không đổi protocol E2 hiện hành hoặc thay lại số liệu để giả lập thí nghiệm này.

Theo góp ý cô, nhóm có thể ưu tiên **phân tích chi phí và tài nguyên của pipeline hiện có**, không buộc chạy thêm model phức tạp hay dữ liệu lớn hơn. Việc bổ sung thí nghiệm giữ holdout cố định là quyết định phạm vi riêng, không phải bằng chứng đã có.

## 7. Cơ cấu thời gian và khuyến nghị triển khai có căn cứ

{md(stage, ['subset', 'raw_read_share_pct', 'preprocessing_share_pct', 'train_share_pct', 'final_eval_share_pct'])}

Tỷ trọng trên tổng stage E5 không gồm first-seen; chưa phải CPU/GPU utilization hay whole-job wall. Ở mức nhỏ, ưu tiên tái sử dụng workflow/feature đã fit đúng phiên bản và tránh chạy lại preprocessing không cần thiết; ở mức lớn, train chiếm ưu thế nên batch và số optimizer update là tradeoff có thể kiểm tra từ E3. Không đổi batch giữa E2 vì sẽ phá so sánh data scaling. Parquet giúp storage/read, nhưng read chỉ là một phần nhỏ nên không hứa tốc độ cả pipeline tăng bằng tốc độ đọc.

Việc có VM Ubuntu/Docker/T4 và artifact contract đáp ứng hướng triển khai Big Data/Cloud của nhóm; một máy GPU và pipeline partitioned/streaming **không chứng minh distributed speedup, autoscaling, fault tolerance hoặc cloud rẻ hơn local**. Chưa có cost ledger/utilization/repeated trials cho các kết luận đó. Giá trị của thực nghiệm là pipeline tái lập, phạm vi đo nhất quán, provenance và quyết định kỹ thuật dựa trên bottleneck, không chỉ dung lượng dữ liệu hay độ phức tạp model.

## 8. Kết luận nên dùng khi trình bày

- Trong cùng test/catalog E1, XLNet có metric cao nhất; Popularity có chi phí thấp nhất. Chưa có significance/repeated seed nên dùng “trong các run đã đo”.
- E2/E5 cho thấy chi phí pipeline tăng theo quy mô; bottleneck chuyển từ preprocessing sang train. Accuracy tăng đồng thời là quan sát giữa kịch bản, chưa là isolated train-size gain.
- E3 có tradeoff runtime/accuracy khi đổi batch; không suy từ sampled RSS rằng cấu hình nào tiết kiệm RAM hơn.
- E4 Parquet giảm storage/read, cải thiện full preprocessing ít hơn; warm-cache và chi phí chuyển đổi được tách rõ.
- Tính đại diện được hỗ trợ bởi thống kê quần thể, counts và hai phân bố đã đo; browsing dominance, cleanup, session-length selection, preprocessing fit trước split và một seed là limitations chính.

Nguồn nội bộ: `data/manifests/session_sampling_manifest.json`, `data/manifests/e2_preprocessing_verified.json`, `data/manifests/raw_subset_counts.csv`, `data/raw_audit.csv`, `pipeline/preprocess_weekly.py`, raw E2 logs trong evidence của phân tích chính. Không lấy thống kê tutorial làm số liệu nhóm. Góp ý giảng viên được người dùng cung cấp trong chat; không biến các đề xuất chưa chạy thành kết quả thực nghiệm.
'''
    (OUT / "instructor_feedback_analysis.md").write_text(text, encoding="utf-8")
    paths = [sampling_path, selected_path, raw_path, audit_path, "pipeline/preprocess_weekly.py", str(OUT / "E2.csv")]
    paths += [r["source_metrics"] for r in e2]
    record = {"status": "passed", "scope": "descriptive analysis from existing artifacts; no protocol/rerun change",
              "checks": ["raw/sampling populations", "histogram event and session totals", "eligible sequence counts",
                         "event-type totals", "same-stage distribution comparisons"],
              "sources_sha256": {p: hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in paths}}
    Path("metrics/tv2-analysis-20261124/supplement_validation.json").write_text(json.dumps(record, indent=2) + "\n")
    return text


if __name__ == "__main__":
    generate()
    print("PASS: subset/event/retention and timing-share descriptive supplement generated")
