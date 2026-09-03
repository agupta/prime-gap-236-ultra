#!/usr/bin/env python3
"""Tests for strict exact D14 one-band A assembly."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / (
    "agents/structural-basis/code/assemble_exact_d14_one_band_a_v1.py")


def load_source():
    spec = importlib.util.spec_from_file_location(
        "test_assemble_exact_d14_one_band_a_v1_source", SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load_source()


class AssembleExactD14OneBandATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = M.build_aggregate()

    def test_exact_aggregate_identity_and_positivity(self):
        row = self.result
        self.assertEqual(row["status"],
                         "EXACT D14 ONE-BAND A AGGREGATE PASS")
        scaled = Q(row["exact_A_scaled"])
        unscaled = Q(row["exact_A_unscaled"])
        self.assertGreater(scaled, 0)
        self.assertEqual(scaled, 10**76 * unscaled)
        self.assertEqual(len(row["counts"]), 13)
        self.assertEqual([item["count"] for item in row["counts"]],
                         list(range(13)))
        self.assertTrue(all(row["checks"].values()))

    def test_every_shard_and_static_dependency_is_hash_pinned(self):
        for count, expected in M.SHARD_SHA256.items():
            path = M.SHARD_DIRECTORY / f"r{count:02d}.json"
            self.assertEqual(M.sha256(path), expected)
        M.validate_static_pins()
        self.assertFalse(self.result["b_launch_authorized"])
        self.assertFalse(self.result["resume_supported"])

    def test_deterministic_and_strict_json(self):
        first = M.canonical_json(self.result)
        second = M.canonical_json(M.build_aggregate())
        self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            M.strict_json_bytes(b'{"a":1,"a":2}\n', "duplicate")
        with self.assertRaises(ValueError):
            M.strict_json_bytes(b'{"a":NaN}\n', "nonfinite")
        with self.assertRaises(ValueError):
            M.canonical_q("2/4")


if __name__ == "__main__":
    unittest.main()
