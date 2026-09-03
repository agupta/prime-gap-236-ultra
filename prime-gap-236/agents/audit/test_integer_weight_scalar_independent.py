#!/usr/bin/env python3
"""Independent hostile tests for frozen integer-weight scalar v4.

The packed-family oracle below expands both affine powers as ordinary named
polynomials and integrates the resulting polynomial directly over rational
polygons/intervals/points.  It never calls fast-v2's affine collector or
domain-moment batcher.  Full k=2 checks additionally use the literal original
coordinate oracle from the independent cross-engine audit.
"""

from __future__ import annotations

from collections import defaultdict
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


O = load("integer_weight_literal_cross_oracle",
         HERE / "test_symmetric_cutoff_cross_independent.py")
FAST = load("integer_weight_hostile_fast",
            REPO / "agents/exact-projection-engine/fast_tagged_scalar.py")
PRUNED = load("integer_weight_hostile_pruned",
              REPO / "agents/exact-projection-engine/pruned_integer_radial.py")
TARGET = load("integer_weight_hostile_target",
              REPO / "agents/exact-projection-engine/integer_weight_scalar.py")
PRUNED.FAST_V2 = FAST
TARGET.FAST_V2 = FAST
TARGET.PRUNED_V3 = PRUNED

ZERO, ONE = Q(0), Q(1)


def multiply(left, right):
    result = defaultdict(Q)
    for (i, j), a in left.items():
        for (p, q), b in right.items():
            result[(i + p, j + q)] += a * b
    return {key: value for key, value in result.items() if value}


def power_affine(power, affine):
    result = {(0, 0): ONE}
    linear = {(0, 0): affine[0], (1, 0): affine[1], (0, 1): affine[2]}
    linear = {key: value for key, value in linear.items() if value}
    for _ in range(power):
        result = multiply(result, linear)
    return result


def add_scaled(target, source, scale):
    for key, value in source.items():
        target[key] += scale * value
        if not target[key]:
            del target[key]


def integrate_interval_polynomial(poly, variable, lower, upper):
    if upper <= lower:
        return ZERO
    result = ZERO
    for (xp, yp), coefficient in poly.items():
        forbidden = yp if variable == "x" else xp
        exponent = xp if variable == "x" else yp
        if forbidden:
            # The absent aggregate is fixed at zero.  Radial powers in that
            # aggregate are rejected before expansion, while powers supplied
            # by an affine factor simply evaluate to zero.
            continue
        result += coefficient * (upper ** (exponent + 1)
                                 - lower ** (exponent + 1)) / (exponent + 1)
    return result


def integrate_shift_poly(poly, *, r, s, domain, shift):
    total = domain.total_bound - shift
    y_lower = None if domain.y_lower is None else domain.y_lower - shift
    y_upper = None if domain.y_upper is None else domain.y_upper - shift
    total_lower = (None if domain.total_lower is None else
                   domain.total_lower - shift)
    if total < 0 or (total == 0 and r + s > 0):
        return ZERO
    if r == 0 and s == 0:
        valid = not (
            (domain.x_bound is not None and domain.x_bound < 0)
            or (y_lower is not None and y_lower >= 0)
            or (y_upper is not None and y_upper < 0)
            or (total_lower is not None and total_lower >= 0))
        return poly.get((0, 0), ZERO) if valid else ZERO
    if r == 0:
        if domain.x_bound is not None and domain.x_bound < 0:
            return ZERO
        lower = max(ZERO, y_lower if y_lower is not None else ZERO,
                    total_lower if total_lower is not None else ZERO)
        upper = min(total, y_upper if y_upper is not None else total)
        return integrate_interval_polynomial(poly, "y", lower, upper)
    if s == 0:
        upper = min(total, domain.x_bound) \
            if domain.x_bound is not None else total
        if (upper <= 0 or (y_lower is not None and y_lower >= 0)
                or (y_upper is not None and y_upper < 0)):
            return ZERO
        lower = max(ZERO, total_lower if total_lower is not None else ZERO)
        return integrate_interval_polynomial(poly, "x", lower, upper)
    constraints = [(-ONE, ZERO, ZERO), (ZERO, -ONE, ZERO),
                   (ONE, ONE, total)]
    if domain.x_bound is not None:
        constraints.append((ONE, ZERO, domain.x_bound))
    if y_lower is not None:
        constraints.append((ZERO, -ONE, -y_lower))
    if y_upper is not None:
        constraints.append((ZERO, ONE, y_upper))
    if total_lower is not None:
        constraints.append((-ONE, -ONE, -total_lower))
    return O.integrate_polygon(poly, constraints)


def direct_packed(packed, *, r, s, delta, domain, first, second):
    result = ZERO
    for number_shifted, rows in sorted(packed.items()):
        shift = number_shifted * delta
        total = domain.total_bound - shift
        if total < 0 or (total == 0 and r + s > 0):
            continue
        polynomial = defaultdict(Q)
        for fp, sp, xp, yp, coefficient in rows:
            if type(coefficient) is not int:
                raise TypeError("literal oracle requires integer coefficient")
            if (r == 0 and xp) or (s == 0 and yp):
                raise ArithmeticError("literal oracle forbidden aggregate power")
            left = power_affine(
                fp, (first[0] + first[2] * shift, first[1], first[2]))
            right = power_affine(
                sp, (second[0] + second[2] * shift, second[1], second[2]))
            term = multiply({(xp, yp): Q(coefficient)}, multiply(left, right))
            add_scaled(polynomial, term, ONE)
        result += integrate_shift_poly(dict(polynomial), r=r, s=s,
                                       domain=domain, shift=shift)
    return result


def build_families(inner_terms, outer_terms, alpha_f, delta, k=2):
    marginal = O.M.marginal_polynomial(
        O.F.ei, tuple(inner_terms), tuple(inner_terms.values()), k, alpha_f)
    components = O.M.distinguished_components(
        O.F.ei, tuple(outer_terms), tuple(outer_terms.values()), k)
    kernel, _ = O.M.global_cross_kernel(O.F.ei, marginal, components)
    families, _ = O.M.primitive_tagged_families(
        kernel, alpha_f=alpha_f, delta=delta)
    return families


class IntegerWeightScalarHostileAudit(unittest.TestCase):
    maxDiff = None

    def assert_packed(self, packed, r, s, delta, domain, first, second):
        expected = direct_packed(
            packed, r=r, s=s, delta=delta, domain=domain,
            first=first, second=second)
        observed, stats = TARGET.integrate_packed_integer_weights(
            O.R, packed, r=r, s=s, delta=delta, domain=domain,
            first_affine=first, second_affine=second)
        self.assertEqual(observed, expected)
        self.assertGreaterEqual(stats["maximum_affine_denominator_bits"], 1)
        self.assertGreaterEqual(stats["maximum_moment_denominator_bits"], 1)

    def test_dense_manual_all_domain_shapes_against_literal_oracle(self):
        packed = {
            0: ((0, 0, 0, 0, 7), (2, 1, 1, 0, -11),
                (1, 3, 0, 2, 13), (3, 2, 2, 1, -5)),
            1: ((2, 2, 0, 0, 17), (1, 0, 2, 1, -19),
                (0, 3, 1, 2, 23)),
            2: ((4, 3, 1, 1, -31),),
            7: ((1, 1, 0, 0, 29),),
        }
        delta = Q(1, 11)
        affine_pairs = (
            ((Q(2, 7), Q(-3, 5), Q(4, 9)),
             (Q(5, 13), Q(2, 3), Q(-7, 8))),
            ((Q(-1, 6), Q(5, 12), Q(5, 12)),
             (Q(7, 10), Q(5, 12), Q(5, 12))),
        )
        domains = (
            O.R.AggregateDomain(Q(5, 11)),
            O.R.AggregateDomain(Q(5, 11), x_bound=Q(3, 11)),
            O.R.AggregateDomain(Q(5, 11), y_lower=Q(1, 11)),
            O.R.AggregateDomain(Q(5, 11), y_upper=Q(2, 11)),
            O.R.AggregateDomain(Q(5, 11), total_lower=Q(2, 11)),
            O.R.AggregateDomain(Q(5, 11), x_bound=Q(3, 11),
                                y_lower=Q(1, 11), y_upper=Q(4, 11),
                                total_lower=Q(2, 11)),
        )
        for first, second in affine_pairs:
            for domain in domains:
                self.assert_packed(packed, 2, 3, delta, domain, first, second)
            allowed_r0 = {shift: tuple(row for row in rows if row[2] == 0)
                          for shift, rows in packed.items()}
            allowed_s0 = {shift: tuple(row for row in rows if row[3] == 0)
                          for shift, rows in packed.items()}
            self.assert_packed(allowed_r0, 0, 3, delta,
                               O.R.AggregateDomain(Q(5, 11), y_lower=Q(1, 11),
                                                   y_upper=Q(4, 11)),
                               first, second)
            self.assert_packed(allowed_s0, 2, 0, delta,
                               O.R.AggregateDomain(Q(5, 11), x_bound=Q(3, 11),
                                                   total_lower=Q(1, 11)),
                               first, second)

    def test_seeded_random_packed_exact_cancellation_and_isolation(self):
        generator = random.Random(236_048_004)
        for case in range(80):
            r, s = generator.choice(((1, 1), (2, 3), (0, 3), (3, 0)))
            delta = Q(generator.randint(1, 4), 30)
            rows = {}
            for shift in range(generator.randint(1, 5)):
                terms = []
                for _ in range(generator.randint(1, 7)):
                    terms.append((
                        generator.randint(0, 4), generator.randint(0, 4),
                        0 if r == 0 else generator.randint(0, 3),
                        0 if s == 0 else generator.randint(0, 3),
                        generator.choice((-1, 1)) * generator.randint(1, 31)))
                rows[shift] = tuple(terms)
            first = tuple(Q(generator.randint(-7, 7), generator.randint(2, 13))
                          for _ in range(3))
            second = tuple(Q(generator.randint(-7, 7), generator.randint(2, 13))
                           for _ in range(3))
            total = Q(generator.randint(8, 19), 30)
            domain = O.R.AggregateDomain(
                total,
                x_bound=None if generator.randrange(2) else
                    Q(generator.randint(3, 16), 30),
                y_lower=None if generator.randrange(2) else
                    Q(generator.randint(-2, 12), 30),
                y_upper=None if generator.randrange(2) else
                    Q(generator.randint(3, 18), 30),
                total_lower=None if generator.randrange(2) else
                    Q(generator.randint(-2, 12), 30))
            self.assert_packed(rows, r, s, delta, domain, first, second)

        # Equal and opposite rows must cancel after both LCM clearings.
        cancelling = {0: ((3, 4, 2, 1, 97), (3, 4, 2, 1, -97))}
        first = (Q(2, 7), Q(-3, 11), Q(5, 13))
        second = (Q(-7, 17), Q(11, 19), Q(-13, 23))
        value, _ = TARGET.integrate_packed_integer_weights(
            O.R, cancelling, r=2, s=2, delta=Q(1, 10),
            domain=O.R.AggregateDomain(Q(2, 5)),
            first_affine=first, second_affine=second)
        self.assertEqual(value, ZERO)

    def test_zero_dimensions_empty_boundaries_and_zero_affines(self):
        packed = {0: ((0, 0, 0, 0, 9),),
                  1: ((0, 0, 0, 0, -4),),
                  2: ((2, 3, 0, 0, 11),)}
        first = (Q(2, 3), Q(7, 5), Q(-3, 8))
        second = (Q(5, 7), Q(-2, 9), Q(11, 13))
        for domain in (
                O.R.AggregateDomain(Q(0)),
                O.R.AggregateDomain(Q(0), x_bound=Q(-1, 17)),
                O.R.AggregateDomain(Q(1, 10), y_lower=Q(0)),
                O.R.AggregateDomain(Q(1, 10), y_upper=Q(-1, 19)),
                O.R.AggregateDomain(Q(1, 10), total_lower=Q(0))):
            self.assert_packed(packed, 0, 0, Q(1, 10), domain, first, second)
        zero_affine = {0: ((2, 1, 0, 0, 37),)}
        self.assert_packed(
            zero_affine, 1, 1, Q(1, 10), O.R.AggregateDomain(Q(2, 5)),
            (ZERO, ZERO, ZERO), second)
        with self.assertRaises(TypeError):
            TARGET.integrate_packed_integer_weights(
                O.R, {0: ((0, 0, 0, 0, Q(1, 2)),)}, r=1, s=1,
                delta=Q(1, 10), domain=O.R.AggregateDomain(Q(2, 5)),
                first_affine=first, second_affine=second)
        with self.assertRaises(ArithmeticError):
            TARGET.integrate_packed_integer_weights(
                O.R, {0: ((0, 0, 1, 0, 1),)}, r=0, s=1,
                delta=Q(1, 10), domain=O.R.AggregateDomain(Q(2, 5)),
                first_affine=first, second_affine=second)

    def test_full_k2_branches_against_original_coordinate_polygons(self):
        geometry = dict(O.IndependentLiteralCrossAudit.GEOMETRY)
        labels = O.IndependentLiteralCrossAudit.BASIS
        cases = [({label: ONE}, {other: ONE})
                 for label, other in zip(labels, reversed(labels))]
        generator = random.Random(236_048_004_2)
        for _ in range(10):
            inner = {label: Q(generator.randint(-3, 3), generator.randint(1, 9))
                     for label in labels}
            outer = {label: Q(generator.randint(-3, 3), generator.randint(1, 9))
                     for label in labels}
            cases.append(({key: value for key, value in inner.items() if value},
                          {key: value for key, value in outer.items() if value}))
        seen = set()
        for inner, outer in cases:
            families = build_families(inner, outer, geometry["alpha_f"],
                                      geometry["delta"])
            polynomial = O.marginal_times_outer(
                inner, outer, geometry["alpha_f"])
            high = O.direct_cross_endpoint(
                polynomial, alpha=geometry["alpha_high"], eta=geometry["eta"],
                delta=geometry["delta"], schedule=geometry["schedule"])
            low = O.direct_cross_endpoint(
                polynomial, alpha=geometry["alpha_low"], eta=geometry["eta"],
                delta=geometry["delta"], schedule=geometry["schedule"])
            expected_total = ZERO
            observed_total = ZERO
            for r in (0, 1):
                observed, diagnostics = TARGET.band_cross_r_integer(
                    O.M, O.R, families, k=2,
                    alpha_high=geometry["alpha_high"],
                    alpha_low=geometry["alpha_low"],
                    alpha_f=geometry["alpha_f"], eta=geometry["eta"],
                    delta=geometry["delta"], schedule=geometry["schedule"],
                    common_r=r)
                observed_total += observed
                for branch in O.M.BRANCHES:
                    self.assertEqual(diagnostics["high"].get(branch, ZERO),
                                     high[r][branch], (r, branch, "high"))
                    self.assertEqual(diagnostics["low"].get(branch, ZERO),
                                     low[r][branch], (r, branch, "low"))
                    expected_total += 2 * (high[r][branch] - low[r][branch])
                    if high[r][branch] or low[r][branch]:
                        seen.add(branch)
            self.assertEqual(observed_total, expected_total)
        self.assertEqual(seen, set(O.M.BRANCHES))

    def test_exact_v4_v3_and_fraction_reference_equality_varied_k(self):
        generator = random.Random(4_003_236)
        delta, alpha_f = Q(1, 12), Q(7, 20)
        low, high, eta = Q(7, 20), Q(21, 50), Q(1, 3)
        schedule_full = (Q(1, 6), Q(6, 25), Q(3, 10),
                         Q(7, 20), Q(2, 5))
        basis = tuple(O.F.ei.even_basis(4))
        for k in range(1, 6):
            inner = tuple(Q(generator.randint(-4, 4), generator.randint(2, 11))
                          for _ in basis)
            outer = tuple(Q(generator.randint(-4, 4), generator.randint(2, 11))
                          for _ in basis)
            marginal = O.M.marginal_polynomial(
                O.F.ei, basis, inner, k, alpha_f)
            components = O.M.distinguished_components(
                O.F.ei, basis, outer, k)
            kernel, _ = O.M.global_cross_kernel(O.F.ei, marginal, components)
            families, _ = O.M.primitive_tagged_families(
                kernel, alpha_f=alpha_f, delta=delta)
            schedule = schedule_full[:k]
            for r in range(k):
                fraction_value, fraction_row = FAST.band_cross_r(
                    O.M, O.R, families, k=k, alpha_high=high,
                    alpha_low=low, alpha_f=alpha_f, eta=eta, delta=delta,
                    schedule=schedule, common_r=r)
                v3_value, v3_row = PRUNED.band_cross_r_integer(
                    O.M, O.R, families, k=k, alpha_high=high,
                    alpha_low=low, alpha_f=alpha_f, eta=eta, delta=delta,
                    schedule=schedule, common_r=r)
                observed, row = TARGET.band_cross_r_integer(
                    O.M, O.R, families, k=k, alpha_high=high,
                    alpha_low=low, alpha_f=alpha_f, eta=eta, delta=delta,
                    schedule=schedule, common_r=r)
                self.assertEqual(observed, fraction_value, (k, r, "fraction"))
                self.assertEqual(observed, v3_value, (k, r, "v3"))
                self.assertEqual(row["high"], fraction_row["high"])
                self.assertEqual(row["low"], fraction_row["low"])
                self.assertEqual(row["high"], v3_row["high"])
                self.assertEqual(row["low"], v3_row["low"])


if __name__ == "__main__":
    unittest.main()
