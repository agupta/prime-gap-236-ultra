#!/usr/bin/env python3

import importlib
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
W = importlib.import_module("importance_whitening_v6")
E = importlib.import_module("importance_envelope_v6")
from importance_density import C10ImportanceDensity
from importance_conditional import randomized_interior_start
from importance_oracle import load_exact_expectation_oracle

ORACLE_PATH = REPO / \
    "agents/exact-integrator/results/c10_stratum_quadratic_cappedopt_D4_exact.json"
VECTOR_PATH = REPO / \
    "agents/exact-integrator/results/c10_capped_D4_decimal55_vector_input.json"


class ExactWhitenedFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_oracle = load_exact_expectation_oracle(ORACLE_PATH)
        cls.oracle = W.transformed_oracle(cls.original_oracle)
        cls.original = C10ImportanceDensity(VECTOR_PATH, ORACLE_PATH)
        cls.adapter = W.WhitenedC10ImportanceDensity(
            VECTOR_PATH, ORACLE_PATH)

    def test_exact_gram_congruence_and_all_active_pivots(self):
        transform = self.oracle["transform"]["matrix"]
        independent_a = W.congruence(
            self.original_oracle["E_I"], transform)
        independent_b = W.congruence(
            self.original_oracle["E_J"], transform)
        self.assertEqual(independent_a, self.oracle["E_I"])
        self.assertEqual(independent_b, self.oracle["E_J"])
        active = []
        for r, channels in self.oracle["transform"][
                "active_by_stratum"].items():
            block_scaled = self.oracle["transform"]["scaled_pivots"][r]
            self.assertTrue(all(Fraction(1) <= x < 4 for x in block_scaled))
            active.extend(6 * r + channel for channel in channels)
        self.assertEqual(len(active), 93)
        for position, i in enumerate(active):
            self.assertGreaterEqual(self.oracle["E_I"][i][i], 1)
            self.assertLess(self.oracle["E_I"][i][i], 4)
            for j in active[:position]:
                self.assertEqual(self.oracle["E_I"][i][j], 0)

    def test_direct_I_features_equal_pointwise_exact_transform(self):
        point = tuple([0.02] * 3 + [0.001] * 45)
        self.assertTrue(self.adapter.i_support(point))
        original = self.original.i_features(point)
        direct = self.adapter.i_features(point)
        expected = W.apply_transpose(
            self.adapter.whitening_transform_exact, original)
        self.assertEqual(direct, expected)
        self.assertTrue(all(math.isfinite(x) for x in direct))
        self.assertEqual(
            sum(x != 0 for x in direct), 6)

    def test_direct_J_marginals_and_physical_m0_recombine(self):
        common = tuple([0.02] * 3 + [0.001] * 44)
        self.assertTrue(self.adapter.j_support(common))
        original = self.original.j_marginals(common)
        direct = self.adapter.j_marginals(common)
        expected = W.apply_transpose(
            self.adapter.whitening_transform_exact, original)
        self.assertEqual(direct, expected)
        old_m0 = self.original.j_m0(common, original)
        new_m0 = self.adapter.j_m0(common, direct)
        self.assertAlmostEqual(old_m0, new_m0, delta=
                               256 * math.ulp(1.0) * max(1, abs(old_m0)))
        envelope = E.j_envelope_point(self.adapter, common)
        self.assertIsNotNone(envelope)
        self.assertLessEqual(envelope.z, envelope.z_bound + 1e-15)
        self.assertLessEqual(envelope.nonzero_constant_channels, 2)

    def test_all_strata_original_vs_direct_transformed_features(self):
        # Exercise every retained I and common-J stratum, including the rare
        # tail blocks where whitening coefficients are largest.  Starts are
        # constructed with the independently frozen original adapter.
        transform = self.adapter.whitening_transform_exact
        for target_index, target in enumerate(("I", "J")):
            for r in range(16):
                point = randomized_interior_start(
                    self.original, target, r,
                    910_000 + 1000 * target_index + r)
                if target == "I":
                    original = self.original.i_features(point)
                    direct = self.adapter.i_features(point)
                else:
                    original = self.original.j_marginals(point)
                    direct = self.adapter.j_marginals(point)
                brute = [math.fsum(
                    float(transform[i][j]) * float(original[i])
                    for i in range(96)) for j in range(96)]
                self.assertEqual(direct, brute)
                self.assertTrue(all(math.isfinite(x) for x in direct))
                active = ({6 * r + i for i in range(6)} if target == "I"
                          else {6 * r + i for i in range(6)} |
                               ({6 * (r + 1) + i for i in range(6)}
                                if r < 15 else set()))
                self.assertTrue(all(value == 0 for index, value in
                                    enumerate(direct)
                                    if index not in active))

    def test_r15_weighted_identity_and_neighbor_is_not_constant(self):
        # At common r=15 only the small distinguished branch exists.  The
        # weighted transformed constant still reconstructs m0 pointwise.
        common = tuple([0.0101] * 15 + [0.0002] * 32)
        self.assertTrue(self.adapter.j_support(common))
        envelope = E.j_envelope_point(self.adapter, common)
        self.assertIsNotNone(envelope)
        constant = envelope.unit_marginals[90]
        weight = self.adapter.base_constant_weights[90]
        self.assertAlmostEqual(envelope.z, (weight * constant) ** 2)
        self.assertNotEqual(envelope.unit_marginals[91], constant)

    def test_singular_and_indefinite_exact_blocks_fail(self):
        for matrix in ([[1, 1], [1, 1]], [[1, 2], [2, 1]]):
            with self.assertRaises(ArithmeticError):
                W.exact_ldlt(matrix)


if __name__ == "__main__":
    unittest.main()
