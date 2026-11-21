import React from "react";
import { formatValue } from "./data.js";
import { t } from "./i18n.js";

export default function EvaluationProtocol({ protocol, diagram = false }) {
  return <div className="definition">
    <strong>{t("how_this_is_evaluated")}</strong>
    <p>{t("evaluation_protocol", formatValue(protocol?.split_ratio), formatValue(protocol?.seed), formatValue(protocol?.top_k))}</p>
    {diagram && <p>{t("evaluation_flow")}</p>}
  </div>;
}
