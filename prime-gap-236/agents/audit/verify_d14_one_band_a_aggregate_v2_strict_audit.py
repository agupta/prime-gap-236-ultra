#!/usr/bin/env python3
"""Independent fail-closed audit of the strict-v2 exact D14 A aggregate.

No production A producer or assembler is imported.  Every count shard is
strictly decoded and hash-pinned, its exact support subtraction is redone,
and all aggregate fields are reconstructed with ``fractions.Fraction``.
Optionally, all thirteen independent radial-replay outputs are required and
matched separately at their high, low, and band values.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import re


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
AGGREGATE = (REPO / "agents/structural-basis/results/"
             "d14_one_band_a_aggregate_exact_v2_strict.json")
AGGREGATE_SHA = "e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44"
ASSEMBLER = "agents/structural-basis/code/assemble_exact_d14_one_band_a_v2.py"
ASSEMBLER_SHA = "b7ef412482642221dd9b5ff1beab23e4dc9545fc9905edade06fa71236c0b6bd"
BASE_ASSEMBLER = "agents/structural-basis/code/assemble_exact_d14_one_band_a_v1.py"
BASE_ASSEMBLER_SHA = "5086d25b5c16c9462d27e9c6e6afb628627b4671ca9710a932928467f66c4fa4"
PRODUCER = "agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py"
PRODUCER_SHA = "2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d"
PRODUCER_TEST = "agents/structural-basis/tests/test_exact_d14_one_band_a_shard_v2.py"
PRODUCER_TEST_SHA = "4d5402a8e9940755ca18e69c5a346426bc6081d78ea5206236191dc34e527afc"
D19_CHECKER = "verify/check_bv_rational_vector_direct_v2.py"
D19_CHECKER_SHA = "ff2046ce180394a6328fdec2c112d575a4c540ff964f5dede28c6db6091506c5"
D19_RESULT = "verify/results/bv_D19_krylov20_direct_exact_v2_strict.json"
D19_RESULT_SHA = "8b0d47b22b09c057633022682332f0de4b7e47d4b6ab6d630690be081c58e170"
D19_TEST = "verify/test_check_bv_rational_vector_direct_v2.py"
D19_TEST_SHA = "5f03f8cdbc9235dd739c36901fab42cd44216b1213009fd019dfb1ae32fa6d27"
RADIAL_CHECKER_SHA = "e51a8719b4665dc2e38c454f467abfc8b894410d53b3882dd931c7ed82e37666"
SHARD_DIRECTORY = REPO / "agents/structural-basis/results/d14_one_band_a_shards_v2"
SHARD_SHA = {
    0: "b43fea383f5a532bc1174da9d07ede765b2238151ef8fc7a3297803aabb197ac",
    1: "0d56cac302ada1c43626b9fa25370ecbfe9cca817b0b9d9580e80a38b7059c50",
    2: "99403ede00f6b0bb9afd00251c05200554f338232a0f33c0dcbddf6454f59604",
    3: "1ced47fda178b15ebd405b2f4d7cc68ef6a46d491e6455e721a1ec7ab63734a1",
    4: "d6ad1881bd72ba689ce6cdfbb0f89bc235de6a49cde429c9ddda17cf72b5b873",
    5: "668837da7c42a4e2c94ca66ff37af037842bde5a321c9e03d44cd1bd8106cc1b",
    6: "46132be3d60594bf136ec2cc00717b048ba6a98f160e12a0ae970081b9449e36",
    7: "9d0c25c491eda9bf19f485a0bfd923847fa24f0491f01b55cf053d8fbbb27fd2",
    8: "5037b9b3bd3d99dca1fde7af3cd3b451a9a3300600f199a17192056d075927e2",
    9: "a62afca686e2fe53f236d56613a3b6ff2eebdffd036252ba46be3ba65a638632",
    10: "27f2a7fd8e191af4d12982dde944dd2bf7f65db1b05d4196205ccc734a9c1904",
    11: "7785883eebaea8d3d1a441fb6cf32b1cd8f0fa4bb060f87970391fdb8ae47b0c",
    12: "3f288aa603498644a07e2fbcc34bc90e37f14b58c68c68171c2b4d81cf2ab1ca",
}
SHARD_SOURCE_HASHES = {
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
AGGREGATE_SOURCE_HASHES = {
    BASE_ASSEMBLER: BASE_ASSEMBLER_SHA, PRODUCER: PRODUCER_SHA,
    PRODUCER_TEST: PRODUCER_TEST_SHA, D19_CHECKER: D19_CHECKER_SHA,
    D19_RESULT: D19_RESULT_SHA, D19_TEST: D19_TEST_SHA,
}
RADIAL_SOURCE_HASHES = {
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/exact-projection-engine/symmetric_cutoff_cross.py":
        "d3aa9c1793a6c1d7e9ad2b71cb2d81dee690e7d9aaaea56134c428a752967726",
    "agents/small-delta-frontier/frontier_active25_inner_d16_tagged_shell.py":
        "1393a2dd29e5660f10e632b19b6b5eeafe9363bf79b2cd4a8254049d1f9c669a",
    "agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json":
        "722082591e80d8e1634f974a9ca531903f176f540fbf5342821c062aaaf511a0",
    "verify/exact_capped_certificate.py":
        "1787e7b482a5c2982de56486bc774794f6e671b3db4d9ab7207ebb1c85dc079c",
}

COUNTS = tuple(range(13))
SCALE = 10**38
DILATION = Q(9270000, 9500917)
ALPHA1 = Q(103, 400)
ALPHA2 = Q(9500917, 36000000)
ETA = Q(8960917, 36000000)
DELTA = Q(1, 60)
SCHEDULE12 = tuple(map(Q, (
    "1123/8000", "157041/1000000", "5267/31250",
    "87169/500000", "11593/62500", "1523/8000",
    "193097/1000000", "98573/500000", "202047/1000000",
    "20709/100000", "52917/250000", "52917/250000",
)))
SCHEDULE48 = SCHEDULE12 + (SCHEDULE12[-1],) * 36
RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


def sha256(data):
    if isinstance(data, (str, Path)):
        data = Path(data).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_load(data, name):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {name}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ValueError(f"nonfinite token {token!r} in {name}")))


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def load_canonical(path, expected_hash=None):
    data = path.read_bytes()
    if expected_hash is not None and sha256(data) != expected_hash:
        raise ValueError(f"hash mismatch: {path}")
    value = strict_load(data, str(path))
    if canonical(value) != data:
        raise ValueError(f"noncanonical JSON: {path}")
    return value, data


def rational(token, where):
    if type(token) is not str or RATIONAL.fullmatch(token) is None:
        raise ValueError(f"noncanonical rational syntax at {where}")
    value = Q(token)
    if str(value) != token:
        raise ValueError(f"nonreduced rational at {where}")
    return value


def decimal(value, digits=60):
    value = Q(value)
    with localcontext() as context:
        context.prec = digits
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".45E")


def live_hashes(expected):
    for relative, digest in expected.items():
        if sha256(REPO / relative) != digest:
            raise ValueError(f"live source hash mismatch: {relative}")


def finite_nonnegative_float(value, where):
    if (type(value) not in (int, float) or isinstance(value, bool)
            or not math.isfinite(value) or value < 0):
        raise ValueError(f"invalid nonnegative finite number at {where}")


def validate_shard(count, row):
    top = {
        "active_counts", "base_source_sha256", "basis_dimension", "cache_read",
        "candidate", "checkpoint_unit", "checks", "claim_scope", "count",
        "degree", "elapsed_seconds", "exact_values", "fine_grid_status", "format",
        "geometry", "inventory", "k", "launch_authorized", "memory_limit_bytes",
        "one_band_status", "peak_rss_kib", "resume_supported", "rigorous",
        "serialized_matrix_entries_read", "source_hashes", "source_sha256",
        "status", "target_kind", "theorem_ready", "time_limit_seconds",
    }
    if type(row) is not dict or set(row) != top:
        raise ValueError(f"shard top-level schema mismatch at r={count}")
    if (row["format"] != "exact-d14-one-band-a-count-shard-v2"
            or row["status"] != "EXACT D14 ONE-BAND A COUNT SHARD PASS"
            or row["rigorous"] is not True or row["count"] != count
            or row["active_counts"] != list(COUNTS) or row["k"] != 48
            or row["degree"] != 14 or row["basis_dimension"] != 195
            or row["source_sha256"] != PRODUCER_SHA
            or row["base_source_sha256"] !=
                SHARD_SOURCE_HASHES[
                    "agents/structural-basis/code/exact_d14_one_band_a_shard_v1.py"]
            or row["source_hashes"] != SHARD_SOURCE_HASHES
            or row["cache_read"] is not False
            or row["serialized_matrix_entries_read"] is not False
            or row["resume_supported"] is not False
            or row["theorem_ready"] is not False
            or row["launch_authorized"] is not True
            or row["memory_limit_bytes"] != 805306368
            or row["time_limit_seconds"] != 1200):
        raise ValueError(f"shard identity/provenance mismatch at r={count}")
    finite_nonnegative_float(row["elapsed_seconds"], f"r{count}.elapsed")
    if type(row["peak_rss_kib"]) is not int or row["peak_rss_kib"] <= 0:
        raise ValueError(f"invalid shard RSS at r={count}")

    geometry = row["geometry"]
    if geometry != {
        "alpha1": str(ALPHA1), "alpha2": str(ALPHA2),
        "band": "alpha1 <= sum(t) < alpha2, boundaries immaterial",
        "delta": str(DELTA), "eta": str(ETA),
        "schedule": list(map(str, SCHEDULE48)),
        "schedule_extension": "terminal plateau through count 48",
    }:
        raise ValueError(f"geometry mismatch at r={count}")
    inventory = row["inventory"]
    if inventory != {
        "high_faces": 16 - count, "low_faces": 16 - count,
        "shared_density_faces": 16 - count,
        "square_orbit_partition_groups": 508,
        "square_residual_terms_per_support": 3034, "workers": 1,
    }:
        raise ValueError(f"face/orbit inventory mismatch at r={count}")
    if (type(row["checks"]) is not dict or set(row["checks"]) != {
            "band_square_positive", "high_support_square_positive",
            "integer_vector_scale_and_dilation_commute",
            "low_support_square_positive",
            "natural_dilation_two_expansions_equal",
            "nested_supports_same_schedule", "paired_face_density_reuse",
            "termwise_vs_grouped_constant_volume_equal"}
            or any(value is not True for value in row["checks"].values())):
        raise ValueError(f"shard check inventory mismatch at r={count}")

    candidate = row["candidate"]
    if type(candidate) is not dict or set(candidate) != {
            "evaluation_vector_is_integral", "evaluation_vector_scale",
            "exact_full_simplex_48J", "exact_full_simplex_I",
            "exact_full_simplex_quotient", "grid_digits", "name",
            "natural_dilation", "rayleigh_scaling_invariant",
            "scaled_exact_full_simplex_48J", "scaled_exact_full_simplex_I",
            "scaled_vector_sha256", "vector_sha256"}:
        raise ValueError(f"candidate schema mismatch at r={count}")
    if (candidate["name"] != "D14_grid_1e-38"
            or candidate["grid_digits"] != 38
            or candidate["evaluation_vector_is_integral"] is not True
            or rational(candidate["evaluation_vector_scale"], "vector scale") != SCALE
            or rational(candidate["natural_dilation"], "dilation") != DILATION):
        raise ValueError(f"candidate identity mismatch at r={count}")
    full_i = rational(candidate["exact_full_simplex_I"], "full I")
    full_j = rational(candidate["exact_full_simplex_48J"], "full 48J")
    scaled_i = rational(candidate["scaled_exact_full_simplex_I"], "scaled full I")
    scaled_j = rational(candidate["scaled_exact_full_simplex_48J"], "scaled full 48J")
    quotient = rational(candidate["exact_full_simplex_quotient"], "full quotient")
    if (scaled_i != SCALE**2 * full_i or scaled_j != SCALE**2 * full_j
            or quotient != full_j / full_i):
        raise ArithmeticError(f"candidate full-simplex arithmetic mismatch at r={count}")

    values = row["exact_values"]
    if type(values) is not dict or set(values) != {
            "band_I_count", "band_I_count_decimal", "band_volume_count",
            "high_support_I_count", "high_support_volume_count",
            "low_support_I_count", "low_support_volume_count",
            "unscaled_band_I_count", "unscaled_band_I_count_decimal"}:
        raise ValueError(f"exact-values schema mismatch at r={count}")
    high = rational(values["high_support_I_count"], f"r{count}.high")
    low = rational(values["low_support_I_count"], f"r{count}.low")
    band = rational(values["band_I_count"], f"r{count}.band")
    unscaled = rational(values["unscaled_band_I_count"], f"r{count}.unscaled")
    high_volume = rational(values["high_support_volume_count"], f"r{count}.highvol")
    low_volume = rational(values["low_support_volume_count"], f"r{count}.lowvol")
    band_volume = rational(values["band_volume_count"], f"r{count}.bandvol")
    if (high - low != band or band != SCALE**2 * unscaled
            or high_volume - low_volume != band_volume
            or min(high, low, band, high_volume, low_volume, band_volume) <= 0):
        raise ArithmeticError(f"shard exact subtraction/scaling mismatch at r={count}")
    return (high, low, band, unscaled, high_volume, low_volume, band_volume,
            full_i, candidate)


def validate_radial_audit(directory, count, shard, values):
    path = directory / f"r{count:02d}.json"
    audit, data = load_canonical(path)
    top = {
        "arithmetic", "checked_counts", "checker_sha256", "elapsed_seconds",
        "independent_natural_dilation", "independent_orbit_square",
        "peak_rss_kib", "producer_imported", "producer_sha256", "rigorous",
        "rows", "serialized_matrix_entries_read", "source_hashes",
        "square_orbit_groups", "square_residual_terms", "status",
        "sum_scaled_band_I", "sum_unscaled_band_I",
    }
    if (type(audit) is not dict or set(audit) != top
            or audit["status"] !=
                "INDEPENDENT EXACT RADIAL A-v2 SHARD CHECK PASS"
            or audit["rigorous"] is not True
            or audit["checker_sha256"] != RADIAL_CHECKER_SHA
            or audit["producer_sha256"] != PRODUCER_SHA
            or audit["producer_imported"] is not False
            or audit["serialized_matrix_entries_read"] is not False
            or audit["independent_natural_dilation"] is not True
            or audit["independent_orbit_square"] is not True
            or audit["arithmetic"] != "fractions.Fraction only"
            or audit["square_orbit_groups"] != 508
            or audit["square_residual_terms"] != 3034
            or audit["source_hashes"] != RADIAL_SOURCE_HASHES
            or audit["checked_counts"] != [count]
            or type(audit["rows"]) is not list or len(audit["rows"]) != 1):
        raise ValueError(f"radial audit identity/schema mismatch at r={count}")
    row = audit["rows"][0]
    if (type(row) is not dict or set(row) != {
            "band_I_count", "count", "exact_band_equal", "exact_high_equal",
            "exact_low_equal", "high_support_I_count", "low_support_I_count",
            "shard_sha256"}
            or row["count"] != count or row["shard_sha256"] != SHARD_SHA[count]
            or row["exact_high_equal"] is not True
            or row["exact_low_equal"] is not True
            or row["exact_band_equal"] is not True
            or rational(row["high_support_I_count"], "audit high") != values[0]
            or rational(row["low_support_I_count"], "audit low") != values[1]
            or rational(row["band_I_count"], "audit band") != values[2]
            or rational(audit["sum_scaled_band_I"], "audit scaled sum") != values[2]
            or rational(audit["sum_unscaled_band_I"], "audit unscaled sum") != values[3]):
        raise ArithmeticError(f"radial replay mismatch at r={count}")
    finite_nonnegative_float(audit["elapsed_seconds"], "audit elapsed")
    if type(audit["peak_rss_kib"]) is not int or audit["peak_rss_kib"] <= 0:
        raise ValueError(f"invalid radial audit RSS at r={count}")
    return sha256(data)


def audit(radial_directory=None):
    aggregate, aggregate_bytes = load_canonical(AGGREGATE, AGGREGATE_SHA)
    live_hashes({ASSEMBLER: ASSEMBLER_SHA, **AGGREGATE_SOURCE_HASHES,
                 **SHARD_SOURCE_HASHES, **RADIAL_SOURCE_HASHES})
    rows, payloads, parsed = {}, {}, {}
    for count in COUNTS:
        path = SHARD_DIRECTORY / f"r{count:02d}.json"
        row, payload = load_canonical(path, SHARD_SHA[count])
        rows[count], payloads[count] = row, payload
        parsed[count] = validate_shard(count, row)
    if any(rows[count]["candidate"] != rows[0]["candidate"]
           or rows[count]["geometry"] != rows[0]["geometry"]
           for count in COUNTS[1:]):
        raise ValueError("candidate/geometry drift across count shards")

    high = sum((parsed[r][0] for r in COUNTS), Q(0))
    low = sum((parsed[r][1] for r in COUNTS), Q(0))
    exact_a = sum((parsed[r][2] for r in COUNTS), Q(0))
    unscaled_a = sum((parsed[r][3] for r in COUNTS), Q(0))
    high_volume = sum((parsed[r][4] for r in COUNTS), Q(0))
    low_volume = sum((parsed[r][5] for r in COUNTS), Q(0))
    band_volume = sum((parsed[r][6] for r in COUNTS), Q(0))
    if (high - low != exact_a or exact_a != SCALE**2 * unscaled_a
            or high_volume - low_volume != band_volume
            or min(high, low, exact_a, high_volume, low_volume, band_volume) <= 0):
        raise ArithmeticError("independent aggregate arithmetic failed")

    d19, _ = load_canonical(REPO / D19_RESULT, D19_RESULT_SHA)
    if (d19.get("status") != "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS"
            or d19.get("rigorous") is not True or d19.get("cache_read") is not False
            or d19.get("serialized_matrix_entries_read") is not False
            or d19.get("k") != 48 or d19.get("basis_degree") != 19
            or d19.get("basis_dimension") != 568
            or d19.get("checker_sha256") != D19_CHECKER_SHA):
        raise ValueError("strict D19 identity mismatch")
    inner_i = rational(d19["exact_denominator"], "D19 I")
    inner_deficit = rational(d19["exact_deficit"], "D19 deficit")
    normalized_deficit = rational(d19["exact_normalized_deficit"],
                                  "D19 normalized deficit")
    if inner_deficit / inner_i != normalized_deficit:
        raise ArithmeticError("D19 normalized deficit mismatch")
    full_i = parsed[0][7]

    top = {
        "A_over_D14_full_simplex_I", "A_over_D14_full_simplex_I_decimal",
        "A_stage_complete", "D19_inner_provenance", "b_launch_authorized",
        "b_stage_complete", "base_assembler", "cache_read", "checks",
        "claim_scope", "counts", "exact_A_scaled", "exact_A_scaled_decimal",
        "exact_A_unscaled", "exact_A_unscaled_decimal", "exact_band_volume",
        "exact_high_support_I_scaled", "exact_low_support_I_scaled", "format",
        "measured_max_shard_rss_kib", "measured_total_shard_seconds",
        "normalization", "producer", "provenance_repair", "resume_supported",
        "rigorous", "serialized_matrix_entries_read", "source_hashes",
        "source_sha256", "status", "theorem_ready",
    }
    if type(aggregate) is not dict or set(aggregate) != top:
        raise ValueError("aggregate top-level schema mismatch")
    if (aggregate["format"] != "exact-d14-one-band-a-aggregate-v2"
            or aggregate["status"] !=
                "EXACT D14 ONE-BAND A AGGREGATE STRICT-V2 PASS"
            or aggregate["rigorous"] is not True
            or aggregate["source_sha256"] != ASSEMBLER_SHA
            or aggregate["source_hashes"] != AGGREGATE_SOURCE_HASHES
            or aggregate["cache_read"] is not False
            or aggregate["serialized_matrix_entries_read"] is not False
            or aggregate["A_stage_complete"] is not True
            or aggregate["b_stage_complete"] is not False
            or aggregate["b_launch_authorized"] is not False
            or aggregate["resume_supported"] is not False
            or aggregate["theorem_ready"] is not False):
        raise ValueError("aggregate identity/provenance mismatch")
    if (aggregate["base_assembler"] != {
            "path": BASE_ASSEMBLER, "sha256": BASE_ASSEMBLER_SHA,
            "role": "hash-pinned A shard validation and exact summation"}
            or aggregate["producer"] != {
                "path": PRODUCER, "sha256": PRODUCER_SHA,
                "test_path": PRODUCER_TEST, "test_sha256": PRODUCER_TEST_SHA,
                "workers_per_shard": 1, "resume_supported": False}
            or aggregate["D19_inner_provenance"] != {
                "checker_path": D19_CHECKER, "checker_sha256": D19_CHECKER_SHA,
                "result_path": D19_RESULT, "result_sha256": D19_RESULT_SHA,
                "test_path": D19_TEST, "test_sha256": D19_TEST_SHA}):
        raise ValueError("aggregate nested provenance mismatch")
    if (type(aggregate["checks"]) is not dict
            or set(aggregate["checks"]) != {
                "aggregate_high_minus_low_equal_sum_of_band_shards",
                "aggregate_scaled_equals_10pow76_unscaled",
                "all_13_active_counts_present_once",
                "all_per_count_I_and_volume_values_positive",
                "all_per_count_high_minus_low_equal_band",
                "all_per_count_scaled_equals_10pow76_unscaled",
                "all_shards_canonical_and_hash_pinned",
                "candidate_and_geometry_identical_across_shards",
                "no_cache_or_serialized_matrix_entries"}
            or any(value is not True for value in aggregate["checks"].values())):
        raise ValueError("aggregate check inventory mismatch")
    if (rational(aggregate["exact_A_scaled"], "aggregate A") != exact_a
            or rational(aggregate["exact_A_unscaled"], "aggregate unscaled A") != unscaled_a
            or rational(aggregate["exact_high_support_I_scaled"], "aggregate high") != high
            or rational(aggregate["exact_low_support_I_scaled"], "aggregate low") != low
            or rational(aggregate["exact_band_volume"], "aggregate volume") != band_volume
            or rational(aggregate["A_over_D14_full_simplex_I"], "aggregate ratio")
                != exact_a / (SCALE**2 * full_i)
            or aggregate["exact_A_scaled_decimal"] != decimal(exact_a)
            or aggregate["exact_A_unscaled_decimal"] != decimal(unscaled_a)
            or aggregate["A_over_D14_full_simplex_I_decimal"] !=
                decimal(exact_a / (SCALE**2 * full_i))):
        raise ArithmeticError("aggregate exact/decimal values mismatch")

    expected_counts = [{
        "count": r,
        "path": f"agents/structural-basis/results/d14_one_band_a_shards_v2/r{r:02d}.json",
        "sha256": SHARD_SHA[r],
        "exact_A_scaled": rows[r]["exact_values"]["band_I_count"],
        "exact_A_unscaled": rows[r]["exact_values"]["unscaled_band_I_count"],
        "elapsed_seconds": rows[r]["elapsed_seconds"],
        "peak_rss_kib": rows[r]["peak_rss_kib"],
    } for r in COUNTS]
    if aggregate["counts"] != expected_counts:
        raise ValueError("aggregate count inventory differs from frozen shards")
    total_seconds = sum(float(rows[r]["elapsed_seconds"]) for r in COUNTS)
    max_rss = max(int(rows[r]["peak_rss_kib"]) for r in COUNTS)
    if (aggregate["measured_total_shard_seconds"] != total_seconds
            or aggregate["measured_max_shard_rss_kib"] != max_rss):
        raise ArithmeticError("aggregate timing/RSS inventory mismatch")

    normalization = aggregate["normalization"]
    if normalization != {
        "outer_H_scale": str(SCALE), "A_scale_factor": str(SCALE**2),
        "natural_dilation": str(DILATION), "D19_inner_I": str(inner_i),
        "D19_inner_deficit": str(inner_deficit),
        "D19_exact_normalized_deficit": str(normalized_deficit),
        "D19_exact_normalized_deficit_decimal": decimal(normalized_deficit),
        "future_certificate_expression": "b^2/(A*I_D19) - deficit/I_D19",
        "b_definition": "b=48J(F_D19,H_D14)",
    }:
        raise ValueError("aggregate normalization metadata mismatch")
    if aggregate["provenance_repair"] != {
        "replaced_aggregate_result":
            "agents/structural-basis/results/d14_one_band_a_aggregate_exact_v1.json",
        "replaced_aggregate_sha256":
            "1e0e8e35449a19ce83bfc37896f75431c61ea39ccb82abbf99eb5669319fae22",
        "reason": ("v1 attached older D19 checker/result/test metadata; exact A "
                   "and all shard hashes were already correct and are unchanged"),
        "old_and_strict_D19_exact_values_equal": True,
        "strict_D19_provenance_is_theorem_facing": True,
    }:
        raise ValueError("aggregate provenance-repair metadata mismatch")

    radial_hashes = {}
    if radial_directory is not None:
        if sha256(REPO / "agents/audit/verify_d14_one_band_a_v2_radial.py") != \
                RADIAL_CHECKER_SHA:
            raise ValueError("live independent radial checker hash mismatch")
        for count in COUNTS:
            radial_hashes[str(count)] = validate_radial_audit(
                radial_directory, count, rows[count], parsed[count])

    return {
        "status": "STRICT D14 A AGGREGATE INDEPENDENT AUDIT PASS",
        "aggregate_sha256": sha256(aggregate_bytes),
        "exact_A_scaled": str(exact_a), "exact_A_unscaled": str(unscaled_a),
        "all_13_shards_recombined": True,
        "all_13_independent_radial_replays_equal":
            True if radial_directory is not None else None,
        "radial_audit_sha256": radial_hashes,
        "source_closure_verified": True,
    }


def publish(path, payload):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256")
    parser.add_argument("--radial-audit-directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.expected_self_sha256 is not None and sha256(FILE) != args.expected_self_sha256:
        raise RuntimeError("externally pinned audit checker SHA mismatch")
    result = audit(args.radial_audit_directory)
    payload = canonical(result)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        publish(args.output, payload)
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
