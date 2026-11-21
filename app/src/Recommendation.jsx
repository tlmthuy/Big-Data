import { t } from "./i18n.js";
import React, { useMemo, useState } from "react";
import { INVALID_PRODUCT_ID, PROJECT_MODELS, modelKey, modelLabel, sessionContext, usersBySession } from "./data.js";
import EvaluationProtocol from "./EvaluationProtocol.jsx";
import { ProductCard } from "./ProductCard.jsx";
import { categoryHighlights } from "./product.js";
import { DataKindBadge, Issues, Notice } from "./ui.jsx";

function groupLabel(group) {
  const parts = [
    group.subset ?? "subset ?",
    group.split ?? "split ?",
    group.evalPartition !== null ? `partition ${group.evalPartition}` : null,
    `${group.sessionIds.length} session`,
  ].filter(Boolean);
  return parts.join(" · ");
}

/** Options for the model/run selector: every delivered run, plus project models with no output. */
function runOptions(group) {
  const options = group.runs.map((run) => ({
    value: `run:${run.label}`,
    label: group.runs.filter((r) => r.modelKey === run.modelKey).length > 1
      ? `${modelLabel(run.model)} — ${run.label}`
      : modelLabel(run.model),
    run,
  }));
  for (const model of PROJECT_MODELS) {
    if (!group.runs.some((r) => r.modelKey === modelKey(model))) {
      options.push({ value: `missing:${model}`, label: t("0_predictions_pending", model), run: null, model });
    }
  }
  return options;
}

export default function Recommendation({ state, productInfo, protocol }) {
  const { groups = [], issues = [], fatal, error } = state;
  const [groupKey, setGroupKey] = useState("");
  const [choice, setChoice] = useState("");
  const [userId, setUserId] = useState(() => new URLSearchParams(window.location.search).get("user") ?? "");
  const [sessionChoice, setSessionChoice] = useState(() => new URLSearchParams(window.location.search).get("session"));

  const group = groups.find((g) => g.key === groupKey) ?? groups[0];
  const options = group ? runOptions(group) : [];
  const option = options.find((o) => o.value === choice) ?? options[0];

  const sessionUsers = useMemo(() => usersBySession(group), [group]);
  const users = [...new Set(sessionUsers.values())];
  const sessionIds = group?.sessionIds.filter((id) => !userId || sessionUsers.get(id) === userId) ?? [];
  const unknownUser = userId !== "" && !users.includes(userId);
  const unknownSession = sessionChoice !== null && !sessionIds.includes(sessionChoice);
  const sessionId = sessionChoice ?? sessionIds[0] ?? "";

  if (error) return <Notice kind="error" title={t("could_not_load_recommendation_data")}>{error}</Notice>;
  if (fatal) {
    return (
      <>
        <Notice kind="error" title={t("invalid_recommendation_data")}>{fatal}</Notice>
        <Issues issues={issues} />
      </>
    );
  }
  if (!group) return <Notice kind="error" title={t("no_data")}>{t("demo_data_json_contains_no_runs")}</Notice>;

  const selectionError = unknownUser || unknownSession;
  const run = option?.run ?? null;
  const context = sessionContext(group, sessionId);
  const session = run?.sessions.find((s) => s.user_session === sessionId) ?? null;

  const sample = (run ?? group.runs[0]).sample;
  const products = productInfo.products;
  const { matchingIds, summary } = categoryHighlights(
    context.prefix, context.prefixCatalog, session?.recommendations, products,
  );

  const changeGroup = (key) => {
    const next = groups.find((g) => g.key === key);
    setGroupKey(key);
    setUserId("");
    setSessionChoice(null);
    // Keep the same model if the new group has it.
    const keep = next && runOptions(next).find((o) => (o.run?.modelKey ?? modelKey(o.model)) === (option?.run?.modelKey ?? modelKey(option?.model)));
    setChoice(keep?.value ?? "");
  };

  return (
    <>
      <Issues issues={issues} />

      <section className="controls" aria-label={t("choose_data")}>
        <label>{t("session_group")} <select value={group.key} onChange={(e) => changeGroup(e.target.value)}>
            {groups.map((g) => <option key={g.key} value={g.key}>{groupLabel(g)}</option>)}
          </select>
        </label>
        <label>{t("model")} <select aria-label={t("model")} value={option?.value ?? ""} onChange={(e) => setChoice(e.target.value)}>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        {users.length > 0 && (
          <label>{t("users")} <select value={unknownUser ? "" : userId} onChange={(event) => {
              setUserId(event.target.value);
              setSessionChoice(null);
            }}>
              <option value="">{t("all")}</option>
              {users.map((id) => <option value={id} key={id}>{id}</option>)}
            </select>
          </label>
        )}
        <label>{t("session")} <select aria-label={t("session")} value={sessionIds.includes(sessionId) ? sessionId : ""} onChange={(e) => setSessionChoice(e.target.value)}>
            {selectionError && <option value="" disabled>{t("choose_a_session")}</option>}
            {sessionIds.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </label>
      </section>

      <EvaluationProtocol protocol={protocol} />
      <p className="definition">{t("split")} {group.split ?? t("not_available_yet")} {t("partition")} {group.evalPartition ?? t("not_available_yet")}</p>
      {sample && <p className="definition">{t("showing")} {sample.n_selected ?? t("not_available_yet")}/{sample.n_total ?? t("not_available_yet")} {t("sessions_selected_with_a_fixed_seed")} {sample.seed ?? t("not_available_yet")}{t("independently_of_outcome")}</p>}
      {selectionError ? (
        <Notice kind="warn" title={unknownUser ? t("user_not_found") : t("session_not_found")}>
          <p>{unknownUser ? t("user_id_0", userId) : t("session_id_0", sessionChoice)}</p>
          <button type="button" onClick={() => { setUserId(""); setSessionChoice(null); }}>{t("choose_another_session")} </button>
        </Notice>
      ) : (
        <>
          <div className="meta-row">
            <span>{t("model_2")} <strong>{modelLabel(run?.model ?? option?.model)}</strong></span>
            <span>{t("run_id")} <strong>{run?.run_id ?? t("not_available_yet")}</strong></span>
            <span>{t("subset_2")} <strong>{group.subset ?? t("not_available_yet")}</strong></span>
            <span>{t("split_2")} <strong>{group.split ?? t("not_available_yet")}</strong></span>
            <span>{t("catalog")} <strong>{group.catalogSize !== null ? `${group.catalogSize} items` : t("not_available_yet")}</strong></span>
            {run?.catalog_sha256 && <span>{t("catalog_sha_256")} <code>{run.catalog_sha256}</code></span>}
            <span>{t("predictions")} <DataKindBadge kind={(run ?? group.runs[0])?.data_kind} /></span>
            {productInfo.dataKind === "toy" && <span>{t("product_information")} <DataKindBadge kind={productInfo.dataKind} /></span>}
          </div>

          <section className="grid">
            <article className="panel">
              <div className="panel-heading">
                <h2>{t("history")}</h2>
                <span>{context.prefix ? t("0_views", context.prefix.length) : ""}</span>
              </div>
              <p className="definition">{t("products_viewed_before_the_final_item")}</p>
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

            <article className="panel actual-panel">
              <h2>{t("actual_next_item")}</h2>
              {context.target ? <ProductCard id={context.target} products={context.targetCatalog?.has(context.target) ? products : undefined} /> : <p className="missing">{t("not_available_yet")}</p>}
            </article>
          </section>

          <section className="panel recommendations">
            <div className="panel-heading">
              <h2>{t("top_20_recommendations")}</h2>
              <span>{option ? (run ? modelLabel(run.model) : option.model) : ""}</span>
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
              <>
                {session.target && session.target !== INVALID_PRODUCT_ID && (
                  <p className={session.targetRank ? "match" : "miss"}>
                    {session.targetRank ? t("hit_at_rank_0", session.targetRank) : t("not_in_top_20")}
                  </p>
                )}
                {summary && <p className="definition">{summary}</p>}
                <table className="ranking">
                  <thead><tr><th scope="col">{t("rank")}</th><th scope="col">{t("products")}</th><th scope="col">{t("score")}</th></tr></thead>
                  <tbody>
                    {session.recommendations.map((r) => {
                      const isTarget = r.product_id === session.target;
                      const inHistory = session.prefix?.includes(r.product_id);
                      return (
                        <tr className={isTarget ? "hit" : ""} key={`${r.rank}-${r.product_id}`}>
                          <td className="rank">{r.rank}</td>
                          <td>
                            <ProductCard id={r.product_id} products={products} />
                            {isTarget && <span className="tag tag-hit">{t("actual_item")}</span>}
                            {matchingIds.has(r.product_id) && <span className="tag tag-category">{t("same_category")}</span>}
                            {inHistory && <span className="tag tag-history">{t("in_history")}</span>}
                          </td>
                          <td className={r.score === null ? "missing score" : "score"}>{r.score === null ? t("not_available_yet") : r.score}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {!run.scoreAvailable && <p className="definition">{t("ranked_ids_only")}</p>}
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}
