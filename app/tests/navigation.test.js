import { test } from "node:test";
import assert from "node:assert/strict";
import { experimentHref, routeFromHash } from "../src/navigation.js";

test("every view and experiment has its own hash route", () => {
  assert.deepEqual(routeFromHash("#recommendation"), { tab: "recommendation" });
  assert.deepEqual(routeFromHash("#dataset"), { tab: "dataset" });
  assert.deepEqual(routeFromHash("#experiments"), { tab: "experiments", experiment: "E1", select: null });
  for (const id of ["E1", "E2", "E3", "E4", "E5"]) {
    assert.deepEqual(routeFromHash(experimentHref(id)), { tab: "experiments", experiment: id, select: null });
  }
  assert.equal(experimentHref("E3"), "#experiments/e3");
});

test("a level can be preselected, legacy hashes resolve, unknown hashes open Recommendations", () => {
  assert.deepEqual(routeFromHash("#experiments/e2/25"), { tab: "experiments", experiment: "E2", select: "25" });
  assert.equal(experimentHref("E2", 25), "#experiments/e2/25");
  assert.deepEqual(routeFromHash("#experiments-e4"), { tab: "experiments", experiment: "E4", select: null });
  assert.equal(routeFromHash("#data").tab, "dataset");
  assert.equal(routeFromHash("#other").tab, "recommendation");
  assert.equal(routeFromHash("").tab, "recommendation");
});

test("Dataset sections have hash routes", async () => {
  const { DATASET_SECTIONS, datasetHref } = await import("../src/navigation.js");
  for (const section of DATASET_SECTIONS) assert.deepEqual(routeFromHash(datasetHref(section)), { tab: "dataset", section });
  assert.deepEqual(routeFromHash("#dataset/unknown"), { tab: "dataset" });
  assert.ok(DATASET_SECTIONS.length <= 7);
});
