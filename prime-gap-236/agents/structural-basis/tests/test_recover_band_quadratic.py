#!/usr/bin/env python3
"""Exact algebra tests for one-endpoint band-line recovery."""

import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
ROOT = HERE.parents[2]
sys.path.insert(0, str(CODE))

from recover_band_quadratic import (evaluate_quadratic, exact_quadratic,  # noqa: E402
                                    load_recovery, rank_candidates,
                                    rebind_expected, stationary_roots)


RECOVERY = ROOT / \
    "agents/structural-basis/results/c10_D12_band_sparse_gradient_recovered_v2.json"


class RecoverBandQuadraticTests(unittest.TestCase):
    def synthetic(self):
        theta0 = [Fraction(1) for _ in range(20)]
        theta1 = list(theta0)
        theta1[0] += 1
        a = [Fraction(0) for _ in range(20)]
        b = [Fraction(0) for _ in range(20)]
        b[0] = Fraction(1, 5)
        quadratic = exact_quadratic(
            theta0, a, b, Fraction(1), Fraction(9, 10),
            theta1, Fraction(2), Fraction(5, 2))
        return quadratic

    def test_endpoint_and_stationary_polynomial_reconstruction(self):
        quadratic = self.synthetic()
        self.assertEqual(quadratic["D"], (Fraction(1), Fraction(0), Fraction(1)))
        self.assertEqual(quadratic["N"],
                         (Fraction(9, 10), Fraction(2, 5), Fraction(6, 5)))
        self.assertEqual(quadratic["stationary"],
                         (Fraction(2, 5), Fraction(3, 5), Fraction(-2, 5)))
        self.assertEqual(evaluate_quadratic(quadratic["D"], Fraction(1)), 2)
        self.assertEqual(evaluate_quadratic(quadratic["N"], Fraction(1)),
                         Fraction(5, 2))

    def test_stationary_ranking_finds_projective_maximum(self):
        quadratic = self.synthetic()
        roots = stationary_roots(quadratic["stationary"], 100)
        self.assertEqual({Fraction(str(x)) for x in roots},
                         {Fraction(-1, 2), Fraction(2)})
        ranked = rank_candidates(quadratic, roots, 100)
        self.assertEqual(ranked[0][1], "stationary_0")
        self.assertEqual(ranked[0][0], Fraction(13, 10))
        self.assertEqual(ranked[-1][0], Fraction(4, 5))

    def test_dimension_and_denominator_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            exact_quadratic([Fraction(1)], [Fraction(0)], [Fraction(0)],
                            Fraction(1), Fraction(1), [Fraction(1)],
                            Fraction(1), Fraction(1))
        zero = [Fraction(0) for _ in range(20)]
        with self.assertRaisesRegex(ValueError, "denominators"):
            exact_quadratic(zero, zero, zero, Fraction(0), Fraction(1),
                            zero, Fraction(1), Fraction(1))

    def test_pinned_recovery_halves_are_recontracted(self):
        recovery, theta, a_theta, b_theta = load_recovery(RECOVERY.read_bytes())
        self.assertEqual(len(theta), 20)
        self.assertEqual([2 * x for x in a_theta],
                         [Fraction(x) for x in recovery["grad_denominator"]])
        self.assertEqual([2 * x for x in b_theta],
                         [Fraction(x) for x in recovery["grad_numerator"]])

    def test_postvalidation_dependency_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "dependency"
            path.write_bytes(b"validated")
            expected = __import__("hashlib").sha256(b"validated").hexdigest()
            rebind_expected({path.resolve(): expected})
            path.write_bytes(b"changed before output")
            with self.assertRaisesRegex(ValueError,
                                        "quadratic trusted byte changed"):
                rebind_expected({path.resolve(): expected})


if __name__ == "__main__":
    unittest.main()
