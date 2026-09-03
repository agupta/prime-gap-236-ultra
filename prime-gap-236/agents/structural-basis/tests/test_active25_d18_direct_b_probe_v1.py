#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


TARGET = (Path(__file__).resolve().parents[1] / "code" /
          "active25_d18_direct_b_probe_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d18_direct_b_probe_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class DirectBProbeTest(unittest.TestCase):
    def test_plan_pin_and_no_target_path(self):
        self.assertEqual(M.sha256(M.PLAN), M.PLAN_SHA256)
        text = TARGET.read_text()
        self.assertNotIn("attempt_001", text)
        self.assertNotIn("--run", text)

    def test_marginal_block_literal(self):
        frontier = M.plan.load("direct_b_block_test_frontier", M.plan.FRONTIER)
        marginal = {(1, ()): Q(2), (2, (3,)): Q(-1)}
        block = M.marginal_orbit_block(
            frontier, marginal, Q(1, 2), Q(1, 10))
        self.assertEqual(block[()][(0, 0)], Q(4, 5))
        self.assertEqual(block[()][(1, 0)], Q(-2))
        self.assertEqual(block[()][(0, 1)], Q(-2))
        self.assertEqual(block[(3,)][(0, 0)], Q(-4, 25))
        self.assertEqual(block[(3,)][(1, 0)], Q(4, 5))
        self.assertEqual(block[(3,)][(0, 1)], Q(4, 5))
        self.assertEqual(block[(3,)][(2, 0)], Q(-1))

    def test_low_k_direct_identity_against_canonical_cross(self):
        frontier = M.plan.load("direct_b_low_k_frontier", M.plan.FRONTIER)
        scan = M.plan.load("direct_b_low_k_scan", M.plan.SCAN)
        k, delta, alpha1, eta = 2, Q(1, 10), Q(7, 20), Q(3, 10)
        low, high = Q(7, 20), Q(2, 5)
        schedule = (Q(3, 20), Q(1, 5))
        basis = ((0, ()), (1, ()), (0, (2,)))
        inner = (Q(2), Q(-3), Q(5))
        outer = (Q(-1), Q(4), Q(2))
        marginal = scan.marginal_polynomial(basis, inner, k, alpha1)
        observed = M.exact_direct_band_b(
            frontier, basis, outer, marginal, k=k, delta=delta,
            alpha1=alpha1, eta=eta, schedule=schedule, low=low, high=high)
        support_type = frontier.shell.ScheduledStratumSupport
        full = support_type.make(k, alpha1, eta, delta, (alpha1,) * k)
        high_support = support_type.make(k, high, eta, delta, schedule)
        low_support = support_type.make(k, low, eta, delta, schedule)
        inner_components = frontier.outer_core.components(basis, inner, k)
        outer_components = frontier.outer_core.components(basis, outer, k)
        expected = 48 * (
            frontier.outer_core.cross_marginal(
                full, inner_components, high_support, outer_components, eta) -
            frontier.outer_core.cross_marginal(
                full, inner_components, low_support, outer_components, eta))
        self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
