#!/usr/bin/env python3
"""Authorized, resume-safe exact-common-r producer for the active25 pencil.

This source only stages the 26 exact inner/shell cross shards and a manifest.
It does not assemble a pencil or make a sign claim.  The byte-pinned v3 gate
is authorized, but repository policy still withholds execution until an
independent v3 delta audit and a later explicit root launch instruction.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
V2 = HERE / "frontier_active25_inner_d16_staged_v2.py"
V2_TEST = HERE / "test_frontier_active25_inner_d16_staged_v2.py"
V2_SPEC = HERE / "FRONTIER-ACTIVE25-INNER-D16-TAGGED-SHELL-PRELAUNCH-V2.md"
GATE = HERE / "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v3.json"
AUDIT_CHECKER = REPO / "agents/audit/verify_frontier_active25_grouped_prelaunch.py"
AUDIT_RESULT = REPO / "agents/audit/results/frontier_active25_grouped_prelaunch_v2_audit.json"
AUDIT_REPORT = REPO / "agents/audit/FRONTIER-ACTIVE25-GROUPED-PRELAUNCH-V2-AUDIT.md"

PINNED = {
    V2: "bb00675f722a843c0d87ef36e382aea812d6622c79da517e238b0146af9592dd",
    V2_TEST: "27fabdfa8e4f73820ca70af6189751d2e30acd7f699b580b9cd2cfdb625f10ed",
    V2_SPEC: "1a39e72a2d69ab0e64570ed05a9b0ea762b7f4223a4d88205d7a1f525230c721",
    GATE: "19ab3d54c08fbd24d6b70ea9d946ca7272030bf20716da383f4bed285de411bb",
    AUDIT_CHECKER: "dba6064473a56cb16c99c4423efb0852b3990d0a7f39d027c1b5c1bdc0f4c622",
    AUDIT_RESULT: "bd93b52f3556b9d35edb2568b61c74362e4e156f5b607e6755f2ac7203a3c9a2",
    AUDIT_REPORT: "0c37f563d99191f0fbb4abc1c0ea5700ed6288ed9011d5edc691c91394cdc6a9",
}
STAGE_LEAVES = tuple(f"common_r_{r:02d}.json" for r in range(26))
MANIFEST_LEAF = "manifest.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"v3 staged dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()
_SPEC = importlib.util.spec_from_file_location("active25_staged_v2_core", V2)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(V2)
v2 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = v2
_SPEC.loader.exec_module(v2)


def dependency_record():
    return {str(path.relative_to(REPO)): expected
            for path, expected in sorted(PINNED.items(), key=lambda item: str(item[0]))}


def load_gate():
    gate = json.loads(_START[GATE])
    resource_gate = gate.get("resource_gate")
    audit = gate.get("independent_v2_prelaunch_audit")
    if (gate.get("format") !=
            "frontier-active25-inner-D16-tagged-shell-authorized-gate-v3" or
            gate.get("status") != "AUTHORIZED" or
            gate.get("launch_authorized") is not True or
            gate.get("arithmetic_core_sha256") != v2.PINNED[v2.CORE_PATH] or
            gate.get("active_outer_counts") != list(range(26)) or
            gate.get("stage_common_r") != list(range(26)) or
            gate.get("dimension") != 27 or
            type(resource_gate) is not dict or
            resource_gate.get("workers") != 1 or
            resource_gate.get("required_stable_mem_readings") != 2 or
            resource_gate.get("minimum_mem_available_kib_each_reading") != 1_400_000 or
            resource_gate.get("minimum_seconds_between_mem_readings") != 5 or
            resource_gate.get("max_total_wall_seconds") != 14_400 or
            gate.get("wall_envelope_seconds") !=
            "9989.249547201907905" or
            type(audit) is not dict or
            audit != {
                "checker_sha256": PINNED[AUDIT_CHECKER],
                "report_sha256": PINNED[AUDIT_REPORT],
                "result_sha256": PINNED[AUDIT_RESULT],
                "status": "PRELAUNCH PASS",
            }):
        raise ValueError("v3 authorization gate identity mismatch")
    audited = json.loads(_START[AUDIT_RESULT])
    if (audited.get("status") !=
            "PRELAUNCH PASS FOR FROZEN DISABLED V2; LAUNCH DISABLED" or
            audited.get("pinned", {}).get(str(V2.relative_to(REPO))) !=
            PINNED[V2] or
            audited.get("pinned", {}).get(str(V2_TEST.relative_to(REPO))) !=
            PINNED[V2_TEST]):
        raise ValueError("v2 audit does not bind the frozen v2 tuple")
    return gate


def live_resource_gate(*, reader=None, sleeper=None):
    gate = load_gate()["resource_gate"]
    reader = v2.core.mem_available_kib if reader is None else reader
    sleeper = time.sleep if sleeper is None else sleeper
    readings = []
    for index in range(2):
        value = reader()
        if type(value) is not int or value < 0:
            raise ValueError("MemAvailable reader returned a malformed value")
        readings.append(value)
        if index == 0:
            sleeper(gate["minimum_seconds_between_mem_readings"])
    if any(value < gate["minimum_mem_available_kib_each_reading"]
           for value in readings):
        raise RuntimeError("live MemAvailable resource gate failed")
    return readings


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def build_stage(common_r, *, inner_loader=v2.core.load_inner_coordinate,
                progress=True):
    if type(common_r) is not int or common_r not in range(26):
        raise ValueError("common_r is outside the authorized stage set")
    started = time.monotonic_ns()
    self_start = FILE.read_bytes()
    dep_start = snapshots()
    core_start = v2.core.require_pins()
    shard = v2.exact_common_r_shard(
        common_r, inner_loader=inner_loader, progress=progress)
    if (FILE.read_bytes() != self_start or snapshots() != dep_start or
            v2.core.require_pins() != core_start):
        raise RuntimeError("v3 stage closure changed during traversal")
    return {
        "arithmetic_core_sha256": v2.PINNED[v2.CORE_PATH],
        "complete_common_r": True,
        "dependency_sha256": dependency_record(),
        "driver_sha256": sha256_bytes(self_start),
        "format": "frontier-active25-inner-D16-common-r-stage-v3",
        "gate_sha256": PINNED[GATE],
        "parameters": v2.core.parameter_record(),
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "shard": shard,
        "status": "complete",
        "theorem_ready": False,
        "wall_nanoseconds": time.monotonic_ns() - started,
    }


def strict_stage(value, expected_r=None):
    if type(value) is not dict or set(value) != {
            "arithmetic_core_sha256", "complete_common_r",
            "dependency_sha256", "driver_sha256", "format", "gate_sha256",
            "parameters", "peak_rss_kib", "shard", "status",
            "theorem_ready", "wall_nanoseconds"}:
        raise ValueError("stage schema mismatch")
    if (value["arithmetic_core_sha256"] != v2.PINNED[v2.CORE_PATH] or
            value["complete_common_r"] is not True or
            value["dependency_sha256"] != dependency_record() or
            value["driver_sha256"] != sha256(FILE) or
            value["format"] !=
            "frontier-active25-inner-D16-common-r-stage-v3" or
            value["gate_sha256"] != PINNED[GATE] or
            value["parameters"] != v2.core.parameter_record() or
            type(value["peak_rss_kib"]) is not int or
            value["peak_rss_kib"] <= 0 or
            value["status"] != "complete" or
            value["theorem_ready"] is not False or
            type(value["wall_nanoseconds"]) is not int or
            value["wall_nanoseconds"] <= 0):
        raise ValueError("stage identity mismatch")
    r, vector = v2.strict_shard(value["shard"])
    if expected_r is not None and r != expected_r:
        raise ValueError("stage is bound to the wrong common count")
    return r, vector


def parse_stage_bytes(data: bytes, expected_r=None):
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("stage is not strict JSON") from error
    if canonical_json(value) != data:
        raise ValueError("stage JSON is not canonical")
    strict_stage(value, expected_r)
    return value


def _safe_leaf(name):
    if (type(name) is not str or not name or Path(name).name != name or
            name in (".", "..") or "/" in name or "\x00" in name):
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
        raise ValueError("record path is not a directory")
    handle = {"path": canonical, "device": int(observed.st_dev),
              "inode": int(observed.st_ino), "descriptor": descriptor}
    validate_record_dir(handle)
    return handle


def close_record_dir(handle):
    descriptor = handle.get("descriptor")
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
        current = os.fstat(check)
        if ((int(current.st_dev), int(current.st_ino)) !=
                (handle["device"], handle["inode"])):
            raise RuntimeError("record-directory pathname was replaced")
    finally:
        os.close(check)
    return True


def read_leaf(handle, name, *, maximum_bytes=16_000_000):
    validate_record_dir(handle)
    name = _safe_leaf(name)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=handle["descriptor"])
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_size < 0 or
                before.st_size > maximum_bytes):
            raise ValueError("record leaf is not a bounded regular file")
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
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)):
            raise RuntimeError("record leaf changed during read")
        validate_record_dir(handle)
        return {"data": data, "sha256": sha256_bytes(data),
                "device": int(after.st_dev), "inode": int(after.st_ino),
                "leaf": name}
    finally:
        os.close(descriptor)


def leaf_exists(handle, name):
    validate_record_dir(handle)
    name = _safe_leaf(name)
    try:
        observed = os.stat(name, dir_fd=handle["descriptor"],
                           follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(observed.st_mode):
        raise ValueError("existing record leaf is not regular")
    return True


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
                raise OSError("short record-leaf write")
            position += count
        os.fsync(descriptor)
        owned = os.fstat(descriptor)
        if not stat.S_ISREG(owned.st_mode):
            raise RuntimeError("published record leaf is not regular")
        os.lseek(descriptor, 0, os.SEEK_SET)
        written = b""
        while len(written) < len(data) + 1:
            block = os.read(descriptor, min(1_048_576,
                                            len(data) + 1 - len(written)))
            if not block:
                break
            written += block
        rebound = read_leaf(handle, name, maximum_bytes=max(1, len(data)))
        if (written != data or rebound["data"] != data or
                (rebound["device"], rebound["inode"]) !=
                (int(owned.st_dev), int(owned.st_ino))):
            raise RuntimeError("published record leaf was replaced")
        os.fsync(handle["descriptor"])
        return rebound
    finally:
        os.close(descriptor)


def strict_manifest(value, handle, expected_sha=None):
    if type(value) is not dict or set(value) != {
            "complete", "dependency_sha256", "dimension", "driver_sha256",
            "format", "gate_sha256", "merged_raw_J_cross_by_target_R",
            "parameters", "record_directory", "resource_readings_kib",
            "stages", "status", "theorem_ready", "wall_nanoseconds"}:
        raise ValueError("manifest schema mismatch")
    directory = value["record_directory"]
    readings = value["resource_readings_kib"]
    if (value["complete"] is not True or
            value["dependency_sha256"] != dependency_record() or
            value["dimension"] != 27 or
            value["driver_sha256"] != sha256(FILE) or
            value["format"] !=
            "frontier-active25-inner-D16-stage-manifest-v3" or
            value["gate_sha256"] != PINNED[GATE] or
            value["parameters"] != v2.core.parameter_record() or
            type(directory) is not dict or directory != {
                "path": handle["path"], "device": handle["device"],
                "inode": handle["inode"]} or
            type(readings) is not list or len(readings) != 2 or
            any(type(x) is not int or x < 1_400_000 for x in readings) or
            value["status"] != "complete" or
            value["theorem_ready"] is not False or
            type(value["wall_nanoseconds"]) is not int or
            value["wall_nanoseconds"] <= 0 or
            type(value["merged_raw_J_cross_by_target_R"]) is not list or
            len(value["merged_raw_J_cross_by_target_R"]) != v2.core.K + 1 or
            any(type(x) is not str or str(Q(x)) != x
                for x in value["merged_raw_J_cross_by_target_R"]) or
            type(value["stages"]) is not list or len(value["stages"]) != 26):
        raise ValueError("manifest identity mismatch")
    if expected_sha is not None and (type(expected_sha) is not str or
            len(expected_sha) != 64 or
            any(c not in "0123456789abcdef" for c in expected_sha)):
        raise ValueError("expected manifest SHA is malformed")
    expected_rows = []
    shards = []
    for r, row in enumerate(value["stages"]):
        if type(row) is not dict or set(row) != {
                "common_r", "device", "inode", "leaf", "sha256"}:
            raise ValueError("stage binding schema mismatch")
        if (row["common_r"] != r or type(row["common_r"]) is not int or
                row["leaf"] != STAGE_LEAVES[r] or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0 or
                type(row["sha256"]) is not str or len(row["sha256"]) != 64):
            raise ValueError("stage binding identity mismatch")
        snap = read_leaf(handle, row["leaf"])
        if {key: snap[key] for key in ("leaf", "sha256", "device", "inode")} != {
                key: row[key] for key in ("leaf", "sha256", "device", "inode")}:
            raise RuntimeError("manifest stage binding changed")
        stage = parse_stage_bytes(snap["data"], r)
        shards.append(stage["shard"])
        expected_rows.append(row)
    merged, identity = v2.merge_exact_shards(shards)
    if ([str(x) for x in merged] != value["merged_raw_J_cross_by_target_R"] or
            identity is None):
        raise ValueError("manifest exact merge mismatch")
    return True


def run_all(record_dir, *, stage_builder=None, mem_reader=None, sleeper=None):
    """Create or validate 26 exact shards, then atomically add a manifest."""
    gate = load_gate()
    if gate["launch_authorized"] is not True:
        raise RuntimeError("v3 gate is not authorized")
    readings = live_resource_gate(reader=mem_reader, sleeper=sleeper)
    started = time.monotonic_ns()
    self_start = FILE.read_bytes()
    dep_start = snapshots()
    core_start = v2.core.require_pins()
    handle = open_record_dir(record_dir)
    try:
        allowed = set(STAGE_LEAVES) | {MANIFEST_LEAF}
        observed = set(os.listdir(handle["descriptor"]))
        if not observed <= allowed:
            raise ValueError("record directory contains an unauthorized leaf")
        if MANIFEST_LEAF in observed:
            manifest_snap = read_leaf(handle, MANIFEST_LEAF)
            manifest = json.loads(manifest_snap["data"])
            if canonical_json(manifest) != manifest_snap["data"]:
                raise ValueError("existing manifest is not canonical")
            strict_manifest(manifest, handle, manifest_snap["sha256"])
            return {"manifest_sha256": manifest_snap["sha256"],
                    "resumed_complete": True}
        builder = build_stage if stage_builder is None else stage_builder
        stage_rows = []
        stage_values = []
        for r, leaf in enumerate(STAGE_LEAVES):
            if leaf_exists(handle, leaf):
                snap = read_leaf(handle, leaf)
                stage = parse_stage_bytes(snap["data"], r)
            else:
                stage = builder(r)
                strict_stage(stage, r)
                snap = write_leaf_exclusive(handle, leaf,
                                            canonical_json(stage))
            stage_rows.append({"common_r": r, "leaf": leaf,
                               "sha256": snap["sha256"],
                               "device": snap["device"],
                               "inode": snap["inode"]})
            stage_values.append(stage)
            if (time.monotonic_ns() - started >
                    gate["resource_gate"]["max_total_wall_seconds"] * 10**9):
                raise RuntimeError(
                    "v3 traversal exceeded the frozen wall gate")
        merged, identity = v2.merge_exact_shards(
            [value["shard"] for value in stage_values])
        if identity is None:
            raise ArithmeticError("empty exact shard identity")
        elapsed = time.monotonic_ns() - started
        if elapsed > gate["resource_gate"]["max_total_wall_seconds"] * 10**9:
            raise RuntimeError("v3 traversal exceeded the frozen wall gate")
        manifest = {
            "complete": True,
            "dependency_sha256": dependency_record(),
            "dimension": 27,
            "driver_sha256": sha256_bytes(self_start),
            "format": "frontier-active25-inner-D16-stage-manifest-v3",
            "gate_sha256": PINNED[GATE],
            "merged_raw_J_cross_by_target_R": [str(x) for x in merged],
            "parameters": v2.core.parameter_record(),
            "record_directory": {key: handle[key]
                                 for key in ("path", "device", "inode")},
            "resource_readings_kib": readings,
            "stages": stage_rows,
            "status": "complete",
            "theorem_ready": False,
            "wall_nanoseconds": elapsed,
        }
        if (FILE.read_bytes() != self_start or snapshots() != dep_start or
                v2.core.require_pins() != core_start):
            raise RuntimeError("v3 closure changed before manifest publication")
        manifest_snap = write_leaf_exclusive(
            handle, MANIFEST_LEAF, canonical_json(manifest))
        strict_manifest(manifest, handle, manifest_snap["sha256"])
        if (FILE.read_bytes() != self_start or snapshots() != dep_start or
                v2.core.require_pins() != core_start):
            raise RuntimeError("v3 closure changed after manifest publication")
        validate_record_dir(handle)
        return {"manifest_sha256": manifest_snap["sha256"],
                "resumed_complete": False}
    finally:
        close_record_dir(handle)


def preflight():
    gate = load_gate()
    return {
        "active_common_r": list(range(26)),
        "arithmetic_core_sha256": v2.PINNED[v2.CORE_PATH],
        "dimension": 27,
        "driver_sha256": sha256(FILE),
        "gate_sha256": PINNED[GATE],
        "independent_v2_audit_sha256": PINNED[AUDIT_RESULT],
        "launch_authorized_by_gate": gate["launch_authorized"],
        "one_worker_only": True,
        "record_leaves": list(STAGE_LEAVES),
        "resource_gate": gate["resource_gate"],
        "status": "frontier-active25-v3-authorized-preflight",
        "target_started": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--record-dir", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        if args.record_dir is not None:
            parser.error("preflight takes no record directory")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    if args.record_dir is None:
        parser.error("target staging requires --record-dir")
    print(json.dumps(run_all(args.record_dir), sort_keys=True))


if __name__ == "__main__":
    main()
