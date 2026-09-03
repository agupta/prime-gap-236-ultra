#!/usr/bin/env python3
"""Exact regressions for cached-cost direct integer radialization."""

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


ENGINE = load("cached_test_engine", HERE / "symmetric_cutoff_cross.py")
FAST = load("cached_test_fast", HERE / "fast_tagged_scalar.py")
PRUNED = load("cached_test_pruned", HERE / "pruned_integer_radial.py")
COLLECTED = load("cached_test_collected", HERE / "collected_integer_scalar.py")
FIXED = load("cached_test_fixed", HERE / "fixed_denominator_radial.py")
TARGET = load("cached_test_target", HERE / "cached_fixed_denominator_radial.py")
RADIAL = load("cached_test_radial", REPO / "verify/exact_capped_certificate.py")
FRONTIER = load(
    "cached_test_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
PRUNED.FAST_V2 = FAST
COLLECTED.FAST_V2 = FAST
COLLECTED.PRUNED_V3 = PRUNED
FIXED.FAST_V2 = FAST
FIXED.COLLECTED_V5 = COLLECTED
TARGET.FIXED_V6 = FIXED
TARGET.FAST_V2 = FAST
TARGET.COLLECTED_V5 = COLLECTED


class CachedFixedDenominatorRadialTest(unittest.TestCase):
    def test_partition_and_family_maps_are_literally_fixed_v6_maps(self):
        parts = ((), (2,), (4, 2), (2, 2, 2), (6, 4, 2),
                 (4, 2, 2, 2))
        for delta in (Q(1, 10), Q(2, 9)):
            for n in range(0, 8):
                valid = tuple(part for part in parts if len(part) <= n)
                maximum_degree = max(map(sum, valid), default=0)
                ceiling = max(0, maximum_degree + n - 1)
                denominator = (delta.denominator ** maximum_degree *
                               math.factorial(ceiling))
                for r in range(n + 1):
                    maximum_shift = min(2, n - r)
                    for part in valid:
                        kwargs = dict(
                            maximum_degree=maximum_degree,
                            factorial_ceiling=ceiling,
                            common_denominator=denominator)
                        expected = FIXED.partition_face_scaled_integer(
                            RADIAL, part, n, r, delta, maximum_shift,
                            **kwargs)
                        observed = TARGET.partition_face_scaled_integer(
                            RADIAL, part, n, r, delta, maximum_shift,
                            **kwargs)
                        self.assertEqual(observed, expected)

        families = {
            "small": {(0, 0): {(): 3, (2,): -5, (4, 2): 7}},
            "large": {(1, 0): {(2,): 11, (2, 2): -13},
                      (3, 2): {(6, 2): 17}},
        }
        for n in (3, 6):
            for r in range(n + 1):
                kwargs = dict(number_variables=n, number_large=r,
                              delta=Q(2, 15), maximum_shift=min(2, n - r))
                expected = FIXED.radialize_integer_families_fixed(
                    RADIAL, families, **kwargs)
                observed = TARGET.radialize_integer_families_fixed(
                    RADIAL, families, **kwargs)
                self.assertEqual(observed[:2], expected[:2])

    def test_nonuniform_all_branch_band_and_inactive_family_equal_v6(self):
        k = 4
        delta, alpha_f, eta = Q(1, 10), Q(7, 20), Q(29, 100)
        low_alpha, high_alpha = alpha_f, Q(21, 50)
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
        cases = [
            (r, schedule, eta) for r in range(k)]
        cases.append((
            2, (Q(9, 50), Q(13, 50), Q(29, 100), Q(7, 20)),
            Q(29, 100)))
        for r, case_schedule, case_eta in cases:
            kwargs = dict(
                k=k, alpha_high=high_alpha, alpha_low=low_alpha,
                alpha_f=alpha_f, eta=case_eta, delta=delta,
                schedule=case_schedule, common_r=r)
            expected, expected_diagnostics = FIXED.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            observed, diagnostics = TARGET.band_cross_r_integer(
                ENGINE, RADIAL, families, **kwargs)
            self.assertEqual(observed, expected)
            self.assertEqual(diagnostics["high"],
                             expected_diagnostics["high"])
            self.assertEqual(diagnostics["low"],
                             expected_diagnostics["low"])


if __name__ == "__main__":
    unittest.main()
