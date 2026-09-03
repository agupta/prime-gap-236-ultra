#!/usr/bin/env python3
"""Independent hostile verifier for the frozen D4 calibration v6 package.

This file intentionally does not use the producer's LDL, transform, matrix
congruence, or point-evaluation helpers when reconstructing the mathematics.
It also records the known serialized-J counterexample without creating any
production or authorization directory.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
CODE = REPO / "agents/structural-basis/code"
sys.path.insert(0, str(CODE))

import importance_d4_calibration_v6 as V6  # noqa: E402
import importance_envelope as LEGACY_ENVELOPE  # noqa: E402
import importance_envelope_v6 as ENVELOPE  # noqa: E402
import importance_whitening_v6 as PRODUCER_WHITENING  # noqa: E402


GATE = REPO / "agents/structural-basis/results/importance_d4_calibration_gate_v6.json"
ORACLE = REPO / V6.REQUIRED_DATA_PATHS[0]
VECTOR = REPO / V6.REQUIRED_DATA_PATHS[1]
WEIGHTS = REPO / V6.REQUIRED_DATA_PATHS[2]
EXPECTED_TRANSFORM_SHA256 = \
    "f2a0e8325809956c6883191d04cde6bc67ea74c4af34f86dce7a1ac60c4ac1fb"
EXPECTED_FROZEN_HASHES = {
    "agents/structural-basis/results/importance_d4_calibration_gate_v6.json":
        "d7ab62d01cc873e732857f1662d40af53624aa1fe36abaaf58bacbe03729521b",
    "agents/structural-basis/code/build_importance_d4_calibration_gate_v6.py":
        "96e908fe7bf29e117a2d7919023d8c443618a4e85472cb9869fdd3178e5ed344",
    "agents/structural-basis/code/importance_d4_calibration_v6.py":
        "26cc965edcefaef939a692729f11ccc51e76252c4c1877a2f9c8027e5007cfb1",
    "agents/structural-basis/code/importance_whitening_v6.py":
        "fcbc7068c7e5648601316e043c2ecb9b50bc3324c8f3b576618eb04250ba7901",
    "agents/structural-basis/code/importance_envelope_v6.py":
        "741dc672228021d5e67e847c911cf3b19a7f70b4f908e600304c92569c8164ee",
    "agents/structural-basis/tests/test_importance_d4_calibration_v6.py":
        "39a267795154e52c2c8c407ef94be4adffbe2be0758f0d00adca3a965331fa4e",
    "agents/structural-basis/tests/test_importance_whitening_v6.py":
        "30fcc951164d1d40a395478f21692ade1372bb8be72849488751f07e3e816430",
    "agents/structural-basis/IMPORTANCE-D4-CALIBRATION-V6-SPEC.md":
        "5cd72aefe0a49ec5b867043d31f7eb48f023e707d3114e3cad51fe7046987de5",
    "agents/structural-basis/code/importance_d4_rank_postmortem.py":
        "62e0a032383a8124377dcb7ce144b88cdc5414b489b00d239e431523600d4987",
    "agents/structural-basis/tests/test_importance_d4_rank_postmortem.py":
        "dde27f36949b54888ef9d0352f79f534a0ae2dc10df2255d80e54d7e7290f69f",
    "agents/structural-basis/results/importance_d4_calibration_gate_v5.json":
        "860a9a51284187388e2384b7ca19615dc7d17eb523a7a4fa4d5617e2e6f29196",
}
POWERS = ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2))
N = 96


class AuditFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(data, label):
    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AuditFailure(f"duplicate key in {label}: {key}")
            result[key] = value
        return result

    def reject_constant(token):
        raise AuditFailure(f"nonfinite token in {label}: {token}")

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs_hook,
                      parse_constant=reject_constant)


def zeros(rows=N, columns=N):
    return [[Fraction(0) for _ in range(columns)] for _ in range(rows)]


def independent_oracle():
    raw = strict_json(ORACLE.read_bytes(), "exact D4 oracle")
    require(raw["rigorous_forms"] is True and raw["k"] == 48,
            "oracle status/k mismatch")
    require(tuple(map(tuple, raw["channel_powers"])) == POWERS,
            "oracle channel order mismatch")
    alpha = Fraction(raw["parameters"]["alpha"])
    degree = tuple(sum(pair) for pair in POWERS)
    i_matrix = zeros()
    for r in range(16):
        block = raw["i_blocks"][str(r)]
        require(len(block) == 6 and all(len(row) == 6 for row in block),
                f"I block {r} shape mismatch")
        for a in range(6):
            for b in range(6):
                require(block[a][b] == block[b][a],
                        f"I block {r} is asymmetric")
                i_matrix[6 * r + a][6 * r + b] = \
                    Fraction(block[a][b]) / alpha ** (degree[a] + degree[b])
    i0 = sum(i_matrix[6 * r][6 * r] for r in range(16))

    expected_j_keys = set()
    b48 = zeros()
    for r in range(16):
        for a in range(6):
            for b in range(a, 6):
                key = f"(({r}, {a}), ({r}, {b}))"
                expected_j_keys.add(key)
                value = 48 * Fraction(raw["j_entries"][key]) / \
                    alpha ** (degree[a] + degree[b])
                b48[6 * r + a][6 * r + b] = value
                b48[6 * r + b][6 * r + a] = value
    for r in range(15):
        for a in range(6):
            for b in range(6):
                key = f"(({r}, {a}), ({r + 1}, {b}))"
                expected_j_keys.add(key)
                value = 48 * Fraction(raw["j_entries"][key]) / \
                    alpha ** (degree[a] + degree[b])
                b48[6 * r + a][6 * (r + 1) + b] = value
                b48[6 * (r + 1) + b][6 * r + a] = value
    require(set(raw["j_entries"]) == expected_j_keys,
            "J oracle support is not exactly diagonal/adjacent")
    constants = tuple(6 * r for r in range(16))
    b0 = sum(b48[i][j] for i in constants for j in constants)
    require(i0 > 0 and b0 > 0, "nonpositive base form")
    return {
        "raw": raw, "alpha": alpha, "I0": i0, "B0": b0,
        "base_quotient": b0 / i0,
        "E_I": [[value / i0 for value in row] for row in i_matrix],
        "E_J": [[value / b0 for value in row] for row in b48],
        "I": i_matrix, "B48": b48,
    }


def independent_ldlt(block):
    n = len(block)
    require(n and all(len(row) == n for row in block), "LDL shape")
    lower = [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    diagonal = []
    for column in range(n):
        pivot = block[column][column] - sum(
            lower[column][k] * lower[column][k] * diagonal[k]
            for k in range(column))
        require(pivot > 0, f"nonpositive independent LDL pivot {column}")
        diagonal.append(pivot)
        for row in range(column + 1, n):
            numerator = block[row][column] - sum(
                lower[row][k] * lower[column][k] * diagonal[k]
                for k in range(column))
            lower[row][column] = numerator / pivot
    for i in range(n):
        for j in range(n):
            rebuilt = sum(lower[i][k] * diagonal[k] * lower[j][k]
                          for k in range(n))
            require(rebuilt == block[i][j], "independent LDL reconstruction")
    return lower, diagonal


def independent_transform(oracle):
    full = zeros()
    active_by_stratum = {}
    scaled_pivots = {}
    scale_exponents = {}
    base = [Fraction(0) for _ in range(N)]
    for r in range(16):
        offset = 6 * r
        active = [c for c in range(6)
                  if oracle["E_I"][offset + c][offset + c] > 0]
        active.sort(key=lambda c: (sum(POWERS[c]), c))
        expected = [0, 2, 5] if r == 0 else list(range(6))
        require(active == expected, f"wrong exact active channels at r={r}")
        block = [[oracle["E_I"][offset + i][offset + j] for j in active]
                 for i in active]
        lower, diagonal = independent_ldlt(block)
        scales = []
        exponents = []
        scaled = []
        for pivot in diagonal:
            exponent = 0
            candidate = pivot
            if candidate < 1:
                while candidate < 1:
                    candidate *= 4
                    exponent += 1
            else:
                while candidate >= 4:
                    candidate /= 4
                    exponent -= 1
            scale = (Fraction(2 ** exponent) if exponent >= 0 else
                     Fraction(1, 2 ** (-exponent)))
            require(Fraction(1) <= pivot * scale * scale < 4,
                    "independent dyadic scaling failed")
            scales.append(scale)
            exponents.append(exponent)
            scaled.append(pivot * scale * scale)
        n = len(active)
        local = [[Fraction(0) for _ in range(n)] for _ in range(n)]
        # Back substitution in L^T T = S, independently spelling out each
        # triangular equation rather than invoking the producer helper.
        for column in range(n):
            for row in reversed(range(n)):
                rhs = scales[column] if row == column else Fraction(0)
                for k in range(row + 1, n):
                    rhs -= lower[k][row] * local[k][column]
                local[row][column] = rhs
        for i, old_channel in enumerate(active):
            for j, new_channel in enumerate(active):
                full[offset + old_channel][offset + new_channel] = local[i][j]
        base[offset] = 1 / local[0][0]
        active_by_stratum[r] = tuple(active)
        scaled_pivots[r] = tuple(scaled)
        scale_exponents[r] = tuple(exponents)
    encoded = json.dumps([[str(value) for value in row] for row in full],
                         separators=(",", ":")).encode()
    return {
        "matrix": full,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "active_by_stratum": active_by_stratum,
        "scaled_pivots": scaled_pivots,
        "scale_exponents": scale_exponents,
        "base_weights": tuple(base),
    }


def block_congruence(matrix, transform):
    result = zeros()
    for r in range(16):
        ro = 6 * r
        for s in range(16):
            so = 6 * s
            if not any(matrix[ro + i][so + j] != 0
                       for i in range(6) for j in range(6)):
                continue
            for a in range(6):
                for b in range(6):
                    result[ro + a][so + b] = sum(
                        transform[ro + i][ro + a] *
                        matrix[ro + i][so + j] *
                        transform[so + j][so + b]
                        for i in range(6) for j in range(6))
    return result


def matmul_poly(left, right):
    result = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            result[i + j] += x * y
    return result


def add_poly(target, source, factor=Fraction(1)):
    if len(target) < len(source):
        target.extend(Fraction(0) for _ in range(len(source) - len(target)))
    for i, value in enumerate(source):
        target[i] += factor * value


def affine_power(constant, linear, exponent):
    # Degrees never exceed four, so this independent repeated multiplication
    # is intentionally different from the producer's binomial expansion.
    result = [Fraction(1)]
    for _ in range(exponent):
        result = matmul_poly(result, [constant, linear])
    return result


def independent_marginals(adapter, common, vector_raw):
    common = tuple(Fraction.from_float(float(x)) for x in common)
    alpha = Fraction.from_float(adapter.alpha)
    delta = Fraction.from_float(adapter.delta)
    scaled_exact = [Fraction(value) for value in vector_raw["rational_vector"]]
    common_scale = max(abs(value) for value in scaled_exact)
    # The runtime deliberately rounds each normalized coefficient once.
    coefficients = [Fraction.from_float(float(value / common_scale))
                    for value in scaled_exact]
    basis = [(item[0], tuple(item[1])) for item in vector_raw["basis"]]
    require(set(partition for _, partition in basis) <=
            {(), (2,), (3,), (4,), (2, 2)},
            "independent D4 marginal formula needs an unknown partition")
    common_sum = sum(common)
    power_sums = {p: sum(x ** p for x in common) for p in (2, 3, 4)}
    pair22 = sum(common[i] ** 2 * common[j] ** 2
                 for i in range(len(common)) for j in range(i + 1, len(common)))

    distinguished = []
    for coefficient, (residual_degree, partition) in zip(coefficients, basis):
        if partition == ():
            monomial = [Fraction(1)]
        elif len(partition) == 1:
            p = partition[0]
            monomial = [power_sums[p]] + [Fraction(0)] * (p - 1) + [Fraction(1)]
        else:
            require(partition == (2, 2), "unexpected double partition")
            monomial = [pair22, Fraction(0), power_sums[2]]
        term = matmul_poly(
            affine_power(Fraction(1) - common_sum, Fraction(-1),
                         residual_degree), monomial)
        add_poly(distinguished, term, coefficient)

    large_coordinates = [x for x in common if x > delta]
    small_coordinates = [x for x in common if x <= delta]
    r = len(large_coordinates)
    large_sum = sum(large_coordinates)
    small_sum = sum(small_coordinates)
    total_upper = alpha - common_sum
    beta_r = Fraction.from_float(adapter.beta(r))
    beta_next = Fraction.from_float(adapter.beta(r + 1))
    small_upper = min(delta, total_upper)
    small_present = (r == 0 or large_sum <= beta_r) and small_upper > 0
    large_upper = min(total_upper, beta_next - large_sum)
    large_present = large_upper > delta

    def integrate(poly, lower, upper):
        if upper <= lower:
            return Fraction(0)
        return sum(value * (upper ** (i + 1) - lower ** (i + 1)) /
                   (i + 1) for i, value in enumerate(poly))

    answer = [Fraction(0) for _ in range(N)]
    for channel, (a, b) in enumerate(POWERS):
        if small_present:
            multiplier = matmul_poly([large_sum ** a],
                                     affine_power(small_sum, 1, b))
            answer[6 * r + channel] += integrate(
                matmul_poly(distinguished, multiplier), 0, small_upper) / \
                alpha ** (a + b)
        if large_present:
            multiplier = matmul_poly(affine_power(large_sum, 1, a),
                                     [small_sum ** b])
            answer[6 * (r + 1) + channel] += integrate(
                matmul_poly(distinguished, multiplier), delta, large_upper) / \
                alpha ** (a + b)
    return answer


def transformed_vector(transform, vector):
    return [sum(transform[i][j] * vector[i] for i in range(N))
            for j in range(N)]


def verify_hashes_and_gate():
    for relative, expected in EXPECTED_FROZEN_HASHES.items():
        require(sha256(REPO / relative) == expected,
                f"frozen hash mismatch: {relative}")
    require(sha256(GATE) == EXPECTED_FROZEN_HASHES[
        "agents/structural-basis/results/importance_d4_calibration_gate_v6.json"],
        "v6 gate hash mismatch")
    bound = V6.load_and_validate_gate(GATE)
    gate = bound["gate"]
    require(gate["production_launch_authorized"] is False,
            "prelaunch gate unexpectedly authorizes production")
    for table_name in ("source_hashes", "data_hashes"):
        for relative, expected in gate[table_name].items():
            require(sha256(REPO / relative) == expected,
                    f"gate dependency mismatch: {relative}")
    require(gate["conventions"]["exact_whitening"]["transform_sha256"] ==
            EXPECTED_TRANSFORM_SHA256, "gate transform hash mismatch")
    return gate


def verify_exact_transform(independent):
    package = independent_transform(independent)
    require(package["sha256"] == EXPECTED_TRANSFORM_SHA256,
            "independent transform hash mismatch")
    require(sum(len(x) for x in package["active_by_stratum"].values()) == 93,
            "active dimension is not 93")
    t = package["matrix"]
    a_new = block_congruence(independent["E_I"], t)
    b_new = block_congruence(independent["E_J"], t)
    degrees = tuple(sum(pair) for pair in POWERS)
    for i in range(N):
        for j in range(N):
            if t[i][j] != 0:
                require(i // 6 == j // 6, "transform crosses strata")
                require(degrees[i % 6] <= degrees[j % 6],
                        "transform violates degree nesting")
    counts = []
    for degree in range(3):
        counts.append(sum(
            independent["E_I"][6 * r + c][6 * r + c] > 0
            for r in range(16) for c in range(6)
            if degrees[c] <= degree))
    require(counts == [16, 47, 93], "degree nesting count mismatch")
    active = {6 * r + c for r, channels in
              package["active_by_stratum"].items() for c in channels}
    for i in range(N):
        for j in range(N):
            expected = (next(
                (package["scaled_pivots"][i // 6][position]
                 for position, c in enumerate(package["active_by_stratum"][i // 6])
                 if 6 * (i // 6) + c == i), Fraction(0))
                        if i == j and i in active else Fraction(0))
            require(a_new[i][j] == expected, "T^T A T is not scaled diagonal")

    old_base = [Fraction(int(i % 6 == 0)) for i in range(N)]
    rebuilt = [sum(t[i][j] * package["base_weights"][j]
                   for j in range(N)) for i in range(N)]
    require(rebuilt == old_base, "T w does not reconstruct old constants")
    for matrix in (a_new, b_new):
        value = sum(package["base_weights"][i] * matrix[i][j] *
                    package["base_weights"][j]
                    for i in range(N) for j in range(N))
        require(value == 1, "transformed normalized base form is not exactly 1")

    producer = PRODUCER_WHITENING.load_transformed_oracle(ORACLE)
    require(package["matrix"] == producer["transform"]["matrix"],
            "producer transform differs from independent transform")
    require(package["base_weights"] == producer["transform"]["base_weights"],
            "producer base weights differ")
    require(a_new == producer["E_I"] and b_new == producer["E_J"],
            "producer transformed oracle has wrong congruence/orientation")

    # A deliberately reversed congruence is observably different.
    r = 1
    o = 6 * r
    wrong = [[sum(t[o + a][o + i] * independent["E_I"][o + i][o + j] *
                  t[o + b][o + j] for i in range(6) for j in range(6))
              for b in range(6)] for a in range(6)]
    right = [[a_new[o + a][o + b] for b in range(6)] for a in range(6)]
    require(wrong != right, "orientation discriminator unexpectedly degenerate")
    return package, a_new, b_new


def verify_weights(independent, package):
    raw = strict_json(WEIGHTS.read_bytes(), "stratum weights")
    with localcontext() as context:
        context.prec = 240

        def dec(fraction):
            return Decimal(fraction.numerator) / Decimal(fraction.denominator)

        denominator = Decimal(raw["baseline_denominator"])
        numerator = Decimal(raw["baseline_numerator"])
        i_values = [Decimal(x) for x in raw["baseline_i_by_r"]]
        j_values = [Decimal(x) for x in raw["baseline_j_by_common_r"]]
        tol = Decimal("1e-110")
        require(abs(denominator / dec(independent["I0"]) - 1) <= tol,
                "I0 Decimal artifact mismatch")
        require(abs(numerator / dec(independent["B0"]) - 1) <= tol,
                "48J0 Decimal artifact/factor mismatch")
        require(abs((numerator / denominator) /
                    dec(independent["base_quotient"]) - 1) <= tol,
                "base quotient mismatch")
        require(abs(sum(i_values) / denominator - 1) < Decimal("1e-150"),
                "I stratum values do not reconstruct I0")
        require(abs(sum(j_values) / numerator - 1) < Decimal("1e-150"),
                "J common-stratum values do not reconstruct 48J0")
        for r in range(16):
            old_mass = independent["E_I"][6 * r][6 * r]
            scale = package["matrix"][6 * r][6 * r]
            transformed_mass = package["base_weights"][6 * r] ** 2 * \
                scale ** 2 * old_mass
            require(old_mass == transformed_mass,
                    f"transformed I base mass mismatch at r={r}")
            require(abs((i_values[r] / denominator) / dec(old_mass) - 1) <= tol,
                    f"I stratum Decimal mismatch at r={r}")
    return {
        "maximum_z_bound": max(float(
            package["base_weights"][6 * r] ** 2 +
            (package["base_weights"][6 * (r + 1)] ** 2 if r < 15 else 0))
                               for r in range(16)),
    }


def verify_direct_points_and_envelope(package):
    adapter = PRODUCER_WHITENING.WhitenedC10ImportanceDensity(VECTOR, ORACLE)
    vector_raw = strict_json(VECTOR.read_bytes(), "D4 vector")
    transform = package["matrix"]
    max_i_error = 0.0
    max_j_scaled_error = 0.0
    max_m0_scaled_error = 0.0
    z_bounds = []
    last_common = None
    for r in range(16):
        i_point = tuple([0.0101] * r + [0.00001] * (48 - r))
        require(adapter.i_support(i_point), f"I witness unsupported at r={r}")
        large = sum(x for x in i_point if x > adapter.delta)
        small = sum(x for x in i_point if x <= adapter.delta)
        old = [0.0] * N
        for channel, (a, b) in enumerate(POWERS):
            old[6 * r + channel] = \
                (large / adapter.alpha) ** a * (small / adapter.alpha) ** b
        expected = [math.fsum(float(transform[i][j]) * old[i]
                              for i in range(N)) for j in range(N)]
        observed = adapter.i_features(i_point)
        error = max(abs(a - b) for a, b in zip(expected, observed))
        max_i_error = max(max_i_error, error)
        require(error == 0, f"I direct transform mismatch at r={r}")

        common = tuple([0.0101] * r + [0.00001] * (47 - r))
        require(adapter.j_support(common), f"J witness unsupported at r={r}")
        independent_old = independent_marginals(adapter, common, vector_raw)
        independent_new = transformed_vector(transform, independent_old)
        observed_new = adapter.j_marginals(common)
        scale = max(max(abs(float(x)) for x in independent_new), 1e-300)
        error = max(abs(float(x) - y) for x, y in
                    zip(independent_new, observed_new)) / scale
        max_j_scaled_error = max(max_j_scaled_error, error)
        require(error <= 2e-11,
                f"independent direct J marginal mismatch at r={r}: {error}")
        independent_m0 = sum(independent_old[6 * s] for s in range(16))
        observed_m0 = adapter.j_m0(common, observed_new)
        m0_scale = max(abs(float(independent_m0)), 1e-300)
        m0_error = abs(float(independent_m0) - observed_m0) / m0_scale
        max_m0_scaled_error = max(max_m0_scaled_error, m0_error)
        require(m0_error <= 2e-11,
                f"physical m0 reconstruction mismatch at r={r}")

        envelope = ENVELOPE.j_envelope_point(adapter, common)
        require(envelope is not None, f"missing v6 envelope at r={r}")
        allowed = (r, r + 1) if r < 15 else (r,)
        expected_bound = math.fsum(
            adapter.base_constant_weights[6 * s] ** 2 for s in allowed)
        require(envelope.z_bound == expected_bound,
                f"wrong Cauchy z bound at r={r}")
        require(0 <= envelope.z <= envelope.z_bound +
                128 * math.ulp(1.0) * max(1.0, envelope.z_bound),
                f"z exceeds Cauchy bound at r={r}")
        require(envelope.nonzero_constant_channels <= 2,
                f"too many constant branches at r={r}")
        z_bounds.append(expected_bound)
        last_common = common
    require(max(z_bounds) == 0.125 and max(z_bounds) < 2,
            "global v6 z bound is not the audited 1/8")
    try:
        LEGACY_ENVELOPE.j_envelope_point(adapter, last_common)
    except ArithmeticError:
        legacy_rejected = True
    else:
        legacy_rejected = False
    require(legacy_rejected, "legacy unweighted envelope silently accepted")
    return adapter, {
        "maximum_i_absolute_error": max_i_error,
        "maximum_j_scaled_error": max_j_scaled_error,
        "maximum_m0_scaled_error": max_m0_scaled_error,
        "maximum_z_bound": max(z_bounds),
        "legacy_envelope_rejected": legacy_rejected,
    }


def reproduce_serialized_j_gap(adapter):
    V6._patch_v5_runtime()
    schedule = V6.v5.tiny_smoke_schedule()
    spec = V6.v5.expected_chain_table()[64]  # J, common r=0, replicate 0.
    record = V6.v5.run_one_chain(adapter, spec, schedule)
    bound = math.fsum((adapter.base_constant_weights[0] ** 2,
                       adapter.base_constant_weights[6] ** 2))
    # Change only one batch second moment and its raw aggregate.  All estimated
    # matrices, J ratios, batch means, z precision, R-hat, and roots are thus
    # unchanged; the inflated raw variance can only increase the reported ESS.
    # Nevertheless this batch second moment is impossible because z^2 <= b^2.
    impossible = json.loads(json.dumps(record))
    seconds = [V6.v5.parse_float_hex(value)
               for value in impossible["batch_z_second_means"]]
    old_second = seconds[0]
    seconds[0] = 2 * bound * bound
    impossible["batch_z_second_means"][0] = V6.v5.float_hex(seconds[0])
    impossible["raw_second_sum"][-1] = V6.v5.float_hex(
        schedule["samples_per_batch"] * math.fsum(seconds))
    accepted = V6.validate_chain_record(
        impossible, spec, schedule, adapter=adapter)
    require(accepted is True, "known serialized-J gap was unexpectedly closed")
    return {
        "target": "J", "stratum": 0, "replicate": 0,
        "retained_samples": schedule["retained_samples"],
        "audited_z_bound": bound,
        "audited_z_second_bound": bound * bound,
        "original_batch_z_second": old_second,
        "mutated_batch_z_second": seconds[0],
        "bound_violation_factor": seconds[0] / (bound * bound),
        "mutated_fields": ["batch_z_second_means[0]", "raw_second_sum[-1]"],
        "matrix_and_ratio_inputs_unchanged": True,
        "v6_validate_chain_record_accepted": accepted,
    }


def main():
    gate = verify_hashes_and_gate()
    independent = independent_oracle()
    package, _, _ = verify_exact_transform(independent)
    weight_summary = verify_weights(independent, package)
    adapter, point_summary = verify_direct_points_and_envelope(package)
    counterexample = reproduce_serialized_j_gap(adapter)
    result = {
        "status": "AUDIT FAIL",
        "reason": "serialized J records do not enforce the v6 Cauchy bounds on z and z^2",
        "gate_sha256": sha256(GATE),
        "transform_sha256": package["sha256"],
        "source_count": len(gate["source_hashes"]),
        "data_count": len(gate["data_hashes"]),
        "active_dimensions": [16, 47, 93],
        "scaled_pivot_min": min(float(x) for values in
                                package["scaled_pivots"].values() for x in values),
        "scaled_pivot_max": max(float(x) for values in
                                package["scaled_pivots"].values() for x in values),
        "weights": weight_summary,
        "direct_points": point_summary,
        "counterexample": counterexample,
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
