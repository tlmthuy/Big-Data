"""Render SVG figures from the TV2 package and delivered cuDF weekly manifest."""

import argparse
from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path

from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

from export_figures import ROOT, figure_runs

WEEKLY_MANIFEST = ROOT.parent / "Big-Data/data/manifests/e2_preprocessing_verified.json"
MISSING = "Not available yet — awaiting the TV2 metrics package"
COLORS = ("#27577a", "#9d511f")


@dataclass(frozen=True)
class FigureSpec:
    name: str
    experiment: str
    title: str
    x_label: str
    y_label: str
    metrics: tuple[str, ...]
    unit: str


SPECS = (
    FigureSpec("e1-ranking", "E1", "E1 · Ranking quality by model", "Model (category)", "Ranking quality (ratio)", ("Recall@20", "NDCG@20"), "ratio"),
    FigureSpec("e1-training", "E1", "E1 · Training time by model", "Model (category)", "Training time (s)", ("train_with_input_scan_seconds",), "s"),
    FigureSpec("e2-runtime", "E2", "E2 · Runtime by weekly event count", "Weekly volume (events)", "Collector runtime (s)", ("elapsed_seconds",), "s"),
    FigureSpec("e2-rss", "E2", "E2 · Peak RSS by weekly event count", "Weekly volume (events)", "Peak process-tree RSS (bytes)", ("peak_process_tree_rss_bytes",), "bytes"),
    FigureSpec("e3-training", "E3", "E3 · Training time by batch size", "Training batch (sessions/batch)", "Training time (s)", ("train_with_input_scan_seconds",), "s"),
    FigureSpec("e3-throughput", "E3", "E3 · Evaluation throughput by batch size", "Training batch (sessions/batch)", "Evaluation throughput (sessions/s)", ("inference_sessions_per_second",), "sessions/s"),
    FigureSpec("e3-cuda", "E3", "E3 · Peak CUDA reserved by batch size", "Training batch (sessions/batch)", "Peak CUDA reserved (bytes)", ("peak_cuda_reserved_bytes",), "bytes"),
    FigureSpec("e4-size", "E4", "E4 · File size by format", "Input format (category)", "File size (bytes)", ("bytes",), "bytes"),
    FigureSpec("e4-read", "E4", "E4 · Read time by format", "Input format (category)", "Read time (s)", ("read_seconds",), "s"),
    FigureSpec("e5-scaling", "E5", "E5 · Runtime per million events", "Subset (share of weekly sessions, %)", "Runtime (s per million events)", ("seconds_per_million_events",), "s/million events"),
)

MODEL_NAMES = {"popularity": "Popularity", "gru": "GRU", "xlnet": "XLNet"}


def configuration(run, field):
    actual = run.get("actual", {}).get(field)
    return actual if actual is not None else run.get("planned", {}).get(field)


def metric_value(run, name, unit=None):
    if run.get("status") in {"failed", "excluded"}:
        return None
    entry = run.get("metrics", {}).get(name) or {}
    value = entry.get("value")
    if type(value) not in (float, int) or not isfinite(value):
        return None
    if unit is not None and entry.get("unit") != unit:
        raise ValueError(f"{run['run_id']}: expected {name} in {unit}, found {entry.get('unit')}")
    return value


def weekly_data(manifest):
    runs = manifest["runs"]
    events = {str(run["subset"]): run["n_events"] for run in runs}
    if len(events) != len(runs) or any(type(count) is not int or count <= 0 for count in events.values()):
        raise ValueError("The cuDF manifest must give one positive event count per subset")
    costs = {run["first_seen_seconds"] for run in runs if run.get("first_seen_seconds") is not None}
    if len(costs) > 1:
        raise ValueError("The cuDF manifest disagrees on the shared monthly first-seen cost")
    return events, next(iter(costs), None)


def axis_positions(spec, runs, events, *, toy):
    if spec.experiment == "E2":
        points = []
        for run in runs:
            subset = str(configuration(run, "subset"))
            if toy:
                count = metric_value(run, "n_events")
                if count is None:
                    continue
                label = f"Toy · {count:,} events"
            else:
                if subset not in events:
                    raise ValueError(f"{run['run_id']}: no cuDF weekly event count for subset {subset}")
                count = events[subset]
                label = f"{subset}% sessions · {count:,} events"
            points.append((count, label, run))
        return sorted(points, key=lambda point: point[0])

    if spec.experiment == "E3":
        runs = sorted(runs, key=lambda run: int(configuration(run, "train_batch_size") or 0))
    elif spec.experiment == "E1":
        models = list(MODEL_NAMES)
        runs = sorted(runs, key=lambda run: models.index(str(run.get("model")).lower()) if str(run.get("model")).lower() in models else len(models))
    points = []
    for position, run in enumerate(runs):
        if spec.experiment == "E1":
            label = MODEL_NAMES.get(str(run.get("model")).lower(), run.get("model") or run["run_id"])
        elif spec.experiment == "E3":
            label = str(configuration(run, "train_batch_size") or run["run_id"])
        elif spec.experiment == "E4":
            label = {"csv": "CSV", "parquet": "Parquet"}.get(configuration(run, "input_format"), run["run_id"])
        else:
            subset = configuration(run, "subset")
            label = f"{subset}%" if subset is not None else run["run_id"]
        points.append((position, label, run))
    return points


def render(spec, runs, events, first_seen, team_commit, destination, *, toy=False):
    points = axis_positions(spec, runs, events, toy=toy)
    values = [[metric_value(run, name, spec.unit) for _, _, run in points] for name in spec.metrics]
    measured = any(value is not None for series in values for value in series)
    title = spec.title + ("\nTOY DATA — not a benchmark result" if toy else "")
    kind = "toy" if toy else "real" if measured else "unconfirmed"
    source_ids = ", ".join(dict.fromkeys(run["run_id"] for run in runs)) or "no delivered runs"
    source = f"Source: {source_ids} · team commit {team_commit} · {kind}"

    with rc_context({"svg.fonttype": "none", "svg.hashsalt": destination.stem}):
        figure = Figure(figsize=(10.8, 4.6), facecolor="white")
        axis = figure.subplots()
        figure.subplots_adjust(left=0.14, right=0.98, top=0.82 if toy else 0.88, bottom=0.29)
        axis.set_title(title, loc="left", fontweight="bold", pad=12)
        axis.set_xlabel(spec.x_label)
        axis.set_ylabel(spec.y_label)
        axis.spines[["top", "right"]].set_visible(False)
        x_values = [x for x, _, _ in points]
        labels = [label for _, label, _ in points]
        axis.set_xticks(x_values, labels, rotation=12 if spec.experiment == "E2" else 0)
        if x_values:
            gaps = [right - left for left, right in zip(x_values, x_values[1:]) if right > left]
            spacing = min(gaps, default=max(abs(x_values[0]) * 0.25, 1) if spec.experiment == "E2" else 1)
            axis.set_xlim(min(x_values) - spacing * 0.58, max(x_values) + spacing * 0.58)
        else:
            spacing = 1

        if measured:
            width = spacing * 0.72 / len(spec.metrics)
            for index, series in enumerate(values):
                for x, value in zip(x_values, series):
                    position = x + (index - (len(values) - 1) / 2) * width
                    if value is None:
                        axis.text(position, 0.03, "n/a", transform=axis.get_xaxis_transform(), ha="center", color="#555555")
                    else:
                        bar = axis.bar(position, value, width=width, color=COLORS[index])[0]
                        bar.set_gid(f"metric-bar-{index}-{x}")
            axis.set_ylim(bottom=0)
            axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.6g}" if abs(value) < 1 else f"{value:,.6f}".rstrip("0").rstrip(".")))
            axis.grid(axis="y", alpha=0.25)
            axis.set_axisbelow(True)
        else:
            axis.set_yticks([])
            axis.text(0.5, 0.5, MISSING, transform=axis.transAxes, ha="center", va="center", color="#505862")

        if len(spec.metrics) > 1:
            axis.legend(handles=[Patch(color=COLORS[i], label=name) for i, name in enumerate(spec.metrics)], loc="upper right")
        if spec.experiment == "E5" and not toy:
            cost = f"{first_seen} s" if first_seen is not None else "Not available yet"
            figure.text(0.06, 0.11, f"First-seen lookup: shared monthly cost, counted once, not per subset · {cost}",
                        fontsize=9, color="#505862")
            figure.text(0.06, 0.077, "Preliminary value from the TV1 cuDF weekly manifest.", fontsize=8, color="#505862")
        elif spec.experiment == "E2" and not toy:
            figure.text(0.06, 0.08, "Weekly event counts: TV1 cuDF E2 preprocessing manifest.", fontsize=8, color="#505862")
        figure.text(0.06, 0.035, source, fontsize=8, color="#505862", wrap=True)
        figure.savefig(destination, format="svg", metadata={"Date": None, "Title": title, "Description": source})
    svg = destination.read_text(encoding="utf-8")
    destination.write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "public/run-results.json")
    parser.add_argument("--weekly-manifest", type=Path, default=WEEKLY_MANIFEST)
    parser.add_argument("--output", type=Path, default=ROOT / "figures")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    events, first_seen = weekly_data(json.loads(args.weekly_manifest.read_text(encoding="utf-8")))
    args.output.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        runs = figure_runs(payload, spec.experiment)
        official = [run for run in runs if run["data_kind"] != "toy"]
        toy = [run for run in runs if run["data_kind"] == "toy"]
        for records, is_toy in ((official, False), (toy, True)):
            if is_toy and not records:
                continue
            output = args.output / f"{spec.name}{'-toy' if is_toy else ''}.svg"
            render(spec, records, events, first_seen, payload["team_commit"], output, toy=is_toy)
            print(output.name)


if __name__ == "__main__":
    main()
