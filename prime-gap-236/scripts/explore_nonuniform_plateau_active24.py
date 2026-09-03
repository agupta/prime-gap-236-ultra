#!/usr/bin/env python3
"""Exact-grid discovery scan above the count-23 activation threshold.

Keep the independently audited first nine nonuniform outer caps fixed and
replace every later cap by one common plateau.  Definition 1 permits count 23
to become active; the previous certificate deliberately stopped just below
that transition.  This script searches the remaining monotone interval up to
the schedule-slope ceiling B_9+delta.  It is a discovery tool only: any new
endpoint needs a separately frozen hostile analytic audit.
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


spec = importlib.util.spec_from_file_location("active24_discovery_base", AUDIT)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen analytic audit")
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)
if sha(AUDIT) != AUDIT_SHA:
    raise RuntimeError("frozen analytic audit changed")

m = v.m
FIRST_NINE = v.OUTER[:9]
LOWER = Q(3321, 20000)
UPPER = FIRST_NINE[-1] + m.DELTA


def schedule(plateau: Q) -> tuple[Q, ...]:
    # Count 24 is the first empty count throughout the searched interval, so
    # serialize through that count rather than silently truncating at 23.
    return FIRST_NINE + (plateau,) * 15


def geometry(head: tuple[Q, ...]) -> dict[str, object]:
    active = m.active(head)
    margins: dict[str, Q] = {}
    v._source_schedule_check("candidate", head, active, margins)
    return {"active": list(active), "least_margin": str(min(margins.values()))}


def fixed(head: tuple[Q, ...]) -> dict[str, object]:
    return v.fixed_families(head)


def feasible(plateau: Q, include_dynamic: bool) -> tuple[bool, object]:
    head = schedule(plateau)
    try:
        result: dict[str, object] = {
            "plateau": str(plateau),
            "geometry": geometry(head),
            "fixed": fixed(head),
        }
        if include_dynamic:
            result["dynamic_iic"] = v.dynamic_outer(head)
        return True, result
    except (ArithmeticError, AssertionError, ValueError) as exc:
        return False, {"plateau": str(plateau), "failure": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denominator", type=int, default=1_000_000)
    parser.add_argument("--fixed-only", action="store_true")
    args = parser.parse_args()
    if args.denominator < 20_000:
        parser.error("denominator must be at least 20000")

    denominator = args.denominator
    low_tick = -((-LOWER.numerator * denominator) // LOWER.denominator)
    high_tick = (UPPER.numerator * denominator) // UPPER.denominator
    started = time.monotonic()
    probes: list[object] = []

    # Feasibility is downward closed because lowering a cap only shrinks the
    # support.  Binary search includes the active-count discontinuity exactly.
    lo, hi = low_tick, high_tick
    while lo < hi:
        mid = (lo + hi + 1) // 2
        ok, detail = feasible(Q(mid, denominator), not args.fixed_only)
        probes.append(detail)
        print(json.dumps({"ok": ok, "probe": detail}, sort_keys=True),
              flush=True)
        if ok:
            lo = mid
        else:
            hi = mid - 1

    ok, endpoint = feasible(Q(lo, denominator), not args.fixed_only)
    if not ok:
        raise ArithmeticError("lower endpoint unexpectedly infeasible")
    result = {
        "format": "nonuniform-active24-plateau-discovery-v1",
        "claim_scope": "exact-grid discovery; independent audit required",
        "script_sha256": sha(FILE),
        "audit_source_sha256": AUDIT_SHA,
        "grid_denominator": denominator,
        "fixed_only": args.fixed_only,
        "search_interval": [str(LOWER), str(UPPER)],
        "selected_plateau": str(Q(lo, denominator)),
        "selected": endpoint,
        "probe_count": len(probes),
        "wall_seconds": time.monotonic() - started,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
