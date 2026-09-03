#!/usr/bin/env python3

from __future__ import annotations

import ast
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = REPO / "agents/structural-basis/code/importance_d4_calibration_v67_recover.py"
BUILDER = REPO / "agents/structural-basis/code/build_importance_d4_calibration_v67_recovery_authorization.py"
TEMPLATE = REPO / "agents/structural-basis/results/importance_d4_calibration_v67_recovery_authorization_template.json"
spec = importlib.util.spec_from_file_location("hostile_v67_recovery", SOURCE)
R = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = R
spec.loader.exec_module(R)


class V67RecoveryHostileTests(unittest.TestCase):
    def test_template_cannot_authorize(self):
        raw = json.loads(TEMPLATE.read_bytes())
        target = Path(raw["output_parent_binding"]["path"]) / raw["output_leaf"]
        with self.assertRaises(ValueError):
            R.preflight_recovery_authorization(
                TEMPLATE, target, R.sha256_file(SOURCE))
        self.assertFalse(target.exists())

    def test_external_wrong_self_hash_precedes_records(self):
        command = [
            sys.executable, str(SOURCE), "--expected-recovery-sha256",
            "0" * 64, "--authorization", str(TEMPLATE),
            "--output", "/tmp/forbidden-v67-recovery.json"]
        completed = subprocess.run(
            command, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not match external SHA-256", completed.stderr)

    def test_numpy_bool_is_only_new_serializer_case(self):
        examples = [None, True, 7, "x", 0.5, (1, 2), [3], {"x": 4},
                    np.asarray([1, 2]), math.inf, -math.inf, math.nan]
        for value in examples:
            self.assertEqual(R.json_safe_v67(value), R.LEGACY_JSON_SAFE(value))
        with self.assertRaises(TypeError):
            R.LEGACY_JSON_SAFE(np.bool_(True))
        self.assertIs(R.json_safe_v67(np.bool_(True)), True)
        with self.assertRaises(TypeError):
            R.json_safe_v67(object())

    def test_builder_and_recovery_have_no_chain_call(self):
        forbidden = {"run_one_chain", "extend_one_chain",
                     "run_fresh_initial_chain", "run_fresh_extended_chain",
                     "run_smoke"}
        for path in (SOURCE, BUILDER):
            tree = ast.parse(path.read_text())
            calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    function = node.func
                    name = (function.id if isinstance(function, ast.Name) else
                            function.attr if isinstance(function, ast.Attribute)
                            else None)
                    if name in forbidden:
                        calls.append((name, node.lineno))
            self.assertEqual(calls, [])

    def test_paths_reject_alias_existing_and_record_descendant(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "records"
            records.mkdir()
            target, authority = root / "target", root / "authority"
            self.assertEqual(R.validate_recovery_paths(
                target, authority, records),
                (target.resolve(), authority.resolve()))
            with self.assertRaises(ValueError):
                R.validate_recovery_paths(target, target, records)
            with self.assertRaises(ValueError):
                R.validate_recovery_paths(
                    target, records / "authority", records)
            target.write_text("occupied")
            with self.assertRaises(FileExistsError):
                R.validate_recovery_paths(target, authority, records)

    def test_preloaded_runtime_module_fails_fresh_import(self):
        command = (
            "import importlib.util,pathlib,sys,types;"
            "sys.modules['importance_statistics']=types.ModuleType('bad');"
            f"p=pathlib.Path({str(SOURCE)!r});"
            "s=importlib.util.spec_from_file_location('x',p);"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)")
        completed = subprocess.run(
            [sys.executable, "-c", command], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("preloaded local modules: importance_statistics",
                      completed.stderr)


if __name__ == "__main__":
    unittest.main()
