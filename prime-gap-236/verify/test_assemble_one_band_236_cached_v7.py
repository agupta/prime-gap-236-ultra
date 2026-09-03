#!/usr/bin/env python3
"""Small mutation tests for the cached-v7 scalar assembler wrapper."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "assemble_one_band_236_cached_v7.py"
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


M = load("cached_v7_assembler_test", SOURCE)
T7 = load("cached_v7_assembler_conversion", V7_TEST)
T6 = load("cached_v7_assembler_fixture", V6_FIXTURE)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixture():
    return T7.to_v7(M.V7, T6.synthetic_r0(M.V7.V6))


class CachedV7AssemblerTest(unittest.TestCase):
    def test_exact_snapshot_passes(self):
        row = fixture()
        value = M.parse_b_shard(Path("r00.json"), canonical(row), 0)
        self.assertEqual(str(value), row["scaled_b_shard"])

    def test_factor_and_cache_mutations_fail(self):
        row = fixture()
        row["scaled_b_shard"] = "0"
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r00.json"), canonical(row), 0)
        row = fixture()
        row["branch_values_and_fast_stats"]["integer_radialization"][
            "radial_stats"]["cached_factorial_ratios"] = -1
        with self.assertRaises(ValueError):
            M.parse_b_shard(Path("r00.json"), canonical(row), 0)

    def test_wrong_count_and_noncanonical_bytes_fail(self):
        row = fixture()
        with self.assertRaises(ArithmeticError):
            M.parse_b_shard(Path("r01.json"), canonical(row), 1)
        with self.assertRaises(ValueError):
            M.parse_b_shard(Path("r00.json"), canonical(row).replace(b"\n", b" \n"), 0)


if __name__ == "__main__":
    unittest.main()
