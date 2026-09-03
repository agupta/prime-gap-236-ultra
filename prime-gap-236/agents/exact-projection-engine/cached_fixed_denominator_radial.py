#!/usr/bin/env python3
"""Cached-cost variant of the exact direct-integer radial transform.

The mathematical transform is the frozen fixed-v6 transform.  This version
hoists factorial tables, factorial-denominator ratios, and powers of the
rational cap denominator out of the innermost partition-split loops.  It is
kept separate so no running or audited v6 byte is changed.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction as Q
from functools import lru_cache
from itertools import product
import math
import time


Q0 = Q(0)


@lru_cache(maxsize=None)
def _factorials_through(ceiling):
    values = [1]
    for value in range(1, ceiling + 1):
        values.append(values[-1] * value)
    return tuple(values)


@lru_cache(maxsize=None)
def _factorial_ratio(ceiling, x_power, y_power):
    factorials = _factorials_through(ceiling)
    denominator = factorials[x_power] * factorials[y_power]
    if factorials[ceiling] % denominator:
        raise ArithmeticError("factorial ceiling failed to clear")
    return factorials[ceiling] // denominator


@lru_cache(maxsize=None)
def _delta_scales(delta_numerator, delta_denominator, maximum_degree,
                  total_degree):
    return tuple(
        delta_numerator ** (total_degree - selected_degree) *
        delta_denominator ** (
            maximum_degree - total_degree + selected_degree)
        for selected_degree in range(total_degree + 1))


def partition_face_scaled_integer(radial_backend, part, number_variables,
                                  number_large, delta, maximum_shift, *,
                                  maximum_degree, factorial_ceiling,
                                  common_denominator):
    fixed = globals().get("FIXED_V6")
    if fixed is None:
        raise RuntimeError("FIXED_V6 backend was not bound")
    if not 0 <= number_large <= number_variables:
        raise ValueError("face index outside variable range")
    if (type(maximum_degree) is not int or maximum_degree < sum(part) or
            type(factorial_ceiling) is not int or factorial_ceiling < 0 or
            type(common_denominator) is not int or common_denominator <= 0):
        raise ValueError("invalid fixed-denominator parameters")
    if maximum_shift < 0 or len(part) > number_variables:
        return {}
    delta = Q(delta)
    if delta <= 0:
        raise ValueError("delta must be positive")
    delta_numerator = delta.numerator
    delta_denominator = delta.denominator
    total_degree = sum(part)
    factorial_top = _factorials_through(factorial_ceiling)[factorial_ceiling]
    expected_denominator = (
        delta_denominator ** maximum_degree * factorial_top)
    if common_denominator != expected_denominator:
        raise ArithmeticError("fixed transform denominator mismatch")
    delta_scales = _delta_scales(
        delta_numerator, delta_denominator, maximum_degree, total_degree)

    ell = len(part)
    groups = sorted(Counter(part).items(), reverse=True)
    orbit_multiplier = radial_backend.orbit_size(number_variables, part)
    number_small = number_variables - number_large
    answer = defaultdict(int)
    for selected_counts in product(*(range(count + 1)
                                     for _, count in groups)):
        marked_large = sum(selected_counts)
        zero_large = number_large - marked_large
        zero_small = number_variables - ell - zero_large
        if zero_large < 0 or zero_small < 0:
            continue
        multiplicity = math.comb(number_variables - ell, zero_large)
        large_positive, small_positive = [], []
        for (exponent, count), selected in zip(
                groups, selected_counts, strict=True):
            multiplicity *= math.comb(count, selected)
            large_positive.extend([exponent] * selected)
            small_positive.extend([exponent] * (count - selected))
        large_positive = tuple(sorted(large_positive, reverse=True))
        small_positive = tuple(sorted(small_positive, reverse=True))
        large = (fixed._large_falling_numerators(large_positive)
                 if number_large else {0: 1})
        small = (fixed._small_falling_numerators(
            small_positive, zero_small, maximum_shift)
                 if number_small else {(0, 0): 1})
        orbit_scale = orbit_multiplier * multiplicity
        for large_degree, large_coefficient in large.items():
            x_power = (large_degree + number_large - 1
                       if number_large else 0)
            for (shift, small_degree), small_coefficient in small.items():
                y_power = (small_degree + number_small - 1
                           if number_small else 0)
                selected_degree = large_degree + small_degree
                if selected_degree > total_degree:
                    raise ArithmeticError("falling degree exceeds orbit degree")
                answer[(shift, x_power, y_power)] += (
                    orbit_scale * large_coefficient * small_coefficient *
                    delta_scales[selected_degree] *
                    _factorial_ratio(
                        factorial_ceiling, x_power, y_power))
    return {key: value for key, value in answer.items() if value}


def radialize_integer_families_fixed(
        radial_backend, integer_families, *, number_variables,
        number_large, delta, maximum_shift):
    inverted = defaultdict(list)
    associations = 0
    for family, tagged in integer_families.items():
        for tag, polynomial in tagged.items():
            for part, coefficient in polynomial.items():
                if type(coefficient) is not int:
                    raise TypeError("fixed radialization requires integer families")
                if coefficient:
                    inverted[part].append((family, tag, coefficient))
                    associations += 1
    maximum_degree = max((sum(part) for part in inverted), default=0)
    factorial_ceiling = max(0, maximum_degree + number_variables - 1)
    delta = Q(delta)
    factorial_top = _factorials_through(factorial_ceiling)[factorial_ceiling]
    provisional_denominator = (
        delta.denominator ** maximum_degree * factorial_top)
    transforms = {}
    common_gcd = provisional_denominator
    for part in sorted(inverted):
        transform = partition_face_scaled_integer(
            radial_backend, part, number_variables, number_large, delta,
            maximum_shift, maximum_degree=maximum_degree,
            factorial_ceiling=factorial_ceiling,
            common_denominator=provisional_denominator)
        transforms[part] = transform
        for coefficient in transform.values():
            common_gcd = math.gcd(common_gcd, abs(coefficient))
    radial_denominator = provisional_denominator // common_gcd

    accumulators = {
        family: {tag: defaultdict(int) for tag in tagged}
        for family, tagged in integer_families.items()}
    distributed = 0
    transform_terms = 0
    for part in sorted(inverted):
        if any(coefficient % common_gcd
               for coefficient in transforms[part].values()):
            raise ArithmeticError("global transform gcd does not divide numerator")
        transform = tuple(
            (key, coefficient // common_gcd)
            for key, coefficient in transforms[part].items())
        transform_terms += len(transform)
        for family, tag, coefficient in inverted[part]:
            destination = accumulators[family][tag]
            for key, radial_coefficient in transform:
                destination[key] += coefficient * radial_coefficient
                distributed += 1
    packed, output_terms = {}, 0
    for family, tagged in accumulators.items():
        by_shift = defaultdict(list)
        for (first_power, second_power), radial in tagged.items():
            for (shift, x_power, y_power), coefficient in radial.items():
                if coefficient:
                    by_shift[shift].append((
                        first_power, second_power, x_power, y_power,
                        coefficient))
                    output_terms += 1
        packed[family] = {shift: tuple(terms)
                          for shift, terms in by_shift.items()}
    return packed, radial_denominator, {
        "orbit_tag_associations": associations,
        "orbit_transforms": len(transforms),
        "transform_terms": transform_terms,
        "radial_denominator_bits": radial_denominator.bit_length(),
        "distributed_terms": distributed,
        "packed_nonzero_terms": output_terms,
        "maximum_shift_pruned_inside_convolution": maximum_shift,
        "fixed_provisional_denominator_bits":
            provisional_denominator.bit_length(),
        "fixed_denominator_common_gcd_bits": common_gcd.bit_length(),
        "maximum_orbit_degree": maximum_degree,
        "factorial_ceiling": factorial_ceiling,
        "cached_factorial_ratios": _factorial_ratio.cache_info().currsize,
        "cached_delta_scale_tables": _delta_scales.cache_info().currsize,
    }


def band_cross_r_integer(engine, radial_backend, families, *, k, alpha_high,
                         alpha_low, alpha_f, eta, delta, schedule, common_r):
    fast = globals().get("FAST_V2")
    collected = globals().get("COLLECTED_V5")
    if fast is None or collected is None:
        raise RuntimeError("FAST_V2 and COLLECTED_V5 must be bound")
    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return Q0, {"high": {}, "low": {}, "timing_seconds": {}}
    jobs = [
        *engine.scheduled_cross_branch_jobs(
            radial_backend, k=k, alpha=alpha_high, eta=eta, delta=delta,
            schedule=schedule, common_r=common_r),
        *engine.scheduled_cross_branch_jobs(
            radial_backend, k=k, alpha=alpha_low, eta=eta, delta=delta,
            schedule=schedule, common_r=common_r)]
    active_families = {family for _, family, _, _ in jobs}
    missing = active_families - set(families)
    if missing:
        raise KeyError(f"active branch families are absent: {sorted(missing)}")
    filtered_families = {
        family: tagged for family, tagged in families.items()
        if family in active_families}
    started = time.monotonic()
    integer_families, family_denominator, clear_stats = \
        fast.clear_family_denominators(filtered_families)
    clear_seconds = time.monotonic() - started
    maximum_shift = radial_backend._maximum_active_shift(cutoff, delta)
    stamp = time.monotonic()
    packed, radial_denominator, radial_stats = \
        radialize_integer_families_fixed(
            radial_backend, integer_families, number_variables=k - 1,
            number_large=common_r, delta=delta,
            maximum_shift=maximum_shift)
    radial_seconds = time.monotonic() - stamp
    common_denominator = family_denominator * radial_denominator
    stamp = time.monotonic()
    high_integer, high_values_integer, high_stats = collected.endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_high,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    low_integer, low_values_integer, low_stats = collected.endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_low,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    integration_seconds = time.monotonic() - stamp
    high, low = (high_integer / common_denominator,
                 low_integer / common_denominator)
    return k * (high - low), {
        "high": {key: value / common_denominator
                 for key, value in high_values_integer.items()},
        "low": {key: value / common_denominator
                for key, value in low_values_integer.items()},
        "high_stats": high_stats, "low_stats": low_stats,
        "integer_radialization": {
            "family_denominator": str(family_denominator),
            "radial_denominator": str(radial_denominator),
            "combined_denominator_bits": common_denominator.bit_length(),
            "clear_stats": clear_stats, "radial_stats": radial_stats,
            "active_branch_families": sorted(active_families),
            "inactive_families_pruned_before_radialization": sorted(
                set(families) - active_families),
        },
        "timing_seconds": {
            "clear_family_denominators": clear_seconds,
            "radialize_cached_fixed_denominator_integers": radial_seconds,
            "integrate_globally_collected_integers": integration_seconds,
        },
    }
