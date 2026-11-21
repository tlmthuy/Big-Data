# E1–E5 metric and table structure for the report (TV5 task 20/11)

Purpose: list, for every experiment, which **runs (run_id)**, **metrics**, **units** and **source logs/fields** the
report needs, so the tables can be built directly from the TV2 metrics package and every number is traceable.

Built from (`main`, 20/11/2026): `docs/experiment_matrix.md`, `configs/experiments.json` (11 planned runs),
`benchmark/collect.py` (`run.json`), `evaluation/run_neural.py` / `run_popularity.py` (`metrics.json`),
`benchmark/format_io.py` (E4), `benchmark/scalability.py` (E5), `docs/modeling/inference_timing.md`, and the
toy record `metrics/tv2-config-collector-smoke/` (used **only** to read field names — toy values are never reported).

Status: **structure only, no values.** Fill only from the official TV2 package; values from toy runs
(`metadata.data_kind = "toy"`) are excluded.

---

## 1. Where the numbers live (per run)

Every run writes to `metrics/raw/<run_id>/` (planned `output_path` in `configs/experiments.json`):

| File | Written by | Contains |
| --- | --- | --- |
| `run.json` | benchmark collector (TV3 runs it) | run config (`metadata.run.*`), versions, artifact checksums, environment ref, `pipeline_metrics`, `status`, `exit_code`, `elapsed_seconds`, `peak_process_tree_rss_bytes`, start/finish time, git commit |
| `stdout.txt`, `stderr.txt` | collector | raw console log (source log for captions; error evidence for failed runs) |
| `artifacts/metrics.json` | model / format scripts | accuracy and timing metrics (model runs) or file/read metrics (E4) |
| `artifacts/predictions.jsonl` | model scripts | per-session top-20 (used by the demo, not by tables) |
| `reports/e5/summary.json`, `scalability.csv`, `scalability.svg` | `python -m benchmark.scalability --logs metrics/raw --output reports/e5` | E5 rows derived from passed E2 runs |

Every table row must carry: `run_id`, `status` (`passed` / `failed` / excluded), `data_kind` = `real`, and the source
path above.

## 2. Planned runs (from `configs/experiments.json`)

| Experiment | run_id | Model | Subset | Split evaluated | Changed variable | Fixed |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | `e1-popularity-010` | Popularity | 10% | test (partition D) | model | train 1…D−1; no batch/epoch/seed (counting only); split seed 1 belongs to the membership, not the model |
| E1 | `e1-gru-010` | GRU | 10% | test D | model | batch 256, 3 epochs |
| E1 | `e1-xlnet-010` | XLNet | 10% | test D | model | batch 256, 3 epochs |
| E2 | `e2-gru-010` / `-025` / `-050` / `-100` | GRU | 10/25/50/100% | test D | subset size | batch 256, 3 epochs |
| E3 | `e3-gru-010-b32` / `e3-gru-010-b128` | GRU | 10% | **validation** D | `train_batch_size` 32 vs 128 | 3 epochs, seq len 20, eval batch 32 |
| E4 | `e4-010-csv` / `e4-010-parquet` | — (I/O) | raw 10% | — | input format | same 9 columns, same rows |
| E5 | — (derived from the four E2 runs) | GRU | 10–100% | — | — | no new runs |

Note for captions: E1/E2 report the **test** partition D; E3 reports **validation** D — do not put them in the same
accuracy table.

## 3. Metrics needed, with unit and source field

Display unit = what the report shows; raw unit = what the file stores. **Unit convention:** memory and file sizes
are shown in binary units and labelled **MiB / GiB** (1 GiB = 1024³ bytes), stated once in 4.2.2. Always name which
memory is reported: *peak process-tree RSS* (CPU, sampled), *peak CUDA reserved* (GPU), or *peak reader RSS* (E4).
Exception: the raw CSV size in 1.1 / 2.1 (5,668,612,855 bytes) is quoted as "5.67 GB" (decimal) — write "(10⁹ bytes)"
once, or convert to 5.28 GiB for consistency.

### Table ID map (same IDs as `reports/report_outline.md`)

| Table | Content | Source type |
| --- | --- | --- |
| Assignment table (front matter) | Team roles | `AGENTS.md` §9 |
| Data dictionary (2.1) | 9 columns | `docs/data_dictionary.md` |
| Table 2.1 | 5V | `data/raw_audit.csv`, `raw_audit_manifest.json` |
| Table 2.2 | Subset statistics (raw and after cleanup) | `data/manifests/raw_subset_counts.csv`, `data/manifests/e2_preprocessing_verified.json` (manifest, no run_id) |
| Table 2.3 | Coverage / representativeness | `e2_preprocessing_verified.json` → `runs[].profile` (manifest, no run_id) |
| Table 2.4 | Event mix raw vs after cleanup | `data/raw_audit.csv`, `e2_preprocessing_verified.json` → `profile.event_types` |
| Table 2.5 | Rows in/out per preprocessing step | `e2_preprocessing_verified.json` |
| Table 3.1 | Model configuration | `metrics.json → config` of the E1 runs |
| Table 3.2 | Sessions per split | TV1 split manifest of the official cuDF run |
| Table 4.1 | Environment | `environment/README.md`, `run.json → metadata.environment` |
| Table 4.2 | Experiment matrix | `configs/experiments.json` |
| Tables 5.1–5.4 | E1–E4 results | `metrics/raw/<run_id>/` (run_id per row) |
| Table 5.5 | E5 scalability | `reports/e5/summary.json`, rows cite the **E2** run_ids |

Dataset tables (Chapter 2) cite their CSV/manifest directly; experiment tables (5.1–5.5) cite run_ids.

### E1 — model comparison (Table 5.1, Figure 5.1)

| Report column | Source field | Raw unit | Display | Scope / note |
| --- | --- | --- | --- | --- |
| Recall@20 | `metrics.json` → `Recall@20` | ratio 0–1 | 4 decimals | sum over valid sessions / n_sessions |
| NDCG@20 | `metrics.json` → `NDCG@20` | ratio 0–1 | 4 decimals | same aggregation |
| Evaluated sessions | `metrics.json` → `n_sessions` | sessions | integer | must be equal for the 3 models |
| Training time | `metrics.json` → `train_with_input_scan_seconds` | s | s (1 dec.) | includes input scan; Popularity = counting time |
| Inference time | `metrics.json` → `inference_seconds` | s | s | `full_evaluation_wall_v1`: read + prepare + predict + rank + aggregate + write JSONL |
| Time per session | `inference_ms_per_session` | ms/session | ms | = `inference_seconds` × 1000 ÷ `n_sessions` (evaluated sessions of test D); includes I/O |
| Throughput | `inference_sessions_per_second` | sessions/s | integer | same scope |
| Whole-run wall time | `run.json` → `elapsed_seconds` | s | s | whole launched command |
| Peak CPU memory | `run.json` → `peak_process_tree_rss_bytes` | bytes | GiB | sampled parent+child RSS; may double-count shared pages |
| Peak GPU memory | `metrics.json` → `peak_cuda_reserved_bytes` | bytes | GiB | neural runs only; Popularity = "N/A" |
| Model size (optional) | `metrics.json` → `parameter_bytes` | bytes | MiB | neural only |
| Status | `run.json` → `status`, `exit_code` | — | badge | failed/OOM runs listed, metrics suppressed |

Do **not** compare `prediction_compute_seconds` across models (diagnostic only, per `inference_timing.md`).

### E2 — data size (Table 5.2, Figure 5.2)

| Report column | Source field | Raw unit | Display | Note |
| --- | --- | --- | --- | --- |
| Subset | `run.json` → `metadata.run.subset` | % sessions | 10/25/50/100% | session ratio, not event ratio |
| Events (measured) | `metadata.pipeline_metrics.n_events` | events | thousands sep. | raw weekly events of the subset; x-axis of E2/E5 |
| Events after cleanup | `metadata.pipeline_metrics.events_after_repeat_removal` | events | thousands sep. | after cuDF repeat removal |
| Sessions, users, items, categories, brands | `data/manifests/e2_preprocessing_verified.json` → `runs[].profile.distinct` | counts | integer | **available** (official cuDF run); not in run.json |
| Sequences (≥ 2 interactions) | `e2_preprocessing_verified.json` → `runs[].sequence_count` | sessions | integer | **available** |
| Vocabulary / catalog size | `e2_preprocessing_verified.json` → `runs[].vocabulary_size` | items | integer | **available**; grows with the subset — show next to accuracy |
| Raw read time | `metadata.pipeline_metrics.read_seconds` | s | s | TV1 measured stage |
| Preprocessing time | `metadata.pipeline_metrics.preprocessing_seconds` | s | s | = prepare + workflow + split; excludes raw read and first-seen |
| Prepare / workflow fit / split time | `metadata.pipeline_metrics.prepare_seconds`, `workflow_seconds`, `split_seconds` | s | s | stage breakdown for Figure 5.2 (copied from TV1 `timings.json`) |
| Shared first-seen cost | `metadata.pipeline_metrics.first_seen_seconds` | s | s | same value for all subsets — show once, separately |
| Training time | `metrics.json` → `train_with_input_scan_seconds` | s | s | |
| Inference time | `metrics.json` → `inference_seconds` | s | s | |
| Peak CPU memory | `run.json` → `peak_process_tree_rss_bytes` | bytes | GiB | model process only |
| Peak GPU memory | `metrics.json` → `peak_cuda_reserved_bytes` | bytes | GiB | |
| Raw subset CSV size | `data/manifests/raw_subset_manifest.json` → `subsets[].output_bytes` | bytes | MiB | **available** (TV1 manifest) |
| Session Parquet size | — | bytes | MiB | **NEED TV1/TV2**: which Parquet artifact to measure |
| Recall@20, NDCG@20 (optional column) | `metrics.json` | ratio | 4 dec. | shows if accuracy changes with data |

### E3 — resources (Table 5.3)

| Report column | Source field | Raw unit | Display | Note |
| --- | --- | --- | --- | --- |
| Train batch size | `metrics.json` → `config.batch_size` (planned: matrix `batch_size`) | sessions/batch | 32 / 128 | the only changed variable |
| Training time | `train_with_input_scan_seconds` | s | s | |
| Training throughput | — | sessions/s | | **NEED TV2**: official E3 throughput definition (train vs eval) |
| Evaluation throughput | `inference_sessions_per_second` | sessions/s | | eval batch fixed at 32 |
| Whole-run wall time | `run.json` → `elapsed_seconds` | s | s | |
| Peak CPU memory | `peak_process_tree_rss_bytes` | bytes | GiB | |
| Peak GPU memory | `peak_cuda_reserved_bytes` | bytes | GiB | key resource effect |
| Recall@20, NDCG@20 (validation) | `metrics.json` | ratio | 4 dec. | validation split, not test |
| Cost | — | USD | | **NEED TV3/TV2**: price/hour × wall time, or "not measured" |

### E4 — CSV vs Parquet (Table 5.4)

| Report column | Source field (`artifacts/metrics.json` of `e4-010-*`) | Raw unit | Display | Note |
| --- | --- | --- | --- | --- |
| Format | `format` | — | CSV / Parquet | |
| Rows (check) | `n_events` | events | integer | must be equal for both formats |
| Same content check | `verification`, `verification_method` | — | ✓ | row count **and** multiplicity-sensitive multiset fingerprint of the 9 fields (probabilistic) |
| File size | `bytes` | bytes | MiB | + compression ratio CSV/Parquet |
| Read time | `read_seconds` | s | s | full streamed decode, all 9 fields read as strings (`schema_policy`); OS cache warm after the pair check (`cache_policy`) |
| Peak reader memory | `peak_read_process_rss_bytes` | bytes | MiB | sampled at batch boundaries |
| Preprocessing time | `preprocessing.elapsed_seconds` | s | s | TV1 command incl. its own input read |
| Preprocessing peak memory | `preprocessing.peak_process_tree_rss_bytes` (collector record of the nested command, `benchmark/collect.py`) | bytes | GiB | same RSS scope as model runs |
| Status | `status` | — | badge | `read_only_diagnostic` runs are not full E4 results |

### E5 — scalability (Table 5.5, Figure 5.3)

From `reports/e5/summary.json` / `scalability.csv` (one row per passed E2 run):

| Report column | Source field | Raw unit | Display | Note |
| --- | --- | --- | --- | --- |
| Subset, source run_id | `subset`, `run_id`, `source_log` | — | | traceability |
| Events | `n_events` | events | | x-axis |
| Raw read | `raw_read` | s | s | stage |
| Preprocessing | `preprocessing_excluding_raw_read_and_first_seen` | s | s | stage |
| Training | `train_including_sequence_io` | s | s | stage |
| Final evaluation | `final_evaluation_including_io` | s | s | stage |
| Total (excl. first-seen) | `composed_seconds_excluding_first_seen` | s | s | |
| **Runtime per 1M events** | `seconds_per_million_events` | s / 1M events | s | = `composed_seconds_excluding_first_seen` × 10⁶ ÷ `n_events` (measured weekly events before sequence building); a sum of separately measured stages, not one observed wall time |
| Train partitions used | `trained_partition_count`, `eval_day` | count, index | | write in caption |
| Bottleneck | `bottleneck` | stage name | text | largest stage |
| Shared first-seen | `first_seen_seconds_shared` | s | s | shown once |
| Total incl. first-seen | `composed_seconds_with_first_seen` | s | s | composed total incl. the shared first-seen, not an observed end-to-end time |
| Observed process wall | `process_wall_seconds` | s | s | sanity check vs composed total |
| Peak memory | `peak_model_process_tree_rss_bytes` | bytes | GiB | |
| Completeness | `summary.json` → `status` | complete / partial | | partial ⇒ say which subset is missing |
| Uncertainty | limitations text | — | | one run per subset; **NEED TV2** numeric uncertainty decision |

### Environment (Table 4.1) — joined to every run

`run.json` → `metadata.environment` (path + sha256) → GPU, CUDA, driver, Python, torch, package versions;
neural `metrics.json` also records `gpu`, `cuda`, `packages`. CPU model, cores, RAM, OS, cloud instance and price:
**NEED TV3** (`environment/README.md`).

## 3b. Empty table files (fill when the package arrives)

One CSV per experiment table, with planned run_ids and source paths pre-filled, all values empty, `status = pending`:
`table5_1_e1_model_comparison.csv`, `table5_2_e2_data_size.csv`, `table5_3_e3_batch_size.csv`,
`table5_4_e4_storage_format.csv`, `table5_5_e5_scalability.csv`. Copy values only from the TV2 package; set
`status` to `passed` / `failed` / `excluded` and `data_kind` to `real`.

Traceability rules for the CSVs:
- Every row has `row_type` (`run` = one experiment run; `shared` = a cost shared by several runs, e.g. the monthly
  first-seen row in Table 5.2), `run_id` (Table 5.5: the E2 `source_run_id`), `status`, `data_kind`, and the paths it
  was copied from: `source_run` (`run.json`), `source_metrics` (`artifacts/metrics.json`), `source_log`
  (`stdout.txt`, or E5 `rows[].source_log`), `source_counts` (manifest) where relevant.
- Column name = source field name. When a value is **converted or derived**, the name says so:
  `*_gib` / `*_mib` = bytes ÷ 1024³ / 1024² of the field with the same stem; `content_verified` (Table 5.4) is derived
  from the `verification` object (fingerprints equal → `true`), the raw object stays in `source_metrics`;
  `train_throughput_sessions_per_second` (Table 5.3) is derived with the formula TV2 confirms
  (`format_check.md` §3 #4).

## 4. Caption template

`Table n.m: <what> on the <subset> subset, <split> partition D. Source runs: <run_id, …> (metrics/raw/<run_id>/).
Units: <…>. Scope: <timing scope / memory scope>. <Excluded or failed runs, if any>.`

Example (structure only): `Table 5.1: E1 model comparison on the 10% subset, test partition D. Source runs:
e1-popularity-010, e1-gru-010, e1-xlnet-010. Inference time = full evaluation wall incl. I/O
(full_evaluation_wall_v1). Peak CPU memory = sampled process-tree RSS.`

## 5. Open points to send to TV2 (for the 21/11 format check)

Superseded by the consolidated, prioritised list in [`format_check.md`](format_check.md) §3 (12 items with priority and owners);
the list below is kept for history.

1. E2: per-subset sessions/users/items/categories/brands and vocabulary size — which file is the official source?
2. E2: which "data size in bytes" to report (raw subset CSV, cleaned Parquet, or session Parquet)?
3. E3: official throughput definition (training sessions/s vs evaluation sessions/s).
4. E3: is cost reported? If yes, price source and formula.
5. E4: is preprocessing memory part of the official E4 table (field exists: `preprocessing.peak_process_tree_rss_bytes`)?
6. E5: numeric uncertainty or text-only limitation (one run per subset)?
7. All: status label for excluded runs and where the exclusion reason is written.
8. Sequence length actually used at runtime (metrics.json has no field; matrix says 20).
9. Popularity "training time" = counting time — confirm wording for the report.
10. **E5 inconsistency (blocker before quoting `summary.json`):** `benchmark/scalability.py` sums
    `final_evaluation_including_io` = `inference_seconds` (full evaluation wall incl. I/O), but its `limitations`
    text says "Final inference is compute/ranking only; validation, audit, checksum and serialization excluded".
    TV2 must fix the text (or the field) and regenerate `summary.json`.
11. Session-prediction contract: `app/output_contract.md` exists only on `feature/tv4-demo-documentation`
    (pending TV2 approval), not on `main`. Agree on the approved version before filling demo-related fields.
