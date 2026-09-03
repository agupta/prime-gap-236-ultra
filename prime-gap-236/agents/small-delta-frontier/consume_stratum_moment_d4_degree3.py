#!/usr/bin/env python3
"""Read-only checker/discovery consumer for a completed exact D4 D3 run.

This program never calls an integrator and has no output-file option.  A
caller must name a completed producer artifact and supply both its byte
SHA-256 and a caller-pinned SHA-256 for this consumer's own frozen bytes.
The exact matrices are reconstructed from canonical moment rows; the matrix
hash strings in the artifact are only checked after reconstruction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
from functools import lru_cache
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction as Q
from pathlib import Path
from typing import NamedTuple


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
PRODUCER_GATE = HERE / "results/c10_D4_degree3_moment_prelaunch_gate.json"
CONSUMER_GATE = HERE / "results/c10_D4_degree3_moment_consumer_gate.json"
AUTHORIZATION = HERE / "results/c10_D4_degree3_moment_authorization.json"
REFERENCE = (HERE.parent / "exact-integrator/results/"
             "c10_stratum_quadratic_cappedopt_D4_exact.json")

PRODUCER_GATE_SHA = \
    "964ab9cdbe952b317f4c42d7b18a47269f886448fdf5f53d581f754405e32e3b"
CONSUMER_GATE_SHA = \
    "a1ab82c3f5f4805c3f3c2506baa00295caf884f94200da290bb906f74e4b0ed3"
PRODUCER_SHA = \
    "e48d46f447893d21addef38d979670107086550495fd390a1adeebf1ad6ba7ef"
AUTHORIZATION_SHA = \
    "8bf587b2ee0c0ff27c99d18446802b7be3007c17651cf4aa6c573b1745445c89"
REFERENCE_SHA = \
    "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86"
INPUT_SHA = \
    "2b11a18c697e9a2be61204b5493bf7a235ce4add39d853bbb4d76ef31fb4666b"
TAG_SCHEMA_SHA = \
    "320272a9dfb08ab6d12396127de3ff35ffe35c47b4715e4035bc985e67981aad"

DEGREE = 3
STRATA = 16
K_FACTOR = 48
PRECISIONS = (120, 200)
QUOTIENT_AGREEMENT = Decimal("1e-85")
RESIDUAL_LIMITS = {120: Decimal("1e-105"), 200: Decimal("1e-185")}
GRID_DIGITS = 80
MAX_RESULT_BYTES = 256_000_000

PARAMETERS = {
    "alpha": Q(79247, 300000), "delta": Q(1, 100),
    "eta": Q(76247, 300000), "beta1": Q(3, 20),
    "beta2": Q(3, 20), "beta3plus": Q(97, 625),
}
EXPECTED_COUNTS = {
    "matrix_dimension": 160,
    "i_faces": 312,
    "j_branch_domains": 1200,
    "j_fused_traversals": 1200,
    "i_scalar_moment_integrals": 8736,
    "j_logical_moment_products": 14712,
    "j_scalar_moment_integrals": 167380,
}
RESOURCE_GATE = {
    "maximum_fused_seconds": 1800,
    "maximum_total_validation_seconds": 3600,
    "maximum_peak_rss_kib": 262144,
}

HEX64 = re.compile(r"[0-9a-f]{64}\Z")
RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")
REFERENCE_J_KEY = re.compile(
    r"\(\(([0-9]+), ([0-9]+)\), \(([0-9]+), ([0-9]+)\)\)\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def require_sha(value, description):
    require(type(value) is str and HEX64.fullmatch(value) is not None,
            f"{description}: require lowercase SHA-256")


def exact_keys(value, keys, description):
    require(type(value) is dict and set(value) == set(keys),
            f"{description}: schema mismatch")


def strict_json(raw, description, maximum=MAX_RESULT_BYTES):
    require(type(raw) is bytes and 0 < len(raw) <= maximum,
            f"{description}: bounded nonempty bytes")

    def pairs(items):
        answer = {}
        for key, value in items:
            require(type(key) is str and key not in answer,
                    f"{description}: duplicate/non-string key")
            answer[key] = value
        return answer

    def integer(token):
        require(len(token.lstrip("-")) <= 64,
                f"{description}: oversized JSON integer")
        return int(token)

    def nonfinite(token):
        raise ValueError(f"{description}: nonfinite token {token}")

    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                          parse_float=Decimal, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{description}: invalid strict JSON") from error


class Snapshot(NamedTuple):
    path: Path
    raw: bytes
    digest: str
    identity: tuple[int, int]


def read_pinned(path_text, expected_sha, description, maximum):
    """Read one regular, non-symlink file and bind it before JSON parsing."""
    require_sha(expected_sha, f"{description} caller SHA")
    path = Path(path_text).absolute()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
                f"{description}: regular bounded file")
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(1 << 20, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        require(len(raw) <= maximum and before.st_size == len(raw) and
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                f"{description}: changed during snapshot")
    finally:
        os.close(descriptor)
    visible = os.stat(path, follow_symlinks=False)
    require(stat.S_ISREG(visible.st_mode) and
            (visible.st_dev, visible.st_ino) ==
            (after.st_dev, after.st_ino),
            f"{description}: path ownership changed")
    digest = sha256(raw)
    require(digest == expected_sha, f"{description}: SHA-256 mismatch")
    return Snapshot(path, raw, digest, (after.st_dev, after.st_ino))


def verify_snapshot(snapshot, description, maximum):
    current = read_pinned(snapshot.path, snapshot.digest, description, maximum)
    require(current.identity == snapshot.identity,
            f"{description}: inode changed")


def fraction(value, description):
    require(type(value) is str and len(value) <= 20_000 and
            RATIONAL.fullmatch(value) is not None,
            f"{description}: canonical rational syntax")
    try:
        answer = Q(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{description}: malformed rational") from error
    require(str(answer) == value, f"{description}: rational not reduced")
    return answer


def channel_powers(degree):
    require(type(degree) is int and 0 <= degree <= 8,
            "channel degree")
    return tuple((a, total - a) for total in range(degree + 1)
                 for a in range(total, -1, -1))


CHANNELS3 = channel_powers(3)
CHANNELS2 = channel_powers(2)
EXPECTED_DISCARDED = (
    (0, (1, 0)), (0, (2, 0)), (0, (1, 1)),
    (0, (3, 0)), (0, (2, 1)), (0, (1, 2)),
)


@lru_cache(maxsize=None)
def matrix_query_tag_inventory(degree=DEGREE, strata=STRATA):
    """Enumerate exactly the J moment tags queried by all matrix entries.

    This is deliberately derived from the complete label pairs and their
    common-R branch classes, rather than from the producer's tag generator.
    """
    powers = channel_powers(degree)
    labels = tuple((r, power) for r in range(strata) for power in powers)
    tags = set()
    for common_r in range(strata):
        for left_r, left_power in labels:
            left_class = left_r - common_r
            if left_class not in (0, 1):
                continue
            left_max = left_power[0] if left_class else left_power[1]
            for right_r, right_power in labels:
                right_class = right_r - common_r
                if right_class not in (0, 1):
                    continue
                right_max = right_power[0] if right_class else right_power[1]
                for j in range(left_max + 1):
                    left_remaining = _remaining_power(
                        left_power, j, bool(left_class))
                    for k in range(right_max + 1):
                        right_remaining = _remaining_power(
                            right_power, k, bool(right_class))
                        tags.add((
                            common_r, left_class, right_class, j, k,
                            left_remaining[0] + right_remaining[0],
                            left_remaining[1] + right_remaining[1],
                        ))
    return frozenset(tags)


def tag_inventory_sha(tags):
    raw = json.dumps([list(x) for x in sorted(tags)],
                     separators=(",", ":")).encode()
    return sha256(raw)


MATRIX_QUERY_TAG_COUNT = 10980
MATRIX_QUERY_TAG_SHA = \
    "746de1d75e0deee16c7e15380e1b912dbe36c6de215e1e45844cec1ceea7fa92"


def load_consumer_gate():
    snapshot = read_pinned(
        CONSUMER_GATE, CONSUMER_GATE_SHA, "consumer prelaunch gate", 100_000)
    gate = strict_json(snapshot.raw, "consumer prelaunch gate", 100_000)
    query_tags = matrix_query_tag_inventory()
    require(len(query_tags) == MATRIX_QUERY_TAG_COUNT and
            tag_inventory_sha(query_tags) == MATRIX_QUERY_TAG_SHA,
            "independent matrix-query tag inventory identity")
    exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized", "mode",
        "consumer_self_binding",
        "producer_gate_sha256", "producer_driver_sha256",
        "authorization_sha256", "degree2_reference_sha256",
        "future_result_binding",
        "expected_counts", "resource_gate", "reconstruction_gate",
        "rank_gate", "solve_gate", "rationalization_gate",
        "continuation_gate",
    }, "consumer prelaunch gate")
    require(gate["status"] ==
            "frozen-c10-d4-degree3-moment-consumer-prelaunch" and
            gate["rigorous"] is False and
            gate["production_launch_authorized"] is False and
            gate["mode"] ==
            "read-only-exact-row-reconstruction-and-discovery" and
            gate["consumer_self_binding"] ==
            "caller-supplied-lowercase-sha256-verified-before-result-access-and-at-final-closure" and
            gate["producer_gate_sha256"] == PRODUCER_GATE_SHA and
            gate["producer_driver_sha256"] == PRODUCER_SHA and
            gate["authorization_sha256"] == AUTHORIZATION_SHA and
            gate["degree2_reference_sha256"] == REFERENCE_SHA and
            gate["future_result_binding"] ==
            "caller-supplied-lowercase-sha256-of-completed-bytes" and
            gate["expected_counts"] == EXPECTED_COUNTS and
            gate["resource_gate"] == RESOURCE_GATE,
            "consumer prelaunch gate identity")
    require(gate["reconstruction_gate"] == {
        "degree": 3, "strata": 16, "k_factor": 48,
        "channel_order": [list(x) for x in CHANNELS3],
        "i_row_inventory_count": 448,
        "j_matrix_query_tag_count": MATRIX_QUERY_TAG_COUNT,
        "j_matrix_query_tag_sha256": MATRIX_QUERY_TAG_SHA,
        "j_row_semantics":
            "canonical-sparse-subset-of-matrix-query-tags; omission-denotes-zero-for-reconstruction",
        "source_integral_trust":
            "caller-result-sha-plus-exact-fused-unfused-producer-equality; rows-alone-do-not-prove-omitted-integrals-zero",
        "expected_counts_role":
            "matrix-dimension-plus-producer-traversal-and-integration-work-counters; not-serialized-row-cardinalities",
        "serialized_matrix_hash_role": "secondary-equality-check-only",
        "degree2_check":
            "all-96-by-96-principal-entries-against-byte-pinned-reference",
    }, "consumer reconstruction policy")
    require(gate["rank_gate"] == {
        "selection":
            "per-R-canonical-order-exact-incremental-LDL-Schur-complement",
        "expected_exact_rank": 154,
        "expected_discarded_coordinates":
            [[r, list(power)] for r, power in EXPECTED_DISCARDED],
        "zero_schur_action":
            "discard-after-exact-A-column-and-B-column-dependence-check",
        "negative_schur_action": "reject",
    }, "consumer exact-rank policy")
    require(gate["solve_gate"] == {
        "precisions": [120, 200],
        "maximum_relative_quotient_disagreement": "1e-85",
        "maximum_relative_residual_by_precision": {
            "120": "1e-105", "200": "1e-185"},
        "normalization":
            "first-maximum-absolute-coordinate-positive-and-equal-to-one",
        "numerical_claim_rigorous": False,
    }, "consumer solve policy")
    require(gate["rationalization_gate"] == {
        "condition":
            "both-stable-numerical-quotients-strictly-greater-than-one",
        "decimal_grid_digits": 80,
        "rounding": "ROUND_HALF_EVEN",
        "discarded_coordinates": "exact-zero",
        "exact_continuation_condition":
            "denominator-positive-and-numerator-strictly-greater-than-denominator",
    }, "consumer rationalization policy")
    require(gate["continuation_gate"] == [
        "producer-status-count-resource-authorization-and-provenance-gates-pass-without-relaxation",
        "canonical-dense-I-and-inventory-bounded-sparse-J-rows-reconstruct-symmetric-matrices-and-secondary-hashes",
        "complete-degree2-principal-submatrix-and-embedded-contraction-pass-exactly",
        "exact-rank-and-null-coordinate-gate-passes",
        "two-precision-agreement-and-residual-gates-pass",
        "rationalization-occurs-only-after-both-numerical-quotients-exceed-one",
        "only-an-exact-rationalized-margin-above-zero-may-continue",
    ], "consumer continuation policy")
    return gate, snapshot


def load_producer_gate():
    snapshot = read_pinned(
        PRODUCER_GATE, PRODUCER_GATE_SHA, "producer prelaunch gate", 100_000)
    gate = strict_json(snapshot.raw, "producer prelaunch gate", 100_000)
    exact_keys(gate, {
        "status", "rigorous", "production_launch_authorized", "degree",
        "parameters", "source_hashes", "data_hashes",
        "tag_schema_sha256", "expected_counts", "resource_gate",
        "validation_targets", "baseline_measurement",
    }, "producer prelaunch gate")
    producer_relative = \
        "agents/small-delta-frontier/check_stratum_moment_d4_degree3.py"
    reference_relative = (
        "agents/exact-integrator/results/"
        "c10_stratum_quadratic_cappedopt_D4_exact.json")
    require(gate["status"] ==
            "frozen-c10-d4-degree3-moment-prelaunch" and
            gate["rigorous"] is False and
            gate["production_launch_authorized"] is False and
            gate["degree"] == DEGREE and
            gate["parameters"] == {k: str(v) for k, v in PARAMETERS.items()} and
            gate["source_hashes"].get(producer_relative) == PRODUCER_SHA and
            gate["data_hashes"].get(reference_relative) == REFERENCE_SHA and
            gate["tag_schema_sha256"] == TAG_SCHEMA_SHA and
            gate["expected_counts"] == EXPECTED_COUNTS,
            "producer prelaunch gate identity")
    require({k: gate["resource_gate"][k] for k in RESOURCE_GATE} ==
            RESOURCE_GATE, "producer resource limits changed")
    return gate, snapshot


def load_authorization():
    snapshot = read_pinned(
        AUTHORIZATION, AUTHORIZATION_SHA, "degree-three authorization",
        100_000)
    value = strict_json(
        snapshot.raw, "degree-three authorization", 100_000)
    exact_keys(value, {
        "status", "authorized", "mode", "gate_sha256", "driver_sha256",
    }, "degree-three authorization")
    require(value == {
        "status": "root-authorized-c10-d4-degree3-moment-run",
        "authorized": True,
        "mode": "exact-D4-degree3-fused-plus-unfused",
        "gate_sha256": PRODUCER_GATE_SHA,
        "driver_sha256": PRODUCER_SHA,
    }, "degree-three authorization identity")
    return value, snapshot


REFERENCE_KEYS = {
    "active_quadratic_labels", "block_direct_bitwise_equal",
    "channel_powers", "cross_precision_solves",
    "cross_precision_stability_pass", "denominator",
    "denominator_positive", "direct_i_faces", "direct_j_branch_domains",
    "direct_seconds", "discarded_gram_dependent_labels",
    "discovery_basis_dimension", "eigenvector_discovery_rigorous",
    "fixed_basis_dimension", "forms_seconds", "grouped_evaluator_sha256",
    "i_blocks", "i_faces", "i_orbit_groups", "input_json",
    "input_sha256", "integrator_sha256", "j_branch_domains",
    "j_channel_integrals", "j_entries", "k", "margin",
    "margin_positive", "marginal_components", "numerator",
    "parallelism_note", "parameters", "peak_rss_kib",
    "quadratic_basis_dimension", "quadratic_labels", "quotient",
    "rational_denominator_limit", "rational_vector", "rigorous_forms",
    "robust_solver_sha256", "script_sha256", "solve_seconds", "status",
    "stratum_linear_sha256", "total_seconds", "workers",
}


def channel_name(power):
    a, b = power
    pieces = []
    if a:
        pieces.append("L" if a == 1 else f"L^{a}")
    if b:
        pieces.append("Z" if b == 1 else f"Z^{b}")
    return "".join(pieces) if pieces else "1"


def load_reference():
    snapshot = read_pinned(
        REFERENCE, REFERENCE_SHA, "degree-two exact reference", 5_000_000)
    value = strict_json(snapshot.raw, "degree-two exact reference", 5_000_000)
    exact_keys(value, REFERENCE_KEYS, "degree-two exact reference")
    labels = [(r, p) for r in range(STRATA)
              for p in range(len(CHANNELS2))]
    rendered_labels = [[r, channel_name(CHANNELS2[p])] for r, p in labels]
    require(value["status"] == "exact-stratum-quadratic-rational-vector" and
            value["rigorous_forms"] is True and
            value["eigenvector_discovery_rigorous"] is False and
            value["k"] == K_FACTOR and
            value["parameters"] == {k: str(v) for k, v in PARAMETERS.items()} and
            value["input_sha256"] == INPUT_SHA and
            value["fixed_basis_dimension"] == 12 and
            value["quadratic_basis_dimension"] == len(labels) == 96 and
            value["discovery_basis_dimension"] == 93 and
            value["channel_powers"] == [list(x) for x in CHANNELS2] and
            value["quadratic_labels"] == rendered_labels and
            value["discarded_gram_dependent_labels"] ==
            [[0, "L"], [0, "L^2"], [0, "LZ"]] and
            value["denominator_positive"] is True and
            value["block_direct_bitwise_equal"] is True,
            "degree-two reference identity/schema")

    blocks = value["i_blocks"]
    require(type(blocks) is dict and
            set(blocks) == {str(r) for r in range(STRATA)},
            "degree-two I block keys")
    a = [[Q(0) for _ in labels] for _ in labels]
    for r in range(STRATA):
        block = blocks[str(r)]
        require(type(block) is list and len(block) == len(CHANNELS2) and
                all(type(row) is list and len(row) == len(CHANNELS2)
                    for row in block), "degree-two I block shape")
        for p, row in enumerate(block):
            for q, entry in enumerate(row):
                a[r * len(CHANNELS2) + p][r * len(CHANNELS2) + q] = \
                    fraction(entry, f"degree-two I[{r},{p},{q}]")

    entries = value["j_entries"]
    require(type(entries) is dict and entries,
            "degree-two J entries object")
    b = [[Q(0) for _ in labels] for _ in labels]
    positions = {label: i for i, label in enumerate(labels)}
    for text, raw_entry in entries.items():
        match = REFERENCE_J_KEY.fullmatch(text)
        require(match is not None, "degree-two J key syntax")
        left = (int(match.group(1)), int(match.group(2)))
        right = (int(match.group(3)), int(match.group(4)))
        require(left in positions and right in positions and left <= right,
                "degree-two J key range/order")
        entry = fraction(raw_entry, f"degree-two J[{text}]")
        i, j = positions[left], positions[right]
        b[i][j] += K_FACTOR * entry
        if i != j:
            b[j][i] += K_FACTOR * entry
    require(all(a[i][j] == a[j][i] and b[i][j] == b[j][i]
                for i in range(len(labels)) for j in range(len(labels))),
            "degree-two reference matrix symmetry")

    vector = value["rational_vector"]
    require(type(vector) is list and len(vector) == len(labels),
            "degree-two rational vector shape")
    vector = [fraction(x, f"degree-two vector[{i}]")
              for i, x in enumerate(vector)]
    denominator = fraction(value["denominator"], "degree-two denominator")
    numerator = fraction(value["numerator"], "degree-two numerator")
    quotient = fraction(value["quotient"], "degree-two quotient")
    margin = fraction(value["margin"], "degree-two margin")
    require(denominator > 0 and numerator / denominator == quotient and
            numerator - denominator == margin and
            exact_quadratic(a, vector) == denominator and
            exact_quadratic(b, vector) == numerator,
            "degree-two exact contraction")
    return {
        "labels": labels, "a": a, "b": b, "vector": vector,
        "denominator": denominator, "numerator": numerator,
        "quotient": quotient,
    }, snapshot


RESULT_KEYS = {
    "status", "rigorous_forms", "theorem_ready", "scope",
    "gate_sha256", "authorization_sha256", "driver_sha256",
    "input_sha256", "reference_sha256", "tag_schema_sha256",
    "expected_counts", "all_fused_unfused_entries_equal",
    "all_degree2_oracle_entries_equal", "particular_denominator",
    "particular_numerator", "particular_quotient", "a_matrix_sha256",
    "b48_matrix_sha256", "i_moment_rows", "j_moment_rows",
    "fused_seconds", "unfused_seconds", "total_validation_seconds",
    "peak_rss_kib", "resource_gate_passed",
}


def validate_result_metadata(value, producer_gate):
    exact_keys(value, RESULT_KEYS, "degree-three producer result")
    for field in ("authorization_sha256", "driver_sha256", "input_sha256",
                  "reference_sha256", "tag_schema_sha256",
                  "a_matrix_sha256", "b48_matrix_sha256", "gate_sha256"):
        require_sha(value[field], f"degree-three result {field}")
    require(value["status"] == "exact-c10-d4-degree3-moment-pass" and
            value["rigorous_forms"] is True and
            value["theorem_ready"] is False and
            value["scope"] ==
            "D4 degree-three finite space only; no D12 sign" and
            value["gate_sha256"] == PRODUCER_GATE_SHA and
            value["authorization_sha256"] == AUTHORIZATION_SHA and
            value["driver_sha256"] == PRODUCER_SHA and
            value["input_sha256"] == INPUT_SHA and
            value["reference_sha256"] == REFERENCE_SHA and
            value["tag_schema_sha256"] == TAG_SCHEMA_SHA and
            value["expected_counts"] == EXPECTED_COUNTS and
            value["all_fused_unfused_entries_equal"] is True and
            value["all_degree2_oracle_entries_equal"] is True and
            value["resource_gate_passed"] is True,
            "degree-three producer status/provenance/count gates")
    for field in ("fused_seconds", "unfused_seconds",
                  "total_validation_seconds"):
        require(type(value[field]) is Decimal and value[field].is_finite() and
                value[field] >= 0, f"degree-three result {field}")
    require(type(value["peak_rss_kib"]) is int and
            value["peak_rss_kib"] >= 0,
            "degree-three result peak RSS")
    require(value["fused_seconds"] <=
            Decimal(RESOURCE_GATE["maximum_fused_seconds"]) and
            value["total_validation_seconds"] <=
            Decimal(RESOURCE_GATE["maximum_total_validation_seconds"]) and
            value["peak_rss_kib"] <= RESOURCE_GATE["maximum_peak_rss_kib"] and
            value["total_validation_seconds"] >= value["fused_seconds"] and
            value["total_validation_seconds"] >= value["unfused_seconds"],
            "degree-three fixed resource gate")
    timing_scale = max(Decimal(1), value["total_validation_seconds"])
    require(abs(value["total_validation_seconds"] -
                value["fused_seconds"] - value["unfused_seconds"]) <=
            Decimal("1e-12") * timing_scale,
            "degree-three timing sum identity")
    require({k: producer_gate["resource_gate"][k] for k in RESOURCE_GATE} ==
            RESOURCE_GATE, "producer resource gate was relaxed")
    denominator = fraction(
        value["particular_denominator"], "reported particular denominator")
    numerator = fraction(
        value["particular_numerator"], "reported particular numerator")
    quotient = fraction(
        value["particular_quotient"], "reported particular quotient")
    require(denominator > 0 and numerator / denominator == quotient,
            "reported particular quotient identity")
    require(type(value["i_moment_rows"]) is list and
            type(value["j_moment_rows"]) is list,
            "degree-three moment row containers")


def parse_i_rows(rows, degree=DEGREE, strata=STRATA):
    expected = sorted((r, u, v) for r in range(strata)
                      for u in range(2 * degree + 1)
                      for v in range(2 * degree + 1 - u))
    require(type(rows) is list and len(rows) == len(expected),
            "I moment row count")
    table = {}
    observed = []
    for index, row in enumerate(rows):
        require(type(row) is list and len(row) == 4 and
                all(type(row[i]) is int for i in range(3)),
                f"I moment row {index} shape/types")
        key = tuple(row[:3])
        observed.append(key)
        table[key] = fraction(row[3], f"I moment row {index} value")
    require(observed == expected and len(table) == len(expected),
            "I moment rows not complete canonical order")
    return table


def parse_j_rows(rows, degree=DEGREE, strata=STRATA):
    require(type(rows) is list, "J moment rows must be a list")
    query_inventory = matrix_query_tag_inventory(degree, strata)
    table = {}
    previous = None
    for index, row in enumerate(rows):
        require(type(row) is list and len(row) == 8 and
                all(type(row[i]) is int for i in range(7)),
                f"J moment row {index} shape/types")
        r, left_class, right_class, j, k, u, v = row[:7]
        key = (r, left_class, right_class, j, k, u, v)
        require(0 <= r < strata and left_class in (0, 1) and
                right_class in (0, 1) and 0 <= j <= degree and
                0 <= k <= degree and u >= 0 and v >= 0 and
                j + k + u + v <= 2 * degree,
                f"J moment row {index} tag range")
        require(key in query_inventory,
                f"J moment row {index} outside matrix-query tag inventory")
        require(previous is None or previous < key,
                "J moment rows not strict canonical order")
        previous = key
        table[key] = fraction(row[7], f"J moment row {index} value")
    require(len(table) <= len(query_inventory),
            "J sparse row count exceeds matrix-query inventory")
    for key, value in table.items():
        r, left_class, right_class, j, k, u, v = key
        mirror = (r, right_class, left_class, k, j, u, v)
        require(mirror in table and table[mirror] == value,
                "J moment exact mirror symmetry")
    return table


def _remaining_power(power, moment, large):
    a, b = power
    return (a - moment, b) if large else (a, b - moment)


def _j_entry(table, common_r, left_power, right_power,
             left_class, right_class):
    left_max = left_power[0] if left_class else left_power[1]
    right_max = right_power[0] if right_class else right_power[1]
    answer = Q(0)
    for j in range(left_max + 1):
        lu, lv = _remaining_power(left_power, j, bool(left_class))
        for k in range(right_max + 1):
            ru, rv = _remaining_power(right_power, k, bool(right_class))
            answer += Q(math.comb(left_max, j) *
                        math.comb(right_max, k)) * table.get(
                (common_r, left_class, right_class,
                 j, k, lu + ru, lv + rv), Q(0))
    return answer


def reconstruct_matrices(i_table, j_table, degree=DEGREE,
                         strata=STRATA, k_factor=K_FACTOR):
    powers = channel_powers(degree)
    labels = [(r, p) for r in range(strata) for p in range(len(powers))]
    positions = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    a = [[Q(0) for _ in range(n)] for _ in range(n)]
    b = [[Q(0) for _ in range(n)] for _ in range(n)]
    for r in range(strata):
        for p, left in enumerate(powers):
            for q, right in enumerate(powers):
                a[positions[(r, p)]][positions[(r, q)]] = i_table[
                    (r, left[0] + right[0], left[1] + right[1])]
    for common_r in range(strata):
        for left_class in (0, 1):
            left_r = common_r + left_class
            if left_r >= strata:
                continue
            for right_class in (0, 1):
                right_r = common_r + right_class
                if right_r >= strata:
                    continue
                for p, left in enumerate(powers):
                    i = positions[(left_r, p)]
                    for q, right in enumerate(powers):
                        j = positions[(right_r, q)]
                        b[i][j] += k_factor * _j_entry(
                            j_table, common_r, left, right,
                            left_class, right_class)
    require(all(a[i][j] == a[j][i] and b[i][j] == b[j][i]
                for i in range(n) for j in range(n)),
            "reconstructed degree-three matrix symmetry")
    return labels, a, b


def matrix_sha(matrix):
    """Hash the producer's compact JSON matrix encoding without materializing it."""
    digest = hashlib.sha256()
    digest.update(b"[")
    for i, row in enumerate(matrix):
        if i:
            digest.update(b",")
        digest.update(b"[")
        for j, value in enumerate(row):
            if j:
                digest.update(b",")
            digest.update(json.dumps(str(value), separators=(",", ":")).encode())
        digest.update(b"]")
    digest.update(b"]")
    return digest.hexdigest()


def exact_quadratic(matrix, vector):
    require(len(matrix) == len(vector) and
            all(len(row) == len(vector) for row in matrix),
            "quadratic dimensions")
    active = [i for i, value in enumerate(vector) if value]
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in active for j in active), Q(0))


def validate_degree2_principal(a, b, reference):
    positions3 = {(r, power): r * len(CHANNELS3) + p
                  for r in range(STRATA)
                  for p, power in enumerate(CHANNELS3)}
    positions = [positions3[(r, CHANNELS2[p])]
                 for r, p in reference["labels"]]
    require(all(a[positions[i]][positions[j]] == reference["a"][i][j] and
                b[positions[i]][positions[j]] == reference["b"][i][j]
                for i in range(len(positions))
                for j in range(len(positions))),
            "complete degree-two exact principal submatrix")
    embedded = [Q(0) for _ in range(len(a))]
    for position, value in zip(positions, reference["vector"]):
        embedded[position] = value
    denominator = exact_quadratic(a, embedded)
    numerator = exact_quadratic(b, embedded)
    require(denominator == reference["denominator"] and
            numerator == reference["numerator"],
            "embedded degree-two exact contraction")
    return embedded, denominator, numerator


def _dependency_coefficients(lower_rows, pivots, cross):
    n = len(pivots)
    y = [Q(0) for _ in range(n)]
    for i in range(n):
        y[i] = cross[i] - sum(
            (lower_rows[i][k] * y[k] for k in range(i)), Q(0))
    z = [y[i] / pivots[i] for i in range(n)]
    answer = [Q(0) for _ in range(n)]
    for i in range(n - 1, -1, -1):
        answer[i] = z[i] - sum(
            (lower_rows[k][i] * answer[k]
             for k in range(i + 1, n)), Q(0))
    return answer


def gram_independent_coordinates(a, b, labels, powers,
                                 expected_discarded=None,
                                 expected_rank=None):
    n = len(labels)
    require(len(a) == len(b) == n and
            all(len(row) == n for row in a + b) and
            all(a[i][j] == a[j][i] and b[i][j] == b[j][i]
                for i in range(n) for j in range(n)),
            "Gram pencil dimensions/symmetry")
    selected = []
    discarded = []
    pivots_by_r = []
    strata = sorted({r for r, _ in labels})
    for r in strata:
        candidates = [i for i, label in enumerate(labels) if label[0] == r]
        block_selected = []
        lower_rows = []
        pivots = []
        for candidate in candidates:
            cross = [a[candidate][index] for index in block_selected]
            row = []
            for j in range(len(block_selected)):
                residual = cross[j] - sum(
                    (row[k] * pivots[k] * lower_rows[j][k]
                     for k in range(j)), Q(0))
                row.append(residual / pivots[j])
            schur = a[candidate][candidate] - sum(
                (row[k] * row[k] * pivots[k]
                 for k in range(len(row))), Q(0))
            if schur > 0:
                block_selected.append(candidate)
                lower_rows.append(row + [Q(1)])
                pivots.append(schur)
            elif schur == 0:
                coefficients = _dependency_coefficients(
                    lower_rows, pivots, cross)
                require(all(a[i][candidate] == sum(
                    (a[i][index] * coefficient
                     for index, coefficient in
                     zip(block_selected, coefficients)), Q(0))
                    for i in range(n)),
                    "discarded coordinate A-column dependence")
                require(all(b[i][candidate] == sum(
                    (b[i][index] * coefficient
                     for index, coefficient in
                     zip(block_selected, coefficients)), Q(0))
                    for i in range(n)),
                    "discarded coordinate B-column dependence")
                discarded.append(candidate)
            else:
                raise ValueError(
                    f"negative exact Gram Schur complement at {labels[candidate]}")
        selected.extend(block_selected)
        pivots_by_r.extend(pivots)
    discarded_labels = tuple((labels[i][0], powers[labels[i][1]])
                             for i in discarded)
    if expected_discarded is not None:
        require(discarded_labels == tuple(expected_discarded),
                "unexpected exact Gram-dependent coordinates")
    if expected_rank is not None:
        require(len(selected) == expected_rank,
                "unexpected exact Gram rank")
    require(selected, "empty exact Gram-independent coordinate set")
    return selected, discarded, pivots_by_r


def _decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def _transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def _matmul(left, right):
    rows, inner, columns = len(left), len(right), len(right[0])
    require(rows and len(left[0]) == inner, "decimal matrix dimensions")
    return [[sum((left[i][k] * right[k][j] for k in range(inner)),
                 Decimal(0)) for j in range(columns)]
            for i in range(rows)]


def _dot(left, right):
    return sum((x * y for x, y in zip(left, right)), Decimal(0))


def _matvec(matrix, vector):
    return [_dot(row, vector) for row in matrix]


def _cholesky(matrix):
    n = len(matrix)
    lower = [[Decimal(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            value = matrix[i][j] - sum(
                (lower[i][k] * lower[j][k] for k in range(j)), Decimal(0))
            if i == j:
                require(value > 0, f"decimal Gram Cholesky pivot {i}")
                lower[i][j] = value.sqrt()
            else:
                lower[i][j] = value / lower[j][j]
    return lower


def _inverse_lower(lower):
    n = len(lower)
    inverse = [[Decimal(0) for _ in range(n)] for _ in range(n)]
    for column in range(n):
        for i in range(n):
            rhs = Decimal(int(i == column)) - sum(
                (lower[i][k] * inverse[k][column] for k in range(i)),
                Decimal(0))
            inverse[i][column] = rhs / lower[i][i]
    return inverse


def _jacobi_symmetric(matrix, precision):
    n = len(matrix)
    require(n > 0, "empty decimal eigensystem")
    a = [list(row) for row in matrix]
    vectors = [[Decimal(int(i == j)) for j in range(n)] for i in range(n)]
    tolerance = Decimal(10) ** (-(precision - 30))
    maximum = 20_000 * max(1, n)
    for rotation in range(maximum):
        if n == 1:
            return [a[0][0]], vectors, rotation
        p, q, largest = 0, 1, abs(a[0][1])
        for i in range(n):
            for j in range(i):
                candidate = abs(a[i][j])
                if candidate > largest:
                    p, q, largest = j, i, candidate
        scale = max(Decimal(1), max(abs(a[i][i]) for i in range(n)))
        if largest <= tolerance * scale:
            return [a[i][i] for i in range(n)], vectors, rotation
        apq, app, aqq = a[p][q], a[p][p], a[q][q]
        tau = (aqq - app) / (2 * apq)
        sign = Decimal(1) if tau >= 0 else Decimal(-1)
        t = sign / (abs(tau) + (Decimal(1) + tau * tau).sqrt())
        c = Decimal(1) / (Decimal(1) + t * t).sqrt()
        s = t * c
        for k in range(n):
            if k in (p, q):
                continue
            akp, akq = a[k][p], a[k][q]
            a[k][p] = a[p][k] = c * akp - s * akq
            a[k][q] = a[q][k] = s * akp + c * akq
        a[p][p] = app - t * apq
        a[q][q] = aqq + t * apq
        a[p][q] = a[q][p] = Decimal(0)
        for k in range(n):
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p] = c * vkp - s * vkq
            vectors[k][q] = s * vkp + c * vkq
    raise ValueError("Decimal Jacobi eigensolver did not converge")


def solve_once(a_exact, b_exact, precision):
    require(type(precision) is int and precision >= 80,
            "solve precision")
    with localcontext() as context:
        context.prec = precision
        a = [[_decimal(x) for x in row] for row in a_exact]
        b = [[_decimal(x) for x in row] for row in b_exact]
        scales = [a[i][i].sqrt() for i in range(len(a))]
        require(all(x > 0 for x in scales),
                "positive retained Gram diagonals")
        scaled_a = [[a[i][j] / scales[i] / scales[j]
                     for j in range(len(a))] for i in range(len(a))]
        scaled_b = [[b[i][j] / scales[i] / scales[j]
                     for j in range(len(a))] for i in range(len(a))]
        lower = _cholesky(scaled_a)
        inverse = _inverse_lower(lower)
        reduced = _matmul(_matmul(inverse, scaled_b), _transpose(inverse))
        reduced = [[(reduced[i][j] + reduced[j][i]) / 2
                    for j in range(len(a))] for i in range(len(a))]
        eigenvalues, eigenvectors, rotations = _jacobi_symmetric(
            reduced, precision)
        winner = max(range(len(eigenvalues)), key=eigenvalues.__getitem__)
        y = [eigenvectors[i][winner] for i in range(len(a))]
        w = _matvec(_transpose(inverse), y)
        vector = [w[i] / scales[i] for i in range(len(a))]
        norm = max(abs(x) for x in vector)
        require(norm > 0, "zero maximum eigenvector")
        vector = [x / norm for x in vector]
        pivot = next(i for i, x in enumerate(vector) if abs(x) == 1)
        if vector[pivot] < 0:
            vector = [-x for x in vector]
        av, bv = _matvec(a, vector), _matvec(b, vector)
        denominator, numerator = _dot(vector, av), _dot(vector, bv)
        require(denominator > 0, "decimal Rayleigh denominator")
        quotient = numerator / denominator
        residual = max(abs(bv[i] - quotient * av[i])
                       for i in range(len(a)))
        residual_scale = max(
            Decimal(1), max(abs(x) for x in bv),
            abs(quotient) * max(abs(x) for x in av))
        return {
            "precision": precision,
            "eigenvalue": str(+eigenvalues[winner]),
            "rayleigh_quotient": str(+quotient),
            "relative_residual": str(+(residual / residual_scale)),
            "jacobi_rotations": rotations,
            "vector": [str(+x) for x in vector],
        }


def validate_solves(solves):
    require(type(solves) is list and
            [solve.get("precision") for solve in solves] == list(PRECISIONS),
            "fixed two-precision solve set")
    quotients = []
    for solve in solves:
        precision = solve["precision"]
        quotient = Decimal(solve["rayleigh_quotient"])
        residual = Decimal(solve["relative_residual"])
        require(quotient.is_finite() and residual.is_finite() and
                residual >= 0 and residual <= RESIDUAL_LIMITS[precision],
                f"precision-{precision} residual gate")
        quotients.append(quotient)
    disagreement = abs(quotients[0] - quotients[1]) / max(
        Decimal(1), abs(quotients[1]))
    require(disagreement <= QUOTIENT_AGREEMENT,
            "two-precision quotient agreement gate")
    return quotients, disagreement


def rationalize_if_improved(solves, active, dimension, a, b):
    quotients, disagreement = validate_solves(solves)
    if not all(value > 1 for value in quotients):
        return None, disagreement
    high = [Decimal(x) for x in solves[-1]["vector"]]
    grid = 10 ** GRID_DIGITS
    with localcontext() as context:
        context.prec = max(PRECISIONS) + 30
        reduced = [Q(int((value * Decimal(grid)).to_integral_value(
                         rounding=ROUND_HALF_EVEN)), grid)
                   for value in high]
    vector = [Q(0) for _ in range(dimension)]
    for index, value in zip(active, reduced):
        vector[index] = value
    denominator = exact_quadratic(a, vector)
    numerator = exact_quadratic(b, vector)
    require(denominator > 0, "rationalized exact denominator")
    quotient = numerator / denominator
    return {
        "grid_digits": GRID_DIGITS,
        "vector": [str(x) for x in vector],
        "denominator": str(denominator),
        "numerator": str(numerator),
        "quotient": str(quotient),
        "margin": str(numerator - denominator),
        "exact_continuation_gate": numerator > denominator,
    }, disagreement


def consume_value(value, producer_gate, reference):
    validate_result_metadata(value, producer_gate)
    i_table = parse_i_rows(value["i_moment_rows"])
    j_table = parse_j_rows(value["j_moment_rows"])
    labels, a, b = reconstruct_matrices(i_table, j_table)
    require(len(labels) == EXPECTED_COUNTS["matrix_dimension"],
            "reconstructed matrix dimension")
    a_sha, b_sha = matrix_sha(a), matrix_sha(b)
    require(a_sha == value["a_matrix_sha256"] and
            b_sha == value["b48_matrix_sha256"],
            "secondary reconstructed matrix hash check")
    _, d2_denominator, d2_numerator = validate_degree2_principal(
        a, b, reference)
    require(d2_denominator == fraction(
                value["particular_denominator"],
                "producer particular denominator replay") and
            d2_numerator == fraction(
                value["particular_numerator"],
                "producer particular numerator replay"),
            "producer embedded particular contraction")
    active, discarded, pivots = gram_independent_coordinates(
        a, b, labels, CHANNELS3,
        expected_discarded=EXPECTED_DISCARDED, expected_rank=154)
    reduced_a = [[a[i][j] for j in active] for i in active]
    reduced_b = [[b[i][j] for j in active] for i in active]
    solves = [solve_once(reduced_a, reduced_b, precision)
              for precision in PRECISIONS]
    rationalized, disagreement = rationalize_if_improved(
        solves, active, len(labels), a, b)
    exact_gate = (rationalized is not None and
                  rationalized["exact_continuation_gate"] is True)
    compact_solves = [{k: solve[k] for k in (
        "precision", "eigenvalue", "rayleigh_quotient",
        "relative_residual", "jacobi_rotations")} for solve in solves]
    return {
        "status": ("c10-d4-degree3-consumer-exact-improvement"
                   if exact_gate else
                   "c10-d4-degree3-consumer-no-exact-continuation"),
        "exact_matrix_reconstruction_from_pinned_rows": True,
        "source_integrals_independently_recomputed": False,
        "eigenvalue_discovery_rigorous": False,
        "theorem_ready": False,
        "matrix_source":
            "canonical dense I rows and inventory-bounded sparse J rows",
        "sparse_j_omission_semantics":
            "omitted queried tags reconstruct as zero under pinned producer fused/unfused trust; rows alone do not prove source-integral zero",
        "serialized_matrix_hash_role": "secondary equality check only",
        "a_matrix_sha256": a_sha,
        "b48_matrix_sha256": b_sha,
        "degree2_principal_entries_equal": True,
        "embedded_degree2_denominator": str(d2_denominator),
        "embedded_degree2_numerator": str(d2_numerator),
        "exact_gram_rank": len(active),
        "discarded_gram_coordinates": [
            [labels[i][0], list(CHANNELS3[labels[i][1]])]
            for i in discarded],
        "exact_gram_pivot_sha256": sha256(json.dumps(
            [str(x) for x in pivots], separators=(",", ":")).encode()),
        "precision_runs": compact_solves,
        "relative_quotient_disagreement": str(disagreement),
        "numerical_improvement_gate": all(
            Decimal(x["rayleigh_quotient"]) > 1 for x in solves),
        "rationalization_performed": rationalized is not None,
        "rationalized_particular": rationalized,
        "exact_continuation_gate": exact_gate,
        "claim_scope": (
            "exact reconstruction from the pinned producer serialization, "
            "rank/D2 checks and, conditionally, one exact rational-vector "
            "contraction; no independent source integration and no rigorous "
            "eigenvalue bound"),
    }


def consume(path_text, expected_result_sha, expected_consumer_sha):
    require_sha(expected_result_sha, "future result caller SHA")
    require_sha(expected_consumer_sha, "consumer caller SHA")
    self_snapshot = read_pinned(
        Path(__file__), expected_consumer_sha, "consumer self", 5_000_000)
    consumer_gate, consumer_snapshot = load_consumer_gate()
    producer_gate, producer_snapshot = load_producer_gate()
    _, authorization_snapshot = load_authorization()
    reference, reference_snapshot = load_reference()
    result_snapshot = read_pinned(
        path_text, expected_result_sha, "completed degree-three result",
        MAX_RESULT_BYTES)
    require(len({snapshot.identity for snapshot in (
        self_snapshot, consumer_snapshot, producer_snapshot,
        authorization_snapshot, reference_snapshot,
        result_snapshot)}) == 6, "trusted input path alias")
    require(result_snapshot.raw.startswith(b"{") and
            result_snapshot.raw.endswith(b"}\n"),
            "completed degree-three result canonical envelope")
    value = strict_json(result_snapshot.raw, "completed degree-three result")
    report = consume_value(value, producer_gate, reference)
    report.update({
        "producer_result_sha256": result_snapshot.digest,
        "producer_gate_sha256": producer_snapshot.digest,
        "consumer_gate_sha256": consumer_snapshot.digest,
        "authorization_sha256": authorization_snapshot.digest,
        "degree2_reference_sha256": reference_snapshot.digest,
        "consumer_sha256": self_snapshot.digest,
        "consumer_gate_status": consumer_gate["status"],
    })
    verify_snapshot(result_snapshot, "completed degree-three result closure",
                    MAX_RESULT_BYTES)
    verify_snapshot(reference_snapshot, "degree-two reference closure",
                    5_000_000)
    verify_snapshot(authorization_snapshot, "authorization closure", 100_000)
    verify_snapshot(producer_snapshot, "producer gate closure", 100_000)
    verify_snapshot(consumer_snapshot, "consumer gate closure", 100_000)
    verify_snapshot(self_snapshot, "consumer self final closure", 5_000_000)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Read-only exact-row consumer; never launches integration")
    parser.add_argument("--result", required=True,
                        help="completed producer JSON (there is no default)")
    parser.add_argument("--expected-result-sha256", required=True,
                        help="caller-supplied SHA-256 of completed bytes")
    parser.add_argument("--expected-consumer-sha256", required=True,
                        help="caller-supplied SHA-256 of these consumer bytes")
    args = parser.parse_args()
    report = consume(args.result, args.expected_result_sha256,
                     args.expected_consumer_sha256)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
