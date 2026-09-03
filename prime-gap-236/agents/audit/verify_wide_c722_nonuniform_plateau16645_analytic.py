#!/usr/bin/env python3
"""Independent exact audit of the nonuniform plateau 3329/20000 support.

This checker does not import the schedule-discovery program.  It starts from
the frozen 0.16605 audit, installs the explicit rational schedule below, and
reruns the source-level fixed and dynamic Proposition-1 geometry.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


FILE = Path(__file__).resolve()
BASE = FILE.with_name("verify_wide_c722_nonuniform_plateau16605_analytic.py")
BASE_SHA = "1c041d15fbd18ec4e049bd32690e135310f98d93d653f67892244f47fc3ce607"
BASE_JSON = FILE.with_name("results") / (
    "wide_c722_nonuniform_plateau16605_analytic_audit.json")
BASE_JSON_SHA = (
    "700f7931b5a700a4b144a05a94f9c0f28791d3f40c257a4b56a5a8482617af7b")

spec = importlib.util.spec_from_file_location(
    "nonuniform_plateau16645_frozen_base", BASE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen plateau-0.16605 verifier")
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
if b.v.sha(BASE) != BASE_SHA:
    raise RuntimeError("frozen plateau-0.16605 verifier changed")


v, m = b.v, b.m
PLATEAU = Q(3329, 20000)
FIRST_RADIUS = Q(1, 200000)
PLATEAU_RADIUS = Q(1, 500000)
GRID_PROBE = Q(166453, 1000000)
EXPECTED_ACTIVE = tuple(range(24))
PREDECESSOR = b.OUTER + (b.PLATEAU,)
OUTER = b.OUTER[:9] + (PLATEAU,) * 15
PLATEAU_ONLY = tuple(
    min(Q(13, 125) + (count - 1) * m.DELTA, PLATEAU)
    for count in range(1, 25))


def schedule_heads():
    return v.INNER, OUTER


def schedule_check(name, head, expected, margins):
    if name == "outer":
        expected = EXPECTED_ACTIVE
    return v._source_schedule_check(name, head, expected, margins)


def box_head(mask: int) -> tuple[Q, ...]:
    first = tuple(
        OUTER[index] +
        (FIRST_RADIUS if mask & (1 << index) else -FIRST_RADIUS)
        for index in range(9))
    plateau = PLATEAU + (
        PLATEAU_RADIUS if mask & (1 << 9) else -PLATEAU_RADIUS)
    return first + (plateau,) * 15


def schedule_audit(head: tuple[Q, ...], label: str):
    margins = {}
    v._source_schedule_check(label, head, EXPECTED_ACTIVE, margins)
    return {
        "least_margin": str(min(margins.values())),
        "least_margin_key": min(margins, key=margins.get),
        "active": list(m.active(head)),
    }


# Install the explicit schedule in the frozen source-level verifier.  Its
# dynamic routine derives its inventory from m.active(head); only the source
# schedule check needs the new expected active set.
m.FILE = FILE
m.OUTER_CAP = PLATEAU
m.schedule_heads = schedule_heads
m.check_schedule = schedule_check
m.PINNED = dict(m.PINNED)
m.PINNED[
    "agents/audit/verify_wide_c722_nonuniform_plateau16605_analytic.py"
] = BASE_SHA
m.PINNED[
    "agents/audit/results/"
    "wide_c722_nonuniform_plateau16605_analytic_audit.json"
] = BASE_JSON_SHA


def build():
    m.require(v.sha(BASE_JSON) == BASE_JSON_SHA,
              "frozen plateau-0.16605 audit JSON changed")
    old = v.strict_json(BASE_JSON)
    m.require(
        old.get("status") == "AUDIT PASS" and
        tuple(Q(x) for x in old["parameters"][
            "outer_schedule_through_first_empty"]) == b.OUTER,
        "frozen plateau-0.16605 predecessor is malformed")

    result = m.build()
    m.require(
        result["parameters"]["outer_active"] == list(EXPECTED_ACTIVE) and
        result["fixed_prefix"]["mixed"]["pairs"] == 863 and
        result["fixed_prefix"]["mixed"]["checks"] == 2589 and
        result["fixed_prefix"]["outer"]["pairs"] == 575 and
        result["fixed_prefix"]["outer"]["checks"] == 1725 and
        result["dynamic_iic"]["checks"] == 147200,
        "plateau-0.16645 inventory changed")

    # Reconstruct the corresponding uniform-ramp proposal independently.
    plateau_geometry = schedule_audit(PLATEAU_ONLY, "plateau-only")
    plateau_fixed = v.fixed_families(PLATEAU_ONLY)
    plateau_dynamic = v.dynamic_outer(PLATEAU_ONLY)
    m.require(
        plateau_geometry["active"] == list(EXPECTED_ACTIVE) and
        plateau_dynamic["checks"] == 147200,
        "plateau-only reconstruction incomplete")

    gains = tuple(new - old for new, old in zip(OUTER, PREDECESSOR))
    plateau_gains = tuple(new - old for new, old in
                          zip(OUTER, PLATEAU_ONLY))
    m.require(
        all(x > 0 for x in gains[9:]) and
        all(x == 0 for x in gains[:9]) and
        all(x >= 0 for x in plateau_gains) and
        all(x > 0 for x in plateau_gains[:9]),
        "pointwise dominance changed")

    # The schedule conditions are affine in the ten independent parameters.
    # Test all vertices.  Every support inside the box is contained in its
    # componentwise upper corner, so monotonicity reduces every packing case
    # to a fresh full fixed/dynamic verification at that upper corner.
    corner_worst = None
    for mask in range(1 << 10):
        head = box_head(mask)
        margins = {}
        v._source_schedule_check(
            f"box-corner-{mask}", head, EXPECTED_ACTIVE, margins)
        item = (min(margins.values()), mask,
                min(margins, key=margins.get))
        corner_worst = item if corner_worst is None or item < corner_worst \
            else corner_worst
    upper = box_head((1 << 10) - 1)
    upper_fixed = v.fixed_families(upper)
    upper_dynamic = v.dynamic_outer(upper)
    m.require(
        corner_worst is not None and corner_worst[0] > 0 and
        all(a <= z for a, z in zip(OUTER, upper)),
        "strict component box failed")

    # Independently check the reported near-frontier grid point, but do not
    # use it as the central support or as a premise for the box proof.
    grid = OUTER[:9] + (GRID_PROBE,) * 15
    grid_geometry = schedule_audit(grid, "grid-probe")
    grid_fixed = v.fixed_families(grid)
    grid_dynamic = v.dynamic_outer(grid)

    # A larger plateau retains Definition-1 geometry yet fails an actual
    # mixed fixed branch.  This ensures the verifier is not merely accepting
    # every schedule with the same active count.
    hostile = OUTER[:9] + (PLATEAU + Q(1, 100000),) * 15
    hostile_geometry = schedule_audit(hostile, "hostile-plateau")
    hostile_failure = v.first_fixed_failure(hostile)
    m.require(
        hostile_failure is not None and
        (hostile_failure["family"], hostile_failure["branch"],
         hostile_failure["pair"]) == ("mixed", "IIb", [1, 10]),
        "hostile plateau mutation did not expose mixed IIb")

    result["schedule_id"] = "nonuniform-outer-plateau16645-v3"
    result["parameters"].update({
        "outer_plateau": str(PLATEAU),
        "outer_schedule_through_first_empty": [str(x) for x in OUTER],
        "outer_schedule_canonical_sha256":
            v.canonical_schedule_hash(OUTER),
    })
    result["predecessor_dominance"] = {
        "plateau16605_schedule_extended_through_new_first_empty":
            [str(x) for x in PREDECESSOR],
        "coordinate_gains": [str(x) for x in gains],
        "strictly_improved_counts": list(range(10, 25)),
        "activates_new_total_large_count": 23,
        "over_plateau_only_coordinate_gains":
            [str(x) for x in plateau_gains],
    }
    result["independent_plateau_only_reconstruction"] = {
        "schedule": [str(x) for x in PLATEAU_ONLY],
        "geometry": plateau_geometry,
        "fixed_prefix": plateau_fixed,
        "dynamic_iic": plateau_dynamic,
        "status": "AUDIT PASS",
    }
    result["independent_grid_probe_166453_over_1e6"] = {
        "geometry": grid_geometry,
        "fixed_prefix": grid_fixed,
        "dynamic_iic": grid_dynamic,
        "status": "AUDIT PASS",
    }
    result["strict_component_interior"] = {
        "independent_coordinates": list(range(1, 10)),
        "shared_plateau_counts": list(range(10, 25)),
        "first_nine_radius_each": str(FIRST_RADIUS),
        "plateau_radius": str(PLATEAU_RADIUS),
        "definition1_vertices_checked": 1 << 10,
        "worst_vertex": corner_worst[1],
        "worst_vertex_schedule_margin": str(corner_worst[0]),
        "worst_vertex_schedule_margin_key": corner_worst[2],
        "pointwise_upper_corner_fixed_prefix": upper_fixed,
        "pointwise_upper_corner_dynamic_iic": upper_dynamic,
        "continuum_argument": (
            "all affine schedule and active-set constraints pass at every "
            "box vertex; every support in the box is contained in the "
            "fully verified componentwise upper corner"),
    }
    result["hostile_plateau_mutation"] = {
        "increment": "1/100000",
        "definition1_geometry": hostile_geometry,
        "first_fixed_failure": hostile_failure,
    }
    result["decision"] = (
        "the exact nonuniform schedule with plateau 3329/20000 is a "
        "strict-interior analytic Proposition-1 support, activates total "
        "large count 23, and pointwise dominates the frozen 0.16605 support; "
        "no finite-dimensional quotient is proved")
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
