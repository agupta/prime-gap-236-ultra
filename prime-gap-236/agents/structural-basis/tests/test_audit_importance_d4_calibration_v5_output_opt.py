#!/usr/bin/env python3

"""Pre-completion parity tests for the optimized replication consumer."""

import importlib
import sys
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
OPT = importlib.import_module(
    "audit_importance_d4_calibration_v5_output_opt")


class OptimizedOutputAuditorTests(unittest.TestCase):
    def test_replication_pins_are_exact_and_do_not_open_live_output(self):
        self.assertEqual(OPT.sha256_file(OPT.DRIVER), OPT.DRIVER_SHA256)
        self.assertEqual(OPT.sha256_file(OPT.GATE), OPT.GATE_SHA256)
        self.assertEqual(OPT.sha256_file(OPT.AUTHORIZATION),
                         OPT.AUTHORIZATION_SHA256)
        self.assertEqual(
            OPT.AUTHORIZATION.name,
            "importance_d4_calibration_v5_authorization_opt.json")
        self.assertEqual(
            OPT.PRODUCTION_RESULT.name,
            "importance_d4_calibration_v5_production_opt.json")
        self.assertEqual(
            OPT.RECORD_DIRECTORY.name,
            "importance_d4_calibration_v5_records_opt")

    def test_only_declared_run_pins_differ_from_normal_consumer(self):
        normal_path = CODE / "audit_importance_d4_calibration_v5_output.py"
        normal = normal_path.read_text()
        optimized = OPT.HERE.read_text()
        replacements = {
            "frozen D4 v5 -O replication": "frozen D4 v5 production",
            "importance_d4_calibration_v5_authorization_opt.json":
                "importance_d4_calibration_v5_authorization.json",
            "importance_d4_calibration_v5_production_opt.json":
                "importance_d4_calibration_v5_production.json",
            "importance_d4_calibration_v5_records_opt":
                "importance_d4_calibration_v5_records",
            "26f8da920c032d9fdf1f0000a65cec26894f07a47d17ba675b1f2ca2f6e117c9":
                "11f75e01e019be90be1caea052f8e6452d59f8d59bbaea9bddf5022a9bb978dd",
            "d67005ba95fc1a0435bbe8122d612393c8939b3ea6ea761416224954894227bd":
                "4e9ab0002b3f33019162d537f03310880e0ff788d48b36239957d05cb9608cf7",
        }
        for source, target in replacements.items():
            optimized = optimized.replace(source, target)
        self.assertEqual(optimized, normal)

    def test_external_completion_and_self_hashes_precede_reads(self):
        with mock.patch.object(
                OPT, "load_decision_table",
                side_effect=AssertionError("must not read live inputs")):
            with self.assertRaises(ValueError):
                OPT.audit_completed_output(
                    "bad", "0" * 64, "unused-audit.json")
            with self.assertRaisesRegex(ValueError, "external trust root"):
                OPT.audit_completed_output(
                    "0" * 64, "f" * 64, "unused-audit.json")


if __name__ == "__main__":
    unittest.main()
