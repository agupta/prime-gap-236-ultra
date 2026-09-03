#!/usr/bin/env python3
"""Reconstruct and verify one exact-integrator JSON result without its cache.

The JSON contains only parameters, explicit basis labels, and a rational vector.
This checker rebuilds every matrix entry from ``src/exact_integrator.py`` and
compares the canonical matrix hash before evaluating both quadratic forms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from fractions import Fraction

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "src"))

from exact_integrator import OneStratumSupport, exact_quadratic  # noqa: E402


def matrix_hash(m1, m2):
    digest = hashlib.sha256()
    for name, matrix in (("M1", m1), ("M2", m2)):
        digest.update((name + "\n").encode())
        for row in matrix:
            digest.update(("\t".join(str(x) for x in row) + "\n").encode())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result")
    parser.add_argument("--expect-above", type=Fraction,
                        help="fail unless the exact quotient is above this value")
    args = parser.parse_args()

    with open(args.result, encoding="utf-8") as stream:
        record = json.load(stream)
    required = {"k", "parameters", "basis", "rational_vector",
                "exact_matrices_sha256"}
    missing = required - record.keys()
    if missing:
        raise SystemExit(f"malformed result: missing {sorted(missing)}")

    p = record["parameters"]
    for key in ("alpha", "delta", "eta", "beta1", "beta2", "beta3plus"):
        if key not in p or not isinstance(p[key], str):
            raise SystemExit(f"malformed parameter {key!r}")
    basis = []
    for label in record["basis"]:
        if (not isinstance(label, list) or len(label) != 2 or
                not isinstance(label[0], int) or label[0] < 0 or
                not isinstance(label[1], list) or
                any(not isinstance(x, int) or x <= 0 for x in label[1])):
            raise SystemExit(f"malformed basis label: {label!r}")
        basis.append((label[0], tuple(label[1])))
    if len(basis) != len(set(basis)):
        raise SystemExit("duplicate basis label")
    vector = [Fraction(x) for x in record["rational_vector"]]
    if len(vector) != len(basis):
        raise SystemExit("basis/vector dimension mismatch")

    support = OneStratumSupport(
        int(record["k"]), Fraction(p["alpha"]), Fraction(p["delta"]),
        Fraction(p["eta"]), Fraction(p["beta1"]), Fraction(p["beta2"]),
        Fraction(p["beta3plus"]),
    )
    m1, m2 = support.matrices(basis)
    got_hash = matrix_hash(m1, m2)
    expected_hash = record["exact_matrices_sha256"]
    if got_hash != expected_hash:
        raise SystemExit(f"matrix hash mismatch: {got_hash} != {expected_hash}")

    denominator = exact_quadratic(m1, vector)
    numerator = exact_quadratic(m2, vector)
    if denominator <= 0:
        raise SystemExit(f"nonpositive I quadratic form: {denominator}")
    quotient = numerator / denominator
    margin = numerator - denominator
    if "exact_margin" in record and Fraction(record["exact_margin"]) != margin:
        raise SystemExit("stored exact margin does not match reconstruction")
    if args.expect_above is not None and not quotient > args.expect_above:
        raise SystemExit(f"exact quotient {float(quotient):.17g} is not above "
                         f"{args.expect_above}")

    print(f"MATRIX HASH PASS {got_hash}")
    print(f"I POSITIVE: {denominator > 0}")
    print(f"M2-M1 SIGN: {'positive' if margin > 0 else 'zero' if margin == 0 else 'negative'}")
    print(f"EXACT QUOTIENT (decimal display): {float(quotient):.17g}")
    print(f"EXACT MARGIN: {margin}")


if __name__ == "__main__":
    main()
