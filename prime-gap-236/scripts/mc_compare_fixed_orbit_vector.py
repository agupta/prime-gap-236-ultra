#!/usr/bin/env python3
"""Paired Monte-Carlo comparison of one fixed symmetric orbit polynomial.

This is discovery code only.  It evaluates the same explicit polynomial on
two one-stratum supports using common simplex samples.  The distinguished
coordinate in J is integrated analytically, so only the remaining k-1
coordinates are sampled.  A positive difference is never a certificate.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXACT_SRC = os.path.join(HERE, "..", "agents", "exact-integrator", "src")
sys.path.insert(0, os.path.abspath(EXACT_SRC))
from exact_integrator import multiply_monomial_orbits  # noqa: E402


def parse_bounds(text: str) -> tuple[float, ...]:
    return tuple(float(Fraction(x)) for x in text.split(","))


def cap(bounds: tuple[float, ...], count: np.ndarray) -> np.ndarray:
    index = np.minimum(np.maximum(count - 1, 0), len(bounds) - 1)
    return np.asarray(bounds)[index]


def simplex_batch(rng, rows: int, dimension: int, radius: float):
    e = rng.exponential(1.0, size=(rows, dimension + 1))
    return radius * e[:, :dimension] / e.sum(axis=1, keepdims=True)


def load_vector(path: str):
    data = json.load(open(path, encoding="utf-8"))
    labels = [(int(a), tuple(int(x) for x in lam))
              for a, lam in data["basis"]]
    coeffs = np.asarray([float(Fraction(x)) for x in data["rational_vector"]])
    if len(labels) != len(coeffs) or len(labels) != len(set(labels)):
        raise ValueError("malformed fixed-vector input")
    return labels, coeffs


def orbit_values(coords: np.ndarray, partitions):
    """Evaluate monomial-orbit symmetric polynomials, not power products."""
    partitions = set(partitions)
    needed = sorted({j for lam in partitions for j in lam})
    ps = {j: np.sum(coords ** j, axis=1) for j in needed}
    values = {(): np.ones(len(coords))}

    def evaluate(lam):
        if lam in values:
            return values[lam]
        first, rest = lam[0], lam[1:]
        product = ps[first] * evaluate(rest)
        expansion = dict(multiply_monomial_orbits((first,), rest))
        target = tuple(sorted(lam, reverse=True))
        coefficient = expansion.pop(target)
        for nu, multiplicity in expansion.items():
            product -= multiplicity * evaluate(nu)
        values[target] = product / coefficient
        return values[target]

    for lam in sorted(partitions, key=lambda x: (len(x), sum(x), x)):
        evaluate(tuple(sorted(lam, reverse=True)))
    return {lam: values[tuple(sorted(lam, reverse=True))] for lam in partitions}


def fixed_values(coords: np.ndarray, labels, coeffs):
    residual = 1.0 - np.sum(coords, axis=1)
    orbits = orbit_values(coords, {lam for _, lam in labels})
    out = np.zeros(len(coords))
    for coefficient, (a, lam) in zip(coeffs, labels):
        out += coefficient * residual ** a * orbits[lam]
    return out


def marginal_components(labels, coeffs, k):
    """Expand P_lambda(u,t) and aggregate (a,t_power,lambda_on_u)."""
    components = defaultdict(float)
    for coefficient, (a, lam) in zip(coeffs, labels):
        if len(lam) < k:
            components[(a, 0, lam)] += coefficient
        for power in sorted(set(lam)):
            remainder = list(lam)
            remainder.remove(power)
            components[(a, power, tuple(remainder))] += coefficient
    return [(weight, key) for key, weight in components.items() if weight]


def residual_integral(residual, lo, hi, a: int, power: int):
    active = hi > lo
    ans = np.zeros_like(residual)
    if not np.any(active):
        return ans
    rr, ll, uu = residual[active], lo[active], hi[active]
    value = np.zeros_like(rr)
    for h in range(a + 1):
        exponent = power + h + 1
        value += ((-1) ** h * math.comb(a, h) * rr ** (a - h) *
                  (uu ** exponent - ll ** exponent) / exponent)
    ans[active] = value
    return ans


def marginal_values(base: np.ndarray, bounds, delta, alpha, components):
    total = np.sum(base, axis=1)
    residual = 1.0 - total
    room = np.maximum(0.0, alpha - total)
    large = base > delta
    count = np.sum(large, axis=1)
    large_sum = np.sum(base * large, axis=1)

    small_hi = np.minimum(delta, room)
    small_ok = (count == 0) | (large_sum <= cap(bounds, count))
    small_hi = np.where(small_ok, small_hi, 0.0)
    large_hi = np.minimum(room, cap(bounds, count + 1) - large_sum)
    large_hi = np.maximum(large_hi, delta)

    partitions = {lam for _, (_, _, lam) in components}
    orbits = orbit_values(base, partitions)
    needed = {(a, power) for _, (a, power, _) in components}
    integrals = {}
    zero = np.zeros(len(base))
    dlo = np.full(len(base), delta)
    for a, power in needed:
        integrals[(a, power)] = (
            residual_integral(residual, zero, small_hi, a, power) +
            residual_integral(residual, dlo, large_hi, a, power)
        )
    out = np.zeros(len(base))
    for weight, (a, power, lam) in components:
        out += weight * orbits[lam] * integrals[(a, power)]
    return out


def estimate(args, seed, labels, coeffs, components, bounds_a, bounds_b):
    rng = np.random.default_rng(seed)
    isum = np.zeros(2)
    jsum = np.zeros(2)
    idiff2 = jdiff2 = 0.0
    accepted = np.zeros(2, dtype=np.int64)
    done = 0
    while done < args.samples:
        take = min(args.batch, args.samples - done)
        points = simplex_batch(rng, take, args.k, args.alpha)
        values = fixed_values(points, labels, coeffs)
        large = points > args.delta
        count = np.sum(large, axis=1)
        large_sum = np.sum(points * large, axis=1)
        ivals = []
        for z, bounds in enumerate((bounds_a, bounds_b)):
            mask = (count == 0) | (large_sum <= cap(bounds, count))
            x = mask * values * values
            isum[z] += np.sum(x)
            accepted[z] += int(np.sum(mask))
            ivals.append(x)
        idiff2 += np.sum((ivals[1] - ivals[0]) ** 2)

        base = simplex_batch(rng, take, args.k - 1, args.eta)
        jvals = []
        for z, bounds in enumerate((bounds_a, bounds_b)):
            marginal = marginal_values(
                base, bounds, args.delta, args.alpha, components)
            x = marginal * marginal
            jsum[z] += np.sum(x)
            jvals.append(x)
        jdiff2 += np.sum((jvals[1] - jvals[0]) ** 2)
        done += take

    factor = args.k * args.k * args.eta ** (args.k - 1) / args.alpha ** args.k
    imean, jmean = isum / args.samples, jsum / args.samples
    quotient = factor * jmean / imean
    # Paired second moments are reported only as diagnostics; quotient error
    # is assessed through independent replicates in the CLI.
    return quotient, imean, jmean, accepted / args.samples, idiff2, jdiff2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--bounds-a", required=True)
    ap.add_argument("--bounds-b", required=True)
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--delta", type=float, default=0.01)
    ap.add_argument("--alpha", type=float, default=79247 / 300000)
    ap.add_argument("--eta", type=float, default=76247 / 300000)
    ap.add_argument("--samples", type=int, default=100000)
    ap.add_argument("--batch", type=int, default=5000)
    ap.add_argument("--replicates", type=int, default=3)
    ap.add_argument("--seed", type=int, default=236)
    args = ap.parse_args()
    labels, coeffs = load_vector(args.input)
    components = marginal_components(labels, coeffs, args.k)
    bounds_a, bounds_b = parse_bounds(args.bounds_a), parse_bounds(args.bounds_b)
    print("HEURISTIC PAIRED FIXED-VECTOR MONTE CARLO ONLY")
    print("basis/components", len(labels), len(components))
    for rep in range(args.replicates):
        result = estimate(args, args.seed + 1009 * rep, labels, coeffs,
                          components, bounds_a, bounds_b)
        q, imean, jmean, accepted, idiff2, jdiff2 = result
        print("rep", rep, "quotients", q.tolist(), "gain", float(q[1] - q[0]))
        print("means I", imean.tolist(), "J", jmean.tolist(),
              "I_accept", accepted.tolist())
        print("paired_difference_second_sums", idiff2, jdiff2)


if __name__ == "__main__":
    main()
