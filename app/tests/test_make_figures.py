import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET

from export_figures import ROOT, figure_runs
from make_figures import MISSING, SPECS, axis_positions, render, weekly_data

COMMIT = "43841c9"
SVG = "{http://www.w3.org/2000/svg}"


def run(run_id, subset, metrics=None):
    return {"run_id": run_id, "planned": {"subset": subset}, "metrics": metrics or {}, "model": "gru"}


def svg_content(path):
    root = ET.parse(path).getroot()
    text = " ".join(node.text or "" for node in root.iter(f"{SVG}text"))
    bars = [ET.tostring(node) for node in root.iter() if node.get("id", "").startswith("metric-bar-")]
    return text, bars


class FigureTest(unittest.TestCase):
    def test_all_specs_render_empty_figures_with_units_and_run_sources(self):
        with TemporaryDirectory() as directory:
            for spec in SPECS:
                with self.subTest(spec=spec.name):
                    path = Path(directory) / f"{spec.name}.svg"
                    render(spec, [run("planned-run", "10")], {"10": 882808}, None, COMMIT, path)
                    text, bars = svg_content(path)
                    for label in (spec.title, spec.x_label, spec.y_label, MISSING,
                                  f"Source: planned-run · team commit {COMMIT} · unconfirmed"):
                        self.assertIn(label, text)
                    self.assertTrue(spec.unit)
                    self.assertFalse(bars)
                    if len(spec.metrics) > 1:
                        for name in spec.metrics:
                            self.assertIn(name, text)

    def test_e2_positions_are_actual_weekly_event_counts(self):
        events, _ = weekly_data({"runs": [{"subset": 10, "n_events": 882808}, {"subset": 25, "n_events": 2213138}]})
        for spec in (spec for spec in SPECS if spec.experiment == "E2"):
            points = axis_positions(spec, [run("e2-25", "25"), run("e2-10", "10")], events, toy=False)
            self.assertEqual([(x, label) for x, label, _ in points], [
                (882808, "10% sessions · 882,808 events"), (2213138, "25% sessions · 2,213,138 events"),
            ])

    def test_first_seen_cost_is_annotation_only_and_missing_value_has_no_bar(self):
        spec = next(spec for spec in SPECS if spec.experiment == "E5")
        records = [run("e2-10", "10", {"seconds_per_million_events": {"value": 9, "unit": spec.unit}}),
                   run("e2-25", "25")]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "e5-scaling.svg"
            render(spec, records, {}, 5, COMMIT, path)
            text, bars = svg_content(path)
            self.assertIn("First-seen lookup: shared monthly cost, counted once, not per subset · 5 s", text)
            self.assertIn("n/a", text)
            self.assertEqual(len(bars), 1)
            render(spec, records, {}, 15, COMMIT, path)
            self.assertEqual(svg_content(path)[1], bars)

    def test_e5_csv_has_source_rows_and_no_empty_csv_rows(self):
        payload = json.loads((ROOT / "public/run-results.json").read_text())
        planned = {record["run_id"] for record in figure_runs(payload, "E5") if record["data_kind"] is None}
        for path in (ROOT / "figures/data").glob("*.csv"):
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(all(row["run_id"] and row["metric"] for row in rows), path.name)
            if path.name == "e5-scaling.csv":
                self.assertEqual({row["run_id"] for row in rows if row["series"] == "planned"}, planned)
                self.assertTrue(all(row["value"] == "" for row in rows if row["series"] == "planned"))
