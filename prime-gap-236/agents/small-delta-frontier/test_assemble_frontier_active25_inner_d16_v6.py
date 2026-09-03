#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("assemble_frontier_active25_inner_d16_v6.py")
SPEC = importlib.util.spec_from_file_location("active25_assembler_v6_test", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fake_bindings():
    ledger = {"leaf": M.staged.LEDGER_LEAF, "sha256": "1" * 64,
              "device": 7, "inode": 10}
    manifest = {"path": "/tmp/records/manifest.json", "sha256": "2" * 64,
                "device": 7, "inode": 11}
    authorization = {"path": "/tmp/root-authorization.json",
                     "sha256": "3" * 64, "device": 7, "inode": 12}
    stages = [{"leaf": M.staged.STAGE_LEAVES[r], "sha256": f"{r + 20:064x}",
               "device": 7, "inode": 100 + r} for r in range(26)]
    return ledger, manifest, authorization, stages


def fake_result():
    ledger, manifest, authorization, stages = fake_bindings()
    a = [Q(1) for _ in range(27)]
    b = [[Q(0) for _ in range(27)] for _ in range(27)]
    b[0][0] = Q(2)
    vector = [Q(1)] + [Q(0)] * 26
    solve_vector = ["1"] + ["0"] * 26
    solves = [{
        "eigenvalue": "2",
        "jacobi_rotations": 0,
        "precision": precision,
        "rayleigh_quotient": "2",
        "relative_residual_bound": "0",
        "vector": solve_vector,
    } for precision in (100, 160)]
    return {
        "48J_matrix": [[str(item) for item in row] for row in b],
        "I_diagonal": [str(item) for item in a],
        "assembler_sha256": M._SELF["sha256"],
        "authorization_binding": authorization,
        "complete_manifest_binding": manifest,
        "dependency_sha256": M.dependency_record(),
        "dimension": 27,
        "eigenvalue_optimality_rigorous": False,
        "exact_margin": "1",
        "exact_quotient": "2",
        "exact_rational_denominator": "1",
        "exact_rational_numerator": "2",
        "finite_space_crosses_one": True,
        "format": "frontier-active25-inner-D16-conditional-pencil-v6",
        "independent_arithmetic_reconstruction": False,
        "ledger_binding": {
            "device": ledger["device"], "inode": ledger["inode"],
            "path": "/tmp/records/ledger.json", "sha256": ledger["sha256"]},
        "parameters": M.staged.v5.v2.core.parameter_record(),
        "precision_discovery": solves,
        "producer_driver_sha256": M.PINNED[M.STAGED],
        "rational_denominator_limit": 10**18,
        "rational_vector": [str(item) for item in vector],
        "serialized_stage_arithmetic_conditional": True,
        "shell_domain_counts": {"hh": 1, "hl": 2, "ll": 3},
        "stage_bindings": stages,
        "status": "CONDITIONAL_DISCOVERY_ONLY",
        "theorem_ready": False,
        "two_precision_gate": {
            "precisions": [100, 160],
            "quotient_absolute_tolerance": "1e-70",
            "relative_residual_maximum": "1e-70",
        },
    }, ledger


class AssemblerV6Tests(unittest.TestCase):
    def test_01_startup_source_and_complete_transitive_closure(self):
        self.assertEqual(M.bind_startup_self(digest(SOURCE)), SOURCE.read_bytes())
        self.assertEqual(M.staged.bind_startup_self(M.PINNED[M.STAGED]),
                         M.STAGED.read_bytes())
        closure = M.closure_snapshot(digest(SOURCE))
        self.assertIn("shell", closure["transitive_dependencies"])
        with self.assertRaises(RuntimeError):
            M.bind_startup_self("0" * 64)

    def test_02_conditional_result_exactly_recontracts(self):
        result, ledger = fake_result()
        self.assertTrue(M.strict_result(result, "2" * 64, ledger, "3" * 64))
        self.assertIs(result["theorem_ready"], False)
        self.assertIs(result["independent_arithmetic_reconstruction"], False)
        self.assertIs(result["serialized_stage_arithmetic_conditional"], True)

    def test_03_factor48_margin_and_claim_mutations_reject(self):
        for mutate in (
                lambda row: row.update(theorem_ready=True),
                lambda row: row.update(independent_arithmetic_reconstruction=True),
                lambda row: row.update(exact_margin="2"),
                lambda row: row["48J_matrix"][0].__setitem__(0, "96"),
                lambda row: row.update(finite_space_crosses_one=False),
                lambda row: row["I_diagonal"].__setitem__(0, True)):
            with self.subTest(mutate=mutate):
                result, ledger = fake_result()
                mutate(result)
                with self.assertRaises((ValueError, ArithmeticError, TypeError)):
                    M.strict_result(result, "2" * 64, ledger, "3" * 64)

    def test_04_cross_factor_is_48_once_without_extra_two(self):
        raw = [Q(5), Q(7), Q(0)]
        masses = [Q(2), Q(3)]
        shell = [[Q(11), Q(13)], [Q(13), Q(17)]]
        a, b = M.v5_assembler.assemble_exact_matrices(
            Q(19), Q(23), raw, [0, 1], masses, shell, k=48)
        self.assertEqual(a, [Q(19), Q(2), Q(3)])
        self.assertEqual(b[0][1], 48 * raw[0])
        self.assertEqual(b[0][2], 48 * raw[1])
        self.assertEqual(b[1][0], b[0][1])
        with self.assertRaises(ValueError):
            M.v5_assembler.assemble_exact_matrices(
                Q(19), Q(23), raw, [0, 1], masses, shell, k=96)

    def test_05_stage_binding_alias_and_inactive_tail_reject(self):
        result, ledger = fake_result()
        result["stage_bindings"][1]["inode"] = \
            result["stage_bindings"][0]["inode"]
        with self.assertRaises(ValueError):
            M.strict_result(result, "2" * 64, ledger, "3" * 64)
        shard = {
            "common_r": 25, "complete_common_r": True,
            "domain_counts": {"rh": 1, "rl": 1, "vh": 1, "vl": 1},
            "faces": 1, "geometric_group_count": 1, "inner_48J": "1",
            "inner_I": "1", "inner_basis_dimension": 307,
            "nonzero_group_count": 1,
            "raw_J_cross_by_target_R": ["0"] * 49,
        }
        shard["raw_J_cross_by_target_R"][26] = "1"
        with self.assertRaises(ValueError):
            M.staged.strict_v6_shard(shard)

    def test_06_live_postrun_read_may_follow_deadline_but_not_start(self):
        boot = M.staged.BOOT_ID_PATH.read_text().strip()
        ledger = {"boot_id": boot, "start_monotonic_ns": 10,
                  "deadline_monotonic_ns": 20}
        with mock.patch.object(M.time, "monotonic_ns", return_value=25):
            self.assertEqual(M._fresh_live_observation(ledger), 25)
        with mock.patch.object(M.time, "monotonic_ns", return_value=9):
            with self.assertRaises(RuntimeError):
                M._fresh_live_observation(ledger)

    def test_07_external_result_inode_replacement_rejects(self):
        result, _ = fake_result()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            path.write_bytes(M.staged.canonical_json(result))
            value, snapshot = M._read_external(path, digest(path))
            self.assertEqual(value, result)
            replacement = Path(directory) / "replacement.json"
            replacement.write_bytes(path.read_bytes())
            os.replace(replacement, path)
            with self.assertRaises(RuntimeError):
                M._rebind_external(path, snapshot)

    def test_08_existing_output_is_never_overwritten(self):
        result, _ = fake_result()
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            output_dir = Path(directory) / "output"
            record.mkdir()
            output_dir.mkdir()
            target = output_dir / "result.json"
            target.write_bytes(b"foreign\n")
            authorization = Path(directory) / "authorization.json"
            authorization.write_bytes(b"{}\n")
            context = {
                "authorization": {"path": str(authorization)},
                "handle": M.staged.v5.open_record_dir(record),
            }
            try:
                with mock.patch.object(M, "rebind_completed", return_value=1):
                    with self.assertRaises(FileExistsError):
                        M.publish_output(
                            target, result, context, "2" * 64,
                            M.PINNED[M.STAGED], digest(SOURCE))
                self.assertEqual(target.read_bytes(), b"foreign\n")
            finally:
                M.staged.v5.close_record_dir(context["handle"])

    def test_09_imported_invocation_is_not_production_cli(self):
        with self.assertRaises(RuntimeError):
            M._direct_cli_identity(digest(SOURCE))


if __name__ == "__main__":
    unittest.main()
