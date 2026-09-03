#!/usr/bin/env python3
"""Fail-closed mutation tests for the integer-scaled D12 input checker."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
CHECKER = HERE / "verify_integer_scaled_input.py"
GENERATOR = HERE / "make_integer_scaled_input.py"
SOURCE = HERE / "results" / "hb_c10_fullsimplex_noones_D12.json"
SCALED = HERE / "results" / "hb_c10_fullsimplex_noones_D12_integer_scaled.json"
SOURCE_ARG = "results/hb_c10_fullsimplex_noones_D12.json"
SCALED_ARG = "results/hb_c10_fullsimplex_noones_D12_integer_scaled.json"


class ScaledInputFailClosed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = json.loads(SCALED.read_bytes())

    def run_checker(self, document):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.json"
            candidate.write_text(json.dumps(document), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), SOURCE_ARG, str(candidate)],
                cwd=HERE, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)

    def test_positive_artifact(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), SOURCE_ARG, SCALED_ARG],
            cwd=HERE, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("INTEGER-SCALED INPUT PASS", result.stdout)

    def test_positive_artifact_with_absolute_paths(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(SOURCE), str(SCALED)],
            cwd=HERE.parent.parent.parent, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("INTEGER-SCALED INPUT PASS", result.stdout)

    def test_absolute_generator_checker_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "generated.json"
            make = subprocess.run(
                [sys.executable, str(GENERATOR), str(SOURCE), str(generated)],
                cwd=HERE.parent.parent.parent, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)
            self.assertEqual(make.returncode, 0, make.stdout)
            check = subprocess.run(
                [sys.executable, str(CHECKER), str(SOURCE), str(generated)],
                cwd=HERE.parent.parent.parent, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)
            self.assertEqual(check.returncode, 0, check.stdout)

    def test_rejects_basis_dimension_mutation(self):
        bad = copy.deepcopy(self.good)
        bad["basis_dimension"] -= 1
        self.assertNotEqual(self.run_checker(bad).returncode, 0)

    def test_rejects_decimal_integer_token(self):
        bad = copy.deepcopy(self.good)
        bad["rational_vector"][0] += ".0"
        self.assertNotEqual(self.run_checker(bad).returncode, 0)

    def test_rejects_status_mutation(self):
        bad = copy.deepcopy(self.good)
        bad["status"] = "unverified"
        self.assertNotEqual(self.run_checker(bad).returncode, 0)

    def test_rejects_form_scale_mutation(self):
        bad = copy.deepcopy(self.good)
        bad["integer_scaling"]["form_scale"] = "least_common_denominator"
        self.assertNotEqual(self.run_checker(bad).returncode, 0)

    def test_rejects_extra_key(self):
        bad = copy.deepcopy(self.good)
        bad["trusted"] = True
        self.assertNotEqual(self.run_checker(bad).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
