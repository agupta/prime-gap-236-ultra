#!/usr/bin/env python3

import copy
import importlib
import math
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
V = importlib.import_module("importance_d4_calibration_v64")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d4_calibration_gate_v64")


class CalibrationV64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V.install_runtime()
        V.v63.v62.v61.v6._patch_v5_runtime()
        cls.adapter = W.WhitenedC10ImportanceDensity(
            REPO / V.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1],
            REPO / V.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0])
        cls.schedule = V.v63.v62.v61.v6.v5.tiny_smoke_schedule()

    @staticmethod
    def minimal_record(mean, second, raw, raw_second):
        encode = V.v63.v62.v61.v6.v5.float_hex
        return {
            "target": "J",
            "batch_z_means": [encode(mean)] * 4,
            "batch_z_second_means": [encode(second)] * 4,
            "raw_sum": [encode(raw)],
            "raw_second_sum": [encode(raw_second)],
        }

    def test_v63_zero_second_counterexample_rejects(self):
        h = float.fromhex("0x1.0000000000000p-537")
        record = self.minimal_record(h, 0.0, 8 * h, 0.0)
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        self.assertTrue(V.v63._validate_j_totals_before_averaging(
            record, schedule))
        with self.assertRaises(ArithmeticError):
            V._validate_j_first_second_support(record, schedule)

    def test_public_tail_zero_second_mutation_rejects(self):
        spec = V.v63.v62.v61.v6.v5.expected_chain_table()[124]
        record = V.v63.v62.v61.v6.v5.run_one_chain(
            self.adapter, spec, self.schedule)
        h = float.fromhex("0x1.0000000000000p-537")
        mutated = copy.deepcopy(record)
        encode = V.v63.v62.v61.v6.v5.float_hex
        mutated["batch_z_means"] = [encode(h)] * 4
        mutated["batch_z_second_means"] = [encode(0.0)] * 4
        mutated["raw_sum"][-1] = encode(8 * h)
        mutated["raw_second_sum"][-1] = encode(0.0)
        self.assertTrue(V.FROZEN_V63_VALIDATE_CHAIN_RECORD(
            mutated, spec, self.schedule, adapter=self.adapter))
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                mutated, spec, self.schedule, adapter=self.adapter)

    def test_positive_subnormal_and_both_zero_cases(self):
        encode = V.v63.v62.v61.v6.v5.float_hex
        with self.assertRaises(ArithmeticError):
            V._resolved_nonnegative(
                [encode(math.ulp(0.0))], "subnormal fixture")
        zeros = self.minimal_record(0.0, 0.0, 0.0, 0.0)
        self.assertTrue(V._validate_j_first_second_support(
            zeros, {"batches_per_chain": 4}))

    def test_pointwise_positive_subnormal_square_rejects(self):
        original = V.FROZEN_V63_J_ENVELOPE_POINT
        h = float.fromhex("0x1.0000000000000p-537")
        V.FROZEN_V63_J_ENVELOPE_POINT = lambda _adapter, _common: \
            SimpleNamespace(z=h, log_g=0.0)
        try:
            with self.assertRaises(ArithmeticError):
                V.j_envelope_point(None, ())
        finally:
            V.FROZEN_V63_J_ENVELOPE_POINT = original

    def test_honest_tiny_records_pass_all_strata(self):
        for r in range(16):
            spec = V.v63.v62.v61.v6.v5.expected_chain_table()[64 + 4 * r]
            record = V.v63.v62.v61.v6.v5.run_one_chain(
                self.adapter, spec, self.schedule)
            self.assertTrue(V.validate_chain_record(
                record, spec, self.schedule, adapter=self.adapter))

    def test_gate_pins_v63_failure_and_remains_disabled(self):
        self.assertTrue(V.validate_v63_failure_artifacts())
        builder_sha = V.v63.v62.v61.v6.v5.sha256_file(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_invalid_gate_sha256"],
                         V.V63_GATE_SHA256)
        for relative, expected in V.V63_FAILURE_ARTIFACT_HASHES.items():
            self.assertEqual(gate["source_hashes"][relative], expected)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_v63_failure_artifact_mutation_rejects(self):
        relative, expected = next(iter(V.V63_FAILURE_ARTIFACT_HASHES.items()))
        V.V63_FAILURE_ARTIFACT_HASHES[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V.validate_v63_failure_artifacts()
        finally:
            V.V63_FAILURE_ARTIFACT_HASHES[relative] = expected


if __name__ == "__main__":
    unittest.main()
