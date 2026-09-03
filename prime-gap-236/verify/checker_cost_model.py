#!/usr/bin/env python3
"""Static combinatorial cost model; performs no certificate integration."""

from __future__ import annotations

import json
import math
from collections import Counter
from functools import lru_cache
from typing import Iterable


Partition = tuple[int, ...]


def partitions(total: int, maximum: int | None = None) -> Iterable[Partition]:
    if total == 0:
        yield ()
        return
    if maximum is None or maximum > total:
        maximum = total
    for first in range(maximum, 0, -1):
        for tail in partitions(total - first, first):
            yield (first,) + tail


@lru_cache(maxsize=64)
def cumulative_partition_count(degree: int) -> int:
    return sum(1 for total in range(degree + 1) for _ in partitions(total))


@lru_cache(maxsize=64)
def cumulative_no_ones_partition_count(degree: int) -> int:
    return sum(
        1
        for total in range(degree + 1)
        for part in partitions(total)
        if 1 not in part
    )


@lru_cache(maxsize=64)
def split_assignment_calls(degree: int, maximum_face: int) -> int:
    """Count calls made by representative exponent-to-face splitting."""
    answer = 0
    for total in range(degree + 1):
        for part in partitions(total):
            by_selected_count = [1]
            for multiplicity in Counter(part).values():
                updated = [0] * (len(by_selected_count) + multiplicity)
                for old_count, old_ways in enumerate(by_selected_count):
                    for selected in range(multiplicity + 1):
                        updated[old_count + selected] += old_ways
                by_selected_count = updated
            answer += sum(
                sum(by_selected_count[: min(face, len(part)) + 1])
                for face in range(maximum_face + 1)
            )
    return answer


@lru_cache(maxsize=64)
def split_assignment_calls_no_ones(degree: int, maximum_face: int) -> int:
    """Face-split calls after residual powers remove exponent-one strings."""
    answer = 0
    for total in range(degree + 1):
        for part in partitions(total):
            if 1 in part:
                continue
            by_selected_count = [1]
            for multiplicity in Counter(part).values():
                updated = [0] * (len(by_selected_count) + multiplicity)
                for old_count, old_ways in enumerate(by_selected_count):
                    for selected in range(multiplicity + 1):
                        updated[old_count + selected] += old_ways
                by_selected_count = updated
            answer += sum(
                sum(by_selected_count[: min(face, len(part)) + 1])
                for face in range(maximum_face + 1)
            )
    return answer


def model(
    input_degree: int,
    i_maximum_face: int,
    large_j_maximum_face: int,
    initial_j_shift_count: int,
) -> dict[str, int]:
    squared_degree = 2 * input_degree
    i_orbits = cumulative_partition_count(squared_degree)
    i_split_calls = split_assignment_calls(squared_degree, i_maximum_face)

    ss_components = cumulative_partition_count(squared_degree)
    sl_components = sum(
        cumulative_partition_count(squared_degree + 1 - fiber_power)
        for fiber_power in range(1, input_degree + 2)
    )
    ll_components = sum(
        cumulative_partition_count(squared_degree + 2 - combined_power)
        for combined_power in range(2, squared_degree + 3)
    )
    small_faces = i_maximum_face + 1
    large_faces = large_j_maximum_face + 1
    j_component_traversals = (
        small_faces * ss_components
        + 4 * large_faces * sl_components
        + 2 * large_faces * ll_components
    )
    j_split_calls = (
        split_assignment_calls(squared_degree, i_maximum_face)
        + 4
        * sum(
            split_assignment_calls(squared_degree + 1 - fiber_power, large_j_maximum_face)
            for fiber_power in range(1, input_degree + 2)
        )
        + 2
        * sum(
            split_assignment_calls(squared_degree + 2 - combined_power, large_j_maximum_face)
            for combined_power in range(2, squared_degree + 3)
        )
    )
    streaming_family_polynomials = 1 + (input_degree + 1) + (2 * input_degree + 1)
    streaming_ordered_jobs = (
        small_faces
        + 4 * large_faces * (input_degree + 1)
        + 2 * large_faces * (2 * input_degree + 1)
    )
    streaming_boundary_jobs = 3 * small_faces + 6 * large_faces
    streaming_j_split_calls = split_assignment_calls(squared_degree, i_maximum_face)
    small_shift_visits = sum(initial_j_shift_count - r for r in range(small_faces))
    large_shift_visits = sum(initial_j_shift_count - r for r in range(large_faces))
    streaming_geometry_jobs = (
        small_shift_visits
        + 4 * (input_degree + 1) * large_shift_visits
        + 2 * (2 * input_degree + 1) * large_shift_visits
    )
    streaming_boundary_geometry_jobs = 3 * small_shift_visits + 6 * large_shift_visits
    tagged_orbits = cumulative_no_ones_partition_count(squared_degree)
    tagged_split_calls = split_assignment_calls_no_ones(squared_degree, i_maximum_face)
    tagged_ss_targets = 2 * input_degree + 1
    tagged_sl_targets = (input_degree + 1) * (3 * input_degree + 2) // 2
    tagged_ll_targets = (2 * input_degree + 1) * (input_degree + 1)
    tagged_ordered_jobs = small_faces + 6 * large_faces
    tagged_shift_geometry_jobs = small_shift_visits + 6 * large_shift_visits
    tagged_dense_radial_key_ceiling = initial_j_shift_count * math.comb(
        2 * input_degree + 6,
        4,
    )
    tagged_moment_pair_ceiling = math.comb(2 * input_degree + 4, 2)
    return {
        "input_degree": input_degree,
        "expanded_F_orbit_ceiling": cumulative_partition_count(input_degree),
        "expanded_square_orbit_ceiling": i_orbits,
        "I_nonempty_faces": small_faces,
        "I_orbit_face_slots": small_faces * i_orbits,
        "I_fixed_assignment_calls": i_split_calls,
        "J_SS_components": ss_components,
        "J_SL_components_one_order": sl_components,
        "J_LL_components": ll_components,
        "J_ordered_component_face_traversals": j_component_traversals,
        "J_fixed_assignment_calls_without_face_transform_reuse": j_split_calls,
        "streaming_J_radial_family_polynomials_per_face": streaming_family_polynomials,
        "streaming_J_ordered_radial_integral_jobs": streaming_ordered_jobs,
        "streaming_J_boundary_measure_jobs": streaming_boundary_jobs,
        "streaming_J_ordered_shift_geometry_jobs": streaming_geometry_jobs,
        "streaming_J_boundary_shift_geometry_jobs": streaming_boundary_geometry_jobs,
        "streaming_J_orbit_face_slots": small_faces * i_orbits,
        "streaming_J_fixed_assignment_calls": streaming_j_split_calls,
        "streaming_J_assignment_reduction_numerator": j_split_calls,
        "streaming_J_assignment_reduction_denominator": streaming_j_split_calls,
        "tagged_base_orbit_ceiling": tagged_orbits,
        "tagged_orbit_face_slots": small_faces * tagged_orbits,
        "tagged_fixed_assignment_calls": tagged_split_calls,
        "tagged_SS_target_maps_per_face": tagged_ss_targets,
        "tagged_SL_target_maps_per_face": tagged_sl_targets,
        "tagged_LL_target_maps_per_face": tagged_ll_targets,
        "tagged_ordered_branch_jobs": tagged_ordered_jobs,
        "tagged_ordered_shift_geometry_jobs": tagged_shift_geometry_jobs,
        "tagged_dense_radial_key_ceiling_one_face": tagged_dense_radial_key_ceiling,
        "tagged_transient_moment_pair_ceiling": tagged_moment_pair_ceiling,
    }


def main() -> None:
    result = {
        "C10_D4": model(
            input_degree=4,
            i_maximum_face=15,
            large_j_maximum_face=14,
            initial_j_shift_count=26,
        ),
        "C10_D12": model(
            input_degree=12,
            i_maximum_face=15,
            large_j_maximum_face=14,
            initial_j_shift_count=26,
        ),
        "note": "dense structural ceilings; no Fraction integration or certificate data read",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
