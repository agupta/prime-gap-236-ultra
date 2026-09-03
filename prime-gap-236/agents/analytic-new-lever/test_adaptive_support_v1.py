#!/usr/bin/env python3
"""Hostile regression tests for the frozen adaptive support gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise ImportError(filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v = load("adaptive_support_v1_under_test", "verify_adaptive_support_v1.py")
d = load("three_bin_iib_v1_under_test", "diagnose_three_bin_iib_v1.py")


class AdaptiveSupportV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = v.build()
        cls.diag = d.build()

    def test_frozen_rational_point_and_main_face(self):
        candidate = self.result["candidate"]
        self.assertEqual(candidate["parameters"]["delta"], "1/60")
        self.assertEqual(candidate["parameters"]["A"][2], "231241/900000")
        self.assertEqual(candidate["parameters"]["A2_minus_A1"], "6241/900000")
        self.assertEqual(candidate["parameters"]["main_direct_HB_face"],
                         "3747/100000")
        self.assertEqual(candidate["parameters"]["main_direct_HB_face_reserve"],
                         "3/100000")

    def test_complete_ordered_inventories_include_zero_counts(self):
        fixed = self.result["candidate"]["fixed_and_literal_IIb"]
        self.assertEqual(fixed["ordered_pairs"], 668)
        self.assertEqual(fixed["IIa_III_checks"], 1336)
        self.assertEqual(fixed["IIb_crossing_number_checks"], 767)
        self.assertEqual(fixed["small_count_partition"], {
            "left-zero": 48, "right-zero": 48,
            "both-positive-at-most-two": 16,
            "exactly-one-at-most-two": 160,
            "both-at-least-three": 396})
        dynamic = self.result["candidate"]["dynamic_IIc"]
        self.assertEqual((dynamic["ordered_pairs"], dynamic["checks"]),
                         (143, 36608))
        self.assertEqual(dynamic["small_count_partition"]["left-zero"], 11)
        self.assertEqual(dynamic["small_count_partition"]["right-zero"], 11)

    def test_exact_worst_margins_are_strict(self):
        candidate = self.result["candidate"]
        self.assertEqual(candidate["source_geometry"]["minimum_margin"],
                         "1/200000000000")
        self.assertEqual(candidate["fixed_and_literal_IIb"]["IIa_III_worst"][0],
                         "43599493/7200000000000")
        self.assertEqual(
            candidate["fixed_and_literal_IIb"]["IIb_uniform_empty_third_worst"][0],
            "53930026073/90000000000000")
        self.assertEqual(candidate["dynamic_IIc"]["worst"][0],
                         "800009/180000000000")
        reserve = self.result["candidate_strict_outer_cap_reserve"]
        self.assertEqual(reserve["uniform_outer_cap_radius"], "1/1000000")
        self.assertEqual(reserve["upper_dynamic_worst"][0],
                         "440009/180000000000")

    def test_prime_indicator_endpoint_and_beta(self):
        prop = self.result["candidate"]["proposition2_and_prop1"]
        self.assertEqual(prop["xi"], ["19/50", "2/5", "2/5"])
        self.assertEqual((prop["c1"], prop["c2"], prop["beta"]),
                         ("0", "0", "1/2"))
        self.assertEqual(prop["maximum_Bj1"], "103/400")
        self.assertEqual(prop["margins"]["beta-max-Bj1"], "97/400")

    def test_theorem_gate_has_no_proxy_or_old_audit_dependency(self):
        forbidden = ("adaptive_projection_proxy", "correlated_iib_lift")
        self.assertTrue(all(not any(word in path for word in forbidden)
                            for path in v.PINNED))
        rendered = repr(self.result)
        self.assertNotIn("energy_retention", rendered)
        self.assertNotIn("selected_nonempty_third", rendered)

    def test_definition1_mutation_fails_closed(self):
        # Make count 12 active while retaining the frozen expected inventory.
        head = list(v.CANDIDATE.outer_head)
        head[11] = v.Q(1, 5)
        bad = v.Config("hostile-active12", v.CANDIDATE.delta,
                       v.CANDIDATE.epsilon, v.CANDIDATE.a2,
                       tuple(head), 11)
        with self.assertRaises(ArithmeticError):
            v.definition1_check(bad)

    def test_three_bin_mechanism_is_separate_and_nontrivial(self):
        self.assertEqual(self.diag["acceptance_role"],
                         "none; not read by the frozen support gate")
        candidate = self.diag["candidate"]
        self.assertEqual(candidate["ordered_pairs"], 668)
        self.assertEqual(candidate["endpoint_and_interval_records"], 4618)
        self.assertEqual(candidate["selected_nonempty_third_records"], 196)
        self.assertEqual(candidate["maximum_selected_q"], 1)
        self.assertEqual(candidate["first_pair_selecting_nonempty_third"][:3],
                         ["mixed", 1, 5])


if __name__ == "__main__":
    unittest.main()
