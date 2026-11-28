# Team progress and data sources — context for the demo agent

**Snapshot:** 25/11/2026. Team repo `tlmthuy/Big-Data`, branch `main`, commit `88f7e02` (24/11 21:59 +07). Demo repo `callmeshinny/demo-big-data`, last commit `643634a` (21/11).

**Purpose:** Tell an AI agent working in `demo-big-data` what the team has finished, which real artifacts now exist, where each one lives, and what the demo still has to change. Read this together with `AGENTS.md`, `docs/CONTEXT.md` and `docs/data_contract.md` in the demo repo. Where this file and `docs/CONTEXT.md` disagree, this file is newer: `CONTEXT.md` describes the 21/11 state, before the official results existed.

**Paths:** all paths below are relative to the team repo root unless marked *demo repo* or *VM*. The `/workspace/...` paths exist only on the AWS VM used by TV3, not in Git.

---

## 1. Big picture: what changed since the demo's last snapshot

| Area | At demo snapshot (21/11) | Now (25/11) |
| --- | --- | --- |
| Data pipeline (TV1) | Raw audit, sampling, cleanup, first-seen done; sequences/splits pending | **All TV1 tasks done**: weekly cuDF workflow, catalog/mapping per subset, sequences, splits for 10/25/50/100% |
| Models (TV2) | Scripts and toy smoke only | **Real runs done and verified**: E1–E5 on real data, official metrics package released |
| Cloud runtime (TV3) | VM pending | **AWS VM done**: Tesla T4, Docker Merlin image, all E1–E5 runs executed, raw logs handed to TV2 |
| Official numbers | None; demo used `null` / toy | **Package `tv2-20261124`** with E1–E5 CSV/JSON, configs, units, run registry |
| Prediction sample (TV4) | Built in demo repo | **Accepted by TV2 and merged into team repo** (`app/samples/`, commit `c41f191`) |
| Real per-session predictions | Not delivered | **Still not in Git.** They exist on the VM only (see §6). |
| Product metadata (brand/category/price) | Toy file | **Still not delivered as a lookup file** (see §6). |

**Consequence for the demo:** the Experiments tab and the Dataset tab can now switch from `null`/toy to **real, official numbers**. The Recommendation tab must stay on toy data until real predictions and product metadata are exported from the VM.

---

## 2. The project in short

- **Dataset:** Kaggle "eCommerce behavior data from multi-category store", file `2019-Oct.csv`, 42,448,764 rows, 9 columns:
  - `event_time`, `event_type` (view/cart/purchase), `product_id`, `category_id`, `category_code`, `brand`, `price`, `user_id`, `user_session`.
  - There are **no product names and no images**.
- **Task:** session-based next-item recommendation.
  - A session is one visit; each click is one event.
  - For each evaluated session, the model sees all items except the last (prefix) and returns **one Top-20 list** for the **single next item**.
  - The real last item is the ground truth (`target`).
- **Metrics:**
  - Recall@20: hit if the target is in the Top-20.
  - NDCG@20: 1/log2(rank+1) if hit, else 0.
  - Both are averaged over valid sessions. K = 20. Items already in the prefix may be recommended.
- **Models:** Popularity baseline, GRU and XLNet (NVIDIA Transformers4Rec, upstream pinned at `f0ca2b5`). All use `product_id` only.
- **Big Data experiments:**

  | ID | Question | Design |
  | --- | --- | --- |
  | E1 | Model comparison | 10% subset, test partition 7 |
  | E2 | Data size | GRU on 10/25/50/100% subsets |
  | E3 | Resources | GRU 10%, train batch 32 vs 128, eval batch 32, validation split |
  | E4 | Storage format | CSV vs Parquet, same 882,808 events |
  | E5 | Scalability | Derived from E2 logs; no new model runs |

---

## 3. What each member has finished (verified in the repo)

Status comes from the team task sheet the user provided, and was checked against files on `main`.

### TV1 — Data (Châu): all tasks done

| Task | Evidence |
| --- | --- |
| 9-column data dictionary | `docs/data_dictionary.md` |
| NVIDIA preprocessing review (CSV → Parquet diagram, steps) | `docs/preprocessing_review.md` |
| Raw audit before sampling (rows, event types, sessions, users, items, categories, brands, missing values) | `data/raw_audit.csv`, `data/manifests/raw_audit_manifest.json` |
| Session sampling by stable hash: SHA-256(seed 42 + ":" + session ID), nested 10/25/50/100% | `data/manifests/session_sampling_manifest.json` |
| Raw subset export, first week 01–07/10 UTC, with counts | `data/manifests/raw_subset_manifest.json`, `data/manifests/raw_subset_counts.csv` |
| `event_time` → `event_time_ts` (unix seconds UTC) | `data/manifests/event_timestamp.json` |
| Session cleanup and consecutive-repeat removal | `data/manifests/timestamp_session_cleanup.json`, `docs/timestamp_session_cleanup.md` |
| Monthly first-seen lookup (shared cost 1.516 s) | `data/manifests/monthly_first_seen.json` |
| Fitted workflow, schema, mapping, vocabulary and catalog per subset | `data/manifests/weekly_workflows_verified.json`, `weekly_workflow_inputs.json` |
| Sequences per session (min 2 interactions, last 20 items kept) | `data/manifests/weekly_sequence_recheck.txt` |
| Train/validation/test split by day_index (~80/10/10, GPU seed 1) | `data/manifests/weekly_splits_verified.json` |
| Final 10/25/50/100% datasets and E2 preprocessing command | `data/manifests/e2_preprocessing_verified.json`, `weekly_subset_profiles.json`, `e4_preprocessing_smoke.json` |

TV1 selected the **cuDF weekly** artifacts for official runs. The older DuckDB profiles are reference only.

### TV2 — Models, protocol, analysis (Thùy): all tasks done

| Task | Evidence |
| --- | --- |
| Model parameter table (Popularity, GRU, XLNet) | `docs/modeling/model_comparison.md` |
| Problem definition (prefix → Top-20, next-item target) | `docs/modeling/next_item_problem.md` |
| Split protocol, catalog rule, K = 20 | `docs/modeling/model_protocol.md` |
| Recall@20 / NDCG@20 with toy tests | `evaluation/ranking.py`, `evaluation/tests/` |
| Popularity, GRU, XLNet scripts | `models/popularity.py`, `models/session_models.py`, `evaluation/run_popularity.py`, `evaluation/run_neural.py` |
| Experiment matrix E1–E5 and runner | `configs/experiments.json`, `docs/experiment_matrix.md`, `scripts/runs/run_experiments.py` |
| Handoff of scripts/configs to TV3 | `configs/tv2_handoff.json`, `docs/modeling/experiment_runbook.md` |
| Acceptance of TV1 data | `docs/handoff.md` |
| **E1–E5 analysis** | `reports/tables/tv2-20261124/analysis.md` (Vietnamese), plus supporting CSVs |
| **Official metrics package for TV4/TV5** | `metrics/releases/tv2-20261124/` (TV4 acknowledged on 24/11; TV5 pending) |

### TV3 — Cloud environment and runs (Đăng): all listed tasks done

| Task | Evidence |
| --- | --- |
| Ubuntu GPU VM on public cloud (AWS) | `environment/README.md` (runtime table) |
| Docker + NVIDIA Merlin runtime, imports verified | `environment/logs/02-import-test.log`, `04-docker-image-inspect.json` |
| Environment versions recorded | `environment/README.md`, `environment/pip_freeze_baseline.txt` |
| Parquet and model smoke tests | `metrics/tv3-parquet-smoke-20261122/`, `metrics/tv3-model-smoke-20261122-result.json` |
| Runtime/memory collector | `benchmark/collect.py`, `metrics/tv3-collector-smoke-20261122-result.json` |
| E1, E2, E3, E4, E5 runs | `metrics/e1-tv3-run-summary.json` … `e5-tv3-run-summary.json` |
| Reruns of fixable failures | Recorded in `docs/handoff.md` |
| Raw logs handed to TV2 | Archived copies in `metrics/tv2-analysis-20261124/evidence/` |

### TV4 — Demo (callmeshinny / Ngọc)

| Task | Status |
| --- | --- |
| Demo skeleton, README, figures folder | Done (`app/`, `reports/figures/`) |
| Output contract (Part A sessions, Part B runs, dependencies) | Done, merged (`app/output_contract.md`, commit `5f839a7`) |
| Prediction JSON/CSV sample, format confirmed by TV2 | Done, merged (`app/samples/`, commit `c41f191`). Toy data, not benchmark. |
| Figure script skeleton (22/11) | Exists in the demo repo (`scripts/make_figures.py`, `figures/`) with toy/empty-state SVGs |
| 25/11 → 28/11 | Figure templates and captions; run_id checks; integrate into UI; official figures; demo fallback; live demo practice. **This is the agent's work.** |

### TV5 — Report and slides

Uses the same package. TV5's receipt is still pending in `metrics/releases/tv2-20261124/manifest.json`.

---

## 4. Runtime environment (for the "Environment" blocks in the UI)

Source: `environment/README.md` (runtime table, verified 21–22/11/2026) and `configs.json` → `runtime`.

| Item | Value |
| --- | --- |
| Cloud | AWS EC2 VM, Ubuntu 22.04.5 LTS, kernel `6.8.0-1036-aws` |
| GPU | Tesla T4 (compute capability 7.5), 15,360 MiB VRAM |
| CPU / RAM | Intel Xeon Platinum 8259CL @ 2.50 GHz, 8 vCPU / 30.98 GiB |
| Driver / CUDA | Driver `570.172.08` (supports CUDA 12.8); CUDA toolkit in container `12.1.105` |
| Docker / NVIDIA Container Toolkit | Docker `28.4.0` / `1.20.2` |
| Image | `merlin-pytorch:23.12` (digest in `environment/logs/04-docker-image-inspect.json`) |
| Python / PyTorch / Transformers4Rec | `3.10.12` / runtime `2.1.0a0+4136153` (pip metadata says `torch==2.1.2`) / `23.12.0` (transformers `4.27.1`) |
| Warm-up / cache | No warm-up; no OS cache flush (inherited cache state). E4 cache warm after pair verification. |

All official runs used this single machine. There is **no cost measurement**: show "Chưa có" / "Not measured" for cost.

---

## 5. Official results (package `tv2-20261124`)

**Folder:** `metrics/releases/tv2-20261124/`

| File | Content |
| --- | --- |
| `E1.csv` … `E5.csv` | Official tables chosen by TV2 |
| `metrics.json` | The same numbers as typed JSON (`schema_version 1`, `data_kind: "real"`, `tables.E1`…`E5`, `null` for unmeasured) |
| `configs.json` | Per run (11 keys): `effective_config` (actual), `run_metadata.run` (planned matrix row), `training_config`, `command_argv`, `versions` (workflow/mapping/catalog SHA), `artifacts` (catalog/schema path + SHA), `split_counts`, `runtime` (python/packages/gpu/cuda), `warmup`, `cache`, `source_run`, `source_metrics`. E4 entries have `preprocessing_argv`, `verification`, `cache`, `read_scope`, `schema_policy`, `workflow_manifest`, `split_manifest`, `timings`. |
| `run_registry.json` | 15 entries: 11 passed runs + 4 E5 rows (`derived_from_verified_E2`). Excluded: `e4-010-csv`, `e4-010-parquet` (smoke pair superseded by full E4). |
| `data_dictionary.json` | Units, scopes and interpretation limits. **Read before displaying anything.** |
| `manifest.json`, `review.json` | Checksums, TV4/TV5 receipts, review record |

Integrity check, run from the team repo root:

```bash
python -c "from scripts.package_metrics import verify; print(verify())"
```

### Headline numbers (copy from the package, never retype)

**E1 — 10% subset, test partition 7, 1,337 sessions**

| Model | Recall@20 | NDCG@20 | Train s | Final eval s | Eval ms/session |
| --- | --- | --- | --- | --- | --- |
| Popularity | 0.08676 | 0.03477 | 6.55 | 0.076 | 0.057 |
| GRU | 0.08826 | 0.03804 | 28.13 | 0.703 | 0.525 |
| XLNet | 0.12491 | 0.05133 | 30.65 | 0.858 | 0.642 |

**E2 — GRU, train batch 256, eval batch 32, 3 epochs/partition, lr 0.00071, seed 1**

| Subset | Events | Test sessions | Recall@20 | Train s |
| --- | --- | --- | --- | --- |
| 10% | 882,808 | 1,337 | 0.0883 | 27.6 |
| 25% | 2,213,138 | 3,266 | 0.1574 | 89.2 |
| 50% | 4,421,037 | 6,427 | 0.2748 | 203.1 |
| 100% | 8,829,314 | 13,052 | 0.3899 | 432.6 |

**E3 — GRU 10%, validation partition 7, 1,324 sessions, eval batch 32**

| Train batch | Recall@20 | NDCG@20 | Train s | Process wall s |
| --- | --- | --- | --- | --- |
| 32 | 0.1964 | 0.0906 | 51.66 | 65.94 |
| 128 | 0.1299 | 0.0591 | 30.59 | 44.77 |

**E4 — 10% raw subset, 882,808 events, nine string columns**

| Format | Bytes | Read s | Preprocessing wall s (includes read) |
| --- | --- | --- | --- |
| CSV | 134,004,153 | 0.454 | 34.99 |
| Parquet | 25,382,745 | 0.109 | 33.57 |

**E5 — composed stages from E2, excluding the shared first-seen cost**

| Subset | Composed s | s per 1M events | Bottleneck |
| --- | --- | --- | --- |
| 10% | 58.9 | 66.7 | preprocessing |
| 25% | 125.9 | 56.9 | train |
| 50% | 246.8 | 55.8 | train |
| 100% | 491.2 | 55.6 | train |

The shared first-seen cost is 1.516 s. Add it **once** per complete scenario.

### Interpretation rules (from `data_dictionary.json` and `analysis.md`) — the UI must respect these

1. **Single run, single seed.** No mean, std or confidence interval. Do not invent error bars.
2. **E1 is the only fair model comparison.** E3 accuracy is on validation; never place it next to E1/E2 test accuracy.
3. **E2 accuracy is not a pure train-size effect.** The test set and catalog change with the subset. Present E2/E5 as cost scaling first.
4. **E3 is a tradeoff.** Batch 128 is about 1.47× faster in process wall time but less accurate (different number of optimizer updates).
5. **E4:**
   - Parquet is 5.28× smaller and its timed read is 4.19× faster.
   - Full preprocessing barely changes (34.99 → 33.57 s).
   - Do not add the standalone read to the preprocessing wall time, which already includes it.
6. **E5 composed time** = raw read + preprocessing (excluding read and first-seen) + train (with sequence I/O) + final evaluation. It is **not** an observed end-to-end wall time.
7. **Inference time:**
   - It is `full_evaluation_wall_v1`: the whole evaluation including I/O and metrics, not pure model latency.
   - Do not use `prediction_compute_seconds`.
8. **Memory:**
   - `sampled_rss_bytes_descriptive_only` is descriptive only. No RAM conclusions across configs.
   - `sampled_gpu_process_bytes` is sampled process GPU memory, not CUDA allocated/reserved. `sampled_gpu_status = unavailable` means `null`, never 0 (Popularity).
9. **No cost data.**
10. **Coverage:** in the 100% week, 912,061 of 1,877,365 sessions (48.58%) have only one interaction after cleanup, so they cannot be evaluated. Metrics apply to sessions with at least 2 interactions.
11. **Browsing-heavy data:** cleanup leaves about 99.98% view events. The task is next-product in browsing, not purchase prediction.

### Figures and supporting tables already produced by TV2

| File | Use in the demo |
| --- | --- |
| `reports/figures/tv2-20261124/scalability/scalability.svg` (+ `.png`, `.csv`, `summary.json`) | E5 scaling curve |
| `reports/tables/tv2-20261124/sampling_population.csv` | Per subset: raw sessions/events/users, catalog items, cleaned events/users, model sequences, categories, brands, catalog coverage |
| `reports/tables/tv2-20261124/subset_distribution.csv` | Event mix and session-length distribution per subset |
| `reports/tables/tv2-20261124/event_mix_before_after.csv` | View/cart/purchase before vs after cleanup |
| `reports/tables/tv2-20261124/preprocessing_retention.csv` | Events removed, single-interaction session share, eligible sessions |
| `reports/tables/tv2-20261124/split_population.csv` | Train/validation/test sessions per subset |
| `reports/tables/tv2-20261124/stage_shares.csv` | Share of each stage in the E5 composition |
| `reports/tables/tv2-20261124/analysis.md`, `instructor_feedback_analysis.md` | Findings and limitations text (Vietnamese) to paraphrase in captions |

---

## 6. Where to get each piece of data the demo needs

| Demo element | Source | Status | Notes |
| --- | --- | --- | --- |
| E1–E5 metric values | `metrics/releases/tv2-20261124/metrics.json` (or `E*.csv`) | **Available, real** | Mark `confirmed_by_tv2: true`, `package_id: "tv2-20261124"`, `data_kind: "real"` |
| Planned config (Dự kiến) | `configs.json` → `<run>.run_metadata.run`, or `configs/experiments.json` | Available | Fields: `batch_size`, `epochs`, `sequence_length` (20), `split`, `seed`, `subset`, `train_partitions` (1..D-1), `eval_partition` (D), `input_format`, `resource_config` |
| Actual config (Thực tế) | `configs.json` → `<run>.effective_config` and `training_config` | Available | `batch_size`, `eval_batch_size` (32), `epochs`, `seed`, `learning_rate` (GRU 0.00071, XLNet 0.000666), `split`, `train_through` (6), `subset`, `device`. Popularity has no neural config: show "Không áp dụng". Sequence length is not in `effective_config`; show the planned 20 and mark the actual as "Chưa có". |
| Data versions | `configs.json` → `run_metadata.versions`, `artifacts.catalog.sha256` | Available | Show short SHA |
| Environment per run | `environment/README.md` + `configs.json` → `runtime` | Available | Same VM for all runs (§4) |
| Run status and exclusions | `run_registry.json` | Available | Show the excluded E4 smoke pair with its reason |
| Units, scopes, caveats | `data_dictionary.json` | Available | Show as tooltips or captions |
| E5 chart | `reports/figures/tv2-20261124/scalability/` | Available | Reuse the SVG or redraw from `scalability.csv` |
| Dataset/sampling overview | `reports/tables/tv2-20261124/*.csv`, `data/raw_audit.csv`, `data/manifests/*` | Available | Replace the "unconfirmed" values in the demo's `public/dataset-overview.json` |
| Prediction sample (toy) | `app/samples/demo-data.json`, `sample-predictions.csv` (schema `tv4-demo-data/v2`, 6 toy runs, 23-item catalog) | Available, **toy** | Already identical in shape to the demo repo's `public/demo-data.json` |
| **Real per-session predictions** | **VM:** `metrics/raw/<run_id>/artifacts/predictions.jsonl` for `e1-popularity-010`, `e1-gru-010`, `e1-xlnet-010` (1,337 sessions each). SHA-256 values in `metrics/tv2-analysis-20261124/prediction_checks.json`. | **Not in Git** | Needs TV3/TV2 to copy them out. Rows have 5 keys (`user_session`, `prefix`, `target`, `top20`, `product_ids`); no score. |
| **Real catalog (encoded → original ID)** | **VM:** `/workspace/data/clean/e2-weekly/10/workflow/catalog.json` | **Not in Git** | SHA-256 `04422f11…5fa6` (in `configs.json`). Required to decode `prefix`/`target`. |
| **Product metadata** (brand, category_code, price) | **VM / TV1 machine:** cleaned events Parquet. Monthly file `data/clean/month_cpu/events_clean.parquet` has `product_id`, `brand`, `category_code`, `price`, `event_time_ts`. The weekly cuDF set is under `/workspace/data/clean/e2-weekly/...`. | **Not in Git** | Needs TV1 (or TV3) to run the demo's `scripts/export_product_info.py` or deliver a small CSV for the 10% catalog only. |
| `user_id` per session | Same cleaned events (`user_id`, `user_session`) | **Not in Git** | Optional. Only if TV1/TV2 export a `user_session → user_id` map. Otherwise keep the session picker. |
| Per-item score | Not exported by any model | **Not available** | Keep "Chưa có". Never derive from rank. |

### What to ask teammates for (if the user wants a real Recommendation tab)

One small bundle from the VM, for the 10% subset E1 runs:

1. `predictions.jsonl` for the 3 E1 runs.
2. The matching 10% `catalog.json`.
3. A product lookup CSV restricted to products in that catalog: `product_id, brand, category_code, price`, using the rule "last observed price in the subset week".
4. Optionally, a `user_session → user_id` map for the 1,337 test sessions.

These are small (a few MB) and can be committed as demo JSON after conversion. They must keep SHA-256 checks against `prediction_checks.json` and `configs.json`.

---

## 7. State of the demo repo (`callmeshinny/demo-big-data` @ `643634a`)

Already built:
- **UI:** English default with Vietnamese toggle; Dataset tab (5V, subset selection, preliminary measurements); Evaluation protocol; Recommendation tab with `ProductCard`; Experiments tab with charts and a planned/actual structure.
- **Adapters** in `scripts/`:
  - `export_demo_data.py`
  - `export_run_results.py` (accepts `--collector-dir` for a real package)
  - `export_dataset_overview.py`
  - `export_product_info.py`
  - `export_figures.py` / `make_figures.py`, with `figure_specs.json`
  - `capture_screens.mjs`
- **Figures:** `figures/` (toy and empty-state SVGs, `CAPTIONS.md`).
- **Docs:** `docs/DEMO_SCRIPT.md`, `docs/DEMO_DAY.md`, `docs/SAMPLE_PREDICTION.md`, `docs/CONTRACT_NOTES.md`.
- **Tests:** `tests/`.

Data files and their current state:

| File (demo repo) | Current | Should become |
| --- | --- | --- |
| `public/run-results.json` | `package_id: null`, `confirmed_by_tv2: false`, `data_kind: "unconfirmed"`, 16 runs with `null` metrics | Generated from `metrics/releases/tv2-20261124/` (`metrics.json` + `configs.json` + `run_registry.json` + `data_dictionary.json`), `package_id: "tv2-20261124"`, `confirmed_by_tv2: true`, `data_kind: "real"`, with the environment from §4 |
| `public/dataset-overview.json` | `data_kind: "unconfirmed"`, `source_confirmed_by: null` | Filled from TV2 supplementary tables, `data/raw_audit.csv`, and verified manifests |
| `figures/*.svg` | Toy or empty-state | Official figures from the package (E1 ranking, E1 training time, E2 runtime, E3 tradeoff, E4 size/read, E5 scaling), each with title, axis units, legend, source `run_id` |
| `public/demo-data.json` | Toy (6 runs) | Stays toy until §6 real predictions arrive. Keep the toy badge. |
| `public/product-info.json` | Toy metadata | Stays toy until TV1 delivers metadata |

---

## 8. Next work for the agent (priority order)

1. **Experiments tab → real data.**
   - Extend or adapt `scripts/export_run_results.py` to read `metrics/releases/tv2-20261124/`.
   - Verify checksums against `manifest.json`.
   - Fill metrics, planned vs actual config, environment and sources. Show units and scopes from `data_dictionary.json`.
   - Apply the interpretation rules in §5, for example the "validation — not comparable with E1" note on E3.
2. **Official figures** from the package, replacing the toy SVGs. Write captions that state metric, unit, config, source `run_id` and the main limitation. Hand the figures and captions to TV5 (due 28/11).
3. **Dataset tab → real data.** Regenerate `dataset-overview.json` from the TV2 supplementary tables, and show the coverage and browsing-heavy caveats.
4. **Recommendation tab.** Keep the toy data with a clear badge, or switch to real data if the §6 bundle is delivered:
   - write an adapter that decodes with the real catalog;
   - check SHA-256 against `prediction_checks.json`;
   - select a few readable sessions;
   - join the product lookup for names.
   Never invent product names.
5. **Fallback for demo day:** screenshots via `scripts/capture_screens.mjs`, a static build, and an updated `docs/DEMO_DAY.md`.
6. **Sync back to the team repo** at the milestone (27–28/11), following `docs/SYNC.md`. Make one clean commit into `app/` (and `reports/figures/` for official figures) on a TV4 branch.

---

## 9. Hard rules (unchanged)

- Display only. Never train, refit or rerun models from the demo.
- Never invent numbers, scores, names or images. Missing = `null` → "Chưa có" / "Not available"; inapplicable → "Không áp dụng".
- Never recompute or redefine a metric. Use package values as delivered.
- Keep planned and actual configuration separate.
- Label toy data visibly. Do not mix toy and real values in the same table or chart.
- Every number on screen must trace to a `run_id` and a file in the package.
- No large data in Git. Commit only small JSON/SVG outputs.
- Do not push unless the user asks.
