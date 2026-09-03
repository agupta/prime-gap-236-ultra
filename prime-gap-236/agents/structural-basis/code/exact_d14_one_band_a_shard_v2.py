#!/usr/bin/env python3
"""Paired high-minus-low exact D14 A shard producer.

Version 1 evaluates the two nested scheduled supports separately.  This version
keeps the same exact formulas and immutable one-count interface, but reuses the
large/small orbit density on each common ``(R,h)`` face.  Only the outer radial
endpoint and its residual polynomial differ between the high and low support.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction as Q
import gc
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

FILE = Path(__file__).resolve()
BASE = FILE.with_name("exact_d14_one_band_a_shard_v1.py")
BASE_SHA256 = \
    "6fa3c7c99735ec9eeb5817413e4dfc77dc6ae57e1cef26c720f54f33eb93896e"


def load_base():
    if __import__("hashlib").sha256(BASE.read_bytes()).hexdigest() != BASE_SHA256:
        raise RuntimeError("pinned exact-A v1 implementation changed")
    spec = importlib.util.spec_from_file_location(
        "exact_d14_one_band_a_shard_v1_for_v2", BASE)
    if spec is None or spec.loader is None:
        raise ImportError(BASE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


B = load_base()


def common_square_terms(exact_module, basis, common_vector):
    """Collect H^2 as P_nu (1-S)^power before choosing a radial endpoint."""
    terms = defaultdict(Q)
    for i, (a, lam) in enumerate(basis):
        for j in range(i + 1):
            b, mu = basis[j]
            factor = common_vector[i] * common_vector[j]
            if i != j:
                factor *= 2
            for nu, multiplicity in exact_module.multiply_monomial_orbits(
                    lam, mu):
                terms[(nu, a + b)] += factor * multiplicity
    grouped = defaultdict(dict)
    for (nu, power), coefficient in terms.items():
        if coefficient:
            grouped[nu][power] = coefficient
    return dict(grouped)


def paired_evaluate(grouped_module, high, low, basis, common_vector,
                    count, progress=False):
    """Evaluate both nested supports with one endpoint-independent face poly."""
    high_evaluator = grouped_module.GroupedEvaluator(
        high, basis, common_vector, Q)
    low_evaluator = grouped_module.GroupedEvaluator(
        low, basis, common_vector, Q)
    common_grouped = common_square_terms(
        grouped_module.ei, basis, common_vector)
    term_count = sum(len(row) for row in common_grouped.values())
    if (not common_grouped or
            (len(basis) == B.DIMENSION and
             term_count != B.EXPECTED_SQUARE_RESIDUAL_TERMS)):
        raise ArithmeticError("paired D14 square inventory mismatch")
    dimension = high.k
    high_max_h = int(high.alpha // high.delta) - count
    low_max_h = int(low.alpha // low.delta) - count
    if high_max_h != low_max_h or high.delta != low.delta:
        raise ArithmeticError("nested supports do not share face combinatorics")
    max_h = high_max_h
    if max_h < 0:
        return Q(0), Q(0), len(common_grouped), term_count, 0, 0
    constraints = ()
    if count:
        high_cap = high.beta(count) - count * high.delta
        low_cap = low.beta(count) - count * low.delta
        if high_cap != low_cap or high_cap <= 0:
            raise ArithmeticError("nested support cap mismatch")
        constraints = ((Q(1), Q(0), high_cap),)
    high_answer = Q(0)
    low_answer = Q(0)
    high_faces = 0
    low_faces = 0
    one = Q(1)
    for h in range(max_h + 1):
        high_outer = high.alpha - (count + h) * high.delta
        low_outer = low.alpha - (count + h) * low.delta
        total_poly = defaultdict(Q)
        # Since H^2 is stored in powers of (1-S), this base is independent of
        # the high/low radial endpoint.  Only the integration domain changes.
        common_outer = Q(1) - (count + h) * high.delta
        for nu, residuals in common_grouped.items():
            density = high_evaluator.orbit_density(
                dimension, nu, count, h, max_h)
            if not density:
                continue
            residual_poly = defaultdict(Q)
            for power, coefficient in residuals.items():
                grouped_module.add_poly(
                    residual_poly,
                    dict(grouped_module.ei._linear_power(
                        common_outer, -one, -one, power)),
                    coefficient)
            grouped_module.add_poly(
                total_poly,
                grouped_module.ei._poly_mul(density, residual_poly), one)
        if high_outer > 0:
            high_answer += high_evaluator.integrate_domain(
                dict(total_poly), dimension, count, high_outer, constraints)
            high_faces += 1
        if low_outer > 0:
            low_answer += low_evaluator.integrate_domain(
                dict(total_poly), dimension, count, low_outer, constraints)
            low_faces += 1
        if progress:
            print(json.dumps({
                "count": count, "h": h, "high_faces": high_faces,
                "low_faces": low_faces, "orbit_groups": len(common_grouped),
                "common_poly_terms": len(total_poly),
            }, sort_keys=True), flush=True)
        high_evaluator.clear_face_caches()
        low_evaluator.clear_face_caches()
    high_evaluator.clear_radial_caches()
    return (high_answer, low_answer, len(common_grouped), term_count,
            high_faces, low_faces)


def build_shard(count: int, *, progress=False):
    if isinstance(count, bool) or not isinstance(count, int) or \
            count not in B.ACTIVE_COUNTS:
        raise ValueError("count must be one of the frozen active counts 0..12")
    tracked = (FILE, BASE) + tuple(B.PINNED_INPUTS)
    snapshots = {path: path.read_bytes() for path in tracked}
    if B.sha256(snapshots[BASE]) != BASE_SHA256:
        raise RuntimeError("pinned exact-A v1 implementation changed")
    B.validate_pins(snapshots)
    exact, stratum, grouped = B.load_integrators()
    fine, selected, basis, vector, one_band = B.load_inputs()
    if tuple(exact.even_basis(B.DEGREE)) != basis:
        raise ArithmeticError("D14 basis is not the pinned even basis")
    Support = B.make_support_class(stratum)
    high, low = B.validate_geometry(Support)
    dilation = B.ALPHA1 / B.ALPHA2
    scaled_vector = tuple(B.VECTOR_SCALE * value for value in vector)
    if any(value.denominator != 1 for value in scaled_vector):
        raise ArithmeticError("10^38 did not clear the selected grid denominators")
    unscaled_common = B.natural_dilation_common_vector(
        basis, vector, dilation)
    common_vector = B.natural_dilation_common_vector(
        basis, scaled_vector, dilation)
    if common_vector != tuple(B.VECTOR_SCALE * value
                              for value in unscaled_common):
        raise ArithmeticError("natural dilation did not commute with scaling")
    for center in (B.ALPHA1, B.ALPHA2):
        if B.centered_from_common(basis, common_vector, center) != \
                B.centered_direct_from_original(
                    basis, scaled_vector, dilation, center):
            raise ArithmeticError("natural-dilation expansion mismatch")

    started = time.monotonic()
    high_volume_termwise = B.exact_constant_volume(high, count)
    high_volume_grouped, high_volume_faces = B.grouped_constant_volume(
        grouped, high, count)
    low_volume_termwise = B.exact_constant_volume(low, count)
    low_volume_grouped, low_volume_faces = B.grouped_constant_volume(
        grouped, low, count)
    if (high_volume_termwise != high_volume_grouped or
            low_volume_termwise != low_volume_grouped):
        raise ArithmeticError("termwise/grouped stratum volume mismatch")
    band_volume = high_volume_termwise - low_volume_termwise
    if band_volume <= 0:
        raise ArithmeticError("active one-band stratum has nonpositive volume")

    (high_value, low_value, groups, terms,
     high_faces, low_faces) = paired_evaluate(
         grouped, high, low, basis, common_vector, count, progress)
    band_value = high_value - low_value
    if high_value <= 0 or low_value <= 0 or band_value <= 0:
        raise ArithmeticError("exact squared-polynomial positivity failed")
    if high_volume_faces != high_faces or low_volume_faces != low_faces:
        raise ArithmeticError("volume/polynomial face inventory mismatch")
    elapsed = time.monotonic() - started
    gc.collect()
    for path, payload in snapshots.items():
        if path.read_bytes() != payload:
            raise RuntimeError(f"exact-A source closure changed: {path}")

    vector_tokens = [B.canonical_q(x) for x in vector]
    scaled_tokens = [B.canonical_q(x) for x in scaled_vector]
    return {
        "format": "exact-d14-one-band-a-count-shard-v2",
        "status": "EXACT D14 ONE-BAND A COUNT SHARD PASS",
        "rigorous": True,
        "claim_scope": (
            "one exact large-coordinate-count contribution to I(H) on the "
            "frozen single outer band; no J or final Rayleigh claim"),
        "count": count,
        "active_counts": list(B.ACTIVE_COUNTS),
        "k": B.K,
        "degree": B.DEGREE,
        "basis_dimension": B.DIMENSION,
        "candidate": {
            "name": selected["name"],
            "grid_digits": B.GRID_DIGITS,
            "vector_sha256": B.sha256((json.dumps(
                vector_tokens, separators=(",", ":")) + "\n").encode("ascii")),
            "evaluation_vector_scale": B.canonical_q(B.VECTOR_SCALE),
            "evaluation_vector_is_integral": True,
            "scaled_vector_sha256": B.sha256((json.dumps(
                scaled_tokens, separators=(",", ":")) + "\n").encode("ascii")),
            "rayleigh_scaling_invariant": (
                "A scales by 10^76 and b by 10^38, so b^2/A is unchanged"),
            "natural_dilation": B.canonical_q(dilation),
            "exact_full_simplex_I": selected["exact_denominator"],
            "exact_full_simplex_48J": selected["exact_numerator_48J"],
            "exact_full_simplex_quotient": selected["exact_quotient"],
            "scaled_exact_full_simplex_I": B.canonical_q(
                Q(selected["exact_denominator"]) * B.VECTOR_SCALE ** 2),
            "scaled_exact_full_simplex_48J": B.canonical_q(
                Q(selected["exact_numerator_48J"]) * B.VECTOR_SCALE ** 2),
        },
        "geometry": {
            "alpha1": B.canonical_q(B.ALPHA1),
            "alpha2": B.canonical_q(B.ALPHA2),
            "eta": B.canonical_q(B.ETA),
            "delta": B.canonical_q(B.DELTA),
            "schedule": [B.canonical_q(x) for x in B.SCHEDULE],
            "schedule_extension": "terminal plateau through count 48",
            "band": "alpha1 <= sum(t) < alpha2, boundaries immaterial",
        },
        "exact_values": {
            "high_support_I_count": B.canonical_q(high_value),
            "low_support_I_count": B.canonical_q(low_value),
            "band_I_count": B.canonical_q(band_value),
            "band_I_count_decimal": B.rational_decimal(band_value),
            "unscaled_band_I_count": B.canonical_q(
                band_value / B.VECTOR_SCALE ** 2),
            "unscaled_band_I_count_decimal": B.rational_decimal(
                band_value / B.VECTOR_SCALE ** 2),
            "high_support_volume_count": B.canonical_q(high_volume_termwise),
            "low_support_volume_count": B.canonical_q(low_volume_termwise),
            "band_volume_count": B.canonical_q(band_volume),
        },
        "checks": {
            "natural_dilation_two_expansions_equal": True,
            "integer_vector_scale_and_dilation_commute": True,
            "termwise_vs_grouped_constant_volume_equal": True,
            "high_support_square_positive": True,
            "low_support_square_positive": True,
            "band_square_positive": True,
            "nested_supports_same_schedule": True,
            "paired_face_density_reuse": True,
        },
        "inventory": {
            "square_orbit_partition_groups": groups,
            "square_residual_terms_per_support": terms,
            "high_faces": high_faces,
            "low_faces": low_faces,
            "shared_density_faces": high_faces,
            "workers": 1,
        },
        "elapsed_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "memory_limit_bytes": B.MAX_ADDRESS_SPACE_BYTES,
        "time_limit_seconds": B.TIME_LIMIT_SECONDS,
        "source_sha256": B.sha256(snapshots[FILE]),
        "base_source_sha256": BASE_SHA256,
        "source_hashes": {
            str(path.relative_to(B.REPO)): expected
            for path, expected in B.PINNED_INPUTS.items()
        } | {str(BASE.relative_to(B.REPO)): BASE_SHA256},
        "one_band_status": one_band["status"],
        "fine_grid_status": fine["status"],
        "cache_read": False,
        "serialized_matrix_entries_read": False,
        "launch_authorized": True,
        "target_kind": "authorized exact A-only prerequisite",
        "resume_supported": False,
        "checkpoint_unit": "one immutable explicit-count shard",
        "theorem_ready": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, choices=B.ACTIVE_COUNTS,
                        required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()
    B.apply_limits()
    result = build_shard(args.count, progress=args.progress)
    payload = B.canonical_json(result)
    B.publish_exclusive(args.output, payload)
    print(json.dumps({
        "status": result["status"],
        "count": args.count,
        "scaled_band_I_count_decimal": result["exact_values"][
            "band_I_count_decimal"],
        "unscaled_band_I_count_decimal": result["exact_values"][
            "unscaled_band_I_count_decimal"],
        "elapsed_seconds": result["elapsed_seconds"],
        "peak_rss_kib": result["peak_rss_kib"],
        "output_sha256": B.sha256(payload),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
