#!/usr/bin/env python3
"""Run the independent interval-cover checker on the exact C10 schedule."""

from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent


def main() -> None:
    # Counts 1,...,15 are nonempty.  Count 16 is included explicitly and is
    # empty; constant extension then proves emptiness for every count through
    # floor(1/delta)=100.
    bounds = ["3/20", "3/20"] + ["97/625"] * 14
    command = [
        sys.executable,
        str(HERE / "code" / "verify_direct_hb_support.py"),
        "--epsilon",
        "1/200",
        "--delta",
        "1/100",
        "--A",
        "77747/300000",
        "--bounds",
        ",".join(bounds),
        "--gamma-cells",
        "4",
        "--omega-cells",
        "4",
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
