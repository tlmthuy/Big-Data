# Copyright 2022 NVIDIA Corporation. All Rights Reserved.
# Adapted by the project team, 2026. Licensed under Apache-2.0.
# Source: NVIDIA-Merlin/Transformers4Rec f0ca2b5343dd1e40b5d2422b942f014b224f5c20,
# examples/tutorial/03-Session-based-recsys.ipynb, cells 20/22/26 and 62/64.
# License: docs/vendor/nvidia-transformers4rec/upstream/LICENSE.
"""Notebook architectures; the fitted schema is loaded, never refitted here."""

from pathlib import Path

SOURCE_COMMIT = "f0ca2b5343dd1e40b5d2422b942f014b224f5c20"
DEFAULTS = {"gru": {"d_model": 128, "learning_rate": 0.00071},
            "xlnet": {"d_model": 192, "learning_rate": 0.000666}}
FEATURE = "product_id-list"


def build_model(name, schema_path, catalog):
    import torch
    import transformers4rec.torch as tr
    from merlin_standard_lib import Schema, categorical_cardinalities

    path = Path(schema_path)
    schema = Schema()
    schema = (schema.from_json(str(path)) if path.suffix == ".json"
              else schema.from_proto_text(str(path)))
    schema = schema.select_by_name([FEATURE])
    if schema.column_names != [FEATURE]:
        raise ValueError(f"Fitted schema must contain {FEATURE}")
    cardinality = categorical_cardinalities(schema)[FEATURE]
    if max(catalog.products.keys() | catalog.technical_ids) >= cardinality:
        raise ValueError("Catalog IDs exceed fitted schema cardinality")
    width = DEFAULTS[name]["d_model"]
    masking = "causal" if name == "gru" else "mlm"
    kwargs = {"d_output": width} if name == "xlnet" else {}
    inputs = tr.TabularSequenceFeatures.from_schema(
        schema, max_sequence_length=20, masking=masking,
        padding_idx=catalog.padding_id, eval_on_last_item_seq_only=True, **kwargs)
    if inputs.item_id != FEATURE or not inputs.masking.eval_on_last_item_seq_only:
        raise ValueError("Runtime schema/masking does not match the fixed item-only protocol")
    if name == "gru":
        # Source tensors are [batch, sequence, hidden]; batch_first prevents
        # independent sessions from being treated as recurrent time steps.
        recurrent = torch.nn.GRU(width, width, num_layers=1, batch_first=True)
        body = tr.SequentialBlock(inputs, tr.MLPBlock([width]),
                                  tr.Block(recurrent, [None, 20, width]))
    else:
        config = tr.XLNetConfig.build(d_model=width, n_head=4, n_layer=2,
                                     total_seq_length=20)
        body = tr.SequentialBlock(inputs, tr.MLPBlock([width]),
                                  tr.TransformerBlock(config, masking=inputs.masking))
    task = tr.NextItemPredictionTask(weight_tying=True, metrics=[],
                                     padding_idx=catalog.padding_id)
    model = tr.Model(tr.Head(body, task, inputs=inputs), max_sequence_length=20)
    if task.target_dim != cardinality:
        raise ValueError("Prediction head cardinality disagrees with the fitted vocabulary")
    return model
