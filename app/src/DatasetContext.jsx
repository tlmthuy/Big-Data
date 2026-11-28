import React from "react";
import { formatValue } from "./data.js";
import { t } from "./i18n.js";
import { dateRange, formatDistance } from "./format.js";

function Evidence({ source, short = false }) {
  if (!source) return null;
  return <p className="definition">{t("source")} <code title={source}>{short ? source.split("/").at(-1) : source}</code></p>;
}

export function SubsetSelection({ sampling, subsets, source, distributionSource }) {
  if (!sampling) return null;
  return <section className="panel" id="dataset-subsets">
    <h2>{t("why_subset")}</h2>
    <p>{t("whole_session_sampling", formatValue(sampling.seed))}</p>
    <p>{t("session_sampling_rationale")}</p>
    {(() => { const range = dateRange(sampling.scope, { endExclusive: true });
      return <p>{t("sampling_scope", range?.start ?? t("MISSING"), range?.end ?? t("MISSING"), formatValue(sampling.population_sessions))}</p>; })()}
    <p>{t("subset_diversity")}</p>
    <div className="table-scroll"><table className="config-table numeric-table">
      <thead><tr>{[t("target_percent"), t("actual_raw_session_pct"), t("raw_sessions")].map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{subsets.map((row) => <tr key={row.subset_session_threshold_pct}>
        <th scope="row">{formatValue(row.subset_session_threshold_pct)}%</th>
        <td className="num" title={String(row.actual_raw_session_pct)}>{formatValue(row.actual_raw_session_pct)}</td>
        <td className="num" title={String(row.raw_sessions)}>{formatValue(row.raw_sessions)}</td>
      </tr>)}</tbody>
    </table></div>
    <Evidence source={sampling.source} />
    <Evidence source={source} />
    <Evidence source={distributionSource} />
    <div className="table-scroll dataset-tv-table"><table className="config-table numeric-table">
      <thead><tr>{[t("subset"), t("length_tv_vs_100"), t("event_tv_vs_100")].map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{subsets.map((row) => <tr key={row.subset}><th scope="row">{formatValue(row.subset)}%</th>
        {["length_TV_vs_100", "event_TV_vs_100"].map((field) => { const cell = formatDistance(row[field]); return <td key={field} className="num" title={cell.raw}>{cell.text}</td>; })}
      </tr>)}</tbody>
    </table></div>
    <p>{t("tv_distance_explanation")}</p>
    <Evidence source={distributionSource} />
  </section>;
}

export function FiveVs({ overview }) {
  const { raw_month: raw, sampling, cleanup_reference: cleanup, raw_schema: schema, evaluation_protocol: protocol } = overview;
  const cards = [
    ["volume", t("volume_facts", formatValue(raw.row_count), formatValue(sampling?.input_bytes)), [raw.source, sampling?.source]],
    ["velocity", t("velocity_facts", formatValue(overview.subsets.find((row) => row.subset === 100)?.last_partition_D)), [overview.supplementary_sources?.split_population]],
    ["variety", t("variety_facts", formatValue(schema?.columns), formatValue(raw.distinct?.event_type), formatValue(raw.distinct?.category_code), formatValue(raw.distinct?.brand)), [schema?.source, raw.source]],
    ["veracity", t("veracity_facts", formatValue(raw.missing?.brand), formatValue(raw.missing?.category_code), formatValue(raw.invalid_timestamps), formatValue(cleanup?.consecutive_repeat_rows_removed)), [raw.source, cleanup?.source]],
    ["value", t("value_facts", formatValue(protocol?.top_k)), [protocol?.source]],
  ];
  return <section className="panel" id="dataset-5v">
    <h2>{t("five_vs")}</h2>
    <div className="dataset-cards">{cards.map(([key, text, sources]) => <article key={key}>
      <h3>{t(key)}</h3><p>{text}</p>
      {sources.filter(Boolean).map((source) => <Evidence key={source} source={source} short />)}
    </article>)}</div>
  </section>;
}
