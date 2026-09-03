#!/usr/bin/env python3
"""Bounded J envelope for exact-whitened D4 multiplier coordinates."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class WhitenedEnvelopePoint:
    unit_marginals: tuple
    log_g: float
    z: float
    nonzero_constant_channels: int
    z_bound: float


def j_envelope_point(adapter, common):
    if not adapter.j_support(common):
        return None
    marginals = tuple(float(x) for x in adapter.j_marginals(common))
    if len(marginals) != adapter.dimension or \
            not all(math.isfinite(x) for x in marginals):
        raise ArithmeticError("invalid transformed marginal vector")
    scale = max((abs(x) for x in marginals), default=0.0)
    if scale == 0:
        return None
    scaled = tuple(x / scale for x in marginals)
    norm_squared = math.fsum(x * x for x in scaled)
    if not math.isfinite(norm_squared) or norm_squared <= 0:
        raise ArithmeticError("invalid transformed envelope norm")
    norm = math.sqrt(norm_squared)
    unit = tuple(x / norm for x in scaled)
    common_r = sum(float(x) > float(adapter.delta) for x in common)
    allowed = {common_r, common_r + 1}
    constants = [(r, unit[6 * r], adapter.base_constant_weights[6 * r])
                 for r in adapter.strata]
    if any(value != 0 and r not in allowed for r, value, _ in constants):
        raise ArithmeticError("transformed marginal leaked outside two strata")
    nonzero = sum(value != 0 for _, value, _ in constants)
    if nonzero > 2:
        raise ArithmeticError("more than two transformed constants are nonzero")
    weighted_m0 = math.fsum(weight * value
                            for _, value, weight in constants)
    z = weighted_m0 * weighted_m0
    z_bound = math.fsum(weight * weight for r, _, weight in constants
                        if r in allowed)
    tolerance = 128 * math.ulp(1.0) * max(1.0, z_bound)
    if not (math.isfinite(z) and 0 <= z <= z_bound + tolerance and
            z_bound <= 2):
        raise ArithmeticError("weighted transformed z bound failed")
    recorded = float(adapter.j_m0(common, marginals)) / scale / norm
    if (not math.isfinite(recorded) or
            abs(recorded - weighted_m0) >
            128 * math.ulp(1.0) * max(1.0, abs(recorded))):
        raise ArithmeticError("transformed constants do not reconstruct m0")
    log_g = 2 * math.log(scale) + math.log(norm_squared)
    if not math.isfinite(log_g):
        raise ArithmeticError("transformed envelope density is nonfinite")
    return WhitenedEnvelopePoint(unit, log_g, z, nonzero, z_bound)


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def bounded_outer_entry(point, i, j):
    if (isinstance(i, bool) or not isinstance(i, int) or
            isinstance(j, bool) or not isinstance(j, int) or
            not 0 <= i < len(point.unit_marginals) or
            not 0 <= j < len(point.unit_marginals)):
        raise IndexError("transformed envelope index outside range")
    value = point.unit_marginals[i] * point.unit_marginals[j]
    bound = 1.0 if i == j else 0.5
    if abs(value) > bound + 16 * math.ulp(1.0):
        raise ArithmeticError("transformed envelope outer bound failed")
    return value
