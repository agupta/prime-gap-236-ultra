#!/usr/bin/env python3
"""Fail-closed independent checker for an exact degree-band decomposition.

The checker does not use the code which created the decomposition.  It reads the
original explicit basis/vector and the proposed core plus degree bands, parses
every coefficient as a rational number, and proves coefficient-by-coefficient
that the compressed polynomial expands to the original polynomial.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path


def label(raw):
    if not (isinstance(raw, list) and len(raw) == 2 and
            isinstance(raw[0], int) and isinstance(raw[1], list)):
        raise ValueError(f"malformed basis label: {raw!r}")
    a = raw[0]
    lam = tuple(raw[1])
    if a < 0 or any(not isinstance(x, int) or x < 2 for x in lam):
        raise ValueError(f"invalid no-ones label: {raw!r}")
    if any(lam[i] < lam[i + 1] for i in range(len(lam) - 1)):
        raise ValueError(f"partition is not weakly decreasing: {raw!r}")
    return a, lam


def terms_from_entries(entries, where):
    answer = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"label", "coefficient"}:
            raise ValueError(f"malformed {where} entry {index}")
        key = label(entry["label"])
        if key in answer:
            raise ValueError(f"duplicate label {key} in {where}")
        answer[key] = Fraction(entry["coefficient"])
    return answer


def complete_no_ones_basis(degree):
    """Enumerate {(a,lambda): a+|lambda|<=degree}, independently."""
    partitions = set()

    def visit(budget, maximum, current):
        partitions.add(tuple(current))
        for part in range(min(budget, maximum), 1, -1):
            visit(budget - part, part, current + [part])

    visit(degree, degree, [])
    return {(a, lam) for lam in partitions
            for a in range(degree - sum(lam) + 1)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_json")
    parser.add_argument("band_json")
    args = parser.parse_args()

    source_path = Path(args.source_json)
    band_path = Path(args.band_json)
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes)
    bands = json.loads(band_path.read_bytes())

    expected_sha = bands.get("source_sha256")
    actual_sha = hashlib.sha256(source_bytes).hexdigest()
    if expected_sha != actual_sha:
        raise SystemExit(f"SOURCE SHA MISMATCH: {expected_sha} != {actual_sha}")

    raw_basis = source.get("basis")
    raw_vector = source.get("rational_vector")
    if not isinstance(raw_basis, list) or not isinstance(raw_vector, list):
        raise SystemExit("source lacks explicit basis or rational vector")
    if len(raw_basis) != len(raw_vector):
        raise SystemExit("source basis/vector dimension mismatch")
    original = {}
    for index, (raw_label, raw_coefficient) in enumerate(zip(raw_basis, raw_vector)):
        key = label(raw_label)
        if key in original:
            raise SystemExit(f"duplicate source label {key} at index {index}")
        original[key] = Fraction(raw_coefficient)

    source_degree = source.get("degree")
    if not isinstance(source_degree, int) or source_degree < 0:
        raise SystemExit("source degree is missing or invalid")
    expected_basis = complete_no_ones_basis(source_degree)
    if set(original) != expected_basis:
        missing = min(expected_basis - set(original), default=None)
        extra = min(set(original) - expected_basis, default=None)
        raise SystemExit(f"source is not the complete no-ones B_{source_degree}: "
                         f"missing={missing}, extra={extra}")

    core_degree = bands.get("core_degree")
    if not isinstance(core_degree, int) or core_degree < 0:
        raise SystemExit("invalid core_degree")
    reconstructed = terms_from_entries(bands.get("core", []), "core")
    if any(a + sum(lam) > core_degree for a, lam in reconstructed):
        raise SystemExit("core contains a label above core_degree")

    raw_bands = bands.get("bands")
    if not isinstance(raw_bands, dict):
        raise SystemExit("bands is not an object")
    nonempty_band_count = 0
    for raw_degree, entries in raw_bands.items():
        try:
            degree = int(raw_degree)
        except ValueError as error:
            raise SystemExit(f"noninteger band key: {raw_degree!r}") from error
        if str(degree) != raw_degree or degree <= core_degree:
            raise SystemExit(f"invalid band degree {raw_degree!r}")
        block = terms_from_entries(entries, f"band {degree}")
        if not block:
            raise SystemExit(f"empty band {degree}")
        nonempty_band_count += 1
        for key, coefficient in block.items():
            if key[0] + sum(key[1]) != degree:
                raise SystemExit(f"label {key} is in wrong degree band {degree}")
            if key in reconstructed:
                raise SystemExit(f"label {key} occurs in more than one block")
            reconstructed[key] = coefficient

    all_keys = set(original) | set(reconstructed)
    differences = {key: reconstructed.get(key, Fraction(0)) -
                   original.get(key, Fraction(0)) for key in all_keys}
    differences = {key: value for key, value in differences.items() if value}
    if differences:
        first = min(differences)
        raise SystemExit(f"POLYNOMIAL IDENTITY FAILED at {first}: {differences[first]}")

    if bands.get("expanded_term_count") != len(original):
        raise SystemExit("expanded_term_count metadata mismatch")
    expected_dimension = len(reconstructed) if not nonempty_band_count else (
        sum(1 for a, lam in reconstructed if a + sum(lam) <= core_degree) +
        nonempty_band_count)
    if bands.get("compressed_basis_dimension") != expected_dimension:
        raise SystemExit("compressed_basis_dimension metadata mismatch")

    print("DEGREE-BAND IDENTITY PASS")
    print(f"source_sha256={actual_sha}")
    print(f"expanded_terms={len(original)}")
    print(f"complete_no_ones_degree={source_degree}")
    print(f"core_terms={expected_dimension - nonempty_band_count}")
    print(f"bands={nonempty_band_count}")
    print(f"compressed_dimension={expected_dimension}")


if __name__ == "__main__":
    main()
