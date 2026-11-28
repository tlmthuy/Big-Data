# Demo day runbook

## Before presenting

1. Confirm the demo branch is checked out and the official results file is present: `public/official-results.json` (`tv2-20261124`).
2. Build and check the site:

   ```bash
   npm test
   npm run build
   ```

3. For the hosted demo, open [https://demo-big-data.onrender.com/](https://demo-big-data.onrender.com/) and confirm the page loads. For a local demo, start Vite with `npm run dev`.
4. Open Recommendations, Dataset and Experiments E1–E5 once from the segmented control at the top. Confirm the one badge “Real E1 predictions · Showing 30 of 1,337 sessions” and three model choices. The page follows the system light or dark appearance.
5. Turn on **Presenter mode** in the header (or open `?present=1`). It is remembered on this browser.

## Live three-minute walkthrough

The order matches [DEMO_SCRIPT.md](DEMO_SCRIPT.md): Dataset → Recommendations → E1 → E2 → E3 → E4 → E5.

1. **Dataset:** explain session-based next-item prediction and the weekly cuDF subsets. Point out the official population, cleaning and split tables. Each subset column links to its E2 result.
2. **Recommendations:** click the presenter tip “Try session X: hit for all 3 models” (X is computed from the data; currently 21546). Show the interaction history, the actual next item and the sentence “Hit — the actual item is ranked N of 20”. Hover the green row in the Top-20: the Actual next item panel highlights too. Switch models with the segmented control. Explain that the fixed seed-1 sample is outcome-independent, that the E1 strip below the list is the official full-test result (not recomputed on this sample), and that the page replays saved outputs (no Score column, no live inference).
3. **Experiments → E1 · Model comparison:** read the Key finding headline. Click the XLNet bar: the other bars dim and the XLNet table column highlights. Press Esc. Say this is one run and one seed.
4. **E2 · Data size:** read the Key finding (Recall@20 at 10% and 100%). Say that test data and catalog change with the subset, so it is not a pure train-size effect.
5. **E3 · Compute resources:** say the VM and GPU stayed the same and only the GRU training batch changed (read the sizes from the panel title). Point at the Validation badge and the hardware/held-constant notes. Do not compare with E1/E2 test.
6. **E4 · Storage format:** point at the "Same data" fairness line, then compare file size (MiB), read time and preprocessing time; preprocessing already includes reading, so it barely changes. Mention warm-cache conditions.
7. **E5 · Scalability:** show composed time and seconds per million events against event count (axes start at zero). Click a point to show its tooltip and the link to the same E2 level. State that composed time excludes shared first-seen and is not observed end-to-end wall time.

Use [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the bilingual talk track and Q&A. Read detailed values from the screen so labels, units and source IDs remain visible.

## Fallback without network access

A ready fallback pack lives **outside Git** in `../tv4-fallback/`: `dist/` (the built site with its JSON), `screenshots/` (talk order, 1280×800 EN; Recommendations hit rows for session 21546 per model and the 46465 miss; presenter E1/E5 at 1440) and `README.txt` (how to open it offline). Rebuild it after any UI change. **The fallback video is not included: a person must record it.**


1. Before the event, generate the static site and screenshots:

   ```bash
   npm run build
   node scripts/capture_screens.mjs
   ```

2. Start the local production preview:

   ```bash
   npm run preview
   ```

3. Open the local preview URL in the browser. The built site is static and uses the JSON files shipped in `public/`.
4. If the preview browser is unavailable, present screenshots from `screenshots/` (`<lang>-<light|dark>-<1280|375>-<view>.png`). The recommendation shot uses the all-model hit session; also choose `dataset` and `experiments-e1` through `experiments-e5`.

## Recovery notes

- If results fail to load, verify `public/official-results.json` is present, then rebuild.
- The checked-in `public/demo-data.json` is a 30-session real sample; rebuilds use the local `../tv4-real-bundle/` source and the checksum-verified exporter. Never substitute toy predictions.
- If a displayed value is missing, describe it as unavailable rather than estimating it.
