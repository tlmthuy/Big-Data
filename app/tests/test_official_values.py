"""Every official value shown by the UI still matches the team package (metrics.json -> tables).

Reads <BIG_DATA_ROOT>/metrics/releases/tv2-20261124/metrics.json (the source of truth; BIG_DATA_ROOT
defaults to ../Big-Data). Skips if the team repo cannot be found. Also checks every public/*.json stays < 300 KB.
"""
import json
import math
import unittest
from pathlib import Path

from team_root import BIG_DATA_ROOT, ROOT

PACKAGE = BIG_DATA_ROOT / "metrics" / "releases" / "tv2-20261124" / "metrics.json"


def leaves(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, path + (index,))
    else:
        yield path, value


def same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and math.isclose(a, b, rel_tol=0, abs_tol=0)
    return a == b


class OfficialValuesTest(unittest.TestCase):
    @unittest.skipUnless(PACKAGE.exists(), f"team repo not found at {BIG_DATA_ROOT}; set BIG_DATA_ROOT")
    def test_all_table_values_match_metrics_json(self):
        package = json.loads(PACKAGE.read_text(encoding="utf8"))["tables"]
        public = json.loads((ROOT / "public" / "official-results.json").read_text(encoding="utf8"))["tables"]
        expected = list(leaves(package))
        shown = dict(leaves(public))
        mismatched = [path for path, value in expected if not same(shown.get(path, object()), value)]
        self.assertEqual(mismatched, [])
        self.assertEqual(len(expected), 262, "number of official leaf values in tables E1-E5")
        print(f"\nofficial values matched: {len(expected) - len(mismatched)}/{len(expected)}")

    def test_public_json_files_are_small(self):
        for path in sorted((ROOT / "public").glob("*.json")):
            self.assertLess(path.stat().st_size, 300_000, path.name)


if __name__ == "__main__":
    unittest.main()
