#!/usr/bin/env python3

import importlib
import math
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
V = importlib.import_module("importance_d4_calibration_v65")
W = importlib.import_module("importance_whitening_v6")
G = importlib.import_module("build_importance_d4_calibration_gate_v65")


def presquare_fixture():
    adapter = W.WhitenedC10ImportanceDensity(
        REPO / V.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1],
        REPO / V.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0])
    marginals = [0.0] * adapter.dimension
    marginals[0] = float.fromhex("0x1p-600")
    marginals[1] = 1.0
    adapter.j_support = lambda _common: True
    adapter.j_marginals = lambda _common: tuple(marginals)

    def j_m0(_common, transformed=None):
        values = marginals if transformed is None else transformed
        return math.fsum(
            adapter.base_constant_weights[6 * r] * values[6 * r]
            for r in adapter.strata)

    adapter.j_m0 = j_m0
    return adapter, (0.0,) * 47


class CalibrationV65Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        V.install_runtime()
        V.v64.v63.v62.v61.v6._patch_v5_runtime()
        cls.adapter = W.WhitenedC10ImportanceDensity(
            REPO / V.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[1],
            REPO / V.v64.v63.v62.v61.v6.REQUIRED_DATA_PATHS[0])
        cls.schedule = V.v64.v63.v62.v61.v6.v5.tiny_smoke_schedule()

    def test_v64_presquare_counterexample_rejects(self):
        adapter, common = presquare_fixture()
        point = V.FROZEN_V64_J_ENVELOPE_POINT(adapter, common)
        weighted = math.fsum(
            adapter.base_constant_weights[6 * r] *
            point.unit_marginals[6 * r] for r in adapter.strata)
        self.assertNotEqual(weighted, 0)
        self.assertEqual(point.z, 0)
        with self.assertRaises(ArithmeticError):
            V.j_envelope_point(adapter, common)

    def test_returned_z_is_recomputed_on_honest_points(self):
        conditional = importlib.import_module("importance_conditional")
        for r in range(16):
            common = conditional.randomized_interior_start(
                self.adapter, "J", r, 815_000 + r)
            point = V.j_envelope_point(self.adapter, common)
            self.assertIsNotNone(point)
            _, square = V._weighted_m0_and_square(self.adapter, point)
            self.assertLessEqual(
                abs(point.z - square),
                16 * max(math.ulp(point.z), math.ulp(square)))

    def test_tagged_product_underflow_rejects(self):
        adapter, common = presquare_fixture()
        point = V.FROZEN_V64_J_ENVELOPE_POINT(adapter, common)
        unit = list(point.unit_marginals)
        unit[0] = math.ulp(0.0)
        forged = type(point)(tuple(unit), point.log_g, 0.0,
                             point.nonzero_constant_channels, point.z_bound)
        with self.assertRaises(ArithmeticError):
            V._weighted_m0_and_square(adapter, forged)

    def test_gate_pins_v64_failure_and_remains_disabled(self):
        self.assertTrue(V.validate_v64_failure_artifacts())
        builder_sha = V.v64.v63.v62.v61.v6.v5.sha256_file(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["production_launch_authorized"])
        self.assertEqual(gate["supersedes_invalid_gate_sha256"],
                         V.V64_GATE_SHA256)
        for relative, expected in V.V64_FAILURE_ARTIFACT_HASHES.items():
            self.assertEqual(gate["source_hashes"][relative], expected)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_v64_failure_artifact_mutation_rejects(self):
        relative, expected = next(iter(V.V64_FAILURE_ARTIFACT_HASHES.items()))
        V.V64_FAILURE_ARTIFACT_HASHES[relative] = "0" * 64
        try:
            with self.assertRaises(ValueError):
                V.validate_v64_failure_artifacts()
        finally:
            V.V64_FAILURE_ARTIFACT_HASHES[relative] = expected


if __name__ == "__main__":
    unittest.main()
