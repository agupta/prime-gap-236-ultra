#!/usr/bin/env python3
"""Exact two-dimensional integrator for a support-stratum L,Z basis.

This file is deliberately independent of ``audit_c70.py``.  It reconstructs
the I and J matrices for

    1_{R=r} (L/alpha)^a (Z/alpha)^b,       a+b <= D,

where R is the number of coordinates above delta, L is their sum, and Z is
the sum of the remaining coordinates.  All arithmetic is ``Fraction``
arithmetic.  No quadrature or floating-point decision enters a matrix entry.

The reduction uses the exact densities

    f_r(L) = (L-r*delta)^(r-1)/(r-1)!                         (r>0),
    g_n(Z) = sum_{j<=Z/delta} (-1)^j C(n,j)
             (Z-j*delta)^(n-1)/(n-1)!                       (n>0).

The J matrix is block tridiagonal in R.  On the base region L+Z<=eta,
alpha-eta>=delta makes the small distinguished-coordinate branch polynomial:

    S_{r,a,b}=L^a ((Z+delta)^(b+1)-Z^(b+1))
                / ((b+1) alpha^(a+b)).

For the large branch into stratum r+1, put B=B_{r+1}.  It is

    T_low = Z^b (B^(a+1)-(L+delta)^(a+1))
                 / ((a+1) alpha^(a+b)),       Z<=alpha-B,
    T_high= Z^b ((alpha-Z)^(a+1)-(L+delta)^(a+1))
                 / ((a+1) alpha^(a+b)),       Z>=alpha-B,

on L<=B-delta.  Thus only exact polynomial moments over clipped rectangles
and triangles are required.

Run ``python3 exact_lz_integrator.py --self-test`` for fail-closed low-k hand
tests and an independent fixed-vector contraction test.  ``--build-c722``
builds a requested C722 matrix and writes an exact JSON artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from fractions import Fraction as Q
from functools import lru_cache
from math import comb, factorial
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Tuple


Monomial = Tuple[int, int]  # powers of (L,Z)
Poly = Dict[Monomial, Q]
Label = Tuple[int, int, int]  # (R,a,b)


def qtext(x: Q) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def qparse(x: str | int | Q) -> Q:
    return x if isinstance(x, Q) else Q(x)


def poly_clean(p: Mapping[Monomial, Q]) -> Poly:
    return {m: Q(c) for m, c in p.items() if c}


def poly_add(*ps: Mapping[Monomial, Q]) -> Poly:
    out: Poly = {}
    for p in ps:
        for m, c in p.items():
            out[m] = out.get(m, Q(0)) + c
    return poly_clean(out)


def poly_scale(p: Mapping[Monomial, Q], c: Q) -> Poly:
    return poly_clean({m: c * v for m, v in p.items()})


def poly_mul(p: Mapping[Monomial, Q], q: Mapping[Monomial, Q]) -> Poly:
    out: Poly = {}
    for (i, j), a in p.items():
        for (u, v), b in q.items():
            m = (i + u, j + v)
            out[m] = out.get(m, Q(0)) + a * b
    return poly_clean(out)


def poly_pow(p: Mapping[Monomial, Q], n: int) -> Poly:
    if n < 0:
        raise ValueError("negative polynomial exponent")
    ans: Poly = {(0, 0): Q(1)}
    base = dict(p)
    while n:
        if n & 1:
            ans = poly_mul(ans, base)
        n //= 2
        if n:
            base = poly_mul(base, base)
    return ans


def linear_pow(c0: Q, cL: Q, cZ: Q, n: int) -> Poly:
    return poly_pow({(0, 0): c0, (1, 0): cL, (0, 1): cZ}, n)


def poly_eval_axis(p: Mapping[Monomial, Q], *, L: Q | None = None,
                   Z: Q | None = None) -> Poly:
    """Substitute one or both axes; retained axes keep their usual exponent."""
    out: Poly = {}
    for (i, j), c in p.items():
        if L is not None:
            c *= L ** i
            i = 0
        if Z is not None:
            c *= Z ** j
            j = 0
        out[(i, j)] = out.get((i, j), Q(0)) + c
    return poly_clean(out)


def integrate_power(lo: Q, hi: Q, p: int) -> Q:
    if hi <= lo:
        return Q(0)
    return (hi ** (p + 1) - lo ** (p + 1)) / (p + 1)


@dataclass(frozen=True)
class LZSupport:
    k: int
    delta: Q
    alpha: Q
    eta: Q
    bounds: Tuple[Q, ...]

    def __post_init__(self) -> None:
        if self.k < 1:
            raise ValueError("k must be positive")
        if not (0 < self.delta <= self.alpha):
            raise ValueError("require 0<delta<=alpha")
        if not (0 <= self.eta <= self.alpha):
            raise ValueError("require 0<=eta<=alpha")
        if self.alpha - self.eta < self.delta:
            raise ValueError(
                "the polynomial S formula requires alpha-eta>=delta")
        if len(self.bounds) < self.k:
            raise ValueError("bounds must contain B_1,...,B_k")
        if any(b <= self.delta for b in self.bounds):
            raise ValueError("every supplied B_r must exceed delta")

    def bound(self, r: int) -> Q:
        if not 1 <= r <= len(self.bounds):
            raise IndexError(r)
        return self.bounds[r - 1]

    def active_strata(self) -> Tuple[int, ...]:
        ans = [0]
        for r in range(1, self.k + 1):
            if r * self.delta <= min(self.alpha, self.bound(r)):
                ans.append(r)
        return tuple(ans)


class ExactMoments:
    """Cached exact moments against the L,Z stratum densities."""

    def __init__(self, support: LZSupport):
        self.s = support

    @lru_cache(maxsize=None)
    def large_density(self, r: int) -> Tuple[Tuple[Monomial, Q], ...]:
        if r <= 0:
            raise ValueError("r=0 is a delta mass")
        p = poly_scale(
            linear_pow(-r * self.s.delta, Q(1), Q(0), r - 1),
            Q(1, factorial(r - 1)),
        )
        return tuple(sorted(p.items()))

    @lru_cache(maxsize=None)
    def small_density_piece(self, n: int, h: int) -> Tuple[Tuple[Monomial, Q], ...]:
        """Polynomial density on h*delta < Z < (h+1)*delta."""
        if n <= 0:
            raise ValueError("n=0 is a delta mass")
        h = min(h, n - 1)
        out: Poly = {}
        for j in range(h + 1):
            term = linear_pow(-j * self.s.delta, Q(0), Q(1), n - 1)
            term = poly_scale(term, Q((-1) ** j * comb(n, j), factorial(n - 1)))
            out = poly_add(out, term)
        return tuple(sorted(out.items()))

    @staticmethod
    def _integrate_rect_monomial(i: int, j: int, llo: Q, lhi: Q,
                                 zlo: Q, zhi: Q) -> Q:
        return integrate_power(llo, lhi, i) * integrate_power(zlo, zhi, j)

    @staticmethod
    def _integrate_triangle_monomial(i: int, j: int, llo: Q,
                                     total: Q, zlo: Q, zhi: Q) -> Q:
        """Integral of L^i Z^j, llo<=L<=total-Z, zlo<=Z<=zhi."""
        ans = Q(0)
        # Integral in L gives ((total-Z)^(i+1)-llo^(i+1))/(i+1).
        for v in range(i + 2):
            ans += (Q((-1) ** v * comb(i + 1, v)) *
                    total ** (i + 1 - v) *
                    integrate_power(zlo, zhi, j + v) / (i + 1))
        ans -= (llo ** (i + 1) * integrate_power(zlo, zhi, j) /
                (i + 1))
        return ans

    @lru_cache(maxsize=None)
    def moment_expanded_density(self, dim: int, r: int, cap: Q, total: Q,
                                zlo: Q, zhi: Q, ipow: int, jpow: int) -> Q:
        """Reference implementation using piecewise expanded densities.

        This slower implementation is retained as an independent regression
        oracle for low dimensions.  Production calls use ``moment`` below,
        which shifts the integration variables before expansion.
        """
        if not (0 <= r <= dim) or ipow < 0 or jpow < 0:
            raise ValueError("invalid moment indices")
        n = dim - r
        d = self.s.delta
        zlo = max(Q(0), zlo)

        # Both densities are point masses.
        if r == 0 and n == 0:
            if cap < 0 or total < 0 or not (zlo <= 0 <= zhi):
                return Q(0)
            return Q(1) if ipow == 0 and jpow == 0 else Q(0)

        # L=0 point mass, leaving a one-dimensional small-box density.
        if r == 0:
            if cap < 0 or ipow:
                return Q(0)
            hi = min(zhi, n * d, total)
            if hi <= zlo:
                return Q(0)
            ans = Q(0)
            points = {zlo, hi}
            points.update(j * d for j in range(1, n) if zlo < j * d < hi)
            pts = sorted(points)
            for a, b in zip(pts, pts[1:]):
                h = min(int(a // d), n - 1)
                dens = dict(self.small_density_piece(n, h))
                for (_, zdeg), c in dens.items():
                    ans += c * integrate_power(a, b, jpow + zdeg)
            return ans

        llo = r * d

        # Z=0 point mass, leaving a one-dimensional shifted-simplex density.
        if n == 0:
            if not (zlo <= 0 <= zhi) or jpow:
                return Q(0)
            hi = min(cap, total)
            if hi <= llo:
                return Q(0)
            ans = Q(0)
            for (ldeg, _), c in self.large_density(r):
                ans += c * integrate_power(llo, hi, ipow + ldeg)
            return ans

        if cap <= llo:
            return Q(0)
        hi = min(zhi, n * d, total - llo)
        if hi <= zlo:
            return Q(0)

        # Split at every density knot and at the rectangle/triangle crossing.
        crossing = total - cap
        points = {zlo, hi}
        points.update(j * d for j in range(1, n) if zlo < j * d < hi)
        if zlo < crossing < hi:
            points.add(crossing)
        pts = sorted(points)
        large = dict(self.large_density(r))
        ans = Q(0)
        for za, zb in zip(pts, pts[1:]):
            if zb <= za:
                continue
            h = min(int(za // d), n - 1)
            small = dict(self.small_density_piece(n, h))
            dens = poly_mul(large, small)
            rectangle = zb <= crossing
            for (ldeg, zdeg), c in dens.items():
                ii, jj = ipow + ldeg, jpow + zdeg
                if rectangle:
                    v = self._integrate_rect_monomial(
                        ii, jj, llo, cap, za, zb)
                else:
                    v = self._integrate_triangle_monomial(
                        ii, jj, llo, total, za, zb)
                ans += c * v
        return ans

    @lru_cache(maxsize=None)
    def moment(self, dim: int, r: int, cap: Q, total: Q,
               zlo: Q, zhi: Q, ipow: int, jpow: int) -> Q:
        """Exact shifted-variable evaluation of a clipped density moment.

        Inclusion--exclusion is applied before polynomial expansion.  For its
        term s put x=L-r*delta and y=Z-s*delta.  The density is then the single
        monomial x^(r-1)y^(n-1), while only the requested low powers L^ipow and
        Z^jpow must be expanded.  This is mathematically identical to
        ``moment_expanded_density`` but dramatically faster for n near 48.
        """
        if not (0 <= r <= dim) or ipow < 0 or jpow < 0:
            raise ValueError("invalid moment indices")
        n = dim - r
        d = self.s.delta
        zlo = max(Q(0), zlo)

        if r == 0 and n == 0:
            if cap < 0 or total < 0 or not (zlo <= 0 <= zhi):
                return Q(0)
            return Q(1) if ipow == 0 and jpow == 0 else Q(0)

        if r == 0:
            if cap < 0 or ipow:
                return Q(0)
            hi = min(zhi, n * d, total)
            if hi <= zlo:
                return Q(0)
            ans = Q(0)
            fact = factorial(n - 1)
            for ss in range(n):
                shift = ss * d
                za = max(zlo, shift)
                if hi <= za:
                    continue
                ya, yb = za - shift, hi - shift
                outer = Q((-1) ** ss * comb(n, ss), fact)
                for v in range(jpow + 1):
                    coeff = Q(comb(jpow, v)) * shift ** (jpow - v)
                    ans += outer * coeff * integrate_power(
                        ya, yb, n - 1 + v)
            return ans

        rd = r * d
        if n == 0:
            if not (zlo <= 0 <= zhi) or jpow:
                return Q(0)
            hi = min(cap, total)
            if hi <= rd:
                return Q(0)
            xmax = hi - rd
            ans = Q(0)
            fact = factorial(r - 1)
            for u in range(ipow + 1):
                coeff = Q(comb(ipow, u)) * rd ** (ipow - u)
                ans += coeff * xmax ** (r + u) / (fact * (r + u))
            return ans

        if cap <= rd:
            return Q(0)
        hi = min(zhi, n * d, total - rd)
        if hi <= zlo:
            return Q(0)

        crossing = total - cap
        xmax = cap - rd
        denom = factorial(r - 1) * factorial(n - 1)
        ans = Q(0)
        for ss in range(n):
            shift = ss * d
            za = max(zlo, shift)
            if hi <= za:
                continue
            outer = Q((-1) ** ss * comb(n, ss), denom)
            # Coefficients after L=x+rd and Z=y+shift.
            lexp = tuple((u, Q(comb(ipow, u)) * rd ** (ipow - u))
                         for u in range(ipow + 1))
            zexp = tuple((v, Q(comb(jpow, v)) * shift ** (jpow - v))
                         for v in range(jpow + 1))

            # Rectangle portion: x ranges independently over [0,xmax].
            rb = min(hi, crossing)
            if za < rb:
                ya, yb = za - shift, rb - shift
                for u, cu in lexp:
                    xmoment = xmax ** (r + u) / (r + u)
                    for v, cv in zexp:
                        ans += (outer * cu * cv * xmoment *
                                integrate_power(ya, yb, n - 1 + v))

            # Triangle portion: 0<=x<=H-y.
            ta = max(za, crossing)
            if ta < hi:
                ya, yb = ta - shift, hi - shift
                H = total - rd - shift
                for u, cu in lexp:
                    power = r + u
                    for v, cv in zexp:
                        subtotal = Q(0)
                        for w in range(power + 1):
                            subtotal += (Q((-1) ** w * comb(power, w)) *
                                         H ** (power - w) *
                                         integrate_power(
                                             ya, yb, n - 1 + v + w) /
                                         power)
                        ans += outer * cu * cv * subtotal
        return ans

    def integrate(self, p: Mapping[Monomial, Q], dim: int, r: int,
                  cap: Q, total: Q, zlo: Q = Q(0),
                  zhi: Q | None = None) -> Q:
        if zhi is None:
            zhi = total
        return sum(c * self.moment(dim, r, cap, total, zlo, zhi, i, j)
                   for (i, j), c in p.items())


def labels_for(s: LZSupport, degree: int) -> Tuple[Label, ...]:
    if degree < 0:
        raise ValueError("negative degree")
    return tuple((r, a, b) for r in s.active_strata()
                 for a in range(degree + 1)
                 for b in range(degree + 1 - a))


class LZMatrixBuilder:
    def __init__(self, support: LZSupport, degree: int):
        self.s = support
        self.degree = degree
        self.labels = labels_for(support, degree)
        self.mom = ExactMoments(support)

    @lru_cache(maxsize=None)
    def basis_poly(self, a: int, b: int) -> Tuple[Tuple[Monomial, Q], ...]:
        return (((a, b), Q(1, 1) / self.s.alpha ** (a + b)),)

    @lru_cache(maxsize=None)
    def small_inner(self, a: int, b: int) -> Tuple[Tuple[Monomial, Q], ...]:
        upper = linear_pow(self.s.delta, Q(0), Q(1), b + 1)
        lower = {(0, b + 1): Q(1)}
        p = poly_add(upper, poly_scale(lower, Q(-1)))
        p = poly_mul({(a, 0): Q(1)}, p)
        p = poly_scale(p, Q(1, b + 1) / self.s.alpha ** (a + b))
        return tuple(sorted(p.items()))

    @lru_cache(maxsize=None)
    def large_inner(self, a: int, b: int, target_r: int,
                    side: str) -> Tuple[Tuple[Monomial, Q], ...]:
        B = self.s.bound(target_r)
        lower = linear_pow(self.s.delta, Q(1), Q(0), a + 1)
        if side == "low":
            upper: Poly = {(0, 0): B ** (a + 1)}
        elif side == "high":
            upper = linear_pow(self.s.alpha, Q(0), Q(-1), a + 1)
        else:
            raise ValueError(side)
        p = poly_add(upper, poly_scale(lower, Q(-1)))
        p = poly_mul({(0, b): Q(1)}, p)
        p = poly_scale(p, Q(1, a + 1) / self.s.alpha ** (a + b))
        return tuple(sorted(p.items()))

    def _scap(self, r: int) -> Q:
        return self.s.eta if r == 0 else min(self.s.eta, self.s.bound(r))

    def _tcap(self, target_r: int) -> Q:
        return min(self.s.eta, self.s.bound(target_r) - self.s.delta)

    def _split_integral(self, p_low: Mapping[Monomial, Q],
                        p_high: Mapping[Monomial, Q], dim: int, r: int,
                        cap: Q, target_r: int) -> Q:
        z0 = self.s.alpha - self.s.bound(target_r)
        return (self.mom.integrate(p_low, dim, r, cap, self.s.eta,
                                   Q(0), z0) +
                self.mom.integrate(p_high, dim, r, cap, self.s.eta,
                                   max(Q(0), z0), self.s.eta))

    @lru_cache(maxsize=None)
    def i_entry(self, x: Label, y: Label) -> Q:
        rx, ax, bx = x
        ry, ay, by = y
        if rx != ry:
            return Q(0)
        p = poly_mul(dict(self.basis_poly(ax, bx)),
                     dict(self.basis_poly(ay, by)))
        cap = self.s.alpha if rx == 0 else min(self.s.alpha, self.s.bound(rx))
        return Q(comb(self.s.k, rx)) * self.mom.integrate(
            p, self.s.k, rx, cap, self.s.alpha)

    @lru_cache(maxsize=None)
    def j_entry(self, x: Label, y: Label) -> Q:
        rx, ax, bx = x
        ry, ay, by = y
        if abs(rx - ry) > 1:
            return Q(0)
        # Put the lower stratum on the left.  This also canonicalizes cache use.
        if rx > ry:
            return self.j_entry(y, x)
        dim = self.s.k - 1
        ans = Q(0)
        if rx == ry:
            # Both distinguished coordinates are small; common stratum rx.
            if rx <= dim:
                ss = poly_mul(dict(self.small_inner(ax, bx)),
                              dict(self.small_inner(ay, by)))
                ans += Q(comb(dim, rx)) * self.mom.integrate(
                    ss, dim, rx, self._scap(rx), self.s.eta)
            # Both are large; common stratum rx-1.
            if rx >= 1:
                r = rx - 1
                low = poly_mul(dict(self.large_inner(ax, bx, rx, "low")),
                               dict(self.large_inner(ay, by, rx, "low")))
                high = poly_mul(dict(self.large_inner(ax, bx, rx, "high")),
                                dict(self.large_inner(ay, by, rx, "high")))
                ans += Q(comb(dim, r)) * self._split_integral(
                    low, high, dim, r, self._tcap(rx), rx)
            return ans

        # Adjacent target strata rx,rx+1: small branch times large branch.
        assert ry == rx + 1
        if rx > dim:
            return Q(0)
        S = dict(self.small_inner(ax, bx))
        Tlo = dict(self.large_inner(ay, by, ry, "low"))
        Thi = dict(self.large_inner(ay, by, ry, "high"))
        cap = min(self._scap(rx), self._tcap(ry))
        ans += Q(comb(dim, rx)) * self._split_integral(
            poly_mul(S, Tlo), poly_mul(S, Thi), dim, rx, cap, ry)
        return ans

    def matrices(self) -> Tuple[list[list[Q]], list[list[Q]]]:
        n = len(self.labels)
        I = [[Q(0) for _ in range(n)] for _ in range(n)]
        J = [[Q(0) for _ in range(n)] for _ in range(n)]
        for i, x in enumerate(self.labels):
            for j in range(i + 1):
                y = self.labels[j]
                if x[0] == y[0]:
                    I[i][j] = I[j][i] = self.i_entry(x, y)
                if abs(x[0] - y[0]) <= 1:
                    J[i][j] = J[j][i] = self.j_entry(x, y)
        return I, J

    @staticmethod
    def quadratic(M: Sequence[Sequence[Q]], c: Sequence[Q]) -> Q:
        if len(M) != len(c) or any(len(row) != len(c) for row in M):
            raise ValueError("matrix/vector dimension mismatch")
        return sum(c[i] * M[i][j] * c[j]
                   for i in range(len(c)) for j in range(len(c)))

    def direct_fixed_vector(self, c: Sequence[Q]) -> Tuple[Q, Q]:
        """Independently assemble F_R and inner marginals before squaring.

        This deliberately does not call ``i_entry`` or ``j_entry``.  Equality
        with matrix contraction catches block factors, off-diagonal factors,
        branch assignments, and label-order errors.
        """
        if len(c) != len(self.labels):
            raise ValueError("coefficient length mismatch")
        by_r: dict[int, list[Tuple[int, int, Q]]] = {}
        for coeff, (r, a, b) in zip(c, self.labels):
            if coeff:
                by_r.setdefault(r, []).append((a, b, coeff))

        If = Q(0)
        for r, terms in by_r.items():
            F: Poly = {}
            for a, b, coeff in terms:
                F = poly_add(F, poly_scale(dict(self.basis_poly(a, b)), coeff))
            cap = self.s.alpha if r == 0 else min(self.s.alpha, self.s.bound(r))
            If += Q(comb(self.s.k, r)) * self.mom.integrate(
                poly_mul(F, F), self.s.k, r, cap, self.s.alpha)

        Jf = Q(0)
        dim = self.s.k - 1
        maxr = max(by_r, default=0)
        # A common stratum lives in k-1 coordinates, so r never exceeds dim.
        # (The full stratum k can still enter through its large branch at
        # common r=k-1.)
        for r in range(min(maxr, dim) + 1):
            S: Poly = {}
            for a, b, coeff in by_r.get(r, ()):
                S = poly_add(S, poly_scale(dict(self.small_inner(a, b)), coeff))
            Tlo: Poly = {}
            Thi: Poly = {}
            for a, b, coeff in by_r.get(r + 1, ()):
                Tlo = poly_add(
                    Tlo, poly_scale(dict(self.large_inner(a, b, r + 1, "low")), coeff))
                Thi = poly_add(
                    Thi, poly_scale(dict(self.large_inner(a, b, r + 1, "high")), coeff))
            piece = Q(0)
            if S:
                piece += self.mom.integrate(
                    poly_mul(S, S), dim, r, self._scap(r), self.s.eta)
            if Tlo or Thi:
                piece += self._split_integral(
                    poly_mul(Tlo, Tlo), poly_mul(Thi, Thi),
                    dim, r, self._tcap(r + 1), r + 1)
            if S and (Tlo or Thi):
                cap = min(self._scap(r), self._tcap(r + 1))
                piece += 2 * self._split_integral(
                    poly_mul(S, Tlo), poly_mul(S, Thi),
                    dim, r, cap, r + 1)
            Jf += Q(comb(dim, r)) * piece
        return If, Jf


def c722_support(k: int = 48) -> LZSupport:
    """C722, epsilon=1/250, with the audited prefix schedule."""
    listed = (
        Q(7393, 50000), Q(7443, 50000), Q(7493, 50000), Q(7543, 50000),
        Q(7593, 50000), Q(7643, 50000), Q(7693, 50000), Q(7743, 50000),
        Q(7793, 50000), Q(7843, 50000), Q(7893, 50000), Q(7943, 50000),
        Q(7993, 50000), Q(8043, 50000), Q(8093, 50000), Q(8143, 50000),
        Q(8193, 50000), Q(8243, 50000), Q(8293, 50000), Q(2087, 12500),
        Q(8403, 50000), Q(4229, 25000), Q(17127, 100000), Q(8669, 50000),
        Q(18049, 100000), Q(18771, 100000), Q(19493, 100000), Q(4043, 20000),
    )
    if k <= len(listed):
        bounds = listed[:k]
    else:
        bounds = listed + (listed[-1],) * (k - len(listed))
    return LZSupport(k, Q(361, 50000), Q(3169, 12000),
                     Q(3073, 12000), bounds)


def _hand_k1_test() -> None:
    d, alpha, eta, B = Q(1, 10), Q(1), Q(9, 10), Q(2, 5)
    s = LZSupport(1, d, alpha, eta, (B,))
    b = LZMatrixBuilder(s, 2)
    I, J = b.matrices()
    for i, (ri, ai, bi) in enumerate(b.labels):
        for j, (rj, aj, bj) in enumerate(b.labels):
            if ri != rj:
                ie = Q(0)
            elif ri == 0:
                ie = (integrate_power(Q(0), d, bi + bj) if ai + aj == 0
                      else Q(0))
            else:
                ie = (integrate_power(d, B, ai + aj) if bi + bj == 0
                      else Q(0))
            if I[i][j] != ie:
                raise AssertionError(("k1 I", b.labels[i], b.labels[j], I[i][j], ie))

            def inner(label: Label) -> Q:
                r, a, bb = label
                if r == 0:
                    return (d ** (bb + 1) / (bb + 1) if a == 0 else Q(0))
                return (integrate_power(d, B, a) if bb == 0 else Q(0))

            je = inner(b.labels[i]) * inner(b.labels[j])
            if J[i][j] != je:
                raise AssertionError(("k1 J", b.labels[i], b.labels[j], J[i][j], je))


def _density_implementation_test() -> None:
    """Compare the two algebraically independent density-moment algorithms."""
    s = LZSupport(6, Q(1, 10), Q(1), Q(9, 10), (Q(2, 5),) * 6)
    m = ExactMoments(s)
    domains = (
        # cap crossing is internal in the first domain and external in others.
        (Q(2, 5), Q(3, 4), Q(0), Q(3, 5)),
        (Q(4, 5), Q(3, 4), Q(1, 20), Q(7, 10)),
        (Q(7, 20), Q(4, 5), Q(3, 20), Q(11, 20)),
    )
    for dim in range(7):
        for r in range(dim + 1):
            for cap, total, zlo, zhi in domains:
                for i in range(4):
                    for j in range(4 - i):
                        fast = m.moment(dim, r, cap, total, zlo, zhi, i, j)
                        slow = m.moment_expanded_density(
                            dim, r, cap, total, zlo, zhi, i, j)
                        if fast != slow:
                            raise AssertionError((
                                "density algorithms", dim, r, cap, total,
                                zlo, zhi, i, j, fast, slow))


def _hand_k2_d0_test() -> None:
    d, alpha, eta = Q(1, 10), Q(1), Q(9, 10)
    B1, B2 = Q(2, 5), Q(41, 100)
    s = LZSupport(2, d, alpha, eta, (B1, B2))
    b = LZMatrixBuilder(s, 0)
    I, J = b.matrices()
    expected_I = (d * d, 2 * (B1 - d) * d, (B2 - 2 * d) ** 2 / 2)
    if tuple(I[i][i] for i in range(3)) != expected_I:
        raise AssertionError(("k2 I diagonal", tuple(I[i][i] for i in range(3)), expected_I))
    if any(I[i][j] for i in range(3) for j in range(3) if i != j):
        raise AssertionError("k2 I should be stratum block diagonal")

    c = (Q(2), Q(-1), Q(3))
    matrix_j = b.quadratic(J, c)
    # Direct one-variable hand integral over the common coordinate u.
    c0, c1, c2 = c
    hand_j = d * (c0 * d + c1 * (B1 - d)) ** 2
    x = B2 - d
    # On d<=u<=x: c1*d+c2*(B2-d-u), an affine polynomial in u.
    p = {0: c1 * d + c2 * (B2 - d), 1: -c2}
    hand_j += sum(a * bb * integrate_power(d, x, i + j)
                  for i, a in p.items() for j, bb in p.items())
    hand_j += (B1 - x) * (c1 * d) ** 2
    if matrix_j != hand_j:
        raise AssertionError(("k2 J hand", matrix_j, hand_j))


def _fixed_vector_test() -> None:
    # A nontrivial scheduled, clipped case (including both sides of Z=alpha-B)
    # at small k.  Coefficients depend on all label fields and have mixed signs.
    base = c722_support(8)
    b = LZMatrixBuilder(base, 2)
    I, J = b.matrices()
    c = tuple(Q(((-1) ** (r + a)) * (1 + 3 * r + 5 * a + 7 * bb),
                11 + r + a + bb)
              for r, a, bb in b.labels)
    mi, mj = b.quadratic(I, c), b.quadratic(J, c)
    di, dj = b.direct_fixed_vector(c)
    if mi != di or mj != dj:
        raise AssertionError(("fixed vector mismatch", mi, di, mj, dj))


def self_test() -> None:
    _density_implementation_test()
    print("PASS shifted/expanded density moments bitwise (dims 0..6)")
    _hand_k1_test()
    print("PASS k=1 D=2 monomial hand moments")
    _hand_k2_d0_test()
    print("PASS k=2 D=0 geometric I and direct one-variable J")
    _fixed_vector_test()
    print("PASS k=8 D=2 matrix/direct-fixed-vector bitwise equality")


def matrix_json(s: LZSupport, degree: int, labels: Sequence[Label],
                I: Sequence[Sequence[Q]], J: Sequence[Sequence[Q]]) -> dict:
    return {
        "format": "exact-lz-matrices-v1",
        "parameters": {
            "k": s.k, "delta": qtext(s.delta), "alpha": qtext(s.alpha),
            "eta": qtext(s.eta), "bounds": [qtext(x) for x in s.bounds],
            "degree": degree,
        },
        "labels": [list(x) for x in labels],
        "I": [[qtext(x) for x in row] for row in I],
        "J": [[qtext(x) for x in row] for row in J],
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--build-c722", action="store_true")
    ap.add_argument("--degree", type=int, default=2)
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)
    if not args.self_test and not args.build_c722:
        ap.error("choose --self-test and/or --build-c722")
    if args.self_test:
        self_test()
    if args.build_c722:
        s = c722_support(args.k)
        b = LZMatrixBuilder(s, args.degree)
        print(f"building C722 exact matrices: k={args.k} D={args.degree} labels={len(b.labels)}")
        I, J = b.matrices()
        # Deterministic fixed vector comparison on the actual matrix.
        c = tuple(Q(((-1) ** (r + a)) * (1 + 3 * r + 5 * a + 7 * bb),
                    11 + r + a + bb)
                  for r, a, bb in b.labels)
        mi, mj = b.quadratic(I, c), b.quadratic(J, c)
        di, dj = b.direct_fixed_vector(c)
        if (mi, mj) != (di, dj):
            raise AssertionError("actual-matrix fixed-vector comparison failed")
        print("PASS actual matrix/direct-fixed-vector bitwise equality")
        print("fixed I numerator_bits denominator_bits", mi.numerator.bit_length(),
              mi.denominator.bit_length())
        print("fixed J numerator_bits denominator_bits", mj.numerator.bit_length(),
              mj.denominator.bit_length())
        if args.output:
            data = matrix_json(s, args.degree, b.labels, I, J)
            encoded = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(encoded)
            print("wrote", args.output)
            print("sha256", hashlib.sha256(encoded).hexdigest())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
