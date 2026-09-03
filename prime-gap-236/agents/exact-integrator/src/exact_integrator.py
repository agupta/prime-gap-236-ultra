#!/usr/bin/env python3
"""Exact moments for Stadlmann's one-stratum support.

This module is an independent implementation of the integration step in section 5
of arXiv:2608.31126v1.  It is deliberately self contained: only Python's standard
library is needed for exact calculations.  NumPy is used only by the optional
floating-point generalized-eigenvalue discovery routine.

The supported region is

  S_k = {t >= 0: sum(t) <= alpha,
         sum(t_i for t_i > delta) <= beta[r]},

where r is the number of coordinates exceeding delta.  Boundaries have measure
zero, so the paper's mixture of strict and weak inequalities does not affect any
moment.

Symmetric polynomials use the monomial-orbit convention

  P_lambda(t) = sum t_1^a1 ... t_k^ak,

where the sum is over the distinct permutations of lambda padded with zeros.
Basis elements are (1-sum(t))^a P_lambda(t).  ``no_ones_basis`` supplies the
general Polymath coordinate system (all parts of lambda are at least two), while
``even_basis`` supplies the speed-restricted even-signature subfamily.  The TeX
definition of Stadlmann's B_D as squares is ambiguous as a *linear* basis, so
every experiment records its literal finite list rather than relying on that
label alone.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache
from itertools import product
from math import comb, factorial
from typing import Dict, Iterable, Iterator, List, Mapping, Sequence, Tuple


Q = Fraction
Partition = Tuple[int, ...]
Poly2 = Dict[Tuple[int, int], Q]
Point = Tuple[Q, Q]
HalfPlane = Tuple[Q, Q, Q]  # a*z + b*w <= c


def _q(x: int | Q) -> Q:
    return x if isinstance(x, Q) else Q(x)


def _falling(n: int, r: int) -> int:
    return factorial(n) // factorial(n - r)


def orbit_size(k: int, lam: Partition) -> int:
    """Number of distinct permutations of ``lam`` padded with k-len(lam) zeros."""
    if len(lam) > k or any(x <= 0 for x in lam):
        return 0
    ans = factorial(k) // factorial(k - len(lam))
    for m in Counter(lam).values():
        ans //= factorial(m)
    return ans


def integer_partitions(n: int, max_part: int | None = None) -> Iterator[Partition]:
    """Partitions of n in weakly decreasing order; includes () for n=0."""
    if n == 0:
        yield ()
        return
    if max_part is None or max_part > n:
        max_part = n
    for first in range(max_part, 0, -1):
        for rest in integer_partitions(n - first, first):
            yield (first,) + rest


def even_basis(D: int, max_length: int | None = None) -> List[Tuple[int, Partition]]:
    """Return (a,lambda) for (1-P_1)^a P_lambda, lambda all even, a+|lambda|<=D."""
    out: List[Tuple[int, Partition]] = []
    for half_degree in range(D // 2 + 1):
        for base in integer_partitions(half_degree):
            lam = tuple(2 * x for x in base)
            if max_length is not None and len(lam) > max_length:
                continue
            for a in range(D - 2 * half_degree + 1):
                out.append((a, lam))
    out.sort(key=lambda x: (x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    return out


def no_ones_basis(D: int, max_length: int | None = None) -> List[Tuple[int, Partition]]:
    """Polymath basis (1-P_1)^a P_lambda with every part of lambda at least 2."""
    out: List[Tuple[int, Partition]] = []
    for degree in range(D + 1):
        for lam in integer_partitions(degree):
            if any(x == 1 for x in lam):
                continue
            if max_length is not None and len(lam) > max_length:
                continue
            for a in range(D - degree + 1):
                out.append((a, lam))
    out.sort(key=lambda x: (x[0] + sum(x[1]), sum(x[1]), len(x[1]), x[1], x[0]))
    return out


@lru_cache(maxsize=None)
def multiply_monomial_orbits(lam: Partition, mu: Partition) -> Tuple[Tuple[Partition, int], ...]:
    """Stable structure constants P_lam P_mu = sum c_nu P_nu.

    A contingency table records how many occurrences of each part of lam and mu
    land on the same coordinate.  The labeled-matching count is divided by the
    automorphism factors of lam and mu, and multiplied by that of nu.  The result
    is integral; asserting this catches combinatorial mistakes.
    """
    lam = tuple(sorted(lam, reverse=True))
    mu = tuple(sorted(mu, reverse=True))
    if not lam:
        return ((mu, 1),)
    if not mu:
        return ((lam, 1),)

    lc = sorted(Counter(lam).items(), reverse=True)
    mc = sorted(Counter(mu).items(), reverse=True)
    lvals = [x for x, _ in lc]
    lcnts = [n for _, n in lc]
    mvals = [x for x, _ in mc]
    mcnts = [n for _, n in mc]
    aut_l = 1
    aut_m = 1
    for n in lcnts:
        aut_l *= factorial(n)
    for n in mcnts:
        aut_m *= factorial(n)

    totals: Dict[Partition, Q] = defaultdict(Q)
    table = [[0 for _ in mvals] for _ in lvals]

    def row_vectors(cap: int, col_caps: Sequence[int], j: int = 0,
                    cur: Tuple[int, ...] = ()) -> Iterator[Tuple[int, ...]]:
        if j == len(col_caps):
            yield cur
            return
        used = sum(cur)
        for v in range(min(cap - used, col_caps[j]) + 1):
            yield from row_vectors(cap, col_caps, j + 1, cur + (v,))

    def rec(i: int, rem_cols: Tuple[int, ...]) -> None:
        if i < len(lvals):
            for row in row_vectors(lcnts[i], rem_cols):
                table[i][:] = row
                rec(i + 1, tuple(rem_cols[j] - row[j] for j in range(len(mvals))))
            return

        row_sums = [sum(row) for row in table]
        col_sums = [sum(table[i][j] for i in range(len(lvals))) for j in range(len(mvals))]
        parts: List[int] = []
        for i, a in enumerate(lvals):
            parts.extend([a] * (lcnts[i] - row_sums[i]))
        for j, b in enumerate(mvals):
            parts.extend([b] * (mcnts[j] - col_sums[j]))
        for i, a in enumerate(lvals):
            for j, b in enumerate(mvals):
                parts.extend([a + b] * table[i][j])
        nu = tuple(sorted(parts, reverse=True))

        labeled = 1
        for n, used in zip(lcnts, row_sums):
            labeled *= _falling(n, used)
        for n, used in zip(mcnts, col_sums):
            labeled *= _falling(n, used)
        # Divide only after forming the whole denominator.  Individual
        # factorials need not divide an intermediate product even though their
        # product divides the labeled matching count.
        cell_aut = 1
        for row in table:
            for n in row:
                cell_aut *= factorial(n)
        if labeled % cell_aut:
            raise ArithmeticError(("nonintegral labeled matching count", lam, mu,
                                   tuple(tuple(row) for row in table)))
        labeled //= cell_aut
        aut_nu = 1
        for n in Counter(nu).values():
            aut_nu *= factorial(n)
        coeff = Q(aut_nu * labeled, aut_l * aut_m)
        if coeff.denominator != 1:
            raise ArithmeticError((lam, mu, nu, coeff, table))
        totals[nu] += coeff

    rec(0, tuple(mcnts))
    return tuple(sorted(((nu, int(c)) for nu, c in totals.items())))


def _poly_add(a: Mapping[Tuple[int, int], Q], b: Mapping[Tuple[int, int], Q]) -> Poly2:
    out: Dict[Tuple[int, int], Q] = defaultdict(Q)
    for mon, c in a.items():
        out[mon] += c
    for mon, c in b.items():
        out[mon] += c
    return {m: c for m, c in out.items() if c}


def _poly_scale(a: Mapping[Tuple[int, int], Q], c: Q) -> Poly2:
    if not c:
        return {}
    return {m: c * v for m, v in a.items() if v}


def _poly_mul(a: Mapping[Tuple[int, int], Q], b: Mapping[Tuple[int, int], Q]) -> Poly2:
    out: Dict[Tuple[int, int], Q] = defaultdict(Q)
    for (i, j), x in a.items():
        for (u, v), y in b.items():
            out[(i + u, j + v)] += x * y
    return {m: c for m, c in out.items() if c}


@lru_cache(maxsize=None)
def _linear_power(c0: Q, cz: Q, cw: Q, n: int) -> Tuple[Tuple[Tuple[int, int], Q], ...]:
    """Expand (c0+cz*z+cw*w)^n exactly."""
    out: Dict[Tuple[int, int], Q] = defaultdict(Q)
    for i in range(n + 1):
        for j in range(n - i + 1):
            h = n - i - j
            coeff = Q(factorial(n), factorial(i) * factorial(j) * factorial(h))
            out[(i, j)] += coeff * (cz ** i) * (cw ** j) * (c0 ** h)
    return tuple(out.items())


def _lp(c0: Q, cz: Q, cw: Q, n: int) -> Poly2:
    return dict(_linear_power(c0, cz, cw, n))


def _clip_polygon(poly: Sequence[Point], hp: HalfPlane) -> Tuple[Point, ...]:
    a, b, c = hp
    if not poly:
        return ()
    out: List[Point] = []
    prev = poly[-1]
    fp = a * prev[0] + b * prev[1] - c
    prev_in = fp <= 0
    for cur in poly:
        fc = a * cur[0] + b * cur[1] - c
        cur_in = fc <= 0
        if cur_in != prev_in:
            # prev + theta*(cur-prev), solve affine boundary equation.
            den = fp - fc
            if den == 0:
                raise ArithmeticError("parallel clipping edge classified inconsistently")
            theta = fp / den
            out.append((prev[0] + theta * (cur[0] - prev[0]),
                        prev[1] + theta * (cur[1] - prev[1])))
        if cur_in:
            out.append(cur)
        prev, fp, prev_in = cur, fc, cur_in
    # Remove adjacent duplicates created by clipping through a vertex.
    clean: List[Point] = []
    for p in out:
        if not clean or p != clean[-1]:
            clean.append(p)
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    return tuple(clean)


@lru_cache(maxsize=None)
def polygon(outer_sum_cap: Q, constraints: Tuple[HalfPlane, ...] = ()) -> Tuple[Point, ...]:
    """Clip the first-quadrant triangle z+w<=outer_sum_cap by rational halfplanes."""
    if outer_sum_cap <= 0:
        return ()
    p: Tuple[Point, ...] = ((Q(0), Q(0)), (outer_sum_cap, Q(0)), (Q(0), outer_sum_cap))
    for hp in constraints:
        p = _clip_polygon(p, hp)
        if len(p) < 3:
            return ()
    # Zero-area polygons do not contribute.
    area2 = sum(p[i][0] * p[(i + 1) % len(p)][1] -
                p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
    if area2 == 0:
        return ()
    if area2 < 0:
        p = tuple(reversed(p))
    return p


@lru_cache(maxsize=None)
def polygon_monomial(poly: Tuple[Point, ...], az: int, aw: int) -> Q:
    """Integral of z^az w^aw over a CCW rational polygon, by Green's theorem.

    Every edge produced by ``polygon`` is horizontal, vertical, or has slope -1.
    Treating those forms directly is important: the small-box radial exponent is
    about k, so a generic double binomial expansion is needlessly expensive.
    """
    if not poly:
        return Q(0)
    ans = Q(0)
    ap = az + 1
    for idx, (x0, y0) in enumerate(poly):
        x1, y1 = poly[(idx + 1) % len(poly)]
        dx, dy = x1 - x0, y1 - y0
        if dy == 0:
            continue
        if dx == 0:
            ans += (x0 ** ap) * (y1 ** (aw + 1) - y0 ** (aw + 1)) / (ap * (aw + 1))
            continue
        if dx + dy == 0:
            # x+y=C on the edge; integrate (C-y)^ap*y^aw dy / ap.
            C = x0 + y0
            edge = Q(0)
            for i in range(ap + 1):
                edge += (Q(((-1) ** i) * comb(ap, i), aw + i + 1) *
                         (C ** (ap - i)) *
                         (y1 ** (aw + i + 1) - y0 ** (aw + i + 1)))
            ans += edge / ap
            continue
        # Defensive fallback.  It should be unreachable unless a new kind of
        # halfplane is added later.
        edge = Q(0)
        for i in range(ap + 1):
            for j in range(aw + 1):
                edge += (Q(comb(ap, i) * comb(aw, j), i + j + 1) *
                         (x0 ** (ap - i)) * (dx ** i) *
                         (y0 ** (aw - j)) * (dy ** j))
        ans += dy * edge / ap
    return ans


def integrate_poly_polygon(p: Mapping[Tuple[int, int], Q], poly: Tuple[Point, ...],
                           z_shift: int = 0, w_shift: int = 0) -> Q:
    return sum(c * polygon_monomial(poly, i + z_shift, j + w_shift)
               for (i, j), c in p.items())


def _integrate_poly_interval(p: Mapping[Tuple[int, int], Q], lo: Q, hi: Q,
                             w_shift: int = 0) -> Q:
    """Set z=0 and integrate w^w_shift p(0,w) on [lo,hi]."""
    if hi <= lo:
        return Q(0)
    ans = Q(0)
    for (i, j), c in p.items():
        if i:
            continue
        n = j + w_shift + 1
        ans += c * (hi ** n - lo ** n) / n
    return ans


def _integrate_poly_z_interval(p: Mapping[Tuple[int, int], Q], lo: Q, hi: Q,
                               z_shift: int = 0) -> Q:
    """Set w=0 and integrate z^z_shift p(z,0) on [lo,hi]."""
    if hi <= lo:
        return Q(0)
    ans = Q(0)
    for (i, j), c in p.items():
        if j:
            continue
        n = i + z_shift + 1
        ans += c * (hi ** n - lo ** n) / n
    return ans


@lru_cache(maxsize=None)
def _large_shift_dp(exps: Tuple[int, ...], delta: Q) -> Dict[int, Q]:
    """Coefficient by aggregate degree after shifting x_i=delta+z_i.

    The coefficient already includes the angular Dirichlet factor numerator
    product(q_i!).
    """
    dp: Dict[int, Q] = {0: Q(1)}
    for a in exps:
        nd: Dict[int, Q] = defaultdict(Q)
        for total, old in dp.items():
            for q in range(a + 1):
                nd[total + q] += old * comb(a, q) * (delta ** (a - q)) * factorial(q)
        dp = dict(nd)
    return dp


@lru_cache(maxsize=None)
def _small_box_dp(exps: Tuple[int, ...], delta: Q, max_h: int) -> Dict[Tuple[int, int], Q]:
    """Grouped inclusion-exclusion for y_i in [0,delta].

    Keys are (number h of translated upper faces, aggregate exponent P).  Values
    include product(p_i!).  Terms with h>max_h cannot meet the outer sum cap and
    are discarded immediately.
    """
    dp: Dict[Tuple[int, int], Q] = {(0, 0): Q(1)}
    for a in exps:
        nd: Dict[Tuple[int, int], Q] = defaultdict(Q)
        for (h, total), old in dp.items():
            # Coordinate not selected by inclusion-exclusion.
            nd[(h, total + a)] += old * factorial(a)
            # Coordinate translated by delta; the minus sign is per selected face.
            if h < max_h:
                for p in range(a + 1):
                    nd[(h + 1, total + p)] -= (
                        old * comb(a, p) * (delta ** (a - p)) * factorial(p)
                    )
        dp = dict(nd)
    return {key: val for key, val in dp.items() if val}


@lru_cache(maxsize=None)
def _selected_exponent_splits(k: int, lam: Partition, r: int) -> Tuple[Tuple[int, Tuple[int, ...], Tuple[int, ...]], ...]:
    """Grouped choices of r large coordinates from a padded exponent vector.

    Returns (multiplicity, large_exponents, small_exponents).
    """
    counts = Counter(lam)
    counts[0] += k - len(lam)
    cats = sorted(counts.items())
    out: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = []

    def rec(i: int, left: int, chosen: List[int], mult: int) -> None:
        if i == len(cats):
            if left:
                return
            large: List[int] = []
            small: List[int] = []
            for (a, n), q in zip(cats, chosen):
                large.extend([a] * q)
                small.extend([a] * (n - q))
            out.append((mult, tuple(large), tuple(small)))
            return
        a, n = cats[i]
        for q in range(max(0, left - sum(nn for _, nn in cats[i + 1:])), min(n, left) + 1):
            chosen.append(q)
            rec(i + 1, left - q, chosen, mult * comb(n, q))
            chosen.pop()

    rec(0, r, [], 1)
    return tuple(out)


@dataclass(frozen=True)
class OneStratumSupport:
    """Published n=1 support and its J epsilon-enlargement cutoff."""

    k: int
    alpha: Q
    delta: Q
    eta: Q
    beta1: Q
    beta2: Q
    beta3plus: Q

    @classmethod
    def published(cls, k: int) -> "OneStratumSupport":
        return cls(k=k, alpha=Q(521, 2000), delta=Q(7, 250),
                   eta=Q(491, 2000), beta1=Q(3, 20),
                   beta2=Q(3, 20), beta3plus=Q(17, 100))

    def beta(self, r: int) -> Q:
        if r <= 0:
            raise ValueError("beta is defined only for a positive number of large coordinates")
        if r == 1:
            return self.beta1
        if r == 2:
            return self.beta2
        return self.beta3plus

    def max_large(self) -> int:
        # Do not assume beta(r) is monotone.  Proposition 3 permits a schedule
        # with a later upward jump, so an impossible r need not make every
        # larger r impossible.
        feasible = [r for r in range(1, self.k + 1)
                    if r * self.delta < self.beta(r)]
        return max(feasible, default=0)

    def is_full_simplex(self) -> bool:
        """Whether the large-coordinate caps are redundant under sum(t)<=alpha."""
        possible = min(self.k, int(self.alpha // self.delta))
        return all(self.beta(r) >= self.alpha for r in range(1, possible + 1))

    @lru_cache(maxsize=None)
    def _piece_residual(self, large: Tuple[int, ...], small: Tuple[int, ...], c: int) -> Q:
        """Integral on a fixed large/small-coordinate piece of (alpha-sum)^c."""
        r, s = len(large), len(small)
        max_h = int(self.alpha // self.delta) - r
        if max_h < 0:
            return Q(0)
        sd = _small_box_dp(small, self.delta, max_h)
        ld = _large_shift_dp(large, self.delta)
        gamma = self.beta(r) - r * self.delta if r else None
        if r and gamma <= 0:
            return Q(0)
        ans = Q(0)
        for qdeg, lc in ld.items():
            if r:
                lc /= factorial(qdeg + r - 1)
            for (h, pdeg), sc in sd.items():
                L = self.alpha - (r + h) * self.delta
                if L <= 0:
                    continue
                sc *= Q(factorial(c), factorial(pdeg + s + c))
                if not r:
                    ans += lc * sc * (L ** (pdeg + s + c))
                    continue
                u = qdeg + r - 1
                v = pdeg + s + c
                assert gamma is not None
                if gamma >= L:
                    radial = Q(factorial(u) * factorial(v), factorial(u + v + 1)) * (L ** (u + v + 1))
                else:
                    radial = Q(0)
                    for j in range(v + 1):
                        radial += (Q((-1) ** j * comb(v, j), u + j + 1) *
                                   (L ** (v - j)) * (gamma ** (u + j + 1)))
                ans += lc * sc * radial
        return ans

    @lru_cache(maxsize=None)
    def canonical_support_residual(self, lam: Partition, c: int) -> Q:
        """Integral of one canonical monomial times (alpha-sum)^c over S_k."""
        lam = tuple(sorted(lam, reverse=True))
        if len(lam) > self.k:
            return Q(0)
        if self.is_full_simplex():
            angular = factorial(c)
            for x in lam:
                angular *= factorial(x)
            degree = sum(lam) + self.k + c
            return Q(angular, factorial(degree)) * (self.alpha ** degree)
        ans = Q(0)
        for r in range(self.max_large() + 1):
            for mult, large, small in _selected_exponent_splits(self.k, lam, r):
                ans += mult * self._piece_residual(large, small, c)
        return ans

    @lru_cache(maxsize=None)
    def canonical_support_moment(self, lam: Partition, b: int) -> Q:
        """Integral of one canonical monomial times (1-sum)^b over S_k."""
        return sum(Q(comb(b, c)) * ((1 - self.alpha) ** (b - c)) *
                   self.canonical_support_residual(lam, c)
                   for c in range(b + 1))

    def orbit_support_moment(self, lam: Partition, b: int) -> Q:
        return orbit_size(self.k, lam) * self.canonical_support_moment(lam, b)

    @lru_cache(maxsize=None)
    def _branch_constraints(self, r: int, h: int, branch: str) -> Tuple[HalfPlane, ...] | None:
        """Halfplanes for a conditional t-integral branch in aggregate (z,w)."""
        u0 = (r + h) * self.delta
        hp: List[HalfPlane] = []
        if branch.startswith("S") and r:
            cap = self.beta(r) - r * self.delta
            if cap <= 0:
                return None
            hp.append((Q(1), Q(0), cap))
        if branch == "Sdelta":
            hp.append((Q(1), Q(1), self.alpha - u0 - self.delta))
        elif branch == "Stotal":
            # z+w >= alpha-u0-delta.
            hp.append((Q(-1), Q(-1), -(self.alpha - u0 - self.delta)))
            hp.append((Q(1), Q(1), self.alpha - u0))
        elif branch == "Ltotal":
            beta = self.beta(r + 1)
            # Actual small-coordinate sum h*delta+w >= alpha-beta.
            hp.append((Q(0), Q(-1), -(self.alpha - beta - h * self.delta)))
            hp.append((Q(1), Q(1), self.alpha - u0 - self.delta))
        elif branch == "Lbig":
            beta = self.beta(r + 1)
            # If beta=alpha and there is no translated small mass, the two
            # candidate upper bounds agree identically when w=0.  Assign the
            # tie to Ltotal; otherwise a zero-dimensional small group (s=0)
            # would be counted twice.
            if beta == self.alpha and h == 0:
                return None
            hp.append((Q(0), Q(1), self.alpha - beta - h * self.delta))
            hp.append((Q(1), Q(0), beta - (r + 1) * self.delta))
        else:
            raise ValueError(branch)
        return tuple(hp)

    @lru_cache(maxsize=None)
    def _marginal_poly(self, r: int, h: int, branch: str, t_exp: int, resid: int) -> Tuple[Tuple[Tuple[int, int], Q], ...]:
        """Polynomial integral in t on one active-upper-bound branch."""
        u0 = (r + h) * self.delta
        one_u = (Q(1) - u0, Q(-1), Q(-1))
        if branch == "Sdelta":
            upper = (self.delta, Q(0), Q(0))
            lower = Q(0)
        elif branch in ("Stotal", "Ltotal"):
            upper = (self.alpha - u0, Q(-1), Q(-1))
            lower = self.delta if branch == "Ltotal" else Q(0)
        elif branch == "Lbig":
            upper = (self.beta(r + 1) - r * self.delta, Q(-1), Q(0))
            lower = self.delta
        else:
            raise ValueError(branch)

        ans: Poly2 = {}
        for j in range(resid + 1):
            n = t_exp + j + 1
            coeff = Q(((-1) ** j) * comb(resid, j), n)
            first = _poly_mul(_lp(*one_u, resid - j), _lp(*upper, n))
            if lower:
                second = _poly_scale(_lp(*one_u, resid - j), lower ** n)
                first = _poly_add(first, _poly_scale(second, Q(-1)))
            ans = _poly_add(ans, _poly_scale(first, coeff))
        return tuple(ans.items())

    def _branch_interval(self, r: int, h: int, branch: str) -> Tuple[Q, Q] | None:
        """Degenerate z=0 branch domain, used only when there are no shared large u's."""
        assert r == 0
        lo = Q(0)
        hi = self.eta - h * self.delta
        if branch == "Sdelta":
            hi = min(hi, self.alpha - h * self.delta - self.delta)
        elif branch == "Stotal":
            lo = max(lo, self.alpha - h * self.delta - self.delta)
            hi = min(hi, self.alpha - h * self.delta)
        elif branch == "Ltotal":
            lo = max(lo, self.alpha - self.beta(1) - h * self.delta)
            hi = min(hi, self.alpha - h * self.delta - self.delta)
        elif branch == "Lbig":
            hi = min(hi, self.alpha - self.beta(1) - h * self.delta)
            if self.beta(1) - self.delta <= 0:
                return None
        else:
            raise ValueError(branch)
        return (lo, hi) if hi > lo else None

    def _branch_z_interval(self, r: int, h: int, branch: str) -> Tuple[Q, Q] | None:
        """Degenerate w=0 branch domain (there are no shared small coordinates)."""
        lo, hi = Q(0), self.eta - (r + h) * self.delta
        constraints = self._branch_constraints(r, h, branch)
        if constraints is None:
            return None
        for az, aw, c in constraints:
            # w=0.  A constraint independent of z is either automatic or empty.
            if az > 0:
                hi = min(hi, c / az)
            elif az < 0:
                lo = max(lo, c / az)
            elif c < 0:
                return None
        return (lo, hi) if hi > lo else None

    @lru_cache(maxsize=None)
    def _j_piece(self, large: Tuple[int, ...], small: Tuple[int, ...],
                 e: int, a: int, f: int, b: int) -> Q:
        """J bilinear moment on a fixed large/small split of the k-1 shared variables."""
        r, s = len(large), len(small)
        # Inclusion-exclusion terms with a shift beyond eta have empty outer domain.
        max_h = int(self.eta // self.delta) - r
        if max_h < 0:
            return Q(0)
        sd = _small_box_dp(small, self.delta, max_h)
        ld = _large_shift_dp(large, self.delta)
        branches = ("Sdelta", "Stotal", "Ltotal", "Lbig")
        ans = Q(0)
        for qdeg, lc0 in ld.items():
            lc = lc0 / factorial(qdeg + r - 1) if r else lc0
            zpow = qdeg + r - 1 if r else 0
            for (h, pdeg), sc0 in sd.items():
                outer = self.eta - (r + h) * self.delta
                if outer <= 0:
                    continue
                sc = sc0 / factorial(pdeg + s - 1) if s else sc0
                wpow = pdeg + s - 1 if s else 0
                for br1 in branches:
                    p1 = dict(self._marginal_poly(r, h, br1, e, a))
                    if not p1:
                        continue
                    c1 = self._branch_constraints(r, h, br1)
                    if c1 is None:
                        continue
                    for br2 in branches:
                        p2 = dict(self._marginal_poly(r, h, br2, f, b))
                        if not p2:
                            continue
                        c2 = self._branch_constraints(r, h, br2)
                        if c2 is None:
                            continue
                        integrand = _poly_mul(p1, p2)
                        if r and s:
                            pg = polygon(outer, c1 + c2)
                            val = integrate_poly_polygon(integrand, pg, zpow, wpow)
                        elif r:
                            i1 = self._branch_z_interval(r, h, br1)
                            i2 = self._branch_z_interval(r, h, br2)
                            if i1 is None or i2 is None:
                                continue
                            lo, hi = max(i1[0], i2[0]), min(i1[1], i2[1])
                            val = _integrate_poly_z_interval(integrand, lo, hi, zpow)
                        else:
                            i1 = self._branch_interval(r, h, br1)
                            i2 = self._branch_interval(r, h, br2)
                            if i1 is None or i2 is None:
                                continue
                            lo, hi = max(i1[0], i2[0]), min(i1[1], i2[1])
                            val = _integrate_poly_interval(integrand, lo, hi, wpow)
                        ans += lc * sc * val
        return ans

    @lru_cache(maxsize=None)
    def canonical_j_moment(self, nu: Partition, e: int, a: int, f: int, b: int) -> Q:
        """J moment for one canonical shared-u monomial and t exponents e,f."""
        ku = self.k - 1
        if self.is_full_simplex():
            # First integrate each distinguished coordinate up to alpha-U.
            left: Dict[int, Q] = defaultdict(Q)
            right: Dict[int, Q] = defaultdict(Q)
            for c in range(a + 1):
                power = e + c + 1
                left[power] += (Q(comb(a, c) * factorial(e) * factorial(c),
                                  factorial(e + c + 1)) *
                                ((1 - self.alpha) ** (a - c)))
            for c in range(b + 1):
                power = f + c + 1
                right[power] += (Q(comb(b, c) * factorial(f) * factorial(c),
                                   factorial(f + c + 1)) *
                                 ((1 - self.alpha) ** (b - c)))
            prod_nu = 1
            for x in nu:
                prod_nu *= factorial(x)
            total_nu = sum(nu)
            ans = Q(0)
            for p, cp in left.items():
                for q, cq in right.items():
                    power = p + q
                    # Integrate (alpha-U)^power on U<=eta by expanding at eta.
                    for d in range(power + 1):
                        radial_degree = total_nu + ku + d
                        ans += (cp * cq * comb(power, d) *
                                ((self.alpha - self.eta) ** (power - d)) *
                                Q(prod_nu * factorial(d), factorial(radial_degree)) *
                                (self.eta ** radial_degree))
            return ans
        if ku == 0:
            # There is no aggregate u integration; integrate the two t marginals
            # independently at u=0.  Reuse branch polynomials evaluated at z=w=0.
            vals: List[Q] = []
            for te, rr in ((e, a), (f, b)):
                v = Q(0)
                for branch in ("Sdelta", "Stotal", "Ltotal", "Lbig"):
                    interval = self._branch_interval(0, 0, branch)
                    if interval is not None and interval[0] <= 0 <= interval[1]:
                        v += dict(self._marginal_poly(0, 0, branch, te, rr)).get((0, 0), Q(0))
                vals.append(v)
            return vals[0] * vals[1]
        if len(nu) > ku:
            return Q(0)
        ans = Q(0)
        max_r = min(ku, self.max_large())
        for r in range(max_r + 1):
            for mult, large, small in _selected_exponent_splits(ku, nu, r):
                ans += mult * self._j_piece(large, small, e, a, f, b)
        return ans

    def orbit_j_moment(self, nu: Partition, e: int, a: int, f: int, b: int) -> Q:
        return orbit_size(self.k - 1, nu) * self.canonical_j_moment(nu, e, a, f, b)

    @staticmethod
    def split_at_distinguished(lam: Partition, k: int) -> Tuple[Tuple[int, Partition], ...]:
        """P_lam(u,t) = sum_e t^e P_{lam minus e}(u), over distinct e including 0."""
        out: List[Tuple[int, Partition]] = []
        if len(lam) < k:
            out.append((0, lam))
        for e in sorted(set(lam)):
            rest = list(lam)
            rest.remove(e)
            out.append((e, tuple(rest)))
        return tuple(out)

    @lru_cache(maxsize=None)
    def basis_m1(self, x: Tuple[int, Partition], y: Tuple[int, Partition]) -> Q:
        a, lam = x
        b, mu = y
        return sum(coeff * self.orbit_support_moment(nu, a + b)
                   for nu, coeff in multiply_monomial_orbits(lam, mu))

    @lru_cache(maxsize=None)
    def basis_j(self, x: Tuple[int, Partition], y: Tuple[int, Partition]) -> Q:
        a, lam = x
        b, mu = y
        ans = Q(0)
        for e, lr in self.split_at_distinguished(lam, self.k):
            for f, mr in self.split_at_distinguished(mu, self.k):
                for nu, coeff in multiply_monomial_orbits(lr, mr):
                    ans += coeff * self.orbit_j_moment(nu, e, a, f, b)
        return ans

    def matrices(self, basis: Sequence[Tuple[int, Partition]]) -> Tuple[List[List[Q]], List[List[Q]]]:
        """Exact M1 and M2=kJ for c1=c2=0."""
        n = len(basis)
        m1 = [[Q(0) for _ in range(n)] for _ in range(n)]
        m2 = [[Q(0) for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(i + 1):
                x = self.basis_m1(basis[i], basis[j])
                y = self.k * self.basis_j(basis[i], basis[j])
                m1[i][j] = m1[j][i] = x
                m2[i][j] = m2[j][i] = y
        return m1, m2


def exact_quadratic(matrix: Sequence[Sequence[Q]], vector: Sequence[int | Q]) -> Q:
    v = [_q(x) for x in vector]
    return sum(v[i] * matrix[i][j] * v[j]
               for i in range(len(v)) for j in range(len(v)))


def float_generalized_eigen(m1: Sequence[Sequence[Q]], m2: Sequence[Sequence[Q]]):
    """Discovery only: largest eigenpair of M2 v=lambda M1 v using NumPy."""
    import numpy as np

    a = np.array([[float(x) for x in row] for row in m1], dtype=float)
    b = np.array([[float(x) for x in row] for row in m2], dtype=float)
    # Symmetric whitening is substantially more stable than eig(solve(M1,M2)).
    scale = np.sqrt(np.maximum(np.diag(a), np.finfo(float).tiny))
    aa = a / scale[:, None] / scale[None, :]
    bb = b / scale[:, None] / scale[None, :]
    try:
        L = np.linalg.cholesky(aa)
        z = np.linalg.solve(L, bb)
        c = np.linalg.solve(L, z.T).T
        c = (c + c.T) / 2
        vals, vecs = np.linalg.eigh(c)
        w = np.linalg.solve(L.T, vecs[:, -1]) / scale
        return float(vals[-1]), w
    except np.linalg.LinAlgError:
        # Polynomial Gram matrices become extremely ill-conditioned well before
        # the exact matrix is singular.  This fallback is only a discovery aid;
        # every claimed vector must subsequently be checked as an exact quadratic
        # inequality.  Diagonal scaling still improves the raw solve markedly.
        vals, vecs = np.linalg.eig(np.linalg.solve(aa, bb))
        realish = np.where(np.abs(vals.imag) < 1e-7 * np.maximum(1.0, np.abs(vals.real)))[0]
        if not len(realish):
            raise np.linalg.LinAlgError("no numerically real generalized eigenvalues")
        idx = realish[np.argmax(vals[realish].real)]
        return float(vals[idx].real), vecs[:, idx].real / scale


def decimal_generalized_power(m1: Sequence[Sequence[Q]], m2: Sequence[Sequence[Q]],
                              precision: int = 100, iterations: int = 80):
    """High-precision discovery eigenpair by power iteration on M1^{-1} M2.

    The exact Gram matrices are often far beyond double precision's useful
    condition range.  Decimal LU factorization is sufficient for discovery; as
    always, the returned vector is rationalized and its quotient checked exactly.
    """
    n = len(m1)
    with localcontext() as ctx:
        ctx.prec = precision

        def dec(x: Q) -> Decimal:
            return Decimal(x.numerator) / Decimal(x.denominator)

        # Symmetric diagonal scaling keeps pivots in a comparable range.
        scales = [dec(m1[i][i]).sqrt() for i in range(n)]
        A = [[dec(m1[i][j]) / scales[i] / scales[j] for j in range(n)]
             for i in range(n)]
        B = [[dec(m2[i][j]) / scales[i] / scales[j] for j in range(n)]
             for i in range(n)]

        # LU with partial pivoting, performed once.
        LU = [row[:] for row in A]
        piv = list(range(n))
        for col in range(n):
            p = max(range(col, n), key=lambda i: abs(LU[i][col]))
            if LU[p][col] == 0:
                raise ArithmeticError("exact Gram matrix appears singular")
            if p != col:
                LU[p], LU[col] = LU[col], LU[p]
                piv[p], piv[col] = piv[col], piv[p]
            pivot = LU[col][col]
            for i in range(col + 1, n):
                LU[i][col] /= pivot
                mul = LU[i][col]
                for j in range(col + 1, n):
                    LU[i][j] -= mul * LU[col][j]

        def solve(rhs):
            y = [rhs[piv[i]] for i in range(n)]
            for i in range(n):
                for j in range(i):
                    y[i] -= LU[i][j] * y[j]
            x = y[:]
            for i in range(n - 1, -1, -1):
                for j in range(i + 1, n):
                    x[i] -= LU[i][j] * x[j]
                x[i] /= LU[i][i]
            return x

        v = [Decimal(1) / Decimal(i + 1) for i in range(n)]
        eigen = Decimal(0)
        for _ in range(iterations):
            rhs = [sum(B[i][j] * v[j] for j in range(n)) for i in range(n)]
            w = solve(rhs)
            norm = max(abs(x) for x in w)
            if norm == 0:
                raise ArithmeticError("zero vector in generalized power iteration")
            v = [x / norm for x in w]
            av = [sum(A[i][j] * v[j] for j in range(n)) for i in range(n)]
            bv = [sum(B[i][j] * v[j] for j in range(n)) for i in range(n)]
            eigen = sum(v[i] * bv[i] for i in range(n)) / sum(v[i] * av[i] for i in range(n))

        # Undo diagonal scaling: u_i=v_i/scale_i.
        u = [v[i] / scales[i] for i in range(n)]
        norm = max(abs(x) for x in u)
        u = [x / norm for x in u]
        return eigen, u


__all__ = [
    "Fraction", "OneStratumSupport", "decimal_generalized_power", "even_basis", "exact_quadratic",
    "float_generalized_eigen", "integer_partitions", "multiply_monomial_orbits",
    "no_ones_basis",
    "orbit_size", "polygon", "polygon_monomial",
]
