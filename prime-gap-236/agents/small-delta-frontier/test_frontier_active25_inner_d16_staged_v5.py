#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("frontier_active25_inner_d16_staged_v5.py")
SPEC = importlib.util.spec_from_file_location("active25_staged_v5_test", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)

BOOT = "12345678-1234-1234-1234-123456789abc"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fake_shard(r):
    vector = [Q(0)] * (M.v2.core.K + 1)
    vector[r] = Q(r + 1, 17)
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

    def run_child(self, r, timeout_seconds, ledger_row):
        self.children.append((r, timeout_seconds))
        if self.hook is not None:
            self.hook(r)
        self.now += self.child_ns
        if self.fail_r == r:
            raise RuntimeError("synthetic child failure")
        child = {
            "arithmetic_core_sha256": M.v2.PINNED[M.v2.CORE_PATH],
            "dependency_sha256": M.dependency_record(),
            "driver_sha256": M.sha256(M.FILE),
            "format": M.runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v5",
                "synthetic-test"),
            "gate_sha256": M.SYNTHETIC_GATE_SHA256,
            "ledger_binding": ledger_row,
            "parameters": M.v2.core.parameter_record(),
            "shard": fake_shard(r),
            "status": "complete",
            "theorem_ready": False,
        }
        return M.canonical_json(child)


class V5Tests(unittest.TestCase):
    def test_01_gate_and_import_api_have_no_production_dispatch(self):
        gate = M.load_gate()
        self.assertEqual(gate["resource_gate"]["workers"], 1)
        self.assertEqual(gate["resource_gate"]["max_total_wall_seconds"],
                         14_400)
        self.assertEqual(gate["resource_gate"]["max_single_shard_seconds"],
                         600)
        source = SOURCE.read_text()
        self.assertNotIn("_REAL_", source)
        self.assertFalse(hasattr(M, "run_all"))
        self.assertFalse(hasattr(M, "initialize_ledger"))
        self.assertFalse(hasattr(M, "_run_existing"))
        self.assertEqual(
            list(inspect.signature(M._run_all_test_only).parameters),
            ["record_dir", "runtime"])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                M._initialize_ledger_impl(
                    directory, FakeRuntime(), "production")
            self.assertEqual(os.listdir(directory), [])
            with self.assertRaises(RuntimeError):
                M._initialize_ledger_production_cli(directory, digest(SOURCE))
            self.assertEqual(os.listdir(directory), [])

    def test_02_isolated_cli_initializes_only_externally_bindable_ledger(self):
        optimize = ["-O"] if not __debug__ else []
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable, *optimize, "-I", str(SOURCE),
                "--initialize-ledger-only", "--record-dir", directory,
                "--expected-self-sha256", digest(SOURCE),
            ]
            run = subprocess.run(command, capture_output=True, text=True,
                                 timeout=20, check=True)
            response = json.loads(run.stdout)
            self.assertEqual(response["status"], "initialized-ledger-only")
            self.assertEqual(os.listdir(directory), [M.LEDGER_LEAF])
            ledger_path = Path(directory) / M.LEDGER_LEAF
            observed = ledger_path.stat()
            binding = response["ledger_binding"]
            self.assertEqual(binding, {
                "leaf": M.LEDGER_LEAF,
                "sha256": digest(ledger_path),
                "device": observed.st_dev,
                "inode": observed.st_ino,
            })
            self.assertEqual(observed.st_nlink, 1)
            wrong = [
                sys.executable, *optimize, "-I", str(SOURCE),
                "--record-dir", directory,
                "--expected-self-sha256", digest(SOURCE),
                "--expected-ledger-sha256", "f" * 64,
                "--expected-ledger-device", str(observed.st_dev),
                "--expected-ledger-inode", str(observed.st_ino),
            ]
            rejected = subprocess.run(wrong, capture_output=True, text=True,
                                      timeout=20)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(os.listdir(directory), [M.LEDGER_LEAF])

    def test_03_cli_wrong_self_and_nonempty_initialization_reject(self):
        optimize = ["-O"] if not __debug__ else []
        with tempfile.TemporaryDirectory() as directory:
            wrong = subprocess.run([
                sys.executable, *optimize, "-I", str(SOURCE),
                "--initialize-ledger-only", "--record-dir", directory,
                "--expected-self-sha256", "0" * 64,
            ], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(wrong.returncode, 0)
            self.assertEqual(os.listdir(directory), [])
            (Path(directory) / "intruder").write_text("x")
            nonempty = subprocess.run([
                sys.executable, *optimize, "-I", str(SOURCE),
                "--initialize-ledger-only", "--record-dir", directory,
                "--expected-self-sha256", digest(SOURCE),
            ], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(nonempty.returncode, 0)
            self.assertEqual(os.listdir(directory), ["intruder"])

    def test_04_synthetic_run_resume_and_external_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime()
            first = M._run_all_test_only(directory, runtime)
            self.assertIs(first["resumed_complete"], False)
            self.assertEqual(set(os.listdir(directory)), set(M.ALLOWED_LEAVES))
            self.assertEqual([r for r, _ in runtime.children], list(range(26)))
            second = M._run_all_test_only(directory, runtime)
            self.assertIs(second["resumed_complete"], True)
            self.assertEqual(first["manifest_sha256"],
                             second["manifest_sha256"])
            handle = M.open_record_dir(directory)
            try:
                ledger = M.read_leaf(handle, M.LEDGER_LEAF)
            finally:
                M.close_record_dir(handle)
            wrong = M.ledger_binding(ledger)
            wrong["sha256"] = "f" * 64
            with self.assertRaises(RuntimeError):
                M._run_existing_impl(
                    directory, runtime, "synthetic-test", wrong)

    def test_05_synthetic_bytes_are_production_incompatible(self):
        with tempfile.TemporaryDirectory() as directory:
            M._run_all_test_only(directory, FakeRuntime())
            ledger = json.loads((Path(directory) / M.LEDGER_LEAF).read_bytes())
            stage = json.loads((Path(directory) / M.STAGE_LEAVES[0]).read_bytes())
            manifest = json.loads((Path(directory) / M.MANIFEST_LEAF).read_bytes())
            for value in (ledger, stage, manifest):
                self.assertEqual(value["gate_sha256"],
                                 M.SYNTHETIC_GATE_SHA256)
                self.assertIn("synthetic-test", value["format"])
            handle = M.open_record_dir(directory)
            try:
                snap = M.read_leaf(handle, M.LEDGER_LEAF)
                with self.assertRaises(ValueError):
                    M._parse_ledger_snapshot(handle, snap, "production")
            finally:
                M.close_record_dir(handle)

    def test_06_deadline_is_immutable_across_resume_and_boot(self):
        with tempfile.TemporaryDirectory() as directory:
            first = FakeRuntime(fail_r=1)
            with self.assertRaises(RuntimeError):
                M._run_all_test_only(directory, first)
            ledger = json.loads((Path(directory) / M.LEDGER_LEAF).read_bytes())
            self.assertEqual(set(os.listdir(directory)),
                             {M.LEDGER_LEAF, M.STAGE_LEAVES[0]})
            late = FakeRuntime(now=ledger["deadline_monotonic_ns"] + 1)
            with self.assertRaises(M.StageDeadlineExceeded):
                M._run_all_test_only(directory, late)
            rebooted = FakeRuntime(
                now=ledger["start_monotonic_ns"],
                boot="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            with self.assertRaises(RuntimeError):
                M._run_all_test_only(directory, rebooted)

    def test_07_clock_resource_boundaries_and_boolean_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            handle = M.open_record_dir(directory)
            try:
                runtime = FakeRuntime(now=10)
                ledger = M.make_ledger(handle, runtime, "synthetic-test")
                runtime.now = ledger["deadline_monotonic_ns"]
                self.assertEqual(M.live_deadline_check(ledger, runtime),
                                 runtime.now)
                runtime.now += 1
                with self.assertRaises(M.StageDeadlineExceeded):
                    M.live_deadline_check(ledger, runtime)
                runtime.now = ledger["start_monotonic_ns"] - 1
                with self.assertRaises(M.StageDeadlineExceeded):
                    M.live_deadline_check(ledger, runtime)
                runtime.now = True
                with self.assertRaises(ValueError):
                    M.make_ledger(handle, runtime, "synthetic-test")
                runtime.now = M.MAX_CLOCK
                with self.assertRaises(OverflowError):
                    M.make_ledger(handle, runtime, "synthetic-test")
            finally:
                M.close_record_dir(handle)
        with tempfile.TemporaryDirectory() as directory:
            handle = M.open_record_dir(directory)
            runtime = FakeRuntime(now=100)
            try:
                ledger = M.make_ledger(handle, runtime, "synthetic-test")
                observation = M.resource_observation(
                    ledger, runtime, ledger["start_monotonic_ns"])
                self.assertTrue(M.strict_resource(observation, ledger))
                observation["first"]["mem_available_kib"] = True
                with self.assertRaises(ValueError):
                    M.strict_resource(observation, ledger)
            finally:
                M.close_record_dir(handle)

    def test_08_global_interval_overlap_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime()
            M._run_all_test_only(directory, runtime)
            stage0 = json.loads(
                (Path(directory) / M.STAGE_LEAVES[0]).read_bytes())
            stage1_path = Path(directory) / M.STAGE_LEAVES[1]
            stage1 = json.loads(stage1_path.read_bytes())
            stage1["resource_observation"]["first"][
                "before_monotonic_ns"] = \
                stage0["supervised_child_interval"]["end_monotonic_ns"] - 1
            stage1_path.write_bytes(M.canonical_json(stage1))
            manifest_path = Path(directory) / M.MANIFEST_LEAF
            manifest = json.loads(manifest_path.read_bytes())
            manifest["stages"][1]["sha256"] = digest(stage1_path)
            manifest_path.write_bytes(M.canonical_json(manifest))
            with self.assertRaises(ValueError):
                M._run_all_test_only(directory, runtime)

    def test_09_external_hardlinks_for_ledger_stage_manifest_reject(self):
        for leaf_kind in ("ledger", "stage", "manifest"):
            with self.subTest(leaf_kind=leaf_kind), \
                    tempfile.TemporaryDirectory() as base:
                record = Path(base) / "record"
                record.mkdir()
                runtime = FakeRuntime()
                if leaf_kind == "stage":
                    runtime.fail_r = 1
                    with self.assertRaises(RuntimeError):
                        M._run_all_test_only(record, runtime)
                    leaf = M.STAGE_LEAVES[0]
                else:
                    M._run_all_test_only(record, runtime)
                    leaf = (M.LEDGER_LEAF if leaf_kind == "ledger"
                            else M.MANIFEST_LEAF)
                os.link(record / leaf, Path(base) / f"external-{leaf_kind}")
                with self.assertRaises((ValueError, RuntimeError)):
                    M._run_all_test_only(record, runtime)

    def test_10_extra_leaf_during_child_and_timeout_publish_no_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            def inject(_):
                (Path(directory) / "intruder").write_text("x")
            with self.assertRaises(ValueError):
                M._run_all_test_only(directory, FakeRuntime(hook=inject))
            self.assertFalse((Path(directory) / M.STAGE_LEAVES[0]).exists())

        class TimeoutRuntime(FakeRuntime):
            def run_child(self, r, timeout_seconds, ledger_row):
                raise M.StageDeadlineExceeded("synthetic supervised timeout")

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(M.StageDeadlineExceeded):
                M._run_all_test_only(directory, TimeoutRuntime())
            self.assertEqual(os.listdir(directory), [M.LEDGER_LEAF])

    def test_11_real_supervisor_kills_reaps_and_rejects_bad_children(self):
        with self.assertRaises(M.StageDeadlineExceeded):
            M.supervise_command(
                [sys.executable, "-c", "import time; time.sleep(5)"], 0.05)
        with self.assertRaises(RuntimeError):
            M.supervise_command(
                [sys.executable, "-c", "raise SystemExit(3)"], 1)
        with self.assertRaises(RuntimeError):
            M.supervise_command([
                sys.executable, "-c",
                "import sys; print('{}'); print('extra', file=sys.stderr)"
            ], 1)

    def test_12_child_stage_schema_and_canonical_bytes(self):
        row = {"leaf": M.LEDGER_LEAF, "sha256": "0" * 64,
               "device": 1, "inode": 2}
        child = FakeRuntime().run_child(0, 1, row)
        with self.assertRaises(ValueError):
            M.parse_child_bytes(child + b" ", 0, row, "synthetic-test")
        value = json.loads(child)
        value["shard"]["common_r"] = True
        with self.assertRaises(ValueError):
            M.parse_child_bytes(M.canonical_json(value), 0, row,
                                "synthetic-test")

    def test_13_missing_replaced_extra_deleted_and_symlink_reject(self):
        for mutation in ("missing", "replaced", "extra", "ledger", "symlink"):
            with self.subTest(mutation=mutation), \
                    tempfile.TemporaryDirectory() as directory:
                runtime = FakeRuntime()
                M._run_all_test_only(directory, runtime)
                stage = Path(directory) / M.STAGE_LEAVES[7]
                if mutation == "missing":
                    stage.unlink()
                elif mutation == "replaced":
                    stage.write_text("{}\n")
                elif mutation == "extra":
                    (Path(directory) / "late-extra").write_text("x")
                elif mutation == "ledger":
                    (Path(directory) / M.LEDGER_LEAF).unlink()
                else:
                    stage.unlink()
                    stage.symlink_to(Path(directory) / M.LEDGER_LEAF)
                with self.assertRaises((ValueError, RuntimeError,
                                        FileNotFoundError, OSError)):
                    M._run_all_test_only(directory, runtime)


if __name__ == "__main__":
    unittest.main()
