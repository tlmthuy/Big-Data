import { messages, t } from "./i18n.js";
import { byteDisplayUnit, formatBytes, formatCount, formatMsPerSession, formatNumberOnly, formatRatio, formatSeconds, formatSecondsPerMillionEvents } from "./format.js";
import { modelLabel } from "./data.js";
import { formatTick, niceTicks, textWidth } from "./chart-math.js";

const E2_FIELDS = [
  ["Recall@20", "e1_recall_20", formatRatio],
  ["NDCG@20", "e1_ndcg_20", formatRatio],
  ["n_sessions", "e2_test_sessions", formatCount],
  ["train_seconds_including_sequence_io", "e1_train_time_s", formatSeconds],
  ["final_evaluation_seconds", "e1_final_evaluation_s", formatSeconds],
  ["process_wall_seconds", "e1_process_wall_time_s", formatSeconds],
  ["raw_read_seconds", "e2_raw_read_s", formatSeconds],
  ["preprocessing_seconds", "e2_preprocessing_s", formatSeconds],
];

const E5_FIELDS = [
  ["raw_read", "e2_raw_read_s", formatSeconds],
  ["preprocessing_excluding_raw_read_and_first_seen", "e2_preprocessing_s", formatSeconds],
  ["train_including_sequence_io", "e1_train_time_s", formatSeconds],
  ["final_evaluation_including_io", "e1_final_evaluation_s", formatSeconds],
  ["composed_seconds_excluding_first_seen", "e5_composed_time_s", formatSeconds],
  ["seconds_per_million_events", "e5_seconds_per_million_events", formatSeconds],
  ["bottleneck", "e5_bottleneck", (value) => ({ text: value == null ? t("MISSING") : bottleneckLabel(value), raw: String(value) })],
];

/** Package stage name -> translated label; an unknown stage falls back to its raw text (underscores as spaces). */
export function bottleneckLabel(value) {
  const key = `bottleneck_${value}`;
  return Object.hasOwn(messages.en, key) ? t(key) : String(value).replaceAll("_", " ");
}

function rowCell(row, field, formatter) {
  return formatNumberOnly(formatter, row?.[field]);
}

function appendUnit(label, unit) {
  return `${label} (${unit})`;
}

export function buildScalingView(results) {
  const e2 = [...(results?.tables?.E2 ?? [])].sort((a, b) => a.subset - b.subset);
  const e5 = [...(results?.tables?.E5 ?? [])].sort((a, b) => a.subset - b.subset);
  const e2BySubset = new Map(e2.map((row) => [row.subset, row]));
  const e5BySubset = new Map(e5.map((row) => [row.subset, row]));
  const e2Table = {
    columns: e2.map((run) => ({
      subset: run.subset,
      events: formatCount(run.n_events),
      runId: run.run_id,
      cells: E2_FIELDS.map(([field, , formatter]) => rowCell(run, field, formatter)),
    })),
    rows: E2_FIELDS.map(([field, label]) => ({ field, label: t(label) })),
    firstSeen: e2[0]?.first_seen_shared_seconds,
  };
  const e5Table = {
    columns: e5.map((run) => ({ subset: run.subset, runId: run.run_id })),
    rows: E5_FIELDS.map(([field, label, formatter]) => ({
      field,
      label: t(label),
      cells: e5.map((run) => (field === "bottleneck" ? formatter(run[field]) : rowCell(run, field, formatter))),
    })),
  };
  const charts = [
    {
      id: "composed",
      title: t("e5_composed_seconds_chart"),
      yLabel: t("e5_composed_seconds_axis"),
      series: e5.map((row) => ({
        subset: row.subset,
        x: e2BySubset.get(row.subset)?.n_events ?? null,
        y: row.composed_seconds_excluding_first_seen,
        runId: row.run_id,
      })),
      formatValue: (value) => formatNumberOnly(formatSeconds, value),
    },
    {
      id: "normalized",
      title: t("e5_normalized_seconds_chart"),
      yLabel: t("e5_normalized_seconds_axis"),
      series: e5.map((row) => ({
        subset: row.subset,
        x: e2BySubset.get(row.subset)?.n_events ?? null,
        y: row.seconds_per_million_events,
        runId: row.run_id,
      })),
      formatValue: (value) => formatNumberOnly(formatSecondsPerMillionEvents, value),
    },
  ];
  return { e2Table, e5Table, charts, registrySummary: results?.run_registry_summary ?? null };
}

const E3_FIELDS = [
  ["Recall@20", "e3_recall_20_validation", formatRatio],
  ["NDCG@20", "e3_ndcg_20_validation", formatRatio],
  ["train_seconds_including_sequence_io", "e1_train_time_s", formatSeconds],
  ["process_wall_seconds", "e1_process_wall_time_s", formatSeconds],
  ["final_evaluation_seconds", "e1_final_evaluation_s", formatSeconds],
  ["eval_ms_per_session", "e1_evaluation_time_ms_session", formatMsPerSession],
  ["sampled_rss_bytes_descriptive_only", "e1_sampled_rss_descriptive", formatBytes],
  ["sampled_gpu_process_bytes", "e1_sampled_gpu_process_memory", formatBytes],
];

const E4_FIELDS = [
  ["bytes", "e4_file_size_bytes", formatBytes],
  ["read_seconds", "e4_read_time_s", formatSeconds],
  ["preprocessing_wall_seconds_including_read", "e4_preprocessing_wall_including_read_s", formatSeconds],
  ["sampled_rss_bytes_descriptive_only", "e1_sampled_rss_descriptive", formatBytes],
];

function evalPartition(run, config) {
  return config?.split_counts?.filter((item) => item.split === run?.split).at(-1)?.day_index;
}

export function buildE3E4View(results) {
  const e3 = [...(results?.tables?.E3 ?? [])].sort((a, b) => a.train_batch_size - b.train_batch_size);
  const e4 = results?.tables?.E4 ?? [];
  const firstRun = e3[0];
  const config = firstRun ? results.configs?.[firstRun.run_id] : null;
  const context = firstRun ? {
    model: firstRun.model,
    subset: firstRun.subset,
    split: firstRun.split,
    partition: evalPartition(firstRun, config),
    sessions: firstRun.n_sessions,
    evalBatchSize: config?.actual?.eval_batch_size,
    changeOnly: config?.planned?.resource_config?.change_only,
  } : null;
  const e3ByteUnits = Object.fromEntries(["sampled_rss_bytes_descriptive_only", "sampled_gpu_process_bytes"].map((field) => [
    field, byteDisplayUnit(e3.map((run) => run[field])),
  ]));
  const e4ByteUnits = Object.fromEntries(["bytes", "sampled_rss_bytes_descriptive_only"].map((field) => [
    field, byteDisplayUnit(e4.map((run) => run[field])),
  ]));
  return {
    e3: {
      models: e3.map((run) => ({
        runId: run.run_id,
        batchSize: run.train_batch_size,
        cells: E3_FIELDS.map(([field, label, formatter]) => {
          const unit = e3ByteUnits[field];
          return {
          field,
          label: `${t(label)}${unit ? ` (${unit})` : ""}`,
          ...(field === "sampled_gpu_process_bytes" && run.sampled_gpu_status === "unavailable"
            ? { text: t("not_measured"), raw: String(run[field]) }
            : formatNumberOnly(formatter, run[field], unit)),
          };
        }),
      })),
      rows: E3_FIELDS.map(([field, label]) => ({
        field,
        label: `${t(label)}${e3ByteUnits[field] ? ` (${e3ByteUnits[field]})` : ""}`,
      })),
      context,
    },
    e4: {
      formats: e4.map((run) => ({
        label: run.format,
        runId: run.run_id,
        cells: E4_FIELDS.map(([field, label, formatter]) => ({
          field,
          label: `${t(label)}${e4ByteUnits[field] ? ` (${e4ByteUnits[field]})` : ""}`,
          ...formatNumberOnly(formatter, run[field], e4ByteUnits[field]),
        })),
      })),
      rows: E4_FIELDS.map(([field, label]) => ({
        field,
        label: `${t(label)}${e4ByteUnits[field] ? ` (${e4ByteUnits[field]})` : ""}`,
      })),
      excluded: Object.entries(results?.excluded ?? {}),
    },
  };
}

export function formatE3Context(context) {
  if (!context) return t("MISSING");
  const number = (value) => value == null ? t("MISSING") : formatCount(value).text;
  const changedField = context.changeOnly === "train_batch_size" ? t("experiment_train_batch").toLocaleLowerCase() : t("MISSING");
  return t("e3_context", modelLabel(context.model), number(context.subset), context.split, number(context.partition), number(context.sessions), number(context.evalBatchSize), changedField);
}

export function chartCoordinates(series, width = 600, height = 300, padding = {}) {
  const points = series.filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  if (!points.length) return { points: [], yTicks: [] };
  const { left = 66, right = width - 24, top = 24, bottom = height - 54 } = padding;
  const xs = points.map((point) => point.x), ys = points.map((point) => point.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const axis = niceTicks(Math.max(0, ...ys));
  const coordinates = points.map((point) => ({
    ...point,
    cx: left + (maxX === minX ? 0.5 : (point.x - minX) / (maxX - minX)) * (right - left),
    cy: bottom - (point.y / axis.max) * (bottom - top),
  }));
  const yTicks = axis.ticks.map((value) => ({ value, step: axis.step, cy: bottom - (value / axis.max) * (bottom - top) }));
  return { points: coordinates, yTicks };
}

export { textWidth };

function textBox({ x, y, text, anchor, fontSize }) {
  const width = textWidth(text, fontSize);
  const x0 = anchor === "end" ? x - width : anchor === "middle" ? x - width / 2 : x;
  // Browsers report the full line box (ascent + descent), about 1.25 em tall.
  return { x0, x1: x0 + width, y0: y - fontSize * 1.0, y1: y + fontSize * 0.3 };
}

const GAP = 4;
const overlaps = (a, b) => a.x0 - GAP < b.x1 && b.x0 - GAP < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;

/** True when any segment of the polyline passes through the box (sampled every 2 px). */
function crossesLine(box, points) {
  for (let index = 1; index < points.length; index += 1) {
    const a = points[index - 1], b = points[index];
    const steps = Math.max(1, Math.ceil(Math.hypot(b.cx - a.cx, b.cy - a.cy) / 2));
    for (let step = 0; step <= steps; step += 1) {
      const x = a.cx + (b.cx - a.cx) * step / steps, y = a.cy + (b.cy - a.cy) * step / steps;
      if (x > box.x0 - 2 && x < box.x1 + 2 && y > box.y0 - 2 && y < box.y1 + 2) return true;
    }
  }
  return false;
}

/**
 * Lays out a line chart at its real pixel width. The unit lives in the y-axis title only,
 * so ticks and point labels are numbers. Left padding follows the longest tick label.
 * A label that would collide with one already placed is hidden; its value stays in the
 * table above the chart and in the point tooltip.
 */
export function chartLayout(series, { width = 600, height = 300, fontSize = 13, formatValue, formatX = (value) => formatCount(value).text, yLabel = null } = {}) {
  const valid = series.filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  const axis = niceTicks(Math.max(0, ...valid.map((point) => point.y)));
  const tickValues = axis.ticks;
  const tickText = (value) => formatTick(value, axis.step);
  const longestTick = Math.max(...tickValues.map((value) => textWidth(tickText(value), fontSize)));
  const titleBand = fontSize * 1.6;
  const lastX = valid.length ? formatX(valid.at(-1).x) : "";
  const lastPoint = valid.length ? formatValue(valid.at(-1).y).text : "";
  const padding = {
    left: Math.ceil(titleBand + longestTick + 12),
    right: width - Math.ceil(Math.max(16, textWidth(lastX, fontSize) / 2, textWidth(lastPoint, fontSize) / 2) + 6),
    top: Math.ceil(fontSize * 2),
    bottom: height - Math.ceil(fontSize * 3 + 18),
  };
  const { points, yTicks } = chartCoordinates(valid, width, height, padding);
  // The rotated y-axis title owns a left band, only as tall as the title itself (when its text is known).
  const titleMid = (padding.top + padding.bottom) / 2;
  const titleHalf = yLabel ? textWidth(yLabel, fontSize) / 2 + 2 : height;
  const titleBox = { x0: 0, x1: fontSize + 5, y0: Math.max(0, titleMid - titleHalf), y1: Math.min(height, titleMid + titleHalf) };
  const placed = [titleBox];
  const fits = (label, avoidLine) => {
    const box = textBox({ ...label, fontSize });
    const inside = box.x0 >= 0 && box.x1 <= width && box.y0 >= 0 && box.y1 <= height;
    return inside && !placed.some((other) => overlaps(box, other)) && !(avoidLine && crossesLine(box, points)) ? box : null;
  };
  const place = (label) => {
    const box = fits(label, false);
    if (box) placed.push(box);
    return { ...label, visible: Boolean(box) };
  };
  // Point labels try above, upper-left, upper-right, then below, keeping clear of the line.
  const placePoint = (key, point, text) => {
    const gap = 9;
    const candidates = [
      { x: point.cx, y: point.cy - gap, anchor: "middle" },
      { x: point.cx - gap, y: point.cy - gap / 2, anchor: "end" },
      { x: point.cx + gap, y: point.cy - gap / 2, anchor: "start" },
      { x: point.cx + gap, y: point.cy + fontSize + 2, anchor: "start" },
      { x: point.cx - gap, y: point.cy + fontSize + 2, anchor: "end" },
      { x: point.cx, y: point.cy + fontSize + gap, anchor: "middle" },
    ].map((candidate) => ({ key, text, ...candidate }));
    for (const avoidLine of [true, false]) {
      for (const candidate of candidates) {
        const box = fits(candidate, avoidLine);
        if (box) {
          placed.push(box);
          return { ...candidate, visible: true };
        }
      }
    }
    return { ...candidates[0], visible: false };
  };
  const ticks = yTicks.map(({ value, cy }) => place({ key: `y${value}`, value, cy, x: padding.left - 8, y: cy + fontSize * 0.35, text: tickText(value), anchor: "end" }));
  // 12 px below the axis so the first x label never touches the "0" y tick (16 px presenter labels).
  const xLabelY = padding.bottom + fontSize + 12;
  // First and last x labels win; middle ones show when there is room.
  const order = points.map((_, index) => index).sort((a, b) => (a === 0 || a === points.length - 1 ? -1 : 0) - (b === 0 || b === points.length - 1 ? -1 : 0));
  const xLabels = [];
  for (const index of order) {
    const point = points[index];
    const text = formatX(point.x);
    const half = textWidth(text, fontSize) / 2;
    let x = Math.min(Math.max(point.cx, half + 1), width - half - 1);
    // If the label would touch the y-axis title, slide it right just enough (the first tick stays visible).
    const box = textBox({ x, y: xLabelY, text, anchor: "middle", fontSize });
    if (overlaps(box, titleBox)) x = titleBox.x1 + GAP + half + 1;
    xLabels[index] = place({ key: `x${point.runId ?? index}`, x, y: xLabelY, text, anchor: "middle" });
  }
  const pointLabels = [];
  for (const index of order) {
    const point = points[index];
    pointLabels[index] = placePoint(`p${point.runId ?? index}`, point, formatValue(point.y).text);
  }
  return {
    width, height, fontSize, padding, points, ticks, xLabels, pointLabels,
    xTitle: { x: (padding.left + padding.right) / 2, y: height - 6 },
    yTitle: { x: fontSize + 2, y: (padding.top + padding.bottom) / 2 },
  };
}
