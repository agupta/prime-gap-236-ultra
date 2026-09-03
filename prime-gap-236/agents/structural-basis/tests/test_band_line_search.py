#!/usr/bin/env python3
"""Exact/algebraic tests for the two-dimensional projected line search."""

import os
import sys
import unittest
from decimal import Decimal, getcontext

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, "..", "code"))
sys.path.insert(0, CODE)

from band_line_search import rayleigh, solve_projected_line  # noqa: E402


class BandLineSearchTests(unittest.TestCase):
    def setUp(self):
        getcontext().prec = 100

    def test_diagonal_generalized_problem_selects_better_direction(self):
        # A=identity in the two-dimensional projected coordinates and B is
        # diagonal.  Starting at theta is t=0; d is the t=infinity endpoint.
        forms = tuple(map(Decimal, (1, 0, 1, 2, 0, 3)))
        quotient, t, _, feasible = solve_projected_line(forms, 90)
        self.assertEqual(quotient, Decimal(3))
        self.assertIsNone(t)
        self.assertTrue(all(q == rayleigh(*forms, x) for q, x in feasible if x is not None))

    def test_nondiagonal_stationary_root_satisfies_derivative_equation(self):
        forms = tuple(map(Decimal, (5, 1, 3, 4, 2, 7)))
        quotient, t, coefficients, feasible = solve_projected_line(forms, 90)
        self.assertIsNotNone(t)
        c0, c1, c2 = coefficients
        self.assertLess(abs(c0 + c1 * t + c2 * t * t), Decimal("1e-85"))
        self.assertEqual(quotient, max(q for q, _ in feasible))
        self.assertLess(abs(quotient - rayleigh(*forms, t)), Decimal("1e-88"))


if __name__ == "__main__":
    unittest.main()
