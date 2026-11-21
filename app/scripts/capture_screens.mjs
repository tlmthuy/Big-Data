import assert from "node:assert/strict";
import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { preview } from "vite";
import { messages, setLanguage, t } from "../src/i18n.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const destination = path.join(root, "screenshots");
await mkdir(destination, { recursive: true });
const server = await preview({ root, preview: { host: "127.0.0.1", port: 0 } });
const home = `http://127.0.0.1:${server.httpServer.address().port}`;
const widths = [1280, 375];

async function assetExists(file) {
  try {
    return (await stat(path.join(root, "src/branding", file))).isFile();
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
    return false;
  }
}

async function contrast(locator) {
  return locator.evaluate((element) => {
    const channels = (color) => color.match(/[\d.]+/g).map(Number);
    const luminance = (color) => channels(color).slice(0, 3).map((channel) => {
      const value = channel / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    }).reduce((total, value, index) => total + value * [0.2126, 0.7152, 0.0722][index], 0);
    let background = element;
    while (channels(getComputedStyle(background).backgroundColor).at(3) === 0) background = background.parentElement;
    const foreground = luminance(getComputedStyle(element).color);
    const behind = luminance(getComputedStyle(background).backgroundColor);
    return (Math.max(foreground, behind) + 0.05) / (Math.min(foreground, behind) + 0.05);
  });
}

async function checkKeyboardFocus(page, locator) {
  await locator.focus();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  const focusVisible = await locator.evaluate((element) => {
    const style = getComputedStyle(element);
    return element.matches(":focus-visible") && style.outlineStyle === "solid" && parseFloat(style.outlineWidth) >= 2;
  });
  assert.ok(focusVisible, "Expected a visible keyboard focus outline");
}


try {
  const hasLogo = await assetExists("logo.png");
  const hasCover = await assetExists("cover.jpg");
  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome" });
  try {
    for (const locale of ["en", "vi"]) {
      setLanguage(locale);
      const folder = path.join(destination, locale);
      await mkdir(folder, { recursive: true });
      for (const width of widths) {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        page.setDefaultTimeout(8000);
        const errors = [];
        page.on("pageerror", (error) => errors.push(error.message));
        const capture = async (name) => {
          const text = await page.locator("body").innerText();
          const untranslated = Object.keys(messages.en).filter((key) => key.includes("_") && text.split(/\s+/).includes(key) && !["read_seconds", "input_bytes", "preprocessing_seconds"].includes(key));
          assert.deepEqual(untranslated, [], name);
          assert.deepEqual(errors, [], name);
          const overflow = await page.evaluate(() => {
            if (document.documentElement.scrollWidth <= window.innerWidth) return [];
            return [document.documentElement.scrollWidth, ...[...document.querySelectorAll("main *")].filter((el) =>
              !el.closest(".table-scroll") && el.getBoundingClientRect().right > window.innerWidth
            ).slice(0, 8).map((el) => [el.tagName, el.className, el.textContent.slice(0, 120)])];
          });
          assert.deepEqual(overflow, [], `Overflow in ${name} at ${width}`);
          await page.screenshot({ path: path.join(folder, `${name}-${width}.png`), fullPage: true });
        };
        await page.goto(`${home}/#recommendation`);
        await page.locator("html[lang=en]").waitFor();
        await page.getByLabel(messages.en.session, { exact: true }).selectOption("rank20");
        await page.getByRole("button", { name: "VI", exact: true }).click();
        await page.locator("html[lang=vi]").waitFor();
        assert.equal(await page.getByLabel(messages.vi.session, { exact: true }).inputValue(), "rank20");
        assert.equal(new URL(page.url()).hash, "#recommendation");
        if (locale === "en") {
          await page.getByRole("button", { name: "EN", exact: true }).click();
          await page.locator("html[lang=en]").waitFor();
          assert.equal(await page.getByLabel(messages.en.session, { exact: true }).inputValue(), "rank20");
        }
        const heading = page.getByRole("heading", { name: t("site_name"), exact: true });
        await heading.waitFor();
        assert.equal(await page.title(), t("site_name"));
        for (const [selector, exists] of [[".brand-logo", hasLogo], [".brand-cover", hasCover]]) {
          const image = page.locator(selector);
          assert.equal(await image.count(), Number(exists));
          if (exists) assert.ok(await image.evaluate(async (node) => { await node.decode(); return node.naturalWidth > 0; }));
        }
        assert.equal(await page.locator("img").count(), Number(hasLogo) + Number(hasCover));
        const activeLanguage = page.getByRole("button", { name: locale.toUpperCase(), exact: true });
        const inactiveLanguage = page.getByRole("button", { name: locale === "en" ? "VI" : "EN", exact: true });
        assert.equal(await activeLanguage.getAttribute("aria-pressed"), "true");
        assert.equal(await inactiveLanguage.getAttribute("aria-pressed"), "false");
        const weight = (button) => button.evaluate((node) => Number(getComputedStyle(node).fontWeight));
        assert.ok(await weight(activeLanguage) > await weight(inactiveLanguage));
        await checkKeyboardFocus(page, inactiveLanguage);
        await checkKeyboardFocus(page, page.getByRole("tab").first());

        const session = page.getByLabel(t("session"), { exact: true });
        const model = page.getByLabel("Model", { exact: true });
        for (const [id, result] of [
          ["rank1", t("hit_at_rank_0", 1)],
          ["rank20", t("hit_at_rank_0", 20)],
          ["miss", t("not_in_top_20")],
        ]) {
          await session.selectOption(id);
          await page.locator(".recommendations").getByText(result, { exact: true }).waitFor();
          const score = page.locator(".ranking td.score").first();
          assert.equal(await score.innerText(), t("not_available_yet"));
          assert.ok(await score.evaluate((cell) => {
            const text = document.createRange();
            text.selectNodeContents(cell);
            return text.getBoundingClientRect().width <= cell.clientWidth && getComputedStyle(cell).whiteSpace === "nowrap";
          }));
          assert.equal(await page.locator(".product-icon").count(), 0);
          assert.ok(await contrast(score) >= 4.5);
          for (const className of ["tag-category", "tag-history", "tag-hit"]) {
            for (const tag of await page.locator(`.${className}`).all()) {
              assert.ok(await contrast(tag) >= 4.5, `${className} text contrast`);
            }
          }
          const badge = page.getByText(t("toy_data_not_a_benchmark_result"), { exact: true }).first();
          await badge.waitFor();
          assert.ok(await contrast(badge) >= 4.5);
          await capture(id);
        }
        await page.getByText(t("price_unavailable"), { exact: true }).first().waitFor();
        const context = page.locator(".history, .actual-panel .product-card");
        const beforeSwitch = await context.allInnerTexts();
        assert.equal(beforeSwitch.length, 2);
        await model.selectOption("missing:GRU");
        await page.getByText(t("no_predictions_available_for_this_model")).waitFor();
        await page.getByRole("heading", { name: t("actual_next_item") }).waitFor();
        await page.getByRole("heading", { name: t("history") }).waitFor();
        assert.deepEqual(await context.allInnerTexts(), beforeSwitch);
        await capture("gru-no-output");
        await model.selectOption({ label: "Popularity" });
        assert.equal(await session.inputValue(), "miss");
        await page.locator(".recommendations table").waitFor();

        await page.getByRole("tab", { name: t("dataset") }).click();
        await page.getByRole("heading", { name: t("session_length") }).waitFor();
        await page.getByText(t("smoke_awaiting_tv2_confirmation"), { exact: true }).waitFor();
        const weekly = page.locator("section").filter({ has: page.getByRole("heading", { name: t("weekly_cudf_subsets"), exact: true }) });
        for (const key of ["missing_brand", "missing_category"]) {
          assert.equal(await weekly.getByRole("rowheader", { name: t(key), exact: true }).count(), 0);
        }
        assert.equal(await page.locator("[role=tabpanel] meter").count(), 21);
        await page.getByLabel(t("subset"), { exact: true }).selectOption("100");
        await capture("dataset");

        for (const id of ["e1", "e2", "e3", "e4", "e5"]) {
          await page.goto(`${home}/#experiments-${id}`);
          const panel = page.locator("[role=tabpanel] > .panel").filter({
            has: page.getByRole("heading", { name: new RegExp(`^${id} ·`, "i") }),
          });
          await panel.waitFor();
          assert.equal(await page.getByText(t("smoke_awaiting_tv2_confirmation"), { exact: true }).count(), 0);
          if (["e2", "e4"].includes(id)) {
            assert.equal(await panel.getByText(/118[,.]?113[,.]?591|25945758|25,945,758|30\.449049160999493/).count(), 0);
          }
          const toy = panel.locator(".toy-block");
          assert.equal(await panel.locator(".metric-chart meter").count(), await toy.locator("meter").count());
          assert.ok((await panel.locator(".metric-chart").first().innerText()).includes(t("not_available_yet")));
          if (["e1", "e3"].includes(id)) await toy.locator(".badge-toy").first().waitFor();
          if (id === "e3") {
            const checkbox = page.getByRole("checkbox");
            await checkKeyboardFocus(page, checkbox);
            await checkbox.uncheck();
            await checkbox.check();
            assert.equal(await checkbox.evaluate((input) => getComputedStyle(input).accentColor), "rgb(98, 69, 31)");
          }
          await capture(`experiments-${id}`);
        }
        await page.route("**/dataset-overview.json", (route) => route.fulfill({ body: "{", contentType: "application/json" }));
        await page.goto(`${home}/#data`);
        await page.reload();
        const alert = page.getByRole("alert");
        await alert.getByText(t("could_not_load_the_dataset_overview"), { exact: true }).waitFor();
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  server.httpServer.closeAllConnections();
  await new Promise((resolve, reject) => server.httpServer.close((error) => error ? reject(error) : resolve()));
}
if (!process.exitCode) console.log(`Saved screenshots in ${destination}`);
