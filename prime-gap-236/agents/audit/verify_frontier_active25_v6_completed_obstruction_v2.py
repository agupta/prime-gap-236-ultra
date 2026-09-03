#!/usr/bin/env python3
"""Outcome-neutral exact review of the completed active25 D16 v6 pencil.

The frozen v1 checker implements the positive-certificate-only prelaunch
design.  The completed attempt instead reports a negative exact margin.  This
successor preserves v1 byte-for-byte as a pinned reconstruction engine, runs
the same fresh 26-shard and four-ordered-shell reconstruction before parsing
any producer stage or candidate arithmetic, and changes only the terminal
mathematical question:

* serialized forms, scalars, and the sign flag must equal the fresh result;
* for a non-crossing result, an exact no-pivot LDL^T factorization of
  diag(I)-48J must have 27 strictly positive pivots.

The latter proves that every nonzero vector in this 27-dimensional space has
Rayleigh quotient strictly below one.  It is a finite-space obstruction only;
``theorem_ready`` deliberately remains false.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

RAW_FILE = Path(__file__).absolute()
FILE = RAW_FILE.resolve(strict=True)
REPO = FILE.parents[2]
ENGINE_FILE = REPO / "agents/audit/verify_frontier_active25_v6_completed.py"
ENGINE_SHA256 = (
    "6f73b06cf2c494b271a2ce169a00b9324b1ef1f41b224903c6c969bc7edeaa66"
)
REJECTION_SENTINEL = b'{"status":"REJECTED"}\n'


class ObstructionFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ObstructionFailure(message)


def _identity(info):
    return (int(info.st_dev), int(info.st_ino), int(info.st_size),
            int(info.st_mtime_ns), int(info.st_ctime_ns), int(info.st_nlink))


def _load_pinned_engine():
    """Compile the exact held v1 bytes; never trust a second pathname read."""
    try:
        raw = os.lstat(ENGINE_FILE)
    except OSError as error:
        raise ObstructionFailure("cannot lstat frozen v1 engine") from error
    require(stat.S_ISREG(raw.st_mode) and not stat.S_ISLNK(raw.st_mode),
            "frozen v1 engine is not a regular nonsymlink file")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(ENGINE_FILE, flags)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                "frozen v1 engine is not singly linked")
        parts = []
        remaining = 4_000_001
        while remaining:
            block = os.read(descriptor, min(1_048_576, remaining))
            if not block:
                break
            parts.append(block)
            remaining -= len(block)
        source = b"".join(parts)
        after = os.fstat(descriptor)
        require(len(source) <= 4_000_000 and
                _identity(before) == _identity(after) and
                len(source) == after.st_size,
                "frozen v1 engine changed while read")
        require(hashlib.sha256(source).hexdigest() == ENGINE_SHA256,
                "frozen v1 engine SHA-256 mismatch")
        module = types.ModuleType("_active25_completed_v1_engine")
        module.__file__ = str(ENGINE_FILE)
        module.__package__ = None
        module.__spec__ = None
        exec(compile(source, str(ENGINE_FILE), "exec"), module.__dict__)
        require(module._SELF["sha256"] == ENGINE_SHA256 and
                (module._SELF["device"], module._SELF["inode"],
                 module._SELF["size"], module._SELF["mtime_ns"],
                 module._SELF["ctime_ns"], module._SELF["nlink"]) ==
                _identity(before),
                "executed v1 engine is not the held pinned file")
        module._rebind_file(module._SELF)
        return module
    finally:
        os.close(descriptor)


E = _load_pinned_engine()
require(not stat.S_ISLNK(os.lstat(RAW_FILE).st_mode),
        "v2 checker must not be launched through a symlink")
_SELF = E._open_file(FILE, 4_000_000)


def _bind_startup_self(expected_sha256):
    expected_sha256 = E.strict_sha(expected_sha256, "expected v2 checker SHA")
    require(_SELF["sha256"] == expected_sha256,
            "v2 checker self SHA does not match external pin")
    E._rebind_file(_SELF)
    E._rebind_file(E._SELF)
    return _SELF["bytes"]


def canonical_json(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ObstructionFailure("value is not canonical ASCII JSON") from error


def exact_ldlt_obstruction(a_diag, b_matrix):
    """Return an exact LDL^T certificate for diag(a_diag)-b_matrix."""
    n = len(a_diag)
    require(n > 0 and len(b_matrix) == n and
            all(len(row) == n for row in b_matrix) and
            all(isinstance(value, Q) for value in a_diag) and
            all(isinstance(value, Q)
                for row in b_matrix for value in row),
            "LDL input forms are malformed")
    matrix = [[(a_diag[i] if i == j else Q(0)) - b_matrix[i][j]
               for j in range(n)] for i in range(n)]
    require(all(matrix[i][j] == matrix[j][i]
                for i in range(n) for j in range(n)),
            "LDL matrix is not symmetric")

    lower = [[Q(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for j in range(n):
        pivot = matrix[j][j] - sum(
            (lower[j][k] * lower[j][k] * pivots[k]
             for k in range(j)), Q(0))
        require(pivot != 0, f"zero exact LDL pivot at index {j}")
        pivots.append(pivot)
        for i in range(j + 1, n):
            residual = matrix[i][j] - sum(
                (lower[i][k] * lower[j][k] * pivots[k]
                 for k in range(j)), Q(0))
            lower[i][j] = residual / pivot

    reconstructed = [[sum(
        (lower[i][k] * pivots[k] * lower[j][k]
         for k in range(n)), Q(0))
        for j in range(n)] for i in range(n)]
    require(reconstructed == matrix, "exact LDL reconstruction identity failed")
    signs = [1 if pivot > 0 else -1 for pivot in pivots]
    require(all(sign == 1 for sign in signs),
            "diag(I)-48J is not positive definite by exact LDL")
    minimum = min(pivots)
    minimum_index = pivots.index(minimum)
    pivot_strings = [str(pivot) for pivot in pivots]
    pivot_bytes = canonical_json(pivot_strings)
    lower_bytes = canonical_json(
        [[str(value) for value in row] for row in lower])
    return {
        "all_pivots_positive": True,
        "dimension": n,
        "factorization": "no-pivot exact Fraction LDL^T",
        "factorization_identity_verified": True,
        "matrix": "diag(I_diagonal)-48J_matrix",
        "minimum_pivot": str(minimum),
        "minimum_pivot_index": minimum_index,
        "pivot_count": n,
        "pivot_list": pivot_strings,
        "pivot_list_canonical_sha256": hashlib.sha256(pivot_bytes).hexdigest(),
        "pivot_signs": signs,
        "unit_lower_canonical_sha256": hashlib.sha256(lower_bytes).hexdigest(),
    }


def _strict_candidate_outcome(value, candidate_snapshot, record_directory,
                              ledger_snapshot, manifest_snapshot,
                              authorization, authorization_snapshot,
                              producer_dependency, stage_snapshots,
                              fresh_a, fresh_b, fresh_shell_counts):
    """Run every v1 check, replacing only its precommitted positive sign."""
    original_require = E.require

    def outcome_require(condition, message):
        if message == "candidate exact rational vector does not cross one":
            return
        original_require(condition, message)

    E.require = outcome_require
    try:
        vector, denominator, numerator, margin = E._strict_candidate(
            value, candidate_snapshot, record_directory, ledger_snapshot,
            manifest_snapshot, authorization, authorization_snapshot,
            producer_dependency, stage_snapshots, fresh_a, fresh_b,
            fresh_shell_counts)
    finally:
        E.require = original_require
    crosses = margin > 0
    original_require(type(value["finite_space_crosses_one"]) is bool and
                     value["finite_space_crosses_one"] is crosses,
                     "candidate crossing flag differs from exact margin sign")
    original_require(margin != 0,
                     "candidate exact margin is zero and has no strict outcome")
    obstruction = None
    if not crosses:
        obstruction = exact_ldlt_obstruction(fresh_a, fresh_b)
    return vector, denominator, numerator, margin, crosses, obstruction


def _load_low_level_core_v2(sources):
    """Apply v1's local-module scan with this pinned successor as self."""
    engine_file = E.FILE
    E.FILE = FILE
    try:
        return E._load_low_level_core(sources)
    finally:
        E.FILE = engine_file


def _make_production_entry():
    token = object()
    direct_module = (__name__ == "__main__" and __spec__ is None)

    def cli_capability(expected_self_sha256):
        _bind_startup_self(expected_self_sha256)
        require(sys.flags.isolated and direct_module and
                Path(sys.argv[0]).resolve(strict=True) == FILE,
                "v2 reconstruction requires fresh isolated direct CLI")
        return token

    def invoke(args, capability):
        require(capability is token, "v2 production capability absent")
        self_start = _bind_startup_self(args.expected_self_sha256)
        record = None
        candidate_parent = None
        record_snapshots = {}
        candidate_snapshot = None
        authorization_snapshot = None
        sources = {}
        try:
            record = E._open_directory(args.record_dir)
            E.require_exact_leaf_set(record, E.ALLOWED_LEAVES)
            for leaf in E.ALLOWED_LEAVES:
                limit = (2_000_000 if leaf == E.LEDGER_LEAF else
                         16_000_000)
                expected = (args.expected_manifest_sha256
                            if leaf == E.MANIFEST_LEAF else None)
                record_snapshots[leaf] = E._open_leaf(
                    record, leaf, limit, expected_sha256=expected)
            candidate_parent, candidate_snapshot = E._open_external_candidate(
                args.candidate, args.expected_candidate_sha256)
            require(Path(candidate_parent["path"]) ==
                    Path(record["path"]).parent,
                    "candidate directory is not the producer-record parent")
            authorization_leaf = (
                Path(record["path"]).name + ".root-authorization.json")
            authorization_snapshot = E._open_leaf(
                candidate_parent, authorization_leaf, 100_000)
            authorization_snapshot["path"] = str(
                Path(candidate_parent["path"]) / authorization_leaf)
            output_path = Path(args.output).absolute()
            require(output_path != Path(candidate_snapshot["path"]) and
                    output_path.parent != Path(record["path"]) and
                    (args._output_directory_binding["device"],
                     args._output_directory_binding["inode"]) !=
                    (record["device"], record["inode"]) and
                    output_path not in {FILE, E.FILE, *E.STATIC_PINS},
                    "output aliases a protected input path")
            require((record["device"], record["inode"]) !=
                    (candidate_parent["device"], candidate_parent["inode"]),
                    "candidate parent aliases producer record directory")
            dynamic_inodes = set()
            for snapshot in (*record_snapshots.values(), candidate_snapshot,
                             authorization_snapshot):
                identity = (snapshot["device"], snapshot["inode"])
                require(identity not in dynamic_inodes,
                        "producer/candidate dynamic files alias")
                dynamic_inodes.add(identity)

            ledger_snapshot = record_snapshots[E.LEDGER_LEAF]
            ledger = E.strict_json_bytes(
                ledger_snapshot["bytes"], "ledger", canonical=True)
            authorization, dependency = E._strict_ledger(
                ledger, record, ledger_snapshot)
            require(E._snapshot_binding(authorization_snapshot) == authorization,
                    "ledger authorization inode/hash binding mismatch")
            authorization_value = E.strict_json_bytes(
                authorization_snapshot["bytes"], "root launch authorization",
                canonical=True)
            E._strict_authorization_file(
                authorization_value, record, authorization_snapshot)
            ledger_binding = E._snapshot_binding(
                ledger_snapshot, include_leaf=True)
            sources = E._snapshot_source_closure(dependency)
            E._validate_declared_sources(dependency, sources, "producer")
            require(all((snapshot["device"], snapshot["inode"])
                        not in dynamic_inodes for snapshot in sources.values()),
                    "dynamic input aliases a static source")
            E._validate_frozen_oracles(sources)
            E._validate_analytic_artifact(sources)
            core = _load_low_level_core_v2(sources)
            basis, vector, amplitudes, inner_i, inner_b = \
                E._parse_inner_coordinate(sources)
            require(tuple(core.ei.even_basis(16)) == basis,
                    "D16 certificate basis differs from fresh even D16 basis")
            named, catalog, weights, high, low = \
                E._construct_named_cross_inputs(
                    core, basis, vector, amplitudes)

            fresh_vectors = []
            expected_shards = []
            for r in E.ACTIVE:
                again = E._parse_inner_coordinate(sources)
                require(again == (basis, vector, amplitudes, inner_i, inner_b),
                        f"inner coordinate changed before fresh shard {r}")
                fresh, expected = E._reconstruct_cross_expected(
                    core, named, catalog, weights, r, inner_i, inner_b)
                fresh_vectors.append(fresh)
                expected_shards.append(expected)
            merged = tuple(sum(
                (fresh_vectors[r][s] for r in E.ACTIVE), Q(0))
                for s in range(E.K + 1))
            require(all(value == 0 for value in merged[len(E.ACTIVE):]),
                    "fresh merged cross has inactive-count tail")

            masses, shell_48j, shell_counts = E._reconstruct_shell(
                core, high, low)
            fresh_a, fresh_b = E.assemble_fresh_forms(
                inner_i, inner_b, merged, masses, shell_48j)

            # No stage or candidate arithmetic is parsed above this line.
            stage_timing = []
            for r, expected in enumerate(expected_shards):
                stage = E.strict_json_bytes(
                    record_snapshots[E.STAGE_LEAVES[r]]["bytes"],
                    f"stage {r}", canonical=True)
                stage_timing.append(E._strict_stage(
                    stage, r, ledger, ledger_binding, authorization,
                    dependency, expected))

            manifest_snapshot = record_snapshots[E.MANIFEST_LEAF]
            manifest = E.strict_json_bytes(
                manifest_snapshot["bytes"], "manifest", canonical=True)
            manifest_seen = E._strict_manifest(
                manifest, record, ledger, ledger_snapshot, authorization,
                dependency,
                [record_snapshots[leaf] for leaf in E.STAGE_LEAVES],
                stage_timing, merged)
            require((manifest_snapshot["device"], manifest_snapshot["inode"])
                    not in manifest_seen, "manifest aliases ledger or stage")

            candidate = E.strict_json_bytes(
                candidate_snapshot["bytes"], "candidate", canonical=True)
            candidate_dependency = candidate.get("dependency_sha256")
            E._validate_declared_sources(
                candidate_dependency, sources, "candidate")
            (rational_vector, denominator, numerator, margin, crosses,
             obstruction) = _strict_candidate_outcome(
                candidate, candidate_snapshot, record, ledger_snapshot,
                manifest_snapshot, authorization, authorization_snapshot,
                dependency,
                [record_snapshots[leaf] for leaf in E.STAGE_LEAVES],
                fresh_a, fresh_b, shell_counts)
            require(crosses or obstruction is not None,
                    "strict candidate outcome has no certificate")

            forms_bytes = canonical_json({
                "48J_matrix": [
                    [str(value) for value in row] for row in fresh_b],
                "I_diagonal": [str(value) for value in fresh_a],
            })
            result = {
                "authorization_binding": {
                    "device": authorization_snapshot["device"],
                    "inode": authorization_snapshot["inode"],
                    "path": authorization_snapshot["path"],
                    "sha256": authorization_snapshot["sha256"],
                },
                "candidate_binding": {
                    "device": candidate_snapshot["device"],
                    "inode": candidate_snapshot["inode"],
                    "path": candidate_snapshot["path"],
                    "sha256": candidate_snapshot["sha256"],
                },
                "checker_sha256": _SELF["sha256"],
                "design_mismatch": (
                    "frozen design requires positive margin; completed target "
                    "has an exact negative margin, so this outcome-neutral "
                    "successor certifies reproducibility and obstruction"),
                "design_sha256": E.STATIC_PINS[E.DESIGN],
                "exact_margin": str(margin),
                "exact_quotient": str(numerator / denominator),
                "exact_rational_denominator": str(denominator),
                "exact_rational_numerator": str(numerator),
                "finite_space_crosses_one": crosses,
                "finite_space_strictly_below_one": (
                    not crosses and obstruction is not None),
                "fresh_forms_sha256": hashlib.sha256(forms_bytes).hexdigest(),
                "independent_arithmetic_reconstruction": True,
                "ldlt_obstruction": obstruction,
                "ledger_binding": {
                    "device": ledger_snapshot["device"],
                    "inode": ledger_snapshot["inode"],
                    "path": str(Path(record["path"]) / E.LEDGER_LEAF),
                    "sha256": ledger_snapshot["sha256"],
                },
                "manifest_binding": {
                    "device": manifest_snapshot["device"],
                    "inode": manifest_snapshot["inode"],
                    "path": str(Path(record["path"]) / E.MANIFEST_LEAF),
                    "sha256": manifest_snapshot["sha256"],
                },
                "outcome_neutral_successor": True,
                "particular_vector_sha256": hashlib.sha256(canonical_json(
                    [str(value) for value in rational_vector])).hexdigest(),
                "positive_only_engine_sha256": ENGINE_SHA256,
                "producer_driver_sha256": E.PRODUCER_SHA256,
                "record_directory": {
                    key: record[key] for key in ("path", "device", "inode")
                },
                "reconstructed_common_counts": list(E.ACTIVE),
                "scope": (
                    "fresh exact 26-shard and four-ordered-shell 27D "
                    "reconstruction plus exact finite-space LDL obstruction; "
                    "no claim outside this 27D space and no sieve theorem claim"),
                "shell_domain_counts": shell_counts,
                "source_sha256": E._source_result_map(sources),
                "stage_bindings": [
                    E._snapshot_binding(
                        record_snapshots[leaf], include_leaf=True)
                    for leaf in E.STAGE_LEAVES
                ],
                "status": (
                    "INDEPENDENT ARITHMETIC RECONSTRUCTION AND EXACT "
                    "FINITE-SPACE OBSTRUCTION PASS"),
                "theorem_ready": False,
            }
            payload = canonical_json(result)
            E._rebind_source_closure(sources)
            E._dynamic_rebind(record, record_snapshots, candidate_parent,
                              candidate_snapshot, authorization_snapshot)
            E._rebind_file(E._SELF)
            require(_bind_startup_self(args.expected_self_sha256) == self_start,
                    "v2 checker source changed during reconstruction")
            return payload
        finally:
            E._close_snapshots(sources.values())
            E._close_snapshots(record_snapshots.values())
            E._close_snapshots([candidate_snapshot, authorization_snapshot])
            E._close_snapshots([record, candidate_parent])

    return invoke, cli_capability


_PRODUCTION_INVOKE, _CLI_CAPABILITY = _make_production_entry()


def _parser():
    parser = argparse.ArgumentParser(
        description="outcome-neutral fresh active25 D16 v6 obstruction audit")
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--record-dir", required=True, type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main():
    args = _parser().parse_args()
    output = E._prepare_output(args.output)
    args._output_directory_binding = {
        key: output["directory"][key] for key in ("path", "device", "inode")
    }
    try:
        E.strict_sha(args.expected_self_sha256, "expected v2 checker self SHA")
        E.strict_sha(args.expected_manifest_sha256, "expected manifest SHA")
        E.strict_sha(args.expected_candidate_sha256, "expected candidate SHA")
        capability = _CLI_CAPABILITY(args.expected_self_sha256)
        result = _PRODUCTION_INVOKE(args, capability)
        E._publish_output(output, result)
        sys.stdout.buffer.write(result)
        sys.stdout.buffer.flush()
        return 0
    except (Exception, KeyboardInterrupt):
        if not output["published"]:
            try:
                E._publish_output(output, REJECTION_SENTINEL)
            except Exception:
                pass
        sys.stderr.write("REJECTED\n")
        return 1
    finally:
        E._close_snapshots([output["directory"]])


if __name__ == "__main__":
    raise SystemExit(main())
