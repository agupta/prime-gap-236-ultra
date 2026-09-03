#!/usr/bin/env python3
"""Two-worker exact cached radialization and branch contraction.

This backend evaluates the frozen cached-v7 coefficient map.  Independent
partition transforms are split between two forked workers; after deterministic
merge and denominator reduction, the independent endpoint/branch integrals
are likewise split between two workers.  ``Pool.map`` preserves task order,
and all returned values are exact Python integers/Fractions.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import math
import multiprocessing
import resource
import sys
import time


Q0 = Q(0)
WORKERS = 2
_PARTITION_CONTEXT = None
_INTEGRATION_CONTEXT = None


def _partition_task(part):
    cached = globals().get("CACHED_V7")
    context = globals().get("_PARTITION_CONTEXT")
    if cached is None or context is None:
        raise RuntimeError("parallel partition worker lacks frozen context")
    (radial_backend, number_variables, number_large, delta, maximum_shift,
     maximum_degree, factorial_ceiling, common_denominator) = context
    transform = cached.partition_face_scaled_integer(
        radial_backend, part, number_variables, number_large, delta,
        maximum_shift, maximum_degree=maximum_degree,
        factorial_ceiling=factorial_ceiling,
        common_denominator=common_denominator)
    return part, transform


def _integration_task(task):
    collected = globals().get("COLLECTED_V5")
    context = globals().get("_INTEGRATION_CONTEXT")
    if collected is None or context is None:
        raise RuntimeError("parallel integration worker lacks frozen context")
    radial_backend, packed, k, alpha_f, delta, common_r = context
    side, branch, family, domain, first = task
    second = (alpha_f - common_r * delta, -Q(1), -Q(1))
    value, statistics = collected.integrate_packed_collected_integers(
        radial_backend, packed[family], r=common_r,
        s=(k - 1) - common_r, delta=delta, domain=domain,
        first_affine=first, second_affine=second)
    return side, branch, value, statistics


def _fork_pool_map(function, tasks):
    if "fork" not in multiprocessing.get_all_start_methods():
        raise RuntimeError("exact parallel backend requires fork start method")
    context = multiprocessing.get_context("fork")
    with context.Pool(processes=min(WORKERS, len(tasks))) as pool:
        # Partition costs are strongly nonuniform, so the default large map
        # chunks can leave one worker idle behind a single hard tail.
        return pool.map(function, tasks, chunksize=1)


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
                    raise TypeError("parallel radialization requires integers")
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
    parts = sorted(inverted)
    global _PARTITION_CONTEXT
    if _PARTITION_CONTEXT is not None:
        raise RuntimeError("parallel partition context already active")
    _PARTITION_CONTEXT = (
        radial_backend, number_variables, number_large, delta, maximum_shift,
        maximum_degree, factorial_ceiling, provisional_denominator)
    try:
        pairs = (_fork_pool_map(_partition_task, parts)
                 if parts else [])
    finally:
        _PARTITION_CONTEXT = None
    transforms = dict(pairs)
    if list(transforms) != parts:
        raise ArithmeticError("parallel partition merge lost or reordered keys")
    common_gcd = provisional_denominator
    for part in parts:
        for coefficient in transforms[part].values():
            common_gcd = math.gcd(common_gcd, abs(coefficient))
    radial_denominator = provisional_denominator // common_gcd

    accumulators = {
        family: {tag: defaultdict(int) for tag in tagged}
        for family, tagged in integer_families.items()}
    distributed = 0
    transform_terms = 0
    for part in parts:
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
        "parallel_partition_workers": min(WORKERS, len(parts)),
    }


def band_cross_r_integer(engine, radial_backend, families, *, k, alpha_high,
                         alpha_low, alpha_f, eta, delta, schedule, common_r):
    fast = globals().get("FAST_V2")
    if fast is None:
        raise RuntimeError("FAST_V2 backend was not bound")
    cutoff = eta - common_r * delta
    if cutoff <= 0:
        return Q0, {"high": {}, "low": {}, "timing_seconds": {}}
    jobs_by_side = {}
    for side, alpha in (("high", alpha_high), ("low", alpha_low)):
        jobs_by_side[side] = engine.scheduled_cross_branch_jobs(
            radial_backend, k=k, alpha=alpha, eta=eta, delta=delta,
            schedule=schedule, common_r=common_r)
    active_families = {
        family for jobs in jobs_by_side.values()
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
    print(f"parallel-cached radial r={common_r} seconds={radial_seconds:.3f}",
          file=sys.stderr, flush=True)
    common_denominator = family_denominator * radial_denominator

    tasks = [
        (side, branch, family, domain, first)
        for side in ("high", "low")
        for branch, family, domain, first in jobs_by_side[side]]
    global _INTEGRATION_CONTEXT
    if _INTEGRATION_CONTEXT is not None:
        raise RuntimeError("parallel integration context already active")
    _INTEGRATION_CONTEXT = (
        radial_backend, packed, k, alpha_f, delta, common_r)
    stamp = time.monotonic()
    try:
        rows = _fork_pool_map(_integration_task, tasks) if tasks else []
    finally:
        _INTEGRATION_CONTEXT = None
    integration_seconds = time.monotonic() - stamp
    print(f"parallel-cached integrate r={common_r} "
          f"seconds={integration_seconds:.3f}",
          file=sys.stderr, flush=True)
    values = {"high": {}, "low": {}}
    statistics = {"high": {}, "low": {}}
    for side, branch, value, branch_statistics in rows:
        if branch in values[side]:
            raise ArithmeticError("duplicate parallel endpoint branch")
        values[side][branch] = value
        statistics[side][branch] = branch_statistics
    high_integer = sum(values["high"].values(), Q0)
    low_integer = sum(values["low"].values(), Q0)
    high, low = (high_integer / common_denominator,
                 low_integer / common_denominator)
    return k * (high - low), {
        "high": {key: value / common_denominator
                 for key, value in values["high"].items()},
        "low": {key: value / common_denominator
                for key, value in values["low"].items()},
        "high_stats": statistics["high"],
        "low_stats": statistics["low"],
        "integer_radialization": {
            "family_denominator": str(family_denominator),
            "radial_denominator": str(radial_denominator),
            "combined_denominator_bits": common_denominator.bit_length(),
            "clear_stats": clear_stats, "radial_stats": radial_stats,
            "active_branch_families": sorted(active_families),
            "inactive_families_pruned_before_radialization": sorted(
                set(families) - active_families),
            "parallel_branch_workers": min(WORKERS, len(tasks)),
            "child_peak_rss_kib": resource.getrusage(
                resource.RUSAGE_CHILDREN).ru_maxrss,
        },
        "timing_seconds": {
            "clear_family_denominators": clear_seconds,
            "radialize_parallel_cached_integers": radial_seconds,
            "integrate_parallel_globally_collected_integers":
                integration_seconds,
        },
    }
