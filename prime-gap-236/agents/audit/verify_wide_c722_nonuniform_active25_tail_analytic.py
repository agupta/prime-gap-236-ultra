#!/usr/bin/env python3
"""Independent exact audit of the active-25 nonuniform C722 tail schedule.

No discovery script is imported.  The explicit rational schedule is installed
in the frozen source-level analytic verifier and every fixed/dynamic case is
reconstructed.  A correlated-plateau interval proof supplies a 25-parameter
strict component box without enumerating 2**25 vertices.
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
BASE = FILE.with_name("verify_wide_c722_nonuniform_plateau16645_analytic.py")
BASE_SHA = "fa8b10aa1b95d5f3636fbf3f76f5aac2484eb8fc4aec99e305667631c5363daf"
BASE_JSON = FILE.with_name("results") / (
    "wide_c722_nonuniform_plateau16645_analytic_audit.json")
BASE_JSON_SHA = (
    "999c77ced0adca5bae2f3302a05e481a583a5a75a3d89522bd64e52e7119f8b7")

spec = importlib.util.spec_from_file_location(
    "nonuniform_active25_frozen_base", BASE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen plateau-0.16645 verifier")
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
if b.v.sha(BASE) != BASE_SHA:
    raise RuntimeError("frozen plateau-0.16645 verifier changed")


v, m = b.v, b.m
EXPECTED_ACTIVE = tuple(range(26))
BOX_RADIUS = Q(1, 1000000)
TAIL = tuple(Q(x, 10000) for x in (
    1690, 1695, 1718, 1737, 1752, 1762, 1764, 1774,
    1782, 1790, 1796, 1801, 1806, 1811, 1815))
OUTER = b.OUTER[:10] + TAIL + (Q(1815, 10000),)
PREDECESSOR = b.OUTER + (b.PLATEAU,) * 2


def schedule_heads():
    return v.INNER, OUTER


def schedule_check(name, head, expected, margins):
    if name == "outer":
        expected = EXPECTED_ACTIVE
    return v._source_schedule_check(name, head, expected, margins)


def varied_corner(sign: int) -> tuple[Q, ...]:
    """All independent B1..B24 and the shared B25+ at one sign."""
    if sign not in (-1, 1):
        raise ValueError("corner sign must be +/-1")
    first = tuple(x + sign * BOX_RADIUS for x in OUTER[:24])
    plateau = OUTER[24] + sign * BOX_RADIUS
    return first + (plateau,) * 2


def interval_geometry_certificate():
    """Prove Definition-1 geometry throughout the component box.

    B1,...,B24 vary independently.  B25 and every subsequent Definition-1
    entry share one plateau parameter.  All relevant conditions are affine;
    the exact endpoint bounds below are therefore universal for the box.
    """
    length = int(Q(1) // m.DELTA)
    center = OUTER[:24] + (OUTER[24],) * (length - 24)
    lower = OUTER[:24]
    lower = tuple(x - BOX_RADIUS for x in lower) + \
        (OUTER[24] - BOX_RADIUS,) * (length - 24)
    upper = OUTER[:24]
    upper = tuple(x + BOX_RADIUS for x in upper) + \
        (OUTER[24] + BOX_RADIUS,) * (length - 24)
    m.require(len(center) == len(lower) == len(upper) == 138,
              "component-box extension length changed")

    delta_lower = min(x - m.DELTA for x in lower)
    # Transitions through B24->B25 involve independently varying parameters.
    # B25 onward is one shared plateau and hence has exact difference zero.
    nondecreasing = min(lower[i + 1] - upper[i] for i in range(24))
    step_upper = min(
        m.DELTA - (upper[i + 1] - lower[i]) for i in range(24))
    active_margin = min(lower[count - 1] - count * m.DELTA
                        for count in range(1, 26))
    empty_margin = min(count * m.DELTA - upper[count - 1]
                       for count in range(26, 139))
    m.require(min(delta_lower, nondecreasing, step_upper,
                  active_margin, empty_margin) > 0,
              "component box does not preserve Definition-1 geometry")

    lower_head, upper_head = varied_corner(-1), varied_corner(1)
    lower_margins, upper_margins = {}, {}
    v._source_schedule_check(
        "component-lower", lower_head, EXPECTED_ACTIVE, lower_margins)
    v._source_schedule_check(
        "component-upper", upper_head, EXPECTED_ACTIVE, upper_margins)
    return {
        "independent_coordinates": list(range(1, 25)),
        "shared_plateau_counts": list(range(25, 139)),
        "radius_each": str(BOX_RADIUS),
        "minimum_B_minus_delta": str(delta_lower),
        "minimum_independent_transition_increase": str(nondecreasing),
        "minimum_independent_transition_step_slack": str(step_upper),
        "minimum_active_margin": str(active_margin),
        "minimum_empty_margin": str(empty_margin),
        "lower_corner_minimum_checked_margin":
            str(min(lower_margins.values())),
        "upper_corner_minimum_checked_margin":
            str(min(upper_margins.values())),
        "affine_interval_argument": (
            "the displayed endpoint bounds cover every affine Definition-1 "
            "constraint; entries B25 onward are one shared parameter"),
    }


def schedule_audit(head: tuple[Q, ...], label: str):
    margins = {}
    v._source_schedule_check(label, head, EXPECTED_ACTIVE, margins)
    return {"active": list(m.active(head)),
            "least_margin": str(min(margins.values())),
            "least_margin_key": min(margins, key=margins.get)}


m.FILE = FILE
m.OUTER_CAP = OUTER[-1]
m.schedule_heads = schedule_heads
m.check_schedule = schedule_check
m.PINNED = dict(m.PINNED)
m.PINNED[
    "agents/audit/verify_wide_c722_nonuniform_plateau16645_analytic.py"
] = BASE_SHA
m.PINNED[
    "agents/audit/results/"
    "wide_c722_nonuniform_plateau16645_analytic_audit.json"
] = BASE_JSON_SHA


def build():
    m.require(v.sha(BASE_JSON) == BASE_JSON_SHA,
              "frozen plateau-0.16645 audit JSON changed")
    old = v.strict_json(BASE_JSON)
    m.require(
        old.get("status") == "AUDIT PASS" and
        tuple(Q(x) for x in old["parameters"][
            "outer_schedule_through_first_empty"]) == b.OUTER,
        "frozen plateau-0.16645 predecessor is malformed")
    m.require(len(OUTER) == 26 and OUTER[9] == Q(3329, 20000) and
              OUTER[24] == OUTER[25] == Q(1815, 10000),
              "explicit tail identity changed")

    result = m.build()
    m.require(
        result["parameters"]["outer_active"] == list(EXPECTED_ACTIVE) and
        result["fixed_prefix"]["mixed"]["pairs"] == 935 and
        result["fixed_prefix"]["mixed"]["checks"] == 2805 and
        result["fixed_prefix"]["outer"]["pairs"] == 675 and
        result["fixed_prefix"]["outer"]["checks"] == 2025 and
        result["dynamic_iic"]["pairs"] == 675 and
        result["dynamic_iic"]["checks"] == 172800,
        "active-25 analytic inventory changed")

    gains = tuple(new - old for new, old in zip(OUTER, PREDECESSOR))
    m.require(all(x == 0 for x in gains[:10]) and
              all(x > 0 for x in gains[10:]),
              "predecessor dominance pattern changed")

    box = interval_geometry_certificate()
    upper = varied_corner(1)
    upper_fixed = v.fixed_families(upper)
    upper_dynamic = v.dynamic_outer(upper)
    m.require(all(a <= z for a, z in zip(OUTER, upper)),
              "box upper corner does not contain central support")
    box["pointwise_upper_corner_fixed_prefix"] = upper_fixed
    box["pointwise_upper_corner_dynamic_iic"] = upper_dynamic
    box["packing_continuum_argument"] = (
        "every box support is a subset of the fully verified componentwise "
        "upper corner, so every fixed and dynamic prefix certificate applies")

    # Three independent hostile mutations preserve Definition-1 geometry but
    # fail distinct advertised fixed-prefix bottlenecks.
    hostile = {}
    for label, index, expected in (
            ("B1_plus_1_over_10000", 0, ("mixed", "III", [1, 1])),
            ("B9_plus_1_over_10000", 8, ("mixed", "IIb", [1, 9])),
            ("B10_plus_1_over_10000", 9, ("mixed", "IIb", [1, 10]))):
        changed = list(OUTER)
        changed[index] += Q(1, 10000)
        geometry = schedule_audit(tuple(changed), label)
        failure = v.first_fixed_failure(tuple(changed))
        m.require(
            failure is not None and
            (failure["family"], failure["branch"], failure["pair"]) ==
            expected,
            f"hostile fixture changed: {label}")
        hostile[label] = {"definition1_geometry": geometry,
                          "first_fixed_failure": failure}

    result["schedule_id"] = "nonuniform-outer-active25-tail-v4"
    result["parameters"].update({
        "outer_schedule_through_first_empty": [str(x) for x in OUTER],
        "outer_schedule_canonical_sha256":
            v.canonical_schedule_hash(OUTER),
        "outer_final_plateau": str(OUTER[-1]),
    })
    result["finite_space_count_identity"] = {
        "active_shell_total_large_counts": list(EXPECTED_ACTIVE),
        "shell_constant_coordinates": 26,
        "retained_inner_coordinates": 1,
        "resulting_dimension": 27,
        "first_empty_total_large_count": 26,
        "B25_minus_25delta": str(OUTER[24] - 25 * m.DELTA),
        "26delta_minus_B26": str(26 * m.DELTA - OUTER[25]),
    }
    result["predecessor_dominance"] = {
        "predecessor_schedule_extended_through_new_first_empty":
            [str(x) for x in PREDECESSOR],
        "coordinate_gains": [str(x) for x in gains],
        "strictly_improved_B_indices": list(range(11, 27)),
        "newly_active_total_large_counts": [24, 25],
    }
    result["strict_component_interior"] = box
    result["hostile_mutation_fixtures"] = hostile
    result["decision"] = (
        "the explicit active-25 nonuniform tail is a strict-interior "
        "analytic Proposition-1 support and pointwise dominates the frozen "
        "plateau-0.16645 support; the corresponding inner-plus-shell space "
        "has dimension 27; no quotient is proved")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
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
