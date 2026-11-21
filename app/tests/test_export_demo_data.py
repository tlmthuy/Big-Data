"""Run with PYTHONPATH=../Big-Data:scripts python3 -m unittest discover -s tests."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from export_demo_data import export_run


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
