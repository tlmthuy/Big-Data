"""Inference comparison includes split reads and one-time ranking setup."""

import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation.data import Catalog, read_sessions
from evaluation.run_popularity import run
from models.popularity import Popularity

FIXTURES = Path(__file__).parent / "fixtures"


class InferenceTimingTests(unittest.TestCase):
    def clock_and_reader(self):
        clock = [0.0]

        def reader(path, day=None, split=None):
            for row in read_sessions(path, day=day, split=split):
                if day == 2:
                    clock[0] += 7.0  # deterministic evaluation input/decode cost
                yield row

        return clock, reader

    def test_popularity_includes_reads_and_one_time_catalog_ranking(self):
        clock, reader = self.clock_and_reader()
        recommend = Popularity.recommend

        def timed_recommend(model):
            clock[0] += 2.0
            return recommend(model)

        with tempfile.TemporaryDirectory() as folder:
            args = argparse.Namespace(sessions=FIXTURES / "sessions.jsonl",
                                      catalog=FIXTURES / "catalog.json", train_through=1,
                                      eval_split="validation", subset="toy", run_id="timing",
                                      output=Path(folder) / "run")
            with patch("time.perf_counter", side_effect=lambda: clock[0]), \
                    patch("evaluation.run_popularity.read_sessions", side_effect=reader), \
                    patch.object(Popularity, "recommend", timed_recommend):
                result = run(args)
        self.assertEqual(result["inference_seconds"], 23.0)
        self.assertEqual(result["prediction_compute_seconds"], 2.0)
        self.assertEqual(result["inference_timing_protocol"], "full_evaluation_wall_v1")
        self.assertEqual(result["evaluation_with_io_seconds"], 23.0)
        self.assertAlmostEqual(result["inference_ms_per_session"], 23_000 / 3)

    @unittest.skipUnless(importlib.util.find_spec("torch"), "Requires model runtime")
    def test_neural_uses_the_same_boundary_and_session_denominator(self):
        import torch
        from evaluation.run_neural import evaluate

        clock, reader = self.clock_and_reader()

        class TimedModel(torch.nn.Module):
            def forward(self, inputs, **kwargs):
                clock[0] += 3.0
                seq = inputs["product_id-list"]
                labels = seq[torch.arange(len(seq)), (seq != 0).sum(dim=1) - 1]
                return {"labels": labels, "predictions": torch.zeros(len(seq), 100)}

        args = argparse.Namespace(data=FIXTURES / "sessions.jsonl", eval_batch_size=2)
        with tempfile.TemporaryDirectory() as folder:
            with patch("time.perf_counter", side_effect=lambda: clock[0]), \
                    patch("evaluation.run_neural.read_sessions", side_effect=reader):
                result = evaluate(TimedModel(), args, Catalog.load(FIXTURES / "catalog.json"),
                                  2, "validation", torch.device("cpu"), Path(folder) / "out.jsonl")
        self.assertEqual(result["inference_seconds"], 27.0)
        self.assertEqual(result["prediction_compute_seconds"], 6.0)
        self.assertEqual(result["inference_timing_protocol"], "full_evaluation_wall_v1")
        self.assertEqual(result["evaluation_with_io_seconds"], 27.0)
        self.assertEqual(result["inference_ms_per_session"], 9_000)
