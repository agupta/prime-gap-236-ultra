#!/usr/bin/env python3
"""Independent exact audit of the C10 D4 degree-3 obstruction artifact.

This file deliberately imports no producer, consumer, moment-table, or
obstruction-checker module.  It rebuilds the two rational matrices directly
from the canonical moment rows and verifies the fixed-point LDL certificate
with a separately written Fraction-endpoint interval implementation.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


Q = Fraction
PROJECT = Path(__file__).resolve().parents[2]
FRONTIER = PROJECT / "agents/small-delta-frontier"
RESULTS = FRONTIER / "results"
EXACT_RESULTS = PROJECT / "agents/exact-integrator/results"

MOMENT = RESULTS / "c10_D4_degree3_moment_exact.json"
OBSTRUCTION = RESULTS / "c10_D4_degree3_finite_space_obstruction.json"
PRODUCER_GATE = RESULTS / "c10_D4_degree3_moment_prelaunch_gate.json"
CONSUMER_GATE = RESULTS / "c10_D4_degree3_moment_consumer_gate.json"
AUTHORIZATION = RESULTS / "c10_D4_degree3_moment_authorization.json"
REFERENCE = EXACT_RESULTS / "c10_stratum_quadratic_cappedopt_D4_exact.json"
CONSUMER_REPORT = RESULTS / "c10_D4_degree3_consumer_report.json"
CONSUMER_LEDGER = RESULTS / "c10_D4_degree3_consumer_ledger.json"

EXPECTED_SHA = {
    FRONTIER / "certify_d4_degree3_finite_space.py":
        "d422fe7a472c61223a367c2e1cc1bb332fa79bcb2036f2e083c9ee183ed3d3d1",
    FRONTIER / "consume_stratum_moment_d4_degree3.py":
        "fedf1970b197af825675fa62644aa227875487453d125ad454d213ebcdedfb7c",
    FRONTIER / "check_stratum_moment_d4_degree3.py":
        "e48d46f447893d21addef38d979670107086550495fd390a1adeebf1ad6ba7ef",
    MOMENT:
        "c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5",
    OBSTRUCTION:
        "ace35d91e3ddc1d912711e140d72e54b6ad105355a59e44b07b9f53f3b2b1424",
    PRODUCER_GATE:
        "964ab9cdbe952b317f4c42d7b18a47269f886448fdf5f53d581f754405e32e3b",
    CONSUMER_GATE:
        "a1ab82c3f5f4805c3f3c2506baa00295caf884f94200da290bb906f74e4b0ed3",
    AUTHORIZATION:
        "8bf587b2ee0c0ff27c99d18446802b7be3007c17651cf4aa6c573b1745445c89",
    REFERENCE:
        "fbc8c38d2cf4241fdba03beb4251e2692e96af01ad4918c9a3a1075af2ed6e86",
    CONSUMER_REPORT:
        "4f92ffd427e7d8ca58e4a8e59f38ea0b383e8d57ba7e0668fc6df36074d6b797",
    CONSUMER_LEDGER:
        "5c99e3a52172a768b98154a725bc0e1ae03bd7ab5763c815f8de3989cb0389e2",
}

EXPECTED_A_SHA = "5a412e448a8156d8b4f6d94d58a146b6c2b9e05a0dacd5c47b20720e2dad985e"
EXPECTED_B_SHA = "58aa4b989641517597c85c0c3ad85d7a3bf96faed6665a3331ed3fa211a74252"
EXPECTED_C_SHA = "bd9c5717294d0284e755e5ca2df895ba38e4dcbf083c1f27137cb2261812b241"
EXPECTED_GRAM_PIVOT_SHA = "465e53036085cbeb95a5550bb12e9db6630ef40bbe5a6b6faf9b642693e45dce"
EXPECTED_INTERVAL_PIVOT_SHA = "ff8fb22931c5511a142456684cecdf9ee891a820bec67bda8648a2adfff03325"
EXPECTED_RESIDUAL_SHA = "abafdfa0bebe44b8065d861c3d2ba48af9ce5ffcb0b2bf52906c5c541b3140af"
EXPECTED_QUERY_SHA = "746de1d75e0deee16c7e15380e1b912dbe36c6de215e1e45844cec1ceea7fa92"

DEGREE = 3
STRATA = 16
K = 48
INTERVAL_BITS = 768
NORM_BITS = 512
RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_strict(path):
    raw = path.read_bytes()

    def pairs(items):
        result = {}
        for key, value in items:
            require(type(key) is str and key not in result,
                    f"duplicate/non-string key in {path}")
            result[key] = value
        return result

    def reject_nonfinite(token):
        raise ValueError(f"nonfinite JSON token in {path}: {token}")

    value = json.loads(raw.decode("utf-8", errors="strict"),
                       object_pairs_hook=pairs, parse_float=Decimal,
                       parse_constant=reject_nonfinite)
    return value, raw


def rational(text, description):
    require(type(text) is str and RATIONAL.fullmatch(text) is not None,
            f"bad rational syntax: {description}")
    value = Q(text)
    require(str(value) == text, f"noncanonical rational: {description}")
    return value


def powers(degree):
    return tuple((a, total - a) for total in range(degree + 1)
                 for a in range(total, -1, -1))


POWERS3 = powers(3)
POWERS2 = powers(2)
LABELS = tuple((r, power) for r in range(STRATA) for power in POWERS3)


def remaining(power, moment, large):
    a, b = power
    return (a - moment, b) if large else (a, b - moment)


def query_inventory():
    tags = set()
    for common in range(STRATA):
        for left_r, left_power in LABELS:
            left_class = left_r - common
            if left_class not in (0, 1):
                continue
            left_max = left_power[0] if left_class else left_power[1]
            for right_r, right_power in LABELS:
                right_class = right_r - common
                if right_class not in (0, 1):
                    continue
                right_max = right_power[0] if right_class else right_power[1]
                for j in range(left_max + 1):
                    lp = remaining(left_power, j, bool(left_class))
                    for k in range(right_max + 1):
                        rp = remaining(right_power, k, bool(right_class))
                        tags.add((common, left_class, right_class, j, k,
                                  lp[0] + rp[0], lp[1] + rp[1]))
    return frozenset(tags)


def parse_rows(moment):
    expected_i = [(r, u, v) for r in range(STRATA)
                  for u in range(2 * DEGREE + 1)
                  for v in range(2 * DEGREE + 1 - u)]
    rows = moment["i_moment_rows"]
    require(len(rows) == len(expected_i) == 448, "I inventory size")
    i_table = {}
    observed = []
    for number, row in enumerate(rows):
        require(type(row) is list and len(row) == 4 and
                all(type(x) is int for x in row[:3]), f"I row {number}")
        key = tuple(row[:3])
        observed.append(key)
        i_table[key] = rational(row[3], f"I row {number}")
    require(observed == expected_i and len(i_table) == len(expected_i),
            "I rows not complete canonical inventory")

    inventory = query_inventory()
    inventory_raw = json.dumps([list(x) for x in sorted(inventory)],
                               separators=(",", ":")).encode()
    require(len(inventory) == 10980 and digest(inventory_raw) == EXPECTED_QUERY_SHA,
            "independent J query inventory")
    j_table = {}
    previous = None
    for number, row in enumerate(moment["j_moment_rows"]):
        require(type(row) is list and len(row) == 8 and
                all(type(x) is int for x in row[:7]), f"J row {number}")
        key = tuple(row[:7])
        require(key in inventory and (previous is None or previous < key),
                f"J inventory/order at row {number}")
        previous = key
        value = rational(row[7], f"J row {number}")
        require(value != 0, f"sparse J row {number} serialized a zero")
        j_table[key] = value
    require(len(j_table) == len(moment["j_moment_rows"]) == 10516,
            "J sparse row cardinality")
    for key, value in j_table.items():
        r, lc, rc, j, k, u, v = key
        require(j_table.get((r, rc, lc, k, j, u, v)) == value,
                "J mirror symmetry")
    return i_table, j_table, inventory


def j_entry(table, common, left_power, right_power, left_class, right_class):
    left_max = left_power[0] if left_class else left_power[1]
    right_max = right_power[0] if right_class else right_power[1]
    total = Q(0)
    for j in range(left_max + 1):
        lp = remaining(left_power, j, bool(left_class))
        for k in range(right_max + 1):
            rp = remaining(right_power, k, bool(right_class))
            tag = (common, left_class, right_class, j, k,
                   lp[0] + rp[0], lp[1] + rp[1])
            total += math.comb(left_max, j) * math.comb(right_max, k) * \
                table.get(tag, Q(0))
    return total


def reconstruct(i_table, j_table):
    n = len(LABELS)
    a = [[Q(0) for _ in range(n)] for _ in range(n)]
    b = [[Q(0) for _ in range(n)] for _ in range(n)]
    for i, (left_r, left_power) in enumerate(LABELS):
        for j, (right_r, right_power) in enumerate(LABELS):
            if left_r == right_r:
                a[i][j] = i_table[(left_r,
                                   left_power[0] + right_power[0],
                                   left_power[1] + right_power[1])]
            for common in range(STRATA):
                lc, rc = left_r - common, right_r - common
                if lc in (0, 1) and rc in (0, 1):
                    # Definition 5 gives J; k=48 is applied exactly once here.
                    b[i][j] += K * j_entry(
                        j_table, common, left_power, right_power, lc, rc)
    require(all(a[i][j] == a[j][i] and b[i][j] == b[j][i]
                for i in range(n) for j in range(n)), "matrix symmetry")
    return a, b


def matrix_sha(matrix):
    raw = json.dumps([[str(value) for value in row] for row in matrix],
                     separators=(",", ":")).encode()
    return digest(raw)


def rational_list_sha(values):
    raw = json.dumps([str(value) for value in values],
                     separators=(",", ":")).encode()
    return digest(raw)


def local_gram_ldl(a, active):
    pivots = []
    for r in range(STRATA):
        indices = [i for i in active if LABELS[i][0] == r]
        lower = []
        diagonal = []
        for row_number, i in enumerate(indices):
            row = []
            for column_number, j in enumerate(indices[:row_number]):
                value = a[i][j] - sum(
                    (row[k] * diagonal[k] * lower[column_number][k]
                     for k in range(column_number)), Q(0))
                row.append(value / diagonal[column_number])
            pivot = a[i][i] - sum(
                (row[k] * row[k] * diagonal[k]
                 for k in range(row_number)), Q(0))
            require(pivot > 0, f"A block pivot {r}:{row_number}")
            lower.append(row + [Q(1)])
            diagonal.append(pivot)
            pivots.append(pivot)
    return pivots


def exact_quadratic(matrix, vector):
    nonzero = [i for i, value in enumerate(vector) if value]
    return sum((vector[i] * matrix[i][j] * vector[j]
                for i in nonzero for j in nonzero), Q(0))


def floor_log2(value):
    require(value > 0, "positive log2 input")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if exponent >= 0:
        if value.numerator < (value.denominator << exponent):
            exponent -= 1
    elif (value.numerator << (-exponent)) < value.denominator:
        exponent -= 1
    require(pow2(exponent) <= value < pow2(exponent + 1), "log2 enclosure")
    return exponent


def ceil_log2(value):
    exponent = floor_log2(value)
    return exponent if value == pow2(exponent) else exponent + 1


def pow2(exponent):
    return Q(1 << exponent) if exponent >= 0 else Q(1, 1 << (-exponent))


def scaling_exponents(matrix):
    result = [-(floor_log2(matrix[i][i]) // 2)
              for i in range(len(matrix))]
    require(all(Q(1) <= matrix[i][i] * pow2(2 * result[i]) < Q(4)
                for i in range(len(matrix))), "scaled diagonal range")
    return result


class GridIntervals:
    """Fixed dyadic grid; endpoint arithmetic is performed with Fraction."""

    def __init__(self, bits):
        self.scale = 1 << bits

    def snap(self, low, high):
        require(low <= high, "ordered interval")
        lo_num = low.numerator * self.scale
        hi_num = high.numerator * self.scale
        return (lo_num // low.denominator,
                -((-hi_num) // high.denominator))

    def exact(self, value):
        return self.snap(value, value)

    def endpoints(self, interval):
        return Q(interval[0], self.scale), Q(interval[1], self.scale)

    def sub(self, left, right):
        l0, l1 = self.endpoints(left)
        r0, r1 = self.endpoints(right)
        return self.snap(l0 - r1, l1 - r0)

    def mul(self, left, right):
        l0, l1 = self.endpoints(left)
        r0, r1 = self.endpoints(right)
        products = (l0 * r0, l0 * r1, l1 * r0, l1 * r1)
        return self.snap(min(products), max(products))

    def square(self, value):
        low, high = self.endpoints(value)
        minimum = Q(0) if low <= 0 <= high else min(low * low, high * high)
        return self.snap(minimum, max(low * low, high * high))

    def div(self, numerator, denominator):
        n0, n1 = self.endpoints(numerator)
        d0, d1 = self.endpoints(denominator)
        require(d0 > 0, "positive interval divisor")
        corners = (n0 / d0, n0 / d1, n1 / d0, n1 / d1)
        return self.snap(min(corners), max(corners))


def interval_ldl(matrix, strata, exponents):
    grid = GridIntervals(INTERVAL_BITS)
    lower = []
    pivots = []
    starts = {}
    for i, stratum in enumerate(strata):
        starts.setdefault(stratum, i)
        first = starts.get(stratum - 1, starts[stratum])
        row = {}
        for j in range(first, i):
            exact = matrix[i][j] * pow2(exponents[i] + exponents[j])
            value = grid.exact(exact)
            for k in sorted(set(row).intersection(lower[j])):
                value = grid.sub(value, grid.mul(
                    grid.mul(row[k], pivots[k]), lower[j][k]))
            require(pivots[j][0] > 0, f"positive divisor pivot {j}")
            row[j] = grid.div(value, pivots[j])
        exact_diagonal = matrix[i][i] * pow2(2 * exponents[i])
        pivot = grid.exact(exact_diagonal)
        for k, coefficient in row.items():
            pivot = grid.sub(pivot, grid.mul(
                grid.square(coefficient), pivots[k]))
        require(pivot[0] > 0, f"positive interval pivot {i}")
        lower.append(row)
        pivots.append(pivot)
    return grid, lower, pivots


def midpoint_residual(matrix, exponents, grid, lower, pivots):
    n = len(matrix)
    lmid = [{j: Q(value[0] + value[1], 2 * grid.scale)
             for j, value in row.items()} for row in lower]
    dmid = [Q(value[0] + value[1], 2 * grid.scale) for value in pivots]
    require(all(value > 0 for value in dmid), "positive midpoint diagonal")
    row_sums = [Q(0) for _ in range(n)]
    entries = []
    for i in range(n):
        for j in range(i + 1):
            approximation = dmid[i] if i == j else \
                lmid[i].get(j, Q(0)) * dmid[j]
            for k in set(lmid[i]).intersection(lmid[j]):
                approximation += lmid[i][k] * dmid[k] * lmid[j][k]
            exact = matrix[i][j] * pow2(exponents[i] + exponents[j])
            residual = exact - approximation
            entries.append(residual)
            row_sums[i] += abs(residual)
            if i != j:
                row_sums[j] += abs(residual)
    return lmid, dmid, max(row_sums), entries


def ceil_grid(value, scale):
    require(value >= 0, "nonnegative ceiling")
    return -((-(value.numerator * scale)) // value.denominator)


def inverse_bounds(lower):
    scale = 1 << NORM_BITS
    coefficients = [{j: ceil_grid(abs(value), scale)
                     for j, value in row.items()} for row in lower]
    n = len(lower)
    forward = [scale for _ in range(n)]
    for i in range(n):
        forward[i] = scale + sum(
            (-((-(coefficient * forward[j])) // scale)
             for j, coefficient in coefficients[i].items()), 0)
    backward = [scale for _ in range(n)]
    for i in range(n - 1, -1, -1):
        backward[i] = scale + sum(
            (-((-(coefficients[j][i] * backward[j])) // scale)
             for j in range(i + 1, n) if i in coefficients[j]), 0)
    return Q(max(forward), scale), Q(max(backward), scale)


def verify_dependencies():
    observed = {}
    for path, wanted in EXPECTED_SHA.items():
        got = digest(path.read_bytes())
        require(got == wanted, f"frozen SHA mismatch: {path}")
        observed[str(path.relative_to(PROJECT))] = got
    gate, _ = load_strict(PRODUCER_GATE)
    for section in ("source_hashes", "data_hashes"):
        for relative, wanted in gate[section].items():
            path = PROJECT / relative
            require(path.is_file() and digest(path.read_bytes()) == wanted,
                    f"producer dependency mismatch: {relative}")
    return observed


def main():
    dependency_hashes = verify_dependencies()
    moment, moment_raw = load_strict(MOMENT)
    obstruction, obstruction_raw = load_strict(OBSTRUCTION)
    producer_gate, _ = load_strict(PRODUCER_GATE)
    consumer_gate, _ = load_strict(CONSUMER_GATE)
    authorization, _ = load_strict(AUTHORIZATION)
    reference, _ = load_strict(REFERENCE)
    require(moment_raw.startswith(b"{") and moment_raw.endswith(b"}\n"),
            "moment canonical envelope")
    require(obstruction_raw.startswith(b"{") and obstruction_raw.endswith(b"}\n"),
            "obstruction canonical envelope")
    require(moment["status"] == "exact-c10-d4-degree3-moment-pass" and
            moment["rigorous_forms"] is True and
            moment["scope"] == "D4 degree-three finite space only; no D12 sign",
            "moment status/scope")
    require(producer_gate["degree"] == DEGREE and
            producer_gate["tag_schema_sha256"] ==
            moment["tag_schema_sha256"] and
            moment["gate_sha256"] == EXPECTED_SHA[PRODUCER_GATE] and
            moment["authorization_sha256"] == EXPECTED_SHA[AUTHORIZATION] and
            moment["driver_sha256"] ==
            EXPECTED_SHA[FRONTIER / "check_stratum_moment_d4_degree3.py"] and
            moment["reference_sha256"] == EXPECTED_SHA[REFERENCE] and
            moment["all_fused_unfused_entries_equal"] is True and
            moment["all_degree2_oracle_entries_equal"] is True,
            "moment provenance/equality gates")
    require(authorization == {
        "status": "root-authorized-c10-d4-degree3-moment-run",
        "authorized": True,
        "mode": "exact-D4-degree3-fused-plus-unfused",
        "gate_sha256": EXPECTED_SHA[PRODUCER_GATE],
        "driver_sha256":
            EXPECTED_SHA[FRONTIER / "check_stratum_moment_d4_degree3.py"],
    }, "authorization binding")
    require(consumer_gate["producer_gate_sha256"] ==
            EXPECTED_SHA[PRODUCER_GATE] and
            consumer_gate["producer_driver_sha256"] ==
            EXPECTED_SHA[FRONTIER / "check_stratum_moment_d4_degree3.py"] and
            consumer_gate["authorization_sha256"] ==
            EXPECTED_SHA[AUTHORIZATION] and
            consumer_gate["degree2_reference_sha256"] == EXPECTED_SHA[REFERENCE],
            "consumer gate binding")

    i_table, j_table, inventory = parse_rows(moment)
    a, b = reconstruct(i_table, j_table)
    a_sha, b_sha = matrix_sha(a), matrix_sha(b)
    require(a_sha == moment["a_matrix_sha256"] == EXPECTED_A_SHA,
            "independent A hash")
    require(b_sha == moment["b48_matrix_sha256"] == EXPECTED_B_SHA,
            "independent B=48J hash")

    # Definition 1 has beta(r)=97/625 for r>=3.  With delta=1/100,
    # r=15 is feasible and r=16 is the first impossible large-count stratum.
    delta, beta1, beta2, beta3 = Q(1, 100), Q(3, 20), Q(3, 20), Q(97, 625)
    beta = lambda r: beta1 if r == 1 else beta2 if r == 2 else beta3
    feasible = [r for r in range(1, K + 1) if r * delta < beta(r)]
    require(feasible == list(range(1, 16)), "complete stratum inventory")
    require(len(POWERS3) == 10 and len(LABELS) == 160 and
            set(POWERS3) == {(a0, b0) for a0 in range(4)
                             for b0 in range(4 - a0)},
            "complete total-degree <=3 monomial inventory")

    discarded = [i for i, (r, (large_power, _)) in enumerate(LABELS)
                 if r == 0 and large_power > 0]
    active = [i for i in range(len(LABELS)) if i not in discarded]
    expected_discarded = [1, 3, 4, 6, 7, 8]
    require(discarded == expected_discarded and len(active) == 154,
            "quotient coordinate inventory")
    require(all(a[i][j] == 0 and b[i][j] == 0
                for i in discarded for j in range(len(LABELS))),
            "discarded coordinates are not a common exact kernel")
    gram_pivots = local_gram_ldl(a, active)
    gram_sha = rational_list_sha(gram_pivots)
    require(len(gram_pivots) == 154 and gram_sha == EXPECTED_GRAM_PIVOT_SHA,
            "independent exact Gram rank/pivots")

    # Replay the old degree-2 exact vector in this independently rebuilt pencil.
    vector2 = [rational(value, f"reference vector {i}")
               for i, value in enumerate(reference["rational_vector"])]
    require(len(vector2) == STRATA * len(POWERS2), "reference vector size")
    positions3 = {label: i for i, label in enumerate(LABELS)}
    embedded = [Q(0) for _ in LABELS]
    for r in range(STRATA):
        for p, power in enumerate(POWERS2):
            embedded[positions3[(r, power)]] = vector2[r * len(POWERS2) + p]
    denominator = exact_quadratic(a, embedded)
    numerator = exact_quadratic(b, embedded)
    require(denominator == rational(reference["denominator"], "reference D") ==
            rational(moment["particular_denominator"], "moment D"),
            "degree-2 denominator replay")
    require(numerator == rational(reference["numerator"], "reference N") ==
            rational(moment["particular_numerator"], "moment N"),
            "degree-2 numerator replay")
    require(numerator / denominator ==
            rational(moment["particular_quotient"], "moment quotient"),
            "q=(v^T B v)/(v^T A v) orientation")
    require(denominator > 0 and numerator < denominator,
            "embedded q=B/A is below one")

    c = [[a[i][j] - b[i][j] for j in active] for i in active]
    c_sha = matrix_sha(c)
    strata = [LABELS[i][0] for i in active]
    require(c_sha == EXPECTED_C_SHA and
            all(c[i][j] == c[j][i] for i in range(154) for j in range(154)),
            "active C=A-B matrix")
    require(all(c[i][j] == 0 for i in range(154) for j in range(154)
                if abs(strata[i] - strata[j]) > 1),
            "exact block tridiagonality")

    stored_reconstruction = obstruction["reconstruction"]
    discarded_labels = [[LABELS[i][0], list(LABELS[i][1])]
                        for i in discarded]
    require(stored_reconstruction["full_dimension"] == 160 and
            stored_reconstruction["exact_gram_rank"] == 154 and
            stored_reconstruction["discarded_gram_coordinates"] ==
            discarded_labels and
            stored_reconstruction["exact_gram_pivot_sha256"] == gram_sha and
            stored_reconstruction["a_matrix_sha256"] == a_sha and
            stored_reconstruction["b48_matrix_sha256"] == b_sha and
            stored_reconstruction["c_active_matrix_sha256"] == c_sha,
            "obstruction reconstruction fields")

    exponents = scaling_exponents(c)
    require(exponents == obstruction["exact_congruence"]["exponents"],
            "congruence exponents")
    scaled_diagonal = [c[i][i] * pow2(2 * exponents[i])
                       for i in range(len(c))]
    require(str(min(scaled_diagonal)) ==
            obstruction["exact_congruence"]["scaled_diagonal_lower"] and
            str(max(scaled_diagonal)) ==
            obstruction["exact_congruence"]["scaled_diagonal_upper"],
            "scaled diagonal extrema")
    grid, lower, pivots = interval_ldl(c, strata, exponents)
    pivot_rows = [[str(lo), str(hi)] for lo, hi in pivots]
    pivot_sha = digest(json.dumps(pivot_rows,
                                  separators=(",", ":")).encode())
    stored_ldl = obstruction["directed_interval_ldl"]
    require(stored_ldl["fixed_point_bits"] == INTERVAL_BITS and
            stored_ldl["pivot_count"] == 154 and
            stored_ldl["all_pivot_lower_endpoints_positive"] is True and
            pivot_rows == stored_ldl["pivot_integer_endpoints_over_2pow768"] and
            pivot_sha == stored_ldl["pivot_endpoint_sha256"] ==
            EXPECTED_INTERVAL_PIVOT_SHA and
            min(lo for lo, _ in pivots) ==
            int(stored_ldl["minimum_pivot_lower_integer"]),
            "independent 768-bit interval pivot replay")

    lmid, dmid, residual, residual_entries = midpoint_residual(
        c, exponents, grid, lower, pivots)
    inverse_inf, inverse_one = inverse_bounds(lmid)
    minimum_d = min(dmid)
    base_lower = minimum_d / (inverse_inf * inverse_one)
    require(residual > 0 and residual < base_lower,
            "exact midpoint residual perturbation gate")
    residual_upper_exponent = ceil_log2(residual)
    base_lower_exponent = floor_log2(base_lower)
    require(residual_upper_exponent < base_lower_exponent,
            "strict dyadic residual separation")
    residual_sha = rational_list_sha(residual_entries)
    stored_residual = obstruction["exact_midpoint_residual_check"]
    require(stored_residual["inverse_norm_fixed_point_bits"] == NORM_BITS and
            stored_residual["strict_exact_residual_gate"] is True and
            str(residual) == stored_residual["residual_infinity_norm"] and
            residual_sha == stored_residual["residual_entry_sha256"] ==
            EXPECTED_RESIDUAL_SHA and
            str(inverse_inf) == stored_residual["inverse_l_infinity_upper"] and
            str(inverse_one) == stored_residual["inverse_l_one_upper"] and
            str(minimum_d) == stored_residual["minimum_midpoint_pivot"] and
            str(base_lower) == stored_residual["perturbation_base_lower"] and
            residual_upper_exponent == -725 and
            base_lower_exponent == -388 and
            base_lower_exponent - residual_upper_exponent == 337,
            "exact residual fields")

    require(obstruction["status"] ==
            "exact-c10-d4-degree3-finite-space-obstruction" and
            obstruction["rigorous"] is True and
            obstruction["theorem_ready_scope"] ==
            "D4 degree-three finite space only" and
            obstruction["identity"]["producer_result_sha256"] ==
            EXPECTED_SHA[MOMENT] and
            obstruction["identity"]["checker_sha256"] ==
            EXPECTED_SHA[FRONTIER / "certify_d4_degree3_finite_space.py"] and
            obstruction["identity"]["reconstruction_consumer_sha256"] ==
            EXPECTED_SHA[FRONTIER / "consume_stratum_moment_d4_degree3.py"],
            "obstruction identity bindings")

    print(json.dumps({
        "status": "AUDIT PASS",
        "obstruction_sha256": EXPECTED_SHA[OBSTRUCTION],
        "moment_sha256": EXPECTED_SHA[MOMENT],
        "a_matrix_sha256": a_sha,
        "b48_matrix_sha256": b_sha,
        "c_active_matrix_sha256": c_sha,
        "full_dimension": len(LABELS),
        "exact_gram_rank": len(active),
        "common_kernel_indices": discarded,
        "j_query_tags": len(inventory),
        "j_serialized_nonzero_rows": len(j_table),
        "gram_pivot_sha256": gram_sha,
        "interval_pivot_sha256": pivot_sha,
        "residual_entry_sha256": residual_sha,
        "residual_upper_exponent": residual_upper_exponent,
        "base_lower_exponent": base_lower_exponent,
        "dyadic_separation_bits": base_lower_exponent - residual_upper_exponent,
        "q_orientation": "B/A=(48J)/I",
        "dependency_hash_count": len(dependency_hashes),
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
