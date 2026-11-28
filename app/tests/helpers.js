// Shared test helper for sentences that contain formatted values.
import assert from "node:assert/strict";

export const NBSP = " ";
const BROKEN_UNIT = /\d[\d.,]* (?:s|ms\/session|MiB|GiB)(?![\w/])/;

/**
 * Asserts that every number–unit pair in `text` is joined with U+00A0 (src/format.js NBSP),
 * then returns the text with U+00A0 shown as an ordinary space so expectations stay readable.
 */
export function plain(text) {
  assert.ok(!BROKEN_UNIT.test(text), `number and unit joined with an ordinary space: ${text}`);
  return String(text).replaceAll(NBSP, " ");
}
