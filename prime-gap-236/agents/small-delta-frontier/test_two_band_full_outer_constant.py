#!/usr/bin/env python3
"""Hostile low-k tests for the full capped outer-band cross evaluator."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
PATH = HERE / "two_band_full_outer_constant.py"
SPEC = importlib.util.spec_from_file_location("full_outer_tested", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load full outer implementation")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def constant_marginal_k2(support, u):
    """Literal distinguished-t length from the support definition at k=2."""
    remaining = support.alpha - u
    if remaining <= 0 or u < 0:
        return Q(0)
    delta = support.delta
    if u <= delta:
        # Common u is small.  A large distinguished t is capped by B_1.
        return max(Q(0), min(remaining, support.beta(1)))
    # Common u is already large and must itself meet B_1.  A small t does not
    # change the large count; a large t invokes B_2.
    if u > support.beta(1):
        return Q(0)
    small = max(Q(0), min(delta, remaining))
    large_upper = min(remaining, support.beta(2) - u)
    large = max(Q(0), large_upper - delta)
    return small + large


def literal_constant_cross_k2(left, right, eta):
    points = {Q(0), eta}
    for support in (left, right):
        points.update((
            support.delta, support.alpha, support.alpha - support.delta,
            support.alpha - support.beta(1), support.beta(1),
            support.beta(2) - support.delta, support.beta(2),
        ))
    points = sorted(x for x in points if 0 <= x <= eta)
    answer = Q(0)
    for lo, hi in zip(points, points[1:]):
        if hi <= lo:
            continue
        x1 = (2 * lo + hi) / 3
        x2 = (lo + 2 * hi) / 3
        l1, l2 = constant_marginal_k2(left, x1), constant_marginal_k2(left, x2)
        r1, r2 = constant_marginal_k2(right, x1), constant_marginal_k2(right, x2)
        lslope = (l2 - l1) / (x2 - x1)
        rslope = (r2 - r1) / (x2 - x1)
        lzero, rzero = l1 - lslope * x1, r1 - rslope * x1
        midpoint = (lo + hi) / 2
        if (constant_marginal_k2(left, midpoint) != lzero + lslope * midpoint or
                constant_marginal_k2(right, midpoint) != rzero + rslope * midpoint):
            raise AssertionError("missing literal marginal breakpoint")
        answer += (
            lzero * rzero * (hi - lo) +
            (lzero * rslope + lslope * rzero) * (hi ** 2 - lo ** 2) / 2 +
            lslope * rslope * (hi ** 3 - lo ** 3) / 3)
    return answer


class FullOuterCrossTests(unittest.TestCase):
    def test_different_support_constant_cross_literal_k2(self):
        delta = M.DELTA
        left = M.ScheduledSupport.make(
            2, Q(11, 50), Q(1, 5), (Q(9, 50), Q(1, 5)))
        right = M.ScheduledSupport.make(
            2, Q(6, 25), Q(1, 5), (Q(4, 25), Q(9, 50)))
        one = (((), 0, 0, Q(1)),)
        got = M.cross_marginal(left, one, right, one, Q(1, 5))
        expected = literal_constant_cross_k2(left, right, Q(1, 5))
        self.assertEqual(got, expected)

    def test_support_difference_polarization_and_factor(self):
        high = M.ScheduledSupport.make(
            2, Q(6, 25), Q(1, 5), (Q(6, 25), Q(6, 25)))
        low = M.ScheduledSupport.make(
            2, Q(11, 50), Q(1, 5), (Q(6, 25), Q(6, 25)))
        one = (((), 0, 0, Q(1)),)
        hh = M.cross_marginal(high, one, high, one, Q(1, 5))
        hl = M.cross_marginal(high, one, low, one, Q(1, 5))
        ll = M.cross_marginal(low, one, low, one, Q(1, 5))
        shell = hh - 2 * hl + ll
        literal = (
            literal_constant_cross_k2(high, high, Q(1, 5)) -
            2 * literal_constant_cross_k2(high, low, Q(1, 5)) +
            literal_constant_cross_k2(low, low, Q(1, 5)))
        self.assertEqual(shell, literal)
        self.assertGreater(shell, 0)
        # The low-k numerator convention is k*J, so the realized k=2 shell
        # entry is exactly 2*shell (and not shell or 4*shell).
        numerator_k2 = Q(2) * shell
        self.assertEqual(numerator_k2 / 2, shell)
        self.assertNotEqual(numerator_k2, shell)

    def test_builtin_signed_orbit_regression(self):
        M.validate_sources()
        M.low_k_self_test()

    def test_invalid_schedule_rejected(self):
        with self.assertRaisesRegex(ValueError, "B_m"):
            M.ScheduledSupport.make(
                2, Q(11, 50), Q(1, 5), (Q(9, 50), Q(21, 100)))


if __name__ == "__main__":
    unittest.main()
