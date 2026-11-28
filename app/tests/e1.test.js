import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { setLanguage } from "../src/i18n.js";
import { buildE1View, formatE1Context } from "../src/e1.js";

const official = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8"));

test("official E1 view formats XLNet Recall and unavailable Popularity GPU memory", () => {
  setLanguage("en");
  const view = buildE1View(official);
  const recall = view.rows.find((row) => row.field === "Recall@20");
  const gpu = view.rows.find((row) => row.field === "sampled_gpu_process_bytes");
  assert.equal(view.models.map(({ label }) => label).join(" | "), "Popularity | GRU | XLNet");
  assert.equal(recall.cells[2].text, "0.1249");
  assert.equal(gpu.cells[0].text, "Not measured");
  assert.equal(gpu.cells[0].raw, "null");
  assert.match(gpu.label, /\(GiB\)$/);
  assert.equal(view.rows.find((row) => row.field === "train_seconds_including_sequence_io").cells[1].text, "28.1");
  assert.equal(formatE1Context(view.context), "10% subset · test partition 7 · 1,337 sessions · single run, single seed");
});
