#!/usr/bin/env python3
"""Heuristic falsifier for the specialized direct-Heath--Brown support.

It checks random Xi tuples against Type IIa, IIb, repaired IIc (omega0>=0),
and corrected Type III bins.  PASS is never a proof.
"""

from __future__ import annotations

import argparse
import random

from search_support import fits


H = 1e-10


def random_group(m: int, bound: float, delta: float) -> tuple[float, ...]:
    slack = bound - m * delta
    if slack < -1e-14:
        raise ValueError("empty group")
    slack = max(0.0, slack)
    used = slack * random.random() ** random.choice((0.2, 0.4, 0.7, 1, 2, 5))
    weights = [random.expovariate(random.choice((0.15, 0.5, 1, 3, 10))) for _ in range(m + 1)]
    scale = used / sum(weights)
    return tuple(delta + scale * weights[i] for i in range(m))


def capacities_iia(w: float, d: float):
    return (0.4 + 4.8 * w + 1.4 * d - 2 * H, 1 / 14 - 24 * w / 7 - 2 * H)


def capacities_iib(w: float, d: float):
    return (
        1 / 3 + 8 * w + 7 * d / 3 - 4 * H,
        0.1 - 6.8 * w - 1.4 * d - 4 * H,
        1 / 35 + 22 * w / 35 + 0.6 * d - 4 * H,
    )


def capacities_iic(gamma: float, omega0: float, d: float):
    return (
        gamma - 2 * d - 8 * omega0 - H,
        0.5 - gamma - 2 * omega0 - H,
        4 * omega0 + d - H,
        8 * omega0,
    )


def capacities_iii(w: float):
    # Corrected Section-3 substitution, conservatively retaining all h loss.
    return (1 - 6 * w - 0.6 - 8 * H / 3, 2.5 * w + 0.15 - 2 * H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delta", type=float, required=True)
    ap.add_argument("--A", type=float, required=True)
    ap.add_argument("--bounds", required=True)
    ap.add_argument("--trials", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=236)
    ap.add_argument("--grid", type=int, default=10)
    args = ap.parse_args()
    random.seed(args.seed)
    d, w = args.delta, args.A - 0.25
    bounds = [float(x) for x in args.bounds.split(",")]
    if d <= 0 or w < 0:
        raise SystemExit("need delta>0 and A>=1/4")
    gmin = 0.4 - H
    gmax = 1 / 3 + 8 * w + 7 * d / 3 + 3 * H
    # Exact scalar conditions, tested conservatively in floats.
    scalar = {
        "II-1": 9.5 - 36 * args.A - 13 * d + 100 * H,
        "II-2a": 0.84 - 3.2 * args.A - 2 * H - d,
        "II-2b": 0.7875 - 3 * args.A - 2 * H - d,
        "III": 0.925 - 3.5 * args.A - 2 * H - d,
    }
    if min(scalar.values()) <= 0:
        print("SCALAR FAIL", scalar)
        raise SystemExit(1)
    fixed = (("IIa", capacities_iia(w, d)), ("IIb", capacities_iib(w, d)), ("III", capacities_iii(w)))
    if min(c for _, caps in fixed for c in caps) < 0:
        print("NEGATIVE CAPACITY", fixed)
        raise SystemExit(1)
    gamma_grid = [gmin + (gmax - gmin) * i / args.grid for i in range(args.grid + 1)] if gmax >= gmin else []
    omega_grid = [w * i / args.grid for i in range(args.grid + 1)]
    pairs = [(m, mp) for m in range(len(bounds) + 1) for mp in range(len(bounds) + 1) if m + mp]
    for trial in range(args.trials):
        m, mp = random.choice(pairs)
        bm = bounds[m - 1] if m else 0.0
        bp = bounds[mp - 1] if mp else 0.0
        if m * d > bm + 1e-14 or mp * d > bp + 1e-14:
            continue
        items = (() if m == 0 else random_group(m, bm, d)) + (() if mp == 0 else random_group(mp, bp, d))
        tests = list(fixed)
        tests.extend((f"IIc(g={g:.12g},o={o:.12g})", capacities_iic(g, o, d)) for g in gamma_grid for o in omega_grid)
        for label, caps in tests:
            if not fits(items, caps):
                print("HEURISTIC COUNTEREXAMPLE", label)
                print("delta,A,w", repr(d), repr(args.A), repr(w))
                print("m,mprime", m, mp)
                print("bounds", bounds)
                print("caps", caps)
                print("items", items)
                print("group sums", sum(items[:m]), sum(items[m:]))
                return
    print("HEURISTIC PASS", args.trials, "delta,A,w", d, args.A, w, "bounds", bounds)


if __name__ == "__main__":
    main()
