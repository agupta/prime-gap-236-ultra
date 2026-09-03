#!/usr/bin/env python3
"""C10 density and feature adapters for importance-Ritz discovery.

The adapter deliberately keeps stochastic discovery separate from exact
integration.  It loads a finite exact input vector, rescales it by a common
positive constant for safe floating-point evaluation, and exposes the two
unnormalised log densities and feature vectors in equations (1)--(2) of
``IMPORTANCE-RITZ-DESIGN.md``.
"""

from __future__ import annotations

import json
import hashlib
import math
import re
from fractions import Fraction
from pathlib import Path

from importance_oracle import (
    CHANNEL_POWERS,
    load_exact_expectation_oracle,
)
from importance_point_eval import (
    MonomialSymmetricPointEvaluator,
    evaluate_sieve_polynomial,
    distinguished_intervals,
    marginal_multiplier_vector,
    stratum_statistics,
    support_contains,
)


_CANONICAL_INTEGER = re.compile(r"^(?:0|-?[1-9][0-9]*)$")
_CANONICAL_FRACTION = re.compile(
    r"^(?:0|-?[1-9][0-9]*)/[1-9][0-9]*$")
_CANONICAL_DECIMAL = re.compile(
    # Decimal vectors deliberately preserve the producer's finite decimal
    # spelling (including significant trailing zeroes) and interpret it as
    # an exact rational.  Exponents, whitespace, leading zeroes, and -0 are
    # still rejected.
    r"^-?(?:0|[1-9][0-9]*)\.[0-9]+$")


def _reject_json_float(_value):
    raise ValueError("floating-point JSON token in exact vector")


def _reject_json_constant(_value):
    raise ValueError("nonfinite JSON token in exact vector")


def _strict_json_bytes(data):
    if not isinstance(data, bytes) or len(data) > 64_000_000:
        raise ValueError("vector must be bounded JSON bytes")

    def pairs_hook(pairs):
        answer = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in answer:
                raise ValueError("duplicate or non-string JSON key in vector")
            answer[key] = value
        return answer

    return json.loads(
        data.decode("utf-8"), object_pairs_hook=pairs_hook,
        parse_float=_reject_json_float, parse_constant=_reject_json_constant)


def _fraction(value):
    if isinstance(value, bool):
        raise TypeError("Boolean is not an exact scalar")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        if len(value) > 100_000 or not (
                _CANONICAL_INTEGER.fullmatch(value) or
                _CANONICAL_FRACTION.fullmatch(value) or
                _CANONICAL_DECIMAL.fullmatch(value)):
            raise ValueError("coefficient is not an accepted exact scalar")
        answer = Fraction(value)
        if answer == 0 and value.startswith("-"):
            raise ValueError("negative zero is not an accepted exact scalar")
        if "/" in value and str(answer) != value:
            raise ValueError("coefficient fraction is not reduced")
        return answer
    raise TypeError("coefficient must be an exact integer or rational string")


def _exact_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an exact integer")
    return value


def _parse_basis(raw_basis, k):
    if not isinstance(raw_basis, list) or not raw_basis:
        raise ValueError("basis must be a nonempty list")
    answer = []
    for index, item in enumerate(raw_basis):
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(f"basis[{index}] must be [a, partition]")
        residual = _exact_int(item[0], f"basis[{index}] residual")
        partition_raw = item[1]
        if residual < 0 or not isinstance(partition_raw, list):
            raise ValueError(f"malformed basis[{index}]")
        partition = tuple(
            _exact_int(x, f"basis[{index}] part") for x in partition_raw)
        if (any(x <= 0 for x in partition) or len(partition) > k or
                partition != tuple(sorted(partition, reverse=True))):
            raise ValueError(f"basis[{index}] partition is not canonical")
        answer.append((residual, partition))
    if len(set(answer)) != len(answer):
        raise ValueError("basis contains duplicate labels")
    return tuple(answer)


class C10ImportanceDensity:
    """Prepared I/J targets and normalized degree-two stratum features."""

    def __init__(self, vector_path, parameter_artifact_path):
        self.vector_path = Path(vector_path)
        self.parameter_artifact_path = Path(parameter_artifact_path)
        vector_bytes = self.vector_path.read_bytes()
        vector = _strict_json_bytes(vector_bytes)
        oracle = load_exact_expectation_oracle(self.parameter_artifact_path)
        if not isinstance(vector, dict):
            raise ValueError("vector top level must be an object")
        if isinstance(vector.get("k"), bool) or vector.get("k") != 48:
            raise ValueError("vector artifact must be k=48")
        basis = vector.get("basis")
        raw_coefficients = vector.get("rational_vector")
        if not isinstance(basis, list) or not isinstance(raw_coefficients, list):
            raise ValueError("vector artifact lacks basis or rational_vector")
        if len(basis) != len(raw_coefficients) or not basis:
            raise ValueError("empty or mismatched fixed vector")
        dimension = _exact_int(vector.get("basis_dimension"),
                               "basis_dimension")
        if dimension != len(basis):
            raise ValueError("basis_dimension does not match vector length")
        coefficients = [_fraction(x) for x in raw_coefficients]
        common_scale = max(abs(x) for x in coefficients)
        if common_scale == 0:
            raise ValueError("fixed polynomial is identically zero")

        self.k = 48
        self.vector_sha256 = hashlib.sha256(vector_bytes).hexdigest()
        self.parameter_sha256 = oracle["source_sha256"]
        self.basis = _parse_basis(basis, self.k)
        exact_scaled = tuple(x / common_scale for x in coefficients)
        self.coefficients = tuple(float(x) for x in exact_scaled)
        if not all(math.isfinite(x) for x in self.coefficients):
            raise ArithmeticError("coefficient normalization was not finite")
        if any(exact != 0 and approximate == 0
               for exact, approximate in zip(
                   exact_scaled, self.coefficients)):
            raise ArithmeticError("coefficient normalization underflowed")
        self.evaluator = MonomialSymmetricPointEvaluator(
            item[1] for item in self.basis)
        required_marginal_partitions = set()
        for _, partition in self.basis:
            required_marginal_partitions.add(partition)
            for exponent in set(partition):
                rest = list(partition)
                rest.remove(exponent)
                required_marginal_partitions.add(tuple(rest))
        self.marginal_evaluator = MonomialSymmetricPointEvaluator(
            required_marginal_partitions)

        exact_parameters = oracle["parameters"]
        self.alpha_exact = exact_parameters["alpha"]
        self.eta_exact = exact_parameters["eta"]
        self.delta_exact = exact_parameters["delta"]
        self.beta1_exact = exact_parameters["beta1"]
        self.beta2_exact = exact_parameters["beta2"]
        self.beta3_exact = exact_parameters["beta3plus"]
        self.alpha = float(self.alpha_exact)
        self.eta = float(self.eta_exact)
        self.delta = float(self.delta_exact)

        active = []
        for r in range(self.k + 1):
            if r == 0 or r * self.delta_exact < min(
                    self.alpha_exact, self.beta_exact(r)):
                active.append(r)
        if active != list(range(len(active))):
            raise ValueError("active C10 strata are unexpectedly nonconsecutive")
        self.strata = tuple(active)
        self.channels = tuple((r, a, b) for r in self.strata
                              for a, b in CHANNEL_POWERS)
        self.dimension = len(self.channels)

    def beta_exact(self, r):
        if r == 1:
            return self.beta1_exact
        if r == 2:
            return self.beta2_exact
        return self.beta3_exact

    def beta(self, r):
        r = _exact_int(r, "stratum")
        return float(self.beta_exact(r))

    @staticmethod
    def _finite_nonnegative(point):
        return all(not isinstance(x, bool) and math.isfinite(float(x)) and
                   x >= 0 for x in point)

    def i_support(self, point):
        return (len(point) == self.k and self._finite_nonnegative(point) and
                support_contains(point, self.alpha, self.delta, self.beta))

    def j_support(self, common):
        if len(common) != self.k - 1 or not self._finite_nonnegative(common):
            return False
        if sum(common) > self.eta:
            return False
        small, large = distinguished_intervals(
            common, self.alpha, self.eta, self.delta, self.beta)
        return small is not None or large is not None

    @staticmethod
    def _log_square(value):
        value = float(value)
        if not math.isfinite(value):
            raise ArithmeticError("nonfinite polynomial or marginal value")
        if value == 0:
            return -math.inf
        return 2 * math.log(abs(value))

    def polynomial(self, point):
        return evaluate_sieve_polynomial(
            point, self.basis, self.coefficients, self.evaluator)

    def i_log_density(self, point):
        if not self.i_support(point):
            return -math.inf
        return self._log_square(self.polynomial(point))

    def i_features(self, point):
        if not self.i_support(point):
            raise ValueError("I feature point is outside support")
        r, large_sum, small_sum = stratum_statistics(point, self.delta)
        if r not in self.strata:
            raise ArithmeticError("support point has an unlisted stratum")
        features = [0.0] * self.dimension
        offset = 6 * r
        for channel, (a, b) in enumerate(CHANNEL_POWERS):
            features[offset + channel] = \
                (large_sum / self.alpha) ** a * \
                (small_sum / self.alpha) ** b
        return features

    def j_marginals(self, common):
        if not self.j_support(common):
            return [0.0] * self.dimension
        return marginal_multiplier_vector(
            common, self.basis, self.coefficients, self.channels,
            self.alpha, self.eta, self.delta, self.beta,
            normalize_powers=True, evaluator=self.marginal_evaluator)

    def j_m0(self, common, marginals=None):
        if marginals is None:
            marginals = self.j_marginals(common)
        if len(marginals) != self.dimension:
            raise ValueError("marginal vector dimension mismatch")
        return math.fsum(marginals[6 * r] for r in self.strata)

    def j_log_density(self, common):
        if not self.j_support(common):
            return -math.inf
        return self._log_square(self.j_m0(common))

    def j_features(self, common):
        marginals = self.j_marginals(common)
        m0 = self.j_m0(common, marginals)
        if m0 == 0:
            raise ZeroDivisionError("J feature ratio is undefined at m0=0")
        if not math.isfinite(float(m0)):
            raise ArithmeticError("nonfinite base marginal")
        answer = [float(value / m0) for value in marginals]
        if not all(math.isfinite(x) for x in answer):
            raise ArithmeticError("nonfinite J feature ratio")
        return answer
