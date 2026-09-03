#!/usr/bin/env python3
"""Regression tests for the exact truncated one-outer-band gate."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "truncated_lower_energy_v3_under_test",
    HERE / "verify_truncated_lower_energy_v3.py")
if spec is None or spec.loader is None:
    raise ImportError("cannot load truncated exact gate")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


class TruncatedLowerEnergyV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = gate.build()

    def test_inventory(self):
        self.assertEqual(
            self.result["status"],
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS")
        packing = self.result["ordered_pair_packing"]
        self.assertEqual((packing["main_ordered_pairs"],
                          packing["near_ordered_pairs"]), (582, 168))
        self.assertEqual((packing["main_zero_left"],
                          packing["main_zero_right"]), (39, 39))
        self.assertEqual(packing["IIa_III_checks"], 1500)
        self.assertEqual((packing["dynamic_pairs"],
                          packing["dynamic_checks"]), (168, 43008))
        self.assertEqual(packing["dynamic_required_three_block_cells"], 6081)

    def test_literal_definition5_cutoffs(self):
        cutoffs = self.result["definition5_single_outer_band"]
        self.assertEqual(cutoffs["eta_inner_inner"], "97/400")
        self.assertEqual(cutoffs["eta_inner_outer"],
                         "8960917/36000000")
        self.assertEqual(cutoffs["eta_outer_outer"],
                         "8960917/36000000")
        self.assertIn("exactly one outer band", cutoffs["reason"])

    def test_active_inventory_and_strict_interval(self):
        self.assertEqual(self.result["parameters"]["outer_active_counts"],
                         list(range(13)))
        interval = self.result["strict_outer_cap_interval"]
        self.assertEqual(interval["radius"], "1/10000000")
        self.assertEqual(interval["lower_active"], interval["upper_active"])

    def test_dependency_hash_fails_closed(self):
        expected = gate.V2_SHA256
        try:
            gate.V2_SHA256 = "0" * 64
            with self.assertRaisesRegex(ArithmeticError,
                                        "v2 exact primitives changed"):
                gate.build()
        finally:
            gate.V2_SHA256 = expected

    def test_no_multiband_energy_claim(self):
        rendered = json.dumps(self.result, sort_keys=True)
        self.assertNotIn("adaptive_projection_proxy", rendered)
        self.assertIn("no Riesz energy lower bound", self.result["scope"])
        self.assertIn("no indefinite cross-band outer-J",
                      self.result["definition5_single_outer_band"]["reason"])


if __name__ == "__main__":
    unittest.main()
