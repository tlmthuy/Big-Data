# Sample prediction export

**Toy data, not a benchmark result.** Source snapshot: team commit `43841c9`.
Contract merged in team commit `5f839a7`. TV2 format confirmation was reported by the project owner in this chat on 24/11/2026; the owner authorized integration. This confirms the sample format, not official benchmark results.

The adapter `app/export_prediction_samples.py` generates `app/samples/demo-data.json`
and `app/samples/sample-predictions.csv` together. The CSV lists one row per
run, session and recommendation rank, in artifact order.

| Field | Meaning and representation |
| --- | --- |
| `run_id`, `model`, `subset`, `split` | Run identity, model, delivered subset label and evaluation split. Present in both formats. |
| `data_kind`, `catalog_sha256` | Data classification and the SHA-256 recorded for the run catalog. Present in both formats. |
| `user_session` | Session key from the prediction artifact. |
| `prefix`, `target` | History and actual next item in original product IDs. JSON uses a history array. CSV joins the array with ` > `. |
| `top20`, `recommendations` | JSON lists up to 20 original product IDs and the corresponding rank, product ID and score records. Technical tokens are excluded. |
| `target_rank` | One-based position of the target in Top-20. A miss is JSON `null` and a blank CSV cell. |
| `rank`, `product_id`, `score` | Recommendation position, original ID and per-item score. CSV flattens these fields from JSON. TV2 exports no scores, so JSON uses `null` and CSV leaves the cell blank. |
| `schema`, `team_commit`, `generated_at`, `runs` | JSON envelope version, team source revision, export date when stamped, and run list. The envelope may also carry an overall `data_kind`. |
| `catalog`, `sessions`, `provenance` | JSON-only real-item catalog, sessions and traceability. Provenance records run and catalog paths, catalog match, evaluation day, experiment, score availability, metrics path and SHA-256, and any delivered mapping or vocabulary SHA-256. Missing checksums are null. Sampled exports also record the sample rule, seed and counts. |

The adapter verifies the run catalog against the SHA-256 in `metrics.json`
before decoding history and target. It cross-checks every delivered Top-20
original ID against that same catalog and rejects technical IDs. A recorded
line-ending-only difference is allowed for legacy toy runs. Real runs require
an exact byte match.

## Integration and reproduction

Source: [callmeshinny/demo-big-data at 643634a](https://github.com/callmeshinny/demo-big-data/tree/643634af898ea4a9d7145ea918a01009880491d4).
The original files are preserved in app/samples/. The adapter was renamed and its
module instructions adapted for this team repo. No UI, model or evaluation code
was changed. The bundled sample has six toy runs and eight session/run records.
The catalog itself contains the encoded-to-original mapping; separate mapping
and vocabulary checksums remain null when not delivered by the source run.

From the repository root, choose an existing output directory and a new JSON
filename. The exporter also writes sample-predictions.csv in that directory:

```bash
python -m app.export_prediction_samples --run metrics/tv2-toy-day1=evaluation/tests/fixtures/catalog.json --output metrics/local/prediction-sample.json
```

Create metrics/local/ first if absent. To export more runs, repeat --run with
RUN_DIR=CATALOG pairs from the bundled JSON provenance. Catalog line-ending-only
matching is allowed only for legacy toy runs; real runs require exact hashes.
The multi-run sample JSON is separate from app/public/demo-data.json, which
continues to serve the older draft UI.
