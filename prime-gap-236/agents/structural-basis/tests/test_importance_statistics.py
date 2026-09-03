#!/usr/bin/env python3

import importlib
import math
import sys
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
MOD = importlib.import_module("importance_statistics")


class ImportanceStatisticsTests(unittest.TestCase):
    def test_split_rhat_detects_between_chain_shift(self):
        base = np.array([0.0, 1.0, 0.0, 1.0,
                         0.0, 1.0, 0.0, 1.0])
        identical = np.stack((base, base, base))[:, :, None]
        self.assertEqual(float(MOD.split_rhat(identical)[0]), 1.0)
        shifted = identical.copy()
        shifted[2] += 20
        self.assertGreater(float(MOD.split_rhat(shifted)[0]), 2.0)
        overflow = np.full((2, 4, 1), 1e308)
        overflow[1] *= -1
        self.assertTrue(math.isinf(float(MOD.split_rhat(overflow)[0])))
        with self.assertRaises(ValueError):
            MOD.split_rhat(np.zeros((1, 8)))

    def test_batch_ess_is_bounded_and_constant_safe(self):
        batches = np.array([[[1.0], [2.0], [1.0], [2.0]],
                            [[1.5], [2.5], [1.5], [2.5]]])
        mean = np.mean(batches, axis=(0, 1))
        ess = MOD.batch_means_ess(
            mean, np.array([3.75]), batches, 10)
        self.assertGreaterEqual(float(ess[0]), 1)
        self.assertLessEqual(float(ess[0]), 80)
        constant = MOD.batch_means_ess(
            np.array([3.0]), np.array([9.0]), np.full((2, 4, 1), 3.0), 10)
        self.assertEqual(float(constant[0]), 80)
        with self.assertRaises(ValueError):
            MOD.batch_means_ess(
                np.array([0.0]), np.array([1.0]), np.zeros((1, 1, 1)), 10)
        with self.assertRaises(ArithmeticError):
            MOD.batch_means_ess(
                np.array([10.0]), np.array([0.0]),
                np.zeros((2, 4, 1)), 10)
        alternating = np.array([[[-1e-3], [1e-3], [-1e-3], [1e-3]],
                                [[-1e-3], [1e-3], [-1e-3], [1e-3]]])
        with self.assertRaises(ArithmeticError):
            MOD.batch_means_ess(
                np.array([0.0]), np.array([0.0]), alternating, 10)

    def test_joint_ratio_delta_identity(self):
        z = np.array([[0.5, 1.0, 1.5, 2.0],
                      [0.75, 1.25, 1.75, 0.25]])
        fixed = np.array([[0.2, -0.05], [-0.05, 0.3]])
        y = z[..., None, None] * fixed
        result = MOD.ratio_matrix_delta(y, z)
        np.testing.assert_allclose(result["ratio"], fixed, rtol=0, atol=1e-15)
        np.testing.assert_allclose(
            result["standard_error"], 0, rtol=0, atol=1e-16)
        with self.assertRaises(ArithmeticError):
            MOD.ratio_matrix_delta(y, -z)
        with self.assertRaises(ArithmeticError):
            MOD.ratio_matrix_delta(y, np.array([[-1.0, 3.0, 1.0, 1.0],
                                                [1.0, 1.0, 1.0, 1.0]]))
        tiny_z = np.full((2, 4), 1e-320)
        huge_ratio_y = np.ones((2, 4, 1, 1))
        with self.assertRaises(ArithmeticError):
            MOD.ratio_matrix_delta(huge_ratio_y, tiny_z)
        negative_diagonal = y.copy()
        negative_diagonal[0, 0, 0, 0] = -0.1
        with self.assertRaises(ArithmeticError):
            MOD.ratio_matrix_delta(negative_diagonal, z)
        oversized_cross = y.copy()
        oversized_cross[0, 0, 0, 1] = 0.6
        oversized_cross[0, 0, 1, 0] = 0.6
        with self.assertRaises(ArithmeticError):
            MOD.ratio_matrix_delta(oversized_cross, z)
        nonsymmetric = y.copy()
        nonsymmetric[0, 0, 0, 1] = 0.1
        with self.assertRaises(ArithmeticError):
            MOD.ratio_matrix_delta(nonsymmetric, z)

    def test_generalized_root_and_indefinite_rejection(self):
        a = np.diag([4.0, 9.0, 0.0])
        b = np.diag([8.0, 9.0, 0.0])
        result = MOD.largest_generalized_root(
            a, b, base_quotient=0.75, active_indices=[0, 1])
        self.assertAlmostEqual(result["root"], 1.5)
        self.assertAlmostEqual(result["root"], result["rayleigh"])
        self.assertEqual(result["rank"], 2)
        # A tiny but exactly active coordinate must survive diagonal
        # equilibration; global magnitude thresholding would drop it.
        rare = MOD.largest_generalized_root(
            np.diag([1.0, 1e-30]), np.diag([1.0, 2e-30]),
            active_indices=[0, 1])
        self.assertAlmostEqual(rare["root"], 2.0)
        with self.assertRaises(ArithmeticError):
            MOD.largest_generalized_root(a, b)
        with self.assertRaises(ArithmeticError):
            MOD.largest_generalized_root(
                np.diag([1.0, 1.0]), np.diag([1.0, 100.0]),
                active_indices=[0])
        antisymmetric = np.array([[1.0, 1.0], [-1.0, 0.0]])
        with self.assertRaises(ArithmeticError):
            MOD.largest_generalized_root(
                antisymmetric, np.zeros((2, 2)), active_indices=[0])
        with self.assertRaises(ArithmeticError):
            MOD.largest_generalized_root(np.diag([1.0, -0.1]), np.eye(2))

    def test_zero_width_coverage_fails_closed(self):
        estimate = np.array([[1.0, 0.0], [0.0, 2.0]])
        exact = np.array([[1.0, 1e-9], [1e-9, 2.0]])
        error = np.zeros((2, 2))
        mask = np.ones((2, 2), dtype=bool)
        result = MOD.simultaneous_coverage(
            estimate, error, exact, mask, multiplier=6)
        self.assertFalse(result["pass"])
        self.assertEqual(set(result["failed_indices"]), {(0, 1), (1, 0)})
        self.assertTrue(math.isinf(result["max_standardized_discrepancy"]))


if __name__ == "__main__":
    unittest.main()
