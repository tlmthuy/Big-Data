"""Execute one argv without a shell and preserve runtime/RSS/GPU/stdout/stderr."""

import argparse
import json
import shutil
import subprocess
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
import sys

import psutil


def _process_tree_snapshot(pid):
    """Return sampled RSS and PIDs for the child and live descendants."""
    try:
        parent = psutil.Process(pid)
        members = [parent, *parent.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0, set()
    rss = 0
    pids = set()
    for member in members:
        try:
            rss += member.memory_info().rss
            pids.add(member.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return rss, pids


def _nvidia_smi_values(query):
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None
    try:
        output = subprocess.check_output(
            [executable, query, "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if not output.strip():
        return None
    values = []
    for line in output.splitlines():
        value = line.rsplit(",", 1)[-1].strip()
        try:
            values.append(int(value))
        except ValueError:
            continue
    return values


def _gpu_memory_for_processes(pids):
    executable = shutil.which("nvidia-smi")
    if not executable:
        return 0, False
    try:
        output = subprocess.check_output(
            [executable, "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return 0, False
    total_mib = 0
    found = False
    for line in output.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 2:
            continue
        try:
            pid = int(fields[0])
            memory_mib = int(fields[1])
        except ValueError:
            continue
        if pid in pids:
            found = True
            total_mib += memory_mib
    return total_mib * 1024 * 1024, found


def _gpu_total_memory():
    values = _nvidia_smi_values("--query-gpu=memory.used")
    if values is None or not values:
        return 0, False
    return sum(values) * 1024 * 1024, True


def run_command(argv, output, metadata=None):
    if not argv or not all(isinstance(arg, str) and arg for arg in argv):
        raise ValueError("Command must be a nonempty argv list")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    metadata = metadata or {}
    run_id = metadata.get("run_id")
    if not run_id:
        run_id = metadata.get("run", {}).get("run_id") if isinstance(metadata.get("run"), dict) else None
    if not run_id:
        run_id = output.name
    warm_up_policy = metadata.get("warm_up_policy", "none")
    cache_policy = metadata.get("cache_policy", "no cache flush; inherited OS cache state")
    record = {"argv": argv, "metadata": metadata or {},
              "run_id": run_id, "output_path": str(output.resolve()),
              "started_at": datetime.now(timezone.utc).isoformat(),
              "peak_process_tree_rss_bytes": 0, "cpu_memory_unit": "bytes",
              "rss_sampling_seconds": 0.05,
              "rss_scope": "sum of sampled parent/child RSS; shared pages may be counted twice",
              "gpu_memory_bytes_peak": 0, "gpu_memory_unit": "bytes",
              "gpu_memory_scope": "nvidia-smi compute-app used_memory matched to sampled parent/child PIDs",
              "gpu_memory_sampling_seconds": 0.05,
              "gpu_memory_observation_available": False,
              "gpu_memory_bytes_status": "missing",
              "gpu_memory_missing_reason": "nvidia-smi or matching compute-app GPU memory was unavailable",
              "gpu_memory_total_used_bytes_peak": 0,
              "gpu_memory_total_scope": "sum of nvidia-smi memory.used across visible GPUs",
              "gpu_memory_total_used_bytes_status": "missing",
              "gpu_memory_total_missing_reason": "nvidia-smi total GPU memory was unavailable",
              "elapsed_seconds_unit": "seconds",
              "measurement_scope": "child process wall time; sampled process-tree RSS/GPU memory; excludes run.json write",
              "warm_up_policy": warm_up_policy,
              "cache_policy": cache_policy,
              "stdout": str((output / "stdout.txt").resolve()),
              "stderr": str((output / "stderr.txt").resolve())}
    tick = time.perf_counter()
    try:
        with (output / "stdout.txt").open("w", encoding="utf-8") as stdout, \
                (output / "stderr.txt").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
            exit_state = threading.Event()
            completion = {}

            def wait_for_child():
                try:
                    completion["exit_code"] = process.wait()
                    completion["finished_perf_counter"] = time.perf_counter()
                finally:
                    exit_state.set()

            waiter = threading.Thread(target=wait_for_child, daemon=True)
            waiter.start()

            rss, pids = _process_tree_snapshot(process.pid)
            record["peak_process_tree_rss_bytes"] = max(record["peak_process_tree_rss_bytes"], rss)
            gpu_bytes, gpu_available = _gpu_memory_for_processes(pids)
            record["gpu_memory_observation_available"] = record["gpu_memory_observation_available"] or gpu_available
            record["gpu_memory_bytes_peak"] = max(record["gpu_memory_bytes_peak"], gpu_bytes)
            if gpu_available:
                record["gpu_memory_bytes_status"] = "observed"

            while not exit_state.wait(0.05):
                try:
                    rss, pids = _process_tree_snapshot(process.pid)
                    record["peak_process_tree_rss_bytes"] = max(record["peak_process_tree_rss_bytes"], rss)
                    gpu_bytes, gpu_available = _gpu_memory_for_processes(pids)
                    record["gpu_memory_observation_available"] = record["gpu_memory_observation_available"] or gpu_available
                    record["gpu_memory_bytes_peak"] = max(record["gpu_memory_bytes_peak"], gpu_bytes)
                    if gpu_available:
                        record["gpu_memory_bytes_status"] = "observed"
                    gpu_total, gpu_total_available = _gpu_total_memory()
                    if gpu_total_available:
                        record["gpu_memory_total_used_bytes_peak"] = max(
                            record["gpu_memory_total_used_bytes_peak"], gpu_total)
                        record["gpu_memory_total_used_bytes_status"] = "observed"
                except psutil.NoSuchProcess:
                    pass
            waiter.join()
            rss, pids = _process_tree_snapshot(process.pid)
            record["peak_process_tree_rss_bytes"] = max(record["peak_process_tree_rss_bytes"], rss)
            record["exit_code"] = completion["exit_code"]
            record["status"] = "passed" if record["exit_code"] == 0 else "failed"
    except OSError as error:
        record.update(status="failed", exit_code=None, error=str(error))
    finally:
        record["elapsed_seconds"] = (
            completion["finished_perf_counter"] - tick
            if "completion" in locals() and "finished_perf_counter" in completion
            else time.perf_counter() - tick
        )
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description="Run one benchmark command and collect runtime/memory evidence.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--warm-up-policy", default="none")
    parser.add_argument("--cache-policy", default="no cache flush; inherited OS cache state")
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
    if not argv:
        parser.error("Provide the benchmark argv after --")
    record = run_command(
        argv,
        Path(args.output),
        {
            "run_id": args.run_id,
            "warm_up_policy": args.warm_up_policy,
            "cache_policy": args.cache_policy,
        },
    )
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "passed" else record["exit_code"] or 1


if __name__ == "__main__":
    raise SystemExit(main())
