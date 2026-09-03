#!/usr/bin/env python3
"""Standalone exact verifier for the pinned admissible 48-tuple.

This file intentionally shares no code with ``verify/check_tuple.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Sequence


EXPECTED_SHA256 = "adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9"
EXPECTED_SIZE = 48
EXPECTED_MINIMUM = 0
EXPECTED_MAXIMUM = 236
_INTEGER_LINE = re.compile(rb"(?:0|[1-9][0-9]*)\Z")


class TupleVerificationError(ValueError):
    pass


def parse_canonical_lines(data: bytes) -> list[int]:
    if len(data) > 10_000:
        raise TupleVerificationError("tuple file exceeds 10 KB")
    if not data or not data.endswith(b"\n"):
        raise TupleVerificationError("tuple file must be nonempty and newline-terminated")
    lines = data.splitlines()
    if any(_INTEGER_LINE.fullmatch(line) is None for line in lines):
        raise TupleVerificationError("every tuple line must be a canonical nonnegative decimal integer")
    return [int(line) for line in lines]


def primes_through(limit: int) -> list[int]:
    if limit < 2:
        return []
    primes: list[int] = []
    for candidate in range(2, limit + 1):
        prime = True
        for divisor in primes:
            if divisor * divisor > candidate:
                break
            if candidate % divisor == 0:
                prime = False
                break
        if prime:
            primes.append(candidate)
    return primes


def missing_residue_witnesses(values: Sequence[int]) -> dict[int, int]:
    """Return one omitted residue for every prime that needs checking.

    A tuple of length k automatically omits a class for every prime p>k, so
    generating and checking the primes p<=k is sufficient and finite.
    """
    witnesses: dict[int, int] = {}
    for prime in primes_through(len(values)):
        occupied = {value % prime for value in values}
        missing = next((residue for residue in range(prime) if residue not in occupied), None)
        if missing is None:
            raise TupleVerificationError(f"tuple covers every residue modulo {prime}")
        witnesses[prime] = missing
    return witnesses


def verify_pinned_tuple(path: Path) -> dict[str, object]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TupleVerificationError(f"cannot read tuple: {exc}") from exc
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise TupleVerificationError(f"tuple SHA-256 mismatch: {digest}")
    values = parse_canonical_lines(data)
    if len(values) != EXPECTED_SIZE:
        raise TupleVerificationError(f"expected {EXPECTED_SIZE} entries, found {len(values)}")
    if len(set(values)) != len(values):
        raise TupleVerificationError("tuple entries are not distinct")
    if any(left >= right for left, right in zip(values, values[1:])):
        raise TupleVerificationError("tuple entries must be strictly increasing")
    if min(values) != EXPECTED_MINIMUM or max(values) != EXPECTED_MAXIMUM:
        raise TupleVerificationError("tuple endpoints are not exactly 0 and 236")
    if max(values) - min(values) != EXPECTED_MAXIMUM:
        raise TupleVerificationError("tuple diameter is not exactly 236")
    witnesses = missing_residue_witnesses(values)
    return {
        "tuple_verified": True,
        "sha256": digest,
        "size": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "diameter": max(values) - min(values),
        "missing_residue_witnesses": {str(prime): residue for prime, residue in witnesses.items()},
    }


def main(argv: Sequence[str] | None = None) -> int:
    default_path = Path(__file__).resolve().parent.parent / "sources/admissible_48_236.txt"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tuple_file", nargs="?", type=Path, default=default_path)
    args = parser.parse_args(argv)
    try:
        result = verify_pinned_tuple(args.tuple_file)
    except (TupleVerificationError, ValueError) as exc:
        print(json.dumps({"tuple_verified": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
