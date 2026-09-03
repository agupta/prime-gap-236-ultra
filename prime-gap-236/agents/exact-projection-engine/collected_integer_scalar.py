#!/usr/bin/env python3
"""Exact globally collected integer scalar contraction.

For each branch and inclusion--exclusion shift, first collect the complete
product of the packed radial polynomial and its tagged affine factors by the
final aggregate monomial ``X^a Y^b``.  Polygon moments are then multiplied
only once per surviving monomial.  All collection is over exact integers
after clearing one affine denominator, and all moments use one separately
cleared exact denominator; their product is restored once per shift.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import math
import time


Q0 = Q(0)


def integrate_packed_collected_integers(radial_backend, packed_by_shift, *,
                                        r, s, delta, domain, first_affine,
                                        second_affine):
    fast = globals().get("FAST_V2")
    if fast is None:
        raise RuntimeError("FAST_V2 backend was not bound")
    answer = Q0
    stats = {
        "active_shifts": 0, "packed_terms": 0, "tag_groups": 0,
        "collected_affine_terms": 0, "requested_moments": 0,
        "scalar_products": 0, "nonzero_product_monomials": 0,
        "cancelled_product_monomials": 0,
        "maximum_affine_denominator_bits": 0,
        "maximum_moment_denominator_bits": 0,
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
            if type(coefficient) is not int:
                raise TypeError(
                    "collected-integer contraction requires integer coefficients")
            if (r == 0 and xp) or (s == 0 and yp):
                raise ArithmeticError(
                    "radial power on zero-dimensional aggregate")
            grouped[(fp, sp)].append((xp, yp, coefficient))

        affine_products = {}
        affine_denominator = 1
        for fp, sp in grouped:
            affine = fast._affine_product(
                radial_backend, fp, sp,
                (f0 + fy * shift, fx, fy),
                (s0 + sy * shift, sx, sy))
            affine_products[(fp, sp)] = affine
            for coefficient in affine.values():
                affine_denominator = math.lcm(
                    affine_denominator, coefficient.denominator)

        # This is the global product collection.  It uses only integers;
        # cancellation is completed before any polygon moment is evaluated.
        product = defaultdict(int)
        scalar_products = 0
        for tag, radial_terms in grouped.items():
            integer_affine = tuple(
                (ax, ay, coefficient.numerator *
                 (affine_denominator // coefficient.denominator))
                for (ax, ay), coefficient in affine_products[tag].items())
            for xp, yp, radial_coefficient in radial_terms:
                for ax, ay, affine_coefficient in integer_affine:
                    product[(xp + ax, yp + ay)] += (
                        radial_coefficient * affine_coefficient)
                    scalar_products += 1
        preclean_count = len(product)
        product = {key: coefficient for key, coefficient in product.items()
                   if coefficient}
        requested = set(product)
        moments = fast._domain_moments(
            radial_backend, requested, r, s, domain, shift)
        moment_denominator = 1
        for moment in moments.values():
            moment_denominator = math.lcm(
                moment_denominator, moment.denominator)
        numerator = sum(
            coefficient * moments[key].numerator *
            (moment_denominator // moments[key].denominator)
            for key, coefficient in product.items())
        answer += Q(numerator, affine_denominator * moment_denominator)

        stats["active_shifts"] += 1
        stats["packed_terms"] += sum(map(len, grouped.values()))
        stats["tag_groups"] += len(grouped)
        stats["collected_affine_terms"] += sum(
            map(len, affine_products.values()))
        stats["requested_moments"] += len(requested)
        stats["scalar_products"] += scalar_products
        stats["nonzero_product_monomials"] += len(product)
        stats["cancelled_product_monomials"] += preclean_count - len(product)
        stats["maximum_affine_denominator_bits"] = max(
            stats["maximum_affine_denominator_bits"],
            affine_denominator.bit_length())
        stats["maximum_moment_denominator_bits"] = max(
            stats["maximum_moment_denominator_bits"],
            moment_denominator.bit_length())
    return answer, stats


def endpoint(engine, radial_backend, packed_families, *, k, alpha, alpha_f,
             eta, delta, schedule, common_r):
    jobs = engine.scheduled_cross_branch_jobs(
        radial_backend, k=k, alpha=alpha, eta=eta, delta=delta,
        schedule=schedule, common_r=common_r)
    second = (alpha_f - common_r * delta, -Q(1), -Q(1))
    values, statistics = {}, {}
    for branch, family, domain, first in jobs:
        value, branch_stats = integrate_packed_collected_integers(
            radial_backend, packed_families[family], r=common_r,
            s=(k - 1) - common_r, delta=delta, domain=domain,
            first_affine=first, second_affine=second)
        values[branch] = value
        statistics[branch] = branch_stats
    return sum(values.values(), Q0), values, statistics


def band_cross_r_integer(engine, radial_backend, families, *, k, alpha_high,
                         alpha_low, alpha_f, eta, delta, schedule, common_r):
    fast = globals().get("FAST_V2")
    pruned = globals().get("PRUNED_V3")
    if fast is None or pruned is None:
        raise RuntimeError("FAST_V2 and PRUNED_V3 backends must be bound")
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
        pruned.radialize_integer_families_pruned(
            radial_backend, integer_families, number_variables=k - 1,
            number_large=common_r, delta=delta,
            maximum_shift=maximum_shift)
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
            "integrate_globally_collected_integers": integration_seconds,
        },
    }
