#!/usr/bin/env python3
"""Fail-closed verifier for a finite admissible tuple."""

from __future__ import annotations

import argparse
from pathlib import Path


def primes_through(n: int) -> list[int]:
    out: list[int] = []
    for q in range(2, n + 1):
        if all(q % p for p in out if p * p <= q):
            out.append(q)
    return out


def load_tuple(path: Path) -> list[int]:
    values: list[int] = []
    for line_no, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        text = raw.strip()
        if not text:
            continue
        try:
            value = int(text, 10)
        except ValueError as exc:
            raise SystemExit(f"FAIL: non-integer on line {line_no}: {text!r}") from exc
        values.append(value)
    return values


def verify(values: list[int], expected_size: int, expected_diameter: int) -> list[tuple[int, int]]:
    if len(values) != expected_size:
        raise SystemExit(f"FAIL: size {len(values)} != {expected_size}")
    if len(set(values)) != len(values):
        raise SystemExit("FAIL: tuple contains duplicates")
    ordered = sorted(values)
    diameter = ordered[-1] - ordered[0]
    if diameter != expected_diameter:
        raise SystemExit(f"FAIL: diameter {diameter} != {expected_diameter}")

    witnesses: list[tuple[int, int]] = []
    # If q>|H|, |H mod q|<=|H|<q automatically.  It is therefore enough to
    # check primes q<=|H|, including q=|H| when that endpoint is prime.
    for q in primes_through(expected_size):
        occupied = {h % q for h in values}
        missing = sorted(set(range(q)) - occupied)
        if not missing:
            raise SystemExit(f"FAIL: all residue classes are occupied modulo {q}")
        witnesses.append((q, missing[0]))
    return witnesses


def main() -> None:
    default = Path(__file__).resolve().parents[1] / "sources" / "admissible_48_236.txt"
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", type=Path, default=default)
    ap.add_argument("--size", type=int, default=48)
    ap.add_argument("--diameter", type=int, default=236)
    args = ap.parse_args()
    values = load_tuple(args.path)
    witnesses = verify(values, args.size, args.diameter)
    print(f"PASS size={len(values)} min={min(values)} max={max(values)} diameter={max(values)-min(values)}")
    print("missing_residue_witnesses=" + " ".join(f"{q}:{a}" for q, a in witnesses))


if __name__ == "__main__":
    main()

