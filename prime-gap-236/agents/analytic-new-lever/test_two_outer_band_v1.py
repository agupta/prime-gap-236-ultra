#!/usr/bin/env python3
"""Regression tests for the exact two-outer-band analytic gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


CHECKER = Path(__file__).with_name("verify_two_outer_band_v1.py")
spec = importlib.util.spec_from_file_location("two_outer_band_under_test", CHECKER)
if spec is None or spec.loader is None:
    raise ImportError(CHECKER)
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
spec.loader.exec_module(v)


class TwoOuterBandV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = v.build()

    def test_frozen_band_endpoints_and_target_gains(self):
        p = self.result["parameters"]
        self.assertEqual(p["A"], ["-3/400", "1/4",
                                  "256241/1000000", "231241/900000"])
        self.assertEqual(p["lower_width_fraction_of_outer"], "9/10")
        self.assertEqual(p["count_4_to_7_gains"], {
            "4": "663/500000", "5": "649/200000",
            "6": "633/200000", "7": "1687/500000"})
        self.assertEqual(p["lower_minus_upper_caps"][2], "-173/200000")

    def test_every_ordered_pair_and_zero_count_is_present(self):
        p = self.result["ordered_pair_packing"]
        self.assertEqual((p["main_ordered_pairs"], p["near_ordered_pairs"]),
                         (1336, 572))
        self.assertEqual((p["main_zero_left"], p["main_zero_right"]),
                         (96, 96))
        self.assertEqual(p["IIa_III_checks"], 3816)
        self.assertEqual(p["IIb_crossing_number_checks"], 1726)
        self.assertEqual((p["dynamic_pairs"], p["dynamic_checks"]),
                         (572, 146432))

    def test_exact_worst_reserves(self):
        p = self.result["ordered_pair_packing"]
        self.assertEqual(p["IIa_III_worst"][0], "10199831/2400000000000")
        self.assertEqual(p["IIb_uniform_empty_third_worst"][0],
                         "290026073/90000000000000")
        self.assertEqual(p["dynamic_worst"][0], "319991/120000000000")
        reserve = self.result["strict_lower_cap_interval"]
        self.assertEqual(reserve["radius"], "1/1000000")
        self.assertEqual(reserve["upper_dynamic_worst"][0],
                         "199991/120000000000")

    def test_every_distinct_omega_has_correct_iic_regime(self):
        regimes = self.result["source_geometry"]["regimes"]
        actual = {item["omega"]: item["IIc"] for item in regimes.values()}
        self.assertEqual(actual, {
            "0": "empty",
            "6241/2000000": "empty",
            "6241/1800000": "empty",
            "6241/1000000": "nonempty",
            "118579/18000000": "nonempty",
            "6241/900000": "nonempty"})
        self.assertEqual(self.result["source_geometry"]["new_omega_minimum"],
                         "1/200000000000")

    def test_volume_is_labeled_secondary(self):
        volume = self.result["exact_volume_diagnostic_not_objective"]
        self.assertEqual(volume["two_over_single_decimal"],
                         "1.00000000020680608077920")
        self.assertIn("secondary", volume["meaning"])
        self.assertIn("not a D18 projection", volume["meaning"])

    def test_active12_mutation_fails_closed(self):
        original = v.LOWER_HEAD
        try:
            hostile = list(original)
            hostile[11] = v.Q(1, 5)
            v.LOWER_HEAD = tuple(hostile)
            with self.assertRaises(ArithmeticError):
                v.definition1_check()
        finally:
            v.LOWER_HEAD = original


if __name__ == "__main__":
    unittest.main()
