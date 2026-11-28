import { t } from "./i18n.js";
import { INVALID_PRODUCT_ID } from "./data.js";
import { formatPrice, isMissing } from "./format.js";

/**
 * Product card lines from public/product-info.json (brand, category_code, last weekly price).
 * The dataset has no product names, so none is built: line 1 is the original ID, line 2 the brand as in
 * the data and the category path ("electronics › camera › video"), line 3 "Price 308.86" (no currency:
 * the dataset does not state one). Missing parts are omitted; with no entry only the ID is shown.
 */
export function productCardDisplay(id, products) {
  if (id === INVALID_PRODUCT_ID) return { id: null, invalid: t("invalid_id"), meta: null, price: null, priceRaw: null };
  const product = products?.get(id);
  const category = product?.category_code ? product.category_code.split(".").filter(Boolean).join(" › ") : null;
  const meta = [product?.brand || null, category].filter(Boolean).join(" · ") || null;
  const hasPrice = product && !isMissing(product.price);
  return {
    id,
    invalid: null,
    meta,
    price: hasPrice ? t("product_price", formatPrice(product.price).text) : null,
    priceRaw: hasPrice ? String(product.price) : null,
  };
}
