import React from "react";
import { t } from "./i18n.js";

const UNIT = "(?:s\\/million events|ms\\/session|MiB|GiB|s)";
/** A metric value as format.js writes it: a decimal ("0.1964", "51.7%", "51.7 s") or a number with a unit ("433 s"). */
const METRIC = new RegExp(`\\d[\\d,]*\\.\\d+(?:%|\\u00A0${UNIT})?|\\d[\\d,]*\\u00A0${UNIT}`, "g");

/** Splits a finding body into text and metric parts; plain counts such as "10%" or "128" stay text. */
export function metricParts(text) {
  const parts = [];
  let last = 0;
  for (const match of String(text).matchAll(METRIC)) {
    if (match.index > last) parts.push({ text: text.slice(last, match.index), metric: false });
    parts.push({ text: match[0], metric: true });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), metric: false });
  return parts;
}

/**
 * "Key finding" callout (TV2 analysis.md, 24/11). Peach-to-white card (styles.css "Key finding callout");
 * metric numbers in the body are bold burnt orange. Not an alert colour: no red, no glass.
 * The headline is optional: it is passed only when the JSON values agree with it (src/findings.js).
 * The source line is shown once per tab (KeyFindingSource), not in every callout.
 */
export function KeyFinding({ finding, level = 3, showLabel = true }) {
  const Heading = `h${level}`;
  return <aside className="key-finding" aria-label={t("key_finding")}>
    {showLabel && <p className="kf-label">{t("key_finding")}</p>}
    {finding.headline && <Heading className="kf-headline">{finding.headline}</Heading>}
    <p className="kf-body">{metricParts(finding.body).map((part, index) => part.metric
      ? <strong key={index} className="kf-num">{part.text}</strong> : <React.Fragment key={index}>{part.text}</React.Fragment>)}</p>
    {finding.caveat && <p className="kf-caveat">{finding.caveat}</p>}
  </aside>;
}

/** One footnote per tab naming where the Key findings come from. */
export function KeyFindingSource() {
  return <p className="definition kf-footnote">{t("kf_source_footnote")}</p>;
}
