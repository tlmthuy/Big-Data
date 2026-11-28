"""Build official E1–E5 figures from public/official-results.json."""

import argparse
import json
from math import isfinite
from pathlib import Path

from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "public/official-results.json"
DEFAULT_OUTPUT = ROOT / "figures"
MIB = 1024 ** 2
COLORS = ("#27577a", "#a75b25")
MODEL_LABELS = {"popularity": "Popularity", "gru": "GRU", "xlnet": "XLNet"}
FIGURES = (
    "e1-ranking.svg", "e1-training.svg", "e2-training.svg",
    "e3-tradeoff.svg", "e4-format.svg", "e5-scaling.svg",
)


def rows(payload, table):
    result = payload.get("tables", {}).get(table)
    if not isinstance(result, list) or not result:
        raise ValueError(f"official-results.json has no {table} rows")
    return result


def value(row, field):
    number = row.get(field)
    if number is None:
        return None
    if type(number) not in (int, float) or not isfinite(number):
        raise ValueError(f"{row.get('run_id')}: {field} is not a finite number")
    return number


def require_real_package(payload):
    if payload.get("schema") != "tv4-official-results/v1" or payload.get("package_id") != "tv2-20261124":
        raise ValueError("Expected the official tv2-20261124 results package")
    if payload.get("confirmed_by_tv2") is not True or payload.get("data_kind") != "real":
        raise ValueError("Refusing to build figures from unconfirmed or non-real data")
    if not payload.get("team_commit"):
        raise ValueError("official-results.json has no team_commit")


def source_footer(payload, source_rows):
    run_ids = ", ".join(row["run_id"] for row in source_rows)
    return f"Source: {payload['package_id']} · {run_ids} · team {payload['team_commit']}"


def label_points(axis, bars, formatter):
    for bar in bars:
        height = bar.get_height()
        axis.annotate(formatter(height), (bar.get_x() + bar.get_width() / 2, height),
                      xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8)


def bars(axis, labels, values, ylabel, formatter, color=COLORS[0]):
    positions = list(range(len(labels)))
    valid = [(position, number) for position, number in zip(positions, values) if number is not None]
    axis.set_xticks(positions, labels)
    axis.set_ylabel(ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=0.22)
    axis.set_axisbelow(True)
    axis.set_ylim(bottom=0)
    drawn = axis.bar([position for position, _ in valid], [number for _, number in valid], color=color, width=0.62)
    label_points(axis, drawn, formatter)
    if valid:
        axis.set_ylim(0, max(number for _, number in valid) * 1.18)
    for position, number in zip(positions, values):
        if number is None:
            axis.text(position, 0.04, "Not available yet", transform=axis.get_xaxis_transform(), ha="center", fontsize=8)
    return drawn


def line_values(axis, x_values, y_values, ylabel, formatter, color=COLORS[0]):
    axis.plot(x_values, y_values, color=color, marker="o", linewidth=2)
    shown = [y for y in y_values if y is not None]
    # Headroom so the top point label clears the subplot title.
    axis.set_ylim(bottom=0, top=max(shown) * 1.15 if shown else None)
    axis.set_xlabel("Events (n_events)")
    axis.set_ylabel(ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=0.22)
    for x, y in zip(x_values, y_values):
        if y is not None:
            axis.annotate(formatter(y), (x, y), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8)
    axis.xaxis.set_major_formatter(FuncFormatter(lambda number, _: f"{number:,.0f}"))


def make_figure(name, payload):
    require_real_package(payload)
    if name == "e1-ranking":
        data = rows(payload, "E1")
        figure = Figure(figsize=(8.6, 4.9), facecolor="white")
        axis = figure.subplots()
        positions = list(range(len(data)))
        width = 0.34
        series = (("Recall@20", COLORS[0], -width / 2), ("NDCG@20", COLORS[1], width / 2))
        for metric, color, offset in series:
            measurements = [value(row, metric) for row in data]
            valid = [(x + offset, y) for x, y in zip(positions, measurements) if y is not None]
            drawn = axis.bar([x for x, _ in valid], [y for _, y in valid], width=width, color=color, label=metric)
            label_points(axis, drawn, lambda number: f"{number:.4f}")
        axis.set_xticks(positions, [MODEL_LABELS.get(str(row["model"]).lower(), row["model"]) for row in data])
        axis.set_ylabel("Ranking score (ratio)")
        axis.set_title("E1 · Recall@20 and NDCG@20 by model", loc="left", fontweight="bold")
        axis.legend(frameon=False)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.22)
        axis.set_axisbelow(True)
        axis.set_ylim(0, max(value(row, metric) for row in data for metric, _, _ in series) * 1.18)
        source_rows = data
    elif name == "e1-training":
        data = rows(payload, "E1")
        figure = Figure(figsize=(8.6, 4.9), facecolor="white")
        axis = figure.subplots()
        bars(axis, [row["model"] for row in data], [value(row, "train_seconds_including_sequence_io") for row in data],
             "Train time (s)", lambda number: f"{number:.2f}")
        axis.set_title("E1 · Training time by model", loc="left", fontweight="bold")
        source_rows = data
    elif name == "e2-training":
        data = rows(payload, "E2")
        events = [value(row, "n_events") for row in data]
        training = [value(row, "train_seconds_including_sequence_io") for row in data]
        figure = Figure(figsize=(9.2, 5.0), facecolor="white")
        axis = figure.subplots()
        line_values(axis, events, training, "Train time (s)", lambda number: f"{number:.1f}")
        axis.set_title("E2 · Train time by weekly event volume", loc="left", fontweight="bold")
        source_rows = data
    elif name == "e3-tradeoff":
        data = rows(payload, "E3")
        labels = [str(row["train_batch_size"]) for row in data]
        figure = Figure(figsize=(9.4, 4.9), facecolor="white")
        left, right = figure.subplots(1, 2)
        bars(left, labels, [value(row, "Recall@20") for row in data], "Recall@20 (ratio)", lambda number: f"{number:.4f}")
        bars(right, labels, [value(row, "process_wall_seconds") for row in data], "Process wall time (s)", lambda number: f"{number:.2f}", COLORS[1])
        left.set_title("Validation Recall@20", fontsize=10)
        right.set_title("Process wall time", fontsize=10)
        figure.suptitle("E3 · Validation accuracy and process wall time by training batch", x=0.04, ha="left", fontweight="bold")
        figure.text(0.04, 0.07, payload["dictionary"]["E3_accuracy"], fontsize=8, color="#505862")
        source_rows = data
    elif name == "e4-format":
        data = rows(payload, "E4")
        labels = [row["format"].upper() for row in data]
        figure = Figure(figsize=(9.4, 4.9), facecolor="white")
        left, right = figure.subplots(1, 2)
        sizes_mib = [value(row, "bytes") / MIB if value(row, "bytes") is not None else None for row in data]
        bars(left, labels, sizes_mib, "File size (MiB)", lambda number: f"{number:.1f}")
        bars(right, labels, [value(row, "read_seconds") for row in data], "Read time (s)", lambda number: f"{number:.3f}", COLORS[1])
        left.set_title("File size", fontsize=10)
        right.set_title("Read time", fontsize=10)
        figure.suptitle("E4 · File size and read time by format", x=0.04, ha="left", fontweight="bold")
        source_rows = data
    elif name == "e5-scaling":
        data = rows(payload, "E5")
        events = [value(row, "n_events") for row in data]
        figure = Figure(figsize=(9.4, 5.2), facecolor="white")
        left, right = figure.subplots(1, 2)
        line_values(left, events, [value(row, "composed_seconds_excluding_first_seen") for row in data],
                    "Composed time (s)", lambda number: f"{number:.1f}")
        line_values(right, events, [value(row, "seconds_per_million_events") for row in data],
                    "Seconds per million events", lambda number: f"{number:.1f}", COLORS[1])
        left.set_title("Composed time", fontsize=10)
        right.set_title("Seconds per million events", fontsize=10)
        figure.suptitle("E5 · Composed time and normalized time by event volume", x=0.04, ha="left", fontweight="bold")
        figure.text(0.04, 0.07, payload["dictionary"]["E5_composed"], fontsize=8, color="#505862")
        source_rows = data
    else:
        raise ValueError(f"Unknown official figure: {name}")

    figure.text(0.04, 0.025, source_footer(payload, source_rows), fontsize=7.5, color="#505862")
    figure.tight_layout(rect=(0.04, 0.11, 0.98, 0.91))
    return figure


def render(name, payload, destination):
    figure = make_figure(name, payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    title = next((text.get_text() for axis in figure.axes for text in axis.texts if text.get_text().startswith("E")), name)
    with rc_context({"svg.fonttype": "none", "svg.hashsalt": name}):
        figure.savefig(destination, format="svg", metadata={"Date": None, "Title": title, "Description": source_footer(payload, rows(payload, name[:2].upper()))})
    svg = destination.read_text(encoding="utf-8")
    destination.write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n", encoding="utf-8")


def build_all(payload, output):
    require_real_package(payload)
    output.mkdir(parents=True, exist_ok=True)
    for path in output.glob("*.svg"):
        path.unlink()
    for filename in FIGURES:
        name = filename.removesuffix(".svg")
        path = output / filename
        render(name, payload, path)
        print(path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    build_all(payload, args.output)


if __name__ == "__main__":
    main()
