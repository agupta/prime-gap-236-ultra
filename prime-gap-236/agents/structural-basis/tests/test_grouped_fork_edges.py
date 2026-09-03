#!/usr/bin/env python3
"""Small edge-case and POSIX-fork checks for grouped_fixed_vector."""

import multiprocessing
import os
import sys
import unittest
from fractions import Fraction as Q


HERE = os.path.dirname(os.path.abspath(__file__))
EXACT_AGENT = os.path.abspath(os.path.join(HERE, "..", "..", "exact-integrator"))
EXACT_SRC = os.path.join(EXACT_AGENT, "src")
sys.path[:0] = [EXACT_AGENT, EXACT_SRC]

import exact_integrator as ei  # noqa: E402
from grouped_fixed_vector import GroupedEvaluator  # noqa: E402


class GroupedForkAndEdgeAudit(unittest.TestCase):
    def test_k1_zero_shared_dimensions_matches_pairwise(self):
        """J with no shared variables is point evaluation, not a 1-D integral."""
        support = ei.OneStratumSupport(
            1, Q(1, 4), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(3, 20), Q(17, 100))
        labels = [(0, ())]
        vector = [Q(1)]
        grouped = GroupedEvaluator(support, labels, vector, Q)
        grouped_i, _, _ = grouped.evaluate_i()
        grouped_j, _, _ = grouped.evaluate_j()
        m1, m2 = support.matrices(labels)

        self.assertEqual(grouped_i, Q(3, 20))
        self.assertEqual(grouped_i, ei.exact_quadratic(m1, vector))
        self.assertEqual(grouped_j, Q(9, 400))
        self.assertEqual(support.k * grouped_j, ei.exact_quadratic(m2, vector))

    def test_k1_small_branch_boundary_tie_is_assigned_once(self):
        """The repaired alpha == delta boundary assigns the u=0 tie once."""
        support = ei.OneStratumSupport(
            1, Q(1, 10), Q(1, 10), Q(1, 10),
            Q(1, 20), Q(1, 20), Q(1, 20))
        labels = [(0, ())]
        vector = [Q(1)]
        grouped = GroupedEvaluator(support, labels, vector, Q)
        grouped_i, _, _ = grouped.evaluate_i()
        grouped_j, _, _ = grouped.evaluate_j()
        m1, m2 = support.matrices(labels)

        self.assertEqual(grouped_i, Q(1, 10))
        self.assertEqual(grouped_i, ei.exact_quadratic(m1, vector))
        # The source's half-open convention assigns the zero-dimensional tie
        # once and returns 1/100.
        self.assertEqual(grouped_j, Q(1, 100))
        self.assertEqual(support.k * grouped_j, ei.exact_quadratic(m2, vector))

    @unittest.skipUnless(
        os.name == "posix" and "fork" in multiprocessing.get_all_start_methods(),
        "grouped parallelism deliberately requires POSIX fork")
    def test_two_fork_workers_match_serial_exactly(self):
        support = ei.OneStratumSupport(
            3, Q(13, 50), Q(1, 20), Q(6, 25),
            Q(3, 20), Q(4, 25), Q(17, 100))
        labels = [(0, ()), (1, ()), (0, (2,)), (0, (3,))]
        vector = [Q(2), Q(-3), Q(5), Q(7)]

        serial = GroupedEvaluator(support, labels, vector, Q)
        serial_i = serial.evaluate_i(workers=1)
        serial_j = serial.evaluate_j(workers=1)

        parallel = GroupedEvaluator(support, labels, vector, Q)
        parallel_i = parallel.evaluate_i(workers=2)
        parallel_j = parallel.evaluate_j(workers=2)

        self.assertEqual(parallel_i, serial_i)
        self.assertEqual(parallel_j, serial_j)


if __name__ == "__main__":
    unittest.main()
