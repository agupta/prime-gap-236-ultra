#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
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


ENGINE = load("pruned_test_engine", HERE / "symmetric_cutoff_cross.py")
FAST = load("pruned_test_fast", HERE / "fast_tagged_scalar.py")
PRUNED = load("pruned_test_target", HERE / "pruned_integer_radial.py")
RADIAL = load("pruned_test_radial", REPO / "verify/exact_capped_certificate.py")
FRONTIER = load(
    "pruned_test_frontier",
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
PRUNED.FAST_V2 = FAST


class PrunedRadialTest(unittest.TestCase):
    def test_partition_transforms_equal_reference_after_filter(self):
        parts = ((), (2,), (4, 2), (2, 2, 2), (6, 4, 2))
        for n in (2, 3, 5):
            for r in range(n + 1):
                for maximum_shift in range(n - r + 1):
                    for part in parts:
                        if len(part) > n:
                            continue
                        expected = {
                            key: value for key, value in
                            RADIAL._partition_face_radial(
                                part, n, r, Q(1, 10)).items()
                            if key[0] <= maximum_shift}
                        observed = PRUNED.partition_face_radial_pruned(
                            RADIAL, part, n, r, Q(1, 10), maximum_shift)
                        self.assertEqual(observed, expected)

    def test_band_value_and_branches_equal_frozen_fast_v2(self):
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
            expected, expected_diagnostics = FAST.band_cross_r_integer(
                ENGINE, RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            observed, diagnostics = PRUNED.band_cross_r_integer(
                ENGINE, RADIAL, families, k=k, alpha_high=high_alpha,
                alpha_low=low_alpha, alpha_f=alpha_f, eta=eta,
                delta=delta, schedule=schedule, common_r=r)
            self.assertEqual(observed, expected)
            self.assertEqual(diagnostics["high"], expected_diagnostics["high"])
            self.assertEqual(diagnostics["low"], expected_diagnostics["low"])


if __name__ == "__main__":
    unittest.main()
