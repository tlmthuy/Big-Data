// Data-driven wording for the E3/E4 takeaways: comparison words come from the JSON values.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { setLanguage } from "../src/i18n.js";
import { compare, e3Hardware, e3Limitation, e3Takeaway as e3TakeawayRaw, isSimilar, isSmallPart } from "../src/takeaways.js";
import { plain } from "./helpers.js";
// Sentences are compared through plain(): it first asserts U+00A0 between every number and unit.
const e3Takeaway = (results) => plain(e3TakeawayRaw(results));

const official = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8"));
const withE3 = (patch) => {
  const copy = structuredClone(official);
  copy.tables.E3 = copy.tables.E3.map((run) => ({ ...run, ...(patch[run.train_batch_size] ?? {}) }));
  return copy;
};

test("compare: higher, lower, equal, missing", () => {
  assert.equal(compare(2, 1), "higher");
  assert.equal(compare(1, 2), "lower");
  assert.equal(compare(1, 1), "equal");
  assert.equal(compare(null, 1), null);
  assert.equal(compare(1, Number.NaN), null);
});

test("E3 takeaway with the shipped data: words follow the values, numbers via format.js", () => {
  setLanguage("en");
  assert.equal(e3Takeaway(official),
    "Training time drops from 51.7 s to 30.6 s and GPU memory rises from 2.2 GiB to 3.9 GiB, while validation Recall@20 falls from 0.1964 to 0.1299.");
  setLanguage("vi");
  assert.equal(e3Takeaway(official),
    "Thời gian huấn luyện giảm từ 51.7 s xuống 30.6 s, bộ nhớ GPU tăng từ 2.2 GiB lên 3.9 GiB, còn Recall@20 trên validation giảm từ 0.1964 xuống 0.1299.");
  setLanguage("en");
});

test("E3 takeaway flips every word when the values flip", () => {
  setLanguage("en");
  const flipped = withE3({
    32: { train_seconds_including_sequence_io: 10, sampled_gpu_process_bytes: 4 * 1024 ** 3, "Recall@20": 0.1 },
    128: { train_seconds_including_sequence_io: 20, sampled_gpu_process_bytes: 2 * 1024 ** 3, "Recall@20": 0.2 },
  });
  const text = e3Takeaway(flipped);
  assert.match(text, /Training time rises from 10\.0 s to 20\.0 s/);
  assert.match(text, /GPU memory drops from 4\.0 GiB to 2\.0 GiB/);
  assert.match(text, /validation Recall@20 rises from 0\.1000 to 0\.2000/);
});

test("E3 takeaway is neutral when a value is equal or missing", () => {
  setLanguage("en");
  const equal = withE3({ 32: { train_seconds_including_sequence_io: 30 }, 128: { train_seconds_including_sequence_io: 30 } });
  const missing = withE3({ 128: { sampled_gpu_status: "unavailable", sampled_gpu_process_bytes: null } });
  for (const results of [equal, missing]) {
    const text = e3Takeaway(results);
    assert.ok(!/drops|rises|falls/.test(text), text);
    assert.match(text, /^Train batch 128: training time /);
  }
  assert.match(e3Takeaway(missing), /GPU memory Not available yet/);
});

test("E3 limitation reads hardware from JSON", () => {
  setLanguage("en");
  assert.equal(e3Hardware(official), "one AWS VM (Ubuntu 22.04) with one Tesla T4");
  assert.ok(e3Limitation(official).startsWith("Hardware was fixed: one AWS VM (Ubuntu 22.04) with one Tesla T4. CPU, RAM"));
  setLanguage("vi");
  assert.equal(e3Hardware(official), "một VM AWS (Ubuntu 22.04) với một GPU Tesla T4");
  setLanguage("en");
  assert.equal(e3Hardware({ vm_environment: { cloud: official.vm_environment.cloud } }), "one AWS VM (Ubuntu 22.04)", "missing GPU drops that part");
  assert.equal(e3Hardware({ vm_environment: { gpu: official.vm_environment.gpu } }), "one Tesla T4", "missing VM drops that part");
  assert.equal(e3Hardware({ vm_environment: { cloud: "VM AWS", gpu: "Tesla T4" } }), "one AWS VM with one Tesla T4", "missing OS drops the brackets");
  const noHardware = { ...official, vm_environment: {} };
  assert.equal(e3Hardware(noHardware), null);
  assert.ok(e3Limitation(noHardware).startsWith("Hardware was fixed; CPU, RAM"));
});

test("10% rules: similar and small part", () => {
  assert.equal(isSimilar(100, 91), true);
  assert.equal(isSimilar(100, 90), false, "exactly 10% is not similar");
  assert.equal(isSimilar(null, 1), false);
  assert.equal(isSmallPart(9, 100), true);
  assert.equal(isSmallPart(10, 100), false);
  assert.equal(isSmallPart(1, null), false);
});

import { e4Takeaway as e4TakeawayRaw, formatLabel } from "../src/takeaways.js";
const e4Takeaway = (results) => plain(e4TakeawayRaw(results));
const withE4 = (patch) => {
  const copy = structuredClone(official);
  copy.tables.E4 = copy.tables.E4.map((run) => ({ ...run, ...(patch[run.format] ?? {}) }));
  return copy;
};

test("E4 takeaway with the shipped data: preprocessing only drops a little, 'because' clause applies", () => {
  setLanguage("en");
  assert.equal(e4Takeaway(official),
    "File size goes from 127.8 MiB to 24.2 MiB and read time from 0.454 s to 0.109 s. Total preprocessing only drops from 35.0 s to 33.6 s, because reading is a small part of it.");
  setLanguage("vi");
  assert.equal(e4Takeaway(official),
    "Dung lượng giảm từ 127.8 MiB xuống 24.2 MiB, thời gian đọc từ 0.454 s xuống 0.109 s. Tổng thời gian tiền xử lý chỉ giảm từ 35.0 s xuống 33.6 s, vì bước đọc chỉ chiếm phần nhỏ.");
  setLanguage("en");
  assert.equal(formatLabel("parquet"), "Parquet");
  assert.equal(formatLabel("orc"), "ORC", "unknown formats fall back to the raw value");
});

test("E4: 'only drops' needs lower preprocessing within 10%; otherwise both values are listed", () => {
  setLanguage("en");
  const text = e4Takeaway(withE4({ parquet: { preprocessing_wall_seconds_including_read: 20 } }));
  assert.match(text, /Total preprocessing goes from 35\.0 s to 20\.0 s\.$/);
  assert.ok(!text.includes("because") && !text.includes("only drops"));
  const slower = e4Takeaway(withE4({ parquet: { preprocessing_wall_seconds_including_read: 36 } }));
  assert.match(slower, /Total preprocessing goes from 35\.0 s to 36\.0 s\.$/);
});

test("E4: 'because' only when each read is < 10% of its preprocessing time", () => {
  setLanguage("en");
  const bigRead = e4Takeaway(withE4({ csv: { read_seconds: 5 } }));
  assert.match(bigRead, /only drops from 35\.0 s to 33\.6 s\.$/, bigRead);
  assert.ok(!bigRead.includes("because"));
});

test("E4: equal or missing size/read values give a neutral sentence", () => {
  setLanguage("en");
  for (const results of [withE4({ parquet: { bytes: 134004153 } }), withE4({ parquet: { read_seconds: null } })]) {
    const text = e4Takeaway(results);
    assert.ok(!/goes from|drops/.test(text), text);
    assert.match(text, /^Parquet: file size /);
  }
  const flipped = e4Takeaway(withE4({ parquet: { bytes: 300000000, read_seconds: 1 } }));
  assert.match(flipped, /^Parquet: file size /, "no direction words when Parquet is larger");
});

import { e4Fairness } from "../src/takeaways.js";
test("E4 fairness line only when fingerprints, event counts, program and schema policy all agree", () => {
  setLanguage("en");
  assert.equal(e4Fairness(official), "Same data: 882,808 events, fingerprints match · same program · all nine columns read as strings");
  const breakIt = (mutate) => { const copy = structuredClone(official); mutate(copy.configs["e4-full-010-parquet"].e4_config); return e4Fairness(copy); };
  assert.equal(breakIt((c) => { c.fingerprint_match = false; }), null);
  assert.equal(breakIt((c) => { c.n_events = 1; }), null);
  assert.equal(breakIt((c) => { c.program = "other.py"; }), null);
  assert.equal(breakIt((c) => { c.schema_policy = "typed columns"; }), null);
  const noConfig = structuredClone(official);
  delete noConfig.configs["e4-full-010-csv"].e4_config;
  assert.equal(e4Fairness(noConfig), null);
});
