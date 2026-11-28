// Server-renders every tab and E1–E5 panel in EN and VI through Vite's SSR loader.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createServer } from "vite";
import React from "react";
import * as dom from "react-dom/server";
import { fileURLToPath } from "node:url";

const json = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const demo = json("../public/demo-data.json");
const overview = json("../public/dataset-overview.json");
const official = json("../public/official-results.json");

let server;
let load;
before(async () => {
  globalThis.window ??= { location: { search: "", hash: "" } };
  server = await createServer({ root: fileURLToPath(new URL("..", import.meta.url)), logLevel: "error", server: { middlewareMode: true, hmr: false }, appType: "custom" });
  load = (path) => server.ssrLoadModule(path);
});
after(() => server?.close());

async function modules() {
  const [i18n, data, dataset, rec, ds, exp] = await Promise.all([
    load("/src/i18n.js"), load("/src/data.js"), load("/src/dataset.js"),
    load("/src/Recommendation.jsx"), load("/src/Dataset.jsx"), load("/src/Experiments.jsx"),
  ]);
  return { React, dom, i18n, data, dataset, Recommendation: rec.default, e1StripRows: rec.e1StripRows, Dataset: ds.default, Experiments: exp.default };
}

const text = (html) => html.replace(/<[^>]+>/g, " ").replace(/&[a-z#0-9]+;/gi, " ");


function renderAll(m, locale) {
  m.i18n.setLanguage(locale);
  const h = m.React.createElement;
  const render = (el) => m.dom.renderToStaticMarkup(el);
  const pages = {
    recommendation: render(h(m.Recommendation, { state: m.data.normalizeDemo(demo), productInfo: {}, protocol: overview.evaluation_protocol, official })),
    dataset: render(h(m.Dataset, { state: m.dataset.normalizeDataset(overview) })),
  };
  for (const id of ["E1", "E2", "E3", "E4", "E5"]) pages[id] = render(h(m.Experiments, { state: { results: official }, active: id }));
  return pages;
}

test("no i18n key name appears verbatim on any tab or panel (EN and VI)", async () => {
  const m = await modules();
  // A key whose translation is the key itself labels a package field on purpose (e.g. source_metrics).
  const keys = Object.keys(m.i18n.messages.en).filter((key) => /_|^[A-Z]+$/.test(key)
    && m.i18n.messages.en[key] !== key && m.i18n.messages.vi[key] !== key);
  for (const locale of ["en", "vi"]) {
    for (const [name, html] of Object.entries(renderAll(m, locale))) {
      const tokens = new Set(text(html).split(/[\s:·,;()→]+/u));
      const leaked = keys.filter((key) => tokens.has(key));
      assert.deepEqual(leaked, [], `${locale}/${name}`);
    }
  }
  // A lookup of an undefined key renders the key name itself (e.g. note_E5_derived_from_E2).
  assert.deepEqual([...m.i18n.missingKeys], [], "t() called with undefined keys");
});

test("E5 derived-from-E2 note is translated, cites metrics.json, and follows the flag", async () => {
  const m = await modules();
  const h = m.React.createElement;
  for (const locale of ["en", "vi"]) {
    m.i18n.setLanguage(locale);
    const shown = text(m.dom.renderToStaticMarkup(h(m.Experiments, { state: { results: official }, active: "E5" })));
    assert.ok(shown.includes(m.i18n.t("note_E5_derived_from_E2")), locale);
    assert.ok(shown.includes("metrics.json → E5_aggregation_only"), locale);
    assert.ok(!shown.includes("data_dictionary.json → E5_derived_from_E2"), locale);
    const hidden = text(m.dom.renderToStaticMarkup(h(m.Experiments, { state: { results: { ...official, E5_aggregation_only: false } }, active: "E5" })));
    assert.ok(!hidden.includes(m.i18n.t("note_E5_derived_from_E2")), locale);
  }
});

test("shipped predictions: no Score column, one ranked-IDs note", async () => {
  const m = await modules();
  for (const locale of ["en", "vi"]) {
    const html = renderAll(m, locale).recommendation;
    assert.ok(!html.includes("score-col") && !html.includes('class="missing score"'), locale);
    assert.equal(html.split(m.i18n.t("models_export_ranked_ids_only")).length - 1, 1, locale);
  }
});

test("exported scores are shown with the shared formatter; null scores show the missing text", async () => {
  const m = await modules();
  m.i18n.setLanguage("en");
  const h = m.React.createElement;
  const html = m.dom.renderToStaticMarkup(h(m.Recommendation, { state: m.data.normalizeDemo(json("./fixtures/scored.json")), productInfo: {}, official }));
  assert.ok(html.includes("score-col"));
  assert.match(html, /<td class="score num"[^>]*>0\.8125<\/td>/);
  assert.match(html, /<td class="score num"[^>]*>0\.03125<\/td>/);
  assert.match(html, /<td class="missing score">Not available yet<\/td>/);
  assert.ok(!html.includes(m.i18n.t("models_export_ranked_ids_only")));
});

test("E1 strip shows the selected model via the shared formatter and never prints NaN", async () => {
  const m = await modules();
  m.i18n.setLanguage("en");
  const rows = m.e1StripRows(official);
  assert.deepEqual(rows.map((row) => [row.label, row.recall.text]), [["Popularity", "0.0868"], ["GRU", "0.0883"], ["XLNet", "0.1249"]]);
  const html = m.dom.renderToStaticMarkup(m.React.createElement(m.Recommendation, { state: m.data.normalizeDemo(demo), productInfo: {}, official }));
  const strip = html.slice(html.indexOf('<section class="e1-strip'), html.indexOf("</section>", html.indexOf('<section class="e1-strip')));
  assert.ok(strip.includes('Recall@20 <b class="num">0.0868</b>'), "first model in the sample is Popularity");
  assert.ok(strip.includes('href="#experiments/e1"'));
  const broken = structuredClone(official);
  delete broken.tables.E1.find((row) => row.model === "Popularity")["Recall@20"];
  const brokenHtml = m.dom.renderToStaticMarkup(m.React.createElement(m.Recommendation, { state: m.data.normalizeDemo(demo), productInfo: {}, official: broken }));
  assert.ok(!brokenHtml.includes("NaN"));
  assert.ok(brokenHtml.includes(`Recall@20 <b class="num">${m.i18n.t("not_available_yet")}</b>`));
});

test("navigation is links with exactly one aria-current page per nav, and no tab roles", async () => {
  const [nav, exp] = await Promise.all([load("/src/Nav.jsx"), load("/src/Experiments.jsx")]);
  const i18n = await load("/src/i18n.js");
  const count = (html, pattern) => (html.match(pattern) ?? []).length;
  for (const locale of ["en", "vi"]) {
    i18n.setLanguage(locale);
    for (const tab of ["recommendation", "dataset", "experiments"]) {
      const html = dom.renderToStaticMarkup(React.createElement(nav.MainNav, { tab }));
      assert.equal(count(html, /aria-current="page"/g), 1, `${locale}/${tab}`);
      assert.match(html, new RegExp(`<a href="#${tab}" aria-current="page"`));
      assert.ok(!/role="tab/.test(html));
    }
    for (const active of ["E1", "E2", "E3", "E4", "E5"]) {
      const html = dom.renderToStaticMarkup(React.createElement(exp.default, { state: { results: official }, active }));
      const subnav = html.slice(html.indexOf("<nav"), html.indexOf("</nav>"));
      assert.equal(count(subnav, /aria-current="page"/g), 1, `${locale}/${active}`);
      assert.match(subnav, new RegExp(`href="#experiments/${active.toLowerCase()}" aria-current="page"`));
      assert.ok(subnav.includes(`<span class="subtab-label"><strong>${active}</strong> · ${i18n.t(`experiment_nav_${active.toLowerCase()}`)}</span>`));
    }
  }
  const sources = ["main.jsx", "Nav.jsx", "Experiments.jsx", "Recommendation.jsx", "Dataset.jsx", "ui.jsx"]
    .map((file) => readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8")).join("\n");
  assert.ok(!/role="tab(list|panel)?"/.test(sources), "no role=tab, tablist or tabpanel in src/");
});

test("one colour, one meaning: neutral history tag, accent chart, shared hit marker", async () => {
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const rule = (selector) => {
    const start = css.indexOf(`\n${selector} {`) + 1;
    assert.ok(start > 0, `missing rule ${selector}`);
    return css.slice(start, css.indexOf("}", start));
  };
  assert.ok(!/--danger|--caution|--positive/.test(rule(".tag-history")), "history tag must be neutral");
  assert.match(rule(".tag-history"), /var\(--fill\)/);
  for (const selector of [".chart-line", ".chart-point", ".bar"]) {
    assert.match(rule(selector), /var\(--model-colour/, `${selector} uses the fixed model colour`);
    assert.ok(!/--danger|--positive|--accent\)/.test(rule(selector)), selector);
  }
  assert.match(rule(".ranking tr.is-hit td"), /var\(--positive-bg\)/);
  assert.match(rule(".ranking tr.is-hit .rank"), /font-weight: 700/);
  assert.match(css, /@media \(forced-colors: active\) \{\n  \.ranking tr\.is-hit td, \.actual-panel\.is-hit \{ forced-color-adjust: none; background: Mark; color: MarkText; \}/);
  assert.match(rule(".ranking tr.is-hit td:first-child"), /inset 4px 0 0 var\(--positive\)/);
  assert.match(rule(".actual-panel.is-hit"), /inset 4px 0 0 var\(--positive\)/);
  assert.match(rule(".miss"), /var\(--label-2\)/, "a miss is neutral, not a problem colour");
  assert.ok(!/--danger/.test(rule(".miss")));

  const i18n = await load("/src/i18n.js");
  const data = await load("/src/data.js");
  const { default: Recommendation } = await load("/src/Recommendation.jsx");
  i18n.setLanguage("en");
  const render = (session) => {
    globalThis.window.location.search = `?session=${session}`;
    try {
      return dom.renderToStaticMarkup(React.createElement(Recommendation, { state: data.normalizeDemo(demo), productInfo: {}, official }));
    } finally {
      globalThis.window.location.search = "";
    }
  };
  const hit = render("21546");
  assert.match(hit, /<article class="panel actual-panel is-hit"/);
  assert.equal((hit.match(/<tr class="hit is-hit/g) ?? []).length, 1);
  assert.ok(text(hit).includes(i18n.t("hit_sentence", 7, 20)));
  assert.ok(hit.includes(`<span class="tag tag-hit"><span aria-hidden="true">✓ </span>${i18n.t("actual_next_item")}</span>`));
  const miss = render("46465");
  assert.ok(!miss.includes("is-hit"));
  assert.ok(miss.includes('<p class="hit-sentence miss">'));
  assert.ok(text(miss).includes(i18n.t("miss_sentence", 20)));
});

test("Recommendation: order, presenter tip computed from data, closed method details, translated dataset labels", async () => {
  const i18n = await load("/src/i18n.js");
  const data = await load("/src/data.js");
  const ds = await load("/src/dataset.js");
  const { default: Recommendation } = await load("/src/Recommendation.jsx");
  const { default: Dataset } = await load("/src/Dataset.jsx");
  const expected = data.firstAllModelHitSession(data.normalizeDemo(demo).groups[0]);
  assert.ok(expected, "the shipped sample has an all-model hit session");
  for (const locale of ["en", "vi"]) {
    i18n.setLanguage(locale);
    const html = dom.renderToStaticMarkup(React.createElement(Recommendation, { state: data.normalizeDemo(demo), productInfo: {}, official }));
    const order = ['class="page-head"', 'class="control-bar glass subbar', 'class="panel history-panel"', 'class="panel actual-panel', 'class="ranking"', 'class="e1-strip', 'class="method-details glass"'].map((marker) => html.indexOf(marker));
    assert.ok(order.every((index) => index >= 0), `${locale}: every section rendered`);
    assert.deepEqual([...order].sort((a, b) => a - b), order, `${locale}: sections in the agreed order`);
    assert.ok(text(html).includes(i18n.t("presenter_tip", expected, 3)), locale);
    assert.ok(!/<details class="method-details glass" open/.test(html), "method details closed by default");
    assert.equal((html.match(/class="badge /g) ?? []).length, 1, "exactly one data badge");
    assert.ok(text(html).includes(i18n.t("real_e1_badge", "30", "1,337")), locale);
    const dataset = text(dom.renderToStaticMarkup(React.createElement(Dataset, { state: ds.normalizeDataset(overview) })));
    for (const key of ["product_categories_by_category_id", "pipeline_fit_workflow", "pipeline_model", "pipeline_top_20"]) {
      assert.ok(dataset.includes(i18n.t(key)), `${locale}: ${key}`);
    }
    assert.ok(!dataset.includes("categories (category_id)"), locale);
  }
  const noHit = structuredClone(demo);
  for (const run of noHit.runs) for (const session of run.sessions) session.top20 = session.top20.filter((id) => id !== session.target);
  for (const run of noHit.runs) for (const session of run.sessions) delete session.target_rank;
  const html = dom.renderToStaticMarkup(React.createElement(Recommendation, { state: data.normalizeDemo(noHit), productInfo: {}, official }));
  assert.ok(!html.includes("presenter-tip"), "no tip when no session is a hit for every model");
});

test("presenter tip follows the data: fixture with a known all-hit session", async () => {
  const i18n = await load("/src/i18n.js");
  const data = await load("/src/data.js");
  const { default: Recommendation } = await load("/src/Recommendation.jsx");
  i18n.setLanguage("en");
  const fixture = structuredClone(demo);
  // Make the 5th session (sample order) the first all-model hit by placing its target at rank 3 for every model
  // and removing the target from every earlier session.
  const ids = fixture.runs[0].sessions.map((session) => session.user_session);
  for (const run of fixture.runs) for (const session of run.sessions) {
    const index = ids.indexOf(session.user_session);
    session.top20 = session.top20.filter((id) => id !== session.target);
    if (index === 4) session.top20.splice(2, 0, session.target);
    session.top20 = session.top20.slice(0, 20);
    delete session.target_rank;
  }
  const group = data.normalizeDemo(fixture).groups[0];
  assert.equal(data.firstAllModelHitSession(group), ids[4]);
  const html = dom.renderToStaticMarkup(React.createElement(Recommendation, { state: data.normalizeDemo(fixture), productInfo: {}, official }));
  assert.ok(text(html).includes(i18n.t("presenter_tip", ids[4], 3)));
  const source = readFileSync(new URL("../src/Recommendation.jsx", import.meta.url), "utf8");
  assert.ok(!/21546/.test(source), "the tip session is never hard-coded");
});

test("main result area: no category matching, interactions wording, history and actual item always shown", async () => {
  const i18n = await load("/src/i18n.js");
  const data = await load("/src/data.js");
  const { default: Recommendation } = await load("/src/Recommendation.jsx");
  for (const locale of ["en", "vi"]) {
    i18n.setLanguage(locale);
    const html = dom.renderToStaticMarkup(React.createElement(Recommendation, { state: data.normalizeDemo(demo), productInfo: {}, official }));
    const main = text(html.slice(0, html.indexOf('<details class="method-details')));
    for (const banned of ["Same category", "categorized recommendations match", "Cùng danh mục", "Products viewed", "views"]) {
      assert.ok(!main.includes(banned), `${locale}: ${banned}`);
    }
    assert.ok(main.includes(i18n.t("history")) && main.includes(i18n.t("actual_next_item")), locale);
  }
});

test("glossary: every term is defined in EN and VI and appears as an accessible ⓘ button", async () => {
  const i18n = await load("/src/i18n.js");
  const data = await load("/src/data.js");
  const glossary = await load("/src/Glossary.jsx");
  const { default: Recommendation } = await load("/src/Recommendation.jsx");
  const { default: Experiments } = await load("/src/Experiments.jsx");
  for (const term of glossary.GLOSSARY_TERMS) {
    for (const locale of ["en", "vi"]) {
      assert.ok(i18n.messages[locale][`glossary_${term}`], `${locale}: glossary_${term}`);
      assert.ok(i18n.messages[locale][`glossary_${term}_term`], `${locale}: glossary_${term}_term`);
    }
  }
  i18n.setLanguage("en");
  globalThis.window.location.search = "?session=21546";
  const html = [
    dom.renderToStaticMarkup(React.createElement(Recommendation, { state: data.normalizeDemo(demo), productInfo: {}, official })),
    dom.renderToStaticMarkup(React.createElement(Experiments, { state: { results: official }, active: "E1" })),
    dom.renderToStaticMarkup(React.createElement(Experiments, { state: { results: official }, active: "E3" })),
  ].join("");
  globalThis.window.location.search = "";
  for (const term of glossary.GLOSSARY_TERMS) {
    const label = i18n.t("glossary_label", i18n.t(`glossary_${term}_term`)).replace(/&/g, "&amp;");
    assert.ok(html.includes(`aria-label="${label}"`), `ⓘ for ${term}`);
  }
  assert.match(html, /class="popover-button" aria-expanded="false"/);
  assert.match(html, /role="dialog"[^>]*hidden=""/, "popovers start closed");
});

test("E3 keeps the Validation badge next to its renamed title (EN and VI)", async () => {
  const i18n = await load("/src/i18n.js");
  const { default: Experiments } = await load("/src/Experiments.jsx");
  for (const locale of ["en", "vi"]) {
    i18n.setLanguage(locale);
    const html = dom.renderToStaticMarkup(React.createElement(Experiments, { state: { results: official }, active: "E3" }));
    const heading = html.slice(html.indexOf('<h2 id="title-E3"'), html.indexOf("</h2>", html.indexOf('<h2 id="title-E3"')));
    assert.ok(heading.includes(i18n.t("e3_panel_title", "GRU", 32, 128)), locale);
    if (locale === "en") assert.ok(heading.startsWith('<h2 id="title-E3">E3 · Compute resources: GRU batch 32 vs 128<span'), heading);
    if (locale === "vi") assert.ok(heading.startsWith('<h2 id="title-E3">E3 · Tài nguyên tính toán: batch GRU 32 và 128<span'), heading);
    assert.ok(heading.includes(`<span class="badge badge-validation">${i18n.t("validation_badge")}</span>`), `${locale}: badge inside the title`);
    assert.ok(text(html).includes(`E3 · ${i18n.t("experiment_nav_e3")}`), `${locale}: sub-tab`);
  }
});

test("E4 configuration: preprocessing table without 'Not available yet'; fairness line from the data", async () => {
  const i18n = await load("/src/i18n.js");
  const { default: Experiments } = await load("/src/Experiments.jsx");
  for (const locale of ["en", "vi"]) {
    i18n.setLanguage(locale);
    const html = dom.renderToStaticMarkup(React.createElement(Experiments, { state: { results: official }, active: "E4" }));
    const config = html.slice(html.indexOf('<details class="config config-bundle e4-config"'), html.indexOf("</details>", html.indexOf('class="config config-bundle e4-config"')));
    assert.ok(config.includes(i18n.t("e4cfg_title")), locale);
    assert.ok(!config.includes(i18n.t("MISSING")), `${locale}: no 'Not available yet' in the E4 configuration`);
    assert.ok(!config.includes(i18n.t("experiment_train_batch")), `${locale}: no training rows for E4`);
    assert.equal((config.match(/class="tag tag-same"/g) ?? []).length, 15, `${locale}: every row except input format is the same`);
    assert.ok(text(html).includes(i18n.t("e4_fairness", "882,808")), locale);
    const finding = html.indexOf('<aside class="key-finding"');
    assert.ok(html.indexOf('class="fairness-line"') < finding, "fairness line above the Key finding");
  }
});

test("no intro, subtitle or course lines; no empty paragraphs; one Key finding source per tab", async () => {
  const m = await modules();
  for (const locale of ["en", "vi"]) {
    const pages = renderAll(m, locale);
    for (const [name, html] of Object.entries(pages)) {
      for (const cls of ["page-intro", "experiment-subtitle", "experiment-course", "kf-source"]) assert.ok(!html.includes(cls), `${locale}/${name}: ${cls}`);
      assert.ok(!/<p[^>]*>\s*<\/p>/.test(html), `${locale}/${name}: empty <p>`);
      const sources = html.split(m.i18n.t("kf_source_footnote").replaceAll("'", "&#x27;")).length - 1;
      assert.equal(sources, name === "recommendation" ? 0 : 1, `${locale}/${name}: source footnote count`);
    }
    // E1 context moved into "Configuration & sources" (and the screen-reader table caption).
    const e1 = pages.E1;
    const config = e1.slice(e1.indexOf('<details class="config config-bundle">'));
    assert.match(config, /<p class="config-context">[^<]*1,337/);
  }
});

test("product cards: ID, brand · category, price from product-info.json; Method details names the source", async () => {
  const m = await modules();
  const info = m.data.normalizeProductInfo(json("../public/product-info.json"));
  for (const locale of ["en", "vi"]) {
    m.i18n.setLanguage(locale);
    const html = m.dom.renderToStaticMarkup(m.React.createElement(m.Recommendation, { state: m.data.normalizeDemo(demo), productInfo: info, protocol: overview.evaluation_protocol, official }));
    const note = m.i18n.t("product_details_note", "2019-10-01", "2019-10-07", 10);
    assert.equal(html.split(note).length - 1, 1, `${locale}: one product details line with the window and subset from JSON`);
    assert.equal(info.window, json("../public/product-info.json").checks.window_utc);
    assert.match(html, /<small class="product-meta">[^<]+ › [^<]+<\/small>/, locale);
    assert.match(html, new RegExp(`<small class="product-price" title="[\\d.]+">${m.i18n.t("product_price", "\\d+\\.\\d{2}")}</small>`), locale);
    assert.ok(!/\$\d/.test(text(html)), `${locale}: no currency symbol`);
  }
  // Without a lookup the cards show IDs only and the note is absent.
  const bare = m.dom.renderToStaticMarkup(m.React.createElement(m.Recommendation, { state: m.data.normalizeDemo(demo), productInfo: {}, protocol: overview.evaluation_protocol, official }));
  assert.ok(!bare.includes("product-meta") && !bare.includes(m.i18n.t("product_details_note").slice(0, 16)));
});

test("E2 has processing-time charts: preprocessing and training per subset, never summed", async () => {
  const m = await modules();
  for (const locale of ["en", "vi"]) {
    m.i18n.setLanguage(locale);
    const html = m.dom.renderToStaticMarkup(m.React.createElement(m.Experiments, { state: { results: official }, active: "E2" }));
    assert.equal((html.match(/<figure class="chart/g) ?? []).length, 4, locale);
    for (const key of ["e2_chart_time_pre", "e2_chart_time_train"]) assert.ok(html.includes(`<figcaption>${m.i18n.t(key)}</figcaption>`), `${locale} ${key}`);
  }
});

test("Key finding bodies: metric values are bold (decimals and values with units); plain counts are not", async () => {
  const { metricParts } = await load("/src/KeyFinding.jsx");
  const metrics = (text) => metricParts(text).filter((part) => part.metric).map((part) => part.text.replaceAll("\u00A0", " "));
  assert.deepEqual(metrics("Training time drops from 51.7\u00A0s to 30.6\u00A0s and GPU memory rises from 2.2\u00A0GiB to 3.9\u00A0GiB, while validation Recall@20 falls from 0.1964 to 0.1299."),
    ["51.7 s", "30.6 s", "2.2 GiB", "3.9 GiB", "0.1964", "0.1299"]);
  assert.deepEqual(metrics("Recall@20 rises from 0.0883 at 10% to 0.3899 at 100%. Training from 27.6\u00A0s to 433\u00A0s."), ["0.0883", "0.3899", "27.6 s", "433 s"]);
  assert.deepEqual(metrics("Preprocessing takes 51.7% of the combined stage time at 10%."), ["51.7%"]);
  assert.equal(metricParts("No numbers here.").map((part) => part.text).join(""), "No numbers here.");
  const i18n = await load("/src/i18n.js");
  i18n.setLanguage("en");
  const html = dom.renderToStaticMarkup(React.createElement((await load("/src/Experiments.jsx")).default, { state: { results: official }, active: "E3" }));
  for (const value of ["51.7", "30.6", "2.2", "3.9", "0.1964", "0.1299"]) assert.match(html, new RegExp(`<strong class="kf-num">${value.replace(".", "\\.")}`), value);
});
