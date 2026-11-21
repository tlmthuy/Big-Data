"""Export one CSV per experiment chart using the same metric definitions as the UI."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def figure_runs(payload, experiment):
    runs = [run for run in payload["runs"] if run["experiment"] == experiment]
    if experiment != "E5":
        return runs
    official_ids = {run["run_id"] for run in runs if run["data_kind"] != "toy"}
    return runs + [
        {**run, "status": None, "data_kind": None, "metrics": {}}
        for run in payload["runs"]
        if run["experiment"] == "E2" and run["data_kind"] != "toy" and run["run_id"] not in official_ids
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "public/run-results.json")
    parser.add_argument("--output", type=Path, default=ROOT / "figures/data")
    args = parser.parse_args()
    specs = json.loads(Path(__file__).with_name("figure_specs.json").read_text(encoding="utf-8"))
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    for experiment, charts in specs.items():
        runs = figure_runs(payload, experiment)
        for chart, _, metrics in charts:
            path = args.output / f"{experiment.lower()}-{chart}.csv"
            with path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(("team_commit", "generated_at", "run_id", "series", "status", "metric", "value", "unit", "scope"))
                for run in runs:
                    for metric in metrics:
                        entry = {} if run["status"] in {"failed", "excluded"} else run.get("metrics", {}).get(metric) or {}
                        value = entry.get("value")
                        writer.writerow((
                            payload["team_commit"], payload.get("generated_at"), run["run_id"],
                            "toy" if run["data_kind"] == "toy" else "official" if run["data_kind"] == "real" else "planned", run["status"],
                            metric, value if type(value) in {float, int} else None, entry.get("unit") or ("s/million events" if experiment == "E5" else None), entry.get("scope"),
                        ))


if __name__ == "__main__":
    main()
