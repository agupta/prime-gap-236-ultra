#!/usr/bin/env python3
"""Hostile exact tests for the fused SoA stratum moment product."""

from __future__ import annotations

import copy
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
EI = HERE.parent / "exact-integrator"
sys.path[:0] = [str(HERE), str(EI), str(EI / "src")]

import exact_integrator as ei  # noqa: E402
from stratum_moment_table import StratumMomentTableEvaluator  # noqa: E402
from stratum_moment_table_fused import (  # noqa: E402
    FusedStratumMomentTableEvaluator,
    canonical_schema_bytes,
    canonical_schema_sha256,
    moment_tag_schema,
    validate_moment_tag_schema,
)


class FusedMomentTests(unittest.TestCase):
    @staticmethod
    def fixture():
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        coefficients = [Q(2), Q(-3), Q(5), Q(7)]
        return support, labels, coefficients

    def test_canonical_degree_three_schema_and_mutations(self):
        schema = moment_tag_schema(3)
        self.assertTrue(validate_moment_tag_schema(schema, 3))
        self.assertEqual(len(schema["channels"]), 10)
        self.assertEqual(len(schema["i_tags"]), 28)
        self.assertEqual(len(schema["same_branch_product_tags"]), 10)
        self.assertEqual(len(schema["cross_branch_product_tags"]), 16)
        self.assertEqual(len(schema["same_branch_scalar_tags"]), 115)
        self.assertEqual(len(schema["cross_branch_scalar_tags"]), 180)
        self.assertEqual(
            canonical_schema_sha256(3),
            "320272a9dfb08ab6d12396127de3ff35ffe35c47b4715e4035bc985e67981aad")
        self.assertEqual(canonical_schema_bytes(3),
                         canonical_schema_bytes(3))
        mutations = []
        bad = copy.deepcopy(schema); bad["degree"] = True; mutations.append(bad)
        bad = copy.deepcopy(schema); bad["channels"].reverse(); mutations.append(bad)
        bad = copy.deepcopy(schema); bad["i_tags"].append([0, 0]); mutations.append(bad)
        bad = copy.deepcopy(schema); bad["cross_branch_scalar_tags"][0][0] = True
        mutations.append(bad)
        for value in mutations:
            with self.assertRaises(ValueError):
                validate_moment_tag_schema(value, 3)

    def test_fused_matches_unfused_degree_two_and_three(self):
        support, labels, coefficients = self.fixture()
        for degree in (2, 3):
            unfused = StratumMomentTableEvaluator(
                support, labels, coefficients, Q,
                degree=degree).evaluate_moment_forms()
            fused = FusedStratumMomentTableEvaluator(
                support, labels, coefficients, Q,
                degree=degree).evaluate_moment_forms()
            self.assertEqual(fused["labels"], unfused["labels"])
            self.assertEqual(fused["a_matrix"], unfused["a_matrix"])
            self.assertEqual(fused["b_matrix"], unfused["b_matrix"])
            self.assertEqual(fused["i_moments"], unfused["i_moments"])
            self.assertEqual(fused["j_moments"], unfused["j_moments"])
            self.assertEqual(fused["j_branch_domains"],
                             unfused["j_branch_domains"])
            self.assertEqual(fused["j_logical_moment_products"],
                             unfused["j_moment_products"])
            self.assertEqual(fused["j_scalar_moment_integrals"],
                             unfused["j_scalar_moment_integrals"])
            self.assertEqual(fused["j_fused_traversals"],
                             fused["j_branch_domains"])
            self.assertLess(fused["j_orbit_pair_visits"],
                            fused["j_tagged_polynomial_multiplies"])
            self.assertTrue(validate_moment_tag_schema(
                fused["tag_schema"], degree))

    def test_k1_degree_three_fused_literal_matrix(self):
        delta, cap = Q(1, 10), Q(2, 5)
        support = ei.OneStratumSupport(
            1, Q(1), delta, Q(9, 10), cap, cap, cap)
        evaluator = FusedStratumMomentTableEvaluator(
            support, [(0, ())], [Q(1)], Q, degree=3)
        forms = evaluator.evaluate_moment_forms()
        powers = evaluator.moment_channels

        def integral(lo, hi, exponent):
            return (hi ** (exponent + 1) - lo ** (exponent + 1)) / \
                (exponent + 1)

        def marginal(label):
            r, p = label
            a, b = powers[p]
            return (integral(Q(0), delta, b) if r == 0 and a == 0 else
                    integral(delta, cap, a) if r == 1 and b == 0 else Q(0))

        for i, left in enumerate(forms["labels"]):
            rl, pl = left; al, bl = powers[pl]
            for j, right in enumerate(forms["labels"]):
                rr, pr = right; ar, br = powers[pr]
                expected_i = Q(0)
                if rl == rr == 0 and al + ar == 0:
                    expected_i = integral(Q(0), delta, bl + br)
                elif rl == rr == 1 and bl + br == 0:
                    expected_i = integral(delta, cap, al + ar)
                self.assertEqual(forms["a_matrix"][i][j], expected_i)
                self.assertEqual(forms["b_matrix"][i][j],
                                 marginal(left) * marginal(right))


if __name__ == "__main__":
    unittest.main()
