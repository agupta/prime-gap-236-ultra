#!/usr/bin/env python3
"""Independent small-k exact oracle for per-stratum affine multipliers.

For a symmetric polynomial ``F0`` and

    R = #{i: t_i > delta},
    L = sum_{t_i > delta} t_i,
    Z = sum_{t_i <= delta} t_i,

this module evaluates ``F=F0*(a_R+b_R*L+c_R*Z)``.  It deliberately uses the
literal expanded-polynomial backend of ``exact_capped_certificate`` and all
16 *ordered* distinguished-fiber branch pairs.  It is a low-dimensional
oracle and readiness scaffold, not the eventual D12 production backend.
"""

from __future__ import annotations

import math
from collections import defaultdict
from fractions import Fraction as Q
from pathlib import Path
from typing import Mapping, Sequence

from verify.exact_capped_certificate import (
    AggregateDomain,
    Parameters,
    Partition,
    Point,
    RadialPoly,
    SymPoly,
    _affine_power_terms,
    _maximum_active_shift,
    _polygon_monomial_batch,
    _radialize_symmetric_polynomial,
    _shifted_polygon,
    distinguish_last_variable,
    poly_add_term,
    poly_multiply,
)


Affine = tuple[Q, Q, Q]
MultiplierMap = Mapping[int, Affine]
QUADRATIC_POWERS = ((0, 0), (1, 0), (0, 1),
                    (2, 0), (1, 1), (0, 2))


def _multiply_xy(left, right):
    answer = defaultdict(Q)
    for (a, b), c in left.items():
        for (d, e), f in right.items():
            answer[(a + d, b + e)] += c * f
    return {key: value for key, value in answer.items() if value}


def _integrate_radial_with_affines(
    radial: RadialPoly,
    r: int,
    s: int,
    delta: Q,
    domain: AggregateDomain,
    factors: Sequence[tuple[int, Affine]],
) -> Q:
    """Integrate a face radial polynomial times arbitrary affine powers.

    The inclusion-exclusion shift is applied independently to every affine's
    Y constant.  This is a separate multi-affine expansion from the
    two-tagged-affine production helper.
    """
    by_shift = defaultdict(lambda: defaultdict(Q))
    for (number_shifted, x_power, y_power), coefficient in radial.items():
        by_shift[number_shifted][(x_power, y_power)] += coefficient

    answer = Q(0)
    for number_shifted in sorted(by_shift):
        shift = number_shifted * delta
        total_bound = domain.total_bound - shift
        if total_bound < 0 or (total_bound == 0 and r + s > 0):
            continue
        y_lower = None if domain.y_lower is None else domain.y_lower - shift
        y_upper = None if domain.y_upper is None else domain.y_upper - shift
        total_lower = (None if domain.total_lower is None
                       else domain.total_lower - shift)

        affine_expansion = {(0, 0): Q(1)}
        for power, (q0, qx, qy) in factors:
            affine_expansion = _multiply_xy(
                affine_expansion,
                _affine_power_terms(power, q0 + qy * shift, qx, qy),
            )
        moments = defaultdict(Q)
        for (x_power, y_power), coefficient in by_shift[number_shifted].items():
            for (add_x, add_y), factor in affine_expansion.items():
                moments[(x_power + add_x, y_power + add_y)] += coefficient * factor
        moments = {key: value for key, value in moments.items() if value}
        if not moments:
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
            answer += moments.get((0, 0), Q(0))
            continue
        if r == 0:
            if domain.x_bound is not None and domain.x_bound < 0:
                continue
            lower = max(Q(0), y_lower or Q(0), total_lower or Q(0))
            upper = min(total_bound,
                        y_upper if y_upper is not None else total_bound)
            if upper <= lower:
                continue
            for (x_power, y_power), coefficient in moments.items():
                if x_power:
                    continue
                answer += coefficient * (
                    upper ** (y_power + 1) - lower ** (y_power + 1)
                ) / (y_power + 1)
            continue
        if s == 0:
            upper = min(total_bound,
                        domain.x_bound if domain.x_bound is not None
                        else total_bound)
            if upper <= 0 or (y_lower is not None and y_lower >= 0) or \
                    (y_upper is not None and y_upper < 0):
                continue
            lower = max(Q(0), total_lower or Q(0))
            if upper <= lower:
                continue
            for (x_power, y_power), coefficient in moments.items():
                if y_power:
                    continue
                answer += coefficient * (
                    upper ** (x_power + 1) - lower ** (x_power + 1)
                ) / (x_power + 1)
            continue

        polygon = _shifted_polygon(
            total_bound, domain.x_bound, y_lower, y_upper, total_lower)
        if len(polygon) < 3:
            continue
        polygon_moments = _polygon_monomial_batch(polygon, moments)
        answer += sum((coefficient * polygon_moments[power]
                       for power, coefficient in moments.items()), Q(0))
    return answer


def _marginal_moment_polynomials(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    moment: int,
) -> tuple[SymPoly, dict[int, SymPoly]]:
    """Return small/large families for integral t^moment F0(u,t) dt."""
    if moment < 0:
        raise ValueError("negative fiber moment")
    distinguished = distinguish_last_variable(polynomial, params.k - 1)
    small: SymPoly = {}
    large: dict[int, SymPoly] = defaultdict(dict)
    for t_power, base_poly in distinguished.items():
        endpoint_power = t_power + moment + 1
        for part, coefficient in base_poly.items():
            poly_add_term(
                small, part,
                coefficient * params.delta ** endpoint_power / endpoint_power)
        for fiber_power in range(1, endpoint_power + 1):
            factor = (Q(math.comb(endpoint_power, fiber_power), endpoint_power)
                      * params.delta ** (endpoint_power - fiber_power))
            for part, coefficient in base_poly.items():
                poly_add_term(large[fiber_power], part, coefficient * factor)
    return small, {power: poly for power, poly in large.items() if poly}


def _scale_poly(poly, factor):
    return {part: factor * value for part, value in poly.items()
            if factor * value}


def _weighted_marginal_terms(
    branch: str,
    r: int,
    small_zero: SymPoly,
    large_zero: Mapping[int, SymPoly],
    small_one: SymPoly,
    large_one: Mapping[int, SymPoly],
    multipliers: MultiplierMap,
) -> list[tuple[int, SymPoly, Affine | None]]:
    small_branch = branch in ("small_delta", "small_total")
    total_r = r if small_branch else r + 1
    a, b, c = multipliers.get(total_r, (Q(0), Q(0), Q(0)))
    aggregate_affine = (a + b * r * _weighted_marginal_terms.delta,
                        b, c)
    zero_family = {0: small_zero} if small_branch else large_zero
    one_family = {0: small_one} if small_branch else large_one
    shifted_coefficient = c if small_branch else b
    answer = []
    for fiber_power, poly in zero_family.items():
        if poly and any(aggregate_affine):
            answer.append((fiber_power, poly, aggregate_affine))
    if shifted_coefficient:
        for fiber_power, poly in one_family.items():
            scaled = _scale_poly(poly, shifted_coefficient)
            if scaled:
                answer.append((fiber_power, scaled, None))
    return answer


# Set only for the duration of one public call, avoiding a long argument list
# in the deliberately small internal branch helper.
_weighted_marginal_terms.delta = Q(0)


def compute_i_affine_literal(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    multipliers: MultiplierMap,
) -> Q:
    squared = poly_multiply(polynomial, polynomial, params.k)
    answer = Q(0)
    for r in range(params.k + 1):
        total_bound = params.alpha - r * params.delta
        if total_bound <= 0:
            continue
        x_bound = None if r == 0 else params.beta(r) - r * params.delta
        if x_bound is not None and x_bound <= 0:
            continue
        a, b, c = multipliers.get(r, (Q(0), Q(0), Q(0)))
        radial = _radialize_symmetric_polynomial(
            squared, params.k, r, params.delta,
            maximum_shift=_maximum_active_shift(total_bound, params.delta))
        answer += _integrate_radial_with_affines(
            radial, r, params.k - r, params.delta,
            AggregateDomain(total_bound=total_bound, x_bound=x_bound),
            [(2, (a + b * r * params.delta, b, c))])
    return answer


def compute_j_affine_literal(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    multipliers: MultiplierMap,
) -> Q:
    """Definition-5 J for the affine-multiplied polynomial, for small k."""
    if params.alpha - params.eta != params.delta:
        raise ValueError("ordered affine oracle requires alpha-eta=delta")
    if params.k > 4:
        raise ValueError("literal affine oracle is restricted to k<=4")
    base_variables = params.k - 1
    small_zero, large_zero = _marginal_moment_polynomials(
        polynomial, params, 0)
    small_one, large_one = _marginal_moment_polynomials(
        polynomial, params, 1)
    _weighted_marginal_terms.delta = params.delta
    branches = ("small_delta", "small_total", "cap", "total")
    answer = Q(0)
    for r in range(base_variables + 1):
        total_bound = params.eta - r * params.delta
        if total_bound <= 0:
            continue
        small_x = None if r == 0 else params.beta(r) - r * params.delta
        large_x = params.beta(r + 1) - (r + 1) * params.delta
        threshold = params.eta - params.beta(r + 1) + params.delta
        branch_data = {
            "small_delta": (small_x, None, None, None),
            "small_total": (small_x, None, None, total_bound),
            "cap": (large_x, None, threshold, None),
            "total": (large_x, threshold, None, None),
        }
        constant_radial = _radialize_symmetric_polynomial(
            {(): Q(1)}, base_variables, r, params.delta,
            maximum_shift=_maximum_active_shift(total_bound, params.delta))
        terms = {branch: _weighted_marginal_terms(
            branch, r, small_zero, large_zero, small_one, large_one,
            multipliers) for branch in branches}
        for left in branches:
            for right in branches:  # deliberately ordered; no implicit 2
                lx, ll, lu, lt = branch_data[left]
                rx, rl, ru, rt = branch_data[right]
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
                boundary = ("small_total" in (left, right) or
                            {left, right} == {"cap", "total"})
                if boundary:
                    volume = _integrate_radial_with_affines(
                        constant_radial, r, base_variables - r,
                        params.delta, domain, [])
                    if volume:
                        raise ArithmeticError(
                            "nominal boundary branches have positive measure")
                    continue
                active_large = (left if left in ("cap", "total")
                                else right if right in ("cap", "total")
                                else None)
                if active_large == "cap":
                    fiber_affine = (large_x, Q(-1), Q(0))
                elif active_large == "total":
                    fiber_affine = (total_bound, Q(-1), Q(-1))
                else:
                    fiber_affine = (Q(0), Q(0), Q(0))
                for lp, lpoly, laffine in terms[left]:
                    for rp, rpoly, raffine in terms[right]:
                        product_poly = poly_multiply(
                            lpoly, rpoly, base_variables)
                        radial = _radialize_symmetric_polynomial(
                            product_poly, base_variables, r, params.delta,
                            maximum_shift=_maximum_active_shift(
                                total_bound, params.delta))
                        factors = []
                        if lp + rp:
                            factors.append((lp + rp, fiber_affine))
                        if laffine is not None:
                            factors.append((1, laffine))
                        if raffine is not None:
                            factors.append((1, raffine))
                        answer += _integrate_radial_with_affines(
                            radial, r, base_variables - r, params.delta,
                            domain, factors)
    return answer


def compute_affine_literal(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    multipliers: MultiplierMap,
) -> tuple[Q, Q]:
    """Return ``(I, kJ)`` exactly."""
    i_value = compute_i_affine_literal(polynomial, params, multipliers)
    return i_value, params.k * compute_j_affine_literal(
        polynomial, params, multipliers)


def _quadratic_branch_terms(
    branch: str,
    r: int,
    moment_families,
    multipliers: Mapping[int, Sequence[Q]],
    delta: Q,
):
    """Expand a degree-two multiplier before its fiber integral."""
    small_branch = branch in ("small_delta", "small_total")
    total_r = r if small_branch else r + 1
    coefficients = tuple(multipliers.get(total_r, (Q(0),) * 6))
    if len(coefficients) != 6:
        raise ValueError("quadratic multiplier needs six channels per stratum")
    answer = []
    for coefficient, (l_power, z_power) in zip(
            coefficients, QUADRATIC_POWERS):
        if not coefficient:
            continue
        maximum_moment = z_power if small_branch else l_power
        for moment in range(maximum_moment + 1):
            factor = coefficient * math.comb(maximum_moment, moment)
            remaining_l = l_power - (moment if not small_branch else 0)
            remaining_z = z_power - (moment if small_branch else 0)
            small, large = moment_families[moment]
            family = {0: small} if small_branch else large
            for fiber_power, poly in family.items():
                scaled = _scale_poly(poly, factor)
                if scaled:
                    answer.append((fiber_power, scaled,
                                   remaining_l, remaining_z))
    return answer


def compute_i_quadratic_literal(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    multipliers: Mapping[int, Sequence[Q]],
) -> Q:
    squared = poly_multiply(polynomial, polynomial, params.k)
    answer = Q(0)
    for r in range(params.k + 1):
        total_bound = params.alpha - r * params.delta
        if total_bound <= 0:
            continue
        x_bound = None if r == 0 else params.beta(r) - r * params.delta
        if x_bound is not None and x_bound <= 0:
            continue
        coefficients = tuple(multipliers.get(r, (Q(0),) * 6))
        if len(coefficients) != 6:
            raise ValueError("quadratic multiplier needs six channels per stratum")
        radial = _radialize_symmetric_polynomial(
            squared, params.k, r, params.delta,
            maximum_shift=_maximum_active_shift(total_bound, params.delta))
        l_affine = (r * params.delta, Q(1), Q(0))
        z_affine = (Q(0), Q(0), Q(1))
        for left, (la, za) in zip(coefficients, QUADRATIC_POWERS):
            for right, (lb, zb) in zip(coefficients, QUADRATIC_POWERS):
                scale = left * right
                if not scale:
                    continue
                scaled_radial = {key: scale * value
                                 for key, value in radial.items()}
                factors = []
                if la + lb:
                    factors.append((la + lb, l_affine))
                if za + zb:
                    factors.append((za + zb, z_affine))
                answer += _integrate_radial_with_affines(
                    scaled_radial, r, params.k - r, params.delta,
                    AggregateDomain(total_bound=total_bound,
                                    x_bound=x_bound), factors)
    return answer


def compute_j_quadratic_literal(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    multipliers: Mapping[int, Sequence[Q]],
) -> Q:
    if params.alpha - params.eta != params.delta:
        raise ValueError("ordered quadratic oracle requires alpha-eta=delta")
    if params.k > 4:
        raise ValueError("literal quadratic oracle is restricted to k<=4")
    base_variables = params.k - 1
    moment_families = {
        moment: _marginal_moment_polynomials(polynomial, params, moment)
        for moment in range(3)
    }
    branches = ("small_delta", "small_total", "cap", "total")
    answer = Q(0)
    for r in range(base_variables + 1):
        total_bound = params.eta - r * params.delta
        if total_bound <= 0:
            continue
        small_x = None if r == 0 else params.beta(r) - r * params.delta
        large_x = params.beta(r + 1) - (r + 1) * params.delta
        threshold = params.eta - params.beta(r + 1) + params.delta
        branch_data = {
            "small_delta": (small_x, None, None, None),
            "small_total": (small_x, None, None, total_bound),
            "cap": (large_x, None, threshold, None),
            "total": (large_x, threshold, None, None),
        }
        constant_radial = _radialize_symmetric_polynomial(
            {(): Q(1)}, base_variables, r, params.delta,
            maximum_shift=_maximum_active_shift(total_bound, params.delta))
        terms = {branch: _quadratic_branch_terms(
            branch, r, moment_families, multipliers, params.delta)
                 for branch in branches}
        l_affine = (r * params.delta, Q(1), Q(0))
        z_affine = (Q(0), Q(0), Q(1))
        for left in branches:
            for right in branches:
                lx, ll, lu, lt = branch_data[left]
                rx, rl, ru, rt = branch_data[right]
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
                boundary = ("small_total" in (left, right) or
                            {left, right} == {"cap", "total"})
                if boundary:
                    if _integrate_radial_with_affines(
                            constant_radial, r, base_variables - r,
                            params.delta, domain, []):
                        raise ArithmeticError(
                            "nominal boundary branches have positive measure")
                    continue
                active_large = (left if left in ("cap", "total")
                                else right if right in ("cap", "total")
                                else None)
                if active_large == "cap":
                    fiber_affine = (large_x, Q(-1), Q(0))
                elif active_large == "total":
                    fiber_affine = (total_bound, Q(-1), Q(-1))
                else:
                    fiber_affine = (Q(0), Q(0), Q(0))
                for lp, lpoly, llp, lzp in terms[left]:
                    for rp, rpoly, rlp, rzp in terms[right]:
                        product_poly = poly_multiply(
                            lpoly, rpoly, base_variables)
                        radial = _radialize_symmetric_polynomial(
                            product_poly, base_variables, r, params.delta,
                            maximum_shift=_maximum_active_shift(
                                total_bound, params.delta))
                        factors = []
                        if lp + rp:
                            factors.append((lp + rp, fiber_affine))
                        if llp + rlp:
                            factors.append((llp + rlp, l_affine))
                        if lzp + rzp:
                            factors.append((lzp + rzp, z_affine))
                        answer += _integrate_radial_with_affines(
                            radial, r, base_variables - r, params.delta,
                            domain, factors)
    return answer


def compute_quadratic_literal(
    polynomial: Mapping[Partition, Q],
    params: Parameters,
    multipliers: Mapping[int, Sequence[Q]],
) -> tuple[Q, Q]:
    i_value = compute_i_quadratic_literal(polynomial, params, multipliers)
    return i_value, params.k * compute_j_quadratic_literal(
        polynomial, params, multipliers)
