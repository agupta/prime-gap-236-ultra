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
V = importlib.import_module("importance_d4_calibration_v63")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d4_calibration_gate_v63")


class CalibrationV63Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V.install_runtime()
        V.v62.v61.v6._patch_v5_runtime()
        cls.adapter = W.WhitenedC10ImportanceDensity(
            REPO / V.v62.v61.v6.REQUIRED_DATA_PATHS[1],
            REPO / V.v62.v61.v6.REQUIRED_DATA_PATHS[0])
        cls.schedule = V.v62.v61.v6.v5.tiny_smoke_schedule()

    @staticmethod
    def minimal_record(raw=0.0, raw_second=0.0,
                       means=None, seconds=None):
        encode = V.v62.v61.v6.v5.float_hex
        means = [0.0] * 4 if means is None else means
        seconds = [0.0] * 4 if seconds is None else seconds
        return {
            "target": "J",
            "batch_z_means": [encode(x) for x in means],
            "batch_z_second_means": [encode(x) for x in seconds],
            "raw_sum": [encode(raw)],
            "raw_second_sum": [encode(raw_second)],
        }

    def test_raw_positive_subnormals_cannot_average_to_zero(self):
        tiny = math.ulp(0.0)
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        for field in ("raw_sum", "raw_second_sum"):
            record = self.minimal_record()
            record[field][-1] = V.v62.v61.v6.v5.float_hex(tiny)
            with self.subTest(field=field), self.assertRaises(ArithmeticError):
                V._validate_j_totals_before_averaging(record, schedule)

    def test_positive_batch_second_cannot_vanish_in_average(self):
        tiny = math.ulp(0.0)
        record = self.minimal_record(
            raw_second=2 * tiny, seconds=[tiny, 0.0, 0.0, 0.0])
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        with self.assertRaises(ArithmeticError):
            V._validate_j_totals_before_averaging(record, schedule)

    def test_public_tail_underflow_mutation_rejects(self):
        spec = V.v62.v61.v6.v5.expected_chain_table()[124]
        record = V.v62.v61.v6.v5.run_one_chain(
            self.adapter, spec, self.schedule)
        mutated = copy.deepcopy(record)
        zero = V.v62.v61.v6.v5.float_hex(0.0)
        mutated["batch_z_means"] = [zero] * 4
        mutated["batch_z_second_means"] = [zero] * 4
        mutated["raw_sum"][-1] = V.v62.v61.v6.v5.float_hex(math.ulp(0.0))
        mutated["raw_second_sum"][-1] = zero
        self.assertTrue(V.FROZEN_V62_VALIDATE_CHAIN_RECORD(
            mutated, spec, self.schedule, adapter=self.adapter))
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                mutated, spec, self.schedule, adapter=self.adapter)

    def test_honest_tiny_records_pass_all_strata(self):
        for r in range(16):
            spec = V.v62.v61.v6.v5.expected_chain_table()[64 + 4 * r]
            record = V.v62.v61.v6.v5.run_one_chain(
                self.adapter, spec, self.schedule)
            self.assertTrue(V.validate_chain_record(
                record, spec, self.schedule, adapter=self.adapter))

    def test_full_initial_and_extension_regrouping_do_not_false_reject(self):
        encode = V.v62.v61.v6.v5.float_hex
        bound = float(V.v62.v61.J_Z_BOUNDS_EXACT[15])
        for batch_count in (20, 80):
            samples_per_batch = 200
            raw = raw_second = 0.0
            means, seconds = [], []
            for batch in range(batch_count):
                subtotal = second_subtotal = 0.0
                for offset in range(samples_per_batch):
                    index = batch * samples_per_batch + offset
                    value = bound * ((37 * index + 11) % 1009) / 1009
                    subtotal += value
                    second_subtotal += value * value
                    raw += value
                    raw_second += value * value
                means.append(subtotal / samples_per_batch)
                seconds.append(second_subtotal / samples_per_batch)
            record = {
                "target": "J",
                "batch_z_means": [encode(x) for x in means],
                "batch_z_second_means": [encode(x) for x in seconds],
                "raw_sum": [encode(raw)],
                "raw_second_sum": [encode(raw_second)],
            }
            schedule = {"batches_per_chain": batch_count,
                        "samples_per_batch": samples_per_batch}
            with self.subTest(batch_count=batch_count):
                self.assertTrue(V._validate_j_totals_before_averaging(
                    record, schedule))

    def test_negative_zero_and_positive_second_with_zero_mean_reject(self):
        schedule = {"batches_per_chain": 4, "samples_per_batch": 2}
        negative_zero = self.minimal_record()
        negative_zero["batch_z_means"][0] = (-0.0).hex()
        with self.assertRaises(ArithmeticError):
            V._validate_j_totals_before_averaging(negative_zero, schedule)
        tiny = math.ulp(0.0)
        impossible = self.minimal_record(
            raw_second=2 * tiny, seconds=[tiny, 0.0, 0.0, 0.0])
        with self.assertRaises(ArithmeticError):
            V._validate_j_totals_before_averaging(impossible, schedule)

    def test_gate_pins_v62_failure_and_remains_disabled(self):
        self.assertTrue(V.validate_v62_failure_artifacts())
        builder_sha = V.v62.v61.v6.v5.sha256_file(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_invalid_gate_sha256"],
                         V.V62_GATE_SHA256)
        for relative, expected in V.V62_FAILURE_ARTIFACT_HASHES.items():
            self.assertEqual(gate["source_hashes"][relative], expected)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_v62_failure_artifact_mutation_rejects(self):
        relative, expected = next(iter(V.V62_FAILURE_ARTIFACT_HASHES.items()))
        V.V62_FAILURE_ARTIFACT_HASHES[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V.validate_v62_failure_artifacts()
        finally:
            V.V62_FAILURE_ARTIFACT_HASHES[relative] = expected


if __name__ == "__main__":
    unittest.main()
