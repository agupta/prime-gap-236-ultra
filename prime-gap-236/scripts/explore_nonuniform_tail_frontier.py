#!/usr/bin/env python3
"""Greedy exact-grid discovery of a rising outer-cap tail.

The analytically audited first nine caps are fixed, count 10 starts at
3329/20000, and successive suffixes are enlarged subject to Definition 1 and
every fixed packing branch.  A single complete dynamic-IIc check is then run
on the final (largest) support; by support monotonicity this also covers every
intermediate schedule.  This is discovery only and cannot replace an
independent frozen analytic audit.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
AUDIT = REPO / "agents/audit/verify_wide_c722_nonuniform_outer_analytic.py"
AUDIT_SHA = "9265fead8dda30c5b1d4a67907f2faa3926cdb4a1891ea083ec8b37fbc40d726"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


spec = importlib.util.spec_from_file_location("tail_frontier_base", AUDIT)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen analytic audit")
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)
if sha(AUDIT) != AUDIT_SHA:
    raise RuntimeError("frozen analytic audit changed")
m = v.m

FIRST_NINE = v.OUTER[:9]
COUNT10 = Q(3329, 20000)


def replace_suffix(head: tuple[Q, ...], count: int,
                   value: Q) -> tuple[Q, ...]:
    if not 1 <= count <= len(head):
        raise ValueError("suffix count outside serialized head")
    return head[:count - 1] + (value,) * (len(head) - count + 1)


def geometry(head: tuple[Q, ...]) -> dict[str, object]:
    inventory = m.active(head)
    margins: dict[str, Q] = {}
    v._source_schedule_check("candidate", head, inventory, margins)
    return {"active": list(inventory),
            "least_margin": str(min(margins.values()))}


def fixed_ok(head: tuple[Q, ...]) -> bool:
    try:
        geometry(head)
        v.fixed_families(head)
        return True
    except (ArithmeticError, AssertionError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denominator", type=int, default=1_000_000)
    parser.add_argument("--head-length", type=int, default=40)
    parser.add_argument("--last-count", type=int, default=32)
    parser.add_argument("--skip-dynamic-final", action="store_true")
    args = parser.parse_args()
    if args.denominator < 20_000:
        parser.error("denominator must be at least 20000")
    if not 24 <= args.head_length <= 100:
        parser.error("head length must be in [24,100]")
    if not 11 <= args.last_count <= args.head_length:
        parser.error("last count outside [11,head-length]")

    head = FIRST_NINE + (COUNT10,) * (args.head_length - 9)
    if not fixed_ok(head):
        raise ArithmeticError("starting schedule is not fixed-branch feasible")
    started = time.monotonic()
    rows = []
    for count in range(11, args.last_count + 1):
        lower = head[count - 1]
        upper = head[count - 2] + m.DELTA
        denominator = args.denominator
        lo = -((-lower.numerator * denominator) // lower.denominator)
        hi = (upper.numerator * denominator) // upper.denominator
        calls = 0
        while lo < hi:
            mid = (lo + hi + 1) // 2
            calls += 1
            if fixed_ok(replace_suffix(head, count, Q(mid, denominator))):
                lo = mid
            else:
                hi = mid - 1
        head = replace_suffix(head, count, Q(lo, denominator))
        row = {"count": count, "selected": str(Q(lo, denominator)),
               "slope_ceiling": str(upper), "fixed_calls": calls,
               "active": list(m.active(head))}
        rows.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    fixed = v.fixed_families(head)
    final_geometry = geometry(head)
    dynamic = None
    if not args.skip_dynamic_final:
        dynamic = v.dynamic_outer(head)
    result = {
        "format": "nonuniform-rising-tail-frontier-discovery-v1",
        "claim_scope": "exact-grid discovery; independent audit required",
        "script_sha256": sha(FILE),
        "audit_source_sha256": AUDIT_SHA,
        "grid_denominator": args.denominator,
        "head_length": args.head_length,
        "rows": rows,
        "selected_schedule": [str(x) for x in head],
        "geometry": final_geometry,
        "fixed": fixed,
        "dynamic_iic": dynamic,
        "wall_seconds": time.monotonic() - started,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
