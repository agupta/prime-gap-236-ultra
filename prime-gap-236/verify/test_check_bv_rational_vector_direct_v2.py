#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("check_bv_rational_vector_direct_v2.py")
SPEC = importlib.util.spec_from_file_location("bv_rational_direct_v2_tested", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def candidate(degree=19):
    dimension = MODULE.DIMENSIONS[degree]
    return {
        "k": 48, "degree": 20, "basis_dimension": dimension,
        "basis": [[0, []] for _ in range(dimension)],
        "rational_vector": ["1" for _ in range(dimension)],
        "exact_denominator": "1", "exact_numerator": "1",
        "exact_quotient": "1",
        "exact_deficit_over_denominator": "0",
    }


class DirectRationalVectorV2Tests(unittest.TestCase):
    def test_v1_pin(self):
        self.assertEqual(MODULE.sha256(MODULE.V1), MODULE.V1_SHA256)

    def test_valid_wire_shape(self):
        row = candidate()
        self.assertIs(MODULE.validate_candidate_wire(row, 19), row)

    def test_float_basis_exponent_rejected(self):
        row = candidate()
        row["basis"][0][0] = 0.5
        with self.assertRaises(ValueError):
            MODULE.validate_candidate_wire(row, 19)

    def test_noninteger_partition_parts_rejected(self):
        for bad in (2.0, "2", True, -2):
            row = candidate()
            row["basis"][0][1] = [bad]
            with self.assertRaises(ValueError):
                MODULE.validate_candidate_wire(row, 19)

    def test_identity_numbers_and_rationals_are_typed(self):
        for key, bad in (("k", 48.0), ("degree", "20"),
                         ("basis_dimension", True),
                         ("exact_denominator", 1)):
            row = candidate()
            row[key] = bad
            with self.assertRaises(ValueError):
                MODULE.validate_candidate_wire(row, 19)

    def test_noncanonical_rationals_rejected(self):
        for bad in ("1.0", "01", "+1", "2/2", "1/01", "-0", " 1"):
            row = candidate()
            row["rational_vector"][0] = bad
            with self.assertRaises(ValueError):
                MODULE.validate_candidate_wire(row, 19)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                MODULE.strict_json(raw, Path("hostile.json"))


if __name__ == "__main__":
    unittest.main()
