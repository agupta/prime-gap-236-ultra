#!/usr/bin/env python3
"""Deterministic polynomial integrals for the denominator I.

This implements a compact symmetric-power-sum expansion independently of the
paper's unpublished code.  It is currently binary floating point (intended for
stable discovery/validation), but every operation is a finite sum of powers,
factorials, and binomial coefficients, so the same routines admit a direct
Fraction backend for exact certification.
"""

from __future__ import annotations

import argparse
import functools
import itertools
import math

import numpy as np

from mc_symmetric_basis import basis_labels
from numerical_sum_basis import Support, parse_bounds


def falling(n: int, q: int) -> int:
    if q < 0 or q > n:
        return 0
    return math.factorial(n) // math.factorial(n - q)


@functools.lru_cache(None)
def power_sum_patterns(factors: tuple[int, ...]):
    """Expand product p_e into distinct-coordinate exponent patterns.

    Returns (sorted block-exponent tuple, multiplicity) pairs.  Multiplicity
    counts set partitions of the labeled factors producing the same pattern;
    injection of blocks into coordinates is handled later by falling factorials.
    """
    # A direct set-partition enumeration costs a Bell number in len(factors),
    # even though almost all set partitions collapse to the same (unlabelled)
    # exponent pattern.  Accumulate those patterns as each labelled factor is
    # inserted.  Inserting e either creates a new block, or joins one of the
    # existing blocks; equal existing block sizes are deliberately visited
    # with their multiplicity.  Thus the coefficient remains exactly the
    # number of labelled set partitions giving the pattern, while the running
    # state has only partition-number size.
    states: dict[tuple[int, ...], int] = {(): 1}
    for exponent in factors:
        nxt: dict[tuple[int, ...], int] = {}
        for pattern, coefficient in states.items():
            new_block = tuple(sorted(pattern + (exponent,), reverse=True))
            nxt[new_block] = nxt.get(new_block, 0) + coefficient
            for block in range(len(pattern)):
                merged = list(pattern)
                merged[block] += exponent
                merged_pattern = tuple(sorted(merged, reverse=True))
                nxt[merged_pattern] = nxt.get(merged_pattern, 0) + coefficient
        states = nxt
    return tuple(states.items())


def grouped_simplex_monomial(alpha, beta, r, n, v, c):
    """Integral over x,w>=0, sum(x)<=c, sum(x)+sum(w)<=v."""
    if v <= 0:
        return 0.0
    asum = sum(alpha)
    bsum = sum(beta)
    proda = math.prod(math.factorial(a) for a in alpha)
    prodb = math.prod(math.factorial(b) for b in beta)
    if r == 0:
        return prodb * v ** (bsum + n) / math.factorial(bsum + n)
    tmax = min(c, v)
    if tmax <= 0:
        return 0.0
    if n == 0:
        return proda * tmax ** (asum + r) / math.factorial(asum + r)
    p = asum + r - 1
    q = bsum + n
    beta_integral = 0.0
    for h in range(q + 1):
        beta_integral += (
            (-1) ** h
            * math.comb(q, h)
            * v ** (q - h)
            * tmax ** (p + h + 1)
            / (p + h + 1)
        )
    return (
        proda
        / math.factorial(asum + r - 1)
        * prodb
        / math.factorial(bsum + n)
        * beta_integral
    )


@functools.lru_cache(None)
def fixed_monomial_integral(
    large_exp: tuple[int, ...],
    small_exp: tuple[int, ...],
    r: int,
    n: int,
    upper: float,
    delta: float,
    bound: float,
):
    """Integral of one fixed-coordinate monomial over one support stratum."""
    if len(large_exp) > r or len(small_exp) > n:
        return 0.0
    # Pad exponents so subsequent products include unassigned coordinates.
    la = large_exp + (0,) * (r - len(large_exp))
    sb = small_exp + (0,) * (n - len(small_exp))
    c = bound - r * delta if r else math.inf
    if r and c < 0:
        return 0.0
    answer = 0.0

    # Expand (delta+x_i)^a on the large coordinates.
    large_terms = [((), 1.0)]
    for a in la:
        nxt = []
        for exps, coeff in large_terms:
            for h in range(a + 1):
                nxt.append((exps + (h,), coeff * math.comb(a, h) * delta ** (a - h)))
        large_terms = nxt

    assigned_small = len(small_exp)
    for shifted_mask in range(1 << assigned_small):
        shifted_assigned = shifted_mask.bit_count()
        # Expand powers on shifted assigned small coordinates.  Unshifted
        # assigned coordinates keep their original exponent.
        small_terms = [((), 1.0)]
        for i, b in enumerate(small_exp):
            nxt = []
            if (shifted_mask >> i) & 1:
                choices = range(b + 1)
            else:
                choices = (b,)
            for exps, coeff in small_terms:
                for h in choices:
                    extra = math.comb(b, h) * delta ** (b - h) if ((shifted_mask >> i) & 1) else 1.0
                    nxt.append((exps + (h,), coeff * extra))
            small_terms = nxt
        for q_unassigned in range(n - assigned_small + 1):
            shifted = shifted_assigned + q_unassigned
            ie_coeff = (-1) ** shifted * math.comb(n - assigned_small, q_unassigned)
            v = upper - r * delta - shifted * delta
            if v <= 0:
                continue
            for alpha, ca in large_terms:
                for beta_assigned, cb in small_terms:
                    beta = beta_assigned + (0,) * (n - assigned_small)
                    answer += ie_coeff * ca * cb * grouped_simplex_monomial(
                        alpha, beta, r, n, v, c
                    )
    return answer


def power_product_stratum(factors, r, n, support):
    ans = 0.0
    bound = support.bound(r) if r else math.inf
    for pattern, multiplicity in power_sum_patterns(tuple(sorted(factors))):
        blocks = len(pattern)
        for mask in range(1 << blocks):
            large = tuple(pattern[i] for i in range(blocks) if (mask >> i) & 1)
            small = tuple(pattern[i] for i in range(blocks) if not ((mask >> i) & 1))
            ways = falling(r, len(large)) * falling(n, len(small))
            if not ways:
                continue
            ans += multiplicity * ways * fixed_monomial_integral(
                large,
                small,
                r,
                n,
                support.upper,
                support.delta,
                bound,
            )
    return ans


def denominator_matrix(support, labs):
    out = np.zeros((len(labs), len(labs)))
    for i, (part_i, d_i) in enumerate(labs):
        for j in range(i + 1):
            part_j, d_j = labs[j]
            factors = tuple(part_i) + tuple(part_j) + (1,) * (d_i + d_j)
            degree = sum(factors)
            value = 0.0
            for r in range(min(support.k, len(support.bounds)) + 1):
                if r and r * support.delta > min(support.upper, support.bound(r)):
                    continue
                value += math.comb(support.k, r) * power_product_stratum(
                    factors, r, support.k - r, support
                )
            value /= support.upper**degree
            out[i, j] = out[j, i] = value
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--delta", type=float, default=0.028)
    ap.add_argument("--upper", type=float, default=0.2605)
    ap.add_argument(
        "--bounds",
        default="0.15,0.15,0.17,0.17,0.17,0.17,0.17,0.17,0.17",
    )
    ap.add_argument("--degree", type=int, default=4)
    args = ap.parse_args()
    support = Support(args.k, args.delta, args.upper, parse_bounds(args.bounds))
    labs = basis_labels(args.degree)
    mat = denominator_matrix(support, labs)
    scale = mat[0, 0]
    eig = np.linalg.eigvalsh(mat / scale)
    print("DETERMINISTIC FINITE-SUM FLOATING POINT")
    print("basis size", len(labs))
    print("I00", repr(float(scale)))
    print("normalized spectrum", eig)


if __name__ == "__main__":
    main()
