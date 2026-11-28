"""Product lookup export: last-row rule, nulls, displayed-ID filter, validation failures and size limit."""

import json
import unittest
from datetime import datetime, timezone

import export_product_info as ex

DAY1 = int(datetime(2019, 10, 1, 12, tzinfo=timezone.utc).timestamp())
EXPECT = dict(expected_rows=4, expected_products=2)


def rows():
    return [
        (1, DAY1, "gopro", "electronics.camera.video", 300.0),
        (2, DAY1, None, None, 10.0),
        (1, DAY1 + 60, "gopro", "electronics.camera.video", 308.86),
        (1, DAY1 + 60, " gopro ", "electronics.camera.video", 310.0),  # tie: the later row wins
    ]


def payload(data=None, wanted=("1", "2"), **expected):
    return ex.build_payload(data if data is not None else rows(), set(wanted), source=ex.DEFAULT_SOURCE,
                            source_sha256="0" * 64, **(expected or EXPECT))


class LastRowTest(unittest.TestCase):
    def test_latest_time_wins_and_ties_keep_the_later_row(self):
        products, summary = ex.latest_by_product(rows())
        self.assertEqual(products["1"], {"brand": "gopro", "category_code": "electronics.camera.video", "price": 310.0})
        self.assertEqual(summary, {"rows": 4, "distinct_products": 2, "min_ts": DAY1, "max_ts": DAY1 + 60})

    def test_earlier_row_does_not_replace_a_later_one(self):
        products, _ = ex.latest_by_product([(1, DAY1 + 60, "a", None, 2.0), (1, DAY1, "b", None, 1.0)])
        self.assertEqual(products["1"]["brand"], "a")

    def test_nulls_and_blanks_become_null(self):
        products, _ = ex.latest_by_product([(7, DAY1, "", None, float("nan")), (8, DAY1, None, "  ", None)])
        self.assertEqual(products["7"], {"brand": None, "category_code": None, "price": None})
        self.assertEqual(products["8"], {"brand": None, "category_code": None, "price": None})

    def test_negative_price_fails(self):
        with self.assertRaises(ValueError):
            ex.latest_by_product([(1, DAY1, "a", None, -1.0)])


class PayloadTest(unittest.TestCase):
    def test_only_displayed_ids_are_exported_without_names(self):
        result = payload(wanted=("2", "99"))
        self.assertEqual(list(result["products"]), ["2"])
        self.assertEqual(result["checks"]["displayed_not_in_week"], ["99"])
        self.assertEqual(result["data_kind"], "real")
        self.assertEqual(result["source"], "official 10% cleaned week file, derived by TV4")
        self.assertIn("price_rule", result)
        self.assertRegex(result["generated_at"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("source_file", result)
        self.assertEqual(result["products"]["2"], {"brand": None, "category_code": None, "price": 10.0})

    def test_displayed_ids_cover_history_target_and_top20(self):
        demo = {"runs": [{"sessions": [{"prefix": ["1", "2"], "target": "3", "top20": ["4", "1"]}]},
                         {"sessions": [{"prefix": ["5"], "target": "6", "recommendations": [{"product_id": "7"}]}]}]}
        self.assertEqual(ex.displayed_ids(demo), {"1", "2", "3", "4", "5", "6", "7"})


class ValidationTest(unittest.TestCase):
    def test_wrong_row_count_fails(self):
        with self.assertRaisesRegex(ex.ValidationError, "expected 5 rows, found 4"):
            payload(expected_rows=5, expected_products=2)

    def test_wrong_product_count_fails(self):
        with self.assertRaisesRegex(ex.ValidationError, "distinct products"):
            payload(expected_rows=4, expected_products=3)

    def test_time_outside_the_week_fails(self):
        before = int(datetime(2019, 9, 30, 23, 59, tzinfo=timezone.utc).timestamp())
        after = int(datetime(2019, 10, 8, tzinfo=timezone.utc).timestamp())
        for stamp in (before, after):
            with self.assertRaisesRegex(ex.ValidationError, "2019-10-01 .. 2019-10-07 UTC"):
                payload(rows() + [(2, stamp, None, None, 1.0)], expected_rows=5, expected_products=2)

    def test_official_defaults(self):
        self.assertEqual((ex.EXPECTED_ROWS, ex.EXPECTED_PRODUCTS), (638_089, 63_398))


class SizeTest(unittest.TestCase):
    def test_output_must_stay_under_300_kb(self):
        small = payload()
        self.assertLess(len(ex.render(small).encode()), 300 * 1024)
        big = dict(small, products={str(i): {"brand": "x" * 40, "category_code": None, "price": 1.0} for i in range(5000)})
        with self.assertRaisesRegex(ex.ValidationError, "under 307,200"):
            ex.render(big)

    def test_shipped_file_is_under_300_kb_and_matches_checks(self):
        from pathlib import Path
        shipped = Path(__file__).resolve().parents[1] / "public/product-info.json"
        self.assertLess(shipped.stat().st_size, 300 * 1024)
        info = json.loads(shipped.read_text(encoding="utf-8"))
        self.assertEqual(info["checks"]["rows"], 638_089)
        self.assertEqual(info["checks"]["distinct_products"], 63_398)
        self.assertEqual(info["checks"]["exported_products"], len(info["products"]))


if __name__ == "__main__":
    unittest.main()
