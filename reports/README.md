# Reports — TV5 Report & Results

Status (21/11/2026): outline and table templates ready; no experiment numbers filled in (model runs not started).
All results must come from the official TV2 metrics package (built from TV3 raw logs).

## Layout

| Path | Content | Owner |
| --- | --- | --- |
| Google Docs [report](https://docs.google.com/document/d/1RSZgWxnT7YAtpn2wKLst-MKWnkvyTfD9bsncIv5o50M/edit) | **The report itself**, on the group template (link in the team sheet); written here, exported to PDF at the end | TV5 |
| `reports/report_outline.md` | Plan of the report: what each section writes and shows, sources of every number, team status, open items | TV5 |
| `reports/tables/` | Templates of the Chapter 5 tables (E1–E5): one CSV per table with `run_id`, metric, unit and source columns, empty until the TV2 package arrives; `README.md` = where each field comes from; `format_check.md` = fields checked against the outputs (TV5 tasks 20–22/11) | TV5 |
| `reports/figures/` | Figures + captions + source `run_id` | TV4 → TV5 |
| `reports/slides/` | Slide outline (18 slides, 15:00 timing, backup slides, Q&A prep), later speaker script and final deck | TV5 (demo part: TV4) |

**Outline (updated 21/11/2026):** team chapter proposal after the lecturer's e-mail of 20/11, updated to the
cuDF data decision of 21/11.

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
- [x] Output format check vs report needs + list for TV2 (`tables/format_check.md`, task 21/11) — answers pending
- [ ] Metrics package received from TV2
- [ ] Results / limitations / reproducibility written
- [ ] Report and slides final (English)
- [ ] Rehearsal 15 min + 5 min Q&A
