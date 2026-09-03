#!/usr/bin/env python3
"""Fixed-stratum initialization and proposals for importance discovery."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from importance_envelope import j_envelope_log_density
from importance_sampler import metropolis_step
from importance_point_eval import stratum_statistics


@dataclass(frozen=True)
class ConditionalStep:
    result: object
    move_type: str


def _target_data(adapter, target):
    if target == "I":
        return adapter.k, adapter.alpha, adapter.i_support, adapter.i_log_density
    if target == "J":
        return (adapter.k - 1, adapter.eta, adapter.j_support,
                lambda state: j_envelope_log_density(adapter, state))
    raise ValueError("target must be I or J")


def point_stratum(adapter, point):
    return stratum_statistics(point, adapter.delta)[0]


def conditional_support(adapter, target, stratum):
    if (isinstance(stratum, bool) or not isinstance(stratum, int) or
            stratum not in adapter.strata):
        raise ValueError("stratum is not active")
    _, _, geometric_support, _ = _target_data(adapter, target)

    def predicate(state):
        return (geometric_support(state) and
                point_stratum(adapter, state) == stratum)

    return predicate


def conditional_log_density(adapter, target):
    return _target_data(adapter, target)[3]


def randomized_interior_start(adapter, target, stratum, seed,
                              *, max_attempts=128):
    """Construct a randomized finite-density interior point in one stratum."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an exact integer")
    if (isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or
            max_attempts <= 0):
        raise ValueError("max_attempts must be a positive exact integer")
    dimension, upper, _, log_density = _target_data(adapter, target)
    support = conditional_support(adapter, target, stratum)
    rng = random.Random(seed)
    small_count = dimension - stratum
    if small_count < 0:
        raise ValueError("stratum exceeds physical dimension")

    for _ in range(max_attempts):
        if stratum:
            lower_large = stratum * adapter.delta
            upper_large = min(adapter.beta(stratum), upper)
            if not lower_large < upper_large:
                raise ValueError("requested stratum has empty large-mass interval")
            fraction = 0.2 + 0.45 * rng.random()
            large_total = lower_large + fraction * (
                upper_large - lower_large)
            weights = [0.75 + 0.5 * rng.random()
                       for _ in range(stratum)]
            weight_sum = math.fsum(weights)
            excess = large_total - lower_large
            large = [adapter.delta + excess * weight / weight_sum
                     for weight in weights]
        else:
            large_total = 0.0
            large = []

        if small_count:
            small_capacity = min(
                upper - large_total,
                small_count * adapter.delta)
            if small_capacity <= 0:
                continue
            # Keeping the average below 0.3 delta and drawing weights within
            # a factor 5/3 ensures every small coordinate is strictly below
            # delta, without a floating threshold repair afterward.
            small_total = (0.1 + 0.18 * rng.random()) * small_capacity
            weights = [0.75 + 0.5 * rng.random()
                       for _ in range(small_count)]
            weight_sum = math.fsum(weights)
            small = [small_total * weight / weight_sum for weight in weights]
        else:
            small = []
        point = large + small
        rng.shuffle(point)
        point = tuple(point)
        if not support(point):
            continue
        value = float(log_density(point))
        if math.isfinite(value):
            return point
    raise RuntimeError("could not construct a finite-density interior start")


def choose_mixed_pair(dimension, rng, slack_probability=0.5):
    if (isinstance(dimension, bool) or not isinstance(dimension, int) or
            dimension < 2):
        raise ValueError("at least two physical coordinates are required")
    if not math.isfinite(float(slack_probability)) or not (
            0 < slack_probability < 1):
        raise ValueError("slack_probability must lie strictly inside (0,1)")
    if rng.random() < slack_probability:
        return (rng.randrange(dimension), dimension), "physical-slack"
    return tuple(sorted(rng.sample(range(dimension), 2))), "physical-physical"


def conditional_metropolis_step(adapter, target, stratum, state, rng,
                                *, density_power=1.0,
                                slack_probability=0.5):
    dimension, upper, _, log_density = _target_data(adapter, target)
    geometric_support = conditional_support(adapter, target, stratum)
    if not geometric_support(state):
        raise ValueError("current state is outside its conditional stratum")
    current_log = float(log_density(state))
    if not math.isfinite(current_log):
        raise ValueError("current conditional state must have positive density")
    if density_power == 0:
        # Uniform tempering is restricted to the positive-density interior.
        # This removes only a target-null set mathematically, while preventing
        # the generic power-zero kernel from accepting a represented -inf
        # state that cannot seed the next positive-power stage.
        def support(candidate):
            if not geometric_support(candidate):
                return False
            candidate_log = float(log_density(candidate))
            if math.isnan(candidate_log) or candidate_log == math.inf:
                raise ArithmeticError("invalid conditional log density")
            return candidate_log != -math.inf
    else:
        support = geometric_support
    pair, move_type = choose_mixed_pair(
        dimension, rng, slack_probability=slack_probability)
    result = metropolis_step(
        state, upper, log_density, support, rng,
        density_power=density_power, pair=pair)
    if not support(result.state):
        raise ArithmeticError("conditional kernel returned outside its stratum")
    return ConditionalStep(result, move_type)
