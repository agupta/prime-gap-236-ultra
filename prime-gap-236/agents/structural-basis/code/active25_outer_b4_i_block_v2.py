#!/usr/bin/env python3
"""Actual 55-pair exact active-25 outer even-B4 denominator build.

This successor preserves v1 and its exact matrix, but corrects v1's false
work-count metadata: v1 evaluated all 100 ordered entries per support while
claiming 55 upper-triangle contractions.  Here only ``j <= i`` is evaluated
and each result is copied to its transpose.  There is still no J calculation
or quotient.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
V1_PATH = FILE.with_name("active25_outer_b4_i_block_v1.py")
V1_TEST = (
    REPO / "agents/structural-basis/tests/"
    "test_active25_outer_b4_i_block_v1.py")
V1_SPEC = REPO / "agents/structural-basis/ACTIVE25-OUTER-B4-I-BLOCK.md"
V1_ARTIFACT = (
    REPO / "agents/structural-basis/results/"
    "active25_outer_even_b4_shell_i_exact_v1.json")
TEST_FILE = (
    REPO / "agents/structural-basis/tests/"
    "test_active25_outer_b4_i_block_v2.py")
SPEC_FILE = REPO / "agents/structural-basis/ACTIVE25-OUTER-B4-I-BLOCK-V2.md"

PINNED_V1 = {
    V1_PATH:
        "fdcfa7e05b25f5dea69c070182149ceab7b877da1df67fce4a5b53fab6546b90",
    V1_TEST:
        "3aff824529827cf0cbab9458b239a27912ea78fdcc6a6b155096387b0f481c14",
    V1_SPEC:
        "411947a317db774d9566bcc249d370a4af45ce52c51be19098c09f187843e624",
    V1_ARTIFACT:
        "368c5305189a0121b4f044d363c8677a7be698db28cf9dad0b1c004a5b5486e8",
}


def _sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


for _path, _expected in PINNED_V1.items():
    if _sha(_path) != _expected:
        raise RuntimeError(f"frozen v1 dependency changed: {_path}")
_spec = importlib.util.spec_from_file_location(
    "active25_outer_b4_i_v1_dependency", V1_PATH)
V1 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = V1
_spec.loader.exec_module(V1)


def upper_triangle_matrices(high, low, labels=None, *, progress=False):
    labels = V1.basis_labels() if labels is None else tuple(labels)
    if (high.k != low.k or high.delta != low.delta or
            tuple(high.schedule) != tuple(low.schedule) or
            high.alpha <= low.alpha):
        raise ValueError("denominator supports are not one nested schedule")
    n = len(labels)
    high_matrix = [[Q(0) for _ in range(n)] for _ in range(n)]
    low_matrix = [[Q(0) for _ in range(n)] for _ in range(n)]
    shell_matrix = [[Q(0) for _ in range(n)] for _ in range(n)]
    evaluated_pairs = 0
    for i, left in enumerate(labels):
        for j in range(i + 1):
            right = labels[j]
            hi = high.basis_m1(left, right)
            lo = low.basis_m1(left, right)
            shell = hi - lo
            high_matrix[i][j] = high_matrix[j][i] = hi
            low_matrix[i][j] = low_matrix[j][i] = lo
            shell_matrix[i][j] = shell_matrix[j][i] = shell
            evaluated_pairs += 1
        if progress:
            print(f"ROW {i + 1}/{n} pairs={evaluated_pairs} rss_kib="
                  f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}",
                  flush=True)
        V1.clear_row_caches(high, low)
    if evaluated_pairs != n * (n + 1) // 2:
        raise ArithmeticError("upper-triangle work count changed")
    if any(shell_matrix[i][j] != high_matrix[i][j] - low_matrix[i][j]
           for i in range(n) for j in range(n)):
        raise ArithmeticError("shell difference identity failed")
    return high_matrix, low_matrix, shell_matrix, evaluated_pairs


def _string_matrix(matrix):
    return [[str(x) for x in row] for row in matrix]


def _closure_snapshots():
    paths = (
        FILE, TEST_FILE, SPEC_FILE, *PINNED_V1,
        V1.ACTIVE_CORE, V1.ANALYTIC,
    )
    answer = {}
    for path in paths:
        data = Path(path).read_bytes()
        observed = Path(path).stat()
        answer[str(Path(path).resolve())] = {
            "sha256": V1.sha256_bytes(data),
            "device": int(observed.st_dev),
            "inode": int(observed.st_ino),
        }
    return answer


def build_payload(*, progress=False):
    started = time.perf_counter()
    closure = _closure_snapshots()
    high, low = V1.validate_target()
    labels = V1.basis_labels()
    high_matrix, low_matrix, shell_matrix, pairs = upper_triangle_matrices(
        high, low, labels, progress=progress)
    _, pivots = V1.ldl_pivots(shell_matrix)
    rank = V1.exact_rank(shell_matrix)
    if rank != len(labels) or any(pivot <= 0 for pivot in pivots):
        raise ArithmeticError("outer B4 shell Gram block is not exact PD")
    old = json.loads(V1_ARTIFACT.read_bytes())
    if (old.get("high_matrix") != _string_matrix(high_matrix) or
            old.get("low_matrix") != _string_matrix(low_matrix) or
            old.get("shell_matrix") != _string_matrix(shell_matrix)):
        raise ArithmeticError("v2 55-pair matrix differs from preserved v1")
    signed_vector = tuple(Q(x) for x in
                          (1, -1, 2, -2, 3, -3, 4, -4, 5, -5))
    high_q = V1.exact_quadratic(high_matrix, signed_vector)
    low_q = V1.exact_quadratic(low_matrix, signed_vector)
    shell_q = V1.exact_quadratic(shell_matrix, signed_vector)
    if shell_q != high_q - low_q or shell_q <= 0:
        raise ArithmeticError("signed shell difference identity failed")
    determinant = Q(1)
    for pivot in pivots:
        determinant *= pivot
    V1._rebind_closure(closure)
    return {
        "status": "active25-outer-even-B4-shell-I-exact-v2",
        "rigorous_values": True,
        "theorem_ready": False,
        "contains_J": False,
        "contains_quotient": False,
        "claim_scope": "exact denominator Gram block only",
        "supersedes_v1_artifact_sha256": PINNED_V1[V1_ARTIFACT],
        "v1_defect": (
            "matrix exact, but source evaluated 100 ordered entries per support "
            "while artifact claimed 55 upper-triangle contractions"),
        "k": 48,
        "parameters": {
            "delta": str(V1.A25.DELTA),
            "alpha_high": str(V1.A25.ALPHA2),
            "alpha_low": str(V1.A25.ALPHA1),
            "eta_not_used_by_I": str(V1.A25.ETA2),
            "schedule": [str(x) for x in V1.A25.SCHEDULE],
            "active_counts": list(range(26)),
        },
        "basis": [[a, list(lam)] for a, lam in labels],
        "basis_dimension": len(labels),
        "unique_symmetric_pairs": pairs,
        "basis_m1_calls_per_support": pairs,
        "total_basis_m1_calls": 2 * pairs,
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
        V1.validate_target()
        print(json.dumps({
            "status": "active25-outer-even-B4-I-v2-preflight",
            "basis_dimension": 10,
            "unique_symmetric_pairs": 55,
            "total_basis_m1_calls": 110,
            "contains_J": False,
            "contains_quotient": False,
        }, sort_keys=True))
        return
    if not args.output:
        raise SystemExit("exact build requires a fresh --output path")
    payload, closure = build_payload(progress=args.progress)
    digest = V1.publish_new(args.output, payload, closure)
    print(json.dumps({
        "status": payload["status"], "output_sha256": digest,
        "exact_rank": payload["exact_rank"],
        "ldl_all_positive": payload["ldl_all_positive"],
        "contains_quotient": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
