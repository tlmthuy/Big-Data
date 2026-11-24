# TV2 raw-log analysis evidence — 24/11/2026

Source VM: SSH alias `bigdata-ec2`; workspaces `/home/ubuntu/Big-Data` (E1–E3/E5) and `/home/ubuntu/Big-Data-e4` (E4 full rerun). `source_manifest.json` records original workspace/path/SHA-256 for 62 files. Files under `evidence/` preserve original bytes. No raw datasets or checkpoints are included.

`prediction_checks.json` records metrics recomputed directly from 9 original prediction JSONL files on the VM, with SHA-256. The predictions themselves remain on the VM; this check does not claim catalog completeness solely from summary JSON. Analysis reads raw run/metrics JSON, not `metrics/e*-tv3-run-summary.json`.

Reproduce tables and SVG with `python -m scripts.analyze_results`. Optional matplotlib produces PNG too. The script verifies source checksums, model run identities, prediction-check consistency, E1 shared input, E3 fixed configuration, E4 pair fingerprint and E5 provenance/timing protocol. A repeated run revalidates existing E5 rows; it refuses to overwrite differing E5 results. `analysis_validation.json` is the recorded result.

Report: `reports/tables/tv2-20261124/analysis.md`. Single-run results; sampled RSS remains descriptive only. E4 smoke pair is retained as historical evidence but excluded from the official table. No GPU training or benchmark was rerun for this analysis.

Instructor-feedback supplement: `scripts/analyze_sampling.py` adds descriptive sampling/event/length/retention/split/stage tables to the same report, and writes `instructor_feedback_analysis.md`. It reads the selected cuDF E2 manifest, raw counts, raw audit, sampling manifest and original E2 model metrics; `supplement_validation.json` pins inputs with newline-normalized text SHA-256. It does not modify preprocessing, change split/catalog or present proposed fixed-holdout experiments as completed runs.
