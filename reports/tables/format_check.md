# Output format check for the report (TV5 task 21/11)

**Task (team_tasks.md, 21/11):** compare the output contract / metrics format with what the report needs; send TV2
the list of missing fields to confirm.

**Checked against (20/11/2026, no real-data runs exist yet):**
- TV2 code on `main` @ `86bc1c8`: `evaluation/run_neural.py`, `evaluation/run_popularity.py`,
  `models/session_models.py`, `scripts/runs/run_experiments.py`, `benchmark/collect.py`, `benchmark/format_io.py`,
  `benchmark/scalability.py`, `configs/experiments.json`, `configs/pipeline_metrics.example.json`,
  `docs/modeling/inference_timing.md`, `docs/modeling/experiment_runbook.md`.
- Real output *shape* from toy records: `metrics/tv2-config-collector-smoke/smoke-e1-{popularity,gru,xlnet}-010/`
  (`run.json`, `artifacts/metrics.json`, `artifacts/predictions.jsonl`), `metrics/tv2-model-smoke/environment.json`.
  Toy values are not used anywhere — only field names and structure.
- TV1 manifests: `data/manifests/raw_subset_counts.csv`, `data/manifests/raw_subset_manifest.json`.
- TV4 contract proposal: `app/output_contract.md` on `feature/tv4-demo-documentation` @ `5b2df90`
  (pending TV2 approval, not on `main`).

Legend: ✅ exported as a field · ⚠️ only derivable, planned-only, or fixed in code but not recorded per run ·
❌ not exported.

---

## 1. Field availability per report need

### 1.1 Accuracy and protocol (E1, E2, E3)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| Recall@20, NDCG@20 of the final evaluation | ✅ | `metrics.json` → top-level `Recall@20`, `NDCG@20` (all 3 models); neural also repeats them in `final.*` | Popularity has no `final` object |
| Sums for re-aggregation | ✅ | `recall_sum`, `ndcg_sum`, `n_sessions` | lets us check mean = sum / n |
| Evaluated split and partition | ✅ | `eval_split`, `eval_day`, `train_days` | E1/E2 test D, E3 validation D |
| K | ✅ | `K` | |
| Daily validation curve (optional figure) | ✅ neural · ❌ Popularity | `history[].validation.{Recall@20,NDCG@20,n_sessions}` | Popularity has no `history` |
| Per-partition sessions / items | ✅ | `split_counts[] = {day_index, split, n_sessions, n_items}` | sessions can be summed; **`n_items` are distinct per (day, split) — summing them double-counts**, distinct items across splits need a union |
| Status pass/fail, data kind (model runs E1–E3) | ✅ | `run.json` → `status`, `exit_code`, `metadata.data_kind` | only in `run.json`; E4 also has its own artifact `status` (§1.5) |
| Exclusion reason | ❌ | — | needed to explain excluded runs |

### 1.2 Model configuration (Table 3.1, section 3.1)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| Train batch, eval batch, epochs, seed, learning rate | ✅ neural | `metrics.json` → `config.{batch_size, eval_batch_size, epochs, seed, learning_rate}` | Popularity takes none of these (counting only). Model seed 1 applies to neural runs; the split seed 1 is a property of the membership, not of the run |
| Sequence length | ✅ planned · ⚠️ effective | planned: `run.json` → `metadata.run.sequence_length` (runner rejects ≠ 20); effective: constant `max_sequence_length=20` in `models/session_models.py` | no effective field in `metrics.json` |
| Masking (causal / MLM) | ⚠️ | fixed in code: GRU `causal`, XLNet `mlm` | not recorded per run |
| d_model, layers, heads | ⚠️ | code: GRU d_model 128, 1 layer; XLNet d_model 192, 2 layers, 4 heads | not recorded per run |
| Model size | ✅ neural | `parameter_bytes` | |
| Catalog / mapping / workflow version | ✅ | `run.json` → `metadata.versions`, `metadata.artifacts` (path + sha256) | |
| Catalog size | ⚠️ | count real products in the file at `metadata.artifacts.catalog.path` | keep two names: **catalog size** = real candidate products; **vocabulary cardinality** = schema cardinality incl. technical tokens (padding/null/OOV) |

### 1.3 Time, throughput, memory (E1–E3)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| Training time | ✅ | `train_with_input_scan_seconds` | Popularity: fit (counting) time incl. input scan |
| Inference time, ms/session, sessions/s | ✅ | `inference_seconds`, `inference_ms_per_session` = 1000 × `inference_seconds` ÷ `n_sessions`, `inference_sessions_per_second` = `n_sessions` ÷ `inference_seconds` | scope `full_evaluation_wall_v1`: read, prepare, predict + rank, metric aggregation, JSONL write |
| Training throughput (E3) | ⚠️ | derivable from `history[].train.{n_sessions, train_with_input_scan_seconds}` and `config.epochs` | no exported field; formula needs TV2 (§3 #4) |
| Whole-run wall time | ✅ | `run.json` → `elapsed_seconds` | |
| Peak CPU memory | ✅ | `run.json` → `peak_process_tree_rss_bytes` (collector, sampled every 0.05 s) | may double-count shared pages |
| Peak GPU memory | ✅ neural · absent for Popularity | `metrics.json` → `peak_cuda_reserved_bytes`, `peak_cuda_allocated_bytes` | the CUDA keys are absent in Popularity output; **the table shows `N/A`** |
| Cost | ❌ | — | |

### 1.4 Data size and pipeline (E2, E5)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| Measured weekly events, read / preprocessing / first-seen time | ✅ schema · values pending | `run.json` → `metadata.pipeline_metrics.{n_events, read_seconds, preprocessing_seconds, first_seen_seconds}` | TV1 telemetry delivered 21/11: `data/clean/e2-weekly/<subset>/pipeline_metrics.json` on the VM (also has `prepare_seconds`, `workflow_seconds`, `split_seconds`, `events_after_repeat_removal`); values listed in `data/manifests/e2_preprocessing_verified.json` |
| Raw sessions, users, items per subset | ✅ | `data/manifests/raw_subset_counts.csv`; after cleanup: `e2_preprocessing_verified.json` → `runs[].profile` | raw weekly events before cleanup / official cuDF cleanup |
| Sessions / items after preprocessing | ⚠️ | `split_counts` (see §1.1 note on distinct items) | |
| Categories, brands per subset | ❌ | — | TV1 |
| Raw subset CSV bytes | ✅ | `data/manifests/raw_subset_manifest.json` → `subsets[].output_bytes` | TV1 manifest, not a run output |
| Session Parquet bytes | ❌ | — | artifact to measure not agreed |
| Preprocessing memory (E2) | ❌ | — | `pipeline_metrics` has no memory field (E4 has one) |

### 1.5 Storage format (E4)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| File size, read time, rows | ✅ | `metrics.json` → `bytes`, `read_seconds`, `n_events` | from `benchmark/format_io.py` |
| Content check | ✅ source · derived column | `verification` (fingerprint object), `verification_method` | `content_verified` in Table 5.4 is **derived** from `verification` |
| Peak reader memory | ✅ | `peak_read_process_rss_bytes` | sampled at batch boundaries |
| Preprocessing time and memory | ✅ when run | `preprocessing.elapsed_seconds`, `preprocessing.peak_process_tree_rss_bytes` | present only if the preprocessing step runs (not in `--read-only` diagnostics) |
| Cache / schema policy text | ✅ | `cache_policy`, `schema_policy`, `read_scope` | |
| Committed E4 output example | ❌ | none in `metrics/` | tests create temporary outputs with a worker fixture; full E4 waits for TV1's shared `preprocessing_argv` (§3 #6) |

### 1.6 Scalability (E5)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| Stage times, composed seconds, s / 1M events, bottleneck | ✅ | `reports/e5/summary.json` → `rows[]` | `seconds_per_million_events` = `composed_seconds_excluding_first_seen` × 10⁶ ÷ `n_events` |
| Source E2 run ids + logs | ✅ | `run_id`, `source_log` | |
| Correct scope description | ❌ **inconsistent** | `limitations` says "Final inference is compute/ranking only…", but the stage summed is `inference_seconds` (full evaluation wall incl. I/O) | must be fixed before quoting |
| Uncertainty | ✅ qualitative · ❌ numeric | `limitations`: "One run per subset; no variance or confidence interval measured." | |

### 1.7 Environment (Table 4.1)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| GPU, CUDA, Python, packages | ✅ neural | `metrics.json` → `gpu`, `cuda`, `python`, `packages` | |
| Driver | ✅ via snapshot | environment snapshot linked by `run.json` → `metadata.environment` (path + sha256) | not in `metrics.json` |
| OS / platform | ⚠️ | Popularity `platform` only | |
| CPU model, cores, RAM, cloud instance, price/hour, Docker image | ❌ | — | TV3 snapshot of the real VM |

### 1.8 Session predictions (demo slide, section 5.3)

| Report need | Status | Where | Note |
| --- | --- | --- | --- |
| Session key, prefix, target, top-20 | ✅ | `predictions.jsonl` → `user_session`, `prefix`, `target`, `top20` (encoded IDs) | |
| Original product IDs of top-20 | ✅ | `product_ids` (aligned with `top20`) | prefix/target original IDs need the catalog mapping (TV4 exporter) |
| Target rank / hit | ⚠️ | derivable from `top20` and `target` | |
| Per-item score | ❌ | — | demo backlog (TV4), not needed by the report |

---

## 2. Result

- **Enough for the report as planned:** E1 accuracy/time/memory, E3 batch comparison (except throughput formula and
  cost), E4 field set (pending a full run), E5 stages (pending the text fix), protocol fields, raw subset counts and
  bytes, per-partition session counts.
- **Missing or ambiguous** → list below. All are format/definition decisions; none needs real data to decide.

## 3. List for TV2 (and owners) to confirm

Priority **A** = blocks a table or a run; **B** = needed for correct wording; **C** = nice to have.

| # | Pri | Question | Owner | Proposal from TV5 |
| --- | --- | --- | --- | --- |
| 1 | A | E5: fix `limitations` text in `benchmark/scalability.py` (says inference is compute-only, but `final_evaluation_including_io` = full evaluation wall) | TV2 | text: "full evaluation wall incl. I/O (`full_evaluation_wall_v1`)", then regenerate `summary.json` |
| 2 | A | E2 counts: confirm sources — raw sessions/users/items from `raw_subset_counts.csv`; post-preprocessing sessions from `split_counts`; categories/brands per subset; **catalog size (real products) per subset, kept separate from vocabulary cardinality** | TV1, TV2 | **Partly answered 21/11:** distinct users/products/categories/brands, `vocabulary_size` and `sequence_count` per subset are in `e2_preprocessing_verified.json`; split counts of the official cuDF run still open |
| 3 | A | E2 bytes: raw subset CSV bytes are settled (`raw_subset_manifest.json` → `output_bytes`). **Which Parquet artifact** (cleaned events or session sequences) do we report? | TV1, TV2 | session Parquet of each subset |
| 4 | A | E3 training throughput formula | TV2 | train sessions/s = Σ over trained partitions (`history[].train.n_sessions` × `config.epochs`) ÷ Σ `history[].train.train_with_input_scan_seconds` (train wall incl. input scan); evaluation throughput = `inference_sessions_per_second` |
| 5 | A | Excluded runs: status label and field for the reason | TV2 | `excluded` + `exclusion_note` in the metrics package |
| 6 | A | **E4 full run:** who delivers the shared `preprocessing_argv` command that reads both CSV and Parquet (`{input_path}`, `{input_format}`, `{output_dir}`)? | TV1 (command), TV2 (interface), TV3 (run) | without it only `--read-only` diagnostics exist, not a full E4 |
| 7 | A | Real environment snapshot: CPU model, cores, RAM, OS, driver, Docker image/digest, instance type, price/hour, linked from `metadata.environment` | TV3 | one `environment.json` per VM |
| 8 | B | Record effective sequence length, masking, d_model/layers/heads per run (now planned field + code constants) | TV2 | add to `metrics.json → config`, or state in the package that the code constants at commit X applied |
| 9 | B | E3 cost: reported or "not measured"? | TV2, TV3 | price/hour × `elapsed_seconds` if TV3 gives the price |
| 10 | B | E2 preprocessing memory: add a memory field to `pipeline_metrics`, or report "not measured"? | TV1, TV2 | add `peak_rss_bytes` |
| 11 | B | Approve the TV4 contract version used for demo fields (`app/output_contract.md` @ `5b2df90`) | TV4 (lead), TV2 (approve) | merge to `main` after approval |
| 12 | C | E5 numeric uncertainty — only if repeated runs are planned | TV2 | otherwise text-only (already in `limitations`), stated in 5.2.3 |

**Decided by TV5 (no question needed):** Popularity "training time" is written as **"fit (counting) time incl. input
scan"**. **Moved to TV4 demo backlog:** per-item score in `predictions.jsonl`.

## 4. Inputs from other members

- **Needed for this check:** none beyond the repo (TV2 code and toy records on `main`, TV1 manifests, TV4 contract on
  its branch). The check is about format, not values.
- **Needed to close the questions:** **TV2** (1–6, 8–12), **TV1** (2, 3, 6, 10), **TV3** (6, 7, 9), **TV4** (11).
  Record the answers in §5 and in `docs/handoff.md`.

## 5. Answers received

| # | Answer | From | Date |
| --- | --- | --- | --- |
| | | | |
