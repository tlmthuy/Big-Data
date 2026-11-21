import { test } from "node:test";
import assert from "node:assert/strict";
import { routeFromHash } from "../src/navigation.js";

test("deep links open their tabs and unknown hashes open Recommendations", () => {
  assert.deepEqual(routeFromHash("#experiments-e4"), { tab: "experiments", experiment: "E4" });
  assert.equal(routeFromHash("#data").tab, "data");
  assert.equal(routeFromHash("#other").tab, "recommendation");
});
