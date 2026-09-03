#!/usr/bin/env python3
"""Reversible simplex kernels for importance-Ritz discovery.

No function in this module computes or certifies a sieve quotient.  The
kernel targets a caller-supplied unnormalised log density and is kept separate
from the exact integration code so stochastic output cannot enter a theorem
checker accidentally.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class StepResult:
    state: tuple
    log_density: float
    accepted: bool
    pair: tuple
    fraction: float
    support_rejected: bool


class NumericalSimplexDrift(ArithmeticError):
    """A floating proposal left the represented simplex by roundoff."""


def _exact_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an exact integer")
    return value


def _finite_float(value, name):
    if isinstance(value, (bool, str, bytes, complex)):
        raise ValueError(f"{name} must be a finite real scalar")
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite real scalar") from error
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite real scalar")
    return converted


def _log_value(log_density, state):
    value = float(log_density(state))
    if math.isnan(value) or value == math.inf:
        raise ArithmeticError("log density must be finite or -inf")
    return value


def simplex_slack(state, upper):
    _finite_float(upper, "simplex upper bound")
    for value in state:
        _finite_float(value, "simplex coordinate")
    if upper < 0:
        raise ValueError("simplex upper bound must be nonnegative")
    slack = upper - sum(state)
    if slack < 0:
        raise ValueError("state lies outside simplex")
    if any(x < 0 for x in state):
        raise ValueError("state has a negative coordinate")
    return slack


def redistribute_pair(state, upper, pair, fraction):
    """Redistribute one physical/physical-or-slack pair symmetrically."""
    n = len(state)
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ValueError("pair must contain exactly two indices")
    i, j = pair
    _exact_int(i, "pair index")
    _exact_int(j, "pair index")
    if not (0 <= i < j <= n):
        raise ValueError("pair must be ordered inside physical-plus-slack indices")
    _finite_float(fraction, "redistribution fraction")
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must lie in [0,1]")
    augmented = list(state) + [simplex_slack(state, upper)]
    total = augmented[i] + augmented[j]
    augmented[i] = total * fraction
    augmented[j] = total * (1 - fraction)
    candidate = tuple(augmented[:n])
    # Never return a represented state outside the simplex.  A one-ulp escape
    # is common on a floating boundary and would make the next slack
    # reconstruction fail.  Metropolis treats this dedicated exception as a
    # rejected numerical proposal; exact Fraction proposals never reach it.
    if sum(candidate) > upper:
        raise NumericalSimplexDrift(
            "redistribution escaped simplex numerically")
    return candidate


def reverse_fraction(original, candidate, upper, pair):
    """Fraction which maps `candidate` back to `original` for the same pair."""
    n = len(original)
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ValueError("pair must contain exactly two indices")
    i, j = pair
    _exact_int(i, "pair index")
    _exact_int(j, "pair index")
    if not (0 <= i < j <= n) or len(candidate) != n:
        raise ValueError("invalid reverse pair or state dimension")
    old_augmented = list(original) + [simplex_slack(original, upper)]
    new_augmented = list(candidate) + [simplex_slack(candidate, upper)]
    total = new_augmented[i] + new_augmented[j]
    old_total = old_augmented[i] + old_augmented[j]
    if total != old_total:
        if isinstance(total, (int, Fraction)) and isinstance(
                old_total, (int, Fraction)):
            raise ArithmeticError("pair total changed")
        total_float = _finite_float(total, "new pair total")
        old_float = _finite_float(old_total, "old pair total")
        tolerance = 16 * max(math.ulp(total_float), math.ulp(old_float))
        if abs(total_float - old_float) > tolerance:
            raise ArithmeticError("pair total changed")
    if total == 0:
        return 0
    return old_augmented[i] / total


def metropolis_step(state, upper, log_density, support_predicate, rng=None,
                    *, density_power=1.0, pair=None, fraction=None,
                    log_uniform=None):
    """One Metropolis step reversible with respect to density^`density_power`."""
    _finite_float(density_power, "density power")
    if density_power < 0:
        raise ValueError("density power must be nonnegative")
    if rng is None:
        rng = random.Random()
    if log_uniform is not None:
        log_uniform = float(log_uniform)
        if math.isnan(log_uniform) or log_uniform > 0:
            raise ValueError("log_uniform must lie in [-inf,0]")
    n = len(state)
    if n == 0:
        raise ValueError("at least one physical coordinate is required")
    if pair is None:
        pair = tuple(sorted(rng.sample(range(n + 1), 2)))
    if fraction is None:
        fraction = rng.random()
    current_log = _log_value(log_density, state)
    try:
        candidate = redistribute_pair(state, upper, pair, fraction)
    except NumericalSimplexDrift:
        return StepResult(tuple(state), current_log, False, tuple(pair),
                          float(fraction), True)
    if not support_predicate(candidate):
        return StepResult(tuple(state), current_log, False, tuple(pair),
                          float(fraction), True)
    candidate_log = _log_value(log_density, candidate)
    if current_log == -math.inf and candidate_log == -math.inf:
        accept = density_power == 0
    elif current_log == -math.inf:
        accept = True
    elif candidate_log == -math.inf:
        accept = density_power == 0
    else:
        log_ratio = density_power * (candidate_log - current_log)
        if log_ratio >= 0:
            accept = True
        else:
            if log_uniform is None:
                draw = rng.random()
                if not 0 <= draw < 1:
                    raise ArithmeticError("rng.random() returned outside [0,1)")
                # random() may be exactly zero; that event should accept.
                log_uniform = -math.inf if draw == 0 else math.log(draw)
            accept = float(log_uniform) < log_ratio
    return StepResult(candidate if accept else tuple(state),
                      candidate_log if accept else current_log,
                      bool(accept), tuple(pair), float(fraction), False)


def run_chain(initial, upper, log_density, support_predicate, steps, seed,
              *, density_power=1.0, record_every=1):
    _exact_int(steps, "steps")
    _exact_int(record_every, "record_every")
    _finite_float(density_power, "density power")
    if steps < 0 or record_every <= 0 or density_power < 0:
        raise ValueError("invalid chain length or thinning")
    rng = random.Random(seed)
    state = tuple(initial)
    if not support_predicate(state):
        raise ValueError("initial state is outside support")
    current = _log_value(log_density, state)
    if current == -math.inf and density_power != 0:
        raise ValueError("initial state must have finite positive density")
    samples = []
    accepted = support_rejected = 0
    for iteration in range(steps):
        result = metropolis_step(
            state, upper, log_density, support_predicate, rng,
            density_power=density_power)
        state, current = result.state, result.log_density
        accepted += int(result.accepted)
        support_rejected += int(result.support_rejected)
        if (iteration + 1) % record_every == 0:
            samples.append(state)
    return {
        "samples": samples,
        "accepted": accepted,
        "support_rejected": support_rejected,
        "steps": steps,
        "record_every": record_every,
        "final_state": state,
        "final_log_density": current,
    }
