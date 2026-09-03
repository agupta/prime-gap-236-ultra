#!/usr/bin/env python3
"""Pin-bound hostile counterexample for the frozen active25 v4 wrapper.

No exact target shard is evaluated.  The attack leaves the public runtime
object and its class methods untouched, but replaces the mutable private
call targets used by those methods and the mutable module identity checked by
``run_all``.  The imported public entry then emits production-format records
which the frozen production assembler accepts.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
WRAPPER = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v4.py"
WRAPPER_TEST = REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v4.py"
ASSEMBLER = REPO / "agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v4.py"
ASSEMBLER_TEST = REPO / "agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v4.py"
GATE = REPO / "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v4.json"
SPEC = REPO / "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-STAGED-V4-PRELAUNCH.md"
PINS = {
    WRAPPER: "7d5188ec18ef99ae22aeada193471a69c11cf15363aa26496ef8b3217387beef",
    WRAPPER_TEST: "4082c32c1358d564f6ed17743c3ccdc471813c67df5a5a3013acd9aa1e227ac0",
    ASSEMBLER: "0b60c03e3743fe8003c9571423e79922a3ded08594d30894bee2461e980d0d85",
    ASSEMBLER_TEST: "bb2a751b0459365641e188afc0f67fea27781e7a17a04538b5f35b3bae1140db",
    GATE: "2dcfb44e4c9fbc5ec5f9b030f6565a35b06af478dff60c0805f96b44078c35fe",
    SPEC: "66b4b7de36aecd3a2b4ecbf2ea1cb5e6192c2590d24d8a61bb7bc76a327f2edb",
}


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    require(module_spec is not None and module_spec.loader is not None,
            f"cannot import {path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


def fake_shard(module, common_r):
    # These values satisfy only the public schema.  In particular, they are
    # not the output of exact_common_r_shard and the inner 48J value is an
    # intentionally false sentinel.
    return {
        "common_r": common_r,
        "complete_common_r": True,
        "domain_counts": {"rh": 0, "rl": 0, "vh": 0, "vl": 0},
        "faces": 1,
        "geometric_group_count": 0,
        "inner_48J": "999",
        "inner_I": "1",
        "inner_basis_dimension": 307,
        "nonzero_group_count": 0,
        "raw_J_cross_by_target_R": ["0"] * (module.v2.core.K + 1),
    }


class FakeTargets:
    def __init__(self, module):
        self.module = module
        self.now = 1_000_000_000_000
        self.memory_reads = 0
        self.sleeps = 0
        self.supervised = []

    def monotonic_ns(self):
        return self.now

    def mem_available_kib(self):
        self.memory_reads += 1
        return 1_500_000

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += int(seconds * 10**9)

    def supervise(self, command, timeout_seconds):
        require(0 < timeout_seconds <= 600, "bad claimed child timeout")
        def argument(name):
            return command[command.index(name) + 1]
        common_r = int(argument("--child-stage-r"))
        ledger_row = {
            "leaf": self.module.LEDGER_LEAF,
            "sha256": argument("--ledger-sha256"),
            "device": int(argument("--ledger-device")),
            "inode": int(argument("--ledger-inode")),
        }
        self.now += 1
        self.supervised.append(common_r)
        child = {
            "arithmetic_core_sha256":
                self.module.v2.PINNED[self.module.v2.CORE_PATH],
            "dependency_sha256": self.module.dependency_record(),
            "driver_sha256": self.module.sha256(self.module.FILE),
            "format": self.module.runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v4",
                "production"),
            "gate_sha256": self.module.runtime_gate_sha256("production"),
            "ledger_binding": ledger_row,
            "parameters": self.module.v2.core.parameter_record(),
            "shard": fake_shard(self.module, common_r),
            "status": "complete",
            "theorem_ready": False,
        }
        return self.module.canonical_json(child)


def build():
    for path, expected in PINS.items():
        require(sha(path) == expected, f"frozen v4 input changed: {path}")
    staged = load("hostile_active25_v4_stage", WRAPPER)
    assembler = load("hostile_active25_v4_assembler", ASSEMBLER)
    require(staged.production_runtime_intact(staged._PRODUCTION_RUNTIME),
            "production runtime did not begin intact")

    fake = FakeTargets(staged)
    original = {
        "name": staged.__name__,
        "spec": staged.__spec__,
        "argv": list(sys.argv),
        "monotonic": staged._REAL_MONOTONIC_NS,
        "sleep": staged._REAL_SLEEP,
        "memory": staged._REAL_MEM_AVAILABLE_KIB,
        "supervisor": staged._REAL_SUPERVISE_COMMAND,
    }
    with tempfile.TemporaryDirectory() as directory:
        try:
            # No class method and no _PRODUCTION_RUNTIME object is changed;
            # consequently the frozen integrity predicate remains true.
            staged._REAL_MONOTONIC_NS = fake.monotonic_ns
            staged._REAL_SLEEP = fake.sleep
            staged._REAL_MEM_AVAILABLE_KIB = fake.mem_available_kib
            staged._REAL_SUPERVISE_COMMAND = fake.supervise
            staged.__name__ = "__main__"
            staged.__spec__ = None
            sys.argv = [str(WRAPPER)]
            require(staged.production_runtime_intact(
                        staged._PRODUCTION_RUNTIME),
                    "counterexample unexpectedly tripped runtime predicate")
            run = staged.run_all(directory)
        finally:
            staged.__name__ = original["name"]
            staged.__spec__ = original["spec"]
            sys.argv = original["argv"]
            staged._REAL_MONOTONIC_NS = original["monotonic"]
            staged._REAL_SLEEP = original["sleep"]
            staged._REAL_MEM_AVAILABLE_KIB = original["memory"]
            staged._REAL_SUPERVISE_COMMAND = original["supervisor"]

        require(fake.supervised == list(range(26)) and
                fake.memory_reads == 52 and fake.sleeps == 26,
                "fake execution did not traverse all claimed gates")
        require(set(os.listdir(directory)) == set(staged.ALLOWED_LEAVES),
                "counterexample did not publish exact production leaf set")
        manifest_path = Path(directory) / staged.MANIFEST_LEAF
        manifest = json.loads(manifest_path.read_bytes())
        require(manifest["runtime_mode"] == "production" and
                manifest["gate_sha256"] == PINS[GATE] and
                all(row["runtime_mode"] == "production" for row in (
                    json.loads((Path(directory) / leaf).read_bytes())
                    for leaf in staged.STAGE_LEAVES)),
                "counterexample did not emit production-format artifacts")

        loaded = assembler.load_completed_manifest(
            directory, run["manifest_sha256"])
        handle, _, _, _, accepted_manifest, stages, _ = loaded
        try:
            require(len(stages) == 26 and
                    accepted_manifest["runtime_mode"] == "production" and
                    all(stage["shard"]["inner_48J"] == "999"
                        for stage in stages),
                    "production assembler rejected or rewrote forged shards")
        finally:
            staged.close_record_dir(handle)

    for path, expected in PINS.items():
        require(sha(path) == expected,
                f"frozen v4 input moved during attack: {path}")
    return {
        "status": "PRELAUNCH AUDIT FAIL",
        "checker_sha256": sha(FILE),
        "pinned": {str(path.relative_to(REPO)): expected
                   for path, expected in PINS.items()},
        "smallest_counterexample": {
            "mutable_module_identity_bypasses_import_guard": True,
            "mutable_private_runtime_targets_not_covered_by_integrity_check": True,
            "production_runtime_object_or_class_method_modified": False,
            "actual_meminfo_read_sleep_or_subprocess_executed": False,
            "production_format_stage_count": 26,
            "exact_production_leaf_set_emitted": True,
            "frozen_production_assembler_accepted_manifest": True,
            "deliberately_false_inner_48J_accepted": "999",
        },
        "target_exact_arithmetic_executed": False,
        "target_pencil_or_quotient_constructed": False,
        "launch_authorized_by_audit": False,
        "minimum_repair": (
            "make production a fresh isolated subprocess whose immutable "
            "entry binds an externally supplied expected driver hash; do not "
            "dispatch through mutable module-global runtime targets, and "
            "require an independent consumer to reconstruct every shard "
            "rather than authenticating self-declared stage metadata"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
