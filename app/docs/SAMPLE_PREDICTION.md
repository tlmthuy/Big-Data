# Sample prediction export

**Toy data, not a benchmark result.** Source snapshot: team commit `43841c9`.
Contract merged in team commit `5f839a7`; written TV2 confirmation pending.

The adapter `scripts/export_demo_data.py` generates `public/demo-data.json`
and `public/sample-predictions.csv` together. The CSV lists one row per
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
