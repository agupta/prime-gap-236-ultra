#!/usr/bin/env python3
"""Strict v4 post-run assembler/consumer for the active25 D16 pencil.

The caller must provide the externally recorded SHA-256 of the completed
26-shard manifest.  Every shard byte/inode and all frozen arithmetic inputs
are rebound before exact assembly.  Numerical eigendiscovery is used only to
select a rational vector; its particular I and 48J forms are exact Fractions.
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


FILE = Path(__file__).resolve()
HERE = FILE.parent
REPO = FILE.parents[2]
STAGED = HERE / "frontier_active25_inner_d16_staged_v4.py"
STAGED_TEST = HERE / "test_frontier_active25_inner_d16_staged_v4.py"
PINNED = {
    STAGED: "7d5188ec18ef99ae22aeada193471a69c11cf15363aa26496ef8b3217387beef",
    STAGED_TEST: "4082c32c1358d564f6ed17743c3ccdc471813c67df5a5a3013acd9aa1e227ac0",
}


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
_SPEC = importlib.util.spec_from_file_location("active25_staged_v4_core", STAGED)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(STAGED)
staged = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = staged
_SPEC.loader.exec_module(staged)


def dependency_record():
    result = {str(path.relative_to(REPO)): expected
              for path, expected in PINNED.items()}
    result.update(staged.dependency_record())
    return dict(sorted(result.items()))


def strict_sha(value, name):
    if (type(value) is not str or len(value) != 64 or
            any(c not in "0123456789abcdef" for c in value)):
        raise ValueError(f"{name} is not a canonical SHA-256")
    return value


def load_completed_manifest(record_dir, expected_sha256):
    strict_sha(expected_sha256, "expected manifest SHA")
    handle = staged.open_record_dir(record_dir)
    try:
        staged.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
        ledger_snap = staged.read_leaf(handle, staged.LEDGER_LEAF)
        ledger = staged._parse_ledger_snapshot(handle, ledger_snap,
                                               "production")
        snap = staged.read_leaf(handle, staged.MANIFEST_LEAF)
        if snap["sha256"] != expected_sha256:
            raise ValueError("completed manifest SHA mismatch")
        try:
            manifest = json.loads(snap["data"])
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("completed manifest is not JSON") from error
        if staged.canonical_json(manifest) != snap["data"]:
            raise ValueError("completed manifest is not canonical")
        staged.strict_manifest(manifest, handle, ledger, ledger_snap,
                               "production")
        stages = []
        bindings = []
        for r, row in enumerate(manifest["stages"]):
            stage_snap = staged.read_leaf(handle, row["leaf"])
            if {key: stage_snap[key]
                    for key in ("leaf", "sha256", "device", "inode")} != {
                    key: row[key]
                    for key in ("leaf", "sha256", "device", "inode")}:
                raise RuntimeError("stage changed after manifest validation")
            stages.append(staged.parse_stage_bytes(
                stage_snap["data"], r, ledger,
                staged.ledger_binding(ledger_snap), "production"))
            bindings.append(stage_snap)
        staged.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
        return (handle, ledger_snap, ledger, snap, manifest, stages,
                bindings)
    except Exception:
        staged.close_record_dir(handle)
        raise


def assemble_exact_matrices(inner_i, inner_b, raw_cross, active, masses,
                            shell_b, *, k=48):
    if (type(active) is not list or active != list(range(len(active))) or
            not active or len(raw_cross) <= active[-1] or
            len(masses) <= active[-1] or len(shell_b) <= active[-1]):
        raise ValueError("active shell matrix geometry mismatch")
    if (inner_i <= 0 or any(masses[r] <= 0 for r in active) or
            any(raw_cross[r] != 0 for r in range(active[-1] + 1,
                                                  len(raw_cross)))):
        raise ArithmeticError("invalid exact I/cross support")
    dimension = len(active) + 1
    a_diag = [inner_i] + [masses[r] for r in active]
    b = [[Q(0) for _ in range(dimension)] for _ in range(dimension)]
    b[0][0] = inner_b
    for index, r in enumerate(active, 1):
        # raw_cross is J(inner,C_r), hence the matrix entry is k times it.
        b[0][index] = b[index][0] = k * raw_cross[r]
        for jndex, s in enumerate(active, 1):
            b[index][jndex] = shell_b[r][s]
    if any(b[i][j] != b[j][i]
           for i in range(dimension) for j in range(dimension)):
        raise ArithmeticError("assembled 48J matrix is not symmetric")
    if any(b[i][j] for i in range(1, dimension)
           for j in range(1, dimension) if abs(i - j) > 1):
        raise ArithmeticError("assembled shell block is not tridiagonal")
    return a_diag, b


def exact_quadratic(matrix, vector):
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in range(len(vector)) for j in range(len(vector))), Q(0))


def discovery_and_rationalize(a_diag, b, *, precisions=(100, 160),
                              denominator_limit=10**18):
    solves = [staged.v2.core.shell.decimal_jacobi_diagonal_gram(
        a_diag, b, precision) for precision in precisions]
    with localcontext() as context:
        context.prec = max(precisions) + 20
        q0 = Decimal(solves[0]["rayleigh_quotient"])
        q1 = Decimal(solves[1]["rayleigh_quotient"])
        if abs(q0 - q1) > Decimal("1e-70"):
            raise ArithmeticError("two-precision quotient discovery is unstable")
        if any(Decimal(item["relative_residual_bound"]) > Decimal("1e-70")
               for item in solves):
            raise ArithmeticError("discovery residual exceeds frozen threshold")
    vector = [Q(value).limit_denominator(denominator_limit)
              for value in solves[-1]["vector"]]
    denominator = sum((a_diag[i] * vector[i] * vector[i]
                       for i in range(len(vector))), Q(0))
    numerator = exact_quadratic(b, vector)
    if denominator <= 0:
        raise ArithmeticError("rationalized vector has nonpositive exact I")
    return solves, vector, denominator, numerator


def build_result(record_dir, expected_manifest_sha256):
    self_start = FILE.read_bytes()
    dep_start = snapshots()
    staged_start = staged.snapshots()
    core_start = staged.v2.core.require_pins()
    (handle, ledger_snap, ledger, manifest_snap, manifest, stages,
     bindings) = \
        load_completed_manifest(record_dir, expected_manifest_sha256)
    try:
        shards = [value["shard"] for value in stages]
        raw_cross, identity = staged.v2.merge_exact_shards(shards)
        if identity is None:
            raise ArithmeticError("missing exact inner identity")
        inner_i, inner_b, inner_dimension = identity
        if inner_dimension != 307:
            raise ValueError("unexpected D16 inner dimension")
        active, masses, shell_b, shell_counts = \
            staged.v2.core.shell_i_and_j()
        if active != list(range(26)):
            raise ArithmeticError("shell active set changed")
        a_diag, b = assemble_exact_matrices(
            inner_i, inner_b, raw_cross, active, masses, shell_b)
        solves, vector, denominator, numerator = discovery_and_rationalize(
            a_diag, b)
        result = {
            "I_diagonal": [str(x) for x in a_diag],
            "assembler_sha256": sha256_bytes(self_start),
            "dependency_sha256": dependency_record(),
            "dimension": 27,
            "eigenvalue_optimality_rigorous": False,
            "exact_margin": str(numerator - denominator),
            "exact_quotient": str(numerator / denominator),
            "exact_rational_denominator": str(denominator),
            "exact_rational_numerator": str(numerator),
            "finite_space_crosses_one": numerator > denominator,
            "format": "frontier-active25-inner-D16-exact-pencil-v4",
            "ledger_binding": {
                "device": ledger_snap["device"],
                "inode": ledger_snap["inode"],
                "path": str(Path(handle["path"]) / staged.LEDGER_LEAF),
                "sha256": ledger_snap["sha256"],
            },
            "manifest_binding": {
                "device": manifest_snap["device"],
                "inode": manifest_snap["inode"],
                "path": str(Path(handle["path"]) / staged.MANIFEST_LEAF),
                "sha256": manifest_snap["sha256"],
            },
            "parameters": staged.v2.core.parameter_record(),
            "precision_discovery": solves,
            "rational_denominator_limit": 10**18,
            "rational_vector": [str(x) for x in vector],
            "shell_domain_counts": shell_counts,
            "stage_bindings": [{key: snap[key]
                                for key in ("leaf", "sha256", "device", "inode")}
                               for snap in bindings],
            "status": "complete",
            "theorem_ready": False,
            "two_precision_gate": {
                "precisions": [100, 160],
                "quotient_absolute_tolerance": "1e-70",
                "relative_residual_maximum": "1e-70",
            },
            "48J_matrix": [[str(x) for x in row] for row in b],
        }
        # Rebind all dynamic and static inputs after the exact contraction.
        manifest_after = staged.read_leaf(handle, staged.MANIFEST_LEAF)
        if {key: manifest_after[key]
                for key in ("sha256", "device", "inode")} != {
                key: manifest_snap[key]
                for key in ("sha256", "device", "inode")}:
            raise RuntimeError("manifest changed during exact assembly")
        staged.strict_manifest(manifest, handle, ledger, ledger_snap,
                               "production")
        for row, old in zip(manifest["stages"], bindings):
            new = staged.read_leaf(handle, row["leaf"])
            if {key: new[key] for key in ("sha256", "device", "inode")} != {
                    key: old[key] for key in ("sha256", "device", "inode")}:
                raise RuntimeError("stage changed during exact assembly")
        staged.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
        ledger_after = staged.read_leaf(handle, staged.LEDGER_LEAF)
        if {key: ledger_after[key] for key in ("sha256", "device", "inode")} != {
                key: ledger_snap[key] for key in ("sha256", "device", "inode")}:
            raise RuntimeError("immutable ledger changed during assembly")
        if (FILE.read_bytes() != self_start or snapshots() != dep_start or
                staged.snapshots() != staged_start or
                staged.v2.core.require_pins() != core_start):
            raise RuntimeError("assembler closure changed")
        return result
    finally:
        staged.close_record_dir(handle)


def strict_result(value, expected_manifest_sha256):
    if type(value) is not dict or set(value) != {
            "I_diagonal", "assembler_sha256", "dependency_sha256",
            "dimension", "eigenvalue_optimality_rigorous", "exact_margin",
            "exact_quotient", "exact_rational_denominator",
            "exact_rational_numerator", "finite_space_crosses_one", "format",
            "ledger_binding", "manifest_binding", "parameters", "precision_discovery",
            "rational_denominator_limit", "rational_vector",
            "shell_domain_counts", "stage_bindings", "status",
            "theorem_ready", "two_precision_gate", "48J_matrix"}:
        raise ValueError("assembled result schema mismatch")
    binding = value["manifest_binding"]
    ledger_binding = value["ledger_binding"]
    stage_bindings = value["stage_bindings"]
    gate = value["two_precision_gate"]
    solves = value["precision_discovery"]
    counts = value["shell_domain_counts"]
    if type(ledger_binding) is dict:
        strict_sha(ledger_binding.get("sha256"), "ledger binding SHA")
    if type(binding) is dict:
        strict_sha(binding.get("sha256"), "manifest binding SHA")
    if (value["assembler_sha256"] != sha256(FILE) or
            value["dependency_sha256"] != dependency_record() or
            value["dimension"] != 27 or
            value["eigenvalue_optimality_rigorous"] is not False or
            value["format"] !=
            "frontier-active25-inner-D16-exact-pencil-v4" or
            type(ledger_binding) is not dict or set(ledger_binding) != {
                "device", "inode", "path", "sha256"} or
            type(ledger_binding["path"]) is not str or
            not ledger_binding["path"].endswith("/" + staged.LEDGER_LEAF) or
            type(ledger_binding["device"]) is not int or
            ledger_binding["device"] < 0 or
            type(ledger_binding["inode"]) is not int or
            ledger_binding["inode"] < 0 or
            type(binding) is not dict or set(binding) != {
                "device", "inode", "path", "sha256"} or
            binding["sha256"] != expected_manifest_sha256 or
            type(binding["path"]) is not str or
            not binding["path"].endswith("/" + staged.MANIFEST_LEAF) or
            type(binding["device"]) is not int or binding["device"] < 0 or
            type(binding["inode"]) is not int or binding["inode"] < 0 or
            str(Path(ledger_binding["path"]).parent) !=
            str(Path(binding["path"]).parent) or
            (ledger_binding["device"], ledger_binding["inode"]) ==
            (binding["device"], binding["inode"]) or
            value["parameters"] != staged.v2.core.parameter_record() or
            value["rational_denominator_limit"] != 10**18 or
            type(counts) is not dict or set(counts) != {"hh", "hl", "ll"} or
            any(type(x) is not int or x < 0 for x in counts.values()) or
            type(stage_bindings) is not list or len(stage_bindings) != 26 or
            type(gate) is not dict or gate != {
                "precisions": [100, 160],
                "quotient_absolute_tolerance": "1e-70",
                "relative_residual_maximum": "1e-70",
            } or
            type(solves) is not list or len(solves) != 2 or
            value["status"] != "complete" or
            value["theorem_ready"] is not False):
        raise ValueError("assembled result identity mismatch")
    seen_inodes = {(ledger_binding["device"], ledger_binding["inode"]),
                   (binding["device"], binding["inode"])}
    for r, row in enumerate(stage_bindings):
        if (type(row) is not dict or set(row) != {
                "leaf", "sha256", "device", "inode"} or
                row["leaf"] != staged.STAGE_LEAVES[r] or
                type(row["sha256"]) is not str or
                len(row["sha256"]) != 64 or
                any(c not in "0123456789abcdef" for c in row["sha256"]) or
                type(row["device"]) is not int or row["device"] < 0 or
                type(row["inode"]) is not int or row["inode"] < 0):
            raise ValueError("assembled stage binding is malformed")
        inode_key = (row["device"], row["inode"])
        if inode_key in seen_inodes:
            raise ValueError("assembled dynamic inputs are not inode-distinct")
        seen_inodes.add(inode_key)
    for expected_precision, solve in zip((100, 160), solves):
        if (type(solve) is not dict or set(solve) != {
                "precision", "eigenvalue", "rayleigh_quotient",
                "relative_residual_bound", "jacobi_rotations", "vector"} or
                solve["precision"] != expected_precision or
                type(solve["precision"]) is not int or
                type(solve["jacobi_rotations"]) is not int or
                solve["jacobi_rotations"] < 0 or
                type(solve["vector"]) is not list or
                len(solve["vector"]) != 27 or
                any(type(x) is not str or not Decimal(x).is_finite()
                    for x in (solve["eigenvalue"],
                              solve["rayleigh_quotient"],
                              solve["relative_residual_bound"],
                              *solve["vector"]))):
            raise ValueError("precision discovery record is malformed")
    with localcontext() as context:
        context.prec = 180
        if (abs(Decimal(solves[0]["rayleigh_quotient"]) -
                Decimal(solves[1]["rayleigh_quotient"])) > Decimal("1e-70") or
                any(Decimal(solve["relative_residual_bound"]) >
                    Decimal("1e-70") or
                    Decimal(solve["relative_residual_bound"]) < 0
                    for solve in solves)):
            raise ValueError("serialized precision gate failed")
    a = [Q(x) for x in value["I_diagonal"]]
    b = [[Q(x) for x in row] for row in value["48J_matrix"]]
    vector = [Q(x) for x in value["rational_vector"]]
    scalar_fraction_fields = (
        "exact_margin", "exact_quotient", "exact_rational_denominator",
        "exact_rational_numerator")
    if (any(type(value[key]) is not str or str(Q(value[key])) != value[key]
            for key in scalar_fraction_fields) or
            len(a) != 27 or len(b) != 27 or any(len(row) != 27 for row in b) or
            len(vector) != 27 or
            any(str(x) != raw for x, raw in zip(a, value["I_diagonal"])) or
            any(str(b[i][j]) != value["48J_matrix"][i][j]
                for i in range(27) for j in range(27)) or
            any(str(x) != raw for x, raw in zip(vector,
                                                value["rational_vector"])) or
            any(x <= 0 for x in a) or
            any(b[i][j] != b[j][i] for i in range(27) for j in range(27)) or
            any(b[i][j] for i in range(1, 27) for j in range(1, 27)
                if abs(i - j) > 1)):
        raise ValueError("assembled result contains a noncanonical form")
    denominator = sum((a[i] * vector[i] * vector[i]
                       for i in range(27)), Q(0))
    numerator = exact_quadratic(b, vector)
    if (denominator <= 0 or
            str(denominator) != value["exact_rational_denominator"] or
            str(numerator) != value["exact_rational_numerator"] or
            str(numerator / denominator) != value["exact_quotient"] or
            str(numerator - denominator) != value["exact_margin"] or
            value["finite_space_crosses_one"] is not
            (numerator > denominator)):
        raise ValueError("assembled exact contraction mismatch")
    return True


def read_external_file(path, expected_sha256):
    strict_sha(expected_sha256, "expected result SHA")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(Path(path).resolve(strict=True), flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("assembled result is not regular")
        chunks = []
        while True:
            block = os.read(descriptor, 1_048_576)
            if not block:
                break
            chunks.append(block)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if ((before.st_dev, before.st_ino, before.st_size,
             before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns) or
                len(data) != after.st_size):
            raise RuntimeError("assembled result changed during read")
    finally:
        os.close(descriptor)
    if sha256_bytes(data) != expected_sha256:
        raise ValueError("assembled result SHA mismatch")
    value = json.loads(data)
    if staged.canonical_json(value) != data:
        raise ValueError("assembled result is not canonical")
    return value


def _rebind_manifest_handle(handle, expected_manifest_sha256):
    staged.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
    ledger_snap = staged.read_leaf(handle, staged.LEDGER_LEAF)
    ledger = staged._parse_ledger_snapshot(handle, ledger_snap, "production")
    snap = staged.read_leaf(handle, staged.MANIFEST_LEAF)
    if snap["sha256"] != expected_manifest_sha256:
        raise RuntimeError("stage manifest changed before publication")
    value = json.loads(snap["data"])
    if staged.canonical_json(value) != snap["data"]:
        raise ValueError("stage manifest ceased to be canonical")
    staged.strict_manifest(value, handle, ledger, ledger_snap, "production")
    staged.require_leaf_set(handle, set(staged.ALLOWED_LEAVES))
    return snap


def _hash_descriptor(descriptor):
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while True:
        block = os.read(descriptor, 1_048_576)
        if not block:
            break
        digest.update(block)
    os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest()


def publish_output(path, payload, record_dir, expected_manifest_sha256):
    output = Path(path)
    output_parent = staged.open_record_dir(output.parent)
    record = staged.open_record_dir(record_dir)
    descriptor = None
    try:
        if ((output_parent["device"], output_parent["inode"]) ==
                (record["device"], record["inode"])):
            raise ValueError("assembled output aliases the stage directory")
        if output.resolve(strict=False) in {FILE, *PINNED}:
            raise ValueError("assembled output aliases a frozen input")
        encoded = staged.canonical_json(payload)
        digest = sha256_bytes(encoded)
        _rebind_manifest_handle(record, expected_manifest_sha256)
        static_before = snapshots()
        staged_before = staged.snapshots()
        core_before = staged.v2.core.require_pins()
        self_before = FILE.read_bytes()
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(output.name, flags, 0o600,
                             dir_fd=output_parent["descriptor"])
        position = 0
        while position < len(encoded):
            count = os.write(descriptor, encoded[position:])
            if count <= 0:
                raise OSError("short output write")
            position += count
        os.fsync(descriptor)
        os.fsync(output_parent["descriptor"])
        owned = os.fstat(descriptor)
        rebound = staged.read_leaf(output_parent, output.name,
                                   maximum_bytes=len(encoded))
        if (_hash_descriptor(descriptor) != digest or
                rebound["sha256"] != digest or
                (rebound["device"], rebound["inode"]) !=
                (int(owned.st_dev), int(owned.st_ino))):
            raise RuntimeError("assembled output entry was replaced")
        _rebind_manifest_handle(record, expected_manifest_sha256)
        if (snapshots() != static_before or staged.snapshots() != staged_before or
                staged.v2.core.require_pins() != core_before or
                FILE.read_bytes() != self_before):
            raise RuntimeError("assembler closure changed during publication")
        rebound = staged.read_leaf(output_parent, output.name,
                                   maximum_bytes=len(encoded))
        if (rebound["sha256"] != digest or
                (rebound["device"], rebound["inode"]) !=
                (int(owned.st_dev), int(owned.st_ino))):
            raise RuntimeError("assembled output changed after final rebind")
        os.fsync(output_parent["descriptor"])
        os.close(descriptor)
        descriptor = None
        return rebound
    except Exception:
        if descriptor is not None:
            rejection = b'{"status":"rejected-incomplete-active25-assembly"}\n'
            try:
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.ftruncate(descriptor, 0)
                os.write(descriptor, rejection)
                os.fsync(descriptor)
                os.fsync(output_parent["descriptor"])
            finally:
                os.close(descriptor)
                descriptor = None
        raise
    finally:
        staged.close_record_dir(record)
        staged.close_record_dir(output_parent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-output", type=Path)
    parser.add_argument("--expected-output-sha256")
    args = parser.parse_args()
    if (args.output is None) == (args.verify_output is None):
        parser.error("choose exactly one of --output or --verify-output")
    if args.output is not None:
        if args.expected_output_sha256 is not None:
            parser.error("assembly does not accept an expected output SHA")
        result = build_result(args.record_dir,
                              args.expected_manifest_sha256)
        strict_result(result, args.expected_manifest_sha256)
        snap = publish_output(args.output, result, args.record_dir,
                              args.expected_manifest_sha256)
        print(json.dumps({"output_sha256": snap["sha256"]}, sort_keys=True))
        return
    if args.expected_output_sha256 is None:
        parser.error("verification requires --expected-output-sha256")
    value = read_external_file(args.verify_output,
                               args.expected_output_sha256)
    strict_result(value, args.expected_manifest_sha256)
    rebuilt = build_result(args.record_dir,
                           args.expected_manifest_sha256)
    if staged.canonical_json(rebuilt) != staged.canonical_json(value):
        raise RuntimeError("assembled result differs from fresh reconstruction")
    print(json.dumps({"status": "PASS",
                      "output_sha256": args.expected_output_sha256},
                     sort_keys=True))


if __name__ == "__main__":
    main()
