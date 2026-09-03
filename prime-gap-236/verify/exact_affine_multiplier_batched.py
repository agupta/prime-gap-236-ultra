#!/usr/bin/env python3
"""Batched exact J traversal for a per-stratum affine multiplier.

This is an optimization layer over :mod:`verify.exact_affine_multiplier`.
It changes no algebra: on a fixed large-coordinate face, the four
small/large ordered marginal-product families are radialized together.  The
resulting immutable radial data are then reused by every branch intersection
having that family.  In particular, domains and all sixteen ordered branch
pairs retain separate integration slots.

The slower audited module remains untouched and is the regression oracle for
this implementation.  This module reads no serialized matrix or moment
cache.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Mapping

from verify.exact_affine_multiplier import (
    Affine,
    AffineMultipliers,
    ZERO_AFFINE,
    _expand_aggregate_markers,
    _ordered_branch_product,
    _tagged_marginal_moment_polynomials,
    _weighted_branch_marginal,
    compute_i_affine_tagged,
)
from verify.exact_capped_certificate import (
    AggregateDomain,
    BasisTerms,
    Parameters,
    RadialPoly,
    SymPoly,
    _integrate_radial_polynomial,
    _integrate_tagged_radial_polynomials,
    _maximum_active_shift,
    _pack_tagged_radials_by_shift,
    _partition_face_radial,
    _radialize_tagged_targets,
    _run_two_face_blocks,
)


Family = tuple[bool, bool]


def _compute_j_affine_face_batched(payload, params: Parameters,
                                   r: int) -> Fraction:
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
    term_data: dict[bool, tuple[Mapping, Affine]] = {
        True: (small_terms, small_affine),
        False: (large_terms, large_affine),
    }

    maximum_shift = _maximum_active_shift(total_bound, params.delta)
    constant_radial = {
        key: value
        for key, value in _partition_face_radial(
            (), base_variables, r, params.delta).items()
        if key[0] <= maximum_shift
    }

    # Preserve all sixteen ordered accumulation slots.  A job records only
    # the immutable product family and the exact branch-intersection domain;
    # no symmetry or factor-two convention is used.
    contributions = [Fraction(0) for _ in range(16)]
    jobs: list[tuple[int, Family, str, str, AggregateDomain]] = []
    for li, left_name in enumerate(branch_names):
        for ri, right_name in enumerate(branch_names):
            ordered_index = 4 * li + ri
            lx, ll, lu, lt = branch_data[left_name]
            rx, rl, ru, rt = branch_data[right_name]
            x_bounds = [bound for bound in (lx, rx) if bound is not None]
            x_bound = min(x_bounds) if x_bounds else None
            if x_bound is not None and x_bound <= 0:
                continue
            lowers = [bound for bound in (ll, rl) if bound is not None]
            uppers = [bound for bound in (lu, ru) if bound is not None]
            totals = [bound for bound in (lt, rt) if bound is not None]
            domain = AggregateDomain(
                total_bound=total_bound,
                x_bound=x_bound,
                y_lower=max(lowers) if lowers else None,
                y_upper=min(uppers) if uppers else None,
                total_lower=max(totals) if totals else None,
            )
            boundary = (
                "small_total" in (left_name, right_name)
                or {left_name, right_name} == {"cap", "total"}
            )
            if boundary:
                if _integrate_radial_polynomial(
                        constant_radial, r, base_variables - r,
                        params.delta, domain):
                    raise ArithmeticError(
                        "nominal boundary branches have positive measure")
                continue
            left_small = left_name.startswith("small")
            right_small = right_name.startswith("small")
            if not term_data[left_small][0] or not term_data[right_small][0]:
                continue
            jobs.append((ordered_index, (left_small, right_small),
                         left_name, right_name, domain))

    active_families = {family for _, family, _, _, _ in jobs}
    products: dict[Family, dict[tuple[int, int, int, int], SymPoly]] = {}
    for family in sorted(active_families):
        left_terms = term_data[family[0]][0]
        right_terms = term_data[family[1]][0]
        products[family] = _ordered_branch_product(
            left_terms, right_terms, base_variables)

    # A single orbit-to-face transform serves every tagged polynomial in all
    # four ordered families.  Tags are uniform tuples, so their sorting is
    # deterministic in normal and optimized Python modes.
    flat_polynomials = {}
    for family in sorted(active_families):
        for (fiber_power, residual_power, left_marker, right_marker), poly \
                in sorted(products[family].items()):
            flat_polynomials[(family, fiber_power, residual_power,
                              left_marker, right_marker)] = poly
    flat_radials = _radialize_tagged_targets(
        flat_polynomials,
        base_variables,
        r,
        params.delta,
        maximum_shift,
        precomputed={(): constant_radial},
    )
    family_radials: dict[
        Family,
        dict[tuple[int, int, int, int], RadialPoly],
    ] = defaultdict(dict)
    for tag, radial in flat_radials.items():
        family, fiber_power, residual_power, left_marker, right_marker = tag
        family_radials[family][(
            fiber_power, residual_power, left_marker, right_marker)] = radial

    packed_families = {}
    for family in sorted(active_families):
        left_affine = term_data[family[0]][1]
        right_affine = term_data[family[1]][1]
        expanded = _expand_aggregate_markers(
            family_radials[family], params.delta,
            left_affine, right_affine,
            r, base_variables - r)
        packed_families[family] = _pack_tagged_radials_by_shift(expanded)

    residual_affine = (
        Fraction(1) - r * params.delta,
        Fraction(-1),
        Fraction(-1),
    )
    for ordered_index, family, left_name, right_name, domain in jobs:
        if left_name == "cap" or right_name == "cap":
            fiber_affine = (large_x, Fraction(-1), Fraction(0))
        elif left_name == "total" or right_name == "total":
            fiber_affine = (total_bound, Fraction(-1), Fraction(-1))
        else:
            fiber_affine = ZERO_AFFINE
        contributions[ordered_index] = _integrate_tagged_radial_polynomials(
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


def compute_j_affine_tagged_batched(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: AffineMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> Fraction:
    """Evaluate Definition-5 J exactly with batched face radialization."""
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
            _compute_j_affine_face_batched, payload, params, active)
    return sum((
        _compute_j_affine_face_batched(payload, params, r)
        for r in active
    ), Fraction(0))


def compute_affine_tagged_batched(
    basis_terms: BasisTerms,
    params: Parameters,
    multipliers: AffineMultipliers,
    *,
    reverse_faces: bool = False,
    workers: int = 1,
) -> tuple[Fraction, Fraction]:
    """Return exact ``(I,kJ)`` using the unchanged I and batched exact J."""
    i_value = compute_i_affine_tagged(
        basis_terms, params, multipliers,
        reverse_faces=reverse_faces, workers=workers)
    j_value = compute_j_affine_tagged_batched(
        basis_terms, params, multipliers,
        reverse_faces=reverse_faces, workers=workers)
    return i_value, params.k * j_value


__all__ = [
    "compute_affine_tagged_batched",
    "compute_j_affine_tagged_batched",
]
