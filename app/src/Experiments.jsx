import React, { useLayoutEffect } from "react";
import { isPastStickyLine, useStickyBar } from "./sticky.js";
import { t } from "./i18n.js";
import { EXPERIMENTS, modelLabel } from "./data.js";
import { DataLoadFailure, InterpretationNote, Notice } from "./ui.jsx";
import { buildE1View, formatE1Context } from "./e1.js";
import { buildE3E4View, buildScalingView, formatE3Context } from "./scaling.js";
import { byteDisplayUnit, formatBytes, formatCount, joinUnit, formatMsPerSession, formatRatio, formatSeconds, formatSecondsPerMillionEvents, formatNumberOnly, isMissing } from "./format.js";
import { E4ConfigDetails, EnvironmentCard, PanelConfigDetails } from "./RunConfigDetails.jsx";
import { experimentHref } from "./navigation.js";
import { BarChart, LineChart, useSelection } from "./Chart.jsx";
import { usePresenter } from "./presenter.js";
import { Glossary } from "./Glossary.jsx";
import { e3Limitation, e4Fairness, e4Pair, formatLabel } from "./takeaways.js";
import { e1Finding, e2Finding, e3Finding, e4Finding, e5Finding } from "./findings.js";
import { KeyFinding, KeyFindingSource } from "./KeyFinding.jsx";
import { modelColourKey } from "./Recommendation.jsx";

const basename = (value) => (typeof value === "string" && value ? value.split("/").at(-1) : null);
const missingText = () => t("MISSING");

/** One chart point from a delivered value; `formatter` is the shared formatter for its unit. */
function point({ key, label, value, formatter, unit, runId, source, colour, x, displayUnit }) {
  const full = formatter(value, displayUnit);
  const short = formatNumberOnly(formatter, value, displayUnit).text;
  // Bytes are plotted in the displayed unit (MiB/GiB) so the axis matches its title; the raw byte count stays in the tooltip.
  const scale = displayUnit === "GiB" ? 1024 ** 3 : displayUnit === "MiB" ? 1024 ** 2 : 1;
  return { key, label, y: isMissing(value) ? null : value / scale, short, display: full.text, raw: full.raw, unit, runId, source, colour, x };
}

/** Panel shell: title (+ E4 fairness line), the Key finding callout, charts, table, one note block. */
function Panel({ id, title, badge, lead, finding, children }) {
  return <section className="panel experiment-panel" id={`panel-${id.toLowerCase()}`} aria-labelledby={`title-${id}`}>
    <header className="experiment-head">
      <h2 id={`title-${id}`}>{title}{badge}</h2>
    </header>
    {lead}
    {finding && <KeyFinding finding={finding} level={3} />}
    {children}
  </section>;
}

/** Notes under a table: one block. In presenter mode it starts collapsed. */
function Notes({ children }) {
  const presenter = usePresenter();
  return presenter
    ? <details className="notes"><summary>{t("measurement_notes")}</summary>{children}</details>
    : <aside className="notes" aria-label={t("measurement_notes")}>{children}</aside>;
}

/**
 * Metric × run table. Each run is a column: its header is a button that selects the matching chart
 * mark, and clicking any cell in the column does the same. Units live in the row labels.
 * If no cell has a value, one empty state replaces the table.
 */
function MetricTable({ caption, columns, rows, selected, onSelect, waitingDetails, className = "" }) {
  const allMissing = rows.every((row) => row.cells.every((cell) => cell.text === missingText() || cell.text === t("not_measured")));
  if (allMissing) {
    return <div className="empty-state" role="status">
      <strong>{t("waiting_for_tv2_package")}</strong>
      {waitingDetails}
    </div>;
  }
  const select = (key) => onSelect(selected === key ? null : key);
  return <>
    <p className="scroll-hint">{t("scroll_sideways")}</p>
    <div className="table-scroll"><table className={`metric-table ${className}`}>
      <caption className="sr-only">{caption}</caption>
      <thead><tr><th scope="col">{t("metric")}</th>{columns.map((column) => <th scope="col" key={column.key} className={selected === column.key ? "is-selected" : undefined}>
        <button type="button" className="column-select" aria-pressed={selected === column.key} onClick={() => select(column.key)} title={column.title}>
          {column.colour && <span className={`model-dot model-${column.colour}`} aria-hidden="true" />}
          <span>{column.header}{column.sub && <span className="column-subtitle">{column.sub}</span>}</span>
        </button>
      </th>)}</tr></thead>
      <tbody>{rows.map((row) => <React.Fragment key={row.field}>
        {row.group && <tr className="group-row"><th scope="rowgroup" colSpan={columns.length + 1}>{row.group}</th></tr>}
        <tr className={row.primary ? "primary-row" : undefined}>
          <th scope="row">{row.label}</th>
          {row.cells.map((cell, index) => {
            const key = columns[index].key;
            const absent = cell.text === missingText() || cell.text === t("not_measured");
            const classes = [absent ? "missing" : row.text ? "stage-value" : "num", selected === key && "is-selected"].filter(Boolean).join(" ");
            return <td key={`${row.field}/${key}`} title={cell.raw} className={classes} onClick={() => select(key)}>{cell.text}</td>;
          })}
        </tr>
      </React.Fragment>)}</tbody>
    </table></div>
  </>;
}

/** "Selected: …" line under the charts, with Clear and an optional allowed cross-link. */
function SelectionBar({ label, onClear, link }) {
  if (!label) return <p className="selection-bar muted">{t("chart_hint")}</p>;
  return <p className="selection-bar" role="status">
    <span>{t("selected_item", label)}</span>
    {link}
    <button type="button" className="link-button" onClick={onClear}>{t("clear_selection")}</button>
  </p>;
}

function E1Panel({ results }) {
  const view = buildE1View(results);
  const [selected, setSelected] = useSelection();
  const runs = view.models;
  const chartPoints = (field, formatter) => runs.map(({ label, run }) => point({
    key: label, label, value: run?.[field], formatter, runId: run?.run_id, source: basename(run?.source_metrics), colour: modelColourKey(label),
  }));
  const recall = chartPoints("Recall@20", formatRatio);
  const ndcg = chartPoints("NDCG@20", formatRatio);
  const rows = view.rows.map((row, index) => ({ ...row, primary: index < 2, group: index === 2 ? t("time_and_memory_secondary") : null }));
  const context = formatE1Context(view.context);
  return <Panel id="E1" title={`E1 · ${t("experiment_nav_e1")}`} finding={e1Finding(results)}>
    <p className="fair-note">{t("e1_fair_note")} <span className="terms">{t("terms_label")} {t("e1_recall_20")} <Glossary term="recall" /> {t("e1_ndcg_20")} <Glossary term="ndcg" /></span></p>
    <div className="charts">
      <BarChart title={`${t("e1_recall_20")} (${t("test_split")})`} metric={t("e1_recall_20")} yLabel={t("e1_recall_20")} points={recall} selected={selected} onSelect={setSelected} />
      <BarChart title={`${t("e1_ndcg_20")} (${t("test_split")})`} metric={t("e1_ndcg_20")} yLabel={t("e1_ndcg_20")} points={ndcg} selected={selected} onSelect={setSelected} />
    </div>
    <SelectionBar label={selected} onClear={() => setSelected(null)} />
    <MetricTable caption={`${t("e1_model_comparison")} · ${context}`} className="e1-table" selected={selected} onSelect={setSelected}
      columns={runs.map(({ label, run }) => ({ key: label, header: label, colour: modelColourKey(label), title: run?.run_id }))} rows={rows}
      waitingDetails={<PanelConfigDetails results={results} runIds={runs.map(({ run }) => run?.run_id).filter(Boolean)} />} />
    <Notes>
      <p className="notes-title">{t("measurement_scope")}</p>
      <ul>{view.notes.map(({ label, dictionaryKey }) => <li key={dictionaryKey}><strong>{label}:</strong> <InterpretationNote dictionaryKey={dictionaryKey} /></li>)}</ul>
    </Notes>
    <PanelConfigDetails results={results} runIds={runs.map(({ run }) => run?.run_id).filter(Boolean)} context={context} />
  </Panel>;
}

function E2Panel({ results, initial }) {
  const { e2Table } = buildScalingView(results);
  const runs = [...(results?.tables?.E2 ?? [])].sort((a, b) => a.subset - b.subset);
  const [selected, setSelected] = useSelection(runs.some((run) => String(run.subset) === initial) ? initial : null);
  const colour = modelColourKey(runs[0]?.model);
  const chartPoints = (field) => runs.map((run) => point({
    key: String(run.subset), label: `${run.subset}%`, value: run[field], formatter: formatRatio, runId: run.run_id, source: basename(run.source_metrics), colour,
  }));
  // Processing time (course item): the two delivered time fields in two linked charts, never summed.
  const timePoints = (field) => runs.map((run) => point({
    key: String(run.subset), label: `${run.subset}%`, value: run[field], formatter: formatSeconds, unit: "s", runId: run.run_id, source: basename(run.source_metrics), colour,
  }));
  return <Panel id="E2" title={`E2 · ${t("experiment_nav_e2")}`} finding={e2Finding(results)}>
    <div className="charts">
      <BarChart title={`${t("e1_recall_20")} (${t("test_split")})`} metric={t("e1_recall_20")} yLabel={t("e1_recall_20")} points={chartPoints("Recall@20")} selected={selected} onSelect={setSelected} />
      <BarChart title={`${t("e1_ndcg_20")} (${t("test_split")})`} metric={t("e1_ndcg_20")} yLabel={t("e1_ndcg_20")} points={chartPoints("NDCG@20")} selected={selected} onSelect={setSelected} />
      <BarChart title={t("e2_chart_time_pre")} metric={t("e2_preprocessing_metric")} yLabel={t("seconds_axis")} points={timePoints("preprocessing_seconds")} selected={selected} onSelect={setSelected} />
      <BarChart title={t("e2_chart_time_train")} metric={t("e1_train_time_s")} yLabel={t("seconds_axis")} points={timePoints("train_seconds_including_sequence_io")} selected={selected} onSelect={setSelected} />
    </div>
    <SelectionBar label={selected == null ? null : `${selected}%`} onClear={() => setSelected(null)} />
    <MetricTable caption={t("e2_effect_of_dataset_size")} className="scaling-table" selected={selected} onSelect={setSelected}
      columns={e2Table.columns.map((column) => ({ key: String(column.subset), header: `${column.subset}%`, sub: joinUnit(column.events.text, t("events")), title: column.runId }))}
      rows={e2Table.rows.map((row, rowIndex) => ({ ...row, cells: e2Table.columns.map((column) => column.cells[rowIndex]) }))} />
    <Notes>
      <InterpretationNote dictionaryKey="E2_accuracy" />
      <p className="interpretation-note"><span title={String(e2Table.firstSeen)}>{t("e2_first_seen_shared", formatSeconds(e2Table.firstSeen).text)}</span> <InterpretationNote dictionaryKey="first_seen_shared" /></p>
    </Notes>
    <PanelConfigDetails results={results} runIds={runs.map((run) => run.run_id)} />
  </Panel>;
}

function heldConstant(results, runIds) {
  const configs = runIds.map((id) => results?.configs?.[id]?.actual ?? {});
  const value = (key) => {
    const values = [...new Set(configs.map((config) => config[key]).filter((v) => v !== null && v !== undefined).map(String))];
    return values.length ? values.join(" / ") : missingText();
  };
  return t("e3_held_constant", value("eval_batch_size"), value("epochs"), value("seed"), value("learning_rate"), value("subset"), value("split"), value("train_through"));
}

function E3Panel({ results }) {
  const { e3 } = buildE3E4View(results);
  const [selected, setSelected] = useSelection();
  const runs = [...(results?.tables?.E3 ?? [])].sort((a, b) => a.train_batch_size - b.train_batch_size);
  // Column headers read the train batch from the run configuration (configs → actual.batch_size).
  const batchOf = (run) => results?.configs?.[run.run_id]?.actual?.batch_size ?? results?.configs?.[run.run_id]?.planned?.batch_size ?? run.train_batch_size;
  const header = (run) => t("e3_train_batch_header", batchOf(run) ?? missingText());
  const colour = modelColourKey(runs[0]?.model);
  const title = t("e3_panel_title", modelLabel(runs[0]?.model), runs[0]?.train_batch_size ?? missingText(), runs.at(-1)?.train_batch_size ?? missingText());
  const gpuBytes = (run) => (run.sampled_gpu_status === "unavailable" ? null : run.sampled_gpu_process_bytes);
  const gpuUnit = byteDisplayUnit(runs.map(gpuBytes));
  const chartPoints = (read, formatter, unit, displayUnit) => runs.map((run) => point({
    key: run.run_id, label: header(run), value: read(run), formatter, displayUnit, unit, runId: run.run_id, source: basename(run.source_metrics), colour,
  }));
  return <Panel id="E3" title={title} badge={<span className="badge badge-validation">{t("validation_badge")}</span>}
    finding={e3Finding(results)}>
    <p className="fair-note">{t("e3_not_beside_test")} <Glossary term="validation" /></p>
    <div className="charts charts-3">
      <BarChart title={t("e3_chart_train_time")} metric={t("e1_train_time_s")} yLabel={t("seconds_axis")}
        points={chartPoints((run) => run.train_seconds_including_sequence_io, formatSeconds, "s")} selected={selected} onSelect={setSelected} />
      <BarChart title={t("e3_chart_gpu")} metric={t("e1_sampled_gpu_process_memory")} yLabel={t("memory_axis", gpuUnit)}
        points={chartPoints(gpuBytes, formatBytes, gpuUnit, gpuUnit)} selected={selected} onSelect={setSelected} />
      <BarChart title={t("e3_chart_recall")} metric={t("e3_recall_20_validation")} yLabel={t("e1_recall_20")}
        points={chartPoints((run) => run["Recall@20"], formatRatio)} selected={selected} onSelect={setSelected} />
    </div>
    <SelectionBar label={runs.find((run) => run.run_id === selected) ? header(runs.find((run) => run.run_id === selected)) : null} onClear={() => setSelected(null)} />
    <MetricTable caption={title} className="e3-table" selected={selected} onSelect={setSelected}
      columns={runs.map((run) => ({ key: run.run_id, header: header(run), colour, title: run.run_id }))}
      rows={e3.rows.map((row, rowIndex) => ({ ...row, cells: e3.models.map((model) => model.cells[rowIndex]) }))} />
    <Notes>
      <p className="interpretation-note">{e3Limitation(results)}</p>
      <p className="interpretation-note">{heldConstant(results, runs.map((run) => run.run_id))}</p>
      <InterpretationNote dictionaryKey="E3_accuracy" />
      <InterpretationNote dictionaryKey="inference_protocol" />
    </Notes>
    <PanelConfigDetails results={results} runIds={runs.map((run) => run.run_id)} />
  </Panel>;
}

function E4Panel({ results }) {
  const { e4 } = buildE3E4View(results);
  const [selected, setSelected] = useSelection();
  // CSV first, Parquet second, matching the takeaway (Parquet compared with CSV).
  const runs = e4Pair(results) ?? results?.tables?.E4 ?? [];
  const label = (run) => formatLabel(run.format);
  const chartPoints = (field, formatter, unit) => runs.map((run) => point({
    key: run.run_id, label: label(run), value: run[field], formatter, displayUnit: formatter === formatBytes ? unit : undefined, unit, runId: run.run_id, source: basename(run.source_metrics),
  }));
  const byRun = new Map(e4.formats.map((format) => [format.runId, format]));
  const formats = runs.map((run) => byRun.get(run.run_id)).filter(Boolean);
  const fairness = e4Fairness(results);
  return <Panel id="E4" title={t("e4_panel_title")} finding={e4Finding(results)}
    lead={fairness && <p className="fairness-line"><span className="fairness-mark" aria-hidden="true">✓</span> {fairness}</p>}>
    <div className="charts charts-3">
      <BarChart title={t("e4_file_size_bytes")} metric={t("e4_file_size_bytes")} yLabel={t("mib_axis")} points={chartPoints("bytes", formatBytes, "MiB")} selected={selected} onSelect={setSelected} />
      <BarChart title={t("e4_read_time_s")} metric={t("e4_read_time_s")} yLabel={t("seconds_axis")} points={chartPoints("read_seconds", formatSeconds, "s")} selected={selected} onSelect={setSelected} />
      <BarChart title={t("e4_chart_preprocessing")} metric={t("e4_preprocessing_wall_including_read_s")} yLabel={t("seconds_axis")} points={chartPoints("preprocessing_wall_seconds_including_read", formatSeconds, "s")} selected={selected} onSelect={setSelected} />
    </div>
    <SelectionBar label={runs.find((run) => run.run_id === selected) ? label(runs.find((run) => run.run_id === selected)) : null} onClear={() => setSelected(null)} />
    <MetricTable caption={t("e4_panel_title")} className="e4-table" selected={selected} onSelect={setSelected}
      columns={formats.map((format) => ({ key: format.runId, header: formatLabel(format.label), title: format.runId }))}
      rows={e4.rows.map((row, rowIndex) => ({ ...row, cells: formats.map((format) => format.cells[rowIndex]) }))} />
    <Notes>
      <p className="interpretation-note">{t("e4_limit")}</p>
      <InterpretationNote dictionaryKey="E4_preprocessing_wall" />
      <p className="interpretation-note">{t("e4_bytes_tooltip_note")}</p>
      <details className="excluded-runs"><summary>{t("e4_excluded_runs")}</summary>
        <ul>{e4.excluded.map(([runId, reason]) => <li key={runId}><code>{runId}</code>: {reason}</li>)}</ul>
      </details>
    </Notes>
    <E4ConfigDetails results={results} runIds={formats.map(({ runId }) => runId)} />
  </Panel>;
}

function E5Panel({ results }) {
  const { e5Table, registrySummary } = buildScalingView(results);
  const [selected, setSelected] = useSelection();
  const e5 = [...(results?.tables?.E5 ?? [])].sort((a, b) => a.subset - b.subset);
  const events = new Map((results?.tables?.E2 ?? []).map((row) => [row.subset, row.n_events]));
  const chartPoints = (field, formatter, unit) => e5.map((run) => point({
    key: String(run.subset), label: `${run.subset}% · ${joinUnit(formatCount(events.get(run.subset) ?? run.n_events).text, t("events"))}`,
    value: run[field], formatter, runId: run.run_id, source: basename(run.source_log), x: events.get(run.subset) ?? run.n_events, unit,
  }));
  const first = e5[0], last = e5.at(-1);
  const firstSeen = e5.find((run) => !isMissing(run.first_seen_seconds_shared))?.first_seen_seconds_shared;
  return <Panel id="E5" title={`E5 · ${t("experiment_nav_e5")}`} finding={e5Finding(results)}>
    <div className="charts">
      <LineChart title={t("e5_composed_seconds_chart")} metric={t("e5_composed_time_s")} yLabel={t("e5_composed_seconds_axis")} xLabel={t("e5_x_axis_events")}
        points={chartPoints("composed_seconds_excluding_first_seen", formatSeconds, "s")} selected={selected} onSelect={setSelected} />
      <LineChart title={t("e5_normalized_seconds_chart")} metric={t("e5_seconds_per_million_events")} yLabel={t("e5_normalized_seconds_axis")} xLabel={t("e5_x_axis_events")}
        points={chartPoints("seconds_per_million_events", formatSecondsPerMillionEvents, t("unit_s_per_million_events"))} selected={selected} onSelect={setSelected} />
    </div>
    <SelectionBar label={selected == null ? null : `${selected}%`} onClear={() => setSelected(null)}
      link={selected == null ? null : <a href={experimentHref("E2", selected)}>{t("open_in_e2", selected)}</a>} />
    <MetricTable caption={t("e5_scalability")} className="scaling-table e5-table" selected={selected} onSelect={setSelected}
      columns={e5Table.columns.map((column) => ({ key: String(column.subset), header: `${column.subset}%`, sub: joinUnit(formatCount(events.get(column.subset)).text, t("events")), title: column.runId }))}
      rows={e5Table.rows.map((row) => ({ ...row, text: row.field === "bottleneck" }))} />
    <Notes>
      {results.E5_aggregation_only === true && <InterpretationNote dictionaryKey="E5_derived_from_E2" source={t("source_metrics_flag", "E5_aggregation_only")} />}
      <InterpretationNote dictionaryKey="E5_composed" />
      <p className="interpretation-note"><span title={String(firstSeen)}>{t("e5_first_seen_once", formatSeconds(firstSeen).text)}</span></p>
      {registrySummary && <p className="registry-summary">{t("run_registry_summary", registrySummary.passed, registrySummary.derived_from_verified_E2, registrySummary.excluded)}</p>}
    </Notes>
    <PanelConfigDetails results={results} runIds={e5Table.columns.map(({ runId }) => runId)} />
  </Panel>;
}

export default function Experiments({ state, active, select = null }) {
  const sticky = useStickyBar();
  // Switching E1–E5 while scrolled down: keep the sub-nav in view and bring the new panel's top just
  // below it (scroll-padding-top accounts for header + sub-bar). Runs once per panel switch.
  useLayoutEffect(() => {
    // One-row scrolling sub-nav on phones: keep the active experiment in view.
    const nav = sticky.bar.current;
    const link = nav?.querySelector('[aria-current="page"]');
    if (nav && link && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = Math.max(0, link.offsetLeft - nav.offsetLeft - 16);
    if (!isPastStickyLine(sticky.sentinel.current)) return;
    document.getElementById(`panel-${String(active).toLowerCase()}`)?.scrollIntoView({ block: "start" });
  }, []);
  if (state.error) return <DataLoadFailure title={t("could_not_load_e1_e5_results")} detail={state.error} />;
  if (state.loading) return <p className="loading">{t("loading_data")}</p>;
  const results = state.results;
  if (!results) return <Notice kind="error" title={t("could_not_load_e1_e5_results")}>{t("MISSING")}</Notice>;
  return <>
    <div className="page-head">
      <h1 className="page-title">{t("experiments_e1_e5")}</h1>
    </div>
    <div ref={sticky.sentinel} className="sticky-sentinel" aria-hidden="true" />
    <nav ref={sticky.bar} className={`segmented subtabs glass subbar${sticky.stuck ? " is-stuck" : ""}`} aria-label={t("experiment_subnav")}>{EXPERIMENTS.map((id) => (
      <a key={id} href={experimentHref(id)} aria-current={id === active ? "page" : undefined}>
        <span className="subtab-label"><strong>{id}</strong> · {t(`experiment_nav_${id.toLowerCase()}`)}</span>
      </a>
    ))}</nav>
    {active === "E1" ? <E1Panel results={results} />
      : active === "E2" ? <E2Panel results={results} initial={select} />
        : active === "E3" ? <E3Panel results={results} />
          : active === "E4" ? <E4Panel results={results} />
            : <E5Panel results={results} />}
    <EnvironmentCard results={results} />
    <KeyFindingSource />
  </>;
}
