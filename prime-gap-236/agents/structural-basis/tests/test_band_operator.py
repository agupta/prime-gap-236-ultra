#!/usr/bin/env python3
"""Exact fail tests for the discovery-only degree-band gradient operator."""

import json
import os
import sys
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
STRUCTURAL = os.path.abspath(os.path.join(HERE, ".."))
EXACT_AGENT = os.path.abspath(os.path.join(STRUCTURAL, "..", "exact-integrator"))
sys.path[:0] = [os.path.join(STRUCTURAL, "code"), EXACT_AGENT,
                os.path.join(EXACT_AGENT, "src")]

import exact_integrator as ei  # noqa: E402
from band_operator import (BandMap, BandOperator,  # noqa: E402
                           full_simplex_i_preconditioner)
from band_operator_sparse import SparseBandOperator  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator  # noqa: E402


class BandOperatorTests(unittest.TestCase):
    def setUp(self):
        self.support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        self.labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        # The last compressed direction deliberately combines two labels with
        # nontrivial rational weights, exercising genuine band aggregation.
        self.owner = [0, 1, 2, 2]
        self.weights = [Q(1), Q(1), Q(2), Q(-1, 3)]
        self.theta = [Q(2), Q(-3), Q(5)]
        self.band_map = BandMap.from_explicit(
            self.labels, self.owner, self.weights, self.theta)

    def compressed_matrices(self, support=None):
        support = support or self.support
        m1, m2 = support.matrices(self.labels)
        n = self.band_map.dimension
        a = [[Q(0) for _ in range(n)] for _ in range(n)]
        b = [[Q(0) for _ in range(n)] for _ in range(n)]
        for p in range(len(self.labels)):
            for q in range(len(self.labels)):
                i, j = self.owner[p], self.owner[q]
                factor = self.weights[p] * self.weights[q]
                a[i][j] += factor * m1[p][q]
                b[i][j] += factor * m2[p][q]
        return a, b

    @staticmethod
    def quadratic(matrix, theta):
        return sum(theta[i] * matrix[i][j] * theta[j]
                   for i in range(len(theta)) for j in range(len(theta)))

    @staticmethod
    def matvec(matrix, theta):
        return [sum(matrix[i][j] * theta[j] for j in range(len(theta)))
                for i in range(len(theta))]

    def test_exact_jet_value_gradient_euler_and_polarization(self):
        result = BandOperator(
            self.support, self.band_map, self.theta, Q).apply()
        a, b = self.compressed_matrices()
        self.assertEqual(result["denominator"], self.quadratic(a, self.theta))
        self.assertEqual(result["numerator"], self.quadratic(b, self.theta))
        self.assertEqual(list(result["a_theta"]), self.matvec(a, self.theta))
        self.assertEqual(list(result["b_theta"]), self.matvec(b, self.theta))
        self.assertEqual(result["euler_denominator_error"], 0)
        self.assertEqual(result["euler_numerator_error"], 0)
        for matrix, gradient in ((a, result["grad_denominator"]),
                                 (b, result["grad_numerator"])):
            for i in range(len(self.theta)):
                plus, minus = list(self.theta), list(self.theta)
                plus[i] += 1
                minus[i] -= 1
                central = (self.quadratic(matrix, plus) -
                           self.quadratic(matrix, minus)) / 2
                self.assertEqual(central, gradient[i])

    def test_jet_value_equals_independent_scalar_grouped_evaluator(self):
        coefficients = [self.weights[i] * self.theta[self.owner[i]]
                        for i in range(len(self.labels))]
        scalar = GroupedEvaluator(
            self.support, self.labels, coefficients, Q)
        denominator, _, _ = scalar.evaluate_i()
        j_value, _, _ = scalar.evaluate_j()
        result = BandOperator(
            self.support, self.band_map, self.theta, Q).apply()
        self.assertEqual(result["denominator"], denominator)
        self.assertEqual(result["numerator"], self.support.k * j_value)

    def test_serial_equals_two_fork_workers_channel_by_channel(self):
        serial = BandOperator(
            self.support, self.band_map, self.theta, Q).apply(workers=1)
        parallel = BandOperator(
            self.support, self.band_map, self.theta, Q).apply(workers=2)
        for key in ("denominator", "numerator", "a_theta", "b_theta",
                    "grad_denominator", "grad_numerator",
                    "euler_denominator_error", "euler_numerator_error"):
            self.assertEqual(parallel[key], serial[key], key)

    def test_sparse_structure_of_arrays_equals_dense_jet_exactly(self):
        dense = BandOperator(
            self.support, self.band_map, self.theta, Q).apply(workers=1)
        sparse = SparseBandOperator(
            self.support, self.band_map, self.theta, Q).apply(workers=1)
        for key in ("denominator", "numerator", "a_theta", "b_theta",
                    "grad_denominator", "grad_numerator",
                    "euler_denominator_error", "euler_numerator_error",
                    "i_orbit_groups", "i_faces", "marginal_components",
                    "j_branch_integrals"):
            self.assertEqual(sparse[key], dense[key], key)

    def test_sparse_serial_equals_two_fork_workers(self):
        serial = SparseBandOperator(
            self.support, self.band_map, self.theta, Q).apply(workers=1)
        parallel = SparseBandOperator(
            self.support, self.band_map, self.theta, Q).apply(workers=2)
        for key in ("denominator", "numerator", "a_theta", "b_theta",
                    "grad_denominator", "grad_numerator",
                    "euler_denominator_error", "euler_numerator_error"):
            self.assertEqual(parallel[key], serial[key], key)

    def test_sparse_k1_boundary_assignment_matches_dense(self):
        support = ei.OneStratumSupport(
            1, Q(1, 10), Q(1, 10), Q(1, 10),
            Q(3, 20), Q(3, 20), Q(17, 100))
        band_map = BandMap.from_explicit(
            [(0, ())], [0], [Q(1)], [Q(1)])
        dense = BandOperator(support, band_map, [Q(1)], Q).apply()
        sparse = SparseBandOperator(support, band_map, [Q(1)], Q).apply()
        for key in ("denominator", "numerator", "grad_denominator",
                    "grad_numerator", "euler_denominator_error",
                    "euler_numerator_error"):
            self.assertEqual(sparse[key], dense[key], key)
        self.assertEqual(sparse["denominator"], Q(1, 10))
        self.assertEqual(sparse["numerator"], Q(1, 100))

    def test_sparse_cross_branch_derivative_survives_scalar_cancellation(self):
        operator = SparseBandOperator(
            self.support, self.band_map, self.theta, Q)
        empty = {}
        left_dirs = [{} for _ in range(self.band_map.dimension)]
        right_dirs = [{} for _ in range(self.band_map.dimension)]
        left_dirs[0] = {(): {(0, 0): Q(3)}}
        right_value = {(): {(0, 0): Q(5)}}
        channels = operator.branch_product_channels(
            empty, right_value, left_dirs, right_dirs, False)
        self.assertFalse(channels[0])
        self.assertEqual(channels[1], {(): {(0, 0): Q(30)}})

    def test_full_simplex_preconditioner_equals_pairwise_matrix(self):
        full = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(13, 50), Q(13, 50), Q(13, 50))
        expected, _ = self.compressed_matrices(full)
        actual = full_simplex_i_preconditioner(
            self.band_map, 3, Q(13, 50), Q)
        self.assertEqual(actual, expected)

    def test_d12_band_map_reconstructs_every_source_coefficient(self):
        source = os.path.join(
            EXACT_AGENT, "results", "hb_c10_fullsimplex_noones_D12.json")
        bands = os.path.join(
            STRUCTURAL, "results", "c10_D12_degree_bands.json")
        band_map = BandMap.from_source_and_bands(source, bands)
        with open(source, encoding="utf-8") as stream:
            raw = json.load(stream)
        self.assertEqual(band_map.dimension, 20)
        self.assertEqual(len(band_map.labels), 272)
        self.assertEqual(
            band_map.expand(band_map.theta0_q),
            [Q(x) for x in raw["rational_vector"]])


if __name__ == "__main__":
    unittest.main()
