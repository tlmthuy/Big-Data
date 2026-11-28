# TV4 demo output contract proposal

## 1. Purpose and scope

Approved by TV2 on 24/11/2026 (`docs/handoff.md`, commits `c41f191` and `5a6545e`). Part A defines session predictions. Part B defines run-level results for E1–E5. The demo shows both views and reads artifacts only. Neither view triggers training. Evidence is from `main` at `86bc1c8`. All checked-in model and experiment runs referenced here use toy data.

## 2. Missing data rules

| Case | Adapter value | UI |
| --- | --- | --- |
| Applicable value still pending | `null` | **Chưa có** |
| Inapplicable field | `null` with applicability determined by model or run kind | **Không áp dụng** |
| Failed or excluded run | Status and available reason, with metric values suppressed | Status badge and reason, or **Chưa có** for a pending reason |
| Toy run | `data_kind: "toy"` | Toy badge and exclusion from official benchmark comparisons |

Reserve zero for a value actually reported as zero. Preserve exported ranks and use artifact order for derived rank. Use only scores explicitly exported by TV2, without deriving a score from rank or position. Display metrics as delivered by TV2 without recomputing or redefining them. Keep planned configuration (**Dự kiến**) and actual configuration and measurements (**Thực tế**) separate. E2–E5 results belong in the run-level package.

## Part A — Session prediction

Offline input contains the full ordered sequence, including the held-out final item. The Parquet input has `user_session` and `product_id-list` with partition and split in the path. The debug JSONL input uses `user_session`, `day_index`, `split` and `product_ids`. After right-padding removal, the sequence has 2–20 real items. The model context is the prefix of 1–19 items. Popularity uses a shared ranking based on train interactions. [Session loader](../evaluation/data.py) · [Popularity evaluator](../evaluation/run_popularity.py)

| Field | Source and meaning |
| --- | --- |
| `user_session` | Input key carried into each prediction row. Confirm the production representation with TV1 and TV2. |
| `prefix` | Encoded item IDs in history order, before the held-out item. |
| `target` | Encoded ID of the last real item. |
| `top20` | Ordered list of up to 20 distinct encoded recommendations. |
| `product_ids` | Original IDs aligned with the output `top20` array. |
| `product_id`, `encoded_id` | Original ID and vocabulary index from the exact run catalog. |
| `model`, `run_id` | Model and run identifiers from `metrics.json`. |
| `rank` | Proposed one-based position in the exported recommendations. |
| `target_rank` | Proposed one-based position of the target, or `null` for a known miss. Show the actual next item in either case. |
| `score` | NEED TV2. Both evaluators currently export exactly the five prediction keys above, from `user_session` through `product_ids`. Use `null` until a real per-item score and its meaning are delivered. |

Use the exact catalog for the run and subset, including its SHA-256. Map prefix, target and recommendations to original ID strings and keep the session key for joining. The eligible catalog contains real products from the subset's fitted weekly vocabulary. Previously seen items remain eligible and technical IDs are excluded. Both writers rank ties by ascending encoded ID and the demo preserves their order. Neural scoring stays internal. Popularity is on main. GRU and XLNet GPU smoke runs are on main since `835a09e` and demonstrate the same output shape on toy data. [Neural evaluator](../evaluation/run_neural.py) · [Popularity ranking](../models/popularity.py) · [GPU smoke evidence](../metrics/tv2-model-smoke/README.md)

The following proposed adapter excerpt shows one session from the toy fixture with an abbreviated catalog and recommendation list. The full payload retains the existing fixture keys and aligned arrays.

```json
{
  "model": "Popularity",
  "subset": "toy",
  "split": "validation",
  "run_id": "tv2-toy-day1",
  "data_kind": "toy",
  "catalog_sha256": "a1ae9388c355a4f5dcdacd52f87b521351caac4c69119b2e17b87d7dc467c184",
  "catalog": ["p3", "p4"],
  "sessions": [
    {
      "user_session": "rank1",
      "prefix": ["p4"],
      "target": "p3",
      "top20": ["p3", "p4"],
      "target_rank": 1,
      "recommendations": [
        {"rank": 1, "product_id": "p3", "score": null},
        {"rank": 2, "product_id": "p4", "score": null}
      ]
    }
  ]
}
```

## Part B — Run results (E1–E5)

### B1. Sources

- E1–E3 model runs use `run.json`, `stdout.txt`, `stderr.txt`, `artifacts/metrics.json` and `artifacts/predictions.jsonl`. Predictions feed Part A. Collector metadata links the environment and input artifacts with paths and hashes. Failed runs may have only the collector record and logs. [Collector](../benchmark/collect.py) · [Toy run example](../metrics/tv2-config-collector-smoke/smoke-e1-gru-010/run.json)
- E4 uses `artifacts/metrics.json` from the format benchmark, the collector record and logs, and the nested preprocessing record. [Format benchmark](../benchmark/format_io.py)
- E5 uses `summary.json` derived from passed E2 runs. Its rows retain source run IDs and `source_log`. Display the approved stages and limitations from the same package. [Scalability summary writer](../benchmark/scalability.py)

### B2. Run identity

| Field | Source or rule |
| --- | --- |
| `experiment` | `run.json` → `metadata.run.experiment`. E5 is the summary panel for source E2 runs. |
| `run_id` | Collector `metadata.run.run_id`, checked against the result artifact. E5 retains E2 run IDs. |
| `model` | Matrix model for the planned run and `metrics.json.model` for model runs. E4 has no model. |
| `status` | Collector `passed` or `failed`. Preserve E4 artifact status and E5 summary completeness separately. `excluded` is a proposed TV2 package status. |
| `data_kind` | Collector `metadata.data_kind` (`toy` or `real`). |
| `exclusion_note` | NEED TV2. Proposed exclusion reason supplied by TV2. For failures use the available failure information from the collector and logs. |

### B3. Planned and actual configuration

For model runs, actual sources below refer to `artifacts/metrics.json` unless qualified. E4 uses the format benchmark artifact. Flag discrepancies beside the two values and retain provenance. Keep unavailable actual fields `null` until supported by the artifact or confirmed package.

| Field | Planned source | Actual source | Unit |
| --- | --- | --- | --- |
| Train batch | Matrix `batch_size` | Neural `config.batch_size` | sessions/batch |
| Eval batch | Runner passes `--eval-batch-size 32` for neural runs. The matrix has no eval batch field. | Neural `config.eval_batch_size` | sessions/batch |
| Epochs | Matrix `epochs` | Neural `config.epochs` | epochs/train partition |
| Sequence length | Matrix `sequence_length` | Metrics have no sequence-length field. NEED TV2 verified runtime value. | items |
| Seed | Matrix `seed` | Neural `config.seed` | integer |
| Learning rate | Matrix has no field | Neural `config.learning_rate` | scalar |
| Subset | Matrix `subset` | Top-level `subset` for model runs. E4 requires package provenance. | % of sessions or toy label |
| Split | Matrix `split` | `eval_split` | label |
| Train partitions | Matrix `train_partitions` | `train_days` | day indices |
| Eval partition | Matrix `eval_partition` | `eval_day` | day index |
| Input format | Matrix `input_format` | E4 `format`. For model runs the runner enforces a session Parquet directory and records the session artifact. | label |
| Device / varied parameter | Matrix `resource_config.device` / `resource_config.change_only` | Neural `device`. The varied parameter is a planned constraint, with actual values shown from each run. | labels |
| Data versions | Matrix `artifact_versions` | Collector `metadata.versions` and `metadata.artifacts` fingerprints | versions and SHA-256 |

[Experiment matrix](../configs/experiments.json) · [Runner](../scripts/runs/run_experiments.py) · [Neural metrics example](../metrics/tv2-config-collector-smoke/smoke-e3-gru-010-b32/artifacts/metrics.json)

### B4. Environment

Join each run to its fingerprinted environment snapshot via `metadata.environment`. The toy snapshot provides `gpu`, `cuda`, `driver`, `python` and `torch`. Neural metrics also record `gpu`, `cuda`, `python` and package versions in `packages`. Popularity metrics record `platform`. CPU model, core count, total RAM and OS across all runs need TV3. Keep the fields tied to the specific run environment. [GPU smoke snapshot](../metrics/tv2-model-smoke/environment.json)

### B5. Metrics by experiment

| Metric | Field | Unit | Measurement scope | Experiments |
| --- | --- | --- | --- | --- |
| Ranking accuracy | `Recall@20`, `NDCG@20` | ratios | Evaluated sessions in the reported split and partition | E1–E3 |
| Training time | `train_with_input_scan_seconds` | s | Training stages including input scan | E1–E3 |
| Evaluation wall time | `inference_seconds` | s | `full_evaluation_wall_v1`. Full split read, preparation, prediction and ranking, metrics aggregation and JSONL write. Excludes audit, training, checkpointing and metrics JSON write. | E1–E3 |
| Evaluation time per session | `inference_ms_per_session` | ms/session | Full evaluation wall time normalized by evaluated sessions, including I/O | E1–E3 |
| Evaluation throughput | `inference_sessions_per_second` | sessions/s | Full evaluation wall throughput. NEED TV2 for the official E3 throughput definition. | E1–E3 |
| Collector wall time | `elapsed_seconds` | s | Whole launched command in `run.json` | E1–E4 |
| Peak process RSS | `peak_process_tree_rss_bytes` | bytes | Sampled sum of parent and child RSS. Shared pages may be counted twice. | E1–E4 |
| Peak CUDA reserved memory | `peak_cuda_reserved_bytes` | bytes | Peak PyTorch CUDA allocator reservation for the neural run | E1–E3 neural runs |
| Weekly sampled events | `metadata.pipeline_metrics.n_events` | events | Actual event count in the sampled raw weekly subset | E2 |
| Pipeline read and preprocessing | `read_seconds`, `preprocessing_seconds`, `first_seen_seconds` in `metadata.pipeline_metrics` | s | Separate TV1 raw read, subset preprocessing excluding raw read and first-seen, and shared monthly first-seen | E2 |
| Subset counts and dataset size | NEED TV1/TV2 | sessions, users, items, bytes | Per-subset counts and artifact size with agreed scope | E2 |
| Cost | **Chưa có** | NEED TV2 | Measurement availability and scope pending TV2 | E3 |
| File size | `bytes` | bytes | Input file size | E4 |
| Read wall time | `read_seconds` | s | Full streamed decode, excluding pair verification. Show cache and schema policies from the result. | E4 |
| Peak reader RSS | `peak_read_process_rss_bytes` | bytes | RSS sampled at batch boundaries, including existing reader/cache allocations | E4 |
| Preprocessing wall time | `preprocessing.elapsed_seconds` | s | TV1 preprocessing command including its input read | E4 |
| Normalized scalability time | `seconds_per_million_events` | s/million events | Composed stages excluding shared first-seen, normalized by measured weekly events | E5 |
| Slowest stage | `bottleneck` | stage name | Largest included stage in the E5 composition | E5 |
| Stage timings | `raw_read`, `preprocessing_excluding_raw_read_and_first_seen`, `train_including_sequence_io`, `final_evaluation_including_io` | s | Composed E2 stage measurements with distinct input scopes | E5 |
| Composed and observed timings | `composed_seconds_excluding_first_seen`, `first_seen_seconds_shared`, `composed_seconds_with_first_seen`, `process_wall_seconds` | s | Composed stage totals, shared monthly cost and observed model process wall time | E5 |
| Uncertainty | `limitations` | text | One run per subset. NEED TV2 decision on numeric uncertainty. | E5 |

Evaluation wall timing includes I/O and aggregation. `prediction_compute_seconds` is diagnostic only and excluded from comparisons. The E5 writer consumes `inference_seconds` for `final_evaluation_including_io`, while its current limitations text describes compute and ranking only. TV2 must confirm the final scope and limitations text before publication. [Timing protocol](../docs/modeling/inference_timing.md) · [Pipeline metrics template](../configs/pipeline_metrics.example.json) · [E5 writer](../benchmark/scalability.py)

### B6. E3 comparison

Show `e3-gru-010-b32` and `e3-gru-010-b128` side by side. Both plan GRU on the 10% subset, validation split and eval batch 32. Train batch is the selected variable (32 vs 128). The view reads approved artifacts without rerunning training. [Experiment matrix](../configs/experiments.json) · [Runner](../scripts/runs/run_experiments.py)

### B7. Proposed run-results adapter

Example shape for `app/public/run-results.json`. This excerpt shows both planned E3 configurations with null measurements. Metric entries carry value, unit and scope, and source entries point to the records supporting them.

```json
{
  "package_id": null,
  "confirmed_by_tv2": false,
  "runs": [
    {
      "experiment": "E3",
      "run_id": "e3-gru-010-b32",
      "model": "gru",
      "status": null,
      "data_kind": null,
      "exclusion_note": null,
      "planned": {
        "train_batch_size": 32, "eval_batch_size": 32, "epochs": 3,
        "sequence_length": 20, "seed": 1, "learning_rate": null,
        "subset": "10", "split": "validation", "train_partitions": "1..D-1",
        "eval_partition": "D", "input_format": "session Parquet",
        "device": "cuda", "change_only": "train_batch_size",
        "artifact_versions": "site.subsets.10.workflow_version/mapping_version/catalog_version"
      },
      "actual": {
        "train_batch_size": null, "eval_batch_size": null, "epochs": null,
        "sequence_length": null, "seed": null, "learning_rate": null,
        "subset": null, "split": null, "train_partitions": null,
        "eval_partition": null, "input_format": null, "device": null, "artifact_versions": null
      },
      "environment": {
        "gpu": null, "cuda": null, "driver": null, "python": null, "torch": null,
        "cpu_model": null, "cpu_cores": null, "ram_bytes": null, "os": null
      },
      "metrics": {
        "inference_seconds": {"value": null, "unit": "s", "scope": "full_evaluation_wall_v1"},
        "cost": {"value": null, "unit": null, "scope": null}
      },
      "sources": {"matrix": "configs/experiments.json", "runner": "scripts/runs/run_experiments.py", "run": null, "metrics": null, "environment": null}
    },
    {
      "experiment": "E3",
      "run_id": "e3-gru-010-b128",
      "model": "gru",
      "status": null,
      "data_kind": null,
      "exclusion_note": null,
      "planned": {
        "train_batch_size": 128, "eval_batch_size": 32, "epochs": 3,
        "sequence_length": 20, "seed": 1, "learning_rate": null,
        "subset": "10", "split": "validation", "train_partitions": "1..D-1",
        "eval_partition": "D", "input_format": "session Parquet",
        "device": "cuda", "change_only": "train_batch_size",
        "artifact_versions": "site.subsets.10.workflow_version/mapping_version/catalog_version"
      },
      "actual": {
        "train_batch_size": null, "eval_batch_size": null, "epochs": null,
        "sequence_length": null, "seed": null, "learning_rate": null,
        "subset": null, "split": null, "train_partitions": null,
        "eval_partition": null, "input_format": null, "device": null, "artifact_versions": null
      },
      "environment": {
        "gpu": null, "cuda": null, "driver": null, "python": null, "torch": null,
        "cpu_model": null, "cpu_cores": null, "ram_bytes": null, "os": null
      },
      "metrics": {
        "inference_seconds": {"value": null, "unit": "s", "scope": "full_evaluation_wall_v1"},
        "cost": {"value": null, "unit": null, "scope": null}
      },
      "sources": {"matrix": "configs/experiments.json", "runner": "scripts/runs/run_experiments.py", "run": null, "metrics": null, "environment": null}
    }
  ]
}
```

### B8. UI layout

- **Recommendation** shows a session picker, model selector, history, actual next item and Top-20 with rank and score. Show **Chưa có** for an undelivered score, and display the run ID and toy badge where applicable.
- **Experiments** has one panel each for E1 model comparison, E2 subset scaling, E3 train-batch comparison, E4 CSV/Parquet and E5 scalability. Each panel presents **Dự kiến** and **Thực tế**, the run environment, source run IDs and measurement scope. E5 uses its source E2 records for configuration and environment.

## Dependencies

| # | Item | Owner | Needed for | Current state |
| --- | --- | --- | --- | --- |
| 1 | Approve this contract, formats, field names, run-results shape and offline vs live inference scope | TV2 | Adapter and UI integration | Proposed read-only artifact workflow |
| 2 | Export actual per-item scores and define their meaning for each model | TV2 | Recommendation score column | Both writers currently export ranked IDs |
| 3 | Deliver confirmed predictions and catalog for all three models on a shared subset and split, with the matching ID mapping | TV2 (predictions, catalog), TV1 (mapping support) | Comparable recommendations | Toy artifacts available |
| 4 | Define the production session key and supply its mapping | TV2, TV1 | Session join and picker | Production representation pending |
| 5 | Deliver official E1–E5 metrics and identify excluded runs and reasons | TV2 | Experiment panels | Matrix and toy evidence available |
| 6 | Confirm the effective eval batch and sequence length for E1, E2 and E3 neural runs | TV2 | Configuration and comparison | Runner passes eval batch 32. Matrix plans sequence length 20, but `metrics.json` has no sequence-length field. |
| 7 | Confirm E3 throughput definition and cost coverage | TV2 | E3 comparison | Evaluation throughput field available. Cost is **Chưa có**. |
| 8 | Decide on numeric E5 uncertainty and align the E5 inference-scope text with `full_evaluation_wall_v1` | TV2 | E5 interpretation | `limitations` text says compute/ranking only, while `final_evaluation_including_io` uses full evaluation wall time. No variance or confidence interval measured. |
| 9 | Provide CPU model, core count, RAM and OS for every run | TV3 | Environment view | Partial toy snapshot available |
| 10 | Provide real resource logs linked to run IDs | TV3 | Runtime and memory comparisons | Toy logs available |
| 11 | Provide measured per-subset pipeline metrics (`n_events`, `read_seconds`, `preprocessing_seconds`, `first_seen_seconds`, `first_seen_artifact`, `source_log`), plus session, user and item counts and bytes with scope agreed by TV2 | TV1, TV2 (scope) | E2 scale and E5 inputs | Template only. All values are `null`. No count or bytes fields for sessions, users or items. |

## References

- [Project scope](../AGENTS.md) · [Demo fixture](public/demo-data.json) · [TV2 experiment runbook](../docs/modeling/experiment_runbook.md) · [Toy collector evidence](../metrics/tv2-config-collector-smoke/README.md)
- [NVIDIA tutorial](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html) · [Pinned source and license](../docs/references.md)

## Read-only toy verification

Run from the repository root. This checks existing files and prints the target's rank for each session.

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

from evaluation.data import Catalog, read_sessions

fixture = Path("evaluation/tests/fixtures")
run = Path("metrics/tv2-toy-day1")
catalog_path = fixture / "catalog.json"
sessions_path = fixture / "sessions.jsonl"
catalog = Catalog.load(catalog_path)
metadata = json.loads((run / "metrics.json").read_text())
assert metadata["K"] == 20
assert metadata["model"] == "Popularity"
assert metadata["run_id"] == run.name
for key, path in (("catalog", catalog_path), ("sessions", sessions_path)):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["artifacts"][key]["sha256"]
sessions = {
    row["user_session"]: catalog.sequence(row["product_ids"])
    for row in read_sessions(sessions_path)
    if row["day_index"] == metadata["eval_day"] and row["split"] == metadata["eval_split"]
}
rows = [json.loads(line) for line in (run / "predictions.jsonl").read_text().splitlines()]
counts = json.loads((run / "popularity.json").read_text())["counts"]
expected = sorted(catalog.products, key=lambda item: (-counts.get(str(item), 0), item))[:20]
assert len(rows) == len(sessions) == metadata["n_sessions"]
assert {row["user_session"] for row in rows} == sessions.keys()
for row in rows:
    assert row.keys() == {"user_session", "prefix", "target", "top20", "product_ids"}
    session, prefix, target, top20, product_ids = (
        row[key] for key in ("user_session", "prefix", "target", "top20", "product_ids")
    )
    assert isinstance(session, str) and type(target) is int
    assert all(type(item) is int for item in prefix + top20)
    assert prefix + [target] == sessions[session]
    assert top20 == expected and not set(top20) & catalog.technical_ids
    assert product_ids == [catalog.products[item] for item in top20]
    rank = top20.index(target) + 1 if target in top20 else "miss"
    print(session, catalog.products[target], rank)
demo = json.loads(Path("app/public/demo-data.json").read_text())
assert demo["catalog"] == list(catalog.products.values())
assert len(demo["sessions"]) == len(rows)
for row, session in zip(rows, demo["sessions"]):
    assert session["user_session"] == row["user_session"]
    assert session["prefix"] == [catalog.products[item] for item in row["prefix"]]
    assert session["target"] == catalog.products[row["target"]]
    assert session["top20"] == row["product_ids"]
print("Catalog sizes", len(catalog.products), len(demo["catalog"]))
PY
```
