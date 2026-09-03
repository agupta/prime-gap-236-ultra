#!/usr/bin/env python3
"""Regression for exact counterexamples found in retired Green-v9."""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "exact-projection-engine/green_polygon_moments.py"
SOURCE_SHA256 = \
    "019fecc00727bfdeb62fc3a02277298c6d08543db4d71ce47f049a73bc1d7a0c"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha256(SOURCE) != SOURCE_SHA256:
    raise RuntimeError("counterexample regression source changed")
spec = importlib.util.spec_from_file_location("repaired_green_v9", SOURCE)
if spec is None or spec.loader is None:
    raise ImportError(SOURCE)
G = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = G
spec.loader.exec_module(G)


def main():
    triangle_twice = (
        (Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)),
        (Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)),
    )
    # A five-point star has distinct vertices, so merely rejecting duplicate
    # vertices was not a sufficient repair.
    hull = ((Q(0), Q(0)), (Q(2), Q(0)), (Q(3), Q(1)),
            (Q(1), Q(3)), (Q(-1), Q(1)))
    star = tuple(hull[index] for index in (0, 2, 4, 1, 3))
    zero_area_noncollinear = (
        (Q(5), Q(-2)), (Q(2), Q(1)), (Q(-2), Q(-3)),
        (Q(0), Q(-4)), (Q(-4), Q(4)), (Q(-5), Q(3)))
    failures = []
    for label, polygon in (
            ("repeated triangle", triangle_twice),
            ("distinct star", star),
            ("zero-area noncollinear cycle", zero_area_noncollinear)):
        try:
            G.polygon_monomial_batch_green(polygon, {(0, 0)})
        except ValueError:
            failures.append(label)
        else:
            raise ArithmeticError(f"repaired core accepted {label}")
    print({
        "repaired_source_sha256": SOURCE_SHA256,
        "rejected_exact_counterexamples": failures,
        "historical_failure": (
            "retired cores accepted non-simple positive-winding cycles "
            "or zero-area noncollinear cycles"),
    })


if __name__ == "__main__":
    main()
