"""Export TV1's weekly CSV as an optional UI lookup keyed by original product ID."""

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path


PRICE_RULE = "last observed price in the subset week"
FIELDS = {"product_id", "event_time", "brand", "category_code", "price"}


def metadata(row):
    raw_price = row["price"].strip()
    price = float(raw_price) if raw_price else None
    if price is not None and (not math.isfinite(price) or price < 0):
        raise ValueError("price must be finite and nonnegative")
    return {
        "brand": row["brand"].strip() or None,
        "category_code": row["category_code"].strip() or None,
        "price": price,
    }


def export_products(input_path):
    latest = {}
    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = FIELDS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            try:
                product_id = row["product_id"].strip()
                if not product_id:
                    continue
                timestamp = datetime.fromisoformat(row["event_time"].strip().removesuffix(" UTC"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                previous = latest.get(product_id)
                if previous is None or timestamp >= previous[0]:
                    latest[product_id] = (timestamp, metadata(row))
            except (AttributeError, ValueError) as error:
                raise ValueError(f"{input_path}:{reader.line_num}: {error}") from error
    return {product_id: latest[product_id][1] for product_id in sorted(latest)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True, help="TV1 artifact provenance")
    parser.add_argument("--data-kind", choices=("real", "toy"), required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must use different paths")
    payload = {
        "data_kind": args.data_kind,
        "source": args.source,
        "price_rule": PRICE_RULE,
        "products": export_products(args.input),
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
