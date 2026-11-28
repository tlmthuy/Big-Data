// Key finding body sentences for E3 and E4. Every comparison word is chosen here by comparing the delivered
// JSON values; equal or missing values give a neutral sentence that only lists the values.
// All numbers are formatted by src/format.js; templates live in src/i18n.js (no numeric literals there).
import { messages, t } from "./i18n.js";
import { byteDisplayUnit, formatBytes, formatCount, formatRatio, formatSeconds, isMissing } from "./format.js";

/** "higher" | "lower" | "equal" | null (missing) for a compared with b. */
export function compare(a, b) {
  if (isMissing(a) || isMissing(b)) return null;
  if (a === b) return "equal";
  return a > b ? "higher" : "lower";
}

/** Two values are "similar" when they differ by less than this share of the larger one. */
export const SIMILAR_SHARE = 0.1;
/** Reading counts as "a small part" of preprocessing when it is below this share of it. */
export const SMALL_PART_SHARE = 0.1;

export function isSimilar(a, b, share = SIMILAR_SHARE) {
  if (isMissing(a) || isMissing(b)) return false;
  const larger = Math.max(Math.abs(a), Math.abs(b));
  return larger === 0 ? true : Math.abs(a - b) / larger < share;
}

export function isSmallPart(part, whole, share = SMALL_PART_SHARE) {
  if (isMissing(part) || isMissing(whole) || whole <= 0) return false;
  return part / whole < share;
}

const decided = (...directions) => directions.every((direction) => direction === "higher" || direction === "lower");
/** "drops/rises from a to b" (VI "giảm từ a xuống b" / "tăng từ a lên b"); `down` names the falling verb. */
const change = (direction, from, to, down = "chg_drop") => t(direction === "lower" ? down : "chg_rise", from, to);

const gpuBytes = (run) => (run?.sampled_gpu_status === "unavailable" ? null : run?.sampled_gpu_process_bytes);

/** E3 rows sorted by train batch: [smaller, larger], or null. */
export function e3Pair(results) {
  const runs = [...(results?.tables?.E3 ?? [])].sort((a, b) => a.train_batch_size - b.train_batch_size);
  return runs.length < 2 ? null : [runs[0], runs.at(-1)];
}

/** E3: how the larger train batch (b2) changes training time, GPU memory and validation Recall@20 from b1. */
export function e3Takeaway(results) {
  const pair = e3Pair(results);
  if (!pair) return t("MISSING");
  const [small, large] = pair;
  const unit = byteDisplayUnit([gpuBytes(small), gpuBytes(large)]);
  const time = (run) => formatSeconds(run.train_seconds_including_sequence_io).text;
  const gpu = (run) => formatBytes(gpuBytes(run), unit).text;
  const recall = (run) => formatRatio(run["Recall@20"]).text;
  const dt = compare(large.train_seconds_including_sequence_io, small.train_seconds_including_sequence_io);
  const dg = compare(gpuBytes(large), gpuBytes(small));
  const dr = compare(large["Recall@20"], small["Recall@20"]);
  if (!decided(dt, dg, dr)) {
    return t("e3_takeaway_neutral", large.train_batch_size, time(large), gpu(large), recall(large),
      small.train_batch_size, time(small), gpu(small), recall(small));
  }
  return t("e3_kf_body", change(dt, time(small), time(large)), change(dg, gpu(small), gpu(large)),
    change(dr, recall(small), recall(large), "chg_fall"));
}

/** Hardware named in the limitation note, read from the package environment; null when absent. */
/**
 * Hardware phrase for the E3 limitation note, built from the package environment fields:
 * cloud "VM AWS Ubuntu 22.04" -> provider "AWS", OS "Ubuntu 22.04"; gpu "Tesla T4 (compute …)" -> "Tesla T4".
 * EN "one AWS VM (Ubuntu 22.04) with one Tesla T4". A missing field drops its part; nothing -> null.
 */
export function e3Hardware(results) {
  const vm = results?.vm_environment ?? {};
  const cloud = typeof vm.cloud === "string" ? vm.cloud.trim() : "";
  const match = cloud.match(/^VM\s+(\S+)(?:\s+(.+))?$/i);
  const provider = match?.[1] ?? null;
  const os = match?.[2]?.trim() || null;
  const gpu = typeof vm.gpu === "string" && vm.gpu.trim() ? vm.gpu.split(" (")[0].trim() : null;
  const machine = provider && os ? t("e3_hw_vm_os", provider, os) : provider ? t("e3_hw_vm", provider) : null;
  const card = gpu ? t("e3_hw_gpu", gpu) : null;
  if (machine && card) return t("e3_hw_both", machine, card);
  return machine ?? card ?? null;
}

export function e3Limitation(results) {
  const hardware = e3Hardware(results);
  return hardware ? t("e3_limit", hardware) : t("e3_limit_no_hardware");
}

/** Display label of a storage format ("csv" -> "CSV", "parquet" -> "Parquet"). */
export function formatLabel(format) {
  const key = `format_${String(format ?? "").toLowerCase()}`;
  return Object.hasOwn(messages.en, key) ? t(key) : String(format ?? t("MISSING")).toUpperCase();
}

/** E4 rows ordered [baseline, subject]: CSV first and Parquet as the sentence subject when present. */
export function e4Pair(results) {
  const runs = results?.tables?.E4 ?? [];
  const csv = runs.find((run) => String(run.format).toLowerCase() === "csv") ?? runs[0];
  const parquet = runs.find((run) => String(run.format).toLowerCase() === "parquet") ?? runs.find((run) => run !== csv);
  return csv && parquet ? [csv, parquet] : null;
}

/**
 * E4: CSV (baseline) to Parquet (subject). "File size goes from … and read time from …" only when Parquet is
 * smaller and reads faster; otherwise a neutral sentence that lists the values. "Total preprocessing only
 * drops from …" when it is lower but within 10%, with "because reading is a small part of it" only if each
 * read is < 10% of its own preprocessing time; any other case lists the two values.
 */
export function e4Takeaway(results) {
  const pair = e4Pair(results);
  if (!pair) return t("MISSING");
  const [base, subject] = pair;
  const size = (run) => formatBytes(run.bytes, "MiB").text;
  const read = (run) => formatSeconds(run.read_seconds).text;
  const prep = (run) => formatSeconds(run.preprocessing_wall_seconds_including_read).text;
  const ds = compare(subject.bytes, base.bytes);
  const dr = compare(subject.read_seconds, base.read_seconds);
  if (ds !== "lower" || dr !== "lower") {
    return t("e4_takeaway_neutral", formatLabel(subject.format), size(subject), read(subject), prep(subject),
      formatLabel(base.format), size(base), read(base), prep(base));
  }
  const pb = base.preprocessing_wall_seconds_including_read, ps = subject.preprocessing_wall_seconds_including_read;
  const head = t("e4_kf_body", size(base), size(subject), read(base), read(subject));
  if (compare(ps, pb) === "lower" && isSimilar(ps, pb)) {
    const because = isSmallPart(subject.read_seconds, ps) && isSmallPart(base.read_seconds, pb) ? t("e4_because") : "";
    return `${head} ${t("e4_kf_prep_only", prep(base), prep(subject), because)}`;
  }
  return `${head} ${t("e4_kf_prep", prep(base), prep(subject))}`;
}

/**
 * E4 fairness line, shown only when the delivered configuration backs every part of it: identical
 * fingerprints (fingerprint_match), equal event counts, the same program, and the same all-string
 * schema policy for both runs. Returns the text or null.
 */
export function e4Fairness(results) {
  const pair = e4Pair(results);
  if (!pair) return null;
  const configs = pair.map((run) => results?.configs?.[run.run_id]?.e4_config ?? null);
  if (configs.some((config) => !config)) return null;
  const [a, b] = configs;
  const allStrings = (policy) => typeof policy === "string" && /^all nine fields strings/i.test(policy);
  const backed = a.fingerprint_match === true && b.fingerprint_match === true
    && !isMissing(a.n_events) && a.n_events === b.n_events
    && typeof a.program === "string" && a.program === b.program
    && a.schema_policy === b.schema_policy && allStrings(a.schema_policy);
  return backed ? t("e4_fairness", formatCount(a.n_events).text) : null;
}
