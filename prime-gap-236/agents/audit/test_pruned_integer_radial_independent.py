#!/usr/bin/env python3
"""Independent hostile tests for maximum-shift-pruned radialization."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import importlib.util
from itertools import permutations, product
import math
from pathlib import Path
import random
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENGINE_DIR = REPO / "agents/exact-projection-engine"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ENGINE = load(
    "hostile_pruned_engine", ENGINE_DIR / "symmetric_cutoff_cross.py"
)
FAST = load("hostile_pruned_fast", ENGINE_DIR / "fast_tagged_scalar.py")
TARGET = load(
    "hostile_pruned_target", ENGINE_DIR / "pruned_integer_radial.py"
)
RADIAL = load(
    "hostile_pruned_radial", REPO / "verify/exact_capped_certificate.py"
)
FRONTIER = load(
    "hostile_pruned_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py",
)
TARGET.FAST_V2 = FAST


def literal_large(exponents, delta):
    """Cartesian expansion of translated large coordinates; no target code."""
    r = len(exponents)
    if not r:
        return {0: Q(1)}
    states = {0: Q(1)}
    for exponent in exponents:
        following = defaultdict(Q)
        for old_degree, old_value in states.items():
            for degree in range(exponent + 1):
                following[old_degree + degree] += (
                    old_value * math.comb(exponent, degree) *
                    delta ** (exponent - degree) * math.factorial(degree)
                )
        states = dict(following)
    return {
        degree + r - 1: value / math.factorial(degree + r - 1)
        for degree, value in states.items() if value
    }


def literal_small(exponents, delta, maximum_shift):
    """Literal per-coordinate inclusion-exclusion, filtered only at the end."""
    s = len(exponents)
    if not s:
        return ({(0, 0): Q(1)} if maximum_shift >= 0 else {})
    states = {(0, 0): Q(1)}
    for exponent in exponents:
        choices = [(0, exponent, Q(math.factorial(exponent)))]
        choices.extend(
            (1, degree,
             -Q(math.comb(exponent, degree)) *
             delta ** (exponent - degree) * math.factorial(degree))
            for degree in range(exponent + 1)
        )
        following = defaultdict(Q)
        for (old_shift, old_degree), old_value in states.items():
            for shift, degree, value in choices:
                following[(old_shift + shift, old_degree + degree)] += (
                    old_value * value
                )
        states = dict(following)
    answer = defaultdict(Q)
    for (shift, degree), value in states.items():
        if shift <= maximum_shift:
            radial_power = degree + s - 1
            answer[(shift, radial_power)] += (
                value / math.factorial(radial_power)
            )
    return {key: value for key, value in answer.items() if value}


def literal_partition_face(part, n, r, delta, maximum_shift):
    """Enumerate every orbit monomial on every choice of the r-large face."""
    if len(part) > n or maximum_shift < 0:
        return {}
    padded = tuple(part) + (0,) * (n - len(part))
    assignments = set(permutations(padded))
    answer = defaultdict(Q)
    face_multiplicity = math.comb(n, r)
    for assignment in assignments:
        large = literal_large(assignment[:r], delta)
        small = literal_small(assignment[r:], delta, maximum_shift)
        for x_power, left in large.items():
            for (shift, y_power), right in small.items():
                answer[(shift, x_power, y_power)] += (
                    face_multiplicity * left * right
                )
    return {key: value for key, value in answer.items() if value}


def reference_filtered(part, n, r, delta, maximum_shift):
    return {
        key: value
        for key, value in RADIAL._partition_face_radial(
            part, n, r, delta
        ).items()
        if key[0] <= maximum_shift
    }


def sample_families(parts, generator):
    answer = {}
    for family_index, family in enumerate(("small", "small_total", "large")):
        tagged = {}
        for tag_index, tag in enumerate(((0, 1), (1, 2), (3, 0))):
            polynomial = {}
            for part_index, part in enumerate(parts):
                if (part_index + tag_index + family_index) % 2:
                    continue
                value = generator.randint(-7, 7)
                if not value:
                    value = part_index + 1
                polynomial[part] = value
            tagged[tag] = polynomial
        answer[family] = tagged
    return answer


def make_cross_families(k, alpha_f, delta):
    labels = [(0, ()), (1, ()), (2, ()), (0, (2,)), (1, (2,))]
    if k >= 2:
        labels.extend(((0, (2, 2)), (0, (3, 1))))
    labels = tuple(labels)
    inner = tuple(Q((3 * i) % 11 - 5, i + 7) for i in range(len(labels)))
    outer = tuple(Q((5 * i) % 13 - 6, i + 9) for i in range(len(labels)))
    marginal = ENGINE.marginal_polynomial(
        FRONTIER.ei, labels, inner, k, alpha_f
    )
    components = ENGINE.distinguished_components(
        FRONTIER.ei, labels, outer, k
    )
    kernel, _ = ENGINE.global_cross_kernel(
        FRONTIER.ei, marginal, components
    )
    return ENGINE.primitive_tagged_families(
        kernel, alpha_f=alpha_f, delta=delta
    )[0]


class MaximumShiftPruningHostileAudit(unittest.TestCase):
    PARTS = (
        (), (1,), (2,), (3,), (4,), (2, 1), (3, 1), (2, 2),
        (4, 2), (3, 2, 1), (2, 2, 2), (5, 3, 1, 1),
    )

    def test_literal_orbit_coefficients_exhaustive_faces_and_cutoffs(self):
        # Expected maps enumerate ordinary monomials and IE choices; neither
        # the target's grouped selected-count formula nor the reference radial
        # transform is used to derive them.
        for delta in (Q(1, 10), Q(2, 7)):
            for n in range(6):
                for r in range(n + 1):
                    for maximum_shift in range(-1, n - r + 2):
                        for part in self.PARTS:
                            if len(part) > n:
                                continue
                            expected = literal_partition_face(
                                part, n, r, delta, maximum_shift
                            )
                            observed = TARGET.partition_face_radial_pruned(
                                RADIAL, part, n, r, delta, maximum_shift
                            )
                            old = reference_filtered(
                                part, n, r, delta, maximum_shift
                            )
                            self.assertEqual(observed, expected, (
                                delta, n, r, maximum_shift, part, "literal"
                            ))
                            self.assertEqual(observed, old, (
                                delta, n, r, maximum_shift, part, "reference"
                            ))

    def test_integer_family_maps_coefficient_by_coefficient(self):
        generator = random.Random(236_048_003)
        for n in range(1, 7):
            parts = tuple(part for part in self.PARTS if len(part) <= n)
            for r in range(n + 1):
                for maximum_shift in (-1, 0, max(0, n - r - 1), n - r,
                                      n - r + 1):
                    families = sample_families(parts, generator)
                    expected, expected_denominator, _ = \
                        FAST.radialize_integer_families(
                            RADIAL, families, number_variables=n,
                            number_large=r, delta=Q(3, 23),
                            maximum_shift=maximum_shift,
                        )
                    observed, observed_denominator, stats = \
                        TARGET.radialize_integer_families_pruned(
                            RADIAL, families, number_variables=n,
                            number_large=r, delta=Q(3, 23),
                            maximum_shift=maximum_shift,
                        )
                    self.assertEqual(observed_denominator, expected_denominator)
                    self.assertEqual(observed, expected, (
                        n, r, maximum_shift, "packed coefficient map"
                    ))
                    self.assertEqual(
                        stats["maximum_shift_pruned_inside_convolution"],
                        maximum_shift,
                    )

    def test_full_band_branches_zero_faces_and_integer_cutoff_equality(self):
        cases = (
            # k=1: no shared coordinates (r=s=0).
            (1, Q(1, 10), Q(1, 5), Q(1, 4), Q(3, 10), (Q(7, 25),)),
            # k=2 exercises r=0 and r=1 (zero large / zero small aggregate).
            (2, Q(1, 10), Q(1, 5), Q(7, 25), Q(17, 50),
             (Q(9, 50), Q(29, 100))),
            # eta/delta=3 exactly: the first discarded shift leaves a
            # zero-radius, positive-dimensional simplex.
            (4, Q(1, 10), Q(3, 10), Q(7, 20), Q(21, 50),
             (Q(9, 50), Q(13, 50), Q(31, 100), Q(7, 20))),
            # Nonintegral cutoff and nonuniform cap schedule.
            (5, Q(2, 25), Q(27, 100), Q(31, 100), Q(19, 50),
             (Q(3, 20), Q(11, 50), Q(7, 25), Q(8, 25), Q(9, 25))),
        )
        for k, delta, eta, low, high, schedule in cases:
            alpha_f = low
            families = make_cross_families(k, alpha_f, delta)
            for r in range(k):
                expected, expected_diagnostics = FAST.band_cross_r_integer(
                    ENGINE, RADIAL, families, k=k, alpha_high=high,
                    alpha_low=low, alpha_f=alpha_f, eta=eta, delta=delta,
                    schedule=schedule, common_r=r,
                )
                observed, diagnostics = TARGET.band_cross_r_integer(
                    ENGINE, RADIAL, families, k=k, alpha_high=high,
                    alpha_low=low, alpha_f=alpha_f, eta=eta, delta=delta,
                    schedule=schedule, common_r=r,
                )
                self.assertEqual(observed, expected, (k, r, "band"))
                self.assertEqual(
                    diagnostics["high"], expected_diagnostics["high"],
                    (k, r, "high branches"),
                )
                self.assertEqual(
                    diagnostics["low"], expected_diagnostics["low"],
                    (k, r, "low branches"),
                )
                if "integer_radialization" in expected_diagnostics:
                    self.assertEqual(
                        diagnostics["integer_radialization"][
                            "family_denominator"],
                        expected_diagnostics["integer_radialization"][
                            "family_denominator"],
                    )
                    self.assertEqual(
                        diagnostics["integer_radialization"][
                            "radial_denominator"],
                        expected_diagnostics["integer_radialization"][
                            "radial_denominator"],
                    )
                else:
                    self.assertNotIn("integer_radialization", diagnostics)

        # Make the cutoff equality observable before integration: the old
        # n=3 all-zero transform really has a nonzero h=3 coefficient, but its
        # shifted domain has total radius exactly zero and hence integral zero.
        delta = Q(1, 10)
        old = RADIAL._partition_face_radial((), 3, 0, delta)
        self.assertNotEqual(old.get((3, 0, 2), Q(0)), 0)
        maximum = RADIAL._maximum_active_shift(3 * delta, delta)
        self.assertEqual(maximum, 2)
        pruned = TARGET.partition_face_radial_pruned(
            RADIAL, (), 3, 0, delta, maximum
        )
        self.assertNotIn((3, 0, 2), pruned)
        packed = {3: ((0, 0, 0, 2, old[(3, 0, 2)]),)}
        value, _ = FAST.integrate_packed(
            RADIAL, packed, r=0, s=3, delta=delta,
            domain=RADIAL.AggregateDomain(total_bound=3 * delta),
            first_affine=(Q(0), Q(0), Q(0)),
            second_affine=(Q(0), Q(0), Q(0)),
        )
        self.assertEqual(value, 0)

    def test_target_definition5_domains_make_every_discarded_shift_empty(self):
        k = 48
        delta = Q(1, 60)
        eta = Q(8960917, 36000000)
        low, high = Q(103, 400), Q(9500917, 36000000)
        schedule = tuple(map(Q, (
            "1123/8000", "157041/1000000", "5267/31250",
            "87169/500000", "11593/62500", "1523/8000",
            "193097/1000000", "98573/500000", "202047/1000000",
            "20709/100000", "52917/250000", "52917/250000",
        )))
        for r in range(13):
            cutoff = eta - r * delta
            maximum = RADIAL._maximum_active_shift(cutoff, delta)
            self.assertGreaterEqual(maximum, 0)
            first_discarded = maximum + 1
            self.assertLessEqual(cutoff - first_discarded * delta, 0)
            for alpha in (low, high):
                jobs = ENGINE.scheduled_cross_branch_jobs(
                    RADIAL, k=k, alpha=alpha, eta=eta, delta=delta,
                    schedule=schedule, common_r=r,
                )
                self.assertTrue(jobs)
                for branch, family, domain, affine in jobs:
                    self.assertLessEqual(domain.total_bound, cutoff, (
                        r, alpha, branch, family, affine
                    ))
                    self.assertLessEqual(
                        domain.total_bound - first_discarded * delta, 0,
                        (r, alpha, branch, "first discarded shift"),
                    )

    def test_invalid_and_cache_boundary_cases(self):
        with self.assertRaises(ValueError):
            TARGET.partition_face_radial_pruned(
                RADIAL, (), 3, -1, Q(1, 10), 1
            )
        with self.assertRaises(ValueError):
            TARGET.partition_face_radial_pruned(
                RADIAL, (), 3, 4, Q(1, 10), 1
            )
        self.assertEqual(
            TARGET.partition_face_radial_pruned(
                RADIAL, (2, 2, 2, 2), 3, 0, Q(1, 10), 2
            ), {},
        )
        self.assertEqual(
            TARGET.partition_face_radial_pruned(
                RADIAL, (), 0, 0, Q(1, 10), -1
            ), {},
        )
        self.assertEqual(
            TARGET.partition_face_radial_pruned(
                RADIAL, (), 0, 0, Q(1, 10), 0
            ), {(0, 0, 0): Q(1)},
        )


if __name__ == "__main__":
    unittest.main()
