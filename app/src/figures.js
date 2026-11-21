export function figureRows(runs, metrics) {
  return runs.flatMap((run) => metrics.map((metric) => {
    const entry = ["failed", "excluded"].includes(run.status) ? null : run.metrics?.[metric];
    return {
      runId: run.run_id,
      metric,
      value: typeof entry?.value === "number" && Number.isFinite(entry.value) ? entry.value : null,
      unit: entry?.unit ?? null,
      scope: entry?.scope ?? null,
    };
  }));
}
