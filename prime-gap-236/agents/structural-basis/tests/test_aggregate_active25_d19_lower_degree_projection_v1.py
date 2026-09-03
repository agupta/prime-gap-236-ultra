#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = REPO / (
    "agents/structural-basis/code/"
    "aggregate_active25_d19_lower_degree_projection_v1.py")
SOURCE_SHA256 = "62933a575e2bd2e11b40415be1f28053d936de009fc8a80fbefe25540a66f65f"
RESULT = REPO / (
    "agents/structural-basis/results/"
    "active25_d19_lower_degree_projection_aggregate_v1.json")
RESULT_SHA256 = "db0c2768869fb3584198b5b8005ea710642befe0f7a84061ca6f24dff321bfee"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("lower_projection_aggregate_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LowerProjectionAggregateTest(unittest.TestCase):
    def test_frozen_artifact_and_disabled_state(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        self.assertEqual(digest(RESULT), RESULT_SHA256)
        data = json.loads(RESULT.read_bytes())
        self.assertEqual(
            data["status"],
            "CALIBRATED LOWER-DEGREE PROJECTION SCREEN PASS; D14 EXACT STAGE GATED")
        self.assertFalse(data["launch_authorized"])
        self.assertFalse(data["exact_target_started"])
        self.assertFalse(data["resume_supported"])
        self.assertFalse(data["theorem_ready"])

    def test_ivw_reconstruction(self):
        module = load_source()
        first = json.loads(module.RESULTS[0][0].read_bytes())
        second = json.loads(module.RESULTS[1][0].read_bytes())
        frozen = json.loads(RESULT.read_bytes())
        for name in module.NAMES:
            rows = [item["lower_degree_natural_projections"][name]
                    for item in (first, second)]
            mean, error = module.ivw(
                rows, "projected_energy_over_inner_I",
                "projected_energy_over_inner_I_delta_standard_error")
            observed = frozen["candidates"][name]
            self.assertTrue(math.isclose(
                mean, observed["projected_energy_over_inner_I_IVW"],
                rel_tol=0, abs_tol=1e-18))
            self.assertTrue(math.isclose(
                error, observed["projected_energy_over_inner_I_IVW_standard_error"],
                rel_tol=0, abs_tol=1e-18))

    def test_prespecified_selection(self):
        data = json.loads(RESULT.read_bytes())
        threshold = data["exact_single_band_criterion"][
            "exact_D19_normalized_deficit_decimal"]
        self.assertEqual(data["selection"]["chosen_candidate"], "D14")
        self.assertLess(
            data["candidates"]["D12"]["three_SE_lower_projected_energy"],
            threshold)
        self.assertGreater(
            data["candidates"]["D14"]["three_SE_lower_projected_energy"],
            0.020)
        self.assertGreater(
            data["candidates"]["D16"]["three_SE_lower_projected_energy"],
            0.020)
        self.assertLess(
            data["candidates"]["D14"]
                ["exact_b_global_collection_inventory"]
                ["global_canonical_b_keys_before_coefficient_cancellation"],
            data["candidates"]["D16"]
                ["exact_b_global_collection_inventory"]
                ["global_canonical_b_keys_before_coefficient_cancellation"])


if __name__ == "__main__":
    unittest.main()
