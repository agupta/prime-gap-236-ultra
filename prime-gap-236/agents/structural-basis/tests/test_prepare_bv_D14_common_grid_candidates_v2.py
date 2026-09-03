#!/usr/bin/env python3

from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys
import unittest


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = REPO / (
    "agents/structural-basis/code/prepare_bv_D14_common_grid_candidates_v2.py")
SOURCE_SHA256 = "83dfdd7d88ee7f2f2a4dfbf492af693b9ae99c2bfaf983816c0fdcdec3229a57"
RESULT = REPO / (
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json")
RESULT_SHA256 = "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class D14FineGridTest(unittest.TestCase):
    def test_frozen_result(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        self.assertEqual(digest(RESULT), RESULT_SHA256)
        data = json.loads(RESULT.read_bytes())
        self.assertEqual(
            data["status"],
            "EXACT D14 FINE COMMON-GRID PARTICULAR VECTORS PASS")
        self.assertEqual([row["grid_digits"] for row in data["candidates"]],
                         [38, 40, 42])

    def test_exact_quotients_remain_close(self):
        data = json.loads(RESULT.read_bytes())
        original = Q(data["source_D14"]["exact_quotient"])
        for row in data["candidates"]:
            quotient = Q(row["exact_quotient"])
            self.assertEqual(
                Q(row["absolute_quotient_change"]), abs(quotient - original))
            self.assertLess(abs(quotient - original), Q(1, 10**20))
            self.assertGreater(quotient, Q(97, 100))

    def test_rounding_and_common_grid(self):
        data = json.loads(RESULT.read_bytes())
        for row in data["candidates"]:
            digits = row["grid_digits"]
            self.assertLessEqual(
                Q(row["maximum_absolute_coefficient_error"]),
                Q(1, 2 * 10**digits))
            for coefficient in row["rational_vector"]:
                self.assertEqual((Q(coefficient) * 10**digits).denominator, 1)


if __name__ == "__main__":
    unittest.main()
