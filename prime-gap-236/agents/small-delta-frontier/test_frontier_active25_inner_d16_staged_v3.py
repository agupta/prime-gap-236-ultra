#!/usr/bin/env python3

from __future__ import annotations

from fractions import Fraction as Q
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


FILE = Path(__file__).resolve()
SOURCE = FILE.with_name("frontier_active25_inner_d16_staged_v3.py")
SPEC = importlib.util.spec_from_file_location("active25_staged_v3", SOURCE)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def fake_shard(r, value=Q(1)):
    vector = [Q(0)] * (M.v2.core.K + 1)
    vector[r] = value
    vector[r + 1] = -value / 2
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


def fake_stage(r):
    return {
        "arithmetic_core_sha256": M.v2.PINNED[M.v2.CORE_PATH],
        "complete_common_r": True,
        "dependency_sha256": M.dependency_record(),
        "driver_sha256": M.sha256(M.FILE),
        "format": "frontier-active25-inner-D16-common-r-stage-v3",
        "gate_sha256": M.PINNED[M.GATE],
        "parameters": M.v2.core.parameter_record(),
        "peak_rss_kib": 1,
        "shard": fake_shard(r, Q(r + 1)),
        "status": "complete",
        "theorem_ready": False,
        "wall_nanoseconds": 1,
    }


class V3StagedTests(unittest.TestCase):
    def test_gate_and_preflight(self):
        gate = M.load_gate()
        self.assertIs(gate["launch_authorized"], True)
        self.assertEqual(gate["resource_gate"]["workers"], 1)
        preflight = M.preflight()
        self.assertEqual(preflight["active_common_r"], list(range(26)))
        self.assertEqual(preflight["dimension"], 27)
        self.assertEqual(len(preflight["record_leaves"]), 26)
        self.assertIs(preflight["target_started"], False)

    def test_live_resource_gate_exact_types_and_two_reads(self):
        values = iter((1_400_000, 1_500_000))
        sleeps = []
        self.assertEqual(
            M.live_resource_gate(reader=lambda: next(values),
                                 sleeper=sleeps.append),
            [1_400_000, 1_500_000])
        self.assertEqual(sleeps, [5])
        with self.assertRaises(ValueError):
            M.live_resource_gate(reader=lambda: True, sleeper=lambda _: None)
        values = iter((1_399_999, 2_000_000))
        with self.assertRaises(RuntimeError):
            M.live_resource_gate(reader=lambda: next(values),
                                 sleeper=lambda _: None)

    def test_stage_parser_is_strict_and_canonical(self):
        stage = fake_stage(3)
        data = M.canonical_json(stage)
        self.assertEqual(M.parse_stage_bytes(data, 3), stage)
        with self.assertRaises(ValueError):
            M.parse_stage_bytes(json.dumps(stage).encode(), 3)
        bad = dict(stage, complete_common_r=1)
        with self.assertRaises(ValueError):
            M.strict_stage(bad, 3)
        bad = dict(stage, wall_nanoseconds=True)
        with self.assertRaises(ValueError):
            M.strict_stage(bad, 3)
        bad = json.loads(data)
        bad["shard"]["inner_I"] = "6/4"
        with self.assertRaises(ValueError):
            M.strict_stage(bad, 3)
        with self.assertRaises(ValueError):
            M.strict_stage(stage, 4)

    def test_complete_resume_and_exact_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            readings = iter((1_500_000, 1_500_001))
            first = M.run_all(
                directory, stage_builder=fake_stage,
                mem_reader=lambda: next(readings), sleeper=lambda _: None)
            self.assertIs(first["resumed_complete"], False)
            leaves = sorted(os.listdir(directory))
            self.assertEqual(leaves,
                             sorted((*M.STAGE_LEAVES, M.MANIFEST_LEAF)))
            inodes = {leaf: os.stat(Path(directory) / leaf).st_ino
                      for leaf in leaves}
            readings = iter((1_600_000, 1_600_001))
            second = M.run_all(
                directory, stage_builder=lambda _: self.fail("recomputed"),
                mem_reader=lambda: next(readings), sleeper=lambda _: None)
            self.assertIs(second["resumed_complete"], True)
            self.assertEqual(first["manifest_sha256"],
                             second["manifest_sha256"])
            self.assertEqual(inodes, {leaf: os.stat(Path(directory) / leaf).st_ino
                                      for leaf in leaves})

    def test_corrupt_existing_and_extra_leaf_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / M.STAGE_LEAVES[0]).write_text("{}\n")
            readings = iter((1_500_000, 1_500_000))
            with self.assertRaises(ValueError):
                M.run_all(directory, stage_builder=fake_stage,
                          mem_reader=lambda: next(readings),
                          sleeper=lambda _: None)
            self.assertFalse((Path(directory) / M.MANIFEST_LEAF).exists())
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "unexpected").write_text("x")
            readings = iter((1_500_000, 1_500_000))
            with self.assertRaises(ValueError):
                M.run_all(directory, stage_builder=fake_stage,
                          mem_reader=lambda: next(readings),
                          sleeper=lambda _: None)

    def test_ancestor_swap_and_dependency_mutation_fail_closed(self):
        with tempfile.TemporaryDirectory() as parent:
            original = Path(parent) / "records"
            moved = Path(parent) / "moved"
            replacement = Path(parent) / "replacement"
            original.mkdir()
            replacement.mkdir()
            handle = M.open_record_dir(original)
            try:
                original.rename(moved)
                original.symlink_to(replacement, target_is_directory=True)
                with self.assertRaises(RuntimeError):
                    M.validate_record_dir(handle)
            finally:
                M.close_record_dir(handle)
        with tempfile.TemporaryDirectory() as directory:
            original = M.snapshots
            calls = [0]

            def changing_snapshot():
                calls[0] += 1
                value = original()
                if calls[0] >= 2:
                    value = dict(value)
                    value[M.GATE] += b"changed"
                return value

            M.snapshots = changing_snapshot
            try:
                readings = iter((1_500_000, 1_500_000))
                with self.assertRaises(RuntimeError):
                    M.run_all(directory, stage_builder=fake_stage,
                              mem_reader=lambda: next(readings),
                              sleeper=lambda _: None)
                self.assertFalse((Path(directory) /
                                  M.MANIFEST_LEAF).exists())
            finally:
                M.snapshots = original


if __name__ == "__main__":
    unittest.main()
