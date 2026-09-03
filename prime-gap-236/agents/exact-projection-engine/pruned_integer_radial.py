#!/usr/bin/env python3
"""Exact maximum-shift-pruned integer radialization.

Inclusion--exclusion shifts above ``floor((eta-r*delta)/delta)`` have empty
support.  The reference transform constructs them and discards them only
afterwards.  This module applies that mathematically exact zero test inside
the small-coordinate convolution, which is especially important near the
largest active common count.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction as Q
from functools import lru_cache
import math
from itertools import product
import time


Q0 = Q(0)
Q1 = Q(1)


@lru_cache(maxsize=16_384)
def _small_radial_pruned(exponents, delta, maximum_shift):
    s = len(exponents)
    if s == 0:
        return {(0, 0): Q1}
    positive = [value for value in exponents if value]
    zero_count = s - len(positive)
    terms = {(0, 0): Q1}
    for original in positive:
        choices = [(0, original, Q(math.factorial(original)))]
        choices.extend(
            (1, new_power,
             Q(-math.comb(original, new_power)) *
             delta ** (original - new_power) * math.factorial(new_power))
            for new_power in range(original + 1))
        following = defaultdict(Q)
        for (old_shift, old_degree), old_coefficient in terms.items():
            for add_shift, add_degree, add_coefficient in choices:
                shift = old_shift + add_shift
                if shift <= maximum_shift:
                    following[(shift, old_degree + add_degree)] += (
                        old_coefficient * add_coefficient)
        terms = {key: value for key, value in following.items() if value}
    answer = defaultdict(Q)
    for (positive_shift, total_degree), coefficient in terms.items():
        radial_power = total_degree + s - 1
        coefficient /= math.factorial(radial_power)
        for shifted_zeros in range(
                min(zero_count, maximum_shift - positive_shift) + 1):
            shift = positive_shift + shifted_zeros
            answer[(shift, radial_power)] += (
                coefficient * (-1) ** shifted_zeros *
                math.comb(zero_count, shifted_zeros))
    return {key: value for key, value in answer.items() if value}


def partition_face_radial_pruned(radial_backend, part, number_variables,
                                 number_large, delta, maximum_shift):
    if not 0 <= number_large <= number_variables:
        raise ValueError("face index outside variable range")
    if maximum_shift < 0 or len(part) > number_variables:
        return {}
    ell = len(part)
    groups = sorted(Counter(part).items(), reverse=True)
    orbit_multiplier = radial_backend.orbit_size(number_variables, part)
    answer = defaultdict(Q)
    for selected_counts in product(*(range(count + 1)
                                     for _, count in groups)):
        marked_large = sum(selected_counts)
        zero_large = number_large - marked_large
        zero_small = number_variables - ell - zero_large
        if zero_large < 0 or zero_small < 0:
            continue
        multiplicity = math.comb(number_variables - ell, zero_large)
        large_exponents, small_exponents = [], []
        for (exponent, count), selected in zip(
                groups, selected_counts, strict=True):
            multiplicity *= math.comb(count, selected)
            large_exponents.extend([exponent] * selected)
            small_exponents.extend([exponent] * (count - selected))
        large = radial_backend._large_radial(
            large_exponents + [0] * zero_large, delta)
        small = _small_radial_pruned(
            tuple(small_exponents + [0] * zero_small),
            delta, maximum_shift)
        scale = Q(orbit_multiplier * multiplicity)
        for x_power, left in large.items():
            for (shift, y_power), right in small.items():
                answer[(shift, x_power, y_power)] += scale * left * right
    return {key: value for key, value in answer.items() if value}


def radialize_integer_families_pruned(
        radial_backend, integer_families, *, number_variables,
        number_large, delta, maximum_shift):
    inverted = defaultdict(list)
    associations = 0
    for family, tagged in integer_families.items():
        for tag, polynomial in tagged.items():
            for part, coefficient in polynomial.items():
                if coefficient:
                    inverted[part].append((family, tag, coefficient))
                    associations += 1
    transforms = {}
    radial_denominator = 1
    for part in sorted(inverted):
        transform = partition_face_radial_pruned(
            radial_backend, part, number_variables, number_large, delta,
            maximum_shift)
        transforms[part] = transform
        for coefficient in transform.values():
            radial_denominator = math.lcm(
                radial_denominator, coefficient.denominator)
    accumulators = {
        family: {tag: defaultdict(int) for tag in tagged}
        for family, tagged in integer_families.items()}
    distributed = 0
    for part in sorted(inverted):
        transform = tuple(
            (key, value.numerator *
             (radial_denominator // value.denominator))
            for key, value in transforms[part].items())
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
        "transform_terms": sum(map(len, transforms.values())),
        "radial_denominator_bits": radial_denominator.bit_length(),
        "distributed_terms": distributed,
        "packed_nonzero_terms": output_terms,
        "maximum_shift_pruned_inside_convolution": maximum_shift,
    }


def band_cross_r_integer(engine, radial_backend, families, *, k, alpha_high,
                         alpha_low, alpha_f, eta, delta, schedule, common_r):
    """Drop-in exact replacement for fast-v2 ``band_cross_r_integer``."""
    # Load the frozen fast-v2 backend through the caller's module closure.  A
    # normal import is deliberately avoided because this directory has a
    # hyphen; the runner injects it as ``FAST_V2`` before calling this path.
    fast = globals().get("FAST_V2")
    if fast is None:
        raise RuntimeError("FAST_V2 backend was not bound by the runner/test")
    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return Q0, {"high": {}, "low": {}, "timing_seconds": {}}
    started = time.monotonic()
    integer_families, family_denominator, clear_stats = \
        fast.clear_family_denominators(families)
    clear_seconds = time.monotonic() - started
    maximum_shift = radial_backend._maximum_active_shift(cutoff, delta)
    stamp = time.monotonic()
    packed, radial_denominator, radial_stats = \
        radialize_integer_families_pruned(
            radial_backend, integer_families, number_variables=k - 1,
            number_large=common_r, delta=delta,
            maximum_shift=maximum_shift)
    radial_seconds = time.monotonic() - stamp
    common_denominator = family_denominator * radial_denominator
    stamp = time.monotonic()
    high_integer, high_values_integer, high_stats = fast.endpoint(
        engine, radial_backend, packed, k=k, alpha=alpha_high,
        alpha_f=alpha_f, eta=eta, delta=delta, schedule=schedule,
        common_r=common_r)
    low_integer, low_values_integer, low_stats = fast.endpoint(
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
        },
        "timing_seconds": {
            "clear_family_denominators": clear_seconds,
            "radialize_integer": radial_seconds,
            "integrate_collected_affines": integration_seconds,
        },
    }
