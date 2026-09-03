#!/usr/bin/env python3
"""Fail-closed exact aggregation of the frozen k=48 one-band shards.

This is the inexpensive result assembler, not the independent integration
replay.  It validates every immutable A and b shard, reconstructs the D19
inner deficit from its audited cache-free result, and evaluates the single
exact certificate inequality ``b**2 - A*D > 0``.  The later standalone replay
checker must reconstruct the shard integrals rather than merely call this
assembler.
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


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[1]
INNER_RESULT = REPO / "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json"
A_SOURCE = REPO / "agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py"
A_TEST = REPO / "agents/structural-basis/tests/test_exact_d14_one_band_a_shard_v2.py"
B_RUNNER = REPO / (
    "agents/exact-projection-engine/"
    "d14_grid38_scaled_b_shard_collected_v5.py")

PINNED = {
    INNER_RESULT: "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
    A_SOURCE: "2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d",
    A_TEST: "4d5402a8e9940755ca18e69c5a346426bc6081d78ea5206236191dc34e527afc",
    B_RUNNER: "eaa22454347d17201c60c30e1ed5ac01e34ba39368bc4711c1ea2c7f6d03ba82",
}

A_SOURCE_HASHES = {
    "agents/analytic-new-lever/test_truncated_lower_energy_v3.py":
        "9b0e1409ef4ea2dda1292a69881c344a35d52f4886f0568c0e8a71f806d0b1fa",
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py":
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
    "agents/exact-integrator/grouped_fixed_vector.py":
        "47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a",
    "agents/exact-integrator/src/exact_integrator.py":
        "941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52",
    "agents/exact-integrator/src/stratum_integrator.py":
        "0566f77860b0b61ce0ed342b5bb3a4743990725099d8b0cd6e685efad3c7394f",
    "agents/structural-basis/code/exact_d14_one_band_a_shard_v1.py":
        "6fa3c7c99735ec9eeb5817413e4dfc77dc6ae57e1cef26c720f54f33eb93896e",
    "agents/structural-basis/code/prepare_bv_D14_common_grid_candidates_v2.py":
        "83dfdd7d88ee7f2f2a4dfbf492af693b9ae99c2bfaf983816c0fdcdec3229a57",
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json":
        "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    "agents/structural-basis/tests/test_prepare_bv_D14_common_grid_candidates_v2.py":
        "d7f0f8856f677080495a59dcb04f93c732e7a7103546da9f65311916796e49c3",
}

B_SOURCE_HASHES = {
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py":
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
    "agents/audit/results/bv_D19_krylov20_direct_v2_strict_audit.json":
        "944c37ea2716a80e5ebaf99892d6ce6c025afc7a6fc913b9ffb507054baeeb35",
    "agents/audit/verify_bv_D19_krylov20_direct_v2_strict_audit.py":
        "3e1b552e31d1f21deac70e4c114618b6853677ed5482c2c53597fdbbc5cf7a1f",
    "agents/exact-projection-engine/collected_integer_scalar.py":
        "aef0a183d71b9c41b5373806d03481b94cb4e61a1ff3561888b8c31f94e8c890",
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard.py":
        "deceb6c6248fa97e65c9ce5a604081f3b05f0b7c838dea2f1d1c525a59bea905",
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_fast_v2.py":
        "4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3",
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_pruned_v3.py":
        "ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26",
    "agents/exact-projection-engine/fast_tagged_scalar.py":
        "5d9d82ae7b097a40b852a8471e281d5bd5ad69d08240e1a73d3928e21a40aaa2",
    "agents/exact-projection-engine/pruned_integer_radial.py":
        "834f624647094bf71364ad5c2b47e00371c7e7e78ed37c1d06eeca9186f73afe",
    "agents/exact-projection-engine/symmetric_cutoff_cross.py":
        "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    "agents/exact-projection-engine/test_collected_integer_scalar.py":
        "281ff70246041cc0d2ed948c41187b406a26b9d7ba9b94a1f4b502dab63d31d4",
    "agents/exact-projection-engine/test_pruned_integer_radial.py":
        "17b5eac692f859728d502e90a52b2c9c5ce03ef45e7966ce9104d8878910adfd",
    "agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py":
        "855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d",
    "agents/exact-projection-engine/test_symmetric_cutoff_cross.py":
        "d2898ef57898e1a3dc5b752a842bcc1b04bd234a4575342a804b0dcf1f44be26",
    "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py":
        "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json":
        "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    "verify/check_bv_rational_vector_direct_v2.py":
        "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5",
    "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json":
        "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
}

# The immutable shards serialize this entire transitive source closure.  Pin
# the live copies here as well; a self-consistent but stale/tampered shard is
# therefore rejected before its rational is used.
for relative, expected in B_SOURCE_HASHES.items():
    path = REPO / relative
    if path in PINNED and PINNED[path] != expected:
        raise RuntimeError(f"inconsistent embedded source pin: {relative}")
    PINNED[path] = expected
for relative, expected in A_SOURCE_HASHES.items():
    path = REPO / relative
    if path in PINNED and PINNED[path] != expected:
        raise RuntimeError(f"inconsistent embedded source pin: {relative}")
    PINNED[path] = expected

K = 48
COUNTS = tuple(range(13))
SCALE_F = 10**87
SCALE_H = 10**38
FORM_SCALE = SCALE_F**2
DEFAULT_A_DIR = REPO / "agents/structural-basis/results/d14_one_band_a_shards_v2"
DEFAULT_B_DIR = REPO / (
    "agents/exact-projection-engine/results/"
    "d14_grid38_scaled_b_collected_v5")

DELTA = Q(1, 60)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DILATION = Q(9270000, 9500917)
SCHEDULE = tuple(map(Q, (
    "1123/8000", "157041/1000000", "5267/31250",
    "87169/500000", "11593/62500", "1523/8000",
    "193097/1000000", "98573/500000", "202047/1000000",
    "20709/100000", "52917/250000", "52917/250000",
)))
B_ALGORITHM = {
    "family_common_denominator_integer_accumulation": True,
    "radial_common_denominator_integer_accumulation": True,
    "empty_shifts_pruned_inside_small_coordinate_convolution": True,
    "affine_products_collected_once_per_tag_and_shift": True,
    "complete_affine_radial_product_collected_by_final_monomial": True,
    "affine_common_denominator_integer_collection": True,
    "moment_common_denominator_integer_contraction": True,
    "one_moment_multiplication_per_surviving_product_monomial": True,
    "denominators_restored_exactly_once_per_shift": True,
    "coefficient_level_reference_transform_equality_in_pinned_tests": True,
    "full_low_k_pruned_v3_branch_equality_in_pinned_tests": True,
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes, label: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {label}")
            result[key] = value
        return result

    def reject(token):
        raise ValueError(f"nonfinite JSON token {token!r} in {label}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject)


def canonical_q(value, label: str) -> Q:
    if type(value) is not str:
        raise ValueError(f"{label} is not a rational string")
    parsed = Q(value)
    if str(parsed) != value:
        raise ValueError(f"{label} is not a canonical rational string")
    return parsed


def require_exact_files(directory: Path, prefix: str):
    directory = directory.resolve()
    expected = {directory / f"{prefix}{count:02d}.json" for count in COUNTS}
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    observed = set(directory.glob(f"{prefix}*.json"))
    if observed != expected:
        missing = sorted(str(path) for path in expected - observed)
        extra = sorted(str(path) for path in observed - expected)
        raise ValueError(f"incomplete/noncanonical shard set: missing={missing}, extra={extra}")
    for path in expected:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or path.is_symlink():
            raise ValueError(f"shard is not a plain regular file: {path}")
    return tuple(sorted(expected))


def parse_a_shard(path: Path, data: bytes, count: int):
    row = strict_json(data, str(path))
    top = {
        "active_counts", "base_source_sha256", "basis_dimension",
        "cache_read", "candidate", "checkpoint_unit", "checks",
        "claim_scope", "count", "degree", "elapsed_seconds", "exact_values",
        "fine_grid_status", "format", "geometry", "inventory", "k",
        "launch_authorized", "memory_limit_bytes", "one_band_status",
        "peak_rss_kib", "resume_supported", "rigorous",
        "serialized_matrix_entries_read", "source_hashes", "source_sha256",
        "status", "target_kind", "theorem_ready", "time_limit_seconds",
    }
    if (type(row) is not dict or set(row) != top or
            row.get("format") != "exact-d14-one-band-a-count-shard-v2" or
            row.get("status") != "EXACT D14 ONE-BAND A COUNT SHARD PASS" or
            row.get("rigorous") is not True or row.get("count") != count or
            type(row.get("count")) is not int or
            row.get("active_counts") != list(COUNTS) or row.get("k") != K or
            row.get("source_sha256") != PINNED[A_SOURCE] or
            row.get("base_source_sha256") !=
                A_SOURCE_HASHES[
                    "agents/structural-basis/code/"
                    "exact_d14_one_band_a_shard_v1.py"] or
            row.get("cache_read") is not False or
            row.get("serialized_matrix_entries_read") is not False or
            row.get("degree") != 14 or row.get("basis_dimension") != 195 or
            row.get("theorem_ready") is not False or
            row.get("launch_authorized") is not True or
            row.get("resume_supported") is not False or
            row.get("source_hashes") != A_SOURCE_HASHES):
        raise ValueError(f"A shard identity mismatch: {path}")
    candidate = row.get("candidate", {})
    if (type(candidate) is not dict or
            candidate.get("name") != "D14_grid_1e-38" or
            candidate.get("grid_digits") != 38 or
            candidate.get("vector_sha256") !=
                "86d6d57a224252285d4acc091ef8788530e27e42f74796529a9eb2c92b50502c" or
            candidate.get("scaled_vector_sha256") !=
                "420d163fe614245e7b2c769b858599d1c2de57f030467e6045e8c305c72444f9" or
            candidate.get("evaluation_vector_scale") != str(SCALE_H) or
            candidate.get("evaluation_vector_is_integral") is not True or
            candidate.get("natural_dilation") != "9270000/9500917"):
        raise ValueError(f"A shard candidate mismatch: {path}")

    expected_schedule = list(map(str, SCHEDULE)) + [str(SCHEDULE[-1])] * 36
    geometry = row.get("geometry")
    if geometry != {
            "alpha1": str(ALPHA1), "alpha2": str(ALPHA2),
            "band": "alpha1 <= sum(t) < alpha2, boundaries immaterial",
            "delta": str(DELTA), "eta": str(ETA),
            "schedule": expected_schedule,
            "schedule_extension": "terminal plateau through count 48"}:
        raise ValueError(f"A shard geometry mismatch: {path}")
    expected_checks = {
        "band_square_positive": True,
        "high_support_square_positive": True,
        "integer_vector_scale_and_dilation_commute": True,
        "low_support_square_positive": True,
        "natural_dilation_two_expansions_equal": True,
        "nested_supports_same_schedule": True,
        "paired_face_density_reuse": True,
        "termwise_vs_grouped_constant_volume_equal": True,
    }
    if row.get("checks") != expected_checks:
        raise ValueError(f"A shard exact-check inventory mismatch: {path}")
    inventory = row.get("inventory")
    if inventory != {
            "high_faces": 16 - count, "low_faces": 16 - count,
            "shared_density_faces": 16 - count,
            "square_orbit_partition_groups": 508,
            "square_residual_terms_per_support": 3034, "workers": 1}:
        raise ValueError(f"A shard work inventory mismatch: {path}")

    values = row.get("exact_values", {})
    if type(values) is not dict or set(values) != {
            "band_I_count", "band_I_count_decimal", "band_volume_count",
            "high_support_I_count", "high_support_volume_count",
            "low_support_I_count", "low_support_volume_count",
            "unscaled_band_I_count", "unscaled_band_I_count_decimal"}:
        raise ValueError(f"A shard exact-value schema mismatch: {path}")
    high = canonical_q(values.get("high_support_I_count"), f"A[{count}].high")
    low = canonical_q(values.get("low_support_I_count"), f"A[{count}].low")
    band = canonical_q(values.get("band_I_count"), f"A[{count}].band")
    unscaled = canonical_q(values.get("unscaled_band_I_count"),
                           f"A[{count}].unscaled")
    if high - low != band or band != unscaled * SCALE_H**2 or band <= 0:
        raise ArithmeticError(f"A shard arithmetic mismatch: {path}")
    for key in ("band_volume_count", "high_support_volume_count",
                "low_support_volume_count"):
        volume = canonical_q(values.get(key), f"A[{count}].{key}")
        if volume <= 0:
            raise ArithmeticError(f"A shard volume is nonpositive: {path}")
    return band


def beta(index: int) -> Q:
    if index <= 0:
        raise ValueError("cap index must be positive")
    return SCHEDULE[min(index, len(SCHEDULE)) - 1]


def expected_branches(alpha: Q, count: int):
    cutoff = ETA - count * DELTA
    if cutoff <= 0:
        return set()
    shared_cap = None if count == 0 else beta(count) - count * DELTA
    result = set()
    small_total_bound = min(cutoff, alpha - (count + 1) * DELTA)
    if (shared_cap is None or shared_cap > 0) and small_total_bound > 0:
        result.add("Sdelta")
    if ((shared_cap is None or shared_cap > 0)
            and cutoff > alpha - (count + 1) * DELTA):
        result.add("Stotal")
    large_cap = beta(count + 1) - (count + 1) * DELTA
    if large_cap > 0:
        if min(cutoff, alpha - (count + 1) * DELTA) > 0:
            result.add("Ltotal")
        result.add("Lbig")
    return result


def require_nonnegative_int(value, label: str):
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} is not a nonnegative integer")


def check_integer_map(value, keys, label: str):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label} has malformed schema")
    for key, item in value.items():
        require_nonnegative_int(item, f"{label}.{key}")


def parse_b_shard(path: Path, data: bytes, count: int):
    row = strict_json(data, str(path))
    top = {
        "algorithm", "branch_values_and_fast_stats", "candidate", "common_r",
        "family_stats", "format", "geometry", "kernel_stats", "peak_rss_kib",
        "producer_sha256", "rigorous", "scaled_b_shard", "scaling",
        "serialized_matrices_read", "source_hashes", "status", "timing_seconds",
    }
    if (type(row) is not dict or set(row) != top or
            row.get("format") !=
                "D14-grid38-scaled-cutoff-cross-common-r-collected-v5" or
            row.get("status") !=
                "EXACT COLLECTED COMMON-r CROSS SHARD PASS" or
            row.get("rigorous") is not True or row.get("common_r") != count or
            type(row.get("common_r")) is not int or
            row.get("producer_sha256") != PINNED[B_RUNNER] or
            row.get("serialized_matrices_read") is not False or
            row.get("algorithm") != B_ALGORITHM):
        raise ValueError(f"b shard identity mismatch: {path}")
    scaling = row.get("scaling", {})
    geometry = row.get("geometry", {})
    expected_scaling = {
        "inner_F": str(SCALE_F), "outer_H": str(SCALE_H),
        "b_factor": str(SCALE_F * SCALE_H),
        "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
    }
    expected_geometry = {
        "k": K, "delta": str(DELTA), "alpha1": str(ALPHA1),
        "alpha2": str(ALPHA2), "eta": str(ETA),
        "natural_dilation_alpha1_over_alpha2": str(DILATION),
        "schedule": list(map(str, SCHEDULE)),
        "definition5_cutoff_retained": True,
    }
    expected_candidate = {
        "inner": "pinned strict cache-free exact D19 v2",
        "outer": "D14_grid_1e-38", "inner_basis_dimension": 568,
        "outer_basis_dimension": 195,
        "inner_common_denominator_lcm": str(SCALE_F),
        "outer_common_denominator_lcm": str(SCALE_H),
        "dilation_point_check": True,
    }
    if (scaling != expected_scaling or geometry != expected_geometry or
            row.get("candidate") != expected_candidate):
        raise ValueError(f"b shard scale/geometry mismatch: {path}")
    if row.get("source_hashes") != B_SOURCE_HASHES:
        raise ValueError(f"b shard source closure mismatch: {path}")

    value = canonical_q(row.get("scaled_b_shard"), f"b[{count}]")
    diagnostics = row.get("branch_values_and_fast_stats", {})
    if type(diagnostics) is not dict or set(diagnostics) != {
            "high", "low", "high_stats", "low_stats",
            "integer_radialization", "timing_seconds"}:
        raise ValueError(f"b branch diagnostics malformed: {path}")
    high_expected = expected_branches(ALPHA2, count)
    low_expected = expected_branches(ALPHA1, count)
    high = diagnostics["high"]
    low = diagnostics["low"]
    if (type(high) is not dict or type(low) is not dict or
            set(high) != high_expected or set(low) != low_expected):
        raise ValueError(f"b branch inventory mismatch: {path}")
    high_total = sum((canonical_q(term, f"b[{count}].high.{branch}")
                      for branch, term in high.items()), Q(0))
    low_total = sum((canonical_q(term, f"b[{count}].low.{branch}")
                     for branch, term in low.items()), Q(0))
    if K * (high_total - low_total) != value:
        raise ArithmeticError(f"b branch recombination mismatch: {path}")

    stat_keys = {
        "active_shifts", "packed_terms", "tag_groups",
        "collected_affine_terms", "requested_moments", "scalar_products",
        "nonzero_product_monomials", "cancelled_product_monomials",
        "maximum_affine_denominator_bits", "maximum_moment_denominator_bits",
    }
    for side, expected in (("high_stats", high_expected),
                           ("low_stats", low_expected)):
        stats = diagnostics[side]
        if type(stats) is not dict or set(stats) != expected:
            raise ValueError(f"b statistics branch mismatch: {path}")
        for branch, branch_stats in stats.items():
            check_integer_map(branch_stats, stat_keys,
                              f"b[{count}].{side}.{branch}")
            if (branch_stats["requested_moments"] !=
                    branch_stats["nonzero_product_monomials"] or
                    branch_stats["scalar_products"] <
                    branch_stats["nonzero_product_monomials"] or
                    branch_stats["scalar_products"] <
                    branch_stats["collected_affine_terms"]):
                raise ArithmeticError(f"b collection inventory mismatch: {path}")

    require_nonnegative_int(row.get("peak_rss_kib"), f"b[{count}].peak_rss")
    return value


def encode(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value


def build(a_dir: Path, b_dir: Path, snapshots):
    inner = strict_json(snapshots[INNER_RESULT], str(INNER_RESULT))
    if (inner.get("status") != "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS" or
            inner.get("rigorous") is not True or inner.get("k") != K or
            inner.get("deficit_positive") is not True or
            inner.get("denominator_positive") is not True):
        raise ValueError("inner result identity mismatch")
    inner_i = canonical_q(inner.get("exact_denominator"), "inner I")
    inner_j48 = canonical_q(inner.get("exact_numerator"), "inner 48J")
    inner_d = canonical_q(inner.get("exact_deficit"), "inner deficit")
    if inner_i - inner_j48 != inner_d or inner_i <= 0 or inner_d <= 0:
        raise ArithmeticError("inner exact-form relation mismatch")

    a_paths = require_exact_files(a_dir, "r")
    b_paths = require_exact_files(b_dir, "common_r_")
    a_rows = []
    b_rows = []
    for count, path in zip(COUNTS, a_paths, strict=True):
        data = path.read_bytes()
        a_rows.append((count, parse_a_shard(path, data, count), digest(data)))
    for count, path in zip(COUNTS, b_paths, strict=True):
        data = path.read_bytes()
        b_rows.append((count, parse_b_shard(path, data, count), digest(data)))

    a_value = sum((value for _, value, _ in a_rows), Q(0))
    b_value = sum((value for _, value, _ in b_rows), Q(0))
    i_scaled = inner_i * FORM_SCALE
    d_scaled = inner_d * FORM_SCALE
    margin = b_value**2 - a_value * d_scaled
    denominator = a_value * i_scaled + b_value**2
    if a_value <= 0 or i_scaled <= 0 or denominator <= 0:
        raise ArithmeticError("certificate denominator is nonpositive")
    quotient_margin_lower_bound = margin / denominator
    projected_energy = b_value**2 / (a_value * i_scaled)
    return {
        "format": "H1-236-one-band-exact-shard-aggregate-v1",
        "status": ("EXACT ONE-BAND SCALAR CERTIFICATE PASS" if margin > 0
                   else "EXACT ONE-BAND SCALAR CERTIFICATE FAIL"),
        "rigorous": True,
        "theorem_ready_scalar": margin > 0,
        "k": K,
        "counts": list(COUNTS),
        "scales": {"F": str(SCALE_F), "H": str(SCALE_H),
                   "quadratic_inner": str(FORM_SCALE)},
        "exact": {
            "A_scaled": a_value,
            "b_scaled": b_value,
            "I_F_scaled": i_scaled,
            "D_scaled": d_scaled,
            "margin_b_squared_minus_A_D": margin,
            "mixing_coefficient_b_over_A": b_value / a_value,
            "normalized_inner_deficit": d_scaled / i_scaled,
            "normalized_projected_energy": projected_energy,
            "quotient_margin_lower_bound": quotient_margin_lower_bound,
            "quotient_lower_bound": Q(1) + quotient_margin_lower_bound,
        },
        "a_shards": [{"count": count, "value": value, "sha256": sha}
                     for count, value, sha in a_rows],
        "b_shards": [{"count": count, "value": value, "sha256": sha}
                     for count, value, sha in b_rows],
        "source_hashes": {str(path.relative_to(REPO)): expected
                          for path, expected in PINNED.items()},
        "trust_scope": ("aggregates validated immutable shards; independent "
                        "integration replay and analytic audit remain separate"),
    }


def canonical_json(value) -> bytes:
    return (json.dumps(encode(value), sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def publish_exclusive(path: Path, payload: bytes):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-dir", type=Path, default=DEFAULT_A_DIR)
    parser.add_argument("--b-dir", type=Path, default=DEFAULT_B_DIR)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-self-sha256", required=True)
    args = parser.parse_args(argv)
    self_data = FILE.read_bytes()
    if digest(self_data) != args.expected_self_sha256:
        raise RuntimeError("assembler source does not match external pin")
    snapshots = {path: path.read_bytes() for path in PINNED}
    for path, expected in PINNED.items():
        if digest(snapshots[path]) != expected:
            raise RuntimeError(f"pinned dependency changed: {path}")
    result = build(args.a_dir, args.b_dir, snapshots)
    if (FILE.read_bytes() != self_data or
            any(path.read_bytes() != data for path, data in snapshots.items())):
        raise RuntimeError("assembler source closure changed")
    result["assembler_sha256"] = args.expected_self_sha256
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(digest(payload), args.output)
    return 0 if result["theorem_ready_scalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
