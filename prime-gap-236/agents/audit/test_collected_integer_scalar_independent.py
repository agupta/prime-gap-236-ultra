#!/usr/bin/env python3
"""Independent hostile tests for global integer collection v5."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# This module supplies the separately implemented direct named-polynomial
# polygon/interval/point oracle; its TARGET is v4 and is not used as the sole
# expected-value route in the first four tests.
V4O = load("collected_v5_hostile_literal_oracle",
           HERE / "test_integer_weight_scalar_independent.py")
TARGET = load("collected_v5_hostile_target",
              REPO / "agents/exact-projection-engine/collected_integer_scalar.py")
TARGET.FAST_V2 = V4O.FAST
TARGET.PRUNED_V3 = V4O.PRUNED

ZERO, ONE = Q(0), Q(1)


class CollectedIntegerScalarHostileAudit(unittest.TestCase):
    maxDiff = None

    def assert_literal(self, packed, r, s, delta, domain, first, second):
        expected = V4O.direct_packed(
            packed, r=r, s=s, delta=delta, domain=domain,
            first=first, second=second)
        observed, stats = TARGET.integrate_packed_collected_integers(
            V4O.O.R, packed, r=r, s=s, delta=delta, domain=domain,
            first_affine=first, second_affine=second)
        self.assertEqual(observed, expected)
        self.assertEqual(stats["requested_moments"],
                         stats["nonzero_product_monomials"])
        self.assertGreaterEqual(stats["scalar_products"],
                                stats["nonzero_product_monomials"])
        return stats

    def test_cross_tag_collisions_and_complete_signed_cancellation(self):
        # The first two rows contribute +XY and -XY through different tags;
        # the next two contribute +X^2Y/2 and -X^2Y/2 and also cancel after
        # the global affine LCM is cleared.
        packed = {0: (
            (1, 0, 0, 1, 2), (0, 1, 1, 0, -3),
            (2, 0, 0, 1, 2), (0, 2, 2, 0, -49),
            (0, 0, 0, 0, 5),
        )}
        first = (ZERO, Q(1, 2), ZERO)
        second = (ZERO, ZERO, Q(1, 3))
        # Replace the deliberately unrelated fourth draft row by the exact
        # negative, supplied via a different radial/tag split.
        packed[0] = packed[0][:3] + (
            (1, 0, 1, 1, -1),
            packed[0][-1],
        )
        stats = self.assert_literal(
            packed, 1, 1, Q(1, 10),
            V4O.O.R.AggregateDomain(Q(2, 5)), first, second)
        self.assertGreaterEqual(stats["cancelled_product_monomials"], 2)
        observed, _ = TARGET.integrate_packed_collected_integers(
            V4O.O.R, packed, r=1, s=1, delta=Q(1, 10),
            domain=V4O.O.R.AggregateDomain(Q(2, 5)),
            first_affine=first, second_affine=second)
        self.assertEqual(observed, Q(2, 5))

    def test_seeded_random_packed_all_domain_and_dimension_shapes(self):
        generator = random.Random(5_236_048)
        dimension_pairs = ((2, 3), (1, 1), (0, 3), (3, 0), (0, 0))
        for case in range(100):
            r, s = dimension_pairs[case % len(dimension_pairs)]
            delta = Q(generator.randint(1, 4), 30)
            packed = {}
            for shift in range(generator.randint(1, 6)):
                packed[shift] = tuple(
                    (generator.randint(0, 5), generator.randint(0, 5),
                     0 if r == 0 else generator.randint(0, 3),
                     0 if s == 0 else generator.randint(0, 3),
                     generator.choice((-1, 1)) * generator.randint(1, 37))
                    for _ in range(generator.randint(1, 9)))
            first = tuple(Q(generator.randint(-8, 8), generator.randint(2, 17))
                          for _ in range(3))
            second = tuple(Q(generator.randint(-8, 8), generator.randint(2, 17))
                           for _ in range(3))
            domain = V4O.O.R.AggregateDomain(
                Q(generator.randint(7, 20), 30),
                x_bound=None if generator.randrange(2) else
                    Q(generator.randint(-2, 18), 30),
                y_lower=None if generator.randrange(2) else
                    Q(generator.randint(-2, 13), 30),
                y_upper=None if generator.randrange(2) else
                    Q(generator.randint(-2, 19), 30),
                total_lower=None if generator.randrange(2) else
                    Q(generator.randint(-2, 13), 30))
            self.assert_literal(packed, r, s, delta, domain, first, second)

    def test_zero_affine_empty_domains_and_type_dimension_guards(self):
        second = (Q(5, 7), Q(-2, 9), Q(11, 13))
        zero_affine = {0: ((3, 2, 0, 0, 37),)}
        stats = self.assert_literal(
            zero_affine, 1, 1, Q(1, 10),
            V4O.O.R.AggregateDomain(Q(2, 5)),
            (ZERO, ZERO, ZERO), second)
        self.assertEqual(stats["requested_moments"], 0)
        packed = {0: ((0, 0, 0, 0, 9),), 1: ((1, 2, 0, 0, -7),)}
        first = (Q(2, 3), Q(7, 5), Q(-3, 8))
        for domain in (
                V4O.O.R.AggregateDomain(Q(0)),
                V4O.O.R.AggregateDomain(Q(0), x_bound=Q(-1, 17)),
                V4O.O.R.AggregateDomain(Q(1, 10), y_lower=Q(0)),
                V4O.O.R.AggregateDomain(Q(1, 10), y_upper=Q(-1, 19)),
                V4O.O.R.AggregateDomain(Q(1, 10), total_lower=Q(0))):
            self.assert_literal(packed, 0, 0, Q(1, 10), domain, first, second)
        with self.assertRaises(TypeError):
            TARGET.integrate_packed_collected_integers(
                V4O.O.R, {0: ((0, 0, 0, 0, Q(1, 2)),)}, r=1, s=1,
                delta=Q(1, 10), domain=V4O.O.R.AggregateDomain(Q(2, 5)),
                first_affine=first, second_affine=second)
        with self.assertRaises(ArithmeticError):
            TARGET.integrate_packed_collected_integers(
                V4O.O.R, {0: ((0, 0, 1, 0, 1),)}, r=0, s=1,
                delta=Q(1, 10), domain=V4O.O.R.AggregateDomain(Q(2, 5)),
                first_affine=first, second_affine=second)

    def test_full_k2_all_branches_against_original_coordinate_oracle(self):
        geometry = dict(V4O.O.IndependentLiteralCrossAudit.GEOMETRY)
        labels = V4O.O.IndependentLiteralCrossAudit.BASIS
        generator = random.Random(5_002_236)
        cases = [({label: ONE}, {other: ONE})
                 for label, other in zip(labels, reversed(labels))]
        for _ in range(10):
            inner = {label: Q(generator.randint(-3, 3), generator.randint(1, 9))
                     for label in labels}
            outer = {label: Q(generator.randint(-3, 3), generator.randint(1, 9))
                     for label in labels}
            cases.append(({key: value for key, value in inner.items() if value},
                          {key: value for key, value in outer.items() if value}))
        seen = set()
        for inner, outer in cases:
            families = V4O.build_families(
                inner, outer, geometry["alpha_f"], geometry["delta"])
            polynomial = V4O.O.marginal_times_outer(
                inner, outer, geometry["alpha_f"])
            high = V4O.O.direct_cross_endpoint(
                polynomial, alpha=geometry["alpha_high"], eta=geometry["eta"],
                delta=geometry["delta"], schedule=geometry["schedule"])
            low = V4O.O.direct_cross_endpoint(
                polynomial, alpha=geometry["alpha_low"], eta=geometry["eta"],
                delta=geometry["delta"], schedule=geometry["schedule"])
            expected_total = observed_total = ZERO
            for r in (0, 1):
                observed, diagnostics = TARGET.band_cross_r_integer(
                    V4O.O.M, V4O.O.R, families, k=2,
                    alpha_high=geometry["alpha_high"],
                    alpha_low=geometry["alpha_low"],
                    alpha_f=geometry["alpha_f"], eta=geometry["eta"],
                    delta=geometry["delta"], schedule=geometry["schedule"],
                    common_r=r)
                observed_total += observed
                for branch in V4O.O.M.BRANCHES:
                    self.assertEqual(diagnostics["high"].get(branch, ZERO),
                                     high[r][branch])
                    self.assertEqual(diagnostics["low"].get(branch, ZERO),
                                     low[r][branch])
                    expected_total += 2 * (high[r][branch] - low[r][branch])
                    if high[r][branch] or low[r][branch]:
                        seen.add(branch)
            self.assertEqual(observed_total, expected_total)
        self.assertEqual(seen, set(V4O.O.M.BRANCHES))

    def test_v5_v4_v3_fraction_exact_equality_and_collection_inventory(self):
        generator = random.Random(5_004_236)
        delta, alpha_f = Q(1, 12), Q(7, 20)
        low, high, eta = Q(7, 20), Q(21, 50), Q(1, 3)
        schedule_full = (Q(1, 6), Q(6, 25), Q(3, 10),
                         Q(7, 20), Q(2, 5))
        basis = tuple(V4O.O.F.ei.even_basis(4))
        for k in range(1, 6):
            inner = tuple(Q(generator.randint(-4, 4), generator.randint(2, 11))
                          for _ in basis)
            outer = tuple(Q(generator.randint(-4, 4), generator.randint(2, 11))
                          for _ in basis)
            marginal = V4O.O.M.marginal_polynomial(
                V4O.O.F.ei, basis, inner, k, alpha_f)
            components = V4O.O.M.distinguished_components(
                V4O.O.F.ei, basis, outer, k)
            kernel, _ = V4O.O.M.global_cross_kernel(
                V4O.O.F.ei, marginal, components)
            families, _ = V4O.O.M.primitive_tagged_families(
                kernel, alpha_f=alpha_f, delta=delta)
            schedule = schedule_full[:k]
            for r in range(k):
                kwargs = dict(
                    k=k, alpha_high=high, alpha_low=low, alpha_f=alpha_f,
                    eta=eta, delta=delta, schedule=schedule, common_r=r)
                fraction_value, fraction_row = V4O.FAST.band_cross_r(
                    V4O.O.M, V4O.O.R, families, **kwargs)
                v3_value, v3_row = V4O.PRUNED.band_cross_r_integer(
                    V4O.O.M, V4O.O.R, families, **kwargs)
                v4_value, v4_row = V4O.TARGET.band_cross_r_integer(
                    V4O.O.M, V4O.O.R, families, **kwargs)
                observed, row = TARGET.band_cross_r_integer(
                    V4O.O.M, V4O.O.R, families, **kwargs)
                self.assertEqual(observed, fraction_value)
                self.assertEqual(observed, v3_value)
                self.assertEqual(observed, v4_value)
                for diagnostics in (fraction_row, v3_row, v4_row):
                    self.assertEqual(row["high"], diagnostics["high"])
                    self.assertEqual(row["low"], diagnostics["low"])
                for side in ("high_stats", "low_stats"):
                    for stats in row.get(side, {}).values():
                        self.assertEqual(stats["requested_moments"],
                                         stats["nonzero_product_monomials"])
                        self.assertGreaterEqual(stats["scalar_products"],
                                                stats["requested_moments"])

        # A larger synthetic inventory attacks collisions across hundreds of
        # terms and verifies that moment work is tied to final monomials.
        packed_rows = []
        for index in range(720):
            packed_rows.append((index % 9, (index * 5) % 8,
                                (index * 7) % 13, (index * 11) % 13,
                                (-1 if index % 3 == 0 else 1) * (index % 31 + 1)))
        packed = {0: tuple(packed_rows)}
        kwargs = dict(
            r=2, s=2, delta=Q(1, 60),
            domain=V4O.O.R.AggregateDomain(Q(1, 4), x_bound=Q(3, 20)),
            first_affine=(Q(2, 7), Q(-3, 11), Q(5, 13)),
            second_affine=(Q(-7, 17), Q(11, 19), Q(-13, 23)))
        expected, _ = V4O.TARGET.integrate_packed_integer_weights(
            V4O.O.R, packed, **kwargs)
        observed, stats = TARGET.integrate_packed_collected_integers(
            V4O.O.R, packed, **kwargs)
        self.assertEqual(observed, expected)
        self.assertEqual(stats["requested_moments"],
                         stats["nonzero_product_monomials"])
        self.assertLess(stats["requested_moments"], stats["scalar_products"])


if __name__ == "__main__":
    unittest.main()
