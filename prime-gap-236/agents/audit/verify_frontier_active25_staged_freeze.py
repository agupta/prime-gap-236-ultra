#!/usr/bin/env python3
"""Fail-closed verifier for the announced active25 staged prelaunch tuple.

This deliberately verifies the hashes announced by the producer rather than
accepting whatever bytes happen to occupy the ordinary source paths later.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[2]
PINS = {
    "arithmetic_core": (
        REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py",
        "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a"),
    "arithmetic_tests": (
        REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_tagged_shell.py",
        "a9c822357bb2cb9225030b0df46f11bca225ec05158e48ee0d57ff2394f7071f"),
    "ungrouped_oracle": (
        REPO / "agents/small-delta-frontier/results/frontier_active25_innerD16_shell_cross_r10_h10_ungrouped_oracle.json",
        "f97e16231e47d028406a88702631457fb110fe1cf00fcb9a2a4ba71557dbc21c"),
    "direct_representative": (
        REPO / "agents/small-delta-frontier/results/frontier_active25_innerD16_shell_cross_r10_h10_direct_v2.json",
        "37b0d249a0fd17e823f154277bfabe162c3b80c72c344c97686312c7fac7e393"),
    "disabled_gate": (
        REPO / "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_prelaunch_gate.json",
        "1642a5efcc4e2b304271fe3b785d439ce9b1ddb405855f56a7e62a1b4e61e6ac"),
    "gate_verifier": (
        REPO / "agents/small-delta-frontier/verify_frontier_active25_prelaunch_gate.py",
        "552e6e92916c62179f56262f33fddfeda46d65463c7a13edb165892f0c15020b"),
    "staged_wrapper": (
        REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_staged.py",
        "d1b2d5c15fefdd3351088a6eab1885fdbbe4a12295aacb3b38bb4ad0a5ddbe64"),
    "staged_tests": (
        REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged.py",
        "e252b0c45cffc35e91418395c760ac42cf5cb978cf5f32d2dad8b4a3a56133d8"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures = []
    for label, (path, expected) in PINS.items():
        actual = digest(path) if path.is_file() else "MISSING"
        verdict = "PASS" if actual == expected else "FAIL"
        print(f"{verdict}\t{label}\texpected={expected}\tactual={actual}\t{path}")
        if actual != expected:
            failures.append(label)
    if failures:
        print("PRELAUNCH AUDIT FAIL: frozen tuple mismatch: " + ", ".join(failures))
        return 1
    print("HASH PASS ONLY: proceed to the independent arithmetic/wrapper audit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
