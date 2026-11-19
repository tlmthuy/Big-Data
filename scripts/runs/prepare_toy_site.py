"""Create explicitly synthetic Parquet/site inputs for --smoke E1/E3 only."""

import argparse
import json
from pathlib import Path
import shutil

from evaluation.run_neural import save_json
from evaluation.run_popularity import fingerprint

ROOT = Path(__file__).resolve().parents[2]


def prepare(output, environment):
    import pyarrow as pa
    import pyarrow.parquet as pq

    output, environment = Path(output).resolve(), Path(environment).resolve()
    if not environment.is_file():
        raise ValueError("Supply a real snapshot of the environment running this toy test")
    output.mkdir(parents=True, exist_ok=False)
    fixtures = ROOT / "evaluation/tests/fixtures"
    rows = [json.loads(line) for line in (fixtures / "sessions.jsonl").read_text().splitlines()]
    rows.append({"user_session": "toy-final-test", "day_index": 3,
                 "split": "test", "product_ids": [3, 25]})
    for day in sorted({r["day_index"] for r in rows}):
        directory = output / "sessions" / str(day)
        directory.mkdir(parents=True)
        for split, name in [("train", "train"), ("validation", "valid"), ("test", "test")]:
            selected = [{"user_session": r["user_session"], "day_index": day,
                         "product_id-list": r["product_ids"]} for r in rows
                        if r["day_index"] == day and r["split"] == split]
            if selected:
                pq.write_table(pa.Table.from_pylist(selected), directory / (name + ".parquet"))
    for name in ["catalog.json", "schema.pbtxt"]:
        shutil.copyfile(fixtures / name, output / name)
    shutil.copyfile(environment, output / "environment.json")
    save_json(output / "preprocessing.json", {"data_kind": "toy", "not_TV1_data": True,
              "source": fingerprint(fixtures / "sessions.jsonl"),
              "added": "one synthetic final-day test session", "session_count": len(rows),
              "workflow_fitted": False, "pipeline_telemetry": None})
    site = json.loads((ROOT / "configs/site.example.json").read_text())
    site.update(data_kind="toy", configuration_frozen=True,
                environment_snapshot=str(output / "environment.json"))
    site["subsets"]["10"].update(
        sessions=str(output / "sessions"), schema=str(output / "schema.pbtxt"),
        catalog=str(output / "catalog.json"), preprocessing_manifest=str(output / "preprocessing.json"),
        workflow_version="toy-no-workflow-fit", mapping_version="toy-fixture-v1",
        catalog_version="toy-fixture-v1", accepted_by_tv2=False, final_day=3)
    save_json(output / "site.json", site)
    return output / "site.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.output, args.environment))
