#!/usr/bin/env python3
"""Pin-bound v5 resume-provenance counterexample.

This verifier initializes only a temporary production ledger through the
frozen isolated CLI, constructs canonical-but-fabricated stage/manifest bytes
without evaluating an exact shard, and demonstrates that the frozen isolated
CLI accepts them as a completed run.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
DRIVER = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_staged_v5.py"
DRIVER_TEST = REPO / "agents/small-delta-frontier/test_frontier_active25_inner_d16_staged_v5.py"
ASSEMBLER = REPO / "agents/small-delta-frontier/assemble_frontier_active25_inner_d16_v5.py"
ASSEMBLER_TEST = REPO / "agents/small-delta-frontier/test_assemble_frontier_active25_inner_d16_v5.py"
GATE = REPO / "agents/small-delta-frontier/results/frontier_active25_innerD16_tagged_shell_authorized_gate_v5.json"
SPEC = REPO / "agents/small-delta-frontier/FRONTIER-ACTIVE25-INNER-D16-STAGED-V5-PRELAUNCH.md"
PINS = {
    DRIVER: "8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775",
    DRIVER_TEST: "28b5b8d182fc0836a0bf905af4d7f9b907b403e35a9e61cae779428fb7f899bf",
    ASSEMBLER: "6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9",
    ASSEMBLER_TEST: "9d6a242a7e3b76d8cada75ee23f1ba24c7c100ff7a0d73de0d637e8166c09e74",
    GATE: "b814507140740a821d67b6ccdec65eda3c30985075a19505d8bc485c84fa2420",
    SPEC: "ef365ff9031b7166df50dba71d484996d075574bf668dccef207bf18238daf07",
}
TARGET_RECORDS = REPO / (
    "agents/small-delta-frontier/results/"
    "frontier_active25_innerD16_tagged_shell_v5_records")
TARGET_OUTPUT = REPO / (
    "agents/small-delta-frontier/results/"
    "frontier_active25_innerD16_tagged_shell_v5_exact.json")


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_driver():
    spec = importlib.util.spec_from_file_location(
        "audit_frontier_active25_v5_frozen", DRIVER)
    require(spec is not None and spec.loader is not None,
            "cannot load frozen v5 driver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == DRIVER.resolve(),
            "wrong v5 driver loaded")
    return module


def fake_shard(module, r):
    # These values satisfy only the serialized schema.  No integral is run.
    vector = [Q(0)] * (module.v2.core.K + 1)
    return {
        "common_r": r,
        "complete_common_r": True,
        "domain_counts": {"rh": 0, "rl": 0, "vh": 0, "vl": 0},
        "faces": 1,
        "geometric_group_count": 0,
        "inner_48J": "999",
        "inner_I": "1",
        "inner_basis_dimension": 307,
        "nonzero_group_count": 0,
        "raw_J_cross_by_target_R": [str(value) for value in vector],
    }


def make_stage(module, ledger, ledger_row, r, previous_end):
    # The first memory timestamp equals the preceding child end, so intervals
    # are ordered.  Five seconds is then fabricated between memory readings.
    first_before = previous_end
    first_after = first_before
    second_before = first_after + 5 * 10**9
    second_after = second_before
    child_start = second_after
    child_end = child_start + 1
    shard = fake_shard(module, r)
    child = {
        "arithmetic_core_sha256": module.v2.PINNED[module.v2.CORE_PATH],
        "dependency_sha256": module.dependency_record(),
        "driver_sha256": PINS[DRIVER],
        "format": "frontier-active25-inner-D16-child-arithmetic-v5-production",
        "gate_sha256": PINS[GATE],
        "ledger_binding": ledger_row,
        "parameters": module.v2.core.parameter_record(),
        "shard": shard,
        "status": "complete",
        "theorem_ready": False,
    }
    stage = {
        "child_stdout_sha256": module.sha256_bytes(module.canonical_json(child)),
        "dependency_sha256": module.dependency_record(),
        "driver_sha256": PINS[DRIVER],
        "format": "frontier-active25-inner-D16-common-r-stage-v5-production",
        "gate_sha256": PINS[GATE],
        "ledger_binding": ledger_row,
        "parameters": module.v2.core.parameter_record(),
        "resource_observation": {
            "first": {
                "before_monotonic_ns": first_before,
                "after_monotonic_ns": first_after,
                "mem_available_kib": 1_400_000,
            },
            "minimum_separation_nanoseconds": 5 * 10**9,
            "second": {
                "before_monotonic_ns": second_before,
                "after_monotonic_ns": second_after,
                "mem_available_kib": 1_400_000,
            },
        },
        "runtime_mode": "production",
        "shard": shard,
        "status": "complete",
        "supervised_child_interval": {
            "end_monotonic_ns": child_end,
            "start_monotonic_ns": child_start,
        },
        "supervised_child_nanoseconds": 1,
        "theorem_ready": False,
    }
    # Confirm the producer's own validator accepts each fabricated row.
    module.strict_stage(stage, r, ledger, ledger_row, "production")
    return stage, child_end


def run_counterexample():
    for path, expected in PINS.items():
        require(sha256(path) == expected, f"frozen v5 input changed: {path}")
    require(not TARGET_RECORDS.exists() and not TARGET_OUTPUT.exists(),
            "intended v5 target path already exists")
    module = load_driver()
    require(module.sha256(DRIVER) == PINS[DRIVER], "driver moved on import")
    optimize = ["-O"] if not __debug__ else []

    with tempfile.TemporaryDirectory(prefix="active25-v5-audit-") as raw:
        record_dir = Path(raw) / "records"
        record_dir.mkdir()
        initialize = subprocess.run([
            sys.executable, *optimize, "-I", str(DRIVER),
            "--initialize-ledger-only", "--record-dir", str(record_dir),
            "--expected-self-sha256", PINS[DRIVER],
        ], capture_output=True, text=True, timeout=30, check=True)
        response = json.loads(initialize.stdout)
        ledger_path = record_dir / module.LEDGER_LEAF
        ledger_data = ledger_path.read_bytes()
        ledger = json.loads(ledger_data)
        ledger_stat = ledger_path.stat()
        ledger_row = {
            "leaf": module.LEDGER_LEAF,
            "sha256": hashlib.sha256(ledger_data).hexdigest(),
            "device": int(ledger_stat.st_dev),
            "inode": int(ledger_stat.st_ino),
        }
        require(response == {"ledger_binding": ledger_row,
                             "status": "initialized-ledger-only"},
                "isolated initializer returned the wrong external anchor")

        stage_rows = []
        shards = []
        previous_end = ledger["start_monotonic_ns"]
        for r, leaf in enumerate(module.STAGE_LEAVES):
            stage, previous_end = make_stage(
                module, ledger, ledger_row, r, previous_end)
            data = module.canonical_json(stage)
            path = record_dir / leaf
            path.write_bytes(data)
            observed = path.stat()
            stage_rows.append({
                "common_r": r,
                "device": int(observed.st_dev),
                "inode": int(observed.st_ino),
                "leaf": leaf,
                "sha256": hashlib.sha256(data).hexdigest(),
            })
            shards.append(stage["shard"])
        merged, _ = module.v2.merge_exact_shards(shards)
        manifest = {
            "complete": True,
            "cumulative_supervised_child_nanoseconds": 26,
            "dependency_sha256": module.dependency_record(),
            "dimension": 27,
            "driver_sha256": PINS[DRIVER],
            "elapsed_monotonic_nanoseconds": (
                previous_end - ledger["start_monotonic_ns"]),
            "final_monotonic_ns": previous_end,
            "format": "frontier-active25-inner-D16-stage-manifest-v5-production",
            "gate_sha256": PINS[GATE],
            "ledger_binding": ledger_row,
            "merged_raw_J_cross_by_target_R": [str(value) for value in merged],
            "parameters": module.v2.core.parameter_record(),
            "record_directory": {
                "path": str(record_dir.resolve()),
                "device": int(record_dir.stat().st_dev),
                "inode": int(record_dir.stat().st_ino),
            },
            "runtime_mode": "production",
            "stages": stage_rows,
            "status": "complete",
            "theorem_ready": False,
        }
        manifest_data = module.canonical_json(manifest)
        (record_dir / module.MANIFEST_LEAF).write_bytes(manifest_data)
        before_resume = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in record_dir.iterdir()
        }

        resume = subprocess.run([
            sys.executable, *optimize, "-I", str(DRIVER),
            "--record-dir", str(record_dir),
            "--expected-self-sha256", PINS[DRIVER],
            "--expected-ledger-sha256", ledger_row["sha256"],
            "--expected-ledger-device", str(ledger_row["device"]),
            "--expected-ledger-inode", str(ledger_row["inode"]),
        ], capture_output=True, text=True, timeout=30)
        require(resume.returncode == 0,
                "counterexample unexpectedly rejected: " + resume.stderr[-1000:])
        accepted = json.loads(resume.stdout)
        require(accepted == {
                    "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
                    "resumed_complete": True,
                }, "isolated resume did not accept the fabricated completion")
        after_resume = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in record_dir.iterdir()
        }
        require(after_resume == before_resume,
                "resume unexpectedly computed or replaced a record")
        # At immediate resume, the fabricated completed run is future-dated.
        live_now = __import__("time").monotonic_ns()
        require(manifest["final_monotonic_ns"] > live_now,
                "fixture did not demonstrate acceptance of future intervals")

    for path, expected in PINS.items():
        require(sha256(path) == expected, f"v5 input moved during audit: {path}")
    require(not TARGET_RECORDS.exists() and not TARGET_OUTPUT.exists(),
            "audit touched an intended v5 target path")
    return {
        "status": "PRELAUNCH FAIL",
        "scope": "frozen active25 D16 staged v5 coordinator and conditional assembler",
        "checker_sha256": sha256(FILE),
        "frozen_tuple": {str(path.relative_to(REPO)): expected
                         for path, expected in PINS.items()},
        "counterexample": {
            "isolated_cli_resume_exit_code": 0,
            "fabricated_stage_count": 26,
            "exact_shard_integrations_executed": 0,
            "fabricated_inner_48J_marker": "999",
            "accepted_resumed_complete": True,
            "future_dated_completed_manifest_accepted": True,
            "intended_target_paths_untouched": True,
        },
        "smallest_failure": (
            "the externally anchored ledger does not anchor a resumed stage "
            "prefix or preexisting manifest; canonical fabricated records, "
            "including future-dated intervals, are accepted as complete"),
        "minimum_repair": [
            "require external SHA/device/inode anchors for every preexisting "
            "stage and for any preexisting manifest on resume",
            "reject every persisted resource/child/final timestamp later than "
            "the current live monotonic time",
            "retain theorem_ready=false until the independent checker "
            "recomputes every shard integral",
        ],
        "launch_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(run_counterexample(), sort_keys=True,
                          separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
