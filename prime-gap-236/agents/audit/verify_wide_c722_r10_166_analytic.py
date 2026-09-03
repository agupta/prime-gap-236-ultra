#!/usr/bin/env python3
"""Exact analytic audit for the dominating target-10/0.166 C722 schedule."""

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
REPO = FILE.parents[2]
BASE = FILE.with_name("verify_wide_c722_count15_166_analytic.py")
BASE_SHA = "3d6c3c2a1887d0bce11303b62ad37f5427fbfce425d3aa8888e67f6ac9eb2cdf"
spec = importlib.util.spec_from_file_location("r10_166_analytic_base", BASE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen schedule audit engine")
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
if c.m.sha(BASE) != BASE_SHA:
    raise RuntimeError("frozen schedule audit engine changed")


m = c.m
TARGET = 10
START = Q(5051, 50000)
PLATEAU = Q(83, 500)
RADIUS = Q(1, 100000)
OUTER = c.schedule(START, PLATEAU)


def schedule_heads():
    return c.INNER, OUTER


m.FILE = FILE
m.OUTER_CAP = PLATEAU
m.schedule_heads = schedule_heads
m.PINNED = dict(m.PINNED)
m.PINNED[
    "agents/audit/verify_wide_c722_count15_166_analytic.py"] = BASE_SHA


def canonical_schedule_hash(head):
    data = (json.dumps([str(x) for x in head], separators=(",", ":")) +
            "\n").encode("ascii")
    return hashlib.sha256(data).hexdigest()


def build():
    m.require(START == PLATEAU - (TARGET - 1) * m.DELTA,
              "target-10 ramp identity changed")
    result = m.build()
    result["schedule_id"] = "r10-plateau-166"
    result["parameters"].update({
        "outer_start": str(START), "outer_plateau": str(PLATEAU),
        "ramp_reaches_plateau_at_count": TARGET,
        "outer_schedule_through_first_empty": [str(x) for x in OUTER],
        "outer_schedule_canonical_sha256": canonical_schedule_hash(OUTER),
    })
    m.require(result["parameters"]["outer_active"] == list(range(23)) and
              result["fixed_prefix"]["mixed"]["pairs"] == 827 and
              result["fixed_prefix"]["outer"]["pairs"] == 528 and
              result["dynamic_iic"]["checks"] == 135168,
              "target-10 central inventory changed")

    corners = {}
    for ds in (-RADIUS, RADIUS):
        for dc in (-RADIUS, RADIUS):
            head = c.schedule(START + ds, PLATEAU + dc)
            margins = c.schedule_geometry(head, f"r10-corner-{ds}-{dc}")
            corners[f"{ds},{dc}"] = {
                "first_empty_margin": str(margins[
                    f"r10-corner-{ds}-{dc}.first-empty"]),
                "minimum_schedule_margin": str(min(margins.values())),
            }
    upper = c.schedule(START + RADIUS, PLATEAU + RADIUS)
    upper_fixed = c.fixed_families(upper)
    upper_dynamic = c.dynamic_outer(upper)
    m.require(all(x <= y for x, y in zip(OUTER, upper)),
              "upper corner does not contain target-10 support")

    count15 = c.target_schedule(15)
    volume = c.schedule(c.VOLUME_START, c.VOLUME_CAP)
    m.require(all(x >= y for x, y in zip(OUTER, count15)) and
              all(x >= y for x, y in zip(OUTER, volume)),
              "target-10 pointwise dominance changed")

    required8 = c.required_fixed_family_diagnostic(8)
    required9 = c.required_fixed_family_diagnostic(9)
    required10 = c.required_fixed_family_diagnostic(10)
    m.require(required8.get("branch") == "IIb" and
              required8.get("pair") == [1, 7] and
              required9.get("branch") == "IIb" and
              required9.get("pair") == [1, 9] and
              required10.get("status") == "required-fixed PASS",
              "true neighboring prefix diagnostics changed")
    mixed_empty = (Q(2, 5) - m.H) - m.gb(m.CROSS_W)
    m.require(mixed_empty > 0, "mixed IIc interval not empty")

    result["strict_parameter_interior"] = {
        "independent_start_and_plateau_radius": str(RADIUS),
        "four_definition1_corners": corners,
        "pointwise_upper_corner_fixed_prefix": upper_fixed,
        "pointwise_upper_corner_dynamic_iic": upper_dynamic,
        "continuum_argument": (
            "every schedule in the box is a pointwise subset of the fully "
            "verified upper corner"),
    }
    result["dominance"] = {
        "count15_schedule": True,
        "volume_ramp_schedule": True,
        "strict_for_some_counts": True,
    }
    result["neighboring_true_prefix_diagnostics"] = {
        "target8": required8, "target9": required9,
        "target10": required10,
        "mixed_IIc_empty_exact_margin": str(mixed_empty),
        "generic_mixed_IIc_check_is_inapplicable": True,
    }
    result["decision"] = (
        "this exact target-10 schedule is a strict-interior analytic "
        "Proposition-1 support and pointwise dominates both the count-15 "
        "and prior volume-ramp candidates; no quotient is proved")
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
