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


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("frontier_active25_inner_d16_staged_v6.py")
SPEC = importlib.util.spec_from_file_location("active25_staged_v6_test", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
BOOT = "12345678-1234-1234-1234-123456789abc"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fake_shard(r):
    vector = [Q(0)] * (M.v5.v2.core.K + 1)
    vector[r] = Q(r + 1, 17)
    if r + 1 < 26:
        vector[r + 1] = -Q(r + 1, 31)
    return {
        "common_r": r,
        "complete_common_r": True,
        "domain_counts": {"rh": 1, "rl": 1, "vh": 1, "vl": 1},
        "faces": 1,
        "geometric_group_count": 1,
        "inner_48J": "7/5",
        "inner_I": "3/2",
        "inner_basis_dimension": 307,
        "nonzero_group_count": 1,
        "raw_J_cross_by_target_R": [str(x) for x in vector],
    }


class FakeRuntime:
    def __init__(self, now=1_000_000_000_000, *, boot=BOOT, fail_r=None,
                 hook=None, child_ns=1_000_000_000, memory=1_500_000):
        self.now = now
        self.boot = boot
        self.fail_r = fail_r
        self.hook = hook
        self.child_ns = child_ns
        self.memory = memory
        self.children = []

    def monotonic_ns(self):
        return self.now

    def boot_id(self):
        return self.boot

    def mem_available_kib(self):
        return self.memory

    def sleep(self, seconds):
        self.now += int(seconds * 10**9)

    def run_child(self, r, timeout_seconds, ledger_row, authorization_row):
        self.children.append((r, timeout_seconds))
        if self.hook is not None:
            self.hook(r)
        self.now += self.child_ns
        if self.fail_r == r:
            raise RuntimeError("synthetic child failure")
        return M.canonical_json({
            "arithmetic_core_sha256":
                M.v5.v2.PINNED[M.v5.v2.CORE_PATH],
            "authorization_binding": authorization_row,
            "dependency_sha256": M.dependency_record(),
            "driver_sha256": M._SELF["sha256"],
            "format": M.runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v6",
                "synthetic-test"),
            "gate_sha256": M.SYNTHETIC_GATE_SHA256,
            "ledger_binding": ledger_row,
            "parameters": M.v5.v2.core.parameter_record(),
            "shard": fake_shard(r),
            "status": "complete",
            "theorem_ready": False,
        })


def make_authorization(parent, record):
    path = Path(parent) / "root-launch-authorization.json"
    value = {
        "driver_sha256": digest(SOURCE),
        "format":
            "frontier-active25-inner-D16-v6-root-launch-authorization-v1",
        "gate_sha256": M.PINNED[M.GATE],
        "independent_prelaunch_report_sha256": "a" * 64,
        "max_total_wall_seconds": 14_400,
        "one_shot_attempt_authorized": True,
        "record_directory": str(Path(record).resolve()),
        "status": "ROOT_AUTHORIZED_AFTER_INDEPENDENT_PRELAUNCH_PASS",
        "theorem_ready": False,
        "workers": 1,
    }
    path.write_bytes(M.canonical_json(value))
    return path, digest(path)


class V6Tests(unittest.TestCase):
    def test_01_prelaunch_gate_is_explicitly_unauthorized(self):
        gate = M.load_gate()
        self.assertEqual(gate["status"], "PRELAUNCH_CANDIDATE")
        self.assertIs(gate["launch_authorized"], False)
        self.assertIs(M.preflight()["target_started"], False)
        self.assertIs(M.preflight()["one_shot_no_resume"], True)
        source = SOURCE.read_text()
        self.assertNotIn("_REAL_", source)
        self.assertFalse(hasattr(M, "run_all"))

    def test_02_startup_self_hash_and_inode_are_retained(self):
        expected = digest(SOURCE)
        self.assertEqual(M.bind_startup_self(expected), SOURCE.read_bytes())
        with self.assertRaises(RuntimeError):
            M.bind_startup_self("0" * 64)
        with tempfile.TemporaryDirectory() as directory:
            replacement = Path(directory) / "replacement.py"
            replacement.write_bytes(SOURCE.read_bytes())
            original = M.FILE
            try:
                M.FILE = replacement
                with self.assertRaises(RuntimeError):
                    M.bind_startup_self(expected)
            finally:
                M.FILE = original
        self.assertEqual(M.bind_startup_self(expected), SOURCE.read_bytes())

    def test_03_root_authorization_snapshot_rebind_and_hardlink(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            record.mkdir()
            auth, auth_sha = make_authorization(directory, record)
            handle = M._open_authorization(
                auth, auth_sha, record, digest(SOURCE))
            try:
                self.assertEqual(
                    M._validate_authorization(handle, record, digest(SOURCE)),
                    M.authorization_binding(handle))
                same = Path(directory) / "same.json"
                same.write_bytes(auth.read_bytes())
                os.replace(same, auth)
                with self.assertRaises(RuntimeError):
                    M._validate_authorization(handle, record, digest(SOURCE))
            finally:
                M._close_authorization(handle)
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            record.mkdir()
            auth, auth_sha = make_authorization(directory, record)
            os.link(auth, Path(directory) / "auth-hardlink.json")
            with self.assertRaises(RuntimeError):
                M._open_authorization(auth, auth_sha, record, digest(SOURCE))

    def test_04_synthetic_one_shot_completes_and_never_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime()
            ledger = M._initialize_test_only(directory, runtime)
            result = M._run_test_only(
                directory, runtime, M.ledger_binding(ledger))
            self.assertIs(result["one_shot_complete"], True)
            self.assertEqual([r for r, _ in runtime.children], list(range(26)))
            self.assertEqual(set(os.listdir(directory)), set(M.ALLOWED_LEAVES))
            with self.assertRaises(ValueError):
                M._run_test_only(
                    directory, runtime, M.ledger_binding(ledger))

    def test_05_interrupted_attempt_is_permanently_abandoned(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime(fail_r=1)
            ledger = M._initialize_test_only(directory, runtime)
            with self.assertRaises(RuntimeError):
                M._run_test_only(
                    directory, runtime, M.ledger_binding(ledger))
            self.assertEqual(set(os.listdir(directory)),
                             {M.LEDGER_LEAF, M.STAGE_LEAVES[0]})
            runtime.fail_r = None
            with self.assertRaises(ValueError):
                M._run_test_only(
                    directory, runtime, M.ledger_binding(ledger))
            self.assertFalse((Path(directory) / M.MANIFEST_LEAF).exists())

    def test_06_preexisting_fabricated_prefix_or_manifest_rejects(self):
        for leaf in (M.STAGE_LEAVES[0], M.MANIFEST_LEAF, "intruder"):
            with self.subTest(leaf=leaf), \
                    tempfile.TemporaryDirectory() as directory:
                runtime = FakeRuntime()
                ledger = M._initialize_test_only(directory, runtime)
                (Path(directory) / leaf).write_text("{}\n")
                with self.assertRaises(ValueError):
                    M._run_test_only(
                        directory, runtime, M.ledger_binding(ledger))
                self.assertEqual(runtime.children, [])

    def test_07_future_dated_stage_and_manifest_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime()
            ledger_snap = M._initialize_test_only(directory, runtime)
            handle = M.v5.open_record_dir(directory)
            try:
                ledger = M._parse_ledger(
                    handle, M.v5.read_leaf(handle, M.LEDGER_LEAF),
                    "synthetic-test", M._SELF["sha256"],
                    M.SYNTHETIC_AUTHORIZATION)
                row = M.ledger_binding(ledger_snap)
                child = json.loads(FakeRuntime().run_child(
                    0, 1, row, M.SYNTHETIC_AUTHORIZATION))
                observation = {
                    "first": {"before_monotonic_ns": ledger["start_monotonic_ns"],
                              "after_monotonic_ns": ledger["start_monotonic_ns"],
                              "mem_available_kib": 1_500_000},
                    "minimum_separation_nanoseconds": 5 * 10**9,
                    "second": {"before_monotonic_ns":
                               ledger["start_monotonic_ns"] + 5 * 10**9,
                               "after_monotonic_ns":
                               ledger["start_monotonic_ns"] + 5 * 10**9,
                               "mem_available_kib": 1_500_000},
                }
                start = ledger["start_monotonic_ns"] + 6 * 10**9
                stage = M.make_stage(child, observation, start, start + 1,
                                     "synthetic-test", M._SELF["sha256"])
                with self.assertRaises(ValueError):
                    M.strict_stage(
                        stage, 0, ledger, row, "synthetic-test",
                        M._SELF["sha256"], M.SYNTHETIC_AUTHORIZATION, start)
            finally:
                M.v5.close_record_dir(handle)

    def test_08_global_overlap_extra_leaf_and_timeout_publish_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            def inject(_):
                (Path(directory) / "intruder").write_text("x")
            runtime = FakeRuntime(hook=inject)
            ledger = M._initialize_test_only(directory, runtime)
            with self.assertRaises(ValueError):
                M._run_test_only(directory, runtime, M.ledger_binding(ledger))
            self.assertFalse((Path(directory) / M.STAGE_LEAVES[0]).exists())

        class TimeoutRuntime(FakeRuntime):
            def run_child(self, r, timeout, ledger, authorization):
                raise M.StageDeadlineExceeded("timeout")

        with tempfile.TemporaryDirectory() as directory:
            runtime = TimeoutRuntime()
            ledger = M._initialize_test_only(directory, runtime)
            with self.assertRaises(M.StageDeadlineExceeded):
                M._run_test_only(directory, runtime, M.ledger_binding(ledger))
            self.assertEqual(os.listdir(directory), [M.LEDGER_LEAF])

    def test_09_wrong_ledger_boot_deadline_and_hardlink_reject(self):
        with tempfile.TemporaryDirectory() as base:
            record = Path(base) / "record"
            record.mkdir()
            runtime = FakeRuntime()
            ledger = M._initialize_test_only(record, runtime)
            wrong = M.ledger_binding(ledger)
            wrong["sha256"] = "f" * 64
            with self.assertRaises(RuntimeError):
                M._run_test_only(record, runtime, wrong)
            os.link(record / M.LEDGER_LEAF, Path(base) / "external-ledger")
            with self.assertRaises(ValueError):
                M._run_test_only(record, runtime, M.ledger_binding(ledger))
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime()
            ledger = M._initialize_test_only(directory, runtime)
            runtime.boot = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            with self.assertRaises(RuntimeError):
                M._run_test_only(directory, runtime, M.ledger_binding(ledger))

    def test_10_imported_production_calls_and_missing_authorization_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                M._initialize_impl(
                    directory, FakeRuntime(), "production", digest(SOURCE))
            with self.assertRaises(RuntimeError):
                M._initialize_production_cli(
                    directory, digest(SOURCE), Path(directory) / "missing", "0" * 64)
            self.assertEqual(os.listdir(directory), [])

    def test_11_isolated_cli_init_then_extra_leaf_blocks_before_arithmetic(self):
        optimize = ["-O"] if not __debug__ else []
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / "record"
            record.mkdir()
            auth, auth_sha = make_authorization(directory, record)
            init = subprocess.run([
                sys.executable, *optimize, "-I", str(SOURCE),
                "--initialize-ledger-only", "--record-dir", str(record),
                "--expected-self-sha256", digest(SOURCE),
                "--authorization-file", str(auth),
                "--expected-authorization-sha256", auth_sha,
            ], capture_output=True, text=True, timeout=20, check=True)
            response = json.loads(init.stdout)
            binding = response["ledger_binding"]
            (record / "intruder").write_text("x")
            run = subprocess.run([
                sys.executable, *optimize, "-I", str(SOURCE),
                "--record-dir", str(record),
                "--expected-self-sha256", digest(SOURCE),
                "--authorization-file", str(auth),
                "--expected-authorization-sha256", auth_sha,
                "--expected-ledger-sha256", binding["sha256"],
                "--expected-ledger-device", str(binding["device"]),
                "--expected-ledger-inode", str(binding["inode"]),
            ], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(set(os.listdir(record)),
                             {M.LEDGER_LEAF, "intruder"})

    def test_12_real_supervisor_kills_reaps_and_rejects_bad_child(self):
        with self.assertRaises(M.StageDeadlineExceeded):
            M.supervise_command(
                [sys.executable, "-c", "import time; time.sleep(5)"], 0.05)
        with self.assertRaises(RuntimeError):
            M.supervise_command(
                [sys.executable, "-c", "raise SystemExit(7)"], 1)
        with self.assertRaises(RuntimeError):
            M.supervise_command([
                sys.executable, "-c",
                "import sys; print('{}'); print('bad', file=sys.stderr)"], 1)

    def test_13_inactive_count26_dimension_and_inner_I_reject(self):
        shard = fake_shard(25)
        shard["raw_J_cross_by_target_R"][26] = "1"
        with self.assertRaises(ValueError):
            M.strict_v6_shard(shard)
        shard = fake_shard(3)
        shard["inner_basis_dimension"] = 306
        with self.assertRaises(ValueError):
            M.strict_v6_shard(shard)
        shard = fake_shard(3)
        shard["inner_I"] = "-1"
        with self.assertRaises(ValueError):
            M.strict_v6_shard(shard)

        class InactiveCountRuntime(FakeRuntime):
            def run_child(self, r, timeout_seconds, ledger_row,
                          authorization_row):
                payload = json.loads(super().run_child(
                    r, timeout_seconds, ledger_row, authorization_row))
                if r == 25:
                    payload["shard"]["raw_J_cross_by_target_R"][26] = "1"
                return M.canonical_json(payload)

        with tempfile.TemporaryDirectory() as directory:
            runtime = InactiveCountRuntime()
            ledger = M._initialize_test_only(directory, runtime)
            with self.assertRaises(ValueError):
                M._run_test_only(directory, runtime,
                                 M.ledger_binding(ledger))
            self.assertFalse((Path(directory) / M.STAGE_LEAVES[25]).exists())
            self.assertFalse((Path(directory) / M.MANIFEST_LEAF).exists())

    def test_14_transitive_dependency_inventory_and_rebind(self):
        declared = M.dependency_record()
        for path, expected in M.v5.v2.PINNED.items():
            self.assertEqual(declared[str(path.relative_to(M.REPO))], expected)
        for relative, expected in M.v5.v2.core.require_pins().items():
            self.assertEqual(declared[relative], expected)
        for relative, expected in M.v5.v2.core.shell.require_pins().items():
            self.assertEqual(declared[relative], expected)
        original = M.v5.v2.snapshots
        calls = 0

        def moving_snapshot():
            nonlocal calls
            calls += 1
            return {"generation": calls}

        try:
            M.v5.v2.snapshots = moving_snapshot
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(RuntimeError):
                    M._initialize_test_only(directory, FakeRuntime())
                self.assertEqual(os.listdir(directory), [M.LEDGER_LEAF])
        finally:
            M.v5.v2.snapshots = original


if __name__ == "__main__":
    unittest.main()
