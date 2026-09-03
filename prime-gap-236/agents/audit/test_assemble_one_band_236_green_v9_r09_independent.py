#!/usr/bin/env python3
"""Hostile independent tests for the frozen Green-v9 R<=9 assembler."""

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
SOURCE = REPO / "verify/assemble_one_band_236_green_v9_r09.py"
SOURCE_SHA256 = \
    "4762573e5f699f2641bb0081f571a3c34f23b47d70386f49626f9af1eef2de29"
GREEN_FIXTURES = HERE / "test_verify_green_v9_cross_shard.py"
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
    raise RuntimeError("frozen Green-v9 R<=9 wrapper changed")
M = load("independent_green_v9_Rle9_wrapper", SOURCE)
TG = load("independent_green_v9_fixture", GREEN_FIXTURES)
T8 = load("independent_v8_fixture_for_green", V8_FIXTURES)
T7 = load("independent_v7_fixture_for_green", V7_FIXTURES)
T6 = load("independent_v6_fixture_for_green", V6_FIXTURES)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def fixture(count):
    v7 = T7.to_v7(M.GREEN.V8.V7, T6.synthetic_r0(M.GREEN.V8.V7.V6))
    raw = TG.to_v9(M.GREEN, T8.to_v8(M.GREEN.V8, v7))
    raw["common_r"] = count
    raw["branch_values_and_fast_stats"]["integer_radialization"][
        "radial_stats"]["maximum_shift_pruned_inside_convolution"] = 14-count
    return raw


class GreenV9Rle9AssemblerAudit(unittest.TestCase):
    def test_flat_runtime_closure_includes_both_checker_source_maps(self):
        required = {
            M.R09_ASSEMBLER: M.R09_ASSEMBLER_SHA256,
            M.GREEN_CHECKER: M.GREEN_CHECKER_SHA256,
            M.GREEN_CHECKER_TEST: M.GREEN_CHECKER_TEST_SHA256,
            M.GREEN_RUNNER: M.GREEN_RUNNER_SHA256,
            M.GREEN.V8_CHECKER_PATH: M.GREEN.V8_CHECKER_SHA,
            M.REPO / M.GREEN.V8.PRODUCER: M.GREEN.V8.PRODUCER_SHA,
        }
        for source_map in (M.GREEN.SOURCE_HASHES,
                           M.GREEN.V8.SOURCE_HASHES):
            for relative, expected in source_map.items():
                required[M.REPO / relative] = expected
        for path, expected in M.R09.PINS.items():
            required[path] = expected
        self.assertEqual(len(M.PINS), 54)
        self.assertEqual(len(M.PINS), len(set(M.PINS)))
        for path, expected in required.items():
            self.assertEqual(M.PINS.get(path), expected, str(path))
        for path, expected in M.PINS.items():
            self.assertEqual(digest(path), expected, str(path))

    def test_parser_audits_supplied_snapshot_not_live_path(self):
        raw = fixture(9)
        data = canonical(raw)
        with tempfile.TemporaryDirectory(prefix="green-r09-byte-snapshot-") as text:
            path = Path(text) / "common_r_09.json"
            path.write_bytes(b"malformed-live-name\n")
            value = M.parse_b_green(path, data, 9)
            self.assertEqual(value, Q(raw["scaled_b_shard"]))
            self.assertEqual(path.read_bytes(), b"malformed-live-name\n")

    def test_recursive_checker_repo_reads_are_all_flat_pinned(self):
        original_read = Path.read_bytes
        seen = set()
        repo = M.REPO.resolve()

        def recording_read(path):
            resolved = path.resolve()
            try:
                resolved.relative_to(repo)
            except ValueError:
                pass
            else:
                seen.add(resolved)
            return original_read(path)

        raw = fixture(9)
        with mock.patch.object(Path, "read_bytes", recording_read):
            self.assertEqual(
                M.parse_b_green(Path("ignored.json"), canonical(raw), 9),
                Q(raw["scaled_b_shard"]))
        self.assertTrue(seen)
        self.assertEqual(seen - set(M.PINS), set())

    def test_exact_count_projection_and_high_minus_low_orientation(self):
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
        raw["scaled_b_shard"] = str(M.B.K * (
            sum(map(Q, block["high"].values())) -
            sum(map(Q, block["low"].values()))))
        data = canonical(raw)
        original = M.R09.FULL.parse_b_shard
        try:
            M.R09.FULL.parse_b_shard = M.parse_b_green
            selected, full, rule = M.R09.selected_b_shard(
                Path("ignored-live-name.json"), data, 9)
        finally:
            M.R09.FULL.parse_b_shard = original
        expected = M.B.K * (
            Q(block["high"]["Sdelta"]) + Q(block["high"]["Stotal"]) -
            Q(block["low"]["Sdelta"]) - Q(block["low"]["Stotal"]))
        self.assertEqual(selected, expected)
        self.assertEqual(full, Q(raw["scaled_b_shard"]))
        self.assertEqual(rule, "small-distinguished-only:Sdelta+Stotal")

        for count in (0, 8):
            raw = fixture(count)
            data = canonical(raw)
            original = M.R09.FULL.parse_b_shard
            try:
                M.R09.FULL.parse_b_shard = M.parse_b_green
                selected, full, rule = M.R09.selected_b_shard(
                    Path("ignored.json"), data, count)
            finally:
                M.R09.FULL.parse_b_shard = original
            self.assertEqual(selected, Q(raw["scaled_b_shard"]))
            self.assertEqual(selected, full)
            self.assertEqual(rule, "all-distinguished-branches")

    def test_mixed_file_inventory_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="green-r09-inventory-") as text:
            root = Path(text)
            for count in range(10):
                (root / f"common_r_{count:02d}.json").write_bytes(b"x\n")
            paths = M.R09.require_mixed_files(root)
            self.assertEqual([path.name for path in paths],
                             [f"common_r_{count:02d}.json" for count in range(10)])
            (root / "common_r_09.json").unlink()
            with self.assertRaises(ValueError):
                M.R09.require_mixed_files(root)
            (root / "common_r_09.json").symlink_to(root / "common_r_08.json")
            with self.assertRaises(ValueError):
                M.R09.require_mixed_files(root)
            (root / "common_r_09.json").unlink()
            (root / "common_r_09.json").write_bytes(b"x\n")
            (root / "common_r_10.json").write_bytes(b"x\n")
            with self.assertRaises(ValueError):
                M.R09.require_mixed_files(root)

    def test_parser_restoration_and_source_toctou_failure(self):
        original = M.R09.FULL.parse_b_shard
        with tempfile.TemporaryDirectory(prefix="green-r09-toctou-") as text:
            root = Path(text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"frozen\n")
            output = root / "out.json"

            def mutate(*_args):
                self.assertIs(M.R09.FULL.parse_b_shard, M.parse_b_green)
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

        with mock.patch.object(M.R09, "build", side_effect=ArithmeticError("x")):
            with self.assertRaises(ArithmeticError):
                # The source-pin snapshot succeeds before the forced build error.
                M.main([
                    "--a-dir", "/unused", "--b-dir", "/unused",
                    "--output", "/unused/out.json",
                    "--expected-self-sha256", SOURCE_SHA256,
                ])
        self.assertIs(M.R09.FULL.parse_b_shard, original)

    def test_exclusive_publication_and_optimization_safe_source(self):
        original = M.R09.FULL.parse_b_shard
        with tempfile.TemporaryDirectory(prefix="green-r09-exclusive-") as text:
            root = Path(text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"frozen\n")
            output = root / "out.json"
            sentinel = b"do-not-overwrite\n"
            output.write_bytes(sentinel)
            with mock.patch.object(M, "PINS", {dependency: digest(dependency)}), \
                    mock.patch.object(M, "REPO", root), \
                    mock.patch.object(
                        M.R09, "build",
                        return_value={"theorem_ready_scalar": True}):
                with self.assertRaises(FileExistsError):
                    M.main([
                        "--a-dir", text, "--b-dir", text,
                        "--output", str(output),
                        "--expected-self-sha256", SOURCE_SHA256,
                    ])
            self.assertEqual(output.read_bytes(), sentinel)
        self.assertIs(M.R09.FULL.parse_b_shard, original)
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("assert ", source)
        self.assertNotIn("eval(", source)
        self.assertNotIn("exec(", source)


if __name__ == "__main__":
    unittest.main()
