#!/usr/bin/env python3
"""Lightweight prelaunch tests; never run the D4 exact traversal."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check_stratum_moment_d4_degree3.py"
GATE = HERE / "results/c10_D4_degree3_moment_prelaunch_gate.json"


def load_module():
    spec = importlib.util.spec_from_file_location("d4d3", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DegreeThreePrelaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_tag_counts_and_gate(self):
        gate, digest, raw = self.mod.load_gate(GATE)
        self.assertEqual(len(digest), 64)
        self.assertEqual(raw, GATE.read_bytes())
        self.assertEqual(gate["expected_counts"], self.mod.EXPECTED_COUNTS)
        self.assertEqual(self.mod.TAG_SCHEMA_SHA,
                         self.mod.canonical_schema_sha256(3))

    def test_preflight_is_reproducible_and_production_needs_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            base = [sys.executable, str(SCRIPT), "--gate", str(GATE),
                    "--mode", "preflight"]
            subprocess.run(base + ["--output", str(first)], check=True,
                           stdout=subprocess.PIPE, text=True)
            subprocess.run(base + ["--output", str(second)], check=True,
                           stdout=subprocess.PIPE, text=True)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            raw = json.loads(first.read_bytes())
            self.assertFalse(raw["production_run_performed"])
            failed = subprocess.run(
                [sys.executable, str(SCRIPT), "--gate", str(GATE),
                 "--mode", "production", "--output",
                 str(Path(directory) / "forbidden.json")],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertNotEqual(failed.returncode, 0)

    def test_gate_mutation_and_output_alias_reject(self):
        gate = json.loads(GATE.read_bytes())
        gate["expected_counts"]["j_scalar_moment_integrals"] -= 1
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"
            bad.write_text(json.dumps(gate))
            with self.assertRaises(ValueError):
                self.mod.load_gate(bad)
        failed = subprocess.run(
            [sys.executable, str(SCRIPT), "--gate", str(GATE),
             "--mode", "preflight", "--output", str(GATE)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertNotEqual(failed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
