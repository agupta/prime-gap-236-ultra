#!/usr/bin/env python3

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


TARGET = (Path(__file__).resolve().parents[1] / "code" /
          "active25_d18_two_band_exact_certificate_plan_v1.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_d18_two_band_exact_certificate_plan_v1", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError(TARGET)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class TwoBandExactCertificatePlanTest(unittest.TestCase):
    def test_pins_and_exact_geometry(self):
        self.assertEqual(M.snapshots().keys(), M.PINS.keys())
        M.validate_two_band()
        self.assertEqual(M.BANDS[0]["eta"], Q(248741, 1000000))
        self.assertEqual(M.BANDS[1]["eta"], Q(224491, 900000))
        self.assertEqual(M.active_counts(M.LOWER_SCHEDULE), tuple(range(12)))
        self.assertEqual(M.active_counts(M.UPPER_SCHEDULE), tuple(range(12)))

    def test_exact_certificate_algebra(self):
        row = M.exact_single_band_certificate_tests(
            (Q(2), Q(3)), (Q(1), Q(2)), Q(5), Q(4))
        self.assertEqual(row["tests"][0]["captured_energy"], Q(1, 2))
        self.assertEqual(row["tests"][1]["captured_energy"], Q(4, 3))
        self.assertIs(row["tests"][0]["passes"], False)
        self.assertIs(row["tests"][1]["passes"], True)
        self.assertIs(row["any_single_band_passes"], True)
        self.assertIs(row["energies_may_be_summed"], False)
        with self.assertRaises(ArithmeticError):
            M.exact_single_band_certificate_tests(
                (Q(0), Q(1)), (Q(1), Q(1)), 2, 1)

    def test_count_slices_sum_to_direct_low_k_moment(self):
        frontier = M.load("two_band_plan_test_frontier", M.FRONTIER)
        support_type = frontier.shell.ScheduledStratumSupport
        schedule = (Q(3, 20), Q(1, 5), Q(1, 4))
        high = support_type.make(3, Q(2, 5), Q(3, 10), Q(1, 10), schedule)
        low = support_type.make(3, Q(7, 20), Q(3, 10), Q(1, 10), schedule)
        terms = {(0, ()): Q(3), (1, (2,)): Q(-2),
                 (2, (3, 2)): Q(5, 7)}
        high_by_count = [sum(
            coefficient * high.orbit_support_moment_in_stratum(
                orbit, power, count)
            for (power, orbit), coefficient in terms.items())
            for count in range(4)]
        low_by_count = [sum(
            coefficient * low.orbit_support_moment_in_stratum(
                orbit, power, count)
            for (power, orbit), coefficient in terms.items())
            for count in range(4)]
        self.assertEqual(sum(high_by_count), sum(
            coefficient * high.orbit_support_moment(orbit, power)
            for (power, orbit), coefficient in terms.items()))
        self.assertEqual(sum(low_by_count), sum(
            coefficient * low.orbit_support_moment(orbit, power)
            for (power, orbit), coefficient in terms.items()))

    def test_direct_full_cross_slices_match_canonical_low_k(self):
        frontier = M.load("two_band_plan_cross_test_frontier", M.FRONTIER)
        support_type = frontier.shell.ScheduledStratumSupport
        k, delta, eta = 2, Q(1, 10), Q(3, 10)
        full = support_type.make(
            k, Q(7, 20), eta, delta, (Q(7, 20),) * k)
        capped = support_type.make(
            k, Q(2, 5), eta, delta, (Q(3, 20), Q(1, 5)))
        basis = ((0, ()), (1, ()), (0, (2,)))
        left_vector = (Q(2), Q(-3), Q(5))
        right_vector = (Q(-1), Q(4), Q(2))
        expected = frontier.outer_core.cross_marginal(
            full, frontier.outer_core.components(basis, left_vector, k),
            capped, frontier.outer_core.components(basis, right_vector, k),
            eta)
        observed = Q(0)
        for r in range(min(k - 1, capped.max_large()) + 1):
            for h in range(int(eta // delta) - r + 1):
                for branch in frontier.BRANCHES:
                    try:
                        first = M.cross_face_orbit_slice_generic(
                            frontier, basis, left_vector, right_vector,
                            full, capped, eta, delta, r, h, branch, 0, 1)
                    except ValueError:
                        continue
                    observed += first["J_slice"]
                    for start in range(1, first["right_marginal_orbits"]):
                        observed += M.cross_face_orbit_slice_generic(
                            frontier, basis, left_vector, right_vector,
                            full, capped, eta, delta, r, h, branch,
                            start, start + 1)["J_slice"]
        self.assertEqual(observed, expected)

    def test_preflight_is_disabled_and_keeps_old_coordinate(self):
        row = M.preflight()
        self.assertEqual(row["separate_bases"], [
            ["inner_refined_D18", "lower_outer_natural_D18"],
            ["inner_refined_D18", "upper_outer_natural_D18"]])
        self.assertEqual(row["basis_dimension_per_test"], 2)
        self.assertIs(row["energies_may_be_summed"], False)
        self.assertIs(row[
            "outer_J_block_required_for_separate_single_band_tests"], False)
        self.assertIs(row[
            "outer_J_block_required_for_combined_multiband_test"], True)
        self.assertIs(row["launch_authorized"], False)
        self.assertIs(row["production_target_started"], False)
        self.assertIs(row["resume_supported"], False)
        self.assertEqual(row["heuristic_launch_gate"]["decision"],
                         "DO_NOT_LAUNCH_NATURAL_D18_EXACT_TARGET")

    def test_cli_has_no_production_action_and_optimized_matches(self):
        commands = ([sys.executable, str(TARGET), "--preflight-only"],
                    [sys.executable, "-O", str(TARGET), "--preflight-only"])
        rows = [subprocess.run(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
                for command in commands]
        self.assertEqual([row.returncode for row in rows], [0, 0])
        self.assertEqual(rows[0].stdout, rows[1].stdout)
        self.assertNotIn("attempt_001", TARGET.read_text())
        self.assertNotIn("--run", TARGET.read_text())


if __name__ == "__main__":
    unittest.main()
