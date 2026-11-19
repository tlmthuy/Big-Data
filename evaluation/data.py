"""Explicit artifact contract; never infer the catalog from train observations."""

import json
from dataclasses import dataclass
from pathlib import Path


def encoded_id(value):
    if type(value) is not int or value < 0:
        raise ValueError(f"Encoded ID must be a non-negative integer: {value!r}")
    return value


@dataclass
class Catalog:
    products: dict
    technical_ids: frozenset
    padding_id: int

    @classmethod
    def load(cls, path):
        with Path(path).open(encoding="utf-8") as handle:
            payload = json.load(handle)
        reserved = payload["technical_ids"]
        if not {"padding", "null", "oov"} <= reserved.keys():
            raise ValueError("Declare runtime padding, null and oov IDs explicitly")
        technical = frozenset(encoded_id(v) for v in reserved.values())
        products = {}
        original_ids = set()
        for row in payload["items"]:
            item = encoded_id(row["encoded_id"])
            original = str(row["product_id"])
            if item in technical or item in products or original in original_ids:
                raise ValueError("Catalog must be one-to-one and exclude technical IDs")
            if row["product_id"] is None or not original.strip():
                raise ValueError("Catalog contains an empty original product ID")
            products[item] = original
            original_ids.add(original)
        if not products:
            raise ValueError("Catalog is empty")
        return cls(products, technical, reserved["padding"])

    def sequence(self, values):
        """Remove right padding only; reject unknown/technical interactions."""
        items = [encoded_id(v) for v in values]
        while items and items[-1] == self.padding_id:
            items.pop()
        if not 2 <= len(items) <= 20:
            raise ValueError("Each sequence needs 2..20 real interactions")
        if any(item not in self.products for item in items):
            raise ValueError("Sequence contains technical IDs or items outside catalog")
        return items


def read_sessions(path):
    """Read canonical JSONL or NVIDIA <day>/{train,valid,test}.parquet layout."""
    path = Path(path)
    if path.is_dir():
        import pyarrow.parquet as pq

        paths = sorted(path.glob("*/*.parquet"))
        if not paths:
            raise ValueError("No <day>/*.parquet files in session directory")
        for source in paths:
            split = {"train": "train", "valid": "validation", "test": "test"}.get(source.stem)
            if split is None or not source.parent.name.isdigit():
                raise ValueError(f"Unexpected partition path: {source}")
            day = int(source.parent.name)
            parquet = pq.ParquetFile(source)
            columns = ["user_session", "product_id-list"]
            if "day_index" in parquet.schema_arrow.names:
                columns.append("day_index")
            for batch in parquet.iter_batches(columns=columns):
                for row in batch.to_pylist():
                    if "day_index" in row and row["day_index"] != day:
                        raise ValueError("Parquet day_index disagrees with partition path")
                    yield {"user_session": row["user_session"], "day_index": day,
                           "split": split, "product_ids": row["product_id-list"]}
        return
    if path.suffix != ".jsonl":
        raise ValueError("Expected JSONL or partition directory; see tv2_runbook.md")
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def audit_sessions(path, catalog):
    """Validate persisted membership and report exact session/distinct-item counts."""
    seen = set()
    groups = {}
    for row in read_sessions(path):
        session = row["user_session"]
        if session is None or str(session).strip() == "" or str(session) in seen:
            raise ValueError("Session ID missing or duplicated across membership")
        seen.add(str(session))
        day = row["day_index"]
        if type(day) is not int or day < 1:
            raise ValueError("day_index must be a positive integer")
        split = row["split"]
        if split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation or test")
        items = catalog.sequence(row["product_ids"])
        group = groups.setdefault((day, split), {"n_sessions": 0, "items": set()})
        group["n_sessions"] += 1
        group["items"].update(items)
    if not seen:
        raise ValueError("Empty session membership")
    days = sorted({day for day, _ in groups})
    return [
        {"day_index": day, "split": split,
         "n_sessions": groups.get((day, split), {}).get("n_sessions", 0),
         "n_items": len(groups.get((day, split), {}).get("items", set()))}
        for day in days for split in ("train", "validation", "test")
    ]
