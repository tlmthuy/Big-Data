import React from "react";
import { INVALID_PRODUCT_ID } from "./data.js";
import { productCardDisplay } from "./product.js";

/** Original product ID (mono), then "brand · category › path", then "Price 308.86"; missing lines are omitted. */
export function ProductCard({ id, products }) {
  const { id: originalId, invalid, meta, price, priceRaw } = productCardDisplay(id, products);
  if (id === INVALID_PRODUCT_ID) return <div className="product-card missing">{invalid}</div>;

  return (
    <div className="product-card">
      <div>
        <span className="product-id">{originalId}</span>
        {meta && <small className="product-meta">{meta}</small>}
        {price && <small className="product-price" title={priceRaw}>{price}</small>}
      </div>
    </div>
  );
}
