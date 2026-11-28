import unittest
from pathlib import Path

from check_demo_script import check_text


SCRIPT = Path(__file__).resolve().parents[1] / "docs/DEMO_SCRIPT.md"


class DemoScriptCheckTest(unittest.TestCase):
    def setUp(self):
        self.text = SCRIPT.read_text(encoding="utf-8")

    def test_current_script_has_rounded_metrics_required_q_and_a_and_three_minute_length(self):
        errors, word_count = check_text(self.text)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(word_count, 350)
        self.assertLessEqual(word_count, 430)

    def test_rejects_unrounded_metric_values(self):
        text = self.text.replace("0.1249", "0.124906507", 1)
        errors, _ = check_text(text)
        self.assertTrue(any("more than four decimal places" in error for error in errors))

    def test_requires_model_protocol_citation_in_q4(self):
        text = self.text.replace("docs/modeling/model_protocol.md", "dictionary.inference_protocol")
        errors, _ = check_text(text)
        self.assertTrue(any("Q4 must cite" in error for error in errors))

    def test_requires_recommendation_question(self):
        text = self.text.replace("What does the Recommendation tab show?", "What does the page show?", 1)
        errors, _ = check_text(text)
        self.assertTrue(any("Recommendation tab show" in error for error in errors))


    def test_rejects_a_decimal_that_is_not_a_displayed_json_value(self):
        text = self.text.replace("0.3899", "0.3999", 1)
        errors, _ = check_text(text)
        self.assertTrue(any("0.3999 is not a displayed value" in error for error in errors))

    def test_requires_e3_batch_sizes_from_json(self):
        text = self.text.replace("from 32 to 128", "from 16 to 64", 1)
        errors, _ = check_text(text)
        self.assertTrue(any("E3 batch sizes" in error for error in errors))

    def test_requires_fixed_hardware_question(self):
        text = self.text.replace("Why didn't you vary CPU, RAM or workers?", "Why?", 1)
        errors, _ = check_text(text)
        self.assertTrue(any("vary CPU" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
