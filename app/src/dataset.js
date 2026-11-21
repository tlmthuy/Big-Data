import { t } from "./i18n.js";
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const count = (value) => Number.isSafeInteger(value) && value >= 0;

export function normalizeDataset(raw) {
  if (!object(raw) || raw.schema !== "tv4-dataset-overview/v1" ||
      !object(raw.raw_month) || !Array.isArray(raw.subsets) ||
      !raw.subsets.every((row) => object(row) && count(row.subset))) {
    return { fatal: t("invalid_dataset_overview_json") };
  }
  return { overview: raw };
}

export function histogramBuckets(histogram) {
  const limit = 20;
  if (!object(histogram)) return [];
  const buckets = Array.from({ length: limit }, (_, index) => {
    const length = index + 1;
    return { label: String(length), count: count(histogram[length]) ? histogram[length] : null };
  });
  const longer = Object.entries(histogram).filter(([key]) => /^\d+$/.test(key) && Number(key) > limit);
  buckets.push({
    label: `${limit + 1}+`,
    count: longer.length && longer.every(([, value]) => count(value))
      ? longer.reduce((total, [, value]) => total + value, 0) : null,
  });
  return buckets;
}
