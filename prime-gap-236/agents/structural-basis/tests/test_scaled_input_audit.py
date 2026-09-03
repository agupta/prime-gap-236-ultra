#!/usr/bin/env python3
"""Independent provenance and mutation audit for the integer-scaled D12 input."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXACT = HERE.parents[1] / "exact-integrator"
SOURCE = EXACT / "results" / "hb_c10_fullsimplex_noones_D12.json"
SCALED = EXACT / "results" / "hb_c10_fullsimplex_noones_D12_integer_scaled.json"
GENERATOR = EXACT / "make_integer_scaled_input.py"
CHECKER = EXACT / "verify_integer_scaled_input.py"

SOURCE_SHA = "719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87"
SCALED_SHA = "8650e44cace6b6d3e4eee8e1632cfd8a59cde6a48f76a8763dcfb400e49f4a93"
INTEGER_TOKEN = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")


class ScaledInputIndependentAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = SOURCE.read_bytes()
        cls.scaled_bytes = SCALED.read_bytes()
        cls.source = json.loads(cls.source_bytes)
        cls.scaled = json.loads(cls.scaled_bytes)

    def run_checker(self, candidate: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            path.write_text(json.dumps(candidate), encoding="ascii")
            return subprocess.run(
                [sys.executable, str(CHECKER), str(SOURCE), str(path)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)

    def test_hash_lcm_coefficients_and_content_independently(self):
        self.assertEqual(hashlib.sha256(self.source_bytes).hexdigest(), SOURCE_SHA)
        self.assertEqual(hashlib.sha256(self.scaled_bytes).hexdigest(), SCALED_SHA)
        original = [Fraction(token) for token in self.source["rational_vector"]]
        claimed = self.scaled["integer_scaling"]
        common = 1
        for value in original:
            common = (common // math.gcd(common, value.denominator) *
                      value.denominator)
        self.assertEqual(str(common), claimed["least_common_denominator"])
        self.assertEqual(common.bit_length(), 714)
        raw = self.scaled["rational_vector"]
        self.assertEqual(len(raw), 272)
        self.assertTrue(all(isinstance(x, str) and INTEGER_TOKEN.fullmatch(x)
                            for x in raw))
        integers = [int(x) for x in raw]
        self.assertTrue(all(value * common == integer
                            for value, integer in zip(original, integers)))
        self.assertEqual(math.gcd(*map(abs, integers)), 1)
        self.assertEqual(self.scaled["basis"], self.source["basis"])
        self.assertEqual(self.scaled["basis_dimension"], 272)

    def test_absolute_and_relative_generation_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            absolute_output = Path(directory) / "absolute.json"
            relative_output = Path(directory) / "relative.json"
            absolute = subprocess.run(
                [sys.executable, str(GENERATOR), str(SOURCE),
                 str(absolute_output)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)
            self.assertEqual(absolute.returncode, 0, absolute.stdout)
            relative = subprocess.run(
                [sys.executable, "make_integer_scaled_input.py",
                 "results/hb_c10_fullsimplex_noones_D12.json",
                 str(relative_output)],
                cwd=EXACT, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False)
            self.assertEqual(relative.returncode, 0, relative.stdout)
            self.assertEqual(absolute_output.read_bytes(), self.scaled_bytes)
            self.assertEqual(relative_output.read_bytes(), self.scaled_bytes)

    def test_checker_rejects_core_provenance_and_content_mutations(self):
        mutations = []

        bad = copy.deepcopy(self.scaled)
        bad["rational_vector"][0] = str(int(bad["rational_vector"][0]) + 1)
        mutations.append(("coefficient", bad))

        bad = copy.deepcopy(self.scaled)
        bad["integer_scaling"]["least_common_denominator"] += "0"
        mutations.append(("LCM", bad))

        bad = copy.deepcopy(self.scaled)
        bad["integer_scaling"]["source_sha256"] = "0" * 64
        mutations.append(("source SHA", bad))

        bad = copy.deepcopy(self.scaled)
        bad["integer_scaling"]["quotient_and_margin_sign_preserved"] = False
        mutations.append(("sign metadata", bad))

        bad = copy.deepcopy(self.scaled)
        bad["integer_scaling"]["unexpected"] = True
        mutations.append(("extra metadata", bad))

        bad = copy.deepcopy(self.scaled)
        bad["rational_vector"].pop()
        mutations.append(("truncated vector", bad))

        bad = copy.deepcopy(self.scaled)
        bad["basis"][0], bad["basis"][1] = bad["basis"][1], bad["basis"][0]
        mutations.append(("basis order", bad))

        for name, document in mutations:
            with self.subTest(name=name):
                result = self.run_checker(document)
                self.assertNotEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
