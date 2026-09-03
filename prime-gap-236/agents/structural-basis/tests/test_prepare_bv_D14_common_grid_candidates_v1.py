#!/usr/bin/env python3

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = REPO / (
    "agents/structural-basis/code/prepare_bv_D14_common_grid_candidates_v1.py")
SOURCE_SHA256 = "55eece4f4fc15ae2112a55bb78eafd6d3e10f4e2a21d6a5981a165e853692787"
RESULT = REPO / (
    "agents/structural-basis/results/bv_D14_common_grid_candidates_exact_v1.json")
RESULT_SHA256 = "761bc005f666d57ac459d54d53a18f7b7c771c15c3af26e807bdac03d8810309"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("d14_grid_test_source", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class D14CommonGridTest(unittest.TestCase):
    def test_ties_to_even_for_both_signs(self):
        module = load_source()
        self.assertEqual(module.nearest_integer_ties_even(Q(5, 2)), 2)
        self.assertEqual(module.nearest_integer_ties_even(Q(7, 2)), 4)
        self.assertEqual(module.nearest_integer_ties_even(Q(-5, 2)), -2)
        self.assertEqual(module.nearest_integer_ties_even(Q(-7, 2)), -4)

    def test_frozen_exact_result(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        self.assertEqual(digest(RESULT), RESULT_SHA256)
        data = json.loads(RESULT.read_bytes())
        self.assertEqual(
            data["status"], "EXACT D14 COMMON-GRID PARTICULAR VECTORS PASS")
        self.assertTrue(data["rigorous"])
        self.assertFalse(data["cache_read"])
        self.assertEqual([row["grid_digits"] for row in data["candidates"]],
                         [16, 14, 12])

    def test_rounding_error_and_exact_forms(self):
        data = json.loads(RESULT.read_bytes())
        for row in data["candidates"]:
            digits = row["grid_digits"]
            self.assertLessEqual(
                Q(row["maximum_absolute_coefficient_error"]),
                Q(1, 2 * 10 ** digits))
            denominator = Q(row["exact_denominator"])
            numerator = Q(row["exact_numerator_48J"])
            self.assertEqual(Q(row["exact_quotient"]), numerator / denominator)
            self.assertEqual(
                Q(row["exact_normalized_deficit"]),
                (denominator - numerator) / denominator)
            # This is intentional negative evidence: even the 1e-16 grid
            # destroys the ill-conditioned high-quotient coordinate.
            self.assertLess(Q(row["exact_quotient"]), Q(1, 4))


if __name__ == "__main__":
    unittest.main()
