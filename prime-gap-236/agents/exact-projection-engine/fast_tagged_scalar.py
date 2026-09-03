#!/usr/bin/env python3
"""Exact scalar contraction for packed two-affine radial polynomials.

The reference backend expands the two affine powers afresh for every radial
coefficient.  Here coefficients are grouped by their two power tags, the
affine product is collected once per tag, and polygon moments are batched once
per inclusion--exclusion shift.  This is algebraically identical but avoids a
large repeated Cartesian product in theorem-sized cross shards.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
from math import comb, lcm
import time


Q0 = Q(0)
Q1 = Q(1)


def clear_family_denominators(families):
    """Clear one common exact denominator from every family coefficient."""
    denominator = 1
    count = 0
    for tagged in families.values():
        for polynomial in tagged.values():
            for coefficient in polynomial.values():
                coefficient = Q(coefficient)
                denominator = lcm(denominator, coefficient.denominator)
                count += 1
    integer_families = {}
    for family, tagged in families.items():
        integer_families[family] = {
            tag: {part: Q(coefficient).numerator *
                  (denominator // Q(coefficient).denominator)
                  for part, coefficient in polynomial.items()}
            for tag, polynomial in tagged.items()}
    return integer_families, denominator, {
        "family_coefficients": count,
        "common_denominator_bits": denominator.bit_length(),
    }


def radialize_integer_families(radial_backend, integer_families, *,
                               number_variables, number_large, delta,
                               maximum_shift):
    """Radialize using integer accumulation after one transform denominator.

    The reference path repeatedly normalizes large Fractions while summing
    different orbit contributions.  All orbit transforms here share an exact
    LCM denominator, so the same linear map is performed with Python integers
    and the denominator is restored only after scalar integration.
    """
    inverted = defaultdict(list)
    association_count = 0
    for family, tagged in integer_families.items():
        for tag, polynomial in tagged.items():
            for part, coefficient in polynomial.items():
                if coefficient:
                    inverted[part].append((family, tag, coefficient))
                    association_count += 1
    transforms = {}
    radial_denominator = 1
    transform_terms = 0
    for part in sorted(inverted):
        transform = {
            key: coefficient
            for key, coefficient in radial_backend._partition_face_radial(
                part, number_variables, number_large, delta).items()
            if key[0] <= maximum_shift and coefficient
        }
        transforms[part] = transform
        transform_terms += len(transform)
        for coefficient in transform.values():
            radial_denominator = lcm(
                radial_denominator, coefficient.denominator)
    accumulators = {
        family: {tag: defaultdict(int) for tag in tagged}
        for family, tagged in integer_families.items()}
    distributed_terms = 0
    for part in sorted(inverted):
        integer_transform = tuple(
            (key, coefficient.numerator *
             (radial_denominator // coefficient.denominator))
            for key, coefficient in transforms[part].items())
        for family, tag, coefficient in inverted[part]:
            destination = accumulators[family][tag]
            for key, radial_coefficient in integer_transform:
                destination[key] += coefficient * radial_coefficient
                distributed_terms += 1
    packed = {}
    output_terms = 0
    for family, tagged in accumulators.items():
        by_shift = defaultdict(list)
        for (first_power, second_power), radial in tagged.items():
            for (shift, x_power, y_power), coefficient in radial.items():
                if coefficient:
                    by_shift[shift].append((
                        first_power, second_power, x_power, y_power,
                        coefficient))
                    output_terms += 1
        packed[family] = {
            shift: tuple(terms) for shift, terms in by_shift.items()}
    return packed, radial_denominator, {
        "orbit_tag_associations": association_count,
        "orbit_transforms": len(transforms),
        "transform_terms": transform_terms,
        "radial_denominator_bits": radial_denominator.bit_length(),
        "distributed_terms": distributed_terms,
        "packed_nonzero_terms": output_terms,
    }


def _affine_product(radial_backend, first_power, second_power,
                    first_affine, second_affine):
    """Collect the product of two bivariate affine powers exactly."""
    f0, fx, fy = first_affine
    s0, sx, sy = second_affine
    # The important S-total/L-total case: both factors are polynomials in the
    # same linear form.  Collect in that one variable before expanding it into
    # X,Y, reducing a nominal product of two triangular maps to O(D^2).
    if (fx, fy) == (sx, sy):
        by_linear_power = defaultdict(Q)
        for i in range(first_power + 1):
            left = Q(comb(first_power, i)) * f0 ** (first_power - i)
            if not left:
                continue
            for j in range(second_power + 1):
                right = Q(comb(second_power, j)) * s0 ** (second_power - j)
                if right:
                    by_linear_power[i + j] += left * right
        answer = defaultdict(Q)
        for degree, coefficient in by_linear_power.items():
            for x_power in range(degree + 1):
                y_power = degree - x_power
                value = (coefficient * comb(degree, x_power) *
                         fx ** x_power * fy ** y_power)
                if value:
                    answer[(x_power, y_power)] += value
        return {key: value for key, value in answer.items() if value}

    first = radial_backend._affine_power_terms(
        first_power, f0, fx, fy)
    second = radial_backend._affine_power_terms(
        second_power, s0, sx, sy)
    answer = defaultdict(Q)
    for (ax, ay), left in first.items():
        for (bx, by), right in second.items():
            answer[(ax + bx, ay + by)] += left * right
    return {key: value for key, value in answer.items() if value}


def _domain_moments(radial_backend, requested, r, s, domain, shift):
    """Return all exact aggregate monomial moments for one shifted domain."""
    total_bound = domain.total_bound - shift
    y_lower = None if domain.y_lower is None else domain.y_lower - shift
    y_upper = None if domain.y_upper is None else domain.y_upper - shift
    total_lower = (None if domain.total_lower is None else
                   domain.total_lower - shift)
    zero = {key: Q0 for key in requested}
    if total_bound < 0 or (total_bound == 0 and r + s > 0):
        return zero
    if r == 0 and s == 0:
        valid = not (
            (domain.x_bound is not None and domain.x_bound < 0) or
            (y_lower is not None and y_lower >= 0) or
            (y_upper is not None and y_upper < 0) or
            (total_lower is not None and total_lower >= 0))
        return {key: (Q1 if valid and key == (0, 0) else Q0)
                for key in requested}
    if r == 0:
        if domain.x_bound is not None and domain.x_bound < 0:
            return zero
        lower = max(Q0, y_lower if y_lower is not None else Q0,
                    total_lower if total_lower is not None else Q0)
        upper = min(total_bound,
                    y_upper if y_upper is not None else total_bound)
        if upper <= lower:
            return zero
        return {
            (x_power, y_power): (
                Q0 if x_power else
                (upper ** (y_power + 1) - lower ** (y_power + 1)) /
                (y_power + 1))
            for x_power, y_power in requested}
    if s == 0:
        upper = min(total_bound, domain.x_bound) \
            if domain.x_bound is not None else total_bound
        if (upper <= 0 or (y_lower is not None and y_lower >= 0) or
                (y_upper is not None and y_upper < 0)):
            return zero
        lower = max(Q0, total_lower if total_lower is not None else Q0)
        if upper <= lower:
            return zero
        return {
            (x_power, y_power): (
                Q0 if y_power else
                (upper ** (x_power + 1) - lower ** (x_power + 1)) /
                (x_power + 1))
            for x_power, y_power in requested}
    polygon = radial_backend._shifted_polygon(
        total_bound, domain.x_bound, y_lower, y_upper, total_lower)
    return radial_backend._polygon_monomial_batch(polygon, requested)


def integrate_packed(radial_backend, packed_by_shift, *, r, s, delta,
                     domain, first_affine, second_affine):
    """Integrate a packed tagged radial family with exact global collection."""
    answer = Q0
    statistics = {
        "active_shifts": 0, "packed_terms": 0, "tag_groups": 0,
        "collected_affine_terms": 0, "requested_moments": 0,
        "scalar_products": 0,
    }
    f0, fx, fy = first_affine
    s0, sx, sy = second_affine
    for number_shifted in sorted(packed_by_shift):
        shift = number_shifted * delta
        total_bound = domain.total_bound - shift
        if total_bound < 0 or (total_bound == 0 and r + s > 0):
            continue
        grouped = defaultdict(list)
        for fp, sp, xp, yp, coefficient in packed_by_shift[number_shifted]:
            if (r == 0 and xp) or (s == 0 and yp):
                raise ArithmeticError("radial power on zero-dimensional aggregate")
            grouped[(fp, sp)].append((xp, yp, coefficient))
        affine_products = {}
        requested = set()
        for tag, radial_terms in grouped.items():
            fp, sp = tag
            affine = _affine_product(
                radial_backend, fp, sp,
                (f0 + fy * shift, fx, fy),
                (s0 + sy * shift, sx, sy))
            affine_products[tag] = affine
            for xp, yp, _ in radial_terms:
                requested.update((xp + ax, yp + ay)
                                 for ax, ay in affine)
        moments = _domain_moments(
            radial_backend, requested, r, s, domain, shift)
        for tag, radial_terms in grouped.items():
            affine = affine_products[tag]
            for xp, yp, coefficient in radial_terms:
                inner = sum(
                    (affine_coefficient * moments[(xp + ax, yp + ay)]
                     for (ax, ay), affine_coefficient in affine.items()),
                    Q0)
                answer += coefficient * inner
                statistics["scalar_products"] += len(affine)
        statistics["active_shifts"] += 1
        statistics["packed_terms"] += sum(map(len, grouped.values()))
        statistics["tag_groups"] += len(grouped)
        statistics["collected_affine_terms"] += sum(
            map(len, affine_products.values()))
        statistics["requested_moments"] += len(requested)
    return answer, statistics


def endpoint(engine, radial_backend, packed_families, *, k, alpha, alpha_f,
             eta, delta, schedule, common_r):
    jobs = engine.scheduled_cross_branch_jobs(
        radial_backend, k=k, alpha=alpha, eta=eta, delta=delta,
        schedule=schedule, common_r=common_r)
    second = (alpha_f - common_r * delta, -Q1, -Q1)
    values, statistics = {}, {}
    for branch, family, domain, first in jobs:
        value, stats = integrate_packed(
            radial_backend, packed_families[family], r=common_r,
            s=(k - 1) - common_r, delta=delta, domain=domain,
            first_affine=first, second_affine=second)
        values[branch] = value
        statistics[branch] = stats
    return sum(values.values(), Q0), values, statistics


def band_cross_r(engine, radial_backend, families, *, k, alpha_high,
                 alpha_low, alpha_f, eta, delta, schedule, common_r):
    """Exact fast ``k(J_high-J_low)`` for one common-large-count shard."""
    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return Q0, {"high": {}, "low": {}, "timing_seconds": {}}
    started = time.monotonic()
    maximum_shift = radial_backend._maximum_active_shift(cutoff, delta)
    packed = engine.radialize_tagged_families(
        radial_backend, families, number_variables=k - 1,
        number_large=common_r, delta=delta, maximum_shift=maximum_shift)
    radial_seconds = time.monotonic() - started
    stamp = time.monotonic()
    high, high_values, high_stats = endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_high,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    low, low_values, low_stats = endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_low,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    integration_seconds = time.monotonic() - stamp
    return k * (high - low), {
        "high": high_values, "low": low_values,
        "high_stats": high_stats, "low_stats": low_stats,
        "radial_shift_count": len(set().union(*(
            set(block) for block in packed.values()))) if packed else 0,
        "timing_seconds": {
            "radialize": radial_seconds,
            "integrate": integration_seconds,
        },
    }


def band_cross_r_integer(engine, radial_backend, families, *, k, alpha_high,
                         alpha_low, alpha_f, eta, delta, schedule, common_r):
    """Exact shard with common-denominator integer radial accumulation."""
    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return Q0, {"high": {}, "low": {}, "timing_seconds": {}}
    started = time.monotonic()
    integer_families, family_denominator, clear_stats = \
        clear_family_denominators(families)
    clear_seconds = time.monotonic() - started
    stamp = time.monotonic()
    maximum_shift = radial_backend._maximum_active_shift(cutoff, delta)
    packed, radial_denominator, radial_stats = radialize_integer_families(
        radial_backend, integer_families, number_variables=k - 1,
        number_large=common_r, delta=delta, maximum_shift=maximum_shift)
    radial_seconds = time.monotonic() - stamp
    common_denominator = family_denominator * radial_denominator
    stamp = time.monotonic()
    high_integer, high_values_integer, high_stats = endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_high,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    low_integer, low_values_integer, low_stats = endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_low,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    integration_seconds = time.monotonic() - stamp
    high = high_integer / common_denominator
    low = low_integer / common_denominator
    high_values = {
        branch: value / common_denominator
        for branch, value in high_values_integer.items()}
    low_values = {
        branch: value / common_denominator
        for branch, value in low_values_integer.items()}
    return k * (high - low), {
        "high": high_values, "low": low_values,
        "high_stats": high_stats, "low_stats": low_stats,
        "integer_radialization": {
            "family_denominator": str(family_denominator),
            "radial_denominator": str(radial_denominator),
            "combined_denominator_bits": common_denominator.bit_length(),
            "clear_stats": clear_stats,
            "radial_stats": radial_stats,
        },
        "timing_seconds": {
            "clear_family_denominators": clear_seconds,
            "radialize_integer": radial_seconds,
            "integrate_collected_affines": integration_seconds,
        },
    }
