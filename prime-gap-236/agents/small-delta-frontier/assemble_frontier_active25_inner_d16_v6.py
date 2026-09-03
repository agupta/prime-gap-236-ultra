#!/usr/bin/env python3
"""Conditional assembler for the one-shot active25 D16 v6 stages.

This consumer rebinds the externally anchored ledger, launch authorization,
manifest, and all 26 stage leaves.  It reconstructs and contracts the exact
serialized pencil, but it does not independently repeat the long grouped
integrations.  Consequently every result is discovery-only and never
theorem-ready.  A separate independent arithmetic checker is required.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
STAGED = HERE / "frontier_active25_inner_d16_staged_v6.py"
STAGED_TEST = HERE / "test_frontier_active25_inner_d16_staged_v6.py"
GATE = HERE / (
    "results/frontier_active25_innerD16_tagged_shell_authorized_gate_v6.json")
V5_ASSEMBLER = HERE / "assemble_frontier_active25_inner_d16_v5.py"

PINNED = {
    STAGED: "cfc4c3803312d5e41d87c27a753cd843da9534e85ea5e73d77079bf9ce8e284e",
    STAGED_TEST: "c5e45fe4a929fba55f29ae96f6e127bd8a680d8fa0ca01ca17dfa70f2b56d6ff",
    GATE: "7b37c89dd84b03301e3937c981b7c67ea6ce17e21bfd07a76199430bcfb16b80",
    V5_ASSEMBLER:
        "6163402f5333c73ae011acbe64191ebff7dfac043f43d8e11c2ce635019807e9",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_sha(value, name):
    if (type(value) is not str or len(value) != 64 or
            any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def _read_descriptor(descriptor, maximum=16_000_000):
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
        raise ValueError("bounded file is too large")
    return data


def _open_startup_self():
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(FILE, flags)
    before = os.fstat(descriptor)
    data = _read_descriptor(descriptor, 4_000_000)
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
        raise RuntimeError("assembler source was not stable at startup")
    return {"bytes": data, "descriptor": descriptor,
            "device": identity[0], "inode": identity[1],
            "size": identity[2], "mtime_ns": identity[3],
            "ctime_ns": identity[4], "nlink": identity[5],
            "sha256": sha256_bytes(data)}


_SELF = _open_startup_self()


def bind_startup_self(expected_sha256):
    strict_sha(expected_sha256, "expected assembler self SHA")
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
    descriptor = os.open(FILE, flags)
    try:
        current = os.fstat(descriptor)
        data = _read_descriptor(descriptor, 4_000_000)
        current_identity = (
            int(current.st_dev), int(current.st_ino), int(current.st_size),
            int(current.st_mtime_ns), int(current.st_ctime_ns),
            int(current.st_nlink))
    finally:
        os.close(descriptor)
    if (expected_sha256 != _SELF["sha256"] or
            held_identity != expected_identity or
            current_identity != expected_identity or data != _SELF["bytes"] or
            sha256_bytes(_SELF["bytes"]) != expected_sha256):
        raise RuntimeError("startup-bound assembler source changed")
    return _SELF["bytes"]


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"assembler dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()


def _load_module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    if Path(module.__file__).resolve(strict=True) != path:
        raise RuntimeError("loaded local module path mismatch")
    return module


staged = _load_module("frontier_active25_staged_v6_for_assembler", STAGED)
v5_assembler = _load_module("frontier_active25_v5_math_for_v6", V5_ASSEMBLER)
staged.bind_startup_self(PINNED[STAGED])


def dependency_record():
    result = {str(path.relative_to(REPO)): expected
              for path, expected in PINNED.items()}
    result.update(staged.dependency_record())
    return dict(sorted(result.items()))


def closure_snapshot(expected_self_sha256):
    return {
        "assembler_self": bind_startup_self(expected_self_sha256),
        "assembler_dependencies": snapshots(),
        "producer_self": staged.bind_startup_self(PINNED[STAGED]),
        "producer_dependencies": staged.snapshots(),
        "transitive_dependencies": staged.transitive_snapshots(),
    }


def _direct_cli_identity(expected_self_sha256):
    bind_startup_self(expected_self_sha256)
    if (not sys.flags.isolated or __name__ != "__main__" or
            __spec__ is not None or
            Path(sys.argv[0]).resolve(strict=True) != FILE):
        raise RuntimeError(
            "assembly requires fresh `python3 -I` on the pinned v6 consumer")
    return True


def expected_ledger_binding(sha256_value, device, inode):
    return staged.expected_ledger_binding(sha256_value, device, inode)


def _fresh_live_observation(ledger):
    boot = staged.BOOT_ID_PATH.read_text().strip()
    if staged._boot_id(boot) != ledger["boot_id"]:
        raise RuntimeError("stage boot differs from assembler boot")
    now = staged._clock(time.monotonic_ns(), "assembler live observation")
    if now < ledger["start_monotonic_ns"]:
        raise RuntimeError("assembler clock precedes immutable ledger")
    return now


def open_completed(record_dir, expected_manifest_sha256, expected_ledger,
                   authorization_path, expected_authorization_sha256,
                   expected_producer_sha256, expected_self_sha256):
    strict_sha(expected_manifest_sha256, "expected manifest SHA")
    if expected_producer_sha256 != PINNED[STAGED]:
        raise ValueError("expected producer SHA is not the frozen v6 producer")
    closure_start = closure_snapshot(expected_self_sha256)
    authorization = staged._open_authorization(
        authorization_path, expected_authorization_sha256, record_dir,
        expected_producer_sha256)
    handle = None
    try:
        authorization_row = staged._validate_authorization(
            authorization, record_dir, expected_producer_sha256)
        handle = staged.v5.open_record_dir(record_dir)
        staged.v5.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
        ledger_snap = staged.v5.read_leaf(handle, staged.LEDGER_LEAF)
        if staged.ledger_binding(ledger_snap) != expected_ledger:
            raise RuntimeError("external ledger SHA/inode anchor mismatch")
        ledger = staged._parse_ledger(
            handle, ledger_snap, "production", expected_producer_sha256,
            authorization_row)
        now = _fresh_live_observation(ledger)
        manifest_snap = staged.v5.read_leaf(handle, staged.MANIFEST_LEAF)
        if manifest_snap["sha256"] != expected_manifest_sha256:
            raise RuntimeError("external manifest SHA anchor mismatch")
        try:
            manifest = json.loads(manifest_snap["data"])
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("manifest is not JSON") from error
        if staged.canonical_json(manifest) != manifest_snap["data"]:
            raise ValueError("manifest is not canonical JSON")
        staged.strict_manifest(
            manifest, handle, ledger, ledger_snap, "production",
            expected_producer_sha256, authorization_row, now)
        stages = []
        stage_snaps = []
        for r, row in enumerate(manifest["stages"]):
            snap = staged.v5.read_leaf(handle, row["leaf"])
            binding = {key: snap[key]
                       for key in ("leaf", "sha256", "device", "inode")}
            if binding != {key: row[key] for key in binding}:
                raise RuntimeError("manifest stage binding changed")
            stage = staged.parse_stage_bytes(
                snap["data"], r, ledger, staged.ledger_binding(ledger_snap),
                "production", expected_producer_sha256, authorization_row,
                now)
            stages.append(stage)
            stage_snaps.append(snap)
        staged.merge_v6_shards([stage["shard"] for stage in stages])
        staged.v5.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
        return {
            "authorization": authorization,
            "authorization_binding": authorization_row,
            "closure_start": closure_start,
            "handle": handle,
            "ledger": ledger,
            "ledger_snap": ledger_snap,
            "manifest": manifest,
            "manifest_snap": manifest_snap,
            "now": now,
            "stage_snaps": stage_snaps,
            "stages": stages,
        }
    except Exception:
        if handle is not None:
            staged.v5.close_record_dir(handle)
        staged._close_authorization(authorization)
        raise


def close_completed(context):
    if type(context) is dict:
        handle = context.get("handle")
        authorization = context.get("authorization")
        if type(handle) is dict:
            staged.v5.close_record_dir(handle)
        if type(authorization) is dict:
            staged._close_authorization(authorization)


def rebind_completed(context, expected_manifest_sha256,
                     expected_producer_sha256, expected_self_sha256):
    authorization_row = staged._validate_authorization(
        context["authorization"], context["handle"]["path"],
        expected_producer_sha256)
    if authorization_row != context["authorization_binding"]:
        raise RuntimeError("launch authorization binding changed")
    handle = context["handle"]
    staged.v5.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
    ledger_snap = staged.v5.read_leaf(handle, staged.LEDGER_LEAF)
    if staged.ledger_binding(ledger_snap) != staged.ledger_binding(
            context["ledger_snap"]):
        raise RuntimeError("ledger changed during conditional assembly")
    ledger = staged._parse_ledger(
        handle, ledger_snap, "production", expected_producer_sha256,
        authorization_row)
    now = _fresh_live_observation(ledger)
    manifest_snap = staged.v5.read_leaf(handle, staged.MANIFEST_LEAF)
    if (manifest_snap["sha256"] != expected_manifest_sha256 or
            staged.ledger_binding(manifest_snap) != staged.ledger_binding(
                context["manifest_snap"])):
        raise RuntimeError("manifest changed during conditional assembly")
    manifest = json.loads(manifest_snap["data"])
    if staged.canonical_json(manifest) != manifest_snap["data"]:
        raise ValueError("manifest ceased to be canonical")
    staged.strict_manifest(
        manifest, handle, ledger, ledger_snap, "production",
        expected_producer_sha256, authorization_row, now)
    for old, row in zip(context["stage_snaps"], manifest["stages"]):
        new = staged.v5.read_leaf(handle, row["leaf"])
        if staged.ledger_binding(new) != staged.ledger_binding(old):
            raise RuntimeError("stage changed during conditional assembly")
    staged.v5.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
    if closure_snapshot(expected_self_sha256) != context["closure_start"]:
        raise RuntimeError("conditional assembler source closure changed")
    return now


def _exact_quadratic(matrix, vector):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))), Q(0))


def build_result(context):
    shards = [stage["shard"] for stage in context["stages"]]
    raw_cross, identity = staged.merge_v6_shards(shards)
    if identity is None:
        raise ArithmeticError("missing D16 inner identity")
    inner_i, inner_b, dimension = identity
    if dimension != 307 or inner_i <= 0:
        raise ArithmeticError("invalid D16 inner identity")
    active, masses, shell_b, shell_counts = staged.v5.v2.core.shell_i_and_j()
    if active != list(range(26)):
        raise ArithmeticError("active shell schedule changed")
    a_diag, b_matrix = v5_assembler.assemble_exact_matrices(
        inner_i, inner_b, raw_cross, active, masses, shell_b, k=48)
    solves, vector, denominator, numerator = \
        v5_assembler.discovery_and_rationalize(a_diag, b_matrix)
    return {
        "48J_matrix": [[str(value) for value in row] for row in b_matrix],
        "I_diagonal": [str(value) for value in a_diag],
        "assembler_sha256": _SELF["sha256"],
        "authorization_binding": {
            **context["authorization_binding"],
            "path": context["authorization"]["path"],
        },
        "complete_manifest_binding": {
            "device": context["manifest_snap"]["device"],
            "inode": context["manifest_snap"]["inode"],
            "path": str(Path(context["handle"]["path"]) /
                        staged.MANIFEST_LEAF),
            "sha256": context["manifest_snap"]["sha256"],
        },
        "dependency_sha256": dependency_record(),
        "dimension": 27,
        "eigenvalue_optimality_rigorous": False,
        "exact_margin": str(numerator - denominator),
        "exact_quotient": str(numerator / denominator),
        "exact_rational_denominator": str(denominator),
        "exact_rational_numerator": str(numerator),
        "finite_space_crosses_one": numerator > denominator,
        "format": "frontier-active25-inner-D16-conditional-pencil-v6",
        "independent_arithmetic_reconstruction": False,
        "ledger_binding": {
            "device": context["ledger_snap"]["device"],
            "inode": context["ledger_snap"]["inode"],
            "path": str(Path(context["handle"]["path"]) /
                        staged.LEDGER_LEAF),
            "sha256": context["ledger_snap"]["sha256"],
        },
        "parameters": staged.v5.v2.core.parameter_record(),
        "precision_discovery": solves,
        "producer_driver_sha256": PINNED[STAGED],
        "rational_denominator_limit": 10**18,
        "rational_vector": [str(value) for value in vector],
        "serialized_stage_arithmetic_conditional": True,
        "shell_domain_counts": shell_counts,
        "stage_bindings": [
            {key: snap[key] for key in ("leaf", "sha256", "device", "inode")}
            for snap in context["stage_snaps"]],
        "status": "CONDITIONAL_DISCOVERY_ONLY",
        "theorem_ready": False,
        "two_precision_gate": {
            "precisions": [100, 160],
            "quotient_absolute_tolerance": "1e-70",
            "relative_residual_maximum": "1e-70",
        },
    }


def strict_result(value, expected_manifest_sha256, expected_ledger,
                  expected_authorization_sha256):
    expected_keys = {
        "48J_matrix", "I_diagonal", "assembler_sha256",
        "authorization_binding", "complete_manifest_binding",
        "dependency_sha256", "dimension", "eigenvalue_optimality_rigorous",
        "exact_margin", "exact_quotient", "exact_rational_denominator",
        "exact_rational_numerator", "finite_space_crosses_one", "format",
        "independent_arithmetic_reconstruction", "ledger_binding",
        "parameters", "precision_discovery", "producer_driver_sha256",
        "rational_denominator_limit", "rational_vector",
        "serialized_stage_arithmetic_conditional", "shell_domain_counts",
        "stage_bindings", "status", "theorem_ready", "two_precision_gate",
    }
    if type(value) is not dict or set(value) != expected_keys:
        raise ValueError("v6 conditional result schema mismatch")
    manifest = value["complete_manifest_binding"]
    ledger = value["ledger_binding"]
    authorization = value["authorization_binding"]
    if (value["assembler_sha256"] != _SELF["sha256"] or
            value["dependency_sha256"] != dependency_record() or
            value["dimension"] != 27 or type(value["dimension"]) is not int or
            value["eigenvalue_optimality_rigorous"] is not False or
            value["independent_arithmetic_reconstruction"] is not False or
            value["serialized_stage_arithmetic_conditional"] is not True or
            value["producer_driver_sha256"] != PINNED[STAGED] or
            value["format"] !=
            "frontier-active25-inner-D16-conditional-pencil-v6" or
            value["parameters"] != staged.v5.v2.core.parameter_record() or
            value["rational_denominator_limit"] != 10**18 or
            type(value["rational_denominator_limit"]) is not int or
            value["status"] != "CONDITIONAL_DISCOVERY_ONLY" or
            value["theorem_ready"] is not False or
            value["two_precision_gate"] != {
                "precisions": [100, 160],
                "quotient_absolute_tolerance": "1e-70",
                "relative_residual_maximum": "1e-70",
            }):
        raise ValueError("v6 conditional result identity mismatch")
    for name, binding, expected_sha in (
            ("ledger", ledger, expected_ledger["sha256"]),
            ("manifest", manifest, expected_manifest_sha256),
            ("authorization", authorization,
             expected_authorization_sha256)):
        if (type(binding) is not dict or set(binding) != {
                "device", "inode", "path", "sha256"} or
                type(binding["path"]) is not str or
                type(binding["device"]) is not int or binding["device"] < 0 or
                type(binding["inode"]) is not int or binding["inode"] < 0 or
                strict_sha(binding["sha256"], f"{name} binding SHA") !=
                expected_sha):
            raise ValueError(f"{name} result binding mismatch")
    if ({key: ledger[key] for key in ("sha256", "device", "inode")} !=
            {key: expected_ledger[key]
             for key in ("sha256", "device", "inode")} or
            Path(ledger["path"]).name != staged.LEDGER_LEAF or
            Path(manifest["path"]).name != staged.MANIFEST_LEAF or
            Path(ledger["path"]).parent != Path(manifest["path"]).parent):
        raise ValueError("dynamic result paths or external anchor mismatch")
    stage_bindings = value["stage_bindings"]
    if type(stage_bindings) is not list or len(stage_bindings) != 26:
        raise ValueError("stage binding inventory mismatch")
    seen = {(ledger["device"], ledger["inode"]),
            (manifest["device"], manifest["inode"])}
    for r, row in enumerate(stage_bindings):
        if (type(row) is not dict or set(row) != {
                "device", "inode", "leaf", "sha256"} or
                row["leaf"] != staged.STAGE_LEAVES[r] or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError("malformed stage result binding")
        strict_sha(row["sha256"], "stage result SHA")
        key = (row["device"], row["inode"])
        if key in seen:
            raise ValueError("dynamic result bindings alias")
        seen.add(key)
    a_raw = value["I_diagonal"]
    b_raw = value["48J_matrix"]
    vector_raw = value["rational_vector"]
    if (type(a_raw) is not list or len(a_raw) != 27 or
            type(b_raw) is not list or len(b_raw) != 27 or
            any(type(row) is not list or len(row) != 27 for row in b_raw) or
            type(vector_raw) is not list or len(vector_raw) != 27):
        raise ValueError("conditional matrix dimensions mismatch")
    a = [Q(item) for item in a_raw]
    b = [[Q(item) for item in row] for row in b_raw]
    vector = [Q(item) for item in vector_raw]
    if (any(type(raw) is not str or str(parsed) != raw
            for raw, parsed in zip(a_raw, a)) or
            any(type(b_raw[i][j]) is not str or
                str(b[i][j]) != b_raw[i][j]
                for i in range(27) for j in range(27)) or
            any(type(raw) is not str or str(parsed) != raw
                for raw, parsed in zip(vector_raw, vector)) or
            any(item <= 0 for item in a) or
            any(b[i][j] != b[j][i] for i in range(27) for j in range(27)) or
            any(b[i][j] for i in range(1, 27) for j in range(1, 27)
                if abs(i - j) > 1)):
        raise ValueError("conditional exact matrix invariant failed")
    denominator = sum((a[i] * vector[i] * vector[i]
                       for i in range(27)), Q(0))
    numerator = _exact_quadratic(b, vector)
    scalar = {
        "exact_rational_denominator": denominator,
        "exact_rational_numerator": numerator,
        "exact_quotient": numerator / denominator,
        "exact_margin": numerator - denominator,
    }
    if denominator <= 0:
        raise ArithmeticError("conditional vector has nonpositive I")
    for key, parsed in scalar.items():
        raw = value[key]
        if type(raw) is not str or str(Q(raw)) != raw or raw != str(parsed):
            raise ValueError(f"conditional {key} mismatch")
    if value["finite_space_crosses_one"] is not (numerator > denominator):
        raise ValueError("conditional sign flag mismatch")
    solves = value["precision_discovery"]
    if type(solves) is not list or len(solves) != 2:
        raise ValueError("two-precision discovery inventory mismatch")
    for precision, solve in zip((100, 160), solves):
        if (type(solve) is not dict or set(solve) != {
                "precision", "eigenvalue", "rayleigh_quotient",
                "relative_residual_bound", "jacobi_rotations", "vector"} or
                solve["precision"] != precision or
                type(solve["precision"]) is not int or
                type(solve["jacobi_rotations"]) is not int or
                solve["jacobi_rotations"] < 0 or
                type(solve["vector"]) is not list or
                len(solve["vector"]) != 27 or
                any(type(raw) is not str or not Decimal(raw).is_finite()
                    for raw in (solve["eigenvalue"],
                                solve["rayleigh_quotient"],
                                solve["relative_residual_bound"],
                                *solve["vector"]))):
            raise ValueError("malformed precision-discovery row")
    with localcontext() as context:
        context.prec = 180
        if (abs(Decimal(solves[0]["rayleigh_quotient"]) -
                Decimal(solves[1]["rayleigh_quotient"])) > Decimal("1e-70") or
                any(not Decimal(row["relative_residual_bound"]).is_finite() or
                    Decimal(row["relative_residual_bound"]) < 0 or
                    Decimal(row["relative_residual_bound"]) > Decimal("1e-70")
                    for row in solves)):
            raise ValueError("serialized two-precision gate failed")
    counts = value["shell_domain_counts"]
    if (type(counts) is not dict or set(counts) != {"hh", "hl", "ll"} or
            any(type(item) is not int or item < 0 for item in counts.values())):
        raise ValueError("shell-domain count schema mismatch")
    return True


def _hash_descriptor(descriptor):
    old = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        block = os.read(descriptor, 1_048_576)
        if not block:
            break
        digest.update(block)
    os.lseek(descriptor, old, os.SEEK_SET)
    return digest.hexdigest()


def _read_external(path, expected_sha256):
    strict_sha(expected_sha256, "expected conditional result SHA")
    target = Path(path)
    parent = staged.v5.open_record_dir(target.parent)
    descriptor = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(staged.v5._safe_leaf(target.name), flags,
                             dir_fd=parent["descriptor"])
        before = os.fstat(descriptor)
        data = _read_descriptor(descriptor)
        after = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns, before.st_nlink) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns, after.st_nlink) or
                len(data) != after.st_size or
                sha256_bytes(data) != expected_sha256):
            raise RuntimeError("conditional result snapshot mismatch")
        snapshot = {"data": data, "device": int(after.st_dev),
                    "inode": int(after.st_ino), "sha256": expected_sha256}
    finally:
        if descriptor is not None:
            os.close(descriptor)
        staged.v5.close_record_dir(parent)
    value = json.loads(data)
    if staged.canonical_json(value) != data:
        raise ValueError("conditional result is not canonical JSON")
    return value, snapshot


def _rebind_external(path, snapshot):
    value, current = _read_external(path, snapshot["sha256"])
    if current != snapshot:
        raise RuntimeError("conditional result changed during verification")
    return value


def publish_output(path, payload, context, expected_manifest_sha256,
                   expected_producer_sha256, expected_self_sha256):
    bind_startup_self(expected_self_sha256)
    target = Path(path)
    parent = staged.v5.open_record_dir(target.parent)
    descriptor = None
    try:
        record = context["handle"]
        if ((parent["device"], parent["inode"]) ==
                (record["device"], record["inode"])):
            raise ValueError("conditional output aliases stage directory")
        protected = {FILE, *PINNED,
                     Path(context["authorization"]["path"]),
                     Path(record["path"]) / staged.LEDGER_LEAF,
                     Path(record["path"]) / staged.MANIFEST_LEAF,
                     *(Path(record["path"]) / leaf
                       for leaf in staged.STAGE_LEAVES)}
        if target.resolve(strict=False) in protected:
            raise ValueError("conditional output aliases a protected input")
        encoded = staged.canonical_json(payload)
        digest = sha256_bytes(encoded)
        dep_start = snapshots()
        producer_start = staged.snapshots()
        core_start = staged.v5.v2.core.require_pins()
        self_start = bind_startup_self(expected_self_sha256)
        rebind_completed(context, expected_manifest_sha256,
                         expected_producer_sha256, expected_self_sha256)
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(staged.v5._safe_leaf(target.name), flags, 0o600,
                             dir_fd=parent["descriptor"])
        position = 0
        while position < len(encoded):
            written = os.write(descriptor, encoded[position:])
            if written <= 0:
                raise OSError("short conditional-result write")
            position += written
        os.fsync(descriptor)
        os.fsync(parent["descriptor"])
        owned = os.fstat(descriptor)
        rebound = staged.v5.read_leaf(parent, target.name, len(encoded))
        if (owned.st_nlink != 1 or _hash_descriptor(descriptor) != digest or
                rebound["sha256"] != digest or
                (rebound["device"], rebound["inode"]) !=
                (int(owned.st_dev), int(owned.st_ino))):
            raise RuntimeError("conditional result path was replaced")
        rebind_completed(context, expected_manifest_sha256,
                         expected_producer_sha256, expected_self_sha256)
        if (bind_startup_self(expected_self_sha256) != self_start or
                snapshots() != dep_start or staged.snapshots() != producer_start or
                staged.v5.v2.core.require_pins() != core_start):
            raise RuntimeError("conditional assembler closure changed")
        rebound = staged.v5.read_leaf(parent, target.name, len(encoded))
        if (rebound["sha256"] != digest or
                (rebound["device"], rebound["inode"]) !=
                (int(owned.st_dev), int(owned.st_ino))):
            raise RuntimeError("conditional result changed after final rebind")
        rebind_completed(context, expected_manifest_sha256,
                         expected_producer_sha256, expected_self_sha256)
        os.close(descriptor)
        descriptor = None
        return rebound
    except Exception:
        if descriptor is not None:
            rejection = b'{"status":"rejected-incomplete-v6-assembly"}\n'
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.ftruncate(descriptor, 0)
                os.write(descriptor, rejection)
                os.fsync(descriptor)
                os.fsync(parent["descriptor"])
            finally:
                os.close(descriptor)
                descriptor = None
        raise
    finally:
        staged.v5.close_record_dir(parent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-dir", type=Path, required=True)
    parser.add_argument("--authorization-file", type=Path, required=True)
    parser.add_argument("--expected-authorization-sha256", required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--expected-producer-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-ledger-sha256", required=True)
    parser.add_argument("--expected-ledger-device", type=int, required=True)
    parser.add_argument("--expected-ledger-inode", type=int, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-output", type=Path)
    parser.add_argument("--expected-output-sha256")
    args = parser.parse_args()
    _direct_cli_identity(args.expected_self_sha256)
    ledger = expected_ledger_binding(
        args.expected_ledger_sha256, args.expected_ledger_device,
        args.expected_ledger_inode)
    if (args.output is None) == (args.verify_output is None):
        parser.error("choose exactly one output or verification mode")
    if args.output is not None and args.expected_output_sha256 is not None:
        parser.error("fresh assembly does not accept an output SHA")
    if args.verify_output is not None and args.expected_output_sha256 is None:
        parser.error("verification requires the external output SHA")
    context = open_completed(
        args.record_dir, args.expected_manifest_sha256, ledger,
        args.authorization_file, args.expected_authorization_sha256,
        args.expected_producer_sha256, args.expected_self_sha256)
    try:
        rebuilt = build_result(context)
        strict_result(rebuilt, args.expected_manifest_sha256, ledger,
                      args.expected_authorization_sha256)
        rebind_completed(context, args.expected_manifest_sha256,
                         args.expected_producer_sha256,
                         args.expected_self_sha256)
        if args.output is not None:
            snap = publish_output(
                args.output, rebuilt, context, args.expected_manifest_sha256,
                args.expected_producer_sha256, args.expected_self_sha256)
            print(json.dumps({"output_sha256": snap["sha256"],
                              "theorem_ready": False}, sort_keys=True))
            return
        existing, output_snapshot = _read_external(
            args.verify_output, args.expected_output_sha256)
        strict_result(existing, args.expected_manifest_sha256, ledger,
                      args.expected_authorization_sha256)
        if staged.canonical_json(existing) != staged.canonical_json(rebuilt):
            raise RuntimeError("conditional result differs from fresh rebuild")
        rebind_completed(context, args.expected_manifest_sha256,
                         args.expected_producer_sha256,
                         args.expected_self_sha256)
        if staged.canonical_json(
                _rebind_external(args.verify_output, output_snapshot)) != \
                staged.canonical_json(existing):
            raise RuntimeError("conditional result changed before success")
        print(json.dumps({"output_sha256": args.expected_output_sha256,
                          "status": "CONDITIONAL_MATCH",
                          "theorem_ready": False}, sort_keys=True))
    finally:
        close_completed(context)


if __name__ == "__main__":
    main()
