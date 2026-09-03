#!/usr/bin/env python3
"""Exact mixed-band partition audit for the two-band BV-shell proposal.

This is a geometric Proposition-3/direct-HB factorization audit only.  It
does not prove prime equidistribution and it does not compute a sieve
quotient.  All endpoint arithmetic and all continuum box covers use
``Fraction``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import argparse
import os
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
IV_PATH = REPO / "agents/independent-attack/code/interval_partition_verify.py"
IV_SHA256 = "d120c5fac080d494b4876c7186f51123bba66bee5d9a04ec4d7ea79420fac564"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha256(IV_PATH) != IV_SHA256:
    raise RuntimeError("interval-cover source hash changed")
spec = importlib.util.spec_from_file_location("two_band_interval_cover", IV_PATH)
if spec is None or spec.loader is None:
    raise ImportError("cannot load interval cover")
iv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = iv
spec.loader.exec_module(iv)


H = Q(1, 10**10)
ZETA = H / 1000
INWARD = H / 10
DELTA = Q(7, 250)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(253, 1000)
OMEGA = (A1 + A2) / 2 - Q(1, 4)

# The last repeated value is included through the first empty count.  Counts
# beyond it are empty a fortiori because the schedule is extended constantly.
INNER = (Q(181, 1000), Q(181, 1000), Q(209, 1000), Q(109, 500),
         Q(109, 500), Q(109, 500), Q(109, 500), Q(109, 500))
OUTER = (Q(3, 20), Q(3, 20), Q(17, 100), Q(17, 100),
         Q(17, 100), Q(17, 100), Q(17, 100))

# A one-band interior improvement found by pushing the self-pair all the way
# to omega=3/1000.  The tiny retreat from 4/25 is deliberate: the literal
# inward reserve makes B_1=B_2=4/25 fail IIc at (1,1).
ONE_BAND = (Q(159999999, 10**9), Q(159999999, 10**9),
            Q(177, 1000), Q(177, 1000), Q(177, 1000),
            Q(177, 1000), Q(177, 1000))

# Complementary two-band route which retains the complete BV inner simplex.
# This arithmetic-progression outer schedule is materially larger than the
# first feasible constant 2/25 schedule while preserving Definition 1.
FULL_BV_INNER = (Q(103, 400),) * 10
FULL_BV_OUTER = (Q(43, 500), Q(43, 500), Q(57, 500),
                 Q(71, 500), Q(71, 500), Q(71, 500))


def positive(name: str, value: Q) -> None:
    if value <= 0:
        raise AssertionError(f"{name} is not positive: {value}")


def check_schedule(name: str, schedule: tuple[Q, ...]) -> tuple[int, ...]:
    for index, value in enumerate(schedule):
        positive(f"{name} B[{index + 1}]-delta", value - DELTA)
        if index and not schedule[index - 1] <= value <= \
                schedule[index - 1] + DELTA:
            raise AssertionError(f"{name} Definition-1 transition failed")
    active = tuple(index for index in range(1, len(schedule) + 1)
                   if index * DELTA <= schedule[index - 1])
    first_empty = max(active, default=0) + 1
    if first_empty > len(schedule) or \
            first_empty * DELTA <= schedule[first_empty - 1]:
        raise AssertionError(f"{name} first empty count was not supplied")
    return (0,) + active


def capacities(omega: Q = OMEGA) -> dict[str, tuple[Q, ...]]:
    sigma = Q(1, 10) + H / 10
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    delta_c = DELTA + 4 * H
    gamma_min = Q(2, 5) - H
    gamma_max = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    answer = {
        "IIa": (
            Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA - 2 * H,
            Q(1, 14) - Q(24, 7) * omega - 2 * H,
        ),
        "IIb": (
            Q(1, 3) + 8 * omega + Q(7, 3) * DELTA - 4 * H,
            Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * DELTA - 4 * H,
            Q(1, 35) + Q(22, 35) * omega + Q(21, 35) * DELTA - 4 * H,
        ),
        "III": (
            Q(1, 3) + Q(4, 3) * delta3 - Q(4, 3) * omega - H,
            Q(1, 6) - delta3 / 3 + Q(4, 3) * omega - H,
        ),
        # Literal repaired IIc capacities after shrinking all three open
        # intervals [a_i,b_i] to [a_i+H/10,b_i-H/10].
        "IIc": (
            gamma_min - 2 * delta_c - 8 * omega - 58 * ZETA + INWARD,
            Q(1, 2) - gamma_max - 2 * omega - 6 * ZETA - INWARD,
            delta_c,
            2 * INWARD,
        ),
    }
    for name, values in answer.items():
        for index, value in enumerate(values):
            positive(f"{name} capacity {index + 1}", value)
    return answer


def exact_redundant_counterexample(caps: tuple[Q, ...]) -> None:
    point = (Q(103, 400), Q(3, 20))
    if point[0] + point[1] <= caps[0]:
        raise AssertionError("reported both-in-first obstruction disappeared")
    for value in point:
        if value <= max(caps[1:]):
            raise AssertionError("reported singleton obstruction disappeared")


def retained_smooth_mass_counterexample() -> dict[str, object]:
    """An actual mixed support point still outside repaired D_IIc.

    The outer shell's small-coordinate mass is retained, and even split into
    four factors below x^delta.  Treating those factors as continuously
    divisible would be stronger than justified; the literal four-factor
    smooth modulus has no admissible (r,d1) at gamma=2/5.
    """
    kappa = Q(1, 100000)
    inner_atom = Q(97, 400) - kappa
    outer_large = Q(3, 20)
    outer_total = Q(521, 2000) - kappa
    smooth_total = outer_total - outer_large
    smooth_atom = smooth_total / 4
    atoms = (inner_atom, outer_large) + (smooth_atom,) * 4
    modulus = sum(atoms)
    gamma = Q(2, 5)
    delta_c = DELTA + 4 * H
    if not (Q(103, 400) < outer_total < Q(521, 2000)):
        raise AssertionError("outer point is not strictly inside the shell")
    if not smooth_atom < DELTA:
        raise AssertionError("declared smooth atoms are not below delta")
    if not Q(1, 2) < modulus < Q(503, 1000):
        raise AssertionError("counterexample modulus is not above sqrt")

    admissible_r = []
    for mask in range(1 << len(atoms)):
        r = sum(atoms[index] for index in range(len(atoms))
                if (mask >> index) & 1)
        if not gamma - delta_c < r < gamma:
            continue
        d1_lo = 2 * r + 2 - gamma - delta_c - 4 * modulus
        d1_hi = 2 * r + 2 - gamma - 4 * modulus
        witnesses = []
        indices = [index for index in range(len(atoms))
                   if (mask >> index) & 1]
        for flags in itertools.product((0, 1), repeat=len(indices)):
            d1 = sum(atoms[index] for index, flag in zip(indices, flags)
                     if flag)
            if d1_lo < d1 < d1_hi:
                witnesses.append(str(d1))
        admissible_r.append({
            "mask": mask, "r": str(r), "d1_open_interval":
            [str(d1_lo), str(d1_hi)], "d1_witnesses": witnesses,
        })
    if not admissible_r or any(item["d1_witnesses"] for item in admissible_r):
        raise AssertionError("retained-smooth-mass obstruction disappeared")
    return {
        "kappa": str(kappa),
        "inner_large_atom": str(inner_atom),
        "outer_large_atom": str(outer_large),
        "outer_total": str(outer_total),
        "smooth_total": str(smooth_total),
        "four_smooth_atoms": [str(smooth_atom)] * 4,
        "modulus_exponent": str(modulus),
        "gamma": str(gamma),
        "delta_c": str(delta_c),
        "admissible_r_without_d1": admissible_r,
    }


def cover_pair(m: int, mp: int, inner: Q, outer: Q,
               caps: tuple[Q, ...], label: str) -> dict[str, int]:
    g1 = iv.initial_group(m, inner)
    g2 = iv.initial_group(mp, outer)
    if g1 is None or g2 is None:
        raise AssertionError("active group unexpectedly empty")
    state = {
        "nodes": 0,
        "leaves": 0,
        "max_depth": 0,
        "node_limit": 4_000_000,
        "min_width": Q(1, 10**12),
        "witness_box": None,
    }
    try:
        proved = iv.cover((g1, g2), caps, state)
    except iv.Limit as exc:
        raise RuntimeError(f"node limit in {label}: {state}") from exc
    if not proved:
        raise AssertionError(f"unresolved continuum box in {label}: {state}")
    return {key: state[key] for key in ("nodes", "leaves", "max_depth")}


def cover_schedule_pair(left: tuple[Q, ...], right: tuple[Q, ...],
                        omega: Q, *, unordered: bool = False) -> dict[str, object]:
    """Cover every active count pair for two schedules at one omega."""
    active_left = check_schedule("left", left)
    active_right = check_schedule("right", right)
    caps = capacities(omega)
    covers: dict[str, object] = {}
    totals = {name: 0 for name in caps}
    pair_count = 0
    for m in active_left:
        for mp in active_right:
            if m + mp == 0 or (unordered and m > mp):
                continue
            bm = Q(0) if m == 0 else left[m - 1]
            bp = Q(0) if mp == 0 else right[mp - 1]
            pair = {}
            for name, values in caps.items():
                stats = cover_pair(m, mp, bm, bp, values,
                                   f"{name} pair {m},{mp}")
                pair[name] = stats
                totals[name] += stats["nodes"]
            covers[f"{m},{mp}"] = pair
            pair_count += 1
    return {
        "omega": str(omega),
        "active_left": list(active_left),
        "active_right": list(active_right),
        "pair_count": pair_count,
        "node_totals": totals,
        "covers": covers,
    }


def publish(path: Path, payload: bytes) -> None:
    """Publish fresh output without overwriting an earlier audit artifact."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def build_report() -> dict[str, object]:
    iv.DELTA = DELTA
    iv.H = H
    positive("A2-A1", A2 - A1)
    positive("A2 upper", Q(1, 2) - EPSILON - A2)
    if OMEGA != Q(3, 2000):
        raise AssertionError("mixed omega changed")
    active_inner = check_schedule("inner", INNER)
    active_outer = check_schedule("outer", OUTER)
    caps = capacities(OMEGA)
    expected_iic = (
        Q(1659999995521, 5000000000000),
        Q(1294999995341, 15000000000000),
        Q(70000001, 2500000000),
        Q(1, 50000000000),
    )
    if caps["IIc"] != expected_iic:
        raise ArithmeticError(f"IIc capacity reconstruction changed: {caps['IIc']}")
    exact_redundant_counterexample(caps["IIc"])
    smooth_obstruction = retained_smooth_mass_counterexample()

    original_mixed = cover_schedule_pair(INNER, OUTER, OMEGA)

    one_omega = A2 - Q(1, 4)
    one_caps = capacities(one_omega)
    critical_margin = one_caps["IIc"][0] - 2 * ONE_BAND[0]
    positive("one-band IIc (1,1) margin", critical_margin)
    failed_endpoint_gap = 2 * Q(4, 25) - one_caps["IIc"][0]
    positive("one-band endpoint B=4/25 obstruction", failed_endpoint_gap)
    if any(Q(4, 25) <= value for value in one_caps["IIc"][1:]):
        raise AssertionError("endpoint obstruction no longer excludes singleton bins")
    one_band_cover = cover_schedule_pair(
        ONE_BAND, ONE_BAND, one_omega, unordered=True)

    full_bv_cross = cover_schedule_pair(
        FULL_BV_INNER, FULL_BV_OUTER, OMEGA)
    full_bv_transpose = cover_schedule_pair(
        FULL_BV_OUTER, FULL_BV_INNER, OMEGA)
    full_bv_outer_self = cover_schedule_pair(
        FULL_BV_OUTER, FULL_BV_OUTER, one_omega, unordered=True)

    report = {
        "status": "one-band-and-two-band-exact-geometric-cover-pass",
        "scope": "factorization geometry only; no source-level equidistribution or sieve quotient",
        "script_sha256": sha256(FILE),
        "interval_cover_sha256": IV_SHA256,
        "parameters": {
            "delta": str(DELTA), "epsilon": str(EPSILON),
            "A1": str(A1), "A2": str(A2), "omega_cross": str(OMEGA),
        },
        "inner_schedule": [str(value) for value in INNER],
        "outer_schedule": [str(value) for value in OUTER],
        "active_inner_counts": list(active_inner),
        "active_outer_counts": list(active_outer),
        "capacities": {name: [str(value) for value in values]
                       for name, values in caps.items()},
        "redundant_counterexample": ["103/400", "3/20"],
        "retained_smooth_mass_counterexample": smooth_obstruction,
        "original_relaxed_two_band": original_mixed,
        "one_band_improvement": {
            "A": str(A2),
            "omega": str(one_omega),
            "schedule": [str(value) for value in ONE_BAND],
            "critical_iic_margin": str(critical_margin),
            "excluded_B1_B2_4_over_25_gap": str(failed_endpoint_gap),
            "cover": one_band_cover,
        },
        "full_bv_two_band_backup": {
            "inner_schedule": [str(value) for value in FULL_BV_INNER],
            "outer_schedule": [str(value) for value in FULL_BV_OUTER],
            "low_low_assignment": "classical BV, not direct-HB",
            "cross": full_bv_cross,
            "transpose": full_bv_transpose,
            "outer_self": full_bv_outer_self,
        },
        "definition5_band_split_warning": (
            "equal cap schedules do not collapse J unless eta1=eta2: "
            "the m1^2 term is absent for eta1<u<=eta2"
        ),
        "theorem_ready": False,
        "missing": [
            "prime-equidistribution proof for the refined two-band modulus class",
            "source-level endpoint audit for every reused distribution lemma",
            "finite-dimensional quotient above one",
        ],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    payload = (json.dumps(report, sort_keys=True, separators=(",", ":")) +
               "\n").encode()
    if args.output is not None:
        publish(args.output, payload)
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
