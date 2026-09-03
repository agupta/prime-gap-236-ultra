#!/usr/bin/env python3
"""Exact regressions for joint large/small assignment radial DP."""

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


ENGINE = load("joint_test_engine", HERE / "symmetric_cutoff_cross.py")
FAST = load("joint_test_fast", HERE / "fast_tagged_scalar.py")
PRUNED = load("joint_test_pruned", HERE / "pruned_integer_radial.py")
COLLECTED = load("joint_test_collected", HERE / "collected_integer_scalar.py")
FIXED = load("joint_test_fixed", HERE / "fixed_denominator_radial.py")
CACHED = load("joint_test_cached", HERE / "cached_fixed_denominator_radial.py")
TARGET = load("joint_test_target", HERE / "joint_assignment_radial.py")
RADIAL = load("joint_test_radial", REPO / "verify/exact_capped_certificate.py")
FRONTIER = load(
    "joint_test_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
PRUNED.FAST_V2 = FAST
COLLECTED.FAST_V2 = FAST
COLLECTED.PRUNED_V3 = PRUNED
FIXED.FAST_V2 = FAST
FIXED.COLLECTED_V5 = COLLECTED
CACHED.FIXED_V6 = FIXED
CACHED.FAST_V2 = FAST
CACHED.COLLECTED_V5 = COLLECTED
TARGET.CACHED_V7 = CACHED
TARGET.FAST_V2 = FAST
TARGET.COLLECTED_V5 = COLLECTED


class JointAssignmentRadialTest(unittest.TestCase):
    def test_joint_partition_dp_is_literally_fixed_v6_transform(self):
        parts = ((), (2,), (4,), (2, 2), (6, 2), (4, 2, 2),
                 (6, 4, 2), (2, 2, 2, 2), (4, 4, 2, 2))
        for delta in (Q(1, 10), Q(2, 9), Q(7, 31)):
            for n in range(0, 9):
                valid = tuple(part for part in parts if len(part) <= n)
                maximum_degree = max(map(sum, valid), default=0)
                ceiling = max(0, maximum_degree + n - 1)
                denominator = (delta.denominator ** maximum_degree *
                               math.factorial(ceiling))
                for r in range(n + 1):
                    for maximum_shift in range(min(3, n - r) + 1):
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

    def test_packed_maps_denominator_and_full_branches_equal_fixed_v6(self):
        integer_families = {
            "small": {(0, 0): {(): 3, (2,): -5, (4, 2): 7},
                      (0, 2): {(2, 2, 2): 11}},
            "large": {(1, 0): {(2,): 13, (2, 2): -17},
                      (3, 2): {(6, 2): 19, (4, 2, 2): -23}},
        }
        for n in (3, 6, 9):
            for r in range(n + 1):
                kwargs = dict(number_variables=n, number_large=r,
                              delta=Q(1, 60), maximum_shift=min(2, n - r))
                expected = FIXED.radialize_integer_families_fixed(
                    RADIAL, integer_families, **kwargs)
                observed = TARGET.radialize_integer_families_fixed(
                    RADIAL, integer_families, **kwargs)
                self.assertEqual(observed[1], expected[1])
                self.assertEqual(
                    {family: {shift: tuple(sorted(terms))
                              for shift, terms in shifted.items()}
                     for family, shifted in observed[0].items()},
                    {family: {shift: tuple(sorted(terms))
                              for shift, terms in shifted.items()}
                     for family, shifted in expected[0].items()})

        k = 4
        delta, alpha_f, eta = Q(1, 10), Q(7, 20), Q(29, 100)
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
        cases = [(r, schedule) for r in range(k)]
        cases.append((
            2, (Q(9, 50), Q(13, 50), Q(29, 100), Q(7, 20))))
        for r, case_schedule in cases:
            kwargs = dict(
                k=k, alpha_high=Q(21, 50), alpha_low=alpha_f,
                alpha_f=alpha_f, eta=eta, delta=delta,
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
