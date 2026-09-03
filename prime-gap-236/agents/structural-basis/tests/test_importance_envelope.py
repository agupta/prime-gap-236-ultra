#!/usr/bin/env python3

import importlib
import math
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
ENV = importlib.import_module("importance_envelope")
DENSITY = importlib.import_module("importance_density")
EXACT_RESULTS = HERE.parents[2] / "exact-integrator" / "results"
PARAMETERS = EXACT_RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json"
D4 = EXACT_RESULTS / "c10_capped_D4_decimal55_vector_input.json"
D12 = EXACT_RESULTS / "hb_c10_fullsimplex_noones_D12_integer_scaled.json"


class CancellationAdapter:
    dimension = 12
    strata = (0, 1)
    delta = 0.5
    channels = tuple((r, a, b) for r in strata
                     for a, b in ((0, 0), (1, 0), (0, 1),
                                  (2, 0), (1, 1), (0, 2)))

    @staticmethod
    def j_support(common):
        return tuple(common) == (0.25,)

    @staticmethod
    def j_marginals(common):
        # The two constant tagged marginals cancel exactly in m0, while the
        # finite envelope remains nonzero.
        return [1.0, 2.0, 0, 0, 0, 0, -1.0, 3.0, 0, 0, 0, 0]

    @staticmethod
    def j_m0(common, marginals):
        return marginals[0] + marginals[6]


class LeakingConstantAdapter(CancellationAdapter):
    dimension = 18
    strata = (0, 1, 2)
    channels = tuple((r, a, b) for r in strata
                     for a, b in ((0, 0), (1, 0), (0, 1),
                                  (2, 0), (1, 1), (0, 2)))

    @staticmethod
    def j_marginals(common):
        # At common stratum zero, final stratum two is impossible.
        return [1.0, 0, 0, 0, 0, 0,
                -1.0, 0, 0, 0, 0, 0,
                0.25, 0, 0, 0, 0, 0]

    @staticmethod
    def j_m0(common, marginals):
        return marginals[0] + marginals[6] + marginals[12]


class ImportanceEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = DENSITY.C10ImportanceDensity(D4, PARAMETERS)

    def test_actual_d4_point_bounds_and_permutation(self):
        common = [0.02, 0.03] + [0.001] * 45
        first = ENV.j_envelope_point(self.adapter, common)
        second = ENV.j_envelope_point(
            self.adapter, common[13:] + common[:13])
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertAlmostEqual(
            math.fsum(x * x for x in first.unit_marginals), 1.0, places=14)
        self.assertLessEqual(first.z, first.nonzero_constant_channels)
        self.assertAlmostEqual(first.log_g, second.log_g, places=12)
        self.assertAlmostEqual(first.z, second.z, places=13)
        for left, right in zip(first.unit_marginals, second.unit_marginals):
            self.assertAlmostEqual(left, right, places=13)
        for i in range(96):
            self.assertGreaterEqual(ENV.bounded_outer_entry(first, i, i), 0)
        for i in range(1, 96):
            self.assertLessEqual(abs(ENV.bounded_outer_entry(first, 0, i)),
                                 0.5 + 16 * math.ulp(1.0))

    def test_cancellation_zero_is_nonsingular(self):
        point = ENV.j_envelope_point(CancellationAdapter(), [0.25])
        self.assertIsNotNone(point)
        self.assertEqual(point.z, 0.0)
        self.assertTrue(math.isfinite(point.log_g))
        self.assertAlmostEqual(
            math.fsum(x * x for x in point.unit_marginals), 1.0)

    def test_off_support_zero_envelope_and_bad_indices(self):
        self.assertIsNone(ENV.j_envelope_point(CancellationAdapter(), [0.5]))
        self.assertEqual(
            ENV.j_envelope_log_density(CancellationAdapter(), [0.5]),
            -math.inf)
        point = ENV.j_envelope_point(CancellationAdapter(), [0.25])
        with self.assertRaises(IndexError):
            ENV.bounded_outer_entry(point, -1, 0)
        with self.assertRaises(IndexError):
            ENV.bounded_outer_entry(point, True, 0)

    def test_three_constant_or_wrong_stratum_leak_fails(self):
        with self.assertRaisesRegex(ArithmeticError, "outside"):
            ENV.j_envelope_point(LeakingConstantAdapter(), [0.25])

    def test_bounded_envelope_ratio_identity_on_discrete_fixture(self):
        # Equal-volume points in one common stratum.  This reconstructs the
        # algebra independently of j_envelope_point and of any Markov chain.
        marginal_rows = (
            (1.0, 2.0, -1.0),
            (2.0, -1.0, 0.5),
            (-1.0, 3.0, 1.0),
        )
        g = [math.fsum(x * x for x in row) for row in marginal_rows]
        total_g = math.fsum(g)
        m0 = [row[0] + row[2] for row in marginal_rows]
        j0 = math.fsum(x * x for x in m0)
        for i in range(3):
            for j in range(3):
                e_y = math.fsum(
                    (weight / total_g) * (row[i] * row[j] / weight)
                    for row, weight in zip(marginal_rows, g))
                e_z = math.fsum(
                    (weight / total_g) * (base * base / weight)
                    for base, weight in zip(m0, g))
                direct = math.fsum(
                    row[i] * row[j] for row in marginal_rows) / j0
                self.assertAlmostEqual(e_y / e_z, direct, places=15)

    def test_pinned_bases_have_no_m0_sign_invariant(self):
        # Both pairs lie in one fixed common stratum, and their line segment
        # remains in that stratum.  Continuity therefore forces an interior
        # cancellation zero; direct m_i/m0 normal-band assumptions cannot use
        # positivity of either pinned base as an escape hatch.
        d4_positive = [0.0] * 47
        d4_negative = [1 / 200] * 47
        self.assertGreater(self.adapter.j_m0(d4_positive), 0)
        self.assertLess(self.adapter.j_m0(d4_negative), 0)
        self.assertEqual(sum(x > self.adapter.delta for x in d4_positive), 0)
        self.assertEqual(sum(x > self.adapter.delta for x in d4_negative), 0)

        d12 = DENSITY.C10ImportanceDensity(D12, PARAMETERS)
        d12_positive = [101 / 10000] + [0.0] * 46
        d12_negative = [101 / 10000] + [1 / 250] * 46
        self.assertGreater(d12.j_m0(d12_positive), 0)
        self.assertLess(d12.j_m0(d12_negative), 0)
        self.assertEqual(sum(x > d12.delta for x in d12_positive), 1)
        self.assertEqual(sum(x > d12.delta for x in d12_negative), 1)


if __name__ == "__main__":
    unittest.main()
