
# Session-Based Recommendation Demo

React + Vite demo for session-based next-item recommendation.

Status: draft UI with toy data, accepted for integration on 20/11/2026.
The display protocol below describes the intended behavior; known unavailable-model
and data-validation issues remain. See [TODO.md](TODO.md) for the
review findings, TV2 dependencies and checks required before UI acceptance.

## Run locally

```bash
cd app
npm install
npm run dev
```

Open the URL printed by Vite. Use `npm run build` to create a production build.

## Display protocol

- The history is the session **prefix** after the target is removed.
- The actual next item is always shown as a separate ground-truth card, even when it is outside Top-20.
- Changing model keeps the selected session, subset, split and candidate catalog unchanged.
- Product IDs are shown as original IDs. The demo does not remove items that already appear in the history.
- The bundled JSON is TV2 toy output, not an E1 benchmark or real-data result.

## Prediction data

From the repository root, run the existing Popularity CLI on the toy sessions.
This writes `predictions.jsonl` and `metrics.json` to a new directory. Change
both the run ID and output directory for a repeat run.

```bash
python3 -m evaluation.run_popularity \
  --sessions evaluation/tests/fixtures/sessions.jsonl \
  --catalog evaluation/tests/fixtures/catalog.json \
  --train-through 1 --subset toy --run-id tv4-local-toy \
  --output metrics/local/tv4-local-toy
```

Convert the ranked predictions into the file that React loads at
`/demo-data.json`. The exporter preserves the published ranking order, verifies
the run's catalog checksum, and maps prefix, target and Top-20 to original
product IDs. It includes all 23 toy catalog entries.

```bash
python3 -m app.export_demo_data \
  --run-dir metrics/local/tv4-local-toy \
  --catalog evaluation/tests/fixtures/catalog.json \
  --output app/public/demo-data.json
```

To reproduce the bundled file from the checked-in TV2 output, use
`--run-dir metrics/tv2-toy-day1` in the export command. Start the UI using
[Run locally](#run-locally) and select `rank1`, `rank20`, or `miss` to see the
mapped history, target, and rankings.

GRU and XLNet are shown as unavailable. See the [output contract](output_contract.md)
for the reviewed offline fields and the pending production handoff decisions.

## Approved prediction samples

See [samples/README.md](samples/README.md), [JSON](samples/demo-data.json) and [CSV](samples/sample-predictions.csv). TV2 format confirmation was reported by the project owner; these are toy samples, separate from the draft UI fixture.
