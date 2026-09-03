#!/usr/bin/env python3

import importlib.util
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


SOLVER = Path(__file__).resolve().parents[1]/"code/solve_sparse_pair_core6_ritz.py"


def module():
    spec = importlib.util.spec_from_file_location("core6_ritz_test", SOLVER)
    answer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(answer)
    return answer


class Core6RitzTests(unittest.TestCase):
    def test_exact_ldl_reconstructs_spd(self):
        m = module()
        A = [[Fraction(4), Fraction(2), Fraction(0)],
             [Fraction(2), Fraction(5), Fraction(1)],
             [Fraction(0), Fraction(1), Fraction(3)]]
        lower, pivots = m.exact_ldl_positive(A)
        rebuilt = [[sum(lower[i][k]*pivots[k]*lower[j][k]
                        for k in range(3)) for j in range(3)] for i in range(3)]
        self.assertEqual(rebuilt, A)
        self.assertTrue(all(value > 0 for value in pivots))

    def test_exact_ldl_rejects_indefinite_and_singular(self):
        m = module()
        with self.assertRaises(ValueError):
            m.exact_ldl_positive([[Fraction(1), Fraction(2)],
                                  [Fraction(2), Fraction(1)]])
        with self.assertRaises(ValueError):
            m.exact_ldl_positive([[Fraction(1), Fraction(1)],
                                  [Fraction(1), Fraction(1)]])

    def test_generalized_diagonal_eigenvalue(self):
        m = module()
        A = [[Fraction(2), Fraction(0), Fraction(0)],
             [Fraction(0), Fraction(4), Fraction(0)],
             [Fraction(0), Fraction(0), Fraction(5)]]
        B = [[Fraction(6), Fraction(0), Fraction(0)],
             [Fraction(0), Fraction(4), Fraction(0)],
             [Fraction(0), Fraction(0), Fraction(10)]]
        result = m.solve_generalized(A, B, 100)
        self.assertLess(abs(result["eigenvalue"]-Decimal(3)), Decimal("1e-95"))
        self.assertLess(result["relative_residual"], Decimal("1e-90"))
        self.assertEqual(max(abs(x) for x in result["vector"]), Decimal(1))

    def test_rotated_symmetric_jacobi_and_exact_trial(self):
        m = module()
        A = [[Fraction(2), Fraction(1)], [Fraction(1), Fraction(2)]]
        B = [[Fraction(5), Fraction(2)], [Fraction(2), Fraction(1)]]
        low = m.solve_generalized(A, B, 90)
        high = m.solve_generalized(A, B, 140)
        with localcontext() as context:
            context.prec = 70
            self.assertLess(abs(low["eigenvalue"]-high["eigenvalue"]),
                            Decimal("1e-65"))
        v = [Fraction(str(x)) for x in high["vector"]]
        denominator = m.quadratic(A, v)
        numerator = m.quadratic(B, v)
        self.assertGreater(denominator, 0)
        self.assertGreater(numerator/denominator, Fraction(2))

    def test_unscaled_sum_polarization_factor(self):
        Aii, Ajj, Aij = Fraction(7), Fraction(11), Fraction(-2, 3)
        Bii, Bjj, Bij = Fraction(13), Fraction(17), Fraction(5, 8)
        Asum, Bsum = Aii+Ajj+2*Aij, Bii+Bjj+2*Bij
        self.assertEqual((Asum-Aii-Ajj)/2, Aij)
        self.assertEqual((Bsum-Bii-Bjj)/2, Bij)


if __name__ == "__main__":
    unittest.main()
