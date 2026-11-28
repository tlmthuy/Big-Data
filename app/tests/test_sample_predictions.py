import csv
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SamplePredictionsTest(unittest.TestCase):
    def test_csv_matches_json_and_catalog(self):
        demo = json.loads((ROOT / "public/demo-data.json").read_text())
        self.assertEqual(demo["provenance"]["product_lookup"], "product-info.json")
        with (ROOT / "public/sample-predictions.csv").open(newline="") as stream:
            reader = csv.DictReader(stream)
            fields = ("run_id", "model", "subset", "split", "data_kind", "catalog_sha256", "user_session",
                      "prefix", "target", "target_rank", "rank", "product_id", "score")
            self.assertEqual(tuple(reader.fieldnames), fields)
            rows = list(reader)
        reserved = {"0", "1", "2", "99", "padding", "null", "oov", "mask"}
        index = 0
        misses = 0
        for run in demo["runs"]:
            catalog = set(run["catalog"])
            self.assertFalse(catalog & reserved)
            for session in run["sessions"]:
                target = session["target"]
                top = session["top20"]
                self.assertTrue(set([*session["prefix"], target, *top]) <= catalog)
                target_rank = top.index(target) + 1 if target in top else None
                self.assertEqual(session["target_rank"], target_rank)
                misses += target_rank is None
                for rank, product in enumerate(top, start=1):
                    values = (run["run_id"], run["model"], str(run["subset"]), run["split"], run["data_kind"], run["catalog_sha256"],
                              session["user_session"], " > ".join(session["prefix"]), target, str(target_rank or ""), str(rank), product, "")
                    self.assertEqual(rows[index], dict(zip(fields, values)))
                    index += 1
        self.assertEqual(len(rows), index)
        self.assertGreater(misses, 0)
