// WCAG 2 contrast for the design tokens in src/styles.css: light, dark, high contrast and text on glass.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

function tokens(block) {
  return Object.fromEntries([...block.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-f]{6});/gi)].map(([, name, hex]) => [name, hex.toLowerCase()]));
}
function rgbaTokens(block) {
  return Object.fromEntries([...block.matchAll(/--([a-z0-9-]+):\s*rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\);/gi)]
    .map(([, name, r, g, b, a]) => [name, { rgb: [r, g, b].map(Number), alpha: Number(a) }]));
}
function between(start, end, from = 0) {
  const s = css.indexOf(start, from);
  assert.ok(s >= 0, `missing block ${start}`);
  return css.slice(s, css.indexOf(end, s + start.length));
}

const lightBlock = between(":root {", "@media (prefers-color-scheme: dark)");
const darkBlock = between("@media (prefers-color-scheme: dark)", "@media (prefers-contrast: more)");
const hcBlock = between("@media (prefers-contrast: more) {", "@media (prefers-contrast: more) and (prefers-color-scheme: dark)");
const hcDarkBlock = between("@media (prefers-contrast: more) and (prefers-color-scheme: dark)", "\n}\n");
const light = tokens(lightBlock);
const dark = { ...light, ...tokens(darkBlock) };
const themes = {
  light,
  dark,
  "high contrast light": { ...light, ...tokens(hcBlock) },
  "high contrast dark": { ...dark, ...tokens(hcBlock), ...tokens(hcDarkBlock) },
};
const glass = { light: rgbaTokens(lightBlock).glass, dark: rgbaTokens(darkBlock).glass };

const hexToRgb = (hex) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
function luminanceRgb(rgb) {
  const [r, g, b] = rgb.map((value) => value / 255)
    .map((value) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratioRgb(a, b) {
  const [high, low] = [luminanceRgb(a), luminanceRgb(b)].sort((x, y) => y - x);
  return (high + 0.05) / (low + 0.05);
}
export const ratio = (a, b) => ratioRgb(hexToRgb(a), hexToRgb(b));

const TEXT = 4.5, GRAPHIC = 3;
const PAIRS = [
  // [foreground, background, minimum, what]
  ["label", "bg", TEXT, "body text on page"],
  ["label", "bg-tint", TEXT, "body text on tinted page"],
  ["label", "surface", TEXT, "body text on card"],
  ["label-2", "bg", TEXT, "secondary / footnote text on page"],
  ["label-2", "bg-tint", TEXT, "secondary text on tinted page"],
  ["label-2", "surface", TEXT, "secondary / footnote text on card"],
  ["label", "fill", TEXT, "neutral tag and code chip text"],
  ["label", "segment", TEXT, "selected segment text"],
  ["positive-text", "positive-bg", TEXT, "Hit text on its pale background"],
  ["positive-text", "surface", TEXT, "Hit text on card"],
  ["danger", "danger-bg", TEXT, "problem text on its pale background"],
  ["danger", "surface", TEXT, "problem text on card"],
  ["caution", "caution-bg", TEXT, "caution text on its pale background"],
  ["caution", "surface", TEXT, "caution text on card"],
  ["accent", "surface", TEXT, "accent text on card"],
  ["accent", "bg", TEXT, "accent text on page"],
  ["control-border", "surface", GRAPHIC, "control boundary (WCAG 1.4.11)"],
  ["control-border", "bg", GRAPHIC, "control boundary on page (WCAG 1.4.11)"],
  ["positive", "surface", GRAPHIC, "Hit marker on card"],
  ["positive", "positive-bg", GRAPHIC, "Hit marker on hit row"],
  ["label", "positive-bg", TEXT, "product ID and price in the highlighted Top-20 row / Actual panel"],
  ["label-2", "positive-bg", TEXT, "brand and category line in the highlighted row / Actual panel"],
  ["model-popularity", "surface", GRAPHIC, "Popularity mark"],
  ["model-gru", "surface", GRAPHIC, "GRU mark"],
  ["model-xlnet", "surface", GRAPHIC, "XLNet mark"],
  ["chart-neutral", "surface", GRAPHIC, "neutral chart mark"],
  ["accent", "surface", GRAPHIC, "focus ring on card"],
  ["on-positive", "positive", GRAPHIC, "Hit ✓ glyph on its green badge"],
  ["label-2", "surface", GRAPHIC, "select chevron on a select (graphic)"],
  ["label-2", "selected-bg", TEXT, "column sub-label (N events) in a selected column"],
  ["label", "selected-bg", TEXT, "cell text in a selected column"],
  ["kf-eyebrow", "kf-bg-from", TEXT, "Key finding eyebrow label (13 px) on the peach end of the gradient"],
  ["kf-eyebrow", "kf-bg-to", TEXT, "Key finding eyebrow label (13 px) on the white end of the gradient"],
  ["kf-heading", "kf-bg-from", TEXT, "Key finding headline on the peach end of the gradient"],
  ["kf-heading", "kf-bg-to", TEXT, "Key finding headline on the white end of the gradient"],
  ["kf-body", "kf-bg-from", TEXT, "Key finding body on the peach end of the gradient"],
  ["kf-body", "kf-bg-to", TEXT, "Key finding body on the white end of the gradient"],
  ["kf-number", "kf-bg-from", TEXT, "Key finding bold metric number on the peach end of the gradient"],
  ["kf-number", "kf-bg-to", TEXT, "Key finding bold metric number on the white end of the gradient"],
  ["kf-note", "kf-bg-from", TEXT, "Key finding footnote (13 px) on the peach end of the gradient"],
  ["kf-note", "kf-bg-to", TEXT, "Key finding footnote (13 px) on the white end of the gradient"],
];

const REQUIRED = ["bg", "bg-tint", "surface", "label", "label-2", "control-border", "accent", "fill", "segment",
  "positive", "positive-text", "positive-bg", "on-positive", "selected-bg", "danger", "danger-bg", "caution", "caution-bg",
  "model-popularity", "model-gru", "model-xlnet", "chart-neutral",
  "kf-bg-from", "kf-bg-to", "kf-border", "kf-eyebrow", "kf-heading", "kf-body", "kf-note", "kf-number"];

for (const [scheme, theme] of Object.entries(themes)) {
  test(`${scheme} tokens meet contrast minimums`, () => {
    for (const name of REQUIRED) assert.match(theme[name] ?? "", /^#[0-9a-f]{6}$/, `${scheme}: --${name} must be a hex token`);
    const failures = PAIRS.map(([fg, bg, minimum, what]) => ({ what, fg, bg, minimum, value: ratio(theme[fg], theme[bg]) }))
      .filter(({ value, minimum }) => value < minimum)
      .map(({ what, fg, bg, minimum, value }) => `${what}: --${fg} on --${bg} = ${value.toFixed(2)}:1 < ${minimum}:1`);
    assert.deepEqual(failures, [], scheme);
  });
}

test("high contrast: secondary text reaches 7:1 on page and card", () => {
  for (const scheme of ["high contrast light", "high contrast dark"]) {
    const theme = themes[scheme];
    for (const bg of ["bg", "surface"]) {
      assert.ok(ratio(theme["label-2"], theme[bg]) >= 7, `${scheme}: label-2 on ${bg} = ${ratio(theme["label-2"], theme[bg]).toFixed(2)}`);
      assert.ok(ratio(theme.label, theme[bg]) >= 7, `${scheme}: label on ${bg}`);
    }
  }
});

test("the three model colours are distinct from each other and from the Hit green and danger red", () => {
  for (const theme of [light, dark]) {
    const models = ["model-popularity", "model-gru", "model-xlnet"].map((name) => theme[name]);
    assert.equal(new Set(models).size, 3);
    for (const colour of models) assert.ok(![theme.positive, theme.danger].includes(colour));
  }
});

// Text on glass: the glass tint is blended over the worst content that can scroll under it
// (the darkest text in light mode, the lightest text in dark mode), with no credit for blur.
function blend(top, bottomHex) {
  const bottom = hexToRgb(bottomHex);
  return top.rgb.map((value, index) => value * top.alpha + bottom[index] * (1 - top.alpha));
}
test("text on glass passes 4.5:1 against the worst content underneath", () => {
  assert.ok(glass.light && glass.dark, "glass tokens must be rgba()");
  const cases = [
    ["light", light, ["label", "accent", "danger", "model-xlnet"]],
    ["dark", dark, ["label", "label-2", "accent", "positive"]],
  ];
  for (const [scheme, theme, under] of cases) {
    for (const content of under) {
      const behind = blend(glass[scheme], theme[content]);
      // Only primary text is placed directly on glass; secondary text sits on solid chips.
      const value = ratioRgb(hexToRgb(theme.label), behind);
      assert.ok(value >= TEXT, `${scheme}: label on glass over --${content} = ${value.toFixed(2)}:1`);
    }
  }
});

test("type scale has exactly five steps and nothing below 13 px", () => {
  const sizes = new Set([...css.matchAll(/--t-[a-z]+:\s*\d+\s+(\d+)px\//g)].map(([, size]) => Number(size)));
  assert.deepEqual([...sizes].sort((a, b) => a - b), [13, 16, 18, 22, 28]);
  const literal = [...css.matchAll(/font(?:-size)?:\s*[^;]*?(\d+(?:\.\d+)?)(px|rem|em)\b/g)]
    .filter(([match]) => !match.includes("var(--"))
    .map(([match]) => match);
  assert.deepEqual(literal, [], "font sizes must come from the type tokens");
  assert.ok(!/font-style:\s*italic/.test(css), "no italic body text");
});

test("system font stack only, no bundled SF font files", () => {
  assert.match(css, /--font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;/);
  assert.ok(!/@font-face/.test(css));
  assert.ok(!/SF Pro/.test(css));
});
