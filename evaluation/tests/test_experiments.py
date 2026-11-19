"""Offline protocol, streaming, stage logs and E5 regression tests.

TinyTrainableModel exercises orchestration only; it is not a GRU/XLNet result.
Optional source masking tests execute pinned classes in isolation, not Merlin.
"""

import argparse
import ast
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import typing
import unittest
from unittest.mock import patch

from benchmark.collect import run_command
from benchmark.scalability import summarize, write_outputs
from evaluation.data import Catalog, read_sessions
from evaluation.run_neural import batches, evaluate, parser, preflight, rank_catalog, run
from scripts.runs.run_experiments import resolve

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "evaluation/tests/fixtures"
HAS_TORCH = importlib.util.find_spec("torch") is not None


class ExperimentContracts(unittest.TestCase):
    def test_only_batch_changes_in_E3_and_E2_model_fixed(self):
        matrix = json.loads((ROOT / "configs/experiments.json").read_text())
        runs = matrix["runs"]
        self.assertEqual(len({r["run_id"] for r in runs}), 11)
        e2 = [r for r in runs if r["experiment"] == "E2"]
        self.assertEqual({r["subset"] for r in e2}, {"10", "25", "50", "100"})
        self.assertEqual({(r["model"], r["batch_size"], r["epochs"], r["seed"]) for r in e2},
                         {("gru", 256, 3, 1)})
        a, b = [r for r in runs if r["experiment"] == "E3"]
        self.assertEqual({a["batch_size"], b["batch_size"]}, {32, 128})
        for key in set(a) - {"run_id", "batch_size", "output_path", "command"}:
            self.assertEqual(a[key], b[key], key)

    def test_streaming_partition_filter_and_tail_batch(self):
        rows = list(read_sessions(FIXTURES / "sessions.jsonl", day=2, split="validation"))
        self.assertEqual(len(rows), 3)
        catalog = Catalog.load(FIXTURES / "catalog.json")
        actual = list(batches(FIXTURES / "sessions.jsonl", catalog, 2, "validation", 2))
        self.assertEqual([len(b) for b in actual], [2, 1])

    def test_template_cannot_be_executed_as_real_data(self):
        site = json.loads((ROOT / "configs/site.example.json").read_text())
        config = json.loads((ROOT / "configs/experiments.json").read_text())["runs"][0]
        with self.assertRaisesRegex(ValueError, "versions"):
            resolve(config, site, Path("unused"))

    def test_collector_preserves_success_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            good = run_command([sys.executable, "-c", "print('ok')"], root / "good")
            bad = run_command([sys.executable, "-c", "import sys; print('bad',file=sys.stderr); sys.exit(7)"], root / "bad")
            self.assertEqual(good["status"], "passed")
            self.assertEqual(bad["exit_code"], 7)
            self.assertIn("bad", (root / "bad/stderr.txt").read_text())
            self.assertTrue((root / "bad/run.json").is_file())


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


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "Parquet requires pyarrow")
class FormatTests(unittest.TestCase):
    def test_shared_preprocessing_command_binds_both_formats_and_writes_artifacts(self):
        import csv
        from benchmark.format_io import COLUMNS, prepare_pair, benchmark

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            csv_path, parquet_path = root / "events.csv", root / "events.parquet"
            with csv_path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(COLUMNS)
                writer.writerow(["2019-10-01", "view", "3", "4", "", "", "1", "9", "s"])
            prepare_pair(csv_path, parquet_path)
            worker = ("import pathlib,sys; p=pathlib.Path(sys.argv[3]); p.mkdir(); "
                      "(p/'binding.txt').write_text(sys.argv[1]+' '+sys.argv[2])")
            template = [sys.executable, "-c", worker, "{input_path}", "{input_format}", "{output_dir}"]
            for format_name in ["csv", "parquet"]:
                args = argparse.Namespace(csv=csv_path, parquet=parquet_path, format=format_name,
                                          output=root / format_name, preprocess_argv=json.dumps(template),
                                          read_only=False, run_id=format_name)
                result = benchmark(args)
                self.assertEqual(result["status"], "passed")
                self.assertTrue((args.output / "preprocessed/binding.txt").read_text().endswith(format_name))

    def test_pair_preserves_duplicate_events_and_rejects_changed_content(self):
        import csv
        from benchmark.format_io import COLUMNS, prepare_pair, content_fingerprint, benchmark

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            csv_path, parquet_path = root / "events.csv", root / "events.parquet"
            with csv_path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(COLUMNS)
                writer.writerows([["2019-10-01 00:00:00 UTC", "view", "3", "4", "", "brand", "1.00", "9", "s"]] * 2)
            self.assertEqual(prepare_pair(csv_path, parquet_path), 2)
            self.assertEqual(content_fingerprint(csv_path, "csv"), content_fingerprint(parquet_path, "parquet"))
            with self.assertRaises(ValueError):
                prepare_pair(csv_path, parquet_path)
            args = argparse.Namespace(csv=csv_path, parquet=parquet_path, format="csv", output=root / "read",
                                      preprocess_argv=None, read_only=True, run_id="diagnostic")
            result = benchmark(args)
            self.assertEqual(result["n_events"], 2)
            self.assertEqual(result["status"], "read_only_diagnostic")
            text = csv_path.read_text()
            csv_path.write_text(text.replace("1.00", "2.00"))
            args.output = root / "changed"
            with self.assertRaisesRegex(ValueError, "fingerprints differ"):
                benchmark(args)


class ScalabilityTests(unittest.TestCase):
    def test_e5_uses_actual_events_separates_first_seen_and_ignores_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for subset, events, status in [("10", 500_000, "passed"), ("25", 1_000_000, "passed"), ("50", 2_000_000, "failed")]:
                out = root / f"e2-gru-{subset}" / "artifacts"
                out.mkdir(parents=True)
                meta = {"run": {"experiment": "E2", "run_id": f"e2-gru-{subset}", "subset": subset,
                                "model": "gru", "batch_size": 256, "epochs": 3, "seed": 1,
                                "sequence_length": 20, "split": "test"},
                        "environment": {"sha256": "same-runtime"},
                        "pipeline_metrics": {"n_events": events, "read_seconds": 2, "preprocessing_seconds": 4,
                                             "first_seen_seconds": 100, "first_seen_artifact": "shared"}}
                (out.parent / "run.json").write_text(json.dumps({"status": status, "metadata": meta,
                             "elapsed_seconds": 50, "peak_process_tree_rss_bytes": 123}))
                (out / "metrics.json").write_text(json.dumps({"train_with_input_scan_seconds": 10, "inference_seconds": 1,
                    "training_config": {"model": "gru", "batch_size": 256, "epochs": 3, "seed": 1, "learning_rate": 0.00071},
                    "config": {"checkpoint": None, "eval_batch_size": 32, "device": "cuda"},
                    "source_sha256": {"models/session_models.py": "same-code"},
                    "train_days": [1, 2], "eval_day": 3, "eval_split": "test", "split_counts": [{"day_index": 3}]}))
            rows = summarize(root)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["seconds_per_million_events"], 34)
            self.assertEqual(rows[0]["composed_seconds_with_first_seen"], 117)
            self.assertEqual(rows[0]["bottleneck"], "train_including_sequence_io")
            write_outputs(rows, root / "report")
            self.assertEqual(json.loads((root / "report/summary.json").read_text())["status"], "partial")
            self.assertTrue((root / "report/scalability.svg").exists())
            changed_path = root / "e2-gru-25/artifacts/metrics.json"
            changed = json.loads(changed_path.read_text())
            changed["training_config"]["learning_rate"] = 0.001
            changed_path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "effective model/config/code"):
                summarize(root)
            changed["training_config"]["learning_rate"] = 0.00071
            changed["source_sha256"]["models/session_models.py"] = "different-code"
            changed_path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "effective model/config/code"):
                summarize(root)


if __name__ == "__main__":
    unittest.main()
