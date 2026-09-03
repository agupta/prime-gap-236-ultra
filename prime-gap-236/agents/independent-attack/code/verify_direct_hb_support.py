#!/usr/bin/env python3
"""Exact interval-cover checker for a one-stratum direct-HB support.

Checks Definition 1, specialized Type-II/III scalar inequalities, and every
IIa/IIb/repaired-IIc/corrected-III partition for continuous Xi tuples.
The underlying branch-and-cover routines use only Fraction arithmetic.
"""

from __future__ import annotations

import argparse
import sys
from fractions import Fraction as Q

import interval_partition_verify as iv


H = Q(1, 10**10)
S = H / 10


def frac(text: str) -> Q:
    return Q(text)


def positive(name: str, value: Q):
    if value <= 0:
        raise AssertionError(f"{name} is not strictly positive: {value}")
    print("MARGIN", name, value)


def cap_iia(w: Q, d: Q):
    return (Q(2, 5) + Q(24, 5) * w + Q(7, 5) * d - 2 * H, Q(1, 14) - Q(24, 7) * w - 2 * H)


def cap_iib(w: Q, d: Q):
    return (
        Q(1, 3) + 8 * w + Q(7, 3) * d - 4 * H,
        Q(1, 10) - Q(34, 5) * w - Q(7, 5) * d - 4 * H,
        Q(1, 35) + Q(22, 35) * w + Q(21, 35) * d - 4 * H,
    )


def cap_iii(w: Q):
    gamma3 = Q(1, 2) - (Q(1, 10) + S)
    delta3 = Q(1, 2) - Q(7, 2) * w - Q(9, 8) * gamma3 - H
    # Inward shrink [a+h,b-h] lowers both partition capacities by h.
    return (
        Q(1, 3) + Q(4, 3) * delta3 - Q(4, 3) * w - H,
        Q(1, 6) - delta3 / 3 + Q(4, 3) * w - H,
    ), delta3


def cap_iic_cell(gl: Q, gu: Q, wl: Q, wu: Q, d: Q):
    return (
        gl - 2 * d - 8 * wu - H,
        Q(1, 2) - gu - 2 * wu - H,
        4 * wl + d - H,
        8 * wl,
    )


def check_cover(groups, caps, node_limit: int, min_width: Q, tag: str):
    state = {
        "nodes": 0,
        "leaves": 0,
        "max_depth": 0,
        "node_limit": node_limit,
        "min_width": min_width,
        "witness_box": None,
    }
    try:
        ok = iv.cover(groups, caps, state)
    except iv.Limit as exc:
        raise RuntimeError(f"node limit in {tag}: {state}") from exc
    if not ok:
        raise AssertionError(f"unresolved width in {tag}: {state}")
    return state["nodes"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delta", required=True)
    ap.add_argument("--A", required=True)
    ap.add_argument("--epsilon", default="3/400")
    ap.add_argument("--bounds", required=True)
    ap.add_argument("--gamma-cells", type=int, default=16)
    ap.add_argument("--omega-cells", type=int, default=16)
    ap.add_argument("--node-limit", type=int, default=1000000)
    ap.add_argument("--min-width", default="1/100000000")
    ap.add_argument("--pair")
    args = ap.parse_args()

    d, A, epsilon = frac(args.delta), frac(args.A), frac(args.epsilon)
    bounds = [frac(v) for v in args.bounds.split(",")]
    w = A - Q(1, 4)
    if not d > 0 or not w >= 0:
        raise AssertionError("delta>0 and A>=1/4 required")
    # Install this candidate's exact delta in the independent box routines.
    iv.DELTA = d
    iv.H = H

    # Definition 1.  The supplied final value is extended constantly to
    # floor(1/delta), which proves all omitted transitions too.
    positive("A-1/4 (omega)", w)
    positive("varepsilon", epsilon)
    positive("1/2-varepsilon-A", Q(1, 2) - epsilon - A)
    for i, b in enumerate(bounds):
        positive(f"B{i+1}-delta", b - d)
        if i:
            if not bounds[i - 1] <= b <= bounds[i - 1] + d:
                raise AssertionError(f"Definition 1 transition {i}->{i+1}")

    # Specialized Type-II scalar inequalities and corrected Type III width.
    positive("II scalar 19/2", Q(19, 2) - 36 * A - 13 * d + 100 * H)
    positive("II scalar first min", Q(21, 25) - Q(16, 5) * A - 2 * H - d)
    positive("II scalar second min", Q(63, 80) - 3 * A - 2 * H - d)
    caps3, delta3 = cap_iii(w)
    positive("corrected TypeIII delta3-d", delta3 - d)
    positive("corrected TypeIII distribution", 4 - (28 * w + 9 * (Q(2, 5) - S) + 8 * delta3))
    for label, caps in (("IIa", cap_iia(w, d)), ("IIb", cap_iib(w, d)), ("III", caps3)):
        for j, c in enumerate(caps):
            positive(f"{label} capacity {j+1}", c)

    active = [0]
    for m, b in enumerate(bounds, 1):
        if m * d <= b:
            active.append(m)
    # Constant extension is empty from the first omitted count onward.
    if len(bounds) * d <= bounds[-1]:
        raise AssertionError("bounds list must include the first manifestly empty count")
    pairs = (
        [tuple(int(v) for v in args.pair.split(","))]
        if args.pair
        else [(m, mp) for m in active for mp in active if m <= mp and m + mp]
    )

    gmin = Q(2, 5) - H
    gmax = Q(1, 3) + 8 * w + Q(7, 3) * d + 3 * H
    total_nodes = 0
    min_width = frac(args.min_width)
    for m, mp in pairs:
        bm = Q(0) if m == 0 else bounds[m - 1]
        bp = Q(0) if mp == 0 else bounds[mp - 1]
        g1, g2 = iv.initial_group(m, bm), iv.initial_group(mp, bp)
        assert g1 is not None and g2 is not None
        groups = (g1, g2)
        for label, caps in (("IIa", cap_iia(w, d)), ("IIb", cap_iib(w, d)), ("III", caps3)):
            total_nodes += check_cover(groups, caps, args.node_limit, min_width, f"{label} pair {m},{mp}")
        if gmax >= gmin:
            for iw in range(args.omega_cells):
                wl = w * iw / args.omega_cells
                wu = w * (iw + 1) / args.omega_cells
                for ig in range(args.gamma_cells):
                    gl = gmin + (gmax - gmin) * ig / args.gamma_cells
                    gu = gmin + (gmax - gmin) * (ig + 1) / args.gamma_cells
                    caps = cap_iic_cell(gl, gu, wl, wu, d)
                    total_nodes += check_cover(
                        groups, caps, args.node_limit, min_width,
                        f"IIc pair {m},{mp} cell {iw},{ig}",
                    )
        print("PAIR PASS", m, mp)
    print("DIRECT-HB EXACT SUPPORT COVER PASS", "pairs", len(pairs), "nodes", total_nodes)


if __name__ == "__main__":
    main()
