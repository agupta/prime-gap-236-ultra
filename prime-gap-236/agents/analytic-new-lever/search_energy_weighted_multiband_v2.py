#!/usr/bin/env python3
"""Fast discovery screen for energy-weighted outer-band schedules.

This is deliberately not an exact acceptance gate.  It mirrors the frozen
direct-HB fixed and 16x16 IIc tests in binary floating point and implements
the literal three-bin IIb action with every algebraic gamma breakpoint.
Its purpose is to find rationalization targets for a separate exact checker.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise ImportError(filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exact = load("energy_weighted_frozen_two_band", "verify_two_outer_band_v1.py")
one = load("energy_weighted_float_core", "search_adaptive_support.py")

DELTA = float(exact.CFG.delta)
H = one.H
ZETA = H / 1000
INWARD = H / 10
X = float(exact.CFG.x)
CELLS = 16


def e_capacity(omega: float, gamma: float) -> float:
    return (2 * omega + 9 * ZETA + 3 * gamma / 7 - 1 / 7
            - 24 * omega / 7 - H)


def action_ok(gamma: float, omega: float, action) -> bool:
    ql, qr, third, nl, nr, bl, br = action
    if e_capacity(omega, gamma) - third <= 2e-13:
        return False
    total = bl + br
    first = gamma - 3 * ZETA - INWARD
    if total < first - 2e-13:
        return True
    second = .5 - gamma - 2 * omega - 6 * ZETA - INWARD
    residual_groups = ((nl, bl), (nr, br))
    if (cross_pool_two_bin_ok(residual_groups, (first, second))
            or crossing_item_two_bin_ok(residual_groups, (first, second))):
        return True
    crossing = max(1, math.ceil((total - first) / DELTA - 2e-12))
    window = .5 - 2 * omega - 9 * ZETA - 2 * INWARD - total
    if window <= 2e-13:
        return False
    for count, bound in ((nl, bl), (nr, br), (nl + nr, total)):
        if count < crossing:
            continue
        tail = (bound / count if crossing == 1 else
                (bound - (crossing - 1) * DELTA)
                / (count - crossing + 1))
        if tail < window - 2e-13:
            return True
    return False


def three_bin_iib_ok(lc: int, rc: int, lb: float, rb: float,
                     omega: float) -> bool:
    """Exact-breakpoint topology, evaluated in float for discovery only."""
    low = 1 / 3 + 8 * omega + 7 * DELTA / 3 + 3 * H
    high = .4 + 24 * omega / 5 + 7 * DELTA / 5 + 2 * H
    emax = e_capacity(omega, high)
    actions = []
    points = {low, high}
    for ql in range(lc + 1):
        for qr in range(rc + 1):
            q = ql + qr
            if q > int(emax / DELTA + 1e-11):
                continue
            third = ((ql * lb / lc if ql else 0.0)
                     + (qr * rb / rc if qr else 0.0))
            if q and third >= emax - 2e-13:
                continue
            nl, nr = lc - ql, rc - qr
            bl = 0.0 if nl == 0 else lb - ql * DELTA
            br = 0.0 if nr == 0 else rb - qr * DELTA
            action = (ql, qr, third, nl, nr, bl, br)
            actions.append(action)
            if q:
                threshold = (7 * third + 1 + 10 * omega
                             - 63 * ZETA + 7 * H) / 3
                if low < threshold < high:
                    points.add(threshold)
            total = bl + br
            for crossing in range(nl + nr + 1):
                threshold = (total + 3 * ZETA + INWARD
                             - crossing * DELTA)
                if low < threshold < high:
                    points.add(threshold)
    ordered = sorted(points)
    tests = ordered + [(left + right) / 2
                       for left, right in zip(ordered, ordered[1:])]
    return all(any(action_ok(gamma, omega, action) for action in actions)
               for gamma in tests)


def schedule_ok(schedule) -> bool:
    return (min(schedule) > DELTA
            and all(-2e-13 <= schedule[i] - schedule[i - 1]
                    <= DELTA + 2e-13 for i in range(1, len(schedule))))


def family_ok(left, right, omega: float, dynamic: bool) -> bool:
    left_counts, right_counts = one.active(left, DELTA), one.active(right, DELTA)
    for lc in left_counts:
        for rc in right_counts:
            if lc + rc == 0:
                continue
            lb, rb = one.bound(left, lc), one.bound(right, rc)
            groups = ((lc, lb), (rc, rb))
            if not all(one.prefix_ok(groups, capacities, DELTA)
                       or cross_pool_two_bin_ok(groups, capacities)
                       or crossing_item_two_bin_ok(groups, capacities)
                       for capacities in one.fixed_capacities(DELTA, omega)):
                return False
            if not three_bin_iib_ok(lc, rc, lb, rb, omega):
                return False
    if not dynamic:
        return True
    gmin = .4 - H
    gmax = 1 / 3 + 8 * omega + 7 * DELTA / 3 + 3 * H
    if gmax < gmin:
        return True
    for lc in left_counts:
        for rc in right_counts:
            if lc + rc == 0:
                continue
            groups = ((lc, one.bound(left, lc)),
                      (rc, one.bound(right, rc)))
            for iw in range(CELLS):
                wl, wu = omega * iw / CELLS, omega * (iw + 1) / CELLS
                for ig in range(CELLS):
                    gl = gmin + (gmax - gmin) * ig / CELLS
                    gu = gmin + (gmax - gmin) * (ig + 1) / CELLS
                    capacities = (gl - 2 * DELTA - 8 * wu - H,
                                  .5 - gu - 2 * wu - H,
                                  4 * wl + DELTA - H, 8 * wl)
                    if not (one.prefix_ok(groups, capacities, DELTA)
                            or multi_prefix_ok(groups, capacities)):
                        return False
    return True


def cross_pool_two_bin_ok(groups, capacities) -> bool:
    """Put one whole pool plus q smallest of the other in one bin."""
    if len(capacities) != 2:
        return False
    for whole_index, split_index in ((0, 1), (1, 0)):
        whole_count, whole_bound = groups[whole_index]
        split_count, split_bound = groups[split_index]
        for first_bin, second_bin in ((0, 1), (1, 0)):
            for selected in range(split_count + 1):
                selected_upper = (selected * split_bound / split_count
                                  if selected else 0.0)
                residual_upper = (0.0 if selected == split_count else
                                  split_bound - selected * DELTA)
                if (whole_bound + selected_upper
                        < capacities[first_bin] - 2e-13
                        and residual_upper
                        < capacities[second_bin] - 2e-13):
                    return True
    return False


def crossing_item_two_bin_ok(groups, capacities) -> bool:
    """Least prefix over L, or its crossing item alone, fits bin two."""
    if len(capacities) != 2:
        return False
    total = sum(bound for _, bound in groups)
    overload = total - capacities[0]
    if overload < -2e-13:
        return True
    alternate = capacities[1]
    if alternate <= 2 * overload + 2e-13:
        return False
    crossing_max = max(1, math.ceil(overload / DELTA - 2e-12))
    for count, bound in (*groups, (sum(n for n, _ in groups), total)):
        if count < crossing_max:
            continue
        if all((bound - (j - 1) * DELTA) / (count - j + 1)
               < alternate - 2e-13
               for j in range(1, crossing_max + 1)):
            return True
    return False


def multi_prefix_ok(groups, capacities) -> bool:
    """Three alternate bins via consecutive blocks of a sorted pool.

    This is still evaluated in float here, but unlike the discovery-only
    three-bin-IIb routine the underlying sufficient lemma is elementary:
    after p smallest entries have been removed, the next q have sum at most
    q(B-p*delta)/(n-p).  Remove enough entries to make the first-bin reserve
    strict, and enumerate their allocation to the three alternate bins.
    """
    total_n = sum(count for count, _ in groups)
    total_b = sum(bound for _, bound in groups)
    if total_b < capacities[0] - 2e-13:
        return True
    overload = total_b - capacities[0]
    removed = math.floor(overload / DELTA + 2e-12) + 1
    pools = tuple(groups) + ((total_n, total_b),)
    for count, bound in pools:
        if count < removed:
            continue
        for first in range(removed + 1):
            for second in range(removed - first + 1):
                pieces = (first, second, removed - first - second)
                for order in itertools.permutations(range(1, 4)):
                    used = 0
                    valid = True
                    for size, capacity_index in zip(pieces, order):
                        if size:
                            upper = (size * (bound - used * DELTA)
                                     / (count - used))
                            if upper >= capacities[capacity_index] - 2e-13:
                                valid = False
                                break
                        used += size
                    if valid:
                        return True
    return False


def all_pairs_ok(schedules, endpoints) -> bool:
    if not all(schedule_ok(schedule) for schedule in schedules):
        return False
    inner = [float(value) for value in exact.core.inner_schedule(exact.CFG)]
    bands = [inner, *schedules]
    offsets = [0.0, *endpoints]
    for i in range(len(bands)):
        for j in range(len(bands)):
            if i == j == 0:
                continue
            omega = (offsets[i] + offsets[j]) / 2
            dynamic = (1 / 3 + 8 * omega + 7 * DELTA / 3 + 3 * H
                       >= .4 - H)
            if not family_ok(bands[i], bands[j], omega, dynamic):
                return False
    for left in schedules:
        for right in schedules:
            if not family_ok(left, right, 0.0, False):
                return False
    return True


def single_pairs_ok(schedule, endpoint: float) -> bool:
    if not schedule_ok(schedule):
        return False
    inner = [float(value) for value in exact.core.inner_schedule(exact.CFG)]
    cross = endpoint / 2
    for left, right, omega in (
            (inner, schedule, cross), (schedule, inner, cross),
            (schedule, schedule, endpoint)):
        dynamic = (1 / 3 + 8 * omega + 7 * DELTA / 3 + 3 * H
                   >= .4 - H)
        if not family_ok(left, right, omega, dynamic):
            return False
    return family_ok(schedule, schedule, 0.0, False)


def minimal_schedule(last_active: int, buffer: float = 2e-6):
    length = math.floor(1 / DELTA)
    return [min(index, last_active) * DELTA + buffer
            for index in range(1, length + 1)]


def raise_at(schedule, index: int, amount: float):
    answer = list(schedule)
    target = answer[index] + amount
    for j in range(index, -1, -1):
        answer[j] = max(answer[j], target - (index - j) * DELTA)
    for j in range(index + 1, len(answer)):
        answer[j] = max(answer[j], target)
    return answer


def optimize(split: float, upper_active: int, rounds: int):
    endpoints = [split * X, X]
    frozen = [float(value) for value in exact.core.outer_schedule(exact.CFG)]
    # The top-endpoint optimized schedule is not automatically legal at a
    # smaller mixed omega.  Start from the independently screened conservative
    # schedule, extended by its terminal plateau.
    conservative = list(one.extend(one.BASE_SCHEDULE, DELTA))
    schedules = [conservative, minimal_schedule(upper_active)]
    if not all_pairs_ok(schedules, endpoints):
        raise ArithmeticError("initial energy-weighted schedules fail")
    order = (4, 5, 6, 7, 4, 5, 6, 7, 3, 2, 1, 8, 9, 10, 11)
    for round_index in range(rounds):
        for count in order:
            lo, hi = 0.0, .04
            for _ in range(17):
                mid = (lo + hi) / 2
                trial = [raise_at(schedules[0], count - 1, mid), schedules[1]]
                if all_pairs_ok(trial, endpoints):
                    lo = mid
                else:
                    hi = mid
            if lo > 5e-8:
                schedules[0] = raise_at(schedules[0], count - 1,
                                        max(0.0, lo - 3e-7))
        print("round", round_index,
              ",".join(f"{value:.9f}" for value in schedules[0][:12]),
              flush=True)
        print("gains4-7", ",".join(
            f"{schedules[0][count - 1] - frozen[count - 1]:.9f}"
            for count in (4, 5, 6, 7)), flush=True)
    if not all_pairs_ok(schedules, endpoints):
        raise ArithmeticError("final screen failed")
    return schedules


def optimize_single(width: float, rounds: int, energy_order: bool = False):
    endpoint = width * X
    frozen = [float(value) for value in exact.core.outer_schedule(exact.CFG)]
    schedule = list(one.extend(one.BASE_SCHEDULE, DELTA))
    if not single_pairs_ok(schedule, endpoint):
        raise ArithmeticError("initial single-band schedule fails")
    order = ((3, 4, 2, 5, 3, 4, 2, 5, 1, 6, 7, 8, 9, 10, 11, 12)
             if energy_order else
             (4, 5, 6, 7, 4, 5, 6, 7, 3, 2, 1, 8, 9, 10, 11, 12))
    for round_index in range(rounds):
        for count in order:
            lo, hi = 0.0, .04
            for _ in range(17):
                mid = (lo + hi) / 2
                trial = raise_at(schedule, count - 1, mid)
                if single_pairs_ok(trial, endpoint):
                    lo = mid
                else:
                    hi = mid
            if lo > 5e-8:
                schedule = raise_at(schedule, count - 1,
                                    max(0.0, lo - 3e-7))
        print("round", round_index,
              ",".join(f"{value:.9f}" for value in schedule[:13]),
              flush=True)
        print("gains4-7", ",".join(
            f"{schedule[count - 1] - frozen[count - 1]:.9f}"
            for count in (4, 5, 6, 7)), flush=True)
    if not single_pairs_ok(schedule, endpoint):
        raise ArithmeticError("final single-band screen failed")
    return schedule


def optimize_single_from_minimal(width: float, rounds: int,
                                 count4_first: bool = False):
    """Discovery-only energy face, without inheriting irrelevant old caps.

    First move from the minimally active count-12 schedule toward the frozen
    lambda=37/40 schedule as far as feasibility allows.  Then spend remaining
    slack in the empirically important 3,4,2,5 counts before touching the
    low-energy tail.  This explores a different Pareto face than
    ``optimize_single``, whose old BASE_SCHEDULE can carry accidental slack.
    """
    endpoint = width * X
    target_head = tuple(value / 1e6 for value in (
        140375, 157041, 168544, 174338, 185488, 190375,
        193097, 197146, 202047, 207090, 211668, 211668))
    target = list(one.extend(target_head, DELTA))
    schedule = minimal_schedule(12)
    if not single_pairs_ok(schedule, endpoint):
        raise ArithmeticError("minimal active-12 schedule fails")

    # A common ray supplies a neutral feasible seed; feasibility is downward
    # closed for the cap inequalities, so binary search is appropriate here.
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        trial = [left + mid * (right - left)
                 for left, right in zip(schedule, target)]
        if single_pairs_ok(trial, endpoint):
            lo = mid
        else:
            hi = mid
    schedule = [left + max(0.0, lo - 2e-6) * (right - left)
                for left, right in zip(schedule, target)]

    order = ((4, 3, 5, 2, 4, 3, 5, 2, 4, 3,
              1, 6, 7, 8, 9, 10, 11, 12)
             if count4_first else
             (3, 4, 2, 5, 3, 4, 2, 5, 3, 4,
              1, 6, 7, 8, 9, 10, 11, 12))
    for round_index in range(rounds):
        for count in order:
            lo, hi = 0.0, .05
            for _ in range(18):
                mid = (lo + hi) / 2
                trial = raise_at(schedule, count - 1, mid)
                if single_pairs_ok(trial, endpoint):
                    lo = mid
                else:
                    hi = mid
            if lo > 5e-8:
                schedule = raise_at(schedule, count - 1,
                                    max(0.0, lo - 3e-7))
        print("minimal-round", round_index,
              ",".join(f"{value:.9f}" for value in schedule[:13]),
              flush=True)
    if not single_pairs_ok(schedule, endpoint):
        raise ArithmeticError("minimal energy face failed")
    return schedule


def main() -> None:
    global CELLS
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=float, default=.5)
    parser.add_argument("--upper-active", type=int, default=1,
                        choices=range(1, 13))
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--cells", type=int, default=16,
                        choices=(16, 24, 32, 48, 64))
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--energy-order", action="store_true")
    parser.add_argument("--minimal-energy-face", action="store_true")
    parser.add_argument("--count4-first", action="store_true")
    args = parser.parse_args()
    CELLS = args.cells
    if args.single:
        schedule = (optimize_single_from_minimal(
                        args.split, args.rounds,
                        count4_first=args.count4_first)
                    if args.minimal_energy_face else
                    optimize_single(args.split, args.rounds,
                                    energy_order=args.energy_order))
        print("single", ",".join(f"{value:.12f}"
                                for value in schedule[:13]))
        return
    schedules = optimize(args.split, args.upper_active, args.rounds)
    print("lower", ",".join(f"{value:.12f}" for value in schedules[0][:12]))
    print("upper", ",".join(f"{value:.12f}" for value in schedules[1][:12]))


if __name__ == "__main__":
    main()
