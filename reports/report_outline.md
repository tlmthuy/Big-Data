# Report outline (English)

**Working title:** SESSION-BASED NEXT-ITEM RECOMMENDATION ON ECOMMERCE BEHAVIOR DATA: POPULARITY, GRU AND XLNET
UNDER GROWING DATA AND CHANGING RESOURCES

**Base template:** the course sample report "Realtime Log Anomaly Detection & Log Insight Streaming"
(MSIS405, Group 10). We follow its skeleton — header block, ABSTRACT, INDEX TERMS, six Roman-numbered sections
(I Introduction, II Related Works, III Dataset, IV Methods, V Experiments and Results, VI Conclusion),
ACKNOWLEDGMENT, numbered REFERENCES. Sub-sections that **match the sample by name**: I.A–D, II.A–B, III.A–B,
IV.A, V (processing model, system design, user interface), VI.A Challenges, VI.B Achievements,
VI.C Development directions (same order as the sample). IV.B is renamed from the sample's topic-specific method
("Pattern recognition for log analytics") to "Data processing pipeline" for our recommendation topic.
Sub-sections **added by us** (because the course requires them and the sample has no measured results):
III.C–E, IV.C, V.A, V.C–E, VI.D Limitations, VI.E Reproducibility, Appendix. The sample's use-case and database
diagrams are replaced by a demo use-case figure and an artifact-layout figure (V.B). Re-check every sub-section
against the PDF before the final layout.

**Where we deliberately go further than the sample:** the sample has almost no measured results. The course brief
asks to prioritise experiments, results and analysis, so Section V (Experiments and Results) is the largest
section here (~40% of the pages) and Section IV.A (theory) is kept short.

## Conventions

- Format: two-column journal style, ~9–10 pages, English. Figures numbered "FIGURE n:", tables "TABLE n:".
  Page footer: `<course code> – Group <n>`; running header: `Author et al.: <short names>` (as in the sample).
- Every number has a source. **[AVAILABLE]** = already in the repo (path given), still re-check before final.
  **[PENDING: X]** = wait for input X. Never type numbers from the NVIDIA tutorial or toy runs as our results.
- Owner = who provides the content; TV5 writes the final text.
- Pages = target length in the final two-column layout.

---

## Header block  (owner: TV5 · 0.2 page)

- Institution line: UNIVERSITY OF INFORMATION TECHNOLOGY / FACULTY OF INFORMATION SYSTEMS (confirm faculty).
- Title (above).
- Authors with superscript numbers, faculty and e-mail, same format as the sample:
  `NAME1, NAME2, ... , 1Faculty of ..., University of Information Technology, (e-mail: ...)`. 5 members.

## ABSTRACT  (owner: TV5 · 150–200 words · write last)

One paragraph, in this order (the sample follows the same order):

1. Context — eCommerce sessions are short and often anonymous; recommending the next item from in-session behavior.
2. What we built — a reproducible pipeline on the Kaggle "eCommerce Behavior Data from Multi-Category Store"
   (first 7 days of October 2019) that turns raw events into session sequences and evaluates three recommenders:
   Popularity, GRU and XLNet (Transformers4Rec), with Recall@20 and NDCG@20.
3. System side — five experiments: model comparison (E1), data size 10–100% (E2), resources (E3),
   CSV vs Parquet (E4), scalability per million events (E5), run on a cloud GPU VM with Docker + NVIDIA Merlin.
4. Key findings — 2 sentences with the main numbers. **[PENDING: TV2 metrics package]**
5. Tools — DuckDB, NVTabular/cuDF, PyTorch, Transformers4Rec, Docker, cloud GPU VM, React demo.

## INDEX TERMS

Session-based recommendation, next-item prediction, GRU, XLNet, Transformers4Rec, NVTabular, Parquet,
scalability, cloud GPU.

---

## I. INTRODUCTION  (≈1 page)

### A. REASONS FOR CHOOSING THE TOPIC
Bullets in the same style as the sample (bold lead-in + 2–3 sentences each):

- **Wide applicability:** next-item recommendation is used in eCommerce, media, news; session-based methods work
  even for anonymous users with no long history.
- **Data volume (Big Data need):** one month of one store is a 5.67 GB CSV (5,668,612,855 bytes) with 42,448,764
  events, 3,022,290 users and 9,244,421 session IDs **[AVAILABLE: data/raw_audit.csv,
  data/manifests/raw_audit_manifest.json]**. This scale motivates our technical choices: columnar storage, GPU ETL
  and session-level sampling. (Do not claim pandas "cannot" handle it — we did not measure that.)
- **Business value:** top-K recommendation quality can be measured offline with Recall@K/NDCG@K; a cheap popularity
  baseline is the reference that neural models must be compared against. (No claim about CTR/conversion — not
  measured.)
- **Technical challenges:** building time-ordered session sequences and stating clearly what the preprocessing sees
  (fitted on the whole week before the split), comparing models fairly under one protocol, and measuring how
  runtime/memory change with data size, resources and storage format.

### B. SCOPE OF RESEARCH
One paragraph + bullet list:
- Task: given the item prefix of one `user_session`, return the top-20 products; the target is the next real item.
  Example: A → B → C ⇒ predict D.
- Data: `2019-Oct.csv`, 2019-10-01 00:00:00 to 2019-10-07 23:59:59 UTC, event types view/cart/purchase.
- Models: Popularity (baseline), GRU, XLNet; only product ID as input.
- Metrics: Recall@20, NDCG@20 plus training time, inference time, memory.
- Experiments E1–E5 (one line each).
- Out of scope: feature ablation, extra models or cloud services, online/real-time serving, cold-start benchmark.
- **Goal statement (course objective, say it explicitly):** the aim is not the best algorithm or the largest data,
  but to select suitable data, build a processing pipeline, deploy and experiment, and analyse **how data size and
  computing resources affect system performance**.
- **What we reuse vs. what we add** (course encourages reusing known models/code and extending towards Big Data &
  Cloud). One short paragraph + 2 bullets:
  - Reused: GRU/XLNet models and ETL steps from NVIDIA Transformers4Rec tutorial notebooks 01–03 (pinned commit,
    Apache-2.0); standard metrics Recall/NDCG.
  - Added by the team: session-level stable-hash sampling at 4 sizes, monthly cleanup in DuckDB, a shared evaluation
    protocol and catalog for 3 models, the Popularity baseline, a benchmark collector, the five system experiments
    E1–E5 on a cloud GPU VM, and the offline demo.

### C. STUDY PARTICIPANTS
The sample lists stakeholder groups. We list (1) the team roles and (2) the intended stakeholders.

- Team table (TABLE 1): TV1 Data & preprocessing · TV2 Model, experiments & evaluation · TV3 Environment & runs ·
  TV4 Demo & report support · TV5 Report & results — name + main deliverables. Source: `AGENTS.md` §9.
- Stakeholders (short bullets, sample style): data engineers (pipeline), ML engineers/researchers (models,
  protocol), platform/DevOps (cloud GPU, Docker, cost), product/business owners (recommendation value),
  end users (shoppers receiving the top-20 list).

### D. TOOLS USED
Bulleted list "**Tool:** role in our project" (same format as the sample):
- **Python** — all scripts (pipeline, evaluation, benchmark collector).
- **DuckDB** — CPU processing of the monthly CSV: UTC timestamps, null-session removal, repeated-item cleanup,
  monthly first-seen table.
- **NVIDIA NVTabular / cuDF** — GPU ETL: categorify, feature statistics, Groupby to session sequences, Parquet.
- **PyTorch + Transformers4Rec** — GRU and XLNet next-item models, adapted from NVIDIA tutorial notebook 03.
- **Apache Parquet / PyArrow** — columnar storage for sequences; compared with CSV in E4.
- **Docker + NVIDIA Merlin image** — reproducible GPU runtime.
- **Public cloud GPU VM (Ubuntu)** — training/benchmark machine. **[PENDING: TV3 provider + instance type]**
- **Git/GitHub** — branches per member, manifests, handoff log.
- **React + Vite** — offline demo UI.
- **Visual Studio Code, Kaggle, Google Sheets/Docs** — development, dataset source, task tracking.

---

## II. RELATED WORKS  (≈1 page)

Opening paragraph (3–4 sentences): from popularity/item-kNN baselines to RNN and Transformer models for sessions;
GPU data pipelines make large-scale training practical.

### A. RESEARCH PAPERS
Same format as the sample: numbered title + authors + [ref], then **Main Content** and **Contribution**.
We add one line **Relevance to our project**.

1. **"Session-based Recommendations with Recurrent Neural Networks"** — Hidasi et al., ICLR 2016 (GRU4Rec).
   Main content: GRU over the click sequence of a session, session-parallel mini-batches, ranking losses.
   Contribution: first strong RNN approach for anonymous sessions. Relevance: our GRU is *inspired by* GRU4Rec but
   *implemented* following Transformers4Rec notebook 03 (embedding → MLP → GRU → next-item head, cross-entropy,
   causal training) — say both, do not call our model "GRU4Rec".
2. **"XLNet: Generalized Autoregressive Pretraining for Language Understanding"** — Yang et al., NeurIPS 2019.
   Main content: permutation language modelling (PLM) with Transformer-XL for text. Contribution: bidirectional
   context without BERT's mask mismatch. Relevance: we reuse only the **XLNet Transformer block**; our training
   objective is **item-level masked language modelling (MLM)** from Transformers4Rec, not the paper's PLM.
3. **"Transformers4Rec: Bridging the Gap between NLP and Sequential / Session-Based Recommendation"** —
   de Souza Pereira Moreira et al., RecSys 2021. Main content: library that plugs NLP Transformer architectures
   into sequential/session recommendation, with several training objectives (causal LM, MLM, PLM, replacement token
   detection) and side-information fusion; evaluated on eCommerce and news datasets incl. REES46.
   Contribution: in the authors' experiments, **XLNet trained with replacement token detection (RTD)** gave the best
   results on most datasets. Relevance: our GRU/XLNet code and ETL come from this library's tutorial; we use the
   tutorial's **MLM** setting for XLNet (not RTD) — state this as a scope choice. Re-check the claim against the
   paper before final.
4. **"BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer"** —
   Sun et al., CIKM 2019. Main content: bidirectional Transformer trained by masked item prediction (Cloze task).
   Relevance: explains why MLM training differs from last-item evaluation.
5. *(Cut first if space is short)* **"Self-Attentive Sequential Recommendation" (SASRec)** — Kang & McAuley,
   ICDM 2018.

### B. PROJECTS AND IMPLEMENTATIONS
Sample format: name, **Features**, **Benefits**.
- **NVIDIA Merlin Transformers4Rec** (pinned commit `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`, Apache-2.0):
  tutorial notebooks 01 preprocess, 02 ETL with NVTabular, 03 session-based recsys. What we reused, what we changed
  (sampling, split protocol, Popularity baseline, collector). Source: `docs/references.md`, `docs/preprocessing_review.md`.
- **NVTabular / cuDF (RAPIDS)**: GPU dataframe and feature engineering.
- **REES46 / Kaggle dataset release** — the public data we use.

---

## III. DATASET  (≈1.2 pages)

### A. INTRODUCTION
What the data is (behavior logs of a large multi-category online store, collected by REES46 Open CDP, published on
Kaggle), why it suits session-based recommendation (has `user_session`, event order, product IDs, event types).

### B. DESCRIPTION
- TABLE 2 — the 9 columns: name, type, meaning, example. Source: `docs/data_dictionary.md` **[AVAILABLE]**.
- Bullet statistics in the sample's style ("Total number of …"). **[AVAILABLE: data/raw_audit.csv]**
  - Total events (October 2019): 42,448,764; time range 2019-10-01 00:00:00 – 2019-10-31 23:59:59 UTC; 0 invalid timestamps.
  - Distinct products 166,794; categories 624 (`category_id`), category codes 126; brands 3,445.
  - Users 3,022,290; sessions 9,244,421; sessions with null `user_session`: 2 rows.
  - Event types: view 96.07%, cart 2.18%, purchase 1.75%.
  - Missing values: `category_code` 31.8%, `brand` 14.4%.
  - Daily volume in the first week: ~1.13 M – 1.42 M events per day.
- FIGURE 1 — sample raw rows (screenshot/table, like "FIGURE 1: Log data" in the sample).
- FIGURE 2 — events per day for October (bar chart). **[TV4 figure from raw audit]**

### C. 5V ANALYSIS
TABLE 3 — V, evidence, number, implication:
- **Volume:** 42,448,764 rows; `2019-Oct.csv` = 5,668,612,855 bytes ≈ 5.67 GB
  **[AVAILABLE: data/manifests/raw_audit_manifest.json `input_bytes`]** → sampling + Parquet + GPU.
- **Velocity:** events *recorded* per day: ~1.13–1.42 M/day in the first week (check full-month range in
  `data/raw_audit.csv`) → daily partitions and daily fine-tuning. Batch processing, not streaming, in our scope.
- **Variety:** 3 event types, 624 categories, 3,445 brands, numeric price, timestamps.
- **Veracity:** 31.8% missing `category_code`, 14.4% missing `brand`, 2 rows without `user_session`, 11,715,474
  consecutive repeated events removed **[AVAILABLE: data/manifests/timestamp_session_cleanup.json]**. Note the rule:
  an event is removed when its `product_id` equals the previous event of the session **even if the event type
  differs** (e.g. view → cart of the same product keeps only the view). Sessions may cross midnight.
- **Value:** the data lets us measure next-item recommendation quality offline (Recall@20, NDCG@20) and the
  system cost of producing it.

### D. SUBSET SELECTION
- Rule: 7-day window → SHA-256 stable hash on the original session ID (seed 42) → nested 10/25/50/100% →
  keep every event of a selected session → never sample individual rows. Source: `docs/session_sampling.md`.
- **Why this subset fits the task** (course: "explain why the selected data suits the problem") — one paragraph:
  - *Session-level, not row-level:* next-item prediction needs complete, ordered sessions; sampling rows would cut
    sessions and destroy the target. Hashing the session ID keeps every event of a selected session.
  - *Stable hash, nested sizes:* the same session is always in or out, so 10% ⊂ 25% ⊂ 50% ⊂ 100%; E2/E5 then measure
    only the effect of size, not of a different random sample.
  - *7 days:* enough daily partitions for daily fine-tuning (train t → validate t+1) and a final test day, while
    fitting the GPU/time budget; the full month is analysed in the raw audit only.
  - *Not filtered by category/brand/user type:* all categories, brands and event types stay in, so the subset keeps the
    diversity of the store (checked in III.E).
- TABLE 4 — raw subset counts **[AVAILABLE: data/manifests/raw_subset_counts.csv]** (raw weekly events, before
  cleanup and sequence building — say this in the caption). Add columns **categories, brands** per subset
  **[PENDING: TV1 counts]**, as required by `AGENTS.md` §3:

  | Subset | Events | Sessions | Users | Items | Actual event ratio |
  | --- | --- | --- | --- | --- | --- |
  | 10% | 882,808 | 187,563 | 163,847 | 63,398 | 0.1000 |
  | 25% | 2,213,138 | 469,728 | 356,271 | 87,247 | 0.2507 |
  | 50% | 4,421,037 | 938,071 | 601,608 | 103,940 | 0.5007 |
  | 100% | 8,829,314 | 1,877,365 | 957,543 | 118,333 | 1.0000 |

- Add two separate ratio columns (both computed from the CSV, never assumed):
  **session ratio** 0.0999 / 0.2502 / 0.4997 / 1.0 and **event ratio** 0.1000 / 0.2507 / 0.5007 / 1.0.
  Write "the two ratios are close", not "match".
- Notes for the caption: "100%" = every eligible session of the first week, not the whole month. The 100% subset has
  8,829,314 events while the weekly audit counts 8,829,315 — the difference is the one weekly row without
  `user_session` (dropped before sampling). Source: `docs/raw_subsets.md`.
- After-sequence counts per subset (sessions ≥ 2 interactions, vocabulary size) **[PENDING: TV1 ETL]**.

### E. REPRESENTATIVENESS
The course requires the subset to be **diverse and representative** (many groups, labels, features, cases).
- TABLE 5 — per subset: number of categories and brands covered, event-type shares (view/cart/purchase), share of
  sessions with a purchase, session-length distribution (median, p90, share ≥ 20 items), price range.
- FIGURE 3 — event-type, top-10 categories, top-10 brands and session-length histograms: full week vs each subset
  (overlaid or small multiples).
- State the scope of the comparison: raw weekly events (before cleanup) **or** after cleanup/sequence building —
  pick one and write it in the caption.
- One paragraph that answers a **question**, not a pre-written conclusion: "How far is each subset from the full
  eligible week?" Report the observed differences (e.g. max absolute difference in event-type share, in top-10
  category share, in median session length) and only then judge whether the subset is representative.
  Note what no subset can represent (other months, seasonality). **[PENDING: TV1 distributions]**

---

## IV. METHODS  (≈2 pages)

### A. THEORETICAL BASIS  (short: ~0.8 page total)
Same pattern as the sample: concept → "In this project, X is used for:" bullets.
**Length cap: 3–4 sentences (or one formula block) per item.** The course says not to spend too much on theory;
the sample's 3 pages of generic theory (Python, Kafka, AWS) is the part we do not copy.
Budget for all non-result parts (I.D + II + IV.A) ≤ 2.5 pages.

1. **Session-based next-item prediction** — formal definition: session s = (i1, …, in); input prefix (i1…i(n−1)),
   target in; model returns a ranked list of K = 20 items from the candidate catalog.
2. **Popularity baseline** (group-built, not in notebook 03) — cumulative count of every real interaction in the
   train sequences used so far (partitions 1…t, each counted once, not per epoch); catalog items never counted get
   score 0; ties broken by ascending encoded ID; same list for every session.
3. **GRU** — recurrent cell with update/reset gates; embedding → MLP → GRU → prediction head; causal training
   (predict each next item from the past). FIGURE 4: GRU-based architecture (redraw, credit NVIDIA).
4. **XLNet / Transformer** — self-attention over positions; trained with masked language modelling (MLM) on items;
   evaluation always predicts the last item. FIGURE 5: causal vs MLM masking (redraw, credit NVIDIA).
5. **Evaluation metrics** — formulas:
   - Recall@K = (1/|S|) Σ 1[rank(target) ≤ K]
   - NDCG@K = (1/|S|) Σ 1/log2(rank + 1) if rank ≤ K, else 0 (single target → IDCG = 1)
   - Aggregation = sum over valid sessions / number of valid sessions (not mean of batch means).
6. **Columnar storage (Parquet) and GPU dataframes** — why columnar + compression helps reading;
   cuDF/NVTabular run ETL on GPU.
7. **Cloud GPU VM and containers** — pay-per-use GPU, Docker images for reproducibility.

### B. DATA PROCESSING PIPELINE
FIGURE 6 — pipeline diagram (one row of boxes): `2019-Oct.csv` → timestamp UTC → drop null sessions →
monthly sort + remove consecutive repeats → monthly first-seen → week filter → stable-hash sampling →
NVTabular workflow (categorify, features) → Groupby session → `ListSlice(-20)` → `day_index` → split → Parquet +
schema + mapping + manifest. Source: `AGENTS.md` §6.

1. **Preliminary preprocessing (DuckDB CPU, adapted from notebook 01)** — results **[AVAILABLE]**: 42,448,764
   rows in/out of the timestamp step with 0 parse errors; 2 null-session rows dropped; 11,715,474 consecutive
   repeated events removed; 30,733,288 monthly events left; 166,794 products in the first-seen lookup.
   First-seen build time 1.516 s — scope: monthly Parquet scan + group-by minimum + Parquet write on DuckDB CPU,
   excluding upstream cleanup, verification and checksums (`data/manifests/monthly_first_seen.json`).
   The cleaned output differs from NVIDIA's saved cuDF output by **13 rows in total**. TV1 attributes this to the
   ordering of events with equal timestamps; this is **TV1's explanation — there is no per-event/session comparison
   log yet**. Write it as a likely cause, not a proven one.
   Source: `docs/event_timestamp.md`, `docs/timestamp_session_cleanup.md`, `docs/monthly_first_seen.md`.
2. **Sampling** — summary of III.D.
3. **ETL with NVTabular (notebook 02)** — workflow fitted on the whole week of each subset **before** the split
   (mapping + feature statistics), fixed across partitions; padding 0, null 1, OOV 2, known items from 3;
   sessions with ≥ 2 interactions; keep the last 20 items including the target. **[PENDING: TV1 ETL run]**
4. **Split and training schedule** — write all of these explicitly:
   - Sessions are grouped **first** (whole session kept inside the 7-day window, even if it crosses midnight);
     `day_index` is computed **after Groupby** as `(event_time_dt-first − min).dt.days + 1`, where `min` is the
     minimum first-event timestamp in that subset's workflow — it is an index from the source formula, not a UTC
     calendar day.
   - Equal timestamps: sorted as the source runtime does; no extra CSV-row key (DuckDB order in the monthly cleanup).
   - Inside each `day_index` partition: random ~80/10/10 train/validation/test (`save_time_based_splits`, GPU seed 1,
     sessions sorted by `user_session`); a threshold split, so shares are approximate.
   - Daily fine-tuning: the same model trains on partition t and is validated on t+1 (weights continue, LR scheduler
     reset). Configuration is chosen on validation only.
   - Final test (E1, E2): D = largest `day_index` in the verified membership; evaluate test partition D with the
     checkpoint trained on 1…D−1; report the number of evaluated sessions `n_sessions`.
   - E3 compares configurations on **validation** partition D, not test.
   FIGURE 7: timeline of partitions 1…D with train/val/test colours.
   Source: `docs/modeling/model_protocol.md`.
5. **Encoded ID vs original product ID** — models only see encoded IDs; the saved reverse mapping turns top-20
   back into original product IDs; technical tokens never appear in outputs.

### C. MODEL CONFIGURATION AND EVALUATION PROTOCOL
- TABLE 6 — hyper-parameters per model (sequence length, masking, d_model, layers/heads, batch, epochs, LR,
  prediction head). Start from `docs/modeling/model_comparison.md` but report the **values actually used in our runs**.
  **[PENDING: TV2 final config]**
- Shared protocol bullets: same split, same ground truth (last real item), same candidate catalog (real products in
  the subset's weekly vocabulary), seen items allowed, technical tokens excluded, K = 20, same aggregation.
- Honest statement (use this wording, never "leakage-free"): this is an **offline evaluation in which the
  preprocessing workflow (mapping, vocabulary, feature statistics) is fitted on the whole week of each subset,
  including validation/test sessions, before the split**. Model weights and Popularity counts learn only from train
  partitions; test is used once, after the configuration is fixed. Consequence: the vocabulary/catalog can contain
  products that never appear in train (they get an ID, not OOV). Limitation: results may be optimistic compared with
  a deployment where the vocabulary is built only from past data (repeated in VI.D).

---

## V. EXPERIMENTS AND RESULTS  (≈3.5–4 pages — largest section)

Order follows the sample's V (`1) Processing Model → 2) System Design → 3) User Interface`), with our experiment
parts inserted between System Design and User Interface:
Processing Model (opening) → A Environment → B System Design → C–E Experiments, Results, Summary → F User Interface.

### PROCESSING MODEL  (opening paragraph, ~0.25 page, mirrors the sample's "1) Processing Model")
- One paragraph + FIGURE (reuse the pipeline figure of IV.B in compact form, or a 4-box flow) describing how one
  run goes from data to metrics, without repeating IV.B in detail:
  **session Parquet (per subset, partitions 1…D) → model script (Popularity / GRU / XLNet, daily fine-tuning
  train t → validate t+1) → top-20 over the shared catalog for each evaluated session → Recall@20 / NDCG@20 +
  timings/memory → `metrics.json` + `predictions.jsonl` + `run.json` (collector) → tables, figures, demo.**
- One sentence per experiment family on what is varied in this flow (model, subset, batch size, input format) and
  that E5 reuses the E2 runs.

### A. DEPLOYMENT ENVIRONMENT
- **Why a public cloud GPU VM** (the course allows public cloud or a local VM, so justify the choice):
  NVTabular/cuDF ETL and GRU/XLNet training need an NVIDIA GPU with enough VRAM (XLNet memory grows with sequence
  length and batch); the team's laptops do not give a common, reproducible GPU (local smoke only on an RTX 3050);
  a cloud VM gives one shared machine, a fixed Docker image and a measurable cost per hour. Mention the trade-off
  (cost, setup time) and that the VM is stopped after the runs (cleanup record).
- TABLE 7 — cloud provider, instance, GPU, CPU, RAM, disk, OS, driver, CUDA, Docker image tag/digest, Python,
  package versions (cudf, nvtabular, torch, transformers4rec). **[PENDING: TV3 environment/README.md]**
- Cost per hour and total cost, if measured. **[PENDING: TV3]**
- Measurement tooling: benchmark collector records run_id, start/end, exit code, wall time, peak process RSS,
  peak CUDA reserved memory, config and output paths. Source: `benchmark/collect.py`.
- Measurement scope notes: inference time = `full_evaluation_wall_v1` (whole evaluation incl. I/O), warm-up/cache
  policy, RSS may double-count shared pages. Source: `docs/modeling/inference_timing.md`.

### B. SYSTEM DESIGN
Mirrors "System Design" in the sample (architecture, use case, sequence and database diagrams), adapted to an
offline benchmark: no database, so the database diagram becomes an artifact-layout figure; the use-case diagram is
kept small and only for the demo (FIGURE 10b: viewer selects subset/split/session/model → sees history, top-20,
actual next item). Keep at most 3 figures here; move the rest to the appendix.
- FIGURE 8 — **system architecture**: local/Git → cloud GPU VM → Docker (Merlin) → pipeline/models/evaluation →
  metrics + logs → report/demo.
- FIGURE 9 — **run sequence diagram**: TV2 config → TV3 runner → collector → model script → predictions.jsonl +
  metrics.json → run.json.
- FIGURE 10 — **artifact layout**: what is stored in Git (code, config, manifests, metrics, small logs) vs external
  storage (raw CSV, large Parquet, checkpoints). Replaces the sample's database diagram.

### C. EXPERIMENTAL DESIGN
TABLE 8 — experiment matrix (source: `docs/experiment_matrix.md`, `configs/experiments.json`):

| ID | Question | Variable | Fixed settings | Outputs |
| --- | --- | --- | --- | --- |
| E1 | Which model ranks better, at what cost? | Popularity / GRU / XLNet | 10% subset, same split, catalog, K | Recall@20, NDCG@20, train/inference time, memory |
| E2 | How does the pipeline react to more data? | 10 / 25 / 50 / 100% sessions | GRU, same config | counts, read/preprocess/train time, memory |
| E3 | How do resources change performance? | train batch 32 vs 128 | GRU, 10%, same epochs, seq length | runtime, throughput, memory, cost |
| E4 | CSV vs Parquet? | input format | raw 10% subset, identical content | file size, read time, preprocessing time, memory |
| E5 | Does it scale? | derived from E2 | no new runs | seconds per 1M events, curve, bottleneck |

Plus: number of repeats per run, how failed/OOM runs are handled (kept and reported).

**Why batch size is the resource variable in E3** (the course examples are CPU, RAM, number of workers): on a single
GPU, train batch size directly controls GPU memory use and throughput, so it is the resource knob that matters for
GRU/XLNet; changing only this one variable isolates its effect. State the limitation: CPU/RAM limits and number of
workers/GPUs were not varied (budget), listed again in VI.D.

### D. RESULTS
For each experiment use the same 4-part pattern: **Setup (1–2 sentences: subset, split, partition, n_sessions)
→ Table → Figure → Analysis**. The analysis answers three questions, in this order:
**what changed, how much was measured, which limitation affects how to read the number.**
Do not write the conclusion before the numbers exist; the bullets below are the *questions* each analysis answers.
All values **[PENDING: TV2 metrics package]**; each caption lists the source run_id(s), fields and scope
(`reports/tables/README.md`). If a run failed / OOM / timed out, show its status and log path instead of numbers,
and narrow the conclusion to the confirmed runs; E5 with missing E2 runs is labelled `partial`.

1. **E1 — Model comparison** (10% subset, **test partition D**). TABLE 9 (Recall@20, NDCG@20, n_sessions, train
   time, inference time `full_evaluation_wall_v1`, ms/session, peak RSS, peak CUDA). FIGURE 11 grouped bars of
   Recall/NDCG; FIGURE 12 time and memory. Questions: Do GRU/XLNet differ from Popularity, and by how much? What
   does each extra point of Recall/NDCG cost in time and memory? Did XLNet fit in GPU memory?
2. **E2 — Data size** (GRU, 10/25/50/100%, **test partition D**). TABLE 10 per subset (measured events, sessions,
   users, vocabulary, bytes, read, preprocessing, train time, memory; shared monthly first-seen cost shown once,
   separately). FIGURE 13 time vs measured events. Questions: How does each stage grow with events — roughly
   proportional or not? Does accuracy change with more data?
3. **E3 — Batch size on one GPU** (GRU, 10%, **validation partition D**). TABLE 11 batch 32 vs 128 (runtime,
   throughput with its definition, RSS, CUDA memory, cost if measured). FIGURE 14. Name it "effect of train batch
   size on resource use", not general "resources". Questions: speed vs GPU memory trade-off? Any change in
   validation Recall/NDCG?
4. **E4 — Storage format** (raw 10% subset, same 9 string columns). TABLE 12 CSV vs Parquet (rows, content check,
   size, read time, preprocessing time, peak reader RSS). FIGURE 15. Scope to state: identical string schema, OS cache
   warm after the pair check, preprocessing time includes the pipeline's own input read. Questions: compression
   ratio? read speed-up? does it carry over to preprocessing?
5. **E5 — Scalability** (derived from passed E2 runs). TABLE 13 and FIGURE 16. Define the metric exactly:
   **composed time = sum of separately measured stages** (raw read, preprocessing excl. raw read and first-seen,
   training incl. sequence I/O, final evaluation incl. I/O) **÷ measured weekly events before sequence building ×
   10⁶**; shared first-seen reported separately; state the number of train partitions actually used. Questions:
   which stage is the bottleneck? Is seconds-per-million-events stable across sizes? Projection to the full month
   only if clearly labelled. Uncertainty: one run per subset.
   **Open issue to resolve with TV2 before quoting `summary.json`:** `benchmark/scalability.py` sums
   `final_evaluation_including_io` (full evaluation wall), but its `limitations` text says "Final inference is
   compute/ranking only" — the text must be corrected or the field changed.

### E. SUMMARY OF FINDINGS
- 5 numbered sentences, one per experiment (E1–E5), each with its key number and table/figure.
- **Closing paragraph that answers the course objective directly:** how did *data size* (E2, E5) and *computing
  resources / storage format* (E3, E4) affect runtime, memory, throughput and accuracy? Which stage is the
  bottleneck and what would we change first to scale? **[PENDING: TV2 package]**

### F. USER INTERFACE (DEMO)
Like "User Interface" in the sample, with screenshots (FIGURE 17–19). Source: `app/README.md` (TV4).
- Session picker (subset, split, session) — FIGURE 17.
- Session history (prefix) with original product IDs + actual next item card — FIGURE 18.
- Top-20 list with rank, hit/miss highlight, model switch (Popularity/GRU/XLNet) on the same session — FIGURE 19.
- How it works: offline predictions → exporter maps encoded IDs to original IDs → React UI; no training per request.

---

## VI. CONCLUSION  (≈1 page)

### A. CHALLENGES
Sample style: numbered items with a short paragraph each. Fill with what really happened (collect from
`docs/handoff.md` and the team):
1. **Building a fair, leakage-aware protocol** — split by `day_index`, shared catalog, last-item target, MLM vs
   causal training with the same evaluation.
2. **Reproducing the NVIDIA preprocessing** — duplicate-timestamp ordering (13-row difference), DuckDB instead of
   cuDF for the monthly steps.
3. **GPU runtime and memory** — Merlin/Docker setup, XLNet memory, OOM handling. **[PENDING: TV3]**
4. **Measuring system cost correctly** — separating shared first-seen cost, defining inference time scope,
   warm-up/cache effects.
5. **Team coordination** — five branches, handoffs with manifests and commit hashes.

### B. ACHIEVEMENTS
Numbered, sample style. **Only list an item once its evidence exists** (run_id / log / commit); otherwise move it
to limitations or development directions.
1. A reproducible pipeline from raw CSV to session Parquet with manifests and checksums — *partly available now*
   (monthly cleanup, first-seen, sampling done; ETL/split pending TV1).
2. Three models evaluated under one protocol (E1) — only if all three runs passed; otherwise state which did.
3. A system benchmark of data size, batch size, storage format and scalability (E2–E5) — list runs that passed.
4. An offline demo showing predictions with original product IDs — only if it runs on real prediction output.
5. Skills gained: GPU ETL, cloud deployment, experiment design, technical writing in English.

### C. DEVELOPMENT DIRECTIONS
(Same position as in the sample: A → B → C. D and E below are added because TV5 must write them.)
Sample style bullets: side features (category, brand, price, recency); longer time windows / whole month;
more resource configs (CPU/RAM limits, number of workers, multi-GPU); hyper-parameter search; vocabulary built only
from past data; online/streaming inference service; cold-start evaluation. Each direction should follow from a
limitation in VI.D or a result in V.

### D. LIMITATIONS
- Offline evaluation only; preprocessing fitted on the whole week before the split, so the vocabulary includes
  products seen only in validation/test (results may be optimistic vs. a past-only vocabulary); one run per configuration
  (no confidence interval); only 7 days; product ID only (no side features); E3 changes only train batch size
  (no CPU/RAM/worker/multi-GPU variation); measurement caveats; failed/OOM runs listed.

### E. REPRODUCIBILITY
- Commands from raw → subset → Parquet → train/eval → metrics; config files; seeds (hash seed 42, split seed 1);
  pinned NVIDIA commit; manifests/checksums; result of one re-run by another member. Source: `README.md`,
  runbooks, `docs/handoff.md`. **[PENDING: TV3 re-run log]**

## ACKNOWLEDGMENT
Thank the course lecturer by name and title **[confirm name]**, same tone as the sample (guidance, responsibility,
openness to feedback).

## REFERENCES
IEEE style. Rules: number `[n]` **in order of first citation in the text** (the list below is not the final
order); every entry cited at least once; give authors, title, venue, year, pages and DOI when they exist; online
sources get URL + real access date; **verify every field against the publisher page before final** (TV4
standardises, `docs/references.md`; IEEE Reference Guide).

Candidates (draft metadata — verify):
- Dataset: M. Kechinov, "eCommerce behavior data from multi category store," Kaggle. [Online]. Available:
  https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store (Accessed: <date>).
  Add data provider REES46 Open CDP. Use the dataset version/date shown on Kaggle — do not write "2019/2020".
- B. Hidasi, A. Karatzoglou, L. Baltrunas, and D. Tikk, "Session-based recommendations with recurrent neural
  networks," in *Proc. ICLR*, 2016 (arXiv:1511.06939).
- K. Cho *et al.*, "Learning phrase representations using RNN encoder–decoder for statistical machine translation,"
  in *Proc. EMNLP*, 2014, pp. 1724–1734 (GRU cell).
- Z. Yang *et al.*, "XLNet: Generalized autoregressive pretraining for language understanding," in *Proc. NeurIPS*,
  2019.
- G. de Souza Pereira Moreira, S. Rabhi, J. M. Lee, R. Ak, and E. Oldridge, "Transformers4Rec: Bridging the gap
  between NLP and sequential / session-based recommendation," in *Proc. 15th ACM RecSys*, 2021 (add pages + DOI).
- F. Sun *et al.*, "BERT4Rec: Sequential recommendation with bidirectional encoder representations from
  transformer," in *Proc. 28th ACM CIKM*, 2019 (add pages + DOI).
- *(optional)* W.-C. Kang and J. McAuley, "Self-attentive sequential recommendation," in *Proc. IEEE ICDM*, 2018.
- *(only if RTD is mentioned)* K. Clark *et al.*, "ELECTRA: Pre-training text encoders as discriminators rather
  than generators," in *Proc. ICLR*, 2020.
- K. Järvelin and J. Kekäläinen, "Cumulated gain-based evaluation of IR techniques," *ACM Trans. Inf. Syst.*,
  vol. 20, no. 4, 2002 (NDCG).
- NVIDIA, "Transformers4Rec," GitHub repository, commit f0ca2b5343dd1e40b5d2422b942f014b224f5c20 (full hash),
  Apache-2.0. Cite the tutorial notebooks 01–03 separately with URL + access date.
- NVIDIA NVTabular, RAPIDS cuDF, Apache Parquet, DuckDB documentation — only those actually used, with the version.

## APPENDIX  (not counted in page budget)
- A. AI-use statement (source: `docs/ai-use-statement.md`; update with all AI use, including this report).
- B. Team contribution table.
- C. Run registry: run_id → experiment, config, status (pass / fail / OOM / timeout), source log.
- D. Data dictionary (full) if not shown in III.B.

---

## Course requirement coverage (`docs/course_requirements.txt`)

| Course requirement | Where in this outline |
| --- | --- |
| 1. Dataset with Big Data characteristics, explain relevant V's | III.B, III.C |
| 1. Subset allowed; must be diverse and representative | III.D (why), III.E (evidence) |
| 1. Explain how the subset was chosen and why it fits the problem | III.D |
| 2. Clear, testable problem | I.B, IV.A.1 |
| 3. Reuse known algorithms; understand and compare them | II, IV.A, IV.C, V.D.1 |
| 4. Deployment environment (cloud or VM, Docker…) and why | I.D, V.A |
| 5. Compare models with suitable metrics | E1 |
| 5. Vary dataset size | E2 |
| 5. Vary computing resources | E3 (+ justification in V.C) |
| 5. Compare storage / processing methods | E4 |
| 5. Scalability analysis | E5 |
| 6. Report in English; focus on problem, data, method, environment, design, results, discussion | whole outline; V is largest |
| 6. Prioritise results over theory | IV.A length cap, page budget |
| 7. Not just one model without analysis | 3 models + Analysis part per experiment |
| 7. Reuse previous code, extend towards Big Data & Cloud | I.B "What we reuse vs. what we add", II.B |
| 7. Goal: effect of data and resources on system performance | V.E closing paragraph, VI |

## Figure and table checklist

| No. | Item | Section | Owner | Status |
| --- | --- | --- | --- | --- |
| Fig 1 | Raw data sample | III.B | TV1/TV5 | can do now |
| Fig 2 | Events per day | III.B | TV4 | data available |
| Fig 3 | Distribution full week vs subsets | III.E | TV4 | PENDING TV1 |
| Fig 4–5 | GRU architecture; causal vs MLM masking | IV.A | TV4 | can do now (credit NVIDIA) |
| Fig 6 | Data pipeline | IV.B | TV4 | can do now |
| Fig 7 | Partition / training timeline | IV.B | TV4 | can do now |
| Fig 8–10 | Architecture, run sequence, artifact layout | V.B | TV4/TV3 | draft now |
| Fig 11–16 | E1–E5 charts | V.D | TV4 | PENDING TV2 |
| Fig 17–19 | Demo screenshots | V.F | TV4 | PENDING demo |
| Tab 1 | Team roles | I.C | TV5 | can do now |
| Tab 2 | 9 columns | III.B | TV5 | available |
| Tab 3 | 5V | III.C | TV5 | mostly available |
| Tab 4 | Subset counts | III.D | TV5 | available |
| Tab 5 | Representativeness | III.E | TV5 | PENDING TV1 |
| Tab 6 | Hyper-parameters | IV.C | TV5 | PENDING TV2 |
| Tab 7 | Environment | V.A | TV5 | PENDING TV3 |
| Tab 8 | Experiment matrix | V.C | TV5 | available |
| Tab 9–13 | E1–E5 results | V.D | TV5 | PENDING TV2 |

## Page budget and what goes to the appendix

I–VI as listed sum to ~9.7–10.2 pages before header, abstract and references — too long with 19 figures and
13 tables. Keep in the main text: Tables 1(short), 2, 4, 8, 9–13 and Figures 2, 6, 7, 8, 11, 13–16, 18.
Move to the appendix / slide backup: full data dictionary, hyper-parameter table (keep one sentence in IV.C),
run registry, Figures 4–5 (cite NVIDIA instead), Figure 9–10, extra demo screenshots. Do a **trial layout in the
two-column template by 24/11** to check the length.

## Writing order and timeline

1. **21–22/11** — lock fields, units and table IDs (`reports/tables/README.md`); build an exportable two-column
   draft with I, II, III.A–D, IV.A–C, V.C, Tables 1–4 and 8, empty result tables, captions and slide skeleton.
2. **23–24/11** — trial layout; add III.E, IV.B.3, V.A, V.B when TV1/TV3 deliver; send the open questions to TV2.
3. **25–26/11** — read the handed-over logs with TV2/TV4: config, split, failed runs, sources; draft result
   paragraphs as questions; prepare speaker notes.
4. **27/11** — fill the official TV2 package into tables **and** figures from the same data; write V.D–E, VI.B, VI.D–E,
   then ABSTRACT.
5. **28/11** — check the exported PDF (numbers vs package, run_id in every caption, references, AI statement,
   page limit) and rehearse.
If something must be cut: architecture theory, tool logos, duplicate UI screenshots and the full-month projection
go first. Missing runs are labelled `partial` with the scope of the conclusion narrowed.
