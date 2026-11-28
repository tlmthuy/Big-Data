import { readLanguage, setLanguage, t } from "./i18n.js";
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { loadDeclaredProductInfo, loadJson, normalizeDemo, normalizeProductInfo } from "./data.js";
import Recommendation from "./Recommendation.jsx";
import { routeFromHash } from "./navigation.js";
import Dataset from "./Dataset.jsx";
import { normalizeDataset } from "./dataset.js";
import Experiments from "./Experiments.jsx";
import { AboutDemo, LanguageSwitch, MainNav, PresenterToggle } from "./Nav.jsx";
import { PresenterContext, readPresenter, savePresenter } from "./presenter.js";
import "./styles.css";

const branding = import.meta.glob(["./branding/logo.png", "./branding/cover.jpg"], {
  eager: true, query: "?url", import: "default",
});
const logo = branding["./branding/logo.png"];
const cover = branding["./branding/cover.jpg"];

// Optional overrides for testing broken files, e.g. ?demo=/tests/fixtures/empty.json
// Only same-origin absolute paths are accepted.
function source(param, fallback) {
  if (!import.meta.env.DEV) return fallback;
  const value = new URLSearchParams(window.location.search).get(param);
  return value && value.startsWith("/") && !value.startsWith("//") ? value : fallback;
}
const base = import.meta.env.BASE_URL;
const DEMO_URL = source("demo", `${base}demo-data.json`);
const DATASET_URL = source("dataset", `${base}dataset-overview.json`);
const OFFICIAL_RESULTS_URL = `${base}official-results.json`;

function normalizeOfficialResults(data) {
  return { results: data };
}

function useData(url, normalize, language) {
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    let alive = true;
    loadJson(url).then(({ data, error }) => {
      if (!alive) return;
      setState(error ? { error } : { ...normalize(data), provenance: {
        team_commit: data?.team_commit,
        generated_at: data?.generated_at,
        data_kind: data?.data_kind,
        product_lookup: data?.provenance?.product_lookup,
      } });
    });
    return () => { alive = false; };
  }, [url, normalize, language]);
  return state;
}

function useOptionalProductInfo(url, language) {
  const [state, setState] = useState({});
  useEffect(() => {
    let alive = true;
    setState(url ? { loading: true } : {});
    loadDeclaredProductInfo(url).then(({ data, error, requested }) => {
      if (!alive) return;
      if (!requested) {
        setState({});
        return;
      }
      setState(error ? { error } : { ...normalizeProductInfo(data), provenance: {
        source_file: data?.source_file,
        source_sha256: data?.source_sha256,
        team_commit: data?.team_commit,
        generated_at: data?.generated_at,
        data_kind: data?.data_kind,
      } });
    });
    return () => { alive = false; };
  }, [url, language]);
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
  const [{ tab, experiment, select, section }, setRoute] = useState(currentRoute);
  const [presenter, setPresenter] = useState(() => readPresenter());
  useEffect(() => {
    document.documentElement.classList.toggle("presenter", presenter);
  }, [presenter]);
  function choosePresenter(on) {
    savePresenter(on);
    setPresenter(on);
  }
  const demo = useData(DEMO_URL, normalizeDemo, language);
  const productLookup = demo.provenance?.product_lookup;
  const productsUrl = typeof productLookup === "string" && productLookup.trim()
    ? source("products", `${base}${productLookup}`)
    : null;
  const products = useOptionalProductInfo(productsUrl, language);
  const dataset = useData(DATASET_URL, normalizeDataset, language);
  const officialResults = useData(OFFICIAL_RESULTS_URL, normalizeOfficialResults, language);

  useEffect(() => {
    const onHash = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const state = { recommendation: demo, dataset, experiments: officialResults }[tab];

  return (
    <PresenterContext.Provider value={presenter}>
      <header className="topbar glass">
        <div className="topbar-inner">
        <div className="brand">
          {logo && <img className="brand-logo" src={logo} alt="" />}
          <span className="brand-name"><span className="brand-full">{siteName}</span><span className="brand-short">{t("site_name_short")}</span></span>
        </div>
        <MainNav tab={tab} />
        <div className="header-utility">
          <AboutDemo />
          <PresenterToggle on={presenter} onToggle={choosePresenter} />
          <LanguageSwitch language={language} onChoose={chooseLanguage} />
        </div>
        </div>
      </header>
      <main className="shell">
      {cover && <img className="brand-cover" src={cover} alt="" />}
      <div className="view" id="view">
        {state.loading ? <p className="loading">{t("loading_data")}</p>
          : tab === "recommendation" ? <Recommendation state={state} productInfo={products} protocol={dataset.overview?.evaluation_protocol} official={officialResults.results} />
            : tab === "dataset" ? <Dataset state={state} section={section ?? null} e2Levels={(officialResults.results?.tables?.E2 ?? []).map((row) => row.subset)} />
              : <Experiments key={`${experiment}/${select ?? ""}`} state={state} active={experiment} select={select} />}
      </div>

      <footer>
        <p>{t("values_pending_delivery_show_not_available")}</p>
        <ul>{[
          ["demo-data.json", demo], ["product-info.json", products],
          ["dataset-overview.json", dataset], ["official-results.json", officialResults],
        ].filter(([name, file]) => name !== "product-info.json" || file.provenance?.data_kind === "real").map(([name, file]) => <li key={name}>
          <code>{name}</code> {file.provenance?.source_sha256
            ? t("footer_source_sha", file.provenance.source_file ?? t("not_available_yet"), file.provenance.source_sha256.slice(0, 8), file.provenance.generated_at ?? t("not_available_yet"))
            : <>{t("commit")} {file.provenance?.team_commit ?? t("not_available_yet")} {t("exported")} {file.provenance?.generated_at ?? t("not_available_yet")}</>} · {file.provenance?.data_kind ?? t("not_available_yet")}
        </li>)}</ul>
      </footer>
      </main>
    </PresenterContext.Provider>
  );
}

createRoot(document.getElementById("root")).render(<App />);
