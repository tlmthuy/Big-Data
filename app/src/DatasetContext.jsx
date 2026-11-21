import React from "react";
import { exactValue, formatValue } from "./data.js";
import { t } from "./i18n.js";

function Evidence({ source }) {
  return source ? <p className="definition">{t("source")} <code>{source}</code></p> : null;
}

export function SubsetSelection({ sampling }) {
  if (!sampling) return null;
  return <section className="panel">
    <h2>{t("why_subset")}</h2>
    <p>{t("whole_session_sampling", formatValue(sampling.seed))}</p>
    <p>{t("sampling_scope", formatValue(sampling.population_sessions))}</p>
    <div className="table-scroll"><table className="config-table">
      <thead><tr>{["target_percent", "actual_session_ratio", "sessions"].map((key) => <th scope="col" key={key}>{t(key)}</th>)}</tr></thead>
      <tbody>{sampling.outputs.map((row) => <tr key={row.percent}>
        <th scope="row">{formatValue(row.percent)}%</th>
        <td>{exactValue(row.actual_session_ratio)}</td>
        <td>{formatValue(row.session_count)}</td>
      </tr>)}</tbody>
    </table></div>
    <Evidence source={sampling.source} />
  </section>;
}

export function FiveVs({ overview }) {
  const { raw_month: raw, sampling, cleanup_reference: cleanup, raw_schema: schema, evaluation_protocol: protocol } = overview;
  const cards = [
    ["volume", t("volume_facts", formatValue(raw.row_count), formatValue(sampling?.input_bytes)), [raw.source, sampling?.source]],
    ["velocity", t("velocity_facts"), [raw.source, protocol?.source]],
    ["variety", t("variety_facts", formatValue(schema?.columns), formatValue(raw.distinct?.event_type), formatValue(raw.distinct?.category_code), formatValue(raw.distinct?.brand)), [schema?.source, raw.source]],
    ["veracity", t("veracity_facts", formatValue(raw.missing?.brand), formatValue(raw.missing?.category_code), formatValue(raw.invalid_timestamps), formatValue(cleanup?.consecutive_repeat_rows_removed)), [raw.source, cleanup?.source]],
    ["value", t("value_facts", formatValue(protocol?.top_k)), [protocol?.source]],
  ];
  return <section className="panel">
    <h2>{t("five_vs")}</h2>
    <p className="definition">{t("draft_wording")}</p>
    <div className="dataset-cards">{cards.map(([key, text, sources]) => <article key={key}>
      <h3>{t(key)}</h3><p>{text}</p>
      {sources.filter(Boolean).map((source) => <Evidence key={source} source={source} />)}
    </article>)}</div>
  </section>;
}
