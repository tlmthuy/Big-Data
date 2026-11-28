import assert from "node:assert/strict";
import { test } from "node:test";
import { messages, readLanguage, setLanguage, t } from "../src/i18n.js";

test("both locales provide the same UI keys and interpolate values", () => {
  assert.deepEqual(Object.keys(messages.en).sort(), Object.keys(messages.vi).sort());
  assert.equal(readLanguage(), "en");
  setLanguage("en");
  assert.equal(t("hit_sentence", 5, 20), "Hit — the actual item is ranked 5 of 20");
  assert.equal(t("e5_x_axis_events"), "Events (count)");
  assert.equal(t("section_data_could_not_be_loaded"), "This section's data could not be loaded. Please refresh; the presenter has a backup.");
  setLanguage("vi");
  assert.equal(t("hit_sentence", 5, 20), "Trúng — sản phẩm thực tế đứng hạng 5/20");
  assert.ok(!/[✅❌]/u.test(Object.values(messages.vi).join(" ")), "no emoji in VI strings");
  assert.equal(t("e5_x_axis_events"), "Số sự kiện");
  assert.equal(t("section_data_could_not_be_loaded"), "Không thể tải dữ liệu cho mục này. Vui lòng tải lại trang; người thuyết trình đã có bản dự phòng.");
});

// Data facts (dates, subset sizes, counts) come from public/*.json, never from i18n.js. Digits may only appear
// in labels and identifiers (stripped below) or in the keys listed here: protocol constants, notation and formulas.
const ALLOWED_DIGIT_KEYS = new Set([
  "kf_source_footnote",          // source label "analysis.md, 24/11"
  "keep_up_to_20_products_per",  // protocol constant: sequences keep at most 20 items
  "glossary_top20",              // protocol constant K = 20 in the Top-20 definition
  "length_tv_vs_100", "event_tv_vs_100", "catalog_coverage_of_100_pct", "tv_distance_explanation", // "100%" reference level
  "train_used_partitions", "validation_used_partitions", // partition notation "(1 to D−1)", "(2 to D)"
  "glossary_recall", "glossary_ndcg", // formulas "1 … 0", "1/log2(r+1)"
]);
const LABELS = /\b(?:E[1-5]|TV[1-5]|Top-\d+|Recall@20|NDCG@20|5V|SHA-256|UTF-8|transformers4rec|full_evaluation_wall_v1|top20)\b|\{\d+\}/g;

test("no data literals in i18n.js: digits only in labels or in the allow-listed keys", () => {
  const offenders = [];
  for (const lang of ["en", "vi"]) {
    for (const [key, value] of Object.entries(messages[lang])) {
      if (/\d/.test(value.replace(LABELS, "")) && !ALLOWED_DIGIT_KEYS.has(key)) offenders.push(`${lang}.${key}: ${value}`);
    }
  }
  assert.deepEqual(offenders, []);
  for (const key of ALLOWED_DIGIT_KEYS) assert.ok(key in messages.en, `allow-list names a real key: ${key}`);
});
