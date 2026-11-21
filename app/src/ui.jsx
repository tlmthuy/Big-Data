import { t } from "./i18n.js";
import React from "react";

export function Notice({ kind = "info", title, children }) {
  return (
    <section className={`notice notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {title && <strong>{title}</strong>}
      {children && <div>{children}</div>}
    </section>
  );
}

export function DataKindBadge({ kind }) {
  if (kind === "toy") return <span className="badge badge-toy" title={t("toy_data_for_checking_the_export")}>{t("toy_data_not_a_benchmark_result")}</span>;
  if (kind === "real") return <span className="badge badge-real">{t("real_data")}</span>;
  return <span className="badge badge-unknown" title={t("artifact_does_not_specify_data_kind")}>{t("data_kind_not_available_yet")}</span>;
}

const statusLabels = () => ({ passed: t("passed"), failed: t("failed"), excluded: t("excluded") });

export function StatusBadge({ status }) {
  if (!status) return <span className="badge badge-unknown">{t("status_not_available_yet")}</span>;
  return <span className={`badge badge-status-${status}`}>{statusLabels()[status] ?? status}</span>;
}

export function Issues({ issues }) {
  if (!issues?.length) return null;
  return (
    <details className="issues">
      <summary>{issues.length} {t("data_warnings")}</summary>
      <ul>{issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
    </details>
  );
}
