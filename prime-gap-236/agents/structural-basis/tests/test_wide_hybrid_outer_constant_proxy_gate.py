#!/usr/bin/env python3

import copy
import importlib
import json
import sys
import tempfile
import unittest
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
P = importlib.import_module("wide_hybrid_outer_constant_proxy")
G = importlib.import_module("build_wide_hybrid_outer_constant_proxy_gate")


class WideHybridOuterConstantGateTests(unittest.TestCase):
    def test_frozen_gate_is_disabled_and_exactly_parameterized(self):
        builder_sha = P.sha256(G.HERE)
        gate = G.build_gate(builder_sha)
        self.assertFalse(gate["proxy_launch_authorized"])
        self.assertFalse(gate["target_k48_launch_authorized"])
        self.assertEqual(gate["parameters"], {
            "target_k": 48, "proxy_k": 30,
            "delta": "361/50000", "alpha1": "103/400",
            "eta1": "97/400", "alpha2": "3211/12000",
            "eta2": "3031/12000"})
        self.assertEqual(
            gate["schedules"]["high_plateau"]["active_counts"],
            list(range(24)))
        self.assertEqual(
            gate["schedules"]["volume_ramp"]["active_counts"],
            list(range(23)))
        self.assertEqual(gate["low_k_signed_literal"],
                         P.low_k_signed_literal_tests())
        self.assertEqual(gate["source_hashes"][G.SOURCE_RELATIVE],
                         P.sha256(P.FILE))
        self.assertEqual(gate["source_hashes"][str(G.HERE.relative_to(REPO))],
                         builder_sha)
        self.assertTrue(gate["continuation_gate"]
                        ["proxy_resource_gate_pass"])
        self.assertFalse(gate["continuation_gate"]
                         ["target_k48_resource_gate_pass"])
        self.assertEqual(
            gate["continuation_gate"]["minimum_best_exact_proxy_gain"],
            "1/100000")
        self.assertEqual(
            gate["continuation_gate"]
                ["minimum_best_minus_other_exact_quotient"],
            "1/10000000")
        for name, command in gate["planned_proxy_commands"].items():
            self.assertIn(f"--schedule {name}", command)
            self.assertIn(G.PROXY_OUTPUTS[name], command)

    def test_analytic_audits_are_bound_but_supply_no_quotient(self):
        audits = G.validate_analytic_audits()
        self.assertEqual(set(audits), set(P.SCHEDULES))
        for block in audits.values():
            self.assertEqual(block["status"], "AUDIT PASS")
            self.assertEqual((block["c1"], block["c2"]), ("0", "0"))
            self.assertEqual(len(block["artifact_sha256"]), 64)

    def test_cost_probe_and_parallel_call_arithmetic(self):
        probe = G.validate_cost_probe(REPO / G.COST_PROBE_RELATIVE)
        estimate = P.parallel_proxy_resource_estimate(probe)
        self.assertEqual(estimate["branch_calls_per_process"], {
            "high_plateau": 71034, "volume_ramp": 70266})
        self.assertLess(Q(estimate["estimated_parallel_wall_seconds"]), 900)
        self.assertLessEqual(estimate["estimated_aggregate_peak_rss_kib"],
                             262144)

    def test_probe_mutations_and_wrong_self_hash_reject(self):
        probe = G.validate_cost_probe(REPO / G.COST_PROBE_RELATIVE)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe.json"
            mutation = copy.deepcopy(probe)
            mutation["probe"]["branch_calls"] += 1
            path.write_text(json.dumps(mutation), encoding="ascii")
            with self.assertRaises(ValueError):
                G.validate_cost_probe(path)
            path.write_text('{"status":"x","status":"y"}',
                            encoding="ascii")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                G.validate_cost_probe(path)
        with self.assertRaises(ValueError):
            G.build_gate("0" * 64)

    def test_same_bv_coordinate_is_present_only_as_deferred_cost(self):
        gate = G.build_gate(P.sha256(G.HERE))
        cost = gate["outer_coordinate_cost_assessment"]
        self.assertEqual(cost["same_bv_d16"]["rest_orbits"], 67)
        self.assertFalse(cost["same_bv_d16_is_cheap"])
        self.assertTrue(gate["continuation_gate"]
                        ["same_bv_d16_outer_coordinate_deferred_as_not_cheap"])


if __name__ == "__main__":
    unittest.main()
