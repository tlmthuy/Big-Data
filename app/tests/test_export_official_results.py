"""Run with PYTHONPATH=../Big-Data:scripts python3 -m unittest discover -s tests (team repo: BIG_DATA_ROOT, default ../Big-Data)."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from export_official_results import VM_ENVIRONMENT_VALUES, e4_configs, read_stage_shares, read_vm_environment


from team_root import BIG_DATA_ROOT, ROOT

TEAM_ROOT = BIG_DATA_ROOT
PACKAGE = TEAM_ROOT / "metrics/releases/tv2-20261124"
SCRIPT = ROOT / "scripts/export_official_results.py"


@unittest.skipUnless(PACKAGE.exists(), f"team repo not found at {BIG_DATA_ROOT}; set BIG_DATA_ROOT")
class OfficialResultsExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)

    def run_export(self, package, output):
        return subprocess.run(
            ["python3", str(SCRIPT), "--package", str(package), "--output", str(output)],
            cwd=ROOT, text=True, capture_output=True,
        )

    def test_export_copies_official_values_and_records_exception(self):
        output = self.workspace / "official.json"
        result = self.run_export(PACKAGE, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(output.read_text())
        self.assertEqual(data["tables"]["E1"][2]["Recall@20"], 0.12490650710545999)
        e4 = next(row for row in data["tables"]["E4"] if row["run_id"] == "e4-full-010-csv")
        self.assertEqual(e4["bytes"], 134004153)
        self.assertEqual(len(data["tables"]["E5"]), 4)
        self.assertIs(data["E5_aggregation_only"], True)
        self.assertEqual(data["run_registry_summary"], {
            "passed": 11,
            "derived_from_verified_E2": 4,
            "excluded": 2,
        })
        popularity = next(row for row in data["tables"]["E1"] if row["run_id"] == "e1-popularity-010")
        self.assertIsNone(popularity["sampled_gpu_process_bytes"])
        self.assertEqual(popularity["sampled_gpu_status"], "unavailable")
        self.assertEqual(data["team_commit"], subprocess.check_output(
            ["git", "-C", str(TEAM_ROOT), "rev-parse", "--short", "HEAD"], text=True,
        ).strip())
        self.assertEqual(data["known_checksum_exceptions"], [{
            "file": "environment/README.md",
            "reason": "TV3 doc edit after packaging (team commit 88f7e02), log links only",
        }])

    def test_stage_shares_equal_the_csv_and_are_checked_against_e5(self):
        csv_path = TEAM_ROOT / "reports/tables/tv2-20261124/stage_shares.csv"
        e5 = json.loads((PACKAGE / "metrics.json").read_text())["tables"]["E5"]
        exported = read_stage_shares(PACKAGE, e5)
        self.assertEqual(exported["source"], "reports/tables/tv2-20261124/stage_shares.csv")
        import csv
        with csv_path.open(encoding="utf-8", newline="") as handle:
            records = list(csv.DictReader(handle))
        self.assertEqual(len(exported["rows"]), len(records))
        for row, record in zip(exported["rows"], records):
            self.assertEqual(row["subset"], int(record["subset"]))
            self.assertEqual(row["raw_read"], float(record["raw_read_share_pct"]))
            self.assertEqual(row["preprocessing"], float(record["preprocessing_share_pct"]))
            self.assertEqual(row["train"], float(record["train_share_pct"]))
            self.assertEqual(row["final_eval"], float(record["final_eval_share_pct"]))
        public = json.loads((ROOT / "public/official-results.json").read_text())
        self.assertEqual(public["stage_shares"], exported)
        broken = [dict(row) for row in e5]
        broken[0]["train_including_sequence_io"] += 1
        with self.assertRaises(ValueError):
            read_stage_shares(PACKAGE, broken)

    def test_e4_config_block_and_fingerprint_comparison(self):
        configs = json.loads((PACKAGE / "configs.json").read_text())
        e4_ids = [row["run_id"] for row in json.loads((PACKAGE / "metrics.json").read_text())["tables"]["E4"]]
        exported = e4_configs(configs, e4_ids, "metrics/releases/tv2-20261124/configs.json")
        self.assertEqual(set(exported), set(e4_ids))
        for run_id, block in exported.items():
            source = configs[run_id]
            self.assertEqual(block["input_format"], source["preprocessing_argv"][source["preprocessing_argv"].index("--input-format") + 1])
            self.assertEqual(block["subset"], int(source["preprocessing_argv"][source["preprocessing_argv"].index("--subset") + 1]))
            self.assertEqual(block["n_events"], source["verification"]["n_events"])
            self.assertEqual(block["schema_policy"], source["schema_policy"])
            self.assertEqual(block["events_after_repeat_removal"], source["timings"]["events_after_repeat_removal"])
            self.assertEqual(block["notebook_commit"], source["workflow_manifest"]["notebook_commit"])
            self.assertEqual(block["split_seed"], source["split_manifest"]["seed"])
            self.assertTrue(block["fingerprint_match"])
            for forbidden in ("read_seconds", "prepare_seconds", "workflow_seconds", "split_seconds", "sum_sha256_mod_2_256"):
                self.assertNotIn(forbidden, block, "stage timings and raw fingerprints are not exported")
        public = json.loads((ROOT / "public/official-results.json").read_text())
        for run_id in e4_ids:
            self.assertEqual(public["configs"][run_id]["e4_config"], exported[run_id])
        changed = json.loads(json.dumps(configs))
        changed[e4_ids[1]]["verification"]["sum_squared_sha256_mod_2_256"] = "0"
        self.assertTrue(all(not block["fingerprint_match"] for block in e4_configs(changed, e4_ids, "x").values()))
        missing = json.loads(json.dumps(configs))
        del missing[e4_ids[0]]["verification"]["sum_sha256_mod_2_256"]
        self.assertTrue(all(not block["fingerprint_match"] for block in e4_configs(missing, e4_ids, "x").values()))

    def test_changed_package_byte_fails_checksum(self):
        copied_root = self.workspace / "Big-Data"
        package_copy = copied_root / "metrics/releases/tv2-20261124"
        package_copy.mkdir(parents=True)
        shutil.copy2(PACKAGE / "manifest.json", package_copy / "manifest.json")
        for group in json.loads((PACKAGE / "manifest.json").read_text())["files_sha256"].values():
            for relative in group:
                source = TEAM_ROOT / relative
                destination = copied_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        target = package_copy / "E1.csv"
        target.write_bytes(target.read_bytes() + b"x")
        output = self.workspace / "bad.json"
        result = self.run_export(package_copy, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Checksum mismatch in package group", result.stderr)

    def test_vm_environment_values_are_verbatim_readme_substrings(self):
        environment = read_vm_environment(TEAM_ROOT)
        readme = (TEAM_ROOT / "environment/README.md").read_text(encoding="utf-8")
        for field, value in VM_ENVIRONMENT_VALUES.items():
            self.assertEqual(environment[field], value)
        for field in ("gpu", "vram", "cpu", "vcpu"):
            with self.subTest(field=field):
                self.assertIn(environment[field], readme)
        self.assertEqual(environment["source"], "environment/README.md (team 88f7e02)")
        self.assertEqual(environment["checksum_note"], "file edited by TV3 after packaging; links only, values unchanged")

    def test_vm_environment_export_fails_if_required_substring_is_missing(self):
        root = self.workspace / "team"
        readme = root / "environment/README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text("VM AWS Ubuntu 22.04\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Required vm_environment.gpu substring not found"):
            read_vm_environment(root)


if __name__ == "__main__":
    unittest.main()
