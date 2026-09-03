#!/usr/bin/env python3
"""Exact D16-inner plus support-adapted outer-shell B4 pencil.

The fixed first coordinate is the exact BV D16 polynomial on the complete
inner simplex.  The other ten coordinates are independent ``even_basis(4)``
polynomials on the scheduled outer shell ``H \\ L``.  Thus this is a genuine
outer-polynomial reoptimization, not a transported D16 coefficient vector.

All matrix entries are Fraction values reconstructed from the branch
recurrence.  Decimal Cholesky/Jacobi is used only to discover a particular
vector; the selected vector is contracted exactly.  The current CLI exposes
only a bounded cost preflight.  A target build must be enabled by a separate
audited launch wrapper after the analytic support artifact is frozen.
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
import resource
import stat
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
PROXY_PATH = FILE.with_name("wide_hybrid_outer_constant_proxy.py")
SOLVER_PATH = REPO / "agents/exact-integrator/robust_generalized_solve.py"
CERTIFICATE_PATH = (
    REPO / "agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json")

PINNED_PROXY_SHA256 = (
    "21b9b384d0ec502cbfd83bacb2da1d7e7529a1131a8a959e28eaa948f568ba16"
)
PINNED_SOLVER_SHA256 = (
    "2086244acb674e5bd92e4880fb38d32d6dd981cd0272db595de2578554da257e"
)
PINNED_CERTIFICATE_SHA256 = (
    "59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62"
)
PINNED_INTEGRATOR_SHA256 = (
    "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52"
)
PINNED_GROUPED_SHA256 = (
    "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a"
)

K = 48
DEGREE = 4
DELTA = Q(361, 50000)
ALPHA_INNER = Q(103, 400)
ETA_INNER = Q(97, 400)
ALPHA_OUTER = Q(3211, 12000)
ETA_OUTER = Q(3031, 12000)
CAP_START = Q(13, 125)
CAP_PLATEAU = Q(83, 500)
MAX_PREFLIGHT_WALL_SECONDS = Q(7200)
MAX_PREFLIGHT_PEAK_RSS_KIB = 524288
D6_MINIMUM_D4_QUOTIENT = Q(199, 200)       # 0.995
D6_MINIMUM_GAIN_OVER_BASE = Q(1, 100)      # 0.01
D6_MAXIMUM_ESTIMATED_WALL_SECONDS = Q(14400)


def sha256(value) -> str:
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_module(name, path, expected):
    if sha256(path) != expected:
        raise RuntimeError(f"pinned dependency changed: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = load_module("frontier_r10_exact_proxy", PROXY_PATH,
                PINNED_PROXY_SHA256)
S = load_module("frontier_r10_robust_solver", SOLVER_PATH,
                PINNED_SOLVER_SHA256)


def schedule():
    return tuple(min(CAP_START + (m - 1) * DELTA, CAP_PLATEAU)
                 for m in range(1, 24))


SCHEDULE = schedule()
BASIS = tuple(P.ei.even_basis(DEGREE))
WORST_PROBE_LABEL = (0, (2, 2))


def source_paths():
    return (
        FILE,
        PROXY_PATH,
        SOLVER_PATH,
        CERTIFICATE_PATH,
        REPO / "agents/exact-integrator/src/exact_integrator.py",
        REPO / "agents/exact-integrator/grouped_fixed_vector.py",
        REPO / "agents/exact-integrator/run_scheduled_basis.py",
        REPO / "agents/exact-integrator/verify_scheduled_fixed_vector.py",
    )


def snapshot_sources():
    snapshots = {}
    for path in source_paths():
        resolved = path.resolve()
        if resolved in snapshots:
            raise ValueError("source path alias")
        snapshots[resolved] = resolved.read_bytes()
    if sha256(snapshots[PROXY_PATH]) != PINNED_PROXY_SHA256:
        raise RuntimeError("proxy snapshot changed")
    if sha256(snapshots[SOLVER_PATH]) != PINNED_SOLVER_SHA256:
        raise RuntimeError("solver snapshot changed")
    if sha256(snapshots[CERTIFICATE_PATH]) != PINNED_CERTIFICATE_SHA256:
        raise RuntimeError("certificate snapshot changed")
    integrator = (REPO / "agents/exact-integrator/src/exact_integrator.py").resolve()
    grouped = (REPO / "agents/exact-integrator/grouped_fixed_vector.py").resolve()
    if (sha256(snapshots[integrator]) != PINNED_INTEGRATOR_SHA256 or
            sha256(snapshots[grouped]) != PINNED_GROUPED_SHA256):
        raise RuntimeError("exact recurrence snapshot changed")
    return snapshots


def validate_schedule():
    expected_prefix = (
        Q(13, 125), Q(5561, 50000), Q(2961, 25000), Q(6283, 50000),
        Q(1661, 12500), Q(1401, 10000), Q(3683, 25000), Q(7727, 50000),
        Q(1011, 6250), Q(83, 500),
    )
    if SCHEDULE[:10] != expected_prefix or any(
            value != CAP_PLATEAU for value in SCHEDULE[9:]):
        raise ArithmeticError("frontier-r10 schedule changed")
    active = P.active_counts(SCHEDULE)
    if active != tuple(range(23)):
        raise ArithmeticError("frontier-r10 active counts changed")
    if not (22 * DELTA <= SCHEDULE[21] and
            23 * DELTA > SCHEDULE[22]):
        raise ArithmeticError("first empty count changed")
    return active


def strict_json_bytes(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite JSON token: {token}")))


def load_base():
    raw_bytes = CERTIFICATE_PATH.read_bytes()
    if sha256(raw_bytes) != PINNED_CERTIFICATE_SHA256:
        raise RuntimeError("BV D16 certificate changed")
    raw = strict_json_bytes(raw_bytes)
    basis = tuple((int(a), tuple(int(x) for x in lam))
                  for a, lam in raw.get("basis", ()))
    vector = tuple(Q(value) for value in raw.get("rational_vector", ()))
    expected_parameters = {
        "alpha": "103/400", "beta1": "103/400",
        "beta2": "103/400", "beta3plus": "103/400",
        "delta": "7/250", "eta": "97/400",
    }
    if (raw.get("k") != K or raw.get("degree") != 16 or
            raw.get("integrator_sha256") != PINNED_INTEGRATOR_SHA256 or
            raw.get("parameters") != expected_parameters or
            basis != tuple(P.ei.even_basis(16)) or len(vector) != 307):
        raise ValueError("BV D16 certificate schema changed")
    denominator = Q(raw["exact_denominator"])
    numerator = Q(raw["exact_numerator"])
    quotient = Q(raw["exact_quotient"])
    if (denominator <= 0 or numerator / denominator != quotient or
            raw.get("denominator_positive") is not True):
        raise ArithmeticError("BV D16 certificate forms changed")
    return {"basis": basis, "vector": vector,
            "denominator": denominator, "numerator": numerator,
            "quotient": quotient, "bytes": raw_bytes}


def supports(k=K):
    prefix = SCHEDULE[:min(k, len(SCHEDULE))]
    inner = P.ei.OneStratumSupport(
        k, ALPHA_INNER, DELTA, ETA_OUTER,
        ALPHA_INNER, ALPHA_INNER, ALPHA_INNER)
    high = P.ScheduledSupport.make(
        k, ALPHA_OUTER, DELTA, ETA_OUTER, prefix)
    low = P.ScheduledSupport.make(
        k, ALPHA_INNER, DELTA, ETA_OUTER, prefix)
    return inner, high, low


def label_components(label, k=K):
    return P.components((label,), (Q(1),), k)


def exact_ldl(matrix):
    n = len(matrix)
    lower = [[Q(int(i == j)) for j in range(n)] for i in range(n)]
    pivots = []
    for j in range(n):
        pivot = matrix[j][j] - sum(
            lower[j][h] ** 2 * pivots[h] for h in range(j))
        if pivot <= 0:
            raise ArithmeticError(f"nonpositive exact Gram pivot {j}")
        pivots.append(pivot)
        for i in range(j + 1, n):
            lower[i][j] = (matrix[i][j] - sum(
                lower[i][h] * lower[j][h] * pivots[h]
                for h in range(j))) / pivot
    return pivots


def matrix_sha(a, b):
    digest = hashlib.sha256()
    for name, matrix in (("M1", a), ("M2", b)):
        digest.update((name + "\n").encode("ascii"))
        for row in matrix:
            digest.update(("\t".join(str(value) for value in row) +
                           "\n").encode("ascii"))
    return digest.hexdigest()


def signed_shell_bilinear(hh, hl, lh, ll):
    """Bilinear expansion of ``(H-L)_left (H-L)_right``."""
    return hh - hl - lh + ll


def timed_cross(left_support, left_components, right_support,
                right_components):
    started = time.perf_counter()
    value, by_r, calls = P.cross_marginal(
        left_support, left_components, right_support, right_components,
        ETA_OUTER, return_by_r=True)
    return {"value": value, "by_r": by_r, "calls": calls,
            "seconds": time.perf_counter() - started}


def low_k_regression():
    # Independent of the production schedule: this checks the literal branch
    # cross engine, symmetry, and the single factor k in a signed shell.
    base = P.low_k_signed_literal_tests()
    delta, eta = Q(1, 20), Q(1, 5)
    high = P.ScheduledSupport.make(
        2, Q(13, 50), delta, eta, (Q(3, 10), Q(3, 10)))
    low = P.ScheduledSupport.make(
        2, Q(6, 25), delta, eta, (Q(3, 10), Q(3, 10)))
    label = (0, (2,))
    component = P.components((label,), (Q(1),), 2)
    hh = P.cross_marginal(high, component, high, component, eta)
    hl = P.cross_marginal(high, component, low, component, eta)
    lh = P.cross_marginal(low, component, high, component, eta)
    ll = P.cross_marginal(low, component, low, component, eta)
    if hh != high.basis_j(label, label) or ll != low.basis_j(label, label):
        raise ArithmeticError("same-support branch/canonical J mismatch")
    if hl != lh:
        raise ArithmeticError("cross-support J symmetry failed")
    shell = hh - hl - lh + ll
    if shell <= 0:
        raise ArithmeticError("low-k shell square is nonpositive")
    return {**base, "D4_label": [0, [2]],
            "D4_cross": str(hl), "D4_shell_J": str(shell),
            "D4_kJ": str(2 * shell)}


def build_preflight():
    snapshots = snapshot_sources()
    active = validate_schedule()
    low_k = low_k_regression()
    base = load_base()
    inner, high, low = supports()
    base_components = P.components(base["basis"], base["vector"], K)
    if len(base_components) != 769 or len({row[0] for row in base_components}) != 67:
        raise ArithmeticError("fixed D16 marginal inventory changed")
    probe_components = label_components(WORST_PROBE_LABEL)
    if len(probe_components) != 2:
        raise ArithmeticError("worst D4 probe component count changed")

    entries = {}
    for tag, left_support, left_components, right_support, right_components in (
            ("fh", inner, base_components, high, probe_components),
            ("fl", inner, base_components, low, probe_components),
            ("hh", high, probe_components, high, probe_components),
            ("hl", high, probe_components, low, probe_components),
            ("ll", low, probe_components, low, probe_components)):
        entries[tag] = timed_cross(
            left_support, left_components, right_support, right_components)
    if (entries["hh"]["value"] !=
            high.basis_j(WORST_PROBE_LABEL, WORST_PROBE_LABEL) or
            entries["ll"]["value"] !=
            low.basis_j(WORST_PROBE_LABEL, WORST_PROBE_LABEL)):
        raise ArithmeticError("production same-support J engines disagree")
    shell_i = (high.basis_m1(WORST_PROBE_LABEL, WORST_PROBE_LABEL) -
               low.basis_m1(WORST_PROBE_LABEL, WORST_PROBE_LABEL))
    shell_j = signed_shell_bilinear(
        entries["hh"]["value"], entries["hl"]["value"],
        entries["hl"]["value"], entries["ll"]["value"])
    cross_j = entries["fh"]["value"] - entries["fl"]["value"]
    if shell_i <= 0 or shell_j <= 0:
        raise ArithmeticError("probe Gram/self form is nonpositive")

    fixed_cross_seconds = entries["fh"]["seconds"] + entries["fl"]["seconds"]
    same_support_seconds = entries["hh"]["seconds"] + entries["ll"]["seconds"]
    mixed_seconds = entries["hl"]["seconds"]
    # Full build: ten fixed/base cross rows; 55 symmetric HH and LL entries;
    # every ordered HL entry (100).  The measured two-component label is a
    # conservative representative of B4, and an additional factor two is
    # applied before authorizing target work.
    raw_estimate = (10 * fixed_cross_seconds +
                    55 * same_support_seconds + 100 * mixed_seconds)
    estimated = Q(str(raw_estimate)) * 2
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    gate = (estimated <= MAX_PREFLIGHT_WALL_SECONDS and
            peak <= MAX_PREFLIGHT_PEAK_RSS_KIB)
    result = {
        "status": "wide-frontier-r10-D16-plus-outer-B4-cost-preflight-v1",
        "rigorous": False,
        "theorem_ready": False,
        "target_matrix_built": False,
        "script_sha256": sha256(FILE),
        "source_hashes": {str(path.relative_to(REPO)): sha256(raw)
                          for path, raw in snapshots.items()},
        "parameters": {
            "k": K, "degree": DEGREE, "delta": str(DELTA),
            "alpha_inner": str(ALPHA_INNER), "eta_inner": str(ETA_INNER),
            "alpha_outer": str(ALPHA_OUTER), "eta_outer": str(ETA_OUTER),
            "cap_start": str(CAP_START), "cap_plateau": str(CAP_PLATEAU),
            "schedule": [str(value) for value in SCHEDULE],
            "active_counts": list(active),
        },
        "finite_space": {
            "fixed_inner": "pinned exact BV D16 polynomial",
            "outer_shell_basis": [[a, list(lam)] for a, lam in BASIS],
            "outer_shell_basis_dimension": len(BASIS),
            "total_dimension": 1 + len(BASIS),
            "denominator_cross_zero_by_disjoint_band_interiors": True,
            "inner_inner_J_cutoff": str(ETA_INNER),
            "all_outer_involving_J_cutoff": str(ETA_OUTER),
        },
        "base": {"certificate_sha256": PINNED_CERTIFICATE_SHA256,
                 "exact_denominator": str(base["denominator"]),
                 "exact_numerator": str(base["numerator"]),
                 "exact_quotient": str(base["quotient"]),
                 "marginal_components": len(base_components),
                 "rest_orbits": len({row[0] for row in base_components})},
        "low_k_regression": low_k,
        "probe_label": [WORST_PROBE_LABEL[0], list(WORST_PROBE_LABEL[1])],
        "probe_entries": {
            tag: {"exact_value": str(row["value"]),
                  "branch_integrals": row["calls"],
                  "nonzero_common_rows": sum(value != 0
                                               for value in row["by_r"]),
                  "seconds": row["seconds"]}
            for tag, row in entries.items()},
        "probe_combined": {"I_shell": str(shell_i),
                           "J_inner_shell": str(cross_j),
                           "J_shell_shell": str(shell_j),
                           "kJ_inner_shell": str(K * cross_j),
                           "kJ_shell_shell": str(K * shell_j)},
        "resource_estimate": {
            "raw_seconds": str(Q(str(raw_estimate))),
            "safety_factor": "2",
            "estimated_target_seconds": str(estimated),
            "maximum_target_seconds": str(MAX_PREFLIGHT_WALL_SECONDS),
            "peak_rss_kib": peak,
            "maximum_peak_rss_kib": MAX_PREFLIGHT_PEAK_RSS_KIB,
            "resource_gate_pass": gate,
        },
        "continuation": {
            "target_build_requires_frozen_analytic_audit": True,
            "target_build_requires_independent_preflight_audit": True,
            "target_build_requires_separate_root_authorization": True,
            "D6_minimum_exact_D4_quotient": str(D6_MINIMUM_D4_QUOTIENT),
            "D6_minimum_exact_gain_over_base": str(D6_MINIMUM_GAIN_OVER_BASE),
            "D6_maximum_estimated_wall_seconds":
                str(D6_MAXIMUM_ESTIMATED_WALL_SECONDS),
            "target_launch_authorized": False,
            "D6_launch_authorized": False,
        },
    }
    for path, raw in snapshots.items():
        if path.read_bytes() != raw:
            raise RuntimeError(f"source changed during preflight: {path}")
    return result


def assemble_exact_matrix(progress=False):
    """Fresh exact 11x11 target matrix; callable only by an audited wrapper."""
    base = load_base()
    inner, high, low = supports()
    base_components = P.components(base["basis"], base["vector"], K)
    components = [label_components(label) for label in BASIS]
    n = 1 + len(BASIS)
    a = [[Q(0) for _ in range(n)] for _ in range(n)]
    b = [[Q(0) for _ in range(n)] for _ in range(n)]
    a[0][0], b[0][0] = base["denominator"], base["numerator"]
    diagnostics = {"fixed_cross_calls": [], "mixed_shell_calls": []}
    for j, component in enumerate(components, 1):
        fh, _, calls_h = P.cross_marginal(
            inner, base_components, high, component, ETA_OUTER,
            return_by_r=True)
        fl, _, calls_l = P.cross_marginal(
            inner, base_components, low, component, ETA_OUTER,
            return_by_r=True)
        b[0][j] = b[j][0] = K * (fh - fl)
        diagnostics["fixed_cross_calls"].append(calls_h + calls_l)
        if progress:
            print(f"fixed/outer cross {j}/{len(BASIS)}", flush=True)
    for i, left in enumerate(BASIS):
        for j in range(i + 1):
            right = BASIS[j]
            ii, jj = i + 1, j + 1
            a[ii][jj] = a[jj][ii] = (
                high.basis_m1(left, right) - low.basis_m1(left, right))
            hh = high.basis_j(left, right)
            ll = low.basis_j(left, right)
            hl, _, calls_hl = P.cross_marginal(
                high, components[i], low, components[j], ETA_OUTER,
                return_by_r=True)
            if i == j:
                lh, calls_lh = hl, 0
            else:
                lh, _, calls_lh = P.cross_marginal(
                    high, components[j], low, components[i], ETA_OUTER,
                    return_by_r=True)
            b[ii][jj] = b[jj][ii] = K * signed_shell_bilinear(
                hh, hl, lh, ll)
            diagnostics["mixed_shell_calls"].append(calls_hl + calls_lh)
        if progress:
            print(f"outer block row {i + 1}/{len(BASIS)}", flush=True)
    pivots = exact_ldl(a)
    return a, b, pivots, diagnostics


def solve_particular(a, b, precisions=(120, 180), digits=70):
    solves = [S.solve_once(a, b, precision) for precision in precisions]
    with localcontext() as context:
        context.prec = max(precisions) + 20
        vector = [Q(format(Decimal(value), f".{digits}E"))
                  for value in solves[-1]["vector"]]
    denominator = P.ei.exact_quadratic(a, vector)
    numerator = P.ei.exact_quadratic(b, vector)
    if denominator <= 0:
        raise ArithmeticError("particular vector has nonpositive denominator")
    return solves, vector, denominator, numerator


def publish_new(path, result, snapshots):
    target = Path(path).resolve()
    if target in snapshots:
        raise ValueError("output aliases source")
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n").encode("ascii")
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            if written <= 0:
                raise OSError("short output write")
            offset += written
        os.fsync(fd)
        before = os.fstat(fd)
        after = os.stat(target, follow_symlinks=False)
        if (not stat.S_ISREG(before.st_mode) or
                (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)):
            raise RuntimeError("output ownership changed")
        for source, raw in snapshots.items():
            if source.read_bytes() != raw:
                raise RuntimeError(f"source changed: {source}")
        os.lseek(fd, 0, os.SEEK_SET)
        observed = b""
        while len(observed) < len(payload):
            chunk = os.read(fd, len(payload) - len(observed))
            if not chunk:
                break
            observed += chunk
        if observed != payload:
            raise RuntimeError("published output bytes changed")
    finally:
        os.close(fd)
    return sha256(payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight",), default="preflight")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshots = snapshot_sources()
    result = build_preflight()
    digest = publish_new(args.output, result, snapshots)
    print(json.dumps({"artifact_sha256": digest,
                      "resource_gate_pass":
                          result["resource_estimate"]["resource_gate_pass"],
                      "estimated_target_seconds":
                          result["resource_estimate"]["estimated_target_seconds"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
