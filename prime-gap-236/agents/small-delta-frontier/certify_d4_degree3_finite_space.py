#!/usr/bin/env python3
"""Rigorous finite-space obstruction for the pinned D4 degree-three pencil.

This checker performs no integration and no numerical eigensolve.  It imports
the frozen exact-row reconstruction consumer only from caller-independent,
byte-pinned source.  On the exact Gram-independent coordinates it proves
``A - B`` positive definite using outward-rounded fixed-point LDL, then checks
the same conclusion through an exact midpoint-factor residual inequality.

The result is only published to a new path after all input/self closure checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import stat
import sys
import tempfile
import time
import types
from fractions import Fraction as Q
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONSUMER = HERE / "consume_stratum_moment_d4_degree3.py"
CONSUMER_SHA = \
    "fedf1970b197af825675fa62644aa227875487453d125ad454d213ebcdedfb7c"
RESULT_SHA = \
    "c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5"

INTERVAL_BITS = 768
NORM_BOUND_BITS = 512
EXPECTED_DIMENSION = 160
EXPECTED_RANK = 154
MAX_SOURCE_BYTES = 5_000_000
MAX_RESULT_BYTES = 256_000_000
HEX64 = frozenset("0123456789abcdef")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def require_sha(value, description):
    require(type(value) is str and len(value) == 64 and
            all(character in HEX64 for character in value),
            f"{description}: require lowercase SHA-256")


class Snapshot(tuple):
    """Immutable (path, bytes, digest, (device,inode)) snapshot."""

    __slots__ = ()

    def __new__(cls, path, raw, digest, identity):
        return tuple.__new__(cls, (path, raw, digest, identity))

    path = property(lambda self: self[0])
    raw = property(lambda self: self[1])
    digest = property(lambda self: self[2])
    identity = property(lambda self: self[3])


def read_pinned(path_text, expected_sha, description, maximum):
    """Snapshot one bounded regular file without following a final symlink."""
    require_sha(expected_sha, f"{description} caller SHA")
    path = Path(path_text).absolute()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum,
                f"{description}: bounded nonempty regular file")
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
        require(len(raw) <= maximum and len(raw) == before.st_size and
                (before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns),
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


def load_frozen_consumer(snapshot):
    """Execute exactly the already-snapshotted consumer bytes, never its path."""
    require(snapshot.digest == CONSUMER_SHA,
            "frozen reconstruction consumer identity")
    module = types.ModuleType("_frozen_d4_degree3_consumer")
    module.__file__ = str(snapshot.path)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    code = compile(snapshot.raw, str(snapshot.path), "exec", dont_inherit=True)
    exec(code, module.__dict__)
    return module


def floor_log2(value):
    require(type(value) is Q and value > 0, "positive rational logarithm")
    numerator, denominator = value.numerator, value.denominator
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < (denominator << exponent):
            exponent -= 1
    elif (numerator << (-exponent)) < denominator:
        exponent -= 1
    require(power2(exponent) <= value < power2(exponent + 1),
            "floor log2 postcondition")
    return exponent


def ceil_log2(value):
    exponent = floor_log2(value)
    return exponent if value == power2(exponent) else exponent + 1


def power2(exponent):
    require(type(exponent) is int, "integer power-of-two exponent")
    return Q(1 << exponent) if exponent >= 0 else Q(1, 1 << (-exponent))


def congruence_exponents(matrix):
    """Choose exact powers so each congruent diagonal lies in [1,4)."""
    answer = []
    for index, row in enumerate(matrix):
        require(len(row) == len(matrix) and row[index] > 0,
                f"positive C diagonal {index}")
        answer.append(-(floor_log2(row[index]) // 2))
    for index, exponent in enumerate(answer):
        scaled = matrix[index][index] * power2(2 * exponent)
        require(Q(1) <= scaled < Q(4),
                f"scaled diagonal range {index}")
    return answer


def congruence_entry(value, left_exponent, right_exponent):
    return value * power2(left_exponent + right_exponent)


# An interval is the pair of integer endpoints (lo, hi), denoting
# [lo / scale, hi / scale].  Every operation rounds outwards.
def interval_encode(value, scale):
    require(type(value) is Q and type(scale) is int and scale > 0,
            "interval encoding inputs")
    numerator = value.numerator * scale
    denominator = value.denominator
    return (numerator // denominator, -((-numerator) // denominator))


def interval_sub(left, right):
    return (left[0] - right[1], left[1] - right[0])


def interval_mul(left, right, scale):
    products = (left[0] * right[0], left[0] * right[1],
                left[1] * right[0], left[1] * right[1])
    return (min(products) // scale, -((-max(products)) // scale))


def interval_square(value, scale):
    lo, hi = value
    maximum = max(lo * lo, hi * hi)
    minimum = 0 if lo <= 0 <= hi else min(lo * lo, hi * hi)
    return (minimum // scale, -((-maximum) // scale))


def interval_div(numerator, denominator, scale):
    require(denominator[0] > 0, "strictly positive interval divisor")
    corners = tuple(Q(x * scale, y)
                    for x in numerator for y in denominator)
    low, high = min(corners), max(corners)
    return (low.numerator // low.denominator,
            -((-high.numerator) // high.denominator))


def interval_contains(interval, value, scale):
    return Q(interval[0], scale) <= value <= Q(interval[1], scale)


def exact_block_band_gate(matrix, strata):
    n = len(matrix)
    require(len(strata) == n and
            all(len(row) == n for row in matrix),
            "block-band dimensions")
    outside_nonzero = []
    for i in range(n):
        for j in range(i):
            if strata[i] - strata[j] > 1 and matrix[i][j] != 0:
                outside_nonzero.append((i, j))
    require(not outside_nonzero,
            f"C not exact block tridiagonal: {outside_nonzero[:3]}")


def interval_ldl(matrix, strata, exponents, bits=INTERVAL_BITS):
    """Outward-rounded block-banded LDL for an exact symmetric matrix."""
    n = len(matrix)
    require(type(bits) is int and bits >= 64 and len(strata) == n and
            len(exponents) == n and all(len(row) == n for row in matrix),
            "interval LDL dimensions/precision")
    require(all(matrix[i][j] == matrix[j][i]
                for i in range(n) for j in range(i)),
            "interval LDL exact symmetry")
    exact_block_band_gate(matrix, strata)
    scale = 1 << bits
    lower = []
    pivots = []
    first_by_stratum = {}
    for i, stratum in enumerate(strata):
        first_by_stratum.setdefault(stratum, i)
        first = first_by_stratum.get(stratum - 1,
                                     first_by_stratum[stratum])
        row = {}
        for j in range(first, i):
            value = interval_encode(congruence_entry(
                matrix[i][j], exponents[i], exponents[j]), scale)
            for k in sorted(set(row).intersection(lower[j])):
                term = interval_mul(row[k], pivots[k], scale)
                term = interval_mul(term, lower[j][k], scale)
                value = interval_sub(value, term)
            require(pivots[j][0] > 0,
                    f"nonpositive divisor enclosure at pivot {j}")
            row[j] = interval_div(value, pivots[j], scale)
        pivot = interval_encode(congruence_entry(
            matrix[i][i], exponents[i], exponents[i]), scale)
        for k, coefficient in row.items():
            term = interval_mul(interval_square(coefficient, scale),
                                pivots[k], scale)
            pivot = interval_sub(pivot, term)
        require(pivot[0] > 0,
                f"nonpositive LDL pivot lower endpoint {i}")
        lower.append(row)
        pivots.append(pivot)
    return scale, lower, pivots


def interval_midpoint(value, scale):
    return Q(value[0] + value[1], 2 * scale)


def midpoint_residual(matrix, exponents, lower, pivots, scale):
    """Return exact ||H-Lhat Dhat Lhat^T||_infinity and factors."""
    n = len(matrix)
    lmid = [{j: interval_midpoint(value, scale)
             for j, value in row.items()} for row in lower]
    dmid = [interval_midpoint(value, scale) for value in pivots]
    require(all(value > 0 for value in dmid),
            "positive midpoint pivots")
    row_sums = [Q(0) for _ in range(n)]
    residual_entries = []
    for i in range(n):
        for j in range(i + 1):
            approximation = Q(0)
            if i == j:
                approximation += dmid[i]
            elif j in lmid[i]:
                approximation += lmid[i][j] * dmid[j]
            for k in set(lmid[i]).intersection(lmid[j]):
                approximation += lmid[i][k] * dmid[k] * lmid[j][k]
            exact = congruence_entry(
                matrix[i][j], exponents[i], exponents[j])
            residual = exact - approximation
            residual_entries.append(residual)
            magnitude = abs(residual)
            row_sums[i] += magnitude
            if i != j:
                row_sums[j] += magnitude
    infinity = max(row_sums)
    require(infinity > 0, "unexpected zero midpoint residual")
    return lmid, dmid, infinity, residual_entries


def ceil_scaled_nonnegative(value, scale):
    require(type(value) is Q and value >= 0 and scale > 0,
            "nonnegative fixed-point upper bound")
    numerator = value.numerator * scale
    return -((-numerator) // value.denominator)


def inverse_norm_upper_bounds(lower, bits=NORM_BOUND_BITS):
    """Rigorous fixed-point bounds for ||L^-1||_inf and ||L^-1||_1.

    For |x|_inf <= 1, forward substitution gives
      r_i <= 1 + sum_{j<i} |L_ij| r_j.
    The reverse recurrence for L^T gives the corresponding one-norm bound.
    Coefficients and every update are rounded upward on the fixed grid.
    """
    require(type(bits) is int and bits >= 64, "norm bound precision")
    scale = 1 << bits
    n = len(lower)
    coefficients = [{j: ceil_scaled_nonnegative(abs(value), scale)
                     for j, value in row.items()} for row in lower]
    row_bounds = [scale for _ in range(n)]
    for i in range(n):
        total = scale
        for j, coefficient in coefficients[i].items():
            total += -((-(coefficient * row_bounds[j])) // scale)
        row_bounds[i] = total
    transpose_bounds = [scale for _ in range(n)]
    for i in range(n - 1, -1, -1):
        total = scale
        for j in range(i + 1, n):
            coefficient = coefficients[j].get(i)
            if coefficient is not None:
                total += -((-(coefficient * transpose_bounds[j])) // scale)
        transpose_bounds[i] = total
    infinity = Q(max(row_bounds), scale)
    one = Q(max(transpose_bounds), scale)
    require(infinity >= 1 and one >= 1,
            "inverse norm bound postcondition")
    return infinity, one, row_bounds, transpose_bounds


def rational_sha(values):
    raw = json.dumps([str(value) for value in values],
                     separators=(",", ":")).encode()
    return sha256(raw)


def certify_matrix(matrix, strata, exponents=None,
                   interval_bits=INTERVAL_BITS,
                   norm_bits=NORM_BOUND_BITS):
    """Produce both rigorous positive-definiteness certificates."""
    if exponents is None:
        exponents = congruence_exponents(matrix)
    scale, lower, pivots = interval_ldl(
        matrix, strata, exponents, interval_bits)
    lmid, dmid, residual, residual_entries = midpoint_residual(
        matrix, exponents, lower, pivots, scale)
    inverse_inf, inverse_one, row_bounds, transpose_bounds = \
        inverse_norm_upper_bounds(lmid, norm_bits)
    minimum_d = min(dmid)
    base_lower = minimum_d / (inverse_inf * inverse_one)
    require(residual < base_lower,
            "midpoint residual not below rigorous perturbation base")
    residual_upper_exponent = ceil_log2(residual)
    base_lower_exponent = floor_log2(base_lower)
    require(residual_upper_exponent < base_lower_exponent,
            "explicit dyadic residual gap is not strict")
    pivot_rows = [[str(lo), str(hi)] for lo, hi in pivots]
    return {
        "scale": scale,
        "lower": lower,
        "pivots": pivots,
        "lmid": lmid,
        "dmid": dmid,
        "residual": residual,
        "residual_entries": residual_entries,
        "inverse_inf": inverse_inf,
        "inverse_one": inverse_one,
        "row_bounds": row_bounds,
        "transpose_bounds": transpose_bounds,
        "minimum_d": minimum_d,
        "base_lower": base_lower,
        "residual_upper_exponent": residual_upper_exponent,
        "base_lower_exponent": base_lower_exponent,
        "pivot_rows": pivot_rows,
    }


def closure_snapshots(entries):
    for snapshot, description, maximum in entries:
        verify_snapshot(snapshot, description, maximum)


def build_report(result_path, expected_result_sha, expected_checker_sha):
    start = time.monotonic()
    require(expected_result_sha == RESULT_SHA,
            "result SHA differs from frozen completed-result identity")
    self_snapshot = read_pinned(
        Path(__file__), expected_checker_sha, "obstruction checker self",
        MAX_SOURCE_BYTES)
    consumer_snapshot = read_pinned(
        CONSUMER, CONSUMER_SHA, "frozen reconstruction consumer",
        MAX_SOURCE_BYTES)
    consumer = load_frozen_consumer(consumer_snapshot)

    consumer_gate, consumer_gate_snapshot = consumer.load_consumer_gate()
    producer_gate, producer_gate_snapshot = consumer.load_producer_gate()
    _, authorization_snapshot = consumer.load_authorization()
    reference, reference_snapshot = consumer.load_reference()
    result_snapshot = consumer.read_pinned(
        result_path, expected_result_sha, "completed degree-three result",
        MAX_RESULT_BYTES)
    snapshots = (
        self_snapshot, consumer_snapshot, consumer_gate_snapshot,
        producer_gate_snapshot, authorization_snapshot, reference_snapshot,
        result_snapshot,
    )
    require(len({snapshot.identity for snapshot in snapshots}) ==
            len(snapshots), "trusted input path alias")
    require(result_snapshot.raw.startswith(b"{") and
            result_snapshot.raw.endswith(b"}\n"),
            "completed degree-three result canonical envelope")
    value = consumer.strict_json(
        result_snapshot.raw, "completed degree-three result")
    consumer.validate_result_metadata(value, producer_gate)
    i_table = consumer.parse_i_rows(value["i_moment_rows"])
    j_table = consumer.parse_j_rows(value["j_moment_rows"])
    labels, a_matrix, b_matrix = consumer.reconstruct_matrices(
        i_table, j_table)
    require(len(labels) == EXPECTED_DIMENSION,
            "reconstructed matrix dimension")
    a_sha = consumer.matrix_sha(a_matrix)
    b_sha = consumer.matrix_sha(b_matrix)
    require(a_sha == value["a_matrix_sha256"] and
            b_sha == value["b48_matrix_sha256"],
            "secondary reconstructed matrix hashes")
    _, d2_denominator, d2_numerator = \
        consumer.validate_degree2_principal(a_matrix, b_matrix, reference)
    require(d2_denominator == consumer.fraction(
                value["particular_denominator"], "particular denominator") and
            d2_numerator == consumer.fraction(
                value["particular_numerator"], "particular numerator"),
            "embedded exact degree-two contraction")
    active, discarded, gram_pivots = consumer.gram_independent_coordinates(
        a_matrix, b_matrix, labels, consumer.CHANNELS3,
        expected_discarded=consumer.EXPECTED_DISCARDED,
        expected_rank=EXPECTED_RANK)
    c_matrix = [[a_matrix[i][j] - b_matrix[i][j] for j in active]
                for i in active]
    active_strata = [labels[i][0] for i in active]
    require(all(c_matrix[i][j] == c_matrix[j][i]
                for i in range(EXPECTED_RANK)
                for j in range(EXPECTED_RANK)), "exact C symmetry")
    exact_block_band_gate(c_matrix, active_strata)

    exponents = congruence_exponents(c_matrix)
    certificate = certify_matrix(c_matrix, active_strata, exponents)
    pivot_rows = certificate["pivot_rows"]
    residual = certificate["residual"]
    base_lower = certificate["base_lower"]
    scaled_diagonal = [congruence_entry(
        c_matrix[i][i], exponents[i], exponents[i])
        for i in range(EXPECTED_RANK)]
    discarded_labels = [[labels[i][0], list(consumer.CHANNELS3[labels[i][1]])]
                        for i in discarded]

    closure_entries = (
        (self_snapshot, "obstruction checker self closure", MAX_SOURCE_BYTES),
        (consumer_snapshot, "reconstruction consumer closure", MAX_SOURCE_BYTES),
        (consumer_gate_snapshot, "consumer gate closure", 100_000),
        (producer_gate_snapshot, "producer gate closure", 100_000),
        (authorization_snapshot, "authorization closure", 100_000),
        (reference_snapshot, "degree-two reference closure", 5_000_000),
        (result_snapshot, "completed result closure", MAX_RESULT_BYTES),
    )
    closure_snapshots(closure_entries)
    elapsed = time.monotonic() - start
    usage = resource.getrusage(resource.RUSAGE_SELF)
    report = {
        "status": "exact-c10-d4-degree3-finite-space-obstruction",
        "rigorous": True,
        "theorem_ready_scope": "D4 degree-three finite space only",
        "conclusion": (
            "A-B is positive definite on the exact 154-dimensional "
            "Gram-independent quotient; hence v^T B v / v^T A v < 1 "
            "for every nonzero quotient vector"
        ),
        "identity": {
            "checker_sha256": self_snapshot.digest,
            "reconstruction_consumer_sha256": consumer_snapshot.digest,
            "producer_result_sha256": result_snapshot.digest,
            "consumer_gate_sha256": consumer_gate_snapshot.digest,
            "producer_gate_sha256": producer_gate_snapshot.digest,
            "authorization_sha256": authorization_snapshot.digest,
            "degree2_reference_sha256": reference_snapshot.digest,
        },
        "trust_boundary": {
            "matrix_source": (
                "canonical dense I rows plus inventory-bounded sparse J rows "
                "reconstructed by the byte-pinned frozen consumer"
            ),
            "source_integrals_independently_recomputed": False,
            "sparse_omission": (
                "omitted queried J tags denote zero only under the pinned "
                "result SHA and exact producer fused/unfused equality"
            ),
            "serialized_matrix_hashes": "secondary equality checks only",
            "integration_launched": False,
        },
        "reconstruction": {
            "full_dimension": len(labels),
            "exact_gram_rank": len(active),
            "discarded_gram_coordinates": discarded_labels,
            "exact_gram_pivot_sha256": rational_sha(gram_pivots),
            "a_matrix_sha256": a_sha,
            "b48_matrix_sha256": b_sha,
            "c_active_matrix_sha256": consumer.matrix_sha(c_matrix),
            "degree2_principal_entries_equal": True,
            "degree2_exact_contraction_equal": True,
        },
        "exact_congruence": {
            "kind": "positive diagonal powers of two",
            "exponents": exponents,
            "exponents_sha256": sha256(json.dumps(
                exponents, separators=(",", ":")).encode()),
            "scaled_diagonal_lower": str(min(scaled_diagonal)),
            "scaled_diagonal_upper": str(max(scaled_diagonal)),
            "scaled_diagonal_range_gate": "1 <= diagonal < 4",
            "exact_block_tridiagonal": True,
        },
        "directed_interval_ldl": {
            "fixed_point_bits": INTERVAL_BITS,
            "rounding": "integer-endpoint outward rounding after every operation",
            "pivot_count": len(pivot_rows),
            "all_pivot_lower_endpoints_positive": True,
            "pivot_integer_endpoints_over_2pow768": pivot_rows,
            "pivot_endpoint_sha256": sha256(json.dumps(
                pivot_rows, separators=(",", ":")).encode()),
            "pivot_lower_signs": ["positive"] * len(pivot_rows),
            "pivot_lower_sign_sha256": sha256(json.dumps(
                ["positive"] * len(pivot_rows),
                separators=(",", ":")).encode()),
            "minimum_pivot_lower_integer": str(min(
                value[0] for value in certificate["pivots"])),
        },
        "exact_midpoint_residual_check": {
            "factorization": "H = Lhat Dhat Lhat^T + E",
            "residual_infinity_norm": str(residual),
            "residual_entry_sha256": rational_sha(
                certificate["residual_entries"]),
            "inverse_norm_fixed_point_bits": NORM_BOUND_BITS,
            "inverse_l_infinity_upper": str(certificate["inverse_inf"]),
            "inverse_l_one_upper": str(certificate["inverse_one"]),
            "minimum_midpoint_pivot": str(certificate["minimum_d"]),
            "perturbation_base_lower": str(base_lower),
            "strict_exact_residual_gate": True,
            "residual_upper_bound": (
                f"2^{certificate['residual_upper_exponent']}"
            ),
            "perturbation_base_lower_bound": (
                f"2^{certificate['base_lower_exponent']}"
            ),
            "dyadic_separation_bits": (
                certificate["base_lower_exponent"] -
                certificate["residual_upper_exponent"]
            ),
        },
        "resource_measurement": {
            "elapsed_seconds": format(elapsed, ".9f"),
            "peak_rss_kib": usage.ru_maxrss,
        },
        "closure": {
            "all_seven_pinned_inputs_reverified_before_publication": True,
            "caller_pinned_checker_self": True,
            "caller_pinned_completed_result": True,
            "consumer_gate_status": consumer_gate["status"],
        },
    }
    return report, closure_entries


def publish_new(path_text, raw, closure_entries):
    """Publish canonical bytes without overwriting or aliasing any path."""
    path = Path(path_text).absolute()
    require(path.parent.is_dir(), "output parent must exist")
    require(not path.exists() and not path.is_symlink(),
            "output path must be new")
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        closure_snapshots(closure_entries)
        os.link(temporary, path)
        os.unlink(temporary)
        temporary = None
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        visible = path.read_bytes()
        require(visible == raw, "published output byte closure")
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return sha256(raw)


def main():
    parser = argparse.ArgumentParser(
        description="Rigorous exact finite-space D4 degree-three obstruction")
    parser.add_argument("--result", required=True,
                        help="completed exact producer artifact")
    parser.add_argument("--expected-result-sha256", required=True,
                        help="must equal the frozen completed-result SHA")
    parser.add_argument("--expected-checker-sha256", required=True,
                        help="caller-pinned SHA of these checker bytes")
    parser.add_argument("--output", required=True,
                        help="new canonical JSON artifact path")
    arguments = parser.parse_args()
    report, closure_entries = build_report(
        arguments.result, arguments.expected_result_sha256,
        arguments.expected_checker_sha256)
    raw = (json.dumps(report, sort_keys=True,
                      separators=(",", ":")) + "\n").encode()
    digest = publish_new(arguments.output, raw, closure_entries)
    print(json.dumps({
        "status": report["status"],
        "output": str(Path(arguments.output)),
        "output_sha256": digest,
        "exact_gram_rank": report["reconstruction"]["exact_gram_rank"],
        "all_pivots_positive": True,
        "strict_exact_residual_gate": True,
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
