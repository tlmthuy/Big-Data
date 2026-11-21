import { t } from "./i18n.js";
// Loading and validation for the two JSON files in public/.
// Pure functions (no React) so they can be tested with `node --test`.


/** Known models of the project, in display order. Used only to list models that have no output yet. */
export const PROJECT_MODELS = ["Popularity", "GRU", "XLNet"];

export function modelKey(name) {
  return typeof name === "string" ? name.trim().toLowerCase() : "";
}

export function modelLabel(name) {
  const found = PROJECT_MODELS.find((m) => modelKey(m) === modelKey(name));
  return found ?? (typeof name === "string" && name.trim() ? name : t("not_available_yet"));
}

const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isId = (v) => typeof v === "string" && v.trim() !== "";
const isIdList = (v) => Array.isArray(v) && v.every(isId);

/** fetch + parse with readable errors. Returns { data } or { error }. */
export async function loadJson(url, fetchImpl = fetch) {
  let response;
  try {
    response = await fetchImpl(url, { cache: "no-store" });
    if (!response.ok) return { error: t("could_not_load_0_http_1", url, response.status) };
  } catch (cause) {
    return { error: t("could_not_load_0_1", url, cause.message) };
  }
  let text;
  try {
    text = await response.text();
  } catch (cause) {
    return { error: t("could_not_read_0_1", url, cause.message) };
  }
  if (!text.trim()) return { error: t("0_is_empty", url) };
  try {
    return { data: JSON.parse(text) };
  } catch (cause) {
    return { error: t("0_is_invalid_json_1", url, cause.message) };
  }
}

export function normalizeProductInfo(raw) {
  if (!isObject(raw) || !isObject(raw.products)) return {};
  const products = new Map();
  for (const [id, info] of Object.entries(raw.products)) {
    if (!isObject(info)) continue;
    products.set(id, {
      brand: isId(info.brand) ? info.brand.trim() : null,
      category_code: isId(info.category_code) ? info.category_code.trim().toLowerCase() : null,
      price: Number.isFinite(info.price) ? info.price : null,
    });
  }
  return { products, dataKind: raw.data_kind };
}

// ---------------------------------------------------------------- Part A

export const INVALID_PRODUCT_ID = Symbol("invalid product ID");

function isReservedId(value) {
  return typeof value === "string" && /^(?:[<\[\s_]*)(?:pad(?:ding)?|null|oov|mask)(?:[>\]\s_]*)$/i.test(value);
}

function normalizeSession(raw, catalogSet, issues) {
  const id = raw.user_session;
  const problems = [];
  const isCatalogProduct = (value) => catalogSet?.has(value) === true && !isReservedId(value);

  function contextId(value, field) {
    if (isCatalogProduct(value)) return value;
    if (!isId(value) || isReservedId(value) || /^[+-]?\d+$/.test(value.trim())) {
      problems.push(t("0_invalid_product_id", field));
      return INVALID_PRODUCT_ID;
    }
    problems.push(t("0_product_id_is_absent_from", field));
    return value;
  }

  const prefix = Array.isArray(raw.prefix) ? raw.prefix.map((value) => contextId(value, t("history_2"))) : null;
  if (!prefix) problems.push(t("missing_or_invalid_prefix"));
  const target = Object.hasOwn(raw, "target") ? contextId(raw.target, t("actual_item")) : null;
  if (target === null) problems.push(t("missing_target"));

  let recommendations = null;
  if (Array.isArray(raw.recommendations)) {
    const rows = raw.recommendations.filter((r) => isObject(r) && Number.isInteger(r.rank));
    if (rows.length !== raw.recommendations.length) problems.push(t("skipped_malformed_entries_in_recommendations"));
    recommendations = rows.map((r) => ({
      rank: r.rank,
      product_id: r.product_id,
      score: Number.isFinite(r.score) ? r.score : null,
    }));
  } else if (Array.isArray(raw.top20)) {
    // Artifact position gives rank. Filtering preserves the surviving ranks.
    recommendations = raw.top20.map((product_id, index) => ({ rank: index + 1, product_id, score: null }));
  } else {
    problems.push(t("missing_or_invalid_top20"));
  }

  if (recommendations) {
    const kept = recommendations.filter((r) => isCatalogProduct(r.product_id));
    const hidden = recommendations.length - kept.length;
    recommendations = catalogSet ? kept : null;
    if (hidden) problems.push(t("hid_0_technical_or_out_of", hidden));
  }

  let targetRank = null;
  if (recommendations && target && target !== INVALID_PRODUCT_ID) {
    const hit = recommendations.find((r) => r.product_id === target);
    targetRank = hit ? hit.rank : null;
    if (raw.target_rank !== undefined && raw.target_rank !== targetRank) {
      problems.push(t("target_rank_mismatch", raw.target_rank, targetRank ?? t("outside_top_20")));
    }
  }

  if (problems.length) issues.push(`Session ${id}: ${[...new Set(problems)].join("; ")}`);
  const userId = isId(raw.user_id) || Number.isSafeInteger(raw.user_id) ? String(raw.user_id) : null;
  return { user_session: id, userId, prefix, target, recommendations, targetRank, problems };
}

function normalizeRun(raw, index, issues) {
  const label = isId(raw?.run_id) ? raw.run_id : `run #${index + 1}`;
  if (!isObject(raw)) {
    issues.push(t("0_skipped_non_object_record", label));
    return null;
  }
  if (!isId(raw.model)) {
    issues.push(t("0_skipped_record_without_model", label));
    return null;
  }
  if (!Array.isArray(raw.sessions)) {
    issues.push(t("0_skipped_record_without_a_sessions", label));
    return null;
  }
  const catalog = isIdList(raw.catalog) && raw.catalog.length ? raw.catalog : null;
  if (!catalog) issues.push(t("0_catalog_missing_so_product_ids", label));
  const catalogSet = catalog ? new Set(catalog) : null;

  const seen = new Set();
  const sessions = [];
  for (const s of raw.sessions) {
    if (!isObject(s) || !isId(s.user_session)) {
      issues.push(t("0_skipped_session_without_user_session", label));
      continue;
    }
    if (seen.has(s.user_session)) {
      issues.push(t("0_duplicate_session_1_kept_the", label, s.user_session));
      continue;
    }
    seen.add(s.user_session);
    sessions.push(normalizeSession(s, catalogSet, issues));
  }
  if (!sessions.length) issues.push(t("0_no_valid_sessions", label));

  const provenance = isObject(raw.provenance) ? raw.provenance : {};
  return {
    model: raw.model,
    modelKey: modelKey(raw.model),
    run_id: isId(raw.run_id) ? raw.run_id : null,
    label,
    subset: raw.subset ?? null,
    split: raw.split ?? null,
    data_kind: raw.data_kind ?? null,
    catalog_sha256: raw.catalog_sha256 ?? null,
    catalogSize: catalog ? catalog.length : null,
    catalogSet,
    evalPartition: provenance.eval_day ?? null,
    sample: isObject(provenance.sample) ? provenance.sample : null,
    experiment: provenance.experiment ?? null,
    scoreAvailable: sessions.some((s) => s.recommendations?.some((r) => r.score !== null)),
    sessions,
  };
}

function groupKey(run) {
  const ids = run.sessions.map((s) => s.user_session).sort().join(",");
  return [run.subset, run.split, run.evalPartition, run.catalog_sha256, ids].join("|");
}

/**
 * Normalize demo-data.json. Accepts the v2 shape { runs: [...] } and the
 * legacy single-run shape { model, sessions, ... }.
 * Returns { groups, issues, fatal }.
 */
export function normalizeDemo(raw) {
  const issues = [];
  if (!isObject(raw)) return { groups: [], issues, fatal: t("the_data_file_is_not_a") };
  const rawRuns = Array.isArray(raw.runs) ? raw.runs : Array.isArray(raw.sessions) ? [raw] : null;
  if (!rawRuns) return { groups: [], issues, fatal: t("cannot_find_runs_or_sessions") };

  const runs = rawRuns.map((r, i) => normalizeRun(r, i, issues)).filter((r) => r && r.sessions.length);
  if (!runs.length) return { groups: [], issues, fatal: t("no_run_contains_valid_sessions") };

  const groups = new Map();
  for (const run of runs) {
    const key = groupKey(run);
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        subset: run.subset,
        split: run.split,
        evalPartition: run.evalPartition,
        catalogSize: run.catalogSize,
        sessionIds: run.sessions.map((s) => s.user_session),
        runs: [],
      });
    }
    groups.get(key).runs.push(run);
  }
  return { groups: [...groups.values()], issues, fatal: null };
}

export function usersBySession(group) {
  const users = new Map();
  for (const run of group?.runs ?? []) {
    for (const session of run.sessions) {
      if (session.userId && !users.has(session.user_session)) {
        users.set(session.user_session, session.userId);
      }
    }
  }
  return users;
}

/** History and target for a session, taken from the first run in the group that has them. */
export function sessionContext(group, sessionId) {
  let prefix = null;
  let target = null;
  let prefixCatalog = null;
  let targetCatalog = null;
  for (const run of group.runs) {
    const s = run.sessions.find((x) => x.user_session === sessionId);
    if (!s) continue;
    if (prefix === null && s.prefix !== null) {
      prefix = s.prefix;
      prefixCatalog = run.catalogSet;
    }
    if (target === null && s.target !== null) {
      target = s.target;
      targetCatalog = run.catalogSet;
    }
  }
  return { prefix, target, prefixCatalog, targetCatalog };
}

// ---------------------------------------------------------------- Part B

export const EXPERIMENTS = ["E1", "E2", "E3", "E4", "E5"];

export function normalizeResults(raw) {
  const issues = [];
  if (!isObject(raw)) return { runs: [], meta: {}, issues, fatal: t("the_results_file_is_not_a") };
  if (!Array.isArray(raw.runs)) return { runs: [], meta: {}, issues, fatal: t("cannot_find_the_runs_array") };
  const runs = [];
  raw.runs.forEach((r, i) => {
    if (!isObject(r) || !isId(r.run_id) || !isId(r.experiment)) {
      issues.push(t("record_0_skipped_because_run_id", i + 1));
      return;
    }
    runs.push({
      ...r,
      model: r.model ?? null,
      kind: r.kind ?? (r.model ? "model" : "io"),
      matrix_run_id: r.matrix_run_id ?? r.run_id,
      planned: isObject(r.planned) ? r.planned : {},
      actual: isObject(r.actual) ? r.actual : {},
      environment: isObject(r.environment) ? r.environment : {},
      metrics: isObject(r.metrics) ? r.metrics : {},
      sources: isObject(r.sources) ? r.sources : {},
    });
  });
  return {
    runs,
    meta: {
      environment_baseline: raw.environment_baseline ?? null,
      package_id: raw.package_id ?? null,
      confirmed_by_tv2: raw.confirmed_by_tv2 === true,
      team_commit: raw.team_commit ?? null,
    },
    issues,
    fatal: null,
  };
}

/** Official = not toy. Toy runs are reference only and never mixed with official ones. */
export function splitByKind(runs, experiment) {
  const inExp = runs.filter((r) => r.experiment === experiment);
  return {
    official: inExp.filter((r) => r.data_kind !== "toy"),
    toy: inExp.filter((r) => r.data_kind === "toy"),
  };
}

// ---------------------------------------------------------------- formatting

/** Format a delivered value or a localized placeholder. */
export function formatValue(value) {
  if (value === null || value === undefined || value === "") return t("not_available_yet");
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return String(value);
    if (Number.isInteger(value)) return value.toLocaleString("en-US");
    return Number(value.toPrecision(4)).toLocaleString("en-US", { maximumFractionDigits: 10 });
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.length ? value.map(formatValue).join(", ") : t("not_available_yet");
  if (isObject(value)) {
    const entries = Object.entries(value);
    return entries.length ? entries.map(([k, v]) => `${k}: ${formatValue(v)}`).join(" · ") : t("not_available_yet");
  }
  return String(value);
}

/** Full-precision text for a tooltip. */
export function exactValue(value) {
  if (value === null || value === undefined) return t("not_available_yet");
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

// Planned/actual fields that do not apply to a model, per contract section 2.
const POPULARITY_NA = new Set([
  "train_batch_size", "eval_batch_size", "epochs", "seed", "learning_rate", "device",
  "peak_cuda_reserved_bytes",
]);

export function isApplicable(run, field) {
  if (modelKey(run.model) === "popularity") return !POPULARITY_NA.has(field);
  return true;
}

export function displayCell(run, field, value) {
  if ((value === null || value === undefined) && !isApplicable(run, field)) return t("not_applicable");
  return formatValue(value);
}

// Fields where planned and actual can be compared directly.
const COMPARABLE = new Set([
  "train_batch_size", "eval_batch_size", "epochs", "sequence_length", "seed",
  "learning_rate", "subset", "split", "device", "input_format",
]);

/** "same" | "different" | null (not comparable or a side is missing). */
export function compareConfig(field, planned, actual) {
  if (!COMPARABLE.has(field)) return null;
  if (planned === null || planned === undefined || actual === null || actual === undefined) return null;
  return String(planned).toLowerCase() === String(actual).toLowerCase() ? "same" : "different";
}
