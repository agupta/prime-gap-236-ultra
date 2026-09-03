#!/usr/bin/env python3
"""Focused hostile tests for the outcome-neutral completed-output audit."""

from __future__ import annotations

import ast
from fractions import Fraction as Q
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
CHECKER = REPO / (
    "agents/audit/verify_frontier_active25_v6_completed_obstruction_v2.py")
ENGINE = REPO / "agents/audit/verify_frontier_active25_v6_completed.py"
ENGINE_SHA256 = (
    "6f73b06cf2c494b271a2ce169a00b9324b1ef1f41b224903c6c969bc7edeaa66"
)


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "frontier_active25_completed_obstruction_v2_test_subject", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load_checker()


class ExactLDLTests(unittest.TestCase):
    def test_exact_positive_factorization_and_canonical_hash(self):
        result = M.exact_ldlt_obstruction(
            [Q(3), Q(2)], [[Q(1), Q(1, 2)], [Q(1, 2), Q(1)]])
        self.assertEqual(result["pivot_list"], ["2", "7/8"])
        self.assertEqual(result["pivot_signs"], [1, 1])
        self.assertEqual(result["minimum_pivot"], "7/8")
        self.assertEqual(result["minimum_pivot_index"], 1)
        self.assertEqual(
            result["pivot_list_canonical_sha256"],
            "43ba1950c7c4981eb6f3a05df89e7de9339cefcd95b73e178c9d9692ad603027")
        self.assertTrue(result["factorization_identity_verified"])

    def test_indefinite_matrix_is_rejected(self):
        with self.assertRaisesRegex(
                M.ObstructionFailure, "not positive definite"):
            M.exact_ldlt_obstruction([Q(1)], [[Q(2)]])

    def test_singular_matrix_is_rejected(self):
        with self.assertRaisesRegex(M.ObstructionFailure, "zero exact LDL"):
            M.exact_ldlt_obstruction([Q(1)], [[Q(1)]])

    def test_nonsymmetric_matrix_is_rejected(self):
        with self.assertRaisesRegex(M.ObstructionFailure, "not symmetric"):
            M.exact_ldlt_obstruction(
                [Q(3), Q(3)], [[Q(1), Q(1)], [Q(0), Q(1)]])

    def test_malformed_dimension_is_rejected(self):
        with self.assertRaisesRegex(M.ObstructionFailure, "malformed"):
            M.exact_ldlt_obstruction([Q(1), Q(2)], [[Q(0)]])


class OutcomeNeutralAdapterTests(unittest.TestCase):
    def invoke_with_fake(self, fake, flag, fresh_a, fresh_b):
        original = M.E._strict_candidate
        try:
            M.E._strict_candidate = fake
            return M._strict_candidate_outcome(
                {"finite_space_crosses_one": flag},
                None, None, None, None, None, None, None, None,
                fresh_a, fresh_b, {})
        finally:
            M.E._strict_candidate = original

    @staticmethod
    def negative_fake(value, *unused):
        M.E.require(False, "candidate exact rational vector does not cross one")
        return [Q(1)], Q(2), Q(1), Q(-1)

    @staticmethod
    def positive_fake(value, *unused):
        M.E.require(True, "candidate exact rational vector does not cross one")
        return [Q(1)], Q(1), Q(2), Q(1)

    def test_negative_exact_outcome_gets_obstruction(self):
        before = M.E.require
        vector, denominator, numerator, margin, crosses, obstruction = \
            self.invoke_with_fake(
                self.negative_fake, False, [Q(2)], [[Q(1)]])
        self.assertEqual((vector, denominator, numerator, margin),
                         ([Q(1)], Q(2), Q(1), Q(-1)))
        self.assertFalse(crosses)
        self.assertEqual(obstruction["pivot_list"], ["1"])
        self.assertIs(M.E.require, before)

    def test_positive_exact_outcome_remains_accepted(self):
        result = self.invoke_with_fake(
            self.positive_fake, True, [Q(1)], [[Q(2)]])
        self.assertTrue(result[4])
        self.assertIsNone(result[5])

    def test_false_flag_on_positive_margin_is_rejected(self):
        with self.assertRaisesRegex(
                M.E.ReconstructionFailure, "crossing flag"):
            self.invoke_with_fake(
                self.positive_fake, False, [Q(1)], [[Q(2)]])

    def test_true_flag_on_negative_margin_is_rejected(self):
        with self.assertRaisesRegex(
                M.E.ReconstructionFailure, "crossing flag"):
            self.invoke_with_fake(
                self.negative_fake, True, [Q(2)], [[Q(1)]])

    def test_negative_outcome_without_positive_definiteness_is_rejected(self):
        with self.assertRaisesRegex(
                M.ObstructionFailure, "not positive definite"):
            self.invoke_with_fake(
                self.negative_fake, False, [Q(1)], [[Q(2)]])

    def test_unrelated_engine_failure_is_not_suppressed(self):
        def unrelated(value, *unused):
            M.E.require(False, "unrelated exact arithmetic failure")

        with self.assertRaisesRegex(
                M.E.ReconstructionFailure, "unrelated exact arithmetic"):
            self.invoke_with_fake(unrelated, False, [Q(2)], [[Q(1)]])

    def test_engine_require_is_restored_after_failure(self):
        before = M.E.require

        def fail_after_compatibility(value, *unused):
            M.E.require(False,
                        "candidate exact rational vector does not cross one")
            M.E.require(False, "later failure")

        with self.assertRaisesRegex(M.E.ReconstructionFailure, "later failure"):
            self.invoke_with_fake(
                fail_after_compatibility, False, [Q(2)], [[Q(1)]])
        self.assertIs(M.E.require, before)


class IsolationAndStaticTests(unittest.TestCase):
    def test_frozen_engine_pin(self):
        self.assertEqual(hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
                         ENGINE_SHA256)
        self.assertEqual(M.E._SELF["sha256"], ENGINE_SHA256)

    def test_import_cannot_acquire_cli_capability(self):
        with self.assertRaisesRegex(
                M.ObstructionFailure, "isolated direct CLI"):
            M._CLI_CAPABILITY(M._SELF["sha256"])

    def test_import_cannot_invoke_long_reconstruction(self):
        with self.assertRaisesRegex(
                M.ObstructionFailure, "capability absent"):
            M._PRODUCTION_INVOKE(None, object())

    def test_v2_is_the_pinned_self_during_local_module_scan(self):
        original_loader = M.E._load_low_level_core
        original_file = M.E.FILE
        observed = []

        def fake_loader(sources):
            observed.append(M.E.FILE)
            return "core"

        try:
            M.E._load_low_level_core = fake_loader
            self.assertEqual(M._load_low_level_core_v2({}), "core")
        finally:
            M.E._load_low_level_core = original_loader
        self.assertEqual(observed, [M.FILE])
        self.assertEqual(M.E.FILE, original_file)

    def test_engine_file_is_restored_when_loader_fails(self):
        original_loader = M.E._load_low_level_core
        original_file = M.E.FILE

        def fake_loader(sources):
            raise RuntimeError("loader fixture")

        try:
            M.E._load_low_level_core = fake_loader
            with self.assertRaisesRegex(RuntimeError, "loader fixture"):
                M._load_low_level_core_v2({})
        finally:
            M.E._load_low_level_core = original_loader
        self.assertEqual(M.E.FILE, original_file)

    def test_reconstruction_precedes_stage_and_candidate_parse(self):
        source = CHECKER.read_text(encoding="utf-8")
        core = source.index("core = _load_low_level_core_v2(sources)")
        shell = source.index("masses, shell_48j, shell_counts")
        stage = source.index("stage = E.strict_json_bytes(")
        candidate = source.index("candidate = E.strict_json_bytes(")
        self.assertLess(core, shell)
        self.assertLess(shell, stage)
        self.assertLess(stage, candidate)

    def test_successor_has_no_interrupted_result_input(self):
        source = CHECKER.read_text(encoding="utf-8")
        self.assertNotIn("completed_audit.normal.json", source)
        self.assertNotIn("completed_audit.opt.json", source)

    def test_source_has_no_optimization_sensitive_assert(self):
        source = CHECKER.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(CHECKER))
        self.assertFalse(any(isinstance(node, ast.Assert)
                             for node in ast.walk(tree)))
        self.assertNotIn("__debug__", source)

    def test_no_v6_producer_or_assembler_import(self):
        tree = ast.parse(CHECKER.read_bytes(), filename=str(CHECKER))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        joined = "\n".join(names)
        self.assertNotIn("frontier_active25_inner_d16_staged_v6", joined)
        self.assertNotIn("assemble_frontier_active25_inner_d16_v6", joined)

    def test_pure_ldl_output_is_normal_optimized_identical(self):
        code = (
            "import importlib.util\n"
            "from fractions import Fraction as Q\n"
            f"p={str(CHECKER)!r}\n"
            "s=importlib.util.spec_from_file_location('v2_subprocess',p)\n"
            "m=importlib.util.module_from_spec(s)\n"
            "s.loader.exec_module(m)\n"
            "r=m.exact_ldlt_obstruction([Q(3),Q(2)],"
            "[[Q(1),Q(1,2)],[Q(1,2),Q(1)]])\n"
            "print(m.canonical_json(r).decode('ascii'),end='')\n")
        normal = subprocess.run(
            [sys.executable, "-I", "-c", code], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        optimized = subprocess.run(
            [sys.executable, "-O", "-I", "-c", code], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(normal.stdout, optimized.stdout)
        self.assertEqual(
            hashlib.sha256(normal.stdout).hexdigest(),
            "f425f6dda3455b062ea91be060ecf8358db1ef5f7583568bdd08ab27381476f1")


if __name__ == "__main__":
    unittest.main()
