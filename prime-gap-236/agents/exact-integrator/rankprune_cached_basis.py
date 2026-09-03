#!/usr/bin/env python3
"""Rank-pruned float discovery followed by exact rational contraction.

This is deliberately a discovery driver, not an eigenvalue certifier.  It is
useful for ill-conditioned exact Gram pencils where an unscaled float solve is
misleading.  The reported Rayleigh quotient of each stored rational vector is
nevertheless exact: matrices are reconstructed by the pinned integrator and
contracted with ``Fraction`` arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from fractions import Fraction as Q
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from exact_integrator import OneStratumSupport, exact_quadratic  # noqa: E402
from run_basis import cached_matrices  # noqa: E402


def matrix_sha(m1, m2) -> str:
    digest = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        digest.update((name + "\n").encode())
        for row in matrix:
            digest.update(("\t".join(str(x) for x in row) + "\n").encode())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("basis_result_json")
    parser.add_argument("--cache", required=True)
    parser.add_argument("--cutoffs", default="1e-8,1e-10,1e-12,1e-14")
    parser.add_argument("--significant-digits", type=int, default=15)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    raw_bytes = Path(args.basis_result_json).read_bytes()
    raw = json.loads(raw_bytes)
    basis = [(int(a), tuple(int(x) for x in lam)) for a, lam in raw["basis"]]
    if len(basis) != len(set(basis)):
        parser.error("basis contains duplicates")
    params = raw["parameters"]
    source_path = HERE / "src" / "exact_integrator.py"
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if raw.get("integrator_sha256") != source_hash:
        parser.error("basis artifact was produced by a different integrator")
    support = OneStratumSupport(
        int(raw["k"]), Q(params["alpha"]), Q(params["delta"]),
        Q(params["eta"]), Q(params["beta1"]), Q(params["beta2"]),
        Q(params["beta3plus"]),
    )
    m1, m2, hits, misses = cached_matrices(
        support, basis, args.cache, source_hash)

    af = np.array([[float(x) for x in row] for row in m1])
    bf = np.array([[float(x) for x in row] for row in m2])
    scales = np.sqrt(np.diag(af))
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ArithmeticError("nonpositive or nonfinite Gram diagonal")
    aa = af / scales[:, None] / scales[None, :]
    bb = bf / scales[:, None] / scales[None, :]
    aa = (aa + aa.T) / 2
    bb = (bb + bb.T) / 2
    gram_values, gram_vectors = np.linalg.eigh(aa)
    gram_max = gram_values[-1]
    if not np.isfinite(gram_max) or gram_max <= 0:
        raise ArithmeticError("scaled Gram matrix has no positive spectrum")

    candidates = []
    for cutoff in (float(x) for x in args.cutoffs.split(",")):
        if not 0 < cutoff < 1:
            parser.error("every cutoff must lie in (0,1)")
        keep = gram_values > cutoff * gram_max
        if not np.any(keep):
            raise ArithmeticError(f"cutoff {cutoff} retains no directions")
        whitening = gram_vectors[:, keep] / np.sqrt(gram_values[keep])[None, :]
        reduced = whitening.T @ bb @ whitening
        values, vectors = np.linalg.eigh((reduced + reduced.T) / 2)
        scaled_vector = whitening @ vectors[:, -1]
        vector = scaled_vector / scales
        vector /= np.max(np.abs(vector))
        rational = [Q(format(float(x), f".{args.significant_digits}g"))
                    for x in vector]
        denominator = exact_quadratic(m1, rational)
        numerator = exact_quadratic(m2, rational)
        if denominator <= 0:
            raise ArithmeticError(f"cutoff {cutoff} gave nonpositive exact I")
        candidates.append({
            "relative_gram_cutoff": repr(cutoff),
            "retained_rank": int(np.count_nonzero(keep)),
            "heuristic_eigenvalue": repr(float(values[-1])),
            "rational_vector": [str(x) for x in rational],
            "exact_denominator": str(denominator),
            "exact_numerator": str(numerator),
            "exact_margin": str(numerator - denominator),
            "exact_quotient": str(numerator / denominator),
            "exact_quotient_decimal": repr(float(numerator / denominator)),
        })
    winner = max(candidates, key=lambda item: Q(item["exact_quotient"]))
    result = {
        "format": "rank-pruned-exact-vector-v1",
        "eigenvalue_claim_rigorous": False,
        "particular_vector_forms_rigorous": True,
        "k": int(raw["k"]),
        "basis": [[a, list(lam)] for a, lam in basis],
        "basis_dimension": len(basis),
        "parameters": params,
        "source_basis_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "integrator_sha256": source_hash,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "matrix_sha256": matrix_sha(m1, m2),
        "cache_hits": hits,
        "cache_misses": misses,
        "scaled_gram_min_eigenvalue": repr(float(gram_values[0])),
        "scaled_gram_max_eigenvalue": repr(float(gram_max)),
        "significant_digits": args.significant_digits,
        "candidates": candidates,
        "winner": winner,
    }
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "matrix_sha256": result["matrix_sha256"],
        "basis_dimension": result["basis_dimension"],
        "winner_cutoff": winner["relative_gram_cutoff"],
        "winner_rank": winner["retained_rank"],
        "exact_quotient": winner["exact_quotient"],
        "exact_margin_positive": Q(winner["exact_margin"]) > 0,
    }, indent=2))


if __name__ == "__main__":
    main()
