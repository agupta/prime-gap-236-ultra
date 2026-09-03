#!/usr/bin/env python3
"""Independent low-dimensional regressions for bv_two_band_r0_shell.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "bv_two_band_r0_shell.py"
SPEC = importlib.util.spec_from_file_location("bv_two_band_r0_shell_tested", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load two-band shell implementation")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def positive_part(value):
    return max(Q(0), value)


def box2_cdf_constant(delta, endpoint):
    return (positive_part(endpoint) ** 2 -
            2 * positive_part(endpoint - delta) ** 2 +
            positive_part(endpoint - 2 * delta) ** 2) / 2


def integrate_product_of_linears(c0, c1, d0, d1, lo, hi):
    # Independent literal expansion of (c0+c1*u)(d0+d1*u).
    return ((c0 * d0) * (hi - lo) +
            (c0 * d1 + c1 * d0) * (hi ** 2 - lo ** 2) / 2 +
            (c1 * d1) * (hi ** 3 - lo ** 3) / 3)


class BoxMomentTests(unittest.TestCase):
    def setUp(self):
        M.orbit_density.cache_clear()

    def test_one_dimensional_orbit_signed_polynomial(self):
        delta = Q(1, 3)
        lo, hi = Q(1, 10), Q(1, 2)
        # P_(2)(u)=u^2 in one dimension and the box clips hi to delta.
        expected = (Q(2, 3) * (delta ** 3 - lo ** 3) -
                    Q(3, 4) * (delta ** 4 - lo ** 4))
        got = M.box_orbit_interval(
            1, delta, (2,), {0: Q(2), 1: Q(-3)}, lo, hi)
        self.assertEqual(got, expected)

    def test_two_dimensional_box_cdf(self):
        delta = Q(3, 10)
        for endpoint in (Q(1, 10), Q(2, 5), Q(7, 10)):
            got = M.box_orbit_cumulative(2, delta, (), {0: Q(1)}, endpoint)
            self.assertEqual(got, box2_cdf_constant(delta, endpoint))

    def test_shell_volume_is_difference_of_box_cdfs(self):
        delta = Q(3, 10)
        lo, hi = Q(2, 5), Q(9, 20)
        self.assertEqual(
            M.box_volume_between(2, delta, lo, hi),
            box2_cdf_constant(delta, hi) - box2_cdf_constant(delta, lo))


class LiteralDefinition5Tests(unittest.TestCase):
    def test_signed_k2_cross_and_polarization(self):
        # This deliberately uses signed amplitudes so a dropped sign or a
        # mistaken factor two is visible.  The common dimension is one.
        k = 2
        alpha1, alpha2 = Q(2, 5), Q(9, 20)
        eta1, eta2, delta = Q(8, 25), Q(7, 20), Q(3, 10)
        amp_inner, amp_outer = Q(2), Q(-1)
        intervals = M.shell_intervals(alpha1, alpha2, eta2, delta)
        basis, vector = [(0, ())], [Q(1)]
        mr = M.marginal_expansion(basis, vector, k, alpha1)
        mv = M.marginal_expansion(basis, vector, k, eta1)
        got_cross = (amp_outer * M.contract_marginal_with_shell(
                         mr, alpha1, intervals, 1, delta) +
                     (amp_inner - amp_outer) * M.contract_marginal_with_shell(
                         mv, eta1, M.clip_intervals(intervals, eta1), 1, delta))

        x0, x1 = alpha1 - delta, alpha2 - delta
        stop = min(eta2, delta)
        # p(u)=b(R-u)+(a-b)(V-u) below V and b(R-u) above V;
        # q(u)=u-x0 then alpha2-alpha1.  Integrate those literal fibers.
        expected = Q(0)
        pieces = ((x0, x1, -x0, Q(1)),
                  (x1, stop, alpha2 - alpha1, Q(0)))
        for lo, hi, q0, q1 in pieces:
            if hi <= lo:
                continue
            left_hi = min(hi, eta1)
            if left_hi > lo:
                p0 = amp_outer * alpha1 + \
                    (amp_inner - amp_outer) * eta1
                p1 = -amp_inner
                expected += integrate_product_of_linears(
                    p0, p1, q0, q1, lo, left_hi)
            right_lo = max(lo, eta1)
            if hi > right_lo:
                expected += integrate_product_of_linears(
                    amp_outer * alpha1, -amp_outer,
                    q0, q1, right_lo, hi)
        self.assertEqual(got_cross, expected)

        got_shell_self = sum(M.box_orbit_interval(
            1, delta, (), M.poly_mul(poly, poly), lo, hi)
            for lo, hi, poly in intervals)
        expected_shell_self = (
            integrate_product_of_linears(-x0, 1, -x0, 1, x0, x1) +
            (alpha2 - alpha1) ** 2 * (stop - x1))
        self.assertEqual(got_shell_self, expected_shell_self)

        # Definition 5's numerator for x F1+y F2 has B00+2B01+B11.
        # Checking at signed (x,y)=(3,-2) catches cross ownership and k once.
        p0 = amp_outer * alpha1 + (amp_inner - amp_outer) * eta1
        p1 = -amp_inner
        inner_j = integrate_product_of_linears(
            p0, p1, p0, p1, Q(0), eta1)
        B00, B01, B11 = k * inner_j, k * got_cross, k * got_shell_self
        x, y = Q(3), Q(-2)
        matrix_value = x * x * B00 + 2 * x * y * B01 + y * y * B11
        literal_block_sum = k * (
            x * x * inner_j + 2 * x * y * expected +
            y * y * expected_shell_self)
        self.assertEqual(matrix_value, literal_block_sum)

        # Extending the inner-inner cutoff to eta2 is a genuine error, even
        # when the total support is written as adjacent bands.
        wrong_extra = integrate_product_of_linears(
            amp_outer * alpha1, -amp_outer,
            amp_outer * alpha1, -amp_outer, eta1, eta2)
        self.assertGreater(wrong_extra, 0)
        self.assertNotEqual(B00, B00 + k * wrong_extra)

    def test_radial_marginal_constant(self):
        for upper in (Q(3, 10), Q(2, 5)):
            self.assertEqual(
                M.marginal_expansion([(0, ())], [Q(1)], 3, upper),
                {((), 1): Q(1)})


if __name__ == "__main__":
    unittest.main()
