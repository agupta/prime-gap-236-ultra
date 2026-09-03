#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("check_bv_rational_vector_direct_v1.py")
SPEC = importlib.util.spec_from_file_location("bv_rational_direct_v1_tested", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DirectRationalVectorTests(unittest.TestCase):
    def test_source_pins_and_basis_inventories(self):
        self.assertEqual(MODULE.sha256(MODULE.SCAN), MODULE.SCAN_SHA256)
        self.assertEqual(MODULE.sha256(MODULE.INTEGRATOR), MODULE.INTEGRATOR_SHA256)
        scan = MODULE.load_module("bv_rational_inventory_test", MODULE.SCAN)
        self.assertEqual(len(MODULE.canonical_basis(scan.ei, 19)), 568)
        self.assertEqual(len(MODULE.canonical_basis(scan.ei, 20)), 707)

    def test_fraction_vector_validation(self):
        self.assertEqual(MODULE.parse_fraction_list(["3/5", "-2"], 2),
                         (Q(3, 5), Q(-2)))
        for raw, length in ((["0"], 1), ([1], 1), (["1"], 2),
                            (["1/0"], 1)):
            with self.assertRaises((ValueError, ArithmeticError)):
                MODULE.parse_fraction_list(raw, length)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.strict_json(b'{"x":1,"x":2}', Path("duplicate.json"))

    def test_full_simplex_delta_independence_low_degree(self):
        scan = MODULE.load_module("bv_rational_forms_test", MODULE.SCAN)
        basis = ((0, ()), (1, ()), (0, (2,)))
        vector = (Q(3, 2), Q(-7, 3), Q(5, 11))
        left = scan.direct_forms(
            4, basis, vector, Q(1, 3), Q(1, 4), Q(1, 20))
        right = scan.direct_forms(
            4, basis, vector, Q(1, 3), Q(1, 4), Q(1, 7))
        self.assertEqual(left, right)
        self.assertGreater(left[0], 0)


if __name__ == "__main__":
    unittest.main()
