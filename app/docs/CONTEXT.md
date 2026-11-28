# TV4 demo context

Snapshot: 25/11/2026. The team repository `../Big-Data` is the source of truth for data, metrics and the contract. Official experiment results come from released package `tv2-20261124` and are copied into `public/official-results.json` by `scripts/export_official_results.py` after checksum verification.

## What is real

- The Experiments tab uses confirmed official E1–E5 metrics and configuration/runtime metadata from package `tv2-20261124`.
- The Dataset tab uses the TV2 supplementary tables and TV1 manifests for the weekly cuDF subsets, population, cleaning and split information.
- Six figures in `figures/` are generated from `public/official-results.json`; their sources and limitations are documented in `figures/CAPTIONS.md`.
- The official E1–E5 package contains run-level benchmark values. The delivered real E1 JSONL predictions and matching catalog are exported as a fixed 30-session sample in `public/demo-data.json`; the artifacts have no per-item scores.

## What is still pending

- Product cards show the original ID, brand, category and last weekly price from `public/product-info.json`, derived by TV4 from the official 10% cleaned week file. The dataset has no product names.
- No score should be shown for a recommendation: the exported prediction records contain ranked IDs only.

## Interpretation rules

- E1 is the model comparison on the test partition. The package reports one run and seed, so results are descriptive and do not measure run-to-run variation.
- E3 is a validation comparison and is not directly comparable with E1/E2 test results.
- E4 preprocessing wall time includes its own read; do not add the standalone read time. The package also records a warm-cache condition.
- E5 composed time excludes shared first-seen and is not observed end-to-end wall time.
- Preserve package fields, units, nulls, limitations and source run IDs. Never invent or recompute metrics.

## Regeneration

Use the commands in the repository [README](../README.md) for official result and dataset adapters, real E1 sample generation and figure generation. The local `../tv4-real-bundle/` is an input only and must not be committed. See [DEMO_DAY.md](DEMO_DAY.md) for the live sequence and static offline fallback. See [TEAM_PROGRESS_CONTEXT.md](TEAM_PROGRESS_CONTEXT.md) for the fuller team status and upstream artifact locations.

## UI refresh 26/11 (reviewer feedback, TV2)

Presentation only: no data value, JSON shape or adapter output changed. Every number on screen still comes from `public/*.json`; 262/262 official table values match `metrics.json` (`tests/test_official_values.py`).

- **Design system.** System font stack only (no bundled fonts); exactly five type steps 13/16/18/22/28 px; 8-pt spacing, 14 px cards, 44 px controls, ≤ 1200 px content. Light, dark (`prefers-color-scheme`) and high contrast (`prefers-contrast: more`, `forced-colors`) token sets; `tests/contrast.test.js` checks every text/control pair, the high-contrast 7:1 target and text on glass against the worst content underneath.
- **One colour, one meaning.** Accent blue = interactive only. Green = Hit (marks use `--positive`, text uses the darker `--positive-text` so it passes 4.5:1). Miss is neutral (grey text, ✕ and the word "Miss"). Red (`--danger`) = problems only (load errors, failed/excluded runs, config "Differs"). "In history" = neutral grey outline. Popularity, GRU and XLNet have fixed colour-blind-safe colours (slate, orange, purple), always next to a text label or marker shape.
- **Selective translucency.** Glass only on the sticky header (≤ 56 px), the control bars, chart tooltips/glossary popovers and the Method details panel; solid fallback without `backdrop-filter`, with reduced transparency, high contrast, forced colours and in presenter mode.
- **Navigation.** `<nav>` links with `aria-current`; hash routes `#recommendation`, `#dataset`, `#experiments/e1`…`e5`, plus `#experiments/e2/N` to preselect a level (legacy `#data`, `#experiments-e3` still resolve). One "About the demo" popover in the header.
- **Recommendation.** Title, one intro sentence, one data badge; glass control bar (model segmented control, session select, presenter tip computed from `demo-data.json`); History and Actual next item side by side with "Hit — the actual item is ranked N of 20" / "Miss — the actual item is not in the Top-20"; hit row and actual panel highlight each other; no Score column when scores are not exported; E1 strip for the selected model linking to E1; closed Method details with run ID, checksums, file names and catalog size.
- **Presenter mode.** Header switch or `?present=1`, remembered in `localStorage`. 18 px body/tables, 16 px chart labels, solid header, notes collapsed.
- **Formatting.** `src/format.js` is the only formatter: Recall/NDCG 4 decimals, times 3 significant digits, bytes MiB/GiB with 1 decimal, grouped integers, missing/NaN → "Not available yet". Raw values are in tooltips.
- **Experiments.** Each panel: title, subtitle, one takeaway sentence filled from JSON (i18n template, no literals), interactive SVG charts (hover tooltip, click/Enter select with dimming, Esc clears, arrow keys, 44 px hit areas, zero baselines), a metric × run table whose columns are linked to the chart marks, and one notes block. E3 carries a Validation badge, train-batch headers from `configs` and a held-constant note; no throughput field exists, so none is shown. E5 selection links only to the same E2 level; nothing links E3 beside E1/E2.
- **Glossary.** ⓘ popovers for Session, History (prefix), Top-20, Hit, Recall@20, NDCG@20 and Validation vs test, worded from `docs/data_contract.md` and the team's `docs/modeling/model_protocol.md` / `next_item_problem.md`.
- **Checks.** `npm test` (node unit + SSR render tests), `npm run test:e2e` (browser interactions and text scans on the production build), Python adapter and official-value tests.
