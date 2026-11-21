import { readLanguage, setLanguage, t } from "./i18n.js";
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { loadJson, normalizeDemo, normalizeProductInfo, normalizeResults } from "./data.js";
import Recommendation from "./Recommendation.jsx";
import { routeFromHash } from "./navigation.js";
import Dataset from "./Dataset.jsx";
import { normalizeDataset } from "./dataset.js";
import Experiments from "./Experiments.jsx";
import "./styles.css";

const branding = import.meta.glob(["./branding/logo.png", "./branding/cover.jpg"], {
  eager: true, query: "?url", import: "default",
});
const logo = branding["./branding/logo.png"];
const cover = branding["./branding/cover.jpg"];

const TABS = () => [
  { id: "recommendation", label: t("recommendations") },
  { id: "data", label: t("dataset") },
  { id: "experiments", label: t("experiments_e1_e5") },
];

// Optional overrides for testing broken files, e.g. ?demo=/tests/fixtures/empty.json
// Only same-origin absolute paths are accepted.
function source(param, fallback) {
  if (!import.meta.env.DEV) return fallback;
  const value = new URLSearchParams(window.location.search).get(param);
  return value && value.startsWith("/") && !value.startsWith("//") ? value : fallback;
}
const base = import.meta.env.BASE_URL;
const DEMO_URL = source("demo", `${base}demo-data.json`);
const PRODUCTS_URL = source("products", `${base}product-info.json`);
const DATASET_URL = source("dataset", `${base}dataset-overview.json`);
const RESULTS_URL = source("results", `${base}run-results.json`);

function useData(url, normalize, language) {
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    let alive = true;
    loadJson(url).then(({ data, error }) => {
      if (!alive) return;
      setState(error ? { error } : { ...normalize(data), provenance: {
        team_commit: data?.team_commit, generated_at: data?.generated_at, data_kind: data?.data_kind,
      } });
    });
    return () => { alive = false; };
  }, [url, normalize, language]);
  return state;
}

function currentRoute() {
  return routeFromHash(window.location.hash);
}

function App() {
  const [language, updateLanguage] = useState(readLanguage);
  setLanguage(language);
  const siteName = t("site_name");
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = siteName;
  }, [language, siteName]);
  function chooseLanguage(next) {
    try { localStorage.setItem("tv4-language", next); } catch { /* Storage is optional. */ }
    updateLanguage(next);
  }
  const [{ tab, experiment }, setRoute] = useState(currentRoute);
  const demo = useData(DEMO_URL, normalizeDemo, language);
  const products = useData(PRODUCTS_URL, normalizeProductInfo, language);
  const dataset = useData(DATASET_URL, normalizeDataset, language);
  const results = useData(RESULTS_URL, normalizeResults, language);

  useEffect(() => {
    const onHash = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const state = { recommendation: demo, data: dataset, experiments: results }[tab];

  return (
    <main className="shell">
      <header className="topbar">
        <div className="header-utility">
          <div className="language-switch" role="group" aria-label={t("language")}>
            {["en", "vi"].map((code) => <button type="button" key={code}
              aria-pressed={language === code} onClick={() => chooseLanguage(code)}>{code.toUpperCase()}</button>)}
          </div>
        </div>
        <div className="brand">
          {logo && <img className="brand-logo" src={logo} alt="" />}
          <h1>{siteName}</h1>
        </div>
        <nav className="tabs" role="tablist" aria-label={t("views_2")}>
          {TABS().map(({ id, label }) => (
            <a key={id} href={`#${id}`} role="tab" aria-selected={tab === id} className={tab === id ? "active" : ""}>{label}</a>
          ))}
        </nav>
      </header>
      {cover && <img className="brand-cover" src={cover} alt="" />}
      <section className="site-intro" aria-label={t("demo_intro")}>
        <p className="lede">{t("a_session_is_one_visit_an")}</p>
        <p className="definition">{t("recall_20_measures_how_often_the")}</p>
        <p className="definition">{t("popularity_is_the_baseline_all_three")}</p>
        <p className="definition">{t("the_demo_replays_saved_predictions_see")}</p>
      </section>
      <div role="tabpanel">
        {state.loading ? <p className="loading">{t("loading_data")}</p>
          : tab === "recommendation" ? <Recommendation state={state} productInfo={products} protocol={dataset.overview?.evaluation_protocol} /> : tab === "data" ? <Dataset state={state} /> : <Experiments state={state} active={experiment} />}
      </div>

      <footer>
        <p>{t("values_pending_delivery_show_not_available")}</p>
        <ul>{[
          ["demo-data.json", demo], ["product-info.json", products],
          ["dataset-overview.json", dataset], ["run-results.json", results],
        ].map(([name, file]) => <li key={name}>
          <code>{name}</code> {t("commit")} {file.provenance?.team_commit ?? t("not_available_yet")} {t("exported")} {file.provenance?.generated_at ?? t("not_available_yet")} · {file.provenance?.data_kind ?? t("not_available_yet")}
        </li>)}</ul>
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
