#!/usr/bin/env python3
"""Exact analytic audit for the start=.104, plateau=.166 C722 schedule."""

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
BASE = FILE.with_name("verify_wide_c722_r10_166_analytic.py")
BASE_SHA = "fc48e7398f9ff798e2fa9b09b2878c6688ed44aa3619c86a8c625849b0b0535d"
spec = importlib.util.spec_from_file_location("start104_analytic_base", BASE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen r10 analytic engine")
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
if r.m.sha(BASE) != BASE_SHA:
    raise RuntimeError("frozen r10 analytic engine changed")


c, m = r.c, r.m
START = Q(13, 125)
PLATEAU = Q(83, 500)
START_RADIUS = Q(1, 5000)
PLATEAU_RADIUS = Q(1, 100000)
OUTER = c.schedule(START, PLATEAU)


def schedule_heads():
    return c.INNER, OUTER


m.FILE = FILE
m.OUTER_CAP = PLATEAU
m.schedule_heads = schedule_heads
m.PINNED = dict(m.PINNED)
m.PINNED["agents/audit/verify_wide_c722_r10_166_analytic.py"] = BASE_SHA


def canonical_schedule_hash(head):
    payload = (json.dumps([str(x) for x in head],
                          separators=(",", ":")) + "\n").encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def first_mixed_failure(start):
    outer = c.schedule(start, PLATEAU)
    capacities = m.fixed_capacities(m.CROSS_W)
    for left_count in m.active(c.INNER):
        for right_count in m.active(outer):
            if left_count + right_count == 0:
                continue
            for branch, caps in capacities.items():
                try:
                    m.prefix_certificate(
                        left_count, right_count,
                        m.bound(c.INNER, left_count),
                        m.bound(outer, right_count), caps)
                except ArithmeticError:
                    return {"branch": branch,
                            "pair": [left_count, right_count]}
    return None


def build():
    result = m.build()
    result["schedule_id"] = "start104-plateau166"
    result["parameters"].update({
        "outer_start": str(START), "outer_plateau": str(PLATEAU),
        "outer_schedule_through_first_empty": [str(x) for x in OUTER],
        "outer_schedule_canonical_sha256": canonical_schedule_hash(OUTER),
    })
    m.require(result["parameters"]["outer_active"] == list(range(23)) and
              result["fixed_prefix"]["mixed"]["pairs"] == 827 and
              result["fixed_prefix"]["outer"]["pairs"] == 528 and
              result["dynamic_iic"]["checks"] == 135168,
              "central support inventory changed")

    corners = {}
    for ds in (-START_RADIUS, START_RADIUS):
        for dp in (-PLATEAU_RADIUS, PLATEAU_RADIUS):
            head = c.schedule(START + ds, PLATEAU + dp)
            margins = c.schedule_geometry(head, f"corner-{ds}-{dp}")
            corners[f"{ds},{dp}"] = {
                "first_empty_margin": str(margins[
                    f"corner-{ds}-{dp}.first-empty"]),
                "minimum_schedule_margin": str(min(margins.values())),
            }
    upper = c.schedule(START + START_RADIUS,
                       PLATEAU + PLATEAU_RADIUS)
    upper_fixed = c.fixed_families(upper)
    upper_dynamic = c.dynamic_outer(upper)
    m.require(all(x <= y for x, y in zip(OUTER, upper)),
              "upper corner does not dominate parameter box")

    prior_r10 = c.target_schedule(10)
    count15 = c.target_schedule(15)
    volume = c.schedule(c.VOLUME_START, c.VOLUME_CAP)
    m.require(all(x >= y for x, y in zip(OUTER, prior_r10)) and
              all(x >= y for x, y in zip(OUTER, count15)) and
              all(x >= y for x, y in zip(OUTER, volume)),
              "pointwise support dominance changed")

    mixed_empty = (Q(2, 5) - m.H) - m.gb(m.CROSS_W)
    m.require(mixed_empty > 0, "mixed IIc interval is not empty")
    pass_start, fail_start = Q(417, 4000), Q(5213, 50000)
    m.require(first_mixed_failure(pass_start) is None and
              first_mixed_failure(fail_start) == {
                  "branch": "IIb", "pair": [1, 9]},
              "exact start-frontier bracket changed")
    required8 = c.required_fixed_family_diagnostic(8)
    required9 = c.required_fixed_family_diagnostic(9)
    m.require(required8.get("branch") == "IIb" and
              required8.get("pair") == [1, 7] and
              required9.get("branch") == "IIb" and
              required9.get("pair") == [1, 9],
              "true target-8/9 failure diagnostics changed")

    result["strict_parameter_interior"] = {
        "independent_start_radius": str(START_RADIUS),
        "independent_plateau_radius": str(PLATEAU_RADIUS),
        "four_definition1_corners": corners,
        "pointwise_upper_corner_fixed_prefix": upper_fixed,
        "pointwise_upper_corner_dynamic_iic": upper_dynamic,
        "continuum_argument": (
            "every schedule in this anisotropic rational box is a pointwise "
            "subset of the fully verified upper corner"),
    }
    result["exact_start_frontier_bracket_for_this_prefix_method"] = {
        "passing_start": str(pass_start),
        "failing_start": str(fail_start),
        "failing_required_branch": "mixed IIb",
        "failing_pair": [1, 9],
        "central_distance_below_passing_start": str(pass_start - START),
    }
    result["dominance"] = {
        "prior_r10_start5051_over50000": True,
        "count15_start1623_over25000": True,
        "volume_ramp": True,
    }
    result["neighboring_true_failures"] = {
        "target8": required8, "target9": required9,
        "mixed_IIc_empty_exact_margin": str(mixed_empty),
        "generic_mixed_IIc_check_is_inapplicable": True,
    }
    result["decision"] = (
        "the start=13/125, plateau=83/500 schedule is a strict-interior "
        "analytic Proposition-1 support, pointwise dominates every prior "
        "volume/count15/r10 candidate, and remains quotient-unproved")
    return result


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
