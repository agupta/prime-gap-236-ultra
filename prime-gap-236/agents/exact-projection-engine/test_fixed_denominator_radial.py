#!/usr/bin/env python3
"""Exact independent regressions for direct integer radial transforms."""

from collections import defaultdict
from fractions import Fraction as Q
import importlib.util
import math
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ENGINE = load("fixed_test_engine", HERE / "symmetric_cutoff_cross.py")
FAST = load("fixed_test_fast", HERE / "fast_tagged_scalar.py")
PRUNED = load("fixed_test_pruned", HERE / "pruned_integer_radial.py")
COLLECTED = load("fixed_test_collected", HERE / "collected_integer_scalar.py")
TARGET = load("fixed_test_target", HERE / "fixed_denominator_radial.py")
RADIAL = load("fixed_test_radial", REPO / "verify/exact_capped_certificate.py")
FRONTIER = load(
    "fixed_test_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
PRUNED.FAST_V2 = FAST
COLLECTED.FAST_V2 = FAST
COLLECTED.PRUNED_V3 = PRUNED
TARGET.FAST_V2 = FAST
TARGET.COLLECTED_V5 = COLLECTED


class FixedDenominatorRadialTest(unittest.TestCase):
    def test_direct_integer_partition_coefficients_equal_fraction_reference(self):
        parts = ((), (2,), (4,), (2, 2), (6, 2), (4, 2, 2),
                 (6, 4, 2), (2, 2, 2, 2))
        for delta in (Q(1, 10), Q(2, 9), Q(7, 31)):
            for n in range(0, 8):
                valid = tuple(part for part in parts if len(part) <= n)
                maximum_degree = max(map(sum, valid), default=0)
                ceiling = max(0, maximum_degree + n - 1)
                denominator = (delta.denominator ** maximum_degree *
                               math.factorial(ceiling))
                for r in range(n + 1):
                    for maximum_shift in range(min(3, n - r) + 1):
                        for part in valid:
                            observed = TARGET.partition_face_scaled_integer(
                                RADIAL, part, n, r, delta, maximum_shift,
                                maximum_degree=maximum_degree,
                                factorial_ceiling=ceiling,
                                common_denominator=denominator)
                            expected = {
                                key: value * denominator for key, value in
                                PRUNED.partition_face_radial_pruned(
                                    RADIAL, part, n, r, delta,
                                    maximum_shift).items()}
                            self.assertEqual(observed, expected)
                            self.assertTrue(all(type(value) is int
                                                for value in observed.values()))

    def test_family_map_and_reduced_denominator_equal_reference_values(self):
        families = {
            "small": {
                (0, 0): {(): 3, (2,): -5, (4, 2): 7},
                (0, 2): {(2, 2): 11, (6,): -13},
            },
            "large": {
                (1, 0): {(2,): 17, (4, 2): -19},
                (3, 2): {(2, 2, 2): 23},
            },
        }
        for n in (3, 5, 7):
            for r in range(n + 1):
                kwargs = dict(number_variables=n, number_large=r,
                              delta=Q(2, 15), maximum_shift=min(2, n - r))
                expected, expected_denominator, _ = \
                    PRUNED.radialize_integer_families_pruned(
                        RADIAL, families, **kwargs)
                observed, observed_denominator, _ = \
                    TARGET.radialize_integer_families_fixed(
                        RADIAL, families, **kwargs)
                self.assertEqual(observed_denominator, expected_denominator)
                self.assertEqual(observed, expected)
                self.assertEqual(set(observed), set(expected))
                for family in expected:
                    shifts = set(expected[family]) | set(observed[family])
                    for shift in shifts:
                        left = defaultdict(Q)
                        right = defaultdict(Q)
                        for fp, sp, xp, yp, coefficient in \
                                expected[family].get(shift, ()):
                            left[(fp, sp, xp, yp)] += \
                                Q(coefficient, expected_denominator)
                        for fp, sp, xp, yp, coefficient in \
                                observed[family].get(shift, ()):
                            right[(fp, sp, xp, yp)] += \
                                Q(coefficient, observed_denominator)
                        self.assertEqual(dict(left), dict(right))

    def test_nonuniform_band_matches_pruned_v3_and_collected_v5(self):
        k = 4
        delta, alpha_f, eta = Q(1, 10), Q(7, 20), Q(29, 100)
        low_alpha, high_alpha = Q(7, 20), Q(21, 50)
        schedule = (Q(9, 50), Q(13, 50), Q(31, 100), Q(7, 20))
        basis = tuple(FRONTIER.ei.even_basis(6))
        inner = tuple(Q((i % 7) - 3, i + 5) for i in range(len(basis)))
        outer = tuple(Q((i % 5) - 2, i + 7) for i in range(len(basis)))
        marginal = ENGINE.marginal_polynomial(
            FRONTIER.ei, basis, inner, k, alpha_f)
        components = ENGINE.distinguished_components(
            FRONTIER.ei, basis, outer, k)
        kernel, _ = ENGINE.global_cross_kernel(
            FRONTIER.ei, marginal, components)
        families, _ = ENGINE.primitive_tagged_families(
            kernel, alpha_f=alpha_f, delta=delta)
        for r in range(k):
            kwargs = dict(
                k=k, alpha_high=high_alpha, alpha_low=low_alpha,
                alpha_f=alpha_f, eta=eta, delta=delta,
                schedule=schedule, common_r=r)
            reference, reference_diagnostics = \
                PRUNED.band_cross_r_integer(
                    ENGINE, RADIAL, families, **kwargs)
            collected, collected_diagnostics = \
                COLLECTED.band_cross_r_integer(
                    ENGINE, RADIAL, families, **kwargs)
            observed, diagnostics = TARGET.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            self.assertEqual(observed, reference)
            self.assertEqual(observed, collected)
            self.assertEqual(diagnostics["high"],
                             reference_diagnostics["high"])
            self.assertEqual(diagnostics["low"],
                             reference_diagnostics["low"])
            self.assertEqual(diagnostics["high"],
                             collected_diagnostics["high"])
            self.assertEqual(diagnostics["low"],
                             collected_diagnostics["low"])

        # At r=2 this alternate valid schedule has no large distinguished
        # branch at either endpoint.  The target must omit the whole unused
        # `large` family before radialization while retaining the exact value.
        inactive_kwargs = dict(
            k=k, alpha_high=Q(21, 50), alpha_low=alpha_f,
            alpha_f=alpha_f, eta=Q(29, 100), delta=delta,
            schedule=(Q(9, 50), Q(13, 50), Q(29, 100), Q(7, 20)),
            common_r=2)
        expected, expected_diagnostics = COLLECTED.band_cross_r_integer(
            ENGINE, RADIAL, families, **inactive_kwargs)
        observed, diagnostics = TARGET.band_cross_r_integer(
            ENGINE, RADIAL, families, **inactive_kwargs)
        self.assertEqual(observed, expected)
        self.assertEqual(diagnostics["high"],
                         expected_diagnostics["high"])
        self.assertEqual(diagnostics["low"], expected_diagnostics["low"])
        radial_stats = diagnostics["integer_radialization"]
        self.assertEqual(radial_stats["active_branch_families"],
                         ["small", "small_total"])
        self.assertEqual(
            radial_stats["inactive_families_pruned_before_radialization"],
            ["large"])


if __name__ == "__main__":
    unittest.main()
