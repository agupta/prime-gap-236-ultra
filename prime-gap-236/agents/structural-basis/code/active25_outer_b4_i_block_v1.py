#!/usr/bin/env python3
r"""Exact denominator Gram block for the active-25 outer even-B4 shell.

This deliberately computes only ``I``.  The ten coordinates are the even
orbit basis through degree four, restricted to

    S(alpha2, B_active25) \ S(alpha1, B_active25).

Because the two supports are nested, every entry is reconstructed as the
exact Fraction difference ``I_H(G_i,G_j)-I_L(G_i,G_j)``.  Rows are completed
and all support/radial caches are cleared before the next row.  There is no J
code, generalized eigensolve, Rayleigh quotient, or theorem claim here.
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
REPO = FILE.parents[3]
ACTIVE_CORE = (
    REPO / "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
ANALYTIC = (
    REPO / "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")
TEST_FILE = (
    REPO / "agents/structural-basis/tests/"
    "test_active25_outer_b4_i_block_v1.py")
SPEC_FILE = REPO / "agents/structural-basis/ACTIVE25-OUTER-B4-I-BLOCK.md"

PINNED_ACTIVE_CORE_SHA256 = (
    "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a"
)
PINNED_ANALYTIC_SHA256 = (
    "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


if sha256_file(ACTIVE_CORE) != PINNED_ACTIVE_CORE_SHA256:
    raise RuntimeError("active-25 arithmetic core changed")
if sha256_file(ANALYTIC) != PINNED_ANALYTIC_SHA256:
    raise RuntimeError("active-25 analytic artifact changed")
_spec = importlib.util.spec_from_file_location(
    "active25_b4_i_frozen_dependency", ACTIVE_CORE)
if _spec is None or _spec.loader is None:
    raise ImportError(ACTIVE_CORE)
A25 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = A25
_spec.loader.exec_module(A25)
EI = A25.ei
GROUPED = A25.GroupedEvaluator


def basis_labels():
    labels = tuple((int(a), tuple(int(x) for x in lam))
                   for a, lam in EI.even_basis(4))
    expected = (
        (0, ()), (1, ()), (2, ()), (0, (2,)), (3, ()),
        (1, (2,)), (4, ()), (2, (2,)), (0, (4,)), (0, (2, 2)),
    )
    if labels != expected:
        raise ArithmeticError("even-B4 label order changed")
    return labels


def validate_target():
    analytic = A25.validate_analytic()
    if (sha256_file(ACTIVE_CORE) != PINNED_ACTIVE_CORE_SHA256 or
            sha256_file(ANALYTIC) != PINNED_ANALYTIC_SHA256 or
            analytic["parameters"]["outer_active"] != list(range(26)) or
            analytic["parameters"]["outer_schedule_through_first_empty"] !=
            [str(x) for x in A25.SCHEDULE]):
        raise ValueError("active-25 target identity changed")
    supports = A25.make_supports()
    high, low = supports["H"], supports["L"]
    if (high.k != 48 or low.k != 48 or
            high.alpha != A25.ALPHA2 or low.alpha != A25.ALPHA1 or
            high.delta != A25.DELTA or low.delta != A25.DELTA or
            high.schedule != A25.SCHEDULE or low.schedule != A25.SCHEDULE or
            high.max_large() != 25 or low.max_large() != 25):
        raise ValueError("active-25 shell supports changed")
    return high, low


def _cache_functions(supports):
    names = (
        "basis_m1", "canonical_support_moment",
        "canonical_support_residual", "_piece_residual",
    )
    functions = []
    for support in supports:
        for name in names:
            function = getattr(support, name, None)
            if function is not None and hasattr(function, "cache_clear"):
                functions.append(function)
    for function in (
            getattr(EI, "_large_shift_dp", None),
            getattr(EI, "_small_box_dp", None),
            getattr(EI, "_selected_exponent_splits", None),
            getattr(EI, "multiply_monomial_orbits", None)):
        if function is not None and hasattr(function, "cache_clear"):
            functions.append(function)
    return tuple(functions)


def clear_row_caches(*supports):
    for function in _cache_functions(supports):
        function.cache_clear()


def gram_rows(high, low, labels=None, *, progress=False):
    """Yield one exact ``(row, high, low, shell)`` tuple at a time."""
    labels = basis_labels() if labels is None else tuple(labels)
    if (high.k != low.k or high.delta != low.delta or
            tuple(high.schedule) != tuple(low.schedule) or
            high.alpha <= low.alpha):
        raise ValueError("denominator supports are not one nested schedule")
    for i, left in enumerate(labels):
        high_row, low_row, shell_row = [], [], []
        for right in labels:
            hi = high.basis_m1(left, right)
            lo = low.basis_m1(left, right)
            high_row.append(hi)
            low_row.append(lo)
            shell_row.append(hi - lo)
        if progress:
            print(f"ROW {i + 1}/{len(labels)} rss_kib="
                  f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}",
                  flush=True)
        yield i, tuple(high_row), tuple(low_row), tuple(shell_row)
        clear_row_caches(high, low)


def matrices(high, low, labels=None, *, progress=False):
    labels = basis_labels() if labels is None else tuple(labels)
    high_matrix, low_matrix, shell_matrix = [], [], []
    for i, hi, lo, shell in gram_rows(
            high, low, labels, progress=progress):
        if i != len(high_matrix):
            raise ArithmeticError("row stream changed order")
        high_matrix.append(list(hi))
        low_matrix.append(list(lo))
        shell_matrix.append(list(shell))
    for name, matrix in (
            ("high", high_matrix), ("low", low_matrix),
            ("shell", shell_matrix)):
        if any(matrix[i][j] != matrix[j][i]
               for i in range(len(labels)) for j in range(len(labels))):
            raise ArithmeticError(f"{name} Gram matrix is asymmetric")
    if any(shell_matrix[i][j] != high_matrix[i][j] - low_matrix[i][j]
           for i in range(len(labels)) for j in range(len(labels))):
        raise ArithmeticError("shell difference identity failed")
    return high_matrix, low_matrix, shell_matrix


def grouped_quadratic(support, labels, vector):
    if len(labels) != len(vector):
        raise ValueError("quadratic vector length mismatch")
    value, _, _ = GROUPED(
        support, list(labels), [Q(x) for x in vector], Q).evaluate_i(
            progress=False, workers=1)
    return value


def exact_quadratic(matrix, vector):
    if len(matrix) != len(vector) or any(len(row) != len(vector)
                                         for row in matrix):
        raise ValueError("quadratic dimensions disagree")
    return sum((Q(vector[i]) * matrix[i][j] * Q(vector[j])
                for i in range(len(vector)) for j in range(len(vector))), Q(0))


def ldl_pivots(matrix):
    """Exact unpivoted LDL; positive pivots certify positive definiteness."""
    n = len(matrix)
    if not n or any(len(row) != n for row in matrix) or any(
            matrix[i][j] != matrix[j][i]
            for i in range(n) for j in range(n)):
        raise ValueError("LDL input is not a nonempty symmetric matrix")
    lower = [[Q(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for i in range(n):
        pivot = matrix[i][i] - sum(
            (lower[i][k] * lower[i][k] * pivots[k]
             for k in range(i)), Q(0))
        if pivot == 0:
            raise ArithmeticError("zero exact LDL pivot")
        pivots.append(pivot)
        for j in range(i + 1, n):
            lower[j][i] = (matrix[j][i] - sum(
                (lower[j][k] * lower[i][k] * pivots[k]
                 for k in range(i)), Q(0))) / pivot
    reconstructed = [[sum(
        (lower[i][k] * pivots[k] * lower[j][k]
         for k in range(min(i, j) + 1)), Q(0))
        for j in range(n)] for i in range(n)]
    if reconstructed != matrix:
        raise ArithmeticError("exact LDL reconstruction failed")
    return lower, pivots


def exact_rank(matrix):
    work = [[Q(x) for x in row] for row in matrix]
    if not work:
        return 0
    columns = len(work[0])
    if any(len(row) != columns for row in work):
        raise ValueError("ragged rank input")
    rank = 0
    for column in range(columns):
        pivot = next((r for r in range(rank, len(work))
                      if work[r][column]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        scale = work[rank][column]
        work[rank] = [x / scale for x in work[rank]]
        for row in range(len(work)):
            if row != rank and work[row][column]:
                multiple = work[row][column]
                work[row] = [work[row][j] - multiple * work[rank][j]
                             for j in range(columns)]
        rank += 1
        if rank == len(work):
            break
    return rank


def _string_matrix(matrix):
    return [[str(x) for x in row] for row in matrix]


def _closure_snapshots():
    paths = (FILE, ACTIVE_CORE, ANALYTIC, TEST_FILE, SPEC_FILE)
    answer = {}
    for path in paths:
        data = path.read_bytes()
        stat_result = path.stat()
        answer[str(path.resolve())] = {
            "sha256": sha256_bytes(data),
            "device": int(stat_result.st_dev),
            "inode": int(stat_result.st_ino),
        }
    return answer


def _rebind_closure(snapshots):
    for raw, expected in snapshots.items():
        path = Path(raw)
        observed = path.stat()
        if (not stat.S_ISREG(observed.st_mode) or
                int(observed.st_dev) != expected["device"] or
                int(observed.st_ino) != expected["inode"] or
                sha256_file(path) != expected["sha256"]):
            raise ArithmeticError(f"source closure changed: {raw}")
    return True


def publish_new(path, payload, closure):
    path = Path(path).resolve()
    if str(path) in closure:
        raise ValueError("output aliases source closure")
    if path.exists():
        raise FileExistsError(path)
    parent = path.parent
    parent_stat = parent.stat()
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    directory = os.open(parent, flags)
    descriptor = None
    try:
        held = os.fstat(directory)
        if ((held.st_dev, held.st_ino) !=
                (parent_stat.st_dev, parent_stat.st_ino)):
            raise ArithmeticError("output parent changed before publication")
        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            create_flags |= os.O_NOFOLLOW
        descriptor = os.open(path.name, create_flags, 0o600, dir_fd=directory)
        encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) +
                   "\n").encode()
        os.write(descriptor, encoded)
        os.fsync(descriptor)
        _rebind_closure(closure)
        owned = os.fstat(descriptor)
        check_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            check_flags |= os.O_NOFOLLOW
        check = os.open(path.name, check_flags, dir_fd=directory)
        try:
            current = os.fstat(check)
            if ((owned.st_dev, owned.st_ino) !=
                    (current.st_dev, current.st_ino) or
                    sha256_bytes(os.read(check, len(encoded) + 1)) !=
                    sha256_bytes(encoded)):
                raise ArithmeticError("published output changed")
        finally:
            os.close(check)
        return sha256_bytes(encoded)
    except Exception:
        if descriptor is not None:
            rejection = b'{"status":"rejected-incomplete-I-block"}\n'
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, rejection)
            os.fsync(descriptor)
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def build_payload(*, progress=False):
    started = time.perf_counter()
    closure = _closure_snapshots()
    high, low = validate_target()
    labels = basis_labels()
    high_matrix, low_matrix, shell_matrix = matrices(
        high, low, labels, progress=progress)
    lower, pivots = ldl_pivots(shell_matrix)
    rank = exact_rank(shell_matrix)
    if rank != len(labels) or any(pivot <= 0 for pivot in pivots):
        raise ArithmeticError("outer B4 shell Gram block is not exact PD")
    determinant = Q(1)
    for pivot in pivots:
        determinant *= pivot
    signed_vector = tuple(Q(x) for x in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5))
    high_q = exact_quadratic(high_matrix, signed_vector)
    low_q = exact_quadratic(low_matrix, signed_vector)
    shell_q = exact_quadratic(shell_matrix, signed_vector)
    if shell_q != high_q - low_q or shell_q <= 0:
        raise ArithmeticError("signed target difference identity failed")
    _rebind_closure(closure)
    return {
        "status": "active25-outer-even-B4-shell-I-exact-v1",
        "rigorous_values": True,
        "theorem_ready": False,
        "contains_J": False,
        "contains_quotient": False,
        "claim_scope": "exact denominator Gram block only",
        "k": 48,
        "parameters": {
            "delta": str(A25.DELTA),
            "alpha_high": str(A25.ALPHA2),
            "alpha_low": str(A25.ALPHA1),
            "eta_not_used_by_I": str(A25.ETA2),
            "schedule": [str(x) for x in A25.SCHEDULE],
            "active_counts": list(range(26)),
        },
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "upper_triangle_contractions": len(labels) * (len(labels) + 1) // 2,
        "row_streamed": True,
        "cache_clear_after_each_row": True,
        "high_matrix": _string_matrix(high_matrix),
        "low_matrix": _string_matrix(low_matrix),
        "shell_matrix": _string_matrix(shell_matrix),
        "exact_rank": rank,
        "ldl_pivots": [str(x) for x in pivots],
        "ldl_all_positive": all(x > 0 for x in pivots),
        "determinant": str(determinant),
        "signed_difference_fixture": {
            "vector": [str(x) for x in signed_vector],
            "high": str(high_q), "low": str(low_q), "shell": str(shell_q),
            "identity": shell_q == high_q - low_q,
        },
        "source_closure": closure,
        "wall_seconds": time.perf_counter() - started,
        "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }, closure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        high, low = validate_target()
        print(json.dumps({
            "status": "active25-outer-even-B4-I-preflight",
            "basis_dimension": len(basis_labels()),
            "upper_triangle_contractions": 55,
            "active_counts": list(range(high.max_large() + 1)),
            "nested": high.alpha > low.alpha,
            "contains_J": False,
        }, sort_keys=True))
        return
    if not args.output:
        raise SystemExit("exact build requires a fresh --output path")
    payload, closure = build_payload(progress=args.progress)
    digest = publish_new(args.output, payload, closure)
    print(json.dumps({
        "status": payload["status"], "output_sha256": digest,
        "exact_rank": payload["exact_rank"],
        "ldl_all_positive": payload["ldl_all_positive"],
        "contains_quotient": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
