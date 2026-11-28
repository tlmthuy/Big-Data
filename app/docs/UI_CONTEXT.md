# UI context: TV4 demo web

Snapshot: 27/11/2026. Describes local `main` after the plain-language Key findings, the removed intro/subtitle lines, the E3 rename, the hit-row highlight and product details on cards. `origin/main` is at `5ecc80b`; later commits are local until the user pushes them. Read this before any UI change. Data rules live in `AGENTS.md` and `docs/CONTEXT.md`; this file covers the interface only. If they disagree, `AGENTS.md` wins.

## 1. What the site is

- **Static site, no backend.** React 18 + Vite 6, no server, no database, no API, no live model inference. Deployed as a Render Static Site (`npm ci && npm run build`, publish `dist/`) at https://demo-big-data.onrender.com/, auto-deployed from `main`.
- **Data flow.** Python scripts in `scripts/` read the team repo `../Big-Data` (read only) and `../tv4-real-bundle/` (outside Git) and write `public/*.json`. The browser fetches these JSON files at load time. Every number on screen comes from them.

| File | Used by | Content |
|---|---|---|
| `public/official-results.json` | Experiments, E1 strip | E1–E5 from package `tv2-20261124` (262 values, checked against `metrics.json`), `stage_shares` (from `reports/tables/tv2-20261124/stage_shares.csv`, checked against E5), `configs[*].e4_config` (E4 preprocessing configuration) |
| `public/dataset-overview.json` | Dataset | TV2 supplementary tables, raw audit, manifests |
| `public/demo-data.json` | Recommendations | Real E1 predictions: 30 of 1,337 test sessions, same sessions for Popularity/GRU/XLNet, ranked IDs only (no scores), catalog subset + full-catalog SHA |
| `public/product-info.json` | Recommendations (product cards) | `data_kind: real`; brand, category_code and last weekly price for the 292 displayed product IDs, derived by TV4 from the official 10% cleaned week file (`scripts/export_product_info.py`; checks 638,089 rows, 63,398 products, 2019-10-01..07 UTC; `source_sha256`). Declared by `demo-data.json → provenance.product_lookup`. No names: the dataset has none |
| `public/sample-predictions.csv` | not used by the UI | Format sample (rule 9 exception in `AGENTS.md`) |

- Audience: lecturer and classmates in a 15-minute English talk + 5-minute Q&A. The demo walkthrough is about 3 minutes (`docs/DEMO_SCRIPT.md`). Default language English; Vietnamese via the EN/VI switch.

## 2. File map

| Area | Files |
|---|---|
| Entry, data loading, header | `src/main.jsx` |
| Header controls | `src/Nav.jsx` (`MainNav`, `LanguageSwitch`, `PresenterToggle`, `Popover`, `AboutDemo`) |
| Routing | `src/navigation.js` (`routeFromHash`, `experimentHref`) |
| Presenter mode | `src/presenter.js` (`readPresenter`, `savePresenter`, `PresenterContext`) |
| Tabs | `src/Recommendation.jsx`, `src/Dataset.jsx` (+ `DatasetContext.jsx`), `src/Experiments.jsx` |
| Charts | `src/Chart.jsx` (`BarChart`, `LineChart`, `useSelection`, `useWidth`), `src/chart-math.js` |
| Experiment views | `src/e1.js`, `src/scaling.js` (E2–E5), `src/takeaways.js` (E3/E4 sentences, E4 fairness line), `src/findings.js` (Key findings for E1–E5 and Dataset), `src/KeyFinding.jsx`, `src/run-config.js` (run kinds), `src/RunConfigDetails.jsx` (incl. `E4ConfigDetails`), `src/interpretation-notes.js` |
| Shared UI | `src/ui.jsx` (`Notice`, `DataLoadFailure`, `InterpretationNote`, `DataKindBadge`, `StatusBadge`, `Issues`), `src/ProductCard.jsx`, `src/Glossary.jsx`, `src/EvaluationProtocol.jsx` |
| Data helpers | `src/data.js` (`normalizeDemo`, `firstAllModelHitSession`, `sessionContext`, `modelLabel`, `EXPERIMENTS`) |
| Formatting | `src/format.js` (the only formatter) |
| Text | `src/i18n.js` (`messages.en` / `messages.vi`, `t(key, ...args)` with `{0}` placeholders) |
| Styles | `src/styles.css` (all tokens and components) |

## 3. Design system (Apple HIG-inspired, no Apple logos, trademarks or bundled SF Pro)

**Tokens** (`src/styles.css` `:root`; dark via `prefers-color-scheme: dark`; high contrast via `prefers-contrast: more` and `forced-colors`):

| Token | Light | Dark | Meaning |
|---|---|---|---|
| `--bg` / `--surface` | `#f5f5f7` / `#ffffff` | `#000000` / `#1c1c1e` | page / cards |
| `--label` / `--label-2` | `#1d1d1f` / `#6e6e73` | `#f5f5f7` / `#a1a1a6` | primary / secondary text |
| `--accent` | `#0066cc` | `#2997ff` | interactive only |
| `--control-border` | `#86868b` | `#8e8e93` | control borders (≥ 3:1) |
| `--positive`, `--positive-text`, `--positive-bg` | `#248a3d`, `#1a7f37`, `#edf8f0` | `#30d158`, `#30d158`, `#0e2a16` | Hit only |
| `--on-positive` | `#ffffff` | `#000000` | ✓ glyph on the green Hit badge (≥ 3:1) |
| `--selected-bg` | `#eef5fc` | `#1d2835` | selected table column (`--label-2` on it ≥ 4.5:1) |
| `--danger`, `--danger-bg` | `#d70015`, `#fdeceb` | `#ff453a`, `#3b1210` | problems only |
| `--kf-bg-from` → `--kf-bg-to`, `--kf-border` | `#fed7aa` → `#ffedd5`, `#fb923c` | `#4a2a12` → `#2e1c10`, `#c2621f` | Key finding card gradient and border |
| `--kf-eyebrow`, `--kf-heading`, `--kf-body`, `--kf-note`, `--kf-number` | `#9d4815`, `#0f172a`, `#334155`, `#546175`, `#9d4815` | `#fb923c`, `#f5f5f7`, `#cbd5e1`, `#94a3b8`, `#fdba74` | Key finding text; all ≥ 4.5:1 on both gradient ends (tested). `#9d4815`/`#546175` are the requested `#c2591a`/`#64748b` darkened to pass on the stronger peach |
| `--caution` | `#a15c00` | `#ffb340` | warnings |
| `--model-popularity/-gru/-xlnet` | `#5e7387` / `#c4610a` / `#8e44ad` | `#9fb4c7` / `#ff9f0a` / `#bf5af2` | fixed model colours |
| `--glass` | `rgba(255,255,255,.72)` | `rgba(28,28,30,.72)` | translucent surfaces |

**Type scale: exactly 5 steps.** `--t-title` 28, `--t-section` 22, `--t-lead` 18, `--t-body` / `--t-table` 16, `--t-footnote` 13 (chart ticks, captions, footnotes, column sub-labels only). Body text is not italic. Paragraphs are at most about 3 lines in the default view. Tabular numerals in tables, metrics and chart labels. Product IDs use `--mono`.

**Layout.** 8-pt spacing (`--s1`…`--s6` = 4–32 px), card radius 14 px, control radius 10 px, controls and every clickable target ≥ 44 px (`--control-height`), sticky header 56 px, content ≤ 1200 px.

**Colour rules (one colour, one meaning).**
- Accent blue is for interactive elements only.
- Green means Hit. Hit text uses `--positive-text`. The ✓ glyph uses `--on-positive` (white in light mode, black in dark mode).
- A miss is neutral: grey text, ✕, and the word "Miss". Never red.
- Red is for load errors, failed or excluded runs, and config "Differs" (`--danger`). No other red: the Key finding callout uses a peach/burnt-orange palette so it never reads as an error.
- "In history" is a neutral grey outline.
- Model colours always appear next to a text label or marker shape (● Popularity, ■ GRU, ◆ XLNet). Never rely on colour alone.

**Selective translucency (`.glass`).** `backdrop-filter: saturate(180%) blur(20px)`. Used only on the sticky header, the control bars and segmented sub-tabs, chart tooltips, glossary/About popovers and the Method details panel. Never on data cards, tables or chart plot areas. It falls back to solid `--surface` when there is no `backdrop-filter` support, when reduced transparency, high contrast or forced colours are on, and in presenter mode. Only `--label` text may sit on glass. The page has a faint `--bg-tint` gradient so the glass is visible.

## 4. Screens and behaviour

**Header (glass).**
- Title. It never truncates (no ellipsis). Between 1101 and 1279 px it shows the short label "Next-Item Demo" / "Demo gợi ý".
- `<nav>` links with `aria-current`.
- An About popover, the Presenter mode switch, and the EN/VI segmented switch (remembered in `localStorage`).

**Sticky sub-bars** (one per tab; `src/sticky.js` `useStickyBar`):
- Experiments: the E1–E5 segmented sub-nav. Recommendations: the glass control bar (Model, Session, presenter tip). Dataset: a segmented section nav (Overview, Subsets, 5V, Key findings, Caveats, Splits, Pipeline) with scroll-spy (`aria-current="true"`, IntersectionObserver).
- `position: sticky; top: var(--sticky-top)`: 56 px under the sticky header at ≥ 1101 px; 0 below that, where the header scrolls away (so header + sub-bar ≤ 120 px at 375: the sub-bar alone is 48–60 px). Sticky until the end of the tab content.
- Glass with the usual solid fallbacks (reduced transparency, high contrast, forced colours, presenter mode). A soft separator only while stuck, from an IntersectionObserver sentinel (no per-frame scroll listener). The bar height is published as `--subbar-height`.
- Switching E1–E5 while scrolled brings the new panel's top just below the sub-nav.
- Stuck control bar: below 900 px the presenter tip hides; below 600 px the visible labels and model dots hide too (controls keep accessible names), so Model + Session fit one 60 px row.
- Below 760 px every sub-bar is one horizontally scrolling row (no wrapping, hidden scrollbar, scroll-snap, 48 px, 44 px targets; focus ring drawn inside the link); the Dataset nav already from 900 px. The active item is scrolled into view.
- Print: header and sub-bars are not sticky. Presenter mode: still sticky, solid.

**z-index order.** Header 10 > chart tooltip 9 > sub-bar 8 > page content. Popovers (About, glossary) are 30; native select menus are OS layers. A chart card must not become a stacking context (no containment, transform or z-index on `.chart`), or its tooltip could not rise above the sub-bar; the container query for the detail area lives on `.chart-detail`.

**Selects.** `Select` in `src/ui.jsx` wraps every `<select>`: `appearance: none`, a `--label-2` chevron (CSS mask) 14 px from the right edge, 40 px right padding, 44 px height, `--control-border`, normal focus ring, native keyboard and mobile pickers. Forced colours fall back to the system arrow.

**Routes.** `#recommendation`, `#dataset`, `#experiments/e1`…`#experiments/e5`, `#experiments/e2/N` to preselect a data-size level, and `#dataset/<slug>` for a Dataset section (`overview`, `subsets`, `5v`, `key-findings`, `caveats`, `splits`, `pipeline`; it scrolls there, also after a reload). Legacy `#data` and `#experiments-e3` still resolve. `?session=<id>` preselects a session. `?present=1` / `?present=0` sets presenter mode. `html { scroll-padding-top }` = header + sub-bar, so anchor jumps and keyboard focus land below both.

**Recommendations tab** (order matters; the reviewer asked for it):
1. Title and one badge ("Real E1 predictions · Showing 30 of 1,337 sessions"). No intro sentence.
2. Glass control bar: Model segmented control, Session select, and a presenter tip "Try session X: hit for all 3 models". X is computed by `firstAllModelHitSession` and is 21546 with the current data. Never hard-code it.
3. Interaction history next to the Actual next item, plus the sentence "Hit — the actual item is ranked N of 20" or "Miss — the actual item is not in the Top-20".
4. The Top-20 table. The row whose product ID equals the actual next item has a full-row `--positive-bg` background on every cell (`.ranking tr.is-hit td`), a 4 px `--positive` left bar, a bold `--positive-text` rank and the "✓ Actual next item" tag. The Actual next item panel uses the same background and bar, so the two read as the same item; hover or focus on either draws the linked outline on both. A miss highlights no row and the panel stays neutral. Forced colours use `Mark`/`MarkText`. Text on `--positive-bg` (`--label`, `--label-2`, `--positive-text`) is ≥ 4.5:1 in every scheme (`tests/contrast.test.js`). The Score column is absent because no model exports scores.
   - **Product cards** (history, Actual, Top-20): line 1 the original product ID (mono); line 2 the brand as in the data (lowercase) · the category path joined with ` › ` (`electronics › camera › video`); line 3 "Price 308.86" / "Giá 308.86", 2 decimals and no currency symbol (the dataset states none). Missing parts are omitted; with no entry only the ID shows. Long paths wrap, never an ellipsis. Never build a product name (the dataset has no name column).
5. The E1 strip for the selected model, linking to E1.
6. Closed "Method details & sources": protocol, run ID, checksums, file names, catalog size, and (when `product-info.json` is loaded) "Product details: brand, category and last price seen in week 1 of the 10% data. The dataset has no product names."

Acceptance: at 1280×800, in EN and VI, steps 3 and the Hit/Miss sentence are visible without scrolling.

**Dataset tab.** Title only (no intro sentence). The Key findings group comes first (nav order Key findings, Overview, Subsets, 5V, Caveats, Splits, Pipeline; `#dataset/key-findings` and scroll-spy unchanged). Then raw month facts, why this subset, 5V summary, weekly cuDF subsets (N% links to E2), caveats, representativeness limits, split population, session length, processing pipeline. Never claim that hash sampling guarantees representativeness.

**Experiments tab.**
- A segmented sub-nav with short labels: E1 Model comparison, E2 Data size, E3 Compute resources, E4 Storage format, E5 Scalability (one line at ≥ 1024 px, may wrap below, never an ellipsis).
- The page has a title only (no intro sentence; the chart detail area already says "Select a bar or point for details").
- Each panel contains: title (E3 with the `Validation` badge), (E4) the fairness line, the **Key finding** callout one 16 px gap below, charts, a metric × run table whose columns link to the chart marks, one notes block, and a closed "Configuration & sources". There are no subtitle or course-item lines. The E1 context (subset, test partition, sessions, single run) is the first line of E1 "Configuration & sources" and part of the screen-reader table caption.
- One footnote at the bottom of the tab: "Key findings summarise TV2's analysis (analysis.md, 24/11)." (the Dataset tab has the same footnote at its bottom).
- The Environment card is at the bottom and collapsed.
- Per-experiment rules:
  - **E2 · Data size.** Four charts, two per row: Recall@20, NDCG@20, and processing time by data size as two linked charts (`preprocessing_seconds`, `train_seconds_including_sequence_io`; never summed). The Key finding adds "Preprocessing grows from … and training from … between 10% and 100%" only when both are higher at the largest subset; otherwise it lists the values.
  - **E3 · Compute resources: GRU batch 32 vs 128** (title built from JSON; VI "E3 · Tài nguyên tính toán: batch GRU 32 và 128"). Course item 3 asks to vary compute resources; the hardware was fixed (one AWS VM, one Tesla T4) and only the GRU training batch changed (32 vs 128, read from JSON), on validation. Never claim CPU, RAM or workers were varied. Validation badge, train-batch headers read from configs, a hardware/limitation note (hardware names read from `vm_environment`), the held-constant note. Charts: training time, sampled GPU process memory, validation Recall@20. No throughput (the package has no throughput field) and no "peak" CUDA memory (it is sampled).
  - **E4 · Storage and retrieval: CSV vs Parquet.** Course item 4. The same events stored both ways: file size (MiB, raw bytes in the tooltip), read time, and preprocessing time (which already includes the read). One chart for each.
  - **E4 fairness line** (under the title, above the Key finding): "✓ Same data: {n} events, fingerprints match · same program · all nine columns read as strings". Shown only when both runs have `fingerprint_match` true, equal event counts, the same program and the same all-string schema policy. The ✓ uses `--label` (green means Hit).
  - **E4 "Configuration & sources"** is a "Preprocessing configuration" table (Parameter | CSV run | Parquet run | Same) from `e4_config`: input format, subset, events, fingerprint match, program, read scope, schema policy, cache, events after repeat removal, vocabulary size, cuDF/NVTabular versions, notebook commit (8 chars, full in the tooltip), split seed/ratios, partition column. No training rows. Stage timings are not exported (their scope differs from the official E4 table).
  - **Sentence wording (E3/E4).** `src/takeaways.js` picks every direction word (drops/rises/falls, VI giảm…xuống/tăng…lên) by comparing the JSON values; equal or missing values give a neutral sentence that only lists the values. E4 says "File size goes from … and read time from …" only when Parquet is smaller and reads faster, "Total preprocessing only drops from …" only if it is lower and within 10%, and adds ", because reading is a small part of it" only if each read is < 10% of its preprocessing time.
  - E5 Bottleneck values are mapped to readable i18n labels, with the raw value in the title attribute.
  - E5 links only to the same E2 level. Nothing links E3 beside E1/E2.

**Charts** (hand-written SVG; no chart library).
- Hover previews a mark. Click, Enter or Space selects it and dims the others. Esc or "Clear selection" clears it. Arrow keys move between marks.
- Hit areas are ≥ 44 px, baselines are at zero, and `prefers-reduced-motion` is respected.
- The tooltip shows the display value, raw value, unit, run ID and source file.
- Category labels are never truncated (no ellipsis): measured in the page font, wrapped to two lines, then reduced to the 13 px caption size, then staggered.
- **Fixed detail area under every chart.** The hint ("Select a bar or point for details" / "Chọn một cột hoặc điểm để xem chi tiết", `--label-2`, vertically centred) and every mark's details share one grid cell, so the area is always as tall as the tallest content and hovering or selecting never changes the card height. When the chart card is ≥ 440 px the details are two columns of label: value pairs (about two lines).
- Tooltip placement: on screens ≥ 900 px a floating glass tooltip sits above or beside the mark when it fits without covering the selected mark or any value, category or axis label; otherwise (middle bars, and always below 900 px) the details show in the fixed area.
- Desktop bar charts are 290 px tall. At most two charts per row: E3 and E4 have three, so the third wraps to the next row, left-aligned and the same width (every card ≥ 440 px at 1280 and titles fit one line).
- Never plot a series that is not in the JSON.

**Key finding callouts.** From TV2's `reports/tables/tv2-20261124/analysis.md` (findings 1–7 and section 8); add no claim that is not in that file.
- `KeyFinding` (`<aside aria-label="Key finding">`): label "Key finding" / "Đúc kết" (13 px, `--label-2`, letter-spaced), optional headline (`--t-lead`, a heading one level below the panel title), body (`--t-body`), at most one caveat (13 px, `--label-2`). No source line inside the callout: `KeyFindingSource` renders it once at the bottom of the Experiments tab and once at the bottom of the Dataset tab. Every callout (E1–E5 and Dataset) is a refined card, not an alert: a left-to-right gradient `--kf-bg-from` → `--kf-bg-to` (peach `#fed7aa` → `#ffedd5`), 1 px `--kf-border` (`#fb923c`), shadow `0 1px 3px rgb(0 0 0 / .10)`, 14 px radius, 24 px padding. Eyebrow "KEY FINDING" uppercase bold burnt orange; headline bold near-black at `--t-section` (22 px, two sizes up); body slate; caveat muted gray. In the body, metric values (decimals such as 0.1964 or 51.7%, and values with a unit such as 51.7 s, 3.9 GiB, 433 s) are bold `--kf-number`, by `metricParts()` in `src/KeyFinding.jsx`; plain counts ("10%" subsets, batch sizes) stay plain. Forced colours: 1 px `CanvasText` border. No glass. Presenter mode enlarges it through the type tokens (headline 22 px, body 18 px).
- One per experiment panel, directly under the title (and the E4 fairness line), before the charts. The Dataset tab has a "Key findings" group of three callouts after the 5V summary.
- **Writing style.** Plain and short: headline ≤ 10 words, no colon; body ≤ 2 short sentences; caveat ≤ 1 short sentence or none (E2 has none); no em dashes; no "not X but Y"; no hedging chains. Every number is a `{n}` placeholder filled from JSON through `src/format.js`; never type a number into JSX or `i18n.js`, and never render a new ratio ("5×", "4×"): show both values.
- Current EN headlines: E1 "{best} predicts best; {cheapest} is cheapest to run"; E2 "Larger subsets score higher"; E3 "Batch {b2} trains faster but predicts worse"; E4 "Parquet is much smaller and faster to read"; E5 "As data grows, the bottleneck shifts to {stage}" (or "{Stage} stays the main cost"); D1 "Almost every event is a product view"; D2 "Only sessions with two or more interactions can be tested"; D3 "The {n}% subset still has {items} of {items100} products".
- **Guards** (`src/findings.js`, unit-tested): a headline or added sentence appears only when the JSON values agree with it; otherwise only the body shows. E1 best needs Recall@20 and NDCG@20 to agree and cheapest needs train and final-eval time to agree, else that half is omitted; the "GRU only just beats Popularity" sentence needs Popularity < GRU < best. E2 Recall@20 strictly rising (the body says "rises" only if the last value is higher). E3 larger batch has shorter training time and lower Recall@20; the weight-updates sentence needs equal epochs. E4 smaller, faster read and each read < 10% of preprocessing. E5 bottleneck at the first and last subset, shares from `stage_shares`, "falls" only if time per million events is lower. D1 view share ≥ 90% raw and cleaned (`ALMOST_ALL_PCT`). D2 single-interaction share > 0. D3 the subset's product share exceeds its session share.

**Not applicable vs Not available yet.** `src/run-config.js` classifies a run as training, baseline (Popularity) or preprocessing (E4). A field that does not exist for that kind shows "Not applicable" / "Không áp dụng"; "Not available yet" / "Chưa có" is only for an expected value that was not delivered.

**Glossary ⓘ.** Session, History (prefix), Top-20, Hit, Recall@20, NDCG@20, Validation vs test. Keyboard and touch accessible; Esc closes the popover and returns focus. Definitions follow `docs/data_contract.md` and the team's model protocol. Never invent a definition.

**Presenter mode.** Body and tables 18 px, footnotes 16 px, chart labels 16 px, larger section spacing, solid header, notes collapsed. Never shrink text to make content fit; let the page scroll.

**Loading.** `index.html` shows a static centred "Loading the demo…" (page background, system font, light/dark) inside `#root` until React mounts, plus a `<noscript>` line "This demo needs JavaScript."

**Footer provenance.** Each data file shows its commit and export date; `product-info.json` shows "Source week-010.parquet · SHA {first 8} · Exported {date}" from its `source_file`, `source_sha256` and `generated_at` fields.

**Errors and empty states.** A friendly `DataLoadFailure` with technical details collapsed. Missing values show "Not available yet" / "Chưa có". Inapplicable values show "Not applicable" / "Không áp dụng". Never show NaN, undefined, null or 0 for a missing value.

## 5. Number display (`src/format.js` only)

- Number and unit are always joined with a non-breaking space (U+00A0): "0.454 s", "24.2 MiB", "882,808 events". Percent stays attached ("51.7%").

- Recall/NDCG: 4 decimals.
- Times: 3 significant digits, with the unit in the row or column header.
- Bytes: MiB/GiB with 1 decimal and the unit shown.
- Integers: grouped with thousands separators.
- Missing or NaN: the "Not available yet" text.
- The raw value always goes in the tooltip or title attribute.
- Never recompute or redefine a metric, and never derive a score from a rank. Display rounding is the only change allowed.

## 6. Rules for any UI change

1. All visible text goes through `src/i18n.js` with both `en` and `vi`. No raw keys on screen. No English left in VI mode, except technical terms that the team keeps in English (for example "Fit workflow").
2. Use the tokens. Never hard-code a colour, size or radius in a component.
3. Contrast: text ≥ 4.5:1, large text and control borders ≥ 3:1, the high-contrast set ≥ 7:1 where feasible, and text on glass checked against the worst case. Add every new colour pair to `tests/contrast.test.js`.
4. Keep the Recommendation order and the fold acceptance from section 4.
5. Never put E3 next to E1/E2. Keep planned and actual configuration separate. Keep the interpretation notes.
6. No new dependency unless it is justified in the report. The JS bundle is about 306 kB.
7. Every `public/*.json` stays under 300 KB. Never commit the bundle, the catalog, Parquet or checkpoints.

## 7. Checks (run from `tv4-demo-web/`)

```bash
npm test                 # node unit + SSR render tests (incl. contrast, i18n parity, format)
npm run build
npm run test:e2e         # scripts/check_ui.mjs on the production build: text scan, overflow,
                         # chart select/keyboard/table link, tooltip in 375 px, hit link,
                         # glossary, presenter, fold at 1280x800, header <= 56 px,
                         # header title, 44 px targets, tooltip overlap, no ellipsis in
                         # chart labels, chart card height stable on hover/select
PYTHONPATH=../Big-Data:scripts python3 -m unittest discover -s tests -p "test_*.py"
                         # BIG_DATA_ROOT overrides ../Big-Data
python3 scripts/check_demo_script.py
                         # talk-track length, required Q&A, every decimal = a displayed JSON value
git diff --check
```

Counts at this snapshot: `npm test` 98/98, `npm run test:e2e` 53/53, Python 39/39 (official values 262/262), demo script 429 English walkthrough words. JS bundle 306 kB (gzip 96 kB). Every `public/*.json` is below 300 KB (largest: `demo-data.json`, 80 KB; `product-info.json` 29 KB).

After these pass, look at the screenshots yourself (`scripts/capture_screens.mjs`; save outside the repo, e.g. `/tmp/...`). Automated checks have missed overlap, clipped labels and raw i18n keys before. Check widths 1440, 1280×800, 768 and 375, in EN and VI, in light, dark and high contrast, with presenter mode on and off.

## 8. Known gaps and open decisions

- Commits after `5ecc80b` (this file, the fixed chart detail area, the E3/E4 rewording, stale-label cleanup, the compact detail area, the E3/E4 talk lines) are local until the user pushes `main`.
- Forced-colors mode is not verifiable in headless Chrome. Check it manually on the presentation laptop.
- Done 28/11: numbers and units are joined with U+00A0 (`NBSP`, `joinUnit`, `keepUnitsTogether` in `src/format.js`; browser check at 375 px, EN/VI, E1–E5 and Recommendations). Tests compare sentences through `tests/helpers.js` `plain()`, which first fails on any ordinary number–unit space.
- Done 28/11: no data literals in `i18n.js`. `product_details_note` takes the window from `product-info.json → checks.window_utc` and the subset from the run; `sampling_scope` takes the window from `dataset-overview.json → sampling.scope` (half-open end → last day) via `dateRange()`. `tests/i18n.test.js` fails if any key outside its allow-list (protocol constants, notation, formulas, the source date) contains a digit.
- Product details come from the 10% week file only; a product's last price in that week may differ from other weeks or subsets.
- E3 does not vary CPU, RAM or workers (one VM, one GPU); varying them is listed as future work in `docs/DEMO_SCRIPT.md`.
- Still open for the user to decide ("the site feels too academic"): an Overview tab (problem → what we did → what we found), a Simple/Detailed switch merged with presenter mode, plain-language headings such as "E2 · Does more data help?", and Recall shown as "% of sessions" (the raw value stays in the tooltip; confirm with TV2).
