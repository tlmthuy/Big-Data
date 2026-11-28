"""Run with PYTHONPATH=../Big-Data:scripts python3 -m unittest discover -s tests."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from export_demo_data import export_run, public_product_lookup_path, sample_runs, subset_catalogs


class PredictionAdapterTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.run = self.workspace / "run"
        artifacts = self.run / "artifacts"
        artifacts.mkdir(parents=True)
        self.write(self.run / "run.json", {"metadata": {"data_kind": "real", "artifacts": {"mapping": {"sha256": "a" * 64}}}})
        self.catalog = self.workspace / "catalog.json"
        self.write(self.catalog, {
            "subset": "10",
            "technical_ids": {"padding": 0, "null": 1, "oov": 2, "mask": 99},
            "items": [{"encoded_id": 3, "product_id": "p-history"}, {"encoded_id": 7, "product_id": "p-target"}],
        })
        self.sha = hashlib.sha256(self.catalog.read_bytes()).hexdigest()
        self.write(artifacts / "metrics.json", {
            "K": 20, "model": "gru", "subset": "10", "eval_split": "test", "run_id": "fixture",
            "n_sessions": 1, "artifacts": {"catalog": {"sha256": self.sha}},
        })
        self.write(artifacts / "predictions.jsonl", {
            "user_session": "test", "prefix": [3], "target": 7, "top20": [7], "product_ids": ["p-target"],
        })
        (artifacts / "validation-day1.jsonl").write_text("malformed", encoding="utf-8")

    def write(self, path, data):
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def test_optional_product_lookup_path_is_relative_json_or_null(self):
        self.assertIsNone(public_product_lookup_path(None))
        self.assertEqual(public_product_lookup_path("product-info.json"), "product-info.json")
        self.assertEqual(public_product_lookup_path("metadata/products.json"), "metadata/products.json")
        for path in ("/product-info.json", "../product-info.json", "product-info.csv", r"..\product-info.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                public_product_lookup_path(path)

    def test_maps_history_and_target_and_ignores_validation_files(self):
        row, = export_run(self.run, self.catalog)["sessions"]
        self.assertEqual(row["prefix"], ["p-history"])
        self.assertEqual(row["target"], "p-target")
        self.assertEqual(row["top20"], ["p-target"])
        self.assertIsNone(row["recommendations"][0]["score"])

    def test_copies_checksums_from_artifact_and_collector(self):
        run = export_run(self.run, self.catalog)
        provenance = run["provenance"]
        path = self.run / "artifacts/metrics.json"
        self.assertEqual(provenance["metrics_path"], path.as_posix())
        self.assertEqual(provenance["metrics_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(provenance["mapping_sha256"], "a" * 64)
        self.assertIsNone(provenance["vocabulary_sha256"])

    def test_requires_exact_catalog_from_the_run(self):
        message = f"Ask TV2 for catalog.json with SHA-256 {self.sha} from the same run"
        self.catalog.write_bytes(self.catalog.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(ValueError, message):
            export_run(self.run, self.catalog)
        self.catalog.unlink()
        with self.assertRaisesRegex(ValueError, message):
            export_run(self.run, self.catalog)

    def test_three_row_slice_samples_same_sessions_and_keeps_only_used_catalog_ids(self):
        runs = []
        for run_id, model in (("e1-popularity-010", "Popularity"), ("e1-gru-010", "GRU"), ("e1-xlnet-010", "XLNet")):
            run_dir = self.workspace / run_id
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True)
            self.write(run_dir / "run.json", {"metadata": {"data_kind": "real"}})
            self.write(artifacts / "metrics.json", {
                "K": 20, "model": model, "subset": 10, "eval_split": "test", "run_id": run_id,
                "n_sessions": 3, "eval_day": 7, "artifacts": {"catalog": {"sha256": self.sha}},
            })
            lines = [
                {"user_session": str(i), "prefix": [3], "target": 7, "top20": [7], "product_ids": ["p-target"]}
                for i in range(3)
            ]
            (artifacts / "predictions.jsonl").write_text("".join(json.dumps(row) + "\n" for row in lines), encoding="utf-8")
            runs.append(export_run(run_dir, self.catalog))
        sample_runs(runs, 2, 1)
        subset_catalogs(runs)
        session_sets = [{row["user_session"] for row in run["sessions"]} for run in runs]
        self.assertEqual(session_sets[0], session_sets[1])
        self.assertEqual(session_sets[1], session_sets[2])
        for run in runs:
            allowed = set(run["catalog"])
            self.assertTrue(all(item in allowed for row in run["sessions"] for item in [*row["prefix"], row["target"], *row["top20"]]))
            self.assertTrue(all(row["target_rank"] == row["top20"].index(row["target"]) + 1 for row in run["sessions"]))
            self.assertEqual(run["catalog_size"], 2)
