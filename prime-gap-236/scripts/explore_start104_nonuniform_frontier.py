#!/usr/bin/env python3
"""Exact discovery scan for nonuniform enlargements of the .104/.166 ramp.

For j=1,...,9, add a common x to B_1,...,B_j and leave all later
bounds fixed.  This preserves the maximal-slope transitions inside the
prefix and relaxes the transition from j to j+1.  We binary-search x on a
declared rational grid, first against every fixed packing branch and then
against the complete dynamic-IIc cell cover.

This is a discovery tool, not an analytic certificate: any selected schedule
must be frozen and independently reconstructed by the hostile checker.
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
AUDIT = REPO / "agents/audit/verify_wide_c722_start104_plateau166_analytic.py"
AUDIT_SHA = "faa23bd7370c9c4d1cc00aa3e21577884a2553bca68258f918fca992cf4d111a"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


spec = importlib.util.spec_from_file_location("start104_nonuniform_base", AUDIT)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen analytic audit")
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
if sha(AUDIT) != AUDIT_SHA:
    raise RuntimeError("frozen analytic audit changed")

c = a.c


def shifted_prefix(length: int, amount: Q,
                   base: tuple[Q, ...] | None = None) -> tuple[Q, ...]:
    if not 1 <= length <= 9 or amount < 0:
        raise ValueError("invalid prefix shift")
    base = a.OUTER if base is None else base
    return tuple(value + amount if index < length else value
                 for index, value in enumerate(base))


def fixed_ok(head: tuple[Q, ...]) -> bool:
    try:
        c.schedule_geometry(head, "candidate")
        c.fixed_families(head)
    except (ArithmeticError, AssertionError, ValueError):
        return False
    return True


def dynamic_ok(head: tuple[Q, ...]) -> bool:
    if not fixed_ok(head):
        return False
    try:
        c.dynamic_outer(head)
    except (ArithmeticError, AssertionError, ValueError):
        return False
    return True


def grid_max(length: int, denominator: int, predicate,
             base: tuple[Q, ...] | None = None,
             upper_amount: Q | None = None) -> tuple[int, int]:
    # x cannot exceed the current j/j+1 gap.
    base = a.OUTER if base is None else base
    upper_amount = (base[length] - base[length - 1]
                    if upper_amount is None else upper_amount)
    upper = int(upper_amount * denominator)
    if Q(upper, denominator) > upper_amount:
        upper -= 1
    lo, hi = 0, upper
    calls = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        calls += 1
        if predicate(shifted_prefix(length, Q(mid, denominator), base)):
            lo = mid
        else:
            hi = mid - 1
    return lo, calls


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--denominator", type=int, default=1_000_000)
    ap.add_argument("--skip-dynamic", action="store_true")
    ap.add_argument("--greedy-order", choices=("none", "ascending", "descending"),
                    default="none")
    ap.add_argument("--skip-individual", action="store_true")
    args = ap.parse_args()
    if args.denominator < 50_000:
        ap.error("denominator must be at least 50000")

    started = time.monotonic()
    rows = []
    for length in (() if args.skip_individual else range(1, 10)):
        fixed_tick, fixed_calls = grid_max(length, args.denominator, fixed_ok)
        dynamic_tick = None
        dynamic_calls = 0
        if not args.skip_dynamic:
            # Dynamic feasibility is monotone too, but cannot exceed fixed max.
            dynamic_calls += 1
            if dynamic_ok(shifted_prefix(
                    length, Q(fixed_tick, args.denominator))):
                dynamic_tick = fixed_tick
            else:
                lo, hi = 0, fixed_tick - 1
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    dynamic_calls += 1
                    if dynamic_ok(shifted_prefix(
                            length, Q(mid, args.denominator))):
                        lo = mid
                    else:
                        hi = mid - 1
                dynamic_tick = lo
        tick = fixed_tick if dynamic_tick is None else dynamic_tick
        head = shifted_prefix(length, Q(tick, args.denominator))
        row = {
            "prefix_length": length,
            "fixed_max_shift": str(Q(fixed_tick, args.denominator)),
            "fixed_calls": fixed_calls,
            "dynamic_max_shift": (None if dynamic_tick is None else
                                  str(Q(dynamic_tick, args.denominator))),
            "dynamic_calls": dynamic_calls,
            "selected_schedule": [str(x) for x in head],
        }
        rows.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    greedy = None
    if args.greedy_order != "none":
        base = a.OUTER
        grow_rows = []
        order = (range(1, 9) if args.greedy_order == "ascending" else
                 range(8, 0, -1))
        for length in order:
            fixed_tick, fcalls = grid_max(
                length, args.denominator, fixed_ok, base=base)
            predicate = fixed_ok if args.skip_dynamic else dynamic_ok
            dcalls = 0
            dcalls += 1
            full = shifted_prefix(length, Q(fixed_tick, args.denominator), base)
            if predicate(full):
                selected_tick = fixed_tick
            else:
                lo, hi = 0, fixed_tick - 1
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    dcalls += 1
                    candidate = shifted_prefix(
                        length, Q(mid, args.denominator), base)
                    if predicate(candidate):
                        lo = mid
                    else:
                        hi = mid - 1
                selected_tick = lo
            base = shifted_prefix(
                length, Q(selected_tick, args.denominator), base)
            grow_rows.append({
                "prefix_length": length,
                "selected_shift": str(Q(selected_tick, args.denominator)),
                "fixed_calls": fcalls,
                "final_predicate_calls": dcalls,
                "schedule": [str(x) for x in base],
            })
            print(json.dumps({"greedy": grow_rows[-1]}, sort_keys=True),
                  flush=True)
        greedy = {"order": args.greedy_order, "steps": grow_rows,
                  "schedule": [str(x) for x in base]}

    result = {
        "format": "start104-nonuniform-prefix-frontier-discovery-v1",
        "claim_scope": "exact-grid discovery only; independent analytic audit required",
        "audit_source_sha256": AUDIT_SHA,
        "script_sha256": sha(FILE),
        "grid_denominator": args.denominator,
        "dynamic_checked": not args.skip_dynamic,
        "rows": rows,
        "greedy": greedy,
        "wall_seconds": time.monotonic() - started,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
