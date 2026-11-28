"""Location of the team repository (tlmthuy/Big-Data) for the Python tests.

Set BIG_DATA_ROOT to point at any checkout; the default is ../Big-Data next to this repo,
so the tests also run from a clone in another folder.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIG_DATA_ROOT = Path(os.environ.get("BIG_DATA_ROOT") or ROOT.parent / "Big-Data").expanduser().resolve()
