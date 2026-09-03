#!/usr/bin/env python3
"""Numerical quotient for symmetric test functions depending only on sum(t_i).

The support is the one-stratum region used in Stadlmann v1, generalized to an
arbitrary list B_r.  Dimension is reduced exactly to the sums L of coordinates
above delta and Z of coordinates below delta.  Gauss--Legendre quadrature is
then used in one or two dimensions.  Results are DISCOVERY-ONLY: convergence
checks are printed, but no floating-point value from this file is a theorem.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import numpy as np
from numpy.polynomial.legendre import leggauss


@dataclass(frozen=True)
class Support:
    k: int
    delta: float
    upper: float
    bounds: tuple[float, ...]  # B_1, B_2, ...; absent indices are irrelevant.
    j_cut: float | None = None

    def bound(self, r: int) -> float:
        if r == 0:
            return math.inf
        return self.bounds[min(r, len(self.bounds)) - 1]

    def base_cut(self) -> float:
        return self.upper if self.j_cut is None else self.j_cut


def gauss_interval(a: float, b: float, order: int):
    x, w = leggauss(order)
    return (a + b) / 2 + (b - a) * x / 2, (b - a) * w / 2


def small_sum_density(z: np.ndarray, n: int, delta: float) -> np.ndarray:
    """Density of the sum of n independent Lebesgue variables on [0,delta]."""
    if n <= 0:
        raise ValueError("delta mass is handled separately")
    # The familiar alternating inclusion--exclusion formula is catastrophically
    # ill-conditioned around the middle of the distribution for n around 48.
    # Evaluate the cardinal B-spline M_n(x) instead, using its positive Cox--de
    # Boor recurrence
    #
    # M_m(x) = x M_{m-1}(x)/(m-1)
    #          + (m-x) M_{m-1}(x-1)/(m-1).
    #
    # The Lebesgue (rather than probability) density is delta^(n-1) M_n(z/delta).
    x = np.asarray(z, dtype=np.float64) / delta
    # vals[j] represents M_m(x-j); all recurrences only request j>=0.
    vals = np.zeros((n + 1, len(x)), dtype=np.float64)
    for j in range(n + 1):
        y = x - j
        vals[j] = ((y >= 0.0) & (y < 1.0)).astype(np.float64)
    for m in range(2, n + 1):
        count = n - m + 1
        shifts = np.arange(count, dtype=np.float64)[:, None]
        y = x[None, :] - shifts
        vals[:count] = (
            y * vals[:count] + (m - y) * vals[1 : count + 1]
        ) / (m - 1)
    ans = delta ** (n - 1) * vals[0]
    if float(np.min(ans)) < -1e-15 * max(float(np.max(ans)), 1e-300):
        raise ArithmeticError("negative cardinal B-spline density")
    return np.maximum(ans, 0.0)


def large_sum_density(lval: np.ndarray, r: int, delta: float) -> np.ndarray:
    if r <= 0:
        raise ValueError("delta mass is handled separately")
    return np.maximum(lval - r * delta, 0.0) ** (r - 1) / math.factorial(r - 1)


def monomial_values(s: np.ndarray, upper: float, degree: int) -> np.ndarray:
    x = s / upper
    return np.vstack([x**d for d in range(degree + 1)])


def integrated_monomials(
    u: np.ndarray, lo: float, hi: np.ndarray, upper: float, degree: int
) -> np.ndarray:
    """Vector of integrals int_lo^hi ((u+t)/upper)^d dt at array u."""
    out = np.zeros((degree + 1, len(u)))
    mask = hi > lo
    if not np.any(mask):
        return out
    uu = u[mask]
    hh = hi[mask]
    for d in range(degree + 1):
        out[d, mask] = ((uu + hh) ** (d + 1) - (uu + lo) ** (d + 1)) / (
            (d + 1) * upper**d
        )
    return out


def inner_vector(
    u: np.ndarray, lval: float, r: int, support: Support, degree: int
) -> np.ndarray:
    """Integrate basis functions in the distinguished coordinate t."""
    ans = np.zeros((degree + 1, len(u)))
    room = support.upper - u
    if r == 0 or lval <= support.bound(r) + 2e-15:
        hi = np.minimum(support.delta, room)
        ans += integrated_monomials(u, 0.0, hi, support.upper, degree)
    if r + 1 <= len(support.bounds):
        hi = np.minimum(room, support.bound(r + 1) - lval)
        ans += integrated_monomials(
            u, support.delta, hi, support.upper, degree
        )
    return ans


def inner_vector_stratified(
    u: np.ndarray,
    lval: float,
    r: int,
    support: Support,
    degree: int,
    strata: int,
) -> np.ndarray:
    """Inner integrals for 1_{number of large coordinates=q} (sum/U)^d."""
    ans = np.zeros((strata * (degree + 1), len(u)))
    room = support.upper - u
    if r < strata and (r == 0 or lval <= support.bound(r) + 2e-15):
        hi = np.minimum(support.delta, room)
        ans[r * (degree + 1) : (r + 1) * (degree + 1)] += integrated_monomials(
            u, 0.0, hi, support.upper, degree
        )
    if r + 1 < strata and r + 1 <= len(support.bounds):
        hi = np.minimum(room, support.bound(r + 1) - lval)
        ans[(r + 1) * (degree + 1) : (r + 2) * (degree + 1)] += integrated_monomials(
            u, support.delta, hi, support.upper, degree
        )
    return ans


def z_breaks(zmax: float, delta: float, extras=()) -> list[float]:
    pts = [0.0, zmax]
    pts += [j * delta for j in range(1, int(zmax / delta) + 1)]
    pts += [x for x in extras if 0 < x < zmax]
    return sorted(set(round(x, 15) for x in pts))


def integrate_over_z(
    lval: float,
    r: int,
    nsmall: int,
    support: Support,
    degree: int,
    order: int,
    kind: str,
) -> np.ndarray:
    total_cap = support.upper if kind == "I" else support.base_cut()
    zmax = min(nsmall * support.delta, total_cap - lval)
    shape = (degree + 1, degree + 1)
    if zmax < -1e-15:
        return np.zeros(shape)
    if nsmall == 0:
        z = np.array([0.0])
        wt = np.array([1.0])
        dens = np.array([1.0])
        return eval_z_nodes(z, wt * dens, lval, r, support, degree, kind)
    if zmax <= 0:
        return np.zeros(shape)
    # Kinks of the t interval occur at room=delta and where the total-sum and
    # large-sum upper bounds exchange order.
    extras = (support.upper - lval - support.delta,)
    if r + 1 <= len(support.bounds):
        extras += (support.upper - support.bound(r + 1),)
    pts = z_breaks(zmax, support.delta, extras)
    ans = np.zeros(shape)
    for a, b in zip(pts, pts[1:]):
        if b <= a:
            continue
        z, wt = gauss_interval(a, b, order)
        dens = small_sum_density(z, nsmall, support.delta)
        ans += eval_z_nodes(z, wt * dens, lval, r, support, degree, kind)
    return ans


def eval_z_nodes(z, weights, lval, r, support, degree, kind):
    u = lval + z
    if kind == "I":
        vals = monomial_values(u, support.upper, degree)
    elif kind == "J":
        vals = inner_vector(u, lval, r, support, degree)
    else:
        raise ValueError(kind)
    return (vals * weights) @ vals.T


def integrate_over_z_stratified(
    lval: float,
    r: int,
    nsmall: int,
    support: Support,
    degree: int,
    strata: int,
    order: int,
) -> np.ndarray:
    zmax = min(nsmall * support.delta, support.base_cut() - lval)
    size = strata * (degree + 1)
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
    for z, weights in zsets:
        u = lval + z
        vals = inner_vector_stratified(u, lval, r, support, degree, strata)
        ans += (vals * weights) @ vals.T
    return ans


def matrices_stratified(
    support: Support, degree: int, order: int
) -> tuple[np.ndarray, np.ndarray]:
    # Include precisely the strata that are not manifestly empty.
    possible = [0]
    for r in range(1, min(support.k, len(support.bounds)) + 1):
        if r * support.delta <= min(support.upper, support.bound(r)) + 1e-15:
            possible.append(r)
    strata = max(possible) + 1
    blockdim = degree + 1
    size = strata * blockdim
    I = np.zeros((size, size))
    J = np.zeros((size, size))

    # I is block diagonal by the number r of large coordinates.
    for r in possible:
        nsmall = support.k - r
        if r == 0:
            block = integrate_over_z(
                0.0, r, nsmall, support, degree, order, "I"
            )
        else:
            llo = r * support.delta
            lhi = min(support.upper, support.bound(r))
            lp = [llo, lhi]
            lp += [support.base_cut() - j * support.delta for j in range(nsmall + 1)]
            lp = sorted(set(round(x, 15) for x in lp if llo <= x <= lhi))
            block = np.zeros((blockdim, blockdim))
            for a, b in zip(lp, lp[1:]):
                if b <= a:
                    continue
                ls, ws = gauss_interval(a, b, order)
                densl = large_sum_density(ls, r, support.delta)
                for lv, ww, dl in zip(ls, ws, densl):
                    block += ww * dl * integrate_over_z(
                        float(lv), r, nsmall, support, degree, order, "I"
                    )
        sl = slice(r * blockdim, (r + 1) * blockdim)
        I[sl, sl] += math.comb(support.k, r) * block

    # For J, r is the number of large base coordinates; integrating t couples
    # full strata r and r+1.
    dim = support.k - 1
    for r in range(strata):
        nsmall = dim - r
        if nsmall < 0:
            continue
        if r == 0:
            block = integrate_over_z_stratified(
                0.0, r, nsmall, support, degree, strata, order
            )
        else:
            llo = r * support.delta
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
            lp += [support.upper - j * support.delta for j in range(nsmall + 1)]
            lp = sorted(set(round(x, 15) for x in lp if llo <= x <= lhi))
            block = np.zeros((size, size))
            for a, b in zip(lp, lp[1:]):
                if b <= a:
                    continue
                ls, ws = gauss_interval(a, b, order)
                densl = large_sum_density(ls, r, support.delta)
                for lv, ww, dl in zip(ls, ws, densl):
                    block += ww * dl * integrate_over_z_stratified(
                        float(lv), r, nsmall, support, degree, strata, order
                    )
        J += math.comb(dim, r) * block
    return (I + I.T) / 2, (J + J.T) / 2


def matrix(support: Support, degree: int, order: int, kind: str) -> np.ndarray:
    dim = support.k if kind == "I" else support.k - 1
    ans = np.zeros((degree + 1, degree + 1))
    maxr = min(dim, len(support.bounds))
    for r in range(maxr + 1):
        nsmall = dim - r
        if r == 0:
            block = integrate_over_z(
                0.0, r, nsmall, support, degree, order, kind
            )
        else:
            llo = r * support.delta
            # A base point can contribute to I only under B_r.  For J it can
            # also contribute with distinguished t>delta under B_{r+1}.
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
            # Split where the small-coordinate sum ceiling crosses multiples
            # of delta, and at B_r where the t<=delta interval switches off.
            lp = [llo, lhi]
            total_cap = support.upper if kind == "I" else support.base_cut()
            lp += [total_cap - j * support.delta for j in range(nsmall + 1)]
            if r <= len(support.bounds):
                lp.append(support.bound(r))
            lp = sorted(set(round(x, 15) for x in lp if llo <= x <= lhi))
            block = np.zeros_like(ans)
            for a, b in zip(lp, lp[1:]):
                if b <= a:
                    continue
                ls, ws = gauss_interval(a, b, order)
                densl = large_sum_density(ls, r, support.delta)
                for lv, ww, dl in zip(ls, ws, densl):
                    block += ww * dl * integrate_over_z(
                        float(lv), r, nsmall, support, degree, order, kind
                    )
        ans += math.comb(dim, r) * block
    return (ans + ans.T) / 2


def top_generalized_eigenvalue(I: np.ndarray, J: np.ndarray, k: int):
    # First normalize every basis vector by its own I norm.  Support-stratum
    # bases have blocks whose physical volumes differ by dozens of orders of
    # magnitude; a single global scale incorrectly deletes legitimate rare
    # strata before the generalized eigensolve.
    diagonal = np.diag(I)
    active = np.isfinite(diagonal) & (diagonal > 0)
    if not np.any(active):
        raise ArithmeticError("denominator matrix has no positive diagonal")
    Ia = I[np.ix_(active, active)]
    Ja = J[np.ix_(active, active)]
    d = np.sqrt(np.diag(Ia))
    Is = Ia / (d[:, None] * d[None, :])
    Js = k * Ja / (d[:, None] * d[None, :])
    vals, vecs = np.linalg.eigh((Is + Is.T) / 2)
    keep = vals > max(vals[-1] * 1e-12, 1e-13)
    w = vecs[:, keep] / np.sqrt(vals[keep])
    op = w.T @ Js @ w
    eig = np.linalg.eigvalsh((op + op.T) / 2)
    return eig[-1], len(eig), vals


def parse_bounds(text: str) -> tuple[float, ...]:
    return tuple(float(x) for x in text.split(","))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--delta", type=float, default=0.028)
    ap.add_argument("--upper", type=float, default=0.2605)
    ap.add_argument("--jcut", type=float, default=0.2455)
    ap.add_argument(
        "--bounds",
        default="0.15,0.15,0.17,0.17,0.17,0.17,0.17,0.17,0.17",
    )
    ap.add_argument("--degree", type=int, default=8)
    ap.add_argument("--order", type=int, default=18)
    ap.add_argument("--stratified", action="store_true")
    args = ap.parse_args()
    support = Support(
        args.k, args.delta, args.upper, parse_bounds(args.bounds), args.jcut
    )
    if args.stratified:
        I, J = matrices_stratified(support, args.degree, args.order)
    else:
        I = matrix(support, args.degree, args.order, "I")
        J = matrix(support, args.degree, args.order, "J")
    q, rank, ivals = top_generalized_eigenvalue(I, J, args.k)
    np.set_printoptions(precision=17)
    print("HEURISTIC ONLY")
    print("k degree order rank", args.k, args.degree, args.order, rank)
    print("quotient", repr(float(q)))
    print("I00 J00 kJ00/I00", I[0, 0], J[0, 0], args.k * J[0, 0] / I[0, 0])
    print("I eigenvalues / max", ivals)


if __name__ == "__main__":
    main()
