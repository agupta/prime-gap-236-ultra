#!/usr/bin/env python3

"""Synthetic tests for the normal/-O mathematical comparator."""

import copy
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve()
CODE = HERE.parents[1] / "code"
sys.path.insert(0, str(CODE))
MOD = importlib.import_module("compare_importance_d4_calibration_v5_runs")
FROZEN_GATE = json.loads(MOD.GATE.read_text())


def make_result(auth_sha, auth_path, record_dir, *,
                wall="0x1.0000000000000p+0", peak=1000):
    records = [{"chain": index} for index in range(128)]
    checkpoints = [{
        "path": str((record_dir / name).resolve()),
        "sha256": f"{index:064x}"[-64:], "device": 1, "inode": index + 1}
                   for index, name in enumerate(
                       MOD.expected_checkpoint_names())]
    return {
        "status": "d4-stratified-calibration-pass",
        "rigorous": False, "theorem_ready": False, "mode": "production",
        "gate_path": str(MOD.GATE.relative_to(MOD.REPO_ROOT)),
        "gate_sha256": MOD.GATE_SHA256,
        "driver_sha256": MOD.DRIVER_SHA256,
        "authorization_sha256": auth_sha,
        "parent_result_sha256": None,
        "gate_binding": {"path": str(MOD.GATE.resolve()),
                         "sha256": MOD.GATE_SHA256,
                         "device": 1, "inode": 2},
        "authorization_binding": {
            "path": str(auth_path.resolve()), "sha256": auth_sha,
            "device": 1, "inode": 3},
        "parent_result_binding": None,
        "wall_seconds": wall, "peak_rss_kib": peak,
        "float_encoding": "python-float-hex",
        "conventions": copy.deepcopy(FROZEN_GATE["conventions"]),
        "schedule": copy.deepcopy(FROZEN_GATE["schedule"]),
        "records": records, "record_checkpoints": checkpoints,
        "analysis": {"gates_passed": True,
                     "extension_authorized": False,
                     "hard_gates": {"algebra": True},
                     "statistical_gates": {"coverage": True}},
        "analysis_failure": None,
        "fresh_exact_reconstruction_required": True,
    }


def make_audit(result, result_sha, auditor_sha, result_path, record_dir,
               superseded_auditor_sha):
    records_core = MOD.canonical_sha256(result["records"])
    analysis_core = MOD.canonical_sha256({
        "analysis": result["analysis"],
        "analysis_failure": result["analysis_failure"]})
    return {
        "status": "complete-independent-d4-v5-production-audit",
        "rigorous": False, "theorem_ready": False,
        "scope": "D4-stratified-importance-calibration-discovery-only",
        "decision": "CALIBRATION_PASS", "decision_exit_code": 0,
        "driver_sha256": MOD.DRIVER_SHA256,
        "gate_sha256": MOD.GATE_SHA256,
        "authorization_sha256": result["authorization_sha256"],
        "production_result_binding": {
            "path": str(result_path.resolve()), "sha256": result_sha,
            "device": 1, "inode": 4},
        "decision_table_sha256": MOD.DECISION_TABLE_SHA256,
        "auditor_sha256": auditor_sha,
        "supersedes_invalid_auditor_sha256": superseded_auditor_sha,
        "record_directory_binding": {
            "path": str(record_dir.resolve()), "device": 1, "inode": 5},
        "checkpoint_count": 128,
        "record_leaf_names_sha256": MOD.canonical_sha256(
            sorted(MOD.expected_checkpoint_names())),
        "checkpoint_manifest_sha256": MOD.canonical_sha256(
            result["record_checkpoints"]),
        "records_core_sha256": records_core,
        "analysis_core_sha256": analysis_core,
        "analysis_failure": result["analysis_failure"],
        "hard_gate_failures": [], "statistical_gate_failures": [],
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "numpy_version": MOD.NUMPY_VERSION,
        "numpy_init_sha256": MOD.NUMPY_INIT_SHA256,
        "fresh_exact_reconstruction_required": True,
        "never_implies": MOD.NEVER_IMPLIES,
    }


class RunComparatorTests(unittest.TestCase):
    def test_exact_math_matches_modulo_only_declared_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            normal_dir, opt_dir = root / "normal", root / "opt"
            normal_dir.mkdir()
            opt_dir.mkdir()
            normal = make_result(
                MOD.NORMAL_AUTH_SHA256, MOD.NORMAL_AUTHORIZATION, normal_dir)
            optimized = copy.deepcopy(normal)
            optimized["authorization_sha256"] = MOD.OPT_AUTH_SHA256
            optimized["authorization_binding"] = {
                "path": str(MOD.OPT_AUTHORIZATION.resolve()),
                "sha256": MOD.OPT_AUTH_SHA256,
                "device": 2, "inode": 7}
            optimized["record_checkpoints"] = make_result(
                MOD.OPT_AUTH_SHA256, MOD.OPT_AUTHORIZATION,
                opt_dir)["record_checkpoints"]
            optimized["wall_seconds"] = "0x1.8000000000000p+0"
            optimized["peak_rss_kib"] = 1100
            normal_sha, opt_sha = "a" * 64, "b" * 64
            normal_auditor = MOD.NORMAL_AUDITOR_SHA256
            opt_auditor = MOD.OPT_AUDITOR_SHA256
            normal_audit = make_audit(
                normal, normal_sha, normal_auditor, MOD.NORMAL_RESULT,
                normal_dir, MOD.NORMAL_SUPERSEDED_AUDITOR_SHA256)
            opt_audit = make_audit(
                optimized, opt_sha, opt_auditor, MOD.OPT_RESULT,
                opt_dir, MOD.OPT_SUPERSEDED_AUDITOR_SHA256)
            opt_audit["record_directory_binding"]["device"] = 2
            opt_audit["record_directory_binding"]["inode"] = 8
            comparison_arguments = {
                "normal_result_sha": normal_sha,
                "opt_result_sha": opt_sha,
                "normal_auditor_sha": normal_auditor,
                "opt_auditor_sha": opt_auditor,
                "normal_result_binding": copy.deepcopy(
                    normal_audit["production_result_binding"]),
                "opt_result_binding": copy.deepcopy(
                    opt_audit["production_result_binding"]),
            }
            with mock.patch.object(MOD, "NORMAL_RECORDS", normal_dir), \
                    mock.patch.object(MOD, "OPT_RECORDS", opt_dir):
                result = MOD.compare_mathematical_payloads(
                    normal, optimized, normal_audit, opt_audit,
                    **comparison_arguments)
                self.assertEqual(result["decision"], "CALIBRATION_PASS")
                self.assertEqual(set(result["differing_result_keys"]),
                                 MOD.RESULT_PROVENANCE_DIFFERENCES)

                corrupted = copy.deepcopy(optimized)
                corrupted["records"][17]["chain"] = 999
                with self.assertRaisesRegex(ArithmeticError,
                                            "mathematical result"):
                    MOD.compare_mathematical_payloads(
                        normal, corrupted, normal_audit, opt_audit,
                        **comparison_arguments)

                garbage_normal = copy.deepcopy(normal)
                garbage_opt = copy.deepcopy(optimized)
                garbage_normal["status"] = "garbage-status"
                garbage_opt["status"] = "garbage-status"
                with self.assertRaisesRegex(ValueError,
                                            "identity flags"):
                    MOD.compare_mathematical_payloads(
                        garbage_normal, garbage_opt,
                        normal_audit, opt_audit,
                        **comparison_arguments)

                bad_normal_audit = copy.deepcopy(normal_audit)
                bad_opt_audit = copy.deepcopy(opt_audit)
                bad_normal_audit["decision_exit_code"] = 3
                bad_opt_audit["decision_exit_code"] = 3
                with self.assertRaisesRegex(ValueError,
                                            "provenance/core"):
                    MOD.compare_mathematical_payloads(
                        normal, optimized, bad_normal_audit, bad_opt_audit,
                        **comparison_arguments)

                duplicated = copy.deepcopy(optimized)
                duplicated["record_checkpoints"][1] = copy.deepcopy(
                    duplicated["record_checkpoints"][0])
                with self.assertRaisesRegex(ValueError,
                                            "manifest order/path"):
                    MOD.compare_mathematical_payloads(
                        normal, duplicated, normal_audit, opt_audit,
                        **comparison_arguments)

                wrong_k_normal = copy.deepcopy(normal)
                wrong_k_opt = copy.deepcopy(optimized)
                wrong_k_normal["conventions"]["k"] = 47
                wrong_k_opt["conventions"]["k"] = 47
                with self.assertRaisesRegex(ValueError,
                                            "identity flags"):
                    MOD.compare_mathematical_payloads(
                        wrong_k_normal, wrong_k_opt,
                        normal_audit, opt_audit,
                        **comparison_arguments)

                wrong_schedule_normal = copy.deepcopy(normal)
                wrong_schedule_opt = copy.deepcopy(optimized)
                wrong_schedule_normal["schedule"]["chains_total"] = 127
                wrong_schedule_opt["schedule"]["chains_total"] = 127
                with self.assertRaisesRegex(ValueError,
                                            "identity flags"):
                    MOD.compare_mathematical_payloads(
                        wrong_schedule_normal, wrong_schedule_opt,
                        normal_audit, opt_audit,
                        **comparison_arguments)

                forged_inode_audit = copy.deepcopy(normal_audit)
                forged_inode_audit["production_result_binding"]["inode"] += 1
                with self.assertRaisesRegex(ValueError,
                                            "actual result inode"):
                    MOD.compare_mathematical_payloads(
                        normal, optimized, forged_inode_audit, opt_audit,
                        **comparison_arguments)

    def test_output_rejects_record_directory_and_publication_rebinds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            normal_dir, opt_dir = root / "normal", root / "opt"
            normal_dir.mkdir()
            opt_dir.mkdir()
            with mock.patch.object(MOD, "NORMAL_RECORDS", normal_dir), \
                    mock.patch.object(MOD, "OPT_RECORDS", opt_dir):
                with self.assertRaisesRegex(ValueError, "record directory"):
                    MOD.validate_comparison_output(normal_dir / "bad.json")
                dependency = root / "dependency.json"
                dependency.write_bytes(b"pinned")
                expected = MOD.sha256_file(dependency)
                output = root / "comparison.json"
                digest = MOD.publish_report(
                    output, {"status": "synthetic-pass"},
                    {str(dependency): expected})
                self.assertEqual(digest, MOD.sha256_file(output))

                dependency2 = root / "dependency2.json"
                dependency2.write_bytes(b"before")
                expected2 = MOD.sha256_file(dependency2)
                rejected = root / "rejected.json"
                original = MOD.sha256_file
                calls = 0

                def mutate_on_second(path):
                    nonlocal calls
                    if Path(path).resolve() == dependency2.resolve():
                        calls += 1
                        if calls == 2:
                            dependency2.write_bytes(b"after")
                    return original(path)

                with mock.patch.object(MOD, "sha256_file",
                                       side_effect=mutate_on_second):
                    with self.assertRaisesRegex(ValueError,
                                                "during publication"):
                        MOD.publish_report(
                            rejected, {"status": "must-reject"},
                            {str(dependency2): expected2})
                self.assertEqual(
                    json.loads(rejected.read_text())["status"],
                    "rejected-incomplete-run-comparison")

                dependency3 = root / "dependency3.json"
                dependency3.write_bytes(b"stable")
                expected3 = MOD.sha256_file(dependency3)
                replaced = root / "replaced.json"
                original = MOD.sha256_file
                calls = 0

                def replace_output_after_input_closure(path):
                    nonlocal calls
                    answer = original(path)
                    if Path(path).resolve() == dependency3.resolve():
                        calls += 1
                        if calls == 2:
                            replaced.unlink()
                            replaced.write_bytes(b"foreign-inode")
                    return answer

                with mock.patch.object(
                        MOD, "sha256_file",
                        side_effect=replace_output_after_input_closure):
                    with self.assertRaisesRegex(
                            ArithmeticError, "final closure"):
                        MOD.publish_report(
                            replaced, {"status": "must-reject-replacement"},
                            {str(dependency3): expected3})
                # Failure handling rewrites only the held, now-unlinked owned
                # inode.  It must not damage the foreign replacement.
                self.assertEqual(replaced.read_bytes(), b"foreign-inode")

    def test_self_hash_and_completion_hashes_fail_before_reads(self):
        with mock.patch.object(
                MOD, "read_snapshot",
                side_effect=AssertionError("must not read completed input")):
            with self.assertRaises(ValueError):
                MOD.validate_expected_self("f" * 64)
            for malformed in ("", "A" * 64, "0" * 63, True):
                with self.assertRaises(ValueError):
                    MOD.require_sha256(malformed, "completion")


if __name__ == "__main__":
    unittest.main()
