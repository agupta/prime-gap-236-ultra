#!/usr/bin/env python3
"""Reproduce the frozen fixed-polygon-v8 runner's pre-build AttributeError."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNNER = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_fixed_polygon_v8.py")
RUNNER_SHA256 = (
    "649c50273dce8de9dce04014eb602f41a3ed005ed2593f5b89f15ad3196d9e79")


def main() -> None:
    observed = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
    if observed != RUNNER_SHA256:
        raise RuntimeError(f"frozen runner changed: {observed}")
    with tempfile.TemporaryDirectory(prefix="fixed-polygon-v8-failure-") as root:
        root = Path(root)
        output = root / "common_r_00.json"
        cache = root / "empty-private-cache"
        command = [
            sys.executable, "-B", "-I", "-X", f"pycache_prefix={cache}",
            str(RUNNER), "--common-r", "0", "--output", str(output),
            "--expected-self-sha256", RUNNER_SHA256,
        ]
        completed = subprocess.run(
            command, cwd=REPO, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False)
        needle = (
            "AttributeError: 'PosixPath' object has no attribute "
            "'_polygon_monomial_batch'")
        if completed.returncode == 0:
            raise AssertionError("frozen v8 runner unexpectedly succeeded")
        if needle not in completed.stderr:
            raise AssertionError(completed.stderr)
        if output.exists():
            raise AssertionError("failed v8 runner unexpectedly published output")
        print("FIXED-POLYGON-V8 FATAL COUNTEREXAMPLE REPRODUCED")
        print(f"runner_sha256={observed}")
        print(f"returncode={completed.returncode}")
        print(needle)


if __name__ == "__main__":
    main()
