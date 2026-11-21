import { t } from "./i18n.js";
import ExperimentCharts from "./ExperimentCharts.jsx";
import React, { useState } from "react";
import {
  EXPERIMENTS, compareConfig, displayCell, exactValue, formatValue, modelLabel, splitByKind,
} from "./data.js";
import { DataKindBadge, Issues, Notice, StatusBadge } from "./ui.jsx";

// Metric definitions: label, default unit and scope (contract B5). Values always come from JSON.
const METRICS = () => ({
  "Recall@20": { label: "Recall@20", unit: "ratio" },
  "NDCG@20": { label: "NDCG@20", unit: "ratio" },
  train_with_input_scan_seconds: { label: t("training_time_including_input_scan"), unit: "s" },
  inference_seconds: { label: t("evaluation_time"), unit: "s" },
  inference_ms_per_session: { label: t("experiment_evaluation_time_session"), unit: "ms/session" },
  inference_sessions_per_second: { label: t("experiment_evaluation_throughput"), unit: "sessions/s" },
  elapsed_seconds: { label: t("experiment_collector_wall_time"), unit: "s" },
  peak_process_tree_rss_bytes: { label: t("experiment_peak_process_rss"), unit: "bytes" },
  peak_cuda_reserved_bytes: { label: t("experiment_peak_cuda_reserved"), unit: "bytes" },
  cost: { label: t("cost"), unit: null },
  n_events: { label: t("experiment_weekly_sampled_events"), unit: "events" },
  pipeline_read_seconds: { label: t("experiment_pipeline_raw_read"), unit: "s" },
  preprocessing_seconds: { label: t("experiment_preprocessing"), unit: "s" },
  first_seen_seconds: { label: t("shared_first_seen_time"), unit: "s" },
  bytes: { label: t("file_size"), unit: "bytes" },
  read_seconds: { label: t("experiment_read_wall_time"), unit: "s" },
  peak_read_process_rss_bytes: { label: t("experiment_peak_reader_rss"), unit: "bytes" },
  preprocessing_elapsed_seconds: { label: t("experiment_preprocessing_wall_time"), unit: "s" },
  seconds_per_million_events: { label: t("time_per_million_events"), unit: "s/million events" },
  bottleneck: { label: t("bottleneck_slowest_stage"), unit: "stage" },
  raw_read: { label: t("experiment_stage_raw_read"), unit: "s" },
  preprocessing_excluding_raw_read_and_first_seen: { label: t("experiment_stage_preprocessing"), unit: "s" },
  train_including_sequence_io: { label: t("stage_training_including_sequence_i_o"), unit: "s" },
  final_evaluation_including_io: { label: t("stage_final_evaluation_including_i_o"), unit: "s" },
  composed_seconds_excluding_first_seen: { label: t("total_composed_time_excluding_first_seen"), unit: "s" },
  composed_seconds_with_first_seen: { label: t("total_composed_time_including_first_seen"), unit: "s" },
  process_wall_seconds: { label: t("observed_process_wall_time"), unit: "s" },
  limitations: { label: t("limitations_and_uncertainty"), unit: "text" },
});

const MODEL_METRICS = [
  "Recall@20", "NDCG@20", "train_with_input_scan_seconds", "inference_seconds",
  "inference_ms_per_session", "inference_sessions_per_second", "elapsed_seconds",
  "peak_process_tree_rss_bytes", "peak_cuda_reserved_bytes",
];

const PANELS = () => ({
  E1: {
    title: t("e1_model_comparison"),
    question: t("compare_popularity_gru_and_xlnet_on"),
    metrics: MODEL_METRICS,
  },
  E2: {
    title: t("e2_effect_of_dataset_size"),
    question: t("compare_gru_across_sampling_fractions_for"),
    metrics: [...MODEL_METRICS, "n_events", "pipeline_read_seconds", "preprocessing_seconds", "first_seen_seconds"],
  },
  E3: {
    title: t("e3_effect_of_resources"),
    question: t("compare_two_gru_training_batch_sizes"),
    metrics: [...MODEL_METRICS, "cost"],
  },
  E4: {
    title: t("experiment_e4_csv_vs_parquet"),
    question: t("compare_size_read_time_preprocessing_time"),
    metrics: ["bytes", "read_seconds", "peak_read_process_rss_bytes", "preprocessing_elapsed_seconds", "elapsed_seconds", "peak_process_tree_rss_bytes"],
  },
  E5: {
    title: t("e5_scalability"),
    question: t("summarize_e2_logs_to_show_time"),
    metrics: [
      "seconds_per_million_events", "bottleneck", "raw_read",
      "preprocessing_excluding_raw_read_and_first_seen", "train_including_sequence_io",
      "final_evaluation_including_io", "composed_seconds_excluding_first_seen",
      "composed_seconds_with_first_seen", "process_wall_seconds", "limitations",
    ],
  },
});

const CONFIG_FIELDS = () => [
  ["train_batch_size", t("experiment_train_batch"), "sessions/batch"],
  ["eval_batch_size", t("experiment_eval_batch"), "sessions/batch"],
  ["epochs", t("experiment_epochs"), "epochs"],
  ["sequence_length", t("experiment_sequence_length"), "items"],
  ["seed", t("experiment_seed"), ""],
  ["learning_rate", t("experiment_learning_rate"), ""],
  ["subset", t("experiment_subset"), ""],
  ["split", t("experiment_split"), ""],
  ["train_partitions", t("experiment_train_partitions"), "day index"],
  ["eval_partition", t("experiment_eval_partition"), "day index"],
  ["input_format", t("experiment_input_format"), ""],
  ["device", t("experiment_device"), ""],
  ["change_only", t("varied_parameter"), ""],
  ["artifact_versions", t("experiment_data_versions"), ""],
];

const ENV_FIELDS = () => [
  ["gpu", "GPU"], ["cuda", "CUDA"], ["driver", "Driver"], ["python", "Python"], ["torch", "torch"],
  ["cpu_model", "CPU"], ["cpu_cores", t("experiment_cpu_cores")], ["ram_bytes", "RAM (bytes)"], ["os", "OS"], ["platform", t("experiment_platform")],
];

const hidesMetrics = (run) => ["failed", "excluded"].includes(run.status);

function RunHeader({ run }) {
  return (
    <div className="run-head">
      <strong>{run.model ? modelLabel(run.model) : run.planned?.input_format ?? run.run_id}</strong>
      <code>{run.run_id}</code>
      <span className="badges"><StatusBadge status={run.status} /><DataKindBadge kind={run.data_kind} /></span>
      {(hidesMetrics(run) || run.exclusion_note) && <span className="note">{t("reason")} {run.exclusion_note || t("not_available_yet")}</span>}
    </div>
  );
}

function MetricCell({ run, metricKey }) {
  if (hidesMetrics(run)) return <td className="missing">{t("not_applicable")}</td>;
  const entry = run.metrics?.[metricKey];
  const value = entry?.value ?? null;
  const text = value === null ? displayCell(run, metricKey, value) : exactValue(value);
  const unit = entry?.unit;
  return (
    <td title={value === null ? undefined : exactValue(value)} className={value === null ? "missing" : "num"}>
      {text}
      {value !== null && unit && unit !== "text" && unit !== "stage" && <span className="unit"> {unit}</span>}
      {value !== null && entry?.scope && <span className="scope">{entry.scope}</span>}
    </td>
  );
}

function MetricTable({ runs, metrics, caption }) {
  if (!runs.length) return <p className="missing">{t("not_available_yet")}</p>;
  return (
    <>
    {runs.length > 1 && <p className="scroll-hint">{t("scroll_across_to_see_all")} {runs.length} {t("runs")}</p>}
    <div className="table-scroll">
      <table className="metric-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">{t("metric")}</th>
            {runs.map((run) => <th scope="col" key={run.run_id}><RunHeader run={run} /></th>)}
          </tr>
        </thead>
        <tbody>
          {metrics.map((key) => (
            <tr key={key}>
              <th scope="row">
                {METRICS()[key].label}
                {METRICS()[key].unit && <span className="unit"> ({METRICS()[key].unit})</span>}
              </th>
              {runs.map((run) => <MetricCell key={run.run_id} run={run} metricKey={key} />)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </>
  );
}

function ConfigDetails({ run }) {
  const sources = Object.entries(run.sources ?? {});
  return (
    <details className="config">
      <summary>{t("planned_actual_configuration_environment_and_sources")} <code>{run.run_id}</code></summary>
      <div className="table-scroll">
        <table className="config-table">
          <thead><tr><th scope="col">{t("parameter")}</th><th scope="col">{t("planned")}</th><th scope="col">{t("actual")}</th><th scope="col">{t("comparison")}</th></tr></thead>
          <tbody>
            {CONFIG_FIELDS().map(([key, label, unit]) => {
              const planned = run.planned?.[key] ?? null;
              const actual = key === "change_only" ? undefined : run.actual?.[key] ?? null;
              const cmp = compareConfig(key, planned, actual);
              return (
                <tr key={key} className={cmp === "different" ? "diff" : ""}>
                  <th scope="row">{label}{unit && <span className="unit"> ({unit})</span>}</th>
                  <td className={planned === null ? "missing" : ""}>{displayCell(run, key, planned)}</td>
                  <td className={actual === null ? "missing" : ""}>{actual === undefined ? t("not_applicable") : displayCell(run, key, actual)}</td>
                  <td>{cmp === "different" ? <span className="tag tag-diff">{t("different")}</span> : cmp === "same" ? t("match") : ""}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <h4>{t("environment")}</h4>
      <dl className="env">
        {ENV_FIELDS().map(([key, label]) => (
          <div key={key}><dt>{label}</dt><dd className={run.environment?.[key] == null ? "missing" : ""}>{formatValue(run.environment?.[key])}</dd></div>
        ))}
      </dl>
      <h4>{t("source")}</h4>
      {sources.length ? <ul className="sources">
        {sources.map(([key, value]) => <li key={key}><span>{key}:</span> <code>{formatValue(value)}</code></li>)}
      </ul> : <p className="missing">{t("not_available_yet")}</p>}
    </details>
  );
}

function RunSet({ runs, metrics, caption }) {
  return (
    <>
      <MetricTable runs={runs} metrics={metrics} caption={caption} />
      {runs.map((run) => <ConfigDetails key={run.run_id} run={run} />)}
    </>
  );
}

function E5Panel({ runs }) {
  const panel = PANELS().E5;
  return (
    <>
      {runs.length ? <RunSet runs={runs} metrics={panel.metrics} caption={panel.title} /> : (
        <div className="table-scroll">
          <table className="metric-table">
            <caption className="sr-only">{panel.title}</caption>
            <thead><tr><th scope="col">{t("metric")}</th><th scope="col">{t("e5_summary")}</th></tr></thead>
            <tbody>
              {panel.metrics.map((key) => (
                <tr key={key}>
                  <th scope="row">{METRICS()[key].label}{METRICS()[key].unit && <span className="unit"> ({METRICS()[key].unit})</span>}</th>
                  <td className="missing">{t("not_available_yet")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!runs.length && <p className="definition">{t("source_runs_e2_configuration_and_environment")} {t("not_available_yet")}</p>}
    </>
  );
}

export default function Experiments({ state, active }) {
  const { runs = [], meta = {}, issues = [], fatal, error } = state;
  const [showToy, setShowToy] = useState(true);

  if (error) return <Notice kind="error" title={t("could_not_load_e1_e5_results")}>{error}</Notice>;
  if (fatal) return (<><Notice kind="error" title={t("invalid_run_results_json")}>{fatal}</Notice><Issues issues={issues} /></>);

  const panel = PANELS()[active];
  const { official, toy } = splitByKind(runs, active);
  const order = (r) => official.findIndex((o) => o.run_id === r.matrix_run_id);
  const toySorted = [...toy].sort((a, b) => order(a) - order(b));

  return (
    <>
      <Issues issues={issues} />
      {!meta.confirmed_by_tv2 && (
        <Notice kind="warn" title={t("official_e1_e5_package_pending_from")}>{t("planned_values_come_from_the_experiment")}{t("not_available_yet")}{t("until_tv2_delivers_them")} {meta.team_commit && <> {t("data_exported_from_team_commit")} <code>{meta.team_commit}</code>.</>}
        </Notice>
      )}

      <section className="panel">
        <h2>{t("vm_environment_tv3")}</h2>
        {meta.environment_baseline ? <>
          <p>{meta.environment_baseline.scope}</p>
          <dl className="env">{Object.entries(meta.environment_baseline)
            .filter(([key]) => !["source", "scope"].includes(key))
            .map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{formatValue(value)}</dd></div>)}</dl>
          <p className="definition">{formatValue(meta.environment_baseline.source)}</p>
        </> : <p>{t("not_available_yet")}</p>}
      </section>

      <nav className="subtabs" aria-label={t("experiments")}>
        {EXPERIMENTS.map((id) => (
          <a key={id} href={`#experiments-${id.toLowerCase()}`} className={id === active ? "active" : ""} aria-current={id === active ? "page" : undefined}>{id}</a>
        ))}
        <label className="toggle">
          <input type="checkbox" checked={showToy} onChange={(e) => setShowToy(e.target.checked)} />{t("show_toy_runs_for_format_reference")} </label>
      </nav>

      <section className="panel">
        <div className="panel-heading">
          <h2>{panel.title}</h2>
        </div>
        <p className="definition">{panel.question}</p>

        <ExperimentCharts experiment={active} runs={official} />
        {active === "E5" ? <E5Panel runs={official} /> : (
          <>
            <h3>{meta.confirmed_by_tv2 ? t("official_runs") : t("planned_runs")}</h3>
            {official.length ? <RunSet runs={official} metrics={panel.metrics} caption={t("0_official", panel.title)} /> : <p className="missing">{t("not_available_yet")}</p>}
          </>
        )}

        {showToy && toySorted.length > 0 && (
          <div className="toy-block">
            <h3>{t("toy_smoke_runs")} <DataKindBadge kind="toy" /></h3>
            <p className="definition">{t("these_runs_use_synthetic_data_to")} </p>
            <ExperimentCharts experiment={active} runs={toySorted} />
            <RunSet runs={toySorted} metrics={panel.metrics} caption={t("toy_chart_caption", panel.title)} />
          </div>
        )}
      </section>
    </>
  );
}
