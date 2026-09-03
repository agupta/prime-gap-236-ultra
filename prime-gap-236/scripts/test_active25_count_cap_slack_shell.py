#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("active25_count_cap_slack_shell.py")
SPEC = importlib.util.spec_from_file_location("cap_slack_tested", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class CapSlackTests(unittest.TestCase):
    def small_support(self, k=4):
        schedule = tuple(Q(1, 5) for _ in range(k))
        return M.A25.shell.ScheduledStratumSupport.make(
            k, Q(1, 3), Q(3, 10), Q(1, 20), schedule)

    def test_degree_zero_i_matches_primary_stratum_integrator(self):
        support = self.small_support(5)
        for r in range(6):
            self.assertEqual(
                M.cap_slack_i_moment(support, r, 0),
                support.canonical_support_residual_in_stratum((), 0, r))

    def test_degree_zero_marginal_matches_primary_integrator(self):
        support = self.small_support(4)
        for r in range(4):
            for h in range(3):
                for branch in M.BRANCHES:
                    if support._branch_constraints(r, h, branch) is None:
                        continue
                    total = M.total_count(r, branch)
                    if total and support.beta(total) - total * support.delta <= 0:
                        # The primary helper may return a formal polynomial on
                        # an empty strict-cap branch; our basis drops it early.
                        continue
                    self.assertEqual(
                        M.cap_slack_marginal(support, r, h, branch, 0),
                        dict(support._marginal_poly(r, h, branch, 0, 0)))

    def test_degree_zero_j_matches_constant_table(self):
        left = self.small_support(4)
        right = M.A25.shell.ScheduledStratumSupport.make(
            4, Q(3, 10), Q(3, 10), Q(1, 20), tuple(Q(1, 5) for _ in range(4)))
        basis = tuple((r, 0) for r in range(4))
        observed, _, _ = M.ordered_j_matrix(left, right, basis, Q(3, 10))
        expected, _ = M.A25.shell.cross_constant_stratum_table(
            left, right, Q(3, 10))
        expected = [row[:4] for row in expected[:4]]
        self.assertEqual(observed, expected)

    @staticmethod
    def eval_poly(poly, z, w):
        return sum((value * z ** a * w ** b
                    for (a, b), value in poly.items()), Q(0))

    def test_positive_degree_marginal_against_literal_antiderivative(self):
        support = self.small_support(4)
        z, w = Q(1, 100), Q(1, 200)
        for r in range(3):
            for h in range(2):
                u0 = (r + h) * support.delta
                for branch in M.BRANCHES:
                    if support._branch_constraints(r, h, branch) is None:
                        continue
                    R = M.total_count(r, branch)
                    if R == 0 or support.beta(R) - R * support.delta <= 0:
                        continue
                    gamma = support.beta(R) - R * support.delta
                    for degree in range(1, 4):
                        if branch == "Sdelta":
                            lo, hi = Q(0), support.delta
                            literal = (hi - lo) * (gamma - z) ** degree
                        elif branch == "Stotal":
                            lo, hi = Q(0), support.alpha - u0 - z - w
                            literal = (hi - lo) * (gamma - z) ** degree
                        else:
                            lo = support.delta
                            cap_upper = support.beta(R) - r * support.delta - z
                            hi = (support.alpha - u0 - z - w
                                  if branch == "Ltotal" else cap_upper)
                            literal = ((cap_upper - lo) ** (degree + 1) -
                                       (cap_upper - hi) ** (degree + 1)) / (degree + 1)
                        literal /= gamma ** degree
                        observed = self.eval_poly(
                            M.cap_slack_marginal(
                                support, r, h, branch, degree), z, w)
                        self.assertEqual(observed, literal)

    def test_ldl_congruence(self):
        a = [[Q(4), Q(2), Q(0)], [Q(2), Q(5), Q(1)],
             [Q(0), Q(1), Q(3)]]
        lower, diagonal = M.ldl(a)
        rebuilt = M.matmul(M.matmul(lower, [
            [diagonal[i] if i == j else Q(0) for j in range(3)]
            for i in range(3)]), M.transpose(lower))
        self.assertEqual(rebuilt, a)
        inverse = M.inverse_unit_lower(lower)
        self.assertEqual(M.matmul(inverse, lower), [
            [Q(1) if i == j else Q(0) for j in range(3)] for i in range(3)])


if __name__ == "__main__":
    unittest.main()
