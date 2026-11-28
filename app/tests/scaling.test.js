import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { setLanguage } from "../src/i18n.js";
import { buildE3E4View, buildScalingView, chartCoordinates, chartLayout, formatE3Context, textWidth } from "../src/scaling.js";

const official = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8"));

test("E5 charts use all E2 event counts and exclude shared first-seen", () => {
  setLanguage("en");
  const view = buildScalingView(official);
  const e2Events = official.tables.E2.map((row) => row.n_events);
  assert.equal(view.charts.length, 2);
  for (const chart of view.charts) {
    assert.equal(chart.series.length, 4);
    assert.deepEqual(chart.series.map((point) => point.x), e2Events);
    const coordinates = chartCoordinates(chart.series);
    assert.equal(coordinates.points.length, 4);
    assert.ok(coordinates.yTicks.length >= 3 && coordinates.yTicks.length <= 6);
    assert.equal(coordinates.yTicks[0].value, 0, "axis starts at zero");
    assert.ok(coordinates.yTicks.at(-1).value >= Math.max(...chart.series.map((p) => p.y)), "axis covers the largest value");
  }
  const composed = view.charts.find((chart) => chart.id === "composed");
  assert.deepEqual(composed.series.map((point) => point.y), official.tables.E5.map((row) => row.composed_seconds_excluding_first_seen));
  assert.ok(composed.series.every((point, index) => point.y !== official.tables.E5[index].composed_seconds_with_first_seen));
  assert.equal(view.e2Table.firstSeen, official.tables.E2[0].first_seen_shared_seconds);
  assert.deepEqual(view.registrySummary, { passed: 11, derived_from_verified_E2: 4, excluded: 2 });
});

test("chart coordinates use a zero baseline and round ticks", () => {
  const chart = chartCoordinates([{ x: 1, y: 0 }, { x: 2, y: 10 }]);
  assert.equal(chart.points[0].cy, 246);
  assert.equal(chart.points[1].cy, 24);
  assert.deepEqual(chart.yTicks.map(({ value }) => value), [0, 2.5, 5, 7.5, 10]);
});

test("E3 and E4 panels preserve official configs, measurements, notes, and exclusions", () => {
  setLanguage("en");
  const { e3, e4 } = buildE3E4View(official);
  const scaling = buildScalingView(official);
  assert.deepEqual(e3.models.map((run) => run.batchSize), [32, 128]);
  assert.equal(formatE3Context(e3.context), "GRU · 10% subset · validation partition 7 · 1,324 sessions · eval batch 32 · only train batch changes");
  assert.equal(Object.hasOwn(e3, "note"), false);
  assert.equal(Object.hasOwn(e3, "accuracyNote"), false);
  assert.equal(e3.rows.length, 8);
  assert.deepEqual(e4.formats.map((format) => format.label), ["csv", "parquet"]);
  assert.equal(e4.formats[0].cells[0].text, "127.8");
  assert.equal(e4.rows[0].label, "File size (MiB)");
  assert.equal(e4.rows[3].label, "Sampled RSS (descriptive) (GiB)");
  assert.equal(e3.rows[0].label, "Recall@20 (validation)");
  assert.equal(e3.rows[1].label, "NDCG@20 (validation)");
  const tableCells = [
    ...scaling.e2Table.columns.flatMap((column) => column.cells),
    ...scaling.e5Table.rows.flatMap((row) => row.cells),
    ...e3.models.flatMap((run) => run.cells),
    ...e4.formats.flatMap((format) => format.cells),
  ];
  assert.ok(tableCells.every((cell) => !/(?:\s+s|ms\/session|MiB|GiB|%)$/.test(cell.text)), "table values should not repeat units");
  assert.equal(e4.formats[0].cells[2].raw, String(official.tables.E4[0].preprocessing_wall_seconds_including_read));
  assert.equal(e4.excluded.length, 2);
  assert.equal(Object.hasOwn(e4, "preprocessingNote"), false);
});

test("E5 chart labels are numbers only, padded from the longest tick, and never collide", () => {
  for (const locale of ["en", "vi"]) {
    setLanguage(locale);
    const view = buildScalingView(official);
    assert.equal(view.e5Table.rows.find((row) => row.field === "seconds_per_million_events").label.includes("(s)"), false);
    for (const chart of view.charts) {
      for (const width of [600, 520, 300, 260]) {
        const layout = chartLayout(chart.series, { width, height: 300, formatValue: chart.formatValue });
        const labels = [...layout.ticks, ...layout.xLabels, ...layout.pointLabels];
        for (const label of [...layout.ticks, ...layout.pointLabels]) {
          assert.match(label.text, /^[\d.,]+$/, `${chart.id}: "${label.text}" must be a number only`);
        }
        const longest = Math.max(...layout.ticks.map((tick) => textWidth(tick.text, layout.fontSize)));
        assert.ok(layout.padding.left >= longest + layout.fontSize, `${chart.id}@${width}: left padding fits tick labels`);
        assert.ok(layout.ticks.every((tick) => tick.visible), `${chart.id}@${width}: all y ticks shown`);
        assert.ok(labels.filter((label) => label.visible).length >= 8, `${chart.id}@${width}: most labels shown`);
      }
    }
    assert.ok(!view.charts.some((chart) => chart.yLabel.includes("million events (s)")));
  }
});

test("E5 charts always show the first and last event-count ticks, without overlap", () => {
  for (const locale of ["en", "vi"]) {
    setLanguage(locale);
    const view = buildScalingView(official);
    for (const chart of view.charts) {
      for (const [width, fontSize, presenterHeight] of [[600, 13], [520, 13], [420, 13], [300, 13], [260, 13], [560, 16, 320], [516, 16, 320], [496, 16, 320]]) {
        const height = presenterHeight ?? (width < 420 ? 260 : 290);
        const layout = chartLayout(chart.series, { width, height, fontSize, formatValue: chart.formatValue, yLabel: chart.yLabel });
        assert.ok(layout.xLabels[0].visible, `${locale} ${chart.id}@${width}: first x tick (${layout.xLabels[0].text})`);
        assert.ok(layout.xLabels.at(-1).visible, `${locale} ${chart.id}@${width}: last x tick`);
        assert.equal(layout.xLabels[0].text, new Intl.NumberFormat("en-US").format(official.tables.E2.toSorted((a, b) => a.subset - b.subset)[0].n_events));
      }
    }
  }
});

test("E5 bottleneck values are translated labels with the raw stage name kept for the tooltip", async () => {
  const { bottleneckLabel } = await import("../src/scaling.js");
  for (const locale of ["en", "vi"]) {
    setLanguage(locale);
    const row = buildScalingView(official).e5Table.rows.find((r) => r.field === "bottleneck");
    official.tables.E5.toSorted((a, b) => a.subset - b.subset).forEach((run, index) => {
      assert.equal(row.cells[index].raw, run.bottleneck, "raw stage name in the title attribute");
      assert.ok(!row.cells[index].text.includes("_"), `${locale}: "${row.cells[index].text}" is a label, not a raw key`);
    });
  }
  setLanguage("en");
  assert.equal(bottleneckLabel("train_including_sequence_io"), "Training (incl. sequence I/O)");
  assert.equal(bottleneckLabel("some_new_stage"), "some new stage", "unknown values fall back to the raw text");
});
