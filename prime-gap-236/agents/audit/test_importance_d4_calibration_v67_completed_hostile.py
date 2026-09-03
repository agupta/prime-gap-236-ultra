#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
CHECKER = REPO / "agents/audit/verify_importance_d4_calibration_v67_completed.py"
RECOVERED = REPO / "agents/structural-basis/results/importance_d4_calibration_v67_recovered_from_v66.json"

spec = importlib.util.spec_from_file_location(
    "hostile_v67_completed_checker", CHECKER)
V = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = V
spec.loader.exec_module(V)


def fixture():
    full = json.loads(RECOVERED.read_bytes())["analysis"]
    return {
        "hard_gates": copy.deepcopy(full["hard_gates"]),
        "statistical_gates": copy.deepcopy(full["statistical_gates"]),
        "gates_passed": full["gates_passed"],
        "extension_authorized": full["extension_authorized"],
        "jackknife": {
            degree: {
                key: copy.deepcopy(full["jackknife"][degree][key])
                for key in ("exact_in_interval", "relative_discrepancy_pass",
                            "relative_discrepancy")}
            for degree in ("0", "1", "2")
        },
        "reconstruction": {
            "maximum_split_rhat": copy.deepcopy(
                full["reconstruction"]["maximum_split_rhat"]),
            "minimum_batch_means_ess": copy.deepcopy(
                full["reconstruction"]["minimum_batch_means_ess"]),
            "all_z_precision_pass":
                full["reconstruction"]["all_z_precision_pass"],
            "conditional": copy.deepcopy(
                full["reconstruction"]["conditional"]),
        },
        "coverage_i": copy.deepcopy(full["coverage_i"]),
        "coverage_j": copy.deepcopy(full["coverage_j"]),
        "maximum_standardized_oracle_discrepancy": copy.deepcopy(
            full["maximum_standardized_oracle_discrepancy"]),
    }


class V67CompletedHostileTests(unittest.TestCase):
    def assert_rejected(self, mutation):
        value = fixture()
        mutation(value)
        with self.assertRaises(V.AuditFailure):
            V.summarize_serialized_rejection(value, V.expected_thresholds())

    def test_frozen_projection_passes(self):
        summary = V.summarize_serialized_rejection(
            fixture(), V.expected_thresholds())
        self.assertEqual(summary["only_failed_hard_gate"],
                         "root_deletion_stability")
        self.assertEqual(summary["first_failed_jackknife_degree"], 1)
        self.assertEqual(summary["failed_j_z_precision_groups"], 16)

    def test_false_hard_gate_cannot_be_hidden(self):
        self.assert_rejected(lambda value:
                             value["hard_gates"].__setitem__(
                                 "root_deletion_stability", True))

    def test_failed_statistical_gate_cannot_be_hidden(self):
        self.assert_rejected(lambda value:
                             value["statistical_gates"].__setitem__(
                                 "split_rhat", True))

    def test_failed_degree_cannot_be_relabelled(self):
        self.assert_rejected(lambda value:
                             value["jackknife"]["1"].__setitem__(
                                 "relative_discrepancy_pass", True))

    def test_extension_or_pass_cannot_be_advertised(self):
        self.assert_rejected(lambda value:
                             value.__setitem__("extension_authorized", True))
        self.assert_rejected(lambda value:
                             value.__setitem__("gates_passed", True))

    def test_threshold_mutation_rejected(self):
        thresholds = V.expected_thresholds()
        thresholds["root_relative_discrepancy"] = "1"
        with self.assertRaises(V.AuditFailure):
            V.summarize_serialized_rejection(fixture(), thresholds)

    def test_coverage_maximum_must_contract_exactly(self):
        self.assert_rejected(lambda value:
                             value.__setitem__(
                                 "maximum_standardized_oracle_discrepancy",
                                 {"float_hex": "0x1.8p+3"}))


if __name__ == "__main__":
    unittest.main()
