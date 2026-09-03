#!/usr/bin/env python3
"""Paired discovery-only Monte Carlo for a two-band fixed polynomial.

This compares the one-band C10 support with a literal Definition-5 two-band
support.  It is deliberately non-rigorous.  The distinguished coordinate is
integrated analytically; the remaining simplex integrals are sampled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

from mc_compare_fixed_orbit_vector import (
    cap,
    fixed_values,
    load_vector,
    marginal_components,
    marginal_values,
    simplex_batch,
)


def parse_bounds(text: str) -> tuple[float, ...]:
    return tuple(float(Fraction(token)) for token in text.split(","))


def estimate(args, seed, labels, coefficients, components, inner, outer):
    rng = np.random.default_rng(seed)
    isum = np.zeros(2)
    jsum = np.zeros(2)
    isquare = np.zeros(2)
    jsquare = np.zeros(2)
    idiff_square = 0.0
    jdiff_square = 0.0
    accepted = np.zeros(2, dtype=np.int64)
    done = 0
    while done < args.samples:
        take = min(args.batch, args.samples - done)

        points = simplex_batch(rng, take, args.k, args.alpha2)
        value = fixed_values(points, labels, coefficients)
        total = np.sum(points, axis=1)
        large_mask = points > args.delta
        count = np.sum(large_mask, axis=1)
        large_sum = np.sum(points * large_mask, axis=1)
        outer_ok = (count == 0) | (large_sum <= cap(outer, count))
        inner_ok = (count == 0) | (large_sum <= cap(inner, count))
        old_mask = outer_ok
        new_mask = np.where(total < args.alpha1, inner_ok, outer_ok)
        ivals = np.asarray((old_mask * value * value,
                            new_mask * value * value))
        isum += np.sum(ivals, axis=1)
        isquare += np.sum(ivals * ivals, axis=1)
        idiff_square += float(np.sum((ivals[1] - ivals[0]) ** 2))
        accepted += (int(np.sum(old_mask)), int(np.sum(new_mask)))

        base = simplex_batch(rng, take, args.k - 1, args.eta2)
        common_total = np.sum(base, axis=1)
        old_marginal = marginal_values(
            base, outer, args.delta, args.alpha2, components)
        outer_at_alpha1 = marginal_values(
            base, outer, args.delta, args.alpha1, components)
        inner_marginal = marginal_values(
            base, inner, args.delta, args.alpha1, components)
        shell_marginal = old_marginal - outer_at_alpha1

        # Literal Definition 5: J_22 and both cross orientations use eta2;
        # only J_11 is cut off at eta1.
        old_j = old_marginal * old_marginal
        new_j = (shell_marginal * shell_marginal
                 + 2.0 * inner_marginal * shell_marginal
                 + (common_total <= args.eta1)
                 * inner_marginal * inner_marginal)
        jvals = np.asarray((old_j, new_j))
        jsum += np.sum(jvals, axis=1)
        jsquare += np.sum(jvals * jvals, axis=1)
        jdiff_square += float(np.sum((jvals[1] - jvals[0]) ** 2))
        done += take

    imean = isum / args.samples
    jmean = jsum / args.samples
    factor = (args.k * args.k * args.eta2 ** (args.k - 1)
              / args.alpha2 ** args.k)
    quotient = factor * jmean / imean
    ivar = np.maximum(0.0, isquare / args.samples - imean * imean)
    jvar = np.maximum(0.0, jsquare / args.samples - jmean * jmean)
    plugin_se = quotient * np.sqrt(
        ivar / args.samples / (imean * imean)
        + jvar / args.samples / (jmean * jmean))
    return {
        "quotients": quotient.tolist(),
        "plugin_se_nonrigorous": plugin_se.tolist(),
        "i_means": imean.tolist(),
        "j_means": jmean.tolist(),
        "i_acceptance": (accepted / args.samples).tolist(),
        "paired_i_difference_second_sum": idiff_square,
        "paired_j_difference_second_sum": jdiff_square,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--inner-bounds", default="181/1000,181/1000,209/1000,109/500")
    parser.add_argument("--outer-bounds", default="3/20,3/20,17/100")
    parser.add_argument("--k", type=int, default=48)
    parser.add_argument("--delta", type=float, default=float(Fraction(7, 250)))
    parser.add_argument("--alpha1", type=float, default=float(Fraction(103, 400)))
    parser.add_argument("--alpha2", type=float, default=float(Fraction(521, 2000)))
    parser.add_argument("--eta1", type=float, default=float(Fraction(97, 400)))
    parser.add_argument("--eta2", type=float, default=float(Fraction(491, 2000)))
    parser.add_argument("--samples", type=int, default=100_000)
    parser.add_argument("--batch", type=int, default=5_000)
    parser.add_argument("--replicates", type=int, default=4)
    parser.add_argument("--seed", type=int, default=236)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not (0 < args.eta1 < args.eta2 < args.alpha1 < args.alpha2):
        parser.error("expected 0 < eta1 < eta2 < alpha1 < alpha2")
    input_bytes = args.input.read_bytes()
    labels, coefficients = load_vector(str(args.input))
    components = marginal_components(labels, coefficients, args.k)
    inner, outer = parse_bounds(args.inner_bounds), parse_bounds(args.outer_bounds)
    records = [estimate(args, args.seed + 1009 * rep, labels, coefficients,
                        components, inner, outer)
               for rep in range(args.replicates)]
    output = {
        "status": "heuristic-two-band-fixed-vector-monte-carlo",
        "rigorous": False,
        "never_implies": ["rigorous integral", "sieve certificate", "H1<=236"],
        "input": str(args.input),
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "labels": ["one_band_C10", "two_band_count_dependent"],
        "parameters": {
            "k": args.k, "delta": repr(args.delta),
            "alpha1": repr(args.alpha1), "alpha2": repr(args.alpha2),
            "eta1": repr(args.eta1), "eta2": repr(args.eta2),
            "inner_bounds": args.inner_bounds,
            "outer_bounds": args.outer_bounds,
        },
        "samples_per_replicate": args.samples,
        "replicates": records,
    }
    rendered = json.dumps(output, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
