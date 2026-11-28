import test from "node:test";
import assert from "node:assert/strict";
import {
  byteDisplayUnit, formatBytes, formatCount, formatGeneralNumber, formatMsPerSession, formatNumberOnly,
  formatPercent, formatPercentShare, formatRatio, formatScore, formatSeconds, formatSecondsPerMillionEvents, dateRange, isMissing, joinUnit, keepUnitsTogether, NBSP, significant3,
} from "../src/format.js";
import { setLanguage } from "../src/i18n.js";

setLanguage("en");

test("ratios: 4 decimals, raw value kept for the tooltip", () => {
  assert.deepEqual(formatRatio(0.08676140613313388), { text: "0.0868", raw: "0.08676140613313388" });
  assert.equal(formatRatio(0.6309297535714575).text, "0.6309");
  assert.equal(formatRatio(0).text, "0.0000", "a real zero stays zero");
  assert.equal(formatRatio(1).text, "1.0000");
});

test("times: 3 significant digits with the unit", () => {
  assert.equal(formatSeconds(1.5164737080049235).text, "1.52\u00A0s");
  assert.equal(formatSeconds(56.9021).text, "56.9\u00A0s");
  assert.equal(formatSeconds(327.5).text, "328\u00A0s");
  assert.equal(formatSeconds(432.6).text, "433\u00A0s");
  assert.equal(formatSeconds(0.17255).text, "0.173\u00A0s");
  assert.equal(formatSeconds(0.0759633).text, "0.0760\u00A0s", "trailing zero kept as a significant digit");
  assert.equal(formatSeconds(999.6).text, "1,000\u00A0s", "carry over to the next power of ten");
  assert.equal(formatSeconds(12345.6).text, "12,346\u00A0s", ">= 1000 is a grouped integer");
  assert.equal(formatSeconds(0).text, "0\u00A0s");
  assert.equal(formatSeconds(65.94311637600003).raw, "65.94311637600003");
  assert.equal(formatSecondsPerMillionEvents(66.73532777002474).text, "66.7\u00A0s/million events");
  assert.equal(formatMsPerSession(0.5250182557969135).text, "0.525\u00A0ms/session");
  assert.equal(formatMsPerSession(0.05681625056096548).text, "0.0568\u00A0ms/session");
  assert.equal(significant3(-2.346), "-2.35");
});

test("number and unit are joined with U+00A0; percent stays attached", () => {
  assert.equal(NBSP, "\u00A0");
  assert.equal(joinUnit("882,808", "events"), "882,808\u00A0events");
  assert.equal(formatPercentShare(51.68347).text, "51.7%");
  assert.equal(keepUnitsTogether("Tesla T4 15360 MiB"), "Tesla T4 15360\u00A0MiB", "delivered text: only the unit space changes");
  assert.equal(keepUnitsTogether("Ubuntu 22.04"), "Ubuntu 22.04");
});

test("dateRange: inclusive window and half-open scope from the JSON text", () => {
  assert.deepEqual(dateRange("2019-10-01 .. 2019-10-07 UTC"), { start: "2019-10-01", end: "2019-10-07" });
  assert.deepEqual(dateRange("UTC [2019-10-01, 2019-10-08); non-null", { endExclusive: true }), { start: "2019-10-01", end: "2019-10-07" });
  assert.equal(dateRange("no dates"), null);
  assert.equal(dateRange(null), null);
});

test("bytes: MiB or GiB with 1 decimal and an explicit unit", () => {
  assert.deepEqual(formatBytes(134004153), { text: "127.8\u00A0MiB", raw: "134004153" });
  assert.equal(formatBytes(25382745).text, "24.2\u00A0MiB");
  assert.equal(formatBytes(7977566208).text, "7.4\u00A0GiB");
  assert.equal(formatBytes(134004153, "GiB").text, "0.1\u00A0GiB", "a shared row unit can be forced");
  assert.equal(byteDisplayUnit([1, 2 * 1024 ** 3]), "GiB");
  assert.equal(byteDisplayUnit([1, null, Number.NaN]), "MiB");
});

test("counts, percentages, scores and general numbers", () => {
  assert.equal(formatCount(882808).text, "882,808");
  assert.equal(formatCount(1337).text, "1,337");
  assert.equal(formatPercent(48.58634).text, "48.59%");
  assert.deepEqual(formatPercentShare(51.68347156956679), { text: "51.7%", raw: "51.68347156956679" });
  assert.equal(formatPercentShare(88.05888).text, "88.1%");
  assert.equal(formatScore(0.8125).text, "0.8125");
  assert.equal(formatGeneralNumber(63398), "63,398");
  assert.equal(formatGeneralNumber(0.123456), "0.1235");
});

test("number-only cells drop the unit that lives in the header, keep the raw value", () => {
  assert.deepEqual(formatNumberOnly(formatSeconds, 28.132), { text: "28.1", raw: "28.132" });
  assert.deepEqual(formatNumberOnly(formatBytes, 134004153, "GiB"), { text: "0.1", raw: "134004153" });
  assert.equal(formatNumberOnly(formatSecondsPerMillionEvents, 55.6372).text, "55.6");
  assert.equal(formatNumberOnly(formatMsPerSession, 0.525).text, "0.525");
  assert.equal(formatNumberOnly(formatSeconds, null).text, "Not available yet");
});

test("missing values never print NaN, undefined, null or 0", () => {
  for (const value of [null, undefined, "", Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]) {
    assert.equal(isMissing(value), true, String(value));
    for (const formatter of [formatRatio, formatSeconds, formatSecondsPerMillionEvents, formatMsPerSession, formatBytes, formatCount, formatPercent, formatPercentShare, formatScore]) {
      const { text, raw } = formatter(value);
      assert.equal(text, "Not available yet", `${formatter.name}(${String(value)})`);
      assert.equal(raw, String(value));
      assert.ok(!/NaN|undefined|null|^0$/.test(text));
    }
  }
  assert.equal(formatGeneralNumber(Number.NaN), "Not available yet");
  assert.equal(isMissing(0), false);
  setLanguage("vi");
  assert.equal(formatRatio(Number.NaN).text, "Chưa có");
  setLanguage("en");
});
