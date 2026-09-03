#!/usr/bin/env python3
"""Point evaluation for orbit-symmetric sieve polynomials.

This module is discovery infrastructure for IMPORTANCE-RITZ-DESIGN.md.  It
does not integrate a form and cannot certify a quotient.  The normalization
matches the monomial-orbit convention used by exact_integrator.py: equal
parts are unordered, while unequal exponents may be assigned to distinct
coordinates in every order.
"""

from __future__ import annotations

from itertools import product
from math import comb, isfinite


def _exact_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an exact integer")
    return value


def _require_finite(values, name):
    for value in values:
        finite_method = getattr(value, "is_finite", None)
        if callable(finite_method):
            finite = bool(finite_method())
        elif isinstance(value, float):
            finite = isfinite(value)
        else:
            finite = True
        if not finite:
            raise ValueError(f"{name} contains a nonfinite scalar")


def _basis_entry(item):
    if not isinstance(item, (list, tuple)) or len(item) != 2:
        raise ValueError("basis entry must be [residual exponent, partition]")
    a = _exact_int(item[0], "residual exponent")
    if a < 0:
        raise ValueError("residual exponent must be nonnegative")
    if not isinstance(item[1], (list, tuple)):
        raise ValueError("partition must be a finite list or tuple")
    partition = tuple(sorted(
        (_exact_int(x, "partition part") for x in item[1]), reverse=True))
    if any(x <= 0 for x in partition):
        raise ValueError("partition parts must be positive")
    return a, partition


def _partition_state(partition, exponents):
    counts = {e: 0 for e in exponents}
    for part in partition:
        if part <= 0:
            raise ValueError("partition parts must be positive")
        if part not in counts:
            raise ValueError("partition exponent outside evaluator universe")
        counts[part] += 1
    return tuple(counts[e] for e in exponents)


class MonomialSymmetricPointEvaluator:
    """Evaluate a fixed finite set of monomial symmetric polynomials.

    A state records how many coordinates have received each exponent.  When a
    new coordinate is processed it is either unused or receives exactly one
    exponent.  Descending-cardinality updates ensure the same coordinate is
    never used twice.  This dynamic program therefore counts each distinct
    monomial once, including the required assignments of unequal exponents.
    """

    def __init__(self, partitions):
        canonical = []
        for raw in partitions:
            if not isinstance(raw, (list, tuple)):
                raise ValueError("partition must be a finite list or tuple")
            part = tuple(sorted(
                (_exact_int(x, "partition part") for x in raw), reverse=True))
            if any(x <= 0 for x in part):
                raise ValueError("partition parts must be positive")
            canonical.append(part)
        self.partitions = tuple(dict.fromkeys(canonical))
        self.exponents = tuple(sorted({x for p in self.partitions for x in p}))
        self.targets = {
            p: _partition_state(p, self.exponents) for p in self.partitions
        }

        if not self.exponents:
            states = {()}
        else:
            states = set()
            for target in self.targets.values():
                for candidate in product(*(range(c + 1) for c in target)):
                    states.add(tuple(candidate))
        self.states = tuple(sorted(states, key=lambda s: (sum(s), s)))
        self.index = {state: i for i, state in enumerate(self.states)}
        if tuple(0 for _ in self.exponents) not in self.index:
            raise ArithmeticError("zero state missing from downward closure")

        allowed = set(self.states)
        transitions = []
        for state in self.states:
            row = []
            for j, exponent in enumerate(self.exponents):
                target = list(state)
                target[j] += 1
                target = tuple(target)
                if target in allowed:
                    row.append((self.index[target], exponent))
            transitions.append(tuple(row))
        self.transitions = tuple(transitions)
        self.descending = tuple(
            sorted(range(len(self.states)),
                   key=lambda i: (sum(self.states[i]), self.states[i]),
                   reverse=True)
        )

    def evaluate(self, point):
        """Return ``{partition: m_partition(point)}`` for the fixed list."""
        _require_finite(point, "point")
        values = [0 for _ in self.states]
        zero_state = tuple(0 for _ in self.exponents)
        values[self.index[zero_state]] = 1
        for x in point:
            powers = {e: x ** e for e in self.exponents}
            for source in self.descending:
                value = values[source]
                if value == 0:
                    continue
                for target, exponent in self.transitions[source]:
                    values[target] += value * powers[exponent]
        return {p: values[self.index[state]] for p, state in self.targets.items()}


def evaluate_sieve_polynomial(point, basis, coefficients, evaluator=None):
    """Evaluate ``sum c_(a,lambda) (1-sum(point))^a m_lambda``.

    ``basis`` entries have the JSON-compatible form ``[a, [parts...]]``.
    Coefficients may be integers, Fractions, Decimals, or floats, but must
    already have been parsed by the caller; this function never treats a
    decimal string as exact data implicitly.
    """
    if len(basis) != len(coefficients):
        raise ValueError("basis/coefficient length mismatch")
    _require_finite(coefficients, "coefficients")
    parsed_basis = [_basis_entry(item) for item in basis]
    partitions = [partition for _, partition in parsed_basis]
    if evaluator is None:
        evaluator = MonomialSymmetricPointEvaluator(partitions)
    values = evaluator.evaluate(point)
    residual = 1 - sum(point)
    answer = 0
    for coefficient, (a, partition) in zip(coefficients, parsed_basis):
        answer += coefficient * residual ** a * values[partition]
    return answer


def _poly_add_scaled(target, source, factor):
    if factor == 0:
        return
    if len(target) < len(source):
        target.extend(0 for _ in range(len(source) - len(target)))
    for degree, coefficient in enumerate(source):
        target[degree] += factor * coefficient


def _poly_mul(left, right):
    if not left or not right:
        return []
    answer = [0 for _ in range(len(left) + len(right) - 1)]
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            answer[i + j] += x * y
    return answer


def _affine_power(constant, linear, exponent):
    if exponent < 0:
        raise ValueError("negative polynomial exponent")
    return [comb(exponent, j) * constant ** (exponent - j) * linear ** j
            for j in range(exponent + 1)]


def distinguished_polynomial(common, basis, coefficients, evaluator=None):
    """Return coefficients of ``t -> F(common,t)`` in ascending degree."""
    if len(basis) != len(coefficients):
        raise ValueError("basis/coefficient length mismatch")
    _require_finite(coefficients, "coefficients")
    required = set()
    parsed_basis = [_basis_entry(item) for item in basis]
    for _, partition in parsed_basis:
        required.add(partition)
        for exponent in set(partition):
            rest = list(partition)
            rest.remove(exponent)
            required.add(tuple(rest))
    if evaluator is None:
        evaluator = MonomialSymmetricPointEvaluator(required)
    values = evaluator.evaluate(common)
    common_sum = sum(common)
    result = []
    for coefficient, (residual_exponent, partition) in zip(
            coefficients, parsed_basis):
        orbit_in_t = [values[partition]]
        for exponent in sorted(set(partition)):
            rest = list(partition)
            rest.remove(exponent)
            if len(orbit_in_t) <= exponent:
                orbit_in_t.extend(0 for _ in range(exponent + 1 - len(orbit_in_t)))
            orbit_in_t[exponent] += values[tuple(rest)]
        residual = _affine_power(1 - common_sum, -1, residual_exponent)
        _poly_add_scaled(result, _poly_mul(residual, orbit_in_t), coefficient)
    while result and result[-1] == 0:
        result.pop()
    return result


def integrate_polynomial(poly, lower, upper):
    """Integrate an ascending-coefficient polynomial on a finite interval."""
    _require_finite((lower, upper), "integration interval")
    if upper <= lower:
        return 0
    return sum(coefficient * (upper ** (degree + 1) -
                              lower ** (degree + 1)) / (degree + 1)
               for degree, coefficient in enumerate(poly))


def stratum_statistics(point, delta):
    """Return ``(R,L,Z)`` using the paper's strict ``t_i > delta`` rule."""
    _require_finite(point, "point")
    _require_finite((delta,), "delta")
    if delta < 0:
        raise ValueError("delta must be nonnegative")
    large = [x for x in point if x > delta]
    small = [x for x in point if x <= delta]
    return len(large), sum(large), sum(small)


def support_contains(point, alpha, delta, beta):
    """Membership away from the irrelevant upper total boundary convention."""
    _require_finite(point, "point")
    _require_finite((alpha, delta), "support parameters")
    if alpha <= 0 or delta < 0:
        raise ValueError("invalid support parameters")
    if any(x < 0 for x in point) or sum(point) >= alpha:
        return False
    r, large_sum, _ = stratum_statistics(point, delta)
    return r == 0 or large_sum <= beta(r)


def distinguished_intervals(common, alpha, eta, delta, beta):
    """Feasible small/large intervals for the distinguished coordinate.

    The returned pair is ``(small_interval, large_interval)`` with ``None``
    for an empty branch.  Endpoint choices do not alter the integral, but the
    strict paper convention is retained by the corresponding point-membership
    routine.
    """
    _require_finite(common, "common point")
    _require_finite((alpha, eta, delta), "support parameters")
    if alpha <= 0 or eta < 0 or eta > alpha or delta < 0:
        raise ValueError("invalid support parameters")
    common_sum = sum(common)
    if common_sum > eta:
        return None, None
    r, large_sum, _ = stratum_statistics(common, delta)
    total_upper = alpha - common_sum
    small = None
    common_cap_ok = r == 0 or large_sum <= beta(r)
    if common_cap_ok:
        small_upper = min(delta, total_upper)
        if small_upper > 0:
            small = (0, small_upper)
    large_upper = min(total_upper, beta(r + 1) - large_sum)
    large = (delta, large_upper) if large_upper > delta else None
    return small, large


def marginal_multiplier_vector(common, basis, coefficients, channels,
                               alpha, eta, delta, beta,
                               normalize_powers=False, evaluator=None):
    """Analytically evaluate one-coordinate marginals for `(R,a,b)` channels.

    The channel multiplier is ``1_R L^a Z^b``.  If ``normalize_powers`` is
    true it is divided by ``alpha^(a+b)``.  This is floating-point discovery
    infrastructure even when called with exact scalar types; a theorem checker
    must reconstruct the selected vector through the integration recurrence.
    """
    polynomial = distinguished_polynomial(
        common, basis, coefficients, evaluator=evaluator)
    small_interval, large_interval = distinguished_intervals(
        common, alpha, eta, delta, beta)
    r, large_sum, small_sum = stratum_statistics(common, delta)
    answer = []
    for target_r, a, b in channels:
        if min(a, b) < 0:
            raise ValueError("multiplier exponents must be nonnegative")
        value = 0
        if target_r == r and small_interval is not None:
            multiplier = _poly_mul(
                [large_sum ** a], _affine_power(small_sum, 1, b))
            value += integrate_polynomial(
                _poly_mul(polynomial, multiplier), *small_interval)
        if target_r == r + 1 and large_interval is not None:
            multiplier = _poly_mul(
                _affine_power(large_sum, 1, a), [small_sum ** b])
            value += integrate_polynomial(
                _poly_mul(polynomial, multiplier), *large_interval)
        if normalize_powers and a + b:
            value /= alpha ** (a + b)
        answer.append(value)
    return answer
