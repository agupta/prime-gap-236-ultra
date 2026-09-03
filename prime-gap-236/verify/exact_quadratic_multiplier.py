#!/usr/bin/env python3
"""Cache-free tagged backend for per-stratum quadratic multipliers.

For a symmetric unexpanded base polynomial ``F0`` this module evaluates

    F(t) = F0(t) * Q_R(L,Z),

where ``R`` is the number of coordinates above ``delta``, ``L`` and ``Z``
are respectively the sums of the large and small coordinates, and

    Q_R(L,Z) = a_R + b_R L + c_R Z
                 + d_R L^2 + e_R L Z + f_R Z^2.

The implementation is independent of the Decimal stratum-quadratic
producer.  It retains the fiber-slack and residual-slack powers as tags and
uses only the audited orbit/face geometry in ``exact_capped_certificate``.
All sixteen ordered distinguished-fiber branch intersections are kept.

Although the type annotations name ``Fraction``, the arithmetic is ring
generic: replacing coefficient leaves by the audited ``DyadicInterval``
ring gives a directed enclosure of the same finite tagged calculation.
Geometry and all branch decisions remain exact Fractions.
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

from verify.exact_affine_multiplier import (
    _tagged_marginal_moment_polynomials,
)
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


CHANNELS = ("1", "L", "Z", "L^2", "LZ", "Z^2")
CHANNEL_POWERS = ((0, 0), (1, 0), (0, 1),
                  (2, 0), (1, 1), (0, 2))
ZERO_QUADRATIC = (Fraction(0),) * 6


@dataclass(frozen=True)
class QuadraticMultipliers:
    """A contiguous exact six-channel table indexed by total count R."""

    coefficients: tuple[tuple[Fraction, ...], ...]
    source_sha256: str | None = None

    def at(self, r: int):
        if r < 0:
            raise ValueError("negative stratum count")
        if r >= len(self.coefficients):
            return ZERO_QUADRATIC
        return self.coefficients[r]

    def validate_for(self, params: Parameters) -> None:
        if not self.coefficients:
            raise ValueError("quadratic multiplier table is empty")
        if len(self.coefficients) > params.k + 1:
            raise ValueError("quadratic multiplier has counts above k")
        for r, row in enumerate(self.coefficients):
            if len(row) != 6:
                raise ValueError(f"quadratic multiplier row {r} is not length six")
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
            raise ValueError(f"quadratic multiplier omits active counts {missing}")


def quadratic_multipliers_from_mapping(
    params: Parameters,
    values: Mapping[int, Sequence[Fraction]],
) -> QuadraticMultipliers:
    if not values:
        raise ValueError("quadratic multiplier mapping is empty")
    keys = sorted(values)
    if keys != list(range(keys[-1] + 1)):
        raise ValueError("quadratic multiplier counts must be contiguous from zero")
    rows = []
    for r in keys:
        row = tuple(values[r])
        if len(row) != 6 or any(not isinstance(x, Fraction) for x in row):
            raise ValueError("each quadratic multiplier needs six Fractions")
        rows.append(row)
    answer = QuadraticMultipliers(tuple(rows))
    answer.validate_for(params)
    return answer


def _expected_active_labels(params: Parameters, maximum_r: int):
    active_counts: set[int] = set()
    for r in range(params.k + 1):
        if params.alpha - r * params.delta > 0 and (
                r == 0 or params.beta(r) - r * params.delta > 0):
            active_counts.add(r)
    for r in range(params.k):
        if params.eta - r * params.delta <= 0:
            continue
        if r == 0 or params.beta(r) - r * params.delta > 0:
            active_counts.add(r)
        if params.beta(r + 1) - (r + 1) * params.delta > 0:
            active_counts.add(r + 1)
    if active_counts != set(range(maximum_r + 1)):
        raise CertificateError(
            "quadratic artifact does not cover exactly the active contiguous counts")
    null = {(0, "L"), (0, "L^2"), (0, "LZ")}
    return [[r, channel] for r in range(maximum_r + 1)
            for channel in CHANNELS if (r, channel) not in null]


def load_exact_quadratic_multiplier(
    path: Path,
    params: Parameters,
    expected_sha256: str,
) -> QuadraticMultipliers:
    """Parse and validate the exact six-channel D4 multiplier artifact.

    The serialized matrices and discovery solve are not consumed.  The byte
    pin and exact-form gates establish the provenance of the rational vector;
    the present module reconstructs every target integral independently.
    """
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise CertificateError(f"cannot read quadratic multiplier: {exc}") from exc
    if len(raw_bytes) > 20_000_000:
        raise CertificateError("quadratic multiplier exceeds the 20 MB limit")
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha != expected_sha256:
        raise CertificateError(
            f"quadratic multiplier SHA mismatch: expected {expected_sha256}, "
            f"got {actual_sha}")
    try:
        raw = json.loads(
            raw_bytes,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CertificateError(f"invalid quadratic multiplier JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise CertificateError("quadratic multiplier must be an object")
    if raw.get("status") != "exact-stratum-quadratic-rational-vector":
        raise CertificateError("quadratic multiplier status is not exact")
    if (raw.get("rigorous_forms") is not True or
            raw.get("block_direct_bitwise_equal") is not True):
        raise CertificateError("quadratic exact-form gates are absent")
    if raw.get("eigenvector_discovery_rigorous") is not False:
        raise CertificateError("quadratic discovery-rigor field is malformed")
    k = raw.get("k")
    if isinstance(k, bool) or not isinstance(k, int) or k != params.k:
        raise CertificateError("quadratic multiplier k mismatch")
    expected_parameters = {
        "alpha": str(params.alpha), "delta": str(params.delta),
        "eta": str(params.eta), "beta1": str(params.beta1),
        "beta2": str(params.beta2), "beta3plus": str(params.beta3plus),
    }
    if raw.get("parameters") != expected_parameters:
        raise CertificateError("quadratic multiplier parameter mismatch")
    if raw.get("channel_powers") != [list(power) for power in CHANNEL_POWERS]:
        raise CertificateError("quadratic channel powers mismatch")
    labels = raw.get("quadratic_labels")
    vector = raw.get("rational_vector")
    if (not isinstance(labels, list) or not isinstance(vector, list) or
            len(labels) != len(vector) or not labels or len(labels) % 6):
        raise CertificateError("malformed quadratic label/vector arrays")
    maximum_r = len(labels) // 6 - 1
    expected_labels = [[r, channel] for r in range(maximum_r + 1)
                       for channel in CHANNELS]
    if labels != expected_labels:
        raise CertificateError("quadratic labels are not canonical contiguous blocks")
    if raw.get("quadratic_basis_dimension") != len(expected_labels):
        raise CertificateError("quadratic basis dimension mismatch")
    discarded = [[0, "L"], [0, "L^2"], [0, "LZ"]]
    if raw.get("discarded_gram_dependent_labels") != discarded:
        raise CertificateError("quadratic discarded-label semantics mismatch")
    active = _expected_active_labels(params, maximum_r)
    if raw.get("active_quadratic_labels") != active:
        raise CertificateError("quadratic active-label semantics mismatch")
    if raw.get("discovery_basis_dimension") != len(active):
        raise CertificateError("quadratic discovery dimension mismatch")
    parsed = [parse_fraction(value, f"rational_vector[{index}]")
              for index, value in enumerate(vector)]
    index_by_label = {tuple(label): index for index, label in enumerate(labels)}
    for label in discarded:
        if parsed[index_by_label[tuple(label)]] != 0:
            raise CertificateError(f"discarded quadratic label {label} is nonzero")
    values = {r: tuple(parsed[6 * r:6 * r + 6])
              for r in range(maximum_r + 1)}
    answer = quadratic_multipliers_from_mapping(params, values)
    return QuadraticMultipliers(answer.coefficients, source_sha256=actual_sha)


def _lz_power_terms(l_power: int, z_power: int, r: int, shift: Fraction,
                    delta: Fraction):
    """Expand L^l Z^z with L=r*delta+X and Z=shift+Y."""
    left = _affine_power_terms(
        l_power, r * delta, Fraction(1), Fraction(0))
    right = _affine_power_terms(
        z_power, shift, Fraction(0), Fraction(1))
    answer = defaultdict(Fraction)
    for (lx, ly), lc in left.items():
        for (rx, ry), rc in right.items():
            answer[(lx + rx, ly + ry)] += lc * rc
    return {power: coefficient for power, coefficient in answer.items()
            if coefficient}


def _expand_lz_markers(
    tagged_radials: Mapping[tuple[int, int, int, int], RadialPoly],
    delta: Fraction,
    r: int,
    s: int,
) -> dict[tuple[int, int], RadialPoly]:
    answer = defaultdict(lambda: defaultdict(Fraction))
    expansions = {}
    for (fiber_power, residual_power, l_power, z_power), radial in \
            sorted(tagged_radials.items()):
        if min(fiber_power, residual_power, l_power, z_power) < 0:
            raise ArithmeticError("negative quadratic marker power")
        destination = answer[(fiber_power, residual_power)]
        for (number_shifted, x_power, y_power), coefficient in radial.items():
            key = (l_power, z_power, number_shifted)
            terms = expansions.get(key)
            if terms is None:
                terms = _lz_power_terms(
                    l_power, z_power, r, number_shifted * delta, delta)
                expansions[key] = terms
            for (add_x, add_y), scale in terms.items():
                if (r == 0 and add_x) or (s == 0 and add_y):
                    continue
                destination[(number_shifted,
                             x_power + add_x,
                             y_power + add_y)] += coefficient * scale
    return {
        tag: {key: coefficient for key, coefficient in radial.items()
              if coefficient}
        for tag, radial in answer.items()
        if any(radial.values())
    }


def _quadratic_square_powers(row):
    answer = defaultdict(Fraction)
    for left, (ll, lz) in zip(row, CHANNEL_POWERS, strict=True):
        if not left:
            continue
        for right, (rl, rz) in zip(row, CHANNEL_POWERS, strict=True):
            if right:
                answer[(ll + rl, lz + rz)] += left * right
    return {power: coefficient for power, coefficient in answer.items()
            if coefficient}


def _compute_i_quadratic_face(payload, params: Parameters, r: int):
    squared, multipliers = payload
    total_bound = params.alpha - r * params.delta
    if total_bound <= 0:
        return Fraction(0)
    x_bound = None if r == 0 else params.beta(r) - r * params.delta
    if x_bound is not None and x_bound <= 0:
        return Fraction(0)
    radials = _radialize_tagged_targets(
        squared, params.k, r, params.delta,
        _maximum_active_shift(total_bound, params.delta))
    marked = {}
    powers = _quadratic_square_powers(multipliers.at(r))
    for (_, residual_power), radial in radials.items():
        for (l_power, z_power), scale in powers.items():
            marked[(0, residual_power, l_power, z_power)] = {
                key: scale * coefficient for key, coefficient in radial.items()
                if scale * coefficient
            }
    expanded = _expand_lz_markers(
        marked, params.delta, r, params.k - r)
    packed = _pack_tagged_radials_by_shift(expanded)
    return _integrate_tagged_radial_polynomials(
        None, r, params.k - r, params.delta,
        AggregateDomain(total_bound=total_bound, x_bound=x_bound),
        first_affine=(Fraction(0), Fraction(0), Fraction(0)),
        second_affine=(total_bound, Fraction(-1), Fraction(-1)),
        packed_by_shift=packed)


def compute_i_quadratic_tagged(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: QuadraticMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
):
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
            _compute_i_quadratic_face, payload, params, active)
    return sum((_compute_i_quadratic_face(payload, params, r) for r in active),
               Fraction(0))


def _weighted_quadratic_branch(
    small_branch: bool,
    r: int,
    moment_families,
    multipliers: QuadraticMultipliers,
):
    """Integrate Q(L,Z+t) or Q(L+t,Z) against the distinguished fiber."""
    total_r = r if small_branch else r + 1
    row = multipliers.at(total_r)
    answer = defaultdict(dict)
    for coefficient, (l_power, z_power) in zip(
            row, CHANNEL_POWERS, strict=True):
        if not coefficient:
            continue
        maximum_moment = z_power if small_branch else l_power
        for moment in range(maximum_moment + 1):
            scale = coefficient * math.comb(maximum_moment, moment)
            remaining_l = l_power - (0 if small_branch else moment)
            remaining_z = z_power - (moment if small_branch else 0)
            small_family, large_family = moment_families[moment]
            family = small_family if small_branch else large_family
            for (fiber_power, residual_power), polynomial in family.items():
                destination = answer[(fiber_power, residual_power,
                                      remaining_l, remaining_z)]
                for part, value in polynomial.items():
                    poly_add_term(destination, part, scale * value)
    return {tag: polynomial for tag, polynomial in answer.items()
            if polynomial}


def _ordered_quadratic_product(left, right, number_variables: int):
    answer = defaultdict(dict)
    for (lf, lr, ll, lz), left_poly in sorted(left.items()):
        for (rf, rr, rl, rz), right_poly in sorted(right.items()):
            product = poly_multiply(left_poly, right_poly, number_variables)
            target = (lf + rf, lr + rr, ll + rl, lz + rz)
            for part, coefficient in product.items():
                poly_add_term(answer[target], part, coefficient)
    return {tag: polynomial for tag, polynomial in answer.items()
            if polynomial}


def _compute_j_quadratic_face(payload, params: Parameters, r: int):
    moment_families, multipliers = payload
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
    small_terms = _weighted_quadratic_branch(
        True, r, moment_families, multipliers)
    large_terms = _weighted_quadratic_branch(
        False, r, moment_families, multipliers)
    term_data = {True: small_terms, False: large_terms}
    maximum_shift = _maximum_active_shift(total_bound, params.delta)
    constant_radial = {
        key: value for key, value in _partition_face_radial(
            (), base_variables, r, params.delta).items()
        if key[0] <= maximum_shift
    }

    contributions = [Fraction(0) for _ in range(16)]
    jobs = []
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
            family = (left_name.startswith("small"),
                      right_name.startswith("small"))
            if not term_data[family[0]] or not term_data[family[1]]:
                continue
            jobs.append((ordered_index, family, left_name, right_name, domain))

    active_families = {family for _, family, _, _, _ in jobs}
    products = {
        family: _ordered_quadratic_product(
            term_data[family[0]], term_data[family[1]], base_variables)
        for family in sorted(active_families)
    }
    flat_polynomials = {}
    for family in sorted(active_families):
        for tag, polynomial in sorted(products[family].items()):
            flat_polynomials[(family, *tag)] = polynomial
    flat_radials = _radialize_tagged_targets(
        flat_polynomials, base_variables, r, params.delta, maximum_shift,
        precomputed={(): constant_radial})
    family_radials = defaultdict(dict)
    for (family, fiber_power, residual_power, l_power, z_power), radial \
            in flat_radials.items():
        family_radials[family][(
            fiber_power, residual_power, l_power, z_power)] = radial
    packed_families = {}
    for family in sorted(active_families):
        expanded = _expand_lz_markers(
            family_radials[family], params.delta,
            r, base_variables - r)
        packed_families[family] = _pack_tagged_radials_by_shift(expanded)

    residual_affine = (Fraction(1) - r * params.delta,
                       Fraction(-1), Fraction(-1))
    for ordered_index, family, left_name, right_name, domain in jobs:
        if left_name == "cap" or right_name == "cap":
            fiber_affine = (large_x, Fraction(-1), Fraction(0))
        elif left_name == "total" or right_name == "total":
            fiber_affine = (total_bound, Fraction(-1), Fraction(-1))
        else:
            fiber_affine = (Fraction(0), Fraction(0), Fraction(0))
        contributions[ordered_index] = _integrate_tagged_radial_polynomials(
            None, r, base_variables - r, params.delta, domain,
            first_affine=fiber_affine,
            second_affine=residual_affine,
            packed_by_shift=packed_families[family])
    return sum(contributions, Fraction(0))


def compute_j_quadratic_tagged(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: QuadraticMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
):
    multipliers.validate_for(params)
    if workers not in (1, 2):
        raise ValueError("exact face workers must be 1 or 2")
    if params.alpha - params.eta != params.delta:
        raise ValueError("tagged quadratic J requires alpha-eta=delta")
    moment_families = {
        moment: _tagged_marginal_moment_polynomials(
            basis_terms, params, moment)
        for moment in range(3)
    }
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
    payload = (moment_families, multipliers)
    if workers == 2:
        return _run_two_face_blocks(
            _compute_j_quadratic_face, payload, params, active)
    return sum((_compute_j_quadratic_face(payload, params, r) for r in active),
               Fraction(0))


def compute_quadratic_tagged(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: QuadraticMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
):
    i_value = compute_i_quadratic_tagged(
        basis_terms, params, multipliers,
        reverse_faces=reverse_faces, workers=workers)
    j_value = compute_j_quadratic_tagged(
        basis_terms, params, multipliers,
        reverse_faces=reverse_faces, workers=workers)
    return i_value, params.k * j_value


__all__ = [
    "CHANNELS", "CHANNEL_POWERS", "QuadraticMultipliers",
    "compute_i_quadratic_tagged", "compute_j_quadratic_tagged",
    "compute_quadratic_tagged", "load_exact_quadratic_multiplier",
    "quadratic_multipliers_from_mapping",
]
