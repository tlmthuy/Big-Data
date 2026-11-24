"""Reproduce TV2 tables and analysis from the archived raw JSON evidence."""

import csv
import hashlib
import json
from pathlib import Path

from benchmark.scalability import summarize, write_outputs

BASE = Path("metrics/tv2-analysis-20261124")
RAW = BASE / "evidence/Big-Data/metrics/raw"
E4 = BASE / "evidence/Big-Data-e4/metrics/raw"
TABLES = Path("reports/tables/tv2-20261124")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def table(name, rows):
    path = TABLES / (name + ".csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def model_row(run_id):
    directory = RAW / run_id
    run, metrics = load(directory / "run.json"), load(directory / "artifacts/metrics.json")
    assert run["status"] == "passed" and run["exit_code"] == 0
    assert run_id == run["metadata"]["run"]["run_id"] == metrics["run_id"]
    assert metrics["inference_timing_protocol"] == "full_evaluation_wall_v1"
    assert metrics["train_days"] == list(range(1, metrics["eval_day"]))
    assert metrics["K"] == 20
    assert metrics["subset"] == "10" or run_id.startswith("e2-")
    return {"run_id": run_id, "model": metrics["model"], "subset": metrics["subset"],
            "split": metrics["eval_split"], "n_sessions": metrics["n_sessions"],
            "Recall@20": metrics["Recall@20"], "NDCG@20": metrics["NDCG@20"],
            "train_seconds_including_sequence_io": metrics["train_with_input_scan_seconds"],
            "final_evaluation_seconds": metrics["inference_seconds"],
            "eval_ms_per_session": 1000 * metrics["inference_seconds"] / metrics["n_sessions"],
            "process_wall_seconds": run["elapsed_seconds"],
            "sampled_rss_bytes_descriptive_only": run["peak_process_tree_rss_bytes"],
            "sampled_gpu_process_bytes": run.get("gpu_memory_bytes_peak"),
            "sampled_gpu_status": run.get("gpu_memory_bytes_status"),
            "source_run": (directory / "run.json").as_posix(),
            "source_metrics": (directory / "artifacts/metrics.json").as_posix()}


def markdown(rows, columns):
    def fmt(value):
        return f"{value:.6f}" if isinstance(value, float) else str(value)
    return ("| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) +
            " |\n" + "\n".join("| " + " | ".join(fmt(r[c]) for c in columns) + " |" for r in rows))


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    for entry in load(BASE / "source_manifest.json"):
        path = BASE / "evidence" / entry["workspace"] / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], path
    checks = {r["run_id"]: r for r in load(BASE / "prediction_checks.json")}
    e1 = [model_row("e1-" + name + "-010") for name in ["popularity", "gru", "xlnet"]]
    e2 = []
    for subset in ["010", "025", "050", "100"]:
        row = model_row("e2-gru-" + subset)
        meta = load(RAW / row["run_id"] / "run.json")["metadata"]
        timing = meta["pipeline_metrics"]
        row.update(n_events=timing["n_events"], raw_read_seconds=timing["read_seconds"],
                   preprocessing_seconds=timing["preprocessing_seconds"],
                   first_seen_shared_seconds=timing["first_seen_seconds"])
        selected = next(r for r in load("data/manifests/e2_preprocessing_verified.json")["runs"]
                        if str(r["subset"]) == row["subset"])
        assert selected["n_events"] == row["n_events"]
        row.update(total_sequence_sessions=selected["sequence_count"],
                   vocabulary_items=selected["vocabulary_size"],
                   raw_week_users=selected["profile"]["distinct"]["user_id"])
        e2.append(row)
    e3 = [model_row("e3-gru-010-b" + str(batch)) | {"train_batch_size": batch}
          for batch in [32, 128]]
    a, b = [load(r["source_metrics"]) for r in e3]
    assert a["artifacts"] == b["artifacts"] and a["source_sha256"] == b["source_sha256"]
    assert {k for k in a["config"] if a["config"][k] != b["config"][k]} == {"batch_size", "run_id", "output"}
    for row in e1 + e2 + e3:
        check = checks[row["run_id"]]
        assert check["status"] == "passed" and check["sessions"] == row["n_sessions"]
        assert abs(check["recall_recomputed"] - row["Recall@20"]) < 1e-12
        assert abs(check["ndcg_recomputed"] - row["NDCG@20"]) < 1e-12
    # E1 must share persisted session/catalog membership and evaluation split.
    signatures = []
    for row in e1:
        m = load(row["source_metrics"])
        signatures.append((m["artifacts"]["sessions"], m["artifacts"]["catalog"], m["split_counts"]))
    assert all(s == signatures[0] for s in signatures)
    e4 = []
    verification = []
    for format_name in ["csv", "parquet"]:
        path = E4 / ("e4-full-010-" + format_name) / "metrics.json"
        m = load(path)
        assert m["status"] == m["preprocessing"]["status"] == "passed"
        assert m["n_events"] == 882808
        verification.append(m["verification"])
        e4.append({"run_id": m["run_id"], "format": format_name, "n_events": m["n_events"],
                   "bytes": m["bytes"], "read_seconds": m["read_seconds"],
                   "preprocessing_wall_seconds_including_read": m["preprocessing"]["elapsed_seconds"],
                   "sampled_rss_bytes_descriptive_only": m["preprocessing"]["peak_process_tree_rss_bytes"],
                   "source_metrics": path.as_posix()})
    assert verification[0] == verification[1]
    e5 = summarize(RAW)
    for row in e5:
        row["source_log"] = row["source_log"].replace("\\", "/")
    output = Path("reports/figures/tv2-20261124/scalability")
    if output.exists():
        assert load(output / "summary.json")["rows"] == e5, "Existing E5 output differs; preserve it and choose a new version"
    else:
        write_outputs(e5, output)
    # PNG is optional for report embedding; the standalone SVG always exists.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None
    if plt is not None:
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        xs = [r["n_events"] / 1e6 for r in e5]
        ys = [r["composed_seconds_excluding_first_seen"] for r in e5]
        ax.plot(xs, ys, "o-")
        for index, (x, y, r) in enumerate(zip(xs, ys, e5)):
            last = index == len(e5) - 1
            ax.annotate(r["subset"] + "% sessions", (x, y),
                        xytext=(-8 if last else 5, 8), textcoords="offset points",
                        ha="right" if last else "left")
        ax.set(xlabel="Weekly events (millions)", ylabel="Composed stage time (seconds)",
               title="E5 — GRU scaling; shared first-seen excluded")
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(output / "scalability.png", dpi=160)
        plt.close(fig)
    for name, rows in [("E1", e1), ("E2", e2), ("E3", e3), ("E4", e4), ("E5", e5)]:
        table(name, rows)
    x = e2[-1]["n_events"] / e2[0]["n_events"]
    y = e5[-1]["composed_seconds_excluding_first_seen"] / e5[0]["composed_seconds_excluding_first_seen"]
    improvement = (e1[2]["Recall@20"] / e1[0]["Recall@20"] - 1) * 100
    batch_wall = e3[0]["process_wall_seconds"] / e3[1]["process_wall_seconds"]
    size_ratio, read_ratio = e4[0]["bytes"] / e4[1]["bytes"], e4[0]["read_seconds"] / e4[1]["read_seconds"]
    text = f'''# TV2 — Phân tích kết quả E1–E5 — 24/11/2026

Nguồn tính toán: bản sao raw JSON từ VM, không lấy số từ các summary TV3 làm đầu vào. Danh mục file/SHA-256 tại `metrics/tv2-analysis-20261124/source_manifest.json`; 9 predictions files được tính lại metric trực tiếp trên VM, kiểm tra session không trùng và Top-20 unique/không token 0/1/2. Kết quả tại `prediction_checks.json`. Tất cả số dưới là một lần chạy/config, seed 1; không có mean/std qua các lần lặp.

Lệnh tái tạo: `python -m scripts.analyze_results` từ root, trên output path mới hoặc lưu trữ output cũ trước khi chạy lại. CSV đầy đủ ở `reports/tables/tv2-20261124/`; có run_id và source path. Biểu đồ SVG/CSV/JSON tại `reports/figures/tv2-20261124/scalability/`.

## E1 — So sánh model

Subset 10%, train partitions 1–6, test partition 7, 1.337 session; kiểm tra cùng session/catalog fingerprints và split counts. K=20, cho phép seen items. Thời gian inference là wall toàn evaluation, gồm input/output/metric, không phải forward latency thuần.

{markdown(e1, ['run_id', 'Recall@20', 'NDCG@20', 'train_seconds_including_sequence_io', 'final_evaluation_seconds', 'eval_ms_per_session'])}

XLNet có Recall/NDCG cao nhất trong ba run; Recall tăng {improvement:.2f}% tương đối so Popularity. GRU chỉ nhỉnh hơn Popularity trên test này. Popularity có train/evaluation wall thấp nhất. Chênh lệch accuracy chưa có kiểm định hoặc nhiều seed; không kết luận ưu thế tổng quát. Không so inference với ranking một lần hoặc compute diagnostic. Train của neural gồm daily validation ngoài trường train_seconds; process_wall là số riêng bao gồm audit/khởi tạo/checkpoint.

## E2 — Tăng dữ liệu

GRU, train batch 256, eval batch 32, 3 epoch/partition, learning rate 0.00071 và seed 1 cố định; workflow/catalog fit riêng mỗi subset.

{markdown(e2, ['run_id', 'n_events', 'n_sessions', 'Recall@20', 'NDCG@20', 'raw_read_seconds', 'preprocessing_seconds', 'train_seconds_including_sequence_io', 'final_evaluation_seconds'])}

Accuracy tăng theo mức dữ liệu trong các run này. Các tập test và catalog khác nhau giữa subset, nên đây là kết quả từng kịch bản, chưa cô lập hoàn toàn tác động training data trên một test set cố định. Tỷ lệ subset là tỷ lệ session được sampling; event count là số đo thực. Chi phí first-seen tháng {e2[0]['first_seen_shared_seconds']:.6f}s dùng chung được tách riêng.

## E3 — Batch train 32 và 128

Giữ cùng GRU/subset 10%, validation partition 7 gồm 1.324 session; eval batch 32 cố định. Không đặt accuracy validation E3 cạnh test E1 để chọn model tốt nhất.

{markdown(e3, ['run_id', 'train_batch_size', 'Recall@20', 'NDCG@20', 'train_seconds_including_sequence_io', 'process_wall_seconds', 'final_evaluation_seconds'])}

Batch 128 có process wall nhanh hơn khoảng {batch_wall:.2f} lần nhưng Recall/NDCG thấp hơn batch 32. Cùng epoch nhưng số optimizer updates khác nhau nên có tradeoff accuracy/runtime; chưa khẳng định batch lớn luôn tốt hơn. Inference gần nhau vì eval batch không đổi. RSS chỉ mô tả quan sát, không dùng để suy luận tiết kiệm RAM.

## E4 — CSV và Parquet

Cặp full raw subset 10%, 882.808 event, chín cột string và multiplicity-sensitive fingerprint bằng nhau; cùng entrypoint preprocessing/first-seen. Chọn full rerun, loại cặp smoke 19.692 event khỏi bảng chính thức.

{markdown(e4, ['run_id', 'bytes', 'read_seconds', 'preprocessing_wall_seconds_including_read'])}

Parquet nhỏ hơn {size_ratio:.2f} lần, timed read nhanh hơn {read_ratio:.2f} lần trong lần đo này. Toàn preprocessing chênh ít hơn nhiều: còn gồm parse/cleanup/fit/groupby/split/write, nên lợi ích read không chuyển nguyên vẹn thành tốc độ cả pipeline. Cache ấm sau verification; conversion/verification ngoài timed read. Preprocessing wall đã gồm lần đọc của pipeline, không cộng thêm standalone read. Chưa có nhiều lần lặp hoặc cold-cache benchmark.

## E5 — Scaling và bottleneck

Tái tính trực tiếp từ bốn successful E2 run bằng `benchmark.scalability`; kiểm tra config hiệu lực/code/environment và không checkpoint replay. Đây là tổng stage ghép: raw_read + preprocessing không gồm raw_read/first-seen + train gồm sequence I/O + final evaluation gồm I/O; không phải wall một process end-to-end. Daily validation/audit/khởi tạo/checkpoint không được gọi là đã bao phủ trong tổng stage.

{markdown(e5, ['run_id', 'n_events', 'composed_seconds_excluding_first_seen', 'seconds_per_million_events', 'bottleneck'])}

![Scaling curve](../../figures/tv2-20261124/scalability/scalability.svg)

Event tăng {x:.2f} lần, tổng stage không gồm first-seen tăng {y:.2f} lần từ 10% tới 100%. Bottleneck 10% là preprocessing; 25–100% là train gồm sequence I/O. Runtime trên triệu event giảm trong miền khảo sát, phản ánh amortization chi phí cố định; chưa suy ra linearity/asymptotic scaling hoặc hiệu năng ngoài 100%. First-seen được cộng đúng một lần cho từng kịch bản nếu báo tổng có chi phí chung.

## Limitations và phạm vi sử dụng

- Một run/mức, một seed: không có độ lệch chuẩn/confidence interval; không tự tạo mean/std từ session hoặc từ run config khác.
- Preprocessing fit trước split trên tuần mỗi subset theo protocol; đây là offline evaluation, không tuyên bố toàn bộ pipeline train-only. Test không dùng cập nhật model.
- RSS là peak quan sát qua lấy mẫu cây process, có thể đếm trùng shared pages. Truy vấn GPU đồng bộ có thể làm gap vượt 50 ms và bỏ lỡ đỉnh ngắn; không dùng các số này để kết luận RAM khác nhau. Muốn kết luận cần sampler độc lập và rerun liên quan.
- GPU memory sampled, peak CUDA allocated/reserved và total GPU used có scope khác nhau; không hoán đổi. Một GPU Tesla T4, VM 8 vCPU/31 GiB, Docker Merlin; không có kết luận cross-hardware hoặc cost vì chưa có nguồn giá/chi phí đã đo.
- Không warmup riêng, không flush OS cache; E4 cache ấm sau pair verification. Timing thể hiện điều kiện lần chạy, chưa phải SLA latency.
- Chỉ so model trong E1, batch trong E3; E2 thay cả train/eval/catalog. E4 là format raw và preprocessing, không phải tốc độ inference model.
- Gói này hoàn thành phân tích từ logs được kiểm tra; việc bàn giao metrics package chính thức cho TV4/TV5 và người nhận nghiệm thu là task tiếp theo, không tự xác nhận thay người nhận.
'''
    Path("reports/tables/tv2-20261124/analysis.md").write_text(text, encoding="utf-8")
    (BASE / "analysis_validation.json").write_text(json.dumps({
        "status": "passed", "source_checksum_files": len(load(BASE / "source_manifest.json")),
        "model_prediction_checks": len(checks), "E1_shared_artifacts": True,
        "E4_full_pair_verified": True, "E5_recomputed_subsets": len(e5),
        "source": "raw VM run/metrics JSON, not TV3 summaries"}, indent=2) + "\n")
    print("PASS: raw evidence validation; E1-E5 CSV, analysis and scaling curve generated")


if __name__ == "__main__":
    main()
