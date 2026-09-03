#!/usr/bin/env python3
"""Low-dimensional exact tests for the independent core-six Ritz solver."""

from __future__ import annotations

import importlib.util
from fractions import Fraction as F
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "independent_core6_ritz", HERE / "solve_core6_pair_ritz_independent.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_exact_ldl_and_generalized_jacobi():
    A = [[F(1), F(0)], [F(0), F(1)]]
    B = [[F(2), F(1)], [F(1), F(2)]]
    L, pivots = M.exact_ldl(A)
    assert L == A and pivots == [F(1), F(1)]
    run = M.solve_precision(A, B, L, pivots, 80)
    assert run["maximum_eigenvalue"] == "3"
    assert run["normalized_eigenvector"] == ["1", "1"]
    assert run["jacobi_offdiagonal_residual"] == "0"
    v = [F(x) for x in run["normalized_eigenvector"]]
    assert M.quadratic(B, v) / M.quadratic(A, v) == 3


def test_nontrivial_ldl_and_indefinite_rejection():
    A = [[F(4), F(2)], [F(2), F(3)]]
    L, pivots = M.exact_ldl(A)
    assert pivots == [F(4), F(2)]
    assert L == [[F(1), F(0)], [F(1, 2), F(1)]]
    try:
        M.exact_ldl([[F(1), F(2)], [F(2), F(1)]])
    except ValueError as exc:
        assert "nonpositive LDL pivot 1" in str(exc)
    else:
        raise AssertionError("indefinite Gram matrix accepted")


def test_polarization_identity_and_factor_convention():
    # The stored B forms are already 48J.  Polarizing a sum therefore needs no
    # additional factor 48 (and no missing factor two).
    A = [[F(5), F(-2)], [F(-2), F(7)]]
    B48 = [[F(11), F(3)], [F(3), F(13)]]
    one = [F(1), F(1)]
    asum, bsum = M.quadratic(A, one), M.quadratic(B48, one)
    assert (asum - A[0][0] - A[1][1]) / 2 == A[0][1]
    assert (bsum - B48[0][0] - B48[1][1]) / 2 == B48[0][1]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_")]
    for test in tests:
        test()
    print(f"PASS {len(tests)}/{len(tests)}")
