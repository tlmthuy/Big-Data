import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET

from make_figures import DEFAULT_INPUT, FIGURES, build_all, make_figure, render

SVG = "{http://www.w3.org/2000/svg}"


def svg_text(path):
    root = ET.parse(path).getroot()
    return " ".join(node.text or "" for node in root.iter(f"{SVG}text"))


class FigureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DEFAULT_INPUT.read_text(encoding="utf-8"))

    def test_rebuilt_e1_training_bars_match_official_json_values(self):
        official_rows = self.payload["tables"]["E1"]
        figure = make_figure("e1-training", self.payload)
        heights = [patch.get_height() for patch in figure.axes[0].patches]
        expected = [row["train_seconds_including_sequence_io"] for row in official_rows]
        self.assertEqual(heights, expected)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "e1-training.svg"
            render("e1-training", self.payload, path)
            text = svg_text(path)
            for row, number in zip(official_rows, expected):
                self.assertIn(row["run_id"], text)
                self.assertIn(f"{number:.2f}", text)
            self.assertIn("Source: tv2-20261124", text)
            self.assertIn(f"team {self.payload['team_commit']}", text)

    def test_e5_line_charts_start_at_zero(self):
        figure = make_figure("e5-scaling", self.payload)
        self.assertEqual(len(figure.axes), 2)
        self.assertTrue(all(axis.get_ylim()[0] == 0 for axis in figure.axes))

    def test_only_six_confirmed_official_figures_are_generated(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            stale = output / "e1-ranking-toy.svg"
            stale.write_text("toy")
            build_all(self.payload, output)
            self.assertFalse(stale.exists())
            self.assertEqual(sorted(path.name for path in output.glob("*.svg")), sorted(FIGURES))
            for path in output.glob("*.svg"):
                text = svg_text(path)
                self.assertIn("Source: tv2-20261124", text, path.name)
                self.assertIn(f"team {self.payload['team_commit']}", text, path.name)

    def test_generator_rejects_unconfirmed_or_toy_inputs(self):
        payload = {**self.payload, "data_kind": "toy"}
        with self.assertRaises(ValueError):
            make_figure("e1-ranking", payload)


if __name__ == "__main__":
    unittest.main()
