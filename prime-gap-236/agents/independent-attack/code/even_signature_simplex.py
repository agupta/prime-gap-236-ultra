#!/usr/bin/env python3
"""Polymath-style even-signature basis on the direct-BV full simplex.

The basis consists of

  (1-s/R)^a product_{r in lambda} (p_r/R^r),

where every part of lambda is even and a+|lambda|<=D.  This is a triangular
power-sum version of Polymath8b's even-signature monomial basis.  Matrix
entries are exact Fractions; only the generalized eigensolve is numerical.
"""

from __future__ import annotations

import argparse
import functools
import math
import pickle
import sys
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path

from deterministic_i import falling, power_sum_patterns


def partitions(n: int, lo: int = 1):
    if n == 0:
        yield ()
        return
    for p in range(lo, n + 1):
        for tail in partitions(n - p, p):
            yield (p,) + tail


def basis_labels(degree: int):
    labels = []
    for half_weight in range(degree // 2 + 1):
        for half_part in partitions(half_weight):
            part = tuple(2 * p for p in half_part)
            weight = 2 * half_weight
            for a in range(degree - weight + 1):
                labels.append((part, a))
    return sorted(labels, key=lambda z: (sum(z[0]) + z[1], z[0], z[1]))


@functools.lru_cache(None)
def full_slack_integral(
    factors: tuple[int, ...], slack_power: int, n: int, radius: Q
) -> Q:
    """Integral of normalized p-product times (1-s/R)^c on sum<R."""
    factors = tuple(sorted(factors))
    degree = sum(factors)
    total = Q(0)
    for pattern, multiplicity in power_sum_patterns(factors):
        blocks = len(pattern)
        if blocks <= n:
            total += Q(
                multiplicity
                * falling(n, blocks)
                * math.prod(math.factorial(v) for v in pattern)
                * math.factorial(slack_power),
                math.factorial(n + degree + slack_power),
            )
    return radius**n * total


@functools.lru_cache(None)
def truncated_slack_integral(
    factors: tuple[int, ...], slack_power: int, n: int, radius: Q, cut: Q
) -> Q:
    """Same integrand, but over sum<cut<R.

    Radial integration after expanding (1-s/R)^c avoids a multivariate
    expansion of the total-sum power.
    """
    factors = tuple(sorted(factors))
    degree = sum(factors)
    radial = Q(0)
    for h in range(slack_power + 1):
        radial += (
            (-1) ** h
            * math.comb(slack_power, h)
            * cut ** (degree + n + h)
            / radius**h
            / (degree + n + h)
        )
    total = Q(0)
    angular_den = math.factorial(degree + n - 1)
    for pattern, multiplicity in power_sum_patterns(factors):
        blocks = len(pattern)
        if blocks <= n:
            total += Q(
                multiplicity
                * falling(n, blocks)
                * math.prod(math.factorial(v) for v in pattern),
                angular_den,
            )
    return total * radial / radius**degree


@functools.lru_cache(None)
def inner_expansion(part: tuple[int, ...], a: int):
    """Expansion of R^{-1} int_0^(R-u) G(x,t)dt.

    Each item is `(unchosen_even_parts, new_slack_power, coefficient)`.
    Equal factors are selected by multiplicity, not by exponential masks.
    """
    groups = sorted(Counter(part).items())
    out: dict[tuple[tuple[int, ...], int], Q] = {}

    def rec(i: int, selected_sum: int, unchosen: list[int], ways: int):
        if i == len(groups):
            q = selected_sum
            b = q + a + 1
            coeff = Q(ways * math.factorial(q) * math.factorial(a), math.factorial(b))
            key = (tuple(sorted(unchosen)), b)
            out[key] = out.get(key, Q(0)) + coeff
            return
        exponent, multiplicity = groups[i]
        for chosen_count in range(multiplicity + 1):
            unchosen_count = multiplicity - chosen_count
            rec(
                i + 1,
                selected_sum + exponent * chosen_count,
                unchosen + [exponent] * unchosen_count,
                ways * math.comb(multiplicity, chosen_count),
            )

    rec(0, 0, [], 1)
    return tuple((p, b, c) for (p, b), c in out.items() if c)


def exact_matrices(k: int, degree: int, radius: Q, cut: Q):
    labels = basis_labels(degree)
    n = len(labels)
    I = [[Q(0) for _ in range(n)] for _ in range(n)]
    J = [[Q(0) for _ in range(n)] for _ in range(n)]
    expansions = [inner_expansion(tuple(part), a) for part, a in labels]
    for i, (pi, ai) in enumerate(labels):
        for j in range(i + 1):
            pj, aj = labels[j]
            iv = full_slack_integral(tuple(pi) + tuple(pj), ai + aj, k, radius)
            jv = Q(0)
            for fi, bi, ci in expansions[i]:
                for fj, bj, cj in expansions[j]:
                    jv += ci * cj * truncated_slack_integral(
                        fi + fj, bi + bj, k - 1, radius, cut
                    )
            jv *= radius**2
            I[i][j] = I[j][i] = iv
            J[i][j] = J[j][i] = jv
    return labels, I, J


def high_precision_quotient(I, J, k: int, dps: int, vendor: str):
    if vendor:
        sys.path.insert(0, vendor)
    import mpmath as mp

    mp.mp.dps = dps

    def cv(q: Q):
        return mp.mpf(q.numerator) / q.denominator

    n = len(I)
    diagonal = [mp.sqrt(cv(I[i][i])) for i in range(n)]
    A, B = mp.matrix(n), mp.matrix(n)
    for i in range(n):
        for j in range(n):
            A[i, j] = cv(I[i][j]) / (diagonal[i] * diagonal[j])
            B[i, j] = k * cv(J[i][j]) / (diagonal[i] * diagonal[j])
    L = mp.cholesky(A)
    Linv = L**-1
    C = Linv * B * Linv.T
    vals, vecs = mp.eigsy(C)
    z = vecs[:, n - 1]
    scaled = Linv.T * z
    raw = [scaled[i] / diagonal[i] for i in range(n)]
    scale = max(abs(x) for x in raw)
    return vals[n - 1], [x / scale for x in raw]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--degree", type=int, default=8)
    ap.add_argument("--epsilon", default="3/400")
    ap.add_argument("--dps", type=int, default=70)
    ap.add_argument("--vendor", default="vendor")
    ap.add_argument("--cache")
    ap.add_argument("--rational-denominator", type=int, default=0)
    args = ap.parse_args()

    epsilon = Q(args.epsilon)
    if not Q(0) < epsilon < Q(1, 4):
        raise SystemExit("epsilon must be in (0,1/4)")
    radius, cut = Q(1, 4) + epsilon, Q(1, 4) - epsilon
    cache = Path(args.cache) if args.cache else None
    if cache and cache.exists():
        with cache.open("rb") as fh:
            labels, I, J = pickle.load(fh)
    else:
        labels, I, J = exact_matrices(args.k, args.degree, radius, cut)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with cache.open("wb") as fh:
                pickle.dump((labels, I, J), fh)

    q, vector = high_precision_quotient(I, J, args.k, args.dps, args.vendor)
    print("EXACT MATRICES; HIGH-PRECISION DISCOVERY EIGENSOLVE")
    print("k degree basis", args.k, args.degree, len(labels))
    print("epsilon radius cut", epsilon, radius, cut)
    print("heuristic quotient", q)

    if args.rational_denominator:
        c = [Q(str(x)).limit_denominator(args.rational_denominator) for x in vector]
        num = sum(
            args.k * c[i] * J[i][j] * c[j]
            for i in range(len(c))
            for j in range(len(c))
        )
        den = sum(
            c[i] * I[i][j] * c[j]
            for i in range(len(c))
            for j in range(len(c))
        )
        assert den > 0
        print("exact rationalized quotient", float(num / den))
        print("exact margin sign", num - den > 0)
        print("exact margin", num - den)


if __name__ == "__main__":
    main()
