import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from evaluation.run_popularity import sha256
from scripts.runs.prepare_real_smoke_cohort import prepare


ROOT = Path(__file__).resolve().parents[2]
HAS_ARROW = importlib.util.find_spec("pyarrow") is not None


@unittest.skipUnless(HAS_ARROW, "pyarrow is required to exercise the Parquet cohort builder")
class RealSmokeCohortTests(unittest.TestCase):
    def setUp(self):
        import pyarrow as pa
        import pyarrow.parquet as pq

        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sessions = self.root / "source"
        rows = {
            (1, "train"): [("tr-c", [3, 4]), ("tr-a", [4, 5]), ("tr-b", [5, 6])],
            (2, "valid"): [("va-c", [3, 5]), ("va-a", [4, 6]), ("va-b", [3, 6])],
        }
        self.paths = {}
        for (day, split), members in rows.items():
            path = self.sessions / str(day) / ("valid" if split == "validation" else split) / "part.parquet"
            path.parent.mkdir(parents=True)
            table = pa.Table.from_pylist([{"user_session": sid, "day_index": day,
                                           "product_id-list": items} for sid, items in members])
            pq.write_table(table, path)
            self.paths[(day, split)] = path
        # The canonical loader expects one parquet per <day>/<split>, so move files to that layout.
        for key, path in list(self.paths.items()):
            canonical = path.parent.parent / ("valid.parquet" if key[1] == "validation" else "train.parquet")
            path.replace(canonical)
            canonical.parent.rmdir()
            self.paths[key] = canonical
        self.catalog = ROOT / "evaluation/tests/fixtures/catalog.json"
        self.schema = ROOT / "evaluation/tests/fixtures/schema.pbtxt"
        counts = []
        for (day, split), path in self.paths.items():
            counts.append({"day_index": day, "split": "valid" if split == "validation" else split,
                           "sessions": 3, "distinct_items": len({item for seq in rows[(day, split)] for item in seq}),
                           "item_interactions": sum(len(seq) for seq in rows[(day, split)]),
                           "path": path.relative_to(self.sessions).as_posix(),
                           "sha256": sha256(path)})
        mapping = self.root / "workflow/product_mapping.parquet"
        mapping.parent.mkdir()
        mapping.write_bytes(b"test mapping fingerprint")
        week = self.root / "week.parquet"
        week.write_bytes(b"test workflow sequence fingerprint")
        sequence = mapping.parent / "processed_nvt/part_0.parquet"
        sequence.parent.mkdir()
        sequence.write_bytes(b"test split sequence fingerprint")
        self.workflow_manifest = mapping.parent / "manifest.json"
        self.workflow_manifest.write_text(json.dumps({
            "technical_ids": {"padding": 0, "null": 1, "oov": 2},
            "product_vocabulary_size": 23,
            "input_sha256": sha256(week),
            "checksums": {"catalog.json": sha256(self.catalog),
                          "processed_nvt/schema.pbtxt": sha256(self.schema),
                          "product_mapping.parquet": sha256(mapping)},
        }), encoding="utf-8")
        self.split_manifest = self.root / "split-manifest.json"
        self.split_manifest.write_text(json.dumps({
            "no_overlap_and_complete_coverage": True,
            "catalog_sha256": sha256(self.catalog), "schema_sha256": sha256(self.schema),
            "input_hashes": {"part_0.parquet": sha256(sequence)},
            "counts": counts,
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_cohort_is_deterministic_and_uses_only_requested_partitions(self):
        first = prepare(self.sessions, self.catalog, self.schema, self.split_manifest,
                        self.root / "cohort-a", self.workflow_manifest,
                        train_count=2, eval_count=2, seed=7)
        second = prepare(self.sessions, self.catalog, self.schema, self.split_manifest,
                         self.root / "cohort-b", self.workflow_manifest,
                         train_count=2, eval_count=2, seed=7)
        self.assertEqual(first["train"]["session_ids"], second["train"]["session_ids"])
        self.assertEqual(first["validation"]["session_ids"], second["validation"]["session_ids"])
        self.assertFalse(first["test_partition_used"])
        self.assertEqual(first["audit"]["real_catalog_items"], 23)
        self.assertEqual(set(first["train"]["session_ids"]) & set(first["validation"]["session_ids"]), set())
        self.assertTrue((self.root / "cohort-a/cohort.json").is_file())

    def test_refuses_partition_checksum_mismatch(self):
        manifest = json.loads(self.split_manifest.read_text(encoding="utf-8"))
        manifest["counts"][0]["sha256"] = "0" * 64
        bad_manifest = self.root / "bad.json"
        bad_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Partition checksum mismatch"):
            prepare(self.sessions, self.catalog, self.schema, bad_manifest,
                    self.root / "bad-cohort", self.workflow_manifest,
                    train_count=2, eval_count=2)


if __name__ == "__main__":
    unittest.main()
