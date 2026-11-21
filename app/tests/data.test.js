import { setLanguage, t } from "../src/i18n.js";
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  INVALID_PRODUCT_ID, compareConfig, displayCell, formatValue, loadJson,
  normalizeDemo, normalizeResults, sessionContext, splitByKind, usersBySession,
} from "../src/data.js";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const json = (path) => JSON.parse(read(path));
const fakeFetch = (body, status = 200) => async () => ({ ok: status < 400, status, text: async () => body });

setLanguage(process.env.TV4_TEST_LANGUAGE);

test("shipped demo-data.json is valid and keeps artifact order", () => {
  const { groups, issues, fatal } = normalizeDemo(json("../public/demo-data.json"));
  assert.equal(fatal, null);
  assert.deepEqual(issues, []);
  const day1 = groups.find((g) => g.sessionIds.includes("rank1"));
  const run = day1.runs[0];
  const byId = Object.fromEntries(run.sessions.map((s) => [s.user_session, s]));
  assert.equal(byId.rank1.targetRank, 1);
  assert.equal(byId.rank20.targetRank, 20);
  assert.equal(byId.miss.targetRank, null);
  assert.equal(byId.rank1.recommendations[0].product_id, "p3");
  assert.ok(byId.rank1.recommendations.every((r) => r.score === null), "no score is invented");
  assert.ok(run.sessions.every((s) => /^p\d+$/.test(s.target)), "original IDs only");
});

test("E1 toy group holds Popularity, GRU and XLNet on the same session", () => {
  const { groups } = normalizeDemo(json("../public/demo-data.json"));
  const e1 = groups.find((g) => g.runs.some((r) => r.run_id === "smoke-e1-gru-010"));
  assert.deepEqual(e1.runs.map((r) => r.modelKey).sort(), ["gru", "popularity", "xlnet"]);
  assert.ok(e1.runs.every((r) => r.data_kind === "toy"));
});

test("legacy single-run shape is still accepted", () => {
  const legacy = { model: "Popularity", subset: "toy", split: "validation", catalog: ["p3", "p4"],
    sessions: [{ user_session: "a", prefix: ["p4"], target: "p3", top20: ["p3", "p4"] }] };
  const { groups, fatal } = normalizeDemo(legacy);
  assert.equal(fatal, null);
  assert.equal(groups[0].runs[0].sessions[0].targetRank, 1);
});

test("empty sessions is a readable fatal error, not a crash", () => {
  const { fatal } = normalizeDemo(json("./fixtures/no-sessions.json"));
  assert.match(fatal, /session/);
});

test("non-object input is rejected", () => {
  assert.ok(normalizeDemo(null).fatal);
  assert.ok(normalizeDemo([]).fatal);
  assert.ok(normalizeDemo({ foo: 1 }).fatal);
});

test("missing prefix/target/top20 keep the other parts and report issues", () => {
  const { groups, issues, fatal } = normalizeDemo(json("./fixtures/missing-fields.json"));
  assert.equal(fatal, null);
  const s = Object.fromEntries(groups[0].runs[0].sessions.map((x) => [x.user_session, x]));
  assert.equal(s["no-prefix"].prefix, null);
  assert.equal(s["no-prefix"].target, "p3");
  assert.equal(s["no-target"].target, null);
  assert.equal(s["no-top20"].recommendations, null);
  assert.equal(s["no-top20"].prefix[0], "p4");
  assert.deepEqual(s["technical-id"].recommendations.map((r) => r.product_id), ["p3", "p5"]);
  assert.equal(s["technical-id"].targetRank, 3, "rank stays the artifact position");
  assert.ok(issues.some((i) => i.includes("user_session")));
  assert.equal(groups[0].sessionIds.length, 4);
});

test("history and target come from the group even when a model has no run", () => {
  const { groups } = normalizeDemo(json("../public/demo-data.json"));
  const day1 = groups.find((g) => g.sessionIds.includes("miss"));
  const { prefix, target } = sessionContext(day1, "miss");
  assert.deepEqual({ prefix, target }, { prefix: ["p3"], target: "p23" });
});

test("out-of-catalog context stays visible and technical IDs keep their position as placeholders", () => {
  const { groups, issues } = normalizeDemo(json("./fixtures/unknown-ids.json"));
  const [group] = groups;
  const { prefix, target, targetCatalog } = sessionContext(group, "unknown-ids");
  assert.deepEqual(prefix, ["p3", INVALID_PRODUCT_ID, INVALID_PRODUCT_ID, INVALID_PRODUCT_ID, "p-unknown-history", "p4"]);
  assert.equal(target, "p5");
  assert.equal(targetCatalog.has(target), false);
  assert.equal(sessionContext(group, "invalid-target").target, INVALID_PRODUCT_ID);
  const [session] = group.runs[0].sessions;
  assert.deepEqual(session.recommendations.map(({ rank, product_id }) => [rank, product_id]), [[1, "p4"], [5, "p3"]]);
  assert.ok(issues[0].includes(t("0_invalid_product_id", t("history_2"))));
  assert.ok(issues[0].includes(t("0_product_id_is_absent_from", t("history_2"))));
  assert.ok(issues[0].includes(t("0_product_id_is_absent_from", t("actual_item"))));
  assert.ok(issues[0].includes(t("hid_0_technical_or_out_of", 3)));
});

test("user picker has no options for shipped sessions and reads user IDs from a test fixture", () => {
  const { groups } = normalizeDemo(json("../public/demo-data.json"));
  for (const group of groups) assert.equal(usersBySession(group).size, 0);
  const [fixture] = normalizeDemo(json("./fixtures/session-users.json")).groups;
  assert.deepEqual([...usersBySession(fixture)], [
    ["fixture-a", "fixture-user-a"],
    ["fixture-b", "fixture-user-b"],
  ]);
});

test("loadJson reports empty, malformed and HTTP errors", async () => {
  assert.equal((await loadJson("x", fakeFetch(read("./fixtures/empty.json")))).error, t("0_is_empty", "x"));
  assert.match((await loadJson("x", fakeFetch(read("./fixtures/malformed.json")))).error, /JSON/);
  assert.match((await loadJson("x", fakeFetch("", 404))).error, /404/);
  assert.deepEqual((await loadJson("x", fakeFetch('{"a":1}'))).data, { a: 1 });
});

test("shipped run-results.json: planned runs have no invented values", () => {
  const { runs, fatal, meta } = normalizeResults(json("../public/run-results.json"));
  assert.equal(fatal, null);
  assert.equal(meta.confirmed_by_tv2, false);
  const e3 = splitByKind(runs, "E3");
  assert.deepEqual(e3.official.map((r) => r.run_id), ["e3-gru-010-b32", "e3-gru-010-b128"]);
  for (const run of runs.filter((r) => r.data_kind !== "toy")) {
    for (const [name, m] of Object.entries(run.metrics)) assert.equal(m.value, null, `${run.run_id} ${name}`);
  }
  assert.ok(e3.toy.every((r) => r.data_kind === "toy"));
});

test("bad run-results shape is a fatal error", () => {
  assert.ok(normalizeResults(json("./fixtures/bad-results.json")).fatal);
});

test("formatting never turns missing into zero", () => {
  assert.equal(formatValue(null), t("not_available_yet"));
  assert.equal(formatValue(undefined), t("not_available_yet"));
  assert.equal(formatValue(0), "0");
  assert.equal(formatValue(3561836544), "3,561,836,544");
  assert.equal(displayCell({ model: "Popularity" }, "peak_cuda_reserved_bytes", null), t("not_applicable"));
  assert.equal(displayCell({ model: "gru" }, "peak_cuda_reserved_bytes", null), t("not_available_yet"));
});

test("planned vs actual comparison flags differences only when both exist", () => {
  assert.equal(compareConfig("subset", "10", "toy"), "different");
  assert.equal(compareConfig("train_batch_size", 32, 32), "same");
  assert.equal(compareConfig("sequence_length", 20, null), null);
  assert.equal(compareConfig("train_partitions", "1..D-1", [1, 2]), null);
});
