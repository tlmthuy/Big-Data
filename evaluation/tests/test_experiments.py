"""Toy config, stage logs, CSV/Parquet and synthetic E5 regression tests."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from benchmark.collect import _gpu_total_memory, _nvidia_smi_values, _process_tree_snapshot, run_command
from benchmark.scalability import summarize, write_outputs
from scripts.runs.run_experiments import resolve

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "evaluation/tests/fixtures"


class ExperimentContracts(unittest.TestCase):
    def test_empty_nvidia_smi_output_is_missing_not_zero_observation(self):
        with mock.patch("benchmark.collect.shutil.which", return_value="/usr/bin/nvidia-smi"), \
                mock.patch("benchmark.collect.subprocess.check_output", return_value="\n"):
            self.assertIsNone(_nvidia_smi_values("--query-gpu=memory.used"))
            self.assertEqual(_gpu_total_memory(), (0, False))

    def test_process_tree_snapshot_sums_live_members_and_pids(self):
        parent = mock.Mock()
        parent.pid = 101
        parent.memory_info.return_value = mock.Mock(rss=100)
        child = mock.Mock()
        child.pid = 202
        child.memory_info.return_value = mock.Mock(rss=50)
        parent.children.return_value = [child]
        with mock.patch("benchmark.collect.psutil.Process", return_value=parent):
            rss, pids = _process_tree_snapshot(101)
        self.assertEqual(rss, 150)
        self.assertEqual(pids, {101, 202})

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

    def test_toy_site_cannot_execute_as_real_data(self):
        from scripts.runs.prepare_toy_site import prepare

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            snapshot = root / "environment.json"
            snapshot.write_text('{"scope":"unit test fixture"}')
            site = json.loads(prepare(root / "toy", snapshot).read_text())
            config = json.loads((ROOT / "configs/experiments.json").read_text())["runs"][0]
            self.assertFalse(site["subsets"]["10"]["accepted_by_tv2"])
            with self.assertRaisesRegex(ValueError, "Toy site requires"):
                resolve(config, site, root / "wrong")
            argv, _ = resolve(config, site, root / "smoke", smoke=True)
            self.assertEqual(argv[argv.index("--subset") + 1], "toy")

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
            self.assertEqual(good["run_id"], "good")
            self.assertEqual(good["cpu_memory_unit"], "bytes")
            self.assertEqual(good["gpu_memory_unit"], "bytes")
            self.assertIn(good["gpu_memory_bytes_status"], ("missing", "observed"))
            self.assertIn(good["gpu_memory_total_used_bytes_status"], ("missing", "observed"))
            if not good["gpu_memory_observation_available"]:
                self.assertEqual(good["gpu_memory_bytes_status"], "missing")
                self.assertIn("unavailable", good["gpu_memory_missing_reason"])
            self.assertEqual(good["elapsed_seconds_unit"], "seconds")
            self.assertEqual(Path(good["output_path"]).name, "good")
            self.assertIn("cache", good["cache_policy"])




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
    def test_toy_smoke_is_excluded_from_official_E5(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "toy-run"
            output.mkdir()
            (output / "run.json").write_text(json.dumps({"status": "passed",
                "metadata": {"run": {"experiment": "E2"}, "data_kind": "toy"}}))
            with self.assertRaisesRegex(ValueError, "No successful E2"):
                summarize(Path(folder))

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
                (out / "metrics.json").write_text(json.dumps({"train_with_input_scan_seconds": 10, "inference_seconds": 1, "inference_timing_protocol": "full_evaluation_wall_v1",
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
            changed["source_sha256"]["models/session_models.py"] = "same-code"
            del changed["inference_timing_protocol"]
            changed_path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, "timing protocol missing/obsolete"):
                summarize(root)


if __name__ == "__main__":
    unittest.main()
