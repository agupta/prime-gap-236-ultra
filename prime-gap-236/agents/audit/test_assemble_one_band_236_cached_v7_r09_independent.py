#!/usr/bin/env python3
"""Independent hostile tests for the cached-v7 R<=9 shard assembler.

These tests do not reuse the production assembler's mutation fixtures.  They
state the total-large-count rule literally, inject unrelated exact branch
values, reconstruct the projection arithmetic, and exercise inventory,
snapshot, and publication failure paths.
"""

from __future__ import annotations

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
SOURCE = REPO / "verify/assemble_one_band_236_cached_v7_r09.py"
SOURCE_SHA256 = (
    "aaa3dc5199636da3dcff198fd16a84b097a192a72d89a5326dc690206946ce29")
FULL_SHA256 = (
    "08fb7e612f37050a21bc94d27e4b8ed0ad1838f64ce5e2a147d15aef9f076f05")


def digest(value: bytes | Path) -> str:
    data = value if isinstance(value, bytes) else value.read_bytes()
    return hashlib.sha256(data).hexdigest()


if digest(SOURCE) != SOURCE_SHA256:
    raise RuntimeError("frozen R<=9 assembler changed")
spec = importlib.util.spec_from_file_location(
    "independent_cached_v7_r09_assembler", SOURCE)
if spec is None or spec.loader is None:
    raise ImportError(SOURCE)
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def exact_branch_fixture():
    return {
        "branch_values_and_fast_stats": {
            "high": {
                "Sdelta": "2/3", "Stotal": "-5/7",
                "Ltotal": "11/13", "Lbig": "-17/19",
            },
            "low": {
                "Sdelta": "-23/29", "Stotal": "31/37",
                "Ltotal": "-41/43", "Lbig": "47/53",
            },
        },
    }


def totals(raw, names):
    block = raw["branch_values_and_fast_stats"]
    high = sum((Q(block["high"][name]) for name in names), Q(0))
    low = sum((Q(block["low"][name]) for name in names), Q(0))
    return M.B.K * (high - low)


class DefinitionFiveCountTest(unittest.TestCase):
    def test_exhaustive_literal_low_k_total_count_rule(self):
        # Definition 1 uses I={i:t_i>delta}; equality belongs to the small
        # side.  Exhaust every possible common count in several low k values.
        delta = Q(2, 11)
        fibers = (Q(0), delta / 2, delta, delta + Q(1, 97), 2 * delta)
        for k in range(1, 8):
            for cap in range(k + 1):
                for common_r in range(k):
                    for t in fibers:
                        literal = common_r + int(t > delta) <= cap
                        split_rule = ((common_r < cap) or
                                      (common_r == cap and t <= delta))
                        self.assertEqual(
                            literal, split_rule,
                            (k, cap, common_r, t, literal, split_rule))

    def test_target_branch_rule_and_endpoint(self):
        self.assertEqual(M.TOTAL_COUNTS, tuple(range(10)))
        self.assertEqual(M.ZEROED_TOTAL_COUNTS, (10, 11, 12))
        self.assertEqual(M.MIXED_COMMON_COUNTS, tuple(range(10)))
        self.assertEqual(M.R9_BRANCHES, ("Sdelta", "Stotal"))
        delta = M.B.DELTA
        for common_r in range(13):
            self.assertEqual(
                common_r + int(delta > delta) <= 9,
                common_r <= 9)
            self.assertEqual(
                common_r + int((delta + Q(1, 10**9)) > delta) <= 9,
                common_r <= 8)


class ExactBranchSelectionTest(unittest.TestCase):
    def call(self, raw, count, full=None):
        if full is None:
            full = totals(raw, ("Sdelta", "Stotal", "Ltotal", "Lbig"))
        with mock.patch.object(M.FULL, "parse_b_shard", return_value=full):
            return M.selected_b_shard(
                Path(f"common_r_{count:02d}.json"), canonical(raw), count)

    def test_all_branches_before_boundary_and_small_only_at_boundary(self):
        raw = exact_branch_fixture()
        full_expected = totals(raw, ("Sdelta", "Stotal", "Ltotal", "Lbig"))
        small_expected = totals(raw, ("Sdelta", "Stotal"))
        for count in range(9):
            selected, full, rule = self.call(raw, count)
            self.assertEqual(selected, full_expected)
            self.assertEqual(full, full_expected)
            self.assertEqual(rule, "all-distinguished-branches")
        selected, full, rule = self.call(raw, 9)
        self.assertEqual(selected, small_expected)
        self.assertEqual(full, full_expected)
        self.assertEqual(rule, "small-distinguished-only:Sdelta+Stotal")

    def test_r9_high_low_signs_factor48_and_large_branch_independence(self):
        raw = exact_branch_fixture()
        base, _, _ = self.call(raw, 9)
        for side, sign in (("high", 1), ("low", -1)):
            for name in ("Sdelta", "Stotal"):
                changed = json.loads(canonical(raw))
                changed["branch_values_and_fast_stats"][side][name] = str(
                    Q(changed["branch_values_and_fast_stats"][side][name]) +
                    Q(7, 31))
                value, _, _ = self.call(changed, 9)
                self.assertEqual(value - base, sign * M.B.K * Q(7, 31))
        for side in ("high", "low"):
            for name in ("Ltotal", "Lbig"):
                changed = json.loads(canonical(raw))
                changed["branch_values_and_fast_stats"][side][name] = str(
                    Q(changed["branch_values_and_fast_stats"][side][name]) +
                    Q(101, 103))
                value, full, _ = self.call(changed, 9)
                self.assertEqual(value, base)
                self.assertNotEqual(
                    full, totals(raw, ("Sdelta", "Stotal", "Ltotal", "Lbig")))

    def test_malformed_counts_branches_and_rationals_fail(self):
        raw = exact_branch_fixture()
        for bad in (True, False, 9.0, -1, 10):
            with self.assertRaises(ValueError):
                self.call(raw, bad)
        for side in ("high", "low"):
            for name in ("Sdelta", "Stotal"):
                changed = json.loads(canonical(raw))
                del changed["branch_values_and_fast_stats"][side][name]
                with self.assertRaises(ValueError):
                    self.call(changed, 9, Q(0))
        changed = json.loads(canonical(raw))
        changed["branch_values_and_fast_stats"]["high"]["Sdelta"] = "4/6"
        with self.assertRaises(ValueError):
            self.call(changed, 9, Q(0))


class InventoryAndProjectionTest(unittest.TestCase):
    def test_mixed_file_inventory_and_plain_file_requirement(self):
        with tempfile.TemporaryDirectory(prefix="r09-inventory-") as root_text:
            root = Path(root_text)
            for count in range(10):
                (root / f"common_r_{count:02d}.json").write_bytes(b"{}\n")
            paths = M.require_mixed_files(root)
            self.assertEqual(
                tuple(path.name for path in paths),
                tuple(f"common_r_{count:02d}.json" for count in range(10)))
            extra = root / "common_r_10.json"
            extra.write_bytes(b"{}\n")
            with self.assertRaises(ValueError):
                M.require_mixed_files(root)
            extra.unlink()
            missing = root / "common_r_04.json"
            missing.unlink()
            with self.assertRaises(ValueError):
                M.require_mixed_files(root)
            missing.symlink_to(root / "common_r_03.json")
            with self.assertRaises(ValueError):
                M.require_mixed_files(root)

    def test_build_reconstructs_truncated_projection_exactly(self):
        with tempfile.TemporaryDirectory(prefix="r09-projection-") as root_text:
            root = Path(root_text)
            a_paths = tuple(root / f"r_{count:02d}.json" for count in range(13))
            b_paths = tuple(root / f"common_r_{count:02d}.json"
                            for count in range(10))
            for count, path in enumerate(a_paths):
                path.write_bytes(f"A-{count}\n".encode("ascii"))
            for count, path in enumerate(b_paths):
                path.write_bytes(f"B-{count}\n".encode("ascii"))
            inner = canonical({
                "status": "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS",
                "rigorous": True, "k": 48,
                "deficit_positive": True, "denominator_positive": True,
                "exact_denominator": "10", "exact_numerator": "8",
                "exact_deficit": "2",
            })
            snapshots = {M.B.INNER_RESULT: inner}
            scale = M.B.FORM_SCALE

            def parse_a(_path, _data, count):
                return Q(count + 1)

            def parse_b(_path, _data, count):
                selected = Q((count + 1) * scale)
                return selected, 2 * selected, (
                    "all-distinguished-branches" if count < 9 else
                    "small-distinguished-only:Sdelta+Stotal")

            with mock.patch.object(M.B, "require_exact_files",
                                   return_value=a_paths), \
                    mock.patch.object(M, "require_mixed_files",
                                      return_value=b_paths), \
                    mock.patch.object(M.B, "parse_a_shard",
                                      side_effect=parse_a), \
                    mock.patch.object(M, "selected_b_shard",
                                      side_effect=parse_b):
                result = M.build(root, root, snapshots)

            a_value = Q(sum(range(1, 11)))
            b_value = Q(sum(range(1, 11)) * scale)
            i_value = Q(10 * scale)
            d_value = Q(2 * scale)
            margin = b_value**2 - a_value * d_value
            denominator = a_value * i_value + b_value**2
            exact = result["exact"]
            self.assertEqual(Q(exact["A_scaled"]), a_value)
            self.assertEqual(Q(exact["b_scaled"]), b_value)
            self.assertEqual(Q(exact["I_F_scaled"]), i_value)
            self.assertEqual(Q(exact["D_scaled"]), d_value)
            self.assertEqual(
                Q(exact["margin_b_squared_minus_A_D"]), margin)
            self.assertEqual(
                Q(exact["quotient_lower_bound"]),
                Q(1) + margin / denominator)
            self.assertTrue(result["theorem_ready_scalar"])
            self.assertEqual([row["count"] for row in result["a_shards"]],
                             list(range(10)))
            self.assertEqual(
                [row["count"] for row in result["zeroed_a_shards"]],
                [10, 11, 12])
            self.assertEqual([row["count"] for row in result["b_shards"]],
                             list(range(10)))
            for count, row in enumerate(result["a_shards"]):
                self.assertEqual(row["sha256"], digest(a_paths[count]))
            for count, row in enumerate(result["b_shards"]):
                self.assertEqual(row["sha256"], digest(b_paths[count]))


class ClosureAndPublicationTest(unittest.TestCase):
    def test_flat_source_closure_is_exact_and_live(self):
        self.assertEqual(digest(SOURCE), SOURCE_SHA256)
        self.assertEqual(M.FULL_ASSEMBLER_SHA256, FULL_SHA256)
        expected = dict(M.FULL.PINS)
        expected[M.FULL_ASSEMBLER] = FULL_SHA256
        self.assertEqual(M.PINS, expected)
        self.assertEqual(len(M.PINS), 43)
        for path, wanted in M.PINS.items():
            self.assertEqual(digest(path), wanted, str(path))

    def test_main_binds_dependency_snapshot_and_publishes_exclusively(self):
        with tempfile.TemporaryDirectory(prefix="r09-main-") as root_text:
            root = Path(root_text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"frozen\n")
            expected = digest(dependency)
            output = root / "aggregate.json"
            result = {"theorem_ready_scalar": True, "rigorous": True}
            arguments = [
                "--a-dir", str(root), "--b-dir", str(root),
                "--output", str(output),
                "--expected-self-sha256", SOURCE_SHA256,
            ]
            with mock.patch.object(M, "PINS", {dependency: expected}), \
                    mock.patch.object(M, "REPO", root), \
                    mock.patch.object(M, "build", return_value=dict(result)):
                self.assertEqual(M.main(arguments), 0)
                original = output.read_bytes()
                with self.assertRaises(FileExistsError):
                    M.main(arguments)
                self.assertEqual(output.read_bytes(), original)
            parsed = json.loads(original)
            self.assertEqual(parsed["source_hashes"], {"dependency.py": expected})
            self.assertEqual(parsed["assembler_sha256"], SOURCE_SHA256)
            self.assertEqual(parsed["full_assembler_sha256"], FULL_SHA256)

    def test_main_rejects_dependency_toc_tou(self):
        with tempfile.TemporaryDirectory(prefix="r09-toc-") as root_text:
            root = Path(root_text)
            dependency = root / "dependency.py"
            dependency.write_bytes(b"before\n")
            expected = digest(dependency)
            output = root / "aggregate.json"

            def mutate(_a, _b, _snapshots):
                dependency.write_bytes(b"after\n")
                return {"theorem_ready_scalar": True}

            arguments = [
                "--a-dir", str(root), "--b-dir", str(root),
                "--output", str(output),
                "--expected-self-sha256", SOURCE_SHA256,
            ]
            with mock.patch.object(M, "PINS", {dependency: expected}), \
                    mock.patch.object(M, "REPO", root), \
                    mock.patch.object(M, "build", side_effect=mutate):
                with self.assertRaises(RuntimeError):
                    M.main(arguments)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
