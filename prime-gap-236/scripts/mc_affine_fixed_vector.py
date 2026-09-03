#!/usr/bin/env python3
"""Discovery-only Monte Carlo for a fixed stratum-affine C10 candidate.

The distinguished J coordinate is integrated analytically.  This script is
an independent, deliberately non-rigorous sign/scale diagnostic; no output is
a certificate or an error bound.
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from mc_compare_fixed_orbit_vector import (  # noqa: E402
    cap,
    fixed_values,
    load_vector,
    marginal_components,
    orbit_values,
    residual_integral,
    simplex_batch,
)


def load_multiplier(path: Path, k: int, cutoff: int):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if (raw.get("status") != "exact-stratum-linear-rational-vector" or
            raw.get("rigorous_forms") is not True or
            raw.get("block_direct_bitwise_equal") is not True or
            raw.get("k") != k):
        raise ValueError("multiplier exact-source gates failed")
    labels = raw.get("linear_labels")
    vector = raw.get("rational_vector")
    if labels != [[r, channel] for r in range(16)
                  for channel in ("1", "L", "Z")]:
        raise ValueError("multiplier labels are not canonical")
    if not isinstance(vector, list) or len(vector) != len(labels):
        raise ValueError("multiplier vector is malformed")
    coefficients = np.zeros((k + 1, 3), dtype=np.float64)
    for index, ((r, channel), token) in enumerate(zip(labels, vector,
                                                       strict=True)):
        column = ("1", "L", "Z").index(channel)
        value = float(Fraction(token))
        if column and r > cutoff:
            value = 0.0
        coefficients[r, column] = value
    if not np.all(np.isfinite(coefficients)):
        raise ValueError("multiplier conversion is non-finite")
    return coefficients


def affine_marginal_values(base, bounds, delta, alpha, components,
                           multiplier):
    total = np.sum(base, axis=1)
    residual = 1.0 - total
    room = np.maximum(0.0, alpha - total)
    large_mask = base > delta
    count = np.sum(large_mask, axis=1)
    large_sum = np.sum(base * large_mask, axis=1)
    small_sum = total - large_sum

    small_hi = np.minimum(delta, room)
    small_ok = (count == 0) | (large_sum <= cap(bounds, count))
    small_hi = np.where(small_ok, small_hi, 0.0)
    large_hi = np.minimum(room, cap(bounds, count + 1) - large_sum)
    large_hi = np.maximum(large_hi, delta)

    small_coefficients = multiplier[count]
    large_coefficients = multiplier[count + 1]
    small_constant = (small_coefficients[:, 0] +
                      small_coefficients[:, 1] * large_sum +
                      small_coefficients[:, 2] * small_sum)
    small_slope = small_coefficients[:, 2]
    large_constant = (large_coefficients[:, 0] +
                      large_coefficients[:, 1] * large_sum +
                      large_coefficients[:, 2] * small_sum)
    large_slope = large_coefficients[:, 1]

    partitions = {lam for _, (_, _, lam) in components}
    orbits = orbit_values(base, partitions)
    needed = {(a, power + shift)
              for _, (a, power, _) in components for shift in (0, 1)}
    zero = np.zeros(len(base))
    delta_lower = np.full(len(base), delta)
    small_integrals = {}
    large_integrals = {}
    for a, power in needed:
        small_integrals[(a, power)] = residual_integral(
            residual, zero, small_hi, a, power)
        large_integrals[(a, power)] = residual_integral(
            residual, delta_lower, large_hi, a, power)

    answer = np.zeros(len(base))
    for weight, (a, power, lam) in components:
        orbit = orbits[lam]
        small = (small_constant * small_integrals[(a, power)] +
                 small_slope * small_integrals[(a, power + 1)])
        large = (large_constant * large_integrals[(a, power)] +
                 large_slope * large_integrals[(a, power + 1)])
        answer += weight * orbit * (small + large)
    return answer


def estimate(args, seed, labels, coefficients, components, bounds,
             multiplier):
    rng = np.random.default_rng(seed)
    isum = 0.0
    jsum = 0.0
    isquare = 0.0
    jsquare = 0.0
    accepted = 0
    done = 0
    while done < args.samples:
        take = min(args.batch, args.samples - done)
        points = simplex_batch(rng, take, args.k, args.alpha)
        base_value = fixed_values(points, labels, coefficients)
        large_mask = points > args.delta
        count = np.sum(large_mask, axis=1)
        large_sum = np.sum(points * large_mask, axis=1)
        small_sum = np.sum(points, axis=1) - large_sum
        affine = (multiplier[count, 0] +
                  multiplier[count, 1] * large_sum +
                  multiplier[count, 2] * small_sum)
        mask = (count == 0) | (large_sum <= cap(bounds, count))
        integrand_i = mask * (base_value * affine) ** 2
        isum += float(np.sum(integrand_i))
        isquare += float(np.dot(integrand_i, integrand_i))
        accepted += int(np.sum(mask))

        base = simplex_batch(rng, take, args.k - 1, args.eta)
        marginal = affine_marginal_values(
            base, bounds, args.delta, args.alpha, components, multiplier)
        integrand_j = marginal * marginal
        jsum += float(np.sum(integrand_j))
        jsquare += float(np.dot(integrand_j, integrand_j))
        done += take

    imean = isum / args.samples
    jmean = jsum / args.samples
    factor = (args.k * args.k * args.eta ** (args.k - 1) /
              args.alpha ** args.k)
    quotient = factor * jmean / imean
    # These are plug-in standard errors of the separate sample means only;
    # the displayed quotient has no rigorous enclosure.
    ivar = max(0.0, isquare / args.samples - imean * imean)
    jvar = max(0.0, jsquare / args.samples - jmean * jmean)
    relative_se = ((ivar / args.samples) / (imean * imean) +
                   (jvar / args.samples) / (jmean * jmean)) ** 0.5
    return quotient, quotient * relative_se, imean, jmean, \
        accepted / args.samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--multiplier", type=Path, required=True)
    parser.add_argument("--linear-cutoff", type=int, default=11)
    parser.add_argument("--bounds", default="3/20,3/20,97/625")
    parser.add_argument("--k", type=int, default=48)
    parser.add_argument("--delta", type=float, default=1 / 100)
    parser.add_argument("--alpha", type=float, default=79247 / 300000)
    parser.add_argument("--eta", type=float, default=76247 / 300000)
    parser.add_argument("--samples", type=int, default=100_000)
    parser.add_argument("--batch", type=int, default=5_000)
    parser.add_argument("--replicates", type=int, default=4)
    parser.add_argument("--seed", type=int, default=236)
    args = parser.parse_args()
    if not 0 <= args.linear_cutoff <= 15:
        parser.error("linear cutoff must be in [0,15]")
    labels, coefficients = load_vector(str(args.input))
    components = marginal_components(labels, coefficients, args.k)
    bounds = tuple(float(Fraction(token)) for token in args.bounds.split(","))
    multiplier = load_multiplier(
        args.multiplier, args.k, args.linear_cutoff)
    print("HEURISTIC AFFINE FIXED-VECTOR MONTE CARLO ONLY")
    print("basis/components", len(labels), len(components),
          "samples/replicates", args.samples, args.replicates)
    for replicate in range(args.replicates):
        result = estimate(
            args, args.seed + 1009 * replicate,
            labels, coefficients, components, bounds, multiplier)
        quotient, plugin_se, imean, jmean, acceptance = result
        print("rep", replicate, "quotient", repr(quotient),
              "plugin_se_nonrigorous", repr(plugin_se),
              "Imean", repr(imean), "Jmean", repr(jmean),
              "I_accept", repr(acceptance), flush=True)


if __name__ == "__main__":
    main()
