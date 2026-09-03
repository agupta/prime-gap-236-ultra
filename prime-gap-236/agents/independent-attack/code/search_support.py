#!/usr/bin/env python3
"""Heuristic adversarial search for the Type-IIc partition condition.

This is deliberately only a falsifier: passing randomized tests is not a proof.
All arithmetic in the final `fits` call is ordinary binary floating point, and
the script labels its output HEURISTIC.  Candidate bounds found here are later
checked by a separate exact grid-cover certificate.
"""

from __future__ import annotations

import argparse
import functools
import random


DELTA = 0.028
WMAX = 0.003
GAMMA_MIN = 0.4
GAMMA_MAX = 1 / 3 + 8 * WMAX + 7 * DELTA / 3


def capacities(gamma: float, omega: float) -> tuple[float, ...]:
    return (
        gamma - 2 * DELTA - 8 * omega,
        0.5 - gamma - 2 * omega,
        4 * omega + DELTA,
        8 * omega,
    )


def fits(items: tuple[float, ...], caps: tuple[float, ...]) -> bool:
    """Exact combinatorial bin-packing decision for the supplied floats."""
    items = tuple(sorted(items, reverse=True))
    caps = tuple(caps)

    @functools.lru_cache(None)
    def rec(i: int, remaining: tuple[float, ...]) -> bool:
        if i == len(items):
            return True
        x = items[i]
        seen = set()
        for j, r in enumerate(remaining):
            # Symmetry prune bins having the same remaining capacity.
            key = round(r, 13)
            if key in seen:
                continue
            seen.add(key)
            if x <= r + 1e-14:
                rr = list(remaining)
                rr[j] = round(r - x, 13)
                if rec(i + 1, tuple(rr)):
                    return True
        return False

    return rec(0, caps)


def random_group(m: int, bound: float) -> tuple[float, ...]:
    """Generate a biased random point in {y_i>=delta, sum y_i<=bound}."""
    slack = bound - m * DELTA
    if slack < 0:
        raise ValueError("empty group")
    # Dirichlet-like random allocation with random unused slack.  Powers bias
    # toward both vertices and balanced points.
    used = slack * random.random() ** random.choice((0.25, 0.5, 1, 2, 4))
    weights = [random.expovariate(random.choice((0.2, 1, 5))) for _ in range(m + 1)]
    scale = used / sum(weights)
    return tuple(DELTA + scale * weights[i] for i in range(m))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bsmall", type=float, default=0.15)
    ap.add_argument("--blarge", type=float, default=0.19)
    ap.add_argument(
        "--bounds",
        help="comma-separated B_1,...,B_R (overrides bsmall/blarge)",
    )
    ap.add_argument("--trials", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=236)
    args = ap.parse_args()
    random.seed(args.seed)
    gamma_grid = [GAMMA_MIN + (GAMMA_MAX - GAMMA_MIN) * i / 8 for i in range(9)]
    omega_grid = [WMAX * i / 8 for i in range(9)]
    bounds = (
        [float(x) for x in args.bounds.split(",")]
        if args.bounds
        else [args.bsmall, args.bsmall] + [args.blarge] * 4
    )
    if not bounds:
        raise SystemExit("--bounds requires at least one value")
    pairs = [
        (m, mp)
        for m in range(0, len(bounds) + 1)
        for mp in range(0, len(bounds) + 1)
        if m + mp > 0
    ]
    for trial in range(args.trials):
        m, mp = random.choice(pairs)
        bm = bounds[m - 1] if m else 0.0
        bmp = bounds[mp - 1] if mp else 0.0
        if m * DELTA > bm or mp * DELTA > bmp:
            continue
        items = (() if m == 0 else random_group(m, bm)) + (
            () if mp == 0 else random_group(mp, bmp)
        )
        for gamma in gamma_grid:
            for omega in omega_grid:
                caps = capacities(gamma, omega)
                if not fits(items, caps):
                    print("HEURISTIC COUNTEREXAMPLE")
                    print("m,mprime", m, mp)
                    print("gamma,omega", repr(gamma), repr(omega))
                    print("caps", caps)
                    print("items", items)
                    print("group sums", sum(items[:m]), sum(items[m:]))
                    return
    print("HEURISTIC PASS", args.trials, "trials", bounds)


if __name__ == "__main__":
    main()
