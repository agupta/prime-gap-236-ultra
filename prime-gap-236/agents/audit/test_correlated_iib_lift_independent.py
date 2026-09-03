#!/usr/bin/env python3
"""Regression and adversarial tests for the independent IIb-lift audit."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
CHECKER = HERE / "verify_correlated_iib_lift_independent.py"
SPEC = importlib.util.spec_from_file_location(
    "correlated_iib_lift_independent_under_test", CHECKER)
if SPEC is None or SPEC.loader is None:
    raise ImportError("cannot load independent correlated-IIb checker")
v = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v
SPEC.loader.exec_module(v)


def direct_two_bin_partition_exists(values, first_capacity, second_capacity):
    """Literal subset oracle used only on finite hostile regression fixtures."""
    total = sum(values, Q(0))
    for mask in range(1 << len(values)):
        second = sum((value for index, value in enumerate(values)
                      if mask & (1 << index)), Q(0))
        if second <= second_capacity and total - second <= first_capacity:
            return True
    return False


class CorrelatedIIbIndependentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = v.build()

    def test_complete_inventories_and_exact_worst_cases(self):
        self.assertEqual(self.result["status"], "AUDIT PASS")
        fixed = self.result["all_fixed_and_correlated_IIb"]
        dynamic = self.result["all_dynamic_IIc"]
        self.assertEqual(fixed["total_pairs"], 3220)
        self.assertEqual(fixed["IIa_III_checks"], 6440)
        self.assertEqual(fixed["IIb_crossing_checks"], 9325)
        self.assertEqual(fixed["changed_subset"], {
            "pairs": 1694, "IIa_III_checks": 3388,
            "IIb_crossing_checks": 2602})
        self.assertEqual(
            fixed["IIa_III_worst"][:5],
            ["186599869/600000000000", "outer", "III", 8, 17])
        self.assertEqual(
            fixed["IIb_worst"][:4],
            ["800002897/10000000000000", "outer-near", 9, 23])
        self.assertEqual(dynamic["pairs"], 675)
        self.assertEqual(dynamic["checks"], 172800)
        self.assertEqual(dynamic["changed_subset"], {
            "pairs": 451, "checks": 115456})
        self.assertEqual(
            dynamic["worst"][:5],
            ["89993/40000000000", 6, 25, 9, 1])

    def test_all_zero_and_small_count_branches_are_present(self):
        fixed_classes = self.result[
            "all_fixed_and_correlated_IIb"]["small_index_partition"]
        dynamic_classes = self.result[
            "all_dynamic_IIc"]["small_index_partition"]
        self.assertEqual(sum(fixed_classes.values()), 3220)
        self.assertEqual(fixed_classes["left-zero"], 110)
        self.assertEqual(fixed_classes["right-zero"], 110)
        self.assertEqual(fixed_classes["both-positive-at-most-two"], 16)
        self.assertEqual(sum(dynamic_classes.values()), 675)
        self.assertEqual(dynamic_classes["left-zero"], 25)
        self.assertEqual(dynamic_classes["right-zero"], 25)
        self.assertEqual(dynamic_classes["both-positive-at-most-two"], 4)

    def test_definition1_nonstrict_steps_and_strict_empty_count(self):
        # Definition 1 permits both equal consecutive caps and a step exactly
        # delta.  The lifted schedule deliberately uses both endpoint cases.
        for right_index in (1, 2, 3, 4, 5, 7):
            self.assertEqual(
                v.NEW_OUTER[right_index] - v.NEW_OUTER[right_index - 1],
                v.DELTA)
        self.assertEqual(v.NEW_OUTER[6] - v.NEW_OUTER[5], 0)
        self.assertEqual(v.NEW_OUTER[9] - v.NEW_OUTER[8], 0)
        self.assertGreater(v.NEW_OUTER[24] - 25 * v.DELTA, 0)
        self.assertGreater(26 * v.DELTA - v.NEW_OUTER[25], 0)

    def test_source_open_intervals_have_uniform_reserve(self):
        source = self.result["source_geometry"]
        self.assertEqual(source["minimum_margin"], "1/200000000000")
        for label in ("near", "mixed", "outer"):
            margins = source["margins"]
            self.assertEqual(margins[f"{label}.IIb-width"],
                             "3/350000000000")
            self.assertEqual(margins[f"{label}.IIb-distribution-1"],
                             "7/10000000000")
            self.assertGreater(Q(margins[f"{label}.IIb-a1-positive"]), 0)
            self.assertGreater(Q(margins[f"{label}.IIb-a2-positive"]), 0)
            self.assertGreater(Q(margins[f"{label}.IIb-bsum-below-half"]), 0)

    def test_literal_subsets_on_adverse_mixed_pair(self):
        # This is not used as the universal proof.  It independently attacks
        # the key (inner count 1, outer count 9) lift with literal subset
        # enumeration at every gamma crossing boundary and several extreme
        # tuples.  The old coordinatewise-minimum test rejects this pair.
        omega = v.CROSS_OMEGA
        left_cap = v.INNER_CAP
        right_cap = v.NEW_OUTER[8]
        delta = v.DELTA
        gamma_low, gamma_high = v.gamma_b(omega), v.gamma_a(omega)
        a = 3 * v.ZETA_MAX + v.INWARD

        right_fixtures = (
            (right_cap / 9,) * 9,
            (right_cap - 8 * delta,) + (delta,) * 8,
            (delta,) * 8 + (right_cap - 8 * delta,),
            tuple(delta + (right_cap - 9 * delta) * Q(index, 36)
                  for index in range(9)),
        )
        # The last arithmetic progression has total right_cap exactly.
        self.assertEqual(sum(right_fixtures[-1], Q(0)), right_cap)
        left_fixtures = (delta, (delta + left_cap) / 2, left_cap)

        total_cap = left_cap + right_cap
        gamma_points = {gamma_low, gamma_high, (gamma_low + gamma_high) / 2}
        max_crossing = v.ceil_fraction(
            (total_cap - (gamma_low - a)) / delta)
        tiny = Q(1, 10**18)
        for crossing in range(1, max_crossing + 1):
            boundary = total_cap + a - crossing * delta
            for point in (boundary - tiny, boundary, boundary + tiny):
                if gamma_low <= point <= gamma_high:
                    gamma_points.add(point)

        for left in left_fixtures:
            for right in right_fixtures:
                values = (left,) + right
                self.assertLessEqual(left, left_cap)
                self.assertLessEqual(sum(right, Q(0)), right_cap)
                self.assertTrue(all(value >= delta for value in values))
                for gamma in gamma_points:
                    first = gamma - 3 * v.ZETA_MAX - v.INWARD
                    second = (Q(1, 2) - gamma - 2 * omega
                              - 6 * v.ZETA_MAX - v.INWARD)
                    self.assertTrue(
                        direct_two_bin_partition_exists(values, first, second),
                        (left, right, gamma, first, second))

    def test_coarse_endpoint_minima_really_do_not_certify_lift(self):
        self.assertTrue(self.result["coarse_printed_IIb_test"]["rejected"])
        capacities = tuple(Q(text) for text in
                           self.result["coarse_printed_IIb_test"]["capacities"])
        with self.assertRaises(ArithmeticError):
            v.fixed_partition_certificate(
                1, 9, v.INNER_CAP, v.NEW_OUTER[8], capacities)

    def test_every_advertised_sliver_has_positive_measure_witness(self):
        witnesses = self.result[
            "support_and_embedding"]["strict_open_witnesses"]
        self.assertEqual([item["count"] for item in witnesses], list(range(1, 12)))
        for item in witnesses:
            self.assertGreater(Q(item["old_cap_violation"]), 0)
            self.assertGreater(Q(item["new_cap_slack"]), 0)
            self.assertGreater(Q(item["large_coordinate"]), v.DELTA)
            self.assertLess(Q(item["small_coordinate"]), v.DELTA)


if __name__ == "__main__":
    unittest.main()
