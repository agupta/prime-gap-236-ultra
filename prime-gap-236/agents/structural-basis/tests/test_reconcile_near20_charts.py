#!/usr/bin/env python3
"""Exact regressions for the near20 affine-chart reconciliation."""

import copy
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
CODE = HERE.parent / "code"
sys.path.insert(0, str(CODE))

from reconcile_near20_charts import (H_PATH, H_SHA, RAW_PATH, RAW_SHA,  # noqa: E402
                                     load_bound, reconcile)


class ReconcileNear20ChartsTests(unittest.TestCase):
    def setUp(self):
        self.h = load_bound(H_PATH, H_SHA)
        self.raw = load_bound(RAW_PATH, RAW_SHA)

    def test_exact_chart_residual_and_negative_maximum(self):
        result = reconcile(self.h, self.raw)
        self.assertLess(result["h_best_q"], 1)
        self.assertLess(result["raw_best_q"], 1)
        self.assertLess(abs(result["stationary_q_difference"]),
                        Fraction(1, 10**60))
        self.assertNotEqual(result["h_chart_infinity_q"],
                            result["raw_chart_infinity_q"])

    def test_coefficient_mutation_is_rejected(self):
        altered = copy.deepcopy(self.h)
        altered["quadratic"]["D_coefficients"][1] = str(
            Fraction(altered["quadratic"]["D_coefficients"][1]) + 1)
        with self.assertRaisesRegex(ValueError, "D chart residual identity"):
            reconcile(altered, self.raw)


if __name__ == "__main__":
    unittest.main()
