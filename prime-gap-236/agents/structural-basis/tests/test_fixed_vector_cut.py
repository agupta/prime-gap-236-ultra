#!/usr/bin/env python3

import os
import sys
import unittest
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
STRUCT = os.path.abspath(os.path.join(HERE, "..", "code"))
EXACT = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator", "src"))
sys.path[:0] = [STRUCT, EXACT]

from exact_integrator import OneStratumSupport, exact_quadratic  # noqa:E402
from fixed_vector_cut import fixed_i, fixed_j  # noqa:E402


class FixedVectorCutTests(unittest.TestCase):
    def check(self, support, labels, vector):
        m1, m2 = support.matrices(labels)
        den, _ = fixed_i(support, labels, vector)
        j, _, _ = fixed_j(support, labels, vector)
        self.assertEqual(den, exact_quadratic(m1, vector))
        self.assertEqual(support.k * j, exact_quadratic(m2, vector))

    def test_mixed_odd_orbits_k3(self):
        support = OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        self.check(support,
                   [(0, ()), (1, ()), (0, (2,)), (0, (3,))],
                   [Q(2), Q(-3), Q(5), Q(7)])

    def test_repeated_part_orbit_k4(self):
        support = OneStratumSupport(
            4, Q(27, 100), Q(1, 25), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(9, 50))
        self.check(support,
                   [(0, ()), (2, ()), (0, (2, 2)), (1, (3,))],
                   [Q(11, 3), Q(-5, 2), Q(7, 4), Q(2, 9)])


if __name__ == "__main__":
    unittest.main()
