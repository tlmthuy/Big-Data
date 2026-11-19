"""Execute one argv without a shell and preserve runtime/RSS/stdout/stderr."""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


def run_command(argv, output, metadata=None):
    if not argv or not all(isinstance(arg, str) and arg for arg in argv):
        raise ValueError("Command must be a nonempty argv list")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = {"argv": argv, "metadata": metadata or {},
              "started_at": datetime.now(timezone.utc).isoformat(),
              "peak_process_tree_rss_bytes": 0, "rss_sampling_seconds": 0.05,
              "rss_scope": "sum of sampled parent/child RSS; shared pages may be counted twice",
              "stdout": str(output / "stdout.txt"), "stderr": str(output / "stderr.txt")}
    tick = time.perf_counter()
    try:
        with (output / "stdout.txt").open("w", encoding="utf-8") as stdout, \
                (output / "stderr.txt").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
            try:
                parent = psutil.Process(process.pid)
            except psutil.NoSuchProcess:
                parent = None
            while process.poll() is None:
                try:
                    members = [parent, *parent.children(recursive=True)] if parent else []
                    rss = 0
                    for member in members:
                        try:
                            rss += member.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    record["peak_process_tree_rss_bytes"] = max(record["peak_process_tree_rss_bytes"], rss)
                except psutil.NoSuchProcess:
                    pass
                time.sleep(0.05)
            record["exit_code"] = process.wait()
            record["status"] = "passed" if record["exit_code"] == 0 else "failed"
    except OSError as error:
        record.update(status="failed", exit_code=None, error=str(error))
    finally:
        record["elapsed_seconds"] = time.perf_counter() - tick
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record
