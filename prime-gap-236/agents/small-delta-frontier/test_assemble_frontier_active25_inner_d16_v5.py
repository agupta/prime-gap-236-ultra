#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("assemble_frontier_active25_inner_d16_v5.py")
SPEC = importlib.util.spec_from_file_location("assemble_active25_v5", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def fake_shard(r):
    vector = [Q(0)] * (M.staged.v2.core.K + 1)
    vector[r] = Q(r + 1, 17)
    vector[r + 1] = -Q(r + 1, 31)
    return {
        "common_r": r, "complete_common_r": True,
        "domain_counts": {"rh": 1, "rl": 1, "vh": 1, "vl": 1},
        "faces": 1, "geometric_group_count": 1,
        "inner_48J": "7/5", "inner_I": "3/2",
        "inner_basis_dimension": 307, "nonzero_group_count": 1,
        "raw_J_cross_by_target_R": [str(x) for x in vector],
    }


class FakeRuntime:
    def __init__(self):
        self.now = 1_000_000_000_000

    def monotonic_ns(self):
        return self.now

    def boot_id(self):
        return "12345678-1234-1234-1234-123456789abc"

    def mem_available_kib(self):
        return 1_500_000

    def sleep(self, seconds):
        self.now += int(seconds * 10**9)

    def run_child(self, r, timeout_seconds, ledger_row):
        self.now += 1_000_000_000
        child = {
            "arithmetic_core_sha256":
                M.staged.v2.PINNED[M.staged.v2.CORE_PATH],
            "dependency_sha256": M.staged.dependency_record(),
            "driver_sha256": M.staged.sha256(M.staged.FILE),
            "format": M.staged.runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v5",
                "synthetic-test"),
            "gate_sha256": M.staged.runtime_gate_sha256("synthetic-test"),
            "ledger_binding": ledger_row,
            "parameters": M.staged.v2.core.parameter_record(),
            "shard": fake_shard(r), "status": "complete",
            "theorem_ready": False,
        }
        return M.staged.canonical_json(child)


def fake_expected_ledger():
    return {"leaf": M.staged.LEDGER_LEAF, "sha256": "b" * 64,
            "device": 1, "inode": 27}


def fake_result(manifest_sha="a" * 64):
    vector = ["1"] + ["0"] * 26
    matrix = [["0" for _ in range(27)] for _ in range(27)]
    matrix[0][0] = "2"
    solve = {
        "precision": 100, "eigenvalue": "2", "rayleigh_quotient": "2",
        "relative_residual_bound": "0", "jacobi_rotations": 0,
        "vector": vector,
    }
    return {
        "I_diagonal": ["1"] * 27,
        "assembler_sha256": M.sha256(M.FILE),
        "dependency_sha256": M.dependency_record(), "dimension": 27,
        "eigenvalue_optimality_rigorous": False,
        "independent_arithmetic_reconstruction": False,
        "exact_margin": "1",
        "exact_quotient": "2", "exact_rational_denominator": "1",
        "exact_rational_numerator": "2", "finite_space_crosses_one": True,
        "format": "frontier-active25-inner-D16-exact-pencil-v5",
        "ledger_binding": {"device": 1, "inode": 27,
                           "path": "/tmp/records/ledger.json",
                           "sha256": "b" * 64},
        "manifest_binding": {"device": 1, "inode": 2,
                             "path": "/tmp/records/manifest.json",
                             "sha256": manifest_sha},
        "parameters": M.staged.v2.core.parameter_record(),
        "precision_discovery": [solve, dict(solve, precision=160)],
        "rational_denominator_limit": 10**18, "rational_vector": vector,
        "serialized_stage_arithmetic_conditional": True,
        "shell_domain_counts": {"hh": 1, "hl": 2, "ll": 3},
        "stage_bindings": [
            {"leaf": M.staged.STAGE_LEAVES[r], "sha256": "0" * 64,
             "device": 1, "inode": r + 30} for r in range(26)],
        "status": "complete", "theorem_ready": False,
        "two_precision_gate": {
            "precisions": [100, 160],
            "quotient_absolute_tolerance": "1e-70",
            "relative_residual_maximum": "1e-70"},
        "48J_matrix": matrix,
    }


class AssemblerTests(unittest.TestCase):
    def test_factor_48_once_and_oriented_symmetric_matrix(self):
        a, b = M.assemble_exact_matrices(
            Q(13), Q(17), [Q(1, 3), Q(-2, 5), Q(0), Q(0)],
            [0, 1], [Q(2), Q(3)], [[Q(5), Q(7)], [Q(7), Q(11)]])
        self.assertEqual(a, [Q(13), Q(2), Q(3)])
        self.assertEqual(b, [[Q(17), Q(16), Q(-96, 5)],
                             [Q(16), Q(5), Q(7)],
                             [Q(-96, 5), Q(7), Q(11)]])
        with self.assertRaises(ArithmeticError):
            M.assemble_exact_matrices(
                Q(13), Q(17), [Q(1), Q(1), Q(1)], [0, 1],
                [Q(2), Q(3)], [[Q(5), Q(7)], [Q(7), Q(11)]])
        with self.assertRaises(ValueError):
            M.assemble_exact_matrices(
                Q(13), Q(17), [Q(1), Q(1), Q(0)], [0, 1],
                [Q(2), Q(3)], [[Q(5), Q(7)], [Q(7), Q(11)]], k=47)

    def test_two_precision_diagonal_oracle(self):
        solves, vector, denominator, numerator = M.discovery_and_rationalize(
            [Q(1), Q(2)], [[Q(1), Q(0)], [Q(0), Q(4)]])
        self.assertEqual([x["rayleigh_quotient"] for x in solves], ["2", "2"])
        self.assertEqual((vector, denominator, numerator),
                         ([Q(0), Q(1)], Q(2), Q(4)))

    def test_external_manifest_sha_and_stage_rebind(self):
        with tempfile.TemporaryDirectory() as directory:
            run = M.staged._run_all_test_only(directory, FakeRuntime())
            handle = M.staged.open_record_dir(directory)
            try:
                ledger_snap = M.staged.read_leaf(handle, M.staged.LEDGER_LEAF)
                ledger = M.staged._parse_ledger_snapshot(
                    handle, ledger_snap, "synthetic-test")
                snap = M.staged.read_leaf(handle, M.staged.MANIFEST_LEAF)
                manifest = json.loads(snap["data"])
                self.assertTrue(M.staged.strict_manifest(
                    manifest, handle, ledger, ledger_snap, "synthetic-test"))
            finally:
                M.staged.close_record_dir(handle)
            with self.assertRaises((ValueError, RuntimeError)):
                M.load_completed_manifest(
                    directory, run["manifest_sha256"], fake_expected_ledger())
            first = Path(directory) / M.staged.STAGE_LEAVES[0]
            first.write_text("{}\n")
            with self.assertRaises((ValueError, RuntimeError)):
                M.load_completed_manifest(
                    directory, run["manifest_sha256"], fake_expected_ledger())
            with self.assertRaises(ValueError):
                M.load_completed_manifest(
                    directory, "A" * 64, fake_expected_ledger())

    def test_strict_result_exact_contraction_and_boolean_rejection(self):
        value = fake_result()
        ledger = fake_expected_ledger()
        self.assertTrue(M.strict_result(value, "a" * 64, ledger))
        bad = dict(value, finite_space_crosses_one=1)
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64, ledger)
        bad = json.loads(json.dumps(value))
        bad["48J_matrix"][0][0] = "3"
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64, ledger)
        bad = json.loads(json.dumps(value))
        bad["stage_bindings"][0]["leaf"] = "common_r_01.json"
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64, ledger)
        bad = json.loads(json.dumps(value))
        bad["independent_arithmetic_reconstruction"] = True
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64, ledger)
        wrong_ledger = dict(ledger, inode=28)
        with self.assertRaises(ValueError):
            M.strict_result(value, "a" * 64, wrong_ledger)

    def test_o_excl_output_and_record_alias_rejection(self):
        with tempfile.TemporaryDirectory() as parent:
            record = Path(parent) / "record"
            output_parent = Path(parent) / "output"
            record.mkdir()
            output_parent.mkdir()
            manifest_sha = "a" * 64
            ledger = fake_expected_ledger()
            value = fake_result(manifest_sha)
            target = output_parent / "result.json"
            original = M._rebind_manifest_handle
            try:
                M._rebind_manifest_handle = \
                    lambda handle, expected, expected_ledger: None
                snap = M.publish_output(
                    target, value, record, manifest_sha, ledger)
                self.assertEqual(
                    snap["sha256"],
                    M.sha256_bytes(M.staged.canonical_json(value)))
                with self.assertRaises(FileExistsError):
                    M.publish_output(
                        target, value, record, manifest_sha, ledger)
                with self.assertRaises(ValueError):
                    M.publish_output(record / "bad.json", value, record,
                                     manifest_sha, ledger)
            finally:
                M._rebind_manifest_handle = original

    def test_late_output_replacement_preserves_foreign_inode(self):
        with tempfile.TemporaryDirectory() as parent:
            record = Path(parent) / "record"
            output_parent = Path(parent) / "output"
            record.mkdir()
            output_parent.mkdir()
            manifest_sha = "a" * 64
            ledger = fake_expected_ledger()
            value = fake_result(manifest_sha)
            target = output_parent / "race.json"
            original_rebind = M._rebind_manifest_handle
            original_read = M.staged.read_leaf
            swapped = False

            def swapping_read(handle, name, maximum_bytes=16_000_000):
                nonlocal swapped
                if (not swapped and handle["path"] == str(output_parent.resolve())
                        and name == target.name):
                    swapped = True
                    os.unlink(name, dir_fd=handle["descriptor"])
                    descriptor = os.open(
                        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
                        dir_fd=handle["descriptor"])
                    try:
                        os.write(descriptor, b"foreign\n")
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                return original_read(handle, name, maximum_bytes)

            try:
                M._rebind_manifest_handle = \
                    lambda handle, expected, expected_ledger: None
                M.staged.read_leaf = swapping_read
                with self.assertRaises(RuntimeError):
                    M.publish_output(
                        target, value, record, manifest_sha, ledger)
            finally:
                M.staged.read_leaf = original_read
                M._rebind_manifest_handle = original_rebind
            self.assertTrue(swapped)
            self.assertEqual(target.read_bytes(), b"foreign\n")

    def test_external_result_hardlink_and_self_sha_reject(self):
        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / "result.json"
            target.write_bytes(M.staged.canonical_json({}))
            expected = M.sha256(target)
            self.assertEqual(M.read_external_file(target, expected), {})
            os.link(target, Path(parent) / "second-link.json")
            with self.assertRaises(ValueError):
                M.read_external_file(target, expected)
        self.assertEqual(M.require_self_sha256(M.sha256(M.FILE)),
                         M.sha256(M.FILE))
        with self.assertRaises(RuntimeError):
            M.require_self_sha256("0" * 64)


if __name__ == "__main__":
    unittest.main()
