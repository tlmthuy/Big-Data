"""Hand-calculated cases, data-contract checks and cumulative leakage regression."""

import argparse
import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from evaluation.data import Catalog, audit_sessions, read_sessions
from evaluation.ranking import RankingMetrics, score_session
from evaluation.run_popularity import run
from models.popularity import Popularity

FIXTURES = Path(__file__).parent / "fixtures"


class MetricTests(unittest.TestCase):
    def test_hand_calculated_ranks(self):
        ranking = list(range(3, 24))
        for target, expected_recall, expected_ndcg in [
            (3, 1, 1), (4, 1, 0.6309297535714575),
            (22, 1, 0.227670248696953), (23, 0, 0), (99, 0, 0),
        ]:
            with self.subTest(target=target):
                recall, ndcg = score_session(target, ranking)
                self.assertEqual(recall, expected_recall)
                self.assertAlmostEqual(ndcg, expected_ndcg)

    def test_session_weighting_not_batch_means(self):
        metric = RankingMetrics()
        metric.update(3, [3])
        for _ in range(3):
            metric.update(4, [3])
        self.assertEqual(metric.compute()["Recall@20"], 0.25)
        self.assertEqual(metric.compute()["NDCG@20"], 0.25)

    def test_empty_and_duplicate_predictions(self):
        self.assertEqual(score_session(3, []), (0, 0))
        with self.assertRaises(ValueError):
            score_session(3, [3, 3])
        with self.assertRaises(ValueError):
            RankingMetrics().compute()


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog.load(FIXTURES / "catalog.json")

    def test_padding_seen_items_zero_scores_and_ties(self):
        model = Popularity(self.catalog)
        model.update_partition(1, [{"day_index": 1, "split": "train",
                                    "product_ids": [5, 3, 5, 0, 0]}])
        self.assertEqual(model.counts, {5: 2, 3: 1})
        self.assertEqual(model.recommend(), [5, 3, 4, *range(6, 23)])

    def test_cumulative_partition_once_and_train_only(self):
        model = Popularity(self.catalog)
        for day in [1, 2]:
            model.update_partition(day, [{"day_index": day, "split": "train",
                                          "product_ids": [3, 4]}])
        self.assertEqual(model.counts, {3: 2, 4: 2})
        with self.assertRaises(ValueError):
            model.update_partition(2, [])
        with self.assertRaises(ValueError):
            model.update_partition(3, [{"day_index": 3, "split": "test",
                                        "product_ids": [5, 6]}])
        self.assertEqual(model.counts, {3: 2, 4: 2})

    def test_invalid_sequences(self):
        for values in [[3], [3, 1], [3, 2], [3, 26], [3, 0, 4], [3, 4] * 11]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.catalog.sequence(values)

    def test_duplicate_membership_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.jsonl"
            row = {"user_session": "same", "day_index": 1,
                   "split": "train", "product_ids": [3, 4]}
            path.write_text(json.dumps(row) + "\n" + json.dumps(row), encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_sessions(path, self.catalog)

    def test_end_to_end_ignores_future_train_and_all_holdout(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(sessions=FIXTURES / "sessions.jsonl",
                                      catalog=FIXTURES / "catalog.json", train_through=1,
                                      eval_split="validation", subset="toy", run_id="test",
                                      output=Path(directory) / "run")
            result = run(args)
            self.assertEqual(result["n_sessions"], 3)
            self.assertAlmostEqual(result["Recall@20"], 2 / 3)
            self.assertAlmostEqual(result["NDCG@20"], (1 + 0.227670248696953) / 3)
            state = json.loads((args.output / "popularity.json").read_text())
            self.assertEqual(state["counts"], {"3": 2, "4": 1, "5": 1})
            args.output = Path(directory) / "run2"
            args.train_through = 2
            result = run(args)
            state = json.loads((args.output / "popularity.json").read_text())
            self.assertEqual(state["counts"], {"3": 2, "4": 1, "5": 1, "24": 1, "25": 2})
            self.assertEqual(result["Recall@20"], 1)

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "Parquet requires pyarrow")
    def test_nvidia_parquet_layout_matches_jsonl(self):
        import pyarrow as pa
        import pyarrow.parquet as pq

        rows = list(read_sessions(FIXTURES / "sessions.jsonl"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sessions"
            for day in {row["day_index"] for row in rows}:
                (root / str(day)).mkdir(parents=True)
                for name, split in [("train", "train"), ("valid", "validation"), ("test", "test")]:
                    partition = [{"user_session": row["user_session"], "day_index": day,
                                  "product_id-list": row["product_ids"]}
                                 for row in rows if row["day_index"] == day and row["split"] == split]
                    if partition:
                        pq.write_table(pa.Table.from_pylist(partition), root / str(day) / f"{name}.parquet")
            self.assertEqual(audit_sessions(root, self.catalog),
                             audit_sessions(FIXTURES / "sessions.jsonl", self.catalog))
            result = run(argparse.Namespace(sessions=root, catalog=FIXTURES / "catalog.json",
                                           train_through=1, eval_split="validation", subset="toy",
                                           run_id="parquet-test", output=Path(directory) / "run"))
            self.assertAlmostEqual(result["Recall@20"], 2 / 3)

    def test_catalog_cannot_include_technical_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps({"technical_ids": {"padding": 0, "null": 1, "oov": 2},
                                        "items": [{"encoded_id": 0, "product_id": 123}]}))
            with self.assertRaises(ValueError):
                Catalog.load(path)

    def test_test_split_blocked_until_protocol_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(sessions=FIXTURES / "sessions.jsonl",
                                      catalog=FIXTURES / "catalog.json", train_through=1,
                                      eval_split="test", subset="toy", run_id="test",
                                      output=Path(directory) / "run")
            with self.assertRaisesRegex(ValueError, "test schedule"):
                run(args)
            self.assertFalse(args.output.exists())


if __name__ == "__main__":
    unittest.main()
