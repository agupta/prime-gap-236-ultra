#!/usr/bin/env python3
"""Independent exact reconstruction of the active25 outer-B4 I block."""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
SOURCE = REPO / "agents/structural-basis/code/active25_outer_b4_i_block_v2.py"
TEST = REPO / "agents/structural-basis/tests/test_active25_outer_b4_i_block_v2.py"
SPEC = REPO / "agents/structural-basis/ACTIVE25-OUTER-B4-I-BLOCK-V2.md"
ARTIFACT = REPO / "agents/structural-basis/results/active25_outer_even_b4_shell_i_exact_v2.json"
V1_SOURCE = REPO / "agents/structural-basis/code/active25_outer_b4_i_block_v1.py"
V1_TEST = REPO / "agents/structural-basis/tests/test_active25_outer_b4_i_block_v1.py"
V1_SPEC = REPO / "agents/structural-basis/ACTIVE25-OUTER-B4-I-BLOCK.md"
V1_ARTIFACT = REPO / "agents/structural-basis/results/active25_outer_even_b4_shell_i_exact_v1.json"
CORE = REPO / "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py"
ANALYTIC = REPO / "agents/audit/results/wide_c722_nonuniform_active25_tail_analytic_audit.json"
PINS = {
    SOURCE: "ddad99bdd12710e669870fcade850eb72e1c5989ef4747b2e0658be28551b6bb",
    TEST: "daaacda045b84eb30fbafe551300c771815f669bf5267092322854d48ba6a7e8",
    SPEC: "c6cb7207e1c4a4c0931d4562fffe539d6830bf8fff45aa9dd79751b6cfe64aa2",
    ARTIFACT: "ffe98de8ee5d47da7f046f4aa91aaadc3f7981222f7b7803276556ea558e756c",
    V1_SOURCE: "fdcfa7e05b25f5dea69c070182149ceab7b877da1df67fce4a5b53fab6546b90",
    V1_TEST: "3aff824529827cf0cbab9458b239a27912ea78fdcc6a6b155096387b0f481c14",
    V1_SPEC: "411947a317db774d9566bcc249d370a4af45ce52c51be19098c09f187843e624",
    V1_ARTIFACT: "368c5305189a0121b4f044d363c8677a7be698db28cf9dad0b1c004a5b5486e8",
    CORE: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    ANALYTIC: "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
}

EXPECTED_KEYS = {
    "basis", "basis_dimension", "basis_m1_calls_per_support",
    "cache_clear_after_each_row", "claim_scope", "contains_J",
    "contains_quotient", "determinant", "exact_rank", "high_matrix", "k",
    "ldl_all_positive", "ldl_pivots", "low_matrix", "parameters",
    "peak_rss_kib", "rigorous_values", "row_streamed", "shell_matrix",
    "signed_difference_fixture", "source_closure", "status",
    "supersedes_v1_artifact_sha256", "theorem_ready",
    "total_basis_m1_calls", "unique_symmetric_pairs", "v1_defect",
    "wall_seconds",
}


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          AuditFailure(f"nonfinite JSON in {path}: {value}")))


def load_core():
    module_spec = importlib.util.spec_from_file_location(
        "independent_active25_b4_i_core", CORE)
    require(module_spec is not None and module_spec.loader is not None,
            "cannot load active25 arithmetic core")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == CORE.resolve() and
            sha(module.__file__) == PINS[CORE], "wrong arithmetic core loaded")
    return module


def parse_fraction_matrix(raw, name):
    require(type(raw) is list and len(raw) == 10 and
            all(type(row) is list and len(row) == 10 for row in raw),
            f"{name} dimension changed")
    result = []
    for row in raw:
        parsed = []
        for value in row:
            require(type(value) is str, f"{name} entry is not a string")
            number = Q(value)
            require(str(number) == value, f"{name} entry is noncanonical")
            parsed.append(number)
        result.append(parsed)
    return result


def clear_caches(core, *supports):
    for support in supports:
        for name in ("basis_m1", "canonical_support_moment",
                     "canonical_support_residual", "_piece_residual"):
            function = getattr(support, name, None)
            if function is not None and hasattr(function, "cache_clear"):
                function.cache_clear()
    for name in ("_large_shift_dp", "_small_box_dp",
                 "_selected_exponent_splits", "multiply_monomial_orbits"):
        function = getattr(core.ei, name, None)
        if function is not None and hasattr(function, "cache_clear"):
            function.cache_clear()


def reconstruct(core, high, low, labels):
    n = len(labels)
    high_matrix = [[Q(0) for _ in range(n)] for _ in range(n)]
    low_matrix = [[Q(0) for _ in range(n)] for _ in range(n)]
    calls_high = calls_low = 0
    for i, left in enumerate(labels):
        for j in range(i + 1):
            right = labels[j]
            hi = high.basis_m1(left, right)
            calls_high += 1
            lo = low.basis_m1(left, right)
            calls_low += 1
            high_matrix[i][j] = high_matrix[j][i] = hi
            low_matrix[i][j] = low_matrix[j][i] = lo
        clear_caches(core, high, low)
    shell = [[high_matrix[i][j] - low_matrix[i][j]
              for j in range(n)] for i in range(n)]
    return high_matrix, low_matrix, shell, calls_high, calls_low


def exact_ldl(matrix):
    n = len(matrix)
    require(n and all(len(row) == n for row in matrix) and
            all(matrix[i][j] == matrix[j][i]
                for i in range(n) for j in range(n)),
            "LDL input is not symmetric square")
    lower = [[Q(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for i in range(n):
        pivot = matrix[i][i] - sum(
            (lower[i][k] ** 2 * pivots[k] for k in range(i)), Q(0))
        require(pivot != 0, "zero exact LDL pivot")
        pivots.append(pivot)
        for j in range(i + 1, n):
            lower[j][i] = (matrix[j][i] - sum(
                (lower[j][k] * lower[i][k] * pivots[k]
                 for k in range(i)), Q(0))) / pivot
    rebuilt = [[sum((lower[i][k] * pivots[k] * lower[j][k]
                     for k in range(min(i, j) + 1)), Q(0))
                for j in range(n)] for i in range(n)]
    require(rebuilt == matrix, "independent exact LDL reconstruction failed")
    return pivots


def exact_rank(matrix):
    work = [[Q(value) for value in row] for row in matrix]
    rank = 0
    columns = len(work[0]) if work else 0
    require(all(len(row) == columns for row in work), "rank input is ragged")
    for column in range(columns):
        pivot = next((row for row in range(rank, len(work))
                      if work[row][column]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        scale = work[rank][column]
        work[rank] = [value / scale for value in work[rank]]
        for row in range(len(work)):
            if row != rank and work[row][column]:
                multiple = work[row][column]
                work[row] = [work[row][j] - multiple * work[rank][j]
                             for j in range(columns)]
        rank += 1
    return rank


def quadratic(matrix, vector):
    return sum((Q(vector[i]) * matrix[i][j] * Q(vector[j])
                for i in range(len(vector)) for j in range(len(vector))), Q(0))


def build():
    for path, expected in PINS.items():
        require(sha(path) == expected, f"frozen input changed: {path}")
    artifact = strict_json(ARTIFACT)
    require(type(artifact) is dict and set(artifact) == EXPECTED_KEYS,
            "artifact schema changed")
    core = load_core()
    require(core.require_pins() == {
                str(path.relative_to(REPO)): digest
                for path, digest in core.PINNED.items()},
            "transitive arithmetic pins changed")
    require(Path(core.shell.__file__).resolve() == core.SHELL_PATH.resolve() and
            Path(core.outer_core.__file__).resolve() == core.OUTER_PATH.resolve(),
            "wrong transitive arithmetic module loaded")

    analytic = core.validate_analytic()
    supports = core.make_supports()
    high, low = supports["H"], supports["L"]
    require(high.k == low.k == 48 and
            high.alpha == core.ALPHA2 and low.alpha == core.ALPHA1 and
            high.delta == low.delta == core.DELTA and
            tuple(high.schedule) == tuple(low.schedule) == core.SCHEDULE and
            high.max_large() == low.max_large() == 25 and
            analytic["parameters"]["outer_active"] == list(range(26)),
            "nested active25 support identity changed")
    labels = (
        (0, ()), (1, ()), (2, ()), (0, (2,)), (3, ()),
        (1, (2,)), (4, ()), (2, (2,)), (0, (4,)), (0, (2, 2)),
    )
    require(tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in core.ei.even_basis(4)) == labels,
            "independent even-B4 label order changed")

    high_matrix, low_matrix, shell_matrix, calls_high, calls_low = reconstruct(
        core, high, low, labels)
    require((calls_high, calls_low) == (55, 55),
            "reconstruction did not evaluate 55 pairs per support")
    serialized = lambda matrix: [[str(value) for value in row] for row in matrix]
    require(artifact["high_matrix"] == serialized(high_matrix) and
            artifact["low_matrix"] == serialized(low_matrix) and
            artifact["shell_matrix"] == serialized(shell_matrix),
            "artifact matrices differ from independent 55-pair reconstruction")

    parsed_high = parse_fraction_matrix(artifact["high_matrix"], "high")
    parsed_low = parse_fraction_matrix(artifact["low_matrix"], "low")
    parsed_shell = parse_fraction_matrix(artifact["shell_matrix"], "shell")
    require(parsed_high == high_matrix and parsed_low == low_matrix and
            parsed_shell == shell_matrix and
            all(shell_matrix[i][j] == high_matrix[i][j] - low_matrix[i][j]
                for i in range(10) for j in range(10)),
            "H-L entry identity failed")
    old = strict_json(V1_ARTIFACT)
    require(old["high_matrix"] == artifact["high_matrix"] and
            old["low_matrix"] == artifact["low_matrix"] and
            old["shell_matrix"] == artifact["shell_matrix"],
            "v2 exact values differ from preserved v1")

    pivots = exact_ldl(shell_matrix)
    rank = exact_rank(shell_matrix)
    determinant = math.prod(pivots, start=Q(1))
    require(rank == artifact["exact_rank"] == 10 and
            all(pivot > 0 for pivot in pivots) and
            artifact["ldl_all_positive"] is True and
            artifact["ldl_pivots"] == [str(pivot) for pivot in pivots] and
            artifact["determinant"] == str(determinant),
            "rank/positive-LDL certificate mismatch")

    fixture = artifact["signed_difference_fixture"]
    require(type(fixture) is dict and set(fixture) == {
                "vector", "high", "low", "shell", "identity"},
            "signed fixture schema changed")
    vector = [Q(value) for value in fixture["vector"]]
    high_q, low_q, shell_q = (quadratic(matrix, vector)
                              for matrix in (high_matrix, low_matrix,
                                             shell_matrix))
    require(len(vector) == 10 and fixture == {
                "vector": [str(value) for value in vector],
                "high": str(high_q), "low": str(low_q),
                "shell": str(shell_q), "identity": True,
            } and shell_q == high_q - low_q and shell_q > 0,
            "signed exact difference fixture failed")

    require(artifact["status"] ==
            "active25-outer-even-B4-shell-I-exact-v2" and
            artifact["rigorous_values"] is True and
            artifact["theorem_ready"] is False and
            artifact["contains_J"] is False and
            artifact["contains_quotient"] is False and
            artifact["claim_scope"] == "exact denominator Gram block only" and
            artifact["supersedes_v1_artifact_sha256"] == PINS[V1_ARTIFACT] and
            artifact["k"] == 48 and artifact["basis_dimension"] == 10 and
            artifact["basis"] == [[a, list(lam)] for a, lam in labels] and
            artifact["unique_symmetric_pairs"] == 55 and
            artifact["basis_m1_calls_per_support"] == 55 and
            artifact["total_basis_m1_calls"] == 110 and
            artifact["row_streamed"] is True and
            artifact["cache_clear_after_each_row"] is True and
            type(artifact["peak_rss_kib"]) is int and
            artifact["peak_rss_kib"] > 0 and
            type(artifact["wall_seconds"]) in (int, float) and
            not isinstance(artifact["wall_seconds"], bool) and
            math.isfinite(artifact["wall_seconds"]) and
            artifact["wall_seconds"] > 0,
            "scope/work metadata mismatch")
    require(artifact["parameters"] == {
                "delta": str(core.DELTA), "alpha_high": str(core.ALPHA2),
                "alpha_low": str(core.ALPHA1),
                "eta_not_used_by_I": str(core.ETA2),
                "schedule": [str(value) for value in core.SCHEDULE],
                "active_counts": list(range(26)),
            }, "parameter metadata mismatch")

    closure = artifact["source_closure"]
    expected_closure_paths = set(str(path.resolve()) for path in (
        SOURCE, TEST, SPEC, *(
            V1_SOURCE, V1_TEST, V1_SPEC, V1_ARTIFACT), CORE, ANALYTIC))
    require(type(closure) is dict and set(closure) == expected_closure_paths,
            "source closure path inventory changed")
    for raw_path, binding in closure.items():
        path = Path(raw_path)
        observed = path.stat()
        require(type(binding) is dict and set(binding) == {
                    "sha256", "device", "inode"} and
                binding["sha256"] == sha(path) == PINS[path] and
                binding["device"] == int(observed.st_dev) and
                binding["inode"] == int(observed.st_ino) and
                stat.S_ISREG(observed.st_mode),
                f"source closure binding changed: {path}")

    core.require_pins()
    for path, expected in PINS.items():
        require(sha(path) == expected, f"input moved during audit: {path}")
    return {
        "status": "AUDIT PASS",
        "scope": "exact active25 outer even-B4 denominator Gram block only",
        "checker_sha256": sha(FILE),
        "artifact_sha256": PINS[ARTIFACT],
        "checks": {
            "basis_dimension": 10,
            "unique_symmetric_pairs_recomputed_per_support": 55,
            "total_exact_support_calls_recomputed": 110,
            "all_100_matrix_entries_match": True,
            "H_minus_L_entry_identity": True,
            "preserved_v1_exact_values_match": True,
            "exact_rank": rank,
            "exact_positive_ldl_pivots": len(pivots),
            "source_hash_and_inode_closure": True,
            "contains_J": False,
            "contains_quotient": False,
            "theorem_ready": False,
        },
        "decision": (
            "arithmetic and corrected 55-pair metadata accepted at its "
            "denominator-only scope; it supplies no Rayleigh or sieve result"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
