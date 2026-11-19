"""Common full-split evaluation timing; model compute remains diagnostic only."""

import time

INFERENCE_PROTOCOL = "full_evaluation_wall_v1"
INFERENCE_SCOPE = (
    "full evaluation split wall: input read/decode, sequence preparation/device transfer, "
    "prediction and Top-20, metric aggregation and prediction JSONL write/close; "
    "includes one-time Popularity ranking and native neural testing mask/labels/loss; "
    "excludes audit, model construction, training, checkpoint and metrics JSON write; "
    "single pass with no extra warmup or OS cache flush; not pure model latency"
)
TIMING_FIELDS = ("inference_seconds", "inference_timing_protocol", "inference_scope",
                 "evaluation_with_io_seconds", "inference_ms_per_session",
                 "inference_sessions_per_second", "prediction_compute_seconds",
                 "prediction_compute_scope")


def evaluation_timing(started, n_sessions, compute_seconds, compute_scope):
    elapsed = time.perf_counter() - started
    return {"inference_seconds": elapsed,
            "inference_timing_protocol": INFERENCE_PROTOCOL,
            "inference_scope": INFERENCE_SCOPE,
            "evaluation_with_io_seconds": elapsed,
            "inference_ms_per_session": elapsed * 1_000 / n_sessions if n_sessions else None,
            "inference_sessions_per_second": n_sessions / elapsed if elapsed > 0 else None,
            "prediction_compute_seconds": compute_seconds,
            "prediction_compute_scope": compute_scope}
