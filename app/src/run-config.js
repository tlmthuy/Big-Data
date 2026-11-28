import { t } from "./i18n.js";
import { formatValue } from "./data.js";

const CONFIG_FIELDS = [
  ["batch_size", "experiment_train_batch", "batch_size", "batch_size"],
  ["eval_batch_size", "experiment_eval_batch", "eval_batch_size", "eval_batch_size"],
  ["epochs", "experiment_epochs", "epochs", "epochs"],
  ["sequence_length", "experiment_sequence_length", "sequence_length", "sequence_length"],
  ["seed", "experiment_seed", "seed", "seed"],
  ["learning_rate", "experiment_learning_rate", "learning_rate", "learning_rate"],
  ["split", "experiment_split", "split", "split"],
  ["train_through", "experiment_train_through", "train_partitions", "train_through"],
  ["subset", "experiment_subset", "subset", "subset"],
  ["device", "experiment_device", "resource_config.device", "device"],
];

const NEURAL_FIELDS = new Set(["batch_size", "eval_batch_size", "epochs", "sequence_length", "seed", "learning_rate", "device"]);

function isPlainComparable(value) {
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value !== "string" || /D|\.\./.test(value)) return false;
  return /^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$/.test(value) || /^[A-Za-z][A-Za-z -]*$/.test(value);
}

function readPath(object, path) {
  return path.split(".").reduce((value, key) => value?.[key], object);
}

/**
 * Kind of run, which decides which fields exist for it:
 * "preprocessing" (E4: no model, no training config), "baseline" (Popularity: no neural settings),
 * "training" (GRU/XLNet). A field that does not exist for the kind is "Not applicable";
 * "Not available yet" is only for an expected value that was not delivered.
 */
export function runKind(config) {
  if (config?.e4_config) return "preprocessing";
  const model = String(config?.planned?.model ?? config?.actual?.model ?? "").toLowerCase();
  return model === "popularity" ? "baseline" : "training";
}

const NOT_APPLICABLE = {
  preprocessing: () => true,
  baseline: (key) => NEURAL_FIELDS.has(key),
  training: () => false,
};

export function isApplicableField(config, key) {
  return !NOT_APPLICABLE[runKind(config)](key);
}

export function configurationRows(config) {
  const planned = config?.planned;
  const actual = config?.actual;
  return CONFIG_FIELDS.map(([key, labelKey, plannedPath, actualPath]) => {
    const na = !isApplicableField(config, key);
    const plannedValue = na ? undefined : readPath(planned, plannedPath);
    const actualValue = na || key === "sequence_length" ? undefined : key === "split"
      ? actual?.split ?? actual?.eval_split
      : readPath(actual, actualPath);
    const plannedExists = plannedValue !== null && plannedValue !== undefined;
    const actualExists = actualValue !== null && actualValue !== undefined;
    return {
      key,
      label: t(labelKey),
      planned: na ? t("not_applicable") : plannedExists ? formatValue(plannedValue) : t("MISSING"),
      actual: na ? t("not_applicable") : key === "sequence_length" ? t("MISSING") : actualExists ? formatValue(actualValue) : t("MISSING"),
      plannedRaw: plannedExists ? String(plannedValue) : undefined,
      actualRaw: actualExists ? String(actualValue) : undefined,
      differs: !na && plannedExists && actualExists
        && isPlainComparable(plannedValue) && isPlainComparable(actualValue)
        && String(plannedValue) !== String(actualValue),
    };
  });
}

export function runtimeRows(config) {
  const runtime = config?.runtime ?? {};
  const packages = runtime.packages ?? {};
  const kind = runKind(config);
  // Training runtime fields do not exist for a preprocessing run; GPU/CUDA/torch do not apply to the baseline.
  const applicable = (value) => (kind !== "training" ? t("not_applicable") : value ?? t("MISSING"));
  return [
    { key: "gpu", label: t("runtime_gpu"), value: applicable(runtime.gpu) },
    { key: "cuda", label: t("runtime_cuda"), value: applicable(runtime.cuda) },
    { key: "python", label: t("runtime_python"), value: kind === "preprocessing" ? t("not_applicable") : runtime.python ?? t("MISSING") },
    { key: "torch", label: t("runtime_torch"), value: applicable(packages.torch) },
    { key: "transformers4rec", label: t("runtime_transformers4rec"), value: applicable(packages.transformers4rec) },
  ];
}
