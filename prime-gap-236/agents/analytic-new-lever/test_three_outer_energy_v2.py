#!/usr/bin/env python3
"""Regression tests for the exact three-outer-band support gate."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "three_outer_energy_v2_under_test",
    HERE / "verify_three_outer_energy_v2.py")
if spec is None or spec.loader is None:
    raise ImportError("cannot load exact checker")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


class ThreeOuterEnergyV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = gate.build()

    def test_exact_inventory_and_new_mechanisms(self):
        result = self.result
        self.assertEqual(result["status"],
                         "EXACT THREE-OUTER-BAND ENERGY SUPPORT PASS")
        packing = result["ordered_pair_packing"]
        self.assertEqual((packing["main_ordered_pairs"],
                          packing["near_ordered_pairs"]), (818, 280))
        self.assertEqual((packing["main_zero_left"],
                          packing["main_zero_right"]), (101, 101))
        self.assertEqual(packing["IIa_III_checks"], 2196)
        self.assertGreater(packing["IIa_III_old_prefix_failures"], 0)
        self.assertGreater(
            packing["IIb_selected_two_bin_mechanisms"]["crossing-item"], 0)
        self.assertEqual(packing["dynamic_checks"], 71680)
        self.assertGreater(packing["dynamic_required_three_block_cells"], 0)

    def test_target_gains_and_strict_interval(self):
        self.assertEqual(
            self.result["parameters"]["count_4_to_7_gains"],
            {"4": "53/20000", "5": "1951/250000",
             "6": "9787/1000000", "7": "1939/200000"})
        interval = self.result["strict_lower_cap_interval"]
        self.assertEqual(interval["radius"], "1/10000000")
        self.assertEqual(interval["lower_active"], interval["upper_active"])

    def test_three_block_fails_closed(self):
        delta = gate.CFG.delta
        with self.assertRaises(ArithmeticError):
            gate.sorted_three_block_certificate(
                1, 1, delta, delta,
                (delta / 10, delta / 10, delta / 10, delta / 10))

    def test_dependency_hash_fails_closed_before_acceptance(self):
        expected = gate.FROZEN_SHA256
        try:
            gate.FROZEN_SHA256 = "0" * 64
            with self.assertRaisesRegex(ArithmeticError,
                                        "frozen exact primitive file changed"):
                gate.build()
        finally:
            gate.FROZEN_SHA256 = expected

    def test_no_proxy_or_quotient_dependency(self):
        rendered = json.dumps(self.result, sort_keys=True)
        self.assertNotIn("adaptive_projection_proxy", rendered)
        self.assertIn("no Riesz energy lower bound", self.result["scope"])


if __name__ == "__main__":
    unittest.main()
