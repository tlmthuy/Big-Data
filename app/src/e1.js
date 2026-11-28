import { t } from "./i18n.js";
import { byteDisplayUnit, formatBytes, formatCount, formatMsPerSession, formatNumberOnly, formatRatio, formatSeconds } from "./format.js";
import { modelLabel } from "./data.js";

const FIELDS = [
  ["Recall@20", "e1_recall_20", formatRatio],
  ["NDCG@20", "e1_ndcg_20", formatRatio],
  ["train_seconds_including_sequence_io", "e1_train_time_s", formatSeconds],
  ["final_evaluation_seconds", "e1_final_evaluation_s", formatSeconds],
  ["eval_ms_per_session", "e1_evaluation_time_ms_session", formatMsPerSession],
  ["process_wall_seconds", "e1_process_wall_time_s", formatSeconds],
  ["sampled_rss_bytes_descriptive_only", "e1_sampled_rss_descriptive", formatBytes],
  ["sampled_gpu_process_bytes", "e1_sampled_gpu_process_memory", formatBytes],
];

export function buildE1View(results) {
  const runs = results?.tables?.E1 ?? [];
  const models = ["Popularity", "GRU", "XLNet"].map((label) => ({
    label,
    run: runs.find((run) => modelLabel(run.model) === label) ?? null,
  }));
  const firstRun = models.find(({ run }) => run)?.run;
  const config = firstRun ? results.configs?.[firstRun.run_id] : null;
  const partition = config?.split_counts?.filter((item) => item.split === firstRun?.split).at(-1)?.day_index;
  const byteFields = new Set(["sampled_rss_bytes_descriptive_only", "sampled_gpu_process_bytes"]);
  return {
    models,
    context: firstRun ? {
      subset: firstRun.subset,
      split: firstRun.split,
      partition,
      sessions: firstRun.n_sessions,
    } : null,
    rows: FIELDS.map(([field, labelKey, formatter]) => {
      const rowUnit = byteFields.has(field) ? byteDisplayUnit(models.map(({ run }) => run?.[field])) : undefined;
      const label = `${t(labelKey)}${rowUnit ? ` (${rowUnit})` : ""}`;
      return {
        field,
        label,
        cells: models.map(({ run }) => {
        const raw = run?.[field];
        if (field === "sampled_gpu_process_bytes" && run?.sampled_gpu_status === "unavailable") {
          return { text: t("not_measured"), raw: raw === null || raw === undefined ? "null" : String(raw) };
        }
        return formatNumberOnly(formatter, raw, rowUnit);
        }),
      };
    }),
    notes: [
      { label: t("e1_inference_protocol"), dictionaryKey: "inference_protocol" },
      { label: t("e1_training_time_scope"), dictionaryKey: "train_seconds_including_sequence_io" },
      { label: t("e1_sampled_rss_scope"), dictionaryKey: "sampled_rss_bytes_descriptive_only" },
      { label: t("e1_sampled_gpu_scope"), dictionaryKey: "sampled_gpu_process_bytes" },
    ],
  };
}

export function formatE1Context(context) {
  if (!context) return t("MISSING");
  const partition = context.partition == null ? t("MISSING") : formatCount(context.partition).text;
  return t("e1_context", context.subset, context.split, partition, formatCount(context.sessions).text);
}
