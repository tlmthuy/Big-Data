# Reports — TV5 Report & Results

Status (20/11/2026): **skeleton only**. No experiment numbers are filled in.
All results must come from the official TV2 metrics package (built from TV3 raw logs).

## Layout

| Path | Content | Owner |
| --- | --- | --- |
| `reports/report_outline.md` | English report outline following the course sample report skeleton (I–VI), with data sources, figure/table checklist and writing order | TV5 |
| `reports/report.md` (later) | Report draft; final version exported to the course template (PDF) | TV5 |
| `reports/tables/` | E1–E5 tables (CSV/Markdown) + captions, filled only from the metrics package | TV5 |
| `reports/figures/` | Figures + captions + source `run_id` | TV4 → TV5 |
| `reports/slides/` | Slide outline (21 slides, 15:00 timing, backup slides, Q&A prep), later speaker script and final deck | TV5 (demo part: TV4) |

Demo lives in `app/` (TV4). References and AI statement: `docs/references.md`, `docs/ai-use-statement.md`.

## Rules for numbers in the report/slides

1. **Experimental numbers** (E1–E5) come from the official TV2 metrics package and have a `run_id`, config, unit and
   source log. **Dataset numbers** (audit, cleanup, subset counts) cite their CSV/manifest directly.
2. Toy runs (`data_kind: "toy"`) and NVIDIA tutorial outputs are never reported as group results.
3. Session ratio ≠ event ratio: report the measured event/session counts of each subset.
4. Keep the shared monthly first-seen cost separate from per-subset preprocessing cost.
5. Describe the pipeline correctly: the NVTabular workflow/mapping is fitted on the whole week of each subset
   **before** the split; first-seen is computed on the month **before** the week filter; model weights learn
   from train partitions only. Do not call the whole pipeline "train-only".
6. Failed / OOM / timeout runs stay in the report as limitations; they are not deleted.

## Inputs TV5 waits for

| Input | From | Needed for |
| --- | --- | --- |
| Raw audit, subset counts, distributions (event type, category, brand, session length) | TV1 | Dataset, 5V, sampling sections |
| Environment snapshot (GPU, CPU, RAM, OS, driver, CUDA, Docker image, packages) | TV3 | Environment section |
| Official metrics package E1–E5 (CSV/JSON + config + source log + excluded runs) | TV2 | Results, tables |
| Figures + captions + source `run_id`, references, license, AI statement | TV4 | Results, references |
| Demo screenshots / fallback output | TV4 | Demo section and slide |

## Checklist

- [x] `reports/`, `reports/tables/`, `reports/slides/` created
- [x] Report outline (`report_outline.md`)
- [x] Slide outline (`slides/slide_outline.md`)
- [x] E1–E5 metric/table structure: run_id, metric, unit, source field/log, open questions for TV2 (`tables/README.md`, task 20/11)
- [ ] Metrics package received from TV2
- [ ] Results / limitations / reproducibility written
- [ ] Report and slides final (English)
- [ ] Rehearsal 15 min + 5 min Q&A
