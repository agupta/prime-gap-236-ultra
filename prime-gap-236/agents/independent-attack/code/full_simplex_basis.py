#!/usr/bin/env python3
"""Exact matrices for the direct-BV full-simplex support.

Parameters A=1/4 and epsilon=3/400 give F-support radius R=103/400 and
the J base-sum cut V=97/400.  The basis is the normalized power-sum monomial
basis of total degree <=D.  Matrix entries are reconstructed as Fractions from
Dirichlet integrals; only the final generalized eigensolve is floating point.
"""

from __future__ import annotations

import argparse
import functools
import math
import pickle
import sys
from fractions import Fraction as Q
from pathlib import Path

import numpy as np

from deterministic_i import falling, power_sum_patterns
from mc_symmetric_basis import basis_labels


@functools.lru_cache(None)
def simplex_power_integral(factors: tuple[int, ...], n: int, radius: Q) -> Q:
    factors = tuple(sorted(factors))
    degree = sum(factors)
    total = Q(0)
    for pattern, multiplicity in power_sum_patterns(factors):
        blocks = len(pattern)
        if blocks > n:
            continue
        total += (
            multiplicity
            * falling(n, blocks)
            * math.prod(math.factorial(e) for e in pattern)
            * radius ** (degree + n)
            / math.factorial(degree + n)
        )
    return total


@functools.lru_cache(None)
def inner_expansion(part: tuple[int, ...], d: int, radius: Q):
    """Expansion of int_0^(R-u) G(x,t)dt in base power-sum monomials."""
    degree = sum(part) + d
    out: dict[tuple[int, ...], Q] = {}
    length = len(part)
    for mask in range(1 << length):
        chosen_power = sum(part[i] for i in range(length) if (mask >> i) & 1)
        unchosen = tuple(part[i] for i in range(length) if not ((mask >> i) & 1))
        for h in range(d + 1):
            coeff0 = Q(math.comb(d, h), 1)
            q = chosen_power + h + 1
            for a in range(q + 1):
                coeff = (
                    coeff0
                    * (-1) ** a
                    * math.comb(q, a)
                    * radius ** (q - a)
                    / q
                    / radius**degree
                )
                factors = tuple(sorted(unchosen + (1,) * (d - h + a)))
                out[factors] = out.get(factors, Q(0)) + coeff
    return tuple((key, value) for key, value in out.items() if value)


def exact_matrices(k: int, degree: int, radius: Q, cut: Q):
    labs = basis_labels(degree)
    size = len(labs)
    I = [[Q(0) for _ in range(size)] for _ in range(size)]
    J = [[Q(0) for _ in range(size)] for _ in range(size)]
    expansions = [inner_expansion(tuple(part), d, radius) for part, d in labs]
    for i, (parti, di) in enumerate(labs):
        for j in range(i + 1):
            partj, dj = labs[j]
            factors = tuple(parti) + tuple(partj) + (1,) * (di + dj)
            val_i = simplex_power_integral(factors, k, radius) / radius ** sum(factors)
            val_j = Q(0)
            for fi, ci in expansions[i]:
                for fj, cj in expansions[j]:
                    val_j += ci * cj * simplex_power_integral(fi + fj, k - 1, cut)
            I[i][j] = I[j][i] = val_i
            J[i][j] = J[j][i] = val_j
    return labs, I, J


def scaled_float_matrix(M, diagonal):
    n = len(M)
    return np.array(
        [
            [float(M[i][j] / (diagonal[i] * diagonal[j])) for j in range(n)]
            for i in range(n)
        ]
    )


def numerical_quotient(I, J, k):
    diag = [Q(math.isqrt(x.numerator), math.isqrt(x.denominator)) if False else Q(1) for x in []]
    # Exact square roots are generally irrational; compute diagonal scaling as
    # floats first, while every matrix entry itself remains exactly available.
    n = len(I)
    d = np.array([math.sqrt(float(I[i][i])) for i in range(n)])
    Is = np.array([[float(I[i][j]) / (d[i] * d[j]) for j in range(n)] for i in range(n)])
    Js = np.array([[float(k * J[i][j]) / (d[i] * d[j]) for j in range(n)] for i in range(n)])
    evals, evecs = np.linalg.eigh((Is + Is.T) / 2)
    keep = evals > max(1e-13, evals[-1] * 1e-12)
    W = evecs[:, keep] / np.sqrt(evals[keep])
    op = W.T @ Js @ W
    qvals, qvecs = np.linalg.eigh((op + op.T) / 2)
    return qvals[-1], int(keep.sum()), evals, d, W @ qvecs[:, -1]


def high_precision_quotient(I, J, k, dps, vendor):
    if vendor:
        sys.path.insert(0, vendor)
    import mpmath as mp

    mp.mp.dps = dps
    n = len(I)

    def cv(x):
        return mp.mpf(x.numerator) / x.denominator

    diag = [mp.sqrt(cv(I[i][i])) for i in range(n)]
    A = mp.matrix(n)
    B = mp.matrix(n)
    for i in range(n):
        for j in range(n):
            A[i, j] = cv(I[i][j]) / (diag[i] * diag[j])
            B[i, j] = k * cv(J[i][j]) / (diag[i] * diag[j])
    L = mp.cholesky(A)
    Linv = L ** -1
    C = Linv * B * Linv.T
    vals, vecs = mp.eigsy(C)
    z = vecs[:, n - 1]
    scaled = Linv.T * z
    raw = [scaled[i] / diag[i] for i in range(n)]
    norm = max(abs(x) for x in raw)
    raw = [x / norm for x in raw]
    return vals[n - 1], raw


def mp_matrices(k, degree, epsilon: Q, dps, vendor):
    """Build discovery matrices directly in mpmath, avoiding Fraction swell."""
    if vendor:
        sys.path.insert(0, vendor)
    import mpmath as mp

    mp.mp.dps = dps
    epsmp = mp.mpf(epsilon.numerator) / epsilon.denominator
    radius, cut = mp.mpf(1) / 4 + epsmp, mp.mpf(1) / 4 - epsmp
    labs = basis_labels(degree)
    simp_cache = {}

    def simp(factors, n, rad):
        key = (tuple(sorted(factors)), n, str(rad))
        if key in simp_cache:
            return simp_cache[key]
        factors = key[0]
        deg = sum(factors)
        ans = mp.mpf(0)
        for pattern, multiplicity in power_sum_patterns(factors):
            b = len(pattern)
            if b <= n:
                ans += (
                    multiplicity
                    * falling(n, b)
                    * math.prod(math.factorial(e) for e in pattern)
                    * rad ** (deg + n)
                    / math.factorial(deg + n)
                )
        simp_cache[key] = ans
        return ans

    def expansion(part, d):
        deg = sum(part) + d
        out = {}
        for mask in range(1 << len(part)):
            chosen = sum(part[i] for i in range(len(part)) if (mask >> i) & 1)
            unchosen = tuple(part[i] for i in range(len(part)) if not ((mask >> i) & 1))
            for h in range(d + 1):
                q = chosen + h + 1
                for a in range(q + 1):
                    coeff = (
                        math.comb(d, h)
                        * (-1) ** a
                        * math.comb(q, a)
                        * radius ** (q - a)
                        / q
                        / radius**deg
                    )
                    f = tuple(sorted(unchosen + (1,) * (d - h + a)))
                    out[f] = out.get(f, mp.mpf(0)) + coeff
        return [(f, c) for f, c in out.items() if c]

    exps = [expansion(tuple(part), d) for part, d in labs]
    n = len(labs)
    I, J = mp.matrix(n), mp.matrix(n)
    for i, (pi, di) in enumerate(labs):
        for j in range(i + 1):
            pj, dj = labs[j]
            factors = tuple(pi) + tuple(pj) + (1,) * (di + dj)
            iv = simp(factors, k, radius) / radius ** sum(factors)
            jv = mp.mpf(0)
            for fi, ci in exps[i]:
                for fj, cj in exps[j]:
                    jv += ci * cj * simp(fi + fj, k - 1, cut)
            I[i, j] = I[j, i] = iv
            J[i, j] = J[j, i] = jv
    return labs, I, J, mp


def quotient_mp_matrices(I, J, k, mp):
    n = I.rows
    diag = [mp.sqrt(I[i, i]) for i in range(n)]
    A, B = mp.matrix(n), mp.matrix(n)
    for i in range(n):
        for j in range(n):
            A[i, j] = I[i, j] / (diag[i] * diag[j])
            B[i, j] = k * J[i, j] / (diag[i] * diag[j])
    L = mp.cholesky(A)
    Linv = L ** -1
    C = Linv * B * Linv.T
    vals = mp.eigsy(C, eigvals_only=True)
    return vals[n - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--degree", type=int, default=6)
    ap.add_argument("--cache")
    ap.add_argument("--mp-dps", type=int, default=0)
    ap.add_argument("--vendor", default="vendor")
    ap.add_argument("--mp-build", action="store_true")
    ap.add_argument("--epsilon", default="3/400")
    args = ap.parse_args()
    eps = Q(args.epsilon)
    if not (Q(0) < eps < Q(1, 4)):
        raise SystemExit("epsilon must lie strictly between 0 and 1/4")
    radius, cut = Q(1, 4) + eps, Q(1, 4) - eps
    if args.mp_build:
        dps = args.mp_dps or 60
        labs, Imp, Jmp, mp = mp_matrices(args.k, args.degree, eps, dps, args.vendor)
        q = quotient_mp_matrices(Imp, Jmp, args.k, mp)
        print("HIGH-PRECISION DISCOVERY MATRICES AND EIGENSOLVE")
        print("k degree basis", args.k, args.degree, len(labs))
        print("heuristic quotient", q)
        return
    if args.cache and Path(args.cache).exists():
        with open(args.cache, "rb") as fh:
            labs, I, J = pickle.load(fh)
    else:
        labs, I, J = exact_matrices(args.k, args.degree, radius, cut)
        if args.cache:
            with open(args.cache, "wb") as fh:
                pickle.dump((labs, I, J), fh)
    if args.mp_dps:
        q, raw_mp = high_precision_quotient(I, J, args.k, args.mp_dps, args.vendor)
        rank = len(labs)
        raw = [float(x) for x in raw_mp]
        print("EXACT MATRICES; HIGH-PRECISION EIGENSOLVE")
        print("k degree basis rank", args.k, args.degree, len(labs), rank)
        print("heuristic quotient", q)
    else:
        q, rank, spectrum, scales, vector = numerical_quotient(I, J, args.k)
        print("EXACT MATRICES; FLOATING EIGENSOLVE ONLY")
        print("k degree basis rank", args.k, args.degree, len(labs), rank)
        print("heuristic quotient", repr(float(q)))
        print("I correlation spectrum min/max", repr(float(spectrum[0])), repr(float(spectrum[-1])))
        raw = vector / scales
        raw /= max(abs(raw))
    # A moderate-denominator discovery vector, followed by an exact quotient.
    rational = [Q(float(x)).limit_denominator(10**8) for x in raw]
    num = sum(rational[i] * J[i][j] * rational[j] * args.k for i in range(len(labs)) for j in range(len(labs)))
    den = sum(rational[i] * I[i][j] * rational[j] for i in range(len(labs)) for j in range(len(labs)))
    print("rationalized exact quotient", float(num / den))
    print("exact margin numerator sign", (num - den) > 0)
    print("margin", num - den)


if __name__ == "__main__":
    main()
