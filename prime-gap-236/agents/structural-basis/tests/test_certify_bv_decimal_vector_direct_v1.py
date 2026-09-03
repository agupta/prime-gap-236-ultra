#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "code" /
          "certify_bv_decimal_vector_direct_v1.py")
spec = importlib.util.spec_from_file_location("direct_decimal_cert_test", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class DirectDecimalVectorTests(unittest.TestCase):
    def test_significant_grid(self):
        self.assertEqual(module.rationalize_significant("1.23456789", 5),
                         Q(12346, 10000))
        self.assertEqual(module.rationalize_significant("-0E-90", 60), Q(0))

    def test_basis_inventory(self):
        scan = module.load_module("direct_decimal_inventory_test", module.SCAN)
        self.assertEqual(len(module.expected_basis(scan.ei, 18)), 471)
        self.assertEqual(len(module.expected_basis(scan.ei, 20)), 707)

    def test_full_simplex_delta_independence_low_degree(self):
        scan = module.load_module("direct_decimal_forms_test", module.SCAN)
        basis = ((0, ()), (1, ()), (0, (2,)))
        vector = (Q(3, 2), Q(-7, 3), Q(5, 11))
        left = scan.direct_forms(
            4, basis, vector, Q(1, 3), Q(1, 4), Q(1, 20))
        right = scan.direct_forms(
            4, basis, vector, Q(1, 3), Q(1, 4), Q(1, 7))
        self.assertEqual(left, right)
        self.assertGreater(left[0], 0)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            module.rationalize_significant("NaN", 60)


if __name__ == "__main__":
    unittest.main()
