#!/usr/bin/env python3
"""Strict deterministic assembly of all exact D14 one-band A count shards."""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path
import sys


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
REPO = FILE.parents[3]
PRODUCER = FILE.with_name("exact_d14_one_band_a_shard_v2.py")
PRODUCER_SHA256 = \
    "2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d"
PRODUCER_TEST = REPO / (
    "agents/structural-basis/tests/test_exact_d14_one_band_a_shard_v2.py")
PRODUCER_TEST_SHA256 = \
    "4d5402a8e9940755ca18e69c5a346426bc6081d78ea5206236191dc34e527afc"
D19_CHECKER = REPO / "verify/check_bv_rational_vector_direct_v1.py"
D19_CHECKER_SHA256 = \
    "63bd2a3adc84191d212d52d3175179f583a1257d7c862f1ee07ecaa2ade3b7d3"
D19_RESULT = REPO / "verify/results/bv_D19_krylov20_direct_exact_v1.json"
D19_RESULT_SHA256 = \
    "a71b9bacf9fbe9ce21d6d0f3c23eec69baa917c46157c402d2d60e6565517d0b"
D19_TEST = REPO / "verify/test_check_bv_rational_vector_direct_v1.py"
D19_TEST_SHA256 = \
    "a8d5dd13cf73dc3c59f89dbfdee21819cbc4c230ed063d7bdec42d57bcf81247"

SHARD_DIRECTORY = REPO / (
    "agents/structural-basis/results/d14_one_band_a_shards_v2")
SHARD_SHA256 = {
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
ACTIVE_COUNTS = tuple(range(13))
VECTOR_SCALE = 10 ** 38
EXPECTED_DILATION = Q(9270000, 9500917)
EXPECTED_ALPHA1 = Q(103, 400)
EXPECTED_ALPHA2 = Q(9500917, 36000000)
EXPECTED_ETA = Q(8960917, 36000000)
EXPECTED_DELTA = Q(1, 60)


def sha256(value):
    data = value if isinstance(value, bytes) else Path(value).read_bytes()
    return hashlib.sha256(data).hexdigest()


def strict_json_bytes(data: bytes, label: str):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key {key!r} in {label}")
            out[key] = value
        return out

    def reject(token):
        raise ValueError(f"nonfinite JSON token {token!r} in {label}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject)


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("ascii")


def canonical_q(token):
    if not isinstance(token, str):
        raise TypeError("exact rational must be a string")
    value = Q(token)
    if str(value) != token:
        raise ValueError(f"noncanonical rational token {token!r}")
    return value


def decimal(value, digits=60):
    value = Q(value)
    with localcontext() as ctx:
        ctx.prec = digits
        return format(Decimal(value.numerator) / Decimal(value.denominator),
                      ".45E")


def validate_static_pins():
    for path, expected in (
            (PRODUCER, PRODUCER_SHA256),
            (PRODUCER_TEST, PRODUCER_TEST_SHA256),
            (D19_CHECKER, D19_CHECKER_SHA256),
            (D19_RESULT, D19_RESULT_SHA256),
            (D19_TEST, D19_TEST_SHA256)):
        if sha256(path) != expected:
            raise RuntimeError(f"pinned exact-A aggregate input changed: {path}")


def load_shards():
    rows = {}
    payloads = {}
    for count in ACTIVE_COUNTS:
        path = SHARD_DIRECTORY / f"r{count:02d}.json"
        payload = path.read_bytes()
        if sha256(payload) != SHARD_SHA256[count]:
            raise RuntimeError(f"pinned exact-A shard changed: {path}")
        row = strict_json_bytes(payload, str(path))
        # Producer output itself is required to be canonical, so alternate
        # duplicate-key/whitespace/number encodings cannot survive assembly.
        if canonical_json(row) != payload:
            raise ValueError(f"noncanonical exact-A shard: {path}")
        observed = row.get("count")
        if observed in rows:
            raise ValueError(f"duplicate exact-A count {observed}")
        rows[observed] = row
        payloads[observed] = payload
    if set(rows) != set(ACTIVE_COUNTS):
        raise ValueError("missing, duplicate, or out-of-range exact-A counts")
    return rows, payloads


def validate_shard(count, row):
    candidate = row.get("candidate", {})
    geometry = row.get("geometry", {})
    checks = row.get("checks", {})
    inventory = row.get("inventory", {})
    if (row.get("format") != "exact-d14-one-band-a-count-shard-v2" or
            row.get("status") != "EXACT D14 ONE-BAND A COUNT SHARD PASS" or
            row.get("rigorous") is not True or row.get("count") != count or
            tuple(row.get("active_counts", ())) != ACTIVE_COUNTS or
            row.get("k") != 48 or row.get("degree") != 14 or
            row.get("basis_dimension") != 195 or
            row.get("source_sha256") != PRODUCER_SHA256 or
            row.get("cache_read") is not False or
            row.get("serialized_matrix_entries_read") is not False or
            row.get("resume_supported") is not False or
            row.get("theorem_ready") is not False or
            candidate.get("name") != "D14_grid_1e-38" or
            candidate.get("grid_digits") != 38 or
            canonical_q(candidate.get("evaluation_vector_scale")) !=
            VECTOR_SCALE or
            candidate.get("evaluation_vector_is_integral") is not True or
            canonical_q(candidate.get("natural_dilation")) !=
            EXPECTED_DILATION or
            canonical_q(geometry.get("alpha1")) != EXPECTED_ALPHA1 or
            canonical_q(geometry.get("alpha2")) != EXPECTED_ALPHA2 or
            canonical_q(geometry.get("eta")) != EXPECTED_ETA or
            canonical_q(geometry.get("delta")) != EXPECTED_DELTA or
            geometry.get("schedule_extension") !=
            "terminal plateau through count 48" or
            len(geometry.get("schedule", ())) != 48 or
            not checks or not all(value is True for value in checks.values()) or
            inventory.get("square_orbit_partition_groups") != 508 or
            inventory.get("square_residual_terms_per_support") != 3034 or
            inventory.get("high_faces") != 16 - count or
            inventory.get("low_faces") != 16 - count or
            inventory.get("shared_density_faces") != 16 - count or
            inventory.get("workers") != 1):
        raise ValueError(f"exact-A shard schema/identity mismatch at R={count}")
    values = row.get("exact_values", {})
    high = canonical_q(values.get("high_support_I_count"))
    low = canonical_q(values.get("low_support_I_count"))
    band = canonical_q(values.get("band_I_count"))
    unscaled = canonical_q(values.get("unscaled_band_I_count"))
    high_volume = canonical_q(values.get("high_support_volume_count"))
    low_volume = canonical_q(values.get("low_support_volume_count"))
    band_volume = canonical_q(values.get("band_volume_count"))
    if (high - low != band or band != VECTOR_SCALE ** 2 * unscaled or
            high_volume - low_volume != band_volume or
            min(high, low, band, high_volume, low_volume, band_volume) <= 0):
        raise ArithmeticError(f"exact-A shard arithmetic mismatch at R={count}")
    return high, low, band, unscaled, high_volume, low_volume, band_volume


def build_aggregate():
    validate_static_pins()
    rows, payloads = load_shards()
    parsed = {count: validate_shard(count, rows[count])
              for count in ACTIVE_COUNTS}
    reference_candidate = rows[0]["candidate"]
    reference_geometry = rows[0]["geometry"]
    for count in ACTIVE_COUNTS[1:]:
        if (rows[count]["candidate"] != reference_candidate or
                rows[count]["geometry"] != reference_geometry):
            raise ValueError(f"candidate/geometry drift at R={count}")

    high = sum((parsed[r][0] for r in ACTIVE_COUNTS), Q(0))
    low = sum((parsed[r][1] for r in ACTIVE_COUNTS), Q(0))
    exact_a = sum((parsed[r][2] for r in ACTIVE_COUNTS), Q(0))
    unscaled_a = sum((parsed[r][3] for r in ACTIVE_COUNTS), Q(0))
    high_volume = sum((parsed[r][4] for r in ACTIVE_COUNTS), Q(0))
    low_volume = sum((parsed[r][5] for r in ACTIVE_COUNTS), Q(0))
    band_volume = sum((parsed[r][6] for r in ACTIVE_COUNTS), Q(0))
    if (high - low != exact_a or exact_a != VECTOR_SCALE ** 2 * unscaled_a or
            high_volume - low_volume != band_volume or
            min(high, low, exact_a, high_volume, low_volume, band_volume) <= 0):
        raise ArithmeticError("exact-A aggregate arithmetic/positivity failed")

    d19 = strict_json_bytes(D19_RESULT.read_bytes(), str(D19_RESULT))
    if (d19.get("status") != "INDEPENDENT EXACT PARTICULAR INNER VECTOR PASS" or
            d19.get("rigorous") is not True or d19.get("cache_read") is not False or
            d19.get("serialized_matrix_entries_read") is not False or
            d19.get("k") != 48 or d19.get("basis_degree") != 19 or
            d19.get("basis_dimension") != 568 or
            d19.get("checker_sha256") != D19_CHECKER_SHA256):
        raise ValueError("D19 exact inner identity mismatch")
    inner_i = canonical_q(d19["exact_denominator"])
    inner_deficit = canonical_q(d19["exact_deficit"])
    normalized_deficit = canonical_q(d19["exact_normalized_deficit"])
    if inner_deficit / inner_i != normalized_deficit:
        raise ArithmeticError("D19 exact normalized deficit mismatch")
    scaled_d14_full_i = canonical_q(
        reference_candidate["scaled_exact_full_simplex_I"])
    d14_full_i = canonical_q(reference_candidate["exact_full_simplex_I"])
    if scaled_d14_full_i != VECTOR_SCALE ** 2 * d14_full_i:
        raise ArithmeticError("D14 full-simplex scaling mismatch")

    total_elapsed = sum(float(rows[r]["elapsed_seconds"])
                        for r in ACTIVE_COUNTS)
    max_rss = max(int(rows[r]["peak_rss_kib"]) for r in ACTIVE_COUNTS)
    return {
        "format": "exact-d14-one-band-a-aggregate-v1",
        "status": "EXACT D14 ONE-BAND A AGGREGATE PASS",
        "rigorous": True,
        "claim_scope": (
            "exact I(H) for the scaled natural D14 coordinate on the frozen "
            "single outer band; the cutoff-aware b=48J(F,H) remains separate"),
        "exact_A_scaled": str(exact_a),
        "exact_A_scaled_decimal": decimal(exact_a),
        "exact_A_unscaled": str(unscaled_a),
        "exact_A_unscaled_decimal": decimal(unscaled_a),
        "exact_high_support_I_scaled": str(high),
        "exact_low_support_I_scaled": str(low),
        "exact_band_volume": str(band_volume),
        "A_over_D14_full_simplex_I": str(exact_a / scaled_d14_full_i),
        "A_over_D14_full_simplex_I_decimal": decimal(
            exact_a / scaled_d14_full_i),
        "normalization": {
            "outer_H_scale": str(VECTOR_SCALE),
            "A_scale_factor": str(VECTOR_SCALE ** 2),
            "natural_dilation": str(EXPECTED_DILATION),
            "D19_inner_I": str(inner_i),
            "D19_inner_deficit": str(inner_deficit),
            "D19_exact_normalized_deficit": str(normalized_deficit),
            "D19_exact_normalized_deficit_decimal": decimal(normalized_deficit),
            "future_certificate_expression": "b^2/(A*I_D19) - deficit/I_D19",
            "b_definition": "b=48J(F_D19,H_D14)",
        },
        "checks": {
            "all_13_active_counts_present_once": True,
            "all_shards_canonical_and_hash_pinned": True,
            "all_per_count_high_minus_low_equal_band": True,
            "all_per_count_scaled_equals_10pow76_unscaled": True,
            "all_per_count_I_and_volume_values_positive": True,
            "aggregate_high_minus_low_equal_sum_of_band_shards": True,
            "aggregate_scaled_equals_10pow76_unscaled": True,
            "candidate_and_geometry_identical_across_shards": True,
            "no_cache_or_serialized_matrix_entries": True,
        },
        "counts": [{
            "count": r,
            "path": str((SHARD_DIRECTORY / f"r{r:02d}.json").relative_to(REPO)),
            "sha256": SHARD_SHA256[r],
            "exact_A_scaled": rows[r]["exact_values"]["band_I_count"],
            "exact_A_unscaled": rows[r]["exact_values"]["unscaled_band_I_count"],
            "elapsed_seconds": rows[r]["elapsed_seconds"],
            "peak_rss_kib": rows[r]["peak_rss_kib"],
        } for r in ACTIVE_COUNTS],
        "measured_total_shard_seconds": total_elapsed,
        "measured_max_shard_rss_kib": max_rss,
        "producer": {
            "path": str(PRODUCER.relative_to(REPO)),
            "sha256": PRODUCER_SHA256,
            "test_path": str(PRODUCER_TEST.relative_to(REPO)),
            "test_sha256": PRODUCER_TEST_SHA256,
            "workers_per_shard": 1,
            "resume_supported": False,
        },
        "D19_inner_provenance": {
            "checker_path": str(D19_CHECKER.relative_to(REPO)),
            "checker_sha256": D19_CHECKER_SHA256,
            "result_path": str(D19_RESULT.relative_to(REPO)),
            "result_sha256": D19_RESULT_SHA256,
            "test_path": str(D19_TEST.relative_to(REPO)),
            "test_sha256": D19_TEST_SHA256,
        },
        "source_sha256": sha256(FILE),
        "source_hashes": {
            str(PRODUCER.relative_to(REPO)): PRODUCER_SHA256,
            str(PRODUCER_TEST.relative_to(REPO)): PRODUCER_TEST_SHA256,
            str(D19_CHECKER.relative_to(REPO)): D19_CHECKER_SHA256,
            str(D19_RESULT.relative_to(REPO)): D19_RESULT_SHA256,
            str(D19_TEST.relative_to(REPO)): D19_TEST_SHA256,
        },
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "A_stage_complete": True,
        "b_stage_complete": False,
        "b_launch_authorized": False,
        "resume_supported": False,
        "theorem_ready": False,
    }


def publish_exclusive(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_aggregate()
    payload = canonical_json(result)
    publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "exact_A_scaled_decimal": result["exact_A_scaled_decimal"],
        "exact_A_unscaled_decimal": result["exact_A_unscaled_decimal"],
        "A_over_D14_full_simplex_I_decimal":
            result["A_over_D14_full_simplex_I_decimal"],
        "measured_total_shard_seconds": result["measured_total_shard_seconds"],
        "measured_max_shard_rss_kib": result["measured_max_shard_rss_kib"],
        "output_sha256": sha256(payload),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
