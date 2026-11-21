import { t } from "./i18n.js";
import { createElement } from "react";

export function visiblePipelineMeasurements(measurements) {
  return measurements?.show === true ? measurements : null;
}

export function PipelineMeasurementBadge({ measurements }) {
  return visiblePipelineMeasurements(measurements)
    ? createElement("span", { className: "tag tag-diff preliminary-badge" }, t("smoke_awaiting_tv2_confirmation"))
    : null;
}
