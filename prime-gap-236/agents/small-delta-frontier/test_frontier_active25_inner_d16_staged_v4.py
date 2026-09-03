#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
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
SOURCE = FILE.with_name("frontier_active25_inner_d16_staged_v4.py")
SPEC = importlib.util.spec_from_file_location("active25_staged_v4", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)

BOOT = "12345678-1234-1234-1234-123456789abc"


def fake_shard(r):
    vector = [Q(0)] * (M.v2.core.K + 1)
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


class FakeRuntime:
    def __init__(self, now=1_000_000_000_000, *, boot=BOOT, fail_r=None,
                 hook=None, child_ns=1_000_000_000):
        self.now = now
        self.boot = boot
        self.fail_r = fail_r
        self.hook = hook
        self.child_ns = child_ns
        self.children = []

    def monotonic_ns(self):
        return self.now

    def boot_id(self):
        return self.boot

    def mem_available_kib(self):
        return 1_500_000

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
                "frontier-active25-inner-D16-child-arithmetic-v4",
                "synthetic-test"),
            "gate_sha256": M.runtime_gate_sha256("synthetic-test"),
            "ledger_binding": ledger_row,
            "parameters": M.v2.core.parameter_record(),
            "shard": fake_shard(r), "status": "complete",
            "theorem_ready": False,
        }
        return M.canonical_json(child)


class V4Tests(unittest.TestCase):
    def test_public_entry_has_no_runtime_injection_and_gate(self):
        self.assertEqual(list(inspect.signature(M.run_all).parameters),
                         ["record_dir"])
        gate = M.load_gate()
        self.assertEqual(gate["resource_gate"]["workers"], 1)
        self.assertEqual(gate["resource_gate"]["max_total_wall_seconds"],
                         14400)
        self.assertEqual(gate["resource_gate"]["max_single_shard_seconds"],
                         600)
        self.assertIs(M.preflight()["target_started"], False)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                M._run_all(directory, FakeRuntime(), "production")
            with self.assertRaises(RuntimeError):
                M.run_all(directory)
            self.assertEqual(os.listdir(directory), [])

    def test_direct_isolated_cli_reaches_production_leaf_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "intruder").write_text("x")
            optimize = ["-O"] if not __debug__ else []
            run = subprocess.run(
                [sys.executable, *optimize, "-I", str(SOURCE),
                 "--record-dir", directory], capture_output=True, text=True,
                timeout=10)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("unauthorized leaf", run.stderr)
            self.assertNotIn("CLI", run.stderr)

    def test_full_synthetic_run_resume_and_exact_leaf_set(self):
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

    def test_immutable_start_deadline_blocks_resume_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            first = FakeRuntime(fail_r=1)
            with self.assertRaises(RuntimeError):
                M._run_all_test_only(directory, first)
            self.assertEqual(set(os.listdir(directory)),
                             {M.LEDGER_LEAF, M.STAGE_LEAVES[0]})
            ledger = json.loads((Path(directory) / M.LEDGER_LEAF).read_bytes())
            late = FakeRuntime(now=ledger["deadline_monotonic_ns"] + 1)
            with self.assertRaises(M.StageDeadlineExceeded):
                M._run_all_test_only(directory, late)
            self.assertFalse((Path(directory) / M.MANIFEST_LEAF).exists())

    def test_deadline_edges_boot_and_clock_types(self):
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
                runtime.now = ledger["start_monotonic_ns"]
                runtime.boot = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                with self.assertRaises(RuntimeError):
                    M.live_deadline_check(ledger, runtime)
                runtime.now = True
                with self.assertRaises(ValueError):
                    M.make_ledger(handle, runtime, "synthetic-test")
                runtime.now = M.MAX_CLOCK
                with self.assertRaises(OverflowError):
                    M.make_ledger(handle, runtime, "synthetic-test")
            finally:
                M.close_record_dir(handle)

    def test_resource_timestamps_and_boolean_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            handle = M.open_record_dir(directory)
            runtime = FakeRuntime(now=100)
            try:
                ledger = M.make_ledger(handle, runtime, "synthetic-test")
                observation = M.resource_observation(ledger, runtime)
                self.assertTrue(M.strict_resource(observation, ledger))
                self.assertEqual(
                    observation["second"]["before_monotonic_ns"] -
                    observation["first"]["after_monotonic_ns"], 5 * 10**9)
                bad = json.loads(json.dumps(observation))
                bad["first"]["mem_available_kib"] = True
                with self.assertRaises(ValueError):
                    M.strict_resource(bad, ledger)
            finally:
                M.close_record_dir(handle)

    def test_extra_leaf_during_child_and_zero_stage_ledger_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            def inject(_):
                (Path(directory) / "intruder").write_text("x")

            with self.assertRaises(ValueError):
                M._run_all_test_only(directory, FakeRuntime(hook=inject))
            self.assertFalse((Path(directory) / M.STAGE_LEAVES[0]).exists())
        with tempfile.TemporaryDirectory() as directory:
            handle = M.open_record_dir(directory)
            runtime = FakeRuntime()
            try:
                ledger = M.make_ledger(handle, runtime, "synthetic-test")
                M.write_leaf_exclusive(handle, M.LEDGER_LEAF,
                                       M.canonical_json(ledger))
            finally:
                M.close_record_dir(handle)
            with self.assertRaises(ValueError):
                M._run_all_test_only(directory, runtime)

    def test_ledger_and_stage_tamper_hardlink_and_noncanonical_child(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime(fail_r=1)
            with self.assertRaises(RuntimeError):
                M._run_all_test_only(directory, runtime)
            ledger_path = Path(directory) / M.LEDGER_LEAF
            ledger = json.loads(ledger_path.read_bytes())
            ledger["deadline_monotonic_ns"] -= 1
            ledger_path.write_bytes(M.canonical_json(ledger))
            with self.assertRaises(ValueError):
                M._run_all_test_only(directory, runtime)
        with tempfile.TemporaryDirectory() as directory:
            handle = M.open_record_dir(directory)
            runtime = FakeRuntime()
            try:
                ledger = M.make_ledger(handle, runtime, "synthetic-test")
                ledger_snap = M.write_leaf_exclusive(
                    handle, M.LEDGER_LEAF, M.canonical_json(ledger))
                os.link(M.LEDGER_LEAF, M.STAGE_LEAVES[0],
                        src_dir_fd=handle["descriptor"],
                        dst_dir_fd=handle["descriptor"])
            finally:
                M.close_record_dir(handle)
            with self.assertRaises((ValueError, RuntimeError)):
                M._run_all_test_only(directory, runtime)
        row = {"leaf": M.LEDGER_LEAF, "sha256": "0" * 64,
               "device": 1, "inode": 2}
        child = FakeRuntime().run_child(0, 1, row)
        with self.assertRaises(ValueError):
            M.parse_child_bytes(child + b" ", 0, row, "synthetic-test")

    def test_synthetic_artifacts_are_disjoint_from_production(self):
        with tempfile.TemporaryDirectory() as directory:
            run = M._run_all_test_only(directory, FakeRuntime())
            ledger = json.loads((Path(directory) / M.LEDGER_LEAF).read_bytes())
            stage = json.loads((Path(directory) / M.STAGE_LEAVES[0]).read_bytes())
            manifest = json.loads((Path(directory) / M.MANIFEST_LEAF).read_bytes())
            self.assertEqual(ledger["gate_sha256"], M.SYNTHETIC_GATE_SHA256)
            self.assertEqual(stage["gate_sha256"], M.SYNTHETIC_GATE_SHA256)
            self.assertEqual(manifest["gate_sha256"], M.SYNTHETIC_GATE_SHA256)
            self.assertIn("synthetic-test", ledger["format"])
            self.assertIn("synthetic-test", stage["format"])
            self.assertIn("synthetic-test", manifest["format"])
            self.assertTrue(run["manifest_sha256"])
            handle = M.open_record_dir(directory)
            try:
                ledger_snap = M.read_leaf(handle, M.LEDGER_LEAF)
                with self.assertRaises(ValueError):
                    M._parse_ledger_snapshot(handle, ledger_snap,
                                             "production")
            finally:
                M.close_record_dir(handle)

    def test_production_runtime_monkeypatch_is_detected(self):
        self.assertTrue(M.production_runtime_intact(M._PRODUCTION_RUNTIME))
        self.assertFalse(M.production_runtime_intact(M.ProductionRuntime()))
        original = M.ProductionRuntime.__dict__["mem_available_kib"]
        try:
            M.ProductionRuntime.mem_available_kib = staticmethod(
                lambda: 9_999_999)
            self.assertFalse(M.production_runtime_intact(
                M._PRODUCTION_RUNTIME))
        finally:
            M.ProductionRuntime.mem_available_kib = original
        self.assertTrue(M.production_runtime_intact(M._PRODUCTION_RUNTIME))

    def test_real_supervisor_kills_timeout_and_rejects_nonzero(self):
        with self.assertRaises(M.StageDeadlineExceeded):
            M.supervise_command(
                [sys.executable, "-c", "import time; time.sleep(5)"], 0.05)
        with self.assertRaises(RuntimeError):
            M.supervise_command([sys.executable, "-c", "raise SystemExit(3)"],
                                1)
        with self.assertRaises(RuntimeError):
            M.supervise_command(
                [sys.executable, "-c",
                 "import sys; print('{}'); print('extra', file=sys.stderr)"],
                1)
        class TimeoutRuntime(FakeRuntime):
            def run_child(self, r, timeout_seconds, ledger_row):
                raise M.StageDeadlineExceeded("synthetic supervised timeout")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(M.StageDeadlineExceeded):
                M._run_all_test_only(directory, TimeoutRuntime())
            self.assertEqual(set(os.listdir(directory)), {M.LEDGER_LEAF})
            self.assertFalse((Path(directory) / M.STAGE_LEAVES[0]).exists())

    def test_completed_missing_replaced_and_extra_leaves_reject(self):
        for mutation in ("missing", "replaced", "extra"):
            with self.subTest(mutation=mutation), \
                    tempfile.TemporaryDirectory() as directory:
                runtime = FakeRuntime()
                M._run_all_test_only(directory, runtime)
                stage = Path(directory) / M.STAGE_LEAVES[7]
                if mutation == "missing":
                    stage.unlink()
                elif mutation == "replaced":
                    stage.write_text("{}\n")
                else:
                    (Path(directory) / "late-extra").write_text("x")
                with self.assertRaises((ValueError, RuntimeError,
                                        FileNotFoundError)):
                    M._run_all_test_only(directory, runtime)

    def test_deleted_ledger_and_symlink_stage_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime(fail_r=1)
            with self.assertRaises(RuntimeError):
                M._run_all_test_only(directory, runtime)
            (Path(directory) / M.LEDGER_LEAF).unlink()
            with self.assertRaises(ValueError):
                M._run_all_test_only(directory, runtime)
        with tempfile.TemporaryDirectory() as directory:
            runtime = FakeRuntime(fail_r=1)
            with self.assertRaises(RuntimeError):
                M._run_all_test_only(directory, runtime)
            stage = Path(directory) / M.STAGE_LEAVES[0]
            stage.unlink()
            stage.symlink_to(Path(directory) / M.LEDGER_LEAF)
            with self.assertRaises((ValueError, RuntimeError, OSError)):
                M._run_all_test_only(directory, runtime)


if __name__ == "__main__":
    unittest.main()
