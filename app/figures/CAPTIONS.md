# Official figures for TV5

Regenerate all figures from `public/official-results.json` with:

```bash
python3 scripts/make_figures.py
```

- **e1-ranking.svg — For TV5 report.** Recall@20 and NDCG@20 (ratio) by model for the 10% subset and test split. Source runs: `e1-popularity-010`, `e1-gru-010`, `e1-xlnet-010`. Limitation: one run and one seed.
- **e1-training.svg — For TV5 report.** `train_seconds_including_sequence_io` (s) by model for the same 10% subset and test split. Source runs: `e1-popularity-010`, `e1-gru-010`, `e1-xlnet-010`. Limitation: the package defines this as training only, excluding daily validation.
- **e2-training.svg — For TV5 report.** `train_seconds_including_sequence_io` (s) against `n_events` for the GRU E2 runs across the four subsets. Source runs: `e2-gru-010`, `e2-gru-025`, `e2-gru-050`, `e2-gru-100`. Limitation: evaluation sets and catalogs change across subsets, so this is a cost-scaling view.
- **e3-tradeoff.svg — For TV5 report.** Validation Recall@20 (ratio) and `process_wall_seconds` (s) by `train_batch_size` for GRU on the 10% subset. Source runs: `e3-gru-010-b32`, `e3-gru-010-b128`. Limitation: these validation metrics are not directly comparable with E1/E2 test metrics.
- **e4-format.svg — For TV5 report.** E4 file size (`bytes`, displayed in MiB) and `read_seconds` (s) by CSV/Parquet format for the same 10% input. Source runs: `e4-full-010-csv`, `e4-full-010-parquet`. Limitation: E4 used a warm cache.
- **e5-scaling.svg — For TV5 report.** `composed_seconds_excluding_first_seen` (s) and `seconds_per_million_events` against `n_events` for the E2 runs. Source runs: `e2-gru-010`, `e2-gru-025`, `e2-gru-050`, `e2-gru-100`. Limitation: composed time is not observed end-to-end wall time; the shared first-seen cost is not added to each subset.
