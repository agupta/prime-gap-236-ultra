#!/usr/bin/env python3
"""Hostile independent tests for the fixed-polygon-v8 R<=9 wrapper."""

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
REPO = HERE.parents[1]
SOURCE = REPO / "verify/assemble_one_band_236_fixed_polygon_v8_r09.py"
SOURCE_SHA256 = \
    "67c479a18b12f7e5d4df84a854dd8364f981ecdbcfd2daf2fd256edb2029b557"
V8_FIXTURES = HERE / "test_verify_fixed_polygon_v8_cross_shard.py"
V7_FIXTURES = HERE / "test_verify_cached_v7_cross_shard.py"
V6_FIXTURES = HERE / "test_verify_fixed_v6_cross_shard.py"


def digest(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if digest(SOURCE) != SOURCE_SHA256:
    raise RuntimeError("frozen fixed-polygon-v8 R<=9 wrapper changed")
M = load("independent_fixed_polygon_v8_Rle9_wrapper", SOURCE)
T8 = load("independent_fixed_polygon_v8_fixture", V8_FIXTURES)
T7 = load("independent_cached_v7_fixture_for_v8", V7_FIXTURES)
T6 = load("independent_fixed_v6_fixture_for_v8", V6_FIXTURES)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixture(count):
    raw = T8.to_v8(M.V8, T7.to_v7(M.V8.V7, T6.synthetic_r0(M.V8.V7.V6)))
    raw["common_r"] = count
    raw["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 14-count
    return raw


class FixedPolygonV8Rle9WrapperAudit(unittest.TestCase):
    def test_flat_runtime_closure_is_exact_and_live(self):
        required = {
            M.R09_ASSEMBLER: M.R09_ASSEMBLER_SHA256,
            M.V8_CHECKER: M.V8_CHECKER_SHA256,
            M.V8_CHECKER_TEST: M.V8_CHECKER_TEST_SHA256,
            M.V8_RUNNER: M.V8_RUNNER_SHA256,
        }
        for relative, expected in M.V8.SOURCE_HASHES.items():
            required[M.REPO / relative] = expected
        for path, expected in required.items():
            self.assertEqual(M.PINS.get(path), expected, str(path))
        for path, expected in M.R09.PINS.items():
            self.assertEqual(M.PINS.get(path), expected, str(path))
        self.assertEqual(len(M.PINS), len(set(M.PINS)))
        for path, expected in M.PINS.items():
            self.assertEqual(digest(path), expected, str(path))

    def test_parser_audits_supplied_bytes_not_live_name(self):
        good = fixture(9)
        good_data = canonical(good)
        with tempfile.TemporaryDirectory(prefix="v8-r09-byte-snapshot-") as text:
            path = Path(text) / "common_r_09.json"
            path.write_bytes(b"not-json\n")
            value = M.parse_b_v8(path, good_data, 9)
            self.assertEqual(value, Q(good["scaled_b_shard"]))
            self.assertEqual(path.read_bytes(), b"not-json\n")

    def test_exact_r9_branch_projection_uses_v8_audited_record(self):
        raw = fixture(9)
        block = raw["branch_values_and_fast_stats"]
        block["high"].update({
            "Sdelta": "101/7", "Stotal": "103/11",
            "Ltotal": "1000001", "Lbig": "-1000000",
        })
        block["low"].update({
            "Sdelta": "107/13", "Stotal": "109/17",
            "Ltotal": "-2000000", "Lbig": "2000001",
        })
        # Restore the full factor-48 identity required by the structural
        # checker after independently assigning all eight branch values.
        raw["scaled_b_shard"] = str(M.B.K * (
            sum(map(Q, block["high"].values())) -
            sum(map(Q, block["low"].values()))))
        data = canonical(raw)
        old = M.R09.FULL.parse_b_shard
        try:
            M.R09.FULL.parse_b_shard = M.parse_b_v8
            selected, full, rule = M.R09.selected_b_shard(
                Path("ignored-live-name.json"), data, 9)
        finally:
            M.R09.FULL.parse_b_shard = old
        expected = M.B.K * (
            Q(block["high"]["Sdelta"]) + Q(block["high"]["Stotal"]) -
            Q(block["low"]["Sdelta"]) - Q(block["low"]["Stotal"]))
        self.assertEqual(selected, expected)
        self.assertEqual(full, Q(raw["scaled_b_shard"]))
        self.assertEqual(rule, "small-distinguished-only:Sdelta+Stotal")

    def test_parser_is_restored_when_wrapped_build_raises(self):
        original = M.R09.FULL.parse_b_shard
        with tempfile.TemporaryDirectory(prefix="v8-r09-restore-") as text:
            root = Path(text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"frozen\n")
            with mock.patch.object(M, "PINS", {dependency: digest(dependency)}), \
                    mock.patch.object(M.R09, "build", side_effect=ArithmeticError("x")):
                with self.assertRaises(ArithmeticError):
                    M.main([
                        "--a-dir", text, "--b-dir", text,
                        "--output", str(root / "out.json"),
                        "--expected-self-sha256", SOURCE_SHA256,
                    ])
        self.assertIs(M.R09.FULL.parse_b_shard, original)

    def test_dependency_mutation_fails_before_publication_and_restores(self):
        original = M.R09.FULL.parse_b_shard
        with tempfile.TemporaryDirectory(prefix="v8-r09-toctou-") as text:
            root = Path(text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"frozen\n")
            output = root / "out.json"

            def mutate(*_args):
                self.assertIs(M.R09.FULL.parse_b_shard, M.parse_b_v8)
                dependency.write_bytes(b"changed\n")
                return {"theorem_ready_scalar": True}

            with mock.patch.object(M, "PINS", {dependency: digest(dependency)}), \
                    mock.patch.object(M.R09, "build", side_effect=mutate):
                with self.assertRaises(RuntimeError):
                    M.main([
                        "--a-dir", text, "--b-dir", text,
                        "--output", str(output),
                        "--expected-self-sha256", SOURCE_SHA256,
                    ])
            self.assertFalse(output.exists())
        self.assertIs(M.R09.FULL.parse_b_shard, original)

    def test_no_assert_or_dynamic_execution_in_wrapper(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("assert ", text)
        self.assertNotIn("eval(", text)
        self.assertNotIn("exec(", text)


if __name__ == "__main__":
    unittest.main()
