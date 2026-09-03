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
SOURCE = REPO / "agents/structural-basis/code/check_bv_d12_d14_d16_vectors_direct_v1.py"
SOURCE_SHA256 = "9d5224cd36190dee55f3eebc69e78ef93f81273acaa29ba6db13cd1c5b2fe0b2"
RESULT = REPO / "agents/structural-basis/results/bv_D12_D14_D16_vectors_direct_exact_v1.json"
RESULT_SHA256 = "77884ae1197beace517fd758323e53b92d4cc8ef055ddf873ae4cd858625dbe4"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("lower_vector_checker_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LowerVectorDirectTest(unittest.TestCase):
    def test_frozen_closure_and_identity(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        self.assertEqual(digest(RESULT), RESULT_SHA256)
        data = json.loads(RESULT.read_bytes())
        self.assertEqual(
            data["status"],
            "INDEPENDENT EXACT LOWER-DEGREE PARTICULAR VECTORS PASS")
        self.assertTrue(data["rigorous"])
        self.assertFalse(data["cache_read"])
        self.assertFalse(data["serialized_matrix_entries_read"])
        self.assertEqual(data["checker_sha256"], SOURCE_SHA256)
        self.assertEqual(
            [(row["degree"], row["basis_dimension"]) for row in data["rows"]],
            [(12, 120), (14, 195), (16, 307)])

    def test_exact_form_algebra_and_inventories(self):
        data = json.loads(RESULT.read_bytes())
        expected = [(1508, 120, 1508), (3034, 195, 3034),
                    (5825, 307, 5825)]
        for row, inventory in zip(data["rows"], expected):
            denominator = Q(row["exact_denominator"])
            numerator = Q(row["exact_numerator_48J"])
            self.assertGreater(denominator, numerator)
            self.assertGreater(numerator, 0)
            self.assertEqual(Q(row["exact_quotient"]), numerator / denominator)
            self.assertEqual(
                Q(row["exact_normalized_deficit"]),
                (denominator - numerator) / denominator)
            counts = row["term_counts"]
            self.assertEqual(
                (counts["square_product_groups"], counts["marginal_groups"],
                 counts["marginal_square_product_groups"]), inventory)

    def test_literal_low_k_oracle(self):
        module = load_source()
        scan = module.load_module("lower_vector_checker_low_k_scan", module.SCAN)
        scan.self_test()


if __name__ == "__main__":
    unittest.main()
