#!/usr/bin/env python3
"""Reconstruct one exact D14-grid38 capped cross shard from pinned sources.

This runner never reads serialized moments or matrices.  It reconstructs the
D19 full-simplex marginal, the naturally dilated D14 target, the global orbit
product kernel, and the cutoff-aware radial integral.  Each invocation emits
one immutable common-large-count shard of

    b = 48 * J(F_D19, H_D14 * 1_V).

The two exact common-denominator scalings are part of the certificate:
``F <- 10^87 F`` and ``H <- 10^38 H``.  Hence a sum of these shard values is
``10^125`` times the unscaled b.  No floating point enters the value path.
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
import resource
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
ENGINE = FILE.with_name("symmetric_cutoff_cross.py")
FRONTIER = REPO / (
    "agents/small-delta-frontier/"
    "frontier_active25_inner_d16_tagged_shell.py")
RADIAL = REPO / "verify/exact_capped_certificate.py"
INNER = REPO / "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json"
INNER_CHECKER = REPO / "verify/check_bv_rational_vector_direct_v2.py"
INNER_AUDIT_CHECKER = REPO / (
    "agents/audit/verify_bv_D19_krylov20_direct_v2_strict_audit.py")
INNER_AUDIT_RESULT = REPO / (
    "agents/audit/results/bv_D19_krylov20_direct_v2_strict_audit.json")
OUTER = REPO / (
    "agents/structural-basis/results/"
    "bv_D14_fine_common_grid_candidates_exact_v2.json")
SUPPORT = REPO / (
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json")
SUPPORT_CHECKER = REPO / (
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py")

PINNED = {
    ENGINE: "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    FRONTIER: "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    RADIAL: "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    INNER: "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
    INNER_CHECKER: "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5",
    INNER_AUDIT_CHECKER: "3e1b552e31d1f21deac70e4c114618b6853677ed5482c2c53597fdbbc5cf7a1f",
    INNER_AUDIT_RESULT: "944c37ea2716a80e5ebaf99892d6ce6c025afc7a6fc913b9ffb507054baeeb35",
    OUTER: "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    SUPPORT: "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    SUPPORT_CHECKER: "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
}

K = 48
DEGREE_F = 19
DEGREE_H = 14
DELTA = Q(1, 60)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DILATION = ALPHA1 / ALPHA2
SCALE_F = 10**87
SCALE_H = 10**38
SCHEDULE = tuple(map(Q, (
    "1123/8000", "157041/1000000", "5267/31250",
    "87169/500000", "11593/62500", "1523/8000",
    "193097/1000000", "98573/500000", "202047/1000000",
    "20709/100000", "52917/250000", "52917/250000",
)))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def strict_json_bytes(data, name):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate key {key!r} in {name}")
            out[key] = value
        return out
    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite token {token!r} in {name}")))


def import_snapshot(name, path, data):
    # The digest was checked before import, and the post-computation snapshot
    # check below detects concurrent replacement.
    if path.read_bytes() != data:
        raise RuntimeError(f"dependency changed before import: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parse_basis(raw, expected):
    if not isinstance(raw, list):
        raise ValueError("basis is not an array")
    basis = []
    for index, label in enumerate(raw):
        if (not isinstance(label, list) or len(label) != 2 or
                type(label[0]) is not int or label[0] < 0 or
                not isinstance(label[1], list) or
                any(type(x) is not int or x <= 0 for x in label[1])):
            raise ValueError(f"malformed basis label {index}")
        basis.append((label[0], tuple(label[1])))
    basis = tuple(basis)
    if basis != tuple(expected):
        raise ValueError("basis is not the canonical ordered even basis")
    return basis


def parse_vector(raw, dimension):
    if not isinstance(raw, list) or len(raw) != dimension:
        raise ValueError("rational vector length mismatch")
    vector = []
    for index, value in enumerate(raw):
        if type(value) is not str:
            raise ValueError(f"coefficient {index} is not a rational string")
        parsed = Q(value)
        if str(parsed) != value:
            raise ValueError(f"coefficient {index} is not canonical")
        vector.append(parsed)
    if not any(vector):
        raise ValueError("zero vector")
    return tuple(vector)


def encode(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {str(key): encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def build(common_r, snapshots, *, progress=True):
    started = time.monotonic()
    stage_times = {}

    frontier = import_snapshot("d14_grid38_scaled_frontier", FRONTIER,
                               snapshots[FRONTIER])
    radial = import_snapshot("d14_grid38_scaled_radial", RADIAL,
                             snapshots[RADIAL])
    engine = import_snapshot("d14_grid38_scaled_engine", ENGINE,
                             snapshots[ENGINE])

    inner_raw = strict_json_bytes(snapshots[INNER], str(INNER))
    outer_raw = strict_json_bytes(snapshots[OUTER], str(OUTER))
    support_raw = strict_json_bytes(snapshots[SUPPORT], str(SUPPORT))
    inner_basis = parse_basis(inner_raw.get("basis"),
                              frontier.ei.even_basis(DEGREE_F))
    outer_basis = parse_basis(outer_raw.get("basis"),
                              frontier.ei.even_basis(DEGREE_H))
    inner_vector = parse_vector(inner_raw.get("rational_vector"),
                                len(inner_basis))
    candidates = outer_raw.get("candidates")
    if (not isinstance(candidates, list) or not candidates or
            candidates[0].get("name") != "D14_grid_1e-38"):
        raise ValueError("pinned grid-38 candidate is absent or reordered")
    outer_vector = parse_vector(candidates[0].get("rational_vector"),
                                len(outer_basis))
    if (inner_raw.get("format") != "bv-rational-vector-cache-free-direct-check-v2" or
            inner_raw.get("rigorous") is not True or inner_raw.get("k") != K or
            inner_raw.get("wire_types_validated_before_reconstruction") is not True or
            inner_raw.get("checker_sha256") != PINNED[INNER_CHECKER] or
            outer_raw.get("format") !=
                "bv-D14-fine-common-grid-candidates-exact-v2" or
            outer_raw.get("rigorous") is not True or outer_raw.get("k") != K or
            outer_raw.get("degree") != DEGREE_H):
        raise ValueError("source result identity mismatch")

    parameters = support_raw.get("parameters", {})
    if (support_raw.get("status") !=
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS" or
            support_raw.get("checker_sha256") != PINNED[SUPPORT_CHECKER] or
            parameters.get("k") != K or
            Q(parameters.get("delta")) != DELTA or
            tuple(map(Q, parameters.get("alpha", []))) != (ALPHA1, ALPHA2) or
            tuple(map(Q, parameters.get(
                "outer_schedule_through_first_empty", []))) != SCHEDULE or
            support_raw.get("definition5_single_outer_band", {}).get(
                "eta_inner_outer") != str(ETA)):
        raise ValueError("frozen support geometry mismatch")

    lcm_f = math.lcm(*(value.denominator for value in inner_vector))
    lcm_h = math.lcm(*(value.denominator for value in outer_vector))
    if lcm_f != SCALE_F or lcm_h != SCALE_H:
        raise ArithmeticError(
            f"common denominator mismatch: F={lcm_f}, H={lcm_h}")
    inner_scaled = engine.scale_vector(inner_vector, SCALE_F)
    outer_scaled = engine.scale_vector(outer_vector, SCALE_H)
    if (any(value.denominator != 1 for value in inner_scaled) or
            any(value.denominator != 1 for value in outer_scaled)):
        raise ArithmeticError("common-denominator scaling did not make integers")

    outer_dilated_terms = engine.dilate_residual_terms(
        outer_basis, outer_scaled, DILATION)
    outer_dilated = tuple(outer_dilated_terms.get(label, Q(0))
                          for label in outer_basis)
    if set(outer_dilated_terms) - set(outer_basis):
        raise ArithmeticError("dilation escaped the canonical D14 basis")
    # Independent exact pointwise identity; eight nonzero coordinates exercise
    # every allowed partition length in B14, while the remaining forty retain
    # the actual theorem dimension.
    point = tuple(Q(index + 1, 10000 + 2 * index)
                  if index < 8 else Q(0) for index in range(K))
    original_terms = {label: coefficient for label, coefficient in
                      zip(outer_basis, outer_scaled) if coefficient}
    if engine.evaluate_residual_terms(outer_dilated_terms, point) != \
            engine.evaluate_residual_terms(
                original_terms,
                tuple(DILATION * coordinate for coordinate in point)):
        raise ArithmeticError("exact natural-dilation point check failed")

    stamp = time.monotonic()
    marginal = engine.marginal_polynomial(
        frontier.ei, inner_basis, inner_scaled, K, ALPHA1)
    components = engine.distinguished_components(
        frontier.ei, outer_basis, outer_dilated, K)
    stage_times["marginal_and_components"] = time.monotonic() - stamp
    stamp = time.monotonic()
    kernel, kernel_stats = engine.global_cross_kernel(
        frontier.ei, marginal, components)
    stage_times["global_kernel"] = time.monotonic() - stamp
    if progress:
        print(f"kernel r={common_r} {kernel_stats} "
              f"seconds={stage_times['global_kernel']:.3f}",
              file=sys.stderr, flush=True)
    stamp = time.monotonic()
    families, family_stats = engine.primitive_tagged_families(
        kernel, alpha_f=ALPHA1, delta=DELTA)
    stage_times["primitive_families"] = time.monotonic() - stamp
    if progress:
        print(f"families r={common_r} {family_stats} "
              f"seconds={stage_times['primitive_families']:.3f}",
              file=sys.stderr, flush=True)
    stamp = time.monotonic()
    value, diagnostics = engine.radialized_band_cross_r(
        radial, families, k=K, alpha_high=ALPHA2, alpha_low=ALPHA1,
        alpha_f=ALPHA1, eta=ETA, delta=DELTA, schedule=SCHEDULE,
        common_r=common_r)
    stage_times["radialize_and_integrate"] = time.monotonic() - stamp
    stage_times["total"] = time.monotonic() - started
    if progress:
        print(f"done r={common_r} seconds={stage_times['total']:.3f}",
              file=sys.stderr, flush=True)
    return {
        "format": "D14-grid38-scaled-cutoff-cross-common-r-v1",
        "status": "EXACT COMMON-r CROSS SHARD PASS",
        "rigorous": True,
        "serialized_matrices_read": False,
        "common_r": common_r,
        "scaled_b_shard": str(value),
        "scaling": {
            "inner_F": str(SCALE_F), "outer_H": str(SCALE_H),
            "b_factor": str(SCALE_F * SCALE_H),
            "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
        },
        "geometry": {
            "k": K, "delta": str(DELTA), "alpha1": str(ALPHA1),
            "alpha2": str(ALPHA2), "eta": str(ETA),
            "natural_dilation_alpha1_over_alpha2": str(DILATION),
            "schedule": list(map(str, SCHEDULE)),
            "definition5_cutoff_retained": True,
        },
        "source_hashes": {
            str(path.relative_to(REPO)): digest
            for path, digest in PINNED.items()},
        "candidate": {
            "inner": "pinned cache-free exact D19 v2",
            "outer": "D14_grid_1e-38",
            "inner_basis_dimension": len(inner_basis),
            "outer_basis_dimension": len(outer_basis),
            "inner_common_denominator_lcm": str(lcm_f),
            "outer_common_denominator_lcm": str(lcm_h),
            "dilation_point_check": True,
        },
        "kernel_stats": kernel_stats,
        "family_stats": family_stats,
        "branch_values": encode(diagnostics),
        "timing_seconds": stage_times,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--common-r", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args()
    self_data = FILE.read_bytes()
    if sha256_bytes(self_data) != args.expected_self_sha256:
        raise RuntimeError("externally pinned runner SHA does not match")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    snapshots = {path: path.read_bytes() for path in PINNED}
    for path, expected in PINNED.items():
        if sha256_bytes(snapshots[path]) != expected:
            raise RuntimeError(f"pinned dependency changed: {path}")
    result = build(args.common_r, snapshots)
    if FILE.read_bytes() != self_data or any(
            path.read_bytes() != data for path, data in snapshots.items()):
        raise RuntimeError("source closure changed during computation")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(
        f".{args.output.name}.tmp.{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(temporary)
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, args.output)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(sha256_bytes(payload), args.output)


if __name__ == "__main__":
    main()
