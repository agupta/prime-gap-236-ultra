#!/usr/bin/env python3
"""Independent synthetic hostile tests for the frozen v5 run comparator.

This suite imports only the comparator under audit.  It never opens either
production result, audit result, or checkpoint directory.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve()
TARGET = HERE.parents[1] / \
    "structural-basis/code/compare_importance_d4_calibration_v5_runs.py"
SPEC = importlib.util.spec_from_file_location("importance_v5_comparator_hostile", TARGET)
if SPEC is None or SPEC.loader is None:
    raise ImportError("cannot load comparator")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
GATE_BYTES = MOD.GATE.read_bytes()
if MOD.sha256_bytes(GATE_BYTES) != MOD.GATE_SHA256:
    raise ValueError("frozen gate bytes changed")
FROZEN_GATE = MOD.strict_json_bytes(GATE_BYTES, "hostile-test frozen gate")


def make_result(auth_sha, auth_path, record_dir, *, optimized=False):
    checkpoints = [{
        "path": str((record_dir / name).resolve()),
        "sha256": f"{index + 1:064x}",
        "device": 2 if optimized else 1,
        "inode": 10_000 + index + (1_000 if optimized else 0),
    } for index, name in enumerate(MOD.expected_checkpoint_names())]
    return {
        "status": "d4-stratified-calibration-pass",
        "rigorous": False,
        "theorem_ready": False,
        "mode": "production",
        "gate_path": str(MOD.GATE.relative_to(MOD.REPO_ROOT)),
        "gate_sha256": MOD.GATE_SHA256,
        "driver_sha256": MOD.DRIVER_SHA256,
        "authorization_sha256": auth_sha,
        "parent_result_sha256": None,
        "gate_binding": {
            "path": str(MOD.GATE.resolve()),
            "sha256": MOD.GATE_SHA256,
            "device": 1,
            "inode": 101,
        },
        "authorization_binding": {
            "path": str(auth_path.resolve()),
            "sha256": auth_sha,
            "device": 2 if optimized else 1,
            "inode": 202 if optimized else 201,
        },
        "parent_result_binding": None,
        "wall_seconds": "0x1.8000000000000p+0" if optimized
                        else "0x1.0000000000000p+0",
        "peak_rss_kib": 1100 if optimized else 1000,
        "float_encoding": "python-float-hex",
        "conventions": copy.deepcopy(FROZEN_GATE["conventions"]),
        "schedule": copy.deepcopy(FROZEN_GATE["schedule"]),
        "records": [{"chain": index} for index in range(128)],
        "record_checkpoints": checkpoints,
        "analysis": {
            "gates_passed": True,
            "extension_authorized": False,
            "hard_gates": {"algebra": True},
            "statistical_gates": {"coverage": True},
        },
        "analysis_failure": None,
        "fresh_exact_reconstruction_required": True,
    }


def make_audit(result, result_sha, result_path, record_dir, auditor_sha,
               superseded_sha, *, optimized=False):
    return {
        "status": "complete-independent-d4-v5-production-audit",
        "rigorous": False,
        "theorem_ready": False,
        "scope": MOD.AUDIT_SCOPE,
        "decision": "CALIBRATION_PASS",
        "decision_exit_code": 0,
        "driver_sha256": MOD.DRIVER_SHA256,
        "gate_sha256": MOD.GATE_SHA256,
        "authorization_sha256": result["authorization_sha256"],
        "production_result_binding": {
            "path": str(result_path.resolve()),
            "sha256": result_sha,
            "device": 2 if optimized else 1,
            "inode": 302 if optimized else 301,
        },
        "decision_table_sha256": MOD.DECISION_TABLE_SHA256,
        "auditor_sha256": auditor_sha,
        "supersedes_invalid_auditor_sha256": superseded_sha,
        "record_directory_binding": {
            "path": str(record_dir.resolve()),
            "device": 2 if optimized else 1,
            "inode": 402 if optimized else 401,
        },
        "checkpoint_count": 128,
        "record_leaf_names_sha256": MOD.canonical_sha256(
            sorted(MOD.expected_checkpoint_names())),
        "checkpoint_manifest_sha256": MOD.canonical_sha256(
            result["record_checkpoints"]),
        "records_core_sha256": MOD.canonical_sha256(result["records"]),
        "analysis_core_sha256": MOD.canonical_sha256({
            "analysis": result["analysis"],
            "analysis_failure": result["analysis_failure"],
        }),
        "analysis_failure": result["analysis_failure"],
        "hard_gate_failures": [],
        "statistical_gate_failures": [],
        "wall_seconds": result["wall_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "numpy_version": MOD.NUMPY_VERSION,
        "numpy_init_sha256": MOD.NUMPY_INIT_SHA256,
        "fresh_exact_reconstruction_required": True,
        "never_implies": MOD.NEVER_IMPLIES,
    }


def fixtures(root):
    normal_dir = root / "normal-records"
    opt_dir = root / "opt-records"
    normal_dir.mkdir()
    opt_dir.mkdir()
    normal = make_result(
        MOD.NORMAL_AUTH_SHA256, MOD.NORMAL_AUTHORIZATION, normal_dir)
    optimized = make_result(
        MOD.OPT_AUTH_SHA256, MOD.OPT_AUTHORIZATION, opt_dir, optimized=True)
    normal_sha = "a" * 64
    opt_sha = "b" * 64
    normal_audit = make_audit(
        normal, normal_sha, MOD.NORMAL_RESULT, normal_dir,
        MOD.NORMAL_AUDITOR_SHA256, MOD.NORMAL_SUPERSEDED_AUDITOR_SHA256)
    opt_audit = make_audit(
        optimized, opt_sha, MOD.OPT_RESULT, opt_dir,
        MOD.OPT_AUDITOR_SHA256, MOD.OPT_SUPERSEDED_AUDITOR_SHA256,
        optimized=True)
    return (normal_dir, opt_dir, normal, optimized, normal_audit, opt_audit,
            normal_sha, opt_sha)


def compare(bundle):
    (normal_dir, opt_dir, normal, optimized, normal_audit, opt_audit,
     normal_sha, opt_sha) = bundle
    with mock.patch.object(MOD, "NORMAL_RECORDS", normal_dir), \
            mock.patch.object(MOD, "OPT_RECORDS", opt_dir):
        return MOD.compare_mathematical_payloads(
            normal, optimized, normal_audit, opt_audit,
            normal_result_sha=normal_sha,
            opt_result_sha=opt_sha,
            normal_auditor_sha=MOD.NORMAL_AUDITOR_SHA256,
            opt_auditor_sha=MOD.OPT_AUDITOR_SHA256,
            normal_result_binding=copy.deepcopy(
                normal_audit["production_result_binding"]),
            opt_result_binding=copy.deepcopy(
                opt_audit["production_result_binding"]))


class ComparatorHostileTests(unittest.TestCase):
    def test_baseline_fixture_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(compare(fixtures(Path(directory)))["decision"],
                             "CALIBRATION_PASS")

    def test_wrong_sieve_k_must_fail_closed(self):
        """Both payloads agreeing on k=47 must not authenticate a C10 k=48 run."""
        with tempfile.TemporaryDirectory() as directory:
            bundle = fixtures(Path(directory))
            bundle[2]["conventions"]["k"] = 47
            bundle[3]["conventions"]["k"] = 47
            with self.assertRaises(ValueError):
                compare(bundle)

    def test_wrong_schedule_must_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = fixtures(Path(directory))
            bundle[2]["schedule"]["chains_total"] = 127
            bundle[3]["schedule"]["chains_total"] = 127
            with self.assertRaises(ValueError):
                compare(bundle)

    def test_actual_result_inode_must_equal_audit_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = fixtures(Path(directory))
            (normal_dir, opt_dir, normal, optimized, normal_audit, opt_audit,
             normal_sha, opt_sha) = bundle
            actual_normal = copy.deepcopy(
                normal_audit["production_result_binding"])
            actual_normal["inode"] += 1
            with mock.patch.object(MOD, "NORMAL_RECORDS", normal_dir), \
                    mock.patch.object(MOD, "OPT_RECORDS", opt_dir):
                with self.assertRaises(ValueError):
                    MOD.compare_mathematical_payloads(
                        normal, optimized, normal_audit, opt_audit,
                        normal_result_sha=normal_sha,
                        opt_result_sha=opt_sha,
                        normal_auditor_sha=MOD.NORMAL_AUDITOR_SHA256,
                        opt_auditor_sha=MOD.OPT_AUDITOR_SHA256,
                        normal_result_binding=actual_normal,
                        opt_result_binding=copy.deepcopy(
                            opt_audit["production_result_binding"]))


if __name__ == "__main__":
    unittest.main()
