#!/usr/bin/env python3
"""Exact joint-assignment DP for fixed-denominator radial transforms.

Instead of enumerating how each exponent multiplicity splits between the
large and small coordinate groups and then convolving two radial polynomials,
this backend processes the exponent occurrences once.  Its DP state records
large-count, inclusion--exclusion shift, large degree, and small degree.
Equal allocations collide immediately over integers.  Zero exponents are
inserted at the end with one exact multinomial factor.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import math
import time


Q0 = Q(0)


def partition_face_scaled_integer(radial_backend, part, number_variables,
                                  number_large, delta, maximum_shift, *,
                                  maximum_degree, factorial_ceiling,
                                  common_denominator):
    cached = globals().get("CACHED_V7")
    if cached is None:
        raise RuntimeError("CACHED_V7 backend was not bound")
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
    total_degree = sum(part)
    factorial_top = cached._factorials_through(
        factorial_ceiling)[factorial_ceiling]
    expected_denominator = (
        delta.denominator ** maximum_degree * factorial_top)
    if common_denominator != expected_denominator:
        raise ArithmeticError("fixed transform denominator mismatch")
    delta_scales = cached._delta_scales(
        delta.numerator, delta.denominator, maximum_degree, total_degree)

    # (large_count, shifted_small_count, large_degree, small_degree) -> Z.
    states = {(0, 0, 0, 0): 1}
    for exponent in part:
        following = defaultdict(int)
        falling = [1]
        for power in range(1, exponent + 1):
            falling.append(falling[-1] * (exponent - power + 1))
        factorial_exponent = falling[-1]
        for (large_count, shift, large_degree, small_degree), coefficient \
                in states.items():
            if large_count < number_large:
                for power, factor in enumerate(falling):
                    following[(large_count + 1, shift,
                               large_degree + power,
                               small_degree)] += coefficient * factor
            # The unshifted upper endpoint of a small coordinate.
            following[(large_count, shift, large_degree,
                       small_degree + exponent)] += (
                coefficient * factorial_exponent)
            # The shifted lower endpoint, including its minus sign.
            if shift < maximum_shift:
                for power, factor in enumerate(falling):
                    following[(large_count, shift + 1, large_degree,
                               small_degree + power)] -= coefficient * factor
        states = {key: value for key, value in following.items() if value}

    zero_count = number_variables - len(part)
    number_small = number_variables - number_large
    answer = defaultdict(int)
    orbit_multiplier = radial_backend.orbit_size(number_variables, part)
    for (marked_large, positive_shift, large_degree, small_degree), \
            coefficient in states.items():
        zero_large = number_large - marked_large
        if not 0 <= zero_large <= zero_count:
            continue
        zero_small = zero_count - zero_large
        assignment_count = math.comb(zero_count, zero_large)
        x_power = (large_degree + number_large - 1
                   if number_large else 0)
        y_power = (small_degree + number_small - 1
                   if number_small else 0)
        selected_degree = large_degree + small_degree
        if selected_degree > total_degree:
            raise ArithmeticError("joint falling degree exceeds orbit degree")
        common_scale = (
            orbit_multiplier * assignment_count * coefficient *
            delta_scales[selected_degree] *
            cached._factorial_ratio(
                factorial_ceiling, x_power, y_power))
        for shifted_zeros in range(
                min(zero_small, maximum_shift - positive_shift) + 1):
            answer[(positive_shift + shifted_zeros,
                    x_power, y_power)] += (
                common_scale * (-1) ** shifted_zeros *
                math.comb(zero_small, shifted_zeros))
    return {key: value for key, value in answer.items() if value}


def radialize_integer_families_fixed(
        radial_backend, integer_families, *, number_variables,
        number_large, delta, maximum_shift):
    cached = globals().get("CACHED_V7")
    if cached is None:
        raise RuntimeError("CACHED_V7 backend was not bound")
    inverted = defaultdict(list)
    associations = 0
    for family, tagged in integer_families.items():
        for tag, polynomial in tagged.items():
            for part, coefficient in polynomial.items():
                if type(coefficient) is not int:
                    raise TypeError("joint radialization requires integer families")
                if coefficient:
                    inverted[part].append((family, tag, coefficient))
                    associations += 1
    maximum_degree = max((sum(part) for part in inverted), default=0)
    factorial_ceiling = max(0, maximum_degree + number_variables - 1)
    delta = Q(delta)
    factorial_top = cached._factorials_through(
        factorial_ceiling)[factorial_ceiling]
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
        "joint_large_small_assignment_dp": True,
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
            "radialize_joint_assignment_integers": radial_seconds,
            "integrate_globally_collected_integers": integration_seconds,
        },
    }
