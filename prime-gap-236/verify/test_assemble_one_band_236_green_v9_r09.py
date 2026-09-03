#!/usr/bin/env python3
"""Mutation tests for the Green-polygon-v9 R<=9 assembler wrapper."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "assemble_one_band_236_green_v9_r09.py"
GREEN_TEST = HERE.parent / "agents/audit/test_verify_green_v9_cross_shard.py"
V8_TEST = HERE.parent / "agents/audit/test_verify_fixed_polygon_v8_cross_shard.py"
V7_TEST = HERE.parent / "agents/audit/test_verify_cached_v7_cross_shard.py"
V6_TEST = HERE.parent / "agents/audit/test_verify_fixed_v6_cross_shard.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("green_v9_r09_assembler_test", SOURCE)
TG = load("green_v9_r09_conversion", GREEN_TEST)
T8 = load("green_v9_r09_v8_conversion", V8_TEST)
T7 = load("green_v9_r09_v7_fixture", V7_TEST)
T6 = load("green_v9_r09_v6_fixture", V6_TEST)


def digest(data_or_path):
    data = (data_or_path if isinstance(data_or_path, bytes)
            else data_or_path.read_bytes())
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixture(count):
    v7 = T7.to_v7(M.GREEN.V8.V7, T6.synthetic_r0(M.GREEN.V8.V7.V6))
    v8 = T8.to_v8(M.GREEN.V8, v7)
    raw = TG.to_v9(M.GREEN, v8)
    raw["common_r"] = count
    raw["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 14-count
    return raw


class GreenV9R09AssemblerTest(unittest.TestCase):
    def test_real_green_audit_parser_and_r9_selection(self):
        raw = fixture(9)
        data = canonical(raw)
        full = M.parse_b_green(Path("common_r_09.json"), data, 9)
        self.assertEqual(full, Q(raw["scaled_b_shard"]))
        old = M.R09.FULL.parse_b_shard
        try:
            M.R09.FULL.parse_b_shard = M.parse_b_green
            selected, parsed_full, rule = M.R09.selected_b_shard(
                Path("common_r_09.json"), data, 9)
        finally:
            M.R09.FULL.parse_b_shard = old
        block = raw["branch_values_and_fast_stats"]
        expected = M.B.K * (
            sum((Q(block["high"][name]) for name in M.R09.R9_BRANCHES), Q(0)) -
            sum((Q(block["low"][name]) for name in M.R09.R9_BRANCHES), Q(0)))
        self.assertEqual(selected, expected)
        self.assertEqual(parsed_full, full)
        self.assertEqual(rule, "small-distinguished-only:Sdelta+Stotal")

    def test_green_identity_count_and_scalar_mutations_fail(self):
        raw = fixture(4)
        mutant = copy.deepcopy(raw)
        mutant["algorithm"]["polygon_convex_cyclic_order_checked"] = False
        with self.assertRaises(ValueError):
            M.parse_b_green(Path("common_r_04.json"), canonical(mutant), 4)
        with self.assertRaises((ValueError, ArithmeticError)):
            M.parse_b_green(Path("common_r_03.json"), canonical(raw), 3)
        mutant = copy.deepcopy(raw)
        mutant["scaled_b_shard"] = "0"
        with self.assertRaises((ValueError, ArithmeticError)):
            M.parse_b_green(Path("common_r_04.json"), canonical(mutant), 4)

    def test_flat_source_closure_and_main_restores_parser(self):
        for path, expected in M.PINS.items():
            self.assertEqual(digest(path), expected, str(path))
        source_sha = digest(SOURCE)
        with tempfile.TemporaryDirectory(prefix="green-v9-r09-main-") as root_text:
            root = Path(root_text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"frozen\n")
            output = root / "aggregate.json"
            original_parser = M.R09.FULL.parse_b_shard
            arguments = [
                "--a-dir", str(root), "--b-dir", str(root),
                "--output", str(output),
                "--expected-self-sha256", source_sha,
            ]
            with mock.patch.object(M, "PINS", {dependency: digest(dependency)}), \
                    mock.patch.object(M, "REPO", root), \
                    mock.patch.object(
                        M.R09, "build",
                        return_value={"theorem_ready_scalar": True}):
                self.assertEqual(M.main(arguments), 0)
            self.assertIs(M.R09.FULL.parse_b_shard, original_parser)
            result = json.loads(output.read_bytes())
            self.assertEqual(result["assembler_sha256"], source_sha)
            self.assertEqual(
                result["b_engine"],
                "green-v9-with-Rle9-branch-projection")
            self.assertEqual(
                result["source_hashes"], {"dependency.py": digest(dependency)})


if __name__ == "__main__":
    unittest.main()
