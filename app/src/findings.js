// "Key finding" callouts for E1–E5 and the Dataset tab, from TV2's analysis
// (reports/tables/tv2-20261124/analysis.md, findings 1–7 and section 8). Every number comes from the
// public JSON via src/format.js; every headline and added clause is shown only when the JSON values agree
// with it (guards below, unit-tested). Ratios that exist only in analysis.md prose are never rendered.
import { messages, t } from "./i18n.js";
import { formatCount, formatPercent, formatPercentShare, formatRatio, formatSeconds, isMissing } from "./format.js";
import { modelLabel } from "./data.js";
import { compare, e3Pair, e3Takeaway, e4Pair, e4Takeaway, isSmallPart } from "./takeaways.js";

const has = (value) => !isMissing(value);
const sortBy = (rows, field) => [...rows].sort((a, b) => a[field] - b[field]);

function argBy(runs, field, pick) {
  const valid = runs.filter((run) => has(run?.[field]));
  if (!valid.length || valid.length !== runs.length) return null;
  const target = pick(...valid.map((run) => run[field]));
  const winners = valid.filter((run) => run[field] === target);
  return winners.length === 1 ? winners[0] : null;
}

// ---------------------------------------------------------------- E1

/** Model with the highest Recall@20 AND NDCG@20 (both must agree), or null. */
export function e1Best(runs) {
  const recall = argBy(runs, "Recall@20", Math.max);
  const ndcg = argBy(runs, "NDCG@20", Math.max);
  return recall && recall === ndcg ? recall : null;
}

/** Model with the lowest training time AND final evaluation time (both must agree), or null. */
export function e1Cheapest(runs) {
  const train = argBy(runs, "train_seconds_including_sequence_io", Math.min);
  const evaluation = argBy(runs, "final_evaluation_seconds", Math.min);
  return train && train === evaluation ? train : null;
}

/** "0.1249 for XLNet, 0.0883 for GRU, 0.0868 for Popularity": every model, highest Recall@20 first. */
export function e1RecallList(runs) {
  const ranked = runs.filter((run) => has(run["Recall@20"])).sort((a, b) => b["Recall@20"] - a["Recall@20"]);
  return ranked.map((run) => t("e1_kf_item", modelLabel(run.model), formatRatio(run["Recall@20"]).text)).join(", ");
}

export function e1Finding(results) {
  const runs = results?.tables?.E1 ?? [];
  const best = e1Best(runs);
  const cheapest = e1Cheapest(runs);
  const name = (run) => modelLabel(run.model);
  const headline = best && cheapest ? t("e1_kf_headline", name(best), name(cheapest))
    : best ? t("e1_kf_headline_best", name(best))
      : cheapest ? t("e1_kf_headline_cheapest", name(cheapest)) : null;
  const byModel = (label) => runs.find((run) => modelLabel(run.model) === label);
  const pop = byModel("Popularity"), gru = byModel("GRU");
  const list = e1RecallList(runs);
  const body = [list ? t("e1_kf_body", list) : t("MISSING")];
  if (best && pop && gru && best !== gru && best !== pop
    && pop["Recall@20"] < gru["Recall@20"] && gru["Recall@20"] < best["Recall@20"]) {
    body.push(t("e1_kf_gru_vs_pop"));
  }
  return { headline, body: body.join(" "), caveat: t("e1_kf_caveat") };
}

// ---------------------------------------------------------------- E2

export function strictlyIncreasing(values) {
  return values.length > 1 && values.every(has) && values.every((value, index) => index === 0 || value > values[index - 1]);
}

export function e2Finding(results) {
  const runs = sortBy(results?.tables?.E2 ?? [], "subset");
  if (runs.length < 2) return { headline: null, body: t("MISSING"), caveat: null };
  const first = runs[0], last = runs.at(-1);
  const rises = compare(last["Recall@20"], first["Recall@20"]) === "higher";
  const recall = t(rises ? "e2_kf_recall" : "e2_kf_recall_neutral", formatRatio(first["Recall@20"]).text, first.subset, formatRatio(last["Recall@20"]).text, last.subset);
  // Processing time: two delivered fields, never summed. "grows" only if both are higher at the largest subset.
  const pre = "preprocessing_seconds", train = "train_seconds_including_sequence_io";
  const grows = compare(last[pre], first[pre]) === "higher" && compare(last[train], first[train]) === "higher";
  const time = t(grows ? "e2_kf_time" : "e2_kf_time_neutral", formatSeconds(first[pre]).text, formatSeconds(last[pre]).text,
    formatSeconds(first[train]).text, formatSeconds(last[train]).text, first.subset, last.subset);
  return {
    headline: strictlyIncreasing(runs.map((run) => run["Recall@20"])) ? t("e2_kf_headline") : null,
    body: [recall, time, t(rises ? "e2_kf_scope" : "e2_kf_scope_neutral")].join(" "),
    caveat: null,
  };
}

// ---------------------------------------------------------------- E3

export function e3Finding(results) {
  const pair = e3Pair(results);
  if (!pair) return { headline: null, body: t("MISSING"), caveat: t("e3_kf_caveat") };
  const [small, large] = pair;
  // Headline: the larger batch has a shorter training time AND a lower validation Recall@20.
  const tradeOff = compare(large.train_seconds_including_sequence_io, small.train_seconds_including_sequence_io) === "lower"
    && compare(large["Recall@20"], small["Recall@20"]) === "lower";
  const config = (run) => results?.configs?.[run.run_id]?.actual ?? {};
  const body = [e3Takeaway(results)];
  const epochs = [config(small).epochs, config(large).epochs];
  if (epochs.every(has) && epochs[0] === epochs[1]) body.push(t("e3_kf_updates"));
  return { headline: tradeOff ? t("e3_kf_headline", large.train_batch_size) : null, body: body.join(" "), caveat: t("e3_kf_caveat") };
}

// ---------------------------------------------------------------- E4

export function e4Finding(results) {
  const pair = e4Pair(results);
  const body = [e4Takeaway(results)];
  let headline = null;
  if (pair) {
    const [base, subject] = pair;
    const smaller = compare(subject.bytes, base.bytes) === "lower";
    const faster = compare(subject.read_seconds, base.read_seconds) === "lower";
    const smallReads = isSmallPart(subject.read_seconds, subject.preprocessing_wall_seconds_including_read)
      && isSmallPart(base.read_seconds, base.preprocessing_wall_seconds_including_read);
    if (smaller && faster && smallReads) headline = t("e4_kf_headline");
  }
  return { headline, body: body.join(" "), caveat: t("e4_kf_caveat") };
}

// ---------------------------------------------------------------- E5

/** Short readable stage name ("preprocessing", "training"); unknown values fall back to the raw text. */
export function stageShort(value) {
  const key = `stage_short_${value}`;
  return Object.hasOwn(messages.en, key) ? t(key) : String(value ?? t("MISSING")).replaceAll("_", " ");
}

const capitalise = (text) => text.charAt(0).toUpperCase() + text.slice(1);

export function e5Finding(results) {
  const runs = sortBy(results?.tables?.E5 ?? [], "subset");
  const shares = new Map((results?.stage_shares?.rows ?? []).map((row) => [row.subset, row]));
  if (runs.length < 2) return { headline: null, body: t("MISSING"), caveat: t("e5_kf_caveat") };
  const first = runs[0], last = runs.at(-1);
  const headline = !has(first.bottleneck) || !has(last.bottleneck) ? null
    : first.bottleneck === last.bottleneck ? t("e5_kf_headline_same", capitalise(stageShort(last.bottleneck)))
      : t("e5_kf_headline", stageShort(last.bottleneck));
  const body = [];
  const pre = shares.get(first.subset)?.preprocessing, train = shares.get(last.subset)?.train;
  if (has(pre) && has(train)) {
    body.push(t("e5_kf_shares", formatPercentShare(pre).text, first.subset, formatPercentShare(train).text, last.subset));
  }
  if (compare(last.seconds_per_million_events, first.seconds_per_million_events) === "lower") {
    body.push(t("e5_kf_per_million", formatSeconds(first.seconds_per_million_events).text,
      formatSeconds(last.seconds_per_million_events).text));
  }
  return { headline, body: body.length ? body.join(" ") : t("MISSING"), caveat: t("e5_kf_caveat") };
}

// ---------------------------------------------------------------- Dataset

/** "Almost every event is a view" needs the view share at or above this percentage, raw and cleaned. */
export const ALMOST_ALL_PCT = 90;

export function datasetFindings(overview) {
  const subsets = sortBy(overview?.subsets ?? [], "subset");
  const smallest = subsets[0], full = subsets.find((row) => row.subset === 100) ?? subsets.at(-1);
  const view = (overview?.event_mix_before_after ?? []).find((row) => row.event_type === "view");
  const findings = [];
  if (view && has(view.raw_week_pct) && has(view.clean_100_pct)) {
    findings.push({
      key: "d1",
      headline: view.raw_week_pct >= ALMOST_ALL_PCT && view.clean_100_pct >= ALMOST_ALL_PCT ? t("d1_kf_headline") : null,
      body: t("d1_kf_body", formatPercent(view.raw_week_pct).text, formatPercent(view.clean_100_pct).text),
    });
  }
  if (full && has(full.single_interaction_session_pct)) {
    findings.push({
      key: "d2",
      headline: full.single_interaction_session_pct > 0 ? t("d2_kf_headline") : null,
      body: t("d2_kf_body", formatPercent(full.single_interaction_session_pct).text),
    });
  }
  if (smallest && full && smallest !== full && has(smallest.catalog_items) && has(full.catalog_items)) {
    const coverage = smallest.catalog_coverage_of_100_pct;
    // "Still has many products": the subset's product share is larger than its session share.
    const share = has(coverage) ? coverage : (100 * smallest.catalog_items) / full.catalog_items;
    const manyProducts = has(smallest.actual_raw_session_pct) && share > smallest.actual_raw_session_pct;
    findings.push({
      key: "d3",
      headline: manyProducts ? t("d3_kf_headline", smallest.subset, formatCount(smallest.catalog_items).text, formatCount(full.catalog_items).text) : null,
      body: t("d3_kf_body"),
    });
  }
  return findings;
}
