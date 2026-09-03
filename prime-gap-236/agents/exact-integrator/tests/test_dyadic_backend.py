#!/usr/bin/env python3
"""Containment test for the grouped integrator's dyadic backend."""

from __future__ import annotations

import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
ROOT = AGENT.parent.parent


class DyadicBackendTests(unittest.TestCase):
    def test_small_signed_grouped_i_j_contain_exact_values(self):
        # Isolation is intentional: install_dyadic replaces module-global
        # arithmetic hooks and should never contaminate another unit test.
        program = textwrap.dedent(f"""
            import sys
            from fractions import Fraction as Q
            sys.path[:0] = [{str(ROOT)!r}, {str(AGENT)!r},
                            {str(AGENT / 'src')!r}]
            import exact_integrator as ei
            from grouped_fixed_vector import GroupedEvaluator, precompute_orbits
            from dyadic_backend import install_dyadic
            from stratum_linear import StratumLinearEvaluator

            labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
            coefficients = [Q(2), Q(-3), Q(5, 7), Q(-11, 13)]
            params = (3, Q(13, 50), Q(1, 20), Q(6, 25),
                      Q(3, 20), Q(4, 25), Q(17, 100))
            exact_support = ei.OneStratumSupport(*params)
            exact = GroupedEvaluator(
                exact_support, labels, coefficients, Q)
            expected_i, _, _ = exact.evaluate_i()
            expected_j, _, _ = exact.evaluate_j()
            exact_linear = StratumLinearEvaluator(
                exact_support, labels, coefficients, Q)
            maximum_r = max(exact_linear._r_values_i())
            affine = [Q(((-1) ** (r + p)) * (2 * r + p + 1),
                        r + p + 2)
                      for r in range(maximum_r + 1) for p in range(3)]
            expected_affine = exact_linear.evaluate_direct(affine)[:2]

            # Deliberately leave scalar-dependent method caches warm.  The
            # backend must clear them because exact and interval supports are
            # numerically equal cache keys.
            exact_support._branch_constraints(1, 0, 'Sdelta')
            exact_support._marginal_poly(1, 0, 'Sdelta', 0, 0)

            orbit_table = precompute_orbits(labels, 3)
            scalar = install_dyadic(orbit_table, precision=192,
                                     shadow_bits=96)
            mutated_key = next(iter(orbit_table))
            orbit_table[mutated_key] = ()
            support = ei.OneStratumSupport(
                3, *[scalar(x.numerator, x.denominator) for x in params[1:]])
            before_branch = ei.OneStratumSupport._branch_constraints.cache_info()
            constraints = support._branch_constraints(1, 0, 'Sdelta')
            after_branch = ei.OneStratumSupport._branch_constraints.cache_info()
            before_marginal = ei.OneStratumSupport._marginal_poly.cache_info()
            marginal = support._marginal_poly(1, 0, 'Sdelta', 0, 0)
            after_marginal = ei.OneStratumSupport._marginal_poly.cache_info()
            if after_branch.misses != before_branch.misses + 1:
                raise SystemExit('interval branch constraints reused an old cache')
            if after_marginal.misses != before_marginal.misses + 1:
                raise SystemExit('interval marginal reused an old cache')
            if not all(type(value).__name__ == 'DyadicInterval'
                       for plane in constraints for value in plane):
                raise SystemExit(('non-interval constraint after install', constraints))
            if not all(type(value).__name__ == 'DyadicInterval'
                       for _, value in marginal):
                raise SystemExit(('non-interval marginal after install', marginal))
            vector = [scalar(x.numerator, x.denominator)
                      for x in coefficients]
            enclosed = GroupedEvaluator(support, labels, vector, scalar)
            got_i, _, _ = enclosed.evaluate_i()
            got_j, _, _ = enclosed.evaluate_j()
            if not got_i.contains(expected_i):
                raise SystemExit(('I containment failure', got_i, expected_i))
            if not got_j.contains(expected_j):
                raise SystemExit(('J containment failure', got_j, expected_j))
            if got_i.width_units() <= 0 or got_j.width_units() <= 0:
                raise SystemExit('test did not exercise outward rounding')
            enclosed_linear = StratumLinearEvaluator(
                support, labels, vector, scalar)
            affine_iv = [scalar(x.numerator, x.denominator) for x in affine]
            got_affine = enclosed_linear.evaluate_direct(affine_iv)[:2]
            if not got_affine[0].contains(expected_affine[0]):
                raise SystemExit(('affine I containment failure',
                                  got_affine[0], expected_affine[0]))
            if not got_affine[1].contains(expected_affine[1]):
                raise SystemExit(('affine kJ containment failure',
                                  got_affine[1], expected_affine[1]))
            print('DYADIC GROUPED CONTAINMENT PASS')
        """)
        result = subprocess.run(
            [sys.executable, "-c", program], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DYADIC GROUPED CONTAINMENT PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
