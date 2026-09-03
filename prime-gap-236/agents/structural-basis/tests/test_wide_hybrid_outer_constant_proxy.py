#!/usr/bin/env python3

import importlib.util
import copy
import json
import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
SOURCE = HERE.parents[1] / "code" / "wide_hybrid_outer_constant_proxy.py"
SPEC = importlib.util.spec_from_file_location("wide_hybrid_proxy_tested", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load wide-hybrid proxy")
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def independent_constant_marginal(support, common):
    remaining = support.alpha - common
    if remaining <= 0 or common < 0:
        return Q(0)
    if common <= support.delta:
        return max(Q(0), min(remaining, support.beta(1)))
    if common > support.beta(1):
        return Q(0)
    return (max(Q(0), min(support.delta, remaining)) +
            max(Q(0), min(remaining, support.beta(2) - common) -
                support.delta))


def independent_literal_cross(left, right, eta):
    breakpoints = {Q(0), Q(eta)}
    for support in (left, right):
        breakpoints.update({
            support.delta, support.alpha,
            support.alpha - support.delta,
            support.alpha - support.beta(1), support.beta(1),
            support.beta(2) - support.delta, support.beta(2)})
    breakpoints = sorted(value for value in breakpoints if 0 <= value <= eta)
    total = Q(0)
    for lower, upper in zip(breakpoints, breakpoints[1:]):
        if lower == upper:
            continue
        x0, x1 = (2 * lower + upper) / 3, (lower + 2 * upper) / 3
        l0, l1 = (independent_constant_marginal(left, x0),
                  independent_constant_marginal(left, x1))
        r0, r1 = (independent_constant_marginal(right, x0),
                  independent_constant_marginal(right, x1))
        ls, rs = (l1 - l0) / (x1 - x0), (r1 - r0) / (x1 - x0)
        lc, rc = l0 - ls * x0, r0 - rs * x0
        midpoint = (lower + upper) / 2
        if (independent_constant_marginal(left, midpoint) != lc + ls * midpoint or
                independent_constant_marginal(right, midpoint) !=
                rc + rs * midpoint):
            raise AssertionError("independent breakpoint set is incomplete")
        total += (lc * rc * (upper - lower) +
                  (lc * rs + ls * rc) * (upper ** 2 - lower ** 2) / 2 +
                  ls * rs * (upper ** 3 - lower ** 3) / 3)
    return total


class WideHybridOuterConstantProxyTests(unittest.TestCase):
    def test_exact_schedule_formulas_and_active_counts(self):
        self.assertTrue(M.validate_schedules())
        high = M.SCHEDULES["high_plateau"]
        volume = M.SCHEDULES["volume_ramp"]
        self.assertEqual(high[0], Q(11, 200))
        self.assertEqual(high[17:], (Q(43, 250),) * 7)
        self.assertEqual(volume[0], Q(49, 625))
        self.assertEqual(volume[12:], (Q(1599, 10000),) * 11)
        self.assertEqual(M.active_counts(high), tuple(range(24)))
        self.assertEqual(M.active_counts(volume), tuple(range(23)))

    def test_k2_literal_cross_without_producer_literal_helper(self):
        delta, eta = Q(1, 20), Q(1, 5)
        left = M.ScheduledSupport.make(
            2, Q(6, 25), delta, eta, (Q(4, 25), Q(9, 50)))
        right = M.ScheduledSupport.make(
            2, Q(13, 50), delta, eta, (Q(9, 50), Q(1, 5)))
        one = (((), 0, 0, Q(1)),)
        observed = M.cross_marginal(left, one, right, one, eta)
        self.assertEqual(observed, independent_literal_cross(left, right, eta))
        self.assertEqual(observed, Q(7079, 3000000))

    def test_signed_orbit_and_polarization_regressions(self):
        result = M.low_k_signed_literal_tests()
        self.assertEqual(result["signed_self"], "94927012783/126000000000000")
        self.assertEqual(result["shell_j"], "1/12500")
        self.assertEqual(result["k2_shell_numerator"], "1/6250")

    def test_certified_radial_base_is_recontracted(self):
        self.assertEqual(M.validate_sources()[M.CERTIFICATE_RELATIVE],
                         M.CERTIFICATE_SHA256)
        radial = M.load_radial_base()
        self.assertEqual(radial["amplitudes"][0], 1)
        self.assertEqual(radial["numerator"] / radial["denominator"],
                         radial["quotient"])
        self.assertGreater(radial["quotient"], Q(9812, 10000))

    def test_target_constant_shell_masses_match_independent_artifact(self):
        masses = M.exact_target_shell_masses()
        self.assertGreater(masses["high_plateau"], 0)
        self.assertGreater(masses["volume_ramp"],
                           17 * masses["high_plateau"])
        comparison = json.loads(
            (M.REPO / M.SHELL_VOLUME_RELATIVE).read_bytes())
        self.assertEqual(masses["high_plateau"],
                         Q(comparison["balanced"]["exact_I_shell"]))
        self.assertEqual(masses["volume_ramp"],
                         Q(comparison["volume_ramp"]["exact_I_shell"]))

    def test_same_bv_outer_coordinate_is_not_the_cheap_screen(self):
        cost = M.outer_coordinate_complexity()
        self.assertEqual(cost["constant"]["rest_orbits"], 1)
        self.assertEqual(cost["same_bv_d16"]["basis_terms"], 307)
        self.assertEqual(cost["same_bv_d16"]["marginal_components"], 769)
        self.assertEqual(cost["same_bv_d16"]["rest_orbits"], 67)
        self.assertEqual(
            cost["raw_rest_orbit_pair_ratio_self_vs_constant"], 4489)
        self.assertFalse(cost["same_bv_d16_is_cheap"])

    def test_proxy_dimension_is_minimal_nonempty_common_dimension(self):
        self.assertEqual(M.PROXY_K, 30)
        for name, schedule in M.SCHEDULES.items():
            at_proxy = schedule[:M.PROXY_K]
            high = M.ScheduledSupport.make(
                M.PROXY_K, M.ALPHA2, M.DELTA, M.ETA2, at_proxy)
            low = M.ScheduledSupport.make(
                M.PROXY_K, M.ALPHA1, M.DELTA, M.ETA2, at_proxy)
            shell = (high.basis_m1((0, ()), (0, ())) -
                     low.basis_m1((0, ()), (0, ())))
            self.assertGreater(shell, 0, name)
        schedule = M.SCHEDULES["high_plateau"][:29]
        high = M.ScheduledSupport.make(
            29, M.ALPHA2, M.DELTA, M.ETA2, schedule)
        low = M.ScheduledSupport.make(
            29, M.ALPHA1, M.DELTA, M.ETA2, schedule)
        self.assertEqual(high.basis_m1((0, ()), (0, ())),
                         low.basis_m1((0, ()), (0, ())))

    def test_target_geometry_and_cost_are_predeclared(self):
        expected_calls = {"high_plateau": 62784, "volume_ramp": 61456}
        for name, schedule in M.SCHEDULES.items():
            geometry = M.target_geometry_estimate(schedule)
            calls = sum(value["branch_pair_upper"]
                        for value in geometry.values())
            self.assertEqual(calls, expected_calls[name])
            estimate = M.resource_estimate(geometry)
            self.assertGreater(Q(estimate["estimated_wall_seconds"]),
                               M.MAX_ESTIMATED_TARGET_WALL_SECONDS)
        self.assertEqual(M.MIN_PROXY_GAIN, Q(1, 100000))
        self.assertEqual(M.MIN_PROXY_SCHEDULE_SEPARATION,
                         Q(1, 10000000))
        proxy = M.proxy_geometry_estimate()
        self.assertEqual(proxy["total_branch_pair_upper"], 119610)
        self.assertEqual(
            proxy["schedules"]["high_plateau"]["rr"][
                "branch_pair_upper"], 7008)
        self.assertEqual(M.MAX_ESTIMATED_PROXY_WALL_SECONDS, 900)
        self.assertEqual(M.MAX_PROXY_PEAK_RSS_KIB, 131072)

        old_probe = json.loads((M.REPO / "agents/structural-basis/results/"
                                "wide_hybrid_outer_constant_D4_k30_cost_probe.json"
                                ).read_bytes())
        probe = copy.deepcopy(old_probe)
        probe["script_sha256"] = M.sha256(M.FILE)
        estimate = M.parallel_proxy_resource_estimate(probe)
        self.assertEqual(estimate["branch_calls_per_process"], {
            "high_plateau": 71034, "volume_ramp": 70266})
        self.assertTrue(estimate["resource_gate_pass"])
        self.assertLessEqual(Q(estimate["estimated_parallel_wall_seconds"]),
                             M.MAX_ESTIMATED_PROXY_WALL_SECONDS)

    def test_invalid_schedule_rejected(self):
        with self.assertRaisesRegex(ValueError, "B_m"):
            M.ScheduledSupport.make(
                2, Q(6, 25), Q(1, 20), Q(1, 5),
                (Q(3, 20), Q(21, 100)))


if __name__ == "__main__":
    unittest.main()
