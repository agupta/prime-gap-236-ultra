#!/usr/bin/env python3
"""Cache-free exact tagged backend for per-stratum affine multipliers.

For an unexpanded symmetric basis polynomial ``F0`` this module evaluates

    F(t) = F0(t) * (a_R + b_R L + c_R Z),

where ``R`` is the number of coordinates above ``delta`` and ``L,Z`` are the
large/small coordinate sums.  It imports only the independently audited
orbit and exact support-geometry primitives from ``exact_capped_certificate``;
no discovery matrix, Decimal evaluator, or moment cache is consumed.

The distinguished-fiber J calculation keeps the fiber-slack and residual-
slack powers tagged.  The two degree-one aggregate multipliers are expanded
only after face radialization, leaving the existing exact two-affine geometry
integrator responsible for the fiber and residual powers.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence

from verify.exact_capped_certificate import (
    AggregateDomain,
    BasisTerms,
    CertificateError,
    Parameters,
    Partition,
    RadialPoly,
    SymPoly,
    _affine_power_terms,
    _integrate_radial_polynomial,
    _integrate_tagged_radial_polynomials,
    _maximum_active_shift,
    _pack_tagged_radials_by_shift,
    _partition_face_radial,
    _radialize_tagged_targets,
    _run_two_face_blocks,
    _tagged_i_square,
    _reject_constant,
    _reject_duplicate_object,
    parse_fraction,
    poly_add_term,
    poly_multiply,
)


Affine = tuple[Fraction, Fraction, Fraction]
ZERO_AFFINE: Affine = (Fraction(0), Fraction(0), Fraction(0))
CHANNELS = ("1", "L", "Z")


@dataclass(frozen=True)
class AffineMultipliers:
    """A contiguous exact coefficient table indexed by the total count R."""

    coefficients: tuple[Affine, ...]
    source_sha256: str | None = None
    linear_cutoff: int | None = None

    def at(self, r: int) -> Affine:
        if r < 0:
            raise ValueError("negative stratum count")
        if r >= len(self.coefficients):
            return ZERO_AFFINE
        return self.coefficients[r]

    def validate_for(self, params: Parameters) -> None:
        if not self.coefficients:
            raise ValueError("affine multiplier table is empty")
        if len(self.coefficients) > params.k + 1:
            raise ValueError("affine multiplier has counts above k")
        active: set[int] = set()
        for r in range(params.k + 1):
            if params.alpha - r * params.delta > 0 and (
                    r == 0 or params.beta(r) - r * params.delta > 0):
                active.add(r)
        for r in range(params.k):
            if params.eta - r * params.delta <= 0:
                continue
            if r == 0 or params.beta(r) - r * params.delta > 0:
                active.add(r)
            if params.beta(r + 1) - (r + 1) * params.delta > 0:
                active.add(r + 1)
        missing = sorted(r for r in active if r >= len(self.coefficients))
        if missing:
            raise ValueError(f"affine multiplier omits active counts {missing}")


def affine_multipliers_from_mapping(
    params: Parameters,
    values: Mapping[int, Sequence[Fraction]],
    *,
    linear_cutoff: int | None = None,
) -> AffineMultipliers:
    """Build a checked contiguous table for exact tests and reconstructions."""
    if (linear_cutoff is not None and
            (isinstance(linear_cutoff, bool) or linear_cutoff < 0 or
             linear_cutoff > params.k)):
        raise ValueError("linear cutoff must be an integer in [0,k]")
    if not values:
        raise ValueError("affine multiplier mapping is empty")
    keys = sorted(values)
    if keys != list(range(keys[-1] + 1)):
        raise ValueError("affine multiplier counts must be contiguous from zero")
    coefficients: list[Affine] = []
    for r in keys:
        vector = tuple(values[r])
        if len(vector) != 3 or any(not isinstance(x, Fraction) for x in vector):
            raise ValueError("each affine multiplier needs three Fractions")
        a, b, c = vector
        if linear_cutoff is not None and r > linear_cutoff:
            b = c = Fraction(0)
        coefficients.append((a, b, c))
    answer = AffineMultipliers(
        tuple(coefficients), linear_cutoff=linear_cutoff)
    answer.validate_for(params)
    return answer


def load_exact_affine_multiplier(
    path: Path,
    params: Parameters,
    expected_sha256: str,
    *,
    linear_cutoff: int | None = None,
) -> AffineMultipliers:
    """Parse the exact stratum-linear artifact without trusting its matrices."""
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise CertificateError(f"cannot read affine multiplier: {exc}") from exc
    if len(raw_bytes) > 20_000_000:
        raise CertificateError("affine multiplier exceeds the 20 MB input limit")
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha != expected_sha256:
        raise CertificateError(
            f"affine multiplier SHA mismatch: expected {expected_sha256}, "
            f"got {actual_sha}")
    try:
        raw = json.loads(
            raw_bytes,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CertificateError(f"invalid affine multiplier JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise CertificateError("affine multiplier must be a JSON object")
    if raw.get("status") != "exact-stratum-linear-rational-vector":
        raise CertificateError("affine multiplier status is not exact")
    if raw.get("rigorous_forms") is not True or \
            raw.get("block_direct_bitwise_equal") is not True:
        raise CertificateError("affine multiplier exact gates are absent")
    k = raw.get("k")
    if isinstance(k, bool) or not isinstance(k, int) or k != params.k:
        raise CertificateError("affine multiplier k mismatch")
    labels = raw.get("linear_labels")
    vector = raw.get("rational_vector")
    if not isinstance(labels, list) or not isinstance(vector, list) or \
            len(labels) != len(vector) or not labels:
        raise CertificateError("malformed affine label/vector arrays")
    if len(labels) % 3:
        raise CertificateError("affine label count is not divisible by three")
    maximum_r = len(labels) // 3 - 1
    expected_labels = [[r, channel]
                       for r in range(maximum_r + 1)
                       for channel in CHANNELS]
    if labels != expected_labels:
        raise CertificateError("affine labels are not canonical contiguous 1/L/Z blocks")
    parsed = [parse_fraction(value, f"rational_vector[{index}]")
              for index, value in enumerate(vector)]
    values = {
        r: tuple(parsed[3 * r:3 * r + 3])
        for r in range(maximum_r + 1)
    }
    answer = affine_multipliers_from_mapping(
        params, values, linear_cutoff=linear_cutoff)
    return AffineMultipliers(
        answer.coefficients,
        source_sha256=actual_sha,
        linear_cutoff=linear_cutoff,
    )


def _compute_i_affine_face(payload, params: Parameters, r: int) -> Fraction:
    squared, multipliers = payload
    total_bound = params.alpha - r * params.delta
    if total_bound <= 0:
        return Fraction(0)
    x_bound = None if r == 0 else params.beta(r) - r * params.delta
    if x_bound is not None and x_bound <= 0:
        return Fraction(0)
    radials = _radialize_tagged_targets(
        squared,
        params.k,
        r,
        params.delta,
        _maximum_active_shift(total_bound, params.delta),
    )
    retagged = {(2, residual_power): radial
                for (_, residual_power), radial in radials.items()}
    packed = _pack_tagged_radials_by_shift(retagged)
    a, b, c = multipliers.at(r)
    return _integrate_tagged_radial_polynomials(
        None,
        r,
        params.k - r,
        params.delta,
        AggregateDomain(total_bound=total_bound, x_bound=x_bound),
        first_affine=(a + b * r * params.delta, b, c),
        second_affine=(
            params.alpha - r * params.delta,
            Fraction(-1),
            Fraction(-1),
        ),
        packed_by_shift=packed,
    )


def compute_i_affine_tagged(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: AffineMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Evaluate I exactly while retaining all residual-slack powers."""
    multipliers.validate_for(params)
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    squared = _tagged_i_square(basis_terms, params.k, params.alpha)
    active = [r for r in range(params.k + 1)
              if params.alpha - r * params.delta > 0 and
              (r == 0 or params.beta(r) - r * params.delta > 0)]
    if reverse_faces:
        active.reverse()
    payload = (squared, multipliers)
    if workers == 2:
        return _run_two_face_blocks(
            _compute_i_affine_face, payload, params, active)
    return sum((_compute_i_affine_face(payload, params, r) for r in active),
               Fraction(0))


def _tagged_marginal_moment_polynomials(
    basis_terms: BasisTerms,
    params: Parameters,
    moment: int,
) -> tuple[dict[tuple[int, int], SymPoly],
           dict[tuple[int, int], SymPoly]]:
    """Return small/large tagged families for integral t^moment F0(U,t)dt."""
    if moment < 0:
        raise ValueError("negative distinguished-fiber moment")
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
                endpoint_power = (
                    t_power + binomial_power + moment + 1)
                common = (
                    source_coefficient
                    * (-1) ** binomial_power
                    * Fraction(math.comb(
                        residual_power, binomial_power), endpoint_power)
                )
                poly_add_term(
                    small[(0, remaining_residual)],
                    remaining_part,
                    common * params.delta ** endpoint_power,
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


def _scale_poly(polynomial: Mapping[Partition, Fraction],
                scale: Fraction) -> SymPoly:
    return {part: scale * coefficient
            for part, coefficient in polynomial.items()
            if scale * coefficient}


def _weighted_branch_marginal(
    small_branch: bool,
    r: int,
    zero_families,
    first_families,
    params: Parameters,
    multipliers: AffineMultipliers,
) -> tuple[dict[tuple[int, int, int], SymPoly], Affine]:
    total_r = r if small_branch else r + 1
    a, b, c = multipliers.at(total_r)
    aggregate = (a + b * r * params.delta, b, c)
    zero_family = zero_families[0] if small_branch else zero_families[1]
    first_family = first_families[0] if small_branch else first_families[1]
    shifted_scale = c if small_branch else b
    answer: dict[tuple[int, int, int], SymPoly] = defaultdict(dict)
    if any(aggregate):
        for (fiber_power, residual_power), polynomial in zero_family.items():
            for part, coefficient in polynomial.items():
                poly_add_term(
                    answer[(fiber_power, residual_power, 1)],
                    part, coefficient)
    if shifted_scale:
        for (fiber_power, residual_power), polynomial in first_family.items():
            for part, coefficient in polynomial.items():
                poly_add_term(
                    answer[(fiber_power, residual_power, 0)],
                    part, shifted_scale * coefficient)
    return ({tag: polynomial for tag, polynomial in answer.items()
             if polynomial}, aggregate)


def _ordered_branch_product(
    left: Mapping[tuple[int, int, int], Mapping[Partition, Fraction]],
    right: Mapping[tuple[int, int, int], Mapping[Partition, Fraction]],
    number_variables: int,
) -> dict[tuple[int, int, int, int], SymPoly]:
    answer: dict[tuple[int, int, int, int], SymPoly] = defaultdict(dict)
    for (lf, lr, la), left_poly in sorted(left.items()):
        for (rf, rr, ra), right_poly in sorted(right.items()):
            multiplied = poly_multiply(left_poly, right_poly, number_variables)
            target = (lf + rf, lr + rr, la, ra)
            for part, coefficient in multiplied.items():
                poly_add_term(answer[target], part, coefficient)
    return {tag: polynomial for tag, polynomial in answer.items()
            if polynomial}


def _expand_aggregate_markers(
    tagged_radials: Mapping[tuple[int, int, int, int], RadialPoly],
    delta: Fraction,
    left_affine: Affine,
    right_affine: Affine,
    r: int,
    s: int,
) -> dict[tuple[int, int], RadialPoly]:
    """Expand the two degree-one aggregate affines after radialization."""
    answer: dict[tuple[int, int], dict[tuple[int, int, int], Fraction]] = \
        defaultdict(lambda: defaultdict(Fraction))
    for (fiber_power, residual_power, left_power, right_power), radial in \
            sorted(tagged_radials.items()):
        if left_power not in (0, 1) or right_power not in (0, 1):
            raise ArithmeticError("aggregate affine marker exceeds degree one")
        for (number_shifted, x_power, y_power), coefficient in radial.items():
            shift = number_shifted * delta
            left_terms = _affine_power_terms(
                left_power,
                left_affine[0] + left_affine[2] * shift,
                left_affine[1], left_affine[2])
            right_terms = _affine_power_terms(
                right_power,
                right_affine[0] + right_affine[2] * shift,
                right_affine[1], right_affine[2])
            destination = answer[(fiber_power, residual_power)]
            for (lx, ly), lc in left_terms.items():
                for (rx, ry), rc in right_terms.items():
                    # X or Y is the identically-zero aggregate on a face
                    # with no variables of the corresponding kind.
                    if (r == 0 and lx + rx) or (s == 0 and ly + ry):
                        continue
                    destination[(number_shifted,
                                 x_power + lx + rx,
                                 y_power + ly + ry)] += coefficient * lc * rc
    return {
        tag: {key: coefficient for key, coefficient in radial.items()
              if coefficient}
        for tag, radial in answer.items()
        if any(radial.values())
    }


def _compute_j_affine_face(payload, params: Parameters, r: int) -> Fraction:
    zero_families, first_families, multipliers = payload
    base_variables = params.k - 1
    total_bound = params.eta - r * params.delta
    if total_bound <= 0:
        return Fraction(0)
    small_x = None if r == 0 else params.beta(r) - r * params.delta
    large_x = params.beta(r + 1) - (r + 1) * params.delta
    threshold = params.eta - params.beta(r + 1) + params.delta
    branch_names = ("small_delta", "small_total", "cap", "total")
    branch_data = {
        "small_delta": (small_x, None, None, None),
        "small_total": (small_x, None, None, total_bound),
        "cap": (large_x, None, threshold, None),
        "total": (large_x, threshold, None, None),
    }
    small_terms, small_affine = _weighted_branch_marginal(
        True, r, zero_families, first_families, params, multipliers)
    large_terms, large_affine = _weighted_branch_marginal(
        False, r, zero_families, first_families, params, multipliers)
    term_data = {
        "small_delta": (small_terms, small_affine),
        "small_total": (small_terms, small_affine),
        "cap": (large_terms, large_affine),
        "total": (large_terms, large_affine),
    }
    maximum_shift = _maximum_active_shift(total_bound, params.delta)
    constant_radial = {
        key: value for key, value in _partition_face_radial(
            (), base_variables, r, params.delta).items()
        if key[0] <= maximum_shift
    }
    contributions = [Fraction(0) for _ in range(16)]
    product_cache = {}
    for li, left_name in enumerate(branch_names):
        for ri, right_name in enumerate(branch_names):
            ordered_index = 4 * li + ri
            lx, ll, lu, lt = branch_data[left_name]
            rx, rl, ru, rt = branch_data[right_name]
            x_bounds = [x for x in (lx, rx) if x is not None]
            x_bound = min(x_bounds) if x_bounds else None
            if x_bound is not None and x_bound <= 0:
                continue
            lowers = [x for x in (ll, rl) if x is not None]
            uppers = [x for x in (lu, ru) if x is not None]
            totals = [x for x in (lt, rt) if x is not None]
            domain = AggregateDomain(
                total_bound=total_bound,
                x_bound=x_bound,
                y_lower=max(lowers) if lowers else None,
                y_upper=min(uppers) if uppers else None,
                total_lower=max(totals) if totals else None,
            )
            boundary = ("small_total" in (left_name, right_name) or
                        {left_name, right_name} == {"cap", "total"})
            if boundary:
                if _integrate_radial_polynomial(
                        constant_radial, r, base_variables - r,
                        params.delta, domain):
                    raise ArithmeticError(
                        "nominal boundary branches have positive measure")
                continue
            left_terms, left_affine = term_data[left_name]
            right_terms, right_affine = term_data[right_name]
            if not left_terms or not right_terms:
                continue
            family = (left_name.startswith("small"),
                      right_name.startswith("small"))
            products = product_cache.get(family)
            if products is None:
                products = _ordered_branch_product(
                    left_terms, right_terms, base_variables)
                product_cache[family] = products
            flat = _radialize_tagged_targets(
                products, base_variables, r, params.delta, maximum_shift,
                precomputed={(): constant_radial})
            expanded = _expand_aggregate_markers(
                flat, params.delta, left_affine, right_affine,
                r, base_variables - r)
            packed = _pack_tagged_radials_by_shift(expanded)
            if left_name == "cap" or right_name == "cap":
                fiber_affine = (large_x, Fraction(-1), Fraction(0))
            elif left_name == "total" or right_name == "total":
                fiber_affine = (total_bound, Fraction(-1), Fraction(-1))
            else:
                fiber_affine = ZERO_AFFINE
            residual_affine = (
                Fraction(1) - r * params.delta,
                Fraction(-1), Fraction(-1))
            contributions[ordered_index] = _integrate_tagged_radial_polynomials(
                None, r, base_variables - r, params.delta, domain,
                first_affine=fiber_affine,
                second_affine=residual_affine,
                packed_by_shift=packed)
    return sum(contributions, Fraction(0))


def compute_j_affine_tagged(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: AffineMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Evaluate Definition-5 J exactly with 16 ordered branch pairs."""
    multipliers.validate_for(params)
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    if params.alpha - params.eta != params.delta:
        raise ValueError("tagged affine J requires alpha-eta=delta")
    zero_families = _tagged_marginal_moment_polynomials(
        basis_terms, params, 0)
    first_families = _tagged_marginal_moment_polynomials(
        basis_terms, params, 1)
    active = []
    for r in range(params.k):
        if params.eta - r * params.delta <= 0:
            continue
        small_active = r == 0 or params.beta(r) - r * params.delta > 0
        large_active = params.beta(r + 1) - (r + 1) * params.delta > 0
        if small_active or large_active:
            active.append(r)
    if reverse_faces:
        active.reverse()
    payload = (zero_families, first_families, multipliers)
    if workers == 2:
        return _run_two_face_blocks(
            _compute_j_affine_face, payload, params, active)
    return sum((_compute_j_affine_face(payload, params, r) for r in active),
               Fraction(0))


def compute_affine_tagged(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: AffineMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> tuple[Fraction, Fraction]:
    """Return exact ``(I,kJ)`` for one tagged affine-multiplied polynomial."""
    i_value = compute_i_affine_tagged(
        basis_terms, params, multipliers,
        reverse_faces=reverse_faces, workers=workers)
    j_value = compute_j_affine_tagged(
        basis_terms, params, multipliers,
        reverse_faces=reverse_faces, workers=workers)
    return i_value, params.k * j_value
