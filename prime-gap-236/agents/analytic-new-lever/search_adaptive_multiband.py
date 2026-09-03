#!/usr/bin/env python3
"""Heuristic coordinate search for a cross-compatible multi-band support.

This is discovery code only.  It deliberately calls the existing floating
support oracle and cannot certify any instance of Proposition 1.  Its useful
output is a finite portfolio of rationalization targets for a later,
independent exact checker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import search_adaptive_support as one


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("search_adaptive_support.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dynamic_nonempty(delta: float, omega: float) -> bool:
    return (1 / 3 + 8 * omega + 7 * delta / 3 + 3 * one.H >=
            .4 - one.H)


def all_pairs_ok(schedules, endpoints, p, *, quick: bool) -> bool:
    """Apply the one-band sufficient tests to every ordered band pair."""
    inner = (p.alpha1,) * max(1, int(1 / p.delta))
    for schedule, endpoint in zip(schedules, endpoints):
        omega = endpoint / 2
        dynamic = (not quick and dynamic_nonempty(p.delta, omega))
        if not one.family_ok(inner, schedule, omega, p, dynamic=dynamic):
            return False
        if not one.family_ok(schedule, inner, omega, p, dynamic=dynamic):
            return False
    for left, left_endpoint in zip(schedules, endpoints):
        for right, right_endpoint in zip(schedules, endpoints):
            omega = (left_endpoint + right_endpoint) / 2
            dynamic = (not quick and dynamic_nonempty(p.delta, omega))
            if not one.family_ok(left, right, omega, p, dynamic=dynamic):
                return False
            # Preserve the extra outer/outer near-square family in the
            # audited single-band oracle.  This is intentionally an
            # overcheck until a source-level multi-band proof is written.
            dynamic_zero = (not quick and
                            dynamic_nonempty(p.delta, 0.0))
            if not one.family_ok(left, right, 0.0, p,
                                 dynamic=dynamic_zero):
                return False
    return True


def optimize(bands: int, rounds: int):
    delta = 1 / 60
    outer_width = (.03747 - delta) / 3
    p = one.Parameters(delta, outer_width)
    endpoints = tuple(outer_width * (i + 1) / bands
                      for i in range(bands))
    # The endpoint-optimized one-band schedule need not remain feasible for
    # mixed inner/lower-band pairs.  Start from the conservative schedule
    # that passes the entire endpoint range, then enlarge each band only
    # under the joint ordered-pair gate below.
    common = tuple(one.BASE_SCHEDULE)
    schedules = [common for _ in endpoints]
    if not all_pairs_ok(schedules, endpoints, p, quick=False):
        raise ArithmeticError("common schedule failed multi-band baseline")

    order = (8, 7, 9, 6, 10, 5, 11, 4, 3, 2, 1, 12, 13)
    for _ in range(rounds):
        # Lower bands first; each accepted move is checked against all
        # schedules already retained and all future common schedules.
        for band in range(bands):
            for count in order:
                index = count - 1
                if index >= len(schedules[band]):
                    continue

                def trial_ok(amount, quick):
                    trial = list(schedules)
                    trial[band] = one.raise_at(
                        schedules[band], index, amount, delta)
                    return (one.schedule_ok(trial[band], p) and
                            all_pairs_ok(trial, endpoints, p, quick=quick))

                lo, hi = 0.0, .02
                while trial_ok(hi, True) and hi < .16:
                    hi *= 2
                for _step in range(12):
                    mid = (lo + hi) / 2
                    if trial_ok(mid, True):
                        lo = mid
                    else:
                        hi = mid
                fixed_ceiling, lo = lo, 0.0
                for _step in range(8):
                    mid = (lo + fixed_ceiling) / 2
                    if trial_ok(mid, False):
                        lo = mid
                    else:
                        fixed_ceiling = mid
                if lo:
                    schedules[band] = one.raise_at(
                        schedules[band], index, max(0.0, lo - 1e-8), delta)
    if not all_pairs_ok(schedules, endpoints, p, quick=False):
        raise ArithmeticError("final cross-band support screen failed")

    alpha0 = p.alpha1
    rows = []
    total_volume = 0.0
    common_volume = 0.0
    for band, (endpoint, schedule) in enumerate(
            zip(endpoints, schedules), 1):
        alpha1 = p.alpha1 + endpoint
        band_volume = 0.0
        common_band_volume = 0.0
        for count in one.active(schedule, delta):
            cap = 0.0 if count == 0 else schedule[count - 1]
            band_volume += (one.shell_volume(alpha1, delta, count, cap) -
                            one.shell_volume(alpha0, delta, count, cap))
        for count in one.active(common, delta):
            cap = 0.0 if count == 0 else common[count - 1]
            common_band_volume += (
                one.shell_volume(alpha1, delta, count, cap) -
                one.shell_volume(alpha0, delta, count, cap))
        rows.append({
            "band": band,
            "A_endpoint_offset": endpoint,
            "total_interval": [alpha0, alpha1],
            "schedule": list(schedule),
            "active_counts": list(one.active(schedule, delta)),
            "volume": band_volume,
            "common_schedule_volume": common_band_volume,
        })
        total_volume += band_volume
        common_volume += common_band_volume
        alpha0 = alpha1
    return {
        "format": "adaptive-multiband-support-heuristic-v1",
        "status": "HEURISTIC ONLY",
        "rigorous": False,
        "theorem_ready": False,
        "never_implies": ["Proposition 1", "a sieve quotient", "H1<=236"],
        "delta": delta,
        "epsilon": p.epsilon,
        "outer_width": outer_width,
        "bands": bands,
        "rounds": rounds,
        "common_schedule": list(common),
        "rows": rows,
        "total_volume": total_volume,
        "common_schedule_total_volume": common_volume,
        "volume_ratio_to_common": total_volume / common_volume,
        "all_ordered_pair_screen_pass": True,
        "source_sha256": sha256(SOURCE),
        "script_sha256_before_output": sha256(FILE),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bands", type=int, default=4, choices=range(2, 7))
    parser.add_argument("--rounds", type=int, default=1, choices=(1, 2))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    result = optimize(args.bands, args.rounds)
    result["wall_seconds"] = time.monotonic() - started
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is None:
        print(payload.decode("ascii"), end="")
        return
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(payload)
    print(json.dumps({"output": str(target),
                      "output_sha256": hashlib.sha256(payload).hexdigest(),
                      "volume_ratio_to_common":
                          result["volume_ratio_to_common"],
                      "wall_seconds": result["wall_seconds"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
