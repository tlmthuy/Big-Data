import React from "react";
import { t } from "./i18n.js";
import { formatValue } from "./data.js";
import { configurationRows, runtimeRows } from "./run-config.js";
import { formatCount, keepUnitsTogether } from "./format.js";
import { formatLabel } from "./takeaways.js";

function ConfigRun({ runId, config }) {
  const rows = configurationRows(config);
  const runtimeFields = runtimeRows(config);
  const catalogSha = config?.catalog_sha256 ?? null;
  const sourceMetrics = config?.source_metrics ?? null;
  return <section className="config-run">
    <h3><code>{runId}</code></h3>
    <div className="table-scroll"><table className="config-table">
      <thead><tr><th scope="col">{t("parameter")}</th><th scope="col">{t("planned")}</th><th scope="col">{t("actual")}</th><th scope="col">{t("comparison")}</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.key} className={row.differs ? "diff" : ""}>
        <th scope="row">{row.label}</th>
        <td title={row.plannedRaw}>{row.planned}</td>
        <td title={row.actualRaw}>{row.actual}</td>
        <td>{row.differs && <span className="tag tag-diff">{t("differs")}</span>}</td>
      </tr>)}</tbody>
    </table></div>
    <h4>{t("environment")}</h4>
    <dl className="env config-runtime">{runtimeFields.map(({ key, label, value }) => <div key={key}>
      <dt>{label}</dt><dd title={value == null ? undefined : String(value)}>{formatValue(value)}</dd>
    </div>)}</dl>
    <ul className="sources">
      <li><span>{t("catalog_sha_short")}:</span> <code title={catalogSha ?? undefined}>{catalogSha ? catalogSha.slice(0, 12) : t("MISSING")}</code></li>
      <li><span>{t("source_metrics")}:</span> <code title={sourceMetrics ?? undefined}>{sourceMetrics ?? t("MISSING")}</code></li>
    </ul>
  </section>;
}

/** One row of the E4 preprocessing table: label, how to show a value, and whether to compare it. */
const E4_ROWS = [
  ["input_format", "e4cfg_input_format", (value) => formatLabel(value)],
  ["subset", "e4cfg_subset", (value) => `${formatValue(value)}%`],
  ["n_events", "e4cfg_n_events", (value) => formatCount(value).text],
  ["fingerprint_match", "e4cfg_fingerprint", (value) => t(value ? "e4cfg_fingerprint_yes" : "e4cfg_fingerprint_no")],
  ["program", "e4cfg_program", (value) => value],
  ["read_scope", "e4cfg_read_scope", (value) => value],
  ["schema_policy", "e4cfg_schema_policy", (value) => value],
  ["cache", "e4cfg_cache", (value) => value],
  ["events_after_repeat_removal", "e4cfg_events_after_repeat_removal", (value) => formatCount(value).text],
  ["product_vocabulary_size", "e4cfg_product_vocabulary_size", (value) => formatCount(value).text],
  ["cudf_version", "e4cfg_cudf_version", (value) => value],
  ["nvtabular_version", "e4cfg_nvtabular_version", (value) => value],
  ["notebook_commit", "e4cfg_notebook_commit", (value) => String(value).slice(0, 8)],
  ["split_seed", "e4cfg_split_seed", (value) => formatValue(value)],
  ["requested_ratios", "e4cfg_requested_ratios", (value) => Object.entries(value).map(([name, share]) => `${name} ${formatValue(share)}`).join(" · ")],
  ["partition_col", "e4cfg_partition_col", (value) => value],
];

/** E4 "Configuration & sources": preprocessing configuration of the CSV and Parquet runs side by side. */
export function E4ConfigDetails({ results, runIds }) {
  const runs = runIds.map((runId) => ({ runId, e4: results?.configs?.[runId]?.e4_config ?? null }));
  const cell = (run, key, show) => {
    if (!run.e4) return { text: t("not_applicable"), raw: undefined };
    const value = run.e4[key];
    if (value === null || value === undefined) return { text: t("MISSING"), raw: undefined };
    return { text: show(value), raw: typeof value === "object" ? JSON.stringify(value) : String(value) };
  };
  const sources = [...new Set(runs.map((run) => run.e4?.source).filter(Boolean))];
  return <details className="config config-bundle e4-config">
    <summary>{t("configuration_and_sources")}</summary>
    <h3>{t("e4cfg_title")}</h3>
    <div className="table-scroll"><table className="config-table">
      <thead><tr><th scope="col">{t("parameter")}</th>{runs.map((run) => <th scope="col" key={run.runId} title={run.runId}>
        {t("e4cfg_run", run.e4 ? formatLabel(run.e4.input_format) : run.runId)}</th>)}<th scope="col">{t("comparison")}</th></tr></thead>
      <tbody>{E4_ROWS.map(([key, labelKey, show]) => {
        const cells = runs.map((run) => cell(run, key, show));
        const same = cells.length > 1 && cells.every((value) => value.raw !== undefined && value.raw === cells[0].raw);
        return <tr key={key}>
          <th scope="row">{t(labelKey)}</th>
          {cells.map((value, index) => <td key={runs[index].runId} title={value.raw}>{value.text}</td>)}
          <td>{same && <span className="tag tag-same">{t("e4cfg_same")}</span>}</td>
        </tr>;
      })}</tbody>
    </table></div>
    <ul className="sources">
      {runs.map((run) => <li key={run.runId}><span>{t("run_id_label")}:</span> <code>{run.runId}</code></li>)}
      {sources.map((source) => <li key={source}><span>{t("source")}</span> <code>{source}</code></li>)}
    </ul>
  </details>;
}

export function PanelConfigDetails({ results, runIds, context = null }) {
  return <details className="config config-bundle">
    <summary>{t("configuration_and_sources")}</summary>
    {context && <p className="config-context">{context}</p>}
    {runIds.map((runId) => <ConfigRun key={runId} runId={runId} config={results?.configs?.[runId]} />)}
  </details>;
}

export function EnvironmentCard({ results }) {
  const e1Runs = results?.tables?.E1 ?? [];
  const candidates = e1Runs.map((run) => results?.configs?.[run.run_id]?.runtime).filter(Boolean);
  const valueFor = (key, packageKey) => candidates.map((runtime) => packageKey ? runtime.packages?.[packageKey] : runtime[key]).find((value) => value !== null && value !== undefined);
  const vm = results?.vm_environment ?? {};
  const rows = [
    [t("environment_cloud"), vm.cloud],
    [t("environment_gpu_vram"), vm.gpu && vm.vram ? t("environment_gpu_vram_value", vm.gpu, vm.vram) : null],
    [t("environment_cpu_vcpu"), vm.cpu && vm.vcpu ? t("environment_cpu_vcpu_value", vm.cpu, vm.vcpu) : null],
    [t("environment_ram"), vm.ram], [t("environment_os"), vm.os],
    [t("environment_driver"), vm.driver], [t("environment_cuda_toolkit"), vm.cuda_toolkit],
    [t("environment_docker"), vm.docker], [t("environment_image"), vm.image],
    [t("runtime_python"), valueFor("python")], [t("pytorch"), valueFor(null, "torch")],
    [t("runtime_transformers4rec"), valueFor(null, "transformers4rec")],
    [t("cost"), t("not_measured")],
  ];
  return <details className="panel environment-card">
    <summary><span className="summary-title">{t("environment")}</span> <span className="summary-sub">{t("environment_summary")}</span></summary>
    <dl className="env">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{keepUnitsTogether(value) ?? t("MISSING")}</dd></div>)}</dl>
    <p className="environment-source">{t("environment_source_note", vm.source ?? t("MISSING"), vm.checksum_note ?? t("MISSING"))}</p>
  </details>;
}
