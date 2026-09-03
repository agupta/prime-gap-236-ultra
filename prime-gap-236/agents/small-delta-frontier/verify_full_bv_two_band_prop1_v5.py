#!/usr/bin/env python3
"""Corrected exact analytic audit for the first full-BV two-band support.

This supersedes the withdrawn v4 audit.  V4 checked the maximal-omega fixed
families and the above-square-root Type-IIc rectangles, but omitted the
separate near-square-root ``omega=0`` fixed covers.  Here both mixed orders
and the outer self-pair are split into small, near-square, and above-square
modulus ranges.  Fixed IIb uses its uniform lower-gamma third capacity.

This is an analytic support audit only; it deliberately proves no quotient.
"""

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
REPO = FILE.parents[2]
CORE = HERE / "verify_wide_c722_two_band_prop1.py"
CORE_SHA256 = "3ec590c95376432a75fb55c7810fbff10e87b67964d6cc4f761576c23aa414ca"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha256(CORE) != CORE_SHA256:
    raise RuntimeError("shared exact cover core changed")
_spec = importlib.util.spec_from_file_location("narrow_two_band_v5_core", CORE)
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load shared exact cover core")
core = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = core
_spec.loader.exec_module(core)


EPSILON = Q(3, 400)
DELTA = Q(7, 250)
A1 = Q(1, 4)
A2 = Q(253, 1000)
INNER = (Q(103, 400),) * 10
OUTER = (Q(43, 500), Q(43, 500), Q(57, 500),
         Q(71, 500), Q(71, 500), Q(71, 500))
CROSS_OMEGA = Q(3, 2000)
OUTER_OMEGA = Q(3, 1000)


def configure_core() -> None:
    core.DELTA = DELTA
    core.EPSILON = EPSILON
    core.iv.DELTA, core.iv.H = DELTA, core.H


def require_positive_capacities(omega: Q, label: str,
                                margins: dict[str, Q]) -> dict[str, tuple[Q, ...]]:
    capacities = core.fixed_capacities(omega)
    for family, values in capacities.items():
        for index, value in enumerate(values, 1):
            core.positive(margins, f"{label} {family} capacity {index}", value)
    actual_gap = core.iib_c3_actual_infimum(omega) - capacities["IIb"][2]
    if actual_gap != 2 * core.H / 7:
        raise ArithmeticError("corrected IIb third-capacity reserve changed")
    margins[f"{label} IIb actual-minus-safe C3"] = actual_gap
    return capacities


def build_result() -> dict[str, object]:
    configure_core()
    for relative, expected in core.PINNED_ANALYTIC.items():
        actual = sha256(REPO / relative)
        if actual != expected:
            raise RuntimeError(f"pinned analytic dependency changed: {relative}")

    margins: dict[str, Q] = {}
    core.positive(margins, "Definition1 epsilon", EPSILON)
    core.positive(margins, "Definition1 delta", DELTA)
    core.positive(margins, "Definition1 A1-A0", A1 + EPSILON)
    core.positive(margins, "Definition1 A2-A1", A2 - A1)
    core.positive(margins, "Definition1 upper", Q(1, 2) - EPSILON - A2)
    inner_active = core.check_schedule("inner", INNER, 10, margins)
    outer_active = core.check_schedule("outer", OUTER, 6, margins)

    exponents = {
        "low_low": (A1 - EPSILON) + (A1 + EPSILON),
        "low_high": (A1 - EPSILON) + (A2 + EPSILON),
        "high_low": (A2 - EPSILON) + (A1 + EPSILON),
        "high_high": (A2 - EPSILON) + (A2 + EPSILON),
    }
    expected_exponents = {"low_low": Q(1, 2), "low_high": Q(503, 1000),
                          "high_low": Q(503, 1000),
                          "high_high": Q(253, 500)}
    if exponents != expected_exponents:
        raise ArithmeticError("band exponent identities changed")

    # Maximal parameters govern Type 0 and the above-square-root blocks.
    core.scalar_direct_hb(margins, "mixed above", CROSS_OMEGA)
    core.scalar_direct_hb(margins, "outer above", OUTER_OMEGA)
    # The near-square-root strip is a separate fixed-factor application at
    # omega=0.  Type IIc is empty there; IIa, IIb, and III are literal covers.
    core.scalar_direct_hb(margins, "mixed near", Q(0))
    core.scalar_direct_hb(margins, "outer near", Q(0))
    near_iic_empty = ((Q(2, 5) - core.H) -
                      (Q(1, 3) + Q(7, 3) * DELTA + 3 * core.H))
    core.positive(margins, "near-square IIc empty", near_iic_empty)

    fixed_parameters = {
        "near": require_positive_capacities(Q(0), "near", margins),
        "mixed_above": require_positive_capacities(
            CROSS_OMEGA, "mixed above", margins),
        "outer_above": require_positive_capacities(
            OUTER_OMEGA, "outer above", margins),
    }
    families = ("IIa", "IIb", "III")
    fixed_near = {
        "cross": core.fixed_interval_family(INNER, OUTER, Q(0), families),
        "transpose": core.fixed_interval_family(OUTER, INNER, Q(0), families),
        "outer_ordered": core.fixed_interval_family(
            OUTER, OUTER, Q(0), families),
    }
    fixed_above = {
        "cross": core.fixed_interval_family(
            INNER, OUTER, CROSS_OMEGA, families),
        "transpose": core.fixed_interval_family(
            OUTER, INNER, CROSS_OMEGA, families),
        "outer_ordered": core.fixed_interval_family(
            OUTER, OUTER, OUTER_OMEGA, families),
    }
    expected_pairs = {"cross": 59, "transpose": 59, "outer_ordered": 35}
    for range_name, result in (("near", fixed_near), ("above", fixed_above)):
        for name, expected in expected_pairs.items():
            if (result[name]["pairs"], result[name]["checks"]) != \
                    (expected, 3 * expected):
                raise ArithmeticError(
                    f"{range_name} {name} fixed inventory changed")

    # Only above the square root is omega_0 nonnegative and IIc nonempty.
    dynamic = {
        "cross": core.dynamic_iic_family(INNER, OUTER, CROSS_OMEGA),
        "transpose": core.dynamic_iic_family(OUTER, INNER, CROSS_OMEGA),
        "outer_ordered": core.dynamic_iic_family(
            OUTER, OUTER, OUTER_OMEGA),
    }
    if tuple(dynamic[name]["checks"] for name in
             ("cross", "transpose", "outer_ordered")) != \
            (15104, 15104, 8960):
        raise ArithmeticError("above-square dynamic IIc inventory changed")

    sigma = Q(1, 10) + core.S
    core.positive(margins, "HB sigma endpoint", sigma - Q(1, 10))
    core.positive(margins, "HB K=10", 2 * sigma - Q(1, 10))
    core.positive(margins, "HB TypeII lower",
                  (Q(1, 2) - sigma) - (core.XI2 - core.H))
    core.positive(margins, "HB TypeII upper",
                  (1 - core.XI2 + core.H) - (Q(1, 2) + sigma))
    core.positive(margins, "HB TypeIII lower",
                  2 * sigma - (1 - 2 * core.XI3 - core.H))
    core.positive(margins, "HB TypeIII upper",
                  (core.XI3 + core.H) - (Q(1, 2) - sigma))
    core.positive(margins, "HB TypeIII pair",
                  (Q(1, 2) + sigma) - (1 - core.XI3 - core.H))
    for name, schedule in (("inner", INNER), ("outer", OUTER)):
        core.positive(margins, f"Prop1 beta-{name}-B1",
                      Q(1, 2) - schedule[0])
        core.positive(margins, f"Prop1 beta-{name}-B2",
                      Q(1, 2) - schedule[1])

    return {
        "status": "full-bv-two-band-prop1-analytic-pass-v5",
        "scope": "all Proposition-1 analytic hypotheses; exact quotient absent",
        "script_sha256": sha256(FILE), "core_sha256": CORE_SHA256,
        "interval_cover_sha256": core.IV_SHA256,
        "pinned_analytic_dependencies": core.PINNED_ANALYTIC,
        "supersedes_withdrawn": {
            "script_sha256":
                "1a771681617757b7a67c137e80a0dced72046493a55cfa9aa64a3e38e2ff53aa",
            "artifact_sha256":
                "2c413b368a6c4fc9e82641d3bd68d644dd0b1f10fc32c83a867b2389e235a549",
            "reason": "missing explicit omega=0 near-square fixed covers",
        },
        "parameters": {
            "k": 48, "epsilon": str(EPSILON), "delta": str(DELTA),
            "A": [str(-EPSILON), str(A1), str(A2)],
            "inner_schedule": [str(x) for x in INNER],
            "outer_schedule": [str(x) for x in OUTER],
            "active_inner": list(inner_active), "active_outer": list(outer_active),
            "pair_exponents": {k: str(v) for k, v in exponents.items()},
            "rho": "(log n/log(3x))*1_P on [x,2x]",
            "c1": "0", "c2": "0", "beta": "1/2",
        },
        "distribution_decomposition": {
            "1,1": "classical Bombieri-Vinogradov",
            "1,2": "small BV; near omega=0; above fixed omega=3/2000",
            "2,1": "small BV; near omega=0; above fixed omega=3/2000",
            "2,2": "small BV; near omega=0; above fixed omega=3/1000",
        },
        "fixed_capacities": {
            tag: {family: [str(x) for x in values]
                  for family, values in families_map.items()}
            for tag, families_map in fixed_parameters.items()},
        "fixed_near_square_interval_cover": fixed_near,
        "fixed_above_square_interval_cover": fixed_above,
        "dynamic_iic_16x16_above_square": dynamic,
        "margins": {k: str(v) for k, v in margins.items()},
        "finite_union_transfer": (
            "nonnegative Definition-3 discrepancy is restricted to and summed "
            "over four ordered band pairs and disjoint modulus ranges"),
        "theorem_ready": False,
        "remaining": "exact k=48 quotient above one and final independent audit",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_result()
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
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
