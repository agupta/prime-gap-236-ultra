#!/usr/bin/env python3
"""Discovery-only Monte Carlo for the piecewise Krylov span {1,L1}.

For the two-radius full-simplex problem

    I(F) = int_{sum t_i <= alpha} F(t)^2 dt,
    J(F) = int_{sum u_i <= eta} (int_0^{alpha-sum u} F(u,t) dt)^2 du,

let L be the self-adjoint operator satisfying <F,LG> = k J(F,G).
The first Krylov function is available pointwise without quadrature:

    (L1)(t) = sum_i (alpha-sum(t)+t_i) 1_{sum(t)-t_i <= eta}.

This script estimates the four normalized moments mu_j=<1,L^j1>/I(1),
j=0,...,3, and solves the resulting 2 by 2 generalized pencil exactly as
a floating-point discovery calculation.  It is not a rigorous integration or
a sieve certificate; its purpose is to decide whether this piecewise basis is
worth an exact implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import numpy as np


def simplex_batch(rng: np.random.Generator, rows: int, dimension: int,
                  radius: float) -> np.ndarray:
    exponential = rng.exponential(1.0, size=(rows, dimension + 1))
    return radius * exponential[:, :dimension] / exponential.sum(
        axis=1, keepdims=True)


def largest_root(a: np.ndarray, b: np.ndarray) -> float:
    chol = np.linalg.cholesky(a)
    left = np.linalg.solve(chol, b)
    whitened = np.linalg.solve(chol, left.T).T
    whitened = (whitened + whitened.T) / 2
    return float(np.linalg.eigvalsh(whitened)[-1])


def one_replicate(args: argparse.Namespace, seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    sum_h = sum_h2 = sum_h4 = 0.0
    sum_m2 = sum_m4 = 0.0
    done = 0
    gap = args.alpha - args.eta
    while done < args.samples:
        take = min(args.batch, args.samples - done)

        point = simplex_batch(rng, take, args.k, args.alpha)
        total = point.sum(axis=1)
        slack = args.alpha - total
        width = slack[:, None] + point
        h = np.sum(width * (width >= gap), axis=1)
        sum_h += float(h.sum())
        sum_h2 += float(np.dot(h, h))
        sum_h4 += float(np.dot(h * h, h * h))

        base = simplex_batch(rng, take, args.k - 1, args.eta)
        base_total = base.sum(axis=1)
        radius = args.alpha - base_total
        # Integrate L1(base,t) over 0 <= t <= radius.  The distinguished
        # width is radius.  For every other coordinate u_j, substitute
        # w=radius+u_j-t and integrate w 1_{w>=gap} exactly.
        clipped = np.maximum(base, gap)
        marginal = (radius * radius + 0.5 * np.sum(
            (radius[:, None] + base) ** 2 - clipped ** 2, axis=1))
        marginal2 = marginal * marginal
        sum_m2 += float(marginal2.sum())
        sum_m4 += float(np.dot(marginal2, marginal2))
        done += take

    mean_h = sum_h / args.samples
    mean_h2 = sum_h2 / args.samples
    mean_m2 = sum_m2 / args.samples
    factor = (args.k * args.k * args.eta ** (args.k - 1)
              / args.alpha ** args.k)

    mu0 = 1.0
    mu1 = mean_h
    mu2 = mean_h2
    mu3 = factor * mean_m2
    a = np.asarray(((mu0, mu1), (mu1, mu2)))
    b = np.asarray(((mu1, mu2), (mu2, mu3)))
    root = largest_root(a, b)

    # Independent exact identity for mu1/I(1) catches scaling or support
    # mistakes: kJ(1)/I(1) with a beta integral over the eta simplex.
    r = args.eta / args.alpha
    exact_mu1 = (args.k * args.k * (args.k - 1) * args.alpha
                 * (r ** (args.k - 1) / (args.k - 1)
                    - 2 * r ** args.k / args.k
                    + r ** (args.k + 1) / (args.k + 1)))
    var_h = max(0.0, mean_h2 - mean_h * mean_h)
    var_h2 = max(0.0, sum_h4 / args.samples - mean_h2 * mean_h2)
    var_m2 = max(0.0, sum_m4 / args.samples - mean_m2 * mean_m2)
    return {
        "seed": seed,
        "normalized_moments": [mu0, mu1, mu2, mu3],
        "mu1_exact_identity": exact_mu1,
        "mu1_sampling_error": mu1 - exact_mu1,
        "largest_generalized_root": root,
        "plugin_standard_errors": {
            "mu1": (var_h / args.samples) ** 0.5,
            "mu2": (var_h2 / args.samples) ** 0.5,
            "mu3": factor * (var_m2 / args.samples) ** 0.5,
        },
        "I_gram_determinant": float(np.linalg.det(a)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=48)
    parser.add_argument("--alpha", type=float,
                        default=float(Fraction(103, 400)))
    parser.add_argument("--eta", type=float,
                        default=float(Fraction(97, 400)))
    parser.add_argument("--samples", type=int, default=1_000_000)
    parser.add_argument("--batch", type=int, default=10_000)
    parser.add_argument("--replicates", type=int, default=4)
    parser.add_argument("--seed", type=int, default=236)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.k < 2 or not (0 < args.eta < args.alpha):
        parser.error("require k>=2 and 0<eta<alpha")
    if args.samples <= 0 or args.batch <= 0 or args.replicates <= 0:
        parser.error("sample, batch, and replicate counts must be positive")
    records = [one_replicate(args, args.seed + 1009 * index)
               for index in range(args.replicates)]
    result = {
        "status": "heuristic-piecewise-krylov-l1-monte-carlo",
        "rigorous": False,
        "never_implies": ["rigorous integral", "sieve certificate", "H1<=236"],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parameters": {"k": args.k, "alpha": repr(args.alpha),
                       "eta": repr(args.eta)},
        "samples_per_replicate": args.samples,
        "replicates": records,
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
