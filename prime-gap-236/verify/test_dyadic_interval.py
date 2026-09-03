#!/usr/bin/env python3
"""Adversarial arithmetic tests for the fixed-point interval ring."""

from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.dyadic_interval import DyadicInterval as D
from verify.dyadic_interval import IndeterminateComparison


class DyadicIntervalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        D.configure(24, 40)

    def assert_contains(self, interval, exact):
        self.assertTrue(interval.contains(exact), (interval, exact))

    def test_leaf_and_all_signed_binary_operations(self):
        values = [Q(n, d) for n in range(-9, 10)
                  for d in range(1, 10)]
        for x in values:
            ix = D(x)
            self.assert_contains(ix, x)
            for y in values:
                iy = D(y)
                self.assert_contains(ix + iy, x + y)
                self.assert_contains(ix - iy, x - y)
                self.assert_contains(ix * iy, x * y)
                if y:
                    self.assert_contains(ix / iy, x / y)

    def test_integer_powers(self):
        for x in [Q(-7, 5), Q(-1, 9), Q(0), Q(2, 3), Q(13, 4)]:
            for exponent in range(10):
                self.assert_contains(D(x) ** exponent, x ** exponent)
            if x:
                for exponent in range(-4, 0):
                    self.assert_contains(D(x) ** exponent, x ** exponent)

    def test_exact_geometry_comparisons_and_fail_closed_overlap(self):
        self.assertTrue(D(Q(1, 3)) < D(Q(1, 2)))
        self.assertTrue(D(Q(1, 3)) <= D(Q(1, 3)))
        x = D._from_bounds(0, 2, None)
        y = D._from_bounds(1, 3, None)
        with self.assertRaises(IndeterminateComparison):
            _ = x < y
        with self.assertRaises(IndeterminateComparison):
            _ = x <= y

    def test_zero_divisor_rejected(self):
        denominator = D._from_bounds(-1, 1, None)
        with self.assertRaises(ZeroDivisionError):
            _ = D(1) / denominator

    def test_widths_are_nonnegative(self):
        x = D(Q(1, 3))
        y = D(Q(-7, 11))
        expressions = [x, y, -x, abs(y), x + y, x - y,
                       x * y, x / y, x ** 7]
        self.assertTrue(all(item.width_units() >= 0 for item in expressions))

    def test_live_endpoints_cannot_be_reinterpreted(self):
        x = D(Q(1, 3))
        D.configure(24, 40)  # an identical idempotent request is harmless
        self.assertTrue(x.contains(Q(1, 3)))
        with self.assertRaises(RuntimeError):
            D.configure(25, 40)
        with self.assertRaises(RuntimeError):
            D.configure(24, 41)
        self.assertTrue(x.contains(Q(1, 3)))

    def test_numeric_equality_obeys_hash_contract(self):
        for value in (0, 1, -3, Q(1, 3), Q(-7, 11)):
            interval = D(value)
            self.assertEqual(interval, value)
            self.assertEqual(hash(interval), hash(value))
            self.assertEqual({interval: "interval"}.get(value), "interval")
            self.assertEqual({value: "number"}.get(interval), "number")

    def test_equal_enclosures_do_not_claim_equal_numbers(self):
        # At this test precision the two distinct rationals round to the same
        # nondegenerate enclosure after their exact shadows are suppressed.
        x_exact = Q(1, (1 << 41) + 1)
        y_exact = x_exact + Q(1, 10 * D.SCALE * (1 << 20))
        x = D(x_exact)
        y = D(y_exact)
        self.assertIsNone(x.exact)
        self.assertIsNone(y.exact)
        self.assertEqual((x.lo, x.hi), (y.lo, y.hi))
        self.assertNotEqual(x, y)
        self.assertNotEqual(x, x_exact)
        self.assertIsNone({x: "x"}.get(x_exact))
        singleton = D._from_bounds(17, 17, None)
        same_singleton = D._from_bounds(17, 17, None)
        self.assertEqual(singleton, same_singleton)
        self.assertEqual(hash(singleton), hash(same_singleton))
        self.assertEqual(hash(singleton), hash(singleton.lower_fraction()))


if __name__ == "__main__":
    unittest.main()
