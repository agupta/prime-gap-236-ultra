#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from itertools import combinations, permutations
import math
from pathlib import Path
import sys
import unittest

import numpy as np


TARGET = Path(__file__).parents[1] / "code/active25_d18_cap_adapted_oracle_v1.py"
SPEC = importlib.util.spec_from_file_location("d18_cap_adapted_oracle_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def literal_orbit(point, partition):
    if not partition:
        return 1
    return sum(math.prod(point[index] ** exponent
                         for index, exponent in zip(indices, assignment))
               for indices in combinations(range(len(point)), len(partition))
               for assignment in set(permutations(partition)))


class D18CapAdaptedOracleTest(unittest.TestCase):
    def tearDown(self):
        M.configure_geometry("audited")

    def test_basis_contains_old_and_riesz_coordinates(self):
        labels = M.candidate_labels()
        self.assertEqual(len(labels), 15)
        self.assertEqual(labels[:3], (
            ("inner_d18", None, 0),
            ("riesz_d18", None, 0),
            ("natural_outer_d18", None, 0)))
        self.assertEqual(len(set(labels)), len(labels))

    def test_dilation_formula_literal(self):
        basis = ((0, ()), (1, ()), (2, ()), (0, (2,)), (1, (2,)))
        vector = (Q(2), Q(-3), Q(5), Q(7), Q(-11))
        factor = Q(3, 5)
        dilated = M.dilate_vector(basis, vector, factor)
        for t in (Q(1, 10), Q(2, 9)):
            source = sum(c * (1 - factor * t) ** a *
                         literal_orbit((factor * t,), lam)
                         for c, (a, lam) in zip(vector, basis))
            target = sum(c * (1 - t) ** a * literal_orbit((t,), lam)
                         for c, (a, lam) in zip(dilated, basis))
            self.assertEqual(source, target)

    def test_power_sum_orbits_against_literal(self):
        partitions = ((), (2,), (4, 2), (2, 2, 2))
        evaluator = M.PowerSumOrbitEvaluator(partitions)
        point = np.zeros((1, M.K), dtype=np.longdouble)
        point[0, :4] = [0.03, 0.05, 0.07, 0.11]
        observed = evaluator.evaluate(point)
        literal_point = tuple(float(x) for x in point[0])
        for partition in partitions:
            self.assertAlmostEqual(
                float(observed[evaluator.index[partition], 0]),
                literal_orbit(literal_point, partition), places=14)

    def test_exact_low_k_riesz_identity_and_factor(self):
        row = M.low_k_riesz_oracle()
        self.assertTrue(row["exact_identity_pass"])
        self.assertEqual(row["factor_k"], 2)
        self.assertEqual(Q(row["I_of_G_on_cap"]),
                         Q(row["sum_i_Ji_F_G"]))
        self.assertGreater(Q(row["I_of_G_on_cap"]), 0)

    def test_exact_shell_recurrence_matches_frozen_audited_d0(self):
        M.configure_geometry("audited")
        _cert, _uncapped, d0, *_ = M.load_inputs()
        expected = {i: Q(value) for i, j, value in d0["I_upper_nonzero"]
                    if i == j}
        self.assertEqual(M.exact_shell_volumes(),
                         tuple(expected.get(r, Q(0)) for r in range(26)))

    def test_sampler_stays_in_literal_count_container(self):
        M.configure_geometry("audited")
        points, volume = M.sample_count_cell(
            np.random.default_rng(17), M.K, 10, 64)
        large = points > M.ld(M.DELTA)
        self.assertTrue(np.all(np.sum(large, axis=1) == 10))
        excess = np.where(large, points - M.ld(M.DELTA), 0)
        self.assertTrue(np.all(np.sum(excess, axis=1) <= M.ld(M.gamma(10))))
        expected_volume = (math.comb(M.K, 10) * M.ld(M.gamma(10)) ** 10 /
                           math.factorial(10) * M.ld(M.DELTA) ** 38)
        self.assertEqual(volume, expected_volume)

    def test_upper_shell_importance_geometry_and_weight(self):
        M.configure_geometry("d014")
        count, samples = 6, 128
        points, weights, accepted = M.sample_upper_shell_importance(
            np.random.default_rng(236), M.K, count, samples)
        delta = M.ld(M.DELTA)
        excess = points[:, :count] - delta
        small = points[:, count:]
        effective = min(M.gamma(count), M.ALPHA2 - count * M.DELTA)
        self.assertTrue(np.all(excess >= 0))
        self.assertTrue(np.all(np.sum(excess, axis=1) <= M.ld(effective)))
        vmax = (M.ld(M.ALPHA2 - count * M.DELTA) -
                np.sum(excess, axis=1, dtype=np.longdouble))
        self.assertTrue(np.all(np.sum(small, axis=1) <=
                               vmax + np.longdouble("1e-18")))
        vol_x = M.ld(effective) ** count / math.factorial(count)
        expected = M.upper_shell_importance_weight(
            M.K, count, vol_x, vmax)
        self.assertTrue(np.allclose(weights, expected, rtol=2e-15, atol=0))
        total = np.sum(points, axis=1, dtype=np.longdouble)
        literal = ((np.max(small, axis=1) <= delta) &
                   (total > M.ld(M.ALPHA1)) &
                   (total < M.ld(M.ALPHA2) + np.longdouble("1e-18")))
        self.assertTrue(np.array_equal(accepted, literal))

    def test_exact_low_k_importance_weight(self):
        row = M.low_k_importance_oracle()
        self.assertTrue(row["exact_identity_pass"])
        self.assertEqual(Q(row["direct_shell_volume"]), Q(1, 100))
        self.assertEqual(Q(row["importance_expectation"]), Q(1, 100))

    def test_joint_upper_simplex_tilt_has_constant_weight(self):
        M.configure_geometry("d1over60")
        count, samples = 5, 128
        points, weights, accepted = M.sample_joint_upper_simplex_importance(
            np.random.default_rng(237), M.K, count, samples)
        radial = M.ld(M.ALPHA2 - count * M.DELTA)
        expected = (math.comb(M.K, count) * radial ** M.K /
                    math.factorial(M.K))
        self.assertTrue(np.all(weights == expected))
        excess = points[:, :count] - M.ld(M.DELTA)
        small = points[:, count:]
        total = np.sum(points, axis=1, dtype=np.longdouble)
        literal = ((np.sum(excess, axis=1) <= M.ld(M.gamma(count))) &
                   (np.max(small, axis=1) <= M.ld(M.DELTA)) &
                   (total > M.ld(M.ALPHA1)) &
                   (total < M.ld(M.ALPHA2) + np.longdouble("1e-18")))
        self.assertTrue(np.array_equal(accepted, literal))

    def test_leave_one_out_riesz_matches_literal_loop(self):
        cert, _uncapped, _d0, basis, vector, _outer = M.load_inputs()
        inner = M.ResidualD18(basis, vector, center=M.ALPHA1, dilation=1)
        marginal = M.MarginalD18(basis, vector, inner.scale)
        points, _ = M.sample_count_cell(
            np.random.default_rng(31), M.K, 8, 1)
        omitted = marginal.omit_values(points)
        for i in (0, 7, 20, 47):
            padded = points[0].copy()
            padded[i] = 0
            self.assertAlmostEqual(float(omitted[0, i]),
                                   float(marginal.evaluate(padded[None, :])[0]),
                                   places=12)
        vectorized = marginal.riesz(points)
        total = np.sum(points, axis=1, dtype=np.longdouble)[:, None]
        literal = np.sum(omitted * (total - points <= M.ld(M.ETA2)), axis=1)
        self.assertTrue(np.allclose(vectorized, literal, rtol=2e-12,
                                    atol=1e-100))

    def test_sufficient_threshold_is_exactly_one_minus_q(self):
        q = .985
        threshold = 1 - q
        self.assertLess(M.lower_riesz_quotient(q, threshold * .99), 1)
        self.assertAlmostEqual(M.lower_riesz_quotient(q, threshold), 1)
        self.assertGreater(M.lower_riesz_quotient(q, threshold * 1.01), 1)
        self.assertEqual(M.screen_decision(True, .001, .0001, .01),
                         "HEURISTIC FALSIFICATION")
        self.assertEqual(M.screen_decision(True, .02, .001, .01),
                         "GATED EXACT COMPUTATION WARRANTED")

    def test_d014_is_explicitly_conditional(self):
        M.configure_geometry("d014")
        plan = M.build_preflight()
        self.assertFalse(plan["geometry_analytically_approved"])
        self.assertFalse(plan["launch_authorized"])
        self.assertFalse(plan["exact_target_started"])
        self.assertEqual(M.DELTA, Q(7, 500))
        self.assertEqual(M.ALPHA2, Q(79597, 300000))
        self.assertEqual(M.ETA2, Q(75097, 300000))
        self.assertEqual(M.MAX_ACTIVE_COUNT, 13)

    def test_d014_seed2361817_point_regression(self):
        M.configure_geometry("d014")
        _cert, _uncapped, _d0, basis, vector, outer = M.load_inputs()
        inner = M.ResidualD18(basis, vector, center=M.ALPHA1, dilation=1)
        natural = M.ResidualD18(
            basis, vector, center=M.ALPHA2, dilation=M.OUTER_C)
        row = M.point_consistency(
            inner, natural, basis, vector, outer, 2361817 + 1000003)
        observed = Q(row["maximum_relative_error"])
        self.assertGreater(observed, Q(1, 10**9))
        self.assertLess(observed, Q(1, 10**7))
        self.assertEqual(row["accepted_relative_tolerance"], "1E-7")

    def test_d1over60_parameterization_is_conditional(self):
        M.configure_geometry("d1over60")
        plan = M.build_preflight()
        self.assertFalse(plan["geometry_analytically_approved"])
        self.assertEqual(M.DELTA, Q(1, 60))
        self.assertEqual(M.ALPHA2, Q(237991, 900000))
        self.assertEqual(M.ETA2, Q(224491, 900000))
        self.assertEqual(M.MAX_ACTIVE_COUNT, 11)


if __name__ == "__main__":
    unittest.main()
