#!/usr/bin/env python3
"""Monte-Carlo discovery for a power-sum symmetric polynomial basis.

The basis contains

  (sum_i t_i / U)^d * product_{j in lambda}(sum_i t_i^j / U^j),

where lambda is an integer partition with parts >=2 and d+|lambda|<=D.
Uniform-simplex importance sampling gives I and J matrices on Stadlmann's
one-stratum support.  This is strictly a heuristic search tool; it prints
replicate quotients so Monte-Carlo instability is visible.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter

import numpy as np

from numerical_sum_basis import Support, parse_bounds, top_generalized_eigenvalue


def partitions_no_ones(n: int, minimum: int = 2):
    if n == 0:
        yield ()
        return

    def rec(rem, lo, prefix):
        if rem == 0:
            yield tuple(prefix)
        for q in range(lo, rem + 1):
            prefix.append(q)
            yield from rec(rem - q, q, prefix)
            prefix.pop()

    yield from rec(n, minimum, [])


def basis_labels(degree: int):
    labs = []
    for weight in range(degree + 1):
        for part in partitions_no_ones(weight):
            for d in range(degree - weight + 1):
                labs.append((part, d))
    # Empty partition was produced only at weight zero; sort by total degree.
    return sorted(set(labs), key=lambda x: (sum(x[0]) + x[1], x[0], x[1]))


def full_features(coords: np.ndarray, actual: np.ndarray, labs, upper):
    s = actual.sum(axis=1)
    needed = sorted({j for part, _ in labs for j in part})
    ps = {j: (actual**j).sum(axis=1) / upper**j for j in needed}
    vals = np.empty((len(labs), len(actual)))
    for i, (part, d) in enumerate(labs):
        v = (s / upper) ** d
        for j in part:
            v = v * ps[j]
        vals[i] = v
    return vals


def power_integral(lo, hi, exponent):
    ans = np.zeros_like(hi)
    mask = hi > lo
    if np.any(mask):
        ans[mask] = (
            hi[mask] ** (exponent + 1) - lo[mask] ** (exponent + 1)
        ) / (exponent + 1)
    return ans


def interval_feature_integrals(u, base_ps, lo, hi, labs, upper):
    """Integrate all basis functions over t in [lo,hi], vectorized in base."""
    out = np.zeros((len(labs), len(u)))
    for index, (part, d) in enumerate(labs):
        # Expand product_j (P_j+t^j), retaining multiplicities in `part`.
        terms = {0: np.ones_like(u)}
        for j in part:
            nxt = {}
            for exponent, coeff in terms.items():
                nxt[exponent] = nxt.get(exponent, 0) + coeff * base_ps[j]
                nxt[exponent + j] = nxt.get(exponent + j, 0) + coeff
            terms = nxt
        value = np.zeros_like(u)
        for exponent, coeff in terms.items():
            for h in range(d + 1):
                value += (
                    coeff
                    * math.comb(d, h)
                    * u ** (d - h)
                    * power_integral(lo, hi, exponent + h)
                )
        out[index] = value / upper ** (sum(part) + d)
    return out


def inner_features(actual_base, lval, r, labs, support):
    u = actual_base.sum(axis=1)
    needed = sorted({j for part, _ in labs for j in part})
    base_ps = {j: (actual_base**j).sum(axis=1) for j in needed}
    room = support.upper - u
    out = np.zeros((len(labs), len(u)))
    if r == 0:
        small_ok = np.ones(len(u), dtype=bool)
    else:
        small_ok = lval <= support.bound(r) + 2e-15
    small_hi = np.minimum(support.delta, room)
    if np.isscalar(small_ok):
        if small_ok:
            out += interval_feature_integrals(
                u, base_ps, np.zeros_like(u), small_hi, labs, support.upper
            )
    else:
        small_hi = np.where(small_ok, small_hi, -1.0)
        out += interval_feature_integrals(
            u, base_ps, np.zeros_like(u), small_hi, labs, support.upper
        )
    if r + 1 <= len(support.bounds):
        large_hi = np.minimum(room, support.bound(r + 1) - lval)
        out += interval_feature_integrals(
            u,
            base_ps,
            np.full_like(u, support.delta),
            large_hi,
            labs,
            support.upper,
        )
    return out


def simplex_batch(rng, count, dimension, radius):
    expo = rng.exponential(size=(count, dimension + 1))
    return radius * expo[:, :dimension] / expo.sum(axis=1, keepdims=True)


def estimate_matrix(support, labs, samples, batch, seed, kind):
    rng = np.random.default_rng(seed)
    dim = support.k if kind == "I" else support.k - 1
    size = len(labs)
    total = np.zeros((size, size))
    maxr = min(dim, len(support.bounds))
    diagnostics = []
    for r in range(maxr + 1):
        total_cap = support.upper if kind == "I" else support.base_cut()
        radius = total_cap - r * support.delta
        if radius <= 0:
            continue
        acc_outer = np.zeros((size, size))
        accepted = 0
        drawn = 0
        while drawn < samples:
            take = min(batch, samples - drawn)
            coords = simplex_batch(rng, take, dim, radius)
            drawn += take
            if r:
                large = support.delta + coords[:, :r]
                small = coords[:, r:]
                lvals = large.sum(axis=1)
            else:
                large = coords[:, :0]
                small = coords
                lvals = np.zeros(take)
            mask = np.all(small <= support.delta, axis=1)
            if kind == "I" and r:
                mask &= lvals <= support.bound(r)
            if not np.any(mask):
                continue
            accepted += int(mask.sum())
            actual = np.concatenate((large[mask], small[mask]), axis=1)
            if kind == "I":
                vals = full_features(coords[mask], actual, labs, support.upper)
            else:
                # lval varies sample-by-sample; inner_features accepts vector
                # lval and comparisons/upper endpoints remain vectorized.
                vals = inner_features(actual, lvals[mask], r, labs, support)
            acc_outer += vals @ vals.T
        volume = radius**dim / math.factorial(dim)
        weighted = math.comb(dim, r) * volume * acc_outer / samples
        total += weighted
        diagnostics.append((r, accepted / samples, np.max(np.abs(weighted))))
    return (total + total.T) / 2, diagnostics


def one_run(args, seed):
    support = Support(
        args.k, args.delta, args.upper, parse_bounds(args.bounds), args.jcut
    )
    labs = basis_labels(args.degree)
    if args.deterministic_i:
        # Local import avoids a circular import at module load time.
        from deterministic_i import denominator_matrix

        I = denominator_matrix(support, labs)
        idiag = [("exact-formula", 1.0, float(np.max(np.abs(I))))]
    else:
        I, idiag = estimate_matrix(
            support, labs, args.samples, args.batch, seed, "I"
        )
    J, jdiag = estimate_matrix(
        support, labs, args.samples, args.batch, seed + 10_000_019, "J"
    )
    q, rank, spectrum = top_generalized_eigenvalue(I, J, args.k)
    return q, rank, len(labs), idiag, jdiag, spectrum


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
    ap.add_argument("--degree", type=int, default=6)
    ap.add_argument("--samples", type=int, default=100000)
    ap.add_argument("--batch", type=int, default=10000)
    ap.add_argument("--replicates", type=int, default=2)
    ap.add_argument("--seed", type=int, default=236)
    ap.add_argument("--deterministic-i", action="store_true")
    args = ap.parse_args()
    print("HEURISTIC MONTE CARLO ONLY")
    for rep in range(args.replicates):
        q, rank, size, idiag, jdiag, spectrum = one_run(args, args.seed + rep * 1009)
        print("rep quotient rank size", rep, repr(float(q)), rank, size)
        print("I acceptance", [(r, round(a, 5)) for r, a, _ in idiag])
        print("J acceptance", [(r, round(a, 5)) for r, a, _ in jdiag])
        print("I spectrum min/max", repr(float(spectrum[0])), repr(float(spectrum[-1])))


if __name__ == "__main__":
    main()
