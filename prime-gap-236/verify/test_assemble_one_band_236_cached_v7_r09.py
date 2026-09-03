#!/usr/bin/env python3
"""Mutation tests for the total-large-count <= 9 exact assembler."""

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "assemble_one_band_236_cached_v7_r09.py"
V7_TEST = HERE.parent / "agents/audit/test_verify_cached_v7_cross_shard.py"
V6_FIXTURE = HERE.parent / "agents/audit/test_verify_fixed_v6_cross_shard.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = load("cached_v7_r09_assembler_test", SOURCE)
T7 = load("cached_v7_r09_conversion", V7_TEST)
T6 = load("cached_v7_r09_fixture", V6_FIXTURE)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixture(count):
    raw = T7.to_v7(M.FULL.V7, T6.synthetic_r0(M.FULL.V7.V6))
    raw["common_r"] = count
    raw["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 14-count
    return raw


class CachedV7R09AssemblerTest(unittest.TestCase):
    def test_r0_keeps_full_value(self):
        raw = fixture(0)
        selected, full, rule = M.selected_b_shard(
            Path("r00.json"), canonical(raw), 0)
        self.assertEqual(selected, full)
        self.assertEqual(str(full), raw["scaled_b_shard"])
        self.assertEqual(rule, "all-distinguished-branches")

    def test_r9_keeps_exactly_small_distinguished_branches(self):
        raw = fixture(9)
        selected, full, rule = M.selected_b_shard(
            Path("r09.json"), canonical(raw), 9)
        block = raw["branch_values_and_fast_stats"]
        expected = 48 * (
            sum((Q(block["high"][key]) for key in M.R9_BRANCHES), Q(0)) -
            sum((Q(block["low"][key]) for key in M.R9_BRANCHES), Q(0)))
        self.assertEqual(selected, expected)
        self.assertEqual(str(full), raw["scaled_b_shard"])
        self.assertEqual(rule, "small-distinguished-only:Sdelta+Stotal")

    def test_wrong_count_and_branch_mutations_fail(self):
        raw = fixture(9)
        del raw["branch_values_and_fast_stats"]["high"]["Stotal"]
        with self.assertRaises(ValueError):
            M.selected_b_shard(Path("r09.json"), canonical(raw), 9)
        raw = fixture(9)
        with self.assertRaises(ValueError):
            M.selected_b_shard(Path("r10.json"), canonical(raw), 10)


if __name__ == "__main__":
    unittest.main()
