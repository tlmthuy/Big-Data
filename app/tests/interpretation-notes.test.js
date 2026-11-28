import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { messages, setLanguage, t } from "../src/i18n.js";
import { INTERPRETATION_NOTE_KEYS, interpretationNoteText } from "../src/interpretation-notes.js";

const dictionary = JSON.parse(readFileSync(new URL("../public/official-results.json", import.meta.url), "utf8")).dictionary;

test("every displayed dictionary key has localized full-sentence notes and a source label", () => {
  for (const key of INTERPRETATION_NOTE_KEYS) {
    for (const locale of ["en", "vi"]) {
      setLanguage(locale);
      const note = interpretationNoteText(key);
      assert.ok(note.length > 0 && note !== `note_${key}`, `${locale}: missing note for ${key}`);
      assert.match(note, /[.!?]$/u, `${locale}: note for ${key} must be a full sentence`);
      assert.notEqual(note, dictionary[key], `${locale}: raw dictionary text rendered for ${key}`);
      assert.ok(messages[locale][`note_${key}`], `${locale}: missing i18n note for ${key}`);
      assert.ok(t("source_dictionary", key).includes(key), `${locale}: missing source tag for ${key}`);
    }
  }
});
