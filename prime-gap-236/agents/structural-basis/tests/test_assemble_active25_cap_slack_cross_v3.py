#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "code" /
          "assemble_active25_cap_slack_cross_v3.py")
SPEC = importlib.util.spec_from_file_location("active25_cap_assembler_v3_test",
                                              SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dynamic_bindings():
    ledger = {"leaf": M.staged.LEDGER_LEAF, "sha256": "1" * 64,
              "device": 7, "inode": 10}
    authorization = {"path": "/tmp/root-authorization.json",
                     "sha256": "2" * 64, "device": 7, "inode": 11}
    manifest = {"path": "/tmp/records/manifest.json",
                "sha256": "3" * 64, "device": 7, "inode": 12}
    stages = [{"leaf": M.staged.STAGE_LEAVES[r],
               "sha256": f"{r + 100:064x}",
               "device": 7, "inode": 1000 + r}
              for r in range(26)]
    return ledger, authorization, manifest, stages


def fake_result(raw_values=None):
    labels = M.staged.pilot.pilot_labels()
    if raw_values is None:
        raw_values = [Q(0) for _ in labels]
    raw = [[label[0], label[1], str(value)]
           for label, value in zip(labels, raw_values)]
    _, _, _, inner_i, inner_b = \
        M.staged.pilot.V1.A25.load_inner_coordinate()
    i_matrix, b_matrix = M.assemble_exact_pencil(inner_i, inner_b, raw)
    ledger, authorization, manifest, stages = dynamic_bindings()
    result = {
        "format": M.RESULT_FORMAT,
        "status": "CONDITIONAL_SERIALIZATION_ONLY",
        "assembler_sha256": M._SELF["sha256"],
        "producer_sha256": M.PINNED[M.STAGED],
        "dependency_sha256": M.dependency_record(),
        "parameters": M.staged.pilot.V1.A25.parameter_record(),
        "dimension": 39,
        "basis": [["radial_D16"]] + [list(label) for label in labels],
        "I_upper_nonzero": M._upper_from_dense(i_matrix),
        "48J_upper_nonzero": M._upper_from_dense(b_matrix),
        "raw_J_cross_by_label": raw,
        "cross_factor_applied_exactly_once": 48,
        "authorization_binding": authorization,
        "ledger_binding": {
            "path": "/tmp/records/ledger.json",
            "sha256": ledger["sha256"], "device": ledger["device"],
            "inode": ledger["inode"]},
        "manifest_binding": manifest,
        "stage_bindings": stages,
        "independent_reconstruction_design_sha256":
            M.staged.PINNED[M.staged.INDEPENDENT_DESIGN],
        "serialized_stage_arithmetic_conditional": True,
        "independent_arithmetic_reconstruction": False,
        "contains_vector": False,
        "contains_quotient": False,
        "eigenvalue_optimality_rigorous": False,
        "theorem_ready": False,
    }
    return result, ledger, authorization, manifest


class Active25CapAssemblerV3Tests(unittest.TestCase):
    def test_01_disabled_sparse_preflight(self):
        row = M.preflight()
        self.assertEqual(row["dimension"], 39)
        self.assertEqual(row["restricted_I_upper_nonzero"], 56)
        self.assertEqual(row["restricted_48J_upper_nonzero"], 125)
        self.assertEqual(row["cross_factor"], 48)
        self.assertIs(row["launch_authorized"], False)
        self.assertIs(row["target_started"], False)
        self.assertIs(row["contains_quotient"], False)

    def test_02_restricted_forms_have_exact_count_sparsity(self):
        labels, i_matrix, b_matrix = M.restricted_cap_forms()
        self.assertEqual(len(labels), 38)
        self.assertTrue(all(i_matrix[i][i] > 0 for i in range(38)))
        self.assertTrue(all(
            not i_matrix[i][j] or labels[i][0] == labels[j][0]
            for i in range(38) for j in range(38)))
        self.assertTrue(all(
            not b_matrix[i][j] or abs(labels[i][0] - labels[j][0]) <= 1
            for i in range(38) for j in range(38)))

    def test_03_cross_factor_is_48_once(self):
        labels = M.staged.pilot.pilot_labels()
        values = [Q(0) for _ in labels]
        values[0] = Q(5, 7)
        raw = [[label[0], label[1], str(value)]
               for label, value in zip(labels, values)]
        i_matrix, b_matrix = M.assemble_exact_pencil(Q(3, 2), Q(7, 5), raw)
        self.assertEqual(i_matrix[0][1], 0)
        self.assertEqual(b_matrix[0][1], Q(48) * Q(5, 7))
        self.assertEqual(b_matrix[1][0], b_matrix[0][1])
        with self.assertRaises(ValueError):
            M.assemble_exact_pencil(Q(3, 2), Q(7, 5), raw, k=96)

    def test_04_conditional_result_reconstructs_and_claim_mutations_reject(self):
        result, ledger, authorization, manifest = fake_result()
        self.assertTrue(M.strict_result(
            result, manifest["sha256"], ledger, authorization))
        mutations = (
            lambda row: row.update(theorem_ready=True),
            lambda row: row.update(contains_quotient=True),
            lambda row: row.update(independent_arithmetic_reconstruction=True),
            lambda row: row.update(cross_factor_applied_exactly_once=96),
            lambda row: row["48J_upper_nonzero"][0].__setitem__(2, "2"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed, ledger, authorization, manifest = fake_result()
                mutation(changed)
                with self.assertRaises((ValueError, ArithmeticError)):
                    M.strict_result(
                        changed, manifest["sha256"], ledger, authorization)

    def test_05_external_source_hashes_and_normal_optimized_preflight(self):
        self.assertEqual(M.bind_startup_self(digest(SOURCE)),
                         SOURCE.read_bytes())
        self.assertEqual(
            M.staged.bind_startup_self(M.PINNED[M.STAGED]),
            M.STAGED.read_bytes())
        with self.assertRaises(RuntimeError):
            M.bind_startup_self("0" * 64)
        commands = ([sys.executable, str(SOURCE), "--preflight-only"],
                    [sys.executable, "-O", str(SOURCE), "--preflight-only"])
        rows = [subprocess.run(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
                for command in commands]
        self.assertEqual([row.returncode for row in rows], [0, 0])
        self.assertEqual(rows[0].stderr, rows[1].stderr)
        self.assertEqual(rows[0].stdout, rows[1].stdout)
        self.assertFalse(json.loads(rows[0].stdout)["launch_authorized"])


if __name__ == "__main__":
    unittest.main()
