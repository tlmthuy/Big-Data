// Pure helpers for the hand-written SVG charts and their selection state (tested with node --test).

/** Round axis: 0 … niceMax in 3–5 equal "nice" steps (1, 2, 2.5, 5 × 10^n). The axis always starts at 0. */
export function niceTicks(maxValue, target = 4) {
  const max = Number.isFinite(maxValue) && maxValue > 0 ? maxValue : 1;
  const raw = max / target;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const residual = raw / magnitude;
  const nice = residual <= 1 ? 1 : residual <= 2 ? 2 : residual <= 2.5 ? 2.5 : residual <= 5 ? 5 : 10;
  const step = nice * magnitude;
  const count = Math.ceil(max / step - 1e-9);
  const ticks = Array.from({ length: count + 1 }, (_, index) => Number((index * step).toPrecision(12)));
  return { step, max: ticks.at(-1), ticks };
}

/** Tick text with just enough decimals for the step; a tick is a number only (the unit is in the axis title). */
export function formatTick(value, step) {
  if (value === 0) return "0";
  const magnitude = 10 ** Math.floor(Math.log10(step) + 1e-9);
  const lead = Math.round((step / magnitude) * 10) / 10;
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9) + (lead === 2.5 ? 1 : 0));
  return value.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// Glyph width as a share of font size; 0.62 leaves a margin over typical proportional and mono fonts.
export const GLYPH = 0.62;
export function textWidth(text, fontSize) {
  return String(text).length * fontSize * GLYPH;
}

/**
 * Split a label into at most two lines that fit `maxWidth`. Never truncates: a single word wider than
 * `maxWidth` stays whole (the caller decides whether it may overflow its band). `measure(text, size)`
 * returns a width in px; the default is the conservative glyph estimate.
 */
export function wrapLabel(text, maxWidth, fontSize, measure = textWidth) {
  const label = String(text);
  if (measure(label, fontSize) <= maxWidth) return [label];
  const lines = [""];
  for (const word of label.split(/\s+/)) {
    const candidate = lines.at(-1) ? `${lines.at(-1)} ${word}` : word;
    if (measure(candidate, fontSize) <= maxWidth || !lines.at(-1)) lines[lines.length - 1] = candidate;
    else lines.push(word);
  }
  return lines.length > 2 ? [lines[0], lines.slice(1).join(" ")] : lines;
}

/**
 * Category labels under the bars, never truncated. Tries the chart font, then the 13 px caption size;
 * a label may run past its own band only while it stays clear of its neighbours. If neighbours still
 * collide, every other label drops one row (stagger). Returns { font, rows, labels: [[lines]], stagger }.
 */
export function categoryLabels(texts, { band, fontSize, measure = textWidth, gap = 6 }) {
  const attempt = (font, stagger) => {
    const labels = texts.map((text) => wrapLabel(text, band - 4, font, measure));
    const widths = labels.map((lines) => Math.max(...lines.map((line) => measure(line, font))));
    const rowsOf = (index) => labels[index].length + (stagger && index % 2 ? 1 : 0);
    const clash = widths.some((width, index) => {
      if (index === 0) return false;
      if (stagger) return false;
      return (widths[index - 1] + width) / 2 + gap > band;
    });
    // The first label may not reach the y-axis tick column, the last one not the frame edge.
    const edges = (widths[0] ?? 0) / 2 > band / 2 + 6 || (widths.at(-1) ?? 0) / 2 > band / 2 + 10;
    return { font, stagger, labels, clash: clash || edges, rows: Math.max(1, ...labels.map((_, index) => rowsOf(index))) };
  };
  const fonts = [...new Set([fontSize, 13])];
  for (const font of fonts) {
    const result = attempt(font, false);
    if (!result.clash) return result;
  }
  return attempt(13, true);
}

/** Selection: clicking the selected mark again clears it. */
export function toggleSelection(selected, key) {
  return selected === key ? null : key;
}

/** Arrow-key movement between marks (wraps around). Returns the new index, or null for other keys. */
export function nextMarkIndex(index, key, length) {
  if (!length) return null;
  if (key === "ArrowRight" || key === "ArrowDown") return (index + 1) % length;
  if (key === "ArrowLeft" || key === "ArrowUp") return (index - 1 + length) % length;
  if (key === "Home") return 0;
  if (key === "End") return length - 1;
  return null;
}

/**
 * Bar chart geometry at the real pixel width. Bars start at zero; the left margin follows the longest
 * tick so labels like "327.5" are never clipped. Category labels are never truncated (categoryLabels);
 * value labels that do not fit their band are hidden (the value stays in the tooltip and the table).
 */
export function barLayout(points, { width = 480, height = 240, fontSize = 13, measure = textWidth } = {}) {
  const values = points.map((point) => point.y).filter((value) => Number.isFinite(value));
  const axis = niceTicks(Math.max(0, ...values));
  const tickTexts = axis.ticks.map((value) => formatTick(value, axis.step));
  const longestTick = Math.max(...tickTexts.map((text) => textWidth(text, fontSize)));
  const titleBand = fontSize * 1.6;
  const left = Math.ceil(titleBand + longestTick + 10);
  const right = width - 12;
  const band = (right - left) / Math.max(1, points.length);
  const categories = categoryLabels(points.map((point) => point.label), { band, fontSize, measure });
  const lineHeight = Math.round(categories.font * 1.25);
  const padding = {
    left,
    right,
    top: Math.ceil(fontSize * 2 + 4),
    bottom: height - Math.ceil(lineHeight * Math.max(2, categories.rows) + 14),
  };
  const plot = padding.bottom - padding.top;
  const barWidth = Math.max(16, Math.min(64, band * 0.56));
  const y = (value) => padding.bottom - (value / axis.max) * plot;
  const bars = points.map((point, index) => {
    const cx = padding.left + band * (index + 0.5);
    const has = Number.isFinite(point.y);
    const top = has ? y(point.y) : padding.bottom;
    const valueText = point.short ?? "";
    const valueFits = has && textWidth(valueText, fontSize) <= band - 4;
    const hitWidth = Math.max(44, Math.min(band - 2, barWidth + 16));
    const hitTop = Math.min(top - fontSize - 6, padding.bottom - 44);
    return {
      ...point,
      index,
      cx,
      x: cx - barWidth / 2,
      width: barWidth,
      top,
      height: padding.bottom - top,
      has,
      valueLabel: { x: cx, y: top - 6, text: valueText, visible: valueFits },
      lines: categories.labels[index].map((text, line) => ({
        text, x: cx, y: padding.bottom + lineHeight * (line + 1 + (categories.stagger && index % 2 ? 1 : 0)),
      })),
      hit: { x: cx - hitWidth / 2, y: hitTop, width: hitWidth, height: padding.bottom - hitTop + 4 },
    };
  });
  const ticks = axis.ticks.map((value, index) => ({ value, cy: y(value), text: tickTexts[index], x: padding.left - 8 }));
  return { width, height, fontSize, categoryFont: categories.font, padding, axis, ticks, bars, yTitle: { x: fontSize + 2, y: (padding.top + padding.bottom) / 2 } };
}

const intersects = (a, b, pad = 4) => a.x0 < b.x1 + pad && b.x0 < a.x1 + pad && a.y0 < b.y1 + pad && b.y0 < a.y1 + pad;

/**
 * Where to put a chart tooltip of size {w, h} inside a frame {w, h} so it covers neither the marks in
 * `marks` (shown and selected) nor any label in `labels`. Tries, in order: above the mark, right of it,
 * left of it, then the free spot closest to the mark (8 px grid). Returns {left, top} or null when
 * nothing fits; the caller then shows the tooltip below the chart instead.
 */
export function placeTooltip({ size, frame, mark, marks = [], labels = [], gap = 8 }) {
  const obstacles = [...marks, ...labels];
  const fits = (left, top) => {
    const box = { x0: left, x1: left + size.w, y0: top, y1: top + size.h };
    return left >= 0 && top >= 0 && box.x1 <= frame.w && box.y1 <= frame.h && !obstacles.some((o) => intersects(box, o));
  };
  const clampX = (x) => Math.min(Math.max(0, x), Math.max(0, frame.w - size.w));
  const clampY = (y) => Math.min(Math.max(0, y), Math.max(0, frame.h - size.h));
  const cx = (mark.x0 + mark.x1) / 2, cy = (mark.y0 + mark.y1) / 2;
  const preferred = [
    [clampX(cx - size.w / 2), mark.y0 - gap - size.h],
    [mark.x1 + gap, clampY(cy - size.h / 2)],
    [mark.x0 - gap - size.w, clampY(cy - size.h / 2)],
  ];
  for (const [left, top] of preferred) if (fits(left, top)) return { left, top };
  let best = null;
  for (let top = 0; top + size.h <= frame.h; top += 8) {
    for (let left = 0; left + size.w <= frame.w; left += 8) {
      if (!fits(left, top)) continue;
      const distance = Math.hypot(left + size.w / 2 - cx, top + size.h / 2 - cy);
      if (!best || distance < best.distance) best = { left, top, distance };
    }
  }
  return best ? { left: best.left, top: best.top } : null;
}
