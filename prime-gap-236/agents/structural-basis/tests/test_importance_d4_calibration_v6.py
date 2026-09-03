#!/usr/bin/env python3

import importlib
import copy
import math
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
V6 = importlib.import_module("importance_d4_calibration_v6")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d4_calibration_gate_v6")

ORACLE = REPO / V6.REQUIRED_DATA_PATHS[0]
VECTOR = REPO / V6.REQUIRED_DATA_PATHS[1]
WEIGHTS = REPO / V6.REQUIRED_DATA_PATHS[2]


class ExactWhitenedCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V6._patch_v5_runtime()
        cls.oracle = W.load_transformed_oracle(ORACLE)
        cls.adapter = W.WhitenedC10ImportanceDensity(VECTOR, ORACLE)

    def test_conventions_predeclare_direct_sampling_and_continuation(self):
        conventions = V6.expected_conventions()
        whitening = conventions["exact_whitening"]
        self.assertEqual(whitening["transform_sha256"], V6.TRANSFORM_SHA256)
        self.assertTrue(whitening["direct_point_evaluation"])
        self.assertFalse(whitening["postprocess_v5_estimates"])
        self.assertEqual(whitening["rank_tolerance"],
                         "1/1000000000000")
        continuation = V6.expected_continuation_rule()
        self.assertEqual(
            continuation["d12_leave_one_chain_quotient_strictly_greater_than"],
            "1.005")
        self.assertEqual(
            continuation["d12_lower_endpoint_strictly_greater_than"],
            "1.002")

    def test_gate_builder_binds_complete_v6_and_superseded_v5_closure(self):
        builder_sha = V6.v5.sha256_file(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_gate_sha256"], V6.V5_GATE_SHA256)
        self.assertEqual(set(gate["source_hashes"]),
                         set(V6.REQUIRED_SOURCE_PATHS))
        self.assertEqual(set(gate["data_hashes"]),
                         set(V6.REQUIRED_DATA_PATHS))
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_runtime_uses_transformed_adapter_oracle_and_envelope(self):
        self.assertIs(V6.v5.C10ImportanceDensity,
                      W.WhitenedC10ImportanceDensity)
        self.assertIs(V6.v5.load_exact_expectation_oracle,
                      W.load_transformed_oracle)
        self.assertIs(V6.v5.j_envelope_point, V6.j_envelope_point)
        self.assertIs(V6.importance_conditional.j_envelope_log_density,
                      V6.j_envelope_log_density)

    def test_exact_base_and_weight_recombination(self):
        transform = self.oracle["transform"]
        self.assertEqual(transform["sha256"], V6.TRANSFORM_SHA256)
        base = transform["base_weights"]
        constants = [6 * r for r in range(16)]
        for matrix_name in ("E_I", "E_J"):
            matrix = self.oracle[matrix_name]
            value = sum(base[i] * matrix[i][j] * base[j]
                        for i in constants for j in constants)
            self.assertEqual(value, 1)
        gate_stub = {"data_hashes": {
            relative: V6.v5.sha256_file(REPO / relative)
            for relative in V6.REQUIRED_DATA_PATHS}}
        weights = V6.v5.load_stratum_weights(
            WEIGHTS, gate_stub["data_hashes"][V6.REQUIRED_DATA_PATHS[2]],
            prefix="baseline_", j_scale_to_numerator=1)
        self.assertTrue(V6.validate_weight_provenance(
            weights, self.oracle, gate_stub))

    def test_tiny_direct_smoke_records_validate(self):
        records = V6.v5.run_smoke(self.adapter)
        schedule = V6.v5.tiny_smoke_schedule()
        specs = [V6.v5.expected_chain_table()[0],
                 V6.v5.expected_chain_table()[64]]
        self.assertEqual(len(records), 2)
        for record, spec in zip(records, specs):
            V6.v5.validate_chain_record(
                record, spec, schedule, adapter=self.adapter)
            self.assertTrue(math.isfinite(
                V6.v5.parse_float_hex(record["raw_antisymmetry"])))

    def test_rare_signed_I_record_validates_and_raw_mutation_rejects(self):
        schedule = V6.v5.tiny_smoke_schedule()
        spec = V6.v5.expected_chain_table()[60]  # I, r=15, replicate 0.
        record = V6.v5.run_one_chain(self.adapter, spec, schedule)
        self.assertTrue(V6.validate_chain_record(
            record, spec, schedule, adapter=self.adapter))
        self.assertTrue(any(
            V6.v5.parse_float_hex(value) < 0
            for row in record["batch_upper_means"] for value in row))
        corrupted = copy.deepcopy(record)
        column = max(range(len(record["raw_sum"])), key=lambda index: abs(
            V6.v5.parse_float_hex(record["raw_sum"][index])))
        old = V6.v5.parse_float_hex(corrupted["raw_sum"][column])
        bound = V6._i_outer_abs_bounds(self.adapter, 15)[column]
        corrupted["raw_sum"][column] = V6.v5.float_hex(
            old + schedule["retained_samples"] * bound * 1e-5)
        with self.assertRaises(ArithmeticError):
            V6.validate_chain_record(
                corrupted, spec, schedule, adapter=self.adapter)
        corrupted = copy.deepcopy(record)
        old = V6.v5.parse_float_hex(corrupted["raw_second_sum"][column])
        corrupted["raw_second_sum"][column] = V6.v5.float_hex(
            old + schedule["retained_samples"] * bound * bound * 1e-5)
        with self.assertRaises(ArithmeticError):
            V6.validate_chain_record(
                corrupted, spec, schedule, adapter=self.adapter)

    def test_wrong_transform_and_old_envelope_are_detected(self):
        gate_stub = {"data_hashes": {
            relative: V6.v5.sha256_file(REPO / relative)
            for relative in V6.REQUIRED_DATA_PATHS}}
        original = self.adapter.whitening_transform_sha256
        self.adapter.whitening_transform_sha256 = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V6.validate_adapter_provenance(self.adapter, gate_stub)
        finally:
            self.adapter.whitening_transform_sha256 = original


if __name__ == "__main__":
    unittest.main()
