#!/usr/bin/env python3
"""One-shot, boot-bound staging for the active25 inner-D16 pencil.

Ledger initialization and production are separate isolated-CLI invocations.
Production accepts exactly one externally anchored ledger leaf, computes all
26 shards continuously, and has no resume/reuse path.  An interrupted attempt
directory is permanently abandoned.  Target execution remains withheld.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
V5 = HERE / "frontier_active25_inner_d16_staged_v5.py"
V5_TEST = HERE / "test_frontier_active25_inner_d16_staged_v5.py"
V5_ASSEMBLER = HERE / "assemble_frontier_active25_inner_d16_v5.py"
V5_ASSEMBLER_TEST = HERE / "test_assemble_frontier_active25_inner_d16_v5.py"
V5_SPEC = HERE / "FRONTIER-ACTIVE25-INNER-D16-STAGED-V5-PRELAUNCH.md"
V5_GATE = HERE / (
    "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v5.json")
V5_FAIL_CHECKER = REPO / "agents/audit/verify_frontier_active25_v5_prelaunch_fail.py"
V5_FAIL_RESULT = REPO / "agents/audit/results/frontier_active25_v5_prelaunch_fail.json"
V5_FAIL_REPORT = REPO / "agents/audit/FRONTIER-ACTIVE25-STAGED-V5-PRELAUNCH-AUDIT.md"
GATE = HERE / (
    "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v6.json")
INDEPENDENT_RECONSTRUCTION_DESIGN = REPO / (
    "agents/audit/"
    "FRONTIER-ACTIVE25-INDEPENDENT-ARITHMETIC-RECONSTRUCTION-DESIGN.md")

PINNED = {
    V5: "8bb0d5088e419d196b4aca732ec384804bf2918554cf001f372a3127e7f1f775",
    V5_TEST: "28b5b8d182fc0836a0bf905af4d7f9b907b403e35a9e61cae779428fb7f899bf",
    V5_ASSEMBLER: "6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9",
    V5_ASSEMBLER_TEST: "9d6a242a7e3b76d8cada75ee23f1ba24c7c100ff7a0d73de0d637e8166c09e74",
    V5_SPEC: "ef365ff9031b7166df50dba71d484996d075574bf668dccef207bf18238daf07",
    V5_GATE: "b814507140740a821d67b6ccdec65eda3c30985075a19505d8bc485c84fa2420",
    V5_FAIL_CHECKER: "127024d7117a130b21e4a93cb5f99ddbf59273e756802270feb52f0494c881a8",
    V5_FAIL_RESULT: "a173658fa20ada39cf2ca78e98ea92601be6e3709db9674826512c9e3a76c875",
    V5_FAIL_REPORT: "c60934e5c88c7d13160b488042c1a5446808201b57b356c4dbd6cb6404d77b99",
    GATE: "7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80",
    INDEPENDENT_RECONSTRUCTION_DESIGN:
        "976d7f43d52d45be33def40f376ebfe657af0fe3aba880f5c4de807a46b2693e",
}

LEDGER_LEAF = "ledger.json"
STAGE_LEAVES = tuple(f"common_r_{r:02d}.json" for r in range(26))
MANIFEST_LEAF = "manifest.json"
ALLOWED_LEAVES = (LEDGER_LEAF, *STAGE_LEAVES, MANIFEST_LEAF)
MAX_CLOCK = 2**63 - 1
BOOT_ID_PATH = Path("/proc/sys/kernel/random/boot_id")
SYNTHETIC_GATE_SHA256 = "0" * 64
SYNTHETIC_AUTHORIZATION = {
    "sha256": "0" * 64, "device": 0, "inode": 0,
}
BOOT_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class StageDeadlineExceeded(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def strict_sha(value, name):
    if (type(value) is not str or len(value) != 64 or
            any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def _read_descriptor(descriptor, maximum=4_000_000):
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    remaining = maximum + 1
    while remaining:
        block = os.read(descriptor, min(1_048_576, remaining))
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
    data = b"".join(chunks)
    if len(data) > maximum:
        raise ValueError("source file exceeds frozen size bound")
    return data


def _open_startup_self():
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(FILE, flags)
    before = os.fstat(descriptor)
    data = _read_descriptor(descriptor)
    after = os.fstat(descriptor)
    identity = (int(before.st_dev), int(before.st_ino), int(before.st_size),
                int(before.st_mtime_ns), int(before.st_ctime_ns),
                int(before.st_nlink))
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            identity != (int(after.st_dev), int(after.st_ino),
                         int(after.st_size), int(after.st_mtime_ns),
                         int(after.st_ctime_ns), int(after.st_nlink)) or
            len(data) != after.st_size):
        os.close(descriptor)
        raise RuntimeError("v6 source was not stable at process startup")
    return {"bytes": data, "descriptor": descriptor,
            "device": identity[0], "inode": identity[1],
            "size": identity[2], "mtime_ns": identity[3],
            "ctime_ns": identity[4], "nlink": identity[5],
            "sha256": sha256_bytes(data)}


_SELF = _open_startup_self()


def bind_startup_self(expected_sha256):
    strict_sha(expected_sha256, "expected producer self SHA")
    held = os.fstat(_SELF["descriptor"])
    held_identity = (int(held.st_dev), int(held.st_ino), int(held.st_size),
                     int(held.st_mtime_ns), int(held.st_ctime_ns),
                     int(held.st_nlink))
    expected_identity = tuple(_SELF[key] for key in
                              ("device", "inode", "size", "mtime_ns",
                               "ctime_ns", "nlink"))
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    current_descriptor = os.open(FILE, flags)
    try:
        current = os.fstat(current_descriptor)
        current_data = _read_descriptor(current_descriptor)
        current_identity = (
            int(current.st_dev), int(current.st_ino), int(current.st_size),
            int(current.st_mtime_ns), int(current.st_ctime_ns),
            int(current.st_nlink))
    finally:
        os.close(current_descriptor)
    if (expected_sha256 != _SELF["sha256"] or
            held_identity != expected_identity or
            current_identity != expected_identity or
            current_data != _SELF["bytes"] or
            sha256_bytes(_SELF["bytes"]) != expected_sha256):
        raise RuntimeError("startup-bound v6 source identity changed")
    return _SELF["bytes"]


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"v6 dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()
_SPEC = importlib.util.spec_from_file_location("active25_staged_v5_for_v6", V5)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(V5)
v5 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = v5
_SPEC.loader.exec_module(v5)


def dependency_record():
    result = {str(path.relative_to(REPO)): expected
              for path, expected in PINNED.items()}
    result.update(v5.dependency_record())
    result.update({str(path.relative_to(REPO)): expected
                   for path, expected in v5.v2.PINNED.items()})
    result.update(v5.v2.core.require_pins())
    result.update(v5.v2.core.shell.require_pins())
    return dict(sorted(result.items()))


def transitive_snapshots():
    """Capture every inherited local source/data layer, not just declarations."""
    return {
        "v5": v5.snapshots(),
        "v2": v5.v2.snapshots(),
        "core": v5.v2.core.require_pins(),
        "shell": v5.v2.core.shell.require_pins(),
    }


def load_gate():
    gate = json.loads(_START[GATE])
    if (type(gate) is not dict or gate.get("format") !=
            "frontier-active25-inner-D16-tagged-shell-authorized-gate-v6" or
            gate.get("status") != "PRELAUNCH_CANDIDATE" or
            gate.get("launch_authorized") is not False or
            gate.get("launch_authorization_contract") != {
                "artifact_format":
                    "frontier-active25-inner-D16-v6-root-launch-authorization-v1",
                "artifact_must_bind_frozen_driver_and_gate": True,
                "artifact_must_bind_independent_prelaunch_report_sha256": True,
                "artifact_must_bind_record_directory": True,
                "artifact_sha256_must_be_supplied_externally": True,
                "may_be_created_only_after_independent_prelaunch_pass": True,
            } or
            gate.get("active_outer_counts") != list(range(26)) or
            gate.get("stage_common_r") != list(range(26)) or
            gate.get("dimension") != 27 or
            gate.get("predecessor_v5_gate_sha256") != PINNED[V5_GATE] or
            gate.get("independent_reconstruction_design_sha256") !=
            PINNED[INDEPENDENT_RECONSTRUCTION_DESIGN] or
            gate.get("superseded_v5_failure") != {
                "checker_sha256": PINNED[V5_FAIL_CHECKER],
                "report_sha256": PINNED[V5_FAIL_REPORT],
                "result_sha256": PINNED[V5_FAIL_RESULT],
            } or gate.get("execution_semantics") != {
                "abandon_after_any_interruption": True,
                "externally_anchor_ledger_sha_device_inode": True,
                "fresh_isolated_cli_required": True,
                "initial_production_leaf_set": [LEDGER_LEAF],
                "resume_or_reuse_forbidden": True,
                "stage_count": 26,
            } or gate.get("resource_gate") != {
                "max_single_shard_seconds": 600,
                "max_total_wall_seconds": 14400,
                "minimum_mem_available_kib_each_reading": 1400000,
                "minimum_seconds_between_mem_readings": 5,
                "required_stable_mem_readings": 2,
                "rss_safety_factor": 4,
                "wall_safety_factor": 3,
                "workers": 1,
            }):
        raise ValueError("v6 gate identity mismatch")
    return gate


def runtime_gate_sha256(mode):
    if mode == "production":
        return PINNED[GATE]
    if mode == "synthetic-test":
        return SYNTHETIC_GATE_SHA256
    raise ValueError("invalid runtime mode")


def runtime_format(stem, mode):
    if mode not in ("production", "synthetic-test"):
        raise ValueError("invalid runtime mode")
    return f"{stem}-{mode}"


def _clock(value, name):
    if type(value) is not int or not 0 <= value <= MAX_CLOCK:
        raise ValueError(f"{name} is not a canonical monotonic clock")
    return value


def _boot_id(value):
    if type(value) is not str or BOOT_PATTERN.fullmatch(value) is None:
        raise ValueError("Linux boot ID is malformed")
    return value


def ledger_binding(snapshot):
    return {key: snapshot[key]
            for key in ("leaf", "sha256", "device", "inode")}


def expected_ledger_binding(sha256_value, device, inode):
    strict_sha(sha256_value, "expected ledger SHA")
    if (type(device) is not int or device < 0 or
            type(inode) is not int or inode < 0):
        raise ValueError("expected ledger device/inode is malformed")
    return {"leaf": LEDGER_LEAF, "sha256": sha256_value,
            "device": device, "inode": inode}


def authorization_binding(snapshot):
    return {key: snapshot[key] for key in ("sha256", "device", "inode")}


def _open_authorization(path, expected_sha256, record_dir,
                        expected_self_sha256):
    strict_sha(expected_sha256, "expected launch-authorization SHA")
    if expected_sha256 == SYNTHETIC_AUTHORIZATION["sha256"]:
        raise ValueError("production authorization cannot use test sentinel")
    canonical = Path(path).resolve(strict=True)
    record_canonical = Path(record_dir).resolve(strict=True)
    if canonical.parent == record_canonical or canonical in {FILE, *PINNED}:
        raise ValueError("launch authorization aliases a protected path")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(canonical, flags)
    try:
        before = os.fstat(descriptor)
        data = _read_descriptor(descriptor, maximum=100_000)
        after = os.fstat(descriptor)
        identity = (int(before.st_dev), int(before.st_ino), int(before.st_size),
                    int(before.st_mtime_ns), int(before.st_ctime_ns),
                    int(before.st_nlink))
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                identity != (int(after.st_dev), int(after.st_ino),
                             int(after.st_size), int(after.st_mtime_ns),
                             int(after.st_ctime_ns), int(after.st_nlink)) or
                len(data) != after.st_size or
                sha256_bytes(data) != expected_sha256):
            raise RuntimeError("launch authorization snapshot is unstable")
        try:
            value = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("launch authorization is not JSON") from error
        if canonical_json(value) != data:
            raise ValueError("launch authorization is not canonical JSON")
        if type(value) is not dict or set(value) != {
                "driver_sha256", "format", "gate_sha256",
                "independent_prelaunch_report_sha256",
                "max_total_wall_seconds", "one_shot_attempt_authorized",
                "record_directory", "status", "theorem_ready", "workers"}:
            raise ValueError("launch authorization schema mismatch")
        strict_sha(value["independent_prelaunch_report_sha256"],
                   "independent prelaunch report SHA")
        if (value["driver_sha256"] != expected_self_sha256 or
                value["format"] !=
                "frontier-active25-inner-D16-v6-root-launch-authorization-v1" or
                value["gate_sha256"] != PINNED[GATE] or
                value["max_total_wall_seconds"] != 14_400 or
                type(value["max_total_wall_seconds"]) is not int or
                value["one_shot_attempt_authorized"] is not True or
                value["record_directory"] != str(record_canonical) or
                value["status"] !=
                "ROOT_AUTHORIZED_AFTER_INDEPENDENT_PRELAUNCH_PASS" or
                value["theorem_ready"] is not False or
                value["workers"] != 1 or type(value["workers"]) is not int):
            raise ValueError("launch authorization identity mismatch")
        return {"bytes": data, "descriptor": descriptor,
                "path": str(canonical), "sha256": expected_sha256,
                "device": identity[0], "inode": identity[1],
                "size": identity[2], "mtime_ns": identity[3],
                "ctime_ns": identity[4], "nlink": identity[5],
                "value": value}
    except Exception:
        os.close(descriptor)
        raise


def _validate_authorization(handle, record_dir, expected_self_sha256):
    if type(handle) is not dict or set(handle) != {
            "bytes", "descriptor", "path", "sha256", "device", "inode",
            "size", "mtime_ns", "ctime_ns", "nlink", "value"}:
        raise ValueError("launch authorization handle is malformed")
    held = os.fstat(handle["descriptor"])
    held_identity = (int(held.st_dev), int(held.st_ino), int(held.st_size),
                     int(held.st_mtime_ns), int(held.st_ctime_ns),
                     int(held.st_nlink))
    expected_identity = tuple(handle[key] for key in
                              ("device", "inode", "size", "mtime_ns",
                               "ctime_ns", "nlink"))
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    check = os.open(handle["path"], flags)
    try:
        current = os.fstat(check)
        current_data = _read_descriptor(check, maximum=100_000)
        current_identity = (
            int(current.st_dev), int(current.st_ino), int(current.st_size),
            int(current.st_mtime_ns), int(current.st_ctime_ns),
            int(current.st_nlink))
    finally:
        os.close(check)
    if (held_identity != expected_identity or current_identity != expected_identity or
            current_data != handle["bytes"] or held.st_nlink != 1 or
            sha256_bytes(handle["bytes"]) != handle["sha256"] or
            handle["value"]["driver_sha256"] != expected_self_sha256 or
            handle["value"]["record_directory"] !=
            str(Path(record_dir).resolve(strict=True))):
        raise RuntimeError("launch authorization changed during invocation")
    return authorization_binding(handle)


def _close_authorization(handle):
    descriptor = handle.get("descriptor") if type(handle) is dict else None
    if type(descriptor) is int:
        os.close(descriptor)
        handle["descriptor"] = None


def _make_mode_guard():
    token = object()

    def validate(mode, capability):
        if mode == "synthetic-test" and capability is None:
            return
        if mode != "production" or capability is not token:
            raise RuntimeError("production mode is isolated-CLI-only")

    def capability(expected_self_sha256):
        _direct_cli_identity(expected_self_sha256)
        return token

    return validate, capability


def _direct_cli_identity(expected_self_sha256):
    bind_startup_self(expected_self_sha256)
    if (not sys.flags.isolated or __name__ != "__main__" or
            __spec__ is not None or
            Path(sys.argv[0]).resolve(strict=True) != FILE):
        raise RuntimeError(
            "production requires fresh `python3 -I` on the pinned v6 source")
    return True


_VALIDATE_MODE, _CLI_CAPABILITY = _make_mode_guard()


def make_ledger(handle, runtime, mode, expected_self_sha256,
                expected_authorization):
    bind_startup_self(expected_self_sha256)
    start = _clock(runtime.monotonic_ns(), "ledger start")
    duration = load_gate()["resource_gate"]["max_total_wall_seconds"] * 10**9
    if start + duration > MAX_CLOCK:
        raise OverflowError("monotonic deadline overflows frozen range")
    return {
        "allowed_leaves": list(ALLOWED_LEAVES),
        "authorization_binding": expected_authorization,
        "boot_id": _boot_id(runtime.boot_id()),
        "deadline_monotonic_ns": start + duration,
        "dependency_sha256": dependency_record(),
        "driver_sha256": expected_self_sha256,
        "format": runtime_format(
            "frontier-active25-inner-D16-immutable-ledger-v6", mode),
        "gate_sha256": runtime_gate_sha256(mode),
        "max_single_shard_nanoseconds": 600 * 10**9,
        "max_total_wall_nanoseconds": duration,
        "record_directory": {key: handle[key]
                             for key in ("path", "device", "inode")},
        "runtime_mode": mode,
        "start_monotonic_ns": start,
        "status": "initialized-one-shot",
        "theorem_ready": False,
    }


def strict_ledger(value, handle, mode, expected_self_sha256,
                  expected_authorization):
    if type(value) is not dict or set(value) != {
            "allowed_leaves", "authorization_binding", "boot_id",
            "deadline_monotonic_ns",
            "dependency_sha256", "driver_sha256", "format", "gate_sha256",
            "max_single_shard_nanoseconds", "max_total_wall_nanoseconds",
            "record_directory", "runtime_mode", "start_monotonic_ns",
            "status", "theorem_ready"}:
        raise ValueError("v6 ledger schema mismatch")
    start = value["start_monotonic_ns"]
    deadline = value["deadline_monotonic_ns"]
    duration = value["max_total_wall_nanoseconds"]
    if (value["allowed_leaves"] != list(ALLOWED_LEAVES) or
            value["authorization_binding"] != expected_authorization or
            type(start) is not int or type(deadline) is not int or
            type(duration) is not int or not 0 <= start <= deadline <= MAX_CLOCK or
            duration != 14_400 * 10**9 or deadline != start + duration or
            _boot_id(value["boot_id"]) != value["boot_id"] or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != expected_self_sha256 or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-immutable-ledger-v6", mode) or
            value["gate_sha256"] != runtime_gate_sha256(mode) or
            value["max_single_shard_nanoseconds"] != 600 * 10**9 or
            value["record_directory"] != {
                key: handle[key] for key in ("path", "device", "inode")} or
            value["runtime_mode"] != mode or
            value["status"] != "initialized-one-shot" or
            value["theorem_ready"] is not False):
        raise ValueError("v6 ledger identity mismatch")
    return value


def live_now(ledger, runtime):
    if _boot_id(runtime.boot_id()) != ledger["boot_id"]:
        raise RuntimeError("boot changed; one-shot monotonic record is invalid")
    now = _clock(runtime.monotonic_ns(), "live monotonic observation")
    if now < ledger["start_monotonic_ns"] or now > ledger["deadline_monotonic_ns"]:
        raise StageDeadlineExceeded("immutable global deadline failed")
    return now


def resource_observation(ledger, runtime, earliest_ns):
    _clock(earliest_ns, "earliest stage timestamp")
    if live_now(ledger, runtime) < earliest_ns:
        raise RuntimeError("live clock precedes prior persisted interval")
    first_before = _clock(runtime.monotonic_ns(), "first memory read start")
    first = runtime.mem_available_kib()
    first_after = _clock(runtime.monotonic_ns(), "first memory read end")
    runtime.sleep(5)
    second_before = _clock(runtime.monotonic_ns(), "second memory read start")
    second = runtime.mem_available_kib()
    second_after = _clock(runtime.monotonic_ns(), "second memory read end")
    if (any(type(value) is not int or value < 1_400_000
            for value in (first, second)) or
            not (ledger["start_monotonic_ns"] <= earliest_ns <= first_before <=
                 first_after <= second_before <= second_after <=
                 ledger["deadline_monotonic_ns"]) or
            second_before - first_after < 5 * 10**9 or
            live_now(ledger, runtime) < second_after):
        raise RuntimeError("two-reading live memory gate failed")
    return {
        "first": {"before_monotonic_ns": first_before,
                  "after_monotonic_ns": first_after,
                  "mem_available_kib": first},
        "minimum_separation_nanoseconds": 5 * 10**9,
        "second": {"before_monotonic_ns": second_before,
                   "after_monotonic_ns": second_after,
                   "mem_available_kib": second},
    }


def strict_resource(value, ledger, observed_now):
    _clock(observed_now, "resource validation observation")
    if (type(value) is not dict or set(value) != {
            "first", "minimum_separation_nanoseconds", "second"} or
            value["minimum_separation_nanoseconds"] != 5 * 10**9):
        raise ValueError("resource observation schema mismatch")
    intervals = []
    for key in ("first", "second"):
        row = value[key]
        if type(row) is not dict or set(row) != {
                "before_monotonic_ns", "after_monotonic_ns",
                "mem_available_kib"}:
            raise ValueError("resource row schema mismatch")
        before = row["before_monotonic_ns"]
        after = row["after_monotonic_ns"]
        memory = row["mem_available_kib"]
        if (type(before) is not int or type(after) is not int or
                type(memory) is not int or memory < 1_400_000 or
                not ledger["start_monotonic_ns"] <= before <= after <=
                observed_now or after > ledger["deadline_monotonic_ns"]):
            raise ValueError("resource row is invalid or future-dated")
        intervals.append((before, after))
    if intervals[1][0] - intervals[0][1] < 5 * 10**9:
        raise ValueError("resource readings are too close")
    return True


def child_payload(common_r, ledger_row, authorization_row,
                  expected_self_sha256, mode):
    self_start = bind_startup_self(expected_self_sha256)
    dep_start = snapshots()
    transitive_start = transitive_snapshots()
    shard = v5.v2.exact_common_r_shard(common_r, progress=False)
    strict_v6_shard(shard)
    if (bind_startup_self(expected_self_sha256) != self_start or
            snapshots() != dep_start or
            transitive_snapshots() != transitive_start):
        raise RuntimeError("v6 child arithmetic closure changed")
    return {
        "arithmetic_core_sha256": v5.v2.PINNED[v5.v2.CORE_PATH],
        "authorization_binding": authorization_row,
        "dependency_sha256": dependency_record(),
        "driver_sha256": expected_self_sha256,
        "format": runtime_format(
            "frontier-active25-inner-D16-child-arithmetic-v6", mode),
        "gate_sha256": runtime_gate_sha256(mode),
        "ledger_binding": ledger_row,
        "parameters": v5.v2.core.parameter_record(),
        "shard": shard,
        "status": "complete",
        "theorem_ready": False,
    }


def strict_v6_shard(value):
    """Tighten the inherited shard schema to this 26-coordinate shell."""
    r, vector = v5.v2.strict_shard(value)
    if value["inner_basis_dimension"] != 307:
        raise ValueError("v6 shard does not carry the frozen D16 dimension")
    if Q(value["inner_I"]) <= 0:
        raise ValueError("v6 shard has nonpositive inner I")
    allowed = {r}
    if r + 1 < 26:
        allowed.add(r + 1)
    if any(coefficient for index, coefficient in enumerate(vector)
           if index not in allowed):
        raise ValueError("v6 shard escaped the active target-count support")
    return r, vector


def merge_v6_shards(shards):
    """Merge only after applying the stricter active-count invariant."""
    for shard in shards:
        strict_v6_shard(shard)
    merged, identity = v5.v2.merge_exact_shards(shards)
    if (identity is None or identity[2] != 307 or
            any(merged[index] for index in range(26, len(merged)))):
        raise ValueError("merged v6 shards escaped the frozen 27D pencil")
    return merged, identity


def strict_child(value, expected_r, expected_ledger, expected_authorization, mode,
                 expected_self_sha256):
    if type(value) is not dict or set(value) != {
            "arithmetic_core_sha256", "authorization_binding",
            "dependency_sha256", "driver_sha256",
            "format", "gate_sha256", "ledger_binding", "parameters", "shard",
            "status", "theorem_ready"}:
        raise ValueError("v6 child schema mismatch")
    if (value["arithmetic_core_sha256"] !=
            v5.v2.PINNED[v5.v2.CORE_PATH] or
            value["authorization_binding"] != expected_authorization or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != expected_self_sha256 or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v6", mode) or
            value["gate_sha256"] != runtime_gate_sha256(mode) or
            value["ledger_binding"] != expected_ledger or
            value["parameters"] != v5.v2.core.parameter_record() or
            value["status"] != "complete" or
            value["theorem_ready"] is not False):
        raise ValueError("v6 child identity mismatch")
    r, _ = strict_v6_shard(value["shard"])
    if r != expected_r:
        raise ValueError("child returned wrong common count")
    return value


def parse_child_bytes(data, expected_r, expected_ledger,
                      expected_authorization, mode,
                      expected_self_sha256):
    if type(data) is not bytes or len(data) > 16_000_000:
        raise ValueError("child stdout is malformed or too large")
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("child stdout is not JSON") from error
    if canonical_json(value) != data:
        raise ValueError("child stdout is noncanonical or has extra bytes")
    return strict_child(value, expected_r, expected_ledger,
                        expected_authorization, mode,
                        expected_self_sha256)


def supervise_command(command, timeout_seconds):
    if (type(command) is not list or not command or
            any(type(x) is not str for x in command) or
            type(timeout_seconds) not in (int, float) or
            isinstance(timeout_seconds, bool) or timeout_seconds <= 0):
        raise ValueError("subprocess supervision arguments are malformed")
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        if process.poll() is None:
            raise RuntimeError("timed-out child was not reaped")
        raise StageDeadlineExceeded("child timed out, was killed, and attempt is abandoned") from error
    if process.returncode != 0:
        raise RuntimeError(
            f"child exited {process.returncode}: {stderr[-1000:]!r}")
    if stderr or len(stdout) > 16_000_000 or len(stderr) > 16_000_000:
        raise RuntimeError("child emitted forbidden stderr or oversized output")
    return stdout


def _direct_runtime(expected_self_sha256):
    _direct_cli_identity(expected_self_sha256)

    class DirectRuntime:
        @staticmethod
        def monotonic_ns():
            return time.monotonic_ns()

        @staticmethod
        def boot_id():
            return BOOT_ID_PATH.read_text().strip()

        @staticmethod
        def mem_available_kib():
            return v5.v2.core.mem_available_kib()

        @staticmethod
        def sleep(seconds):
            time.sleep(seconds)

        @staticmethod
        def run_child(common_r, timeout_seconds, ledger_row,
                      authorization_row):
            optimize = ["-O"] if not __debug__ else []
            command = [sys.executable, *optimize, "-I", str(FILE),
                       "--child-stage-r", str(common_r),
                       "--expected-self-sha256", expected_self_sha256,
                       "--ledger-sha256", ledger_row["sha256"],
                       "--ledger-device", str(ledger_row["device"]),
                       "--ledger-inode", str(ledger_row["inode"]),
                       "--authorization-sha256", authorization_row["sha256"],
                       "--authorization-device", str(authorization_row["device"]),
                       "--authorization-inode", str(authorization_row["inode"])]
            return supervise_command(command, timeout_seconds)

    return DirectRuntime()


def make_stage(child, observation, child_start, child_end, mode,
               expected_self_sha256):
    return {
        "authorization_binding": child["authorization_binding"],
        "child_stdout_sha256": sha256_bytes(canonical_json(child)),
        "dependency_sha256": dependency_record(),
        "driver_sha256": expected_self_sha256,
        "format": runtime_format(
            "frontier-active25-inner-D16-common-r-stage-v6", mode),
        "gate_sha256": runtime_gate_sha256(mode),
        "ledger_binding": child["ledger_binding"],
        "parameters": v5.v2.core.parameter_record(),
        "resource_observation": observation,
        "runtime_mode": mode,
        "shard": child["shard"],
        "status": "complete",
        "supervised_child_interval": {
            "end_monotonic_ns": child_end,
            "start_monotonic_ns": child_start,
        },
        "supervised_child_nanoseconds": child_end - child_start,
        "theorem_ready": False,
    }


def strict_stage(value, expected_r, ledger, ledger_row, mode,
                 expected_self_sha256, expected_authorization, observed_now):
    if type(value) is not dict or set(value) != {
            "authorization_binding", "child_stdout_sha256",
            "dependency_sha256", "driver_sha256",
            "format", "gate_sha256", "ledger_binding", "parameters",
            "resource_observation", "runtime_mode", "shard", "status",
            "supervised_child_interval", "supervised_child_nanoseconds",
            "theorem_ready"}:
        raise ValueError("v6 stage schema mismatch")
    interval = value["supervised_child_interval"]
    if type(interval) is not dict or set(interval) != {
            "start_monotonic_ns", "end_monotonic_ns"}:
        raise ValueError("child interval schema mismatch")
    start = interval["start_monotonic_ns"]
    end = interval["end_monotonic_ns"]
    duration = value["supervised_child_nanoseconds"]
    if (type(start) is not int or type(end) is not int or
            type(duration) is not int or
            not ledger["start_monotonic_ns"] <= start < end <= observed_now or
            end > ledger["deadline_monotonic_ns"] or
            duration != end - start or
            not 0 < duration <= ledger["max_single_shard_nanoseconds"] or
            value["authorization_binding"] != expected_authorization or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != expected_self_sha256 or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-common-r-stage-v6", mode) or
            value["gate_sha256"] != runtime_gate_sha256(mode) or
            value["ledger_binding"] != ledger_row or
            value["parameters"] != v5.v2.core.parameter_record() or
            value["runtime_mode"] != mode or value["status"] != "complete" or
            value["theorem_ready"] is not False):
        raise ValueError("v6 stage identity or live-time bound failed")
    strict_sha(value["child_stdout_sha256"], "child stdout SHA")
    strict_resource(value["resource_observation"], ledger, observed_now)
    if value["resource_observation"]["second"]["after_monotonic_ns"] > start:
        raise ValueError("resource and child intervals overlap")
    r, vector = strict_v6_shard(value["shard"])
    if r != expected_r:
        raise ValueError("stage common count mismatch")
    child = {
        "arithmetic_core_sha256": v5.v2.PINNED[v5.v2.CORE_PATH],
        "authorization_binding": expected_authorization,
        "dependency_sha256": dependency_record(),
        "driver_sha256": expected_self_sha256,
        "format": runtime_format(
            "frontier-active25-inner-D16-child-arithmetic-v6", mode),
        "gate_sha256": runtime_gate_sha256(mode),
        "ledger_binding": ledger_row,
        "parameters": v5.v2.core.parameter_record(),
        "shard": value["shard"],
        "status": "complete",
        "theorem_ready": False,
    }
    if value["child_stdout_sha256"] != sha256_bytes(canonical_json(child)):
        raise ValueError("stage does not bind exact child stdout")
    return vector


def parse_stage_bytes(data, expected_r, ledger, ledger_row, mode,
                      expected_self_sha256, expected_authorization,
                      observed_now):
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("stage is not JSON") from error
    if canonical_json(value) != data:
        raise ValueError("stage JSON is not canonical")
    strict_stage(value, expected_r, ledger, ledger_row, mode,
                 expected_self_sha256, expected_authorization, observed_now)
    return value


def make_manifest(handle, ledger, ledger_snap, stages, stage_rows, final,
                  mode, expected_self_sha256, expected_authorization):
    merged, identity = merge_v6_shards(
        [stage["shard"] for stage in stages])
    if identity is None:
        raise ArithmeticError("exact one-shot stages have no inner identity")
    return {
        "authorization_binding": expected_authorization,
        "complete": True,
        "cumulative_supervised_child_nanoseconds": sum(
            stage["supervised_child_nanoseconds"] for stage in stages),
        "dependency_sha256": dependency_record(),
        "dimension": 27,
        "driver_sha256": expected_self_sha256,
        "elapsed_monotonic_nanoseconds": final - ledger["start_monotonic_ns"],
        "final_monotonic_ns": final,
        "format": runtime_format(
            "frontier-active25-inner-D16-stage-manifest-v6", mode),
        "gate_sha256": runtime_gate_sha256(mode),
        "ledger_binding": ledger_binding(ledger_snap),
        "merged_raw_J_cross_by_target_R": [str(x) for x in merged],
        "parameters": v5.v2.core.parameter_record(),
        "record_directory": {key: handle[key]
                             for key in ("path", "device", "inode")},
        "runtime_mode": mode,
        "stages": stage_rows,
        "status": "complete-one-shot",
        "theorem_ready": False,
    }


def strict_manifest(value, handle, ledger, ledger_snap, mode,
                    expected_self_sha256, expected_authorization,
                    observed_now):
    if type(value) is not dict or set(value) != {
            "authorization_binding", "complete",
            "cumulative_supervised_child_nanoseconds",
            "dependency_sha256", "dimension", "driver_sha256",
            "elapsed_monotonic_nanoseconds", "final_monotonic_ns", "format",
            "gate_sha256", "ledger_binding", "merged_raw_J_cross_by_target_R",
            "parameters", "record_directory", "runtime_mode", "stages",
            "status", "theorem_ready"}:
        raise ValueError("v6 manifest schema mismatch")
    final = value["final_monotonic_ns"]
    elapsed = value["elapsed_monotonic_nanoseconds"]
    cumulative = value["cumulative_supervised_child_nanoseconds"]
    if (value["complete"] is not True or
            value["authorization_binding"] != expected_authorization or
            type(final) is not int or type(elapsed) is not int or
            type(cumulative) is not int or
            not ledger["start_monotonic_ns"] <= final <= observed_now or
            final > ledger["deadline_monotonic_ns"] or
            elapsed != final - ledger["start_monotonic_ns"] or
            not 0 < cumulative <= elapsed <= ledger["max_total_wall_nanoseconds"] or
            value["dependency_sha256"] != dependency_record() or
            value["dimension"] != 27 or
            value["driver_sha256"] != expected_self_sha256 or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-stage-manifest-v6", mode) or
            value["gate_sha256"] != runtime_gate_sha256(mode) or
            value["ledger_binding"] != ledger_binding(ledger_snap) or
            type(value["merged_raw_J_cross_by_target_R"]) is not list or
            len(value["merged_raw_J_cross_by_target_R"]) != v5.v2.core.K + 1 or
            any(type(x) is not str or str(Q(x)) != x
                for x in value["merged_raw_J_cross_by_target_R"]) or
            value["parameters"] != v5.v2.core.parameter_record() or
            value["record_directory"] != {
                key: handle[key] for key in ("path", "device", "inode")} or
            value["runtime_mode"] != mode or
            type(value["stages"]) is not list or len(value["stages"]) != 26 or
            value["status"] != "complete-one-shot" or
            value["theorem_ready"] is not False):
        raise ValueError("v6 manifest identity or live-time bound failed")
    fresh_ledger = v5.read_leaf(handle, LEDGER_LEAF)
    if ledger_binding(fresh_ledger) != ledger_binding(ledger_snap):
        raise RuntimeError("manifest ledger binding changed")
    seen = {(ledger_snap["device"], ledger_snap["inode"])}
    shards = []
    total = 0
    prior_end = ledger["start_monotonic_ns"]
    for r, row in enumerate(value["stages"]):
        if (type(row) is not dict or set(row) != {
                "common_r", "device", "inode", "leaf", "sha256"} or
                row["common_r"] != r or type(row["common_r"]) is not int or
                row["leaf"] != STAGE_LEAVES[r] or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError("manifest stage binding malformed")
        strict_sha(row["sha256"], "stage SHA")
        snap = v5.read_leaf(handle, row["leaf"])
        if ledger_binding(snap) != {key: row[key]
                                    for key in ("leaf", "sha256", "device", "inode")}:
            raise RuntimeError("manifest stage binding changed")
        inode = (snap["device"], snap["inode"])
        if inode in seen:
            raise ValueError("ledger/stages are not inode-distinct")
        seen.add(inode)
        stage = parse_stage_bytes(
            snap["data"], r, ledger, ledger_binding(ledger_snap), mode,
            expected_self_sha256, expected_authorization, observed_now)
        first = stage["resource_observation"]["first"]["before_monotonic_ns"]
        end = stage["supervised_child_interval"]["end_monotonic_ns"]
        if first < prior_end:
            raise ValueError("one-shot stage intervals are not globally ordered")
        prior_end = end
        total += stage["supervised_child_nanoseconds"]
        shards.append(stage["shard"])
    merged, identity = merge_v6_shards(shards)
    if (identity is None or total != cumulative or final < prior_end or
            [str(x) for x in merged] != value["merged_raw_J_cross_by_target_R"]):
        raise ValueError("manifest merge/timeline reconstruction failed")
    return True


def _parse_ledger(handle, snapshot, mode, expected_self_sha256,
                  expected_authorization):
    try:
        value = json.loads(snapshot["data"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("ledger is not JSON") from error
    if canonical_json(value) != snapshot["data"]:
        raise ValueError("ledger JSON is not canonical")
    return strict_ledger(value, handle, mode, expected_self_sha256,
                         expected_authorization)


def _rebind_authorization(mode, authorization_handle, record_dir,
                          expected_self_sha256):
    if mode == "synthetic-test":
        if authorization_handle is not None:
            raise RuntimeError("synthetic run received production authorization")
        return dict(SYNTHETIC_AUTHORIZATION)
    if mode != "production" or authorization_handle is None:
        raise RuntimeError("production launch authorization is missing")
    return _validate_authorization(
        authorization_handle, record_dir, expected_self_sha256)


def _initialize_impl(record_dir, runtime, mode, expected_self_sha256,
                     authorization_handle=None, capability=None):
    _VALIDATE_MODE(mode, capability)
    self_start = bind_startup_self(expected_self_sha256)
    dep_start = snapshots()
    transitive_start = transitive_snapshots()
    expected_authorization = _rebind_authorization(
        mode, authorization_handle, record_dir, expected_self_sha256)
    handle = v5.open_record_dir(record_dir)
    try:
        v5.require_leaf_set(handle, set())
        ledger = make_ledger(handle, runtime, mode, expected_self_sha256,
                             expected_authorization)
        snapshot = v5.write_leaf_exclusive(
            handle, LEDGER_LEAF, canonical_json(ledger))
        v5.require_leaf_set(handle, {LEDGER_LEAF})
        if (bind_startup_self(expected_self_sha256) != self_start or
                _rebind_authorization(
                    mode, authorization_handle, record_dir,
                    expected_self_sha256) != expected_authorization or
                snapshots() != dep_start or
                transitive_snapshots() != transitive_start):
            raise RuntimeError("v6 closure changed during initialization")
        return snapshot
    finally:
        v5.close_record_dir(handle)


def _run_one_shot_impl(record_dir, runtime, mode, expected_self_sha256,
                       expected_ledger, authorization_handle=None,
                       capability=None):
    _VALIDATE_MODE(mode, capability)
    self_start = bind_startup_self(expected_self_sha256)
    dep_start = snapshots()
    transitive_start = transitive_snapshots()
    expected_authorization = _rebind_authorization(
        mode, authorization_handle, record_dir, expected_self_sha256)
    if (type(expected_ledger) is not dict or set(expected_ledger) != {
            "leaf", "sha256", "device", "inode"}):
        raise ValueError("external ledger anchor is missing")
    expected_ledger = expected_ledger_binding(
        expected_ledger["sha256"], expected_ledger["device"],
        expected_ledger["inode"])
    handle = v5.open_record_dir(record_dir)
    try:
        # This is the defining v6 gate: no prefix, manifest, temp, or extra
        # can ever be resumed or reused.
        v5.require_leaf_set(handle, {LEDGER_LEAF})
        ledger_snap = v5.read_leaf(handle, LEDGER_LEAF)
        if ledger_binding(ledger_snap) != expected_ledger:
            raise RuntimeError("external ledger SHA/inode anchor mismatch")
        ledger = _parse_ledger(handle, ledger_snap, mode,
                               expected_self_sha256, expected_authorization)
        prior_end = live_now(ledger, runtime)
        stages = []
        rows = []
        seen = {(ledger_snap["device"], ledger_snap["inode"])}
        for r in range(26):
            expected_leaves = {LEDGER_LEAF, *STAGE_LEAVES[:r]}
            v5.require_leaf_set(handle, expected_leaves)
            observation = resource_observation(ledger, runtime, prior_end)
            child_start = live_now(ledger, runtime)
            remaining = ledger["deadline_monotonic_ns"] - child_start
            timeout_ns = min(ledger["max_single_shard_nanoseconds"], remaining)
            if timeout_ns <= 0:
                raise StageDeadlineExceeded("no time remains for next shard")
            stdout = runtime.run_child(
                r, timeout_ns / 10**9, ledger_binding(ledger_snap),
                expected_authorization)
            child_end = live_now(ledger, runtime)
            if not 0 < child_end - child_start <= timeout_ns:
                raise StageDeadlineExceeded("child exceeded supervised interval")
            child = parse_child_bytes(
                stdout, r, ledger_binding(ledger_snap),
                expected_authorization, mode,
                expected_self_sha256)
            stage = make_stage(child, observation, child_start, child_end,
                               mode, expected_self_sha256)
            observed_before = live_now(ledger, runtime)
            strict_stage(stage, r, ledger, ledger_binding(ledger_snap), mode,
                         expected_self_sha256, expected_authorization,
                         observed_before)
            v5.require_leaf_set(handle, expected_leaves)
            snap = v5.write_leaf_exclusive(
                handle, STAGE_LEAVES[r], canonical_json(stage))
            observed_after = live_now(ledger, runtime)
            persisted = parse_stage_bytes(
                snap["data"], r, ledger, ledger_binding(ledger_snap), mode,
                expected_self_sha256, expected_authorization, observed_after)
            v5.require_leaf_set(handle, expected_leaves | {STAGE_LEAVES[r]})
            if (snap["device"], snap["inode"]) in seen:
                raise ValueError("new stage aliases ledger or prior stage")
            seen.add((snap["device"], snap["inode"]))
            if bind_startup_self(expected_self_sha256) != self_start:
                raise RuntimeError("startup-bound source changed during staging")
            if _rebind_authorization(
                    mode, authorization_handle, record_dir,
                    expected_self_sha256) != expected_authorization:
                raise RuntimeError("launch authorization binding changed")
            stages.append(persisted)
            rows.append({"common_r": r, **{
                key: snap[key] for key in ("leaf", "sha256", "device", "inode")}})
            prior_end = child_end
        v5.require_leaf_set(handle, {LEDGER_LEAF, *STAGE_LEAVES})
        final = live_now(ledger, runtime)
        manifest = make_manifest(handle, ledger, ledger_snap, stages, rows,
                                 final, mode, expected_self_sha256,
                                 expected_authorization)
        strict_manifest(manifest, handle, ledger, ledger_snap, mode,
                        expected_self_sha256, expected_authorization,
                        live_now(ledger, runtime))
        if (bind_startup_self(expected_self_sha256) != self_start or
                _rebind_authorization(
                    mode, authorization_handle, record_dir,
                    expected_self_sha256) != expected_authorization or
                snapshots() != dep_start or
                transitive_snapshots() != transitive_start):
            raise RuntimeError("v6 closure changed before manifest publication")
        manifest_snap = v5.write_leaf_exclusive(
            handle, MANIFEST_LEAF, canonical_json(manifest))
        observed_after = live_now(ledger, runtime)
        strict_manifest(manifest, handle, ledger, ledger_snap, mode,
                        expected_self_sha256, expected_authorization,
                        observed_after)
        v5.require_leaf_set(handle, set(ALLOWED_LEAVES))
        rebound = v5.read_leaf(handle, MANIFEST_LEAF)
        if ledger_binding(rebound) != ledger_binding(manifest_snap):
            raise RuntimeError("published manifest was replaced")
        if (bind_startup_self(expected_self_sha256) != self_start or
                _rebind_authorization(
                    mode, authorization_handle, record_dir,
                    expected_self_sha256) != expected_authorization or
                snapshots() != dep_start or
                transitive_snapshots() != transitive_start):
            raise RuntimeError("v6 closure changed after manifest publication")
        return {"manifest_binding": ledger_binding(manifest_snap),
                "one_shot_complete": True}
    finally:
        v5.close_record_dir(handle)


def _initialize_test_only(record_dir, runtime):
    return _initialize_impl(
        record_dir, runtime, "synthetic-test", _SELF["sha256"])


def _run_test_only(record_dir, runtime, expected_ledger):
    return _run_one_shot_impl(
        record_dir, runtime, "synthetic-test", _SELF["sha256"],
        expected_ledger)


def _initialize_production_cli(record_dir, expected_self_sha256,
                               authorization_path,
                               expected_authorization_sha256):
    capability = _CLI_CAPABILITY(expected_self_sha256)
    runtime = _direct_runtime(expected_self_sha256)
    authorization = _open_authorization(
        authorization_path, expected_authorization_sha256, record_dir,
        expected_self_sha256)
    try:
        snapshot = _initialize_impl(
            record_dir, runtime, "production", expected_self_sha256,
            authorization_handle=authorization, capability=capability)
        _validate_authorization(
            authorization, record_dir, expected_self_sha256)
        return {"authorization_binding": authorization_binding(authorization),
                "ledger_binding": ledger_binding(snapshot),
                "status": "initialized-ledger-only"}
    finally:
        _close_authorization(authorization)


def _run_production_cli(record_dir, expected_self_sha256,
                        ledger_sha256, ledger_device, ledger_inode,
                        authorization_path,
                        expected_authorization_sha256):
    capability = _CLI_CAPABILITY(expected_self_sha256)
    runtime = _direct_runtime(expected_self_sha256)
    expected = expected_ledger_binding(
        ledger_sha256, ledger_device, ledger_inode)
    authorization = _open_authorization(
        authorization_path, expected_authorization_sha256, record_dir,
        expected_self_sha256)
    try:
        result = _run_one_shot_impl(
            record_dir, runtime, "production", expected_self_sha256,
            expected, authorization_handle=authorization,
            capability=capability)
        _validate_authorization(
            authorization, record_dir, expected_self_sha256)
        return result
    finally:
        _close_authorization(authorization)


def preflight():
    gate = load_gate()
    return {
        "abandon_after_interruption": True,
        "active_outer_counts": list(range(26)),
        "dimension": 27,
        "driver_sha256": _SELF["sha256"],
        "gate_sha256": PINNED[GATE],
        "launch_authorized_by_gate": gate["launch_authorized"],
        "one_shot_no_resume": True,
        "resource_gate": gate["resource_gate"],
        "status": "frontier-active25-v6-one-shot-preflight",
        "target_started": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--initialize-ledger-only", action="store_true")
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--expected-authorization-sha256")
    parser.add_argument("--expected-ledger-sha256")
    parser.add_argument("--expected-ledger-device", type=int)
    parser.add_argument("--expected-ledger-inode", type=int)
    parser.add_argument("--child-stage-r", type=int)
    parser.add_argument("--ledger-sha256")
    parser.add_argument("--ledger-device", type=int)
    parser.add_argument("--ledger-inode", type=int)
    parser.add_argument("--authorization-sha256")
    parser.add_argument("--authorization-device", type=int)
    parser.add_argument("--authorization-inode", type=int)
    args = parser.parse_args()
    child = (args.child_stage_r, args.ledger_sha256,
             args.ledger_device, args.ledger_inode,
             args.authorization_sha256, args.authorization_device,
             args.authorization_inode)
    external = (args.expected_ledger_sha256,
                args.expected_ledger_device, args.expected_ledger_inode)
    if args.preflight_only:
        if (args.initialize_ledger_only or args.record_dir is not None or
                args.expected_self_sha256 is not None or
                args.authorization_file is not None or
                args.expected_authorization_sha256 is not None or
                any(x is not None for x in (*child, *external))):
            parser.error("preflight takes no target arguments")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    if args.initialize_ledger_only:
        if (args.record_dir is None or args.expected_self_sha256 is None or
                args.authorization_file is None or
                args.expected_authorization_sha256 is None or
                any(x is not None for x in (*child, *external))):
            parser.error(
                "initialization requires record dir, self SHA, and launch authorization")
        print(json.dumps(_initialize_production_cli(
            args.record_dir, args.expected_self_sha256,
            args.authorization_file,
            args.expected_authorization_sha256), sort_keys=True))
        return
    if any(x is not None for x in child):
        if (args.record_dir is not None or args.expected_self_sha256 is None or
                args.authorization_file is not None or
                args.expected_authorization_sha256 is not None or
                any(x is not None for x in external) or
                any(x is None for x in child) or
                type(args.child_stage_r) is not int or
                args.child_stage_r not in range(26)):
            parser.error("child requires exactly one complete ledger binding")
        _direct_cli_identity(args.expected_self_sha256)
        row = expected_ledger_binding(
            args.ledger_sha256, args.ledger_device, args.ledger_inode)
        auth_row = expected_ledger_binding(
            args.authorization_sha256, args.authorization_device,
            args.authorization_inode)
        auth_row.pop("leaf")
        sys.stdout.buffer.write(canonical_json(child_payload(
            args.child_stage_r, row, auth_row,
            args.expected_self_sha256, "production")))
        return
    if (args.record_dir is None or args.expected_self_sha256 is None or
            args.authorization_file is None or
            args.expected_authorization_sha256 is None or
            any(x is None for x in external)):
        parser.error(
            "one-shot production requires record dir, self SHA, and external "
            "ledger SHA/device/inode")
    print(json.dumps(_run_production_cli(
        args.record_dir, args.expected_self_sha256,
        args.expected_ledger_sha256, args.expected_ledger_device,
        args.expected_ledger_inode, args.authorization_file,
        args.expected_authorization_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
