#!/usr/bin/env python3
"""Exact candidate enrichment by the first missing symmetric orbit p_2.

The pure L,Z basis cannot see dispersion among coordinates with the same two
sums.  The smallest missing global monomial orbit is

    p2(t) = sum_i t_i^2.

This module supplies exact marked density moments for p2 and p2^2 and the I/J
entries of the concrete tagged family

    H_r = 1_{R=r} p2(t)/alpha^2.

It is intentionally a sibling of, rather than a modification to, the audited
pure-L/Z integrator.  The formulas can be used to rank or append selected H_r
columns after the D4 residual is known.
"""

from __future__ import annotations

from fractions import Fraction as Q
from functools import lru_cache
from math import comb, factorial
from typing import Mapping, Tuple

from exact_lz_integrator import (
    ExactMoments,
    LZMatrixBuilder,
    LZSupport,
    Poly,
    c722_support,
    integrate_power,
    poly_add,
    poly_mul,
    poly_scale,
)


def _add1(out, exponent, coefficient):
    if coefficient:
        out[exponent] = out.get(exponent, Q(0)) + coefficient


class MarkedMoments(ExactMoments):
    """Moments with zero, one, or two insertions of base p2."""

    @lru_cache(maxsize=None)
    def large_mark(self, r: int, order: int):
        """Polynomial in x=L-r*delta on an unbounded r-simplex slice."""
        if r == 0:
            return (((0, Q(1)),) if order == 0 else ())
        if not 0 <= order <= 2:
            raise ValueError(order)
        d = self.s.delta
        out = {}
        if order == 0:
            _add1(out, r - 1, Q(1, factorial(r - 1)))
        elif order == 1:
            _add1(out, r + 1, Q(2 * r, factorial(r + 1)))
            _add1(out, r, Q(2) * d / factorial(r - 1))
            _add1(out, r - 1, Q(r) * d * d / factorial(r - 1))
        else:
            # Q_x^2 + 2(2*d*x+r*d^2)Q_x
            #       +(2*d*x+r*d^2)^2.
            _add1(out, r + 3, Q(4 * r * (r + 5), factorial(r + 3)))
            _add1(out, r + 2, Q(8 * r) * d / factorial(r + 1))
            _add1(out, r + 1, Q(4 * r * r) * d * d / factorial(r + 1))
            _add1(out, r + 1, Q(4) * d * d / factorial(r - 1))
            _add1(out, r, Q(4 * r) * d ** 3 / factorial(r - 1))
            _add1(out, r - 1, Q(r * r) * d ** 4 / factorial(r - 1))
        return tuple(sorted((e, c) for e, c in out.items() if c))

    @lru_cache(maxsize=None)
    def small_mark(self, n: int, ss: int, order: int):
        """IE term polynomial in y=Z-ss*delta, including its IE sign/count."""
        if n == 0:
            if ss != 0:
                return ()
            return (((0, Q(1)),) if order == 0 else ())
        if not (0 <= ss < n) or not 0 <= order <= 2:
            raise ValueError((n, ss, order))
        d = self.s.delta
        out = {}
        if order == 0:
            _add1(out, n - 1, Q(1, factorial(n - 1)))
        elif order == 1:
            _add1(out, n + 1, Q(2 * n, factorial(n + 1)))
            _add1(out, n, Q(2 * ss) * d / factorial(n))
            _add1(out, n - 1, Q(ss) * d * d / factorial(n - 1))
        else:
            _add1(out, n + 3, Q(4 * n * (n + 5), factorial(n + 3)))
            _add1(out, n + 2, Q(8 * ss) * d / factorial(n + 1))
            _add1(out, n + 1,
                  Q(4 * ss * (n + ss + 1)) * d * d / factorial(n + 1))
            _add1(out, n, Q(4 * ss * ss) * d ** 3 / factorial(n))
            _add1(out, n - 1,
                  Q(ss * ss) * d ** 4 / factorial(n - 1))
        ie = Q((-1) ** ss * comb(n, ss))
        return tuple(sorted((e, ie * c) for e, c in out.items() if c))

    def _joint_terms(self, r: int, n: int, ss: int, order: int):
        L = [dict(self.large_mark(r, q)) for q in range(3)]
        S = [dict(self.small_mark(n, ss, q)) for q in range(3)]
        out = {}

        def add_product(q1, q2, multiplier=Q(1)):
            for px, a in L[q1].items():
                for py, b in S[q2].items():
                    key = (px, py)
                    out[key] = out.get(key, Q(0)) + multiplier * a * b

        if order == 0:
            add_product(0, 0)
        elif order == 1:
            add_product(1, 0)
            add_product(0, 1)
        elif order == 2:
            add_product(2, 0)
            add_product(1, 1, Q(2))
            add_product(0, 2)
        else:
            raise ValueError(order)
        return tuple((key, c) for key, c in sorted(out.items()) if c)

    @lru_cache(maxsize=None)
    def marked_moment(self, dim: int, r: int, cap: Q, total: Q,
                      zlo: Q, zhi: Q, ipow: int, jpow: int,
                      order: int) -> Q:
        if not (0 <= r <= dim and 0 <= order <= 2):
            raise ValueError((dim, r, order))
        n, d, rd = dim - r, self.s.delta, r * self.s.delta
        zlo = max(Q(0), zlo)

        if r == 0 and n == 0:
            if cap < 0 or total < 0 or not (zlo <= 0 <= zhi):
                return Q(0)
            return Q(1) if order == ipow == jpow == 0 else Q(0)

        hi = min(zhi, n * d, total - rd)
        if r == 0:
            if cap < 0 or ipow or hi <= zlo:
                return Q(0)
            ans = Q(0)
            for ss in range(n):
                shift = ss * d
                za = max(zlo, shift)
                if hi <= za:
                    continue
                ya, yb = za - shift, hi - shift
                for (px, py), base in self._joint_terms(r, n, ss, order):
                    if px:
                        raise AssertionError("r=0 marked density has x power")
                    for v in range(jpow + 1):
                        coeff = Q(comb(jpow, v)) * shift ** (jpow - v)
                        ans += base * coeff * integrate_power(ya, yb, py + v)
            return ans

        if n == 0:
            if not (zlo <= 0 <= zhi) or jpow:
                return Q(0)
            top = min(cap, total)
            if top <= rd:
                return Q(0)
            xmax, ans = top - rd, Q(0)
            for (px, py), base in self._joint_terms(r, n, 0, order):
                if py:
                    raise AssertionError("n=0 marked density has y power")
                for u in range(ipow + 1):
                    coeff = Q(comb(ipow, u)) * rd ** (ipow - u)
                    ans += base * coeff * xmax ** (px + u + 1) / (px + u + 1)
            return ans

        if cap <= rd or hi <= zlo:
            return Q(0)
        crossing, xmax, ans = total - cap, cap - rd, Q(0)
        for ss in range(n):
            shift = ss * d
            za = max(zlo, shift)
            if hi <= za:
                continue
            lexp = tuple((u, Q(comb(ipow, u)) * rd ** (ipow - u))
                         for u in range(ipow + 1))
            zexp = tuple((v, Q(comb(jpow, v)) * shift ** (jpow - v))
                         for v in range(jpow + 1))
            for (px, py), base in self._joint_terms(r, n, ss, order):
                rb = min(hi, crossing)
                if za < rb:
                    ya, yb = za - shift, rb - shift
                    for u, cu in lexp:
                        xm = xmax ** (px + u + 1) / (px + u + 1)
                        for v, cv in zexp:
                            ans += (base * cu * cv * xm *
                                    integrate_power(ya, yb, py + v))
                ta = max(za, crossing)
                if ta < hi:
                    ya, yb = ta - shift, hi - shift
                    H = total - rd - shift
                    for u, cu in lexp:
                        power = px + u + 1
                        for v, cv in zexp:
                            val = Q(0)
                            for w in range(power + 1):
                                val += (Q((-1) ** w * comb(power, w)) *
                                        H ** (power - w) *
                                        integrate_power(ya, yb, py + v + w) /
                                        power)
                            ans += base * cu * cv * val
        return ans

    def integrate_marked(self, p: Mapping[Tuple[int, int], Q], dim: int,
                         r: int, cap: Q, total: Q, order: int,
                         zlo: Q = Q(0), zhi: Q | None = None) -> Q:
        if zhi is None:
            zhi = total
        return sum(c * self.marked_moment(
            dim, r, cap, total, zlo, zhi, i, j, order)
                   for (i, j), c in p.items())


# A marginal is p0(L,Z)+p1(L,Z)*p2(base).
Marginal = Tuple[Poly, Poly]


class P2Entries:
    """Exact matrix-entry engine for L/Z labels plus H_r tags."""

    def __init__(self, support: LZSupport, degree: int):
        self.s = support
        self.base = LZMatrixBuilder(support, degree)
        self.mom = MarkedMoments(support)

    @staticmethod
    def lz(r, a, b):
        return ("lz", r, a, b)

    @staticmethod
    def p2(r):
        return ("p2", r, 0, 0)

    @staticmethod
    def stratum(label):
        return label[1]

    def _scap(self, r):
        return self.base._scap(r)

    def _tcap(self, target):
        return self.base._tcap(target)

    def small_marginal(self, label) -> Marginal:
        kind, r, a, b = label
        if kind == "lz":
            return dict(self.base.small_inner(a, b)), {}
        scale = self.s.alpha ** 2
        return ({(0, 0): self.s.delta ** 3 / (3 * scale)},
                {(0, 0): self.s.delta / scale})

    def large_marginal(self, label, side: str) -> Marginal:
        kind, r, a, b = label
        if kind == "lz":
            return dict(self.base.large_inner(a, b, r, side)), {}
        B, alpha, d = self.s.bound(r), self.s.alpha, self.s.delta
        if side == "low":
            h = {(0, 0): B, (1, 0): Q(-1)}
        elif side == "high":
            h = {(0, 0): alpha, (1, 0): Q(-1), (0, 1): Q(-1)}
        else:
            raise ValueError(side)
        p1 = poly_scale(poly_add(h, {(0, 0): -d}), Q(1) / alpha ** 2)
        p0 = poly_scale(
            poly_add(poly_mul(poly_mul(h, h), h), {(0, 0): -(d ** 3)}),
            Q(1, 3) / alpha ** 2)
        return p0, p1

    def integrate_pair(self, x: Marginal, y: Marginal, dim: int, r: int,
                       cap: Q, zlo=Q(0), zhi=None) -> Q:
        if zhi is None:
            zhi = self.s.eta
        x0, x1 = x
        y0, y1 = y
        ans = self.mom.integrate_marked(
            poly_mul(x0, y0), dim, r, cap, self.s.eta, 0, zlo, zhi)
        cross = poly_add(poly_mul(x0, y1), poly_mul(x1, y0))
        ans += self.mom.integrate_marked(
            cross, dim, r, cap, self.s.eta, 1, zlo, zhi)
        ans += self.mom.integrate_marked(
            poly_mul(x1, y1), dim, r, cap, self.s.eta, 2, zlo, zhi)
        return ans

    def split_pair(self, lowx, highx, lowy, highy, dim, r, cap, target):
        z0 = self.s.alpha - self.s.bound(target)
        return (self.integrate_pair(lowx, lowy, dim, r, cap, Q(0), z0) +
                self.integrate_pair(highx, highy, dim, r, cap,
                                    max(Q(0), z0), self.s.eta))

    @lru_cache(maxsize=None)
    def i_entry(self, x, y):
        rx, ry = self.stratum(x), self.stratum(y)
        if rx != ry:
            return Q(0)
        def full(label):
            kind, r, a, b = label
            if kind == "lz":
                return dict(self.base.basis_poly(a, b)), {}, 0
            return {}, {(0, 0): Q(1) / self.s.alpha ** 2}, 1
        x0, x1, _ = full(x)
        y0, y1, _ = full(y)
        cap = self.s.alpha if rx == 0 else min(self.s.alpha, self.s.bound(rx))
        ans = self.mom.integrate_marked(
            poly_mul(x0, y0), self.s.k, rx, cap, self.s.alpha, 0)
        ans += self.mom.integrate_marked(
            poly_add(poly_mul(x0, y1), poly_mul(x1, y0)),
            self.s.k, rx, cap, self.s.alpha, 1)
        ans += self.mom.integrate_marked(
            poly_mul(x1, y1), self.s.k, rx, cap, self.s.alpha, 2)
        return Q(comb(self.s.k, rx)) * ans

    @lru_cache(maxsize=None)
    def j_entry(self, x, y):
        rx, ry = self.stratum(x), self.stratum(y)
        if abs(rx - ry) > 1:
            return Q(0)
        if rx > ry:
            return self.j_entry(y, x)
        dim, ans = self.s.k - 1, Q(0)
        if rx == ry:
            if rx <= dim:
                ans += Q(comb(dim, rx)) * self.integrate_pair(
                    self.small_marginal(x), self.small_marginal(y),
                    dim, rx, self._scap(rx))
            if rx >= 1:
                r = rx - 1
                ans += Q(comb(dim, r)) * self.split_pair(
                    self.large_marginal(x, "low"),
                    self.large_marginal(x, "high"),
                    self.large_marginal(y, "low"),
                    self.large_marginal(y, "high"),
                    dim, r, self._tcap(rx), rx)
            return ans
        assert ry == rx + 1
        cap = min(self._scap(rx), self._tcap(ry))
        ans += Q(comb(dim, rx)) * self.split_pair(
            self.small_marginal(x), self.small_marginal(x),
            self.large_marginal(y, "low"), self.large_marginal(y, "high"),
            dim, rx, cap, ry)
        return ans

    @staticmethod
    def _sum_marginals(weighted):
        p0, p1 = {}, {}
        for coeff, (q0, q1) in weighted:
            p0 = poly_add(p0, poly_scale(q0, coeff))
            p1 = poly_add(p1, poly_scale(q1, coeff))
        return p0, p1

    def direct_fixed_vector(self, labels, coeff):
        """Sum amplitudes first, then square; independent of entry assembly."""
        if len(labels) != len(coeff):
            raise ValueError("label/vector mismatch")
        by_r = {}
        for lab, c in zip(labels, coeff):
            if c:
                by_r.setdefault(self.stratum(lab), []).append((lab, c))

        If = Q(0)
        for r, terms in by_r.items():
            f0, f1 = {}, {}
            for lab, c in terms:
                kind, _, a, b = lab
                if kind == "lz":
                    f0 = poly_add(
                        f0, poly_scale(dict(self.base.basis_poly(a, b)), c))
                else:
                    f1 = poly_add(
                        f1, {(0, 0): c / self.s.alpha ** 2})
            cap = self.s.alpha if r == 0 else min(self.s.alpha, self.s.bound(r))
            piece = self.mom.integrate_marked(
                poly_mul(f0, f0), self.s.k, r, cap, self.s.alpha, 0)
            piece += 2 * self.mom.integrate_marked(
                poly_mul(f0, f1), self.s.k, r, cap, self.s.alpha, 1)
            piece += self.mom.integrate_marked(
                poly_mul(f1, f1), self.s.k, r, cap, self.s.alpha, 2)
            If += Q(comb(self.s.k, r)) * piece

        Jf, dim = Q(0), self.s.k - 1
        maxr = min(max(by_r, default=0), dim)
        for r in range(maxr + 1):
            small = self._sum_marginals(
                (c, self.small_marginal(lab))
                for lab, c in by_r.get(r, ()))
            low = self._sum_marginals(
                (c, self.large_marginal(lab, "low"))
                for lab, c in by_r.get(r + 1, ()))
            high = self._sum_marginals(
                (c, self.large_marginal(lab, "high"))
                for lab, c in by_r.get(r + 1, ()))
            piece = Q(0)
            if small != ({}, {}):
                piece += self.integrate_pair(
                    small, small, dim, r, self._scap(r))
            if low != ({}, {}) or high != ({}, {}):
                piece += self.split_pair(
                    low, high, low, high, dim, r,
                    self._tcap(r + 1), r + 1)
            if ((small != ({}, {})) and
                    (low != ({}, {}) or high != ({}, {}))):
                piece += 2 * self.split_pair(
                    small, small, low, high, dim, r,
                    min(self._scap(r), self._tcap(r + 1)), r + 1)
            Jf += Q(comb(dim, r)) * piece
        return If, Jf


def self_test():
    s = LZSupport(4, Q(1, 10), Q(1), Q(9, 10), (Q(2, 5),) * 4)
    marked, plain = MarkedMoments(s), ExactMoments(s)
    # Mark order zero must reproduce the separately implemented plain moments.
    for dim in range(5):
        for r in range(dim + 1):
            for i in range(3):
                for j in range(3 - i):
                    a = marked.marked_moment(
                        dim, r, Q(2, 5), Q(3, 4), Q(0), Q(7, 10), i, j, 0)
                    b = plain.moment(
                        dim, r, Q(2, 5), Q(3, 4), Q(0), Q(7, 10), i, j)
                    if a != b:
                        raise AssertionError(("mark0", dim, r, i, j, a, b))
    # For two unrestricted small coordinates, integrate p2 and p2^2 directly.
    d = s.delta
    first = marked.marked_moment(2, 0, Q(1), Q(1), Q(0), Q(1), 0, 0, 1)
    second = marked.marked_moment(2, 0, Q(1), Q(1), Q(0), Q(1), 0, 0, 2)
    if first != Q(2, 3) * d ** 4:
        raise AssertionError(("box p2", first, Q(2, 3) * d ** 4))
    if second != Q(28, 45) * d ** 6:
        raise AssertionError(("box p2^2", second, Q(28, 45) * d ** 6))

    # The generic marginal engine must reproduce every ordinary D2 entry.
    e = P2Entries(c722_support(8), 2)
    for x0 in e.base.labels:
        x = e.lz(*x0)
        for y0 in e.base.labels:
            y = e.lz(*y0)
            if e.i_entry(x, y) != e.base.i_entry(x0, y0):
                raise AssertionError(("ordinary I", x0, y0))
            if e.j_entry(x, y) != e.base.j_entry(x0, y0):
                raise AssertionError(("ordinary J", x0, y0))

    # Mixed p2-tag matrix versus sum-first/square-second contraction.
    m = P2Entries(s, 1)
    labs = ([m.lz(*x) for x in m.base.labels] +
            [m.p2(r) for r in s.active_strata()])
    coeff = tuple(Q(((-1) ** i) * (i + 2), i + 5)
                  for i in range(len(labs)))
    Im = [[m.i_entry(x, y) for y in labs] for x in labs]
    Jm = [[m.j_entry(x, y) for y in labs] for x in labs]
    qi = sum(coeff[i] * Im[i][j] * coeff[j]
             for i in range(len(labs)) for j in range(len(labs)))
    qj = sum(coeff[i] * Jm[i][j] * coeff[j]
             for i in range(len(labs)) for j in range(len(labs)))
    di, dj = m.direct_fixed_vector(labs, coeff)
    if (qi, qj) != (di, dj):
        raise AssertionError(("mixed direct contraction", qi, di, qj, dj))
    print("P2 ENRICHMENT EXACT CORE PASS")


if __name__ == "__main__":
    self_test()
