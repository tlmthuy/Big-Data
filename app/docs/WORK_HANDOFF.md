# TV4 demo work handoff

Snapshot: 26 November 2026 (UI refresh appended below; earlier steps from 25 November)\
Repository: `tv4-demo-web`  
Official source package: `tv2-20261124` from the adjacent read-only `../Big-Data` repository.

## Overall result

The demo uses the official TV2 package for E1–E5 experiment results, dataset overview, figures, and bilingual demo materials. The Recommendation view now replays a fixed, checksum-verified sample of real E1 predictions. Product cards show the original ID, brand, category and last weekly price from `public/product-info.json`, derived by TV4 from the official 10% cleaned week file. The dataset has no product names.

No team-repository files were changed and nothing was pushed.

## Completed steps and commits

| Step | Work | Commit |
|---|---|---|
| 0 | Added team progress context; established baseline | `0e8c5b6 docs: add team progress context 25/11` |
| 1 | Added number formatting helpers and tests | `0397bab feat: display formatting helpers with tests` |
| 2 | Added checksum-aware official results adapter and JSON | `413c9c0 feat: adapter for official TV2 package tv2-20261124` |
| 3 | Improved readability, compacted header and removed repeated intros | `0f52d28 style: larger readable text, compact header, remove duplicate intros` |
| 4 | Added official E1 comparison panel | `c586b38 feat: E1 panel with official package values` |
| 5 | Added E2 table and E5 scaling charts | `c90b0e5 feat: E2 table and E5 scaling charts from official package` |
| 6 | Added E3 batch and E4 format comparisons | `938b204 feat: E3 batch comparison and E4 format comparison` |
| 7 | Added planned/actual configuration, runtime and hidden toy details | `cea6d67 feat: configuration and environment details for experiments` |
| 8 | Replaced dataset overview with official supplementary tables | `e7badce feat: dataset tab from TV2 supplementary tables, remove preliminary section` |
| 9 | Updated recommendation wording/layout and checked for real bundle | `2c65031 feat: recommendation layout, interaction wording, real-bundle check` |
| 10 | Generated official figures and captions from package JSON | `e945059 feat: official figures and captions from tv2-20261124` |
| 11 | Updated context, bilingual talk track, demo runbook and README; captured EN/VI screenshots | `11e75d2 docs: demo script with official results, context and fallback` |
| 12 | Final audit; localized E5 axis labels and tested them | `aaa0825 fix: final audit corrections` |
| 13 | Added verified real E1 predictions as a fixed 30-session sample; product metadata remains pending | See current Step 13 commit below |

## Key data and interpretation decisions

- Official metrics are copied from the package into `public/official-results.json`; values are not recomputed.
- Checksums normalize CRLF to LF. Package, analysis and evidence mismatches fail; the documented `environment/README.md` post-package documentation edit is the allowed warning exception and is not used as a numeric source.
- E3 has no throughput row because the package contains no throughput field. Its table uses the delivered validation and process-wall fields.
- E3 validation results are not directly comparable with E1/E2 test results.
- E4 preprocessing wall time includes reading; it is not added to standalone read time. The package records warm-cache conditions.
- E5 composed time excludes shared first-seen and is not observed end-to-end wall time.
- E1 results represent a single run and seed.
- Missing values stay unavailable; no scores are inferred from ranks.
- The local `../tv4-real-bundle/` is an export input only and must never be committed. The public app stores only sampled IDs and the catalog subset; full-catalog SHA and size are retained.
- Product cards show the original ID, brand, category and last weekly price from `public/product-info.json` (derived by TV4 from the official 10% cleaned week file; `scripts/export_product_info.py`). The dataset has no product names.

## Final audit evidence

- JavaScript tests: 32 passed.
- Python tests: 9 passed with `PYTHONPATH=../Big-Data:scripts`.
- Production build: passed.
- Official results and dataset adapters regenerated outputs equivalent to committed JSON (excluding the official export timestamp).
- Figure generator rebuilt the six expected SVGs: E1 ranking, E1 training, E2 training, E3 tradeoff, E4 format, E5 scaling.
- Browser audit covered E1–E5 at 1280 px and 375 px in English and Vietnamese, toggled configuration details, and found no horizontal overflow or untranslated keys after fixing the E5 event-axis labels.
- Recommendation screenshots were captured in English and Vietnamese at both widths, along with dataset and experiment screenshots.
- High-precision numeric literals are absent from `src/`.
- `git diff --check` passed and the working tree was clean after the final commit.

Ten screen-to-package spot checks are documented in the Step 12 report from the previous conversation. The team package remains the source of truth for every reported value.

## Current stopping point

Step 13 adds the checksum-verified real E1 sample and Recommendation UI; TV1 product metadata remains pending. No team-repository files were changed and nothing was pushed.

## UI refresh 26/11 — Apple-inspired design and TV2 reviewer feedback

Local commits on `main` (not pushed). The team repository was not touched.

| Step | Work |
|---|---|
| 1 | Design tokens, five-step type scale, colour meanings, model colours; contrast test covers HC and glass |
| 2 | Selective translucency (header, control bars, tooltips/popovers, method details) with solid fallbacks |
| 3 | Hash routes per tab and experiment, link navigation, E1–E5 segmented subtitles, single About popover |
| 4 | Recommendation layout from the review: control bar, History + Actual next item + Hit/Miss sentence above the fold, linked hit row, E1 strip, closed Method details |
| 5 | Presenter mode (`?present=1`, header switch, remembered) |
| 6 | Shared formatter (`src/format.js`), unit-tested for every branch |
| 7–9 | Experiments: takeaways from JSON, interactive charts linked to tables, units in headers, one notes block, empty-state rule, E3 validation framing, E5 runtime/normalized charts and E2 link |
| 10 | Glossary ⓘ popovers |
| 11 | Remaining 25/11 and 26/11 audit items (code-chip contrast, 5V grid, table alignment, Dataset title) |
| 12 | Allowed cross-links: Recommendation E1 strip → E1; E5 level → E2 level; Dataset subset → E2 level |
| 13 | `scripts/check_ui.mjs` (`npm run test:e2e`), `tests/test_official_values.py`, chart/presenter/format tests; screenshots in `/tmp/tv4-after/` (outside the repo) |
| 14 | DEMO_SCRIPT (presenter notes, E2 paragraph, on-screen rounding), DEMO_DAY order, CONTEXT, this handoff |

Open items for humans: confirm Windows High Contrast on the presentation laptop (forced colours cannot be judged from headless screenshots); the `public/sample-predictions.csv` Git exception (AGENTS rule 9) is unchanged and still needs a decision.
