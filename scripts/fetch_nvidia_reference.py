"""Import an immutable, attributed subset of the official NVIDIA repository."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

URL = "https://github.com/NVIDIA-Merlin/Transformers4Rec.git"
PATHS = [
    "LICENSE", "NOTICE", "examples/tutorial",
    "transformers4rec/torch/masking.py",
    "transformers4rec/torch/model/prediction_task.py",
    "transformers4rec/torch/ranking_metric.py",
    "transformers4rec/utils/data_utils.py",
]
NOTEBOOKS = [
    "01-preprocess.ipynb", "02-ETL-with-NVTabular.ipynb",
    "03-Session-based-recsys.ipynb",
]


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="main", help="Upstream commit, tag or branch")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dest = root / "docs" / "vendor" / "nvidia-transformers4rec"
    if (dest / "upstream").exists() or (dest / "manifest.json").exists():
        parser.error("Snapshot already exists; preserve it and review any update explicitly.")
    with tempfile.TemporaryDirectory(prefix="nvidia-reference-") as temporary:
        checkout = Path(temporary) / "upstream"
        git("clone", "--filter=blob:none", "--no-checkout", "--depth=1", URL, str(checkout))
        git("-C", str(checkout), "fetch", "--depth=1", "origin", args.ref)
        commit = git("-C", str(checkout), "rev-parse", "FETCH_HEAD")
        git("-C", str(checkout), "sparse-checkout", "set", "--no-cone",
            *["/" + p + ("/" if p == "examples/tutorial" else "") for p in PATHS])
        git("-C", str(checkout), "checkout", "--detach", commit)
        required = [p for p in PATHS if p not in ("NOTICE", "examples/tutorial")]
        required += ["examples/tutorial/" + n for n in NOTEBOOKS]
        missing = [p for p in required if not (checkout / p).is_file()]
        if missing:
            raise RuntimeError(f"Upstream layout changed; missing files: {missing}")
        files = sorted(p for p in checkout.rglob("*")
                       if p.is_file() and ".git" not in p.relative_to(checkout).parts)
        manifest = {"repository": URL, "requested_ref": args.ref, "commit": commit,
                    "license_file": "upstream/LICENSE", "files": {}}
        for source in files:
            relative = source.relative_to(checkout)
            target = dest / "upstream" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest["files"][relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Imported {len(files)} files at {commit} into docs/vendor/nvidia-transformers4rec")


if __name__ == "__main__":
    main()
