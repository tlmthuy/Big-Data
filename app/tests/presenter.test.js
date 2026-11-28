import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { readPresenter, savePresenter } from "../src/presenter.js";

const memory = () => {
  const store = new Map();
  return { getItem: (key) => store.get(key) ?? null, setItem: (key, value) => store.set(key, value) };
};

test("presenter mode: URL param wins, otherwise the remembered choice", () => {
  const storage = memory();
  assert.equal(readPresenter("", storage), false);
  assert.equal(readPresenter("?present=1", storage), true);
  savePresenter(true, storage);
  assert.equal(readPresenter("", storage), true);
  assert.equal(readPresenter("?present=0", storage), false);
});

test("presenter mode survives storage that throws", () => {
  const broken = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };
  assert.equal(readPresenter("", broken), false);
  assert.doesNotThrow(() => savePresenter(true, broken));
});

test("presenter CSS enlarges text, keeps labels >= 14 px and drops glass", () => {
  const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
  const block = css.slice(css.indexOf("\n.presenter {"), css.indexOf("}", css.indexOf("\n.presenter {")));
  const size = (token) => Number(block.match(new RegExp(`--t-${token}:\\s*\\d+\\s+(\\d+)px`))[1]);
  assert.equal(size("body"), 18);
  assert.ok(size("table") >= 16 && size("table") <= 18);
  assert.ok(size("footnote") >= 14, "chart labels and captions >= 14 px");
  assert.match(css, /\.presenter \.glass \{ background: var\(--surface\); -webkit-backdrop-filter: none; backdrop-filter: none; \}/);
});
