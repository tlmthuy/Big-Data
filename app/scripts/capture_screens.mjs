// Screenshots of every view for review (EN/VI × light/dark × 1280/375), into screenshots/ (git-ignored).
// Behaviour checks live in scripts/check_ui.mjs; this script also fails on clipped or overlapping chart text.
// Usage: npm run build && node scripts/capture_screens.mjs [outDir]
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { preview } from "vite";

const root = fileURLToPath(new URL("../", import.meta.url));
const destination = path.resolve(process.argv[2] ?? path.join(root, "screenshots"));
await mkdir(destination, { recursive: true });
const server = await preview({ root, preview: { host: "127.0.0.1", port: 0 }, logLevel: "error" });
const home = `http://127.0.0.1:${server.httpServer.address().port}/`;
const views = [["recommendation", "?session=21546#recommendation"], ["dataset", "#dataset"],
  ...["e1", "e2", "e3", "e4", "e5"].map((id) => [`experiments-${id}`, `#experiments/${id}`])];

async function chartTextProblems(page) {
  return page.evaluate(() => [...document.querySelectorAll("figure.chart")].flatMap((figure, chartIndex) => {
    const card = figure.getBoundingClientRect();
    const texts = [...figure.querySelectorAll("svg text")].map((node) => ({ text: node.textContent, rect: node.getBoundingClientRect() }));
    const outside = texts.filter(({ rect }) => rect.left < card.left - 0.5 || rect.right > card.right + 0.5 || rect.top < card.top - 0.5 || rect.bottom > card.bottom + 0.5)
      .map(({ text }) => `chart ${chartIndex}: "${text}" outside card`);
    const collisions = texts.flatMap((a, index) => texts.slice(index + 1).filter((b) =>
      Math.min(a.rect.right, b.rect.right) - Math.max(a.rect.left, b.rect.left) > 0.5
      && Math.min(a.rect.bottom, b.rect.bottom) - Math.max(a.rect.top, b.rect.top) > 0.5,
    ).map((b) => `chart ${chartIndex}: "${a.text}" overlaps "${b.text}"`));
    return [...outside, ...collisions];
  }));
}

const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || "chrome" });
try {
  for (const locale of ["en", "vi"]) {
    for (const scheme of ["light", "dark"]) {
      for (const width of [1280, 375]) {
        const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: scheme });
        await context.addInitScript((l) => { try { localStorage.setItem("tv4-language", l); } catch { /* optional */ } }, locale);
        const page = await context.newPage();
        const errors = [];
        page.on("pageerror", (error) => errors.push(error.message));
        for (const [name, url] of views) {
          await page.goto(`${home}${url}`, { waitUntil: "networkidle" });
          assert.deepEqual(await chartTextProblems(page), [], `${locale}/${scheme}/${name}@${width}`);
          await page.screenshot({ path: path.join(destination, `${locale}-${scheme}-${width}-${name}.png`), fullPage: true });
        }
        assert.deepEqual(errors, []);
        await context.close();
      }
    }
  }
  console.log(`Saved screenshots in ${destination}`);
} finally {
  await browser.close();
  await server.close();
}
