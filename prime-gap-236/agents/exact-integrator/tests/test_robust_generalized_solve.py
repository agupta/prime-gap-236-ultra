#!/usr/bin/env python3
"""Small deterministic tests for the symmetric Decimal pencil solver."""

import os
import sys
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [AGENT, os.path.join(AGENT, "src")]

from robust_generalized_solve import solve_once  # noqa: E402


class RobustGeneralizedSolveTests(unittest.TestCase):
    def test_largest_algebraic_not_largest_magnitude(self):
        # Ordinary power iteration on A^{-1}B converges to -10, but the
        # generalized Rayleigh maximum is the largest algebraic eigenvalue 2.
        a = [[Q(1), Q(0)], [Q(0), Q(1)]]
        b = [[Q(-10), Q(0)], [Q(0), Q(2)]]
        result = solve_once(a, b, 100)
        self.assertEqual(Decimal(result["rayleigh_quotient"]), Decimal(2))
        self.assertEqual(Decimal(result["relative_residual_bound"]), 0)

    def test_nontrivial_gram_matches_closed_form(self):
        a = [[Q(2), Q(1)], [Q(1), Q(2)]]
        b = [[Q(3), Q(0)], [Q(0), Q(1)]]
        result = solve_once(a, b, 120)
        with localcontext() as context:
            context.prec = 100
            expected = (Decimal(4) + Decimal(7).sqrt()) / Decimal(3)
            observed = Decimal(result["rayleigh_quotient"])
            self.assertLess(abs(observed - expected), Decimal("1e-90"))
            self.assertLess(Decimal(result["relative_residual_bound"]),
                            Decimal("1e-90"))


if __name__ == "__main__":
    unittest.main()
