#!/usr/bin/env python3
"""Bounded J-envelope observables for stratified Ritz discovery.

Sampling from ``g=sum_i m_i^2`` avoids the potentially infinite variance of
direct ``m_i/m_0`` ratios at cancellation zeros of the base marginal.  This
module rescales before squaring, so the discovery target remains stable near
very small or very large marginal values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvelopePoint:
    unit_marginals: tuple
    log_g: float
    z: float
    nonzero_constant_channels: int


def _exact_index(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise IndexError(f"{name} must be an exact integer")
    return value


def j_envelope_point(adapter, common):
    """Return normalized marginal observables, or ``None`` off the envelope."""
    if not adapter.j_support(common):
        return None
    dimension = getattr(adapter, "dimension", None)
    if isinstance(dimension, bool) or not isinstance(dimension, int) or \
            dimension <= 0:
        raise ValueError("adapter dimension must be a positive exact integer")
    strata = tuple(adapter.strata)
    channels = tuple(adapter.channels)
    if not strata or len(set(strata)) != len(strata) or \
            len(channels) != dimension:
        raise ValueError("malformed stratum/channel metadata")
    constant_indices = []
    for r in strata:
        matches = [index for index, channel in enumerate(channels)
                   if channel == (r, 0, 0)]
        if len(matches) != 1:
            raise ValueError("each stratum must have one tagged constant")
        constant_indices.append(matches[0])

    marginals = tuple(float(x) for x in adapter.j_marginals(common))
    if len(marginals) != dimension:
        raise ValueError("marginal vector dimension mismatch")
    if not all(math.isfinite(x) for x in marginals):
        raise ArithmeticError("nonfinite marginal in J envelope")
    scale = max((abs(x) for x in marginals), default=0.0)
    if scale == 0:
        return None
    scaled = tuple(x / scale for x in marginals)
    norm_squared = math.fsum(x * x for x in scaled)
    if not math.isfinite(norm_squared) or norm_squared <= 0:
        raise ArithmeticError("invalid squared marginal envelope")
    norm = math.sqrt(norm_squared)
    unit = tuple(x / norm for x in scaled)
    constants = tuple(unit[index] for index in constant_indices)
    nonzero_constants = sum(x != 0 for x in constants)
    common_r = sum(float(x) > float(adapter.delta) for x in common)
    allowed_constant_strata = {common_r, common_r + 1}
    if any(value != 0 and r not in allowed_constant_strata
           for r, value in zip(strata, constants)):
        raise ArithmeticError("marginal leaked outside its two final strata")
    if nonzero_constants > 2:
        raise ArithmeticError("more than two tagged constants are nonzero")
    z = math.fsum(constants) ** 2
    # Only the small and large distinguished branches contribute tagged
    # constants at fixed common stratum, hence Cauchy--Schwarz gives z <= 2.
    if z > 2 * (1 + 64 * math.ulp(1.0)):
        raise ArithmeticError("base-marginal envelope bound was violated")
    recorded_m0 = float(adapter.j_m0(common, marginals)) / scale / norm
    if (not math.isfinite(recorded_m0) or
            abs(recorded_m0 - math.fsum(constants)) >
            128 * math.ulp(1.0) * max(1.0, abs(recorded_m0))):
        raise ArithmeticError("tagged constants do not reconstruct m0")
    log_g = 2 * math.log(scale) + math.log(norm_squared)
    if not math.isfinite(log_g) or not math.isfinite(z):
        raise ArithmeticError("nonfinite J envelope observable")
    return EnvelopePoint(unit, log_g, z, nonzero_constants)


def j_envelope_log_density(adapter, common):
    point = j_envelope_point(adapter, common)
    return -math.inf if point is None else point.log_g


def bounded_outer_entry(point, i, j):
    dimension = len(point.unit_marginals)
    i = _exact_index(i, "row index")
    j = _exact_index(j, "column index")
    if not (0 <= i < dimension and 0 <= j < dimension):
        raise IndexError("envelope matrix index outside range")
    value = point.unit_marginals[i] * point.unit_marginals[j]
    bound = 1.0 if i == j else 0.5
    if abs(value) > bound + 16 * math.ulp(1.0):
        raise ArithmeticError("normalized envelope outer bound was violated")
    return value
