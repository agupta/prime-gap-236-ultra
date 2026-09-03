#!/usr/bin/env python3
"""Direct integer partition-radial transform under one proved denominator.

For rational ``delta=a/q`` and maximum orbit degree ``E``, every large/small
simplex radial coefficient has denominator dividing

    q**E * factorial(E + number_variables - 1).

This module constructs the numerator under that denominator directly from
falling factorial convolutions.  A final global gcd reduces it to the exact
minimal common denominator before family distribution.  It therefore avoids
building and repeatedly normalizing Fraction objects in the expensive
partition split, without changing any coefficient.
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
def _large_falling_numerators(positive_exponents):
    terms = {0: 1}
    for exponent in positive_exponents:
        following = defaultdict(int)
        falling = 1
        for power in range(exponent + 1):
            if power:
                falling *= exponent - power + 1
            for old_degree, old_coefficient in terms.items():
                following[old_degree + power] += old_coefficient * falling
        terms = {key: value for key, value in following.items() if value}
    return terms


@lru_cache(maxsize=None)
def _small_falling_numerators(positive_exponents, zero_count,
                              maximum_shift):
    terms = {(0, 0): 1}
    for exponent in positive_exponents:
        choices = [(0, exponent, math.factorial(exponent))]
        falling = 1
        for power in range(exponent + 1):
            if power:
                falling *= exponent - power + 1
            choices.append((1, power, -falling))
        following = defaultdict(int)
        for (old_shift, old_degree), old_coefficient in terms.items():
            for add_shift, add_degree, add_coefficient in choices:
                shift = old_shift + add_shift
                if shift <= maximum_shift:
                    following[(shift, old_degree + add_degree)] += (
                        old_coefficient * add_coefficient)
        terms = {key: value for key, value in following.items() if value}
    answer = defaultdict(int)
    for (positive_shift, degree), coefficient in terms.items():
        for shifted_zeros in range(
                min(zero_count, maximum_shift - positive_shift) + 1):
            answer[(positive_shift + shifted_zeros, degree)] += (
                coefficient * (-1) ** shifted_zeros *
                math.comb(zero_count, shifted_zeros))
    return {key: value for key, value in answer.items() if value}


def partition_face_scaled_integer(radial_backend, part, number_variables,
                                  number_large, delta, maximum_shift, *,
                                  maximum_degree, factorial_ceiling,
                                  common_denominator):
    """Return ``common_denominator * reference_transform(part)`` as ints."""
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
    factorial_top = math.factorial(factorial_ceiling)
    expected_denominator = (
        delta_denominator ** maximum_degree * factorial_top)
    if common_denominator != expected_denominator:
        raise ArithmeticError("fixed transform denominator mismatch")

    ell = len(part)
    groups = sorted(Counter(part).items(), reverse=True)
    orbit_multiplier = radial_backend.orbit_size(number_variables, part)
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
        large = (_large_falling_numerators(large_positive)
                 if number_large else {0: 1})
        number_small = number_variables - number_large
        small = (_small_falling_numerators(
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
                factorial_product = (
                    math.factorial(x_power) * math.factorial(y_power))
                if factorial_top % factorial_product:
                    raise ArithmeticError("factorial ceiling failed to clear")
                delta_scale = (
                    delta_numerator ** (total_degree - selected_degree) *
                    delta_denominator ** (
                        maximum_degree - total_degree + selected_degree))
                answer[(shift, x_power, y_power)] += (
                    orbit_scale * large_coefficient * small_coefficient *
                    delta_scale * (factorial_top // factorial_product))
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
    # For either aggregate dimension zero, x_power+y_power can reach
    # maximum_degree+n-1; with both positive it is one lower.  The uniform
    # ceiling is deliberately conservative and valid for every stratum.
    factorial_ceiling = max(0, maximum_degree + number_variables - 1)
    delta = Q(delta)
    provisional_denominator = (
        delta.denominator ** maximum_degree *
        math.factorial(factorial_ceiling))
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
    high_jobs = engine.scheduled_cross_branch_jobs(
        radial_backend, k=k, alpha=alpha_high, eta=eta, delta=delta,
        schedule=schedule, common_r=common_r)
    low_jobs = engine.scheduled_cross_branch_jobs(
        radial_backend, k=k, alpha=alpha_low, eta=eta, delta=delta,
        schedule=schedule, common_r=common_r)
    active_families = {
        family for jobs in (high_jobs, low_jobs)
        for _, family, _, _ in jobs}
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
            "radialize_fixed_denominator_integers": radial_seconds,
            "integrate_globally_collected_integers": integration_seconds,
        },
    }
