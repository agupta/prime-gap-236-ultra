#!/usr/bin/env python3

import importlib
import math
import sys
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
D = importlib.import_module("importance_d12_target_v6")
E = importlib.import_module("importance_envelope_v6")
C = importlib.import_module("importance_conditional")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d12_target_v6_gate")


class D12TargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        C.j_envelope_log_density = E.j_envelope_log_density
        cls.source = D.validate_source_equivalence(REPO)
        cls.normalizers = D.load_d12_normalizers(REPO)
        cls.adapter = D.D12WhitenedMultiplierDensity(REPO)

    def test_exact_source_and_integer_copy_are_common_scale_equivalent(self):
        self.assertEqual(self.adapter.d12_source_sha256,
                         D.EXPECTED_HASHES[D.D12_SOURCE_RELATIVE])
        self.assertEqual(self.adapter.d12_integer_sha256,
                         D.EXPECTED_HASHES[D.D12_INTEGER_RELATIVE])
        self.assertEqual(self.adapter.d12_basis_dimension, 272)
        self.assertEqual(self.adapter.d12_degree, 12)
        self.assertGreater(self.source["least_common_denominator"], 0)

    def test_raw_stratum_normalizers_reproduce_unmultiplied_base(self):
        n = self.normalizers
        self.assertEqual(len(n["i_weights"]), 16)
        self.assertEqual(len(n["j_weights"]), 16)
        self.assertEqual(sum(n["i_weights"], Fraction(0)), 1)
        self.assertEqual(sum(n["j_weights"], Fraction(0)), 1)
        self.assertEqual(n["j_scale_to_numerator"], 48)
        self.assertLess(n["relative_errors"]["sum_i_to_raw"],
                        D.SUM_INTERNAL_RELATIVE_TOLERANCE)
        self.assertLess(n["relative_errors"]["48_sum_j_to_raw"],
                        D.SUM_INTERNAL_RELATIVE_TOLERANCE)
        self.assertLess(n["relative_errors"]["raw_i_to_grouped_baseline"],
                        D.BASELINE_RELATIVE_TOLERANCE)
        self.assertGreater(n["base_quotient"], Decimal("0.9709"))
        self.assertLess(n["base_quotient"], Decimal("0.9711"))

    def test_every_stratum_constant_and_j_base_reconstruct_directly(self):
        for r in range(16):
            point = C.randomized_interior_start(
                self.adapter, "I", r, 712_000 + r)
            original_features = self.adapter.i_features_original(point)
            self.assertEqual(
                self.adapter.i_features(point),
                W.apply_transpose(self.adapter.whitening_transform_exact,
                                  original_features))
            self.assertEqual(self.adapter.validate_constant_multiplier(point), 1)
            common = C.randomized_interior_start(
                self.adapter, "J", r, 713_000 + r)
            transformed = self.adapter.j_marginals(common)
            original = self.adapter.j_marginals_original(common)
            self.assertEqual(
                transformed,
                W.apply_transpose(self.adapter.whitening_transform_exact,
                                  original))
            expected_m0 = math.fsum(original[6 * s]
                                    for s in self.adapter.strata)
            observed_m0 = self.adapter.j_m0(common, transformed)
            self.assertAlmostEqual(
                observed_m0, expected_m0,
                delta=512 * math.ulp(1.0) * max(1.0, abs(expected_m0)))
            envelope = E.j_envelope_point(self.adapter, common)
            self.assertIsNotNone(envelope)
            self.assertLessEqual(envelope.nonzero_constant_channels, 2)

    def test_quadratic_transfer_is_excluded_as_target_normalizer(self):
        raw = D.strict_metadata_json(
            (REPO / D.NEGATIVE_TRANSFER_RELATIVE).read_bytes(),
            "negative transfer")
        transferred = D.positive_decimal(raw["quotient"],
                                         "negative transfer quotient")
        self.assertLess(transferred, D.NEGATIVE_TRANSFER_MAXIMUM_QUOTIENT)
        self.assertLess(transferred, self.normalizers["base_quotient"])
        self.assertNotEqual(raw["input_sha256"],
                            self.adapter.d12_source_sha256)

    def test_duplicate_json_and_dependency_mutation_fail_closed(self):
        with self.assertRaises(ValueError):
            D.strict_metadata_json(b'{"a":1,"a":2}', "duplicate fixture")
        original = D.EXPECTED_HASHES[D.RECOVERED_NORMALIZER_RELATIVE]
        D.EXPECTED_HASHES[D.RECOVERED_NORMALIZER_RELATIVE] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                D.load_d12_normalizers(REPO)
        finally:
            D.EXPECTED_HASHES[D.RECOVERED_NORMALIZER_RELATIVE] = original

    def test_target_gate_predeclares_split_cost_and_strict_continuation(self):
        builder_sha = D.sha256_file(G.HERE)
        gate = G.build_gate(
            builder_sha, REPO / G.D4_GATE_RELATIVE)
        self.assertFalse(gate["screen_launch_authorized"])
        self.assertTrue(gate["requires_d4_v6_calibration_pass"])
        self.assertEqual(gate["data_split"]["training_replicates"], [0, 1])
        self.assertEqual(gate["data_split"]["validation_replicates"], [2, 3])
        self.assertFalse(
            gate["data_split"]["candidate_selection_uses_validation"])
        self.assertEqual(gate["cost_gate"]["maximum_projected_wall_seconds"],
                         7200)
        self.assertEqual(
            gate["continuation_rule"][
                "d12_leave_one_chain_quotient_strictly_greater_than"],
            "1.005")
        self.assertEqual(
            gate["continuation_rule"][
                "d12_lower_endpoint_strictly_greater_than"], "1.002")
        schema = gate["scalar_input_schema"]
        self.assertEqual(schema["base_basis_dimension"], 272)
        self.assertEqual(schema["multiplier_dimension"], 96)
        self.assertEqual(schema["multiplier_status"],
                         "exact-stratum-quadratic-rational-vector")
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64, REPO / G.D4_GATE_RELATIVE)


if __name__ == "__main__":
    unittest.main()
