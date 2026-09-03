#!/usr/bin/env python3
"""Small exact regressions for the independent BV piecewise formulas."""

from __future__ import annotations

import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "agents" / "exact-integrator" / "src"))

import exact_integrator as ei  # noqa: E402
from dead_core_mass import DeadCoreMoments  # noqa: E402
from radial_split import (  # noqa: E402
    CrossMoments,
    marginal_expansion,
    simplex_residual_moment,
)


class DeadCoreTests(unittest.TestCase):
    def test_shifted_triangle_moments(self):
        # k=2, V=1, R=3: C is t1>1,t2>1,t1+t2<3.  After shifting
        # t1=1+x,t2=1+y, it is the unit triangle x,y>=0,x+y<1.
        moments = DeadCoreMoments(2, Q(3), Q(1), Q)
        self.assertEqual(moments.moment(0, ()), Q(1, 2))
        self.assertEqual(moments.moment(0, (1,)), Q(4, 3))
        self.assertEqual(moments.moment(1, ()), Q(-5, 6))

    def test_empty_core_cancels_exactly(self):
        # With two coordinates the inequalities t1> S-V and t2>S-V
        # imply S>2V.  Hence R<2V makes the core empty.
        moments = DeadCoreMoments(2, Q(3, 2), Q(1), Q)
        for c in range(4):
            for nu in ((), (1,), (2,), (1, 1), (3, 1)):
                self.assertEqual(moments.moment(c, nu), 0)


class RadialSplitTests(unittest.TestCase):
    def test_simplex_residual_matches_integrator(self):
        k, radius = 4, Q(3, 10)
        support = ei.OneStratumSupport(
            k, radius, Q(1, 20), radius, radius, radius, radius)
        for c in range(5):
            for nu in ((), (1,), (2,), (1, 1), (3, 1)):
                got = simplex_residual_moment(k, radius, c, nu, Q)
                self.assertEqual(got, support.orbit_support_moment(nu, c))

    def test_rr_marginal_matches_integrator(self):
        k, radius, cutoff = 4, Q(3, 10), Q(1, 4)
        support = ei.OneStratumSupport(
            k, radius, Q(1, 20), cutoff, radius, radius, radius)
        basis = [(0, ()), (1, ()), (0, (2,)), (2, (2,))]
        vector = [Q(2), Q(-3, 2), Q(5, 7), Q(1, 11)]
        marginal = marginal_expansion(basis, vector, k, radius, Q)
        cross = CrossMoments(k - 1, cutoff, Q)
        got_j = cross.contract(marginal, marginal, radius, radius, 0)
        expected_j = sum(
            vector[i] * vector[j] * support.basis_j(basis[i], basis[j])
            for i in range(len(basis)) for j in range(len(basis))
        )
        self.assertEqual(got_j, expected_j)


if __name__ == "__main__":
    unittest.main()
