# Report outline (English) — updated 21/11/2026

**Title:** Session-Based Next-Item Recommendation on eCommerce Behavior Data: Popularity, GRU and XLNet under Growing
Data and Changing Resources
**Class / group:** MSIS406.R12.CTTT · Group 9 · Instructor: Dr. Phạm Đỗ Kim Chi

How to read this file: each section lists **Write** (what the text says), **Show** (table or figure) and, where it
matters, **Dig into** (the analysis that makes the section more than a description). Numbers marked `[AVAILABLE]` are
in the repo; `[PENDING: owner]` waits for input; `[DECIDE: owner]` needs a protocol decision.

---

## A. Where the team stands (21/11/2026, `origin/main` and member branches)

| Member | Done | Not done / blocked |
| --- | --- | --- |
| TV1 data | Four weekly subsets; **official experiment data selected 21/11: cuDF cleanup of the raw week** (`data/clean/e2-weekly/<subset>/` on the VM); NVTabular workflow, sequences and day_index splits for 10/25/50/100%; per-subset profiles; preprocessing timings for the four sizes; E4 CSV/Parquet smoke (`docs/weekly_workflow.md`, `data/manifests/e2_preprocessing_verified.json`, `e4_preprocessing_smoke.json`) | Split counts of the official cuDF run not found in the repo manifests (the split manifest in the repo is the DuckDB comparison set) |
| TV2 models | Popularity, GRU, XLNet scripts; 29 local tests pass; experiment matrix of 11 runs; protocol (test D after freezing the configuration) | No real-data model run yet: **blocked by SSH access to the VM** (`metrics/tv2-real-smoke-20261121/status.json` on the TV2 branch). Fixed validation/test for E2 not decided |
| TV3 environment | Runtime verified on AWS: Ubuntu 22.04.5, Tesla T4 15,360 MiB, 8 vCPU, 31 GiB RAM, Merlin PyTorch 23.12 (`environment/README.md`) | No benchmark run on real data yet; warm-up/cache policy not fixed |
| TV4 demo | Output contract and demo data export on `main` | Demo on real predictions waits for model runs |

Consequence for the report: Chapters 1–4 can be written now with real numbers; Chapter 5 waits for the model runs
and the TV2 metrics package (deadline plan: E1 22/11, E2 23/11, E3 + E5 24/11, E4 25/11, package 27/11).

The DuckDB monthly cleanup used in the 20/11 outline is now a **comparison set** only; it stays the source of the shared
monthly first-seen lookup. All dataset numbers below use the official cuDF weekly run unless stated.

## B. Storyline and what to dig into

The course and the lecturer ask for the effect of **data size and resources on the system**, with analysis, not only
model scores. Six findings already visible in the data are worth building the report around:

1. **Fixed cost dominates preprocessing at small sizes.** 10× more events (0.88 M → 8.83 M) only makes preprocessing
   1.5× longer (30.4 s → 45.4 s). The NVTabular workflow fit takes ~20–26 s at every size, so cost per million events
   falls from ~34 s to ~5 s. → Ch. 5.1.2, 5.1.5, 5.2.1. *(TV1 manifest, one run, cache not controlled — confirm in the
   TV2 package before quoting as E2/E5.)*
2. **The candidate catalog grows with the data.** 63,398 products at 10% → 118,333 at 100% (+87%). A larger catalog
   makes top-20 ranking harder, so E2 accuracy mixes "more training data" with "harder task" and "different test
   sessions". → Ch. 3.2, 5.1.2, 5.2.2; supports the fixed validation/test question.
3. **After repeat removal the sequences are almost only views.** Raw week: ~96% view. After cleanup: 99.98% view
   (100%: 6,389,507 view, 795 cart, 626 purchase). A cart or purchase usually follows a view of the same product and is
   removed as a consecutive repeat. Analysis by target event type has almost no cart/purchase targets. → Ch. 2.3,
   5.2.2 (answers lecturer point 4 with evidence).
4. **Half of the sessions are dropped by the ≥ 2 interaction rule.** 48.6% of sessions have one item after cleanup
   at every size; 96,433 of 187,563 sessions remain at 10%. → Ch. 2.2.2, 2.4.
5. **Subsets keep the same shape.** Session length after cleanup: median 2, p90 8, 1.67% with ≥ 20 items at all four
   sizes; 557–565 of 565 category IDs and 2,277–2,640 brands covered. Product coverage grows (long tail). → Ch. 2.2.3.
6. **The final test set at 10% is small.** Test partition D has ~1,300 sessions at 10% (~13,000 at 100%) in the
   comparison split; Recall@20 differences of 1–2 points between models may be within noise. → Ch. 3.4, 5.1.1, 5.2.3.

Plus, from the E4 smoke (not official): Parquet is 4.55× smaller than CSV and reads faster, but reading is < 1% of
preprocessing time on the GPU pipeline, so the end-to-end difference is small. → Ch. 5.1.4.

## C. Structure decisions (team proposal, optimised)

| Part | Keep / add / merge | Reason |
| --- | --- | --- |
| Chapters 1–6 of the team proposal | **Keep** headings and order | Cover the content the course asks for (`docs/course_requirements.txt` §6–7) and the lecturer's e-mail (table D) |
| Related Works | **Merge**, no separate chapter | Course: prioritise results over theory. Papers cited in 1.1 and 3.1.x; NVIDIA reuse in 1.3 and 4.1.1 |
| 6.3 Reproducibility | **Add** (Future Works → 6.4) | TV5 task "results, limitations and reproducibility"; deliverable "README chạy lại" (`AGENTS.md` §13) |
| 2.4 vs 4.1.1 | Keep both, split content | 2.4 = data steps; 4.1.1 = code and run architecture |
| 5.1.3 E3, 5.1.4 E4 | Keep, optional | Lecturer: not all experiments are mandatory; if not run, keep the heading and state the reason |
| 3.2 | Keep, content pending | Fixed validation/test for E2 waits for TV2 |
| 5.2.3 vs 6.2 | Keep both, split content | 5.2.3 = what the numbers can and cannot show; 6.2 = short list referring to 5.2.3 |

## D. Lecturer feedback (e-mail 20/11/2026) → where it is addressed

| # | Feedback | Section |
| --- | --- | --- |
| 1 | Keeping whole sessions and testing 10/25/50/100% fits next-item prediction | 2.2.1 |
| 2 | State on **which data** the percentages are computed | 2.2.1 |
| 3 | Subsets must be diverse and representative: show statistics and explain the choice | 2.2.2, 2.2.3 |
| 4 | Mostly `view` events: no need to rebalance, but analyse the effect on results | 2.3, 5.2.2 |
| 5 | Train/validation/test split must avoid data leakage | 3.2 |
| 6 | For the training-size study, keep validation/test fixed and change only the train size | 3.2, 4.3, 5.1.2 |
| 7 | Report users, sessions, events, products and the split | 2.2.2, 3.2 |
| 8 | Public cloud GPU VM + Ubuntu + Docker + Transformers4Rec allowed; cloud not mandatory | 4.1.2 |
| 9 | Focus on the effect of data size on processing time, training time and resource use | 4.2, 5.1.2, 5.1.5, 5.2.1 |
| 10 | Not all experiments are mandatory; each chosen one needs comparisons and comments | 4.3, 5.1 |
| 11 | The goal is the workflow and its analysis, not the largest data or the most complex model | 1.2, 6.1 |

## Conventions
- English; ~10–12 pages of body text on the group template (Google Docs report linked in the team sheet).
- Dataset numbers cite their manifest. Experiment numbers (E1–E5) come only from the official TV2 metrics package,
  with `run_id`, config, unit and source log. Never report toy or NVIDIA tutorial numbers as results.
- Table templates for Chapter 5: `reports/tables/` (see `reports/README.md`). Official figures: TV4.

---

## ABSTRACT  (150–200 words, write last)
- Write: context (short, often anonymous sessions) → what we built (pipeline on the first week of October 2019 from
  the Kaggle "eCommerce Behavior Data from Multi-Category Store", Popularity / GRU / XLNet, Recall@20 and NDCG@20) →
  system side (E1–E5 on a cloud GPU VM with Docker + NVIDIA Merlin) → two sentences of key findings
  `[PENDING: TV2 package]` → tools.

## CHAPTER 1. INTRODUCTION  (≈1 page)

### 1.1. Background and Problem Statement
- Write: why session-based recommendation (anonymous users, no long history); why this is a Big Data problem — one
  month is a 5.67 GB CSV (5,668,612,855 bytes), 42,448,764 events, 3,022,290 users, 9,244,421 session IDs
  `[AVAILABLE: data/raw_audit.csv]`; problem definition: given the item prefix of a `user_session`, return the top-20
  products; target = next real item (A → B → C ⇒ predict D) (`docs/modeling/next_item_problem.md`).
- Write: prior work in two or three sentences — GRU4Rec (Hidasi et al., ICLR 2016); Transformer-based sequential
  recommendation: BERT4Rec (Sun et al., CIKM 2019), Transformers4Rec (de Souza Pereira Moreira et al., RecSys 2021).
- Show: Figure 1.1 — one session as a sequence, prefix → target, with a top-20 list.
- Avoid: claims about CTR/conversion or that pandas "cannot" handle the data (not measured).

### 1.2. Objectives and Research Questions
- Write: objective as the course states it — choose suitable data, build a processing pipeline, deploy and
  experiment, analyse how data size and resources affect the system.
- Show: RQ list — RQ1 (E1) which model ranks better and at what cost · RQ2 (E2) how each pipeline stage reacts to more
  data · RQ3 (E3) how training batch size changes time, throughput and memory · RQ4 (E4) CSV or Parquet · RQ5 (E5)
  runtime per million events and the bottleneck stage.

### 1.3. Scope and Contributions
- Write: data scope (`2019-Oct.csv`, 2019-10-01 00:00:00 – 2019-10-07 23:59:59 UTC; view, cart, purchase); models and
  metrics; out of scope (feature ablation, extra models, online serving, cold start, rebalancing).
- Write: reused — NVIDIA Merlin Transformers4Rec notebooks 01–03 at commit `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`
  (Apache-2.0); added by the team — session-level stable-hash sampling at four sizes, a shared evaluation protocol and
  catalog for three models, the Popularity baseline, a benchmark collector, E1–E5 on a cloud GPU VM, the demo.

## CHAPTER 2. DATASET AND PREPROCESSING  (≈2 pages)

### 2.1. Dataset Overview and Big Data Characteristics
- Write: source (REES46 Open CDP via Kaggle), one row = one view / cart / purchase with time, product, category,
  brand, price, user, session; data dictionary of the 9 columns `[AVAILABLE: docs/data_dictionary.md]`.
- Write: October 2019 audit `[AVAILABLE: data/raw_audit.csv]` — 42,448,764 events; 166,794 products; 624 category IDs;
  3,445 brands; 3,022,290 users; 9,244,421 sessions; view 96.07% / cart 2.18% / purchase 1.75%; missing
  `category_code` 31.8%, `brand` 14.4%; 1.13–1.64 M events per day.
- Show: Table 2.1 — 5V: Volume 5.67 GB, 42.4 M rows · Velocity daily event log (processed in batch) · Variety 3 event
  types, 624 categories, 3,445 brands, price, time · Veracity missing category/brand, null sessions, consecutive repeats
  · Value offline-measurable next-item quality and system cost.
- Show: Figure 2.1 — events per day in October (the first week is a typical slice, not a peak).

### 2.2. Subset Selection
#### 2.2.1. Sampling Population and Sampling Rule
- Write: population (lecturer point 2) = every event of 1–7 Oct 2019 (UTC) with a non-null `user_session`:
  8,829,314 events, 1,877,365 sessions `[AVAILABLE: data/manifests/raw_subset_counts.csv]`.
- Write: rule = SHA-256 stable hash of the original session ID (seed 42), nested 10 ⊂ 25 ⊂ 50 ⊂ 100%; all events of a
  selected session kept; rows never sampled (`docs/session_sampling.md`). The percentage is a share of **sessions**;
  "100%" = the whole eligible first week, not the month.
- Write: why it fits — whole sessions keep the target; nested sizes give a growing load with one configuration; no
  filtering on category, brand or user type.
- Show: Figure 2.2 — month → week → hash → four nested subsets, with session counts.

#### 2.2.2. Subset Statistics
- Show: Table 2.2 (raw sample and after cleanup, `[AVAILABLE: data/manifests/raw_subset_counts.csv,
  e2_preprocessing_verified.json]`):

| Subset | Raw events | Events after cleanup | Sessions | Users | Products (= catalog) | Sequences (≥ 2 items) |
| --- | --- | --- | --- | --- | --- | --- |
| 10% | 882,808 | 638,089 | 187,563 | 163,846 | 63,398 | 96,433 |
| 25% | 2,213,138 | 1,601,068 | 469,728 | 356,266 | 87,247 | 241,715 |
| 50% | 4,421,037 | 3,197,007 | 938,071 | 601,598 | 103,940 | 482,239 |
| 100% | 8,829,314 | 6,390,928 | 1,877,365 | 957,537 | 118,333 | 965,304 |

- Write: session ratio vs event ratio are close (0.0999 vs 0.1000 at 10%) — "close", not "equal"; cleanup removes
  ~28% of events at every size; the ≥ 2 rule keeps ~51% of sessions.
- Dig into: the catalog grows +87% from 10% to 100% while sessions grow 10× (finding 2) — this is why E2 accuracy
  must be read together with catalog size.

#### 2.2.3. Diversity and Representativeness
- Show: Table 2.3 — coverage vs the full week after cleanup: category IDs 557 / 560 / 562 / 565; category codes 123 at
  all sizes; brands 2,277 / 2,455 / 2,572 / 2,640; products 54% / 74% / 88% / 100% of 118,333
  `[AVAILABLE: e2_preprocessing_verified.json]`.
- Show: Figure 2.3 — session-length histogram of the four subsets on one chart (median 2, p90 8, 1.67% ≥ 20 items at
  every size).
- Write: subsets keep the category/brand mix and the session-length shape; what grows is the product long tail. What
  no subset represents: other weeks, months and seasonality.
- Optional: missing `category_code` / `brand` share per subset (≈34% / 15% in the DuckDB comparison profiles,
  `data/manifests/weekly_subset_profiles.json`) `[PENDING: TV1 for the cuDF run]`.

### 2.3. Event-Type Distribution and Imbalance
- Show: Table 2.4 — event mix raw week (view 96.21% / cart 2.07% / purchase 1.72%,
  `[AVAILABLE: data/raw_audit.csv raw_week]`) vs after cleanup (100%: view 6,389,507 = 99.98%, cart 795, purchase 626;
  same pattern at 10/25/50%) `[AVAILABLE: e2_preprocessing_verified.json]`.
- Write: why the shares collapse — the notebook 01 rule removes consecutive repeats of the same product, and a cart
  or purchase usually follows a view of that product; the model therefore learns almost only from view sequences.
- Write: no rebalancing (allowed by the lecturer); the task is the next interaction of any type.
- Dig into (lecturer point 4): with < 0.03% cart/purchase targets, a per-event-type metric is not meaningful; instead
  report the target event mix of test D and discuss what the model can and cannot learn (purchase intent is mostly
  invisible) `[PENDING: TV2 target mix of test D]`.

### 2.4. Preprocessing Pipeline
> Data processing steps only; code and run architecture are in 4.1.1.
- Show: Figure 2.4 — `2019-Oct.csv` → week filter + stable-hash sampling → cuDF cleanup on the raw week (UTC timestamp,
  null sessions dropped, sort, consecutive repeats removed, join of the monthly first-seen lookup) → NVTabular
  workflow fitted on the whole week of the subset → group by session, `ListSlice(-20, pad=True)`, ≥ 2 interactions →
  `day_index` → ~80/10/10 split per partition → Parquet + schema + mapping + catalog + manifest.
- Write: the data decision of 21/11 — official experiment data = cuDF cleanup on the raw week; the earlier DuckDB
  monthly cleanup is kept for comparison (8–23 events difference per subset, `docs/weekly_workflow.md`) and remains
  the source of the monthly first-seen lookup (166,794 products, 1.516 s, reported once).
- Write: workflow fitted before the split on the whole week of each subset (padding 0, null 1, OOV 2, known items from
  3), fixed across partitions; models see encoded IDs, outputs are mapped back to original product IDs.
- Show: Table 2.5 — rows in/out per step for the 10% and 100% subsets (raw → after cleanup → sessions → sequences).

## CHAPTER 3. METHODS AND EVALUATION PROTOCOL  (≈1.5 pages)

### 3.1. Recommendation Models
> Each model opens with one or two sentences on the work it comes from (cited), then our configuration.
#### 3.1.1. Popularity
- Write: cumulative count of real interactions in train partitions 1…t (each counted once, not per epoch); unseen
  catalog items score 0; ties by ascending encoded ID; same list for every session. Built by the team (not in
  notebook 03).
#### 3.1.2. GRU
- Write: origin GRU4Rec; ours follows Transformers4Rec notebook 03 (embedding → MLP → GRU d_model 128, 1 layer →
  next-item head; causal training; lr 0.00071) — do not call it "GRU4Rec".
#### 3.1.3. XLNet
- Write: XLNet block (Yang et al., NeurIPS 2019) in Transformers4Rec, trained with item-level masked language modelling
  (as in BERT4Rec), not the paper's permutation objective; d_model 192, 2 layers, 4 heads; evaluated on the last item;
  lr 0.000666.
- Show: Table 3.1 — configuration of the three models: input, sequence length 20, train/eval batch 256/32, 3 epochs,
  learning rate, seed, parameters `[DECIDE: TV2 confirms the values used]`.

### 3.2. Data Splitting and Leakage Considerations
> Final content waits for TV2 on the fixed validation/test question.
- Write: sessions grouped first; `day_index` from the first event (source formula, not a calendar day); 7 partitions;
  inside each, ~80/10/10 train/validation/test (GPU seed 1, sorted by `user_session`).
- Show: Table 3.2 — sessions per split and per subset; test partition D. Comparison split (DuckDB set): test D =
  1,337 / 3,266 / 6,427 / 13,052 sessions for 10/25/50/100% (`data/manifests/weekly_splits_verified.json`)
  `[PENDING: TV1 counts of the official cuDF split]`.
- Write (leakage, never "leakage-free"): weights and Popularity counts learn only from train partitions; test D used
  once after the configuration is fixed; target hidden by causal shift / masking. Limitation: vocabulary and feature
  statistics are fitted on the whole week before the split.
- Dig into (lecturer point 6) `[DECIDE: TV2 before E2]`: today each subset has its own test D, its own catalog and its
  own number of test sessions. Proposal: evaluate every E2 size on one frozen validation/test set (e.g. the
  validation/test sessions of partition D of the 10% subset, which exist in all nested subsets) and vary only the
  training sessions. Time and memory columns are unaffected.

### 3.3. Training and Validation Procedure
- Write: daily fine-tuning — train on partition t, validate on t+1, weights continue, LR scheduler reset per day;
  configuration chosen on validation only; final test D with the checkpoint trained on 1…D−1; E3 compares on
  validation D.
- Show: Figure 3.1 — timeline of partitions 1…7 with train/validation pairs and the final test D.

### 3.4. Evaluation Rules and Metrics
- Write: target = last real item; shared catalog = real products in the subset's weekly vocabulary; seen items
  allowed; technical tokens excluded; K = 20; one aggregation for three models.
- Write: Recall@K = (1/|S|) Σ 1[rank ≤ K]; NDCG@K = (1/|S|) Σ 1/log2(rank + 1) if rank ≤ K else 0 (single target →
  IDCG = 1); sum over valid sessions / number of valid sessions.
- Dig into (finding 6): report `n_sessions` with every score; with ~1,300 test sessions at 10%, a 1–2 point gap may be
  noise — add a 95% bootstrap interval if TV2 agrees `[DECIDE: TV2]`.

## CHAPTER 4. SYSTEM SETUP AND EXPERIMENTAL DESIGN  (≈1.5 pages)

### 4.1. System and Runtime Setup
#### 4.1.1. System Implementation
> Code and run architecture only — do not repeat the data steps of 2.4.
- Write: what is reused from NVIDIA (notebooks 01–03 at the pinned commit) and what the team changed (sampling, split
  protocol, shared catalog, Popularity, measurement) (`docs/references.md`, `docs/preprocessing_review.md`).
- Show: Figure 4.1 — architecture: Git (code, configs, manifests) → AWS GPU VM → Docker (Merlin) → pipeline / models /
  evaluation scripts → benchmark collector (`run.json`, `metrics.json`, logs) → tables, figures, report, demo.
- Write: run flow — `configs/experiments.json` → `scripts/runs/run_experiments.py` → `benchmark/collect.py` →
  `evaluation/run_neural.py`, `run_popularity.py`; Git keeps code, configs, manifests, metrics and small logs; raw
  CSV, large Parquet and checkpoints stay on the VM and are referenced by manifests.
#### 4.1.2. Deployment Environment
- Show: Table 4.1 `[AVAILABLE: environment/README.md]` — AWS VM, Ubuntu 22.04.5 LTS; Tesla T4 15,360 MiB (compute
  7.5); Intel Xeon Platinum 8259CL, 8 vCPU; 30.98 GiB RAM; driver 570.172.08; CUDA 12.1 in the container; Docker
  28.4.0; image `nvcr.io/nvidia/merlin/merlin-pytorch:23.12` (digest pinned); Python 3.10.12; PyTorch 2.1.0a0;
  Transformers4Rec 23.12.00; cuDF 23.04.00; NVTabular 23.08.00. Instance type and cost per hour `[PENDING: TV3]`.
- Write: why a cloud GPU — NVTabular and GRU/XLNet need an NVIDIA GPU; one shared, reproducible image; allowed but not
  required by the lecturer (point 8).

### 4.2. Benchmark Measurement
#### 4.2.1. Processing and Training Time
- Write: stages measured separately — read, prepare (to GPU, timestamp, sort, repeat removal, lookup join, write),
  workflow fit, split; shared first-seen reported once; training incl. input scan; inference =
  `full_evaluation_wall_v1` (read, prepare, predict, rank, aggregate, write) and ms/session
  (`docs/modeling/inference_timing.md`).
#### 4.2.2. Memory Usage and Throughput
- Write: peak process-tree RSS (collector, 0.05 s sampling, may double-count shared pages); peak CUDA reserved memory;
  sessions/s; units MiB/GiB.
#### 4.2.3. Measurement Conditions and Run Status
- Write: same VM and image; one run per configuration; warm-up/cache policy `[PENDING: TV3]` (the preprocessing
  timings of 21/11 are one sequential run per subset, cache not controlled); status pass / fail / OOM / timeout kept;
  failed runs reported, not deleted.

### 4.3. Experiment Designs
- Show: Table 4.2 (`configs/experiments.json`, `docs/experiment_matrix.md`) — question, variable, fixed settings,
  outputs: E1 Popularity / GRU / XLNet on 10%, test D · E2 GRU on 10/25/50/100%, test D (frozen test set if adopted) ·
  E3 GRU 10%, train batch 32 vs 128, validation D · E4 CSV vs Parquet, raw 10% week subset, same content · E5 seconds
  per million events from E2, no new runs.
- Write: E2 and E5 are the core experiments (lecturer point 9); E3 and E4 optional (point 10); why batch size is the
  resource variable (it directly sets GPU memory and throughput on one GPU; CPU/RAM limits not varied).

## CHAPTER 5. RESULTS AND DISCUSSION  (≈3 pages, largest chapter)
Every value from the official TV2 metrics package; every table/figure cites run IDs; failed/OOM runs shown with status.
Pattern per experiment: setup (one line) → table → figure → analysis (what changed, how much, why, which limitation).

### 5.1. Experimental Results
#### 5.1.1. E1: Model Comparison
- Show: Table 5.1 — Recall@20, NDCG@20, n_sessions, training time, inference ms/session, peak CPU and GPU memory for
  Popularity, GRU, XLNet (runs e1-popularity-010, e1-gru-010, e1-xlnet-010) `[PENDING: TV2]`.
- Show: Figure 5.1 — quality vs cost (Recall@20 against training time).
- Dig into: gain over Popularity per second of training and per GiB of GPU memory; whether the GRU–XLNet gap is larger
  than the uncertainty of ~1,300 test sessions.
#### 5.1.2. E2: Dataset Size and System Performance
- Show: Table 5.2 — per subset: events, sessions, catalog size, read / prepare / workflow / split / training /
  inference time, peak memory, Recall@20 (frozen test set if adopted) `[PENDING: TV2/TV3]`.
- Show: Figure 5.2 — stacked bars of stage times per subset. Preliminary preprocessing values (TV1 manifest, not yet
  E2): total 30.45 / 34.09 / 37.86 / 45.41 s; workflow fit 20.57 / 22.14 / 23.24 / 25.89 s; split 8.51 / 10.01 /
  11.87 / 14.84 s; prepare 1.37 / 1.94 / 2.75 / 4.69 s; read 0.17 / 0.37 / 0.74 / 1.36 s.
- Dig into: which stages are fixed cost (workflow fit) and which grow with data (read, prepare, split, training);
  Recall vs data size with the catalog-size caveat (finding 2).
#### 5.1.3. E3: Training Batch Size
> Optional — if not run in time, keep the heading and state the reason.
- Show: Table 5.3 — batch 32 vs 128: training time, sessions/s, peak GPU memory, validation Recall@20 `[PENDING]`.
- Dig into: speed–memory trade-off and whether quality changes with batch size at a fixed number of epochs.
#### 5.1.4. E4: CSV versus Parquet
> Optional — if not run in time, keep the heading and state the reason.
- Show: Table 5.4 — file size, read time, preprocessing time, reader memory for the same 10% raw week subset
  `[PENDING: TV3 official run]`. Smoke on 21/11 (one run, cache not controlled, `e4_preprocessing_smoke.json`):
  118,113,591 B vs 25,945,758 B (4.55× smaller); read 0.166 s vs 0.103 s; preprocessing 31.9 s vs 31.5 s.
- Dig into: storage gain vs end-to-end gain — reading is < 1% of preprocessing on the GPU pipeline.
#### 5.1.5. E5: Scalability and Bottlenecks
- Show: Figure 5.3 — seconds per million events and composed runtime vs events; Table 5.5 — per stage share of the
  total `[PENDING: TV2 from E2]`.
- Write: composed seconds = raw read + preprocessing + training + final evaluation; seconds per million events =
  composed seconds × 10⁶ ÷ measured weekly events; shared first-seen once; `partial` if an E2 run is missing.
- Dig into: bottleneck stage at 100% and the projected cost of the full month (42.4 M events), stated as an
  extrapolation.

### 5.2. Discussion
#### 5.2.1. Effects of Dataset Size on Time and Memory
- Write: growth of each stage and of peak memory with events (sub-linear, linear, or worse); fixed vs variable cost;
  what to optimise first.
#### 5.2.2. Recommendation Quality and Event-Type Imbalance
- Write: model differences; effect of the view-only sequences (finding 3) and of the growing catalog (finding 2) on
  Recall/NDCG; what the scores mean for an online store.
#### 5.2.3. Interpretation Limits
- Write: one run per configuration; small test set at 10%; preprocessing fitted before the split; 7 days only;
  product ID only; batch size the only resource variable; cache not controlled in preprocessing timings; RSS
  double-counting.

### 5.3. Recommendation Demo
- Show: Figure 5.4 — screenshot: one session's history with original product IDs, actual next item, top-20 of each
  model with hit and rank; predictions computed offline `[PENDING: TV4 on real output]`.

## CHAPTER 6. CONCLUSION  (≈0.75 page)
### 6.1. Main Findings
- Write: one sentence per research question with its key number; one paragraph on how data size and resources affect
  the system and which stage to optimise first.
### 6.2. Limitations
- Write: short list referring to 5.2.3, plus failed/OOM runs and the fit-before-split vocabulary.
### 6.3. Reproducibility
- Write: commands from raw CSV to subsets, cuDF cleanup, workflow, split, training, evaluation and metrics; config
  files; seeds (hash 42, split 1); pinned NVIDIA commit and Docker image digest; manifests and checksums; one re-run by
  another member and its result `[PENDING: TV3 re-run log]`.
### 6.4. Future Works
- Write: side features (category, brand, price, recency); a cleanup rule that keeps cart/purchase signals; longer
  periods and other months; more resource settings (CPU/RAM limits, workers, multi-GPU); past-only vocabulary and cold
  start; online inference.

## Back matter (group template)
- LIST OF REFERENCES — IEEE, numbered in order of first citation (dataset, GRU4Rec, Cho et al. GRU, XLNet,
  Transformers4Rec, BERT4Rec, Järvelin & Kekäläinen NDCG, NVIDIA repo commit, tool docs); verify every field.
- REPORT REVIEW CONFIRMATION MINUTES.

## Open items (owners)
1. `[DECIDE: TV2]` Frozen validation/test set for E2 (3.2) — before E2 runs.
2. `[DECIDE: TV2]` Bootstrap interval or not (3.4, 5.1.1).
3. `[PENDING: TV2]` Target event mix of test D (2.3, 5.2.2); confirmed model configuration (3.1).
4. `[PENDING: TV1]` Split counts and missing-value shares of the official cuDF run (2.2.3, 3.2).
5. `[PENDING: TV3]` VM access for TV2, warm-up/cache policy, instance type and cost, re-run log (4.1.2, 4.2.3, 6.3).
