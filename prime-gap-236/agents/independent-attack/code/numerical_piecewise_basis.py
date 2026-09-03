#!/usr/bin/env python3
"""Discovery search in a support-stratum-aligned symmetric polynomial basis.

For a point t, let r=#{i:t_i>delta}, L=sum_{t_i>delta}t_i, and
Z=sum_{t_i<=delta}t_i.  The basis consists of

    1_{r=q} (L/U)^a (Z/U)^b,   a+b <= D.

This is a legitimate finite symmetric square-integrable basis, and its matrix
integrals reduce to two dimensions.  The quadrature here is floating point and
therefore discovery-only; an eventual proof would reconstruct the selected
small basis with exact polynomial integration.
"""

from __future__ import annotations

import argparse
import math

import numpy as np

from numerical_sum_basis import (
    Support,
    gauss_interval,
    large_sum_density,
    parse_bounds,
    small_sum_density,
    top_generalized_eigenvalue,
    z_breaks,
)


def labels(strata: int, degree: int):
    return [(q, a, b) for q in range(strata) for a in range(degree + 1) for b in range(degree + 1 - a)]


def feasible_strata(support: Support):
    out = [0]
    for r in range(1, min(support.k, len(support.bounds)) + 1):
        if r * support.delta <= min(support.upper, support.bound(r)) + 1e-15:
            out.append(r)
    return out


def point_values(lval, z, r, labs, upper):
    vals = np.zeros((len(labs), len(z)))
    for i, (q, a, b) in enumerate(labs):
        if q == r:
            vals[i] = (lval / upper) ** a * (z / upper) ** b
    return vals


def primitive_shift(base, lo, hi, exponent):
    base = np.asarray(base)
    lo = np.broadcast_to(lo, base.shape)
    hi = np.broadcast_to(hi, base.shape)
    out = np.zeros_like(base)
    mask = hi > lo
    out[mask] = (
        (base[mask] + hi[mask]) ** (exponent + 1)
        - (base[mask] + lo[mask]) ** (exponent + 1)
    ) / (exponent + 1)
    return out


def inner_values(lval, z, r, labs, support):
    u = lval + z
    room = support.upper - u
    out = np.zeros((len(labs), len(z)))
    small_hi = np.minimum(support.delta, room)
    small_lo = np.zeros_like(z)
    small_ok = r == 0 or lval <= support.bound(r) + 2e-15
    if not small_ok:
        small_hi[:] = -1
    if r + 1 <= len(support.bounds):
        large_hi = np.minimum(room, support.bound(r + 1) - lval)
    else:
        large_hi = np.full_like(z, -1.0)
    large_lo = np.full_like(z, support.delta)

    for i, (q, a, b) in enumerate(labs):
        if q == r:
            integ = primitive_shift(z, small_lo, small_hi, b)
            out[i] += lval**a * integ / support.upper ** (a + b)
        if q == r + 1:
            integ = primitive_shift(
                np.full_like(z, lval), large_lo, large_hi, a
            )
            out[i] += z**b * integ / support.upper ** (a + b)
    return out


def integrate_z(lval, r, nsmall, labs, support, order, kind):
    size = len(labs)
    total_cap = support.upper if kind == "I" else support.base_cut()
    zmax = min(nsmall * support.delta, total_cap - lval)
    if zmax < -1e-15:
        return np.zeros((size, size))
    if nsmall == 0:
        zsets = [(np.array([0.0]), np.array([1.0]))]
    elif zmax <= 0:
        return np.zeros((size, size))
    else:
        extras = (support.upper - lval - support.delta,)
        if r + 1 <= len(support.bounds):
            extras += (support.upper - support.bound(r + 1),)
        pts = z_breaks(zmax, support.delta, extras)
        zsets = []
        for a, b in zip(pts, pts[1:]):
            if b <= a:
                continue
            z, wt = gauss_interval(a, b, order)
            zsets.append((z, wt * small_sum_density(z, nsmall, support.delta)))
    ans = np.zeros((size, size))
    for z, wt in zsets:
        vals = (
            point_values(lval, z, r, labs, support.upper)
            if kind == "I"
            else inner_values(lval, z, r, labs, support)
        )
        ans += (vals * wt) @ vals.T
    return ans


def build_matrix(support, degree, order, kind):
    poss = feasible_strata(support)
    strata = max(poss) + 1
    labs = labels(strata, degree)
    dim = support.k if kind == "I" else support.k - 1
    ans = np.zeros((len(labs), len(labs)))
    maxr = max(poss) if kind == "I" else max(poss)
    for r in range(maxr + 1):
        nsmall = dim - r
        if nsmall < 0:
            continue
        if r == 0:
            block = integrate_z(0.0, r, nsmall, labs, support, order, kind)
        else:
            llo = r * support.delta
            if kind == "I":
                lhi = min(support.upper, support.bound(r))
            else:
                lhi = min(
                    support.base_cut(),
                    max(
                        support.bound(r),
                        support.bound(r + 1) - support.delta
                        if r + 1 <= len(support.bounds)
                        else -math.inf,
                    ),
                )
            if lhi <= llo:
                continue
            lp = [llo, lhi, support.bound(r)]
            total_cap = support.upper if kind == "I" else support.base_cut()
            lp += [total_cap - j * support.delta for j in range(nsmall + 1)]
            lp = sorted(set(round(x, 15) for x in lp if llo <= x <= lhi))
            block = np.zeros_like(ans)
            for a, b in zip(lp, lp[1:]):
                if b <= a:
                    continue
                ls, ws = gauss_interval(a, b, order)
                dens = large_sum_density(ls, r, support.delta)
                for lv, ww, dl in zip(ls, ws, dens):
                    block += ww * dl * integrate_z(
                        float(lv), r, nsmall, labs, support, order, kind
                    )
        ans += math.comb(dim, r) * block
    return (ans + ans.T) / 2, labs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--delta", type=float, default=0.028)
    ap.add_argument("--upper", type=float, default=0.2605)
    ap.add_argument("--jcut", type=float, default=0.2455)
    ap.add_argument(
        "--bounds",
        default="0.15,0.15,0.17,0.17,0.17,0.17,0.17,0.17,0.17",
    )
    ap.add_argument("--degree", type=int, default=3)
    ap.add_argument("--order", type=int, default=16)
    args = ap.parse_args()
    support = Support(
        args.k, args.delta, args.upper, parse_bounds(args.bounds), args.jcut
    )
    I, labs = build_matrix(support, args.degree, args.order, "I")
    J, labs2 = build_matrix(support, args.degree, args.order, "J")
    assert labs == labs2
    q, rank, ivals = top_generalized_eigenvalue(I, J, args.k)
    print("HEURISTIC ONLY")
    print("basis_size rank degree order", len(labs), rank, args.degree, args.order)
    print("quotient", repr(float(q)))
    print("I spectrum extremes", repr(float(ivals[0])), repr(float(ivals[-1])))


if __name__ == "__main__":
    main()
