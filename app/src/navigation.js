import { EXPERIMENTS } from "./data.js";

/**
 * Hash routes. Every view and every experiment has its own URL, so back/forward and links work:
 *   #recommendation · #dataset · #experiments · #experiments/e1 … #experiments/e5
 *   #experiments/e2/25 opens E2 with the 25% level selected (cross-links from E5 and Dataset).
 * Legacy hashes (#data, #experiments-e3) still resolve.
 */
export function routeFromHash(hash) {
  const name = decodeURIComponent(String(hash ?? "").replace(/^#/, "")).toLowerCase();
  const parts = name.split(/[/-]/);
  if (parts[0] === "experiments") {
    const experiment = EXPERIMENTS.find((id) => id.toLowerCase() === parts[1]) ?? EXPERIMENTS[0];
    const select = /^\d+$/.test(parts[2] ?? "") ? parts[2] : null;
    return { tab: "experiments", experiment, select };
  }
  if (parts[0] === "dataset" || name === "data") {
    const section = DATASET_SECTIONS.includes(name.split("/")[1]) ? name.split("/")[1] : null;
    return section ? { tab: "dataset", section } : { tab: "dataset" };
  }
  return { tab: "recommendation" };
}

export function experimentHref(id, select) {
  return `#experiments/${id.toLowerCase()}${select == null ? "" : `/${select}`}`;
}

export const VIEW_IDS = ["recommendation", "dataset", "experiments"];

/** In-page sections of the Dataset tab (#dataset/<slug>); element ids are `dataset-<slug>`. */
export const DATASET_SECTIONS = ["key-findings", "overview", "subsets", "5v", "caveats", "splits", "pipeline"];

export function datasetHref(section) {
  return `#dataset/${section}`;
}
