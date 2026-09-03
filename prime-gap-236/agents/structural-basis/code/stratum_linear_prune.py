#!/usr/bin/env python3
"""Discovery-only high-stratum pruning scan for an exact D1 artifact.

The input matrices are serialized exact rationals produced by
``stratum_linear.py``.  This script does not certify an optimum: it converts
them to float64, whitens the Gram form, and reports how much of the observed
affine-stratum gain survives when L/Z channels above a cutoff are omitted.
It is a reproducible cost-selection diagnostic for a later D12 run.
"""

from __future__ import annotations

import argparse
import ast
import json
from fractions import Fraction
from pathlib import Path

import numpy as np


CHANNEL = {"1": 0, "L": 1, "Z": 2}


def load_matrices(path: Path):
    raw = json.loads(path.read_text())
    if raw.get("status") != "exact-stratum-linear-rational-vector":
        raise ValueError("unexpected input status")
    if not raw.get("rigorous_forms") or not raw.get("block_direct_bitwise_equal"):
        raise ValueError("input exact-form gates did not pass")
    labels = [(int(r), CHANNEL[name]) for r, name in raw["linear_labels"]]
    if len(labels) != len(set(labels)):
        raise ValueError("duplicate labels")
    positions = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    gram = np.zeros((n, n), dtype=float)
    rayleigh = np.zeros((n, n), dtype=float)
    for text_r, block in raw["i_blocks"].items():
        r = int(text_r)
        if len(block) != 3 or any(len(row) != 3 for row in block):
            raise ValueError("malformed I block")
        for i in range(3):
            for j in range(3):
                gram[positions[(r, i)], positions[(r, j)]] = float(
                    Fraction(block[i][j]))
    k = int(raw["k"])
    for text_key, text_value in raw["j_entries"].items():
        left, right = ast.literal_eval(text_key)
        if left not in positions or right not in positions:
            raise ValueError("J label outside dense basis")
        i, j = positions[left], positions[right]
        value = k * float(Fraction(text_value))
        rayleigh[i, j] += value
        if i != j:
            rayleigh[j, i] += value
    return labels, gram, rayleigh


def top_value(gram, rayleigh, indices, cutoff):
    a = gram[np.ix_(indices, indices)]
    b = rayleigh[np.ix_(indices, indices)]
    diagonal = np.sqrt(np.diag(a))
    positive_diagonal = diagonal > 0
    a = a[np.ix_(positive_diagonal, positive_diagonal)]
    b = b[np.ix_(positive_diagonal, positive_diagonal)]
    diagonal = diagonal[positive_diagonal]
    a = a / diagonal[:, None] / diagonal[None, :]
    b = b / diagonal[:, None] / diagonal[None, :]
    eigenvalues, eigenvectors = np.linalg.eigh((a + a.T) / 2)
    keep = eigenvalues > cutoff * eigenvalues.max()
    if not np.any(keep):
        raise ArithmeticError("cutoff discarded the full Gram space")
    whitening = eigenvectors[:, keep] / np.sqrt(eigenvalues[keep])
    reduced = whitening.T @ b @ whitening
    value = np.linalg.eigvalsh((reduced + reduced.T) / 2)[-1]
    return float(value), int(np.count_nonzero(keep))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--gram-cutoff", type=float, default=1e-12)
    args = parser.parse_args()
    if not 0 < args.gram_cutoff < 1:
        parser.error("Gram cutoff must lie in (0,1)")
    labels, gram, rayleigh = load_matrices(args.artifact)
    max_r = max(r for r, _ in labels)
    print("cutoff\tquotient\tcoordinates\tretained_rank")
    for cutoff_r in range(max_r + 1):
        indices = [i for i, (r, channel) in enumerate(labels)
                   if channel == 0 or r <= cutoff_r]
        value, rank = top_value(
            gram, rayleigh, indices, args.gram_cutoff)
        print(f"{cutoff_r}\t{value:.17g}\t{len(indices)}\t{rank}")


if __name__ == "__main__":
    main()
