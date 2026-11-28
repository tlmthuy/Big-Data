import { t } from "./i18n.js";
import React, { useState } from "react";
import { firstAllModelHitSession, formatValue, INVALID_PRODUCT_ID, modelKey, modelLabel, sessionContext } from "./data.js";
import { buildE1View } from "./e1.js";
import { dateRange, formatCount, formatScore } from "./format.js";
import EvaluationProtocol from "./EvaluationProtocol.jsx";
import { ProductCard } from "./ProductCard.jsx";
import { DataKindBadge, DataLoadFailure, Issues, Notice, Select } from "./ui.jsx";
import { experimentHref } from "./navigation.js";
import { Glossary } from "./Glossary.jsx";
import { useStickyBar } from "./sticky.js";

/** Same cells as the E1 table, so the strip and the table always agree. */
export function e1StripRows(official) {
  if (!official?.tables?.E1?.length) return [];
  const view = buildE1View(official);
  const recall = view.rows.find((row) => row.field === "Recall@20");
  const ndcg = view.rows.find((row) => row.field === "NDCG@20");
  return view.models.map(({ label }, index) => ({ label, recall: recall.cells[index], ndcg: ndcg.cells[index] }));
}

const basename = (value) => (typeof value === "string" && value ? value.split("/").at(-1) : null);

/** Model colour key for CSS (--model-popularity, --model-gru, --model-xlnet). */
export function modelColourKey(model) {
  const key = modelKey(modelLabel(model));
  return ["popularity", "gru", "xlnet"].includes(key) ? key : "unknown";
}

function HitSentence({ session }) {
  if (!session?.recommendations || !session.target || session.target === INVALID_PRODUCT_ID) return null;
  const size = session.recommendations.length;
  return session.targetRank
    ? <p className="hit-sentence match"><span className="outcome-icon" aria-hidden="true">✓</span><span>{t("hit_sentence", session.targetRank, size)}</span><Glossary term="hit" align="end" /></p>
    : <p className="hit-sentence miss"><span className="outcome-icon" aria-hidden="true">✕</span><span>{t("miss_sentence", size)}</span><Glossary term="hit" align="end" /></p>;
}

function MethodDetails({ run, group, protocol, sample, count, hasProducts, productWindow }) {
  const week = dateRange(productWindow);
  const p = run?.provenance ?? {};
  const rows = [
    [t("run_id_label"), run?.run_id],
    [t("predictions_file"), basename(p.predictions_path)],
    [t("predictions_sha256"), p.predictions_sha256],
    [t("catalog_file"), basename(p.catalog_path)],
    [t("catalog_sha256_full"), run?.catalog_sha256 ?? p.catalog_sha256],
    [t("catalog_size_label"), run?.catalogSize == null ? null : formatCount(run.catalogSize).text],
    [t("eval_partition_label"), group?.evalPartition],
  ];
  return <details className="method-details glass">
    <summary>{t("method_details_and_sources")}</summary>
    <p>{t("recall_20_measures_how_often_the")}</p>
    <EvaluationProtocol protocol={protocol} />
    <p>{t("sample_hash_explanation", sample?.seed ?? "—", formatValue(count))}</p>
    {!run?.scoreAvailable && <p>{t("models_export_ranked_ids_only")}</p>}
    {hasProducts && <p>{t("product_details_note", week?.start ?? t("MISSING"), week?.end ?? t("MISSING"), run?.subset ?? t("MISSING"))}</p>}
    <dl className="env method-sources">{rows.map(([label, value]) => <div key={label}>
      <dt>{label}</dt><dd title={value == null ? undefined : String(value)}>{value == null || value === "" ? t("not_available_yet") : String(value)}</dd>
    </div>)}</dl>
  </details>;
}

export default function Recommendation({ state, productInfo, protocol, official }) {
  const { groups = [], issues = [], fatal, error } = state;
  const [choice, setChoice] = useState("");
  const [sessionChoice, setSessionChoice] = useState(() => new URLSearchParams(window.location.search).get("session"));
  const [linked, setLinked] = useState(false);
  const sticky = useStickyBar();

  const group = groups[0];
  const runs = group?.runs ?? [];
  const run = runs.find((r) => r.label === choice) ?? runs[0] ?? null;

  const sessionIds = group?.sessionIds ?? [];
  const unknownSession = sessionChoice !== null && !sessionIds.includes(sessionChoice);
  const sessionId = sessionChoice ?? sessionIds[0] ?? "";

  if (error) return <DataLoadFailure title={t("could_not_load_recommendation_data")} detail={error} />;
  if (fatal) {
    return (
      <>
        <DataLoadFailure title={t("invalid_recommendation_data")} detail={fatal} />
        <Issues issues={issues} />
      </>
    );
  }
  if (!group) return <Notice kind="error" title={t("no_data")}>{t("demo_data_json_contains_no_runs")}</Notice>;

  const context = sessionContext(group, sessionId);
  const session = run?.sessions.find((s) => s.user_session === sessionId) ?? null;
  const strip = e1StripRows(official).find((row) => modelKey(row.label) === modelKey(modelLabel(run?.model)));
  const sample = run?.sample;
  const count = sample?.n_selected ?? sessionIds.length;
  const total = sample?.n_total ?? sessionIds.length;
  const products = productInfo?.dataKind === "real" ? productInfo.products : undefined;
  const presenterHit = firstAllModelHitSession(group);
  const isHit = Boolean(session?.targetRank);
  const linkProps = isHit ? {
    tabIndex: 0,
    onMouseEnter: () => setLinked(true), onMouseLeave: () => setLinked(false),
    onFocus: () => setLinked(true), onBlur: () => setLinked(false),
  } : {};

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">{t("recommendations")}</h1>
        {run?.data_kind === "real"
          ? <span className="badge badge-real">{t("real_e1_badge", formatValue(count), formatValue(total))}</span>
          : <DataKindBadge kind={run?.data_kind} />}
      </div>
      <Issues issues={issues} />

      <div ref={sticky.sentinel} className="sticky-sentinel" aria-hidden="true" />
      <section ref={sticky.bar} className={`control-bar glass subbar${sticky.stuck ? " is-stuck" : ""}`} aria-label={t("choose_data")}>
        <div className="control-group">
          <span className="control-label" id="model-label">{t("model")}</span>
          <div className="segmented model-picker" role="group" aria-labelledby="model-label">
            {runs.map((r) => <button type="button" key={r.label} aria-pressed={r === run} onClick={() => setChoice(r.label)}>
              <span className={`model-dot model-${modelColourKey(r.model)}`} aria-hidden="true" />{modelLabel(r.model)}
            </button>)}
          </div>
        </div>
        <label className="control-group">
          <span className="control-label">{t("session")} <Glossary term="session" /></span>
          <Select aria-label={t("session")} value={sessionIds.includes(sessionId) ? sessionId : ""} onChange={(e) => setSessionChoice(e.target.value)}>
            {unknownSession && <option value="" disabled>{t("choose_a_session")}</option>}
            {sessionIds.map((id) => <option key={id} value={id}>{id}</option>)}
          </Select>
        </label>
        {presenterHit && <button type="button" className="presenter-tip" onClick={() => setSessionChoice(presenterHit)}
          aria-label={t("presenter_tip_aria", presenterHit, runs.length)}>
          {t("presenter_tip", presenterHit, runs.length)}
        </button>}
      </section>

      {unknownSession ? (
        <Notice kind="warn" title={t("session_not_found")}>
          <p>{t("session_id_0", sessionChoice)}</p>
          <button type="button" onClick={() => setSessionChoice(null)}>{t("choose_another_session")} </button>
        </Notice>
      ) : (
        <>
          <section className="result-row">
            <article className="panel history-panel">
              <div className="panel-heading">
                <h2>{t("history")} <Glossary term="history" /></h2>
                <span>{context.prefix ? t("0_interactions", context.prefix.length) : ""}</span>
              </div>
              {context.prefix ? (
                <ol className="history" aria-label={t("history")}>
                  {context.prefix.map((id, index) => (
                    <li key={index}>
                      {index > 0 && <span className="arrow" aria-hidden="true">→</span>}
                      <ProductCard id={id} products={context.prefixCatalog?.has(id) ? products : undefined} />
                    </li>
                  ))}
                </ol>
              ) : <p className="missing">{t("not_available_yet")}</p>}
            </article>

            <article className={`panel actual-panel${isHit ? " is-hit" : ""}${linked ? " is-linked" : ""}`} {...linkProps}
              aria-describedby={isHit ? "hit-row" : undefined}>
              <h2>{t("actual_next_item")}</h2>
              {context.target ? <ProductCard id={context.target} products={context.targetCatalog?.has(context.target) ? products : undefined} /> : <p className="missing">{t("not_available_yet")}</p>}
              <HitSentence session={session} />
            </article>
          </section>

          <section className="panel recommendations">
            <div className="panel-heading">
              <h2>{t("top_20_recommendations")} <Glossary term="top20" /></h2>
              {run && <span className={`model-badge model-${modelColourKey(run.model)}`}><span className="model-dot" aria-hidden="true" />{modelLabel(run.model)}</span>}
            </div>

            {!run ? (
              <div className="empty-state" role="status">
                <strong>{t("no_predictions_available_for_this_model")}</strong>
              </div>
            ) : !session ? (
              <div className="empty-state" role="status">
                <strong>{t("not_available_yet")}</strong>
                <p>{t("run")} {run.label} {t("does_not_contain_session")} {sessionId}.</p>
              </div>
            ) : !session.recommendations ? (
              <div className="empty-state" role="status">
                <strong>{t("not_available_yet")}</strong>
                <p>{t("the_recommendations_for_this_session_are")}</p>
              </div>
            ) : (
              <table className="ranking">
                <thead><tr><th scope="col">{t("rank")}</th><th scope="col">{t("products")}</th>{run.scoreAvailable && <th scope="col" className="score-col">{t("score")}</th>}</tr></thead>
                <tbody>
                  {session.recommendations.map((r) => {
                    const isTarget = r.product_id === session.target;
                    const inHistory = session.prefix?.includes(r.product_id);
                    const classes = [isTarget && "hit is-hit", isTarget && linked && "is-linked", inHistory && "in-history"].filter(Boolean).join(" ");
                    return (
                      <tr className={classes || undefined} key={`${r.rank}-${r.product_id}`} id={isTarget ? "hit-row" : undefined} {...(isTarget ? linkProps : {})}>
                        <td className="rank">{r.rank}</td>
                        <td>
                          <span className="ranking-item">
                            <ProductCard id={r.product_id} products={products} />
                            {isTarget && <span className="tag tag-hit"><span aria-hidden="true">✓ </span>{t("actual_next_item")}</span>}
                            {inHistory && <span className="tag tag-history">{t("in_history")}</span>}
                          </span>
                        </td>
                        {run.scoreAvailable && (r.score === null
                          ? <td className="missing score">{t("not_available_yet")}</td>
                          : <td className="score num" title={formatScore(r.score).raw}>{formatScore(r.score).text}</td>)}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}

      {strip && <section className={`e1-strip model-${modelColourKey(run?.model)}`} aria-label={t("official_e1_metrics")}>
        <span className="model-dot" aria-hidden="true" />
        <strong>{t("e1_strip_title", strip.label, formatValue(count))}</strong>
        <span title={strip.recall.raw}>{t("e1_recall_20")} <b className="num">{strip.recall.text}</b></span><Glossary term="recall" />
        <span title={strip.ndcg.raw}>{t("e1_ndcg_20")} <b className="num">{strip.ndcg.text}</b></span><Glossary term="ndcg" />
        <a href={experimentHref("E1")}>{t("open_e1")}</a>
      </section>}

      <MethodDetails run={run} group={group} protocol={protocol} sample={sample} count={count} hasProducts={Boolean(products?.size)} productWindow={productInfo?.window} />
    </>
  );
}
