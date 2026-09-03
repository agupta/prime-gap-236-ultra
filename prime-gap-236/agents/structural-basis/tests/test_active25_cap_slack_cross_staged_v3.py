#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "code" /
          "active25_cap_slack_cross_staged_v3.py")
SPEC = importlib.util.spec_from_file_location("active25_cap_staged_v3_test",
                                              SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fake_shard(r):
    values = {label: Q(0) for label in M.pilot.pilot_labels()}
    for label in values:
        if label[0] == r:
            values[label] = Q(r + label[1] + 1, 101)
        elif label[0] == r + 1:
            values[label] = -Q(r + label[1] + 1, 103)
    shard = {
        "format": M.SHARD_FORMAT,
        "common_r": r,
        "basis": [list(label) for label in M.pilot.pilot_labels()],
        "raw_J_cross_by_label": M._label_rows(values),
        "faces": 35 - r,
        "literal_weighted_terms": 10 + r,
        "geometric_groups": 5 + r,
        "nonzero_groups": 4 + r,
        "complete_common_r": True,
        "selected_h": None,
        "inner_I": "3/2",
        "inner_48J": "7/5",
        "theorem_ready": False,
    }
    M.strict_shard(shard, r)
    return shard


def make_authorization(parent, record):
    path = Path(parent) / "root-authorization.json"
    value = {
        "driver_sha256": digest(SOURCE),
        "format": M.AUTHORIZATION_FORMAT,
        "gate_sha256": M.PINNED[M.GATE_ARTIFACT],
        "independent_prelaunch_report_sha256": "a" * 64,
        "max_total_wall_seconds": M.MAX_TOTAL_WALL_SECONDS,
        "one_shot_attempt_authorized": True,
        "record_directory": str(Path(record).resolve()),
        "status": "ROOT_AUTHORIZED_AFTER_INDEPENDENT_PRELAUNCH_PASS",
        "theorem_ready": False,
        "workers": 1,
    }
    path.write_bytes(M.canonical_json(value))
    return path, digest(path)


def fake_runner(fail_r=None):
    def run(r, ledger, authorization, source_sha):
        if r == fail_r:
            raise RuntimeError("synthetic interruption")
        return {
            "format": M.CHILD_FORMAT,
            "status": "complete",
            "driver_sha256": source_sha,
            "dependency_sha256": M.dependency_record(),
            "gate_sha256": M.PINNED[M.GATE_ARTIFACT],
            "ledger_binding": ledger,
            "root_authorization_binding": authorization,
            "shard": fake_shard(r),
            "wall_seconds": Q(1, 10).__float__(),
            "peak_rss_kib": 4096,
            "workers": 1,
            "theorem_ready": False,
        }
    return run


class Active25CapStagedV3Tests(unittest.TestCase):
    def test_01_disabled_preflight_and_fixed_bounds(self):
        row = M.preflight()
        self.assertEqual(row["status"], "PRELAUNCH_CANDIDATE")
        self.assertIs(row["launch_authorized"], False)
        self.assertIs(row["target_started"], False)
        self.assertIs(row["one_shot_no_resume"], True)
        self.assertEqual(row["common_r_shards"], list(range(26)))
        self.assertEqual(M.MAX_TOTAL_WALL_SECONDS, 7200)
        self.assertEqual(M.MAX_CHILD_WALL_SECONDS, 600)
        self.assertEqual(M.MAX_CHILD_RSS_KIB, 262144)
        self.assertEqual(M.load_gate()["resource_gate"]["wall_pass"], True)

    def test_02_source_and_authorization_are_externally_bound(self):
        source_sha = digest(SOURCE)
        self.assertEqual(M.bind_startup_self(source_sha), SOURCE.read_bytes())
        with self.assertRaises(RuntimeError):
            M.bind_startup_self("0" * 64)
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            record.mkdir()
            auth, auth_sha = make_authorization(directory, record)
            handle = M._open_authorization(auth, auth_sha, record, source_sha)
            try:
                self.assertEqual(
                    M._validate_authorization(handle, record, source_sha),
                    M.authorization_binding(handle))
                replacement = Path(directory) / "replacement.json"
                replacement.write_bytes(auth.read_bytes())
                os.replace(replacement, auth)
                with self.assertRaises(RuntimeError):
                    M._validate_authorization(handle, record, source_sha)
            finally:
                M._close_authorization(handle)

    def test_03_shard_adjacent_support_and_complete_merge(self):
        shards = [fake_shard(r) for r in range(26)]
        merged = M.merge_shards(shards)
        self.assertEqual(merged["faces"], 585)
        self.assertEqual(len(merged["raw_J_cross_by_label"]), 38)
        self.assertEqual(merged["inner_I"], "3/2")
        bad = fake_shard(10)
        bad["raw_J_cross_by_label"][0][2] = "1"
        with self.assertRaises(ValueError):
            M.strict_shard(bad, 10)
        with self.assertRaises(ValueError):
            M.merge_shards(shards[:-1])

    def test_04_synthetic_one_shot_completes_and_cannot_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            record.mkdir()
            auth, auth_sha = make_authorization(directory, record)
            source_sha = digest(SOURCE)
            ledger = M.initialize_ledger(
                record, auth, auth_sha, source_sha)
            manifest = M.run_one_shot(
                record, auth, auth_sha, source_sha, M.binding(ledger),
                runner=fake_runner())
            self.assertEqual(set(os.listdir(record)), set(M.ALLOWED_LEAVES))
            context = M.open_completed(
                record, auth, auth_sha, source_sha, M.binding(ledger),
                manifest["sha256"])
            try:
                self.assertEqual(context["manifest"]["merged_cross"]["faces"],
                                 585)
                self.assertEqual(len(context["children"]), 26)
            finally:
                M.close_completed(context)
            with self.assertRaises(ValueError):
                M.run_one_shot(
                    record, auth, auth_sha, source_sha, M.binding(ledger),
                    runner=fake_runner())

    def test_05_interruption_abandons_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            record.mkdir()
            auth, auth_sha = make_authorization(directory, record)
            source_sha = digest(SOURCE)
            ledger = M.initialize_ledger(
                record, auth, auth_sha, source_sha)
            with self.assertRaises(RuntimeError):
                M.run_one_shot(
                    record, auth, auth_sha, source_sha, M.binding(ledger),
                    runner=fake_runner(fail_r=2))
            self.assertEqual(set(os.listdir(record)),
                             {M.LEDGER_LEAF, *M.STAGE_LEAVES[:2]})
            with self.assertRaises(ValueError):
                M.run_one_shot(
                    record, auth, auth_sha, source_sha, M.binding(ledger),
                    runner=fake_runner())
            self.assertFalse((record / M.MANIFEST_LEAF).exists())

    def test_06_normal_optimized_preflight_identical_and_no_attempt_path(self):
        commands = ([sys.executable, str(SOURCE), "--preflight-only"],
                    [sys.executable, "-O", str(SOURCE), "--preflight-only"])
        rows = [subprocess.run(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
                for command in commands]
        self.assertEqual([row.returncode for row in rows], [0, 0])
        self.assertEqual(rows[0].stderr, rows[1].stderr)
        self.assertEqual(rows[0].stdout, rows[1].stdout)
        self.assertIs(json.loads(rows[0].stdout)["launch_authorized"], False)
        self.assertNotIn("attempt_001", SOURCE.read_text())


if __name__ == "__main__":
    unittest.main()
