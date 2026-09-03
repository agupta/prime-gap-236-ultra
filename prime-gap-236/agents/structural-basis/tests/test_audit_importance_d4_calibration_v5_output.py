#!/usr/bin/env python3

"""Pre-completion tests for the v5 production-output auditor.

These tests never open the production result or its record directory.
"""

import importlib
import hashlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
AUDIT = importlib.import_module(
    "audit_importance_d4_calibration_v5_output")


class CompletedOutputAuditorTests(unittest.TestCase):
    def test_frozen_nonproduction_inputs_and_decision_table(self):
        self.assertEqual(AUDIT.sha256_file(AUDIT.DRIVER),
                         AUDIT.DRIVER_SHA256)
        self.assertEqual(AUDIT.sha256_file(AUDIT.GATE),
                         AUDIT.GATE_SHA256)
        self.assertEqual(AUDIT.sha256_file(AUDIT.AUTHORIZATION),
                         AUDIT.AUTHORIZATION_SHA256)
        self.assertEqual(AUDIT.sha256_file(AUDIT.DECISION_TABLE),
                         AUDIT.DECISION_TABLE_SHA256)
        table = AUDIT.load_decision_table()
        self.assertEqual(
            [row["decision"] for row in table["ordered_rules"]],
            list(AUDIT.DECISION_EXIT_CODES))

    def test_decision_classification_is_ordered_and_fail_closed(self):
        self.assertEqual(AUDIT.classify(
            {"gates_passed": True, "extension_authorized": True}, None),
            "CALIBRATION_PASS")
        self.assertEqual(AUDIT.classify(
            {"gates_passed": False, "extension_authorized": True}, None),
            "EXTENSION_ELIGIBLE")
        self.assertEqual(AUDIT.classify(
            {"gates_passed": False, "extension_authorized": False}, None),
            "CALIBRATION_RETIRED")
        self.assertEqual(AUDIT.classify(
            None, {"exception_type": "ArithmeticError", "message": "x"}),
            "IMPLEMENTATION_REJECTED")
        with self.assertRaises(ValueError):
            AUDIT.classify(None, None)
        with self.assertRaises(ValueError):
            AUDIT.classify(
                {"gates_passed": True, "extension_authorized": False},
                {"exception_type": "forged"})

    def test_completion_sha_is_required_before_any_input_read(self):
        with mock.patch.object(
                AUDIT, "load_decision_table",
                side_effect=AssertionError("must not read inputs")):
            for malformed in ("", "A" * 64, "0" * 63, True, 17):
                with self.assertRaises(ValueError):
                    AUDIT.audit_completed_output(
                        malformed, "0" * 64, "unused-output.json")

    def test_expected_self_hash_precedes_production_and_detects_mutation(self):
        with mock.patch.object(
                AUDIT, "load_decision_table",
                side_effect=AssertionError("must not read production")):
            with self.assertRaisesRegex(ValueError, "external trust root"):
                AUDIT.audit_completed_output(
                    "0" * 64, "f" * 64, "unused-output.json")
        with tempfile.TemporaryDirectory() as directory:
            stand_in = Path(directory) / "auditor.py"
            stand_in.write_bytes(b"frozen-auditor")
            expected = hashlib.sha256(stand_in.read_bytes()).hexdigest()
            with mock.patch.object(AUDIT, "HERE", stand_in):
                self.assertEqual(
                    AUDIT.validate_expected_auditor_sha256(expected), expected)
                stand_in.write_bytes(b"mutated-after-production-read")
                with self.assertRaisesRegex(ValueError, "changed after"):
                    AUDIT.require_auditor_unchanged(expected)

    def test_fake_preloaded_local_module_is_rejected(self):
        name = "importance_statistics"
        self.assertNotIn(name, sys.modules)
        sys.modules[name] = types.ModuleType(name)
        try:
            with self.assertRaisesRegex(ValueError,
                                        "preloaded computational"):
                AUDIT.load_frozen_driver()
        finally:
            del sys.modules[name]

    def test_audit_output_cannot_modify_record_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "records"
            records.mkdir()
            for index in range(3):
                (records / f"record-{index}.json").write_text(
                    json.dumps({"index": index}))
            before = sorted((path.name, path.read_bytes())
                            for path in records.iterdir())
            with mock.patch.object(AUDIT, "RECORD_DIRECTORY", records):
                with self.assertRaisesRegex(ValueError, "record directory"):
                    AUDIT.validate_audit_output_path(records / "audit.json")
                outside = AUDIT.validate_audit_output_path(
                    root / "audit.json")
                descriptor = os.open(
                    outside, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(descriptor)
            after = sorted((path.name, path.read_bytes())
                           for path in records.iterdir())
            self.assertEqual(after, before)

    def test_strict_json_rejects_duplicate_float_and_nonfinite(self):
        for data in (b'{"x":1,"x":2}', b'{"x":1.25}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                AUDIT.strict_json_bytes(data, "hostile fixture")
        self.assertEqual(AUDIT.strict_json_bytes(
            b'{"x":"0x1.0p+0"}', "exact fixture"),
            {"x": "0x1.0p+0"})

    def test_frozen_driver_and_gate_load_without_production_paths(self):
        driver = AUDIT.load_frozen_driver()
        gate = driver.load_and_validate_gate(AUDIT.GATE)
        self.assertEqual(gate["sha256"], AUDIT.GATE_SHA256)
        self.assertFalse(gate["gate"]["production_launch_authorized"])
        # The frozen publisher normalizes ``extra_hashes`` twice.  A bare
        # SHA string becomes a one-key dictionary and is rejected on the
        # second pass.  The completed-output consumer must therefore pass
        # stable three-key inode bindings for every dynamic file.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dependency = root / "dynamic-input.txt"
            dependency.write_bytes(b"stable dynamic closure")
            snapshot = driver.read_file_snapshot(dependency)
            output = root / "real-publisher-regression.json"
            digest = driver.write_new_result(
                output, {"status": "exact-three-key-closure-regression"},
                gate["gate"], extra_hashes={
                    str(dependency.resolve()): driver.inode_binding(snapshot),
                })
            self.assertEqual(driver.sha256_file(output), digest)

            rejected = root / "one-key-normalization-regression.json"
            with self.assertRaisesRegex(ValueError,
                                        "malformed extra hash binding"):
                driver.write_new_result(
                    rejected, {"status": "must-reject-one-key-closure"},
                    gate["gate"], extra_hashes={
                        str(dependency.resolve()): snapshot["sha256"],
                    })
            self.assertEqual(
                rejected.read_bytes(),
                b'{"status":"rejected-incomplete-calibration-output"}\n')


if __name__ == "__main__":
    unittest.main()
