import { t } from "./i18n.js";

export const INTERPRETATION_NOTE_KEYS = [
  "inference_protocol",
  "train_seconds_including_sequence_io",
  "sampled_rss_bytes_descriptive_only",
  "sampled_gpu_process_bytes",
  "E2_accuracy",
  "E3_accuracy",
  "E4_preprocessing_wall",
  "E5_composed",
  "first_seen_shared",
];

export function interpretationNoteText(dictionaryKey) {
  return t(`note_${dictionaryKey}`);
}
