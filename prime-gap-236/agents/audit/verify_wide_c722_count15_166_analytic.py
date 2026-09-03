#!/usr/bin/env python3
"""Independent exact analytic audit of the custom count-15 C722 schedule.

The frozen p=.172 source-level verifier supplies the already-audited analytic
inequalities.  This wrapper replaces only the schedule, then reruns every
schedule-dependent fixed and continuous packing certificate.  It additionally
certifies a rational open parameter box and diagnoses a spurious "mixed IIc"
frontier produced by the older generic discovery checker.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
COMMON = FILE.with_name("verify_wide_c722_p172_analytic.py")
COMMON_SHA = "b0a972af7d5a708fe0cb52eabeb9a477f70606399743c4f6856559271ab7af06"

spec = importlib.util.spec_from_file_location(
    "count15_166_common_source_audit", COMMON)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen common analytic verifier")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
if m.sha(COMMON) != COMMON_SHA:
    raise RuntimeError("frozen common analytic verifier changed")


PLATEAU = Q(83, 500)
TARGET = 15
START = Q(1623, 25000)
INTERIOR_RADIUS = Q(1, 100000)
VOLUME_START = Q(49, 625)
VOLUME_CAP = Q(1599, 10000)
EXPECTED_ACTIVE = tuple(range(23))
INNER = (m.INNER_CAP,) * 36


def schedule(start: Q, plateau: Q) -> tuple[Q, ...]:
    return tuple(min(start + (count - 1) * m.DELTA, plateau)
                 for count in range(1, 24))


def target_schedule(target: int) -> tuple[Q, ...]:
    return schedule(PLATEAU - (target - 1) * m.DELTA, PLATEAU)


CENTRAL = schedule(START, PLATEAU)


def schedule_heads():
    return INNER, CENTRAL


_source_schedule_check = m.check_schedule


def build_schedule_check(name, head, expected, margins):
    if name == "outer":
        expected = EXPECTED_ACTIVE
    return _source_schedule_check(name, head, expected, margins)


def dynamic_outer(outer: tuple[Q, ...]) -> dict[str, object]:
    """Complete repaired-IIc continuum cover for this active inventory."""
    gmin, gmax = Q(2, 5) - m.H, m.gb(m.OUTER_W)
    worst = None
    pairs = checks = 0
    for left_count in m.active(outer):
        for right_count in m.active(outer):
            if left_count + right_count == 0:
                continue
            for iw in range(m.CELLS):
                wl = m.OUTER_W * iw / m.CELLS
                wu = m.OUTER_W * (iw + 1) / m.CELLS
                for ig in range(m.CELLS):
                    gl = gmin + (gmax - gmin) * ig / m.CELLS
                    gu = gmin + (gmax - gmin) * (ig + 1) / m.CELLS
                    capacities = m.cell_capacities(gl, gu, wl, wu)
                    m.require(min(capacities) >= 0,
                              "negative dynamic-IIc cell capacity")
                    certificate = m.prefix_certificate(
                        left_count, right_count,
                        m.bound(outer, left_count),
                        m.bound(outer, right_count), capacities)
                    item = (certificate[0], left_count, right_count,
                            iw, ig, certificate[1], certificate[2],
                            certificate[3])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
            pairs += 1
    expected_pairs = len(m.active(outer)) ** 2 - 1
    m.require((pairs, checks) == (
        expected_pairs, expected_pairs * m.CELLS * m.CELLS),
        "dynamic-IIc inventory changed")
    m.require(worst is not None and worst[0] > 0,
              "no strict dynamic-IIc certificate")
    return {"pairs": pairs, "checks": checks,
            "worst_margin": str(worst[0]), "worst": list(worst[1:])}


def fixed_families(outer: tuple[Q, ...]) -> dict[str, object]:
    return {
        "mixed": m.check_fixed_family(INNER, outer, m.CROSS_W, "mixed"),
        "transpose": m.check_fixed_family(
            outer, INNER, m.CROSS_W, "transpose"),
        "outer": m.check_fixed_family(
            outer, outer, m.OUTER_W, "outer"),
        "outer_near": m.check_fixed_family(
            outer, outer, Q(0), "outer-near"),
    }


def schedule_geometry(outer: tuple[Q, ...], label: str):
    margins = {}
    _source_schedule_check(label, outer, EXPECTED_ACTIVE, margins)
    return margins


def required_fixed_family_diagnostic(target: int):
    """Return PASS or the first failure among nonempty source branches."""
    outer = target_schedule(target)
    families = (
        ("mixed", INNER, outer, m.CROSS_W),
        ("transpose", outer, INNER, m.CROSS_W),
        ("outer", outer, outer, m.OUTER_W),
        ("outer_near", outer, outer, Q(0)),
    )
    for family, left, right, omega in families:
        capacities = m.fixed_capacities(omega)
        for left_count in m.active(left):
            for right_count in m.active(right):
                if left_count + right_count == 0:
                    continue
                for branch, caps in capacities.items():
                    try:
                        m.prefix_certificate(
                            left_count, right_count,
                            m.bound(left, left_count),
                            m.bound(right, right_count), caps)
                    except ArithmeticError:
                        return {
                            "status": "prefix-certificate FAIL",
                            "family": family, "branch": branch,
                            "pair": [left_count, right_count],
                            "capacities": [str(x) for x in caps],
                        }
    return {"status": "required-fixed PASS"}


def obsolete_mixed_iic_capacities() -> tuple[Q, ...]:
    """The generic producer's fixed IIc capacities, used diagnostically."""
    delta_c = m.DELTA + 4 * m.H
    gamma_min = Q(2, 5) - m.H
    gamma_max = (Q(1, 3) + 8 * m.CROSS_W +
                 Q(7, 3) * m.DELTA + 3 * m.H)
    return (
        gamma_min - 2 * delta_c - 8 * m.CROSS_W - 58 * m.ZETA + m.R0,
        Q(1, 2) - gamma_max - 2 * m.CROSS_W - 6 * m.ZETA - m.R0,
        delta_c,
        2 * m.R0,
    )


def obsolete_generic_failures():
    """Reproduce, but do not endorse, the generic empty-branch failures."""
    caps = obsolete_mixed_iic_capacities()
    results = {}
    for target in range(8, 15):
        outer = target_schedule(target)
        failure = None
        for left_count in m.active(INNER):
            for right_count in m.active(outer):
                if left_count + right_count == 0:
                    continue
                try:
                    m.prefix_certificate(
                        left_count, right_count,
                        m.bound(INNER, left_count),
                        m.bound(outer, right_count), caps)
                except ArithmeticError:
                    failure = [left_count, right_count]
                    break
            if failure is not None:
                break
        results[str(target)] = failure
    return results


# Install only the central schedule into the frozen source-level engine.
m.FILE = FILE
m.OUTER_CAP = PLATEAU
m.schedule_heads = schedule_heads
m.check_schedule = build_schedule_check
m.check_dynamic_outer = dynamic_outer
m.PINNED = dict(m.PINNED)
m.PINNED.pop("results/bv_c722_wide_two_band_geometry_high_plateau_v3.json")
m.PINNED["agents/audit/verify_wide_c722_p172_analytic.py"] = COMMON_SHA


def build():
    m.require(START == PLATEAU - (TARGET - 1) * m.DELTA,
              "central target-ramp identity changed")
    central = m.build()
    central["schedule_id"] = "count15-plateau-166"
    central["parameters"].update({
        "outer_start": str(START), "outer_plateau": str(PLATEAU),
        "ramp_reaches_plateau_at_count": TARGET,
        "outer_schedule_through_first_empty": [str(x) for x in CENTRAL],
    })
    m.require(central["fixed_prefix"]["mixed"]["pairs"] == 827 and
              central["fixed_prefix"]["outer"]["pairs"] == 528 and
              central["dynamic_iic"]["checks"] == 135168,
              "central schedule inventory changed")

    # A full rational two-parameter box lies inside the same analytic region.
    # Every schedule in the box is pointwise bounded by its upper corner, so
    # the upper-corner packing proof covers the continuum, while the four
    # corners certify the Definition-1/active-count combinatorics.
    corners = {}
    for ds in (-INTERIOR_RADIUS, INTERIOR_RADIUS):
        for dc in (-INTERIOR_RADIUS, INTERIOR_RADIUS):
            candidate = schedule(START + ds, PLATEAU + dc)
            margins = schedule_geometry(
                candidate, f"corner-{ds}-{dc}")
            corners[f"{ds},{dc}"] = {
                "first_empty_margin": str(margins[
                    f"corner-{ds}-{dc}.first-empty"]),
                "minimum_schedule_margin": str(min(margins.values())),
            }
    upper = schedule(START + INTERIOR_RADIUS,
                     PLATEAU + INTERIOR_RADIUS)
    upper_fixed = fixed_families(upper)
    upper_dynamic = dynamic_outer(upper)
    m.require(all(a <= b for a, b in zip(CENTRAL, upper)),
              "interior upper corner does not dominate central schedule")

    # Test the maximal-slope family honestly.  The old generic checker adds a
    # mixed IIc branch whose gamma interval is empty; its resulting r=8..14
    # failures are not source hypotheses.  On the actual nonempty branches,
    # r=8,9 fail this sufficient prefix method in IIb, while r=10 passes a
    # complete fixed+dynamic check and pointwise contains r=11,...,15.
    required = {str(target): required_fixed_family_diagnostic(target)
                for target in range(8, 16)}
    m.require(required["8"]["branch"] == "IIb" and
              required["9"]["branch"] == "IIb" and
              all(required[str(target)]["status"] == "required-fixed PASS"
                  for target in range(10, 16)),
              "neighboring required-branch diagnostic changed")
    target10 = target_schedule(10)
    target10_fixed = fixed_families(target10)
    target10_dynamic = dynamic_outer(target10)
    m.require(all(a >= b for a, b in zip(target10, CENTRAL)),
              "target-10 schedule no longer contains target-15 schedule")
    volume = schedule(VOLUME_START, VOLUME_CAP)
    m.require(all(a >= b for a, b in zip(target10, volume)),
              "target-10 schedule no longer contains volume ramp")

    empty_margin = (Q(2, 5) - m.H) - m.gb(m.CROSS_W)
    m.require(empty_margin > 0, "mixed IIc interval is no longer empty")
    obsolete = obsolete_generic_failures()
    m.require(obsolete == {
        "8": [1, 1], "9": [1, 1], "10": [1, 1],
        "11": [1, 2], "12": [1, 9], "13": [1, 12],
        "14": [1, 14]},
        "obsolete generic failure inventory changed")

    central["strict_parameter_interior"] = {
        "independent_start_and_plateau_radius": str(INTERIOR_RADIUS),
        "four_definition1_corners": corners,
        "pointwise_upper_corner_fixed_prefix": upper_fixed,
        "pointwise_upper_corner_dynamic_iic": upper_dynamic,
        "argument": (
            "schedule is monotone in start and plateau; the verified upper "
            "corner contains every support in the rational parameter box"),
    }
    central["neighboring_maximal_slope_family"] = {
        "required_fixed_diagnostics": required,
        "target10_complete_fixed": target10_fixed,
        "target10_complete_dynamic_iic": target10_dynamic,
        "first_fully_verified_target": 10,
        "target10_start": str(PLATEAU - 9 * m.DELTA),
        "target10_pointwise_dominates_count15": True,
        "target10_pointwise_dominates_volume_ramp": True,
        "generic_producer_empty_mixed_IIc_failures": obsolete,
        "mixed_IIc_empty_exact_margin": str(empty_margin),
        "warning": (
            "the generic r=8..14 mixed-IIc failures concern an empty gamma "
            "range and do not establish an analytic frontier at r=15"),
    }
    central["decision"] = (
        "the count-15 schedule is strictly interior and satisfies the exact "
        "analytic Proposition-1 hypotheses; moreover the pointwise larger "
        "target-10 schedule is also analytically verified, so r=15 is not "
        "the genuine frontier")
    return central


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
