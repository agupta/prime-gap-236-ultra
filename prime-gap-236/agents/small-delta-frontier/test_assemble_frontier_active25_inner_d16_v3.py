#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("assemble_frontier_active25_inner_d16_v3.py")
SPEC = importlib.util.spec_from_file_location("assemble_active25_v3", SOURCE)
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


def fake_stage(r):
    return {
        "arithmetic_core_sha256":
            M.staged.v2.PINNED[M.staged.v2.CORE_PATH],
        "complete_common_r": True,
        "dependency_sha256": M.staged.dependency_record(),
        "driver_sha256": M.staged.sha256(M.staged.FILE),
        "format": "frontier-active25-inner-D16-common-r-stage-v3",
        "gate_sha256": M.staged.PINNED[M.staged.GATE],
        "parameters": M.staged.v2.core.parameter_record(),
        "peak_rss_kib": 1, "shard": fake_shard(r), "status": "complete",
        "theorem_ready": False, "wall_nanoseconds": 1,
    }


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
        "eigenvalue_optimality_rigorous": False, "exact_margin": "1",
        "exact_quotient": "2", "exact_rational_denominator": "1",
        "exact_rational_numerator": "2", "finite_space_crosses_one": True,
        "format": "frontier-active25-inner-D16-exact-pencil-v3",
        "manifest_binding": {"device": 1, "inode": 2,
                             "path": "/tmp/records/manifest.json",
                             "sha256": manifest_sha},
        "parameters": M.staged.v2.core.parameter_record(),
        "precision_discovery": [solve, dict(solve, precision=160)],
        "rational_denominator_limit": 10**18, "rational_vector": vector,
        "shell_domain_counts": {"hh": 1, "hl": 2, "ll": 3},
        "stage_bindings": [
            {"leaf": M.staged.STAGE_LEAVES[r], "sha256": "0" * 64,
             "device": 1, "inode": r + 1} for r in range(26)],
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

    def test_two_precision_diagonal_oracle(self):
        solves, vector, denominator, numerator = M.discovery_and_rationalize(
            [Q(1), Q(2)], [[Q(1), Q(0)], [Q(0), Q(4)]])
        self.assertEqual([x["rayleigh_quotient"] for x in solves], ["2", "2"])
        self.assertEqual((vector, denominator, numerator),
                         ([Q(0), Q(1)], Q(2), Q(4)))

    def test_external_manifest_sha_and_stage_rebind(self):
        with tempfile.TemporaryDirectory() as directory:
            readings = iter((1_500_000, 1_500_000))
            run = M.staged.run_all(
                directory, stage_builder=fake_stage,
                mem_reader=lambda: next(readings), sleeper=lambda _: None)
            handle, snap, manifest, stages, bindings = \
                M.load_completed_manifest(directory, run["manifest_sha256"])
            try:
                self.assertEqual(len(stages), 26)
                self.assertEqual(len(bindings), 26)
                self.assertEqual(snap["sha256"], run["manifest_sha256"])
            finally:
                M.staged.close_record_dir(handle)
            first = Path(directory) / M.staged.STAGE_LEAVES[0]
            first.write_text("{}\n")
            with self.assertRaises((ValueError, RuntimeError)):
                M.load_completed_manifest(directory, run["manifest_sha256"])
            with self.assertRaises(ValueError):
                M.load_completed_manifest(directory, "A" * 64)

    def test_strict_result_exact_contraction_and_boolean_rejection(self):
        value = fake_result()
        self.assertTrue(M.strict_result(value, "a" * 64))
        bad = dict(value, finite_space_crosses_one=1)
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64)
        bad = json.loads(json.dumps(value))
        bad["48J_matrix"][0][0] = "3"
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64)
        bad = json.loads(json.dumps(value))
        bad["stage_bindings"][0]["leaf"] = "common_r_01.json"
        with self.assertRaises(ValueError):
            M.strict_result(bad, "a" * 64)

    def test_o_excl_output_and_record_alias_rejection(self):
        with tempfile.TemporaryDirectory() as parent:
            record = Path(parent) / "record"
            output_parent = Path(parent) / "output"
            record.mkdir()
            output_parent.mkdir()
            readings = iter((1_500_000, 1_500_000))
            run = M.staged.run_all(
                record, stage_builder=fake_stage,
                mem_reader=lambda: next(readings), sleeper=lambda _: None)
            value = fake_result(run["manifest_sha256"])
            target = output_parent / "result.json"
            snap = M.publish_output(target, value, record,
                                    run["manifest_sha256"])
            self.assertEqual(snap["sha256"],
                             M.sha256_bytes(M.staged.canonical_json(value)))
            with self.assertRaises(FileExistsError):
                M.publish_output(target, value, record,
                                 run["manifest_sha256"])
            with self.assertRaises(ValueError):
                M.publish_output(record / "bad.json", value, record,
                                 run["manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
