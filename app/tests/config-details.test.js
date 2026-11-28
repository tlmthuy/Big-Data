import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { setLanguage } from "../src/i18n.js";
import { configurationRows, runtimeRows } from "../src/run-config.js";

const official = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8"));

test("configuration details keep planned and actual values distinct and localize missing fields", () => {
  setLanguage("en");
  const popularity = configurationRows(official.configs["e1-popularity-010"]);
  const byKey = Object.fromEntries(popularity.map((row) => [row.key, row]));
  assert.equal(byKey.batch_size.planned, "Not applicable");
  assert.equal(byKey.batch_size.actual, "Not applicable");
  assert.equal(byKey.sequence_length.planned, "Not applicable");
  assert.equal(byKey.sequence_length.actual, "Not applicable");
  const runtime = Object.fromEntries(runtimeRows(official.configs["e1-popularity-010"]).map((row) => [row.key, row.value]));
  for (const field of ["gpu", "cuda", "torch", "transformers4rec"]) assert.equal(runtime[field], "Not applicable");

  const gru = Object.fromEntries(configurationRows(official.configs["e1-gru-010"]).map((row) => [row.key, row]));
  assert.equal(gru.batch_size.planned, "256");
  assert.equal(gru.batch_size.actual, "256");
  assert.equal(gru.batch_size.differs, false);
  assert.equal(gru.eval_batch_size.planned, "Not available yet");
  assert.equal(gru.eval_batch_size.actual, "32");
  assert.equal(gru.sequence_length.actual, "Not available yet");
  assert.equal(gru.learning_rate.differs, false);
});

test("configuration difference flags require both values and an actual difference", () => {
  setLanguage("en");
  const config = {
    planned: { model: "gru", batch_size: 32 },
    actual: { model: "gru", batch_size: 128 },
  };
  const batch = configurationRows(config).find((row) => row.key === "batch_size");
  assert.equal(batch.differs, true);
  const absent = configurationRows({ planned: { model: "gru" }, actual: { model: "gru" } })
    .find((row) => row.key === "batch_size");
  assert.equal(absent.differs, false);

  const symbolic = configurationRows({
    planned: { model: "gru", train_partitions: "1..D-1" },
    actual: { model: "gru", train_through: 6 },
  }).find((row) => row.key === "train_through");
  assert.equal(symbolic.differs, false);

  const sameNumbers = configurationRows({
    planned: { model: "gru", batch_size: 256 }, actual: { model: "gru", batch_size: 256 },
  }).find((row) => row.key === "batch_size");
  assert.equal(sameNumbers.differs, false);
  const differentNumbers = configurationRows({
    planned: { model: "gru", batch_size: 256 }, actual: { model: "gru", batch_size: 128 },
  }).find((row) => row.key === "batch_size");
  assert.equal(differentNumbers.differs, true);
});

import { runKind, runtimeRows as runtimeRowsForKind, configurationRows as rowsForKind } from "../src/run-config.js";
test("run kinds: a field that does not exist for the run type is 'Not applicable', never 'Not available yet'", () => {
  setLanguage("en");
  const e4 = official.configs["e4-full-010-csv"];
  assert.equal(runKind(e4), "preprocessing");
  assert.equal(runKind(official.configs["e1-popularity-010"]), "baseline");
  assert.equal(runKind(official.configs["e1-gru-010"]), "training");
  for (const row of rowsForKind(e4)) assert.deepEqual([row.planned, row.actual], ["Not applicable", "Not applicable"], row.key);
  for (const row of runtimeRowsForKind(e4)) assert.equal(row.value, "Not applicable", row.key);
});
