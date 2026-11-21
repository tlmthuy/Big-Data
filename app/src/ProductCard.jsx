import { t } from "./i18n.js";
import React from "react";
import { INVALID_PRODUCT_ID } from "./data.js";
import { productDisplay } from "./product.js";

export function ProductCard({ id, products }) {
  const { name, breadcrumb, price } = productDisplay(id, products);
  if (id === INVALID_PRODUCT_ID) return <div className="product-card missing">{name}</div>;

  return (
    <div className="product-card">
      <div>
        <strong>{name}</strong>
        {breadcrumb && <small>{breadcrumb}</small>}
        <small className="product-id">{id}</small>
        <span className={price === t("price_unavailable") ? "missing" : undefined}>
          {price}
        </span>
      </div>
    </div>
  );
}
