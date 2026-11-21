import { t } from "./i18n.js";
import { INVALID_PRODUCT_ID } from "./data.js";

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const titleCase = (value) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

function topCategory(product) {
  return product?.category_code?.split(".")[0] || null;
}

export function productDisplay(id, products) {
  if (id === INVALID_PRODUCT_ID) return { name: t("invalid_id") };

  const product = products?.get(id);
  const category = product?.category_code?.split(".").map(titleCase) ?? [];
  const leaf = category.at(-1);
  const brand = product?.brand && titleCase(product.brand);
  const name = brand && leaf ? `${brand} ${leaf}`
    : leaf ? t("0_brand_unknown", leaf)
      : brand ? t("0_category_unknown", brand) : t("product_0", id);

  return {
    name,
    breadcrumb: category.join(" › "),
    price: product?.price == null ? t("price_unavailable") : usd.format(product.price),
  };
}

export function categoryHighlights(prefix, prefixCatalog, recommendations, products) {
  const categoryOf = (id) => topCategory(products?.get(id));
  const historyCategories = new Set();
  for (const id of prefix ?? []) {
    const category = prefixCatalog?.has(id) && categoryOf(id);
    if (category) historyCategories.add(category);
  }

  const matchingIds = new Set();
  let categorizedCount = 0;
  let matchingCount = 0;
  for (const { product_id: id } of recommendations ?? []) {
    const category = categoryOf(id);
    if (!category) continue;
    categorizedCount++;
    if (historyCategories.has(category)) {
      matchingIds.add(id);
      matchingCount++;
    }
  }
  const summary = historyCategories.size && categorizedCount
    ? t("history_categories_0_1_2_categorized", [...historyCategories].join(", "), matchingCount, categorizedCount)
    : null;
  return { matchingIds, summary };
}
