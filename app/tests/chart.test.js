// Chart geometry and selection logic (pure functions behind src/Chart.jsx).
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { barLayout, formatTick, nextMarkIndex, niceTicks, textWidth, toggleSelection, wrapLabel } from "../src/chart-math.js";

const official = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8"));

test("nice ticks start at zero, cover the maximum and use round steps", () => {
  assert.deepEqual(niceTicks(0.1249).ticks, [0, 0.05, 0.1, 0.15]);
  assert.deepEqual(niceTicks(491.2).ticks, [0, 200, 400, 600]);
  assert.deepEqual(niceTicks(66.7).ticks, [0, 20, 40, 60, 80]);
  assert.deepEqual(niceTicks(0).ticks, [0, 0.25, 0.5, 0.75, 1]);
  assert.equal(formatTick(0.05, 0.05), "0.05");
  assert.equal(formatTick(0.075, 0.025), "0.075");
  assert.equal(formatTick(7.5, 2.5), "7.5");
  assert.equal(formatTick(400, 200), "400");
});

test("selection: click selects, clicking again clears", () => {
  assert.equal(toggleSelection(null, "GRU"), "GRU");
  assert.equal(toggleSelection("GRU", "GRU"), null);
  assert.equal(toggleSelection("GRU", "XLNet"), "XLNet");
});

test("keyboard: arrows move between marks and wrap; other keys do nothing", () => {
  assert.equal(nextMarkIndex(0, "ArrowRight", 3), 1);
  assert.equal(nextMarkIndex(2, "ArrowRight", 3), 0);
  assert.equal(nextMarkIndex(0, "ArrowLeft", 3), 2);
  assert.equal(nextMarkIndex(1, "ArrowDown", 3), 2);
  assert.equal(nextMarkIndex(1, "Home", 3), 0);
  assert.equal(nextMarkIndex(1, "End", 3), 2);
  assert.equal(nextMarkIndex(1, "a", 3), null);
});

test("bar layout: zero baseline, ticks never clipped, 44 px hit areas, labels fit their band", () => {
  const e1 = official.tables.E1.map((run) => ({ key: run.model, label: run.model, y: run["Recall@20"], short: run["Recall@20"].toFixed(4) }));
  const e3 = official.tables.E3.map((run) => ({ key: run.run_id, label: `Train batch ${run.train_batch_size}`, y: run.process_wall_seconds, short: String(run.process_wall_seconds) }));
  for (const points of [e1, e3]) {
    for (const width of [600, 420, 300, 260]) {
      for (const fontSize of [13, 16]) {
        const layout = barLayout(points, { width, height: 250, fontSize });
        assert.equal(layout.ticks[0].value, 0);
        for (const tick of layout.ticks) assert.ok(tick.x - textWidth(tick.text, fontSize) >= fontSize, `tick "${tick.text}" fits at ${width}`);
        const boxes = [];
        for (const bar of layout.bars) {
          assert.ok(bar.hit.width >= 44 && bar.hit.height >= 44, "hit area >= 44 x 44");
          assert.ok(bar.lines.length <= 2);
          assert.equal(bar.lines.map((line) => line.text).join(" "), bar.label, "category label is complete (no ellipsis, nothing dropped)");
          for (const line of bar.lines) {
            const w = textWidth(line.text, layout.categoryFont);
            boxes.push({ x0: line.x - w / 2, x1: line.x + w / 2, y: line.y });
            assert.ok(line.x + w / 2 <= width, `"${line.text}" inside the frame at ${width}`);
          }
          if (bar.valueLabel.visible) assert.ok(bar.valueLabel.y >= fontSize, "value label inside the chart");
          assert.ok(bar.top >= layout.padding.top - 0.5);
        }
        for (const a of boxes) for (const b of boxes) {
          if (a !== b && a.y === b.y) assert.ok(a.x1 <= b.x0 || b.x1 <= a.x0, `labels collide at ${width}/${fontSize}`);
        }
        assert.ok(layout.categoryFont === fontSize || layout.categoryFont === 13);
      }
    }
  }
});

test("labels wrap to at most two lines", () => {
  assert.deepEqual(wrapLabel("Train batch 128", 1000, 13), ["Train batch 128"]);
  assert.equal(wrapLabel("Train batch 128", 70, 13).length, 2);
  assert.deepEqual(wrapLabel("Popularity", 30, 13), ["Popularity"], "a long single word is never truncated");
  assert.ok(!wrapLabel("Train batch 128 extra words here", 40, 13).join(" ").includes("…"));
});

test("E4 file-size chart is plotted in MiB, matching its axis title", async () => {
  const source = readFileSync(new URL("../src/Experiments.jsx", import.meta.url), "utf8");
  assert.match(source, /displayUnit === "MiB" \? 1024 \*\* 2/);
  const bytes = official.tables.E4.map((run) => run.bytes / 1024 ** 2);
  const layout = barLayout(bytes.map((y, index) => ({ key: String(index), label: "x", y, short: y.toFixed(1) })), { width: 400 });
  assert.ok(layout.axis.max < 1000, `axis in MiB, not bytes (max ${layout.axis.max})`);
});

test("tooltip placement never covers the mark or any label; falls back to below the chart", async () => {
  const { placeTooltip } = await import("../src/chart-math.js");
  const overlap = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
  const layout = barLayout(official.tables.E1.map((run) => ({ key: run.model, label: run.model, y: run["Recall@20"], short: run["Recall@20"].toFixed(4) })), { width: 520, height: 250 });
  const labels = layout.bars.flatMap((bar) => [
    { x0: bar.cx - textWidth(bar.valueLabel.text, 13) / 2, x1: bar.cx + textWidth(bar.valueLabel.text, 13) / 2, y0: bar.valueLabel.y - 13, y1: bar.valueLabel.y + 3 },
    ...bar.lines.map((line) => ({ x0: line.x - textWidth(line.text, 13) / 2, x1: line.x + textWidth(line.text, 13) / 2, y0: line.y - 13, y1: line.y + 3 })),
  ]);
  for (const bar of layout.bars) {
    const mark = { x0: bar.x, x1: bar.x + bar.width, y0: bar.valueLabel.y - 13, y1: layout.padding.bottom };
    const size = { w: 200, h: 100 };
    const place = placeTooltip({ size, frame: { w: 520, h: 250 }, mark, marks: [mark], labels });
    if (!place) continue;
    const box = { x0: place.left, x1: place.left + size.w, y0: place.top, y1: place.top + size.h };
    assert.ok(box.x0 >= 0 && box.x1 <= 520 && box.y0 >= 0 && box.y1 <= 250, `${bar.key}: inside the frame`);
    for (const other of [mark, ...labels]) assert.ok(!overlap(box, other), `${bar.key}: tooltip covers a mark or label`);
  }
  assert.equal(placeTooltip({ size: { w: 300, h: 200 }, frame: { w: 280, h: 250 }, mark: { x0: 10, x1: 50, y0: 10, y1: 240 } }), null, "too big: below the chart");
});

test("category labels: wide labels shrink to 13 px, then stagger; never an ellipsis", async () => {
  const { categoryLabels } = await import("../src/chart-math.js");
  const normal = categoryLabels(["Popularity", "GRU", "XLNet"], { band: 120, fontSize: 16 });
  assert.equal(normal.font, 16);
  assert.equal(normal.stagger, false);
  const shrunk = categoryLabels(["Popularity", "GRU", "XLNet"], { band: 70, fontSize: 16 });
  assert.equal(shrunk.font, 13);
  const tight = categoryLabels(["Popularity", "Popularity", "Popularity"], { band: 50, fontSize: 13 });
  assert.equal(tight.stagger, true);
  for (const result of [normal, shrunk, tight]) assert.ok(!result.labels.flat().join(" ").includes("…"));
});
