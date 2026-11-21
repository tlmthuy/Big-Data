import { t } from "./i18n.js";
import React, { useState } from "react";
import { formatValue } from "./data.js";
import { histogramBuckets } from "./dataset.js";
import { FiveVs, SubsetSelection } from "./DatasetContext.jsx";
import EvaluationProtocol from "./EvaluationProtocol.jsx";
import PipelineMeasurements from "./PipelineMeasurements.jsx";
import { Notice } from "./ui.jsx";

const ROWS = () => [
  [t("weekly_events_before_cleanup"), "n_events"],
  [t("events_after_consecutive_repeat_removal"), "events_after_repeat_removal"],
  [t("sessions"), "distinct", "user_session"],
  [t("users"), "distinct", "user_id"],
  [t("products"), "distinct", "product_id"],
  [t("categories"), "distinct", "category_code"],
  [t("brands"), "distinct", "brand"],
  [t("views"), "event_types", "view"],
  [t("add_to_cart"), "event_types", "cart"],
  [t("purchases"), "event_types", "purchase"],
  [t("eligible_sequences"), "sequence_count"],
  [t("vocabulary_size"), "vocabulary_size"],
];

const PIPELINE = () => [
  [t("raw_csv"), t("read_the_store_events"), "TV1"],
  [t("clean_data"), t("normalize_timestamps_drop_null_sessions_and"), "TV1"],
  [t("monthly_first_seen"), t("record_when_each_product_first_appeared"), "TV1"],
  ["Fit workflow", t("build_the_mapping_and_catalog"), "TV1"],
  [t("build_sequences"), t("keep_up_to_20_products_per"), "TV1"],
  [t("split_sessions"), t("split_training_validation_and_test_by"), "TV1"],
  ["Model", t("train_and_evaluate_the_models"), "TV2 / TV3"],
  ["Top-20", t("export_a_ranked_list_for_each"), "TV2"],
];

export default function Dataset({ state }) {
  const [selected, setSelected] = useState("");
  if (state.error || state.fatal) return <Notice kind="error" title={t("could_not_load_the_dataset_overview")}>{state.error ?? state.fatal}</Notice>;
  const { overview } = state;
  const raw = overview.raw_month;
  const subset = overview.subsets.find((row) => String(row.subset) === selected) ?? overview.subsets[0];
  const weeklySource = overview.subsets.find((row) => row.source)?.source;
  const buckets = histogramBuckets(subset?.session_length_histogram);
  const max = Math.max(0, ...buckets.map((bucket) => bucket.count ?? 0));
  return (
    <>
      {!overview.confirmed_by_tv1 && <Notice kind="warn" title={t("dataset_figures_come_from_the_tv1")} />}
      <section className="panel">
        <h2>{t("e_commerce_dataset")}</h2>
        <p>{t("the_kaggle_ecommerce_dataset_records_activity")} {raw.min_timestamp_utc?.slice(0, 7) ?? t("not_available_yet")}{t("each_event_is_a_view_add")}</p>
        <h3>{t("raw_month")}</h3>
        <dl className="env">
          {[
            [t("rows"), raw.row_count], [t("start_utc"), raw.min_timestamp_utc], [t("end_utc"), raw.max_timestamp_utc],
            [t("missing_brand"), raw.missing?.brand], [t("missing_category"), raw.missing?.category_code],
          ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{formatValue(value)}</dd></div>)}
        </dl>
        <p className="definition">{t("source")} <code>{formatValue(raw.source)}</code></p>
      </section>
      <SubsetSelection sampling={overview.sampling} />
      <FiveVs overview={overview} />
      <section className="panel">
        <h2>{t("weekly_cudf_subsets")}</h2>
        <div className="table-scroll">
          <table className="config-table">
            <thead><tr><th scope="col">{t("metric")}</th>{overview.subsets.map((row) => <th scope="col" key={row.subset}>{row.subset}%</th>)}</tr></thead>
            <tbody>{ROWS().map(([label, field, key]) => <tr key={label}><th scope="row">{label}</th>{overview.subsets.map((row) => <td key={row.subset}>{formatValue(key ? row[field]?.[key] : row[field])}</td>)}</tr>)}</tbody>
          </table>
        </div>
        <p className="definition">{overview.subsets.at(-1)?.subset ?? t("not_available_yet")}{t("covers_the_first_week_of_october")}</p>
        <p className="definition">{t("subset_diversity")}</p>
        <p className="definition">{t("source")} <code>{formatValue(weeklySource)}</code></p>
      </section>
      <section className="panel">
        <h2>{t("session_length")}</h2>
        {subset && <label>{t("subset")} <select aria-label={t("subset")} value={subset.subset} onChange={(event) => setSelected(event.target.value)}>
          {overview.subsets.map((row) => <option key={row.subset} value={row.subset}>{row.subset}%</option>)}
        </select></label>}
        <p className="definition">{t("single_event_sessions_are_dropped_because")}</p>
        {buckets.length ? <>
          <p className="definition">{buckets.at(-1).label} {t("is_the_sum_of_the_longer")}</p>
          <ul className="bars">{buckets.map((bucket, index) => <li key={bucket.label}>
            <span>{bucket.label}</span>
            {bucket.count !== null && <meter className={index === 0 ? "highlight-bar" : ""} min={0} max={max || 1} value={bucket.count} aria-label={t("sessions_of_length_0", bucket.label)} />}
            <span>{formatValue(bucket.count)}</span>
          </li>)}</ul>
        </> : <p>{t("not_available_yet")}</p>}
      </section>
      <section className="panel">
        <h2>{t("processing_pipeline")}</h2>
        <ol className="pipeline">{PIPELINE().map(([label, description, owner]) => <li key={label}><strong>{label}</strong> · {owner}<p>{description}</p></li>)}</ol>
      </section>
      <section className="panel"><EvaluationProtocol protocol={overview.evaluation_protocol} diagram /></section>
      <PipelineMeasurements measurements={overview.pipeline_measurements} />
    </>
  );
}
