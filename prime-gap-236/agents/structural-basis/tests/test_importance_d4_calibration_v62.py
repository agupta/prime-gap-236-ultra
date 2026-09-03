#!/usr/bin/env python3

import copy
import importlib
import math
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
V = importlib.import_module("importance_d4_calibration_v62")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d4_calibration_gate_v62")


class CalibrationV62Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Candidate tests exercise the arithmetic before audit artifacts are
        # pinned; gate-builder tests are enabled only at the final freeze.
        V.install_runtime()
        V.v61.v6._patch_v5_runtime()
        cls.adapter = W.WhitenedC10ImportanceDensity(
            REPO / V.v61.v6.REQUIRED_DATA_PATHS[1],
            REPO / V.v61.v6.REQUIRED_DATA_PATHS[0])
        cls.schedule = V.v61.v6.v5.tiny_smoke_schedule()

    def j_record(self, r):
        spec = V.v61.v6.v5.expected_chain_table()[64 + 4 * r]
        return spec, V.v61.v6.v5.run_one_chain(
            self.adapter, spec, self.schedule)

    def test_honest_tiny_records_pass_all_strata(self):
        for r in range(16):
            spec, record = self.j_record(r)
            self.assertTrue(V.validate_chain_record(
                record, spec, self.schedule, adapter=self.adapter))

    def test_tail_raw_first_sum_zero_is_rejected(self):
        spec, record = self.j_record(15)
        corrupt = copy.deepcopy(record)
        self.assertGreater(V.v61.v6.v5.parse_float_hex(
            corrupt["raw_sum"][-1]), 0)
        corrupt["raw_sum"][-1] = V.v61.v6.v5.float_hex(0.0)
        # Frozen v6.1 inherits an absolute max(1,...) tolerance and accepts.
        self.assertTrue(V.FROZEN_V61_VALIDATE_CHAIN_RECORD(
            corrupt, spec, self.schedule, adapter=self.adapter))
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                corrupt, spec, self.schedule, adapter=self.adapter)

    def test_tail_batch_second_zero_is_rejected(self):
        spec, record = self.j_record(15)
        corrupt = copy.deepcopy(record)
        means = [V.v61.v6.v5.parse_float_hex(value)
                 for value in corrupt["batch_z_means"]]
        self.assertGreater(means[0] * means[0], 0)
        seconds = [V.v61.v6.v5.parse_float_hex(value)
                   for value in corrupt["batch_z_second_means"]]
        seconds[0] = 0.0
        corrupt["batch_z_second_means"][0] = \
            V.v61.v6.v5.float_hex(0.0)
        corrupt["raw_second_sum"][-1] = V.v61.v6.v5.float_hex(
            self.schedule["samples_per_batch"] * math.fsum(seconds))
        self.assertTrue(V.FROZEN_V61_VALIDATE_CHAIN_RECORD(
            corrupt, spec, self.schedule, adapter=self.adapter))
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                corrupt, spec, self.schedule, adapter=self.adapter)

    def test_local_tolerance_has_no_unit_floor(self):
        tiny = float(V.v61.J_Z_BOUNDS_EXACT[15]) ** 2
        tolerance = V._local_roundoff_tolerance(tiny, 0.0, 10000)
        self.assertGreater(tolerance, 0)
        self.assertLess(tolerance, tiny / 1000)
        self.assertEqual(V._local_roundoff_tolerance(0.0, 0.0, 1), 0.0)
        with self.assertRaises(ValueError):
            V._local_roundoff_tolerance(1.0, 1.0, True)
        with self.assertRaises(ArithmeticError):
            V._require_local_jensen(0.0, math.ulp(0.0), 1,
                                    "underflow fixture")

    def test_raw_second_and_batch_jensen_mutations_separately_reject(self):
        spec, record = self.j_record(15)
        corrupt = copy.deepcopy(record)
        corrupt["raw_second_sum"][-1] = V.v61.v6.v5.float_hex(0.0)
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                corrupt, spec, self.schedule, adapter=self.adapter)

    def test_production_sized_nonnegative_regrouping_tolerance(self):
        batch_count, samples_per_batch = 20, 400
        bound = float(V.v61.J_Z_BOUNDS_EXACT[15])
        batches, second_batches = [], []
        raw = raw_second = 0.0
        for batch in range(batch_count):
            subtotal = second_subtotal = 0.0
            for offset in range(samples_per_batch):
                index = batch * samples_per_batch + offset
                value = bound * ((37 * index + 11) % 1009) / 1009
                subtotal += value
                second_subtotal += value * value
                raw += value
                raw_second += value * value
            batches.append(subtotal / samples_per_batch)
            second_batches.append(second_subtotal / samples_per_batch)
        record = {
            "target": "J",
            "batch_z_means": [V.v61.v6.v5.float_hex(x) for x in batches],
            "batch_z_second_means": [
                V.v61.v6.v5.float_hex(x) for x in second_batches],
            "raw_sum": [V.v61.v6.v5.float_hex(raw)],
            "raw_second_sum": [V.v61.v6.v5.float_hex(raw_second)],
        }
        schedule = {"batches_per_chain": batch_count,
                    "samples_per_batch": samples_per_batch}
        self.assertTrue(V._validate_j_local_consistency(record, schedule))
        corrupt = copy.deepcopy(record)
        corrupt["raw_sum"][-1] = V.v61.v6.v5.float_hex(raw * (1 + 1e-6))
        with self.assertRaises(ArithmeticError):
            V._validate_j_local_consistency(corrupt, schedule)

    def test_gate_pins_failure_artifacts_and_remains_disabled(self):
        self.assertTrue(V.validate_v61_failure_artifacts())
        builder_sha = V.v61.v6.v5.sha256_file(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_invalid_gate_sha256"],
                         V.V61_GATE_SHA256)
        for relative, expected in V.V61_FAILURE_ARTIFACT_HASHES.items():
            self.assertEqual(gate["source_hashes"][relative], expected)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_failure_artifact_mutation_rejects(self):
        relative, expected = next(iter(V.V61_FAILURE_ARTIFACT_HASHES.items()))
        V.V61_FAILURE_ARTIFACT_HASHES[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V.validate_v61_failure_artifacts()
        finally:
            V.V61_FAILURE_ARTIFACT_HASHES[relative] = expected


if __name__ == "__main__":
    unittest.main()
