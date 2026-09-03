#!/usr/bin/env python3
"""Greedy high-degree basis pruning on an exact full-simplex moment matrix.

This is a discovery tool.  It first reconstructs the complete no-part-1 pool
exactly, but then grows a much smaller basis.  At each step every unused
coordinate is ranked by the exact two-dimensional Rayleigh problem on the span
of the current high-precision Ritz vector and that coordinate.  The selected
subspace is reoptimized before the next step.  The final vector is rationalized
and its quotient is evaluated exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal, localcontext
from fractions import Fraction

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "src"))

from exact_integrator import (OneStratumSupport, decimal_generalized_power,
                              exact_quadratic, no_ones_basis)  # noqa: E402
from run_basis import cached_matrices  # noqa: E402


def qarg(text: str) -> Fraction:
    return Fraction(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=48)
    parser.add_argument("--pool-degree", type=int, default=10)
    parser.add_argument("--seed-degree", type=int, default=4)
    parser.add_argument("--target-dimension", type=int, default=40)
    parser.add_argument("--alpha", type=qarg, required=True)
    parser.add_argument("--eta", type=qarg, required=True)
    parser.add_argument("--delta", type=qarg, default=Fraction(1, 50))
    parser.add_argument("--precision", type=int, default=160)
    parser.add_argument("--iterations", type=int, default=350)
    parser.add_argument("--ranking", choices=("augmented", "two-dimensional"),
                        default="augmented")
    parser.add_argument("--rank-precision", type=int, default=90)
    parser.add_argument("--rank-iterations", type=int, default=160)
    parser.add_argument("--rational-denominator", type=int,
                        default=10**24)
    parser.add_argument("--cache", default=os.path.join(HERE, "cache", "greedy.sqlite3"))
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.seed_degree > args.pool_degree:
        parser.error("seed degree exceeds pool degree")
    pool = no_ones_basis(args.pool_degree)
    seed = set(no_ones_basis(args.seed_degree))
    selected = [i for i, label in enumerate(pool) if label in seed]
    target = min(args.target_dimension, len(pool))
    if target < len(selected):
        parser.error("target dimension is smaller than the seed")

    support = OneStratumSupport(args.k, args.alpha, args.delta, args.eta,
                                args.alpha, args.alpha, args.alpha)
    if not support.is_full_simplex():
        parser.error("the pruning proxy must have redundant beta caps")
    integrator_path = os.path.join(HERE, "src", "exact_integrator.py")
    source_hash = hashlib.sha256(open(integrator_path, "rb").read()).hexdigest()
    m1, m2, hits, misses = cached_matrices(
        support, pool, args.cache, source_hash)

    history = []
    final_vector = None
    final_eigen = None
    with localcontext() as ctx:
        ctx.prec = args.precision

        def dec(x: Fraction) -> Decimal:
            return Decimal(x.numerator) / Decimal(x.denominator)

        # Conversion once is much cheaper than converting for every candidate
        # at every greedy step.
        a_full = [[dec(x) for x in row] for row in m1]
        b_full = [[dec(x) for x in row] for row in m2]

        while True:
            aa = [[m1[i][j] for j in selected] for i in selected]
            bb = [[m2[i][j] for j in selected] for i in selected]
            eigen, vector = decimal_generalized_power(
                aa, bb, args.precision, args.iterations)
            final_eigen, final_vector = eigen, vector
            if len(selected) >= target:
                break

            # Current quadratic scalars.  The vector returned by the solver is
            # in the original (unscaled) coordinates.  The two-dimensional
            # mode is inexpensive, but can miss a coordinate whose benefit
            # requires substantial reoptimization of the old coefficients.
            # The default augmented mode solves every one-coordinate enlarged
            # pencil and is therefore the robust ranking.
            av = sum(vector[ii] * a_full[i][j] * vector[jj]
                     for ii, i in enumerate(selected)
                     for jj, j in enumerate(selected))
            bv = sum(vector[ii] * b_full[i][j] * vector[jj]
                     for ii, i in enumerate(selected)
                     for jj, j in enumerate(selected))
            best = None
            selected_set = set(selected)
            for candidate in range(len(pool)):
                if candidate in selected_set:
                    continue
                if args.ranking == "augmented":
                    trial = selected + [candidate]
                    ta = [[m1[i][j] for j in trial] for i in trial]
                    tb = [[m2[i][j] for j in trial] for i in trial]
                    score, _ = decimal_generalized_power(
                        ta, tb, args.rank_precision, args.rank_iterations)
                else:
                    ae = sum(vector[ii] * a_full[i][candidate]
                             for ii, i in enumerate(selected))
                    be = sum(vector[ii] * b_full[i][candidate]
                             for ii, i in enumerate(selected))
                    af = a_full[candidate][candidate]
                    bf = b_full[candidate][candidate]
                    c2 = av * af - ae * ae
                    if c2 <= 0:
                        continue
                    c1 = -(bv * af + bf * av - Decimal(2) * be * ae)
                    c0 = bv * bf - be * be
                    disc = c1 * c1 - Decimal(4) * c2 * c0
                    if disc < 0 and abs(disc) < Decimal(10) ** (-(args.precision // 2)):
                        disc = Decimal(0)
                    if disc < 0:
                        raise ArithmeticError(("negative 2x2 discriminant", pool[candidate], disc))
                    score = (-c1 + disc.sqrt()) / (Decimal(2) * c2)
                item = (score, candidate)
                if best is None or item > best:
                    best = item
            if best is None:
                raise ArithmeticError("no positive-norm extension")
            score, candidate = best
            selected.append(candidate)
            history.append({"dimension": len(selected),
                            "label": [pool[candidate][0], list(pool[candidate][1])],
                            "two_dimensional_score": str(score),
                            "previous_ritz_value": str(eigen)})
            print(len(selected), pool[candidate], score, flush=True)

    assert final_vector is not None and final_eigen is not None
    aa = [[m1[i][j] for j in selected] for i in selected]
    bb = [[m2[i][j] for j in selected] for i in selected]
    rv = [Fraction(x).limit_denominator(args.rational_denominator)
          for x in final_vector]
    den = exact_quadratic(aa, rv)
    num = exact_quadratic(bb, rv)
    record = {
        "parameters": {"k": args.k, "alpha": str(args.alpha),
                       "eta": str(args.eta), "delta": str(args.delta)},
        "pool_degree": args.pool_degree,
        "pool_dimension": len(pool),
        "seed_degree": args.seed_degree,
        "selected_basis": [[pool[i][0], list(pool[i][1])] for i in selected],
        "selected_dimension": len(selected),
        "history": history,
        "cache_hits": hits,
        "cache_misses": misses,
        "decimal_generalized_eigenvalue": str(final_eigen),
        "rational_vector": [str(x) for x in rv],
        "exact_quotient": str(num / den),
        "exact_quotient_decimal": float(num / den),
        "exact_margin": str(num - den),
    }
    rendered = json.dumps(record, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
