#!/usr/bin/env python3
"""Trace an actually surviving degree-80 target product monomial exactly.

This is an independent audit artifact, not a producer dependency.  It rebuilds
the pinned scaled D19/D14 kernel, keeps only the homogeneous degree-35
small-total primitive, radializes its leading shift-zero terms on the r=8
face, and globally collects one final X^42 Y^38 coefficient.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
BASE_PATH = FILE.with_name("d14_grid38_scaled_b_shard.py")
BASE_SHA = "deceb6c6248fa97e65c9ce5a604081f3b05f0b7c838dea2f1d1c525a59bea905"
OUTPUT = FILE.with_name("results") / "fixed_polygon_v8_degree80_trace.json"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path, data=None):
    if data is not None and path.read_bytes() != data:
        raise RuntimeError(f"source changed before import: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def main():
    started = time.monotonic()
    base_data = BASE_PATH.read_bytes()
    if sha256_bytes(base_data) != BASE_SHA:
        raise RuntimeError("base producer source changed")
    base = load("v8_degree80_trace_base", BASE_PATH, base_data)
    snapshots = {path: path.read_bytes() for path in base.PINNED}
    for path, expected in base.PINNED.items():
        if sha256_bytes(snapshots[path]) != expected:
            raise RuntimeError(f"pinned source changed: {path}")
    frontier = base.import_snapshot(
        "v8_degree80_trace_frontier", base.FRONTIER,
        snapshots[base.FRONTIER])
    radial = base.import_snapshot(
        "v8_degree80_trace_radial", base.RADIAL,
        snapshots[base.RADIAL])
    engine = base.import_snapshot(
        "v8_degree80_trace_engine", base.ENGINE,
        snapshots[base.ENGINE])

    inner_raw = base.strict_json_bytes(
        snapshots[base.INNER], str(base.INNER))
    outer_raw = base.strict_json_bytes(
        snapshots[base.OUTER], str(base.OUTER))
    inner_basis = base.parse_basis(
        inner_raw["basis"], frontier.ei.even_basis(base.DEGREE_F))
    outer_basis = base.parse_basis(
        outer_raw["basis"], frontier.ei.even_basis(base.DEGREE_H))
    inner_vector = base.parse_vector(
        inner_raw["rational_vector"], len(inner_basis))
    outer_vector = base.parse_vector(
        outer_raw["candidates"][0]["rational_vector"], len(outer_basis))
    inner_scaled = engine.scale_vector(inner_vector, base.SCALE_F)
    outer_scaled = engine.scale_vector(outer_vector, base.SCALE_H)
    outer_terms = engine.dilate_residual_terms(
        outer_basis, outer_scaled, base.DILATION)
    outer_dilated = tuple(outer_terms.get(label, Q(0))
                          for label in outer_basis)

    marginal = engine.marginal_polynomial(
        frontier.ei, inner_basis, inner_scaled, base.K, base.ALPHA1)
    components = engine.distinguished_components(
        frontier.ei, outer_basis, outer_dilated, base.K)
    kernel, kernel_stats = engine.global_cross_kernel(
        frontier.ei, marginal, components)

    # Reconstruct only homogeneous degree 35 in the small_total primitive.
    # The loop is literally the corresponding branch of
    # primitive_tagged_families, with s=residual-j (the sole top-degree term).
    tagged = defaultdict(lambda: defaultdict(Q))
    top_source_terms = 0
    for orbit, block in kernel.items():
        orbit_degree = sum(orbit)
        for (inner_power, exponent, residual), coefficient in block.items():
            if orbit_degree + inner_power + exponent + residual + 1 != 35:
                continue
            top_source_terms += 1
            for j in range(residual + 1):
                remaining = residual - j
                endpoint_power = exponent + j + 1
                tag = (endpoint_power, inner_power + remaining)
                tagged[tag][orbit] += (
                    coefficient * (-1) ** j * math.comb(residual, j) /
                    endpoint_power)
    tagged = {
        tag: {orbit: coefficient for orbit, coefficient in polynomial.items()
              if coefficient}
        for tag, polynomial in tagged.items()}
    tagged = {tag: polynomial for tag, polynomial in tagged.items()
              if polynomial}
    if not tagged or any(sum(orbit) + sum(tag) != 35
                         for tag, polynomial in tagged.items()
                         for orbit in polynomial):
        raise ArithmeticError("top small_total family reconstruction failed")

    common_r = 8
    number_variables = base.K - 1
    number_small = number_variables - common_r
    maximum_shift = radial._maximum_active_shift(
        base.ETA - common_r * base.DELTA, base.DELTA)
    if maximum_shift != 6:
        raise ArithmeticError("r8 shift ceiling changed")
    target_key = (42, 38)
    transform_cache = {}
    packed = defaultdict(Q)
    contributing_packed_terms = []
    for tag in sorted(tagged):
        for orbit, family_coefficient in tagged[tag].items():
            # y=38 is the minimal small-aggregate density power, so only a
            # shift-zero, zero-selected-small-degree leading term can reach
            # the chosen target key.
            if len(orbit) > common_r:
                continue
            if orbit not in transform_cache:
                transform_cache[orbit] = radial._partition_face_radial(
                    orbit, number_variables, common_r, base.DELTA)
            orbit_degree = sum(orbit)
            radial_key = (0, orbit_degree + common_r - 1,
                          number_small - 1)
            radial_coefficient = transform_cache[orbit].get(radial_key, Q(0))
            if radial_coefficient:
                value = family_coefficient * radial_coefficient
                packed[(tag, radial_key[1], radial_key[2])] += value

    final_coefficient = Q(0)
    individual = []
    for (tag, x_power, y_power), packed_coefficient in sorted(packed.items()):
        if not packed_coefficient:
            continue
        affine_degree = sum(tag)
        add_x = target_key[0] - x_power
        add_y = target_key[1] - y_power
        if add_x < 0 or add_y < 0 or add_x + add_y != affine_degree:
            continue
        # Stotal has both affine slopes (-1,-1); constants do not enter its
        # top homogeneous coefficient.
        affine_coefficient = ((-1) ** affine_degree *
                              math.comb(affine_degree, add_x))
        contribution = packed_coefficient * affine_coefficient
        if contribution:
            individual.append((tag, x_power, y_power,
                               affine_coefficient, contribution))
            final_coefficient += contribution
    if not final_coefficient:
        raise ArithmeticError("degree-80 target coefficient cancelled")
    if target_key[0] + target_key[1] != 80:
        raise ArithmeticError("target trace is not degree 80")

    # Confirm that this algebraic coefficient belongs to an actually active
    # two-dimensional Stotal domain, rather than a formally generated but
    # empty branch.  Both endpoint polygons are checked exactly by shoelace.
    stotal_areas = {}
    for side, alpha in (("low", base.ALPHA1), ("high", base.ALPHA2)):
        jobs = engine.scheduled_cross_branch_jobs(
            radial, k=base.K, alpha=alpha, eta=base.ETA,
            delta=base.DELTA, schedule=base.SCHEDULE,
            common_r=common_r)
        matches = [domain for branch, _family, domain, _first in jobs
                   if branch == "Stotal"]
        if len(matches) != 1:
            raise ArithmeticError(f"{side} Stotal domain is not unique")
        domain = matches[0]
        polygon = radial._shifted_polygon(
            domain.total_bound, domain.x_bound, domain.y_lower,
            domain.y_upper, domain.total_lower)
        twice_area = abs(sum(
            x * next_y - next_x * y
            for (x, y), (next_x, next_y) in
            zip(polygon, polygon[1:] + polygon[:1], strict=True)))
        area = twice_area / 2
        if len(polygon) < 3 or area <= 0:
            raise ArithmeticError(f"{side} Stotal shift-zero domain is empty")
        stotal_areas[side] = area

    witness = individual[0]
    result = {
        "format": "fixed-polygon-v8-degree80-actual-packed-trace-v1",
        "rigorous": True,
        "serialized_matrices_read": False,
        "base_sha256": BASE_SHA,
        "source_hashes": {
            str(path.relative_to(REPO)): expected
            for path, expected in base.PINNED.items()},
        "kernel_stats": kernel_stats,
        "common_r": common_r,
        "branch": "Stotal",
        "family": "small_total",
        "shift": 0,
        "maximum_active_shift": maximum_shift,
        "stotal_shift_zero_polygon_area": {
            side: str(area) for side, area in stotal_areas.items()},
        "top_source_kernel_terms": top_source_terms,
        "top_family_tags": len(tagged),
        "top_family_orbit_entries": sum(map(len, tagged.values())),
        "leading_orbit_transforms_used": len(transform_cache),
        "nonzero_packed_terms_relevant_to_target": len(individual),
        "witness": {
            "tag": list(witness[0]),
            "pre_affine_x_power": witness[1],
            "pre_affine_y_power": witness[2],
            "affine_x_power": target_key[0] - witness[1],
            "affine_y_power": target_key[1] - witness[2],
            "affine_coefficient": str(witness[3]),
            "contribution": str(witness[4]),
        },
        "post_collection_key": list(target_key),
        "post_collection_total_degree": sum(target_key),
        "post_collection_coefficient": str(final_coefficient),
        "post_collection_coefficient_sha256": sha256_bytes(
            str(final_coefficient).encode("ascii")),
        "post_collection_coefficient_numerator_bits":
            abs(final_coefficient.numerator).bit_length(),
        "post_collection_coefficient_denominator_bits":
            final_coefficient.denominator.bit_length(),
        "elapsed_seconds": time.monotonic() - started,
    }
    payload = canonical(result)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    descriptor = OUTPUT.open("xb")
    with descriptor as handle:
        handle.write(payload)
        handle.flush()
    print(sha256_bytes(payload), OUTPUT)
    print(json.dumps({
        "coefficient_sha256":
            result["post_collection_coefficient_sha256"],
        "nonzero_relevant_terms": len(individual),
        "witness": result["witness"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
