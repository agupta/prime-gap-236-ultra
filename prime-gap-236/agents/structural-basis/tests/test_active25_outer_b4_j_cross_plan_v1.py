#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "code" /
          "active25_outer_b4_j_cross_plan_v1.py")
SPEC = importlib.util.spec_from_file_location("active25_b4_j_plan_tested", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class Active25B4JPlanTests(unittest.TestCase):
    @staticmethod
    def eval_poly(poly, z, w):
        return sum((value * z ** a * w ** b
                    for (a, b), value in poly.items()), Q(0))

    def small_scheduled(self, k, alpha):
        delta = Q(1, 20)
        schedule = (Q(3, 20), Q(9, 50), Q(1, 5))[:k]
        return M.A25.shell.ScheduledStratumSupport.make(
            k, alpha, Q(1, 5), delta, schedule)

    def test_independent_cap_marginal_literal_and_reference(self):
        support = self.small_scheduled(3, Q(3, 10))
        z, w = Q(1, 100), Q(1, 200)
        checked = 0
        for r in range(3):
            for h in range(3):
                u0 = (r + h) * support.delta
                for branch in M.BRANCHES:
                    if support._branch_constraints(r, h, branch) is None:
                        continue
                    count = M.branch_total(r, branch)
                    if count == 0:
                        gamma = Q(1)
                        degrees = (0,)
                    else:
                        gamma = support.beta(count) - count * support.delta
                        if gamma <= 0:
                            continue
                        degrees = range(4)
                    for degree in degrees:
                        observed = M.independent_cap_marginal(
                            support, r, h, branch, degree)
                        self.assertEqual(
                            observed,
                            M.CAP.cap_slack_marginal(
                                support, r, h, branch, degree))
                        if branch == "Sdelta":
                            lo, hi = Q(0), support.delta
                            literal = (hi - lo) * (gamma - z) ** degree
                        elif branch == "Stotal":
                            lo, hi = Q(0), support.alpha - u0 - z - w
                            literal = (hi - lo) * (gamma - z) ** degree
                        else:
                            lo = support.delta
                            cap_upper = support.beta(count) - r * support.delta - z
                            hi = (support.alpha - u0 - z - w
                                  if branch == "Ltotal" else cap_upper)
                            literal = (
                                ((cap_upper - lo) ** (degree + 1) -
                                 (cap_upper - hi) ** (degree + 1)) /
                                (degree + 1))
                        if count:
                            literal /= gamma ** degree
                        self.assertEqual(
                            self.eval_poly(observed, z, w), literal)
                        checked += 1
        self.assertGreater(checked, 20)

    def test_grouped_low_k_degree_zero_equals_literal_primary_cross(self):
        k = 3
        high = self.small_scheduled(k, Q(3, 10))
        low = self.small_scheduled(k, Q(1, 4))
        delta, eta = Q(1, 20), Q(1, 5)
        full_r = M.EI.OneStratumSupport(
            k, Q(1, 4), delta, eta,
            Q(1, 4), Q(1, 4), Q(1, 4))
        full_v = M.EI.OneStratumSupport(
            k, Q(1, 5), delta, eta,
            Q(1, 5), Q(1, 5), Q(1, 5))
        supports = {"R": full_r, "V": full_v, "H": high, "L": low}
        basis = tuple((count, 0) for count in range(k + 1))

        def loader():
            return (((0, ()),), (Q(1),), (Q(3), Q(2)), Q(7), Q(11))

        got = Q(0)
        for common_r in range(k):
            values, metadata = M.grouped_inner_cap_cross_shard(
                common_r, basis=basis, inner_loader=loader,
                supports=supports, common_eta=eta)
            self.assertTrue(all(not value or count in
                                (common_r, common_r + 1)
                                for (count, _), value in values.items()))
            self.assertEqual(metadata["inner_I"], Q(7))
            self.assertEqual(metadata["inner_48J"], Q(11))
            got += sum(values.values(), Q(0))

        one = (((), 0, 0, Q(1)),)
        direct = M.A25.outer_core.cross_marginal
        expected = (
            Q(2) * (direct(full_r, one, high, one, eta) -
                    direct(full_r, one, low, one, eta)) +
            (direct(full_v, one, high, one, eta) -
             direct(full_v, one, low, one, eta)))
        self.assertEqual(got, expected)

    def test_factor_48_and_mixed_transpose(self):
        hh = [[Q(5), Q(2)], [Q(2), Q(7)]]
        hl = [[Q(1), Q(3)], [Q(4), Q(2)]]
        ll = [[Q(6), Q(1)], [Q(1), Q(8)]]
        got = M.assemble_natural_outer_b48(hh, hl, ll, k=48)
        self.assertEqual(got, [[Q(432), Q(-192)], [Q(-192), Q(528)]])
        self.assertNotEqual(got[0][1], 48 * (hh[0][1] - 2 * hl[0][1] +
                                             ll[0][1]))
        cross = M.assemble_inner_cross_b48(
            [3, 5], [1, 2], [7, 11], [2, 3], (Q(3), Q(2)))
        self.assertEqual(cross, [Q(432), Q(672)])

    def test_target_inventory_and_cost_bindings(self):
        work = M.target_work_inventory(2)
        self.assertEqual(work["faces"], 585)
        self.assertEqual(work["cap_dimension"], 76)
        self.assertEqual(work["cap_I_unique_nonzero_entries"], 151)
        self.assertEqual(work["cap_J_unique_upper_nonzero_entries"], 370)
        self.assertEqual(work["cap_inner_cross_literal_weighted_terms"], 27280)
        self.assertEqual(work["natural_b4_inner_cross_literal_weighted_terms"],
                         93600)
        self.assertEqual(
            work["natural_b4_outer_j_literal_entry_branch_terms"], 1965600)
        cost = M.measured_cost_model()
        self.assertEqual(len(cost["cap_shell_exact_runs"]), 3)
        self.assertLess(cost["projected_cap_d0_d2_cross_seconds_conservative"],
                        cost["projected_natural_b4_cross_seconds_conservative"])
        self.assertLessEqual(cost["constant_cross_probe_peak_rss_kib"], 40000)

    def test_cli_is_preflight_only(self):
        completed = subprocess.run(
            [sys.executable, str(SOURCE), "--stage-r", "0"],
            text=True, capture_output=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("disabled", completed.stderr)
        completed = subprocess.run(
            [sys.executable, str(SOURCE), "--preflight-only"],
            text=True, capture_output=True, check=True)
        self.assertIn('"launch_authorized": false', completed.stdout)
        self.assertNotIn("exact_quotient", completed.stdout)


if __name__ == "__main__":
    unittest.main()
