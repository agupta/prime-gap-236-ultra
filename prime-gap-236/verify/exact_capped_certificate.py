#!/usr/bin/env python3
"""Independent exact checker for one-band capped Stadlmann supports.

The certificate file supplies only basis labels and rational coefficients.  This
module deliberately reconstructs the polynomial, I, and J from scratch.  It
does not read matrix entries, cached moments, eigenvalues, or claimed signs.

Basis contract
--------------
``[b, lambda]`` denotes

    (1 - t_1 - ... - t_k)^b * m_lambda(t_1, ..., t_k),

where ``m_lambda`` is the *unnormalized* monomial symmetric polynomial: the sum
of every distinct monomial whose positive exponent multiset is ``lambda``.

Only Python's standard library is used.  All arithmetic affecting the result
is ``fractions.Fraction`` arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product
from pathlib import Path
from typing import Iterable, Mapping, Sequence


Partition = tuple[int, ...]
SymPoly = dict[Partition, Fraction]
BasisTerms = dict[tuple[int, Partition], Fraction]
PolynomialTag = tuple[object, ...]
Point = tuple[Fraction, Fraction]
RadialKey = tuple[int, int, int]
RadialPoly = dict[RadialKey, Fraction]

_RATIONAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


class CertificateError(ValueError):
    """Raised when untrusted certificate data fails closed validation."""


@dataclass(frozen=True)
class Parameters:
    name: str
    k: int
    degree: int
    alpha: Fraction
    eta: Fraction
    delta: Fraction
    beta1: Fraction
    beta2: Fraction
    beta3plus: Fraction

    def beta(self, number_large: int) -> Fraction:
        if number_large <= 0:
            raise ValueError("B_0 is not part of the support definition")
        if number_large == 1:
            return self.beta1
        if number_large == 2:
            return self.beta2
        return self.beta3plus


TARGET_C10_D12 = Parameters(
    name="target-c10-d12",
    k=48,
    degree=12,
    alpha=Fraction(79247, 300000),
    eta=Fraction(76247, 300000),
    delta=Fraction(1, 100),
    beta1=Fraction(3, 20),
    beta2=Fraction(3, 20),
    beta3plus=Fraction(97, 625),
)

C10_D4_REGRESSION = Parameters(
    name="regression-c10-d4",
    k=48,
    degree=4,
    alpha=Fraction(79247, 300000),
    eta=Fraction(76247, 300000),
    delta=Fraction(1, 100),
    beta1=Fraction(3, 20),
    beta2=Fraction(3, 20),
    beta3plus=Fraction(97, 625),
)

# Historical C20 D4 artifacts use alpha-eta=1/100 but delta=1/50.  They are
# useful only for auditing a fully general geometry engine and deliberately
# are not exposed as a target-specialized CLI preset.
C20_D4_GENERAL_HISTORY = Parameters(
    name="historical-general-c20-d4",
    k=48,
    degree=4,
    alpha=Fraction(163, 625),
    eta=Fraction(627, 2500),
    delta=Fraction(1, 50),
    beta1=Fraction(3, 20),
    beta2=Fraction(3, 20),
    beta3plus=Fraction(17, 100),
)

PRESETS = {p.name: p for p in (TARGET_C10_D12, C10_D4_REGRESSION)}

# SHA-256 of canonical compact JSON containing exactly the ordered ``basis``
# and ordered ``rational_vector`` arrays from the raw discovery source.  This
# pins provenance/alignment only; no other source field is mathematical input.
TARGET_ORDERED_PAYLOAD_SHA256 = "8ea54de0e3bb4d9f978fee80a6788c81d542a7d6839ed8c69e22a5374845fe4e"
TARGET_A = Fraction(77747, 300000)
TARGET_EPSILON = Fraction(1, 200)


def validate_parameters(params: Parameters) -> None:
    if params.k < 1 or params.degree < 0:
        raise ValueError("invalid dimension or degree")
    if not (Fraction(0) < params.delta and params.eta < params.alpha < Fraction(1, 2)):
        raise ValueError("support parameters violate the one-band simplex bounds")
    if params.alpha - params.eta != params.delta:
        raise ValueError("ordered target geometry requires alpha - eta = delta")
    beta_values = (params.beta1, params.beta2, params.beta3plus)
    if any(beta <= params.delta for beta in beta_values):
        raise ValueError("every positive-index B cap must exceed delta")
    if not (
        params.beta1 <= params.beta2 <= params.beta1 + params.delta
        and params.beta2 <= params.beta3plus <= params.beta2 + params.delta
    ):
        raise ValueError("B caps violate B_m <= B_(m+1) <= B_m + delta")
    if params.name in ("target-c10-d12", "regression-c10-d4"):
        expected_degree = 12 if params.name == "target-c10-d12" else 4
        literal_target = (
            params.k == 48,
            params.degree == expected_degree,
            params.delta == Fraction(1, 100),
            params.alpha == TARGET_A + TARGET_EPSILON,
            params.eta == TARGET_A - TARGET_EPSILON,
            params.beta1 == Fraction(3, 20),
            params.beta2 == Fraction(3, 20),
            params.beta3plus == Fraction(97, 625),
        )
        if not all(literal_target):
            raise ValueError("C10 preset differs from the audited literal parameters")


def _reject_duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CertificateError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise CertificateError(f"non-finite JSON number is forbidden: {token}")


def parse_fraction(value: object, where: str) -> Fraction:
    if not isinstance(value, str) or len(value) > 20_000:
        raise CertificateError(f"{where} must be a bounded rational string")
    if _RATIONAL_RE.fullmatch(value) is None:
        raise CertificateError(f"malformed rational at {where}: {value!r}")
    try:
        answer = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise CertificateError(f"invalid rational at {where}: {exc}") from exc
    if str(answer) != value:
        raise CertificateError(f"non-canonical rational at {where}: {value!r}")
    return answer


def ordered_payload_sha256(raw: Mapping[str, object]) -> str:
    try:
        payload_object = {
            "basis": raw["basis"],
            "rational_vector": raw["rational_vector"],
        }
    except KeyError as exc:
        raise CertificateError(f"missing provenance payload field: {exc.args[0]}") from exc
    try:
        payload = json.dumps(
            payload_object,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, UnicodeEncodeError) as exc:
        raise CertificateError(f"cannot canonicalize ordered provenance payload: {exc}") from exc
    return hashlib.sha256(payload).hexdigest()


def _integer_partitions(total: int, maximum: int | None = None) -> Iterable[Partition]:
    if total == 0:
        yield ()
        return
    if maximum is None or maximum > total:
        maximum = total
    for first in range(maximum, 0, -1):
        for tail in _integer_partitions(total - first, first):
            yield (first,) + tail


def expected_labels(degree: int, k: int) -> set[tuple[int, Partition]]:
    labels: set[tuple[int, Partition]] = set()
    for b in range(degree + 1):
        for total in range(degree - b + 1):
            for part in _integer_partitions(total):
                if len(part) <= k and all(x >= 2 for x in part):
                    labels.add((b, part))
    return labels


def load_certificate(path: Path, params: Parameters) -> tuple[list[tuple[int, Partition]], list[Fraction]]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CertificateError(f"cannot read certificate: {exc}") from exc
    if len(raw_text) > 20_000_000:
        raise CertificateError("certificate exceeds the 20 MB input limit")
    try:
        raw = json.loads(
            raw_text,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CertificateError(f"invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise CertificateError("top-level JSON value must be an object")

    required = {"k", "degree", "basis_dimension", "basis", "rational_vector"}
    missing = required.difference(raw)
    if missing:
        raise CertificateError(f"missing required fields: {sorted(missing)}")
    if params == TARGET_C10_D12:
        payload_hash = ordered_payload_sha256(raw)
        if payload_hash != TARGET_ORDERED_PAYLOAD_SHA256:
            raise CertificateError(
                "ordered target label/vector payload does not match pinned provenance "
                f"({payload_hash})"
            )
    for name, expected in (("k", params.k), ("degree", params.degree)):
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, int) or value != expected:
            raise CertificateError(f"{name} must equal the preset value {expected}")

    basis_raw = raw["basis"]
    vector_raw = raw["rational_vector"]
    dimension = raw["basis_dimension"]
    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
        raise CertificateError("basis_dimension must be a positive integer")
    if not isinstance(basis_raw, list) or not isinstance(vector_raw, list):
        raise CertificateError("basis and rational_vector must be arrays")
    if len(basis_raw) != dimension or len(vector_raw) != dimension:
        raise CertificateError("basis/vector lengths disagree with basis_dimension")

    labels: list[tuple[int, Partition]] = []
    for index, label in enumerate(basis_raw):
        if not isinstance(label, list) or len(label) != 2:
            raise CertificateError(f"basis[{index}] must be [b, partition]")
        b, part_raw = label
        if isinstance(b, bool) or not isinstance(b, int) or b < 0:
            raise CertificateError(f"basis[{index}][0] must be a nonnegative integer")
        if not isinstance(part_raw, list):
            raise CertificateError(f"basis[{index}][1] must be an array")
        if any(isinstance(x, bool) or not isinstance(x, int) for x in part_raw):
            raise CertificateError(f"basis[{index}] partition entries must be integers")
        part = tuple(part_raw)
        if any(x < 2 for x in part):
            raise CertificateError(f"basis[{index}] violates the no-ones label contract")
        if any(part[j] < part[j + 1] for j in range(len(part) - 1)):
            raise CertificateError(f"basis[{index}] partition is not nonincreasing")
        if len(part) > params.k or b + sum(part) > params.degree:
            raise CertificateError(f"basis[{index}] exceeds the preset degree/dimension")
        labels.append((b, part))

    label_set = set(labels)
    expected = expected_labels(params.degree, params.k)
    if len(label_set) != len(labels):
        raise CertificateError("basis contains duplicate labels")
    if label_set != expected:
        absent = sorted(expected - label_set)[:5]
        surplus = sorted(label_set - expected)[:5]
        raise CertificateError(f"basis is incomplete/noncanonical; absent={absent}, surplus={surplus}")

    coefficients = [parse_fraction(value, f"rational_vector[{i}]") for i, value in enumerate(vector_raw)]
    if not any(coefficients):
        raise CertificateError("the rational vector is identically zero")
    return labels, coefficients


def orbit_size(number_variables: int, part: Partition) -> int:
    if len(part) > number_variables:
        return 0
    answer = math.factorial(number_variables) // math.factorial(number_variables - len(part))
    for multiplicity in Counter(part).values():
        answer //= math.factorial(multiplicity)
    return answer


def _falling(n: int, r: int) -> int:
    if r < 0 or r > n:
        return 0
    return math.factorial(n) // math.factorial(n - r)


def monomial_product(left: Partition, right: Partition, number_variables: int) -> dict[Partition, int]:
    """Multiply two unnormalized monomial-symmetric basis elements.

    This is fresh orbit algebra: fix one representative of ``left``, enumerate
    how the exponent multiset of ``right`` meets its occupied coordinates, then
    recover the coefficient per output orbit by orbit-stabilizer counting.
    """
    if right < left:
        left, right = right, left
    return _monomial_product_canonical(left, right, number_variables)


@lru_cache(maxsize=16_384)
def _monomial_product_canonical(
    left: Partition,
    right: Partition,
    number_variables: int,
) -> dict[Partition, int]:
    if len(left) > number_variables or len(right) > number_variables:
        return {}
    occupied = len(left)
    groups = sorted(Counter(right).items(), reverse=True)
    fixed_counts: dict[Partition, int] = defaultdict(int)

    def visit(group_index: int, available: tuple[int, ...], additions: list[int], new_counts: list[tuple[int, int]]) -> None:
        if group_index == len(groups):
            number_new = sum(count for _, count in new_counts)
            if number_new > number_variables - occupied:
                return
            ways_new = _falling(number_variables - occupied, number_new)
            for _, count in new_counts:
                ways_new //= math.factorial(count)
            values = [left[i] + additions[i] for i in range(occupied)]
            for exponent, count in new_counts:
                values.extend([exponent] * count)
            output = tuple(sorted((x for x in values if x), reverse=True))
            fixed_counts[output] += ways_new
            return

        exponent, count = groups[group_index]
        maximum_overlap = min(count, len(available))
        for overlap in range(maximum_overlap + 1):
            for selected in combinations(available, overlap):
                selected_set = set(selected)
                for coordinate in selected:
                    additions[coordinate] = exponent
                visit(
                    group_index + 1,
                    tuple(i for i in available if i not in selected_set),
                    additions,
                    new_counts + [(exponent, count - overlap)],
                )
                for coordinate in selected:
                    additions[coordinate] = 0

    visit(0, tuple(range(occupied)), [0] * occupied, [])
    left_orbit = orbit_size(number_variables, left)
    result: dict[Partition, int] = {}
    for output, fixed_count in fixed_counts.items():
        numerator = left_orbit * fixed_count
        denominator = orbit_size(number_variables, output)
        quotient, remainder = divmod(numerator, denominator)
        if remainder:
            raise ArithmeticError("orbit-stabilizer division was not exact")
        if quotient:
            result[output] = quotient
    return result


def poly_add_term(poly: SymPoly, part: Partition, coefficient: Fraction) -> None:
    if not coefficient:
        return
    value = poly.get(part, Fraction(0)) + coefficient
    if value:
        poly[part] = value
    else:
        poly.pop(part, None)


def poly_multiply(left: Mapping[Partition, Fraction], right: Mapping[Partition, Fraction], number_variables: int) -> SymPoly:
    answer: SymPoly = {}
    for left_part, left_coefficient in left.items():
        for right_part, right_coefficient in right.items():
            for output, multiplicity in monomial_product(left_part, right_part, number_variables).items():
                poly_add_term(answer, output, left_coefficient * right_coefficient * multiplicity)
    return answer


def build_polynomial(labels: Sequence[tuple[int, Partition]], coefficients: Sequence[Fraction], k: int) -> SymPoly:
    one_minus_sum_powers: list[SymPoly] = [{(): Fraction(1)}]
    generator: SymPoly = {(): Fraction(1), (1,): Fraction(-1)}
    maximum_b = max(b for b, _ in labels)
    for _ in range(maximum_b):
        one_minus_sum_powers.append(poly_multiply(one_minus_sum_powers[-1], generator, k))

    answer: SymPoly = {}
    for (b, part), coefficient in zip(labels, coefficients, strict=True):
        term = poly_multiply(one_minus_sum_powers[b], {part: Fraction(1)}, k)
        for output, value in term.items():
            poly_add_term(answer, output, coefficient * value)
    return answer


def build_basis_terms(
    labels: Sequence[tuple[int, Partition]],
    coefficients: Sequence[Fraction],
) -> BasisTerms:
    """Pair checked residual-power labels with coefficients without expansion."""
    if len(labels) != len(coefficients):
        raise ValueError("label/coefficient lengths differ")
    answer: BasisTerms = {}
    for label, coefficient in zip(labels, coefficients, strict=True):
        if label in answer:
            raise ValueError("duplicate tagged basis label")
        if coefficient:
            answer[label] = coefficient
    if not answer:
        raise ValueError("tagged basis polynomial is identically zero")
    return answer


def clip_polygon(polygon: Sequence[Point], a: Fraction, b: Fraction, c: Fraction) -> list[Point]:
    """Clip a convex polygon by ``a*x + b*y <= c`` exactly."""
    if not polygon:
        return []

    def slack(point: Point) -> Fraction:
        return c - a * point[0] - b * point[1]

    answer: list[Point] = []
    previous = polygon[-1]
    previous_slack = slack(previous)
    for current in polygon:
        current_slack = slack(current)
        previous_inside = previous_slack >= 0
        current_inside = current_slack >= 0
        if previous_inside != current_inside:
            ratio = previous_slack / (previous_slack - current_slack)
            intersection = (
                previous[0] + ratio * (current[0] - previous[0]),
                previous[1] + ratio * (current[1] - previous[1]),
            )
            answer.append(intersection)
        if current_inside:
            answer.append(current)
        previous = current
        previous_slack = current_slack

    cleaned: list[Point] = []
    for point in answer:
        if not cleaned or point != cleaned[-1]:
            cleaned.append(point)
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return cleaned


@lru_cache(maxsize=8_192)
def triangle_monomial(origin: Point, first: Point, second: Point, x_power: int, y_power: int) -> Fraction:
    """Integrate x^a y^b over a triangle, by an affine simplex map."""
    px, py = first[0] - origin[0], first[1] - origin[1]
    qx, qy = second[0] - origin[0], second[1] - origin[1]
    determinant = abs(px * qy - py * qx)
    if not determinant:
        return Fraction(0)

    def sparse_linear_power(constant: Fraction, u_term: Fraction, v_term: Fraction, power: int) -> dict[tuple[int, int], Fraction]:
        terms: dict[tuple[int, int], Fraction] = {}
        factorial_power = math.factorial(power)
        for u_exponent in range(power + 1):
            for v_exponent in range(power - u_exponent + 1):
                constant_exponent = power - u_exponent - v_exponent
                if (not constant and constant_exponent) or (not u_term and u_exponent) or (not v_term and v_exponent):
                    continue
                multinomial = factorial_power // (
                    math.factorial(constant_exponent)
                    * math.factorial(u_exponent)
                    * math.factorial(v_exponent)
                )
                terms[(u_exponent, v_exponent)] = (
                    Fraction(multinomial)
                    * constant**constant_exponent
                    * u_term**u_exponent
                    * v_term**v_exponent
                )
        return terms

    # Sparse expansion is important here: almost every support triangle is
    # axis-aligned at the origin, so a nominal O(a^2 b^2) expansion has only
    # one or two genuinely nonzero terms.
    x_terms = sparse_linear_power(origin[0], px, qx, x_power)
    y_terms = sparse_linear_power(origin[1], py, qy, y_power)
    total = Fraction(0)
    for (ux, vx), coefficient_x in x_terms.items():
        for (uy, vy), coefficient_y in y_terms.items():
            u_power = ux + uy
            v_power = vx + vy
            total += coefficient_x * coefficient_y * math.factorial(u_power) * math.factorial(v_power) / math.factorial(u_power + v_power + 2)
    return determinant * total


def polygon_monomial(polygon: Sequence[Point], x_power: int, y_power: int) -> Fraction:
    if len(polygon) < 3:
        return Fraction(0)
    anchor = polygon[0]
    return sum(
        (triangle_monomial(anchor, polygon[i], polygon[i + 1], x_power, y_power) for i in range(1, len(polygon) - 1)),
        Fraction(0),
    )


def _sparse_linear_powers(
    constant: Fraction,
    u_term: Fraction,
    v_term: Fraction,
    powers: Iterable[int],
) -> dict[int, dict[tuple[int, int], Fraction]]:
    """Expand requested powers of one affine form, once per batch.

    This deliberately does not call ``triangle_monomial``.  The streaming
    engine batches all moments of one triangle so the affine expansions for a
    repeated x- or y-degree are shared within that triangle only.
    """
    answer: dict[int, dict[tuple[int, int], Fraction]] = {}
    for power in sorted(set(powers)):
        terms: dict[tuple[int, int], Fraction] = {}
        factorial_power = math.factorial(power)
        for u_exponent in range(power + 1):
            for v_exponent in range(power - u_exponent + 1):
                constant_exponent = power - u_exponent - v_exponent
                if (
                    (not constant and constant_exponent)
                    or (not u_term and u_exponent)
                    or (not v_term and v_exponent)
                ):
                    continue
                multinomial = factorial_power // (
                    math.factorial(constant_exponent)
                    * math.factorial(u_exponent)
                    * math.factorial(v_exponent)
                )
                terms[(u_exponent, v_exponent)] = (
                    Fraction(multinomial)
                    * constant**constant_exponent
                    * u_term**u_exponent
                    * v_term**v_exponent
                )
        answer[power] = terms
    return answer


def _triangle_monomial_batch(
    origin: Point,
    first: Point,
    second: Point,
    powers: Iterable[tuple[int, int]],
) -> dict[tuple[int, int], Fraction]:
    """Return a requested set of exact monomial moments on one triangle."""
    requested = tuple(sorted(set(powers)))
    if not requested:
        return {}
    px, py = first[0] - origin[0], first[1] - origin[1]
    qx, qy = second[0] - origin[0], second[1] - origin[1]
    determinant = abs(px * qy - py * qx)
    if not determinant:
        return {power: Fraction(0) for power in requested}

    x_terms = _sparse_linear_powers(origin[0], px, qx, (a for a, _ in requested))
    y_terms = _sparse_linear_powers(origin[1], py, qy, (b for _, b in requested))
    answer: dict[tuple[int, int], Fraction] = {}
    for x_power, y_power in requested:
        total = Fraction(0)
        for (ux, vx), coefficient_x in x_terms[x_power].items():
            for (uy, vy), coefficient_y in y_terms[y_power].items():
                u_power = ux + uy
                v_power = vx + vy
                total += (
                    coefficient_x
                    * coefficient_y
                    * math.factorial(u_power)
                    * math.factorial(v_power)
                    / math.factorial(u_power + v_power + 2)
                )
        answer[(x_power, y_power)] = determinant * total
    return answer


def _polygon_monomial_batch(
    polygon: Sequence[Point],
    powers: Iterable[tuple[int, int]],
) -> dict[tuple[int, int], Fraction]:
    """Triangulate once and batch every requested exact polygon moment."""
    requested = tuple(sorted(set(powers)))
    answer = {power: Fraction(0) for power in requested}
    if len(polygon) < 3 or not requested:
        return answer
    anchor = polygon[0]
    for index in range(1, len(polygon) - 1):
        triangle = _triangle_monomial_batch(
            anchor,
            polygon[index],
            polygon[index + 1],
            requested,
        )
        for power, value in triangle.items():
            answer[power] += value
    return answer


def affine_power_polygon(
    polygon: Sequence[Point],
    x_power: int,
    y_power: int,
    affine_power: int,
    q0: Fraction,
    qx: Fraction,
    qy: Fraction,
) -> Fraction:
    answer = Fraction(0)
    for ix in range(affine_power + 1):
        for iy in range(affine_power - ix + 1):
            i0 = affine_power - ix - iy
            multinomial = math.factorial(affine_power) // (
                math.factorial(i0) * math.factorial(ix) * math.factorial(iy)
            )
            coefficient = Fraction(multinomial) * q0**i0 * qx**ix * qy**iy
            answer += coefficient * polygon_monomial(polygon, x_power + ix, y_power + iy)
    return answer


def affine_power_interval(
    lower: Fraction,
    upper: Fraction,
    y_power: int,
    affine_power: int,
    q0: Fraction,
    qy: Fraction,
) -> Fraction:
    if upper <= lower:
        return Fraction(0)
    answer = Fraction(0)
    for iy in range(affine_power + 1):
        coefficient = Fraction(math.comb(affine_power, iy)) * q0 ** (affine_power - iy) * qy**iy
        exponent = y_power + iy + 1
        answer += coefficient * (upper**exponent - lower**exponent) / exponent
    return answer


def _large_radial(exponents: Sequence[int], delta: Fraction) -> dict[int, Fraction]:
    return _large_radial_cached(tuple(exponents), delta)


@lru_cache(maxsize=8_192)
def _large_radial_cached(exponents: tuple[int, ...], delta: Fraction) -> dict[int, Fraction]:
    r = len(exponents)
    if r == 0:
        return {0: Fraction(1)}
    # Convolve by total shifted degree.  This is the same explicit binomial
    # expansion as a Cartesian product over every exponent, but repeated
    # exponents do not create an exponential list of tuples.
    degree_terms: dict[int, Fraction] = {0: Fraction(1)}
    for original in (x for x in exponents if x):
        next_terms: dict[int, Fraction] = defaultdict(Fraction)
        for old_degree, old_coefficient in degree_terms.items():
            for shifted_power in range(original + 1):
                coefficient = math.comb(original, shifted_power)
                coefficient *= delta ** (original - shifted_power)
                coefficient *= math.factorial(shifted_power)
                next_terms[old_degree + shifted_power] += old_coefficient * coefficient
        degree_terms = dict(next_terms)
    return {
        total_degree + r - 1: coefficient / math.factorial(total_degree + r - 1)
        for total_degree, coefficient in degree_terms.items()
    }


def _small_radial(exponents: Sequence[int], delta: Fraction) -> dict[tuple[int, int], Fraction]:
    return _small_radial_cached(tuple(exponents), delta)


@lru_cache(maxsize=8_192)
def _small_radial_cached(exponents: tuple[int, ...], delta: Fraction) -> dict[tuple[int, int], Fraction]:
    """Return (number shifted caps, radial power) -> coefficient."""
    s = len(exponents)
    if s == 0:
        return {(0, 0): Fraction(1)}
    positive = [x for x in exponents if x]
    zero_count = s - len(positive)
    # Per positive coordinate there is one unshifted inclusion-exclusion term,
    # plus the shifted-and-binomially-expanded terms.  Convolution retains only
    # (number of shifted caps, total radial degree), which is all the aggregate
    # polygon needs.
    positive_terms: dict[tuple[int, int], Fraction] = {(0, 0): Fraction(1)}
    for original in positive:
        choices: list[tuple[int, int, Fraction]] = [
            (0, original, Fraction(math.factorial(original)))
        ]
        for new_power in range(original + 1):
            coefficient = -math.comb(original, new_power)
            coefficient *= delta ** (original - new_power)
            coefficient *= math.factorial(new_power)
            choices.append((1, new_power, Fraction(coefficient)))
        next_terms: dict[tuple[int, int], Fraction] = defaultdict(Fraction)
        for (old_shift, old_degree), old_coefficient in positive_terms.items():
            for add_shift, add_degree, add_coefficient in choices:
                next_terms[(old_shift + add_shift, old_degree + add_degree)] += old_coefficient * add_coefficient
        positive_terms = dict(next_terms)

    answer: dict[tuple[int, int], Fraction] = defaultdict(Fraction)
    for (positive_shift, total_degree), coefficient in positive_terms.items():
        radial_power = total_degree + s - 1
        coefficient /= math.factorial(radial_power)
        for shifted_zeros in range(zero_count + 1):
            number_shifted = positive_shift + shifted_zeros
            signed = coefficient * ((-1) ** shifted_zeros) * math.comb(zero_count, shifted_zeros)
            answer[(number_shifted, radial_power)] += signed
    return {key: value for key, value in answer.items() if value}


@dataclass(frozen=True)
class AggregateDomain:
    total_bound: Fraction
    x_bound: Fraction | None = None
    y_lower: Fraction | None = None
    y_upper: Fraction | None = None
    total_lower: Fraction | None = None


@lru_cache(maxsize=8_192)
def _aggregate_integral(
    x_power: int,
    y_power: int,
    r: int,
    s: int,
    number_shifted_small: int,
    delta: Fraction,
    domain: AggregateDomain,
    affine_power: int = 0,
    q0: Fraction = Fraction(0),
    qx: Fraction = Fraction(0),
    qy: Fraction = Fraction(0),
) -> Fraction:
    shift = number_shifted_small * delta
    total_bound = domain.total_bound - shift
    if total_bound <= 0:
        return Fraction(0)
    q0_shifted = q0 + qy * shift
    y_lower = None if domain.y_lower is None else domain.y_lower - shift
    y_upper = None if domain.y_upper is None else domain.y_upper - shift
    total_lower = None if domain.total_lower is None else domain.total_lower - shift

    if r == 0:
        if domain.x_bound is not None and domain.x_bound < 0:
            return Fraction(0)
        lower_candidates = [Fraction(0)]
        if y_lower is not None:
            lower_candidates.append(y_lower)
        if total_lower is not None:
            lower_candidates.append(total_lower)
        lower = max(lower_candidates)
        upper = min(total_bound, y_upper if y_upper is not None else total_bound)
        return affine_power_interval(lower, upper, y_power, affine_power, q0_shifted, qy)
    if s == 0:
        upper = total_bound
        if domain.x_bound is not None:
            upper = min(upper, domain.x_bound)
        if upper <= 0:
            return Fraction(0)
        # Ordered branch convention: a zero-dimensional Y aggregate assigns
        # equality to the y_upper (cap-limited) branch, never both branches.
        if y_lower is not None and y_lower >= 0:
            return Fraction(0)
        if y_upper is not None and y_upper < 0:
            return Fraction(0)
        lower = max(Fraction(0), total_lower if total_lower is not None else Fraction(0))
        return affine_power_interval(lower, upper, x_power, affine_power, q0_shifted, qx)

    polygon: list[Point] = [
        (Fraction(0), Fraction(0)),
        (total_bound, Fraction(0)),
        (Fraction(0), total_bound),
    ]
    if domain.x_bound is not None:
        if domain.x_bound <= 0:
            return Fraction(0)
        polygon = clip_polygon(polygon, Fraction(1), Fraction(0), domain.x_bound)
    if y_upper is not None:
        polygon = clip_polygon(polygon, Fraction(0), Fraction(1), y_upper)
    if y_lower is not None:
        polygon = clip_polygon(polygon, Fraction(0), Fraction(-1), -y_lower)
    if total_lower is not None:
        polygon = clip_polygon(
            polygon,
            Fraction(-1),
            Fraction(-1),
            -total_lower,
        )
    return affine_power_polygon(polygon, x_power, y_power, affine_power, q0_shifted, qx, qy)


def fixed_assignment_integral(
    large_exponents: Sequence[int],
    small_exponents: Sequence[int],
    delta: Fraction,
    domain: AggregateDomain,
    affine_power: int = 0,
    q0: Fraction = Fraction(0),
    qx: Fraction = Fraction(0),
    qy: Fraction = Fraction(0),
) -> Fraction:
    r = len(large_exponents)
    s = len(small_exponents)
    large_terms = _large_radial(large_exponents, delta)
    small_terms = _small_radial(small_exponents, delta)
    answer = Fraction(0)
    for x_power, left_coefficient in large_terms.items():
        for (number_shifted, y_power), right_coefficient in small_terms.items():
            integral = _aggregate_integral(
                x_power,
                y_power,
                r,
                s,
                number_shifted,
                delta,
                domain,
                affine_power,
                q0,
                qx,
                qy,
            )
            answer += left_coefficient * right_coefficient * integral
    return answer


def representative_stratum_integral(
    part: Partition,
    number_variables: int,
    number_large: int,
    delta: Fraction,
    domain: AggregateDomain,
    affine_power: int = 0,
    q0: Fraction = Fraction(0),
    qx: Fraction = Fraction(0),
    qy: Fraction = Fraction(0),
) -> Fraction:
    ell = len(part)
    answer = Fraction(0)
    exponent_groups = sorted(Counter(part).items(), reverse=True)
    for selected_counts in product(*(range(count + 1) for _, count in exponent_groups)):
        number_marked_large = sum(selected_counts)
        zero_large = number_large - number_marked_large
        zero_small = number_variables - ell - zero_large
        if zero_large < 0 or zero_small < 0:
            continue
        multiplicity = math.comb(number_variables - ell, zero_large)
        large_exponents: list[int] = []
        small_exponents: list[int] = []
        for (exponent, count), selected_count in zip(exponent_groups, selected_counts, strict=True):
            multiplicity *= math.comb(count, selected_count)
            large_exponents.extend([exponent] * selected_count)
            small_exponents.extend([exponent] * (count - selected_count))
        answer += multiplicity * fixed_assignment_integral(
            large_exponents + [0] * zero_large,
            small_exponents + [0] * zero_small,
            delta,
            domain,
            affine_power,
            q0,
            qx,
            qy,
        )
    return answer


def symmetric_stratum_integral(
    poly: Mapping[Partition, Fraction],
    number_variables: int,
    number_large: int,
    delta: Fraction,
    domain: AggregateDomain,
    affine_power: int = 0,
    q0: Fraction = Fraction(0),
    qx: Fraction = Fraction(0),
    qy: Fraction = Fraction(0),
) -> Fraction:
    answer = Fraction(0)
    for part, coefficient in poly.items():
        representative = representative_stratum_integral(
            part,
            number_variables,
            number_large,
            delta,
            domain,
            affine_power,
            q0,
            qx,
            qy,
        )
        answer += coefficient * orbit_size(number_variables, part) * representative
    return answer


def _partition_face_radial(
    part: Partition,
    number_variables: int,
    number_large: int,
    delta: Fraction,
) -> RadialPoly:
    """Collapse one symmetric orbit on one face to aggregate X/Y powers.

    The returned key is ``(h, a, b)``: ``h`` capped-small coordinates were
    shifted by inclusion-exclusion, and the remaining aggregate density is
    ``X**a * Y**b``.  It already contains the orbit size and the number of
    choices of which coordinates are large.  This is derived directly from
    the same fixed-coordinate Dirichlet factors as the literal engine, but is
    deliberately aggregated before any support polygon is integrated.
    """
    if not 0 <= number_large <= number_variables:
        raise ValueError("face index outside the variable range")
    ell = len(part)
    if ell > number_variables:
        return {}
    exponent_groups = sorted(Counter(part).items(), reverse=True)
    orbit_multiplier = orbit_size(number_variables, part)
    answer: dict[RadialKey, Fraction] = defaultdict(Fraction)
    for selected_counts in product(*(range(count + 1) for _, count in exponent_groups)):
        number_marked_large = sum(selected_counts)
        zero_large = number_large - number_marked_large
        zero_small = number_variables - ell - zero_large
        if zero_large < 0 or zero_small < 0:
            continue

        multiplicity = math.comb(number_variables - ell, zero_large)
        large_exponents: list[int] = []
        small_exponents: list[int] = []
        for (exponent, count), selected_count in zip(
            exponent_groups,
            selected_counts,
            strict=True,
        ):
            multiplicity *= math.comb(count, selected_count)
            large_exponents.extend([exponent] * selected_count)
            small_exponents.extend([exponent] * (count - selected_count))

        large_terms = _large_radial(
            large_exponents + [0] * zero_large,
            delta,
        )
        small_terms = _small_radial(
            small_exponents + [0] * zero_small,
            delta,
        )
        scale = Fraction(orbit_multiplier * multiplicity)
        for x_power, left_coefficient in large_terms.items():
            for (number_shifted, y_power), right_coefficient in small_terms.items():
                answer[(number_shifted, x_power, y_power)] += (
                    scale * left_coefficient * right_coefficient
                )
    return {key: value for key, value in answer.items() if value}


def _radialize_symmetric_polynomial(
    polynomial: Mapping[Partition, Fraction],
    number_variables: int,
    number_large: int,
    delta: Fraction,
    maximum_shift: int | None = None,
) -> RadialPoly:
    """Aggregate a whole symmetric polynomial on one face.

    Every orbit occurs once on the I path, so transforms are consumed
    immediately instead of being retained in a cache.
    """
    answer: dict[RadialKey, Fraction] = defaultdict(Fraction)
    for part, coefficient in sorted(polynomial.items()):
        transform = _partition_face_radial(
            part,
            number_variables,
            number_large,
            delta,
        )
        for key, radial_coefficient in transform.items():
            if maximum_shift is not None and key[0] > maximum_shift:
                continue
            answer[key] += coefficient * radial_coefficient
    return {key: value for key, value in answer.items() if value}


def _affine_power_terms(
    power: int,
    q0: Fraction,
    qx: Fraction,
    qy: Fraction,
) -> dict[tuple[int, int], Fraction]:
    """Expand ``(q0 + qx*X + qy*Y)**power`` as an exact sparse map."""
    if power < 0:
        raise ValueError("negative affine power")
    answer: dict[tuple[int, int], Fraction] = {}
    factorial_power = math.factorial(power)
    for x_power in range(power + 1):
        for y_power in range(power - x_power + 1):
            constant_power = power - x_power - y_power
            if (
                (not q0 and constant_power)
                or (not qx and x_power)
                or (not qy and y_power)
            ):
                continue
            multinomial = factorial_power // (
                math.factorial(constant_power)
                * math.factorial(x_power)
                * math.factorial(y_power)
            )
            coefficient = (
                Fraction(multinomial)
                * q0**constant_power
                * qx**x_power
                * qy**y_power
            )
            if coefficient:
                answer[(x_power, y_power)] = coefficient
    return answer


def _maximum_active_shift(total_bound: Fraction, delta: Fraction) -> int:
    """Largest integer h for which ``total_bound - h*delta`` is positive."""
    if total_bound <= 0 or delta <= 0:
        return -1
    ratio = total_bound / delta
    return (ratio.numerator - 1) // ratio.denominator


def _shifted_polygon(
    total_bound: Fraction,
    x_bound: Fraction | None,
    y_lower: Fraction | None,
    y_upper: Fraction | None,
    total_lower: Fraction | None,
) -> list[Point]:
    polygon: list[Point] = [
        (Fraction(0), Fraction(0)),
        (total_bound, Fraction(0)),
        (Fraction(0), total_bound),
    ]
    if x_bound is not None:
        if x_bound <= 0:
            return []
        polygon = clip_polygon(polygon, Fraction(1), Fraction(0), x_bound)
    if y_upper is not None:
        polygon = clip_polygon(polygon, Fraction(0), Fraction(1), y_upper)
    if y_lower is not None:
        polygon = clip_polygon(polygon, Fraction(0), Fraction(-1), -y_lower)
    if total_lower is not None:
        polygon = clip_polygon(
            polygon,
            Fraction(-1),
            Fraction(-1),
            -total_lower,
        )
    return polygon


def _integrate_radial_polynomial(
    radial: Mapping[RadialKey, Fraction],
    r: int,
    s: int,
    delta: Fraction,
    domain: AggregateDomain,
    affine_power: int = 0,
    q0: Fraction = Fraction(0),
    qx: Fraction = Fraction(0),
    qy: Fraction = Fraction(0),
) -> Fraction:
    """Integrate a face radial polynomial with one geometry pass per IE shift."""
    by_shift: dict[int, dict[tuple[int, int], Fraction]] = defaultdict(
        lambda: defaultdict(Fraction)
    )
    for (number_shifted, x_power, y_power), coefficient in radial.items():
        if number_shifted < 0 or x_power < 0 or y_power < 0:
            raise ArithmeticError("negative radial index")
        by_shift[number_shifted][(x_power, y_power)] += coefficient

    answer = Fraction(0)
    for number_shifted in sorted(by_shift):
        shift = number_shifted * delta
        total_bound = domain.total_bound - shift
        if total_bound <= 0:
            continue
        q0_shifted = q0 + qy * shift
        y_lower = None if domain.y_lower is None else domain.y_lower - shift
        y_upper = None if domain.y_upper is None else domain.y_upper - shift
        total_lower = None if domain.total_lower is None else domain.total_lower - shift
        affine_terms = _affine_power_terms(
            affine_power,
            q0_shifted,
            qx,
            qy,
        )
        if not affine_terms:
            continue

        if r == 0:
            if domain.x_bound is not None and domain.x_bound < 0:
                continue
            lower = max(
                Fraction(0),
                y_lower if y_lower is not None else Fraction(0),
                total_lower if total_lower is not None else Fraction(0),
            )
            upper = min(
                total_bound,
                y_upper if y_upper is not None else total_bound,
            )
            if upper <= lower:
                continue
            univariate: dict[int, Fraction] = defaultdict(Fraction)
            for (x_power, y_power), coefficient in by_shift[number_shifted].items():
                if x_power:
                    raise ArithmeticError("positive X power on a zero-large face")
                for (add_x, add_y), affine_coefficient in affine_terms.items():
                    if add_x:
                        continue
                    univariate[y_power + add_y] += coefficient * affine_coefficient
            for power, coefficient in univariate.items():
                exponent = power + 1
                answer += coefficient * (upper**exponent - lower**exponent) / exponent
            continue

        if s == 0:
            upper = total_bound
            if domain.x_bound is not None:
                upper = min(upper, domain.x_bound)
            if upper <= 0:
                continue
            # The zero-dimensional Y aggregate assigns equality only to the
            # upper/cap branch, exactly as in the literal ordered engine.
            if y_lower is not None and y_lower >= 0:
                continue
            if y_upper is not None and y_upper < 0:
                continue
            lower = max(
                Fraction(0),
                total_lower if total_lower is not None else Fraction(0),
            )
            if upper <= lower:
                continue
            univariate = defaultdict(Fraction)
            for (x_power, y_power), coefficient in by_shift[number_shifted].items():
                if y_power:
                    raise ArithmeticError("positive Y power on a zero-small face")
                for (add_x, add_y), affine_coefficient in affine_terms.items():
                    if add_y:
                        continue
                    univariate[x_power + add_x] += coefficient * affine_coefficient
            for power, coefficient in univariate.items():
                exponent = power + 1
                answer += coefficient * (upper**exponent - lower**exponent) / exponent
            continue

        polygon = _shifted_polygon(
            total_bound,
            domain.x_bound,
            y_lower,
            y_upper,
            total_lower,
        )
        if len(polygon) < 3:
            continue
        moment_coefficients: dict[tuple[int, int], Fraction] = defaultdict(Fraction)
        for (x_power, y_power), coefficient in by_shift[number_shifted].items():
            for (add_x, add_y), affine_coefficient in affine_terms.items():
                moment_coefficients[(x_power + add_x, y_power + add_y)] += (
                    coefficient * affine_coefficient
                )
        moment_coefficients = {
            key: value for key, value in moment_coefficients.items() if value
        }
        moments = _polygon_monomial_batch(polygon, moment_coefficients)
        answer += sum(
            (
                coefficient * moments[power]
                for power, coefficient in moment_coefficients.items()
            ),
            Fraction(0),
        )
    return answer


def _pack_tagged_radials_by_shift(
    tagged_radials: Mapping[tuple[int, int], Mapping[RadialKey, Fraction]],
) -> dict[int, tuple[tuple[int, int, int, int, Fraction], ...]]:
    """Pack immutable tagged radial coefficients once for repeated domains."""
    by_shift: dict[
        int,
        list[tuple[int, int, int, int, Fraction]],
    ] = defaultdict(list)
    for (first_power, second_power), radial in sorted(tagged_radials.items()):
        if first_power < 0 or second_power < 0:
            raise ArithmeticError("negative tagged affine power")
        for (number_shifted, x_power, y_power), coefficient in radial.items():
            if number_shifted < 0 or x_power < 0 or y_power < 0:
                raise ArithmeticError("negative tagged radial index")
            if coefficient:
                by_shift[number_shifted].append(
                    (
                        first_power,
                        second_power,
                        x_power,
                        y_power,
                        coefficient,
                    )
                )
    return {
        number_shifted: tuple(terms)
        for number_shifted, terms in by_shift.items()
    }


def _integrate_tagged_radial_polynomials(
    tagged_radials: Mapping[tuple[int, int], Mapping[RadialKey, Fraction]] | None,
    r: int,
    s: int,
    delta: Fraction,
    domain: AggregateDomain,
    first_affine: tuple[Fraction, Fraction, Fraction],
    second_affine: tuple[Fraction, Fraction, Fraction],
    *,
    packed_by_shift: Mapping[
        int,
        Sequence[tuple[int, int, int, int, Fraction]],
    ] | None = None,
) -> Fraction:
    """Integrate all two-affine tagged terms in one geometry batch per shift.

    A key ``(p,q)`` multiplies its radial polynomial by the ``p``-th power of
    ``first_affine`` and the ``q``-th power of ``second_affine``.  This is the
    production residual-power path; unlike the expanded oracle, residual
    powers never become long partitions of exponent one.
    """
    if packed_by_shift is None:
        if tagged_radials is None:
            raise ValueError("tagged radial input is absent")
        by_shift = _pack_tagged_radials_by_shift(tagged_radials)
    else:
        by_shift = packed_by_shift

    for terms in by_shift.values():
        for _, _, x_power, y_power, _ in terms:
            if r == 0 and x_power:
                raise ArithmeticError("positive radial X power on a zero-large face")
            if s == 0 and y_power:
                raise ArithmeticError("positive radial Y power on a zero-small face")

    answer = Fraction(0)
    first_q0, first_qx, first_qy = first_affine
    second_q0, second_qx, second_qy = second_affine
    for number_shifted in sorted(by_shift):
        shift = number_shifted * delta
        total_bound = domain.total_bound - shift
        if total_bound < 0 or (total_bound == 0 and r + s > 0):
            continue
        y_lower = None if domain.y_lower is None else domain.y_lower - shift
        y_upper = None if domain.y_upper is None else domain.y_upper - shift
        total_lower = None if domain.total_lower is None else domain.total_lower - shift

        first_expansions: dict[int, dict[tuple[int, int], Fraction]] = {}
        second_expansions: dict[int, dict[tuple[int, int], Fraction]] = {}
        moment_coefficients: dict[tuple[int, int], Fraction] = defaultdict(Fraction)
        for first_power, second_power, x_power, y_power, coefficient in by_shift[number_shifted]:
            first_terms = first_expansions.get(first_power)
            if first_terms is None:
                first_terms = _affine_power_terms(
                    first_power,
                    first_q0 + first_qy * shift,
                    first_qx,
                    first_qy,
                )
                first_expansions[first_power] = first_terms
            second_terms = second_expansions.get(second_power)
            if second_terms is None:
                second_terms = _affine_power_terms(
                    second_power,
                    second_q0 + second_qy * shift,
                    second_qx,
                    second_qy,
                )
                second_expansions[second_power] = second_terms
            for (first_x, first_y), first_coefficient in first_terms.items():
                for (second_x, second_y), second_coefficient in second_terms.items():
                    moment_coefficients[
                        (
                            x_power + first_x + second_x,
                            y_power + first_y + second_y,
                        )
                    ] += coefficient * first_coefficient * second_coefficient
        moment_coefficients = {
            key: value for key, value in moment_coefficients.items() if value
        }
        if not moment_coefficients:
            continue

        if r == 0 and s == 0:
            if domain.x_bound is not None and domain.x_bound < 0:
                continue
            if y_lower is not None and y_lower >= 0:
                continue
            if y_upper is not None and y_upper < 0:
                continue
            if total_lower is not None and total_lower >= 0:
                continue
            answer += moment_coefficients.get((0, 0), Fraction(0))
            continue

        if r == 0:
            if domain.x_bound is not None and domain.x_bound < 0:
                continue
            lower = max(
                Fraction(0),
                y_lower if y_lower is not None else Fraction(0),
                total_lower if total_lower is not None else Fraction(0),
            )
            upper = min(
                total_bound,
                y_upper if y_upper is not None else total_bound,
            )
            if upper <= lower:
                continue
            for (x_power, y_power), coefficient in moment_coefficients.items():
                if x_power:
                    continue
                exponent = y_power + 1
                answer += coefficient * (upper**exponent - lower**exponent) / exponent
            continue

        if s == 0:
            upper = total_bound
            if domain.x_bound is not None:
                upper = min(upper, domain.x_bound)
            if upper <= 0:
                continue
            if y_lower is not None and y_lower >= 0:
                continue
            if y_upper is not None and y_upper < 0:
                continue
            lower = max(
                Fraction(0),
                total_lower if total_lower is not None else Fraction(0),
            )
            if upper <= lower:
                continue
            for (x_power, y_power), coefficient in moment_coefficients.items():
                if y_power:
                    continue
                exponent = x_power + 1
                answer += coefficient * (upper**exponent - lower**exponent) / exponent
            continue

        polygon = _shifted_polygon(
            total_bound,
            domain.x_bound,
            y_lower,
            y_upper,
            total_lower,
        )
        if len(polygon) < 3:
            continue
        moments = _polygon_monomial_batch(polygon, moment_coefficients)
        answer += sum(
            (
                coefficient * moments[power]
                for power, coefficient in moment_coefficients.items()
            ),
            Fraction(0),
        )
    return answer


def compute_i_literal(
    polynomial: Mapping[Partition, Fraction],
    params: Parameters,
    *,
    reverse_faces: bool = False,
) -> Fraction:
    """Term-by-term reference engine retained as a small-k oracle."""
    if params.k > 4:
        raise ValueError("the literal I oracle is restricted to k <= 4")
    squared = poly_multiply(polynomial, polynomial, params.k)
    answer = Fraction(0)
    face_order = range(params.k, -1, -1) if reverse_faces else range(params.k + 1)
    for r in face_order:
        if r == 0:
            x_bound = None
        else:
            x_bound = params.beta(r) - r * params.delta
            if x_bound <= 0:
                continue
        total_bound = params.alpha - r * params.delta
        if total_bound <= 0:
            continue
        answer += symmetric_stratum_integral(
            squared,
            params.k,
            r,
            params.delta,
            AggregateDomain(total_bound=total_bound, x_bound=x_bound),
        )
    return answer


def _compute_i_streaming_face(
    squared: Mapping[Partition, Fraction],
    params: Parameters,
    r: int,
) -> Fraction:
    if r == 0:
        x_bound = None
    else:
        x_bound = params.beta(r) - r * params.delta
        if x_bound <= 0:
            return Fraction(0)
    total_bound = params.alpha - r * params.delta
    if total_bound <= 0:
        return Fraction(0)
    radial = _radialize_symmetric_polynomial(
        squared,
        params.k,
        r,
        params.delta,
        maximum_shift=_maximum_active_shift(total_bound, params.delta),
    )
    return _integrate_radial_polynomial(
        radial,
        r,
        params.k - r,
        params.delta,
        AggregateDomain(total_bound=total_bound, x_bound=x_bound),
    )


def _face_block_child(connection, evaluator, payload, params: Parameters, faces: tuple[int, ...]) -> None:
    """Private fork worker: return only freshly computed exact face values."""
    try:
        values = [(r, evaluator(payload, params, r)) for r in faces]
        connection.send(("ok", values))
    except BaseException as exc:  # fail closed across the process boundary
        connection.send(("error", type(exc).__name__, str(exc)))
    finally:
        connection.close()


def _run_two_face_blocks(
    evaluator,
    payload,
    params: Parameters,
    faces: Sequence[int],
) -> Fraction:
    """Evaluate two contiguous r-blocks under fork, then sum canonically.

    Fork is required so the immutable orbit polynomials are inherited
    copy-on-write rather than serialized to, or reconstructed by, workers.
    Only the small list of exact per-face Fractions crosses a pipe.
    """
    ordered_faces = tuple(faces)
    if len(ordered_faces) < 2:
        return sum(
            (evaluator(payload, params, r) for r in ordered_faces),
            Fraction(0),
        )
    if "fork" not in multiprocessing.get_all_start_methods():
        raise ValueError("two-worker exact mode requires the fork start method")
    midpoint = (len(ordered_faces) + 1) // 2
    blocks = (ordered_faces[:midpoint], ordered_faces[midpoint:])
    context = multiprocessing.get_context("fork")
    receivers = []
    processes = []
    try:
        for block in blocks:
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(
                target=_face_block_child,
                args=(sender, evaluator, payload, params, block),
            )
            process.start()
            sender.close()
            receivers.append(receiver)
            processes.append(process)

        values_by_face: dict[int, Fraction] = {}
        errors: list[str] = []
        for receiver in receivers:
            try:
                message = receiver.recv()
            except EOFError:
                errors.append("worker pipe closed without a result")
                continue
            finally:
                receiver.close()
            if not isinstance(message, tuple) or not message:
                errors.append("worker returned a malformed result")
                continue
            if message[0] != "ok":
                if len(message) == 3 and message[0] == "error":
                    errors.append(f"{message[1]}: {message[2]}")
                else:
                    errors.append("worker returned an unknown status")
                continue
            if len(message) != 2 or not isinstance(message[1], list):
                errors.append("worker returned a malformed face list")
                continue
            for item in message[1]:
                if (
                    not isinstance(item, tuple)
                    or len(item) != 2
                    or isinstance(item[0], bool)
                    or not isinstance(item[0], int)
                    or not isinstance(item[1], Fraction)
                    or item[0] in values_by_face
                ):
                    errors.append("worker returned a malformed/duplicate face value")
                    break
                values_by_face[item[0]] = item[1]
        for process in processes:
            process.join()
            if process.exitcode != 0:
                errors.append(f"worker exited with status {process.exitcode}")
        if set(values_by_face) != set(ordered_faces):
            errors.append("worker face coverage is incomplete")
        if errors:
            raise ArithmeticError("two-worker exact evaluation failed: " + "; ".join(errors))
        return sum((values_by_face[r] for r in ordered_faces), Fraction(0))
    finally:
        for receiver in receivers:
            receiver.close()
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join()


def compute_i(
    polynomial: Mapping[Partition, Fraction],
    params: Parameters,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Expanded streaming I oracle, restricted to small dimensions."""
    if params.k > 4:
        raise ValueError("the expanded I oracle is restricted to k <= 4")
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    squared = poly_multiply(polynomial, polynomial, params.k)
    active_faces = [
        r
        for r in range(params.k + 1)
        if params.alpha - r * params.delta > 0
        and (r == 0 or params.beta(r) - r * params.delta > 0)
    ]
    if reverse_faces:
        active_faces.reverse()
    if workers == 2:
        return _run_two_face_blocks(
            _compute_i_streaming_face,
            squared,
            params,
            active_faces,
        )
    return sum(
        (_compute_i_streaming_face(squared, params, r) for r in active_faces),
        Fraction(0),
    )


def _radialize_tagged_targets(
    polynomials: Mapping[PolynomialTag, Mapping[Partition, Fraction]],
    number_variables: int,
    number_large: int,
    delta: Fraction,
    maximum_shift: int,
    precomputed: Mapping[Partition, RadialPoly] | None = None,
) -> dict[PolynomialTag, RadialPoly]:
    """Distribute each face-orbit transform to all tagged target polynomials."""
    targets = [
        (tag, polynomials[tag])
        for tag in sorted(polynomials)
    ]
    all_parts: set[Partition] = set()
    for _, polynomial in targets:
        all_parts.update(polynomial)
    accumulators: dict[PolynomialTag, dict[RadialKey, Fraction]] = {
        tag: defaultdict(Fraction) for tag, _ in targets
    }
    for part in sorted(all_parts):
        transform = None if precomputed is None else precomputed.get(part)
        if transform is None:
            transform = _partition_face_radial(
                part,
                number_variables,
                number_large,
                delta,
            )
        for tag, polynomial in targets:
            coefficient = polynomial.get(part)
            if coefficient is None:
                continue
            destination = accumulators[tag]
            for key, radial_coefficient in transform.items():
                if key[0] <= maximum_shift:
                    destination[key] += coefficient * radial_coefficient
    return {
        tag: {key: value for key, value in radial.items() if value}
        for tag, radial in accumulators.items()
    }


def _tagged_i_square(
    basis_terms: Mapping[tuple[int, Partition], Fraction],
    number_variables: int,
    alpha: Fraction,
) -> dict[tuple[int, int], SymPoly]:
    """Build ``P_nu * (alpha-S)^c`` coefficients for F squared."""
    terms = sorted(basis_terms.items())
    answer: dict[tuple[int, int], SymPoly] = defaultdict(dict)
    for left_index, ((left_residual, left_part), left_coefficient) in enumerate(terms):
        for right_index in range(left_index, len(terms)):
            (right_residual, right_part), right_coefficient = terms[right_index]
            scale = left_coefficient * right_coefficient
            if right_index != left_index:
                scale *= 2
            total_residual = left_residual + right_residual
            product_orbits = monomial_product(
                left_part,
                right_part,
                number_variables,
            )
            for residual_power in range(total_residual + 1):
                residual_coefficient = (
                    Fraction(math.comb(total_residual, residual_power))
                    * (1 - alpha) ** (total_residual - residual_power)
                )
                for output, multiplicity in product_orbits.items():
                    poly_add_term(
                        answer[(0, residual_power)],
                        output,
                        scale * residual_coefficient * multiplicity,
                    )
    return {
        tag: polynomial
        for tag, polynomial in answer.items()
        if polynomial
    }


def _compute_i_tagged_face(
    squared: Mapping[tuple[int, int], Mapping[Partition, Fraction]],
    params: Parameters,
    r: int,
) -> Fraction:
    if r == 0:
        x_bound = None
    else:
        x_bound = params.beta(r) - r * params.delta
        if x_bound <= 0:
            return Fraction(0)
    total_bound = params.alpha - r * params.delta
    if total_bound <= 0:
        return Fraction(0)
    radials = _radialize_tagged_targets(
        squared,
        params.k,
        r,
        params.delta,
        _maximum_active_shift(total_bound, params.delta),
    )
    packed = _pack_tagged_radials_by_shift(radials)
    del radials
    return _integrate_tagged_radial_polynomials(
        None,
        r,
        params.k - r,
        params.delta,
        AggregateDomain(total_bound=total_bound, x_bound=x_bound),
        first_affine=(Fraction(0), Fraction(0), Fraction(0)),
        second_affine=(
            params.alpha - r * params.delta,
            Fraction(-1),
            Fraction(-1),
        ),
        packed_by_shift=packed,
    )


def compute_i_tagged(
    basis_terms: Mapping[tuple[int, Partition], Fraction],
    params: Parameters,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Production I backend retaining residual total-slack powers."""
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    squared = _tagged_i_square(basis_terms, params.k, params.alpha)
    active_faces = [
        r
        for r in range(params.k + 1)
        if params.alpha - r * params.delta > 0
        and (r == 0 or params.beta(r) - r * params.delta > 0)
    ]
    if reverse_faces:
        active_faces.reverse()
    if workers == 2:
        return _run_two_face_blocks(
            _compute_i_tagged_face,
            squared,
            params,
            active_faces,
        )
    return sum(
        (_compute_i_tagged_face(squared, params, r) for r in active_faces),
        Fraction(0),
    )


def distinguish_last_variable(polynomial: Mapping[Partition, Fraction], base_variables: int) -> dict[int, SymPoly]:
    answer: dict[int, SymPoly] = defaultdict(dict)
    for part, coefficient in polynomial.items():
        if len(part) <= base_variables:
            poly_add_term(answer[0], part, coefficient)
        for exponent in sorted(set(part), reverse=True):
            remaining = list(part)
            remaining.remove(exponent)
            if len(remaining) <= base_variables:
                poly_add_term(answer[exponent], tuple(remaining), coefficient)
    return dict(answer)


def marginal_polynomials(polynomial: Mapping[Partition, Fraction], params: Parameters) -> tuple[SymPoly, dict[int, SymPoly]]:
    distinguished = distinguish_last_variable(polynomial, params.k - 1)
    small: SymPoly = {}
    large_by_power: dict[int, SymPoly] = defaultdict(dict)
    for t_power, base_poly in distinguished.items():
        small_factor = params.delta ** (t_power + 1) / (t_power + 1)
        for part, coefficient in base_poly.items():
            poly_add_term(small, part, coefficient * small_factor)
        for q_power in range(1, t_power + 2):
            factor = Fraction(math.comb(t_power + 1, q_power), t_power + 1)
            factor *= params.delta ** (t_power + 1 - q_power)
            for part, coefficient in base_poly.items():
                poly_add_term(large_by_power[q_power], part, coefficient * factor)
    return small, dict(large_by_power)


def _power_weighted_products(
    left: Mapping[int, Mapping[Partition, Fraction]],
    right: Mapping[int, Mapping[Partition, Fraction]],
    number_variables: int,
    scale: Fraction = Fraction(1),
) -> dict[int, SymPoly]:
    answer: dict[int, SymPoly] = defaultdict(dict)
    for left_power, left_poly in left.items():
        for right_power, right_poly in right.items():
            multiplied = poly_multiply(left_poly, right_poly, number_variables)
            for part, coefficient in multiplied.items():
                poly_add_term(answer[left_power + right_power], part, scale * coefficient)
    return dict(answer)


def _tagged_marginal_polynomials(
    basis_terms: Mapping[tuple[int, Partition], Fraction],
    params: Parameters,
) -> tuple[dict[tuple[int, int], SymPoly], dict[tuple[int, int], SymPoly]]:
    """Derive small and large marginals with residual powers unexpanded.

    The tag is ``(fiber_slack_power, residual_(1-U)_power)``.  This is a
    direct finite expansion of the Definition-5 antiderivative, not a
    conversion from the expanded oracle.
    """
    base_variables = params.k - 1
    small: dict[tuple[int, int], SymPoly] = defaultdict(dict)
    large: dict[tuple[int, int], SymPoly] = defaultdict(dict)
    for (residual_power, part), source_coefficient in sorted(basis_terms.items()):
        distinguished: list[tuple[int, Partition]] = []
        if len(part) <= base_variables:
            distinguished.append((0, part))
        for exponent in sorted(set(part), reverse=True):
            remaining = list(part)
            remaining.remove(exponent)
            if len(remaining) <= base_variables:
                distinguished.append((exponent, tuple(remaining)))

        for t_power, remaining_part in distinguished:
            for binomial_power in range(residual_power + 1):
                remaining_residual = residual_power - binomial_power
                endpoint_power = t_power + binomial_power + 1
                common = (
                    source_coefficient
                    * (-1) ** binomial_power
                    * math.comb(residual_power, binomial_power)
                    / endpoint_power
                )
                poly_add_term(
                    small[(0, remaining_residual)],
                    remaining_part,
                    common * params.delta**endpoint_power,
                )
                for fiber_power in range(1, endpoint_power + 1):
                    endpoint_coefficient = (
                        math.comb(endpoint_power, fiber_power)
                        * params.delta ** (endpoint_power - fiber_power)
                    )
                    poly_add_term(
                        large[(fiber_power, remaining_residual)],
                        remaining_part,
                        common * endpoint_coefficient,
                    )
    return (
        {tag: polynomial for tag, polynomial in small.items() if polynomial},
        {tag: polynomial for tag, polynomial in large.items() if polynomial},
    )


def _tagged_power_products(
    left: Mapping[tuple[int, int], Mapping[Partition, Fraction]],
    right: Mapping[tuple[int, int], Mapping[Partition, Fraction]],
    number_variables: int,
) -> dict[tuple[int, int], SymPoly]:
    """Multiply marginal tags and reconstruct every orbit product freshly."""
    answer: dict[tuple[int, int], SymPoly] = defaultdict(dict)
    for (left_fiber, left_residual), left_poly in sorted(left.items()):
        for (right_fiber, right_residual), right_poly in sorted(right.items()):
            multiplied = poly_multiply(left_poly, right_poly, number_variables)
            target = (
                left_fiber + right_fiber,
                left_residual + right_residual,
            )
            for part, coefficient in multiplied.items():
                poly_add_term(answer[target], part, coefficient)
    return {
        tag: polynomial
        for tag, polynomial in answer.items()
        if polynomial
    }


def compute_j_literal(
    polynomial: Mapping[Partition, Fraction],
    params: Parameters,
    *,
    reverse_faces: bool = False,
) -> Fraction:
    """Term-by-term ordered-branch reference retained as a small-k oracle."""
    if params.k > 4:
        raise ValueError("the literal J oracle is restricted to k <= 4")
    if params.alpha - params.eta != params.delta:
        raise ValueError("this ordered-branch J implementation requires alpha - eta = delta")
    base_variables = params.k - 1
    small, large = marginal_polynomials(polynomial, params)
    marginal_families: dict[str, dict[int, SymPoly]] = {
        "small_delta": {0: small},
        # On the target outer domain, the source Stotal branch is confined to
        # total shared mass eta.  Its marginal equals the delta marginal there,
        # but it is retained as a separate ordered, zero-measure branch.
        "small_total": {0: small},
        "cap": large,
        "total": large,
    }
    branch_names = ("small_delta", "small_total", "cap", "total")
    # These three algebraic products are immutable after construction.  The
    # ordered branch loop below still adds every ordered summand separately,
    # while reverse-order pairs reuse the same freshly derived product rather
    # than reconstructing identical orbit algebra four times.
    small_small_product = _power_weighted_products(
        marginal_families["small_delta"],
        marginal_families["small_delta"],
        base_variables,
    )
    small_large_product = _power_weighted_products(
        marginal_families["small_delta"],
        marginal_families["cap"],
        base_variables,
    )
    large_large_product = _power_weighted_products(
        marginal_families["cap"],
        marginal_families["cap"],
        base_variables,
    )
    ordered_products: dict[tuple[str, str], dict[int, SymPoly]] = {}
    for left_name in branch_names:
        for right_name in branch_names:
            if "small_total" in (left_name, right_name) or {left_name, right_name} == {"cap", "total"}:
                continue
            if left_name == right_name == "small_delta":
                ordered_products[(left_name, right_name)] = small_small_product
            elif "small_delta" in (left_name, right_name):
                ordered_products[(left_name, right_name)] = small_large_product
            else:
                ordered_products[(left_name, right_name)] = large_large_product

    answer = Fraction(0)
    face_order = range(base_variables, -1, -1) if reverse_faces else range(base_variables + 1)
    for r in face_order:
        total_bound = params.eta - r * params.delta
        if total_bound <= 0:
            continue

        # Small-fiber domain.  There is no B_0 condition.
        if r == 0:
            small_x_bound = None
        else:
            small_x_bound = params.beta(r) - r * params.delta

        # For a large fiber, q is the minimum of the
        # total-sum slack and the B_{r+1} slack.  Their ordering changes only
        # at the horizontal line V = eta - B_{r+1} + delta.
        large_x_bound = params.beta(r + 1) - (r + 1) * params.delta
        threshold = params.eta - params.beta(r + 1) + params.delta

        branch_data = {
            "small_delta": (small_x_bound, None, None, None),
            "small_total": (small_x_bound, None, None, total_bound),
            "cap": (large_x_bound, None, threshold, None),
            "total": (large_x_bound, threshold, None, None),
        }

        # Enumerate all ordered pairs of the four source branches.  In
        # particular, small_delta/cap and cap/small_delta are separate exact
        # summands; there is no hidden factor-two convention.  The target-only
        # small_total branch and complementary cap/total intersections are
        # sent to the geometry and required to vanish exactly.
        for left_name in branch_names:
            for right_name in branch_names:
                left_x, left_lower, left_upper, left_total_lower = branch_data[left_name]
                right_x, right_lower, right_upper, right_total_lower = branch_data[right_name]
                x_bounds = [bound for bound in (left_x, right_x) if bound is not None]
                x_bound = min(x_bounds) if x_bounds else None
                if x_bound is not None and x_bound <= 0:
                    continue
                lowers = [bound for bound in (left_lower, right_lower) if bound is not None]
                uppers = [bound for bound in (left_upper, right_upper) if bound is not None]
                y_lower = max(lowers) if lowers else None
                y_upper = min(uppers) if uppers else None
                total_lowers = [
                    bound
                    for bound in (left_total_lower, right_total_lower)
                    if bound is not None
                ]
                total_lower = max(total_lowers) if total_lowers else None
                domain = AggregateDomain(
                    total_bound=total_bound,
                    x_bound=x_bound,
                    y_lower=y_lower,
                    y_upper=y_upper,
                    total_lower=total_lower,
                )

                if "small_total" in (left_name, right_name) or {left_name, right_name} == {"cap", "total"}:
                    zero_measure = symmetric_stratum_integral(
                        {(): Fraction(1)},
                        base_variables,
                        r,
                        params.delta,
                        domain,
                    )
                    if zero_measure:
                        raise ArithmeticError("nominally boundary-only ordered J branches overlap in positive measure")
                    continue

                weighted = ordered_products[(left_name, right_name)]
                active_large_name = (
                    left_name if left_name not in ("small_delta", "small_total") else right_name
                )
                for q_power, base_poly in weighted.items():
                    if active_large_name == "cap":
                        q0, qx, qy = large_x_bound, Fraction(-1), Fraction(0)
                    elif active_large_name == "total":
                        q0, qx, qy = total_bound, Fraction(-1), Fraction(-1)
                    else:
                        q0 = qx = qy = Fraction(0)
                    answer += symmetric_stratum_integral(
                        base_poly,
                        base_variables,
                        r,
                        params.delta,
                        domain,
                        affine_power=q_power,
                        q0=q0,
                        qx=qx,
                        qy=qy,
                    )
    return answer


def _radialize_weighted_product_families(
    products: Mapping[str, Mapping[int, Mapping[Partition, Fraction]]],
    number_variables: int,
    number_large: int,
    delta: Fraction,
    precomputed: Mapping[Partition, RadialPoly] | None = None,
    maximum_shift: int | None = None,
) -> dict[tuple[str, int], RadialPoly]:
    """Radialize every (family, q) polynomial with one transform per orbit.

    The input symmetric polynomials remain immutable.  On a fixed face this
    routine visits each distinct partition ``nu`` once, derives its radial
    transform, distributes that transform to every family/q coefficient that
    uses ``nu``, and immediately drops the transform.  Thus there is no
    unbounded transform cache and no serialized producer state.
    """
    targets: list[tuple[str, int, Mapping[Partition, Fraction]]] = []
    all_parts: set[Partition] = set()
    for family in sorted(products):
        for q_power in sorted(products[family]):
            polynomial = products[family][q_power]
            targets.append((family, q_power, polynomial))
            all_parts.update(polynomial)

    accumulators: dict[tuple[str, int], dict[RadialKey, Fraction]] = {
        (family, q_power): defaultdict(Fraction)
        for family, q_power, _ in targets
    }
    for part in sorted(all_parts):
        transform = None if precomputed is None else precomputed.get(part)
        if transform is None:
            transform = _partition_face_radial(
                part,
                number_variables,
                number_large,
                delta,
            )
        for family, q_power, polynomial in targets:
            coefficient = polynomial.get(part)
            if coefficient is None:
                continue
            destination = accumulators[(family, q_power)]
            for key, radial_coefficient in transform.items():
                if maximum_shift is not None and key[0] > maximum_shift:
                    continue
                destination[key] += coefficient * radial_coefficient

    return {
        target: {key: value for key, value in radial.items() if value}
        for target, radial in accumulators.items()
    }


def _compute_j_streaming_face(
    products: Mapping[str, Mapping[int, Mapping[Partition, Fraction]]],
    params: Parameters,
    r: int,
) -> Fraction:
    base_variables = params.k - 1
    total_bound = params.eta - r * params.delta
    if total_bound <= 0:
        return Fraction(0)

    if r == 0:
        small_x_bound = None
    else:
        small_x_bound = params.beta(r) - r * params.delta
    large_x_bound = params.beta(r + 1) - (r + 1) * params.delta
    threshold = params.eta - params.beta(r + 1) + params.delta
    branch_names = ("small_delta", "small_total", "cap", "total")
    branch_data = {
        "small_delta": (small_x_bound, None, None, None),
        "small_total": (small_x_bound, None, None, total_bound),
        "cap": (large_x_bound, None, threshold, None),
        "total": (large_x_bound, threshold, None, None),
    }

    # Jobs retain their ordered branch-pair index.  Radialization is grouped
    # independently for speed, but every ordered summand is integrated and
    # accumulated into its own slot before the slots are summed in order.
    jobs: list[
        tuple[
            int,
            str,
            int,
            AggregateDomain,
            Fraction,
            Fraction,
            Fraction,
        ]
    ] = []
    contributions = [Fraction(0) for _ in range(len(branch_names) ** 2)]
    maximum_shift = _maximum_active_shift(total_bound, params.delta)
    constant_radial = {
        key: value
        for key, value in _partition_face_radial(
            (),
            base_variables,
            r,
            params.delta,
        ).items()
        if key[0] <= maximum_shift
    }

    for left_index, left_name in enumerate(branch_names):
        for right_index, right_name in enumerate(branch_names):
            ordered_index = left_index * len(branch_names) + right_index
            left_x, left_lower, left_upper, left_total_lower = branch_data[left_name]
            right_x, right_lower, right_upper, right_total_lower = branch_data[right_name]
            x_bounds = [bound for bound in (left_x, right_x) if bound is not None]
            x_bound = min(x_bounds) if x_bounds else None
            if x_bound is not None and x_bound <= 0:
                continue
            lowers = [bound for bound in (left_lower, right_lower) if bound is not None]
            uppers = [bound for bound in (left_upper, right_upper) if bound is not None]
            total_lowers = [
                bound
                for bound in (left_total_lower, right_total_lower)
                if bound is not None
            ]
            domain = AggregateDomain(
                total_bound=total_bound,
                x_bound=x_bound,
                y_lower=max(lowers) if lowers else None,
                y_upper=min(uppers) if uppers else None,
                total_lower=max(total_lowers) if total_lowers else None,
            )

            boundary_only = (
                "small_total" in (left_name, right_name)
                or {left_name, right_name} == {"cap", "total"}
            )
            if boundary_only:
                zero_measure = _integrate_radial_polynomial(
                    constant_radial,
                    r,
                    base_variables - r,
                    params.delta,
                    domain,
                )
                if zero_measure:
                    raise ArithmeticError(
                        "nominally boundary-only ordered J branches overlap in positive measure"
                    )
                continue

            if left_name == right_name == "small_delta":
                family = "small_small"
            elif "small_delta" in (left_name, right_name):
                family = "small_large"
            else:
                family = "large_large"

            active_large_name = (
                left_name
                if left_name not in ("small_delta", "small_total")
                else right_name
            )
            if active_large_name == "cap":
                q0, qx, qy = large_x_bound, Fraction(-1), Fraction(0)
            elif active_large_name == "total":
                q0, qx, qy = total_bound, Fraction(-1), Fraction(-1)
            else:
                q0 = qx = qy = Fraction(0)
            for q_power in sorted(products[family]):
                jobs.append(
                    (
                        ordered_index,
                        family,
                        q_power,
                        domain,
                        q0,
                        qx,
                        qy,
                    )
                )

    radials = _radialize_weighted_product_families(
        products,
        base_variables,
        r,
        params.delta,
        precomputed={(): constant_radial},
        maximum_shift=maximum_shift,
    )
    for ordered_index, family, q_power, domain, q0, qx, qy in jobs:
        contributions[ordered_index] += _integrate_radial_polynomial(
            radials[(family, q_power)],
            r,
            base_variables - r,
            params.delta,
            domain,
            affine_power=q_power,
            q0=q0,
            qx=qx,
            qy=qy,
        )
    return sum(contributions, Fraction(0))


def compute_j(
    polynomial: Mapping[Partition, Fraction],
    params: Parameters,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Expanded streaming J oracle, restricted to small dimensions."""
    if params.k > 4:
        raise ValueError("the expanded J oracle is restricted to k <= 4")
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    if params.alpha - params.eta != params.delta:
        raise ValueError("this ordered-branch J implementation requires alpha - eta = delta")
    base_variables = params.k - 1
    small, large = marginal_polynomials(polynomial, params)
    products: dict[str, dict[int, SymPoly]] = {
        "small_small": _power_weighted_products(
            {0: small},
            {0: small},
            base_variables,
        ),
        "small_large": _power_weighted_products(
            {0: small},
            large,
            base_variables,
        ),
        "large_large": _power_weighted_products(
            large,
            large,
            base_variables,
        ),
    }
    active_faces = []
    for r in range(base_variables + 1):
        if params.eta - r * params.delta <= 0:
            continue
        small_active = r == 0 or params.beta(r) - r * params.delta > 0
        large_active = params.beta(r + 1) - (r + 1) * params.delta > 0
        if small_active or large_active:
            active_faces.append(r)
    if reverse_faces:
        active_faces.reverse()
    if workers == 2:
        return _run_two_face_blocks(
            _compute_j_streaming_face,
            products,
            params,
            active_faces,
        )
    return sum(
        (
            _compute_j_streaming_face(products, params, r)
            for r in active_faces
        ),
        Fraction(0),
    )


def _compute_j_tagged_face(
    products: Mapping[str, Mapping[tuple[int, int], Mapping[Partition, Fraction]]],
    params: Parameters,
    r: int,
) -> Fraction:
    base_variables = params.k - 1
    total_bound = params.eta - r * params.delta
    if total_bound <= 0:
        return Fraction(0)

    if r == 0:
        small_x_bound = None
    else:
        small_x_bound = params.beta(r) - r * params.delta
    large_x_bound = params.beta(r + 1) - (r + 1) * params.delta
    threshold = params.eta - params.beta(r + 1) + params.delta
    branch_names = ("small_delta", "small_total", "cap", "total")
    branch_data = {
        "small_delta": (small_x_bound, None, None, None),
        "small_total": (small_x_bound, None, None, total_bound),
        "cap": (large_x_bound, None, threshold, None),
        "total": (large_x_bound, threshold, None, None),
    }

    jobs: list[
        tuple[
            int,
            str,
            AggregateDomain,
            tuple[Fraction, Fraction, Fraction],
        ]
    ] = []
    contributions = [Fraction(0) for _ in range(len(branch_names) ** 2)]
    maximum_shift = _maximum_active_shift(total_bound, params.delta)
    constant_radial = {
        key: value
        for key, value in _partition_face_radial(
            (),
            base_variables,
            r,
            params.delta,
        ).items()
        if key[0] <= maximum_shift
    }

    for left_index, left_name in enumerate(branch_names):
        for right_index, right_name in enumerate(branch_names):
            ordered_index = left_index * len(branch_names) + right_index
            left_x, left_lower, left_upper, left_total_lower = branch_data[left_name]
            right_x, right_lower, right_upper, right_total_lower = branch_data[right_name]
            x_bounds = [bound for bound in (left_x, right_x) if bound is not None]
            x_bound = min(x_bounds) if x_bounds else None
            if x_bound is not None and x_bound <= 0:
                continue
            lowers = [bound for bound in (left_lower, right_lower) if bound is not None]
            uppers = [bound for bound in (left_upper, right_upper) if bound is not None]
            total_lowers = [
                bound
                for bound in (left_total_lower, right_total_lower)
                if bound is not None
            ]
            domain = AggregateDomain(
                total_bound=total_bound,
                x_bound=x_bound,
                y_lower=max(lowers) if lowers else None,
                y_upper=min(uppers) if uppers else None,
                total_lower=max(total_lowers) if total_lowers else None,
            )

            boundary_only = (
                "small_total" in (left_name, right_name)
                or {left_name, right_name} == {"cap", "total"}
            )
            if boundary_only:
                zero_measure = _integrate_radial_polynomial(
                    constant_radial,
                    r,
                    base_variables - r,
                    params.delta,
                    domain,
                )
                if zero_measure:
                    raise ArithmeticError(
                        "nominally boundary-only ordered J branches overlap in positive measure"
                    )
                continue

            if left_name == right_name == "small_delta":
                family = "small_small"
            elif "small_delta" in (left_name, right_name):
                family = "small_large"
            else:
                family = "large_large"

            active_large_name = (
                left_name
                if left_name not in ("small_delta", "small_total")
                else right_name
            )
            if active_large_name == "cap":
                fiber_affine = (
                    large_x_bound,
                    Fraction(-1),
                    Fraction(0),
                )
            elif active_large_name == "total":
                fiber_affine = (
                    total_bound,
                    Fraction(-1),
                    Fraction(-1),
                )
            else:
                fiber_affine = (
                    Fraction(0),
                    Fraction(0),
                    Fraction(0),
                )
            jobs.append((ordered_index, family, domain, fiber_affine))

    active_families = {family for _, family, _, _ in jobs}
    flat_polynomials: dict[PolynomialTag, Mapping[Partition, Fraction]] = {}
    for family in sorted(active_families):
        for (fiber_power, residual_power), polynomial in sorted(products[family].items()):
            flat_polynomials[(family, fiber_power, residual_power)] = polynomial
    flat_radials = _radialize_tagged_targets(
        flat_polynomials,
        base_variables,
        r,
        params.delta,
        maximum_shift,
        precomputed={(): constant_radial},
    )
    family_radials: dict[
        str,
        dict[tuple[int, int], RadialPoly],
    ] = defaultdict(dict)
    for tag, radial in flat_radials.items():
        family, fiber_power, residual_power = tag
        if not isinstance(family, str) or not isinstance(fiber_power, int) or not isinstance(residual_power, int):
            raise ArithmeticError("malformed internal tagged marginal key")
        family_radials[family][(fiber_power, residual_power)] = radial

    # Several ordered branch pairs consume the same exact family.  Pack each
    # family once per face, then share only its immutable tuple structure.
    # Jobs and their ordered accumulation slots remain completely unchanged.
    packed_families = {
        family: _pack_tagged_radials_by_shift(family_radials[family])
        for family in sorted(active_families)
    }
    del flat_radials, family_radials

    residual_affine = (
        Fraction(1) - r * params.delta,
        Fraction(-1),
        Fraction(-1),
    )
    for ordered_index, family, domain, fiber_affine in jobs:
        contributions[ordered_index] += _integrate_tagged_radial_polynomials(
            None,
            r,
            base_variables - r,
            params.delta,
            domain,
            first_affine=fiber_affine,
            second_affine=residual_affine,
            packed_by_shift=packed_families[family],
        )
    return sum(contributions, Fraction(0))


def compute_j_tagged(
    basis_terms: Mapping[tuple[int, Partition], Fraction],
    params: Parameters,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Production ordered J backend retaining both exact affine power tags."""
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    if params.alpha - params.eta != params.delta:
        raise ValueError("the production tagged J backend requires alpha - eta = delta")
    base_variables = params.k - 1
    small, large = _tagged_marginal_polynomials(basis_terms, params)
    products: dict[str, dict[tuple[int, int], SymPoly]] = {
        "small_small": _tagged_power_products(
            small,
            small,
            base_variables,
        ),
        "small_large": _tagged_power_products(
            small,
            large,
            base_variables,
        ),
        "large_large": _tagged_power_products(
            large,
            large,
            base_variables,
        ),
    }
    active_faces = []
    for r in range(base_variables + 1):
        if params.eta - r * params.delta <= 0:
            continue
        small_active = r == 0 or params.beta(r) - r * params.delta > 0
        large_active = params.beta(r + 1) - (r + 1) * params.delta > 0
        if small_active or large_active:
            active_faces.append(r)
    if reverse_faces:
        active_faces.reverse()
    if workers == 2:
        return _run_two_face_blocks(
            _compute_j_tagged_face,
            products,
            params,
            active_faces,
        )
    return sum(
        (
            _compute_j_tagged_face(products, params, r)
            for r in active_faces
        ),
        Fraction(0),
    )


def _compute_j_k1_general_for_tests(polynomial: Mapping[Partition, Fraction], params: Parameters) -> Fraction:
    """Direct Definition-5 k=1 path for tests outside alpha-eta=delta.

    This helper is intentionally private and is not reachable from the target
    CLI.  It lets the general zero-shared-variable boundary convention be
    tested without weakening ``validate_parameters`` or ``compute_j_tagged``.
    """
    if params.k != 1:
        raise ValueError("the private general path is only for k=1 tests")
    if params.eta < 0:
        return Fraction(0)
    coefficients_by_power: dict[int, Fraction] = defaultdict(Fraction)
    for part, coefficient in polynomial.items():
        if len(part) > 1:
            raise ValueError("a one-variable polynomial cannot have a multi-part orbit")
        power = part[0] if part else 0
        coefficients_by_power[power] += coefficient

    small_upper = min(params.alpha, params.delta)
    large_upper = min(params.alpha, params.beta1)
    marginal = Fraction(0)
    for power, coefficient in coefficients_by_power.items():
        marginal += coefficient * small_upper ** (power + 1) / (power + 1)
        if large_upper > params.delta:
            marginal += coefficient * (
                large_upper ** (power + 1) - params.delta ** (power + 1)
            ) / (power + 1)
    return marginal * marginal


def exact_check(
    path: Path,
    params: Parameters,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> dict[str, object]:
    validate_parameters(params)
    labels, coefficients = load_certificate(path, params)
    basis_terms = build_basis_terms(labels, coefficients)
    i_value = compute_i_tagged(
        basis_terms,
        params,
        reverse_faces=reverse_faces,
        workers=workers,
    )
    j_value = compute_j_tagged(
        basis_terms,
        params,
        reverse_faces=reverse_faces,
        workers=workers,
    )
    m2_value = params.k * j_value
    margin = m2_value - i_value
    quotient = m2_value / i_value if i_value else None
    return {
        "checker": "independent exact capped certificate v2 tagged-residual",
        "preset": params.name,
        "streaming_order": "reverse" if reverse_faces else "forward",
        "workers": workers,
        "input": str(path),
        "basis_dimension": len(labels),
        "tagged_nonzero_source_terms": len(basis_terms),
        "ordered_label_vector_provenance_sha256": (
            TARGET_ORDERED_PAYLOAD_SHA256 if params == TARGET_C10_D12 else None
        ),
        "ignored_discovery_fields": "all fields except k, degree, basis_dimension, basis, rational_vector",
        "support": {
            "k": params.k,
            "degree": params.degree,
            "alpha": str(params.alpha),
            "eta": str(params.eta),
            "delta": str(params.delta),
            "A": str((params.alpha + params.eta) / 2),
            "epsilon": str((params.alpha - params.eta) / 2),
            "beta1": str(params.beta1),
            "beta2": str(params.beta2),
            "beta3plus": str(params.beta3plus),
            "c1": "0",
            "c2": "0",
        },
        "I": str(i_value),
        "J": str(j_value),
        "M2": str(m2_value),
        "M2_minus_M1": str(margin),
        "cM1c_positive": i_value > 0,
        "c_M2_minus_M1_c_positive": margin > 0,
        "quotient": None if quotient is None else str(quotient),
        "certificate_passes": i_value > 0 and margin > 0,
    }


def _render_json(value: Mapping[str, object]) -> str:
    """Return the one canonical human-readable encoding emitted by the CLI."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _atomic_write_text(path: Path, payload: str) -> None:
    """Replace ``path`` atomically with a flushed UTF-8 payload."""
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _same_output_and_input(input_path: Path, output_path: Path) -> bool:
    """Reject lexical, symlink, and existing-hardlink input/output aliases."""
    try:
        if input_path.resolve(strict=False) == output_path.resolve(strict=False):
            return True
    except (OSError, RuntimeError):
        if os.path.abspath(input_path) == os.path.abspath(output_path):
            return True
    try:
        return input_path.exists() and output_path.exists() and os.path.samefile(
            input_path,
            output_path,
        )
    except OSError:
        return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--preset", choices=sorted(PRESETS), required=True)
    parser.add_argument(
        "--allow-d12",
        action="store_true",
        help="explicitly allow the expensive D12 target run",
    )
    parser.add_argument(
        "--streaming-order",
        choices=("forward", "reverse"),
        default="forward",
        help="enumerate support faces in the selected order",
    )
    parser.add_argument(
        "--workers",
        type=int,
        choices=(1, 2),
        default=1,
        help="use one process or two deterministic contiguous r-block workers",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "atomically persist the exact emitted JSON; a fail-closed sentinel "
            "is installed before calculation"
        ),
    )
    args = parser.parse_args(argv)
    params = PRESETS[args.preset]

    output_path = args.output
    if output_path is not None:
        if _same_output_and_input(args.certificate, output_path):
            error = {
                "certificate_passes": False,
                "error": "the output path aliases the input certificate",
            }
            sys.stderr.write(_render_json(error))
            return 2
        sentinel = {
            "certificate_passes": False,
            "error": "exact calculation did not complete",
        }
        try:
            _atomic_write_text(output_path, _render_json(sentinel))
        except OSError as exc:
            error = {
                "certificate_passes": False,
                "error": f"cannot initialize atomic output: {exc}",
            }
            sys.stderr.write(_render_json(error))
            return 2

    try:
        if params.degree >= 12 and not args.allow_d12:
            raise CertificateError(
                "D12 execution is guarded; pass --allow-d12 only after review/authorization"
            )
        result = exact_check(
            args.certificate,
            params,
            reverse_faces=args.streaming_order == "reverse",
            workers=args.workers,
        )
    except (CertificateError, ArithmeticError, ValueError) as exc:
        error = {"certificate_passes": False, "error": str(exc)}
        rendered_error = _render_json(error)
        if output_path is not None:
            try:
                _atomic_write_text(output_path, rendered_error)
            except OSError as output_exc:
                error["output_error"] = str(output_exc)
                rendered_error = _render_json(error)
        sys.stderr.write(rendered_error)
        return 2

    rendered_result = _render_json(result)
    if output_path is not None:
        try:
            _atomic_write_text(output_path, rendered_result)
        except OSError as exc:
            error = {
                "certificate_passes": False,
                "error": f"cannot commit atomic output: {exc}",
            }
            sys.stderr.write(_render_json(error))
            return 2
    sys.stdout.write(rendered_result)
    return 0 if result["certificate_passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
