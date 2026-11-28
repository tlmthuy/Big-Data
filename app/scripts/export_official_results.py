"""Export the checksum-verified TV2 official results package."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path

KNOWN_CHECKSUM_EXCEPTIONS = {
    "environment/README.md": "TV3 doc edit after packaging (team commit 88f7e02), log links only",
}
VM_ENVIRONMENT_VALUES = {
    "cloud": "VM AWS Ubuntu 22.04",
    "gpu": "Tesla T4 (compute capability 7.5)",
    "vram": "15360 MiB",
    "cpu": "Intel Xeon Platinum 8259CL @ 2.50GHz",
    "vcpu": "8 vCPU",
    "ram": "30,98 GiB",
    "os": "Ubuntu 22.04.5 LTS",
    "kernel": "6.8.0-1036-aws",
    "driver": "570.172.08",
    "cuda_toolkit": "12.1.105",
    "docker": "28.4.0",
    "image": "merlin-pytorch:23.12",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_checksums(package_root):
    manifest = read_json(package_root / "manifest.json")
    exceptions = []
    for group, files in manifest["files_sha256"].items():
        for relative, expected in files.items():
            path = package_root.parent.parent.parent / relative
            if not path.is_file():
                raise ValueError(f"Manifest file is missing: {relative}")
            content = path.read_bytes().replace(b"\r\n", b"\n")
            actual = hashlib.sha256(content).hexdigest()
            if actual == expected:
                continue
            if group == "runtime" and relative in KNOWN_CHECKSUM_EXCEPTIONS:
                exceptions.append({"file": relative, "reason": KNOWN_CHECKSUM_EXCEPTIONS[relative]})
                continue
            raise ValueError(f"Checksum mismatch in {group} group: {relative}")
    return manifest, exceptions


def read_vm_environment(team_root):
    readme = team_root / "environment/README.md"
    content = readme.read_text(encoding="utf-8")
    environment = {}
    for field, value in VM_ENVIRONMENT_VALUES.items():
        if value not in content:
            raise ValueError(f"Required vm_environment.{field} substring not found in {readme}: {value!r}")
        environment[field] = value
    environment["source"] = "environment/README.md (team 88f7e02)"
    environment["checksum_note"] = "file edited by TV3 after packaging; links only, values unchanged"
    return environment


STAGE_SHARE_FIELDS = {
    "raw_read": ("raw_read_share_pct", "raw_read"),
    "preprocessing": ("preprocessing_share_pct", "preprocessing_excluding_raw_read_and_first_seen"),
    "train": ("train_share_pct", "train_including_sequence_io"),
    "final_eval": ("final_eval_share_pct", "final_evaluation_including_io"),
}


def read_stage_shares(package_root, e5_rows):
    """TV2's stage_shares.csv (percent of composed E5 time per stage). The file is not in the package
    manifest, so every share is checked against the E5 stage times before export."""
    relative = f"reports/tables/{package_root.name}/stage_shares.csv"
    path = package_root.parents[2] / relative
    e5_by_subset = {int(row["subset"]): row for row in e5_rows}
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            subset = int(record["subset"])
            e5 = e5_by_subset.get(subset)
            if e5 is None:
                raise ValueError(f"{relative}: subset {subset} has no E5 row")
            row = {"subset": subset}
            for name, (column, stage) in STAGE_SHARE_FIELDS.items():
                value = float(record[column])
                expected = 100 * e5[stage] / e5["composed_seconds_excluding_first_seen"]
                if abs(value - expected) > 1e-6:
                    raise ValueError(f"{relative}: subset {subset} {column}={value} disagrees with E5 ({expected})")
                row[name] = value
            rows.append(row)
    return {"source": relative, "unit": "percent of composed_seconds_excluding_first_seen", "rows": rows}


def argv_value(argv, flag):
    """Value after a command-line flag, or None."""
    if not isinstance(argv, list) or flag not in argv:
        return None
    index = argv.index(flag)
    return argv[index + 1] if index + 1 < len(argv) else None


def as_number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def e4_configs(configs_source, e4_run_ids, configs_relative):
    """Preprocessing configuration of the E4 runs (they have no training config).

    Stage timings are deliberately not exported: their scope differs from the official E4 table.
    fingerprint_match is true only if both fingerprint sums are identical across all E4 runs; the sums
    themselves are not exported.
    """
    runs = {run_id: configs_source[run_id] for run_id in e4_run_ids if "preprocessing_argv" in configs_source.get(run_id, {})}
    fingerprints = {(config.get("verification") or {}).get("sum_sha256_mod_2_256") for config in runs.values()}
    squared = {(config.get("verification") or {}).get("sum_squared_sha256_mod_2_256") for config in runs.values()}
    match = len(runs) >= 2 and len(fingerprints) == 1 and len(squared) == 1 and None not in fingerprints and None not in squared
    exported = {}
    for run_id, config in runs.items():
        argv = config.get("preprocessing_argv")
        verification = config.get("verification") or {}
        workflow = config.get("workflow_manifest") or {}
        split = config.get("split_manifest") or {}
        timings = config.get("timings") or {}
        exported[run_id] = {
            "program": argv[1] if isinstance(argv, list) and len(argv) > 1 else None,
            "input_format": argv_value(argv, "--input-format"),
            "subset": as_number(argv_value(argv, "--subset")),
            "n_events": verification.get("n_events"),
            "fingerprint_match": match,
            "read_scope": config.get("read_scope"),
            "schema_policy": config.get("schema_policy"),
            "cache": config.get("cache"),
            "events_after_repeat_removal": timings.get("events_after_repeat_removal"),
            "product_vocabulary_size": workflow.get("product_vocabulary_size"),
            "cudf_version": workflow.get("cudf_version"),
            "nvtabular_version": workflow.get("nvtabular_version"),
            "notebook_commit": workflow.get("notebook_commit"),
            "split_seed": split.get("seed"),
            "requested_ratios": split.get("requested_ratios"),
            "partition_col": split.get("partition_col"),
            "source": configs_relative,
        }
    return exported


def export(package_root):
    manifest, exceptions = verify_checksums(package_root)
    metrics = read_json(package_root / "metrics.json")
    configs_source = read_json(package_root / "configs.json")
    registry = read_json(package_root / "run_registry.json")
    registry_status_counts = Counter(row["status"] for row in registry["runs"])
    dictionary = read_json(package_root / "data_dictionary.json")
    vm_environment = read_vm_environment(package_root.parents[2])

    configs = {}
    for run_id, config in configs_source.items():
        metadata = config.get("run_metadata", {})
        artifacts = config.get("artifacts", {})
        catalog = artifacts.get("catalog", {})
        configs[run_id] = {
            "planned": metadata.get("run"),
            "actual": config.get("effective_config"),
            "training_config": config.get("training_config"),
            "split_counts": config.get("split_counts"),
            "versions": metadata.get("versions"),
            "catalog_sha256": catalog.get("sha256"),
            "runtime": config.get("runtime"),
            "warmup": config.get("warmup"),
            "cache": config.get("cache"),
            "source_run": config.get("source_run"),
            "source_metrics": config.get("source_metrics"),
        }
    configs_relative = f"metrics/releases/{package_root.name}/configs.json"
    for run_id, e4 in e4_configs(configs_source, [row["run_id"] for row in metrics["tables"]["E4"]], configs_relative).items():
        configs[run_id]["e4_config"] = e4
    return {
        "schema": "tv4-official-results/v1",
        "package_id": manifest["package_id"],
        "confirmed_by_tv2": True,
        "data_kind": metrics["data_kind"],
        "team_commit": subprocess.run(
            ["git", "-C", str(package_root.parents[2]), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip(),
        "generated_at": date.today().isoformat(),
        "known_checksum_exceptions": exceptions,
        "run_registry_summary": {
            "passed": registry_status_counts.get("passed", 0),
            "derived_from_verified_E2": registry_status_counts.get("derived_from_verified_E2", 0),
            "excluded": len(registry["excluded"]),
        },
        "limits": manifest["limits"],
        "dictionary": dictionary,
        "excluded": registry["excluded"],
        "tables": metrics["tables"],
        "E5_aggregation_only": metrics.get("E5_aggregation_only"),
        "stage_shares": read_stage_shares(package_root, metrics["tables"]["E5"]),
        "configs": configs,
        "vm_environment": vm_environment,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("public/official-results.json"))
    args = parser.parse_args()
    try:
        payload = export(args.package.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Official results export failed: {error}\n")


if __name__ == "__main__":
    main()
