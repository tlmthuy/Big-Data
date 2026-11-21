import { test } from "node:test";
import assert from "node:assert/strict";
import { figureRows } from "../src/figures.js";

test("chart values preserve zero and mask unavailable or excluded metrics", () => {
  const run = { run_id: "run", metrics: { time: { value: 0, unit: "s", scope: "wall" } } };
  assert.deepEqual(figureRows([run, { ...run, status: "excluded" }], ["time", "absent"]).map((row) => row.value), [0, null, null, null]);
});
