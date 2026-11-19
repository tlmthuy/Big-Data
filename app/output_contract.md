# TV4 model output contract review

## 1. Purpose

Document the fields needed for the 20 November 2026 demo handoff and identify the decisions TV2 needs to approve before TV4 prepares the 21 November sample.

## 2. Scope

Status: **Pending TV2 Confirmation**. Evidence comes from `main` at `b40cd76` and the TV2 feature branch at `7277b65`. The checked-in prediction evidence is a three-session Popularity toy run. TV1's current manifest describes intermediate monthly artifacts. The real model-ready sequences, runtime catalog and real prediction package still need verification.

## 3. Input Contract

For offline evaluation, the persisted input is the full, ordered sequence including the held-out last item. Parquet uses `user_session` and `product_id-list` with partition/split inferred from the path. Debug JSONL uses `user_session`, `day_index`, `split` and `product_ids`. `Catalog.sequence` removes right padding and requires 2–20 real encoded IDs. A prediction request conceptually uses the prefix of 1–19 items. The session ID identifies the record for joining and display. Popularity uses a shared train-derived ranking independent of the prefix.

## 4. Prediction Output Contract

The current Popularity CLI writes one record per evaluated session to `predictions.jsonl`. Its keys are `user_session`, `prefix`, `target`, `top20` and `product_ids`. The last two arrays are aligned by position. Join the file with its run metadata in `metrics.json` and its exact catalog. The reviewed TV2 neural branch writes the same five keys in offline evaluation. The production delivery method and public names remain pending TV2 confirmation. React currently reads a separate bundled toy JSON file.

## 5. Field Definitions

Required/optional applies to the specified layer. Pending fields have no approved delivery requirement.

| Field | Meaning | Data type | Input/Output | Required/Optional | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `user_session` | Session join key carried from input to prediction | String in toy and intermediate TV1 manifest. Loader preserves the input value. | Input and output | Required | [audit_sessions](../evaluation/data.py), [TV1 manifest](../data/manifests/tv1_data_handoff.json) | CONFIRMED key. Final original or encoded representation pending TV2 confirmation. |
| `product_id-list` / `product_ids` | Full offline sequence in Parquet / debug JSONL | List of encoded integers | Offline input | Required for its format | [read_sessions](../evaluation/data.py) | CONFIRMED |
| `prefix` | History before target. `input_prefix` is a descriptive alias. | List of encoded integers in prediction JSONL | Logical model input and offline output | Required in prediction row | [run](../evaluation/run_popularity.py) | CONFIRMED |
| `model` | Model identity. `model_name` is a descriptive alias. | String | Run metadata | Required per run | [metrics.json](../metrics/tv2-toy-day1/metrics.json) | CONFIRMED |
| `top20` | Ordered recommendations | List of at most 20 distinct encoded integers | Offline output | Required | [recommend](../models/popularity.py), [predictions.jsonl](../metrics/tv2-toy-day1/predictions.jsonl) | CONFIRMED |
| `product_ids` / `product_id` | Original IDs for ranked items / original ID in each catalog entry | List of strings / string in the normalized mapping | Output / mapping | Required in current prediction row / catalog | [run](../evaluation/run_popularity.py), [Catalog.load](../evaluation/data.py) | CONFIRMED |
| `encoded_id` | Vocabulary index identifying one product | Nonnegative integer | Mapping | Required in current catalog | [Catalog.load](../evaluation/data.py) | CONFIRMED |
| `score` | Train count for Popularity. Neural ranking uses model scores internally. | Integer count or neural floating-point value internally | Potential output | Pending | [Popularity](../models/popularity.py), [TV2 neural evaluator](https://github.com/tlmthuy/Big-Data/blob/7277b65a0121f0f193fa046e33c37597f94561e7/evaluation/run_neural.py) | NEED TV2 CONFIRMATION for export, units and availability |
| `rank` | One-based position in the ordered list | Integer 1–20 | Derived display output | Optional as a separate field | [score_session](../evaluation/ranking.py) | CONFIRMED as position. Explicit field PROPOSED. |
| `target` | Last real encoded item. Also called ground truth. | Integer | Evaluation and demo output | Required for offline evaluation and demo display | [run](../evaluation/run_popularity.py), [model protocol](../docs/modeling/model_protocol.md) | CONFIRMED |
| `run_id` | Identifier linking rows to run metadata | String | Run metadata | Required per run | [metrics.json](../metrics/tv2-toy-day1/metrics.json) | CONFIRMED |
| Catalog metadata | Catalog reference, checksum and context. Popularity records subset and evaluation split/day separately. | Path and SHA-256 strings, subset/split metadata and integer day | Run metadata | Required for traceability | [run](../evaluation/run_popularity.py), [metrics.json](../metrics/tv2-toy-day1/metrics.json) | CONFIRMED for current CLI. Delivery naming pending TV2 confirmation. |
| `recommendations` | Optional demo adapter array of per-item records | List of objects | Potential demo output | Optional proposal | Existing ordered arrays in [predictions.jsonl](../metrics/tv2-toy-day1/predictions.jsonl) | PROPOSED |
| Target in live request | Held-out item for comparison | — | Live inference input | — | [model protocol](../docs/modeling/model_protocol.md) | NOT APPLICABLE |

## 6. Session and Product ID Mapping

Use the catalog from the same subset and run. `Catalog.load` validates a one-to-one mapping, converts original product IDs to strings and rejects overlaps with declared technical IDs. The demo should map prefix, target and recommendations through that same catalog. In the toy catalog, integer `3` maps to original string `p3`. Converting an encoded integer to text only yields `"3"`. Use catalog metadata for actual padding, null, OOV and mask IDs. Preserve the session key and confirm the original/encoded session mapping with TV2 and TV1 before joining production files.

## 7. Ranking Rules

Return at most 20 unique real items, ordered by descending score from the full real-item catalog fitted on the subset's weekly data. Items already in the prefix remain eligible. Exclude technical tokens and retain the artifact order in the demo. Popularity ties use ascending encoded ID. Its unseen catalog items have a count of zero. The TV2 feature branch's `rank_catalog` also uses ascending encoded ID for equal neural scores. This is verified in branch code. The exported rows contain no numeric score or explicit rank. A rank derives from position plus one. Treat internal neural scores as ranking values and ask TV2 to specify the semantics of any exported score.

## 8. Ground Truth and Target Handling

Take the last item after removing right padding from the retained sequence. All preceding items form the prefix. Keep the target available to the evaluator and demo even when absent from Top-20. In the offline neural evaluator, pass the full sequence to the library once. Causal shift for GRU or masking for XLNet isolates the prediction context. The branch compares runtime labels with the last-item labels and expects one prediction per session. Live inference uses observed history only.

## 9. Model Compatibility

| Model | Evidence and status |
| --- | --- |
| Popularity | Integrated on main. `Popularity.update_partition` counts real train interactions, including train-session last items. `recommend` ranks once per run. `popularity.json` stores observed counts separately. Checked-in rankings use toy data. |
| GRU | Causal masking in TV2 branch `build_model`. Its offline evaluator ranks the scores returned by the prediction head. The branch's runtime check reports missing `transformers4rec`. Successful predictions remain unverified. |
| XLNet | Masked language modeling in TV2 branch `build_model`. It uses the same offline writer as GRU. The branch's runtime check reports missing `transformers4rec`. Successful predictions remain unverified. |

NVIDIA Notebook 03 demonstrates GRU/XLNet and computes library metrics. At the pinned source tree, `NextItemPredictionTask.forward` returns labels and prediction tensors in evaluation, or scores and vocabulary indices with `top_k` in inference. Its projection returns logits with optional temperature scaling. The team's exporter applies the real-item catalog and reverse mapping and writes per-session artifacts with separate run metadata. The NVIDIA reference is Apache-2.0. This review reuses no NVIDIA code.

## 10. Confirmed vs Proposed Fields

The current file shape and ordering are confirmed by code and toy output. A demo adapter with named per-item fields and explicit rank is proposed. Public naming, score delivery and production ID representation are pending TV2 confirmation. The bundled UI toy fixture uses stringified encoded IDs and lists 21 candidates. The source toy catalog has 23. Use the full source catalog and its mapping to verify the integration.

## 11. Open Questions for TV2

1. Will the demo receive offline prediction files and run metadata, a callable for live inference, or both? Which format and keys should TV4 use?
2. Will each model export a score? For Popularity, can TV4 read counts with a zero default for unseen catalog items? For GRU and XLNet, what do exported scores represent and should they be displayed? Is rank derived from order or delivered explicitly?
3. What are the production locations and version identifiers for each subset's catalog and inverse mapping? Which session key joins predictions to session metadata and where is its mapping when encoded?
4. Which run package, validation/test partition and catalog should TV4 use for the demo? Please approve this contract before TV4 drafts the 21 November sample.

## 12. References to Repository Files

- [Project scope](../AGENTS.md), [TV4 schedule](../docs/team_tasks.md), [team handoff](../docs/handoff.md).
- [Problem definition](../docs/modeling/next_item_problem.md), [model protocol](../docs/modeling/model_protocol.md), [TV2 runbook](../docs/modeling/tv2_runbook.md).
- [Toy sessions](../evaluation/tests/fixtures/sessions.jsonl), [toy catalog](../evaluation/tests/fixtures/catalog.json), [Popularity counts](../metrics/tv2-toy-day1/popularity.json), [React fixture](public/demo-data.json), [demo review](TODO.md).
- [TV2 model code at 7277b65](https://github.com/tlmthuy/Big-Data/blob/7277b65a0121f0f193fa046e33c37597f94561e7/models/session_models.py), [GRU runtime log](https://github.com/tlmthuy/Big-Data/blob/7277b65a0121f0f193fa046e33c37597f94561e7/metrics/tv2-model-scripts/gru-runtime/failure.json), [XLNet runtime log](https://github.com/tlmthuy/Big-Data/blob/7277b65a0121f0f193fa046e33c37597f94561e7/metrics/tv2-model-scripts/xlnet-runtime/failure.json).
- [NVIDIA tutorial](https://nvidia-merlin.github.io/Transformers4Rec/stable/examples/tutorial/03-Session-based-recsys.html), [reference instructions and license](../docs/references.md). The imported reference tree at `e2859fd` matches the documented tree hash `0cd72aa1d3abd17cd65d46b9c1314b4ea26db9a6` for upstream pin `f0ca2b5343dd1e40b5d2422b942f014b224f5c20`.

## Read-only toy verification

Run from the repository root. This checks existing files and prints the target's rank for each session.

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

from evaluation.data import Catalog, read_sessions

fixture = Path("evaluation/tests/fixtures")
run = Path("metrics/tv2-toy-day1")
catalog_path = fixture / "catalog.json"
sessions_path = fixture / "sessions.jsonl"
catalog = Catalog.load(catalog_path)
metadata = json.loads((run / "metrics.json").read_text())
assert metadata["K"] == 20
assert metadata["model"] == "Popularity"
assert metadata["run_id"] == run.name
for key, path in (("catalog", catalog_path), ("sessions", sessions_path)):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata["artifacts"][key]["sha256"]
sessions = {
    row["user_session"]: catalog.sequence(row["product_ids"])
    for row in read_sessions(sessions_path)
    if row["day_index"] == metadata["eval_day"] and row["split"] == metadata["eval_split"]
}
rows = [json.loads(line) for line in (run / "predictions.jsonl").read_text().splitlines()]
counts = json.loads((run / "popularity.json").read_text())["counts"]
expected = sorted(catalog.products, key=lambda item: (-counts.get(str(item), 0), item))[:20]
assert len(rows) == len(sessions) == metadata["n_sessions"]
assert {row["user_session"] for row in rows} == sessions.keys()
for row in rows:
    assert row.keys() == {"user_session", "prefix", "target", "top20", "product_ids"}
    session, prefix, target, top20, product_ids = (
        row[key] for key in ("user_session", "prefix", "target", "top20", "product_ids")
    )
    assert isinstance(session, str) and type(target) is int
    assert all(type(item) is int for item in prefix + top20)
    assert prefix + [target] == sessions[session]
    assert top20 == expected and not set(top20) & catalog.technical_ids
    assert product_ids == [catalog.products[item] for item in top20]
    rank = top20.index(target) + 1 if target in top20 else "miss"
    print(session, catalog.products[target], rank)
demo = json.loads(Path("app/public/demo-data.json").read_text())
assert len(catalog.products) == 23 and len(demo["catalog"]) == 21
print("Catalog sizes", len(catalog.products), len(demo["catalog"]))
PY
```
