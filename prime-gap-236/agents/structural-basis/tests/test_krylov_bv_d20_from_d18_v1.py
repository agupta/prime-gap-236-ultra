#!/usr/bin/env python3
"""Small hostile tests for the Decimal A-Krylov refinement engine."""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys


SOURCE = Path(__file__).parents[1] / "code/krylov_bv_d20_from_d18_v1.py"
SPEC = importlib.util.spec_from_file_location("krylov_bv_d20_v1_tested", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def rayleigh(a, b, vector):
    av = [sum(row[j] * vector[j] for j in range(len(vector))) for row in a]
    bv = [sum(row[j] * vector[j] for j in range(len(vector))) for row in b]
    return sum(vector[i] * bv[i] for i in range(len(vector))) / sum(
        vector[i] * av[i] for i in range(len(vector)))


def decimal_matrix(matrix):
    return [[Decimal(x.numerator) / Decimal(x.denominator) for x in row]
            for row in matrix]


def test_jacobi_two_by_two():
    with localcontext() as context:
        context.prec = 100
        value, vector, rotations = MODULE.jacobi_top_symmetric(
            [[Decimal(2), Decimal(1)], [Decimal(1), Decimal(2)]],
            Decimal("1e-80"), 20)
        assert abs(value - Decimal(3)) < Decimal("1e-80")
        assert abs(abs(vector[0]) - abs(vector[1])) < Decimal("1e-80")
        assert rotations > 0


def test_generalized_diagonal_space_recovers_top():
    a = [[Q(int(i == j)) for j in range(3)] for i in range(3)]
    b = [[Q(0) for _ in range(3)] for _ in range(3)]
    b[0][0], b[1][1], b[2][2] = Q(1), Q(3), Q(2)
    trace, vector = MODULE.krylov_refine_decimal(
        a, b, [Q(1), Q(1), Q(1)], 100, 3, 100)
    assert len(trace) == 3
    assert abs(Decimal(trace[-1][1]) - Decimal(3)) < Decimal("1e-75")
    q = rayleigh(
        decimal_matrix(a), decimal_matrix(b), vector)
    assert q > Decimal("2.999999999999999999999999999999999999")


def test_ritz_trace_dominates_seed_and_is_monotone():
    a = [[Q(2), Q(1, 4), Q(0)],
         [Q(1, 4), Q(3), Q(1, 5)],
         [Q(0), Q(1, 5), Q(1)]]
    b = [[Q(1), Q(1, 7), Q(0)],
         [Q(1, 7), Q(5, 2), Q(1, 11)],
         [Q(0), Q(1, 11), Q(6, 5)]]
    seed = [Q(1), Q(-2), Q(3)]
    trace, vector = MODULE.krylov_refine_decimal(
        a, b, seed, 120, 3, 150)
    values = [Decimal(item[1]) for item in trace]
    assert all(y + Decimal("1e-90") >= x for x, y in zip(values, values[1:]))
    with localcontext() as context:
        context.prec = 100
        da = [[Decimal(x.numerator) / Decimal(x.denominator) for x in row]
              for row in a]
        db = [[Decimal(x.numerator) / Decimal(x.denominator) for x in row]
              for row in b]
        dseed = [Decimal(x.numerator) / Decimal(x.denominator) for x in seed]
        assert rayleigh(da, db, vector) + Decimal("1e-80") >= rayleigh(
            da, db, dseed)


def test_rejects_bad_controls_and_dimensions():
    a = [[Q(1)]]
    b = [[Q(2)]]
    for bad_dimension in (0, 2):
        try:
            MODULE.krylov_refine_decimal(a, b, [Q(1)], 100, bad_dimension, 20)
        except ValueError:
            pass
        else:
            raise AssertionError("bad Krylov dimension accepted")
    try:
        MODULE.krylov_refine_decimal(a, b, [], 100, 1, 20)
    except ValueError:
        pass
    else:
        raise AssertionError("seed dimension mismatch accepted")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
    print(f"PASS {len(tests)} tests")
