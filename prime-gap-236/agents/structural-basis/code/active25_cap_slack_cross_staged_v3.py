#!/usr/bin/env python3
"""Disabled one-shot staging package for the pruned cap-slack/D16 cross.

The arithmetic unit is one complete common-r shard, but a production attempt
is deliberately non-resumable: after a separately initialized ledger, one
fresh invocation must compute r=0..25 in order and publish a manifest.  Every
production path requires externally supplied source, authorization, and ledger
bindings.  This candidate's package gate remains ``launch_authorized=false``;
no target traversal is performed by preflight or tests.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import stat
import subprocess
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
PILOT_SOURCE = FILE.with_name("active25_cap_slack_cross_pilot_v2.py")
PILOT_TEST = (REPO / "agents/structural-basis/tests/"
              "test_active25_cap_slack_cross_pilot_v2.py")
PILOT_SPEC = (REPO / "agents/structural-basis/"
              "ACTIVE25-CAP-SLACK-CROSS-PILOT-V2.md")
PILOT_ARTIFACT = (REPO / "agents/structural-basis/results/"
                  "active25_cap_slack_d16_cross_pilot_disabled_v2.json")
AUDIT_CHECKER = (REPO / "agents/audit/"
                 "verify_active25_cap_slack_cross_pilot_v2.py")
AUDIT_RESULT = (REPO / "agents/audit/results/"
                "active25_cap_slack_cross_pilot_v2_prelaunch_audit.json")
AUDIT_REPORT = (REPO / "agents/audit/"
                "ACTIVE25-CAP-SLACK-CROSS-PILOT-V2-PRELAUNCH-AUDIT.md")
GATE_SOURCE = FILE.with_name("active25_cap_slack_cross_face_gate_v3.py")
GATE_TEST = (REPO / "agents/structural-basis/tests/"
             "test_active25_cap_slack_cross_face_gate_v3.py")
GATE_ARTIFACT = (REPO / "agents/structural-basis/results/"
                 "active25_cap_slack_d16_cross_face_r10_h10_gate_v3.json")
INDEPENDENT_DESIGN = (REPO / "agents/audit/"
                      "ACTIVE25-CAP-SLACK-D16-INDEPENDENT-"
                      "RECONSTRUCTION-DESIGN-V3.md")
CAP_D2 = REPO / "results/active25_count_cap_slack_shell_d2_v1.json"

PINNED = {
    PILOT_SOURCE:
        "cd20a85e51d623476b5433626ec4ce35d242e8a00a5f706db1af05509b59d913",
    PILOT_TEST:
        "8f16fdc5a72f8e26ffc5c7b2a0ee5f0e8fc734a4383edeb3a2d414a97df94a1f",
    PILOT_SPEC:
        "ce965d905274af92a3c64496369ffdb5cd97bf5c75a088432428f5707d032851",
    PILOT_ARTIFACT:
        "3a07078ca5b480b0d8d554019b42e05b7fb732a1225d97ff761d5b5231abd31c",
    AUDIT_CHECKER:
        "881622f7bb8e189f240e76c8a31750ef0fb2db42b1561d9e03e06dc1124348fe",
    AUDIT_RESULT:
        "bbda024a64b32bca96c76cc7b77917b4779daa3c1c108f3a2ff163200249112d",
    AUDIT_REPORT:
        "bf8e3bbfec2c6fe3bec3a9a30a7c6caa26ad6912b93b4082253feb4438e5b17a",
    GATE_SOURCE:
        "71d1c028e09cbf3484c8b2a7c37e650f747c479ff71fcebb512dbce05ef974a5",
    GATE_TEST:
        "0e7b863a096045d20aedba7d16b62edb3110e8b12eb55469cd5d1118cba86cf0",
    GATE_ARTIFACT:
        "54d9bf648679c373ad6de8178e194d05f395f8150990060da187720f92f4adc8",
    INDEPENDENT_DESIGN:
        "b0fc8a48ead25f5b9c1eb4c632c4a9a69205bb39e5b538affd66f4ab688069cd",
    CAP_D2:
        "c66cd86055385dc372d948d2f209f84fb850136120d21b55554806ba25d73d63",
}

LEDGER_LEAF = "ledger.json"
STAGE_LEAVES = tuple(f"common_r_{r:02d}.json" for r in range(26))
MANIFEST_LEAF = "manifest.json"
ALLOWED_LEAVES = (LEDGER_LEAF, *STAGE_LEAVES, MANIFEST_LEAF)
AUTHORIZATION_FORMAT = "active25-cap-slack-D16-v3-root-launch-authorization-v1"
LEDGER_FORMAT = "active25-cap-slack-D16-one-shot-ledger-v3"
CHILD_FORMAT = "active25-cap-slack-D16-common-r-child-v3"
SHARD_FORMAT = "active25-cap-slack-D16-common-r-shard-v3"
MANIFEST_FORMAT = "active25-cap-slack-D16-one-shot-manifest-v3"
MAX_TOTAL_WALL_SECONDS = 7200
MAX_CHILD_WALL_SECONDS = 600
MAX_CHILD_RSS_KIB = 256 * 1024
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")
BOOT_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
BOOT_ID_PATH = Path("/proc/sys/kernel/random/boot_id")


class StageTimeout(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def strict_sha(value, name):
    if type(value) is not str or SHA_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def strict_q(value, name):
    if type(value) is not str:
        raise ValueError(f"{name} is not a rational string")
    try:
        parsed = Q(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not rational") from error
    if str(parsed) != value:
        raise ValueError(f"{name} is not canonical")
    return parsed


def strict_json_bytes(data, name):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {name}: {key}")
            result[key] = value
        return result
    try:
        return json.loads(
            data, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite constant in {name}: {value}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON in {name}") from error


def _read_descriptor(descriptor, maximum=4_000_000):
    os.lseek(descriptor, 0, os.SEEK_SET)
    blocks = []
    remaining = maximum + 1
    while remaining:
        block = os.read(descriptor, min(1_048_576, remaining))
        if not block:
            break
        blocks.append(block)
        remaining -= len(block)
    data = b"".join(blocks)
    if len(data) > maximum:
        raise ValueError("bound file exceeds its size limit")
    return data


def _open_stable_regular(path, maximum=4_000_000):
    target = Path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags)
    try:
        before = os.fstat(descriptor)
        data = _read_descriptor(descriptor, maximum)
        after = os.fstat(descriptor)
        identity_before = (before.st_dev, before.st_ino, before.st_size,
                           before.st_mtime_ns, before.st_ctime_ns,
                           before.st_nlink)
        identity_after = (after.st_dev, after.st_ino, after.st_size,
                          after.st_mtime_ns, after.st_ctime_ns,
                          after.st_nlink)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                identity_before != identity_after or len(data) != after.st_size):
            raise RuntimeError(f"unstable or aliased regular file: {target}")
        return {"descriptor": descriptor, "path": str(target.resolve()),
                "data": data, "sha256": sha256_bytes(data),
                "device": int(after.st_dev), "inode": int(after.st_ino),
                "size": int(after.st_size), "mtime_ns": int(after.st_mtime_ns),
                "ctime_ns": int(after.st_ctime_ns), "nlink": int(after.st_nlink)}
    except Exception:
        os.close(descriptor)
        raise


def _rebind_stable_regular(handle, maximum=4_000_000):
    held = os.fstat(handle["descriptor"])
    held_data = _read_descriptor(handle["descriptor"], maximum)
    current = _open_stable_regular(handle["path"], maximum)
    try:
        identity = (handle["device"], handle["inode"], handle["size"],
                    handle["mtime_ns"], handle["ctime_ns"], handle["nlink"])
        held_identity = (int(held.st_dev), int(held.st_ino), int(held.st_size),
                         int(held.st_mtime_ns), int(held.st_ctime_ns),
                         int(held.st_nlink))
        current_identity = tuple(current[key] for key in
                                 ("device", "inode", "size", "mtime_ns",
                                  "ctime_ns", "nlink"))
        if (identity != held_identity or identity != current_identity or
                held_data != handle["data"] or current["data"] != handle["data"]):
            raise RuntimeError(f"externally bound file changed: {handle['path']}")
        return handle["data"]
    finally:
        os.close(current["descriptor"])


_SELF = _open_stable_regular(FILE)


def bind_startup_self(expected_sha256):
    strict_sha(expected_sha256, "expected producer self SHA")
    if expected_sha256 != _SELF["sha256"]:
        raise RuntimeError("externally supplied producer SHA does not match")
    return _rebind_stable_regular(_SELF)


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"frozen staged dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()
_PILOT_SPEC = importlib.util.spec_from_file_location(
    "active25_cap_slack_staged_frozen_pilot", PILOT_SOURCE)
if _PILOT_SPEC is None or _PILOT_SPEC.loader is None:
    raise ImportError(PILOT_SOURCE)
pilot = importlib.util.module_from_spec(_PILOT_SPEC)
sys.modules[_PILOT_SPEC.name] = pilot
_PILOT_SPEC.loader.exec_module(pilot)


def dependency_record():
    result = {str(path.relative_to(REPO)): digest
              for path, digest in PINNED.items()}
    result.update({str(path.relative_to(REPO)): digest
                   for path, digest in pilot.V1.PINNED.items()})
    result.update(pilot.V1.A25.require_pins())
    result.update(pilot.V1.A25.shell.require_pins())
    return dict(sorted(result.items()))


def load_gate():
    raw = strict_json_bytes(_START[GATE_ARTIFACT], str(GATE_ARTIFACT))
    resource_gate = raw.get("resource_gate", {})
    reference = raw.get("degree_zero_reference", {})
    if (raw.get("format") != "active25-cap-slack-D16-one-face-gate-v3" or
            raw.get("status") != "PASS" or raw.get("common_r") != 10 or
            raw.get("selected_h") != 10 or raw.get("coordinates") != 38 or
            raw.get("complete_cross") is not False or
            raw.get("launch_authorized") is not False or
            raw.get("theorem_ready") is not False or raw.get("workers") != 1 or
            raw.get("source_sha256") != PINNED[GATE_SOURCE] or
            reference.get("exact_countwise_match") is not True or
            resource_gate.get("wall_limit_seconds") != 20 or
            resource_gate.get("rss_limit_kib") != MAX_CHILD_RSS_KIB or
            resource_gate.get("wall_pass") is not True or
            resource_gate.get("rss_pass") is not True or
            not 0 < resource_gate.get("process_wall_seconds", 0) <= 20 or
            not 0 < resource_gate.get("peak_rss_kib", 0) <= MAX_CHILD_RSS_KIB):
        raise ValueError("one-face gate identity or PASS evidence changed")
    return raw


def preflight():
    gate = load_gate()
    work = pilot.pilot_work_inventory()
    return {
        "status": "PRELAUNCH_CANDIDATE",
        "format": "active25-cap-slack-D16-staged-preflight-v3",
        "source_sha256": _SELF["sha256"],
        "dependency_sha256": dependency_record(),
        "gate_sha256": PINNED[GATE_ARTIFACT],
        "gate_process_wall_seconds":
            gate["resource_gate"]["process_wall_seconds"],
        "gate_peak_rss_kib": gate["resource_gate"]["peak_rss_kib"],
        "coordinates": 38,
        "common_r_shards": list(range(26)),
        "faces": work["faces"],
        "one_shot_no_resume": True,
        "workers": 1,
        "target_started": False,
        "launch_authorized": False,
        "contains_cross_values": False,
        "contains_quotient": False,
        "theorem_ready": False,
        "external_bindings_required": [
            "producer source SHA", "authorization file SHA and inode",
            "ledger SHA, device, and inode", "manifest SHA after completion",
        ],
        "independent_reconstruction_required": True,
        "independent_reconstruction_design_sha256":
            PINNED[INDEPENDENT_DESIGN],
    }


def _label_rows(values):
    return [[count, degree, str(values[(count, degree)])]
            for count, degree in pilot.pilot_labels()]


def exact_common_r_shard(common_r):
    if type(common_r) is not int or not 0 <= common_r <= 25:
        raise ValueError("common_r must be an integer in 0..25")
    start = snapshots()
    values, metadata = pilot.pilot_shard(common_r, progress=False)
    if snapshots() != start:
        raise RuntimeError("staged arithmetic closure changed during shard")
    shard = {
        "format": SHARD_FORMAT,
        "common_r": common_r,
        "basis": [list(label) for label in pilot.pilot_labels()],
        "raw_J_cross_by_label": _label_rows(values),
        "faces": metadata["faces"],
        "literal_weighted_terms": metadata["literal_weighted_terms"],
        "geometric_groups": metadata["geometric_groups"],
        "nonzero_groups": metadata["nonzero_groups"],
        "complete_common_r": metadata["complete_common_r"],
        "selected_h": metadata["selected_h"],
        "inner_I": str(metadata["inner_I"]),
        "inner_48J": str(metadata["inner_48J"]),
        "theorem_ready": False,
    }
    strict_shard(shard, common_r)
    return shard


def strict_shard(value, expected_r=None):
    keys = {
        "basis", "common_r", "complete_common_r", "faces", "format",
        "geometric_groups", "inner_48J", "inner_I",
        "literal_weighted_terms", "nonzero_groups", "raw_J_cross_by_label",
        "selected_h", "theorem_ready",
    }
    if type(value) is not dict or set(value) != keys:
        raise ValueError("common-r shard schema mismatch")
    r = value["common_r"]
    labels = pilot.pilot_labels()
    if (type(r) is not int or not 0 <= r <= 25 or
            (expected_r is not None and r != expected_r) or
            value["format"] != SHARD_FORMAT or
            value["basis"] != [list(label) for label in labels] or
            value["complete_common_r"] is not True or
            value["selected_h"] is not None or
            value["faces"] != 35 - r or
            value["theorem_ready"] is not False or
            any(type(value[key]) is not int or value[key] < 0
                for key in ("literal_weighted_terms", "geometric_groups",
                            "nonzero_groups"))):
        raise ValueError("common-r shard identity mismatch")
    rows = value["raw_J_cross_by_label"]
    if type(rows) is not list or len(rows) != len(labels):
        raise ValueError("common-r vector dimension mismatch")
    parsed = []
    for row, label in zip(rows, labels):
        if (type(row) is not list or len(row) != 3 or
                row[:2] != list(label)):
            raise ValueError("common-r label order mismatch")
        number = strict_q(row[2], "common-r cross value")
        if number and label[0] not in (r, r + 1):
            raise ValueError("common-r shard leaks outside adjacent counts")
        parsed.append(number)
    if strict_q(value["inner_I"], "inner I") <= 0:
        raise ArithmeticError("inner I is not positive")
    strict_q(value["inner_48J"], "inner 48J")
    return parsed


def merge_shards(shards):
    if type(shards) not in (list, tuple) or len(shards) != 26:
        raise ValueError("a complete merge requires exactly 26 shards")
    labels = pilot.pilot_labels()
    total = [Q(0) for _ in labels]
    identity = None
    faces = literal = geometric = nonzero = 0
    for r, shard in enumerate(shards):
        vector = strict_shard(shard, r)
        current_identity = (Q(shard["inner_I"]), Q(shard["inner_48J"]))
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise ArithmeticError("inner identity differs between shards")
        total = [left + right for left, right in zip(total, vector)]
        faces += shard["faces"]
        literal += shard["literal_weighted_terms"]
        geometric += shard["geometric_groups"]
        nonzero += shard["nonzero_groups"]
    if faces != 585:
        raise ArithmeticError("merged face count is not 585")
    rows = [[label[0], label[1], str(value)]
            for label, value in zip(labels, total)]
    return {
        "basis": [list(label) for label in labels],
        "raw_J_cross_by_label": rows,
        "raw_J_cross_sha256": sha256_bytes(canonical_json(rows)),
        "inner_I": str(identity[0]),
        "inner_48J": str(identity[1]),
        "faces": faces,
        "literal_weighted_terms": literal,
        "geometric_groups": geometric,
        "nonzero_groups": nonzero,
    }


def _safe_leaf(value):
    if (type(value) is not str or not value or value in (".", "..") or
            "/" in value or "\x00" in value):
        raise ValueError("unsafe record leaf")
    return value


def open_record_dir(path):
    target = Path(path).resolve()
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags)
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        os.close(descriptor)
        raise ValueError("record path is not a directory")
    return {"descriptor": descriptor, "path": str(target),
            "device": int(observed.st_dev), "inode": int(observed.st_ino)}


def close_record_dir(handle):
    os.close(handle["descriptor"])


def validate_record_dir(handle):
    held = os.fstat(handle["descriptor"])
    current = open_record_dir(handle["path"])
    try:
        if ((int(held.st_dev), int(held.st_ino)) !=
                (handle["device"], handle["inode"]) or
                (current["device"], current["inode"]) !=
                (handle["device"], handle["inode"])):
            raise RuntimeError("record directory identity changed")
    finally:
        close_record_dir(current)


def leaf_set(handle):
    validate_record_dir(handle)
    return set(os.listdir(handle["descriptor"]))


def require_leaf_set(handle, expected):
    observed = leaf_set(handle)
    if observed != set(expected):
        raise ValueError(f"record leaf set mismatch: {sorted(observed)}")


def read_leaf(handle, leaf, maximum_bytes=4_000_000):
    leaf = _safe_leaf(leaf)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(leaf, flags, dir_fd=handle["descriptor"])
    try:
        before = os.fstat(descriptor)
        data = _read_descriptor(descriptor, maximum_bytes)
        after = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns, before.st_nlink) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns, after.st_nlink) or
                len(data) != after.st_size):
            raise RuntimeError(f"unstable stage leaf: {leaf}")
        return {"leaf": leaf, "data": data,
                "sha256": sha256_bytes(data), "device": int(after.st_dev),
                "inode": int(after.st_ino)}
    finally:
        os.close(descriptor)


def publish_leaf(handle, leaf, payload):
    leaf = _safe_leaf(leaf)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(leaf, flags, 0o600, dir_fd=handle["descriptor"])
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short stage write")
            offset += written
        os.fsync(descriptor)
        os.fsync(handle["descriptor"])
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            raise RuntimeError("published leaf is not singly linked regular data")
    finally:
        os.close(descriptor)
    snapshot = read_leaf(handle, leaf, len(payload))
    if snapshot["data"] != payload:
        raise RuntimeError("published leaf bytes changed")
    return snapshot


def binding(snapshot):
    return {key: snapshot[key] for key in
            ("leaf", "sha256", "device", "inode")}


def expected_binding(leaf, digest, device, inode):
    strict_sha(digest, f"expected {leaf} SHA")
    if (type(device) is not int or device < 0 or
            type(inode) is not int or inode < 0):
        raise ValueError(f"expected {leaf} inode binding is malformed")
    return {"leaf": leaf, "sha256": digest,
            "device": device, "inode": inode}


def _open_authorization(path, expected_sha256, record_dir,
                        expected_self_sha256):
    strict_sha(expected_sha256, "expected authorization SHA")
    handle = _open_stable_regular(path, 100_000)
    try:
        if handle["sha256"] != expected_sha256:
            raise RuntimeError("authorization bytes do not match external SHA")
        value = strict_json_bytes(handle["data"], "root authorization")
        if canonical_json(value) != handle["data"]:
            raise ValueError("root authorization is not canonical JSON")
        expected_keys = {
            "driver_sha256", "format", "gate_sha256",
            "independent_prelaunch_report_sha256", "max_total_wall_seconds",
            "one_shot_attempt_authorized", "record_directory", "status",
            "theorem_ready", "workers",
        }
        strict_sha(value.get("independent_prelaunch_report_sha256"),
                   "independent prelaunch report SHA")
        if (set(value) != expected_keys or
                value["format"] != AUTHORIZATION_FORMAT or
                value["driver_sha256"] != expected_self_sha256 or
                value["gate_sha256"] != PINNED[GATE_ARTIFACT] or
                value["record_directory"] != str(Path(record_dir).resolve()) or
                value["max_total_wall_seconds"] != MAX_TOTAL_WALL_SECONDS or
                value["one_shot_attempt_authorized"] is not True or
                value["status"] !=
                "ROOT_AUTHORIZED_AFTER_INDEPENDENT_PRELAUNCH_PASS" or
                value["theorem_ready"] is not False or value["workers"] != 1):
            raise ValueError("root authorization contract mismatch")
        handle["value"] = value
        return handle
    except Exception:
        os.close(handle["descriptor"])
        raise


def authorization_binding(handle):
    return {"sha256": handle["sha256"], "device": handle["device"],
            "inode": handle["inode"], "path": handle["path"]}


def _validate_authorization(handle, record_dir, expected_self_sha256):
    data = _rebind_stable_regular(handle, 100_000)
    value = strict_json_bytes(data, "root authorization")
    if (value != handle["value"] or
            value["record_directory"] != str(Path(record_dir).resolve()) or
            value["driver_sha256"] != expected_self_sha256):
        raise RuntimeError("root authorization changed")
    return authorization_binding(handle)


def _close_authorization(handle):
    os.close(handle["descriptor"])


def boot_id():
    value = BOOT_ID_PATH.read_text().strip()
    if BOOT_PATTERN.fullmatch(value) is None:
        raise RuntimeError("Linux boot ID is unavailable or malformed")
    return value


def make_ledger(record, authorization, expected_self_sha256, started_ns):
    return {
        "format": LEDGER_FORMAT,
        "status": "initialized-for-one-shot-only",
        "driver_sha256": expected_self_sha256,
        "dependency_sha256": dependency_record(),
        "gate_sha256": PINNED[GATE_ARTIFACT],
        "package_gate_launch_authorized": False,
        "root_authorization_binding": authorization,
        "record_directory": {"path": record["path"],
                             "device": record["device"],
                             "inode": record["inode"]},
        "boot_id": boot_id(),
        "start_monotonic_ns": started_ns,
        "deadline_monotonic_ns":
            started_ns + MAX_TOTAL_WALL_SECONDS * 1_000_000_000,
        "common_r_order": list(range(26)),
        "workers": 1,
        "one_shot_no_resume": True,
        "theorem_ready": False,
    }


def strict_ledger(value, record, authorization, expected_self_sha256,
                  observed_now_ns=None):
    keys = {
        "boot_id", "common_r_order", "deadline_monotonic_ns",
        "dependency_sha256", "driver_sha256", "format", "gate_sha256",
        "one_shot_no_resume", "package_gate_launch_authorized",
        "record_directory", "root_authorization_binding",
        "start_monotonic_ns", "status", "theorem_ready", "workers",
    }
    now = time.monotonic_ns() if observed_now_ns is None else observed_now_ns
    if (type(value) is not dict or set(value) != keys or
            value["format"] != LEDGER_FORMAT or
            value["status"] != "initialized-for-one-shot-only" or
            value["driver_sha256"] != expected_self_sha256 or
            value["dependency_sha256"] != dependency_record() or
            value["gate_sha256"] != PINNED[GATE_ARTIFACT] or
            value["package_gate_launch_authorized"] is not False or
            value["root_authorization_binding"] != authorization or
            value["record_directory"] != {
                "path": record["path"], "device": record["device"],
                "inode": record["inode"]} or
            value["boot_id"] != boot_id() or
            type(value["start_monotonic_ns"]) is not int or
            type(value["deadline_monotonic_ns"]) is not int or
            value["deadline_monotonic_ns"] - value["start_monotonic_ns"] !=
            MAX_TOTAL_WALL_SECONDS * 1_000_000_000 or
            not value["start_monotonic_ns"] <= now <=
            value["deadline_monotonic_ns"] or
            value["common_r_order"] != list(range(26)) or
            value["workers"] != 1 or value["one_shot_no_resume"] is not True or
            value["theorem_ready"] is not False):
        raise ValueError("one-shot ledger identity mismatch")
    return value


def initialize_ledger(record_dir, authorization_file,
                      expected_authorization_sha256, expected_self_sha256):
    bind_startup_self(expected_self_sha256)
    load_gate()
    record = open_record_dir(record_dir)
    authorization = _open_authorization(
        authorization_file, expected_authorization_sha256, record_dir,
        expected_self_sha256)
    try:
        require_leaf_set(record, set())
        auth_binding = _validate_authorization(
            authorization, record_dir, expected_self_sha256)
        ledger = make_ledger(record, auth_binding, expected_self_sha256,
                             time.monotonic_ns())
        strict_ledger(ledger, record, auth_binding, expected_self_sha256,
                      ledger["start_monotonic_ns"])
        snapshot = publish_leaf(record, LEDGER_LEAF, canonical_json(ledger))
        require_leaf_set(record, {LEDGER_LEAF})
        _validate_authorization(authorization, record_dir, expected_self_sha256)
        bind_startup_self(expected_self_sha256)
        return snapshot
    finally:
        _close_authorization(authorization)
        close_record_dir(record)


def _parse_bound_ledger(record, expected_ledger, authorization,
                        expected_self_sha256):
    snapshot = read_leaf(record, LEDGER_LEAF)
    if binding(snapshot) != expected_ledger:
        raise RuntimeError("ledger differs from externally recorded binding")
    value = strict_json_bytes(snapshot["data"], "one-shot ledger")
    if canonical_json(value) != snapshot["data"]:
        raise ValueError("one-shot ledger is not canonical JSON")
    strict_ledger(value, record, authorization, expected_self_sha256)
    return value, snapshot


def child_payload(common_r, ledger_binding_value, authorization_value,
                  expected_self_sha256):
    started = time.monotonic_ns()
    shard = exact_common_r_shard(common_r)
    finished = time.monotonic_ns()
    payload = {
        "format": CHILD_FORMAT,
        "status": "complete",
        "driver_sha256": expected_self_sha256,
        "dependency_sha256": dependency_record(),
        "gate_sha256": PINNED[GATE_ARTIFACT],
        "ledger_binding": ledger_binding_value,
        "root_authorization_binding": authorization_value,
        "shard": shard,
        "wall_seconds": (finished - started) / 1_000_000_000,
        "peak_rss_kib":
            int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "workers": 1,
        "theorem_ready": False,
    }
    strict_child(payload, common_r, ledger_binding_value, authorization_value,
                 expected_self_sha256)
    return payload


def strict_child(value, expected_r, expected_ledger, expected_authorization,
                 expected_self_sha256):
    keys = {
        "dependency_sha256", "driver_sha256", "format", "gate_sha256",
        "ledger_binding", "peak_rss_kib", "root_authorization_binding",
        "shard", "status", "theorem_ready", "wall_seconds", "workers",
    }
    if (type(value) is not dict or set(value) != keys or
            value["format"] != CHILD_FORMAT or value["status"] != "complete" or
            value["driver_sha256"] != expected_self_sha256 or
            value["dependency_sha256"] != dependency_record() or
            value["gate_sha256"] != PINNED[GATE_ARTIFACT] or
            value["ledger_binding"] != expected_ledger or
            value["root_authorization_binding"] != expected_authorization or
            type(value["wall_seconds"]) not in (int, float) or
            isinstance(value["wall_seconds"], bool) or
            not math.isfinite(value["wall_seconds"]) or
            not 0 <= value["wall_seconds"] <= MAX_CHILD_WALL_SECONDS or
            type(value["peak_rss_kib"]) is not int or
            not 0 < value["peak_rss_kib"] <= MAX_CHILD_RSS_KIB or
            value["workers"] != 1 or value["theorem_ready"] is not False):
        raise ValueError("common-r child identity/resource mismatch")
    strict_shard(value["shard"], expected_r)
    return True


def _child_limit_handler(_signum, _frame):
    raise StageTimeout("common-r child exceeded its hard deadline")


def _enforce_child_limits(timeout_seconds):
    requested = MAX_CHILD_RSS_KIB * 1024
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY and hard < requested:
        raise RuntimeError("address-space hard limit is below stage limit")
    resource.setrlimit(resource.RLIMIT_AS, (requested, hard))
    signal.signal(signal.SIGALRM, _child_limit_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)


def _default_child_runner(common_r, ledger_row, authorization_row,
                          expected_self_sha256, record_dir,
                          authorization_file, expected_authorization_sha256,
                          deadline_ns):
    remaining = (deadline_ns - time.monotonic_ns()) / 1_000_000_000
    timeout_seconds = min(MAX_CHILD_WALL_SECONDS, remaining)
    if timeout_seconds <= 0:
        raise StageTimeout("global one-shot deadline expired")
    command = [
        sys.executable, "-I", str(FILE), "--child-r", str(common_r),
        "--record-dir", str(record_dir),
        "--authorization-file", str(authorization_file),
        "--expected-authorization-sha256", expected_authorization_sha256,
        "--expected-self-sha256", expected_self_sha256,
        "--expected-ledger-sha256", ledger_row["sha256"],
        "--expected-ledger-device", str(ledger_row["device"]),
        "--expected-ledger-inode", str(ledger_row["inode"]),
    ]
    try:
        completed = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired as error:
        raise StageTimeout(f"common-r {common_r} child timed out") from error
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError(
            f"common-r {common_r} child failed: {completed.stderr!r}")
    value = strict_json_bytes(completed.stdout, f"common-r {common_r} child")
    if canonical_json(value) != completed.stdout:
        raise ValueError("child output is not canonical JSON")
    strict_child(value, common_r, ledger_row, authorization_row,
                 expected_self_sha256)
    return value


def _manifest(stages, children, merged, ledger_row, authorization_row,
              expected_self_sha256, started_ns, finished_ns):
    return {
        "format": MANIFEST_FORMAT,
        "status": "complete-conditional-serialization",
        "driver_sha256": expected_self_sha256,
        "dependency_sha256": dependency_record(),
        "gate_sha256": PINNED[GATE_ARTIFACT],
        "ledger_binding": ledger_row,
        "root_authorization_binding": authorization_row,
        "stages": [binding(snapshot) for snapshot in stages],
        "merged_cross": merged,
        "child_wall_seconds": [child["wall_seconds"] for child in children],
        "child_peak_rss_kib": [child["peak_rss_kib"] for child in children],
        "start_monotonic_ns": started_ns,
        "finish_monotonic_ns": finished_ns,
        "workers": 1,
        "one_shot_complete": True,
        "resume_supported": False,
        "independent_arithmetic_reconstruction": False,
        "contains_quotient": False,
        "theorem_ready": False,
    }


def strict_manifest(value, ledger, expected_ledger, expected_authorization,
                    expected_self_sha256, children=None):
    keys = {
        "child_peak_rss_kib", "child_wall_seconds", "contains_quotient",
        "dependency_sha256", "driver_sha256", "finish_monotonic_ns", "format",
        "gate_sha256", "independent_arithmetic_reconstruction",
        "ledger_binding", "merged_cross", "one_shot_complete",
        "resume_supported", "root_authorization_binding", "stages",
        "start_monotonic_ns", "status", "theorem_ready", "workers",
    }
    if (type(value) is not dict or set(value) != keys or
            value["format"] != MANIFEST_FORMAT or
            value["status"] != "complete-conditional-serialization" or
            value["driver_sha256"] != expected_self_sha256 or
            value["dependency_sha256"] != dependency_record() or
            value["gate_sha256"] != PINNED[GATE_ARTIFACT] or
            value["ledger_binding"] != expected_ledger or
            value["root_authorization_binding"] != expected_authorization or
            type(value["stages"]) is not list or len(value["stages"]) != 26 or
            value["workers"] != 1 or value["one_shot_complete"] is not True or
            value["resume_supported"] is not False or
            value["independent_arithmetic_reconstruction"] is not False or
            value["contains_quotient"] is not False or
            value["theorem_ready"] is not False or
            type(value["start_monotonic_ns"]) is not int or
            type(value["finish_monotonic_ns"]) is not int or
            not ledger["start_monotonic_ns"] <= value["start_monotonic_ns"] <=
            value["finish_monotonic_ns"] <= ledger["deadline_monotonic_ns"]):
        raise ValueError("one-shot manifest identity mismatch")
    seen = {(expected_ledger["device"], expected_ledger["inode"])}
    for r, row in enumerate(value["stages"]):
        if (type(row) is not dict or set(row) != {
                "leaf", "sha256", "device", "inode"} or
                row["leaf"] != STAGE_LEAVES[r] or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError("manifest stage binding is malformed")
        strict_sha(row["sha256"], "manifest stage SHA")
        inode = (row["device"], row["inode"])
        if inode in seen:
            raise ValueError("manifest dynamic leaves alias an inode")
        seen.add(inode)
    if (type(value["child_wall_seconds"]) is not list or
            len(value["child_wall_seconds"]) != 26 or
            any(type(item) not in (int, float) or isinstance(item, bool) or
                not math.isfinite(item) or not 0 <= item <= MAX_CHILD_WALL_SECONDS
                for item in value["child_wall_seconds"]) or
            type(value["child_peak_rss_kib"]) is not list or
            len(value["child_peak_rss_kib"]) != 26 or
            any(type(item) is not int or not 0 < item <= MAX_CHILD_RSS_KIB
                for item in value["child_peak_rss_kib"])):
        raise ValueError("manifest resource inventory is malformed")
    merged = value["merged_cross"]
    if (type(merged) is not dict or set(merged) != {
            "basis", "faces", "geometric_groups", "inner_48J", "inner_I",
            "literal_weighted_terms", "nonzero_groups",
            "raw_J_cross_by_label", "raw_J_cross_sha256"} or
            merged["basis"] != [list(label) for label in pilot.pilot_labels()] or
            merged["faces"] != 585 or
            sha256_bytes(canonical_json(merged["raw_J_cross_by_label"])) !=
            merged["raw_J_cross_sha256"]):
        raise ValueError("manifest merged cross is malformed")
    strict_q(merged["inner_I"], "manifest inner I")
    strict_q(merged["inner_48J"], "manifest inner 48J")
    if children is not None:
        rebuilt = merge_shards([child["shard"] for child in children])
        if rebuilt != merged:
            raise ArithmeticError("manifest merged cross differs from stages")
    return True


def run_one_shot(record_dir, authorization_file,
                 expected_authorization_sha256, expected_self_sha256,
                 expected_ledger, runner=None):
    bind_startup_self(expected_self_sha256)
    static_start = snapshots()
    record = open_record_dir(record_dir)
    authorization = _open_authorization(
        authorization_file, expected_authorization_sha256, record_dir,
        expected_self_sha256)
    try:
        # The exact startup leaf set is the no-resume boundary. Any prior
        # prefix or manifest permanently invalidates this attempt.
        require_leaf_set(record, {LEDGER_LEAF})
        auth_row = _validate_authorization(
            authorization, record_dir, expected_self_sha256)
        ledger, ledger_snapshot = _parse_bound_ledger(
            record, expected_ledger, auth_row, expected_self_sha256)
        ledger_row = binding(ledger_snapshot)
        started = time.monotonic_ns()
        stages, children = [], []
        for common_r in range(26):
            require_leaf_set(record,
                             {LEDGER_LEAF, *STAGE_LEAVES[:common_r]})
            if time.monotonic_ns() > ledger["deadline_monotonic_ns"]:
                raise StageTimeout("global one-shot deadline expired")
            if runner is None:
                child = _default_child_runner(
                    common_r, ledger_row, auth_row, expected_self_sha256,
                    record_dir, authorization_file,
                    expected_authorization_sha256,
                    ledger["deadline_monotonic_ns"])
            else:
                child = runner(common_r, ledger_row, auth_row,
                               expected_self_sha256)
            strict_child(child, common_r, ledger_row, auth_row,
                         expected_self_sha256)
            _validate_authorization(
                authorization, record_dir, expected_self_sha256)
            if binding(read_leaf(record, LEDGER_LEAF)) != ledger_row:
                raise RuntimeError("ledger changed during one-shot run")
            snapshot = publish_leaf(
                record, STAGE_LEAVES[common_r], canonical_json(child))
            stages.append(snapshot)
            children.append(child)
        merged = merge_shards([child["shard"] for child in children])
        finished = time.monotonic_ns()
        manifest = _manifest(
            stages, children, merged, ledger_row, auth_row,
            expected_self_sha256, started, finished)
        strict_manifest(manifest, ledger, ledger_row, auth_row,
                        expected_self_sha256, children)
        manifest_snapshot = publish_leaf(
            record, MANIFEST_LEAF, canonical_json(manifest))
        require_leaf_set(record, set(ALLOWED_LEAVES))
        _validate_authorization(authorization, record_dir,
                                expected_self_sha256)
        if binding(read_leaf(record, LEDGER_LEAF)) != ledger_row:
            raise RuntimeError("ledger changed before completion")
        if snapshots() != static_start:
            raise RuntimeError("staged closure changed during one-shot run")
        bind_startup_self(expected_self_sha256)
        return manifest_snapshot
    finally:
        _close_authorization(authorization)
        close_record_dir(record)


def open_completed(record_dir, authorization_file,
                   expected_authorization_sha256, expected_self_sha256,
                   expected_ledger, expected_manifest_sha256):
    strict_sha(expected_manifest_sha256, "expected manifest SHA")
    record = open_record_dir(record_dir)
    authorization = _open_authorization(
        authorization_file, expected_authorization_sha256, record_dir,
        expected_self_sha256)
    try:
        require_leaf_set(record, set(ALLOWED_LEAVES))
        auth_row = _validate_authorization(
            authorization, record_dir, expected_self_sha256)
        ledger, ledger_snapshot = _parse_bound_ledger(
            record, expected_ledger, auth_row, expected_self_sha256)
        ledger_row = binding(ledger_snapshot)
        manifest_snapshot = read_leaf(record, MANIFEST_LEAF)
        if manifest_snapshot["sha256"] != expected_manifest_sha256:
            raise RuntimeError("manifest differs from external SHA")
        manifest = strict_json_bytes(
            manifest_snapshot["data"], "one-shot manifest")
        if canonical_json(manifest) != manifest_snapshot["data"]:
            raise ValueError("one-shot manifest is not canonical JSON")
        children, stage_snapshots = [], []
        for r, row in enumerate(manifest["stages"]):
            snapshot = read_leaf(record, STAGE_LEAVES[r])
            if binding(snapshot) != row:
                raise RuntimeError("stage differs from manifest binding")
            child = strict_json_bytes(snapshot["data"], f"stage {r}")
            if canonical_json(child) != snapshot["data"]:
                raise ValueError("stage is not canonical JSON")
            strict_child(child, r, ledger_row, auth_row,
                         expected_self_sha256)
            children.append(child)
            stage_snapshots.append(snapshot)
        strict_manifest(manifest, ledger, ledger_row, auth_row,
                        expected_self_sha256, children)
        return {"record": record, "authorization": authorization,
                "authorization_binding": auth_row, "ledger": ledger,
                "ledger_snapshot": ledger_snapshot,
                "manifest": manifest,
                "manifest_snapshot": manifest_snapshot,
                "children": children, "stage_snapshots": stage_snapshots}
    except Exception:
        _close_authorization(authorization)
        close_record_dir(record)
        raise


def close_completed(context):
    _close_authorization(context["authorization"])
    close_record_dir(context["record"])


def _child_cli(args):
    expected = expected_binding(
        LEDGER_LEAF, args.expected_ledger_sha256,
        args.expected_ledger_device, args.expected_ledger_inode)
    bind_startup_self(args.expected_self_sha256)
    record = open_record_dir(args.record_dir)
    authorization = _open_authorization(
        args.authorization_file, args.expected_authorization_sha256,
        args.record_dir, args.expected_self_sha256)
    try:
        auth_row = _validate_authorization(
            authorization, args.record_dir, args.expected_self_sha256)
        _, ledger_snapshot = _parse_bound_ledger(
            record, expected, auth_row, args.expected_self_sha256)
        timeout = min(MAX_CHILD_WALL_SECONDS,
                      max(1, args.child_timeout_seconds))
        _enforce_child_limits(timeout)
        payload = child_payload(args.child_r, binding(ledger_snapshot), auth_row,
                                args.expected_self_sha256)
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout.buffer.write(canonical_json(payload))
    finally:
        _close_authorization(authorization)
        close_record_dir(record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--initialize-ledger-only", action="store_true")
    parser.add_argument("--run-one-shot", action="store_true")
    parser.add_argument("--child-r", type=int)
    parser.add_argument("--child-timeout-seconds", type=int,
                        default=MAX_CHILD_WALL_SECONDS)
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--expected-authorization-sha256")
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--expected-ledger-sha256")
    parser.add_argument("--expected-ledger-device", type=int)
    parser.add_argument("--expected-ledger-inode", type=int)
    args = parser.parse_args()
    modes = sum((args.preflight_only, args.initialize_ledger_only,
                 args.run_one_shot, args.child_r is not None))
    if modes != 1:
        parser.error("choose exactly one execution mode")
    if args.preflight_only:
        forbidden = (args.record_dir, args.authorization_file,
                     args.expected_authorization_sha256,
                     args.expected_self_sha256, args.expected_ledger_sha256,
                     args.expected_ledger_device, args.expected_ledger_inode)
        if any(value is not None for value in forbidden):
            parser.error("preflight accepts no production binding")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    required = (args.record_dir, args.authorization_file,
                args.expected_authorization_sha256, args.expected_self_sha256)
    if any(value is None for value in required):
        parser.error("production mode requires all source/authorization bindings")
    if args.initialize_ledger_only:
        if any(value is not None for value in
               (args.expected_ledger_sha256, args.expected_ledger_device,
                args.expected_ledger_inode)):
            parser.error("ledger initialization accepts no prior ledger")
        snapshot = initialize_ledger(
            args.record_dir, args.authorization_file,
            args.expected_authorization_sha256, args.expected_self_sha256)
        print(json.dumps(binding(snapshot), sort_keys=True))
        return
    ledger_values = (args.expected_ledger_sha256,
                     args.expected_ledger_device, args.expected_ledger_inode)
    if any(value is None for value in ledger_values):
        parser.error("one-shot/child mode requires the external ledger binding")
    if args.child_r is not None:
        _child_cli(args)
        return
    expected = expected_binding(
        LEDGER_LEAF, args.expected_ledger_sha256,
        args.expected_ledger_device, args.expected_ledger_inode)
    snapshot = run_one_shot(
        args.record_dir, args.authorization_file,
        args.expected_authorization_sha256, args.expected_self_sha256,
        expected)
    print(json.dumps(binding(snapshot), sort_keys=True))


if __name__ == "__main__":
    main()
