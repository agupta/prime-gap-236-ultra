#!/usr/bin/env python3
"""Fast exact common-r shard for the scaled D19/D14-grid38 cross.

This is a separate v2 producer: it preserves the frozen v1 reconstruction and
geometry, but replaces Fraction-by-Fraction radial accumulation by a proved
common-denominator integer map and collects the two affine factors before the
final scalar moment contraction.  It reads no serialized moment or matrix.
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
BASE_PATH = FILE.with_name("d14_grid38_scaled_b_shard.py")
FAST_PATH = FILE.with_name("fast_tagged_scalar.py")
TEST_PATH = FILE.with_name("test_symmetric_cutoff_cross.py")
LOCAL_PINNED = {
    BASE_PATH: "deceb6c6248fa97e65c9ce5a604081f3b05f0b7c838dea2f1d1c525a59bea905",
    FAST_PATH: "5d9d82ae7b097a40b852a8471e281d5bd5ad69d08240e1a73d3928e21a40aaa2",
    TEST_PATH: "d2898ef57898e1a3dc5b752a842bcc1b04bd234a4575342a804b0dcf1f44be26",
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path, data):
    if path.read_bytes() != data:
        raise RuntimeError(f"source changed before import: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def encode(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {str(key): encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value


def build(common_r, local_snapshots, dependency_snapshots, base, fast,
          *, progress=True):
    started = time.monotonic()
    stage_times = {}
    frontier = base.import_snapshot(
        "d14_grid38_fast_v2_frontier", base.FRONTIER,
        dependency_snapshots[base.FRONTIER])
    radial = base.import_snapshot(
        "d14_grid38_fast_v2_radial", base.RADIAL,
        dependency_snapshots[base.RADIAL])
    engine = base.import_snapshot(
        "d14_grid38_fast_v2_engine", base.ENGINE,
        dependency_snapshots[base.ENGINE])

    inner_raw = base.strict_json_bytes(
        dependency_snapshots[base.INNER], str(base.INNER))
    outer_raw = base.strict_json_bytes(
        dependency_snapshots[base.OUTER], str(base.OUTER))
    support_raw = base.strict_json_bytes(
        dependency_snapshots[base.SUPPORT], str(base.SUPPORT))
    inner_basis = base.parse_basis(
        inner_raw.get("basis"), frontier.ei.even_basis(base.DEGREE_F))
    outer_basis = base.parse_basis(
        outer_raw.get("basis"), frontier.ei.even_basis(base.DEGREE_H))
    inner_vector = base.parse_vector(
        inner_raw.get("rational_vector"), len(inner_basis))
    candidates = outer_raw.get("candidates")
    if (not isinstance(candidates, list) or not candidates or
            candidates[0].get("name") != "D14_grid_1e-38"):
        raise ValueError("pinned grid-38 candidate is absent or reordered")
    outer_vector = base.parse_vector(
        candidates[0].get("rational_vector"), len(outer_basis))
    if (inner_raw.get("format") !=
            "bv-rational-vector-cache-free-direct-check-v2" or
            inner_raw.get("rigorous") is not True or
            inner_raw.get("wire_types_validated_before_reconstruction") is not True or
            inner_raw.get("checker_sha256") != base.PINNED[base.INNER_CHECKER] or
            inner_raw.get("k") != base.K or
            outer_raw.get("format") !=
                "bv-D14-fine-common-grid-candidates-exact-v2" or
            outer_raw.get("rigorous") is not True or
            outer_raw.get("k") != base.K or
            outer_raw.get("degree") != base.DEGREE_H):
        raise ValueError("source result identity mismatch")
    parameters = support_raw.get("parameters", {})
    if (support_raw.get("status") !=
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS" or
            support_raw.get("checker_sha256") !=
                base.PINNED[base.SUPPORT_CHECKER] or
            parameters.get("k") != base.K or
            Q(parameters.get("delta")) != base.DELTA or
            tuple(map(Q, parameters.get("alpha", []))) !=
                (base.ALPHA1, base.ALPHA2) or
            tuple(map(Q, parameters.get(
                "outer_schedule_through_first_empty", []))) != base.SCHEDULE or
            support_raw.get("definition5_single_outer_band", {}).get(
                "eta_inner_outer") != str(base.ETA)):
        raise ValueError("frozen support geometry mismatch")

    lcm_f = math.lcm(*(value.denominator for value in inner_vector))
    lcm_h = math.lcm(*(value.denominator for value in outer_vector))
    if lcm_f != base.SCALE_F or lcm_h != base.SCALE_H:
        raise ArithmeticError("candidate common denominator changed")
    inner_scaled = engine.scale_vector(inner_vector, base.SCALE_F)
    outer_scaled = engine.scale_vector(outer_vector, base.SCALE_H)
    if (any(value.denominator != 1 for value in inner_scaled) or
            any(value.denominator != 1 for value in outer_scaled)):
        raise ArithmeticError("common-denominator scaling did not make integers")
    outer_dilated_terms = engine.dilate_residual_terms(
        outer_basis, outer_scaled, base.DILATION)
    outer_dilated = tuple(outer_dilated_terms.get(label, Q(0))
                          for label in outer_basis)
    if set(outer_dilated_terms) - set(outer_basis):
        raise ArithmeticError("dilation escaped D14")
    point = tuple(Q(index + 1, 10000 + 2 * index)
                  if index < 8 else Q(0) for index in range(base.K))
    original_terms = {label: coefficient for label, coefficient in
                      zip(outer_basis, outer_scaled) if coefficient}
    if engine.evaluate_residual_terms(outer_dilated_terms, point) != \
            engine.evaluate_residual_terms(
                original_terms,
                tuple(base.DILATION * coordinate for coordinate in point)):
        raise ArithmeticError("exact natural-dilation point check failed")

    stamp = time.monotonic()
    marginal = engine.marginal_polynomial(
        frontier.ei, inner_basis, inner_scaled, base.K, base.ALPHA1)
    components = engine.distinguished_components(
        frontier.ei, outer_basis, outer_dilated, base.K)
    stage_times["marginal_and_components"] = time.monotonic() - stamp
    stamp = time.monotonic()
    kernel, kernel_stats = engine.global_cross_kernel(
        frontier.ei, marginal, components)
    stage_times["global_kernel"] = time.monotonic() - stamp
    if progress:
        print(f"fast-v2 kernel r={common_r} {kernel_stats} "
              f"seconds={stage_times['global_kernel']:.3f}",
              file=sys.stderr, flush=True)
    stamp = time.monotonic()
    families, family_stats = engine.primitive_tagged_families(
        kernel, alpha_f=base.ALPHA1, delta=base.DELTA)
    stage_times["primitive_families"] = time.monotonic() - stamp
    if progress:
        print(f"fast-v2 families r={common_r} {family_stats} "
              f"seconds={stage_times['primitive_families']:.3f}",
              file=sys.stderr, flush=True)
    stamp = time.monotonic()
    value, diagnostics = fast.band_cross_r_integer(
        engine, radial, families, k=base.K, alpha_high=base.ALPHA2,
        alpha_low=base.ALPHA1, alpha_f=base.ALPHA1, eta=base.ETA,
        delta=base.DELTA, schedule=base.SCHEDULE, common_r=common_r)
    stage_times["integer_radialize_and_collected_integrate"] = \
        time.monotonic() - stamp
    stage_times["total"] = time.monotonic() - started
    if progress:
        print(f"fast-v2 done r={common_r} seconds={stage_times['total']:.3f}",
              file=sys.stderr, flush=True)
    source_hashes = {
        str(path.relative_to(REPO)): digest
        for path, digest in {**base.PINNED, **LOCAL_PINNED}.items()}
    return {
        "format": "D14-grid38-scaled-cutoff-cross-common-r-fast-v2",
        "status": "EXACT FAST COMMON-r CROSS SHARD PASS",
        "rigorous": True,
        "serialized_matrices_read": False,
        "common_r": common_r,
        "scaled_b_shard": str(value),
        "scaling": {
            "inner_F": str(base.SCALE_F),
            "outer_H": str(base.SCALE_H),
            "b_factor": str(base.SCALE_F * base.SCALE_H),
            "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
        },
        "geometry": {
            "k": base.K, "delta": str(base.DELTA),
            "alpha1": str(base.ALPHA1), "alpha2": str(base.ALPHA2),
            "eta": str(base.ETA),
            "natural_dilation_alpha1_over_alpha2": str(base.DILATION),
            "schedule": list(map(str, base.SCHEDULE)),
            "definition5_cutoff_retained": True,
        },
        "candidate": {
            "inner": "pinned strict cache-free exact D19 v2",
            "outer": "D14_grid_1e-38",
            "inner_basis_dimension": len(inner_basis),
            "outer_basis_dimension": len(outer_basis),
            "inner_common_denominator_lcm": str(lcm_f),
            "outer_common_denominator_lcm": str(lcm_h),
            "dilation_point_check": True,
        },
        "algorithm": {
            "family_common_denominator_integer_accumulation": True,
            "radial_common_denominator_integer_accumulation": True,
            "affine_products_collected_once_per_tag_and_shift": True,
            "small_k_reference_and_literal_equality_in_pinned_tests": True,
        },
        "source_hashes": source_hashes,
        "kernel_stats": kernel_stats,
        "family_stats": family_stats,
        "branch_values_and_fast_stats": encode(diagnostics),
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
        raise RuntimeError("externally pinned fast-v2 runner SHA does not match")
    if not 0 <= args.common_r <= 12:
        raise ValueError("the frozen support has common r=0..12")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    local_snapshots = {path: path.read_bytes() for path in LOCAL_PINNED}
    for path, digest in LOCAL_PINNED.items():
        if sha256_bytes(local_snapshots[path]) != digest:
            raise RuntimeError(f"local pinned source changed: {path}")
    base = load("d14_grid38_fast_v2_base", BASE_PATH,
                local_snapshots[BASE_PATH])
    fast = load("d14_grid38_fast_v2_algorithm", FAST_PATH,
                local_snapshots[FAST_PATH])
    dependency_snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, digest in base.PINNED.items():
        if sha256_bytes(dependency_snapshots[path]) != digest:
            raise RuntimeError(f"inherited pinned source changed: {path}")
    result = build(args.common_r, local_snapshots, dependency_snapshots,
                   base, fast)
    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data
                for path, data in local_snapshots.items()) or
            any(path.read_bytes() != data
                for path, data in dependency_snapshots.items())):
        raise RuntimeError("fast-v2 source closure changed during computation")
    result["producer_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp.{os.getpid()}")
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
