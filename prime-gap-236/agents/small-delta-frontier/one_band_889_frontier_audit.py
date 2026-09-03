#!/usr/bin/env python3
"""Exact geometric audit of the sharpened one-band 889/5000 support."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
CORE = FILE.with_name("two_band_mixed_audit.py")
CORE_SHA256 = "7323ab20b12e550799646684720e23487ec379886a24f325546d5cef7bb03116"
SCHEDULE = (Q(159999999, 10**9), Q(159999999, 10**9)) + \
    (Q(889, 5000),) * 5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_core():
    if sha256(CORE) != CORE_SHA256:
        raise RuntimeError("frozen exact cover core changed")
    spec = importlib.util.spec_from_file_location("one_band_889_core", CORE)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load exact cover core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fresh_report() -> dict[str, object]:
    core = load_core()
    core.iv.DELTA = core.DELTA
    core.iv.H = core.H
    omega = core.A2 - Q(1, 4)
    cover = core.cover_schedule_pair(SCHEDULE, SCHEDULE, omega, unordered=True)
    capacities = core.capacities(omega)
    c1 = capacities["IIc"][0]
    critical_margin = c1 - 2 * SCHEDULE[0]
    if critical_margin != Q(5521, 5000000000000) or critical_margin <= 0:
        raise ArithmeticError("critical inward IIc margin changed")
    if cover["pair_count"] != 27 or cover["node_totals"] != {
            "IIa": 27, "IIb": 27, "III": 27, "IIc": 1845}:
        raise ArithmeticError("exact cover counts changed")
    if not (SCHEDULE[0] > Q(3, 20) and SCHEDULE[2] == Q(889, 5000)):
        raise AssertionError("support no longer strictly contains B889 baseline")
    return {
        "status": "one-band-889-sharpened-exact-geometric-cover-pass",
        "scope": "exact factorization geometry; source-level analytic transfer checked separately",
        "script_sha256": sha256(FILE),
        "cover_core_sha256": CORE_SHA256,
        "parameters": {
            "k": 48, "epsilon": "3/400", "delta": "7/250",
            "A0": "-3/400", "A1": "253/1000", "omega": "3/1000",
            "schedule_through_first_empty": [str(value) for value in SCHEDULE],
            "first_empty_count": 7,
        },
        "critical_iic_capacity_1": str(c1),
        "critical_iic_margin": str(critical_margin),
        "excluded_endpoint_B1_B2_4_over_25_gap":
            str(2 * Q(4, 25) - c1),
        "strict_containment": {
            "published_B11_gain": str(SCHEDULE[0] - Q(3, 20)),
            "published_B12_gain": str(SCHEDULE[1] - Q(3, 20)),
            "B889_higher_caps_equal": True,
        },
        "cover": cover,
        "theorem_ready": False,
        "remaining": "source-level transfer, exact quotient, and independent final audit",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(fresh_report(), sort_keys=True,
                          separators=(",", ":")) + "\n").encode()
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
