import assert from "node:assert/strict";
import { test } from "node:test";
import { messages, readLanguage, setLanguage, t } from "../src/i18n.js";

test("both locales provide the same UI keys and interpolate values", () => {
  assert.deepEqual(Object.keys(messages.en).sort(), Object.keys(messages.vi).sort());
  assert.equal(readLanguage(), "en");
  setLanguage("en");
  assert.equal(t("hit_at_rank_0", 20), "Hit at rank 20");
  setLanguage("vi");
  assert.equal(t("hit_at_rank_0", 20), "✅ Trúng ở hạng 20");
});
