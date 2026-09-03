#!/usr/bin/env python3
"""Compare normal and ``-O`` D4 v5 runs modulo provenance-only fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
from pathlib import Path


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
NORMAL_RESULT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production.json"
OPT_RESULT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production_opt.json"
NORMAL_AUDIT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production_audit_v3.json"
OPT_AUDIT = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_production_opt_audit_v3.json"
NORMAL_RECORDS = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_records"
OPT_RECORDS = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_records_opt"
GATE = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_gate_v5.json"
NORMAL_AUTHORIZATION = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_authorization.json"
OPT_AUTHORIZATION = REPO_ROOT / \
    "agents/structural-basis/results/importance_d4_calibration_v5_authorization_opt.json"

NORMAL_AUTH_SHA256 = \
    "11f75e01e019be90be1caea052f8e6452d59f8d59bbaea9bddf5022a9bb978dd"
OPT_AUTH_SHA256 = \
    "26f8da920c032d9fdf1f0000a65cec26894f07a47d17ba675b1f2ca2f6e117c9"
GATE_SHA256 = \
    "860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196"
DRIVER_SHA256 = \
    "b0b4350ff1804530724c87b8693aa4dd0059904f3eb9d72696497fb3c90c1b41"
NORMAL_AUDITOR_SHA256 = \
    "7a0685f089125654f5faddced809cce784f9b7aabfd9c4ae8e669771710ab2da"
OPT_AUDITOR_SHA256 = \
    "319d9e2c8aa09c7d6ab1dfe54ba0624519953e9e6ac84e6bf15bd8c603bff642"
NORMAL_SUPERSEDED_AUDITOR_SHA256 = \
    "4e9ab0002b3f33019162d537f03310880e0ff788d48b36239957d05cb9608cf7"
OPT_SUPERSEDED_AUDITOR_SHA256 = \
    "d67005ba95fc1a0435bbe8122d612393c8939b3ea6ea761416224954894227bd"
DECISION_TABLE_SHA256 = \
    "3660ae47168ccbadb8cfa2cb2152deecf64321f9cd78ba2df1d4a0f8a68c29b4"
NUMPY_VERSION = "2.2.4"
NUMPY_INIT_SHA256 = \
    "6ae17b070c0f70a8e3cad89a510a256942e5a1f37ea5feb120cec167ed2a6236"
CONVENTIONS_SHA256 = \
    "43c7a2d225f5ee676ee345194219f9460a5a24135a7ccc052de47368a92efde2"
SCHEDULE_SHA256 = \
    "7d618324c2167e2eaf8caf8ba7c6a097a881ef23e8d35350469c78ea182fe755"
AUDIT_SCOPE = "D4-stratified-importance-calibration-discovery-only"
NEVER_IMPLIES = ["rigorous_error_bound", "exact_sieve_quotient",
                 "H1_at_most_236"]
DECISION_EXIT_CODES = {
    "CALIBRATION_PASS": 0,
    "EXTENSION_ELIGIBLE": 2,
    "CALIBRATION_RETIRED": 3,
    "IMPLEMENTATION_REJECTED": 1,
}

RESULT_PROVENANCE_DIFFERENCES = frozenset({
    "authorization_sha256", "authorization_binding",
    "record_checkpoints", "wall_seconds", "peak_rss_kib",
})
AUDIT_PROVENANCE_DIFFERENCES = frozenset({
    "authorization_sha256", "production_result_binding",
    "auditor_sha256", "record_directory_binding",
    "checkpoint_manifest_sha256", "supersedes_invalid_auditor_sha256",
    "wall_seconds", "peak_rss_kib",
})

RESULT_KEYS = frozenset({
    "status", "rigorous", "theorem_ready", "mode", "gate_path",
    "gate_sha256", "driver_sha256", "authorization_sha256",
    "parent_result_sha256", "gate_binding", "authorization_binding",
    "parent_result_binding", "wall_seconds", "peak_rss_kib",
    "float_encoding", "conventions", "schedule", "records",
    "record_checkpoints", "analysis", "analysis_failure",
    "fresh_exact_reconstruction_required",
})
AUDIT_KEYS = frozenset({
    "status", "rigorous", "theorem_ready", "scope", "decision",
    "decision_exit_code", "driver_sha256", "gate_sha256",
    "authorization_sha256", "production_result_binding",
    "decision_table_sha256", "auditor_sha256",
    "supersedes_invalid_auditor_sha256", "record_directory_binding",
    "checkpoint_count", "record_leaf_names_sha256",
    "checkpoint_manifest_sha256", "records_core_sha256",
    "analysis_core_sha256", "hard_gate_failures",
    "analysis_failure", "statistical_gate_failures", "wall_seconds",
    "peak_rss_kib",
    "numpy_version", "numpy_init_sha256",
    "fresh_exact_reconstruction_required", "never_implies",
})


def expected_checkpoint_names():
    return tuple(
        f"{target}_r{stratum:02d}_rep{replicate}_initial.json"
        for target in ("I", "J") for stratum in range(16)
        for replicate in range(4))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def require_sha256(value, name):
    if (not isinstance(value, str) or len(value) != 64 or
            any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{name} is not canonical lowercase SHA-256")
    return value


def strict_json_bytes(data, name):
    def reject_float(_token):
        raise ValueError(f"{name} contains a JSON float")

    def reject_constant(_token):
        raise ValueError(f"{name} contains a nonfinite token")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError(f"{name} has a duplicate/non-string key")
            answer[key] = value
        return answer

    if not isinstance(data, bytes) or len(data) > 256_000_000:
        raise ValueError(f"{name} is not bounded bytes")
    return json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs_hook,
        parse_float=reject_float, parse_constant=reject_constant)


def canonical_sha256(value):
    return sha256_bytes(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode())


def read_snapshot(path, expected_sha256, name):
    expected_sha256 = require_sha256(expected_sha256, f"{name} SHA-256")
    path = Path(path).resolve()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 256_000_000:
            raise ValueError(f"{name} is not a bounded regular file")
        chunks = []
        total = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > 256_000_000:
                raise ValueError(f"{name} exceeds byte bound")
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if ((before.st_dev, before.st_ino, before.st_size,
             before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)):
            raise ArithmeticError(f"{name} changed during read")
        digest = sha256_bytes(data)
        if digest != expected_sha256:
            raise ValueError(f"{name} differs from completed external SHA")
        return {"path": str(path), "sha256": digest,
                "device": int(after.st_dev), "inode": int(after.st_ino),
                "data": data}
    finally:
        os.close(descriptor)


def validate_expected_self(expected):
    expected = require_sha256(expected, "expected comparator SHA-256")
    if sha256_file(HERE) != expected:
        raise ValueError("running comparator differs from external trust root")
    return expected


def _validate_file_binding(value, expected_path, expected_sha, name):
    if not isinstance(value, dict) or set(value) != {
            "path", "sha256", "device", "inode"}:
        raise ValueError(f"{name} has unexpected schema")
    if (value["path"] != str(Path(expected_path).resolve()) or
            value["sha256"] != expected_sha or
            any(isinstance(value[key], bool) or
                not isinstance(value[key], int) or value[key] < 0
                for key in ("device", "inode"))):
        raise ValueError(f"{name} is malformed or misbound")
    return True


def _expected_analysis_decision(raw):
    analysis = raw["analysis"]
    failure = raw["analysis_failure"]
    if analysis is None:
        if (not isinstance(failure, dict) or set(failure) != {
                "exception_type", "message"} or
                not all(isinstance(failure[key], str) and failure[key]
                        for key in failure)):
            raise ValueError("missing analysis has malformed failure")
        return ("d4-stratified-calibration-rejected",
                "IMPLEMENTATION_REJECTED", [], [])
    if failure is not None or not isinstance(analysis, dict):
        raise ValueError("analysis/failure alternatives are malformed")
    for key in ("gates_passed", "extension_authorized"):
        if not isinstance(analysis.get(key), bool):
            raise ValueError(f"analysis {key} is not Boolean")
    for key in ("hard_gates", "statistical_gates"):
        table = analysis.get(key)
        if (not isinstance(table, dict) or not table or
                not all(isinstance(name, str) and name and
                        isinstance(value, bool)
                        for name, value in table.items())):
            raise ValueError(f"analysis {key} is malformed")
    if analysis["gates_passed"]:
        status, decision = ("d4-stratified-calibration-pass",
                            "CALIBRATION_PASS")
    elif analysis["extension_authorized"]:
        status, decision = ("d4-stratified-calibration-rejected",
                            "EXTENSION_ELIGIBLE")
    else:
        status, decision = ("d4-stratified-calibration-rejected",
                            "CALIBRATION_RETIRED")
    hard = sorted(key for key, value in analysis["hard_gates"].items()
                  if not value)
    statistical = sorted(
        key for key, value in analysis["statistical_gates"].items()
        if not value)
    return status, decision, hard, statistical


def _validate_result(raw, authorization_sha, authorization_path,
                     result_sha, record_directory):
    if not isinstance(raw, dict) or set(raw) != RESULT_KEYS:
        raise ValueError("production result has unexpected schema")
    expected_status, decision, hard, statistical = \
        _expected_analysis_decision(raw)
    if (raw["status"] != expected_status or
            raw["mode"] != "production" or raw["rigorous"] is not False or
            raw["theorem_ready"] is not False or
            raw["gate_path"] != str(GATE.relative_to(REPO_ROOT)) or
            raw["gate_sha256"] != GATE_SHA256 or
            raw["driver_sha256"] != DRIVER_SHA256 or
            raw["authorization_sha256"] != authorization_sha or
            raw["parent_result_sha256"] is not None or
            raw["parent_result_binding"] is not None or
            raw["float_encoding"] != "python-float-hex" or
            not isinstance(raw["conventions"], dict) or
            canonical_sha256(raw["conventions"]) != CONVENTIONS_SHA256 or
            not isinstance(raw["schedule"], dict) or
            canonical_sha256(raw["schedule"]) != SCHEDULE_SHA256 or
            raw["fresh_exact_reconstruction_required"] is not True or
            not isinstance(raw["records"], list) or
            len(raw["records"]) != 128 or
            not isinstance(raw["record_checkpoints"], list) or
            len(raw["record_checkpoints"]) != 128):
        raise ValueError("production result identity flags are invalid")
    _validate_file_binding(
        raw["gate_binding"], GATE, GATE_SHA256,
        "production gate binding")
    _validate_file_binding(
        raw["authorization_binding"], authorization_path,
        authorization_sha, "production authorization binding")
    if not isinstance(raw["wall_seconds"], str):
        raise ValueError("wall time is not canonical float-hex text")
    try:
        wall = float.fromhex(raw["wall_seconds"])
    except ValueError as error:
        raise ValueError("wall time is malformed") from error
    if (not math.isfinite(wall) or wall <= 0 or
            wall.hex() != raw["wall_seconds"]):
        raise ValueError("wall time is noncanonical/nonpositive")
    if (isinstance(raw["peak_rss_kib"], bool) or
            not isinstance(raw["peak_rss_kib"], int) or
            raw["peak_rss_kib"] <= 0):
        raise ValueError("peak RSS is invalid")
    expected_paths = [str((Path(record_directory).resolve() / name))
                      for name in expected_checkpoint_names()]
    observed_paths = []
    observed_inodes = []
    for expected_path, claimed in zip(
            expected_paths, raw["record_checkpoints"]):
        if not isinstance(claimed, dict) or set(claimed) != {
                "path", "sha256", "device", "inode"}:
            raise ValueError("checkpoint binding has unexpected schema")
        require_sha256(claimed["sha256"], "checkpoint SHA-256")
        if (claimed["path"] != expected_path or
                any(isinstance(claimed[key], bool) or
                    not isinstance(claimed[key], int) or claimed[key] < 0
                    for key in ("device", "inode"))):
            raise ValueError("checkpoint manifest order/path is invalid")
        observed_paths.append(claimed["path"])
        observed_inodes.append((claimed["device"], claimed["inode"]))
    if (len(set(observed_paths)) != 128 or
            len(set(observed_inodes)) != 128):
        raise ValueError("checkpoint manifest is not 128 distinct files")
    return {
        "result_sha256": result_sha,
        "records_core_sha256": canonical_sha256(raw["records"]),
        "analysis_core_sha256": canonical_sha256({
            "analysis": raw["analysis"],
            "analysis_failure": raw["analysis_failure"]}),
        "checkpoint_manifest_sha256":
            canonical_sha256(raw["record_checkpoints"]),
        "record_leaf_names_sha256":
            canonical_sha256(sorted(expected_checkpoint_names())),
        "decision": decision,
        "hard_gate_failures": hard,
        "statistical_gate_failures": statistical,
    }


def _validate_audit(raw, result, result_core, *, authorization_sha,
                    result_path, auditor_sha, superseded_auditor_sha,
                    record_directory):
    if not isinstance(raw, dict) or set(raw) != AUDIT_KEYS:
        raise ValueError("independent audit has unexpected schema")
    if (raw["status"] != "complete-independent-d4-v5-production-audit" or
            raw["rigorous"] is not False or raw["theorem_ready"] is not False or
            raw["scope"] != AUDIT_SCOPE or
            raw["driver_sha256"] != DRIVER_SHA256 or
            raw["gate_sha256"] != GATE_SHA256 or
            raw["authorization_sha256"] != authorization_sha or
            raw["decision"] != result_core["decision"] or
            raw["decision_exit_code"] !=
            DECISION_EXIT_CODES[result_core["decision"]] or
            raw["auditor_sha256"] != auditor_sha or
            raw["supersedes_invalid_auditor_sha256"] !=
            superseded_auditor_sha or
            raw["decision_table_sha256"] != DECISION_TABLE_SHA256 or
            raw["checkpoint_count"] != 128 or
            raw["record_leaf_names_sha256"] !=
            result_core["record_leaf_names_sha256"] or
            raw["checkpoint_manifest_sha256"] !=
            result_core["checkpoint_manifest_sha256"] or
            raw["records_core_sha256"] !=
            result_core["records_core_sha256"] or
            raw["analysis_core_sha256"] !=
            result_core["analysis_core_sha256"] or
            raw["analysis_failure"] != result["analysis_failure"] or
            raw["hard_gate_failures"] !=
            result_core["hard_gate_failures"] or
            raw["statistical_gate_failures"] !=
            result_core["statistical_gate_failures"] or
            raw["wall_seconds"] != result["wall_seconds"] or
            raw["peak_rss_kib"] != result["peak_rss_kib"] or
            raw["numpy_version"] != NUMPY_VERSION or
            raw["numpy_init_sha256"] != NUMPY_INIT_SHA256 or
            raw["never_implies"] != NEVER_IMPLIES or
            raw["fresh_exact_reconstruction_required"] is not True):
        raise ValueError("independent audit provenance/core mismatch")
    _validate_file_binding(
        raw["production_result_binding"], result_path,
        result_core["result_sha256"], "audited production result")
    directory = raw["record_directory_binding"]
    if (not isinstance(directory, dict) or set(directory) != {
            "path", "device", "inode"} or
            directory["path"] != str(Path(record_directory).resolve()) or
            any(isinstance(directory[key], bool) or
                not isinstance(directory[key], int) or directory[key] < 0
                for key in ("device", "inode"))):
        raise ValueError("audited record directory is malformed/misbound")
    return True


def compare_mathematical_payloads(normal, optimized, normal_audit, opt_audit,
                                  *, normal_result_sha, opt_result_sha,
                                  normal_auditor_sha, opt_auditor_sha,
                                  normal_result_binding,
                                  opt_result_binding):
    if (normal_auditor_sha != NORMAL_AUDITOR_SHA256 or
            opt_auditor_sha != OPT_AUDITOR_SHA256):
        raise ValueError("completed auditors differ from fixed v3 consumers")
    _validate_file_binding(
        normal_result_binding, NORMAL_RESULT, normal_result_sha,
        "actual normal result snapshot")
    _validate_file_binding(
        opt_result_binding, OPT_RESULT, opt_result_sha,
        "actual optimized result snapshot")
    normal_core = _validate_result(
        normal, NORMAL_AUTH_SHA256, NORMAL_AUTHORIZATION,
        normal_result_sha, NORMAL_RECORDS)
    opt_core = _validate_result(
        optimized, OPT_AUTH_SHA256, OPT_AUTHORIZATION,
        opt_result_sha, OPT_RECORDS)
    differing_result_keys = sorted(
        key for key in RESULT_KEYS if normal[key] != optimized[key])
    unexpected = set(differing_result_keys) - RESULT_PROVENANCE_DIFFERENCES
    if unexpected:
        raise ArithmeticError(
            "normal/-O mathematical result mismatch: " +
            ",".join(sorted(unexpected)))
    if normal_core["records_core_sha256"] != opt_core["records_core_sha256"]:
        raise ArithmeticError("normal/-O record core hashes differ")
    if normal_core["analysis_core_sha256"] != opt_core["analysis_core_sha256"]:
        raise ArithmeticError("normal/-O analysis core hashes differ")
    _validate_audit(
        normal_audit, normal, normal_core,
        authorization_sha=NORMAL_AUTH_SHA256,
        result_path=NORMAL_RESULT, auditor_sha=NORMAL_AUDITOR_SHA256,
        superseded_auditor_sha=NORMAL_SUPERSEDED_AUDITOR_SHA256,
        record_directory=NORMAL_RECORDS)
    if normal_audit["production_result_binding"] != normal_result_binding:
        raise ValueError("normal audit does not bind actual result inode")
    _validate_audit(
        opt_audit, optimized, opt_core,
        authorization_sha=OPT_AUTH_SHA256,
        result_path=OPT_RESULT, auditor_sha=OPT_AUDITOR_SHA256,
        superseded_auditor_sha=OPT_SUPERSEDED_AUDITOR_SHA256,
        record_directory=OPT_RECORDS)
    if opt_audit["production_result_binding"] != opt_result_binding:
        raise ValueError("optimized audit does not bind actual result inode")
    differing_audit_keys = sorted(
        key for key in AUDIT_KEYS if normal_audit[key] != opt_audit[key])
    unexpected = set(differing_audit_keys) - AUDIT_PROVENANCE_DIFFERENCES
    if unexpected:
        raise ArithmeticError(
            "normal/-O mathematical audit mismatch: " +
            ",".join(sorted(unexpected)))
    if (normal_audit["decision"] != opt_audit["decision"] or
            normal_audit["decision_exit_code"] !=
            opt_audit["decision_exit_code"]):
        raise ArithmeticError("normal/-O audit decisions differ")
    return {
        "decision": normal_audit["decision"],
        "decision_exit_code": normal_audit["decision_exit_code"],
        "records_core_sha256": normal_core["records_core_sha256"],
        "analysis_core_sha256": normal_core["analysis_core_sha256"],
        "differing_result_keys": differing_result_keys,
        "differing_audit_keys": differing_audit_keys,
    }


def validate_comparison_output(path):
    path = Path(path)
    parent = path.parent.resolve()
    if not parent.is_dir() or Path(path.name).name != path.name:
        raise ValueError("comparison output must be a fresh safe leaf")
    candidate = parent / path.name
    for trusted in (NORMAL_RECORDS.resolve(), OPT_RECORDS.resolve()):
        try:
            candidate.relative_to(trusted)
        except ValueError:
            pass
        else:
            raise ValueError("comparison output enters a record directory")
    if candidate in {path.resolve() for path in (
            NORMAL_RESULT, OPT_RESULT, NORMAL_AUDIT, OPT_AUDIT, HERE)}:
        raise ValueError("comparison output aliases an input")
    if os.path.lexists(candidate):
        raise FileExistsError("comparison output already exists")
    return candidate


def publish_report(path, report, bindings):
    """O_EXCL publication through a held canonical parent with final rehash."""
    path = validate_comparison_output(path)
    for input_path, digest in bindings.items():
        if sha256_file(input_path) != digest:
            raise ValueError("comparison input changed before publication")
    parent_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        parent_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        parent_flags |= os.O_NOFOLLOW
    parent_fd = os.open(path.parent, parent_flags)
    output_fd = None
    try:
        parent_stat = os.fstat(parent_fd)
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        output_fd = os.open(path.name, flags, 0o600, dir_fd=parent_fd)
        encoded = (json.dumps(report, sort_keys=True, separators=(",", ":"),
                              allow_nan=False) + "\n").encode()
        digest = sha256_bytes(encoded)
        written = 0
        while written < len(encoded):
            count = os.write(output_fd, encoded[written:])
            if count <= 0:
                raise OSError("short comparison-output write")
            written += count
        os.fsync(output_fd)
        os.lseek(output_fd, 0, os.SEEK_SET)
        if sha256_bytes(os.read(output_fd, len(encoded) + 1)) != digest:
            raise ArithmeticError("comparison output bytes changed")
        check_fd = os.open(path.name, os.O_RDONLY, dir_fd=parent_fd)
        try:
            if ((os.fstat(check_fd).st_dev, os.fstat(check_fd).st_ino) !=
                    (os.fstat(output_fd).st_dev, os.fstat(output_fd).st_ino)):
                raise ArithmeticError("comparison output inode changed")
        finally:
            os.close(check_fd)
        for input_path, expected in bindings.items():
            if sha256_file(input_path) != expected:
                raise ValueError("comparison input changed during publication")
        current_parent = os.stat(path.parent, follow_symlinks=False)
        if ((current_parent.st_dev, current_parent.st_ino) !=
                (parent_stat.st_dev, parent_stat.st_ino)):
            raise ArithmeticError("comparison output parent changed")
        # This is deliberately after every input and parent rebind.  A
        # pathname replacement in the last closure window must not be
        # accepted merely because the still-held original descriptor is good.
        final_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            final_flags |= os.O_NOFOLLOW
        final_fd = os.open(path.name, final_flags, dir_fd=parent_fd)
        try:
            final_stat = os.fstat(final_fd)
            os.lseek(final_fd, 0, os.SEEK_SET)
            chunks = []
            while True:
                block = os.read(final_fd, 1024 * 1024)
                if not block:
                    break
                chunks.append(block)
            if ((final_stat.st_dev, final_stat.st_ino) !=
                    (os.fstat(output_fd).st_dev,
                     os.fstat(output_fd).st_ino) or
                    sha256_bytes(b"".join(chunks)) != digest):
                raise ArithmeticError(
                    "comparison output changed after final closure")
        finally:
            os.close(final_fd)
        os.close(output_fd)
        output_fd = None
        return digest
    except Exception:
        if output_fd is not None:
            rejection = b'{"status":"rejected-incomplete-run-comparison"}\n'
            os.lseek(output_fd, 0, os.SEEK_SET)
            os.ftruncate(output_fd, 0)
            os.write(output_fd, rejection)
            os.fsync(output_fd)
        raise
    finally:
        if output_fd is not None:
            os.close(output_fd)
        os.close(parent_fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-comparator-sha256", required=True)
    parser.add_argument("--normal-result-sha256", required=True)
    parser.add_argument("--opt-result-sha256", required=True)
    parser.add_argument("--normal-audit-sha256", required=True)
    parser.add_argument("--opt-audit-sha256", required=True)
    parser.add_argument("--normal-auditor-sha256", required=True)
    parser.add_argument("--opt-auditor-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    expected_self = validate_expected_self(args.expected_comparator_sha256)
    output = validate_comparison_output(args.output)
    normal_result_sha = require_sha256(
        args.normal_result_sha256, "normal result SHA-256")
    opt_result_sha = require_sha256(
        args.opt_result_sha256, "optimized result SHA-256")
    normal_audit_sha = require_sha256(
        args.normal_audit_sha256, "normal audit SHA-256")
    opt_audit_sha = require_sha256(
        args.opt_audit_sha256, "optimized audit SHA-256")
    normal_auditor_sha = require_sha256(
        args.normal_auditor_sha256, "normal auditor SHA-256")
    opt_auditor_sha = require_sha256(
        args.opt_auditor_sha256, "optimized auditor SHA-256")
    if (normal_auditor_sha != NORMAL_AUDITOR_SHA256 or
            opt_auditor_sha != OPT_AUDITOR_SHA256):
        raise ValueError("caller auditor hashes differ from fixed v3 consumers")
    requested = {
        "normal_result": (NORMAL_RESULT, normal_result_sha),
        "opt_result": (OPT_RESULT, opt_result_sha),
        "normal_audit": (NORMAL_AUDIT, normal_audit_sha),
        "opt_audit": (OPT_AUDIT, opt_audit_sha),
    }
    snapshots = {name: read_snapshot(path, digest, name)
                 for name, (path, digest) in requested.items()}
    parsed = {name: strict_json_bytes(item["data"], name)
              for name, item in snapshots.items()}
    comparison = compare_mathematical_payloads(
        parsed["normal_result"], parsed["opt_result"],
        parsed["normal_audit"], parsed["opt_audit"],
        normal_result_sha=snapshots["normal_result"]["sha256"],
        opt_result_sha=snapshots["opt_result"]["sha256"],
        normal_auditor_sha=normal_auditor_sha,
        opt_auditor_sha=opt_auditor_sha,
        normal_result_binding={key: snapshots["normal_result"][key]
                               for key in ("path", "sha256",
                                           "device", "inode")},
        opt_result_binding={key: snapshots["opt_result"][key]
                            for key in ("path", "sha256",
                                        "device", "inode")})
    if sha256_file(HERE) != expected_self:
        raise ValueError("comparator changed after its initial trust check")
    report = {
        "status": "complete-normal-vs-opt-mathematical-comparison",
        "rigorous": False,
        "theorem_ready": False,
        "comparator_sha256": expected_self,
        "normal_result_sha256": snapshots["normal_result"]["sha256"],
        "opt_result_sha256": snapshots["opt_result"]["sha256"],
        "normal_audit_sha256": snapshots["normal_audit"]["sha256"],
        "opt_audit_sha256": snapshots["opt_audit"]["sha256"],
        **comparison,
        "fresh_exact_reconstruction_required": True,
    }
    bindings = {str(HERE): expected_self, **{
        item["path"]: item["sha256"] for item in snapshots.values()}}
    digest = publish_report(output, report, bindings)
    print(json.dumps({"comparison_output_sha256": digest,
                      "decision": comparison["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
