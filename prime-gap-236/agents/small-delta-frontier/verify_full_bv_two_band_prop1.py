#!/usr/bin/env python3
"""Exact analytic audit for the full-BV-core/two-band shell support.

Band (1,1) is assigned to classical Bombieri--Vinogradov.  The mixed ordered
pairs and band (2,2) are assigned to the pinned repaired direct-Heath--Brown
argument.  Every cap-dependent continuum box is rebuilt here, including a
fresh 16 by 16 (gamma,omega_0) subdivision for repaired Type IIc.

This proves the analytic parameter transfer only.  It deliberately leaves
``theorem_ready`` false until an exact k=48 quotient exceeds one and receives
an independent final audit.  The minorant is the source-audited weighted prime
indicator ``(log n/log(3x))*1_P``; replacing it by ``1_P`` is unnecessary.
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
GEOMETRY_SCRIPT = HERE / "two_band_mixed_audit.py"
GEOMETRY_SCRIPT_SHA256 = (
    "7323ab20b12e550799646684720e23487ec379886a24f325546d5cef7bb03116"
)
GEOMETRY_RESULT = HERE / "results/one_band_177_and_two_band_geometry.json"
GEOMETRY_RESULT_SHA256 = (
    "0190e729eb2a4bc547aea0a057c0cb631c480f0a3fd596702340cfc452ccfbeb"
)
PINNED_ANALYTIC = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "agents/independent-attack/direct-bv-family.md":
        "4daa9590c09db003c6ebbd978ca843a26ec5fe9ab0b0260907ef37fe3a2b91e7",
    "agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md":
        "47cd11457c44aa2348e7b3d22c5615261c5af04d999414dae3d58eba16f9e80c",
    "agents/hostile-analytic-audit/c10-analytic-repair-addendum.md":
        "2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7",
    "agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md":
        "f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
}

H = Q(1, 10**10)
S = H / 10
EPSILON = Q(3, 400)
DELTA = Q(7, 250)
A1 = Q(1, 4)
A2 = Q(253, 1000)
INNER = (Q(103, 400),) * 10
OUTER = (Q(43, 500), Q(43, 500), Q(57, 500),
         Q(71, 500), Q(71, 500), Q(71, 500))
XI1, XI2, XI3 = Q(19, 50), Q(2, 5), Q(2, 5)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_sha(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"SHA mismatch for {path}: {actual} != {expected}")


def load_geometry():
    require_sha(GEOMETRY_SCRIPT, GEOMETRY_SCRIPT_SHA256)
    spec = importlib.util.spec_from_file_location(
        "full_bv_two_band_geometry", GEOMETRY_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load frozen geometry checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def positive(margins, name, value):
    if value <= 0:
        raise AssertionError(f"{name} is not positive: {value}")
    margins[name] = value


def active(schedule):
    return (0,) + tuple(m for m, bound in enumerate(schedule, 1)
                        if m * DELTA <= bound)


def cap_iic_cell(gamma_lo, gamma_hi, omega_lo, omega_hi):
    # This is the independent direct-HB cell formula, with every open
    # endpoint moved inward by the frozen H reserve.
    return (
        gamma_lo - 2 * DELTA - 8 * omega_hi - H,
        Q(1, 2) - gamma_hi - 2 * omega_hi - H,
        4 * omega_lo + DELTA - H,
        8 * omega_lo,
    )


def fresh_dynamic_iic(geometry, left, right, omega, cells=16):
    # The combinatorial classification is widened from 2/5-s to the fixed
    # source interval 2/5-H.  Using 2/5-s here would be a favourable and
    # incomplete truncation of the repaired IIc range.
    gamma_lo = Q(2, 5) - H
    gamma_hi = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    if gamma_hi < gamma_lo:
        return {"cells": 0, "nodes": 0, "pairs": 0,
                "minimum_capacity": None}
    pairs = 0
    nodes = 0
    minimum_capacity = None
    for m in active(left):
        for mp in active(right):
            if m + mp == 0:
                continue
            b = Q(0) if m == 0 else left[m - 1]
            bp = Q(0) if mp == 0 else right[mp - 1]
            for io in range(cells):
                ol = omega * io / cells
                ou = omega * (io + 1) / cells
                for ig in range(cells):
                    gl = gamma_lo + (gamma_hi - gamma_lo) * ig / cells
                    gu = gamma_lo + (gamma_hi - gamma_lo) * (ig + 1) / cells
                    caps = cap_iic_cell(gl, gu, ol, ou)
                    local_min = min(caps)
                    minimum_capacity = (local_min if minimum_capacity is None
                                        else min(minimum_capacity, local_min))
                    stats = geometry.cover_pair(
                        m, mp, b, bp, caps,
                        f"dynamic IIc {m},{mp} cell {io},{ig}")
                    nodes += stats["nodes"]
            pairs += 1
    if minimum_capacity is None or minimum_capacity < 0:
        raise ArithmeticError("dynamic IIc has a negative bin capacity")
    return {"cells": cells * cells, "nodes": nodes, "pairs": pairs,
            "minimum_capacity": str(minimum_capacity)}


def scalar_direct_hb_margins(margins, tag, omega):
    average_A = Q(1, 4) + omega
    sigma = Q(1, 10) + S
    qexponent = 2 * average_A
    positive(margins, f"{tag} Type0 sharp interval",
             1 - ((Q(1, 2) - sigma) + qexponent))
    positive(margins, f"{tag} Type0 full Poisson",
             1 - (1 - 2 * sigma + 4 * omega))
    positive(margins, f"{tag} prime square", 1 - qexponent)
    positive(margins, f"{tag} higher prime powers",
             1 - (qexponent + Q(1, 3)))
    positive(margins, f"{tag} near-sqrt IIc gap",
             (Q(1, 2) - sigma) -
             (Q(1, 3) + Q(7, 3) * DELTA + 3 * H))
    positive(margins, f"{tag} TypeII scalar 19/2",
             Q(19, 2) - 36 * average_A - 13 * DELTA + 100 * H)
    positive(margins, f"{tag} TypeII scalar first",
             Q(21, 25) - Q(16, 5) * average_A - 2 * H - DELTA)
    positive(margins, f"{tag} TypeII scalar second",
             Q(63, 80) - 3 * average_A - 2 * H - DELTA)
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    positive(margins, f"{tag} TypeIII width", delta3 - DELTA)
    positive(margins, f"{tag} TypeIII distribution",
             4 - (28 * omega + 9 * gamma3 + 8 * delta3))
    return qexponent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for relative, expected in PINNED_ANALYTIC.items():
        require_sha(REPO / relative, expected)
    require_sha(GEOMETRY_RESULT, GEOMETRY_RESULT_SHA256)
    geometry_artifact = json.loads(GEOMETRY_RESULT.read_bytes())
    geometry = load_geometry()
    geometry.iv.DELTA = DELTA
    geometry.iv.H = H

    backup = geometry_artifact.get("full_bv_two_band_backup", {})
    if (geometry_artifact.get("status") !=
            "one-band-and-two-band-exact-geometric-cover-pass" or
            tuple(map(Q, backup.get("inner_schedule", ()))) != INNER or
            tuple(map(Q, backup.get("outer_schedule", ()))) != OUTER or
            backup.get("low_low_assignment") != "classical BV, not direct-HB"):
        raise ValueError("frozen two-band geometry identity changed")

    margins = {}
    positive(margins, "Definition1 epsilon", EPSILON)
    positive(margins, "Definition1 delta", DELTA)
    positive(margins, "Definition1 A1-A0", A1 + EPSILON)
    positive(margins, "Definition1 A2-A1", A2 - A1)
    positive(margins, "Definition1 upper", Q(1, 2) - EPSILON - A2)
    for tag, head in (("inner", INNER), ("outer", OUTER)):
        extension = head + (head[-1],) * (35 - len(head))
        if len(extension) != int(1 // DELTA):
            raise AssertionError("Definition-1 full schedule length changed")
        for index, value in enumerate(extension):
            positive(margins, f"Definition1 {tag} B{index + 1}-delta",
                     value - DELTA)
            if index and not extension[index - 1] <= value <= \
                    extension[index - 1] + DELTA:
                raise AssertionError(f"{tag} cap transition failed at {index + 1}")
    if active(INNER) != tuple(range(10)) or active(OUTER) != tuple(range(6)):
        raise AssertionError("active count lists changed")

    # The three ordered band-pair exponents are exact consequences of the two
    # total-product constraints in Definition 2; epsilon cancels in each.
    exponents = {
        "low_low": (A1 - EPSILON) + (A1 + EPSILON),
        "low_high": (A1 - EPSILON) + (A2 + EPSILON),
        "high_low": (A2 - EPSILON) + (A1 + EPSILON),
        "high_high": (A2 - EPSILON) + (A2 + EPSILON),
    }
    if exponents != {"low_low": Q(1, 2), "low_high": Q(503, 1000),
                     "high_low": Q(503, 1000),
                     "high_high": Q(253, 500)}:
        raise ArithmeticError("epsilon cancellation changed")
    positive(margins, "BV one-minus-unshrunk endpoint",
             1 - exponents["low_low"])
    # For every fixed epsilon_0>0, (1-epsilon_0)/2 is below the
    # Bombieri--Vinogradov level by a fixed power.  This is the exact (1,1)
    # assignment and does not use the redundant inner caps.

    cross_omega = (exponents["low_high"] - Q(1, 2)) / 2
    outer_omega = (exponents["high_high"] - Q(1, 2)) / 2
    if (cross_omega, outer_omega) != (Q(3, 2000), Q(3, 1000)):
        raise ArithmeticError("pair omega values changed")
    scalar_direct_hb_margins(margins, "mixed", cross_omega)
    scalar_direct_hb_margins(margins, "outer", outer_omega)

    fresh_cross = geometry.cover_schedule_pair(INNER, OUTER, cross_omega)
    fresh_transpose = geometry.cover_schedule_pair(OUTER, INNER, cross_omega)
    fresh_outer = geometry.cover_schedule_pair(
        OUTER, OUTER, outer_omega, unordered=True)
    for key, fresh in (("cross", fresh_cross),
                       ("transpose", fresh_transpose),
                       ("outer_self", fresh_outer)):
        if fresh != backup[key]:
            raise ArithmeticError(f"fresh {key} cover differs from artifact")
    if (fresh_cross["pair_count"], fresh_transpose["pair_count"],
            fresh_outer["pair_count"]) != (59, 59, 20):
        raise ArithmeticError("band-pair count changed")

    dynamic_cross = fresh_dynamic_iic(geometry, INNER, OUTER, cross_omega)
    dynamic_transpose = fresh_dynamic_iic(geometry, OUTER, INNER, cross_omega)
    dynamic_outer = fresh_dynamic_iic(geometry, OUTER, OUTER, outer_omega)
    if (dynamic_cross["pairs"], dynamic_transpose["pairs"],
            dynamic_outer["pairs"]) != (59, 59, 35):
        # The dynamic outer loop is ordered; this is intentionally different
        # from the 20 unordered fixed-cap audit above.
        raise ArithmeticError("dynamic IIc pair coverage changed")
    # The only omitted count pair is (0,0).  Its coordinate multiset is empty,
    # so assigning the empty set to every factorization bin is valid precisely
    # because all fixed and cellwise capacities are nonnegative.  The dynamic
    # minimum includes the omega_0=0 fourth bin, where equality at zero occurs.
    for omega in (cross_omega, outer_omega):
        for values in geometry.capacities(omega).values():
            if min(values) < 0:
                raise ArithmeticError("negative fixed capacity in (0,0) case")
    if any(Q(item["minimum_capacity"]) < 0 for item in
           (dynamic_cross, dynamic_transpose, dynamic_outer)):
        raise ArithmeticError("negative dynamic capacity in (0,0) case")

    sigma = Q(1, 10) + S
    positive(margins, "HB sigma endpoint", sigma - Q(1, 10))
    positive(margins, "HB K=10", 2 * sigma - Q(1, 10))
    positive(margins, "HB TypeII lower containment",
             (Q(1, 2) - sigma) - (XI2 - H))
    positive(margins, "HB TypeII upper containment",
             (1 - XI2 + H) - (Q(1, 2) + sigma))
    positive(margins, "HB TypeIII lower containment",
             2 * sigma - (1 - 2 * XI3 - H))
    positive(margins, "HB TypeIII upper containment",
             (XI3 + H) - (Q(1, 2) - sigma))
    positive(margins, "HB TypeIII pair containment",
             (Q(1, 2) + sigma) - (1 - XI3 - H))
    beta = Q(1, 2)
    for tag, schedule in (("inner", INNER), ("outer", OUTER)):
        positive(margins, f"Prop1 beta-{tag} B1", beta - schedule[0])
        positive(margins, f"Prop1 beta-{tag} B2", beta - schedule[1])

    result = {
        "status": "full-bv-two-band-prop1-analytic-pass",
        "scope": (
            "all Proposition-1 analytic hypotheses: classical BV for (1,1); "
            "pinned repaired direct-HB plus fresh exact covers for mixed and "
            "(2,2); weighted prime minorant rho with c1=c2=0"),
        "script_sha256": sha256(FILE),
        "geometry_script_sha256": GEOMETRY_SCRIPT_SHA256,
        "geometry_result_sha256": GEOMETRY_RESULT_SHA256,
        "pinned_analytic_dependencies": PINNED_ANALYTIC,
        "parameters": {
            "k": 48, "epsilon": str(EPSILON), "delta": str(DELTA),
            "A": [str(-EPSILON), str(A1), str(A2)],
            "inner_schedule_through_first_empty": [str(x) for x in INNER],
            "outer_schedule_through_first_empty": [str(x) for x in OUTER],
            "active_inner": list(active(INNER)),
            "active_outer": list(active(OUTER)),
            "pair_exponents": {key: str(value) for key, value in exponents.items()},
            "rho": "(log n/log(3x))*1_P on [x,2x]", "c1": "0", "c2": "0",
            "beta": str(beta),
        },
        "distribution_decomposition": {
            "1,1": "classical Bombieri-Vinogradov at (1-epsilon_0)/2",
            "1,2": "repaired direct-HB at omega=3/2000",
            "2,1": "repaired direct-HB at omega=3/2000",
            "2,2": "repaired direct-HB at omega=3/1000",
        },
        "margins": {name: str(value) for name, value in margins.items()},
        "fresh_fixed_cover": {
            "cross": {"pairs": 59, "nodes": fresh_cross["node_totals"]},
            "transpose": {"pairs": 59,
                          "nodes": fresh_transpose["node_totals"]},
            "outer_self": {"pairs": 20,
                           "nodes": fresh_outer["node_totals"]},
        },
        "fresh_dynamic_iic": {
            "cross": dynamic_cross, "transpose": dynamic_transpose,
            "outer_ordered": dynamic_outer},
        "zero_zero_case": (
            "vacuous empty coordinate partition; every fixed capacity is "
            "positive and every dynamic cell capacity is nonnegative"),
        "finite_union_transfer": (
            "Definition 3 discrepancy is nonnegative before restriction; "
            "summing the four ordered band-pair bounds preserves log^-A decay"),
        "theorem_ready": False,
        "remaining": "exact k=48 quotient above one and independent final audit",
    }
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
