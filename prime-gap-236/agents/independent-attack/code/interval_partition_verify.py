#!/usr/bin/env python3
"""Exact branch-and-cover verifier for Proposition 3 Type-IIc partitions.

The continuum in (gamma,omega_0,y_1,...,y_N) is covered by rational boxes.
Within each count block we order the y_i, which loses no cases.  A box is
certified when one fixed bin assignment works for every point in it.  If not,
the widest y interval is bisected.  Parameter rectangles are supplied as an
exact grid and each uses outward (lower) capacity bounds.

PASS is a rigorous finite cover for the repaired omega_0>=0 criterion.  An
UNRESOLVED result is not evidence of failure; it means the cover needs finer
subdivision or a stronger robust-assignment test.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction as Q
import functools
import itertools
import sys


DELTA = Q(7, 250)
H = Q(1, 10**10)
WMAX = Q(3, 1000)
GMIN = Q(2, 5) - H
GMAX = Q(317, 750) + 3 * H


@dataclass(frozen=True)
class GroupBox:
    lower: tuple[Q, ...]
    upper: tuple[Q, ...]
    bound: Q


def initial_group(m: int, bound: Q) -> GroupBox | None:
    if m == 0:
        return GroupBox((), (), Q(0))
    if m * DELTA > bound:
        return None
    lo = tuple(DELTA for _ in range(m))
    # Ordered y_0<=...<=y_{m-1}: i earlier entries cost at least delta,
    # while y_i,...,y_{m-1} are all at least y_i.
    hi = tuple((bound - i * DELTA) / (m - i) for i in range(m))
    return tighten(GroupBox(lo, hi, bound))


def tighten(g: GroupBox) -> GroupBox | None:
    if not g.lower:
        return g
    lo, hi = list(g.lower), list(g.upper)
    m = len(lo)
    changed = True
    while changed:
        changed = False
        for i in range(1, m):
            v = max(lo[i], lo[i - 1])
            if v != lo[i]:
                lo[i] = v
                changed = True
        for i in range(m - 2, -1, -1):
            v = min(hi[i], hi[i + 1])
            if v != hi[i]:
                hi[i] = v
                changed = True
        if any(lo[i] > hi[i] for i in range(m)) or sum(lo) > g.bound:
            return None
        # Group-sum upper bound, enhanced by ordering of the suffix.
        prefix = Q(0)
        for i in range(m):
            v = (g.bound - prefix) / (m - i)
            if v < hi[i]:
                hi[i] = v
                changed = True
            prefix += lo[i]
    return GroupBox(tuple(lo), tuple(hi), g.bound)


def worst_subset_load(g: GroupBox, subset: int) -> Q:
    """Safe maximum of sum_{i in subset} y_i on this group box."""
    if not g.lower or subset == 0:
        return Q(0)
    su = sum(u for i, u in enumerate(g.upper) if (subset >> i) & 1)
    complement_floor = sum(
        l for i, l in enumerate(g.lower) if not ((subset >> i) & 1)
    )
    return min(su, g.bound - complement_floor)


def robust_assignment(groups: tuple[GroupBox, GroupBox], caps: tuple[Q, ...]):
    """Find one assignment valid throughout a y-box, or return None."""
    items = []
    for gi, g in enumerate(groups):
        for i, (lo, hi) in enumerate(zip(g.lower, g.upper)):
            items.append((gi, i, lo, hi))
    items.sort(key=lambda z: (z[3], z[2]), reverse=True)
    masks = [[0, 0] for _ in caps]

    def current_load(bin_index):
        return sum(
            worst_subset_load(groups[gi], masks[bin_index][gi])
            for gi in (0, 1)
        )

    def rec(pos):
        if pos == len(items):
            return tuple(tuple(x) for x in masks)
        gi, i, lo, hi = items[pos]
        # Tightest bins first tends to expose impossible assignments early.
        for b in sorted(range(len(caps)), key=lambda q: caps[q]):
            old = masks[b][gi]
            masks[b][gi] = old | (1 << i)
            if current_load(b) <= caps[b]:
                answer = rec(pos + 1)
                if answer is not None:
                    return answer
            masks[b][gi] = old
        return None

    return rec(0)


class Limit(Exception):
    pass


def cover(groups, caps, state, depth=0):
    state["nodes"] += 1
    if state["nodes"] > state["node_limit"]:
        raise Limit
    if robust_assignment(groups, caps) is not None:
        state["leaves"] += 1
        state["max_depth"] = max(state["max_depth"], depth)
        return True

    choices = []
    for gi, g in enumerate(groups):
        for i, (lo, hi) in enumerate(zip(g.lower, g.upper)):
            choices.append((hi - lo, gi, i))
    width, gi, i = max(choices, default=(Q(0), 0, 0))
    if width <= state["min_width"]:
        state["witness_box"] = groups
        return False
    mid = (groups[gi].lower[i] + groups[gi].upper[i]) / 2
    children = []
    for lower_half in (True, False):
        g = groups[gi]
        lo, hi = list(g.lower), list(g.upper)
        if lower_half:
            hi[i] = mid
        else:
            lo[i] = mid
        childg = tighten(GroupBox(tuple(lo), tuple(hi), g.bound))
        if childg is None:
            continue
        gg = list(groups)
        gg[gi] = childg
        children.append(tuple(gg))
    for child in children:
        if not cover(child, caps, state, depth + 1):
            return False
    return True


def parse_q(text: str) -> Q:
    return Q(text)


def capacities(gl, gu, wl, wu):
    # Outward lower bounds on each affine capacity over the cell.
    return (
        gl - 2 * DELTA - 8 * wu - H,
        Q(1, 2) - gu - 2 * wu - H,
        4 * wl + DELTA - H,
        8 * wl,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--bounds",
        default="3/20,3/20,89/500,1/5,21/100,21/100,21/100",
    )
    ap.add_argument("--gamma-cells", type=int, default=12)
    ap.add_argument("--omega-cells", type=int, default=8)
    ap.add_argument("--node-limit", type=int, default=200000)
    ap.add_argument("--min-width", default="1/1000000")
    ap.add_argument("--pair", help="single m,mprime pair")
    args = ap.parse_args()
    bounds = [parse_q(x) for x in args.bounds.split(",")]
    pairs = (
        [tuple(int(x) for x in args.pair.split(","))]
        if args.pair
        else [(m, mp) for m in range(len(bounds) + 1) for mp in range(m, len(bounds) + 1) if m + mp]
    )
    total_nodes = 0
    for m, mp in pairs:
        bm = Q(0) if m == 0 else bounds[m - 1]
        bmp = Q(0) if mp == 0 else bounds[mp - 1]
        g1, g2 = initial_group(m, bm), initial_group(mp, bmp)
        if g1 is None or g2 is None:
            print("EMPTY", m, mp)
            continue
        for iw in range(args.omega_cells):
            wl = WMAX * iw / args.omega_cells
            wu = WMAX * (iw + 1) / args.omega_cells
            for ig in range(args.gamma_cells):
                gl = GMIN + (GMAX - GMIN) * ig / args.gamma_cells
                gu = GMIN + (GMAX - GMIN) * (ig + 1) / args.gamma_cells
                caps = capacities(gl, gu, wl, wu)
                state = {
                    "nodes": 0,
                    "leaves": 0,
                    "max_depth": 0,
                    "node_limit": args.node_limit,
                    "min_width": parse_q(args.min_width),
                    "witness_box": None,
                }
                try:
                    ok = cover((g1, g2), caps, state)
                except Limit:
                    print("UNRESOLVED NODE LIMIT", m, mp, iw, ig, state, file=sys.stderr)
                    raise SystemExit(2)
                total_nodes += state["nodes"]
                if not ok:
                    print("UNRESOLVED WIDTH", m, mp, iw, ig, state, file=sys.stderr)
                    raise SystemExit(3)
        print("PAIR PASS", m, mp)
    print("EXACT INTERVAL COVER PASS", "total_nodes", total_nodes)


if __name__ == "__main__":
    main()
