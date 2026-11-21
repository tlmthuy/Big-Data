import { setLanguage, t } from "../src/i18n.js";
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { INVALID_PRODUCT_ID, loadJson, normalizeDemo, normalizeProductInfo } from "../src/data.js";
import { categoryHighlights, productDisplay } from "../src/product.js";

const json = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const smartphone = { brand: "samsung", category_code: "electronics.smartphone", price: 130.76 };
const display = (metadata) => productDisplay("p3", new Map([["p3", metadata]]));

setLanguage(process.env.TV4_TEST_LANGUAGE);

test("display name handles all combinations of brand and category", () => {
  assert.equal(display(smartphone).name, "Samsung Smartphone");
  assert.equal(display({ ...smartphone, brand: null }).name, t("0_brand_unknown", "Smartphone"));
  assert.equal(display({ ...smartphone, category_code: null }).name, t("0_category_unknown", "Samsung"));
  assert.equal(display({}).name, t("product_0", "p3"));
  assert.equal(productDisplay(INVALID_PRODUCT_ID).name, t("invalid_id"));
});

test("category breadcrumb is readable", () => {
  assert.equal(display(smartphone).breadcrumb, "Electronics › Smartphone");
});

test("USD price displays two decimals, including true zero", () => {
  assert.equal(display(smartphone).price, "$130.76");
  assert.equal(display({ price: 0 }).price, "$0.00");
  assert.equal(display({ price: null }).price, t("price_unavailable"));
});

test("missing file or entry falls back to the original product ID", async () => {
  const failed = await loadJson("product-info.json", async () => ({ ok: false, status: 404 }));
  assert.ok(failed.error);
  const missingFile = normalizeProductInfo(failed.data);
  assert.equal(productDisplay("p3", missingFile.products).name, t("product_0", "p3"));
  const missingEntry = normalizeProductInfo({ products: { p4: smartphone } });
  assert.equal(productDisplay("p3", missingEntry.products).name, t("product_0", "p3"));
});

test("category highlight counts only delivered categories and skips missing ones", () => {
  const { products } = normalizeProductInfo({
    products: { p3: smartphone, p4: { category_code: "electronics.tv" }, p5: {}, p6: { category_code: "furniture.chair" } },
  });
  const prefix = ["p3", "p6", INVALID_PRODUCT_ID];
  const catalog = new Set(["p3", "p4", "p5"]);
  const recommendations = ["p4", "p5", "p6", "p7"].map((product_id) => ({ product_id }));
  const { matchingIds, summary } = categoryHighlights(prefix, catalog, recommendations, products);
  assert.deepEqual([...matchingIds], ["p4"]);
  assert.equal(summary, t("history_categories_0_1_2_categorized", "electronics", 1, 2));
  assert.equal(categoryHighlights(prefix, catalog, [recommendations[1]], products).summary, null);
});

test("shipped metadata is flagged toy and uses only toy catalog IDs", () => {
  const raw = json("../public/product-info.json");
  const info = normalizeProductInfo(raw);
  const toyCatalog = normalizeDemo(json("../public/demo-data.json")).groups
    .flatMap((group) => group.runs).find((run) => run.data_kind === "toy").catalogSet;
  assert.equal(info.dataKind, "toy");
  assert.equal(raw.data_kind, "toy");
  assert.equal(raw.source, "toy sample metadata for UI testing, not from dataset");
  assert.deepEqual([...info.products.keys()], Array.from({ length: 23 }, (_, i) => `p${i + 3}`));
  for (const id of info.products.keys()) assert.ok(toyCatalog.has(id), id);
});
