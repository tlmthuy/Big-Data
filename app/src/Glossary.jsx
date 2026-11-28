import React from "react";
import { t } from "./i18n.js";
import { Popover } from "./Nav.jsx";

/**
 * ⓘ glossary terms. Definitions follow docs/CONTEXT.md, the data contract and the team's
 * model protocol (docs/modeling/model_protocol.md, next_item_problem.md); see docs/CONTEXT.md.
 */
export const GLOSSARY_TERMS = ["session", "history", "top20", "hit", "recall", "ndcg", "validation"];

export function Glossary({ term, align = "start" }) {
  return <Popover className="glossary" align={align} label={t("glossary_label", t(`glossary_${term}_term`))}
    buttonText={<span className="info-dot" aria-hidden="true">i</span>}>
    <strong>{t(`glossary_${term}_term`)}</strong>
    <span className="popover-text">{t(`glossary_${term}`)}</span>
  </Popover>;
}
