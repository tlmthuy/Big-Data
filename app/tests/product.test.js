import { setLanguage, t } from "../src/i18n.js";
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, statSync } from "node:fs";
import { INVALID_PRODUCT_ID, loadJson, normalizeProductInfo } from "../src/data.js";
import { productCardDisplay } from "../src/product.js";

const gopro = { brand: "gopro", category_code: "electronics.camera.video", price: 308.86 };
const card = (metadata) => productCardDisplay("2300296", new Map([["2300296", metadata]]));
const productFile = new URL("../public/product-info.json", import.meta.url);
const demo = JSON.parse(readFileSync(new URL("../public/demo-data.json", import.meta.url), "utf8"));

setLanguage(process.env.TV4_TEST_LANGUAGE);

test("real product lookup is shipped, declared by demo-data.json and under 300 KB", () => {
  const info = JSON.parse(readFileSync(productFile, "utf8"));
  assert.equal(info.data_kind, "real");
  assert.equal(info.source, "official 10% cleaned week file, derived by TV4");
  assert.match(info.source_sha256, /^[0-9a-f]{64}$/);
  assert.equal(demo.provenance.product_lookup, "product-info.json");
  assert.ok(statSync(productFile).size < 300 * 1024);
  for (const entry of Object.values(info.products)) {
    assert.deepEqual(Object.keys(entry).sort(), ["brand", "category_code", "price"], "no invented name field");
  }
});

test("card: ID, brand as in the data · category path with ›, price with 2 decimals and no currency", () => {
  setLanguage("en");
  assert.deepEqual(card(gopro), { id: "2300296", invalid: null, meta: "gopro · electronics › camera › video", price: "Price 308.86", priceRaw: "308.86" });
  assert.equal(card({ ...gopro, price: 45 }).price, "Price 45.00");
  assert.equal(card({ ...gopro, price: 0 }).price, "Price 0.00", "a true zero is shown");
  setLanguage("vi");
  assert.equal(card(gopro).price, "Giá 308.86");
  setLanguage(process.env.TV4_TEST_LANGUAGE);
  assert.ok(!/\$|USD|₫/.test(card(gopro).price));
});

test("card omits missing parts silently; nothing known shows the ID only", () => {
  assert.equal(card({ ...gopro, brand: null }).meta, "electronics › camera › video");
  assert.equal(card({ ...gopro, category_code: null }).meta, "gopro");
  assert.equal(card({ ...gopro, price: null }).price, null);
  assert.deepEqual(card({ brand: null, category_code: null, price: null }), { id: "2300296", invalid: null, meta: null, price: null, priceRaw: null });
  assert.deepEqual(productCardDisplay("p3"), { id: "p3", invalid: null, meta: null, price: null, priceRaw: null });
  assert.equal(productCardDisplay(INVALID_PRODUCT_ID).invalid, t("invalid_id"));
});

test("missing file or entry falls back to the original product ID", async () => {
  const failed = await loadJson("product-info.json", async () => ({ ok: false, status: 404 }));
  assert.ok(failed.error);
  assert.equal(productCardDisplay("p3", normalizeProductInfo(failed.data).products).meta, null);
  const missingEntry = normalizeProductInfo({ products: { p4: gopro } });
  assert.deepEqual(productCardDisplay("p3", missingEntry.products), { id: "p3", invalid: null, meta: null, price: null, priceRaw: null });
});
