"""Export brand, category and last weekly price for the products the demo displays.

Input: the official 10% cleaned week file (Parquet, columns product_id, brand, category_code, price,
event_time_ts in UTC seconds), or a CSV with event_time instead of event_time_ts. For each product the
last row in the week by event time wins; ties keep file order, so the later row wins (stable).
The dataset has no product-name column, so no name is exported or invented.

Example (Parquet input needs pyarrow):
  python3 scripts/export_product_info.py ../tv4-real-bundle/week-010.parquet \\
    --demo-data public/demo-data.json --output public/product-info.json --data-kind real
"""

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path


PRICE_RULE = "last price seen for the product in the week (latest event_time_ts; ties keep the later row)"
DEFAULT_SOURCE = "official 10% cleaned week file, derived by TV4"
PARQUET_FIELDS = ("product_id", "event_time_ts", "brand", "category_code", "price")
CSV_FIELDS = {"product_id", "event_time", "brand", "category_code", "price"}
# Official 10% cleaned week (week-010.parquet): the export fails unless the file matches these.
EXPECTED_ROWS = 638_089
EXPECTED_PRODUCTS = 63_398
WEEK_START = datetime(2019, 10, 1, tzinfo=timezone.utc)
WEEK_END = datetime(2019, 10, 8, tzinfo=timezone.utc)  # exclusive: 2019-10-01 .. 2019-10-07 UTC
MAX_OUTPUT_BYTES = 300 * 1024


class ValidationError(ValueError):
    """The input does not match the official week file, or the output is too large."""


def clean_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_price(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    price = float(value)
    if math.isnan(price):
        return None
    if not math.isfinite(price) or price < 0:
        raise ValueError(f"price must be finite and nonnegative, got {value!r}")
    return price


def latest_by_product(rows):
    """rows: iterable of (product_id, timestamp_seconds, brand, category_code, price) in file order.

    Returns ({product_id: metadata}, summary). The row with the largest timestamp wins; on a tie the
    later row wins. The summary has the row count, distinct products and min/max timestamp.
    """
    latest = {}
    count = 0
    low = high = None
    for product_id, timestamp, brand, category_code, price in rows:
        count += 1
        if product_id is None or timestamp is None:
            raise ValueError(f"row {count}: product_id and event time are required")
        key = str(product_id).strip()
        low = timestamp if low is None else min(low, timestamp)
        high = timestamp if high is None else max(high, timestamp)
        previous = latest.get(key)
        if previous is None or timestamp >= previous[0]:
            latest[key] = (timestamp, {"brand": clean_text(brand), "category_code": clean_text(category_code), "price": clean_price(price)})
    summary = {"rows": count, "distinct_products": len(latest), "min_ts": low, "max_ts": high}
    return {key: value[1] for key, value in latest.items()}, summary


def utc(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def validate(summary, expected_rows=EXPECTED_ROWS, expected_products=EXPECTED_PRODUCTS, start=WEEK_START, end=WEEK_END):
    """Raise ValidationError unless the counts and the time window match the official week file."""
    window = f"{start.date()} .. {(end - timedelta(days=1)).date()} UTC"
    problems = []
    if summary["rows"] != expected_rows:
        problems.append(f"expected {expected_rows:,} rows, found {summary['rows']:,}")
    if summary["distinct_products"] != expected_products:
        problems.append(f"expected {expected_products:,} distinct products, found {summary['distinct_products']:,}")
    if summary["min_ts"] is None or summary["min_ts"] < start.timestamp() or summary["max_ts"] >= end.timestamp():
        span = "no rows" if summary["min_ts"] is None else f"{utc(summary['min_ts'])} .. {utc(summary['max_ts'])}"
        problems.append(f"event times must be inside {window}, found {span}")
    if problems:
        raise ValidationError("input is not the official week file: " + "; ".join(problems))
    return {
        "rows": summary["rows"],
        "distinct_products": summary["distinct_products"],
        "min_event_time_utc": utc(summary["min_ts"]),
        "max_event_time_utc": utc(summary["max_ts"]),
        "window_utc": window,
    }


def displayed_ids(demo):
    """Every product ID the Recommendations tab can show: history, target and Top-20 of all runs."""
    ids = set()
    for run in demo.get("runs", []):
        for session in run.get("sessions", []):
            ids.update(str(item) for item in session.get("prefix") or [])
            if session.get("target") is not None:
                ids.add(str(session["target"]))
            ids.update(str(item) for item in session.get("top20") or [])
            ids.update(str(item["product_id"]) for item in session.get("recommendations") or [])
    return ids


def parquet_rows(path):
    import pyarrow.parquet as pq  # only needed for Parquet input

    table = pq.read_table(path, columns=list(PARQUET_FIELDS))
    return zip(*(table.column(name).to_pylist() for name in PARQUET_FIELDS))


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = CSV_FIELDS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            stamp = datetime.fromisoformat(row["event_time"].strip().removesuffix(" UTC"))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            yield row["product_id"].strip() or None, stamp.timestamp(), row["brand"], row["category_code"], row["price"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_payload(rows, wanted, *, source, source_sha256, data_kind="real", source_file=None, generated_at=None, **expected):
    """Validate the whole week, then keep only the displayed IDs (sorted numerically when possible)."""
    products, summary = latest_by_product(rows)
    checks = validate(summary, **expected)
    exported = {key: products[key] for key in sorted(wanted, key=lambda value: (len(value), value)) if key in products}
    checks.update(displayed_products=len(wanted), exported_products=len(exported),
                  displayed_not_in_week=sorted(set(wanted) - set(exported)))
    return {
        "data_kind": data_kind,
        "source": source,
        "source_sha256": source_sha256,
        "source_file": source_file,
        "generated_at": generated_at or date.today().isoformat(),
        "checks": checks,
        "price_rule": PRICE_RULE,
        "products": exported,
    }


def render(payload):
    """JSON text for public/; fails if it would reach the 300 KB limit for public JSON files."""
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    size = len(text.encode("utf-8"))
    if size >= MAX_OUTPUT_BYTES:
        raise ValidationError(f"output is {size:,} bytes; public JSON must stay under {MAX_OUTPUT_BYTES:,}")
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="week Parquet (or CSV with event_time)")
    parser.add_argument("--demo-data", type=Path, required=True, help="public/demo-data.json: only displayed IDs are exported")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="provenance text")
    parser.add_argument("--data-kind", choices=("real", "toy"), required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must use different paths")
    try:
        rows = parquet_rows(args.input) if args.input.suffix.lower() == ".parquet" else csv_rows(args.input)
        wanted = displayed_ids(json.loads(args.demo_data.read_text(encoding="utf-8")))
        payload = build_payload(rows, wanted, source=args.source, source_sha256=sha256(args.input), data_kind=args.data_kind,
                                source_file=args.input.name)
        text = render(payload)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Export failed: {error}\n")
    args.output.write_text(text, encoding="utf-8")
    checks = payload["checks"]
    print(f"{checks['rows']:,} rows, {checks['distinct_products']:,} products, {checks['min_event_time_utc']} .. {checks['max_event_time_utc']}")
    print(f"Exported {checks['exported_products']} of {checks['displayed_products']} displayed products to {args.output} ({len(text.encode()):,} bytes)")


if __name__ == "__main__":
    main()
