#!/usr/bin/env python3
"""Hostile, target-free tests for the active25 v6 completion checker."""

from __future__ import annotations

import copy
from fractions import Fraction as Q
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


FILE = Path(__file__).resolve()
CHECKER = FILE.with_name("verify_frontier_active25_v6_completed.py")
SPEC = importlib.util.spec_from_file_location(
    "active25_v6_completed_checker_for_tests", CHECKER)
if SPEC is None or SPEC.loader is None:
    raise ImportError(CHECKER)
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)

AUTHORIZATION = {"sha256": "a" * 64, "device": 7, "inode": 11}
LEDGER_BINDING = {
    "leaf": C.LEDGER_LEAF, "sha256": "b" * 64,
    "device": 7, "inode": 12,
}
DEPENDENCY = {}
LEDGER = {
    "start_monotonic_ns": 0,
    "deadline_monotonic_ns": 100 * 10**9,
    "max_single_shard_nanoseconds": 10 * 10**9,
}


def fake_shard(r):
    vector = [Q(0) for _ in range(C.K + 1)]
    vector[r] = Q(r + 1, 101)
    if r + 1 < len(C.ACTIVE):
        vector[r + 1] = -Q(r + 2, 103)
    return C._expected_shard(
        r, vector, {tag: r + 1 for tag in ("rh", "rl", "vh", "vl")},
        r + 2, r + 1, r + 3, Q(3, 2), Q(7, 5), 307)


def fake_stage(r, shard=None):
    shard = fake_shard(r) if shard is None else shard
    child = {
        "arithmetic_core_sha256": C.CORE_SHA256,
        "authorization_binding": AUTHORIZATION,
        "dependency_sha256": DEPENDENCY,
        "driver_sha256": C.PRODUCER_SHA256,
        "format":
            "frontier-active25-inner-D16-child-arithmetic-v6-production",
        "gate_sha256": C.GATE_SHA256,
        "ledger_binding": LEDGER_BINDING,
        "parameters": C.PARAMETERS,
        "shard": shard,
        "status": "complete",
        "theorem_ready": False,
    }
    return {
        "authorization_binding": AUTHORIZATION,
        "child_stdout_sha256": C.sha256_bytes(C.canonical_json(child)),
        "dependency_sha256": DEPENDENCY,
        "driver_sha256": C.PRODUCER_SHA256,
        "format":
            "frontier-active25-inner-D16-common-r-stage-v6-production",
        "gate_sha256": C.GATE_SHA256,
        "ledger_binding": LEDGER_BINDING,
        "parameters": C.PARAMETERS,
        "resource_observation": {
            "first": {"before_monotonic_ns": 0,
                      "after_monotonic_ns": 0,
                      "mem_available_kib": 1_400_000},
            "minimum_separation_nanoseconds": 5 * 10**9,
            "second": {"before_monotonic_ns": 5 * 10**9,
                       "after_monotonic_ns": 5 * 10**9,
                       "mem_available_kib": 1_400_000},
        },
        "runtime_mode": "production",
        "shard": shard,
        "status": "complete",
        "supervised_child_interval": {
            "start_monotonic_ns": 6 * 10**9,
            "end_monotonic_ns": 7 * 10**9,
        },
        "supervised_child_nanoseconds": 10**9,
        "theorem_ready": False,
    }


def fixture_output():
    raw = [Q(0) for _ in range(C.K + 1)]
    raw[0] = Q(2, 3)
    masses = [Q(1) for _ in C.ACTIVE] + [Q(0) for _ in range(23)]
    shell = [[Q(0) for _ in range(C.K + 1)] for _ in range(C.K + 1)]
    a, b = C.assemble_fresh_forms(Q(5, 4), Q(9, 7), raw, masses, shell)
    vector = [Q(1)] + [Q(0) for _ in range(26)]
    denominator, numerator, margin = C.exact_certificate(a, b, vector)
    return C.canonical_json({
        "a": [str(value) for value in a],
        "b01": str(b[0][1]),
        "denominator": str(denominator),
        "margin": str(margin),
        "numerator": str(numerator),
    })


class ArithmeticHostileTests(unittest.TestCase):
    def assertRejected(self, function):
        with self.assertRaises(C.ReconstructionFailure):
            function()

    def validate_stage(self, stage, r, expected=None):
        return C._strict_stage(
            stage, r, LEDGER, LEDGER_BINDING, AUTHORIZATION,
            DEPENDENCY, fake_shard(r) if expected is None else expected)

    def test_each_of_26_altered_stage_rationals_is_rejected(self):
        for r in C.ACTIVE:
            with self.subTest(common_r=r):
                stage = fake_stage(r)
                altered = copy.deepcopy(stage)
                target = r
                old = Q(altered["shard"]["raw_J_cross_by_target_R"][target])
                altered["shard"]["raw_J_cross_by_target_R"][target] = str(old + 1)
                # The stage is internally stale and, more importantly, differs
                # from the independently supplied expected arithmetic.
                self.assertRejected(lambda value=altered, index=r:
                                    self.validate_stage(value, index))

    def test_self_consistent_false_inner_48j_is_rejected(self):
        false = copy.deepcopy(fake_shard(0))
        false["inner_48J"] = "999"
        stage = fake_stage(0, false)  # child hash is recomputed consistently
        self.assertRejected(lambda: self.validate_stage(stage, 0))

    def test_fake_26_stage_manifest_payload_with_inner_999_cannot_validate(self):
        stages = [fake_stage(r) for r in C.ACTIVE]
        false = copy.deepcopy(fake_shard(13))
        false["inner_48J"] = "999"
        stages[13] = fake_stage(13, false)
        accepted = []
        for r, stage in enumerate(stages):
            try:
                self.validate_stage(stage, r)
            except C.ReconstructionFailure:
                accepted.append(False)
            else:
                accepted.append(True)
        self.assertEqual(accepted.count(False), 1)
        self.assertFalse(accepted[13])

    def test_swapped_r_rplus1_ownership_is_rejected(self):
        expected = fake_shard(4)
        swapped = copy.deepcopy(expected)
        vector = swapped["raw_J_cross_by_target_R"]
        vector[4], vector[5] = vector[5], vector[4]
        stage = fake_stage(4, swapped)  # fully self-consistent false record
        self.assertRejected(lambda: self.validate_stage(stage, 4, expected))

    def test_count26_tail_dimension_and_sign_are_rejected(self):
        bad_tail = copy.deepcopy(fake_shard(25))
        bad_tail["raw_J_cross_by_target_R"][26] = "1"
        self.assertRejected(lambda: C._strict_shard_schema(bad_tail, 25))
        bad_dimension = copy.deepcopy(fake_shard(2))
        bad_dimension["inner_basis_dimension"] = 306
        self.assertRejected(lambda: C._strict_shard_schema(bad_dimension, 2))
        bad_i = copy.deepcopy(fake_shard(2))
        bad_i["inner_I"] = "-1"
        self.assertRejected(lambda: C._strict_shard_schema(bad_i, 2))

    def test_eta1_eta2_swap_is_rejected(self):
        stage = fake_stage(3)
        stage["parameters"] = copy.deepcopy(C.PARAMETERS)
        stage["parameters"]["eta"] = list(reversed(stage["parameters"]["eta"]))
        self.assertRejected(lambda: self.validate_stage(stage, 3))

    def test_factor_48_is_applied_exactly_once_without_extra_two(self):
        raw = [Q(0) for _ in range(C.K + 1)]
        raw[0] = Q(2, 3)
        masses = [Q(1) for _ in C.ACTIVE] + [Q(0) for _ in range(23)]
        shell = [[Q(0) for _ in range(C.K + 1)] for _ in range(C.K + 1)]
        _, matrix = C.assemble_fresh_forms(Q(1), Q(1), raw, masses, shell)
        self.assertEqual(matrix[0][1], 32)
        self.assertEqual(matrix[1][0], 32)
        self.assertNotEqual(matrix[0][1], raw[0])
        self.assertNotEqual(matrix[0][1], 2 * C.K * raw[0])
        missing = copy.deepcopy(matrix)
        missing[0][1] = missing[1][0] = raw[0]
        doubled = copy.deepcopy(matrix)
        doubled[0][1] = doubled[1][0] = 2 * C.K * raw[0]
        self.assertRejected(lambda: C.require_exact_forms(
            [Q(1)] * 27, missing, [Q(1)] * 27, matrix))
        self.assertRejected(lambda: C.require_exact_forms(
            [Q(1)] * 27, doubled, [Q(1)] * 27, matrix))

    def test_four_ordered_shell_tables_are_not_two_hl(self):
        hh = [[Q(5), Q(7)], [Q(11), Q(13)]]
        hl = [[Q(1), Q(2)], [Q(3), Q(4)]]
        lh = [[Q(1), Q(3)], [Q(2), Q(4)]]
        ll = [[Q(17), Q(19)], [Q(23), Q(29)]]
        raw, scaled = C.ordered_shell_inclusion(hh, hl, lh, ll)
        doubled_hl = [[hh[i][j] - 2 * hl[i][j] + ll[i][j]
                       for j in range(2)] for i in range(2)]
        self.assertNotEqual(raw, doubled_hl)
        self.assertEqual(scaled,
                         [[C.K * raw[i][j] for j in range(2)] for i in range(2)])
        self.assertRejected(
            lambda: C.ordered_shell_inclusion(hh, hl, hl, ll))
        self.assertRejected(lambda: C.require_exact_forms(
            [Q(1), Q(1)], [[C.K * value for value in row]
                            for row in doubled_hl],
            [Q(1), Q(1)], scaled))

    def test_missing_or_doubled_shell_factor_is_detected(self):
        hh = [[Q(1)]]
        zero = [[Q(0)]]
        raw, scaled = C.ordered_shell_inclusion(hh, zero, zero, zero)
        self.assertEqual(raw, [[Q(1)]])
        self.assertEqual(scaled, [[Q(48)]])
        self.assertNotEqual(scaled, raw)
        self.assertNotEqual(scaled, [[Q(96)]])
        self.assertRejected(lambda: C.require_exact_forms(
            [Q(1)], raw, [Q(1)], scaled))
        self.assertRejected(lambda: C.require_exact_forms(
            [Q(1)], [[Q(96)]], [Q(1)], scaled))

    def test_forged_positive_serialized_margin_is_rejected(self):
        a = [Q(1)]
        b = [[Q(2)]]
        vector = [Q(1)]
        denominator, numerator, margin = C.exact_certificate(a, b, vector)
        serialized = {
            "exact_rational_denominator": "1",
            "exact_rational_numerator": "2",
            "exact_quotient": "2",
            "exact_margin": "999",
        }
        self.assertRejected(lambda: C.require_serialized_certificate(
            serialized, denominator, numerator, margin))

    def test_noncanonical_fraction_and_duplicate_json_are_rejected(self):
        self.assertRejected(lambda: C.strict_fraction("2/2", "fixture"))
        self.assertRejected(lambda: C.strict_json_bytes(
            b'{"x":1,"x":2}\n', "duplicate", canonical=True))


class ProvenanceHostileTests(unittest.TestCase):
    def assertRejected(self, function):
        with self.assertRaises(C.ReconstructionFailure):
            function()

    def test_self_declared_alternative_46_file_closure_is_rejected(self):
        self.assertEqual(C._strict_dependency_record(
            dict(C.EXPECTED_PRODUCER_DEPENDENCY)),
            C.EXPECTED_PRODUCER_DEPENDENCY)
        forged = dict(C.EXPECTED_PRODUCER_DEPENDENCY)
        key = next(iter(forged))
        forged[key] = "0" * 64
        self.assertRejected(lambda: C._strict_dependency_record(forged))

    def test_missing_extra_and_duplicate_inventory(self):
        with tempfile.TemporaryDirectory(prefix="active25-completed-leaves-") as raw:
            root = Path(raw)
            (root / "a").write_bytes(b"a")
            (root / "b").write_bytes(b"b")
            handle = C._open_directory(root)
            try:
                self.assertTrue(C.require_exact_leaf_set(handle, {"a", "b"}))
                self.assertRejected(lambda: C.require_exact_leaf_set(handle, {"a"}))
                self.assertRejected(lambda: C.require_exact_leaf_set(
                    handle, {"a", "b", "c"}))
                self.assertRejected(lambda: C.require_exact_leaf_set(
                    handle, ("a", "a")))
            finally:
                C._close_snapshots([handle])

    def test_symlink_and_hardlink_leaves_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="active25-completed-links-") as raw:
            root = Path(raw)
            (root / "target").write_bytes(b"x")
            os.symlink("target", root / "symlink")
            os.link(root / "target", root / "hardlink")
            handle = C._open_directory(root)
            try:
                self.assertRejected(lambda: C._open_leaf(handle, "symlink", 10))
                self.assertRejected(lambda: C._open_leaf(handle, "target", 10))
                self.assertRejected(lambda: C._open_leaf(handle, "hardlink", 10))
            finally:
                C._close_snapshots([handle])

    def test_deleted_mutated_and_replaced_leaf_rebinding_fails(self):
        for mode in ("deleted", "mutated", "replaced"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(
                    prefix="active25-completed-rebind-") as raw:
                root = Path(raw)
                path = root / "leaf"
                path.write_bytes(b"original")
                directory = C._open_directory(root)
                snapshot = C._open_leaf(directory, "leaf", 100)
                try:
                    if mode == "deleted":
                        path.unlink()
                    elif mode == "mutated":
                        path.write_bytes(b"changed")
                    else:
                        replacement = root / "replacement"
                        replacement.write_bytes(b"original")
                        os.replace(replacement, path)
                    self.assertRejected(lambda: C._rebind_leaf(directory, snapshot))
                finally:
                    C._close_snapshots([snapshot, directory])

    def test_source_mutation_and_replacement_rebinding_fails(self):
        for mode in ("mutated", "replaced"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(
                    prefix="active25-completed-source-") as raw:
                path = Path(raw) / "source.py"
                path.write_bytes(b"x = 1\n")
                snapshot = C._open_file(path, 100)
                try:
                    if mode == "mutated":
                        path.write_bytes(b"x = 2\n")
                    else:
                        replacement = path.with_name("replacement.py")
                        replacement.write_bytes(b"x = 1\n")
                        os.replace(replacement, path)
                    self.assertRejected(lambda: C._rebind_file(snapshot))
                finally:
                    C._close_snapshots([snapshot])

    def test_source_replacement_between_hash_and_import_is_rejected(self):
        with tempfile.TemporaryDirectory(
                prefix="active25-completed-import-race-") as raw:
            path = Path(raw) / "module.py"
            path.write_bytes(b"value = 1\n")
            snapshot = C._open_file(path, 100)
            try:
                replacement = path.with_name("replacement.py")
                replacement.write_bytes(b"value = 2\n")
                os.replace(replacement, path)
                specification = importlib.util.spec_from_file_location(
                    "active25_replaced_source_fixture", path)
                self.assertIsNotNone(specification)
                self.assertIsNotNone(specification.loader)
                module = importlib.util.module_from_spec(specification)
                specification.loader.exec_module(module)
                self.assertEqual(module.value, 2)
                self.assertRejected(lambda: C._rebind_file(snapshot))
            finally:
                C._close_snapshots([snapshot])

    def test_imported_context_cannot_acquire_production_capability(self):
        self.assertRejected(lambda: C._CLI_CAPABILITY(C._SELF["sha256"]))
        self.assertRejected(lambda: C._PRODUCTION_INVOKE(
            SimpleNamespace(), object()))

    def test_normal_and_optimized_pure_output_identity(self):
        outputs = []
        for flags in ([], ["-O"]):
            completed = subprocess.run(
                [sys.executable, *flags, "-I", str(FILE), "--fixture-output"],
                capture_output=True, timeout=10, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, b"")
            outputs.append(completed.stdout)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], fixture_output())

    def test_wrong_self_pin_rejects_before_inputs_with_fixed_sentinel(self):
        for flags in ([], ["-O"]):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory(
                    prefix="active25-completed-sentinel-") as raw:
                root = Path(raw)
                output = root / "rejection.json"
                completed = subprocess.run([
                    sys.executable, *flags, "-I", str(CHECKER),
                    "--expected-self-sha256", "0" * 64,
                    "--record-dir", str(root / "absent-record"),
                    "--expected-manifest-sha256", "0" * 64,
                    "--candidate", str(root / "absent-candidate"),
                    "--expected-candidate-sha256", "0" * 64,
                    "--output", str(output),
                ], capture_output=True, timeout=10, check=False)
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stdout, b"")
                self.assertEqual(completed.stderr, b"REJECTED\n")
                self.assertEqual(output.read_bytes(), C.REJECTION_SENTINEL)


if __name__ == "__main__" and sys.argv[1:] == ["--fixture-output"]:
    sys.stdout.buffer.write(fixture_output())
elif __name__ == "__main__":
    unittest.main()
