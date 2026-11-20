"""Neural protocol regression tests; GPU integration evidence is in metrics/tv2-model-smoke.
TinyTrainableModel checks orchestration, not recommendation accuracy.
"""
import ast
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import typing
import unittest
from unittest.mock import patch
from evaluation.data import Catalog, read_sessions
from evaluation.run_neural import batches, evaluate, parser, preflight, rank_catalog, run
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "evaluation/tests/fixtures"
HAS_TORCH = importlib.util.find_spec("torch") is not None

class StreamingPartitionTests(unittest.TestCase):
    def test_streaming_partition_filter_and_tail_batch(self):
        rows = list(read_sessions(FIXTURES / "sessions.jsonl", day=2, split="validation"))
        self.assertEqual(len(rows), 3)
        catalog = Catalog.load(FIXTURES / "catalog.json")
        actual = list(batches(FIXTURES / "sessions.jsonl", catalog, 2, "validation", 2))
        self.assertEqual([len(b) for b in actual], [2, 1])

@unittest.skipUnless(HAS_TORCH, "PyTorch is provided by model runtime")
class NeuralOrchestration(unittest.TestCase):
    def test_catalog_filter_ties_and_small_catalog(self):
        import torch
        catalog = Catalog({3: "a", 4: "b"}, frozenset({0, 1, 2}), 0)
        self.assertEqual(rank_catalog(torch.tensor([[100., 90., 80., 1., 1.]]), catalog), [[3, 4]])
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            rank_catalog(torch.tensor([[0., 0., 0., float("nan"), 1.]]), catalog)

    def args(self, directory):
        root = Path(directory)
        schema = root / "schema.json"
        schema.write_text("{}")  # Mock model only; not a real Merlin schema.
        sessions = root / "sessions.jsonl"
        rows = list(read_sessions(FIXTURES / "sessions.jsonl"))
        rows.append({"user_session": "final-test", "day_index": 3,
                     "split": "test", "product_ids": [3, 25]})
        sessions.write_text("".join(json.dumps(row) + "\n" for row in rows))
        return parser().parse_args(["--model", "gru", "--data", str(sessions),
                                   "--schema", str(schema), "--catalog", str(FIXTURES / "catalog.json"),
                                   "--split", "test", "--train-through", "2", "--epochs", "1",
                                   "--device", "cpu", "--subset", "toy", "--run-id", "orchestration",
                                   "--output", str(root / "run"), "--config-frozen"])

    def test_daily_weights_continue_and_checkpoint_reproduces_final(self):
        import torch

        class TinyTrainableModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.logits = torch.nn.Parameter(torch.zeros(26))
                self.seen_train = []

            def forward(self, inputs, training=False, testing=False):
                seq = inputs["product_id-list"]
                if training:
                    self.seen_train.extend(seq.tolist())
                    labels = seq[:, 1:][seq[:, 1:] != 0]
                else:
                    labels = seq[torch.arange(len(seq)), (seq != 0).sum(dim=1) - 1]
                scores = self.logits.expand(len(labels), -1)
                return {"loss": torch.nn.functional.cross_entropy(scores, labels),
                        "labels": labels, "predictions": scores}

        with tempfile.TemporaryDirectory() as folder:
            args = self.args(folder)
            tiny = TinyTrainableModel()
            with patch("evaluation.run_neural.build_model", return_value=tiny) as factory:
                result = run(args)
            factory.assert_called_once()
            self.assertEqual(result["train_days"], [1, 2])
            self.assertEqual(len(tiny.seen_train), 2)
            self.assertEqual([r["train"]["updates"] for r in result["history"]], [1, 1])
            self.assertTrue(torch.any(tiny.logits != 0))
            # 24 and 25 are equally frequent in train day 2; 23 is holdout-only.
            self.assertGreater(tiny.logits[25].item(), tiny.logits[23].item())
            predictions = (args.output / "predictions.jsonl").read_text()
            args.checkpoint = args.output / "checkpoint.pt"
            args.output = Path(folder) / "replay"
            with patch("evaluation.run_neural.build_model", return_value=TinyTrainableModel()):
                replay = run(args)
            self.assertEqual(replay["history"], [])
            self.assertEqual((args.output / "predictions.jsonl").read_text(), predictions)
            args.seed = 2
            args.output = Path(folder) / "wrong-config"
            with patch("evaluation.run_neural.build_model", return_value=TinyTrainableModel()):
                with self.assertRaisesRegex(ValueError, "originating training configuration"):
                    run(args)

    def test_test_requires_frozen_config_and_correct_partition(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.args(folder)
            args.config_frozen = False
            with self.assertRaisesRegex(ValueError, "config-frozen"):
                preflight(args)
            args.config_frozen = True
            args.train_through = 1
            with self.assertRaisesRegex(ValueError, "D-1"):
                preflight(args)

    def test_wrong_runtime_label_is_an_error(self):
        import torch

        class WrongLabel(torch.nn.Module):
            def forward(self, inputs, **kwargs):
                n = len(inputs["product_id-list"])
                return {"labels": torch.zeros(n, dtype=torch.long), "predictions": torch.zeros(n, 26)}

        with tempfile.TemporaryDirectory() as folder:
            args = self.args(folder)
            catalog = Catalog.load(args.catalog)
            with self.assertRaisesRegex(ValueError, "last non-padding"):
                evaluate(WrongLabel(), args, catalog, 2, "validation", torch.device("cpu"),
                         Path(folder) / "wrong.jsonl")

    def test_pinned_masking_hides_target_and_gru_keeps_sessions_independent(self):
        import torch
        # Execute only pinned source classes, removing registration/doc decorators.
        # No stubs stand in for a full Transformers4Rec model or its runtime.
        source = subprocess.run(["git", "show", "reference/nvidia-transformers4rec:transformers4rec/torch/masking.py"], capture_output=True)
        if source.returncode:
            self.skipTest("Pinned reference branch unavailable")
        wanted = {"MaskSequence", "CausalLanguageModeling", "MaskedLanguageModeling"}
        nodes = [node for node in ast.parse(source.stdout.decode()).body
                 if isinstance(node, ast.ClassDef) and node.name in wanted]
        for node in nodes:
            for child in ast.walk(node):
                if hasattr(child, "decorator_list"):
                    child.decorator_list = []

        @dataclass
        class MaskingInfo:
            schema: object
            targets: object

        class OutputSizeMixin:
            pass

        namespace = {"torch": torch, "nn": torch.nn, "MaskingInfo": MaskingInfo,
                     "OutputSizeMixin": OutputSizeMixin, "Optional": typing.Optional,
                     "Dict": typing.Dict, "Any": typing.Any}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "pinned_masking.py", "exec"), namespace)
        torch.manual_seed(1)
        ids = torch.tensor([[3, 4, 5, 0], [3, 4, 6, 0]])
        embedded = torch.nn.Embedding(26, 4)(ids)
        causal = namespace["CausalLanguageModeling"](4, eval_on_last_item_seq_only=True)
        masked = causal(embedded, ids, training=False, testing=True)
        recurrent = torch.nn.GRU(4, 4, batch_first=True)
        both = recurrent(masked)[0]
        self.assertTrue(torch.allclose(both[0, 1], both[1, 1]))
        self.assertTrue(torch.allclose(both[:1], recurrent(masked[:1])[0]))
        self.assertEqual(causal.masked_targets[causal.masked_targets != 0].tolist(), [5, 6])
        mlm = namespace["MaskedLanguageModeling"](4, eval_on_last_item_seq_only=True)
        hidden = mlm(embedded, ids, training=False, testing=True)
        self.assertTrue(torch.allclose(hidden[0], hidden[1]))
        self.assertEqual(mlm.masked_targets[mlm.masked_targets != 0].tolist(), [5, 6])
