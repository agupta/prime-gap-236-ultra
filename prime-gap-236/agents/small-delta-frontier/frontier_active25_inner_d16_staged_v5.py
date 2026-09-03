#!/usr/bin/env python3
"""Boot-bound, deadline-enforced v5 staging for the active25 D16 pencil.

The public production entry has no injectable clock, memory reader, sleeper,
or child runner.  It writes an immutable ledger first, gates every new shard
with two real MemAvailable observations, computes arithmetic in a fresh
killable child, and only then O_EXCL-publishes the validated shard.  Execution
remains withheld until an independent v5 audit and explicit root launch.
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
V2 = HERE / "frontier_active25_inner_d16_staged_v2.py"
V2_TEST = HERE / "test_frontier_active25_inner_d16_staged_v2.py"
V2_SPEC = HERE / "FRONTIER-ACTIVE25-INNER-D16-TAGGED-SHELL-PRELAUNCH-V2.md"
GATE = HERE / "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v5.json"
PASS_CHECKER = REPO / "agents/audit/verify_frontier_active25_grouped_prelaunch.py"
PASS_RESULT = REPO / "agents/audit/results/frontier_active25_grouped_prelaunch_v2_audit.json"
PASS_REPORT = REPO / "agents/audit/FRONTIER-ACTIVE25-GROUPED-PRELAUNCH-V2-AUDIT.md"
V3 = HERE / "frontier_active25_inner_d16_staged_v3.py"
V3_TEST = HERE / "test_frontier_active25_inner_d16_staged_v3.py"
V3_ASSEMBLER = HERE / "assemble_frontier_active25_inner_d16_v3.py"
V3_ASSEMBLER_TEST = HERE / "test_assemble_frontier_active25_inner_d16_v3.py"
V3_SPEC = HERE / "FRONTIER-ACTIVE25-INNER-D16-STAGED-V3-PRELAUNCH.md"
V3_GATE = HERE / "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v3.json"
V3_FAIL_TEST = REPO / "agents/audit/test_frontier_active25_v3_resume_wall_bypass.py"
V3_FAIL_REPORT = REPO / "agents/audit/FRONTIER-ACTIVE25-STAGED-V3-DELTA-AUDIT.md"
V4 = HERE / "frontier_active25_inner_d16_staged_v4.py"
V4_TEST = HERE / "test_frontier_active25_inner_d16_staged_v4.py"
V4_ASSEMBLER = HERE / "assemble_frontier_active25_inner_d16_v4.py"
V4_ASSEMBLER_TEST = HERE / "test_assemble_frontier_active25_inner_d16_v4.py"
V4_SPEC = HERE / "FRONTIER-ACTIVE25-INNER-D16-STAGED-V4-PRELAUNCH.md"
V4_GATE = HERE / "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v4.json"
V4_FAIL_CHECKER = REPO / "agents/audit/verify_frontier_active25_v4_prelaunch_fail.py"
V4_FAIL_RESULT = REPO / "agents/audit/results/frontier_active25_v4_prelaunch_fail.json"
V4_FAIL_REPORT = REPO / "agents/audit/FRONTIER-ACTIVE25-STAGED-V4-PRELAUNCH-AUDIT.md"
INDEPENDENT_RECONSTRUCTION_DESIGN = REPO / (
    "agents/audit/"
    "FRONTIER-ACTIVE25-INDEPENDENT-ARITHMETIC-RECONSTRUCTION-DESIGN.md")

PINNED = {
    V2: "bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd",
    V2_TEST: "27fabdfa8e4f73820ca70af6189751d2e30acd7f699b580b9cd2cfdb625f10ed",
    V2_SPEC: "1a39e72a2d69ab0e64570ed05a9b0ea762b7f4223a4d88205d7a1f525230c721",
    GATE: "b814507140740a821d67b6ccdec65eda3c30985075a19505d8bc485c84fa2420",
    PASS_CHECKER: "dba6064473a56cb16c99c4423efb0852b3990d0a7f39d027c1b5c1bdc0f4c622",
    PASS_RESULT: "bd93b52f3556b9d35edb2568b61c74362e4e156f5b607e6755f2ac7203a3c9a2",
    PASS_REPORT: "0c37f563d99191f0fbb4abc1c0ea5700ed6288ed9011d5edc691c91394cdc6a9",
    V3: "79cbeb74b994e8d6bdd5f16e7d0f7d11aa148d6f9d6d4f32a12932854d62efd8",
    V3_TEST: "ab74ac22409f58e3bc7c3ae5a8c50a05c482c47cea69f6f30493adbeaa864e73",
    V3_ASSEMBLER: "c48feddb0cfd1a70ab7140813f4cf0037ae6f21374c229a38089198404079788",
    V3_ASSEMBLER_TEST: "f69f4dac10b610a5a08ec792b7e6bb4c74c4199d0edab78492dadd9703f8aa19",
    V3_SPEC: "9649807e7dfb9111a188ae87b52b59ef0b3d3dab7b7ed20a0492bf8c2082c754",
    V3_GATE: "19ab3d54c08fbd24d6b70ea9d946ca7272030bf20716da383f4bed285de411bb",
    V3_FAIL_TEST: "13c5a756ca7b12e718fbd9b731bf62fae48b556d895cfd5b2caf1b344d3a2b67",
    V3_FAIL_REPORT: "a384a19332f87c7f8adbc17c7514ea2dc070514b5b477bd6d95d256203b40d14",
    V4: "7d5188ec18ef99ae22aeada193471a69c11cf15363aa26496ef8b3217387beef",
    V4_TEST: "4082c32c1358d564f6ed17743c3ccdc471813c67df5a5a3013acd9aa1e227ac0",
    V4_ASSEMBLER: "0b60c03e3743fe8003c9571423e79922a3ded08594d30894bee2461e980d0d85",
    V4_ASSEMBLER_TEST: "bb2a751b0459365641e188afc0f67fea27781e7a17a04538b5f35b3bae1140db",
    V4_SPEC: "66b4b7de36aecd3a2b4ecbf2ea1cb5e6192c2590d24d8a61bb7bc76a327f2edb",
    V4_GATE: "2dcfb44e4c9fbc5ec5f9b030f6565a35b06af478dff60c0805f96b44078c35fe",
    V4_FAIL_CHECKER: "b1da2c8bc980154751da868d67c543bf281d2892113e259c6bf67a9ed8217588",
    V4_FAIL_RESULT: "f020711a107dd36f724561e00f7d2c3fb9e7eb801a4e4f24e6e547cba6d782f5",
    V4_FAIL_REPORT: "11fe3b77f4d795b51d2042eef3f7254662bcf2c06f2cbc6668b8657ca06d328f",
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


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"v5 dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()
_SPEC = importlib.util.spec_from_file_location("active25_staged_v2_for_v5", V2)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(V2)
v2 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = v2
_SPEC.loader.exec_module(v2)


def dependency_record():
    return {str(path.relative_to(REPO)): expected
            for path, expected in sorted(PINNED.items(), key=lambda item: str(item[0]))}


def runtime_gate_sha256(runtime_mode):
    if runtime_mode == "production":
        return PINNED[GATE]
    if runtime_mode == "synthetic-test":
        return SYNTHETIC_GATE_SHA256
    raise ValueError("invalid runtime mode")


def runtime_format(stem, runtime_mode):
    if runtime_mode not in ("production", "synthetic-test"):
        raise ValueError("invalid runtime mode")
    return f"{stem}-{runtime_mode}"


def _make_runtime_mode_guard():
    """Keep the production capability inside a closure reached only by CLI.

    This is not a claim of resistance to arbitrary malicious mutation of a
    live Python process.  The declared production trust boundary is a fresh
    isolated CLI process whose file hash is supplied externally.  The closure
    does, however, make the ordinary imported/test API incapable of selecting
    production formats merely by passing a string.
    """
    production_capability = object()

    def validate(runtime_mode, capability):
        if runtime_mode == "synthetic-test":
            if capability is not None:
                raise RuntimeError("synthetic execution received a capability")
            return
        if (runtime_mode != "production" or
                capability is not production_capability):
            raise RuntimeError(
                "production mode is available only to the isolated CLI")

    def from_isolated_cli(expected_self_sha256):
        _direct_cli_identity(expected_self_sha256)
        return production_capability

    return validate, from_isolated_cli


def load_gate():
    gate = json.loads(_START[GATE])
    resources = gate.get("resource_gate")
    failure = gate.get("superseded_v3_failure")
    failure_v4 = gate.get("superseded_v4_failure")
    if (gate.get("format") !=
            "frontier-active25-inner-D16-tagged-shell-authorized-gate-v5" or
            gate.get("status") != "AUTHORIZED" or
            gate.get("launch_authorized") is not True or
            gate.get("active_outer_counts") != list(range(26)) or
            gate.get("stage_common_r") != list(range(26)) or
            gate.get("dimension") != 27 or
            type(resources) is not dict or resources != {
                "max_single_shard_seconds": 600,
                "max_total_wall_seconds": 14400,
                "minimum_mem_available_kib_each_reading": 1400000,
                "minimum_seconds_between_mem_readings": 5,
                "required_stable_mem_readings": 2,
                "rss_safety_factor": 4,
                "wall_safety_factor": 3,
                "workers": 1,
            } or any(type(resources[key]) is not int
                     for key in resources) or
            failure != {
                "normal_and_optimized_output_sha256":
                    "3d7e92740534cbf9b11093fbf1adaaa22208c592618e69c4c09adc043364be93",
                "regression_sha256": PINNED[V3_FAIL_TEST],
                "report_sha256": PINNED[V3_FAIL_REPORT],
            } or failure_v4 != {
                "checker_sha256": PINNED[V4_FAIL_CHECKER],
                "report_sha256": PINNED[V4_FAIL_REPORT],
                "result_sha256": PINNED[V4_FAIL_RESULT],
            }):
        raise ValueError("v5 gate identity mismatch")
    return gate


def _safe_leaf(name):
    if (type(name) is not str or not name or name in (".", "..") or
            Path(name).name != name or "/" in name or "\x00" in name):
        raise ValueError("unsafe record leaf")
    return name


def open_record_dir(path):
    canonical = str(Path(path).resolve(strict=True))
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(canonical, flags)
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        os.close(descriptor)
        raise ValueError("record path is not a real directory")
    result = {"path": canonical, "device": int(observed.st_dev),
              "inode": int(observed.st_ino), "descriptor": descriptor}
    validate_record_dir(result)
    return result


def close_record_dir(handle):
    descriptor = handle.get("descriptor") if type(handle) is dict else None
    if type(descriptor) is int:
        os.close(descriptor)
        handle["descriptor"] = None


def validate_record_dir(handle):
    if type(handle) is not dict or set(handle) != {
            "path", "device", "inode", "descriptor"}:
        raise ValueError("malformed record-directory handle")
    descriptor = handle["descriptor"]
    if type(descriptor) is not int:
        raise ValueError("record-directory descriptor is closed")
    held = os.fstat(descriptor)
    if (not stat.S_ISDIR(held.st_mode) or
            (int(held.st_dev), int(held.st_ino)) !=
            (handle["device"], handle["inode"])):
        raise RuntimeError("held record directory changed")
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        check = os.open(handle["path"], flags)
    except OSError as error:
        raise RuntimeError("record-directory pathname was replaced") from error
    try:
        observed = os.fstat(check)
        if ((int(observed.st_dev), int(observed.st_ino)) !=
                (handle["device"], handle["inode"])):
            raise RuntimeError("record-directory pathname was replaced")
    finally:
        os.close(check)
    return True


def leaf_set(handle):
    validate_record_dir(handle)
    names = os.listdir(handle["descriptor"])
    if any(type(name) is not str or name not in ALLOWED_LEAVES for name in names):
        raise ValueError("record directory contains an unauthorized leaf")
    return set(names)


def require_leaf_set(handle, expected):
    expected = set(expected)
    if not expected <= set(ALLOWED_LEAVES) or leaf_set(handle) != expected:
        raise ValueError("record directory leaf set is not exact")
    return True


def read_leaf(handle, name, maximum_bytes=16_000_000):
    validate_record_dir(handle)
    name = _safe_leaf(name)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=handle["descriptor"])
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                before.st_size < 0 or
                before.st_size > maximum_bytes):
            raise ValueError(
                "record leaf is not a singly linked bounded regular file")
        chunks = []
        remaining = maximum_bytes + 1
        while remaining:
            block = os.read(descriptor, min(1_048_576, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if (len(data) > maximum_bytes or len(data) != after.st_size or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns, before.st_nlink) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns, after.st_nlink) or
                after.st_nlink != 1):
            raise RuntimeError("record leaf changed during read")
        validate_record_dir(handle)
        return {"leaf": name, "data": data, "sha256": sha256_bytes(data),
                "device": int(after.st_dev), "inode": int(after.st_ino)}
    finally:
        os.close(descriptor)


def write_leaf_exclusive(handle, name, data):
    validate_record_dir(handle)
    name = _safe_leaf(name)
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o600, dir_fd=handle["descriptor"])
    try:
        position = 0
        while position < len(data):
            count = os.write(descriptor, data[position:])
            if count <= 0:
                raise OSError("short record write")
            position += count
        os.fsync(descriptor)
        owned = os.fstat(descriptor)
        rebound = read_leaf(handle, name, max(1, len(data)))
        if (owned.st_nlink != 1 or rebound["data"] != data or
                (rebound["device"], rebound["inode"]) !=
                (int(owned.st_dev), int(owned.st_ino))):
            raise RuntimeError("new record leaf was replaced")
        os.fsync(handle["descriptor"])
        return rebound
    finally:
        os.close(descriptor)


def _clock(value, name):
    if type(value) is not int or not 0 <= value <= MAX_CLOCK:
        raise ValueError(f"{name} is not a canonical monotonic clock value")
    return value


def _boot_id(value):
    if type(value) is not str or BOOT_PATTERN.fullmatch(value) is None:
        raise ValueError("Linux boot ID is malformed")
    return value


def ledger_binding(snapshot):
    return {key: snapshot[key]
            for key in ("leaf", "sha256", "device", "inode")}


def make_ledger(handle, runtime, runtime_mode):
    start = _clock(runtime.monotonic_ns(), "ledger start")
    duration = load_gate()["resource_gate"]["max_total_wall_seconds"] * 10**9
    deadline = start + duration
    if deadline > MAX_CLOCK:
        raise OverflowError("monotonic deadline overflows the frozen range")
    return {
        "allowed_leaves": list(ALLOWED_LEAVES),
        "boot_id": _boot_id(runtime.boot_id()),
        "deadline_monotonic_ns": deadline,
        "dependency_sha256": dependency_record(),
        "driver_sha256": sha256(FILE),
        "format": runtime_format(
            "frontier-active25-inner-D16-immutable-ledger-v5", runtime_mode),
        "gate_sha256": runtime_gate_sha256(runtime_mode),
        "max_single_shard_nanoseconds": 600 * 10**9,
        "max_total_wall_nanoseconds": duration,
        "record_directory": {key: handle[key]
                             for key in ("path", "device", "inode")},
        "runtime_mode": runtime_mode,
        "start_monotonic_ns": start,
        "status": "started",
        "theorem_ready": False,
    }


def strict_ledger(value, handle, runtime_mode):
    if type(value) is not dict or set(value) != {
            "allowed_leaves", "boot_id", "deadline_monotonic_ns",
            "dependency_sha256", "driver_sha256", "format", "gate_sha256",
            "max_single_shard_nanoseconds", "max_total_wall_nanoseconds",
            "record_directory", "runtime_mode", "start_monotonic_ns",
            "status", "theorem_ready"}:
        raise ValueError("ledger schema mismatch")
    start = value["start_monotonic_ns"]
    deadline = value["deadline_monotonic_ns"]
    duration = value["max_total_wall_nanoseconds"]
    if (value["allowed_leaves"] != list(ALLOWED_LEAVES) or
            type(value["boot_id"]) is not str or
            BOOT_PATTERN.fullmatch(value["boot_id"]) is None or
            type(start) is not int or not 0 <= start <= MAX_CLOCK or
            type(deadline) is not int or not 0 <= deadline <= MAX_CLOCK or
            type(duration) is not int or duration != 14_400 * 10**9 or
            deadline != start + duration or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != sha256(FILE) or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-immutable-ledger-v5",
                runtime_mode) or
            value["gate_sha256"] != runtime_gate_sha256(runtime_mode) or
            value["max_single_shard_nanoseconds"] != 600 * 10**9 or
            value["record_directory"] != {
                key: handle[key] for key in ("path", "device", "inode")} or
            value["runtime_mode"] != runtime_mode or
            value["status"] != "started" or
            value["theorem_ready"] is not False):
        raise ValueError("ledger identity mismatch")
    return value


def live_deadline_check(ledger, runtime):
    if _boot_id(runtime.boot_id()) != ledger["boot_id"]:
        raise RuntimeError("Linux boot ID changed; monotonic ledger cannot resume")
    now = _clock(runtime.monotonic_ns(), "current monotonic clock")
    if now < ledger["start_monotonic_ns"] or now > ledger["deadline_monotonic_ns"]:
        raise StageDeadlineExceeded("global immutable wall deadline failed")
    return now


def resource_observation(ledger, runtime, earliest_ns):
    _clock(earliest_ns, "earliest resource timestamp")
    live_deadline_check(ledger, runtime)
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
                 first_after <=
                 second_before <= second_after <= ledger["deadline_monotonic_ns"]) or
            second_before - first_after < 5 * 10**9):
        raise RuntimeError("two-reading live memory gate failed")
    live_deadline_check(ledger, runtime)
    return {
        "first": {"before_monotonic_ns": first_before,
                  "after_monotonic_ns": first_after,
                  "mem_available_kib": first},
        "minimum_separation_nanoseconds": 5 * 10**9,
        "second": {"before_monotonic_ns": second_before,
                   "after_monotonic_ns": second_after,
                   "mem_available_kib": second},
    }


def strict_resource(value, ledger):
    if type(value) is not dict or set(value) != {
            "first", "minimum_separation_nanoseconds", "second"}:
        raise ValueError("resource observation schema mismatch")
    if value["minimum_separation_nanoseconds"] != 5 * 10**9:
        raise ValueError("resource observation separation changed")
    rows = []
    for name in ("first", "second"):
        row = value[name]
        if type(row) is not dict or set(row) != {
                "before_monotonic_ns", "after_monotonic_ns",
                "mem_available_kib"}:
            raise ValueError("resource row schema mismatch")
        before, after, memory = (row["before_monotonic_ns"],
                                 row["after_monotonic_ns"],
                                 row["mem_available_kib"])
        if (type(before) is not int or type(after) is not int or
                type(memory) is not int or memory < 1_400_000 or
                not ledger["start_monotonic_ns"] <= before <= after <=
                ledger["deadline_monotonic_ns"]):
            raise ValueError("resource row identity mismatch")
        rows.append((before, after))
    if rows[1][0] - rows[0][1] < 5 * 10**9:
        raise ValueError("resource observations are too close")
    return True


def child_payload(common_r, ledger_row, runtime_mode="production"):
    self_start = FILE.read_bytes()
    dep_start = snapshots()
    core_start = v2.core.require_pins()
    shard = v2.exact_common_r_shard(common_r, progress=False)
    if (FILE.read_bytes() != self_start or snapshots() != dep_start or
            v2.core.require_pins() != core_start):
        raise RuntimeError("child arithmetic closure changed")
    return {
        "arithmetic_core_sha256": v2.PINNED[v2.CORE_PATH],
        "dependency_sha256": dependency_record(),
        "driver_sha256": sha256_bytes(self_start),
        "format": runtime_format(
            "frontier-active25-inner-D16-child-arithmetic-v5", runtime_mode),
        "gate_sha256": runtime_gate_sha256(runtime_mode),
        "ledger_binding": ledger_row,
        "parameters": v2.core.parameter_record(),
        "shard": shard,
        "status": "complete",
        "theorem_ready": False,
    }


def strict_child(value, expected_r, expected_ledger, runtime_mode):
    if type(value) is not dict or set(value) != {
            "arithmetic_core_sha256", "dependency_sha256", "driver_sha256",
            "format", "gate_sha256", "ledger_binding", "parameters", "shard",
            "status", "theorem_ready"}:
        raise ValueError("child payload schema mismatch")
    if (value["arithmetic_core_sha256"] != v2.PINNED[v2.CORE_PATH] or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != sha256(FILE) or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-child-arithmetic-v5",
                runtime_mode) or
            value["gate_sha256"] != runtime_gate_sha256(runtime_mode) or
            value["ledger_binding"] != expected_ledger or
            value["parameters"] != v2.core.parameter_record() or
            value["status"] != "complete" or
            value["theorem_ready"] is not False):
        raise ValueError("child payload identity mismatch")
    r, _ = v2.strict_shard(value["shard"])
    if r != expected_r:
        raise ValueError("child returned the wrong common count")
    return value


def parse_child_bytes(data, expected_r, expected_ledger, runtime_mode):
    if type(data) is not bytes or len(data) > 16_000_000:
        raise ValueError("child stdout is malformed or too large")
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("child stdout is not strict JSON") from error
    if canonical_json(value) != data:
        raise ValueError("child stdout has truncated or extra bytes")
    return strict_child(value, expected_r, expected_ledger, runtime_mode)


def supervise_command(command, timeout_seconds):
    if (type(command) is not list or not command or
            any(type(item) is not str for item in command) or
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
        raise StageDeadlineExceeded("exact shard child timed out and was killed") from error
    if process.returncode != 0:
        raise RuntimeError(
            f"exact shard child exited {process.returncode}: {stderr[-1000:]!r}")
    if len(stdout) > 16_000_000 or len(stderr) > 16_000_000:
        raise RuntimeError("exact shard child output exceeded the bound")
    if stderr:
        raise RuntimeError("exact shard child emitted unexpected stderr")
    return stdout


def _direct_cli_identity(expected_self_sha256):
    """Bounded trust boundary: a fresh isolated invocation of this file."""
    strict_sha(expected_self_sha256, "expected self SHA")
    if (expected_self_sha256 != sha256(FILE) or not sys.flags.isolated or
            __name__ != "__main__" or __spec__ is not None or
            Path(sys.argv[0]).resolve(strict=True) != FILE):
        raise RuntimeError(
            "production requires a fresh `python3 -I` invocation of the "
            "externally hash-pinned v5 driver")
    return True


_VALIDATE_RUNTIME_MODE, _CAPABILITY_FROM_ISOLATED_CLI = \
    _make_runtime_mode_guard()


def _direct_runtime(expected_self_sha256):
    """Construct production dispatch locally after the isolated-CLI gate."""
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
            return v2.core.mem_available_kib()

        @staticmethod
        def sleep(seconds):
            time.sleep(seconds)

        @staticmethod
        def run_child(common_r, timeout_seconds, ledger_row):
            optimize = ["-O"] if not __debug__ else []
            command = [sys.executable, *optimize, "-I", str(FILE),
                       "--child-stage-r", str(common_r),
                       "--expected-self-sha256", expected_self_sha256,
                       "--ledger-sha256", ledger_row["sha256"],
                       "--ledger-device", str(ledger_row["device"]),
                       "--ledger-inode", str(ledger_row["inode"])]
            return supervise_command(command, timeout_seconds)

    return DirectRuntime()


def make_stage(child, observation, child_start_ns, child_end_ns,
               runtime_mode):
    if (type(child_start_ns) is not int or type(child_end_ns) is not int or
            child_end_ns <= child_start_ns):
        raise ValueError("supervised child interval is malformed")
    supervised_ns = child_end_ns - child_start_ns
    return {
        "child_stdout_sha256": sha256_bytes(canonical_json(child)),
        "dependency_sha256": dependency_record(),
        "driver_sha256": sha256(FILE),
        "format": runtime_format(
            "frontier-active25-inner-D16-common-r-stage-v5", runtime_mode),
        "gate_sha256": runtime_gate_sha256(runtime_mode),
        "ledger_binding": child["ledger_binding"],
        "parameters": v2.core.parameter_record(),
        "resource_observation": observation,
        "runtime_mode": runtime_mode,
        "shard": child["shard"],
        "status": "complete",
        "supervised_child_interval": {
            "end_monotonic_ns": child_end_ns,
            "start_monotonic_ns": child_start_ns,
        },
        "supervised_child_nanoseconds": supervised_ns,
        "theorem_ready": False,
    }


def strict_stage(value, expected_r, ledger, ledger_row, runtime_mode):
    if type(value) is not dict or set(value) != {
            "child_stdout_sha256", "dependency_sha256", "driver_sha256",
            "format", "gate_sha256", "ledger_binding", "parameters",
            "resource_observation", "runtime_mode", "shard", "status",
            "supervised_child_interval", "supervised_child_nanoseconds",
            "theorem_ready"}:
        raise ValueError("stage schema mismatch")
    duration = value["supervised_child_nanoseconds"]
    interval = value["supervised_child_interval"]
    if (type(interval) is not dict or set(interval) != {
            "end_monotonic_ns", "start_monotonic_ns"}):
        raise ValueError("supervised child interval schema mismatch")
    child_start = interval["start_monotonic_ns"]
    child_end = interval["end_monotonic_ns"]
    if (type(duration) is not int or duration <= 0 or
            duration > ledger["max_single_shard_nanoseconds"] or
            type(child_start) is not int or type(child_end) is not int or
            not ledger["start_monotonic_ns"] <= child_start < child_end <=
            ledger["deadline_monotonic_ns"] or
            duration != child_end - child_start or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != sha256(FILE) or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-common-r-stage-v5",
                runtime_mode) or
            value["gate_sha256"] != runtime_gate_sha256(runtime_mode) or
            value["ledger_binding"] != ledger_row or
            value["parameters"] != v2.core.parameter_record() or
            value["runtime_mode"] != runtime_mode or
            value["status"] != "complete" or
            value["theorem_ready"] is not False):
        raise ValueError("stage identity mismatch")
    strict_sha(value["child_stdout_sha256"], "child stdout SHA")
    strict_resource(value["resource_observation"], ledger)
    if value["resource_observation"]["second"]["after_monotonic_ns"] > child_start:
        raise ValueError("resource and child intervals overlap")
    r, vector = v2.strict_shard(value["shard"])
    if r != expected_r:
        raise ValueError("stage common count mismatch")
    reconstructed_child = {
        "arithmetic_core_sha256": v2.PINNED[v2.CORE_PATH],
        "dependency_sha256": dependency_record(),
        "driver_sha256": sha256(FILE),
        "format": runtime_format(
            "frontier-active25-inner-D16-child-arithmetic-v5", runtime_mode),
        "gate_sha256": runtime_gate_sha256(runtime_mode),
        "ledger_binding": ledger_row,
        "parameters": v2.core.parameter_record(),
        "shard": value["shard"],
        "status": "complete",
        "theorem_ready": False,
    }
    if value["child_stdout_sha256"] != sha256_bytes(
            canonical_json(reconstructed_child)):
        raise ValueError("stage does not bind its exact child stdout")
    return vector


def parse_stage_bytes(data, expected_r, ledger, ledger_row, runtime_mode):
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("stage is not strict JSON") from error
    if canonical_json(value) != data:
        raise ValueError("stage JSON is not canonical")
    strict_stage(value, expected_r, ledger, ledger_row, runtime_mode)
    return value


def strict_manifest(value, handle, ledger, ledger_snap, runtime_mode):
    fresh_ledger = read_leaf(handle, LEDGER_LEAF)
    if {key: fresh_ledger[key]
            for key in ("leaf", "sha256", "device", "inode")} != {
            key: ledger_snap[key]
            for key in ("leaf", "sha256", "device", "inode")}:
        raise RuntimeError("manifest no longer binds the immutable ledger")
    if type(value) is not dict or set(value) != {
            "complete", "cumulative_supervised_child_nanoseconds",
            "dependency_sha256", "dimension", "driver_sha256",
            "elapsed_monotonic_nanoseconds", "final_monotonic_ns", "format",
            "gate_sha256", "ledger_binding",
            "merged_raw_J_cross_by_target_R", "parameters", "record_directory",
            "runtime_mode", "stages", "status", "theorem_ready"}:
        raise ValueError("manifest schema mismatch")
    final = value["final_monotonic_ns"]
    elapsed = value["elapsed_monotonic_nanoseconds"]
    cumulative = value["cumulative_supervised_child_nanoseconds"]
    if (value["complete"] is not True or
            type(final) is not int or type(elapsed) is not int or
            type(cumulative) is not int or
            not ledger["start_monotonic_ns"] <= final <=
            ledger["deadline_monotonic_ns"] or
            elapsed != final - ledger["start_monotonic_ns"] or
            not 0 <= cumulative <= elapsed <=
            ledger["max_total_wall_nanoseconds"] or
            value["dependency_sha256"] != dependency_record() or
            value["dimension"] != 27 or
            value["driver_sha256"] != sha256(FILE) or
            value["format"] != runtime_format(
                "frontier-active25-inner-D16-stage-manifest-v5",
                runtime_mode) or
            value["gate_sha256"] != runtime_gate_sha256(runtime_mode) or
            value["ledger_binding"] != ledger_binding(ledger_snap) or
            type(value["merged_raw_J_cross_by_target_R"]) is not list or
            len(value["merged_raw_J_cross_by_target_R"]) != v2.core.K + 1 or
            any(type(x) is not str or str(Q(x)) != x
                for x in value["merged_raw_J_cross_by_target_R"]) or
            value["parameters"] != v2.core.parameter_record() or
            value["record_directory"] != {
                key: handle[key] for key in ("path", "device", "inode")} or
            value["runtime_mode"] != runtime_mode or
            type(value["stages"]) is not list or len(value["stages"]) != 26 or
            value["status"] != "complete" or
            value["theorem_ready"] is not False):
        raise ValueError("manifest identity mismatch")
    seen_inodes = {(ledger_snap["device"], ledger_snap["inode"])}
    shards = []
    stage_total = 0
    previous_end = ledger["start_monotonic_ns"]
    for r, row in enumerate(value["stages"]):
        if type(row) is not dict or set(row) != {
                "common_r", "device", "inode", "leaf", "sha256"}:
            raise ValueError("stage binding schema mismatch")
        if (type(row["common_r"]) is not int or row["common_r"] != r or
                row["leaf"] != STAGE_LEAVES[r] or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError("stage binding identity mismatch")
        strict_sha(row["sha256"], "stage SHA")
        snap = read_leaf(handle, row["leaf"])
        if {key: snap[key] for key in ("leaf", "sha256", "device", "inode")} != {
                key: row[key] for key in ("leaf", "sha256", "device", "inode")}:
            raise RuntimeError("manifest stage binding changed")
        inode_key = (snap["device"], snap["inode"])
        if inode_key in seen_inodes:
            raise ValueError("ledger/stage entries are not inode-distinct")
        seen_inodes.add(inode_key)
        stage = parse_stage_bytes(snap["data"], r, ledger, ledger_binding(ledger_snap),
                                  runtime_mode)
        first_before = stage["resource_observation"]["first"][
            "before_monotonic_ns"]
        child_end = stage["supervised_child_interval"]["end_monotonic_ns"]
        if first_before < previous_end:
            raise ValueError("stage resource/child intervals are not globally ordered")
        previous_end = child_end
        stage_total += stage["supervised_child_nanoseconds"]
        shards.append(stage["shard"])
    merged, identity = v2.merge_exact_shards(shards)
    if (identity is None or stage_total != cumulative or final < previous_end or
            [str(x) for x in merged] !=
            value["merged_raw_J_cross_by_target_R"]):
        raise ValueError("manifest cumulative/merge reconstruction failed")
    return True


def _parse_ledger_snapshot(handle, snap, runtime_mode):
    try:
        value = json.loads(snap["data"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("ledger is not strict JSON") from error
    if canonical_json(value) != snap["data"]:
        raise ValueError("ledger JSON is not canonical")
    return strict_ledger(value, handle, runtime_mode)


def _existing_stage_prefix(handle):
    observed = leaf_set(handle)
    stages = [leaf for leaf in STAGE_LEAVES if leaf in observed]
    if stages != list(STAGE_LEAVES[:len(stages)]):
        raise ValueError("existing stages are not one deterministic prefix")
    expected = {LEDGER_LEAF, *stages}
    if MANIFEST_LEAF in observed:
        expected.add(MANIFEST_LEAF)
    if observed != expected:
        raise ValueError("existing record leaf set is inconsistent")
    return len(stages), MANIFEST_LEAF in observed


def _initialize_ledger_impl(record_dir, runtime, runtime_mode,
                            production_capability=None):
    _VALIDATE_RUNTIME_MODE(runtime_mode, production_capability)
    load_gate()
    self_start = FILE.read_bytes()
    dep_start = snapshots()
    core_start = v2.core.require_pins()
    handle = open_record_dir(record_dir)
    try:
        require_leaf_set(handle, set())
        ledger = make_ledger(handle, runtime, runtime_mode)
        ledger_snap = write_leaf_exclusive(
            handle, LEDGER_LEAF, canonical_json(ledger))
        require_leaf_set(handle, {LEDGER_LEAF})
        if (FILE.read_bytes() != self_start or snapshots() != dep_start or
                v2.core.require_pins() != core_start):
            raise RuntimeError("v5 closure changed during ledger initialization")
        return ledger_snap
    finally:
        close_record_dir(handle)


def _expected_ledger_binding(sha, device, inode):
    strict_sha(sha, "expected ledger SHA")
    if (type(device) is not int or device < 0 or
            type(inode) is not int or inode < 0):
        raise ValueError("expected ledger device/inode is malformed")
    return {"leaf": LEDGER_LEAF, "sha256": sha,
            "device": device, "inode": inode}


def _run_existing_impl(record_dir, runtime, runtime_mode, expected_ledger,
                       production_capability=None):
    _VALIDATE_RUNTIME_MODE(runtime_mode, production_capability)
    if (type(expected_ledger) is not dict or set(expected_ledger) != {
            "leaf", "sha256", "device", "inode"}):
        raise ValueError("external ledger anchor is missing")
    expected_ledger = _expected_ledger_binding(
        expected_ledger["sha256"], expected_ledger["device"],
        expected_ledger["inode"])
    load_gate()
    self_start = FILE.read_bytes()
    dep_start = snapshots()
    core_start = v2.core.require_pins()
    handle = open_record_dir(record_dir)
    try:
        if LEDGER_LEAF not in leaf_set(handle):
            raise ValueError("production requires an initialized ledger")
        ledger_snap = read_leaf(handle, LEDGER_LEAF)
        if ledger_binding(ledger_snap) != expected_ledger:
            raise RuntimeError("external ledger SHA/inode anchor mismatch")
        ledger = _parse_ledger_snapshot(handle, ledger_snap, runtime_mode)
        live_deadline_check(ledger, runtime)
        prefix, has_manifest = _existing_stage_prefix(handle)
        if has_manifest:
            if prefix != 26:
                raise ValueError("manifest exists before all stages")
            require_leaf_set(handle, set(ALLOWED_LEAVES))
            manifest_snap = read_leaf(handle, MANIFEST_LEAF)
            manifest = json.loads(manifest_snap["data"])
            if canonical_json(manifest) != manifest_snap["data"]:
                raise ValueError("existing manifest is not canonical")
            strict_manifest(manifest, handle, ledger, ledger_snap, runtime_mode)
            manifest_after = read_leaf(handle, MANIFEST_LEAF)
            if {key: manifest_after[key]
                    for key in ("sha256", "device", "inode")} != {
                    key: manifest_snap[key]
                    for key in ("sha256", "device", "inode")}:
                raise RuntimeError("completed manifest entry changed")
            return {"manifest_sha256": manifest_snap["sha256"],
                    "resumed_complete": True}
        stage_values = []
        stage_rows = []
        seen_inodes = {(ledger_snap["device"], ledger_snap["inode"])}
        previous_end = ledger["start_monotonic_ns"]
        for r in range(prefix):
            snap = read_leaf(handle, STAGE_LEAVES[r])
            stage = parse_stage_bytes(snap["data"], r, ledger,
                                      ledger_binding(ledger_snap), runtime_mode)
            key = (snap["device"], snap["inode"])
            if key in seen_inodes:
                raise ValueError("existing ledger/stages are hardlinked")
            first_before = stage["resource_observation"]["first"][
                "before_monotonic_ns"]
            if first_before < previous_end:
                raise ValueError(
                    "existing stage resource/child intervals overlap")
            previous_end = stage["supervised_child_interval"][
                "end_monotonic_ns"]
            seen_inodes.add(key)
            stage_values.append(stage)
            stage_rows.append({"common_r": r, **{
                key: snap[key] for key in ("leaf", "sha256", "device", "inode")}})
        for r in range(prefix, 26):
            expected_before = {LEDGER_LEAF, *STAGE_LEAVES[:r]}
            require_leaf_set(handle, expected_before)
            observation = resource_observation(ledger, runtime, previous_end)
            before_child = live_deadline_check(ledger, runtime)
            remaining = ledger["deadline_monotonic_ns"] - before_child
            timeout_ns = min(ledger["max_single_shard_nanoseconds"], remaining)
            if timeout_ns <= 0:
                raise StageDeadlineExceeded("no time remains for another shard")
            stdout = runtime.run_child(r, timeout_ns / 10**9,
                                       ledger_binding(ledger_snap))
            after_child = live_deadline_check(ledger, runtime)
            supervised = after_child - before_child
            if supervised <= 0 or supervised > timeout_ns:
                raise StageDeadlineExceeded("child exceeded its supervised deadline")
            child = parse_child_bytes(stdout, r, ledger_binding(ledger_snap),
                                      runtime_mode)
            require_leaf_set(handle, expected_before)
            stage = make_stage(child, observation, before_child, after_child,
                               runtime_mode)
            strict_stage(stage, r, ledger, ledger_binding(ledger_snap), runtime_mode)
            snap = write_leaf_exclusive(handle, STAGE_LEAVES[r],
                                        canonical_json(stage))
            require_leaf_set(handle, expected_before | {STAGE_LEAVES[r]})
            fresh_ledger = read_leaf(handle, LEDGER_LEAF)
            if {key: fresh_ledger[key] for key in ("sha256", "device", "inode")} != {
                    key: ledger_snap[key] for key in ("sha256", "device", "inode")}:
                raise RuntimeError("immutable ledger changed during staging")
            key = (snap["device"], snap["inode"])
            if key in seen_inodes:
                raise ValueError("new stage aliases an existing inode")
            seen_inodes.add(key)
            previous_end = after_child
            stage_values.append(stage)
            stage_rows.append({"common_r": r, **{
                key: snap[key] for key in ("leaf", "sha256", "device", "inode")}})
        require_leaf_set(handle, {LEDGER_LEAF, *STAGE_LEAVES})
        merged, identity = v2.merge_exact_shards(
            [value["shard"] for value in stage_values])
        if identity is None:
            raise ArithmeticError("exact stage set has no inner identity")
        final = live_deadline_check(ledger, runtime)
        elapsed = final - ledger["start_monotonic_ns"]
        cumulative = sum(value["supervised_child_nanoseconds"]
                         for value in stage_values)
        manifest = {
            "complete": True,
            "cumulative_supervised_child_nanoseconds": cumulative,
            "dependency_sha256": dependency_record(),
            "dimension": 27,
            "driver_sha256": sha256_bytes(self_start),
            "elapsed_monotonic_nanoseconds": elapsed,
            "final_monotonic_ns": final,
            "format": runtime_format(
                "frontier-active25-inner-D16-stage-manifest-v5", runtime_mode),
            "gate_sha256": runtime_gate_sha256(runtime_mode),
            "ledger_binding": ledger_binding(ledger_snap),
            "merged_raw_J_cross_by_target_R": [str(x) for x in merged],
            "parameters": v2.core.parameter_record(),
            "record_directory": {key: handle[key]
                                 for key in ("path", "device", "inode")},
            "runtime_mode": runtime_mode,
            "stages": stage_rows,
            "status": "complete",
            "theorem_ready": False,
        }
        strict_manifest(manifest, handle, ledger, ledger_snap, runtime_mode)
        require_leaf_set(handle, {LEDGER_LEAF, *STAGE_LEAVES})
        if (FILE.read_bytes() != self_start or snapshots() != dep_start or
                v2.core.require_pins() != core_start):
            raise RuntimeError("v5 closure changed before manifest")
        manifest_snap = write_leaf_exclusive(handle, MANIFEST_LEAF,
                                             canonical_json(manifest))
        require_leaf_set(handle, set(ALLOWED_LEAVES))
        strict_manifest(manifest, handle, ledger, ledger_snap, runtime_mode)
        if live_deadline_check(ledger, runtime) > ledger["deadline_monotonic_ns"]:
            raise StageDeadlineExceeded("deadline changed after manifest")
        if (FILE.read_bytes() != self_start or snapshots() != dep_start or
                v2.core.require_pins() != core_start):
            raise RuntimeError("v5 closure changed after manifest")
        require_leaf_set(handle, set(ALLOWED_LEAVES))
        manifest_after = read_leaf(handle, MANIFEST_LEAF)
        if {key: manifest_after[key]
                for key in ("sha256", "device", "inode")} != {
                key: manifest_snap[key]
                for key in ("sha256", "device", "inode")}:
            raise RuntimeError("published manifest entry changed")
        return {"manifest_sha256": manifest_snap["sha256"],
                "resumed_complete": False}
    finally:
        close_record_dir(handle)


def _initialize_ledger_test_only(record_dir, runtime):
    """Synthetic-only initializer; its ledger is production-incompatible."""
    return _initialize_ledger_impl(record_dir, runtime, "synthetic-test")


def _run_all_test_only(record_dir, runtime):
    """Synthetic state machine; it can never emit production-format bytes."""
    handle = open_record_dir(record_dir)
    try:
        observed = leaf_set(handle)
    finally:
        close_record_dir(handle)
    if not observed:
        snap = _initialize_ledger_test_only(record_dir, runtime)
    else:
        handle = open_record_dir(record_dir)
        try:
            snap = read_leaf(handle, LEDGER_LEAF)
        finally:
            close_record_dir(handle)
    return _run_existing_impl(record_dir, runtime, "synthetic-test",
                              ledger_binding(snap))


def _initialize_ledger_production_cli(record_dir, expected_self_sha256):
    capability = _CAPABILITY_FROM_ISOLATED_CLI(expected_self_sha256)
    runtime = _direct_runtime(expected_self_sha256)
    snap = _initialize_ledger_impl(
        record_dir, runtime, "production", capability)
    return {"ledger_binding": ledger_binding(snap),
            "status": "initialized-ledger-only"}


def _run_production_cli(record_dir, expected_self_sha256,
                        expected_ledger_sha256, expected_ledger_device,
                        expected_ledger_inode):
    capability = _CAPABILITY_FROM_ISOLATED_CLI(expected_self_sha256)
    runtime = _direct_runtime(expected_self_sha256)
    expected = _expected_ledger_binding(
        expected_ledger_sha256, expected_ledger_device,
        expected_ledger_inode)
    return _run_existing_impl(
        record_dir, runtime, "production", expected, capability)


def preflight():
    gate = load_gate()
    return {
        "allowed_leaves": list(ALLOWED_LEAVES),
        "dimension": 27,
        "driver_sha256": sha256(FILE),
        "gate_sha256": PINNED[GATE],
        "global_deadline_is_boot_bound": True,
        "launch_authorized_by_gate": gate["launch_authorized"],
        "one_worker_only": True,
        "resource_gate": gate["resource_gate"],
        "stage_child_only_then_parent_o_excl": True,
        "status": "frontier-active25-v5-authorized-preflight",
        "target_started": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--initialize-ledger-only", action="store_true")
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--expected-ledger-sha256")
    parser.add_argument("--expected-ledger-device", type=int)
    parser.add_argument("--expected-ledger-inode", type=int)
    parser.add_argument("--child-stage-r", type=int)
    parser.add_argument("--ledger-sha256")
    parser.add_argument("--ledger-device", type=int)
    parser.add_argument("--ledger-inode", type=int)
    args = parser.parse_args()
    child_fields = (args.child_stage_r, args.ledger_sha256,
                    args.ledger_device, args.ledger_inode)
    expected_ledger_fields = (args.expected_ledger_sha256,
                              args.expected_ledger_device,
                              args.expected_ledger_inode)
    if args.preflight_only:
        if (args.initialize_ledger_only or args.record_dir is not None or
                args.expected_self_sha256 is not None or
                any(x is not None for x in child_fields) or
                any(x is not None for x in expected_ledger_fields)):
            parser.error("preflight takes no target arguments")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    if args.initialize_ledger_only:
        if (args.record_dir is None or args.expected_self_sha256 is None or
                any(x is not None for x in child_fields) or
                any(x is not None for x in expected_ledger_fields)):
            parser.error(
                "ledger initialization requires only record dir and self SHA")
        print(json.dumps(_initialize_ledger_production_cli(
            args.record_dir, args.expected_self_sha256), sort_keys=True))
        return
    if any(x is not None for x in child_fields):
        if (args.record_dir is not None or
                args.expected_self_sha256 is None or
                any(x is not None for x in expected_ledger_fields) or
                any(x is None for x in child_fields) or
                type(args.child_stage_r) is not int or
                args.child_stage_r not in range(26) or
                type(args.ledger_device) is not int or args.ledger_device < 0 or
                type(args.ledger_inode) is not int or args.ledger_inode < 0):
            parser.error("child stage requires one complete ledger binding")
        _direct_cli_identity(args.expected_self_sha256)
        strict_sha(args.ledger_sha256, "ledger SHA")
        row = {"leaf": LEDGER_LEAF, "sha256": args.ledger_sha256,
               "device": args.ledger_device, "inode": args.ledger_inode}
        sys.stdout.buffer.write(canonical_json(child_payload(args.child_stage_r,
                                                             row)))
        return
    if (args.record_dir is None or args.expected_self_sha256 is None or
            any(x is None for x in expected_ledger_fields)):
        parser.error(
            "production resume requires record dir, self SHA, and the "
            "external ledger SHA/device/inode anchor")
    print(json.dumps(_run_production_cli(
        args.record_dir, args.expected_self_sha256,
        args.expected_ledger_sha256, args.expected_ledger_device,
        args.expected_ledger_inode), sort_keys=True))


if __name__ == "__main__":
    main()
