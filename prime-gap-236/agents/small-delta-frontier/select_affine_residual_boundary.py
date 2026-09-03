#!/usr/bin/env python3
"""Exact D4 diagnostic selecting the five-coordinate boundary screen.

The diagonal-normalized squared residual is a coordinatewise ranking proxy,
not a norm induced by the full Gram inverse.  Its only mathematical role is
to select a small subspace; the subspace screen itself is valid independently
of this proxy.
"""

import ast
import hashlib
import json
from decimal import Decimal, getcontext
from fractions import Fraction as Q
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "agents/exact-integrator/results/"
          "c10_stratum_linear_cappedopt_D4_exact.json")
SOURCE_SHA = "ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158"
CUTOFF = 11
BOUNDARY = {(11, 0), (11, 1), (11, 2), (12, 0), (13, 0)}
CHANNELS = ("1", "L", "Z")


def main():
    source_bytes = SOURCE.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != SOURCE_SHA:
        raise SystemExit("D4 affine source SHA mismatch")
    raw = json.loads(source_bytes)
    labels = [(int(r), CHANNELS.index(channel))
              for r, channel in raw["linear_labels"]]
    position = {label: i for i, label in enumerate(labels)}
    coefficients = [Q(x) for x in raw["rational_vector"]]
    effective = []
    for i, label in enumerate(labels):
        r, p = label
        if label == (0, 1) or (p and r > CUTOFF):
            coefficients[i] = Q(0)
        else:
            effective.append(label)
    if len(effective) != 39 or not BOUNDARY < set(effective):
        raise SystemExit("effective coordinate set mismatch")
    blocks = {int(r): [[Q(x) for x in row] for row in block]
              for r, block in raw["i_blocks"].items()}
    i_cross = {}
    i_diagonal = {}
    for label in labels:
        r, p = label
        i_cross[label] = sum(
            blocks[r][p][q] * coefficients[position[(r, q)]]
            for q in range(3))
        i_diagonal[label] = blocks[r][p][p]
    j_cross = {label: Q(0) for label in labels}
    for key, value in raw["j_entries"].items():
        left, right = ast.literal_eval(key)
        entry = 48 * Q(value)
        if left == right:
            j_cross[left] += entry * coefficients[position[left]]
        else:
            j_cross[left] += entry * coefficients[position[right]]
            j_cross[right] += entry * coefficients[position[left]]
    denominator = sum(coefficients[position[x]] * i_cross[x]
                      for x in labels)
    numerator = sum(coefficients[position[x]] * j_cross[x]
                    for x in labels)
    quotient = numerator / denominator
    scores = {
        label: (j_cross[label] - quotient * i_cross[label]) ** 2 /
        (denominator * i_diagonal[label])
        for label in effective if i_diagonal[label] > 0
    }
    full = sum(scores.values(), Q(0))
    selected = sum((scores[label] for label in BOUNDARY), Q(0))
    share = selected / full
    getcontext().prec = 80
    dec = lambda x: str(Decimal(x.numerator) / Decimal(x.denominator))
    print("AFFINE RESIDUAL BOUNDARY SELECTION PASS")
    print(f"source_sha256={SOURCE_SHA}")
    print("boundary=" + ",".join(
        f"{r}:{CHANNELS[p]}" for r, p in sorted(BOUNDARY)))
    print(f"baseline_quotient={dec(quotient)}")
    print(f"diagonal_proxy_share={dec(share)}")
    if not share > Q(999998, 1000000):
        raise SystemExit("exact diagonal-proxy share gate failed")
    print("exact_gate=diagonal_proxy_share>999998/1000000")
    print(f"share_numerator_bits={share.numerator.bit_length()}")
    print(f"share_denominator_bits={share.denominator.bit_length()}")


if __name__ == "__main__":
    main()
