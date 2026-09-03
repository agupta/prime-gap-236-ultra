#!/usr/bin/env python3
"""Hostile lightweight tests for the H=Q+s*1 exact-D4 builder."""

from __future__ import annotations

import copy
import importlib.util
import os
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = (ROOT / "agents" / "exact-integrator" / "results" /
          "c10_stratum_quadratic_cappedopt_D4_exact.json")
INPUT = (ROOT / "agents" / "exact-integrator" / "results" /
         "c10_capped_D4_decimal55_vector_input.json")
SPEC = importlib.util.spec_from_file_location(
    "build_quadratic_span_contingency",
    HERE / "build_quadratic_span_contingency.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class QuadraticSpanBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.raw = MOD.read_pinned(
            SOURCE, MOD.SOURCE_SHA, "quadratic source")
        cls.parsed = MOD.parse_source(cls.raw)

    def test_exact_reconstruction_and_factor_48(self):
        result = MOD.reconstruct(self.parsed, Fraction(1))
        self.assertEqual(len(result["h"]), 96)
        for r in range(16):
            self.assertEqual(
                result["h"][6 * r], self.parsed["vector"][6 * r] + 1)
            self.assertEqual(
                result["h"][6 * r + 1:6 * r + 6],
                self.parsed["vector"][6 * r + 1:6 * r + 6])
        unscaled = Fraction(0)
        q = self.parsed["vector"]
        for (left, right), value in self.parsed["j_entries"].items():
            i, j = 6 * left[0] + left[1], 6 * right[0] + right[1]
            unscaled += value * q[i] * q[j] * (1 if i == j else 2)
        self.assertEqual(48 * unscaled, self.parsed["source_numerator"])
        self.assertNotEqual(unscaled, self.parsed["source_numerator"])
        self.assertTrue(result["block_sparse_bitwise_equal"])
        self.assertTrue(result["polarization_identity_exact"])
        stationary = MOD.d4_span_stationary(result)
        self.assertEqual(len(stationary["ranked_projective_points"]), 3)
        self.assertEqual(stationary["maximum_point"]["point"], "finite")

    def test_channel_null_and_scale_mutations_reject(self):
        mutated = copy.deepcopy(self.raw)
        mutated["channel_powers"][1], mutated["channel_powers"][2] = (
            mutated["channel_powers"][2], mutated["channel_powers"][1])
        with self.assertRaises(ValueError):
            MOD.parse_source(mutated)

        mutated = copy.deepcopy(self.raw)
        mutated["quadratic_labels"][1] = [0, "Z"]
        with self.assertRaises(ValueError):
            MOD.parse_source(mutated)

        mutated = copy.deepcopy(self.raw)
        mutated["rational_vector"][1] = "1"
        with self.assertRaises(ValueError):
            MOD.parse_source(mutated)

        with self.assertRaises(ValueError):
            MOD.construct_h(self.parsed, Fraction(0))
        with self.assertRaises(ValueError):
            MOD.construct_h(self.parsed, Fraction(1 << 129))
        shifted = MOD.construct_h(self.parsed, Fraction(2))[1]
        self.assertEqual(shifted[0], 2 + self.parsed["vector"][0])
        with self.assertRaises(ValueError):
            MOD.canonical_fraction("01", "s")
        with self.assertRaises(ValueError):
            MOD.canonical_fraction(True, "s")

    def test_form_and_source_byte_mutations_reject(self):
        mutated = copy.deepcopy(self.raw)
        mutated["numerator"] = str(
            Fraction(mutated["numerator"]) / 48)
        parsed = MOD.parse_source(mutated)
        with self.assertRaises(ValueError):
            MOD.reconstruct(parsed)

        mutated = copy.deepcopy(self.raw)
        first_key = next(iter(mutated["j_entries"]))
        mutated["j_entries"][first_key] = str(
            Fraction(mutated["j_entries"][first_key]) + 1)
        parsed = MOD.parse_source(mutated)
        with self.assertRaises(ValueError):
            MOD.reconstruct(parsed)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            data = SOURCE.read_bytes()
            path.write_bytes(data)
            MOD.read_pinned(path, MOD.SOURCE_SHA, "temporary source")
            path.write_bytes(data + b"\n")
            with self.assertRaises(ValueError):
                MOD.read_pinned(path, MOD.SOURCE_SHA, "temporary source")

    def test_duplicate_json_alias_and_output_reservation(self):
        with self.assertRaises(ValueError):
            MOD.strict_json(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError):
            MOD.main([
                "--source", str(SOURCE),
                "--expect-source-sha256", MOD.SOURCE_SHA,
                "--input", str(INPUT),
                "--expect-input-sha256", MOD.INPUT_SHA,
                "--constant-scale-s", "1",
                "--output", str(SOURCE),
            ])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "occupied.json"
            output.write_text("foreign\n")
            with self.assertRaises(FileExistsError):
                MOD.reserve_output(output)
            self.assertEqual(output.read_text(), "foreign\n")

            fresh = Path(directory) / "fresh.json"
            fd, identity = MOD.reserve_output(fresh)
            try:
                data = b'{"ok":true}\n'
                MOD.publish_reserved(fd, fresh, identity, data)
                self.assertEqual(fresh.read_bytes(), data)
            finally:
                os.close(fd)


if __name__ == "__main__":
    unittest.main()
