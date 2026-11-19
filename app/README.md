
# Session-Based Recommendation Demo

React + Vite demo for session-based next-item recommendation.

Status: draft UI with toy data, accepted for integration on 20/11/2026.
The display protocol below describes the intended behavior; known ID/catalog
and unavailable-model display issues remain. See [TODO.md](TODO.md) for the
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

The demo reads `public/demo-data.json`. Its `Popularity` entries come from the checked-in TV2 toy predictions:

- `metrics/tv2-toy-day1/predictions.jsonl`
- `metrics/tv2-toy-day1/metrics.json`

GRU and XLNet are shown as unavailable until TV2 provides prediction JSONL, run metadata and an approved catalog for the same subset/split. No synthetic GRU/XLNet rankings are generated.

Live Python inference can be added with FastAPI later. Its response should use the same shape:

```json
{
  "model": "Popularity",
  "subset": "toy",
  "split": "validation",
  "catalog": ["3", "4", "5"],
  "sessions": [
    {
      "user_session": "rank1",
      "prefix": ["4"],
      "target": "3",
      "top20": ["3", "4", "5"]
    }
  ]
}
```
