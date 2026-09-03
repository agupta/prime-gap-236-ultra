#!/usr/bin/env python3
"""Exact rational D4 oracle whitening and transformed C10 features.

The transform is fixed solely from the byte-pinned exact denominator oracle.
It is block-local in the 16 strata, preserves the degree-0/1/2 filtration,
and retains all 93 exact-active coordinates.  Stochastic v6 code evaluates
these transformed features directly at each point.
"""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction

from importance_density import C10ImportanceDensity
from importance_oracle import CHANNEL_POWERS, load_exact_expectation_oracle


CHANNEL_COUNT = 6
STRATA = tuple(range(16))
DIMENSION = 96


def _zero_matrix(dimension):
    return [[Fraction(0) for _ in range(dimension)]
            for _ in range(dimension)]


def exact_ldlt(matrix):
    dimension = len(matrix)
    if (not dimension or any(len(row) != dimension for row in matrix) or
            any(Fraction(matrix[i][j]) != Fraction(matrix[j][i])
                for i in range(dimension) for j in range(i))):
        raise ValueError("whitening denominator is not exact symmetric square")
    a = [[Fraction(value) for value in row] for row in matrix]
    lower = [[Fraction(int(i == j)) for j in range(dimension)]
             for i in range(dimension)]
    diagonal = [Fraction(0) for _ in range(dimension)]
    for j in range(dimension):
        pivot = a[j][j] - sum(
            lower[j][k] ** 2 * diagonal[k] for k in range(j))
        if pivot <= 0:
            raise ArithmeticError(f"nonpositive exact LDL pivot {j}")
        diagonal[j] = pivot
        for i in range(j + 1, dimension):
            lower[i][j] = (a[i][j] - sum(
                lower[i][k] * lower[j][k] * diagonal[k]
                for k in range(j))) / pivot
    for i in range(dimension):
        for j in range(i + 1):
            if sum(lower[i][k] * diagonal[k] * lower[j][k]
                   for k in range(j + 1)) != a[i][j]:
                raise ArithmeticError("exact LDL reconstruction failed")
    return lower, diagonal


def power_two_scales(diagonal):
    scales = []
    exponents = []
    scaled = []
    for value in diagonal:
        value = Fraction(value)
        exponent = 0
        current = value
        while current < 1:
            current *= 4
            exponent += 1
        while current >= 4:
            current /= 4
            exponent -= 1
        scale = (Fraction(2 ** exponent) if exponent >= 0 else
                 Fraction(1, 2 ** (-exponent)))
        if not 1 <= scale * scale * value < 4:
            raise AssertionError("dyadic pivot scaling failed")
        scales.append(scale)
        exponents.append(exponent)
        scaled.append(scale * scale * value)
    return scales, exponents, scaled


def whitening_transform(lower, scales):
    dimension = len(lower)
    transform = _zero_matrix(dimension)
    for column in range(dimension):
        for row in range(dimension - 1, -1, -1):
            right = scales[column] if row == column else Fraction(0)
            right -= sum(lower[k][row] * transform[k][column]
                         for k in range(row + 1, dimension))
            transform[row][column] = right
    for i in range(dimension):
        for j in range(dimension):
            observed = sum(lower[k][i] * transform[k][j]
                           for k in range(dimension))
            if observed != (scales[j] if i == j else 0):
                raise ArithmeticError("exact L^T T=S verification failed")
    return transform


def _matmul(left, right):
    rows = len(left)
    inner = len(right)
    columns = len(right[0])
    if any(len(row) != inner for row in left) or \
            any(len(row) != columns for row in right):
        raise ValueError("exact matrix dimensions differ")
    return [[sum(Fraction(left[i][k]) * Fraction(right[k][j])
                 for k in range(inner))
             for j in range(columns)] for i in range(rows)]


def _transpose(matrix):
    return [list(column) for column in zip(*matrix)]


def congruence(matrix, transform):
    return _matmul(_transpose(transform), _matmul(matrix, transform))


def build_transform(oracle):
    if (oracle["dimension"] != DIMENSION or
            tuple(oracle["strata"]) != STRATA or
            tuple(oracle["channel_powers"]) != tuple(CHANNEL_POWERS)):
        raise ValueError("exact D4 oracle geometry changed")
    full = _zero_matrix(DIMENSION)
    active_by_stratum = {}
    scaled_pivots = {}
    exponents = {}
    base_weights = [Fraction(0) for _ in range(DIMENSION)]
    for r in STRATA:
        offset = CHANNEL_COUNT * r
        active = [channel for channel in range(CHANNEL_COUNT)
                  if oracle["E_I"][offset + channel][offset + channel] > 0]
        active.sort(key=lambda channel: (sum(CHANNEL_POWERS[channel]), channel))
        if active != (([0, 2, 5]) if r == 0 else list(range(6))):
            raise ArithmeticError(f"unexpected active channels at stratum {r}")
        block = [[oracle["E_I"][offset + i][offset + j]
                  for j in active] for i in active]
        lower, diagonal = exact_ldlt(block)
        scales, block_exponents, block_scaled = power_two_scales(diagonal)
        local = whitening_transform(lower, scales)
        for i_position, i in enumerate(active):
            for j_position, j in enumerate(active):
                full[offset + i][offset + j] = local[i_position][j_position]
        # T is upper triangular in degree order.  The old tagged constant is
        # represented by exactly one new tagged constant with coefficient
        # 1/T_00; verify instead of assuming this structural statement.
        weight = Fraction(1, 1) / local[0][0]
        reconstructed = [local[i][0] * weight for i in range(len(active))]
        if reconstructed != [Fraction(1)] + [Fraction(0)] * (len(active) - 1):
            raise ArithmeticError("transformed tagged constant is misrepresented")
        base_weights[offset] = weight
        active_by_stratum[r] = tuple(active)
        scaled_pivots[r] = tuple(block_scaled)
        exponents[r] = tuple(block_exponents)
    active_count = sum(len(value) for value in active_by_stratum.values())
    if active_count != 93:
        raise ArithmeticError("whitening did not retain exactly 93 coordinates")
    encoded = json.dumps([[str(x) for x in row] for row in full],
                         separators=(",", ":")).encode()
    return {
        "matrix": full,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "active_by_stratum": active_by_stratum,
        "scaled_pivots": scaled_pivots,
        "scale_exponents": exponents,
        "base_weights": tuple(base_weights),
    }


def apply_transpose(transform, vector):
    if len(transform) != len(vector):
        raise ValueError("transform/vector dimensions differ")
    return [math.fsum(float(transform[i][j]) * float(vector[i])
                      for i in range(len(vector)))
            for j in range(len(vector))]


def transformed_oracle(original):
    package = build_transform(original)
    transform = package["matrix"]
    answer = dict(original)
    for old_key, new_key in (("I", "I"), ("B48", "B48"),
                             ("E_I", "E_I"), ("E_J", "E_J")):
        answer[new_key] = congruence(original[old_key], transform)
    answer["transform"] = package
    answer["original_E_I"] = original["E_I"]
    answer["original_E_J"] = original["E_J"]
    constants = [6 * r for r in STRATA]
    weights = package["base_weights"]
    if (sum(weights[i] * answer["E_I"][i][j] * weights[j]
            for i in constants for j in constants) != 1 or
            sum(weights[i] * answer["E_J"][i][j] * weights[j]
            for i in constants for j in constants) != 1):
        raise ArithmeticError("transformed base coefficients do not normalize")
    return answer


def load_transformed_oracle(path):
    return transformed_oracle(load_exact_expectation_oracle(path))


class WhitenedC10ImportanceDensity(C10ImportanceDensity):
    """The physical base target with directly evaluated whitened features."""

    def __init__(self, vector_path, parameter_artifact_path):
        super().__init__(vector_path, parameter_artifact_path)
        oracle = load_exact_expectation_oracle(parameter_artifact_path)
        package = build_transform(oracle)
        self.whitening_transform_exact = package["matrix"]
        self.whitening_transform_sha256 = package["sha256"]
        self.base_constant_weights_exact = package["base_weights"]
        self.base_constant_weights = tuple(
            float(value) for value in self.base_constant_weights_exact)

    def i_features_original(self, point):
        return super().i_features(point)

    def j_marginals_original(self, common):
        return super().j_marginals(common)

    def i_features(self, point):
        return apply_transpose(
            self.whitening_transform_exact,
            self.i_features_original(point))

    def j_marginals(self, common):
        return apply_transpose(
            self.whitening_transform_exact,
            self.j_marginals_original(common))

    def j_m0(self, common, marginals=None):
        if marginals is None:
            marginals = self.j_marginals(common)
        if len(marginals) != self.dimension:
            raise ValueError("transformed marginal dimension mismatch")
        return math.fsum(
            self.base_constant_weights[6 * r] * marginals[6 * r]
            for r in self.strata)
