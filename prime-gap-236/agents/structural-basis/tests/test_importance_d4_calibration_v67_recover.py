#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np


HERE = Path(__file__).resolve()
SOURCE = HERE.parents[1] / "code/importance_d4_calibration_v67_recover.py"
_spec = importlib.util.spec_from_file_location(
    "importance_v67_recovery_tested", SOURCE)
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)
V5 = R.V5


class ImportanceV67RecoveryTests(unittest.TestCase):
    def test_numpy_bool_repair_is_exact_and_recursive(self):
        payload = {
            "builtin": True,
            "scalar": np.bool_(False),
            "nested": [np.bool_(True), {"x": np.bool_(False)}],
            "array": np.asarray([True, False], dtype=bool),
        }
        safe = R.json_safe_v67(payload)
        self.assertIs(safe["builtin"], True)
        self.assertIs(safe["scalar"], False)
        self.assertEqual(safe["nested"], [True, {"x": False}])
        self.assertEqual(safe["array"], [True, False])
        self.assertEqual(R.numpy_bool_paths(payload), [
            "$.scalar", "$.nested[0]", "$.nested[1].x",
            "$.array[0]", "$.array[1]",
        ])

    def test_numpy_bool_is_the_legacy_displayed_bool_failure(self):
        # This exactly explains the v6.6 traceback text: NumPy calls its
        # scalar type ``bool``, while it is not a builtin bool/int.
        value = np.bool_(True)
        self.assertEqual(type(value).__name__, "bool")
        self.assertNotIsInstance(value, (bool, int))
        with self.assertRaisesRegex(TypeError,
                                    "cannot serialize value of type bool"):
            R.LEGACY_JSON_SAFE(value)

    def test_other_unknown_types_still_fail_closed(self):
        with self.assertRaises(TypeError):
            R.json_safe_v67(object())
        self.assertEqual(R.json_safe_v67(Fraction(2, 3)), "2/3")
        nonfinite = R.json_safe_v67([math.inf, -math.inf, math.nan])
        self.assertEqual(nonfinite, [
            {"nonfinite_float": "positive-infinity"},
            {"nonfinite_float": "negative-infinity"},
            {"nonfinite_float": "nan"},
        ])

    def test_builder_rejects_alias_existing_and_record_descendant(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "records"
            records.mkdir()
            target = root / "result.json"
            authority = root / "authority.json"
            self.assertEqual(
                R.validate_recovery_paths(
                    target, authority, records),
                (target.resolve(), authority.resolve()))
            with self.assertRaises(ValueError):
                R.validate_recovery_paths(target, target, records)
            with self.assertRaises(ValueError):
                R.validate_recovery_paths(
                    target, records / "authority.json", records)
            target.write_text("occupied")
            with self.assertRaises(FileExistsError):
                R.validate_recovery_paths(
                    target, authority, records)

    def test_real_publisher_accepts_nested_numpy_bool(self):
        previous = V5._json_safe
        V5._json_safe = R.json_safe_v67
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "boolean.json"
                digest = V5.write_new_result(
                    output, {"gate": np.bool_(True)},
                    {"source_hashes": {}, "data_hashes": {}},
                    extra_hashes={})
                self.assertEqual(digest, R.sha256_file(output))
                self.assertEqual(json.loads(output.read_text()),
                                 {"gate": True})
                with self.assertRaises(FileExistsError):
                    V5.write_new_result(
                        output, {"gate": False},
                        {"source_hashes": {}, "data_hashes": {}},
                        extra_hashes={})
        finally:
            V5._json_safe = previous

    def test_external_self_hash_precedes_completed_input_open(self):
        called = []
        with mock.patch.object(
                R, "open_completed_v66_inputs",
                side_effect=lambda: called.append(True)):
            with mock.patch.object(sys, "argv", [
                    str(R.FILE), "--expected-recovery-sha256", "0" * 64,
                    "--authorization", "unused", "--output", "unused"]):
                with self.assertRaises(SystemExit):
                    R.main()
        self.assertEqual(called, [])

    def test_preloaded_local_module_is_rejected_in_fresh_process(self):
        command = (
            "import importlib.util,pathlib,sys,types;"
            "sys.modules['importance_statistics']=types.ModuleType('x');"
            f"p=pathlib.Path({str(SOURCE)!r});"
            "s=importlib.util.spec_from_file_location('hostile_v67',p);"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)")
        completed = subprocess.run(
            [sys.executable, "-c", command], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("preloaded local modules: importance_statistics",
                      completed.stderr)

    def test_frozen_v66_inputs_and_predecessor_regressions(self):
        self.assertEqual(R.sha256_file(R.V66_PATH), R.PINNED_V66_SHA256)
        self.assertEqual(R.sha256_file(R.V66_GATE),
                         R.PINNED_V66_GATE_SHA256)
        self.assertEqual(R.sha256_file(R.V66_AUTHORIZATION),
                         R.PINNED_V66_AUTHORIZATION_SHA256)
        self.assertEqual(R.V66_REJECTED_OUTPUT.read_bytes(),
                         R.PINNED_V66_REJECTED_BYTES)
        self.assertTrue(R.V66.validate_v65_failure_artifacts())

    def test_completed_fixture_replays_without_chain_execution(self):
        # Exact completed-fixture regression: every checkpoint is reopened by
        # its held directory descriptor and the v6.6 validator.  The reduced
        # no-jackknife analysis is sufficient to expose the serializer type;
        # production recovery recomputes the full frozen jackknife analysis.
        context = R.open_completed_v66_inputs()
        try:
            with mock.patch.object(
                    V5, "run_one_chain",
                    side_effect=AssertionError("chain execution forbidden")):
                loaded, oracle, adapter, weights = \
                    R.load_completed_checkpoints(context)
                self.assertEqual(len(loaded), 128)
                analysis = R.V6.analyze_records(
                    [item["record"] for item in loaded], oracle, weights,
                    context["gate"]["schedule"], adapter=adapter,
                    do_jackknife=False)
            paths = R.numpy_bool_paths(analysis)
            self.assertEqual(paths, list(R.EXPECTED_NUMPY_BOOL_PATHS))
            encoded = json.dumps(R.json_safe_v67(analysis),
                                 allow_nan=False)
            self.assertIsInstance(encoded, str)
        finally:
            V5.close_bound_directory(context["directory"])


if __name__ == "__main__":
    unittest.main()
