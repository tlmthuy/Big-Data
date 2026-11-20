# Slide outline (English) — 15 min presentation + 5 min Q&A

Same storyline as `reports/report_outline.md` (sections I–VI of the sample report), compressed for talking.
Course rule: prioritise **experiments, results and analysis** over theory → results get 6:30 of 15:00.

## Time budget

| Block | Slides | Time | Report section |
| --- | --- | --- | --- |
| Opening, problem, related work | 1–4 | 2:00 | I, II |
| Dataset & sampling | 5–7 | 1:45 | III |
| Method & protocol | 8–10 | 2:00 | IV |
| Environment & experiment design | 11–12 | 1:00 | V.A–C |
| Results E1–E5 | 13–16 | 6:30 | V.D–E |
| Demo | 17 | 1:00 | V.F |
| Conclusion | 18 | 0:45 | V.E, VI |
| **Total** | 18 (+ backup) | **15:00** | |
| Q&A | — | 5:00 | |

Speakers are a proposal (each member presents what they built; TV5 presents results; TV4 runs the demo).
Keep speaker changes to ≤ 4 to save transition time. Agree in the team before rehearsal.

---

## Slides

Format: **Title** (time · speaker) · on-slide content · visual · key message · source · status.

### 1. Title  (0:15 · TV5)
- Title, course code, group number, 5 members + roles, lecturer, date. Status: ready (confirm names).

### 2. Motivation  (0:35 · TV5)
- Shoppers browse in short, often anonymous sessions → recommend the next item from the current session only.
- Scale of October 2019: 5.67 GB CSV, 42.4 M events, 3.0 M users, 9.2 M session IDs.
- Visual: 4 big numbers + session illustration.
- Key message: "Large enough that the pipeline itself is part of the problem."
- Source: `data/raw_audit.csv`, `data/manifests/raw_audit_manifest.json`. Status: available.

### 3. Problem & research questions  (0:40 · TV2)
- Input: item prefix of one session → Output: top-20 products → Target: next real item. A → B → C ⇒ D.
- Metrics: Recall@20 (is the target in the list?), NDCG@20 (how high?).
- Five questions E1…E5, one line each; goal line: "How do data size and computing resources affect system
  performance?"
- Visual: session strip with prefix boxes, a "?" box and a top-20 list. Source: `docs/modeling/next_item_problem.md`.

### 4. Related work & what we added  (0:30 · TV4)
- GRU4Rec (2016) → Transformers for sessions (BERT4Rec, XLNet) → Transformers4Rec (RecSys 2021).
- Two-column box **Reused | Added by us**: reused = GRU/XLNet + ETL from NVIDIA notebooks 01–03 (pinned commit,
  Apache-2.0); added = session-hash sampling at 4 sizes, DuckDB monthly cleanup, shared protocol/catalog,
  Popularity baseline, benchmark collector, E1–E5 on cloud GPU, demo.
- Tool icons only as a small strip at the bottom (cut first if short of time).

### 5. Dataset & 5V  (0:40 · TV1)
- Kaggle "eCommerce Behavior Data from Multi-Category Store", `2019-Oct.csv`, 9 columns.
- 5V table, one line each: Volume 5.67 GB / 42.4 M rows · Velocity ~1.13–1.42 M events recorded per day
  (**first week**) · Variety 3 event types, 624 categories, 3,445 brands · Veracity 31.8% missing category code,
  14.4% missing brand, 11.7 M consecutive repeats removed · Value offline-measurable recommendation quality.
- Source: `data/raw_audit.csv`, cleanup manifest. Status: available.

### 6. Sampling  (0:40 · TV1)
- First 7 days; stable SHA-256 hash on session ID; nested 10/25/50/100%; whole sessions, never single rows.
- Why it fits next-item prediction: whole sessions keep the target; nested sizes isolate the size effect;
  7 days = enough daily partitions within the GPU budget.
- Table: events / sessions / users / items (+ categories / brands, PENDING TV1) and **two ratio columns**:
  session ratio 0.0999 / 0.2502 / 0.4997 / 1.0 and event ratio 0.1000 / 0.2507 / 0.5007 / 1.0.
- Key message: "The two ratios are close, and both were measured." (not "match").
- Source: `data/manifests/raw_subset_counts.csv`. Status: available.

### 7. Representativeness  (0:25 · TV1)
- Full eligible week vs each subset: event-type share, top categories/brands, session length — scope stated
  (raw or after cleanup).
- One sentence with the **largest observed difference**; conclude only from that number.
- Status: PENDING TV1 distributions.

### 8. Pipeline  (0:40 · TV1)
- One-row diagram: CSV → UTC timestamp → drop null session → remove consecutive repeats (same product, even if
  event type differs) → monthly first-seen → week filter → hash sampling → NVTabular workflow (fitted on the week) →
  Groupby session → last 20 items → day_index split → Parquet + mapping.
- DuckDB CPU for monthly steps; NVTabular GPU for ETL. Source: `AGENTS.md` §6.

### 9. Models  (0:40 · TV2)
- Popularity: cumulative train counts, unseen catalog items score 0, ties by encoded ID, same list for everyone.
- GRU (causal: learn the next item from the past) · XLNet block trained with item MLM (masked items), evaluated on
  the last item.
- Visual: three columns with a mini architecture each; hyper-parameters in backup B1.

### 10. Evaluation protocol  (0:40 · TV2)
- Timeline: day_index 1…D (computed after Groupby); in each partition ~80/10/10 (GPU seed 1); train t → validate
  t+1, same weights; **E1/E2: test D with checkpoint after 1…D−1; E3: validation D**.
- Shared rules: last real item = target, same catalog (real products of the subset vocabulary), seen items
  allowed, technical tokens removed, K = 20, average over evaluated sessions.
- Honest line: "Vocabulary/statistics fitted on the whole week before the split; weights learn from train only."
- Encoded ID → original product ID for outputs and demo. Source: `docs/modeling/model_protocol.md`.

### 11. Environment  (0:30 · TV3)
- Cloud GPU VM → Ubuntu → Docker → Merlin → cuDF/NVTabular → PyTorch/Transformers4Rec; hardware line
  (GPU, CPU, RAM, cost/hour); collector records run_id, time, memory.
- Why cloud GPU (course allows a local VM): NVTabular + GRU/XLNet need an NVIDIA GPU with enough VRAM; one shared,
  reproducible machine and image; measurable cost; stopped after runs.
- Status: PENDING TV3 environment.

### 12. Experiment design  (0:30 · TV2)
- E1–E5 table: question · variable · fixed settings · split (E1 10% three models, test D; E2 GRU 10–100%, test D;
  E3 batch 32 vs 128, validation D; E4 CSV vs Parquet raw 10%; E5 from E2). Source: `docs/experiment_matrix.md`.

### 13. E1 — Model comparison  (1:45 · TV5)
- Left: grouped bars Recall@20 / NDCG@20 (n_sessions in the caption). Right: train time, inference
  ms/session (`full_evaluation_wall_v1`), peak CPU/GPU memory.
- Takeaway sentence = what changed · how much · caveat. run_id footnote.
- Status: PENDING TV2 package.

### 14. E2 + E5 — More data and scalability  (2:00 · TV5)
- Left: stage times (read / preprocessing / train / evaluation) vs **measured events** for 10–100%.
- Right: seconds per 1M events (composed stage times ÷ weekly events) + bottleneck highlighted; shared first-seen
  shown separately.
- Takeaway: how each stage grows; bottleneck; `partial` if any subset is missing.
- Status: PENDING.

### 15. E3 — Batch size on one GPU  (1:15 · TV5)
- Why batch size: on one GPU it controls memory and throughput; only this variable changes.
- Chart: batch 32 vs 128 — runtime, throughput (definition stated), GPU memory; validation Recall/NDCG.
- Caveat: CPU/RAM/workers not varied. Status: PENDING.

### 16. E4 — CSV vs Parquet  (1:30 · TV5)
- Paired bars: file size, read time, preprocessing time, memory; rows + content fingerprint checked.
- Scope line: same string schema, warm cache, preprocessing includes its own read.
- Takeaway: compression ratio and read speed-up. Status: PENDING.

### 17. Demo  (1:00 · TV4)
- Live: pick a session → history (original product IDs) → top-20 with hit/rank → switch model on the same session.
- Fallback: screenshots / static prediction output prepared before the talk. Status: PENDING real output.

### 18. Conclusion  (0:45 · TV5)
- Five one-line answers (E1…E5) with the key number, then one line answering the course objective (effect of data
  size and resources; bottleneck to fix first).
- Limitations in one line: offline, preprocessing fitted before split, one run per config, 7 days, product ID only.
- Achievements only where evidence exists; future work in one line. "Thank you — Q&A". References + AI statement
  in small text / QR to the repo.

### Backup slides (Q&A only)
- B1 Hyper-parameters per model. · B2 Run registry (pass / fail / OOM / timeout).
- B3 Measurement scope: `full_evaluation_wall_v1`, `ms/session` = full evaluation wall ÷ evaluated sessions incl.
  I/O, RSS caveat, warm-up/cache.
- B4 Encoded vs original ID example; padding 0 / null 1 / OOV 2.
- B5 Preprocessing numbers: 2 null rows, 11,715,474 repeats removed, 30.7 M monthly events left, 13-row difference
  vs NVIDIA (TV1's explanation: equal-timestamp ordering; no per-event log).
- B6 Metric formulas. · B7 Challenges list. · B8 Related-work details.

---

## Q&A preparation (answers in English, each with a concrete check)

| Likely question | Answer direction + evidence | Who |
| --- | --- | --- |
| Why Recall@20 and NDCG@20? | Top-K list setting; Recall = hit, NDCG = position; one target → IDCG = 1; toy tests with target at rank 1, 20 and outside | TV2 |
| How is the ground truth chosen? Can it leak? | Last real item; causal shift / masking hides it; GPU smoke checked label = last item and target hiding | TV2 |
| Is fitting the workflow before the split leakage? | Yes, it is a stated limitation: vocabulary and feature statistics see the whole week; weights and Popularity counts learn only from train; test used once after fixing config | TV2/TV5 |
| Why keep Popularity? | Cheap reference; any neural gain is measured against it | TV2 |
| Why only 7 days / why 100% ≠ full month? | GPU/time budget; E5 gives cost per million events | TV1/TV5 |
| How do you know subsets are representative? | Stable session hash + measured distribution differences (slide 7) | TV1 |
| **Why does E3 use validation D and not test?** | Test is reserved for the final evaluation after config is fixed; comparing configs on test would be tuning on test | TV2 |
| **What does ms/session include?** | Full evaluation wall (read, prepare, predict, rank, aggregate, write) ÷ evaluated sessions | TV2/TV3 |
| **What can you conclude if 100% is missing or XLNet OOMs?** | Conclusions limited to passed runs; E5 marked partial; OOM itself is a resource result (logged) | TV5 |
| Are CSV and Parquet the same data in E4? | Same row count + multiplicity-sensitive fingerprint of the 9 columns before measuring | TV3 |
| Why DuckDB, not cuDF, for the first steps? | Simpler for the monthly CSV on CPU; 13-row difference documented | TV1 |
| What does the demo show — encoded or original IDs? | Original product IDs via the saved reverse mapping | TV4 |
| What did AI help with? | See AI-use statement; results come only from real runs | TV5 |

## Design notes

- One message per slide; result slides = one chart + one takeaway sentence + run_id in small text.
- Same colour per model and per split (train/val/test) in every chart (TV4 figures).
- ≤ 30 words of text per slide; details go to speaker notes.
- Every number on a slide equals the report table and the TV2 package.
- Deck tool still open (Google Slides / PowerPoint). Speaker script `reports/slides/script.md` comes after results;
  rehearse in English and time each block.
