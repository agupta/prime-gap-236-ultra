#!/usr/bin/env python3

import importlib
import sys
import unittest
from fractions import Fraction
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "code"))
MOD = importlib.import_module("importance_d4_rank_postmortem")
MOD.np = np


class ExactWhiteningPostmortemTests(unittest.TestCase):
    def test_exact_ldlt_power_two_transform(self):
        a = [
            [Fraction(1, 64), Fraction(1, 128), Fraction(0)],
            [Fraction(1, 128), Fraction(5, 256), Fraction(1, 64)],
            [Fraction(0), Fraction(1, 64), Fraction(5, 4)],
        ]
        lower, diagonal = MOD.exact_ldlt(a)
        scales, exponents, scaled = MOD.power_two_equilibrators(diagonal)
        transform = MOD.exact_whitening_transform(lower, scales)
        self.assertEqual(len(exponents), 3)
        self.assertTrue(all(1 <= value < 4 for value in scaled))

        exact_transformed = []
        for i in range(3):
            row = []
            for j in range(3):
                row.append(sum(
                    transform[k][i] * a[k][ell] * transform[ell][j]
                    for k in range(3) for ell in range(3)))
            exact_transformed.append(row)
        self.assertEqual(
            exact_transformed,
            [[scaled[i] if i == j else 0 for j in range(3)]
             for i in range(3)])

    def test_float_rank_is_restored_without_dropping_coordinates(self):
        # A badly scaled exact SPD form fails a global unscaled threshold,
        # while the fixed exact transform retains all three directions.
        exact = [
            [Fraction(1), Fraction(1, 2), Fraction(0)],
            [Fraction(1, 2), Fraction(1), Fraction(0)],
            [Fraction(0), Fraction(0), Fraction(1, 10**18)],
        ]
        lower, diagonal = MOD.exact_ldlt(exact)
        scales, _, _ = MOD.power_two_equilibrators(diagonal)
        transform = MOD.exact_whitening_transform(lower, scales)
        sampled = np.asarray([[float(x) for x in row] for row in exact])
        whitened = MOD.transform_float_form(sampled, transform)
        spectrum = MOD.equilibrated_spectrum(whitened)
        self.assertEqual(spectrum["rank"], 3)
        self.assertGreater(spectrum["smallest"], 0)

    def test_indefinite_or_singular_exact_oracle_rejects(self):
        for matrix in (
                [[1, 1], [1, 1]],
                [[1, 2], [2, 1]],
                [[1, 0], [1, 1]]):
            with self.assertRaises((ArithmeticError, ValueError)):
                MOD.exact_ldlt(matrix)

    def test_deletion_summary_cannot_hide_one_rank_failure(self):
        counts = {0: 1, 1: 2, 2: 3}
        rows = []
        for index in range(128):
            spectra = {}
            for degree, dimension in counts.items():
                original_rank = dimension - (
                    1 if index == 17 and degree == 2 else 0)
                spectra[str(degree)] = {
                    "original": {
                        "rank": original_rank, "smallest": 1e-13,
                        "condition_if_positive": 10.0},
                    "whitened": {
                        "rank": dimension, "smallest": 0.5,
                        "condition_if_positive": 2.0},
                }
            rows.append({"identity": {"index": index},
                         "spectra": spectra})
        summary = MOD.deletion_rank_summary(rows, counts)
        self.assertEqual(summary["2"]["original_rank_failure_count"], 1)
        self.assertEqual(summary["2"]["whitened_rank_failure_count"], 0)
        self.assertEqual(
            summary["2"]["original_rank_failures"][0]["identity"],
            {"index": 17})


if __name__ == "__main__":
    unittest.main()
