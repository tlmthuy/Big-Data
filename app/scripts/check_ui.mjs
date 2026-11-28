// Browser checks against the production build (run `npm run build` first): `npm run test:e2e`.
// Interactions (chart select / Esc / keyboard / table <-> mark link / hit link / cross-links),
// rendered-text scans (raw i18n keys, NaN, undefined), console errors, HTTP >= 400 and overflow.
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { preview } from "vite";
import { messages } from "../src/i18n.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const server = await preview({ root, preview: { host: "127.0.0.1", port: 0 }, logLevel: "error" });
const home = `http://127.0.0.1:${server.httpServer.address().port}/`;
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome" });
const keys = Object.keys(messages.en).filter((key) => key.includes("_") && messages.en[key] !== key);
const results = [];

async function open(hash, { width = 1280, height = 800, lang = "en", search = "" } = {}) {
  const context = await browser.newContext({ viewport: { width, height }, reducedMotion: "reduce" });
  await context.addInitScript((l) => { try { localStorage.setItem("tv4-language", l); } catch { /* optional */ } }, lang);
  const page = await context.newPage();
  page.problems = [];
  page.on("console", (message) => { if (message.type() === "error") page.problems.push(message.text()); });
  page.on("pageerror", (error) => page.problems.push(error.message));
  page.on("response", (response) => { if (response.status() >= 400) page.problems.push(`HTTP ${response.status()} ${response.url()}`); });
  await page.goto(`${home}${search}${hash}`, { waitUntil: "networkidle" });
  return page;
}

async function check(name, body) {
  try {
    await body();
    results.push(["ok", name]);
  } catch (error) {
    results.push(["FAIL", name, error.message.split("\n")[0]]);
  }
}

const views = ["#recommendation", "#dataset", "#experiments/e1", "#experiments/e2", "#experiments/e3", "#experiments/e4", "#experiments/e5"];

try {
  for (const lang of ["en", "vi"]) {
    for (const width of [1280, 375]) {
      for (const hash of views) {
        await check(`${lang} ${width} ${hash}: clean text, no errors, no overflow`, async () => {
          const page = await open(hash, { width, lang });
          const text = await page.locator("body").innerText();
          assert.deepEqual(keys.filter((key) => text.split(/[\s:·,;()→]+/u).includes(key)), [], "raw i18n key");
          assert.ok(!/\bNaN\b|\bundefined\b/.test(text), "NaN/undefined on screen");
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), 0, "horizontal overflow");
          assert.deepEqual(page.problems, []);
          await page.context().close();
        });
      }
    }
  }

  await check("chart: click selects + dims others + highlights table column; Esc clears", async () => {
    const page = await open("#experiments/e1");
    const bar = page.locator("[data-mark='GRU']").first();
    await bar.click();
    assert.equal(await bar.getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator(".chart.has-selection").count(), 2, "both E1 charts share the selection");
    const dimmed = await page.locator("[data-mark='XLNet'] .mark").first().evaluate((el) => getComputedStyle(el).opacity);
    assert.equal(Number(dimmed), 0.35);
    assert.equal(await page.locator("th.is-selected").count(), 1);
    assert.match(await page.locator("th.is-selected").innerText(), /GRU/);
    await page.keyboard.press("Escape");
    assert.equal(await page.locator(".chart.has-selection").count(), 0);
    assert.equal(await page.locator("th.is-selected").count(), 0);
    await bar.click();
    await bar.click();
    assert.equal(await bar.getAttribute("aria-pressed"), "false", "click again clears");
    await page.context().close();
  });

  await check("table column -> chart mark", async () => {
    const page = await open("#experiments/e4");
    await page.locator(".column-select").nth(1).click();
    const pressed = await page.locator("[data-mark][aria-pressed='true']").count();
    assert.equal(pressed, await page.locator("figure.chart").count(), "the matching mark is selected in every E4 chart");
    await page.locator(".metric-table tbody td").first().click();
    assert.equal(await page.locator("th.is-selected").count(), 1, "clicking a cell selects its column");
    await page.context().close();
  });

  await check("chart keyboard: arrows move focus, Enter selects, tooltip shown, focus ring visible", async () => {
    const page = await open("#experiments/e5");
    const marks = page.locator(".chart").first().locator("[data-mark]");
    await marks.first().focus();
    await page.keyboard.press("ArrowRight");
    assert.equal(await page.evaluate(() => document.activeElement.getAttribute("data-mark")), await marks.nth(1).getAttribute("data-mark"));
    await page.keyboard.press("Enter");
    assert.equal(await marks.nth(1).getAttribute("aria-pressed"), "true");
    assert.ok(await page.locator(".tooltip, .chart-detail-item.is-active").first().isVisible(), "details for the focused mark");
    const ring = await marks.nth(1).locator(".hit").evaluate((el) => getComputedStyle(el).stroke);
    assert.notEqual(ring, "none");
    await page.keyboard.press("Escape");
    assert.equal(await marks.nth(1).getAttribute("aria-pressed"), "false");
    await page.context().close();
  });

  await check("E5 selection links to the same level in E2 (preselected); E3 never linked", async () => {
    const page = await open("#experiments/e5");
    await page.locator("[data-mark='25']").first().click();
    const link = page.locator(".selection-bar a");
    assert.equal(await link.getAttribute("href"), "#experiments/e2/25");
    await link.click();
    await page.waitForFunction(() => location.hash === "#experiments/e2/25");
    // The lower E2 charts mount after measuring their width; wait (up to 5 s) until all four show the level.
    await page.waitForFunction(() => document.querySelectorAll("[data-mark='25'][aria-pressed='true']").length === 4, null, { timeout: 5000 }).catch(() => {});
    assert.equal(await page.locator("[data-mark='25'][aria-pressed='true']").count(), 4, "all four E2 charts preselect the level");
    assert.equal(await page.locator("a[href^='#experiments/e3']:not(.subtabs a)").count(), 0);
    await page.goBack();
    await page.waitForFunction(() => location.hash === "#experiments/e5");
    assert.equal(await page.locator(".subtabs [aria-current='page']").innerText().then((t) => t.includes("E5")), true, "back works");
    await page.context().close();
  });

  await check("tooltip stays inside a 375 px viewport", async () => {
    const page = await open("#experiments/e1", { width: 375, height: 812 });
    for (const key of ["Popularity", "XLNet"]) {
      const mark = page.locator(`[data-mark='${key}']`).first();
      await mark.scrollIntoViewIfNeeded();
      await mark.click();
      const box = await page.locator(".tooltip, .chart-detail-item.is-active").first().boundingBox();
      assert.ok(box && box.x >= 0 && box.x + box.width <= 375, `${key}: ${JSON.stringify(box)}`);
      await page.keyboard.press("Escape");
    }
    await page.context().close();
  });

  await check("tooltip covers neither the selected mark nor any value/category label (1280 and 375)", async () => {
    for (const [hash, key] of [["#experiments/e1", "XLNet"], ["#experiments/e1", "Popularity"], ["#experiments/e5", "25"], ["#experiments/e5", "10"], ["#experiments/e3", null], ["#experiments/e2", "100"]]) {
      for (const width of [1280, 375]) {
        const page = await open(hash, { width, height: 900 });
        const mark = key ? page.locator(`[data-mark='${key}']`).first() : page.locator("[data-mark]").first();
        await mark.scrollIntoViewIfNeeded();
        await mark.click();
        await page.mouse.move(0, 0);
        const hits = await page.evaluate(() => {
          const chart = document.querySelector(".chart.has-selection");
          const tip = chart.querySelector(".tooltip, .chart-detail-item.is-active").getBoundingClientRect();
          const overlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
          const things = [...chart.querySelectorAll(".mark-group.is-selected .mark, .chart-value, .chart-category, .chart-tick")];
          return things.filter((el) => { const r = el.getBoundingClientRect(); return r.width && overlap(tip, r); }).map((el) => el.textContent || el.tagName);
        });
        assert.deepEqual(hits, [], `${hash} ${key} @${width}`);
        await page.context().close();
      }
    }
  });

  await check("chart card height is identical before hover, during hover and after selecting each mark (E1–E5, 1280 and 375)", async () => {
    for (const width of [1280, 375]) {
      for (const hash of ["#experiments/e1", "#experiments/e2", "#experiments/e3", "#experiments/e4", "#experiments/e5"]) {
        const page = await open(hash, { width, height: 900 });
        const heights = () => page.evaluate(() => [...document.querySelectorAll("figure.chart")].map((figure) => figure.getBoundingClientRect().height));
        const base = await heights();
        assert.ok(base.length >= 2, `${hash}: charts rendered`);
        const marks = page.locator("[data-mark]");
        const count = await marks.count();
        for (let index = 0; index < count; index += 1) {
          const mark = marks.nth(index);
          await mark.scrollIntoViewIfNeeded();
          await mark.hover();
          assert.deepEqual(await heights(), base, `${hash} @${width}: hover mark ${index}`);
          await mark.click();
          assert.deepEqual(await heights(), base, `${hash} @${width}: select mark ${index}`);
          await page.mouse.move(0, 0);
          assert.deepEqual(await heights(), base, `${hash} @${width}: selected, pointer away, mark ${index}`);
          await page.keyboard.press("Escape");
        }
        const hint = await page.locator(".chart-detail-hint.is-active").first().innerText();
        assert.equal(hint, "Select a bar or point for details");
        await page.context().close();
      }
    }
  });

  await check("Key finding: one callout above the first chart on E1–E5 and on Dataset, no duplicate takeaway, 375 and presenter", async () => {
    for (const lang of ["en", "vi"]) for (const [width, search] of [[1280, ""], [375, ""], [1280, "?present=1"]]) {
      for (const hash of ["#experiments/e1", "#experiments/e2", "#experiments/e3", "#experiments/e4", "#experiments/e5"]) {
        const page = await open(hash, { width, lang, search });
        const result = await page.evaluate(() => {
          const panel = document.querySelector(".experiment-panel");
          const callouts = panel.querySelectorAll("aside.key-finding");
          const chart = panel.querySelector("figure.chart");
          const above = callouts.length === 1 && Boolean(callouts[0].compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING);
          const box = callouts[0]?.getBoundingClientRect();
          return { count: callouts.length, above, oldTakeaway: panel.querySelectorAll(".takeaway").length,
            visible: Boolean(box && box.width > 0 && box.height > 0), overflow: document.documentElement.scrollWidth - innerWidth,
            label: callouts[0]?.getAttribute("aria-label") };
        });
        assert.deepEqual([result.count, result.above, result.oldTakeaway, result.visible, result.overflow], [1, true, 0, true, 0], `${lang} ${width}${search} ${hash}`);
        await page.context().close();
      }
      const page = await open("#dataset", { width, lang, search });
      const dataset = await page.evaluate(() => ({ count: document.querySelectorAll("aside.key-finding").length, overflow: document.documentElement.scrollWidth - innerWidth }));
      assert.deepEqual(dataset, { count: 3, overflow: 0 }, `${lang} ${width}${search} dataset`);
      await page.context().close();
    }
  });

  await check("E4 fairness line is visible above the Key finding at 1280 and 375 (EN and VI); config has no 'Not available yet'", async () => {
    for (const lang of ["en", "vi"]) for (const width of [1280, 375]) {
      const page = await open("#experiments/e4", { width, lang });
      const line = page.locator(".fairness-line");
      assert.ok(await line.isVisible(), `${lang} ${width}: fairness line visible`);
      const box = await line.boundingBox();
      assert.ok(box.x >= 0 && box.x + box.width <= width, `${lang} ${width}: inside the viewport`);
      const order = await page.evaluate(() => Boolean(document.querySelector(".fairness-line").compareDocumentPosition(document.querySelector(".key-finding")) & Node.DOCUMENT_POSITION_FOLLOWING));
      assert.ok(order, "fairness line above the Key finding");
      await page.locator(".e4-config > summary").click();
      const configText = await page.locator(".e4-config").innerText();
      assert.ok(!configText.includes(lang === "en" ? "Not available yet" : "Chưa có"), `${lang} ${width}: E4 config`);
      await page.context().close();
    }
  });

  await check("E3/E4 charts: at most two per row, every card >= 440 px at 1280, equal one-line titles per row", async () => {
    for (const lang of ["en", "vi"]) for (const hash of ["#experiments/e3", "#experiments/e4"]) {
      const page = await open(hash, { width: 1280, lang });
      const cards = await page.evaluate(() => [...document.querySelectorAll("figure.chart")].map((figure) => {
        const box = figure.getBoundingClientRect();
        const caption = figure.querySelector("figcaption").getBoundingClientRect();
        const line = parseFloat(getComputedStyle(figure.querySelector("figcaption")).lineHeight);
        return { top: Math.round(box.top), left: Math.round(box.left), width: box.width, captionHeight: caption.height, lines: Math.round(caption.height / line) };
      }));
      assert.equal(cards.length, 3, `${lang} ${hash}`);
      for (const card of cards) assert.ok(card.width >= 440, `${lang} ${hash}: card ${Math.round(card.width)} px`);
      const rows = [...new Set(cards.map((card) => card.top))];
      assert.equal(rows.length, 2, `${lang} ${hash}: two rows`);
      assert.equal(cards[2].left, cards[0].left, `${lang} ${hash}: third chart left-aligned`);
      assert.equal(Math.round(cards[2].width), Math.round(cards[0].width), `${lang} ${hash}: same width`);
      for (const card of cards) assert.equal(card.lines, 1, `${lang} ${hash}: one-line title`);
      await page.context().close();
    }
  });

  const stickyState = (page) => page.evaluate(() => {
    const header = document.querySelector(".topbar").getBoundingClientRect();
    const bar = document.querySelector(".subbar").getBoundingClientRect();
    return { headerBottom: header.bottom, top: bar.top, bottom: bar.bottom, height: bar.height, visible: bar.bottom > 0 && bar.top < innerHeight };
  });

  await check("sticky sub-bars: after scrolling 1500 px the tab's bar is visible right under the header (1280, 375; EN, VI)", async () => {
    for (const lang of ["en", "vi"]) for (const width of [1280, 375]) {
      for (const hash of ["#experiments/e1", "#recommendation", "#dataset"]) {
        const page = await open(hash, { width, height: 800, lang });
        await page.evaluate(() => window.scrollTo(0, 1500));
        await page.waitForTimeout(150);
        const state = await stickyState(page);
        assert.ok(state.visible, `${lang} ${width} ${hash}: bar visible`);
        assert.ok(Math.abs(state.top - Math.max(0, state.headerBottom)) <= 1, `${lang} ${width} ${hash}: bar top ${state.top} vs header bottom ${state.headerBottom}`);
        if (width === 375) assert.ok(Math.max(0, state.headerBottom) + state.height <= 120, `${lang} ${hash}: header + sub-bar ${Math.max(0, state.headerBottom) + state.height} px at 375`);
        assert.ok(await page.locator(".subbar.is-stuck").count() === 1, `${lang} ${width} ${hash}: stuck state`);
        await page.context().close();
      }
    }
  });

  await check("switching to E3 while scrolled shows the E3 title below the sub-nav (1280, 375)", async () => {
    for (const width of [1280, 375]) {
      const page = await open("#experiments/e1", { width, height: 800 });
      await page.evaluate(() => window.scrollTo(0, 1500));
      await page.waitForTimeout(150);
      await page.locator(".subtabs a[href='#experiments/e3']").click();
      await page.waitForFunction(() => document.getElementById("title-E3"));
      await page.waitForTimeout(150);
      const { bar, title } = await page.evaluate(() => ({ bar: document.querySelector(".subbar").getBoundingClientRect().bottom, title: document.getElementById("title-E3").getBoundingClientRect().top }));
      assert.ok(title >= bar - 0.5 && title < 800, `${width}: E3 title top ${title}, sub-nav bottom ${bar}`);
      await page.context().close();
    }
  });

  await check("Dataset nav: 'Key findings' lands below the sub-bar and is aria-current; hash survives reload", async () => {
    for (const lang of ["en", "vi"]) for (const width of [1280, 375]) {
      const page = await open("#dataset", { width, height: 800, lang });
      await page.locator(".dataset-nav a[href='#dataset/key-findings']").click();
      await page.waitForTimeout(400);
      const result = await page.evaluate(() => ({
        bar: document.querySelector(".subbar").getBoundingClientRect().bottom,
        heading: document.getElementById("dataset-key-findings-title").getBoundingClientRect().top,
        current: document.querySelector(".dataset-nav [aria-current='true']")?.getAttribute("href"),
      }));
      assert.ok(result.heading >= result.bar - 0.5 && result.heading < 400, `${lang} ${width}: heading ${result.heading} vs bar ${result.bar}`);
      assert.equal(result.current, "#dataset/key-findings", `${lang} ${width}: aria-current`);
      await page.reload({ waitUntil: "networkidle" });
      await page.waitForTimeout(400);
      const after = await page.evaluate(() => ({ bar: document.querySelector(".subbar").getBoundingClientRect().bottom, heading: document.getElementById("dataset-key-findings-title").getBoundingClientRect().top }));
      assert.ok(after.heading >= after.bar - 0.5 && after.heading < 400, `${lang} ${width}: after reload heading ${after.heading} vs bar ${after.bar}`);
      await page.context().close();
    }
  });

  await check("chart tooltip and glossary popover opened near the sub-bar are not covered by it", async () => {
    const page = await open("#experiments/e1", { width: 1280, height: 800 });
    // Stick the sub-nav, select a bar (pinned tooltip), then scroll until the tooltip overlaps the sub-nav.
    await page.evaluate(() => window.scrollTo(0, 400));
    await page.locator("[data-mark='Popularity']").first().scrollIntoViewIfNeeded();
    await page.locator("[data-mark='Popularity']").first().click();
    await page.mouse.move(5, 790);
    await page.evaluate(() => {
      const tip = document.querySelector(".tooltip").getBoundingClientRect();
      const bar = document.querySelector(".subbar").getBoundingClientRect();
      window.scrollBy(0, tip.top - bar.top - 12);
    });
    await page.waitForTimeout(150);
    const result = await page.evaluate(() => {
      const tip = document.querySelector(".tooltip");
      tip.style.pointerEvents = "auto"; // the tooltip ignores the pointer by design; enable it only to hit-test the paint order
      const box = tip.getBoundingClientRect();
      const bar = document.querySelector(".subbar").getBoundingClientRect();
      const header = document.querySelector(".topbar").getBoundingClientRect();
      const overlapY = Math.max(box.top, bar.top) + 4;
      const onTop = [box.left + 12, box.left + box.width / 2].every((x) => tip.contains(document.elementFromPoint(x, overlapY)));
      // Outside the tooltip the sub-nav itself must still be on top of the chart card.
      const barX = Math.min(bar.right - 20, box.right + 40);
      const barOnTop = document.querySelector(".subbar").contains(document.elementFromPoint(barX, bar.top + bar.height / 2));
      return { overlaps: box.top < bar.bottom && box.bottom > bar.top, onTop, barOnTop, belowHeader: box.top >= header.bottom - 0.5 || !document.querySelector(".topbar").contains(document.elementFromPoint(box.left + 12, header.bottom - 4)) };
    });
    assert.ok(result.overlaps, "the tooltip overlaps the sub-nav area");
    assert.ok(result.onTop, "tooltip is drawn above the sub-nav");
    assert.ok(result.barOnTop, "the sub-nav stays above the chart card");
    await page.keyboard.press("Escape");
    // Glossary popover from the stuck Recommendations control bar.
    await page.goto(`${home}#recommendation`, { waitUntil: "networkidle" });
    await page.evaluate(() => window.scrollTo(0, 1500));
    await page.waitForTimeout(150);
    await page.locator(".control-bar .glossary .popover-button").click();
    const popoverOnTop = await page.evaluate(() => {
      const pop = document.querySelector(".control-bar .popover:not([hidden])");
      const box = pop.getBoundingClientRect();
      return [[box.left + 10, box.top + 10], [box.left + box.width / 2, box.top + box.height / 2]].every(([x, y]) => pop.contains(document.elementFromPoint(x, y)));
    });
    assert.ok(popoverOnTop, "glossary popover is drawn above the content and the sub-bar");
    await page.context().close();
  });

  await check("select chevron sits >= 12 px from the select's right border (Session, Dataset subset)", async () => {
    for (const [hash, scope] of [["#recommendation", ".control-bar"], ["#dataset", "#view"]]) for (const width of [1280, 375]) {
      const page = await open(hash, { width, height: 800 });
      const gap = await page.evaluate((selector) => {
        const wrap = document.querySelector(`${selector} .select-wrap`);
        const select = wrap.querySelector("select").getBoundingClientRect();
        const chevron = wrap.querySelector(".select-chevron").getBoundingClientRect();
        return { gap: select.right - chevron.right, height: select.height, appearance: getComputedStyle(wrap.querySelector("select")).appearance };
      }, scope);
      assert.ok(gap.gap >= 12, `${hash} ${width}: chevron gap ${gap.gap}`);
      assert.equal(gap.height, 44);
      assert.equal(gap.appearance, "none");
      await page.context().close();
    }
  });

  await check("hit row and Actual-next-item panel highlight each other", async () => {
    const tip = await open("#recommendation");
    await tip.locator(".presenter-tip").click();
    await tip.locator("tr.is-hit").hover();
    assert.match(await tip.locator(".actual-panel").getAttribute("class"), /is-linked/);
    await tip.locator(".actual-panel").hover();
    assert.match(await tip.locator("tr.is-hit").getAttribute("class"), /is-linked/);
    assert.ok(/Hit — the actual item is ranked \d+ of 20/.test(await tip.locator(".hit-sentence").innerText()));
    await tip.context().close();
  });

  await check("session 21546: exactly one Top-20 row has the hit background, and it is the actual next item (each model)", async () => {
    const page = await open("#recommendation", { search: "?session=21546" });
    for (const model of ["Popularity", "GRU", "XLNet"]) {
      await page.locator(".model-picker button", { hasText: model }).click();
      const result = await page.evaluate(() => {
        const panelBg = getComputedStyle(document.querySelector(".actual-panel")).backgroundColor;
        const target = document.querySelector(".actual-panel .product-id")?.textContent.trim();
        const rows = [...document.querySelectorAll(".ranking tbody tr")];
        const highlighted = rows.filter((row) => getComputedStyle(row.querySelector("td")).backgroundColor === panelBg);
        return { panelBg, target, ids: highlighted.map((row) => row.querySelector(".product-id")?.textContent.trim()),
          bold: highlighted.map((row) => getComputedStyle(row.querySelector(".rank")).fontWeight) };
      });
      assert.notEqual(result.panelBg, "rgba(0, 0, 0, 0)", `${model}: Actual panel has the hit background`);
      assert.deepEqual(result.ids, [result.target], `${model}: highlighted rows`);
      assert.deepEqual(result.bold, ["700"], `${model}: bold rank`);
    }
    await page.context().close();
  });

  await check("miss session 46465: no highlighted row, neutral Actual panel", async () => {
    const page = await open("#recommendation", { search: "?session=46465" });
    const result = await page.evaluate(() => ({ rows: document.querySelectorAll(".ranking tr.is-hit").length, panel: document.querySelector(".actual-panel").className }));
    assert.equal(result.rows, 0);
    assert.ok(!result.panel.includes("is-hit"), result.panel);
    await page.context().close();
  });

  await check("footer provenance: product-info.json shows source, SHA and export date; no 'Not available yet'", async () => {
    const page = await open("#recommendation");
    const footer = (await page.locator("footer li").allInnerTexts()).join("\n");
    const line = footer.split("\n").find((text) => text.includes("product-info.json"));
    assert.match(line ?? "", /Source week-010\.parquet · SHA [0-9a-f]{8} · Exported \d{4}-\d{2}-\d{2}/, line);
    assert.ok(!footer.includes("Not available yet"), footer);
    await page.context().close();
  });

  await check("static loading message before the bundle runs; replaced after mount", async () => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    let release;
    const gate = new Promise((resolve) => { release = resolve; });
    await page.route(/\/assets\/.*\.js$/, async (route) => { await gate; await route.continue(); });
    // Module scripts delay DOMContentLoaded, so wait only for the response and the static markup.
    await page.goto(`${home}#recommendation`, { waitUntil: "commit" });
    await page.waitForSelector("#root .boot");
    assert.equal((await page.locator("#root .boot").innerText()).trim(), "Loading the demo…");
    release();
    await page.waitForSelector(".page-title");
    assert.equal(await page.locator("#root .boot").count(), 0);
    await context.close();
  });

  await check("375 px: every number–unit pair uses U+00A0 and no unit starts a line (E1–E5, Recommendations, EN and VI)", async () => {
    for (const lang of ["en", "vi"]) {
      for (const hash of ["#recommendation", "#experiments/e1", "#experiments/e2", "#experiments/e3", "#experiments/e4", "#experiments/e5"]) {
        const page = await open(hash, { width: 375, height: 812, lang });
        const problems = await page.evaluate(() => {
          const found = [];
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          const pair = /\d[\d.,]*([\s\u00A0])(s|ms|MiB|GiB|KB|MB)(?![\p{L}\p{N}])/gu;
          for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            if (node.parentElement?.closest("svg, script, style, code")) continue;
            for (const match of node.data.matchAll(pair)) {
              if (match[1] !== "\u00A0") { found.push(`ordinary space: "${match[0]}"`); continue; }
              const range = document.createRange();
              const unitStart = match.index + match[0].length - match[2].length;
              range.setStart(node, match.index); range.setEnd(node, match.index + 1);
              const number = range.getClientRects()[0];
              range.setStart(node, unitStart); range.setEnd(node, unitStart + 1);
              const unit = range.getClientRects()[0];
              if (number && unit && Math.abs(number.top - unit.top) > 2 && unit.width > 0) found.push(`unit on a new line: "${match[0]}"`);
            }
          }
          return found;
        });
        assert.deepEqual(problems, [], `${lang} ${hash}: ${problems.join(" | ")}`);
        await page.context().close();
      }
    }
  });

  await check("glossary popover: opens, Esc closes and returns focus", async () => {
    const page = await open("#recommendation");
    const button = page.locator(".history-panel .glossary .popover-button");
    await button.click();
    assert.ok(await page.locator(".history-panel .popover").isVisible());
    await page.keyboard.press("Escape");
    assert.ok(!(await page.locator(".history-panel .popover").isVisible()));
    assert.ok(await button.evaluate((el) => el === document.activeElement));
    await page.context().close();
  });

  await check("presenter mode: ?present=1, toggle, remembered", async () => {
    const page = await open("#recommendation", { search: "?present=1" });
    assert.ok(await page.evaluate(() => document.documentElement.classList.contains("presenter")));
    assert.equal(await page.locator("body").evaluate((el) => getComputedStyle(el).fontSize), "18px");
    await page.locator(".presenter-toggle").click();
    assert.ok(!(await page.evaluate(() => document.documentElement.classList.contains("presenter"))));
    assert.equal(await page.evaluate(() => localStorage.getItem("tv4-presenter")), "0");
    await page.locator(".presenter-toggle").click();
    await page.goto(`${home}#experiments/e1`);
    assert.ok(await page.evaluate(() => document.documentElement.classList.contains("presenter")), "remembered");
    assert.ok(Number.parseFloat(await page.locator(".chart-tick").first().evaluate((el) => getComputedStyle(el).fontSize)) >= 14, "chart labels >= 14 px");
    await page.context().close();
  });

  await check("fold: History, Actual next item and Hit/Miss sentence visible at 1280x800 (EN, VI)", async () => {
    for (const lang of ["en", "vi"]) {
      const page = await open("#recommendation", { lang });
      for (const selector of [".history-panel", ".actual-panel", ".hit-sentence"]) {
        const box = await page.locator(selector).boundingBox();
        assert.ok(box && box.y >= 0 && box.y + box.height <= 800, `${lang} ${selector}: ${JSON.stringify(box)}`);
      }
      await page.context().close();
    }
  });

  await check("touch targets: summaries, links and buttons are >= 44 px tall (1280 and 375)", async () => {
    for (const [hash, width] of [["#experiments/e5", 1280], ["#experiments/e5", 375], ["#recommendation", 1280], ["#experiments/e1", 375]]) {
      const page = await open(hash, { width, height: 900 });
      const mark = page.locator("[data-mark]").first();
      if (await mark.count()) { await mark.scrollIntoViewIfNeeded(); await mark.click(); }
      const small = await page.evaluate(() => [...document.querySelectorAll("summary, .selection-bar a, .e1-strip a, .column-link, button, select")]
        .filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.height < 43.5; })
        .map((el) => `${el.tagName} "${(el.textContent || "").trim().slice(0, 30)}" ${Math.round(el.getBoundingClientRect().height)}px`));
      assert.deepEqual(small, [], `${hash} @${width}`);
      await page.context().close();
    }
  });

  await check("header title never truncates (1024-1440, default and presenter, EN and VI)", async () => {
    for (const lang of ["en", "vi"]) for (const search of ["", "?present=1"]) for (const width of [1024, 1101, 1180, 1280, 1440]) {
      const page = await open("#recommendation", { width, lang, search });
      const fit = await page.evaluate(() => {
        const name = [...document.querySelectorAll(".brand-name > span")].find((el) => getComputedStyle(el).display !== "none");
        const inner = document.querySelector(".topbar-inner");
        return { clipped: name.scrollWidth > name.clientWidth + 0.5 || name.getBoundingClientRect().width < name.scrollWidth - 0.5,
          ellipsis: getComputedStyle(document.querySelector(".brand-name")).textOverflow === "ellipsis",
          rowOverflow: inner.scrollWidth > inner.clientWidth + 0.5, text: name.textContent };
      });
      assert.deepEqual([fit.clipped, fit.ellipsis, fit.rowOverflow], [false, false, false], `${lang} ${search || "default"} ${width}: ${fit.text}`);
      await page.context().close();
    }
  });

  await check("chart labels are never truncated (no ellipsis) at 1440/1280/768/375, EN and VI, default and presenter", async () => {
    for (const lang of ["en", "vi"]) for (const search of ["", "?present=1"]) for (const width of [1440, 1280, 768, 375]) {
      for (const hash of ["#experiments/e1", "#experiments/e2", "#experiments/e3", "#experiments/e4", "#experiments/e5"]) {
        const page = await open(hash, { width, lang, search });
        const cut = await page.evaluate(() => [...document.querySelectorAll("figure.chart svg text")].map((t) => t.textContent).filter((text) => text.includes("…") || text.includes("...")));
        assert.deepEqual(cut, [], `${lang} ${search || "default"} ${width} ${hash}`);
        await page.context().close();
      }
    }
  });

  await check("sticky header <= 56 px and anchors clear it", async () => {
    const page = await open("#experiments/e1", { width: 1440, height: 900 });
    const header = await page.locator(".topbar").boundingBox();
    assert.ok(header.height <= 56, `header ${header.height}`);
    const padding = await page.evaluate(() => Number.parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop));
    const subbar = await page.locator(".subbar").boundingBox();
    assert.ok(padding >= header.height + subbar.height, `scroll-padding-top ${padding} clears header + sub-bar`);
    await page.context().close();
  });
} finally {
  await browser.close();
  await server.close();
}

for (const [status, name, detail] of results) console.log(`${status} - ${name}${detail ? `: ${detail}` : ""}`);
const failed = results.filter(([status]) => status !== "ok");
console.log(`\n# e2e checks ${results.length}, pass ${results.length - failed.length}, fail ${failed.length}`);
process.exit(failed.length ? 1 : 0);
