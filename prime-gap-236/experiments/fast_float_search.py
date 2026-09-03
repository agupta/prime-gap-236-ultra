#!/usr/bin/env python3
"""Fast discovery matrices from the exact one-stratum recurrence.

This deliberately monkey-patches only the scalar constructor used by
``exact_integrator``.  All orbit products, branch decompositions, polygon
clipping, and inclusion--exclusion choices are therefore identical to the exact
implementation, while rational arithmetic is replaced by IEEE binary64.  The
output is *never* a certificate.  Its purpose is to choose a small finite basis
whose moments will subsequently be reconstructed with ``Fraction`` arithmetic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
INTEGRATOR_SRC = os.path.join(HERE, "..", "agents", "exact-integrator", "src")
sys.path.insert(0, os.path.abspath(INTEGRATOR_SRC))

import exact_integrator as ei  # noqa: E402


class FastFloat(float):
    """A float constructor accepting Fraction's optional denominator syntax."""

    def __new__(cls, numerator=0, denominator=None):
        if denominator is None:
            return float.__new__(cls, numerator)
        return float.__new__(cls, numerator / denominator)

    @property
    def denominator(self):
        # Only queried for orbit structure constants, whose integrality is
        # established combinatorially and covered by the exact regression suite.
        return 1


def install_fast_scalar() -> None:
    # The recurrence resolves its module-global Q at call time.  Start a fresh
    # process for every run so no exact-valued lru_cache entry can be mixed in.
    ei.Q = FastFloat


def scaled_generalized_eigen(m1: np.ndarray, m2: np.ndarray):
    """Discovery-only generalized eigensolve with rank-revealing whitening."""
    scale = np.sqrt(np.maximum(np.diag(m1), np.finfo(float).tiny))
    a = m1 / scale[:, None] / scale[None, :]
    b = m2 / scale[:, None] / scale[None, :]
    a = (a + a.T) / 2
    b = (b + b.T) / 2

    # Diagonalize the Gram matrix first and discard directions below a relative
    # threshold.  Report the retained rank so an unstable apparent improvement
    # cannot masquerade as evidence.
    av, au = np.linalg.eigh(a)
    cutoff = max(av[-1] * 1e-12, 1e-15)
    keep = av > cutoff
    if not np.any(keep):
        raise ArithmeticError("numerical Gram matrix has no retained direction")
    whiten = au[:, keep] / np.sqrt(av[keep])[None, :]
    reduced = whiten.T @ b @ whiten
    reduced = (reduced + reduced.T) / 2
    vals, vecs = np.linalg.eigh(reduced)
    v_scaled = whiten @ vecs[:, -1]
    vector = v_scaled / scale
    quotient = float(vector @ m2 @ vector / (vector @ m1 @ vector))
    residual = np.linalg.norm(m2 @ vector - quotient * (m1 @ vector))
    return quotient, vector, int(np.count_nonzero(keep)), float(cutoff), float(residual)


def parse_scalar(text: str) -> float:
    if "/" in text:
        p, q = text.split("/", 1)
        return int(p) / int(q)
    return float(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=48)
    ap.add_argument("--degree", type=int, default=4)
    ap.add_argument("--family", choices=("even", "no-ones"), default="no-ones")
    ap.add_argument("--max-length", type=int)
    ap.add_argument("--alpha", default="163/625")
    ap.add_argument("--eta", default="627/2500")
    ap.add_argument("--delta", default="1/50")
    ap.add_argument("--beta1", default="3/20")
    ap.add_argument("--beta2", default="3/20")
    ap.add_argument("--beta3plus", default="17/100")
    ap.add_argument("--output")
    args = ap.parse_args()

    install_fast_scalar()
    basis_fn = ei.even_basis if args.family == "even" else ei.no_ones_basis
    basis = basis_fn(args.degree, args.max_length)
    support = ei.OneStratumSupport(
        args.k,
        *map(parse_scalar, (args.alpha, args.delta, args.eta,
                            args.beta1, args.beta2, args.beta3plus)),
    )

    start = time.perf_counter()
    m1_list, m2_list = support.matrices(basis)
    matrix_seconds = time.perf_counter() - start
    m1 = np.asarray(m1_list, dtype=float)
    m2 = np.asarray(m2_list, dtype=float)
    quotient, vector, rank, cutoff, residual = scaled_generalized_eigen(m1, m2)
    order = np.argsort(-np.abs(vector * np.sqrt(np.maximum(np.diag(m1), 0))))
    result = {
        "rigorous": False,
        "status": "binary64 discovery only",
        "parameters": vars(args),
        "basis_dimension": len(basis),
        "matrix_seconds": matrix_seconds,
        "retained_numerical_rank": rank,
        "gram_cutoff": cutoff,
        "quotient": quotient,
        "residual_norm": residual,
        "basis": basis,
        "vector": vector.tolist(),
        "leverage_order": order.tolist(),
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as out:
            out.write(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
