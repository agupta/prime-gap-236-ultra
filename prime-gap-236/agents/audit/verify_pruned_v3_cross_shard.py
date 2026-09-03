#!/usr/bin/env python3
"""Fail-closed structural/result checker for frozen pruned-v3 cross shards.

This checker does not import the production runner or either scalar backend.
It reconstructs the active Definition-5 branch inventory from exact frozen
geometry, checks the complete serialized production-source closure, derives
the last nonempty inclusion--exclusion shift, and recombines every exact
branch value with the factor k exactly once.  An optional frozen fast-v2 shard
provides an exact result-level replay comparison without rerunning integration.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
PRODUCER = "agents/exact-projection-engine/d14_grid38_scaled_b_shard_pruned_v3.py"
PRODUCER_SHA = "ce5236eaed52be549a316587e8c3c543a0b02b1594c14ba32f4c1a877fd9bb26"
SOURCE_HASHES = {
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard.py":
        "deceb6c6248fa97e65c9ce5a604081f3b05f0b7c838dea2f1d1c525a59bea905",
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_fast_v2.py":
        "4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3",
    "agents/exact-projection-engine/fast_tagged_scalar.py":
        "5d9d82ae7b097a40b852a8471e281d5bd5ad69d08240e1a73d3928e21a40aaa2",
    "agents/exact-projection-engine/pruned_integer_radial.py":
        "834f624647094bf71364ad5c2b47e00371c7e7e78ed37c1d06eeca9186f73afe",
    "agents/exact-projection-engine/symmetric_cutoff_cross.py":
        "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    "agents/exact-projection-engine/test_pruned_integer_radial.py":
        "17b5eac692f859728d502e90a52b2c9c5ce03ef45e7966ce9104d8878910adfd",
    "agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py":
        "855b3e07ee71f75917a9ddceb2d969e10aab8c81550aa036423f7104eb5ef78d",
    "agents/exact-projection-engine/test_symmetric_cutoff_cross.py":
        "d2898ef57898e1a3dc5b752a842bcc1b04bd234a4575342a804b0dcf1f44be26",
    "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py":
        "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
    "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json":
        "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170",
    "verify/check_bv_rational_vector_direct_v2.py":
        "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5",
    "agents/audit/verify_bv_D19_krylov20_direct_v2_strict_audit.py":
        "3e1b552e31d1f21deac70e4c114618b6853677ed5482c2c53597fdbbc5cf7a1f",
    "agents/audit/results/bv_D19_krylov20_direct_v2_strict_audit.json":
        "944c37ea2716a80e5ebaf99892d6ce6c025afc7a6fc913b9ffb507054baeeb35",
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json":
        "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py":
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
}
FAST_V2_PRODUCER_SHA = (
    "4613b0fb117bf58c732e9bdeb22fa9d847a1152cc1bcac3b8b92f584231709d3")
_V3_ONLY_SOURCES = {
    "agents/exact-projection-engine/d14_grid38_scaled_b_shard_fast_v2.py",
    "agents/exact-projection-engine/pruned_integer_radial.py",
    "agents/exact-projection-engine/test_pruned_integer_radial.py",
    "agents/exact-projection-engine/test_pruned_v3_exclusive_publish.py",
}
FAST_V2_SOURCE_HASHES = {
    key: value for key, value in SOURCE_HASHES.items()
    if key not in _V3_ONLY_SOURCES
}

K = 48
DELTA = Q(1, 60)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DILATION = Q(9270000, 9500917)
SCALE_F = 10**87
SCALE_H = 10**38
SCHEDULE = tuple(map(Q, (
    "1123/8000", "157041/1000000", "5267/31250",
    "87169/500000", "11593/62500", "1523/8000",
    "193097/1000000", "98573/500000", "202047/1000000",
    "20709/100000", "52917/250000", "52917/250000",
)))
BRANCHES = {"Sdelta", "Stotal", "Ltotal", "Lbig"}
RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def strict_load(data, name):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {name}")
            result[key] = value
        return result
    return json.loads(
        data, object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token {token!r} in {name}")))


def rational(value, where):
    if type(value) is not str or RATIONAL.fullmatch(value) is None:
        raise ValueError(f"{where} is not a canonical rational string")
    result = Q(value)
    if str(result) != value:
        raise ValueError(f"{where} is not reduced/canonical")
    return result


def positive_integer_string(value, where):
    result = rational(value, where)
    if result.denominator != 1 or result <= 0:
        raise ValueError(f"{where} is not a positive integer")
    return result.numerator


def require_nonnegative_int(value, where):
    if type(value) is not int or value < 0:
        raise ValueError(f"{where} is not a nonnegative integer")


def check_integer_map(value, keys, where):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{where} has malformed schema")
    for key, item in value.items():
        require_nonnegative_int(item, f"{where}.{key}")


def beta(index):
    if index <= 0:
        raise ValueError("cap index must be positive")
    return SCHEDULE[min(index, len(SCHEDULE)) - 1]


def expected_branches(alpha, r):
    cutoff = ETA - r * DELTA
    if cutoff <= 0:
        return set()
    shared_cap = None if r == 0 else beta(r) - r * DELTA
    result = set()
    small_total_bound = min(cutoff, alpha - (r + 1) * DELTA)
    if (shared_cap is None or shared_cap > 0) and small_total_bound > 0:
        result.add("Sdelta")
    if ((shared_cap is None or shared_cap > 0)
            and cutoff > alpha - (r + 1) * DELTA):
        result.add("Stotal")
    large_cap = beta(r + 1) - (r + 1) * DELTA
    if large_cap > 0:
        if min(cutoff, alpha - (r + 1) * DELTA) > 0:
            result.add("Ltotal")
        result.add("Lbig")
    return result


def maximum_active_shift(cutoff):
    """Largest integer h with h*delta < cutoff (equality is null)."""
    quotient = cutoff / DELTA
    return (quotient.numerator + quotient.denominator - 1) // \
        quotient.denominator - 1


def check_branch_stats(stats, expected, where):
    if type(stats) is not dict or set(stats) != expected:
        raise ValueError(f"{where} branch stats disagree with exact geometry")
    keys = {
        "active_shifts", "packed_terms", "tag_groups",
        "collected_affine_terms", "requested_moments", "scalar_products",
    }
    for branch, row in stats.items():
        check_integer_map(row, keys, f"{where}.{branch}")


def audit(path, fast_v2_reference=None):
    raw_bytes = path.read_bytes()
    raw = strict_load(raw_bytes, str(path))
    canonical = (json.dumps(
        raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False) + "\n").encode("ascii")
    if canonical != raw_bytes:
        raise ValueError("shard is not canonical JSON")
    top = {
        "algorithm", "branch_values_and_fast_stats", "candidate", "common_r",
        "family_stats", "format", "geometry", "kernel_stats", "peak_rss_kib",
        "producer_sha256", "rigorous", "scaled_b_shard", "scaling",
        "serialized_matrices_read", "source_hashes", "status", "timing_seconds",
    }
    if type(raw) is not dict or set(raw) != top:
        raise ValueError("unexpected or incomplete top-level shard schema")
    if (raw["format"] != "D14-grid38-scaled-cutoff-cross-common-r-pruned-v3"
            or raw["status"] != "EXACT PRUNED COMMON-r CROSS SHARD PASS"
            or raw["rigorous"] is not True
            or raw["serialized_matrices_read"] is not False
            or raw["producer_sha256"] != PRODUCER_SHA):
        raise ValueError("shard identity/status mismatch")
    r = raw["common_r"]
    if type(r) is not int or not 0 <= r <= 12:
        raise ValueError("invalid common_r")

    if raw["geometry"] != {
        "k": K, "delta": str(DELTA), "alpha1": str(ALPHA1),
        "alpha2": str(ALPHA2), "eta": str(ETA),
        "natural_dilation_alpha1_over_alpha2": str(DILATION),
        "schedule": list(map(str, SCHEDULE)),
        "definition5_cutoff_retained": True,
    }:
        raise ValueError("frozen geometry mismatch")
    if raw["scaling"] != {
        "inner_F": str(SCALE_F), "outer_H": str(SCALE_H),
        "b_factor": str(SCALE_F * SCALE_H),
        "invariant": "b_scaled^2/A_scaled = 10^174*(b^2/A)",
    }:
        raise ValueError("scaling metadata mismatch")
    if raw["candidate"] != {
        "inner": "pinned strict cache-free exact D19 v2",
        "outer": "D14_grid_1e-38", "inner_basis_dimension": 568,
        "outer_basis_dimension": 195,
        "inner_common_denominator_lcm": str(SCALE_F),
        "outer_common_denominator_lcm": str(SCALE_H),
        "dilation_point_check": True,
    }:
        raise ValueError("candidate metadata mismatch")
    if raw["algorithm"] != {
        "family_common_denominator_integer_accumulation": True,
        "radial_common_denominator_integer_accumulation": True,
        "affine_products_collected_once_per_tag_and_shift": True,
        "empty_shifts_pruned_inside_small_coordinate_convolution": True,
        "coefficient_level_reference_transform_equality_in_pinned_tests": True,
        "full_low_k_fast_v2_branch_equality_in_pinned_tests": True,
    }:
        raise ValueError("algorithm metadata mismatch")
    if raw["source_hashes"] != SOURCE_HASHES:
        raise ValueError("serialized source closure mismatch")
    if sha256((REPO / PRODUCER).read_bytes()) != PRODUCER_SHA:
        raise ValueError("live producer hash mismatch")
    for relative, digest in SOURCE_HASHES.items():
        if sha256((REPO / relative).read_bytes()) != digest:
            raise ValueError(f"live source hash mismatch: {relative}")

    check_integer_map(raw["kernel_stats"], {
        "marginal_terms", "distinguished_components", "input_pairs",
        "expanded_orbit_products", "output_orbits", "output_kernel_terms",
    }, "kernel_stats")
    kernel = raw["kernel_stats"]
    if (min(kernel.values()) <= 0
            or kernel["input_pairs"] !=
                kernel["marginal_terms"] * kernel["distinguished_components"]
            or kernel["expanded_orbit_products"] < kernel["output_kernel_terms"]
            or kernel["output_kernel_terms"] < kernel["output_orbits"]):
        raise ArithmeticError("kernel inventory relation failed")

    families = raw["family_stats"]
    if type(families) is not dict or set(families) != {
            "source_kernel_terms", "literal_antiderivative_expansions",
            "family_tag_counts", "family_orbit_tag_entries"}:
        raise ValueError("family_stats has malformed schema")
    require_nonnegative_int(families["source_kernel_terms"],
                            "family_stats.source_kernel_terms")
    require_nonnegative_int(families["literal_antiderivative_expansions"],
                            "family_stats.literal_antiderivative_expansions")
    family_names = {"small", "small_total", "large"}
    check_integer_map(families["family_tag_counts"], family_names,
                      "family_stats.family_tag_counts")
    check_integer_map(families["family_orbit_tag_entries"], family_names,
                      "family_stats.family_orbit_tag_entries")
    if (families["source_kernel_terms"] != kernel["output_kernel_terms"]
            or families["literal_antiderivative_expansions"] <=
                families["source_kernel_terms"]
            or min(families["family_tag_counts"].values()) <= 0
            or min(families["family_orbit_tag_entries"].values()) <= 0):
        raise ArithmeticError("primitive-family inventory relation failed")

    block = raw["branch_values_and_fast_stats"]
    if type(block) is not dict or set(block) != {
            "high", "low", "high_stats", "low_stats",
            "integer_radialization", "timing_seconds"}:
        raise ValueError("malformed diagnostic block")
    high_expected = expected_branches(ALPHA2, r)
    low_expected = expected_branches(ALPHA1, r)
    if set(block["high"]) != high_expected or set(block["low"]) != low_expected:
        raise ValueError("branch names disagree with exact Definition-5 geometry")
    if not high_expected.issubset(BRANCHES) or not low_expected.issubset(BRANCHES):
        raise ValueError("unknown branch name")
    high = {key: rational(value, f"high.{key}")
            for key, value in block["high"].items()}
    low = {key: rational(value, f"low.{key}")
           for key, value in block["low"].items()}
    check_branch_stats(block["high_stats"], high_expected, "high_stats")
    check_branch_stats(block["low_stats"], low_expected, "low_stats")
    observed = rational(raw["scaled_b_shard"], "scaled_b_shard")
    if observed != K * (sum(high.values(), Q(0)) - sum(low.values(), Q(0))):
        raise ArithmeticError("branches do not recombine with factor 48")

    integer = block["integer_radialization"]
    if type(integer) is not dict or set(integer) != {
            "family_denominator", "radial_denominator",
            "combined_denominator_bits", "clear_stats", "radial_stats"}:
        raise ValueError("malformed denominator restoration metadata")
    family_den = positive_integer_string(integer["family_denominator"],
                                         "family_denominator")
    radial_den = positive_integer_string(integer["radial_denominator"],
                                         "radial_denominator")
    if integer["combined_denominator_bits"] != \
            (family_den * radial_den).bit_length():
        raise ArithmeticError("combined denominator bit length mismatch")
    check_integer_map(integer["clear_stats"], {
        "family_coefficients", "common_denominator_bits",
    }, "integer_radialization.clear_stats")
    check_integer_map(integer["radial_stats"], {
        "orbit_tag_associations", "orbit_transforms", "transform_terms",
        "radial_denominator_bits", "distributed_terms", "packed_nonzero_terms",
        "maximum_shift_pruned_inside_convolution",
    }, "integer_radialization.radial_stats")
    clear = integer["clear_stats"]
    radial = integer["radial_stats"]
    expected_h = maximum_active_shift(ETA - r * DELTA)
    if expected_h != 14 - r or \
            radial["maximum_shift_pruned_inside_convolution"] != expected_h:
        raise ArithmeticError("maximum pruned shift is not exact H=14-r")
    expected_coefficients = sum(families["family_orbit_tag_entries"].values())
    if (clear["common_denominator_bits"] != family_den.bit_length()
            or radial["radial_denominator_bits"] != radial_den.bit_length()
            or clear["family_coefficients"] != expected_coefficients
            or radial["orbit_tag_associations"] != expected_coefficients
            or radial["orbit_transforms"] <= 0 or radial["transform_terms"] <= 0
            or radial["distributed_terms"] < radial["packed_nonzero_terms"]
            or radial["packed_nonzero_terms"] <= 0):
        raise ArithmeticError("integer radial inventory relation failed")

    timing = raw["timing_seconds"]
    if type(timing) is not dict or set(timing) != {
            "marginal_and_components", "global_kernel", "primitive_families",
            "integer_radialize_and_collected_integrate", "total"}:
        raise ValueError("malformed timing_seconds")
    nested = block["timing_seconds"]
    if type(nested) is not dict or set(nested) != {
            "clear_family_denominators", "radialize_integer",
            "integrate_collected_affines"}:
        raise ValueError("malformed nested timing_seconds")
    for where, values in (("timing_seconds", timing),
                          ("nested timing_seconds", nested)):
        if any(type(value) not in (int, float) or isinstance(value, bool)
               or not math.isfinite(value) or value < 0
               for value in values.values()):
            raise ValueError(f"malformed {where}")
    if timing["total"] < max(value for key, value in timing.items()
                               if key != "total"):
        raise ArithmeticError("total timing smaller than a component")
    require_nonnegative_int(raw["peak_rss_kib"], "peak_rss_kib")

    replay_equal = None
    reference_sha = None
    if fast_v2_reference is not None:
        reference_bytes = fast_v2_reference.read_bytes()
        reference = strict_load(reference_bytes, str(fast_v2_reference))
        canonical_reference = (json.dumps(
            reference, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
        if reference_bytes != canonical_reference:
            raise ValueError("fast-v2 reference is not canonical JSON")
        if (type(reference) is not dict or set(reference) != top
                or reference.get("format") !=
                "D14-grid38-scaled-cutoff-cross-common-r-fast-v2"
                or reference.get("status") !=
                "EXACT FAST COMMON-r CROSS SHARD PASS"
                or reference.get("rigorous") is not True
                or reference.get("serialized_matrices_read") is not False
                or reference.get("producer_sha256") != FAST_V2_PRODUCER_SHA
                or reference.get("common_r") != r):
            raise ValueError("fast-v2 reference identity/count mismatch")
        if (reference.get("source_hashes") != FAST_V2_SOURCE_HASHES
                or reference.get("geometry") != raw["geometry"]
                or reference.get("scaling") != raw["scaling"]
                or reference.get("candidate") != raw["candidate"]
                or reference.get("algorithm") != {
                    "family_common_denominator_integer_accumulation": True,
                    "radial_common_denominator_integer_accumulation": True,
                    "affine_products_collected_once_per_tag_and_shift": True,
                    "small_k_reference_and_literal_equality_in_pinned_tests": True,
                }):
            raise ValueError("fast-v2 reference source/metadata mismatch")
        reference_block = reference.get("branch_values_and_fast_stats", {})
        if (reference.get("scaled_b_shard") != raw["scaled_b_shard"]
                or reference_block.get("high") != block["high"]
                or reference_block.get("low") != block["low"]
                or reference_block.get("high_stats") != block["high_stats"]
                or reference_block.get("low_stats") != block["low_stats"]
                or reference.get("kernel_stats") != raw["kernel_stats"]
                or reference.get("family_stats") != raw["family_stats"]
                or reference_block.get("integer_radialization", {}).get(
                    "family_denominator") != integer["family_denominator"]):
            raise ArithmeticError("pruned-v3 and fast-v2 exact outputs differ")
        replay_equal = True
        reference_sha = sha256(reference_bytes)

    return {
        "status": "PRUNED-V3 CROSS SHARD STRUCTURAL/RESULT AUDIT PASS",
        "input_sha256": sha256(raw_bytes), "common_r": r,
        "scaled_b_shard": str(observed), "recombined_exactly": True,
        "maximum_active_shift": expected_h,
        "family_denominator_bits": family_den.bit_length(),
        "radial_denominator_bits": radial_den.bit_length(),
        "source_closure_verified": True,
        "fast_v2_result_exactly_equal": replay_equal,
        "fast_v2_reference_sha256": reference_sha,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--fast-v2-reference", type=Path)
    parser.add_argument("shard", type=Path)
    args = parser.parse_args()
    if args.expected_self_sha256 is not None and \
            sha256(FILE.read_bytes()) != args.expected_self_sha256:
        raise RuntimeError("externally pinned checker SHA mismatch")
    result = audit(args.shard, args.fast_v2_reference)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
