#!/usr/bin/env python3
"""Exact audit combining the nonuniform caps with plateau 0.16605."""

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
BASE = FILE.with_name("verify_wide_c722_nonuniform_outer_analytic.py")
BASE_SHA = "9265fead8dda30c5b1d4a67907f2faa3926cdb4a1891ea083ec8b37fbc40d726"
BASE_JSON = FILE.with_name("results") / (
    "wide_c722_nonuniform_outer_analytic_audit.json")
BASE_JSON_SHA = (
    "ab782d6c814271380a73fda6bbdeaa0e097c5216856cd64348e569ddf728f473")

spec = importlib.util.spec_from_file_location(
    "nonuniform_plateau16605_base", BASE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen nonuniform analytic verifier")
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)
if v.sha(BASE) != BASE_SHA:
    raise RuntimeError("frozen nonuniform verifier changed")


m = v.m
PLATEAU = Q(3321, 20000)
BOX_RADIUS = Q(1, 200000)
NONUNIFORM_166 = v.OUTER
BASELINE_166 = v.BASELINE
OUTER = NONUNIFORM_166[:9] + (PLATEAU,) * 14
PLATEAU_ONLY = tuple(
    min(Q(13, 125) + (count - 1) * m.DELTA, PLATEAU)
    for count in range(1, 24))


def schedule_heads():
    return v.INNER, OUTER


def box_head(mask: int) -> tuple[Q, ...]:
    first = tuple(OUTER[index] +
                  (BOX_RADIUS if mask & (1 << index) else -BOX_RADIUS)
                  for index in range(9))
    plateau = PLATEAU + (
        BOX_RADIUS if mask & (1 << 9) else -BOX_RADIUS)
    return first + (plateau,) * 14


m.FILE = FILE
m.OUTER_CAP = PLATEAU
m.schedule_heads = schedule_heads
m.PINNED = dict(m.PINNED)
m.PINNED["agents/audit/verify_wide_c722_nonuniform_outer_analytic.py"] = \
    BASE_SHA
m.PINNED[
    "agents/audit/results/wide_c722_nonuniform_outer_analytic_audit.json"
] = BASE_JSON_SHA


def schedule_audit(head: tuple[Q, ...], label: str):
    margins = {}
    v._source_schedule_check(label, head, v.EXPECTED_ACTIVE, margins)
    return {"least_margin": str(min(margins.values())),
            "active": list(m.active(head))}


def build():
    m.require(v.sha(BASE_JSON) == BASE_JSON_SHA,
              "frozen nonuniform audit JSON changed")
    old = v.strict_json(BASE_JSON)
    m.require(old.get("status") == "AUDIT PASS" and
              tuple(Q(x) for x in old["parameters"][
                  "outer_schedule_through_first_empty"]) == NONUNIFORM_166,
              "frozen nonuniform predecessor is malformed")

    result = m.build()
    m.require(result["parameters"]["outer_active"] == list(range(23)) and
              result["fixed_prefix"]["mixed"]["pairs"] == 827 and
              result["fixed_prefix"]["outer"]["pairs"] == 528 and
              result["dynamic_iic"]["checks"] == 135168,
              "combined support inventory changed")

    # Independently reconstruct the plateau-only proposal before comparing it
    # with the combined schedule.
    plateau_geometry = schedule_audit(PLATEAU_ONLY, "plateau-only")
    plateau_fixed = v.fixed_families(PLATEAU_ONLY)
    plateau_dynamic = v.dynamic_outer(PLATEAU_ONLY)
    m.require(plateau_geometry["active"] == list(range(23)) and
              plateau_dynamic["checks"] == 135168,
              "plateau-only reconstruction incomplete")

    gain_old = tuple(a - b for a, b in zip(OUTER, BASELINE_166))
    gain_nonuniform = tuple(a - b for a, b in zip(OUTER, NONUNIFORM_166))
    gain_plateau = tuple(a - b for a, b in zip(OUTER, PLATEAU_ONLY))
    m.require(all(x > 0 for x in gain_old) and
              all(x >= 0 for x in gain_nonuniform) and
              all(x > 0 for x in gain_nonuniform[9:]) and
              all(x >= 0 for x in gain_plateau) and
              all(x > 0 for x in gain_plateau[:9]),
              "combined pointwise dominance changed")

    corner_worst = None
    for mask in range(1 << 10):
        head = box_head(mask)
        margins = {}
        v._source_schedule_check(
            f"box-corner-{mask}", head, v.EXPECTED_ACTIVE, margins)
        item = (min(margins.values()), mask)
        corner_worst = item if corner_worst is None or item < corner_worst \
            else corner_worst
    upper = box_head((1 << 10) - 1)
    upper_fixed = v.fixed_families(upper)
    upper_dynamic = v.dynamic_outer(upper)
    m.require(corner_worst is not None and corner_worst[0] > 0 and
              all(a <= b for a, b in zip(OUTER, upper)),
              "combined strict component box failed")

    mutation1 = list(OUTER)
    mutation1[0] += Q(1, 10000)
    schedule_audit(tuple(mutation1), "hostile-B1")
    failure1 = v.first_fixed_failure(tuple(mutation1))
    mutation9 = list(OUTER)
    mutation9[8] += Q(1, 10000)
    schedule_audit(tuple(mutation9), "hostile-B9")
    failure9 = v.first_fixed_failure(tuple(mutation9))
    m.require(failure1 is not None and
              (failure1["family"], failure1["branch"], failure1["pair"]) ==
              ("mixed", "III", [1, 1]) and
              failure9 is not None and
              (failure9["family"], failure9["branch"], failure9["pair"]) ==
              ("mixed", "IIb", [1, 9]),
              "combined hostile fixtures changed")

    result["schedule_id"] = "nonuniform-outer-plateau16605-v2"
    result["parameters"].update({
        "outer_plateau": str(PLATEAU),
        "outer_schedule_through_first_empty": [str(x) for x in OUTER],
        "outer_schedule_canonical_sha256":
            v.canonical_schedule_hash(OUTER),
    })
    result["independent_plateau_only_reconstruction"] = {
        "schedule": [str(x) for x in PLATEAU_ONLY],
        "geometry": plateau_geometry,
        "fixed_prefix": plateau_fixed,
        "dynamic_iic": plateau_dynamic,
        "mixed_iic_empty_exact_margin":
            str((Q(2, 5) - m.H) - m.gb(m.CROSS_W)),
        "status": "AUDIT PASS",
    }
    result["pointwise_dominance"] = {
        "over_start104_plateau166": [str(x) for x in gain_old],
        "over_nonuniform_plateau166": [str(x) for x in gain_nonuniform],
        "over_start104_plateau16605": [str(x) for x in gain_plateau],
        "strictly_dominates_all_three": True,
    }
    result["strict_component_interior"] = {
        "independent_coordinates": list(range(1, 10)),
        "shared_plateau_counts": list(range(10, 24)),
        "radius_each": str(BOX_RADIUS),
        "definition1_vertices_checked": 1 << 10,
        "worst_vertex": corner_worst[1],
        "worst_vertex_schedule_margin": str(corner_worst[0]),
        "pointwise_upper_corner_fixed_prefix": upper_fixed,
        "pointwise_upper_corner_dynamic_iic": upper_dynamic,
        "continuum_argument": (
            "all affine schedule constraints pass at every box vertex; "
            "each box support is contained in the fully verified upper "
            "corner"),
    }
    result["hostile_mutation_fixtures"] = {
        "B1_plus_1_over_10000": failure1,
        "B9_plus_1_over_10000": failure9,
        "both_mutated_schedules_retain_Definition1_geometry": True,
    }
    result["decision"] = (
        "the exact nonuniform schedule with plateau 3321/20000 is a "
        "strict-interior analytic Proposition-1 support and pointwise "
        "strictly dominates both predecessor enlargements; no quotient is "
        "proved")
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
