import { setLanguage, t } from "../src/i18n.js";
import { test } from "node:test";
import assert from "node:assert/strict";
import { histogramBuckets, normalizeDataset } from "../src/dataset.js";

setLanguage(process.env.TV4_TEST_LANGUAGE);

test("keeps missing buckets distinct from observed zero and sums longer buckets", () => {
  const buckets = histogramBuckets({ 1: 10, 2: 0, 21: 4, 25: 3 });
  assert.deepEqual(buckets.slice(0, 3).map((bucket) => bucket.count), [10, 0, null]);
  assert.deepEqual(buckets.at(-1), { label: "21+", count: 7 });
});

test("rejects a malformed dataset overview", () => {
  assert.ok(normalizeDataset({ subsets: [] }).fatal);
});

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PipelineMeasurementBadge, visiblePipelineMeasurements } from "../src/pipeline-measurements.js";

test("pipeline section and badge are opt-in", () => {
  const render = (measurements) => renderToStaticMarkup(createElement(PipelineMeasurementBadge, { measurements }));
  assert.equal(visiblePipelineMeasurements({ show: false, e2: [{}] }), null);
  assert.equal(render({ show: false }), "");
  assert.ok(render({ show: true }).includes(t("smoke_awaiting_tv2_confirmation")));
});
