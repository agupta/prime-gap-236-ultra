#!/usr/bin/env python3
"""Discovery-only channel-pruning scan for an exact D2 stratum artifact.

Constants are retained in every stratum.  Affine L/Z channels are retained up
to ``--affine-cutoff`` (or the scanned cutoff if omitted), and quadratic
L^2/LZ/Z^2 channels are added through each scanned cutoff.  The calculation is
only a float64 Gram-whitened ranking diagnostic; the input exact artifact and
the selected D12 run remain the sources of any rigorous quadratic forms.
"""

from __future__ import annotations

import argparse
import ast
import json
from fractions import Fraction
from pathlib import Path

import numpy as np


CHANNELS = {"1": 0, "L": 1, "Z": 2, "L^2": 3, "LZ": 4, "Z^2": 5}


def load_matrices(path: Path):
    raw = json.loads(path.read_text())
    if raw.get("status") != "exact-stratum-quadratic-rational-vector":
        raise ValueError("unexpected input status")
    if not raw.get("rigorous_forms") or not raw.get("block_direct_bitwise_equal"):
        raise ValueError("input exact-form gates did not pass")
    labels = [(int(r), CHANNELS[name]) for r, name in raw["quadratic_labels"]]
    if len(labels) != len(set(labels)):
        raise ValueError("duplicate labels")
    positions = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    gram = np.zeros((n, n), dtype=float)
    rayleigh = np.zeros((n, n), dtype=float)
    for text_r, block in raw["i_blocks"].items():
        r = int(text_r)
        if len(block) != 6 or any(len(row) != 6 for row in block):
            raise ValueError("malformed I block")
        for i in range(6):
            for j in range(6):
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
    positive = diagonal > 0
    a = a[np.ix_(positive, positive)]
    b = b[np.ix_(positive, positive)]
    diagonal = diagonal[positive]
    a = a / diagonal[:, None] / diagonal[None, :]
    b = b / diagonal[:, None] / diagonal[None, :]
    values, vectors = np.linalg.eigh((a + a.T) / 2)
    keep = values > cutoff * values.max()
    if not np.any(keep):
        raise ArithmeticError("cutoff discarded the full Gram space")
    whitening = vectors[:, keep] / np.sqrt(values[keep])[None, :]
    reduced = whitening.T @ b @ whitening
    value = np.linalg.eigvalsh((reduced + reduced.T) / 2)[-1]
    return float(value), int(np.count_nonzero(keep))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--gram-cutoff", type=float, default=1e-12)
    parser.add_argument("--affine-cutoff", type=int,
                        help="retain L/Z through this R; default follows the scan")
    args = parser.parse_args()
    if not 0 < args.gram_cutoff < 1:
        parser.error("Gram cutoff must lie in (0,1)")
    labels, gram, rayleigh = load_matrices(args.artifact)
    max_r = max(r for r, _ in labels)
    if args.affine_cutoff is not None and not 0 <= args.affine_cutoff <= max_r:
        parser.error("affine cutoff lies outside the stratum range")
    print("quadratic_cutoff\taffine_cutoff\tquotient\tcoordinates\tretained_rank")
    for quadratic_cutoff in range(max_r + 1):
        affine_cutoff = (quadratic_cutoff if args.affine_cutoff is None
                         else args.affine_cutoff)
        indices = [
            i for i, (r, channel) in enumerate(labels)
            if (channel == 0 or
                (channel in (1, 2) and r <= affine_cutoff) or
                (channel in (3, 4, 5) and r <= quadratic_cutoff))
        ]
        value, rank = top_value(gram, rayleigh, indices, args.gram_cutoff)
        print(f"{quadratic_cutoff}\t{affine_cutoff}\t{value:.17g}\t"
              f"{len(indices)}\t{rank}")


if __name__ == "__main__":
    main()
