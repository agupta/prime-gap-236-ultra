#!/usr/bin/env python3
"""Exact total-sum subspace experiment for Stadlmann's one-stratum support.

This is an independent integrator, not a transcription of a matrix dump.  It
computes I and J for F(t_1,...,t_k)=f(t_1+...+t_k), with f a polynomial, by
splitting according to the coordinates above delta and applying exact
inclusion--exclusion to the remaining box constraints.  All integrals are
Fractions.  Floating point is used only to discover a candidate vector; the
reported candidate margin is then recomputed exactly.
"""

from __future__ import annotations

import argparse
import functools
import math
import time
from fractions import Fraction as Q

import numpy as np


Poly = dict[tuple[int, int], Q]  # x^i z^j -> coefficient
Point = tuple[Q, Q]


def p_add(a: Poly, b: Poly, scale: Q = Q(1)) -> Poly:
    out = dict(a)
    for e, c in b.items():
        out[e] = out.get(e, Q(0)) + scale * c
        if not out[e]:
            del out[e]
    return out


def p_mul(a: Poly, b: Poly) -> Poly:
    out: Poly = {}
    for (i, j), c in a.items():
        for (u, v), d in b.items():
            e = (i + u, j + v)
            out[e] = out.get(e, Q(0)) + c * d
    return {e: c for e, c in out.items() if c}


def p_scale(a: Poly, c: Q) -> Poly:
    return {e: c * v for e, v in a.items() if c * v}


def p_pow(a: Poly, n: int) -> Poly:
    out: Poly = {(0, 0): Q(1)}
    base = a
    while n:
        if n & 1:
            out = p_mul(out, base)
        n //= 2
        if n:
            base = p_mul(base, base)
    return out


def linear_poly(c: Q = Q(0), x: Q = Q(0), z: Q = Q(0)) -> Poly:
    out: Poly = {}
    if c:
        out[(0, 0)] = c
    if x:
        out[(1, 0)] = x
    if z:
        out[(0, 1)] = z
    return out


def clip_polygon(poly: list[Point], a: Q, b: Q, c: Q) -> list[Point]:
    """Clip a convex polygon by a*x+b*z <= c, exactly."""
    if not poly:
        return []
    out: list[Point] = []
    prev = poly[-1]
    fp = a * prev[0] + b * prev[1] - c
    for cur in poly:
        fc = a * cur[0] + b * cur[1] - c
        inp, inc = fp <= 0, fc <= 0
        if inp != inc:
            # prev + t(cur-prev), with the affine form equal to zero.
            t = fp / (fp - fc)
            out.append((prev[0] + t * (cur[0] - prev[0]),
                        prev[1] + t * (cur[1] - prev[1])))
        if inc:
            out.append(cur)
        prev, fp = cur, fc
    # Remove consecutive duplicate vertices introduced on boundaries.
    clean: list[Point] = []
    for p in out:
        if not clean or p != clean[-1]:
            clean.append(p)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    return clean


def region_polygon(total_cap: Q, z_cap: Q, extra: list[tuple[Q, Q, Q]]) -> list[Point]:
    """Polygon x,z>=0, x+z<=total_cap, z<=z_cap, plus halfplanes."""
    if total_cap <= 0 or z_cap < 0:
        return []
    zmax = min(total_cap, z_cap)
    if zmax < total_cap:
        poly: list[Point] = [(Q(0), Q(0)), (total_cap, Q(0)),
                             (total_cap - zmax, zmax), (Q(0), zmax)]
    else:
        poly = [(Q(0), Q(0)), (total_cap, Q(0)), (Q(0), total_cap)]
    # This polygon already enforces x+z<=total_cap and z<=zmax.
    for a, b, c in extra:
        poly = clip_polygon(poly, a, b, c)
        if len(poly) < 3:
            return []
    return poly


def affine_power(c: Q, u: Q, v: Q, n: int) -> dict[tuple[int, int], Q]:
    """Expansion of (c+u*s+v*t)^n."""
    out: dict[tuple[int, int], Q] = {}
    for i in range(n + 1):
        for j in range(n - i + 1):
            h = n - i - j
            coeff = Q(math.factorial(n), math.factorial(i) * math.factorial(j) * math.factorial(h))
            coeff *= (u ** i) * (v ** j) * (c ** h)
            if coeff:
                out[(i, j)] = coeff
    return out


@functools.lru_cache(maxsize=None)
def triangle_monomial(p0: Point, p1: Point, p2: Point, ax: int, az: int) -> Q:
    """Integral x^ax z^az over an exactly specified triangle."""
    x0, z0 = p0
    xu, zu = p1[0] - x0, p1[1] - z0
    xv, zv = p2[0] - x0, p2[1] - z0
    det = xu * zv - xv * zu
    if det == 0:
        return Q(0)
    xp = affine_power(x0, xu, xv, ax)
    zp = affine_power(z0, zu, zv, az)
    total = Q(0)
    for (i, j), a in xp.items():
        for (u, v), b in zp.items():
            # Integral s^(i+u)t^(j+v) on s,t>=0, s+t<=1.
            total += a * b * Q(math.factorial(i + u) * math.factorial(j + v),
                               math.factorial(i + j + u + v + 2))
    return abs(det) * total


def polygon_integral(poly: list[Point], f: Poly) -> Q:
    if len(poly) < 3 or not f:
        return Q(0)
    p0 = poly[0]
    out = Q(0)
    for h in range(1, len(poly) - 1):
        p1, p2 = poly[h], poly[h + 1]
        for (i, j), c in f.items():
            out += c * triangle_monomial(p0, p1, p2, i, j)
    return out


def interval_poly_integral(f: Poly, lo: Q, hi: Q) -> Q:
    """Integrate a polynomial using x as its only variable."""
    if hi <= lo:
        return Q(0)
    out = Q(0)
    for (i, j), c in f.items():
        if j:
            raise ValueError("z occurs in a univariate integral")
        out += c * (hi ** (i + 1) - lo ** (i + 1)) / (i + 1)
    return out


class TotalSumIntegrator:
    def __init__(self, k: int = 48, b3: Q = Q(17, 100)) -> None:
        self.k = k
        self.delta = Q(7, 250)
        self.L = Q(521, 2000)       # A_1 + support epsilon
        self.common_cap = Q(491, 2000)  # A_1 - support epsilon in J
        self.b12 = Q(3, 20)
        self.b3 = b3

    def big_cap(self, r: int) -> Q:
        if r <= 0:
            raise ValueError("B_0 is not used")
        return self.b12 if r <= 2 else self.b3

    def i_moment(self, n: int) -> Q:
        k, d, L = self.k, self.delta, self.L
        ans = Q(0)
        # r=0: every coordinate is small.  Inclusion--exclusion removes x_i<=d.
        for j in range(k + 1):
            cap = L - j * d
            if cap <= 0:
                break
            a = j * d
            term = Q(0)
            for h in range(n + 1):
                term += Q(math.comb(n, h)) * (a ** (n - h)) * (cap ** (k + h)) \
                        * Q(1, math.factorial(k - 1) * (k + h))
            ans += ((-1) ** j) * math.comb(k, j) * term

        # r>=1 selected big coordinates; z is their excess sum and x the sum
        # of the unbounded variables left by inclusion--exclusion.
        for r in range(1, k + 1):
            B = self.big_cap(r)
            zcap = B - r * d
            if zcap < 0:
                break
            u = k - r
            for j in range(u + 1):
                cap = L - (r + j) * d
                if cap <= 0:
                    break
                poly = p_pow(linear_poly((r + j) * d, Q(1), Q(1)), n)
                poly = p_mul(poly, {(u - 1, r - 1): Q(1, math.factorial(u - 1) * math.factorial(r - 1))})
                region = region_polygon(cap, zcap, [])
                term = polygon_integral(region, poly)
                ans += math.comb(k, r) * ((-1) ** j) * math.comb(u, j) * term
        return ans

    def h_poly(self, n: int, a: Q, endpoint: str, bnext: Q | None = None,
               j: int = 0, use_z: bool = True) -> Poly:
        zcoef = Q(1) if use_z else Q(0)
        u = linear_poly(a, Q(1), zcoef)
        if endpoint == "total":
            e = linear_poly(self.L)
        elif endpoint == "linear":
            assert bnext is not None
            e = linear_poly(bnext + j * self.delta, Q(1), Q(0))
        elif endpoint == "delta":
            e = linear_poly(a + self.delta, Q(1), zcoef)
        else:
            raise ValueError(endpoint)
        return p_scale(p_add(p_pow(e, n + 1), p_pow(u, n + 1), Q(-1)), Q(1, n + 1))

    def j_entry(self, na: int, nb: int) -> Q:
        k1, d, L, Qcap = self.k - 1, self.delta, self.L, self.common_cap
        ans = Q(0)

        # No common big coordinate: the admissible t-interval is [0, min(.15,L-u)].
        r = 0
        small = k1
        for j in range(small + 1):
            cap = Qcap - j * d
            if cap <= 0:
                break
            a = j * d
            density = {(small - 1, 0): Q(((-1) ** j) * math.comb(small, j), math.factorial(small - 1))}
            split = L - self.b12 - a
            hs_a = self.h_poly(na, a, "linear", self.b12, j, use_z=False)
            hs_b = self.h_poly(nb, a, "linear", self.b12, j, use_z=False)
            ht_a = self.h_poly(na, a, "total", use_z=False)
            ht_b = self.h_poly(nb, a, "total", use_z=False)
            lo, mid, hi = Q(0), min(max(split, Q(0)), cap), cap
            ans += interval_poly_integral(p_mul(density, p_mul(hs_a, hs_b)), lo, mid)
            ans += interval_poly_integral(p_mul(density, p_mul(ht_a, ht_b)), mid, hi)

        # r>=1 common big coordinates.  Each support regime is a convex polygon.
        for r in range(1, k1 + 1):
            bsmall = self.big_cap(r)
            bnext = self.big_cap(r + 1)
            zcap = bsmall - r * d
            if zcap < 0:
                break
            small = k1 - r
            linear_z_cap = bnext - (r + 1) * d
            for j in range(small + 1):
                cap = Qcap - (r + j) * d
                if cap <= 0:
                    break
                a = (r + j) * d
                coeff = Q(math.comb(k1, r) * ((-1) ** j) * math.comb(small, j),
                          math.factorial(r - 1) * math.factorial(small - 1))
                density = {(small - 1, r - 1): coeff}
                htot = p_mul(self.h_poly(na, a, "total"), self.h_poly(nb, a, "total"))
                hlin = p_mul(self.h_poly(na, a, "linear", bnext, j),
                             self.h_poly(nb, a, "linear", bnext, j))
                hdel = p_mul(self.h_poly(na, a, "delta"), self.h_poly(nb, a, "delta"))

                # Linear support U=B_{r+1}-Y (where U>=delta), split by x.
                if linear_z_cap >= 0:
                    zlin = min(zcap, linear_z_cap)
                    xsplit = L - bnext - j * d
                    # support-limited: z<=zlin and x<=xsplit
                    reg = region_polygon(cap, zlin, [(Q(1), Q(0), xsplit)])
                    ans += polygon_integral(reg, p_mul(density, hlin))
                    # total-limited: z<=zlin and x>=xsplit
                    reg = region_polygon(cap, zlin, [(Q(-1), Q(0), -xsplit)])
                    ans += polygon_integral(reg, p_mul(density, htot))

                # Constant support U=delta (where B_{r+1}-Y<=delta), split by x+z.
                zlo = max(Q(0), linear_z_cap)
                if zcap >= zlo:
                    sumsplit = L - (r + j + 1) * d
                    base_extra = [(Q(0), Q(-1), -zlo)]
                    reg = region_polygon(cap, zcap, base_extra + [(Q(1), Q(1), sumsplit)])
                    ans += polygon_integral(reg, p_mul(density, hdel))
                    reg = region_polygon(cap, zcap, base_extra + [(Q(-1), Q(-1), -sumsplit)])
                    ans += polygon_integral(reg, p_mul(density, htot))
        return ans

    def matrices_monomial(self, degree: int) -> tuple[list[list[Q]], list[list[Q]]]:
        moments = [self.i_moment(n) for n in range(2 * degree + 1)]
        I = [[moments[a + b] for b in range(degree + 1)] for a in range(degree + 1)]
        J = [[Q(0) for _ in range(degree + 1)] for _ in range(degree + 1)]
        for a in range(degree + 1):
            for b in range(a + 1):
                J[a][b] = J[b][a] = self.j_entry(a, b)
        return I, J


def transform_scaled_power(M: list[list[Q]], scale: Q) -> list[list[Q]]:
    """From s^i to (s/scale)^i."""
    n = len(M)
    return [[M[i][j] / (scale ** (i + j)) for j in range(n)] for i in range(n)]


def discover_and_certify(k: int, degree: int, denom: int, b3: Q) -> tuple[float, list[int], Q, Q, Q]:
    integ = TotalSumIntegrator(k, b3)
    I0, J0 = integ.matrices_monomial(degree)
    I = transform_scaled_power(I0, integ.L)
    J = transform_scaled_power(J0, integ.L)
    base = float(I[0][0])
    Af = np.array([[float(v) / base for v in row] for row in I], dtype=float)
    Bf = np.array([[float(k * v) / base for v in row] for row in J], dtype=float)
    # Whiten the positive Gram matrix before the symmetric eigenproblem.
    chol = np.linalg.cholesky(Af)
    left = np.linalg.solve(chol, Bf)
    white = np.linalg.solve(chol, left.T).T
    white = (white + white.T) / 2
    vals, vecs = np.linalg.eigh(white)
    y = vecs[:, -1]
    c = np.linalg.solve(chol.T, y)
    c /= np.max(np.abs(c))
    ci = [int(round(x * denom)) for x in c]

    den = Q(0)
    num = Q(0)
    for i, x in enumerate(ci):
        for j, yv in enumerate(ci):
            den += x * yv * I[i][j]
            num += x * yv * k * J[i][j]
    margin = num - den
    return float(vals[-1]), ci, num, den, margin


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--degree", type=int, default=8)
    ap.add_argument("--denom", type=int, default=10**8)
    ap.add_argument("--b3", default="17/100", help="B_m for m>=3, as p/q")
    args = ap.parse_args()
    b3 = Q(args.b3)
    start = time.monotonic()
    eig, vec, num, den, margin = discover_and_certify(args.k, args.degree, args.denom, b3)
    print(f"k={args.k} degree={args.degree} B3plus={b3} basis=(s/L)^0..{args.degree}")
    print(f"heuristic_largest_quotient={eig:.17g}")
    print("integer_vector=" + ",".join(map(str, vec)))
    print(f"exact_numerator={num.numerator}/{num.denominator}")
    print(f"exact_denominator={den.numerator}/{den.denominator}")
    print(f"exact_margin={margin.numerator}/{margin.denominator}")
    print(f"exact_quotient_decimal={float(num / den):.17g}")
    print(f"wall_seconds={time.monotonic()-start:.3f}")


if __name__ == "__main__":
    main()
