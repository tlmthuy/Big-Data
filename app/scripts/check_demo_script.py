"""Check the English demo talk track's length, metric precision, numbers against the JSON, and required Q&A."""

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/DEMO_SCRIPT.md"
OFFICIAL = ROOT / "public/official-results.json"
REQUIRED_QUESTIONS = (
    "How is a session’s prediction evaluated?",
    "Does the demo run live inference, and how can it be rebuilt?",
    "How is the 30-session sample selected?",
    "Why didn't you vary CPU, RAM or workers?",
    "Was E4 a fair comparison?",
    "Are these toy or real recommendations?",
    "Why might the sample be browsing-heavy?",
    "What does the Recommendation tab show?",
)
# Values the walkthrough must quote, rounded exactly as the UI shows them (src/format.js).
DISPLAY_VALUES = (
    "0.1249", "0.0883", "0.3899",
    "66.7, 56.9, 55.8 and 55.6",
)


def significant3(value):
    """Mirror of significant3() in src/format.js (3 significant digits, no exponent)."""
    if value == 0:
        return "0"
    if abs(value) >= 1000:
        return f"{round(value):,}"
    rounded = float(f"{value:.3g}")
    decimals = max(0, 2 - math.floor(math.log10(abs(rounded)))) if abs(rounded) < 1000 else 0
    return f"{rounded:,.{decimals}f}"


def displayed_decimals(official):
    """Every decimal string the UI can show for a numeric value in official-results.json tables."""
    shown = set()
    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            shown.add(f"{value:.4f}")
            shown.add(significant3(value))
            shown.add(f"{value / 1024 ** 2:.1f}")
            shown.add(f"{value / 1024 ** 3:.1f}")
    walk(official.get("tables", {}))
    return shown


def check_numbers(walkthrough, official):
    """Each decimal in the walkthrough must be a displayed JSON value; E3 batch sizes must match the JSON."""
    errors = []
    allowed = displayed_decimals(official)
    for number in re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", walkthrough):
        if number not in allowed:
            errors.append(f"English walkthrough number {number} is not a displayed value from official-results.json")
    return errors


def check_e4_fairness_answer(text, official):
    """The E4 fairness answer must quote the E4 event count from the JSON (both runs read the same count)."""
    answer = re.search(r"(?ms)\*\*Was E4 a fair comparison\?\*\*(.*?)(?=^\s*\*E4 |^\d+\. |\Z)", text)
    counts = {run.get("n_events") for run in official.get("tables", {}).get("E4", [])}
    if not answer:
        return []
    if len(counts) != 1 or None in counts:
        return ["E4 runs do not report one shared event count; the fairness answer cannot be checked"]
    expected = f"{counts.pop():,}"
    numbers = re.findall(r"\d[\d,]*\d", answer.group(1))
    if expected not in numbers or any(number != expected for number in numbers):
        return [f"E4 fairness answer must quote {expected} events from official-results.json"]
    return []


def check_numbers_e3(walkthrough, official):
    errors = []
    batches = sorted(run["train_batch_size"] for run in official.get("tables", {}).get("E3", []))
    if batches and f"from {batches[0]} to {batches[-1]}" not in walkthrough:
        errors.append(f"English walkthrough must state the E3 batch sizes from the JSON ({batches[0]} and {batches[-1]})")
    return errors


def english_walkthrough(text):
    section = text.split("## Three-minute walkthrough", 1)
    if len(section) != 2:
        return ""
    walkthrough = section[1].split("## Likely questions", 1)[0]
    # A value copied from the UI may contain U+00A0 between number and unit; compare it as a space.
    return " ".join(
        line.removeprefix("**English.**").replace("\u00a0", " ").strip()
        for line in walkthrough.splitlines()
        if line.startswith("**English.**")
    )


def check_text(text):
    walkthrough = english_walkthrough(text)
    words = re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", walkthrough, re.UNICODE)
    errors = []
    if not 350 <= len(words) <= 430:
        errors.append(f"English walkthrough must be 350–430 words; found {len(words)}")
    if re.search(r"(?<![\w.])\d+\.\d{5,}(?!\d)", walkthrough):
        errors.append("English walkthrough contains metric values with more than four decimal places")
    missing_values = [value for value in DISPLAY_VALUES if value not in walkthrough]
    if missing_values:
        errors.append(f"English walkthrough is missing displayed values: {', '.join(missing_values)}")
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    errors.extend(check_numbers(walkthrough, official))
    errors.extend(check_numbers_e3(walkthrough, official))
    errors.extend(check_e4_fairness_answer(text, official))

    q4 = re.search(
        r"(?ms)^4\. \*\*What does Recall@20 mean\?\*\*(.*?)(?=^\s*\*Tiếng Việt\.|^5\.)",
        text,
    )
    if not q4 or "docs/modeling/model_protocol.md" not in q4.group(1):
        errors.append("Q4 must cite docs/modeling/model_protocol.md")
    for question in REQUIRED_QUESTIONS:
        if question not in text:
            errors.append(f"Missing required Q&A: {question}")
    return errors, len(words)


def main():
    text = SCRIPT.read_text(encoding="utf-8")
    errors, word_count = check_text(text)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Demo script checks passed: {word_count} English walkthrough words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
