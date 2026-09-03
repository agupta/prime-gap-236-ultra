#!/usr/bin/env python3

import copy
import importlib
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
V = importlib.import_module("importance_d4_calibration_v61")
G = importlib.import_module("build_importance_d4_calibration_gate_v61")
W = importlib.import_module("importance_whitening_v6")


class CalibrationV61Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V.install_runtime()
        V.v6._patch_v5_runtime()
        cls.adapter = W.WhitenedC10ImportanceDensity(
            REPO / V.v6.REQUIRED_DATA_PATHS[1],
            REPO / V.v6.REQUIRED_DATA_PATHS[0])

    def test_exact_bounds_derive_from_transform(self):
        for r, wanted in enumerate(V.J_Z_BOUNDS_EXACT):
            observed = sum(
                self.adapter.base_constant_weights_exact[6 * s] ** 2
                for s in (r, r + 1) if s < 16)
            self.assertEqual(observed, wanted)
        self.assertEqual(V.J_Z_BOUNDS_EXACT[0], V.Fraction(17, 16384))
        self.assertEqual(max(V.J_Z_BOUNDS_EXACT), V.Fraction(1, 8))

    def test_legacy_false_accept_is_now_rejected(self):
        schedule = V.v6.v5.tiny_smoke_schedule()
        spec = V.v6.v5.expected_chain_table()[64]  # J,r=0,replicate=0.
        record = V.v6.v5.run_one_chain(self.adapter, spec, schedule)
        corrupt = copy.deepcopy(record)
        corrupt["batch_z_means"] = [V.v6.v5.float_hex(1.0)] * 4
        corrupt["batch_z_second_means"] = [V.v6.v5.float_hex(1.0)] * 4
        corrupt["raw_sum"][-1] = V.v6.v5.float_hex(8.0)
        corrupt["raw_second_sum"][-1] = V.v6.v5.float_hex(8.0)
        # Frozen v6/v5 accepted this self-consistent but impossible record.
        self.assertTrue(V.FROZEN_V6_VALIDATE_CHAIN_RECORD(
            corrupt, spec, schedule, adapter=self.adapter))
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                corrupt, spec, schedule, adapter=self.adapter)

    def test_all_common_strata_real_smoke_z_obeys_exact_bound(self):
        schedule = V.v6.v5.tiny_smoke_schedule()
        for r in range(16):
            spec = V.v6.v5.expected_chain_table()[64 + 4 * r]
            record = V.v6.v5.run_one_chain(self.adapter, spec, schedule)
            self.assertTrue(V.validate_chain_record(
                record, spec, schedule, adapter=self.adapter))
            state = tuple(V.v6.v5.parse_float_hex(value)
                          for value in record["final_state"])
            point = V.j_envelope_point(self.adapter, state)
            self.assertLessEqual(point.z, float(V.J_Z_BOUNDS_EXACT[r]) +
                                 4096 * V.math.ulp(
                                     float(V.J_Z_BOUNDS_EXACT[r])))

    def test_raw_and_second_bound_mutations_reject(self):
        schedule = V.v6.v5.tiny_smoke_schedule()
        spec = V.v6.v5.expected_chain_table()[64]
        record = V.v6.v5.run_one_chain(self.adapter, spec, schedule)
        for field in ("raw_sum", "raw_second_sum"):
            corrupt = copy.deepcopy(record)
            corrupt[field][-1] = V.v6.v5.float_hex(1.0)
            with self.assertRaises(ArithmeticError):
                V.validate_chain_record(
                    corrupt, spec, schedule, adapter=self.adapter)
        # Keep first moments intact and make only the second moments
        # self-consistent but larger than the exact local pointwise bound.
        corrupt = copy.deepcopy(record)
        impossible_second = 2 * float(V.J_Z_BOUNDS_EXACT[0]) ** 2
        corrupt["batch_z_second_means"] = [
            V.v6.v5.float_hex(impossible_second)] * 4
        corrupt["raw_second_sum"][-1] = V.v6.v5.float_hex(
            schedule["retained_samples"] * impossible_second)
        self.assertTrue(V.FROZEN_V6_VALIDATE_CHAIN_RECORD(
            corrupt, spec, schedule, adapter=self.adapter))
        with self.assertRaises(ArithmeticError):
            V.validate_chain_record(
                corrupt, spec, schedule, adapter=self.adapter)

    def test_gate_builder_supersedes_v6_and_remains_disabled(self):
        digest = V.v6.v5.sha256_file(G.HERE)
        gate = G.build_gate(digest)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_invalid_gate_sha256"],
                         V.V6_GATE_SHA256)
        self.assertEqual(gate["conventions"]["j_z_bounds_exact"],
                         [str(value) for value in V.J_Z_BOUNDS_EXACT])
        self.assertTrue(V.validate_v6_failure_artifacts())
        for relative, expected in V.V6_FAILURE_ARTIFACT_HASHES.items():
            self.assertEqual(gate["source_hashes"][relative], expected)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_frozen_v6_failure_artifact_mutation_is_rejected(self):
        relative, expected = next(iter(V.V6_FAILURE_ARTIFACT_HASHES.items()))
        V.V6_FAILURE_ARTIFACT_HASHES[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V.validate_v6_failure_artifacts()
        finally:
            V.V6_FAILURE_ARTIFACT_HASHES[relative] = expected


if __name__ == "__main__":
    unittest.main()
