#!/usr/bin/env python3
"""Conditional assembler for the disabled cap-slack/D16 staged package.

This consumer binds an externally identified completed one-shot record,
restricts the frozen D2 cap-shell forms to the 38 pilot labels, and inserts
``48 * raw_J_cross`` exactly once.  It emits sparse exact forms only: there is
no eigensolve, vector, quotient, or theorem claim, and serialized stage
arithmetic still requires the separately designed independent reconstruction.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
STAGED = FILE.with_name("active25_cap_slack_cross_staged_v3.py")
STAGED_TEST = (REPO / "agents/structural-basis/tests/"
               "test_active25_cap_slack_cross_staged_v3.py")
PINNED = {
    STAGED:
        "2657f9e008dbfb461c8010216dfe243e0b64d5450382dc4021b22978d0af020c",
    STAGED_TEST:
        "f75d0fd9ce38d26f0f2ece4ad6022cf827259afa57bbb74894816030b39e771d",
}
RESULT_FORMAT = "active25-cap-slack-D16-conditional-exact-pencil-v3"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def snapshots():
    result = {}
    for path, expected in PINNED.items():
        data = path.read_bytes()
        if sha256_bytes(data) != expected:
            raise RuntimeError(f"assembler dependency changed: {path}")
        result[path] = data
    return result


_START = snapshots()
_SPEC = importlib.util.spec_from_file_location(
    "active25_cap_slack_staged_v3_for_assembler", STAGED)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(STAGED)
staged = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = staged
_SPEC.loader.exec_module(staged)
_SELF = staged._open_stable_regular(FILE)


def bind_startup_self(expected_sha256):
    staged.strict_sha(expected_sha256, "expected assembler self SHA")
    if expected_sha256 != _SELF["sha256"]:
        raise RuntimeError("externally supplied assembler SHA does not match")
    return staged._rebind_stable_regular(_SELF)


def dependency_record():
    result = {str(path.relative_to(REPO)): digest
              for path, digest in PINNED.items()}
    result.update(staged.dependency_record())
    return dict(sorted(result.items()))


def _parse_sparse(raw, dimension, name):
    if type(raw) is not list:
        raise ValueError(f"{name} is not a list")
    entries, keys = [], []
    for position, row in enumerate(raw):
        if (type(row) is not list or len(row) != 3 or
                type(row[0]) is not int or type(row[1]) is not int or
                not 0 <= row[1] <= row[0] < dimension):
            raise ValueError(f"malformed {name} entry {position}")
        value = staged.strict_q(row[2], f"{name} entry {position}")
        if not value:
            raise ValueError(f"explicit zero in {name}")
        keys.append((row[0], row[1]))
        entries.append((row[0], row[1], value))
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ValueError(f"{name} order or uniqueness changed")
    return entries


def _dense_from_upper(entries, dimension):
    matrix = [[Q(0) for _ in range(dimension)]
              for _ in range(dimension)]
    for i, j, value in entries:
        matrix[i][j] = matrix[j][i] = value
    return matrix


def _upper_from_dense(matrix):
    return [[i, j, str(matrix[i][j])]
            for i in range(len(matrix)) for j in range(i + 1)
            if matrix[i][j]]


def restricted_cap_forms():
    raw = staged.strict_json_bytes(
        staged._START[staged.CAP_D2], "frozen cap D2 form")
    full_labels = staged.pilot.V1.cap_labels(2)
    pilot_labels = staged.pilot.pilot_labels()
    if (raw.get("format") != "active25-count-cap-slack-shell-exact-v1" or
            raw.get("dimension") != len(full_labels) or
            raw.get("maximum_cap_slack_degree") != 2 or
            raw.get("basis") != [list(label) for label in full_labels] or
            raw.get("script_sha256") !=
            staged.pilot.V1.PINNED[staged.pilot.V1.CAP_SOURCE] or
            raw.get("rigorous_matrix_entries") is not True or
            raw.get("contains_inner_cross") is not False or
            raw.get("theorem_ready") is not False):
        raise ValueError("frozen cap D2 identity changed")
    index = {label: position for position, label in enumerate(full_labels)}
    selected = {index[label]: position
                for position, label in enumerate(pilot_labels)}
    full_i = _parse_sparse(raw["I_upper_nonzero"], len(full_labels), "D2 I")
    full_b = _parse_sparse(raw["kJ_upper_nonzero"], len(full_labels), "D2 48J")

    def restrict(entries):
        result = []
        for i, j, value in entries:
            if i in selected and j in selected:
                ni, nj = selected[i], selected[j]
                if ni < nj:
                    ni, nj = nj, ni
                result.append((ni, nj, value))
        return sorted(result)

    i_entries = restrict(full_i)
    b_entries = restrict(full_b)
    i_matrix = _dense_from_upper(i_entries, len(pilot_labels))
    b_matrix = _dense_from_upper(b_entries, len(pilot_labels))
    if (any(i_matrix[a][b] for a, left in enumerate(pilot_labels)
            for b, right in enumerate(pilot_labels)
            if left[0] != right[0]) or
            any(b_matrix[a][b] for a, left in enumerate(pilot_labels)
                for b, right in enumerate(pilot_labels)
                if abs(left[0] - right[0]) > 1) or
            any(i_matrix[i][i] <= 0 for i in range(len(pilot_labels)))):
        raise ArithmeticError("restricted cap forms violate exact sparsity")
    return pilot_labels, i_matrix, b_matrix


def assemble_exact_pencil(inner_i, inner_b, raw_cross_rows, *, k=48):
    labels, cap_i, cap_b = restricted_cap_forms()
    if type(k) is not int or k != 48:
        raise ValueError("the cross factor is fixed at 48")
    inner_i, inner_b = Q(inner_i), Q(inner_b)
    if inner_i <= 0:
        raise ArithmeticError("inner I must be positive")
    if type(raw_cross_rows) is not list or len(raw_cross_rows) != len(labels):
        raise ValueError("cross vector dimension mismatch")
    raw_cross = []
    for row, label in zip(raw_cross_rows, labels):
        if type(row) is not list or len(row) != 3 or row[:2] != list(label):
            raise ValueError("cross vector label order mismatch")
        raw_cross.append(staged.strict_q(row[2], "merged raw J cross"))
    dimension = len(labels) + 1
    i_matrix = [[Q(0) for _ in range(dimension)]
                for _ in range(dimension)]
    b_matrix = [[Q(0) for _ in range(dimension)]
                for _ in range(dimension)]
    i_matrix[0][0] = inner_i
    b_matrix[0][0] = inner_b
    for i, value in enumerate(raw_cross, 1):
        # raw_cross is J(inner,C_i); the serialized matrix is 48J. There is
        # no polarization factor in this matrix entry.
        b_matrix[i][0] = b_matrix[0][i] = Q(k) * value
    for i in range(len(labels)):
        for j in range(len(labels)):
            i_matrix[i + 1][j + 1] = cap_i[i][j]
            b_matrix[i + 1][j + 1] = cap_b[i][j]
    if (any(i_matrix[0][i] or i_matrix[i][0]
            for i in range(1, dimension)) or
            any(i_matrix[i][j] != i_matrix[j][i] or
                b_matrix[i][j] != b_matrix[j][i]
                for i in range(dimension) for j in range(dimension))):
        raise ArithmeticError("assembled exact pencil lost block symmetry")
    return i_matrix, b_matrix


def preflight():
    labels, i_matrix, b_matrix = restricted_cap_forms()
    return {
        "status": "PRELAUNCH_CANDIDATE",
        "format": "active25-cap-slack-D16-assembler-preflight-v3",
        "source_sha256": _SELF["sha256"],
        "producer_sha256": PINNED[STAGED],
        "dependency_sha256": dependency_record(),
        "dimension": 1 + len(labels),
        "pilot_labels": [list(label) for label in labels],
        "restricted_I_upper_nonzero": len(_upper_from_dense(i_matrix)),
        "restricted_48J_upper_nonzero": len(_upper_from_dense(b_matrix)),
        "cross_factor": 48,
        "target_started": False,
        "launch_authorized": False,
        "contains_cross_values": False,
        "contains_vector": False,
        "contains_quotient": False,
        "independent_arithmetic_reconstruction": False,
        "independent_reconstruction_required": True,
        "theorem_ready": False,
    }


def _binding(snapshot, path=None):
    result = {key: snapshot[key]
              for key in ("sha256", "device", "inode")}
    if path is not None:
        result["path"] = str(path)
    elif "path" in snapshot:
        result["path"] = snapshot["path"]
    return result


def build_result(context):
    merged = context["manifest"]["merged_cross"]
    i_matrix, b_matrix = assemble_exact_pencil(
        Q(merged["inner_I"]), Q(merged["inner_48J"]),
        merged["raw_J_cross_by_label"])
    record_path = Path(context["record"]["path"])
    result = {
        "format": RESULT_FORMAT,
        "status": "CONDITIONAL_SERIALIZATION_ONLY",
        "assembler_sha256": _SELF["sha256"],
        "producer_sha256": PINNED[STAGED],
        "dependency_sha256": dependency_record(),
        "parameters": staged.pilot.V1.A25.parameter_record(),
        "dimension": len(i_matrix),
        "basis": [["radial_D16"]] +
                 [list(label) for label in staged.pilot.pilot_labels()],
        "I_upper_nonzero": _upper_from_dense(i_matrix),
        "48J_upper_nonzero": _upper_from_dense(b_matrix),
        "raw_J_cross_by_label": merged["raw_J_cross_by_label"],
        "cross_factor_applied_exactly_once": 48,
        "authorization_binding": context["authorization_binding"],
        "ledger_binding": _binding(
            context["ledger_snapshot"], record_path / staged.LEDGER_LEAF),
        "manifest_binding": _binding(
            context["manifest_snapshot"], record_path / staged.MANIFEST_LEAF),
        "stage_bindings": [staged.binding(snapshot)
                           for snapshot in context["stage_snapshots"]],
        "independent_reconstruction_design_sha256":
            staged.PINNED[staged.INDEPENDENT_DESIGN],
        "serialized_stage_arithmetic_conditional": True,
        "independent_arithmetic_reconstruction": False,
        "contains_vector": False,
        "contains_quotient": False,
        "eigenvalue_optimality_rigorous": False,
        "theorem_ready": False,
    }
    strict_result(
        result, context["manifest_snapshot"]["sha256"],
        staged.binding(context["ledger_snapshot"]),
        context["authorization_binding"])
    return result


def strict_result(value, expected_manifest_sha256, expected_ledger,
                  expected_authorization):
    keys = {
        "48J_upper_nonzero", "I_upper_nonzero", "assembler_sha256",
        "authorization_binding", "basis", "contains_quotient",
        "contains_vector", "cross_factor_applied_exactly_once",
        "dependency_sha256", "dimension", "eigenvalue_optimality_rigorous",
        "format", "independent_arithmetic_reconstruction",
        "independent_reconstruction_design_sha256", "ledger_binding",
        "manifest_binding", "parameters", "producer_sha256",
        "raw_J_cross_by_label", "serialized_stage_arithmetic_conditional",
        "stage_bindings", "status", "theorem_ready",
    }
    labels = staged.pilot.pilot_labels()
    dimension = len(labels) + 1
    staged.strict_sha(expected_manifest_sha256, "expected manifest SHA")
    if (type(value) is not dict or set(value) != keys or
            value["format"] != RESULT_FORMAT or
            value["status"] != "CONDITIONAL_SERIALIZATION_ONLY" or
            value["assembler_sha256"] != _SELF["sha256"] or
            value["producer_sha256"] != PINNED[STAGED] or
            value["dependency_sha256"] != dependency_record() or
            value["parameters"] != staged.pilot.V1.A25.parameter_record() or
            value["dimension"] != dimension or
            value["basis"] != [["radial_D16"]] +
            [list(label) for label in labels] or
            value["cross_factor_applied_exactly_once"] != 48 or
            value["independent_reconstruction_design_sha256"] !=
            staged.PINNED[staged.INDEPENDENT_DESIGN] or
            value["serialized_stage_arithmetic_conditional"] is not True or
            value["independent_arithmetic_reconstruction"] is not False or
            value["contains_vector"] is not False or
            value["contains_quotient"] is not False or
            value["eigenvalue_optimality_rigorous"] is not False or
            value["theorem_ready"] is not False):
        raise ValueError("conditional result identity mismatch")
    if (type(expected_ledger) is not dict or set(expected_ledger) != {
            "leaf", "sha256", "device", "inode"} or
            type(expected_authorization) is not dict or
            set(expected_authorization) != {"path", "sha256", "device", "inode"}):
        raise ValueError("external dynamic bindings are malformed")
    ledger = value["ledger_binding"]
    manifest = value["manifest_binding"]
    authorization = value["authorization_binding"]
    for name, row in (("ledger", ledger), ("manifest", manifest),
                      ("authorization", authorization)):
        if (type(row) is not dict or set(row) != {
                "path", "sha256", "device", "inode"} or
                type(row["path"]) is not str or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError(f"conditional {name} binding is malformed")
        staged.strict_sha(row["sha256"], f"conditional {name} SHA")
    if ({key: ledger[key] for key in ("sha256", "device", "inode")} !=
            {key: expected_ledger[key]
             for key in ("sha256", "device", "inode")} or
            manifest["sha256"] != expected_manifest_sha256 or
            authorization != expected_authorization or
            Path(ledger["path"]).name != staged.LEDGER_LEAF or
            Path(manifest["path"]).name != staged.MANIFEST_LEAF or
            Path(ledger["path"]).parent != Path(manifest["path"]).parent):
        raise ValueError("conditional external binding mismatch")
    stage_bindings = value["stage_bindings"]
    if type(stage_bindings) is not list or len(stage_bindings) != 26:
        raise ValueError("conditional stage binding inventory mismatch")
    seen = {(ledger["device"], ledger["inode"]),
            (manifest["device"], manifest["inode"]),
            (authorization["device"], authorization["inode"])}
    for r, row in enumerate(stage_bindings):
        if (type(row) is not dict or set(row) != {
                "leaf", "sha256", "device", "inode"} or
                row["leaf"] != staged.STAGE_LEAVES[r] or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError("conditional stage binding is malformed")
        staged.strict_sha(row["sha256"], "conditional stage SHA")
        inode = (row["device"], row["inode"])
        if inode in seen:
            raise ValueError("conditional dynamic bindings alias")
        seen.add(inode)

    i_entries = _parse_sparse(value["I_upper_nonzero"], dimension, "result I")
    b_entries = _parse_sparse(value["48J_upper_nonzero"], dimension,
                              "result 48J")
    i_matrix = _dense_from_upper(i_entries, dimension)
    b_matrix = _dense_from_upper(b_entries, dimension)
    _, _, _, frozen_inner_i, frozen_inner_b = \
        staged.pilot.V1.A25.load_inner_coordinate()
    if (i_matrix[0][0] != frozen_inner_i or
            b_matrix[0][0] != frozen_inner_b):
        raise ArithmeticError("conditional result changed the fixed D16 identity")
    expected_i, expected_b = assemble_exact_pencil(
        i_matrix[0][0], b_matrix[0][0], value["raw_J_cross_by_label"])
    if i_matrix != expected_i or b_matrix != expected_b:
        raise ArithmeticError("conditional sparse pencil does not reconstruct")
    return True


def _rebind_context(context, expected_manifest_sha256, expected_ledger,
                    expected_authorization_sha256, expected_self_sha256):
    bind_startup_self(expected_self_sha256)
    staged.bind_startup_self(PINNED[STAGED])
    staged.require_leaf_set(context["record"], set(staged.ALLOWED_LEAVES))
    if staged.binding(staged.read_leaf(
            context["record"], staged.LEDGER_LEAF)) != expected_ledger:
        raise RuntimeError("ledger changed during assembly")
    manifest = staged.read_leaf(context["record"], staged.MANIFEST_LEAF)
    if manifest["sha256"] != expected_manifest_sha256:
        raise RuntimeError("manifest changed during assembly")
    if staged._validate_authorization(
            context["authorization"], context["record"]["path"],
            PINNED[STAGED])["sha256"] != expected_authorization_sha256:
        raise RuntimeError("authorization changed during assembly")
    for snapshot in context["stage_snapshots"]:
        if staged.binding(staged.read_leaf(
                context["record"], snapshot["leaf"])) != staged.binding(snapshot):
            raise RuntimeError("stage changed during assembly")


def publish_output(path, payload, context, expected_manifest_sha256,
                   expected_ledger, expected_authorization_sha256,
                   expected_self_sha256):
    target = Path(path)
    parent = staged.open_record_dir(target.parent)
    descriptor = None
    try:
        if ((parent["device"], parent["inode"]) ==
                (context["record"]["device"], context["record"]["inode"])):
            raise ValueError("assembled output aliases the record directory")
        protected = {FILE.resolve(), *(path.resolve() for path in PINNED),
                     *(path.resolve() for path in staged.PINNED)}
        if target.resolve(strict=False) in protected:
            raise ValueError("assembled output aliases a protected input")
        encoded = staged.canonical_json(payload)
        _rebind_context(context, expected_manifest_sha256, expected_ledger,
                        expected_authorization_sha256, expected_self_sha256)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target.name, flags, 0o600,
                             dir_fd=parent["descriptor"])
        offset = 0
        while offset < len(encoded):
            written = os.write(descriptor, encoded[offset:])
            if written <= 0:
                raise OSError("short conditional-result write")
            offset += written
        os.fsync(descriptor)
        os.fsync(parent["descriptor"])
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            raise RuntimeError("conditional output is not singly linked regular data")
        _rebind_context(context, expected_manifest_sha256, expected_ledger,
                        expected_authorization_sha256, expected_self_sha256)
        snapshot = staged.read_leaf(parent, target.name, len(encoded))
        if snapshot["data"] != encoded:
            raise RuntimeError("conditional output bytes changed")
        return snapshot
    finally:
        if descriptor is not None:
            os.close(descriptor)
        staged.close_record_dir(parent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--record-dir", type=Path)
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--expected-authorization-sha256")
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--expected-producer-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expected-ledger-sha256")
    parser.add_argument("--expected-ledger-device", type=int)
    parser.add_argument("--expected-ledger-inode", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        if any(value is not None for key, value in vars(args).items()
               if key != "preflight_only"):
            parser.error("preflight accepts no production binding")
        print(json.dumps(preflight(), sort_keys=True, indent=2))
        return
    required = (args.record_dir, args.authorization_file,
                args.expected_authorization_sha256, args.expected_self_sha256,
                args.expected_producer_sha256, args.expected_manifest_sha256,
                args.expected_ledger_sha256, args.expected_ledger_device,
                args.expected_ledger_inode, args.output)
    if any(value is None for value in required):
        parser.error("conditional assembly requires every external binding")
    bind_startup_self(args.expected_self_sha256)
    if args.expected_producer_sha256 != PINNED[STAGED]:
        raise RuntimeError("externally supplied producer SHA does not match")
    ledger = staged.expected_binding(
        staged.LEDGER_LEAF, args.expected_ledger_sha256,
        args.expected_ledger_device, args.expected_ledger_inode)
    context = staged.open_completed(
        args.record_dir, args.authorization_file,
        args.expected_authorization_sha256, PINNED[STAGED], ledger,
        args.expected_manifest_sha256)
    try:
        result = build_result(context)
        snapshot = publish_output(
            args.output, result, context, args.expected_manifest_sha256,
            ledger, args.expected_authorization_sha256,
            args.expected_self_sha256)
        print(json.dumps({"output_sha256": snapshot["sha256"],
                          "theorem_ready": False}, sort_keys=True))
    finally:
        staged.close_completed(context)


if __name__ == "__main__":
    main()
