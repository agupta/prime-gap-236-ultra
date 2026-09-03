#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "code" /
          "active25_cap_slack_cross_pilot_v2.py")
SPEC = importlib.util.spec_from_file_location("active25_cap_pilot_v2_test", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class Active25CapPilotV2Tests(unittest.TestCase):
    def test_exact_label_and_work_inventory(self):
        labels = M.pilot_labels()
        self.assertEqual(len(labels), 38)
        self.assertEqual([label for label in labels if label[1] > 0], [
            (count, degree) for count in range(9, 15) for degree in (1, 2)])
        work = M.pilot_work_inventory()
        self.assertEqual(work["faces"], 585)
        self.assertEqual(work["weighted_branch_column_terms"], 13888)
        self.assertEqual(sum(row["weighted_branch_column_terms"]
                             for row in work["by_common_r"].values()), 13888)
        self.assertLess(13888, work["full_d0_d2_terms"])
        self.assertLess(work["full_d0_d2_terms"], work["natural_b4_terms"])

    def test_exact_pinned_denominator_ranking(self):
        result = M.exact_d2_denominator_contributions()
        self.assertEqual(result["ranked_counts"][:8],
                         [12, 11, 13, 10, 9, 14, 8, 15])
        selected = Q(result["selected_fraction"])
        self.assertGreater(selected, Q(19, 20))
        self.assertLess(selected, Q(1))
        self.assertEqual(sum((Q(value) for value in
                              result["fractions_by_count"].values()), Q(0)),
                         Q(1))

    def test_pilot_kernel_low_k_matches_full_v1_subset(self):
        k = 3
        delta, eta = Q(1, 20), Q(1, 5)
        schedule = (Q(3, 20), Q(9, 50), Q(1, 5))
        high = M.V1.A25.shell.ScheduledStratumSupport.make(
            k, Q(3, 10), eta, delta, schedule)
        low = M.V1.A25.shell.ScheduledStratumSupport.make(
            k, Q(1, 4), eta, delta, schedule)
        full_r = M.V1.EI.OneStratumSupport(
            k, Q(1, 4), delta, eta,
            Q(1, 4), Q(1, 4), Q(1, 4))
        full_v = M.V1.EI.OneStratumSupport(
            k, Q(1, 5), delta, eta,
            Q(1, 5), Q(1, 5), Q(1, 5))
        supports = {"R": full_r, "V": full_v, "H": high, "L": low}
        def loader():
            return (((0, ()),), (Q(1),), (Q(3), Q(2)), Q(7), Q(11))

        for common_r in range(k):
            expected, emeta = M.V1.grouped_inner_cap_cross_shard(
                common_r, basis=M.pilot_labels(), inner_loader=loader,
                supports=supports, common_eta=eta)
            got, gmeta = M.pilot_shard(
                common_r, inner_loader=loader,
                supports=supports, common_eta=eta)
            self.assertEqual(got, expected)
            self.assertEqual(gmeta, emeta)
            self.assertTrue(all(
                not value or count in (common_r, common_r + 1)
                for (count, _), value in got.items()))

    def test_deterministic_disabled_preflight(self):
        normal = subprocess.run(
            [sys.executable, str(SOURCE), "--preflight-only"],
            text=True, capture_output=True, check=True).stdout
        self.assertIn('"launch_authorized": false', normal)
        self.assertNotIn("exact_quotient", normal)
        denied = subprocess.run(
            [sys.executable, str(SOURCE), "--stage-r", "10"],
            text=True, capture_output=True)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("disabled", denied.stderr)


if __name__ == "__main__":
    unittest.main()
