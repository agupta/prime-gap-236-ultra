#!/usr/bin/env python3
"""Independent exact analytic audit for the volume-ramp C722 shell."""

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
HERE = FILE.parent
CORE = HERE / "verify_wide_c722_two_band_prop1.py"
CORE_SHA256 = "3ec590c95376432a75fb55c7810fbff10e87b67964d6cc4f761576c23aa414ca"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha256(CORE) != CORE_SHA256:
    raise RuntimeError("wide analytic core changed")
spec = importlib.util.spec_from_file_location("volume_ramp_analytic_core", CORE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load wide analytic core")
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)


OUTER = tuple(min(Q(49, 625) + (m - 1) * core.DELTA, Q(1599, 10000))
              for m in range(1, 24))


def build_result():
    for relative, expected in core.PINNED_ANALYTIC.items():
        actual = sha256(core.REPO / relative)
        if actual != expected:
            raise RuntimeError(f"pinned analytic dependency changed: {relative}")
    core.iv.DELTA, core.iv.H = core.DELTA, core.H
    margins = {}
    core.positive(margins, "Definition1 epsilon", core.EPSILON)
    core.positive(margins, "Definition1 delta", core.DELTA)
    core.positive(margins, "Definition1 A1-A0", core.A1 + core.EPSILON)
    core.positive(margins, "Definition1 A2-A1", core.A2 - core.A1)
    core.positive(margins, "Definition1 upper",
                  Q(1, 2) - core.EPSILON - core.A2)
    inner_active = core.check_schedule("inner", core.INNER, 36, margins)
    outer_active = core.check_schedule("outer", OUTER, 23, margins)
    core.scalar_direct_hb(margins, "mixed", core.CROSS_OMEGA)
    core.scalar_direct_hb(margins, "outer", core.OUTER_OMEGA)
    core.scalar_direct_hb(margins, "outer near-square", Q(0))
    fixed_caps = {}
    for tag, omega in (("mixed", core.CROSS_OMEGA),
                       ("outer", core.OUTER_OMEGA)):
        fixed_caps[tag] = core.fixed_capacities(omega)
        for family, capacities in fixed_caps[tag].items():
            for index, capacity in enumerate(capacities, 1):
                core.positive(margins, f"{tag} {family} capacity {index}",
                              capacity)
    fixed_cross = core.fixed_prefix_family(core.INNER, OUTER,
                                           core.CROSS_OMEGA)
    fixed_transpose = core.fixed_prefix_family(OUTER, core.INNER,
                                               core.CROSS_OMEGA)
    fixed_outer = core.fixed_prefix_family(OUTER, OUTER, core.OUTER_OMEGA)
    if (fixed_cross["pairs"], fixed_transpose["pairs"],
            fixed_outer["pairs"]) != (827, 827, 528):
        raise ArithmeticError("fixed volume-ramp inventory changed")
    fixed_outer_near = core.fixed_interval_family(
        OUTER, OUTER, Q(0), ("IIa", "IIb", "III"), unordered=False)
    if (fixed_outer_near["pairs"], fixed_outer_near["checks"]) != (528, 1584):
        raise ArithmeticError("near-square volume-ramp inventory changed")
    if Q(fixed_outer_near["worst_all_first_margin"]) <= 0:
        raise ArithmeticError("near-square all-first margin vanished")
    dynamic_cross = core.dynamic_iic_family(core.INNER, OUTER,
                                            core.CROSS_OMEGA)
    dynamic_transpose = core.dynamic_iic_family(OUTER, core.INNER,
                                                core.CROSS_OMEGA)
    dynamic_outer = core.dynamic_iic_family(OUTER, OUTER,
                                            core.OUTER_OMEGA)
    if (dynamic_cross["checks"], dynamic_transpose["checks"],
            dynamic_outer["checks"]) != (0, 0, 135168):
        raise ArithmeticError("dynamic volume-ramp inventory changed")
    exponents = {"low_low": Q(1, 2),
                 "low_high": core.A1 + core.A2,
                 "high_low": core.A1 + core.A2,
                 "high_high": 2 * core.A2}
    return {
        "status": "volume-ramp-c722-two-band-prop1-analytic-pass",
        "scope": "all analytic Proposition-1 hypotheses; exact quotient absent",
        "script_sha256": sha256(FILE), "core_sha256": CORE_SHA256,
        "interval_cover_sha256": core.IV_SHA256,
        "pinned_analytic_dependencies": core.PINNED_ANALYTIC,
        "parameters": {"k": 48, "epsilon": str(core.EPSILON),
                       "delta": str(core.DELTA),
                       "A": [str(-core.EPSILON), str(core.A1), str(core.A2)],
                       "alpha": [str(core.ALPHA1), str(core.ALPHA2)],
                       "eta": [str(core.ETA1), str(core.ETA2)],
                       "inner_schedule": [str(x) for x in core.INNER],
                       "outer_schedule": [str(x) for x in OUTER],
                       "active_inner": list(inner_active),
                       "active_outer": list(outer_active),
                       "pair_exponents": {k: str(v) for k, v in exponents.items()},
                       "rho": "(log n/log(3x))*1_P on [x,2x]",
                       "c1": "0", "c2": "0", "beta": "1/2"},
        "fixed_capacities": {
            tag: {family: [str(x) for x in capacities]
                  for family, capacities in families.items()}
            for tag, families in fixed_caps.items()},
        "fixed_prefix": {"cross": fixed_cross,
                         "transpose": fixed_transpose,
                         "outer_ordered": fixed_outer},
        "outer_near_square_fixed_interval_cover": fixed_outer_near,
        "dynamic_iic_16x16": {"cross": dynamic_cross,
                              "transpose": dynamic_transpose,
                              "outer_ordered": dynamic_outer},
        "margins": {k: str(v) for k, v in margins.items()},
        "distribution_decomposition": {
            "1,1": "classical Bombieri-Vinogradov",
            "1,2": ("repaired direct-HB with fixed upper parameter "
                    "omega=121/24000; Type-IIc range empty"),
            "2,1": ("repaired direct-HB with fixed upper parameter "
                    "omega=121/24000; Type-IIc range empty"),
            "2,2": ("small moduli BV; near-square IIa/IIb/III at omega=0 "
                    "with IIc empty; above-square fixed omega=121/12000 "
                    "plus repaired 0<=omega_0<=omega IIc")},
        "finite_union_transfer": (
            "nonnegative Definition-3 discrepancy is restricted to and summed "
            "over four ordered band pairs"),
        "theorem_ready": False,
        "remaining": "exact k=48 quotient above one and final independent audit",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build_result(), sort_keys=True,
                          separators=(",", ":")) + "\n").encode("ascii")
    if args.output:
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
