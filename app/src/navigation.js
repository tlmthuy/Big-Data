import { EXPERIMENTS } from "./data.js";

export function routeFromHash(hash) {
  const name = hash.slice(1);
  const experiment = EXPERIMENTS.find((id) => name === `experiments-${id.toLowerCase()}`);
  if (name === "experiments" || experiment) {
    return { tab: "experiments", experiment: experiment ?? EXPERIMENTS[0] };
  }
  if (name === "data") return { tab: "data" };
  return { tab: "recommendation" };
}
