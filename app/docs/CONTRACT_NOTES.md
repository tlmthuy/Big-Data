# Contract notes — differences to report to TV2

`docs/data_contract.md` (pinned at `5b2df90`) wins. This repo only **adds** fields; no contract field is renamed or reshaped. Report these to TV2 when the contract is reviewed.

## Part A — `public/demo-data.json`

| Item | What this repo does | Why |
| --- | --- | --- |
| File wrapper | `{ "schema", "team_commit", "runs": [ <contract Part A object>, ... ] }` | One file for several models/runs. Each element keeps the contract keys (`model`, `subset`, `split`, `run_id`, `data_kind`, `catalog_sha256`, `catalog`, `sessions`). The UI still accepts the legacy single-run object. |
| `provenance` per run | `run_dir`, `eval_day`, `experiment`, `catalog_path`, `catalog_match`, `score_available` | Grouping runs that share the same session set, and traceability. |
| `catalog_match: "line-endings-only"` | The collector smoke runs recorded the SHA-256 of the CRLF (Windows) checkout of `evaluation/tests/fixtures/catalog.json`. Content is identical; the adapter checks this explicitly and records it. | Ask TV2 whether future runs should hash with normalized line endings. |
| `data_kind` for runs without `run.json` | `"toy"` only when `subset == "toy"`, otherwise `null` (UI: "data_kind: Chưa có"). | `metrics/tv2-toy-day1` has no collector record. |
| Real E1 catalog subset | The public real-E1 sample stores only original product IDs used by the sampled prefix, target and Top-20; `catalog_size` and `provenance.catalog_size` retain the full catalog count, and `catalog_sha256` retains the full catalog hash. | Keeps the 30-session public JSON small while preserving catalog identity and membership checks. |
| Real E1 provenance | Adds `provenance.predictions_path`, `predictions_sha256`, `catalog_path`, `catalog_sha256`, `catalog_size`, `n_total` and `sample`. | Makes the TV3 bundle inputs and fixed hash sample traceable. |
| Optional product lookup | `provenance.product_lookup` is `null` unless an optional same-origin public JSON lookup is explicitly supplied. | Prevents an absent TV1 lookup from being requested by the browser. |

## Experiment results

The confirmed E1–E5 package is exported to `public/official-results.json` by
`scripts/export_official_results.py`. It copies the package tables, configs,
environment, exclusions and run-registry summary; no separate run-results
payload is shipped.

## Part C — `public/product-info.json` (proposal, NEED TV1)

This optional companion file is keyed by original `product_id`. It does not
change the prediction payload. The UI works without the file or an individual
entry and shows `Sản phẩm #<id>` as the fallback name. Price is in USD and
missing values are null. TV1 must confirm the subset and provenance. The
proposed price rule is **last observed price in the subset week**.

```json
{
  "data_kind": "toy",
  "source": "toy sample metadata for UI testing, not from dataset",
  "price_rule": "last observed price in the subset week",
  "products": {
    "p3": { "brand": "samsung", "category_code": "electronics.smartphone", "price": 130.76 }
  }
}
```

## Part D — Dataset overview (NEED TV1 confirm)

`public/dataset-overview.json` uses `tv4-dataset-overview/v1` with
`team_commit`, `generated_at`, `data_kind`, `source_confirmed_by`, `raw_month`,
`subsets` and `pipeline_measurements`. The raw month is from `data/raw_audit.csv`.
The weekly rows require the verified cuDF artifact. Confirm the source keys
and the scope of counts and histogram buckets with TV1. The raw-only export
leaves weekly values null. Pipeline measurements have their own opt-in flag
and require TV2 confirmation for benchmark use.

The proposed Part B `environment_baseline` records a VM snapshot and source
commit at file level. The run-level environment continues to come from run artifacts.

### Part A sampling (needs TV2 agreement)

With `--sample N --sample-seed S`, the adapter orders session IDs by
`sha256(f"{seed}:{user_session}")` and retains the first N. All runs in the
same subset, split and evaluation partition must have identical membership
for this export. Each run records `rule`, `seed`, `n_selected` and the
artifact's `n_sessions` as `n_total` in `provenance.sample`. Without sampling the original session order is preserved. The CSV and additional
run provenance fields are documented in [SAMPLE_PREDICTION.md](SAMPLE_PREDICTION.md).

#### Synthetic catalog check

For 63,398 catalog IDs and 30 sessions the adapter exported 1,220,237 bytes
raw and 161,975 bytes gzip. Five fresh Chrome pages per viewport on the
local Vite dev server gave these medians:

| Viewport | JSON.parse | Parse start to recommendation DOM | Navigation to recommendation DOM |
| --- | ---: | ---: | ---: |
| 1280 px | 4.4 ms | 17.3 ms | 91.9 ms |
| 375 px | 4.5 ms | 14.7 ms | 89.5 ms |

A MutationObserver captured the first recommendation DOM insertion.
Navigation time includes dev server and transfer time. The catalog remained
below the gzip threshold for proposing a shape change.
