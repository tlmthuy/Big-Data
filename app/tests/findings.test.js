// Key finding guards: a headline or added clause appears only when the JSON values agree with it.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { setLanguage } from "../src/i18n.js";
import { datasetFindings, e1Best, e1Cheapest, e1Finding, e2Finding as e2Raw, e3Finding as e3Raw, e4Finding as e4Raw, e5Finding as e5Raw, stageShort, strictlyIncreasing } from "../src/findings.js";
import { plain } from "./helpers.js";
// Bodies are compared through plain(): it first asserts U+00A0 between every number and unit.
const viaPlain = (finding) => (results) => { const f = finding(results); return { ...f, body: plain(f.body) }; };
const e2Finding = viaPlain(e2Raw), e3Finding = viaPlain(e3Raw), e4Finding = viaPlain(e4Raw), e5Finding = viaPlain(e5Raw);
import { formatPercentShare } from "../src/format.js";

const official = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8"));
const overview = JSON.parse(readFileSync(new URL("../public/dataset-overview.json", import.meta.url), "utf8"));
const patchTable = (table, key, patch) => {
  const copy = structuredClone(official);
  copy.tables[table] = copy.tables[table].map((row) => ({ ...row, ...(patch[row[key]] ?? {}) }));
  return copy;
};
setLanguage("en");

test("E1: best needs Recall@20 and NDCG@20 to agree; cheapest needs train and eval time to agree", () => {
  const runs = official.tables.E1;
  assert.equal(e1Best(runs).model, "xlnet");
  assert.equal(e1Cheapest(runs).model, "Popularity");
  assert.equal(e1Finding(official).headline, "XLNet predicts best; Popularity is cheapest to run");
  const split = patchTable("E1", "model", { gru: { "NDCG@20": 1 } });
  assert.equal(e1Best(split.tables.E1), null);
  assert.equal(e1Finding(split).headline, "Popularity is cheapest to run", "accuracy half omitted");
  const costly = patchTable("E1", "model", { Popularity: { final_evaluation_seconds: 99 } });
  assert.equal(e1Finding(costly).headline, "XLNet predicts best", "cost half omitted");
  const neither = patchTable("E1", "model", { gru: { "NDCG@20": 1 }, Popularity: { final_evaluation_seconds: 99 } });
  assert.equal(e1Finding(neither).headline, null, "no headline when both halves are omitted");
  const missing = patchTable("E1", "model", { xlnet: { "Recall@20": null } });
  assert.equal(e1Best(missing.tables.E1), null);
});

test("E1: body lists every Recall@20; GRU-vs-Popularity sentence only when Popularity < GRU < best", () => {
  const finding = e1Finding(official);
  assert.equal(finding.body, "Recall@20: 0.1249 for XLNet, 0.0883 for GRU, 0.0868 for Popularity. GRU only just beats the simple Popularity baseline.");
  assert.equal(finding.caveat, "One run, one seed, no significance test, so read the ranking as indicative.");
  const gruLower = patchTable("E1", "model", { gru: { "Recall@20": 0.05 } });
  assert.ok(!e1Finding(gruLower).body.includes("only just beats"));
  setLanguage("vi");
  assert.equal(e1Finding(official).body, "Recall@20: XLNet 0.1249, GRU 0.0883, Popularity 0.0868. GRU chỉ nhỉnh hơn mô hình Popularity đơn giản một chút.");
  setLanguage("en");
});

test("E2: headline only when Recall@20 rises strictly with subset size", () => {
  assert.equal(strictlyIncreasing([1, 2, 3]), true);
  assert.equal(strictlyIncreasing([1, 3, 2]), false);
  assert.equal(strictlyIncreasing([1, null]), false);
  assert.equal(e2Finding(official).headline, "Larger subsets score higher");
  assert.match(e2Finding(official).body, /^Recall@20 rises from 0\.0883 at 10% to 0\.3899 at 100%\. Preprocessing grows/);
  assert.equal(e2Finding(official).caveat, null);
  const dip = patchTable("E2", "subset", { 50: { "Recall@20": 0.01 } });
  assert.equal(e2Finding(dip).headline, null);
  assert.match(e2Finding(official).body, /Preprocessing grows from 30\.4 s to 45\.4 s and training from 27\.6 s to 433 s between 10% and 100%\. Each subset/);
  const flatPre = patchTable("E2", "subset", { 100: { preprocessing_seconds: 1 } });
  assert.ok(!e2Finding(flatPre).body.includes("grows"), "no 'grows' when preprocessing is not higher at 100%");
  assert.match(e2Finding(flatPre).body, /Preprocessing is 30\.4 s at 10% and 1\.00 s at 100%; training is 27\.6 s and 433 s\./);
  const fall = patchTable("E2", "subset", { 100: { "Recall@20": 0.01 } });
  assert.ok(!e2Finding(fall).body.includes("rises"), "no 'rises' when the last value is not higher");
});

test("E3: headline needs a shorter training time AND lower Recall@20 for the larger batch", () => {
  assert.equal(e3Finding(official).headline, "Batch 128 trains faster but predicts worse");
  const noTradeOff = patchTable("E3", "train_batch_size", { 128: { "Recall@20": 0.5 } });
  assert.equal(e3Finding(noTradeOff).headline, null);
  const slower = patchTable("E3", "train_batch_size", { 128: { train_seconds_including_sequence_io: 999 } });
  assert.equal(e3Finding(slower).headline, null);
  assert.equal(e3Finding(official).caveat, "Same VM and GPU, validation split, one run. Do not compare with E1 or E2.");
});

test("E3: weight-updates sentence needs equal epochs", () => {
  const body = e3Finding(official).body;
  assert.match(body, /With the same epochs, a larger batch means fewer weight updates\.$/);
  const epochs = structuredClone(official);
  const id = epochs.tables.E3.find((run) => run.train_batch_size === 128).run_id;
  epochs.configs[id].actual.epochs = 9;
  assert.ok(!e3Finding(epochs).body.includes("weight updates"));
});

test("E4: headline needs smaller AND faster read AND each read < 10% of its preprocessing", () => {
  assert.equal(e4Finding(official).headline, "Parquet is much smaller and faster to read");
  assert.equal(e4Finding(official).caveat, "Warm cache, one run, conversion time not included.");
  assert.equal(e4Finding(patchTable("E4", "format", { parquet: { bytes: 999999999 } })).headline, null);
  assert.equal(e4Finding(patchTable("E4", "format", { parquet: { read_seconds: 9 } })).headline, null);
  assert.equal(e4Finding(patchTable("E4", "format", { csv: { read_seconds: 30 } })).headline, null, "read is not a small part");
});

test("E5: bottleneck headline from the first and last subset; shares from stage_shares (1 decimal)", () => {
  const finding = e5Finding(official);
  assert.equal(finding.headline, "As data grows, the bottleneck shifts to training");
  const shares = Object.fromEntries(official.stage_shares.rows.map((row) => [row.subset, row]));
  assert.ok(finding.body.startsWith(`Preprocessing takes ${formatPercentShare(shares[10].preprocessing).text} of the combined stage time at 10%; training takes ${formatPercentShare(shares[100].train).text} at 100%.`));
  assert.match(finding.body, /Time per million events falls from 66\.7 s to 55\.6 s, which fits fixed costs being shared across more data\.$/);
  assert.equal(finding.caveat, "Four sizes on one machine; says nothing about multi-machine scaling.");
  const same = patchTable("E5", "subset", { 10: { bottleneck: "train_including_sequence_io" } });
  assert.equal(e5Finding(same).headline, "Training stays the main cost");
  setLanguage("vi");
  assert.equal(e5Finding(same).headline, "Huấn luyện vẫn là chi phí chính");
  assert.equal(e5Finding(official).headline, "Khi dữ liệu tăng, nút thắt chuyển sang huấn luyện");
  setLanguage("en");
  const rising = patchTable("E5", "subset", { 100: { seconds_per_million_events: 999 } });
  assert.ok(!e5Finding(rising).body.includes("Time per million events"));
  assert.equal(stageShort("some_new_stage"), "some new stage");
  const noShares = { ...official, stage_shares: undefined };
  assert.ok(!e5Finding(noShares).body.includes("Preprocessing takes"));
});

test("Dataset findings: values from dataset-overview.json; guards follow the data", () => {
  const [d1, d2, d3] = datasetFindings(overview);
  assert.equal(d1.headline, "Almost every event is a product view");
  assert.match(d1.body, /^Views are 96\.21% of raw events and 99\.98% after cleanup/);
  assert.equal(d2.headline, "Only sessions with two or more interactions can be tested");
  assert.match(d2.body, /^48\.58% of sessions have just one interaction after cleanup/);
  assert.equal(d3.headline, "The 10% subset still has 63,398 of 118,333 products");
  assert.match(d3.body, /^Session lengths look like the full week/);
  const flat = structuredClone(overview);
  flat.event_mix_before_after.find((row) => row.event_type === "view").clean_100_pct = 80;
  assert.equal(datasetFindings(flat)[0].headline, null, "no 'almost every' below the threshold");
  const noCoverage = structuredClone(overview);
  for (const row of noCoverage.subsets) delete row.catalog_coverage_of_100_pct;
  assert.equal(datasetFindings(noCoverage)[2].headline, "The 10% subset still has 63,398 of 118,333 products", "share falls back to the counts");
  const fewProducts = structuredClone(overview);
  fewProducts.subsets.find((row) => row.subset === 10).catalog_coverage_of_100_pct = 5;
  assert.equal(datasetFindings(fewProducts)[2].headline, null);
});
