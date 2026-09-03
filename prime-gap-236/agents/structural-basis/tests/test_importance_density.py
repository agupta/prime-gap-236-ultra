#!/usr/bin/env python3

import importlib
import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
MOD = importlib.import_module("importance_density")
POINT = importlib.import_module("importance_point_eval")
EXACT_RESULTS = HERE.parents[2] / "exact-integrator" / "results"
PARAMETERS = EXACT_RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json"
D4 = EXACT_RESULTS / "c10_capped_D4_decimal55_vector_input.json"
D12 = EXACT_RESULTS / "hb_c10_fullsimplex_noones_D12_integer_scaled.json"


class ImportanceDensityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d4 = MOD.C10ImportanceDensity(D4, PARAMETERS)

    def test_loads_exact_d4_and_d12_inputs(self):
        self.assertEqual(self.d4.strata, tuple(range(16)))
        self.assertEqual(self.d4.dimension, 96)
        d12 = MOD.C10ImportanceDensity(D12, PARAMETERS)
        self.assertEqual(len(d12.basis), 272)
        self.assertEqual(d12.strata, self.d4.strata)
        self.assertTrue(all(abs(c) <= 1 for c in d12.coefficients))
        self.assertEqual(self.d4.parameter_sha256,
                         "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86")
        self.assertEqual(self.d4.vector_sha256,
                         hashlib.sha256(D4.read_bytes()).hexdigest())

    def test_i_features_and_support(self):
        point = [0.02, 0.03] + [0.001] * 46
        self.assertTrue(self.d4.i_support(point))
        features = self.d4.i_features(point)
        self.assertEqual(sum(x != 0 for x in features), 6)
        offset = 12
        l_value = 0.05 / self.d4.alpha
        z_value = 0.046 / self.d4.alpha
        expected = [1, l_value, z_value, l_value ** 2,
                    l_value * z_value, z_value ** 2]
        for actual, wanted in zip(features[offset:offset + 6], expected):
            self.assertAlmostEqual(actual, wanted, places=14)
        self.assertFalse(self.d4.i_support([self.d4.alpha] + [0.0] * 47))
        with self.assertRaises(ValueError):
            self.d4.i_features([self.d4.alpha] + [0.0] * 47)

    def test_i_density_is_permutation_invariant(self):
        point = [0.02, 0.03] + [0.001] * 46
        permuted = point[17:] + point[:17]
        self.assertAlmostEqual(self.d4.i_log_density(point),
                               self.d4.i_log_density(permuted), places=13)
        self.assertTrue(math.isfinite(self.d4.i_log_density(point)))

    def test_j_ratios_recombine_and_are_permutation_invariant(self):
        common = [0.02, 0.03] + [0.001] * 45
        self.assertTrue(self.d4.j_support(common))
        first = self.d4.j_features(common)
        second = self.d4.j_features(common[11:] + common[:11])
        self.assertAlmostEqual(sum(first[6 * r] for r in range(16)),
                               1.0, places=14)
        self.assertEqual(len(first), 96)
        for left, right in zip(first, second):
            self.assertAlmostEqual(left, right, places=13)
        self.assertTrue(math.isfinite(self.d4.j_log_density(common)))

    def test_j_m0_common_support_and_alpha_normalization(self):
        common = [0.02, 0.03] + [0.001] * 45
        normalized = self.d4.j_marginals(common)
        raw = POINT.marginal_multiplier_vector(
            common, self.d4.basis, self.d4.coefficients,
            self.d4.channels, self.d4.alpha, self.d4.eta,
            self.d4.delta, self.d4.beta, normalize_powers=False,
            evaluator=self.d4.marginal_evaluator)
        for channel, ((_, a, b), value) in enumerate(
                zip(self.d4.channels, raw)):
            self.assertAlmostEqual(
                normalized[channel], value / self.d4.alpha ** (a + b),
                places=14)

        polynomial = POINT.distinguished_polynomial(
            common, self.d4.basis, self.d4.coefficients,
            evaluator=self.d4.marginal_evaluator)
        intervals = POINT.distinguished_intervals(
            common, self.d4.alpha, self.d4.eta, self.d4.delta,
            self.d4.beta)
        direct = math.fsum(
            POINT.integrate_polynomial(polynomial, *interval)
            for interval in intervals if interval is not None)
        self.assertAlmostEqual(self.d4.j_m0(common, normalized), direct,
                               places=14)

    def test_last_active_stratum_and_cutoff(self):
        large = self.d4.delta + 1e-7
        r15 = [large] * 15 + [0.0] * 33
        r16 = [large] * 16 + [0.0] * 32
        self.assertTrue(self.d4.i_support(r15))
        self.assertFalse(self.d4.i_support(r16))
        features = self.d4.i_features(r15)
        self.assertEqual(features[90], 1.0)
        self.assertEqual(sum(x != 0 for x in features[:90]), 0)
        common15 = [large] * 15 + [0.0] * 32
        self.assertTrue(self.d4.j_support(common15))
        marginals = self.d4.j_marginals(common15)
        self.assertTrue(any(x != 0 for x in marginals[90:96]))

    def test_fail_closed_nonfinite_and_dimension_inputs(self):
        self.assertFalse(self.d4.i_support([math.nan] + [0.0] * 47))
        self.assertFalse(self.d4.i_support([0.0] * 47))
        self.assertFalse(self.d4.j_support([math.inf] + [0.0] * 46))
        self.assertFalse(self.d4.j_support([0.0] * 48))
        self.assertFalse(self.d4.i_support([True] + [0.0] * 47))

    def load_mutated_vector(self, mutation):
        raw = json.loads(D4.read_text())
        mutation(raw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vector.json"
            path.write_text(json.dumps(raw))
            return MOD.C10ImportanceDensity(path, PARAMETERS)

    def test_malformed_basis_and_exact_coefficients_fail(self):
        mutations = (
            lambda raw: raw.__setitem__("basis_dimension", 11),
            lambda raw: raw["basis"].__setitem__(1, raw["basis"][0]),
            lambda raw: raw["basis"][0].__setitem__(0, True),
            lambda raw: raw["rational_vector"].__setitem__(0, "2/2"),
            lambda raw: raw["rational_vector"].__setitem__(0, "-0.0"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(
                    (TypeError, ValueError)):
                self.load_mutated_vector(mutation)

    def test_duplicate_json_and_parameter_byte_mutation_fail(self):
        encoded = D4.read_bytes()
        self.assertIn(b'"k": 48', encoded)
        duplicate = encoded.replace(b'"k": 48', b'"k": 48, "k": 48', 1)
        with tempfile.TemporaryDirectory() as directory:
            vector = Path(directory) / "duplicate.json"
            vector.write_bytes(duplicate)
            with self.assertRaises(ValueError):
                MOD.C10ImportanceDensity(vector, PARAMETERS)
            parameter = Path(directory) / "parameter.json"
            parameter.write_bytes(PARAMETERS.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                MOD.C10ImportanceDensity(D4, parameter)


if __name__ == "__main__":
    unittest.main()
