#!/usr/bin/env python3
"""Exact gate for a three-outer-band, energy-weighted support candidate.

The broad lower band spends three Type-IIc alternate capacities jointly.
The two narrow upper bands use deliberately small schedules.  Every ordered
band pair, zero-count edge case, exact Type-IIb gamma breakpoint, and closed
16x16 Type-IIc cell is checked with Fraction arithmetic.  This certifies only
the specialized analytic support conditions, never a projection or quotient.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
FROZEN_FILE = FILE.with_name("verify_two_outer_band_v1.py")
FROZEN_SHA256 = "187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001"

spec = importlib.util.spec_from_file_location("energy_v2_frozen_primitives",
                                              FROZEN_FILE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen exact primitives")
frozen = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = frozen
spec.loader.exec_module(frozen)
core = frozen.core


CFG = core.CANDIDATE
LOWER_HEAD = tuple(Q(value, 10**6) for value in (
    140375, 157041, 168544, 174338, 185488, 190375,
    193097, 197146, 202047, 207090, 211668, 211668))
SMALL_HEAD = (CFG.delta + Q(2, 10**6),)
ENDPOINTS = (
    core.A1,
    core.A1 + Q(37, 40) * CFG.x,
    core.A1 + Q(39, 40) * CFG.x,
    CFG.a2,
)
BAND_NAMES = ("inner", "lower_outer", "middle_outer", "top_outer")
CAP_RADIUS = Q(1, 10**7)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def positive(margins: dict[str, Q], key: str, value: Q) -> None:
    require(value > 0, f"nonpositive {key}: {value}")
    margins[key] = value


def schedules(lower_shift: Q = Q(0)) -> tuple[tuple[Q, ...], ...]:
    lower = core.extend(tuple(value + lower_shift for value in LOWER_HEAD),
                        CFG.delta)
    small = core.extend(SMALL_HEAD, CFG.delta)
    return core.inner_schedule(CFG), lower, small, small


def omega(i: int, j: int) -> Q:
    return (ENDPOINTS[i] + ENDPOINTS[j]) / 2 - core.A1


def definition1_check(lower_shift: Q = Q(0)) -> dict[str, object]:
    margins: dict[str, Q] = {}
    positive(margins, "epsilon", CFG.epsilon)
    positive(margins, "delta", CFG.delta)
    positive(margins, "A1-A0", core.A1 + CFG.epsilon)
    for index in range(1, len(ENDPOINTS)):
        positive(margins, f"A{index + 1}-A{index}",
                 ENDPOINTS[index] - ENDPOINTS[index - 1])
    positive(margins, "upper",
             Q(1, 2) - CFG.epsilon - ENDPOINTS[-1])
    expected = (tuple(range(16)), tuple(range(13)), (0, 1), (0, 1))
    active_counts = {}
    weak_steps = {}
    for name, schedule, inventory in zip(BAND_NAMES, schedules(lower_shift),
                                         expected):
        zeros = []
        for index, value in enumerate(schedule):
            positive(margins, f"{name}.B{index + 1}-delta",
                     value - CFG.delta)
            if index:
                step = value - schedule[index - 1]
                require(Q(0) <= step <= CFG.delta,
                        f"bad {name} step {index}->{index + 1}: {step}")
                if step == 0:
                    zeros.append(index + 1)
        actual = core.active(schedule, CFG.delta)
        require(actual == inventory, f"{name} active inventory {actual}")
        first_empty = actual[-1] + 1
        positive(margins, f"{name}.first-empty",
                 first_empty * CFG.delta - schedule[first_empty - 1])
        positive(margins, f"{name}.last-active",
                 schedule[actual[-1] - 1] - actual[-1] * CFG.delta)
        active_counts[name] = actual
        weak_steps[name] = zeros
    return {
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "active_counts": active_counts,
        "weak_plateau_steps": weak_steps,
        "margins": margins,
    }


def source_geometry_check() -> dict[str, object]:
    # Reuse only the frozen algebraic source-face evaluator, whose file and
    # transitive core are both hash-pinned.  It reads no result/proxy file.
    baseline = core.source_geometry_check(CFG)
    margins: dict[str, Q] = {}
    regimes = {}
    distinct = {Q(0)}
    for i in range(4):
        for j in range(4):
            if i != 0 or j != 0:
                distinct.add(omega(i, j))
    for index, value in enumerate(sorted(distinct)):
        label = f"omega_{index}"
        regimes[label] = {
            "omega": value,
            "IIc": frozen.source_at_omega(label, value, margins),
        }
    return {
        "frozen_endpoint_minimum": baseline["minimum_margin"],
        "all_regime_minimum": min(margins.values()),
        "all_regime_minimum_key": min(margins, key=margins.get),
        "distinct_omega_regimes": len(distinct),
        "regimes": regimes,
        "margins": margins,
    }


def e_capacity(omega_value: Q, gamma: Q) -> Q:
    return 2 * omega_value + 9 * core.ZETA + core.db(gamma, omega_value)


def three_bin_actions(lc: int, rc: int, lb: Q, rb: Q, omega_value: Q):
    emax = e_capacity(omega_value, core.ga(CFG, omega_value))
    max_q = min(lc + rc, int(emax // CFG.delta))
    answer = []
    for ql in range(lc + 1):
        for qr in range(rc + 1):
            q = ql + qr
            if q > max_q:
                continue
            third = ((Q(ql) * lb / lc if ql else Q(0))
                     + (Q(qr) * rb / rc if qr else Q(0)))
            if q and third >= emax:
                continue
            lcn, rcn = lc - ql, rc - qr
            lbn = Q(0) if lcn == 0 else lb - ql * CFG.delta
            rbn = Q(0) if rcn == 0 else rb - qr * CFG.delta
            require(lbn >= lcn * CFG.delta and rbn >= rcn * CFG.delta,
                    "invalid Type-IIb residual cap")
            answer.append((ql, qr, third, lcn, rcn, lbn, rbn))
    require(answer and answer[0][:2] == (0, 0),
            "empty Type-IIb third-bin action missing")
    return tuple(answer)


def cross_pool_two_bin_certificate(lc: int, rc: int, lb: Q, rb: Q,
                                   capacities: tuple[Q, Q]):
    """Put one whole pool and q smallest of the other into one bin."""
    groups = ((lc, lb), (rc, rb))
    choices = []
    for whole_index, split_index in ((0, 1), (1, 0)):
        _, whole_bound = groups[whole_index]
        split_count, split_bound = groups[split_index]
        for first_bin, second_bin in ((0, 1), (1, 0)):
            for selected in range(split_count + 1):
                selected_upper = (Q(selected) * split_bound / split_count
                                  if selected else Q(0))
                residual_upper = (Q(0) if selected == split_count else
                                  split_bound - selected * CFG.delta)
                first_margin = (capacities[first_bin] - whole_bound
                                - selected_upper)
                second_margin = capacities[second_bin] - residual_upper
                if first_margin > 0 and second_margin > 0:
                    choices.append((min(first_margin, second_margin),
                                    "cross-pool", whole_index, split_index,
                                    selected, first_bin, second_bin))
    require(choices, f"no cross-pool two-bin certificate at {lc},{rc}")
    return max(choices)


def crossing_item_two_bin_certificate(lc: int, rc: int, lb: Q, rb: Q,
                                      capacities: tuple[Q, Q]):
    """Use the least prefix over L, or use its crossing item alone.

    If a least prefix U_j>L already has U_j<D, move it.  Otherwise its
    crossing item y_j is greater than D-L>L when D>2L.  The sorted-tail
    average bounds below make y_j<D for every possible j, so moving y_j
    alone works.  This covers every real tuple represented by the caps.
    """
    total_n, total_b = lc + rc, lb + rb
    first, alternate = capacities
    if total_b < first:
        return first - total_b, "crossing-all-first", 0, 0
    overload = total_b - first
    crossing_max = max(1, core.ceilq(overload / CFG.delta))
    choices = []
    for pool, count, bound in (
            ("left", lc, lb), ("right", rc, rb),
            ("combined", total_n, total_b)):
        if count < crossing_max:
            continue
        tails = tuple((bound - (j - 1) * CFG.delta) / (count - j + 1)
                      for j in range(1, crossing_max + 1))
        margins = (alternate - 2 * overload,
                   *(alternate - tail for tail in tails))
        if min(margins) > 0:
            choices.append((min(margins), "crossing-item", pool,
                            crossing_max))
    require(choices, f"no crossing-item certificate at {lc},{rc}")
    return max(choices)


def enhanced_two_bin_certificate(lc: int, rc: int, lb: Q, rb: Q,
                                 capacities: tuple[Q, Q]):
    choices = []
    for mechanism in (
            lambda: core.fixed_prefix_certificate(
                CFG.delta, lc, rc, lb, rb, capacities),
            lambda: cross_pool_two_bin_certificate(
                lc, rc, lb, rb, capacities),
            lambda: crossing_item_two_bin_certificate(
                lc, rc, lb, rb, capacities)):
        try:
            choices.append(mechanism())
        except ArithmeticError:
            pass
    require(choices, f"no enhanced two-bin certificate at {lc},{rc}")
    return max(choices, key=lambda item: item[0])


def three_bin_action_at(omega_value: Q, gamma: Q, action):
    ql, qr, third, lc, rc, lb, rb = action
    third_margin = e_capacity(omega_value, gamma) - third
    if third_margin <= 0:
        return None
    total_b, total_n = lb + rb, lc + rc
    first = core.iib_c(CFG, gamma)
    if total_b < first:
        return min(third_margin, first - total_b), ql, qr, "all-first", 0
    try:
        two_bin = enhanced_two_bin_certificate(
            lc, rc, lb, rb,
            (first, core.iib_d(omega_value, gamma)))
    except ArithmeticError:
        return None
    return (min(third_margin, two_bin[0]), ql, qr,
            two_bin[1], two_bin[2:])


def three_bin_breakpoints(omega_value: Q, actions) -> tuple[Q, ...]:
    low, high = core.gb(CFG, omega_value), core.ga(CFG, omega_value)
    points = {low, high}
    for ql, qr, third, lc, rc, lb, rb in actions:
        if ql + qr:
            threshold = (7 * third + 1 + 10 * omega_value
                         - 63 * core.ZETA + 7 * core.H) / 3
            if low <= threshold <= high:
                points.add(threshold)
        total_b = lb + rb
        for crossing in range(lc + rc + 1):
            threshold = (total_b + 3 * core.ZETA + core.INWARD
                         - crossing * CFG.delta)
            if low <= threshold <= high:
                points.add(threshold)
        # Every additional enhanced-two-bin predicate is affine in gamma.
        # Including its equality point makes its truth value constant on each
        # resulting open interval, just as for the crossing-number predicates.
        groups = ((lc, lb), (rc, rb))
        for whole_index, split_index in ((0, 1), (1, 0)):
            _, whole_bound = groups[whole_index]
            split_count, split_bound = groups[split_index]
            for selected in range(split_count + 1):
                selected_upper = (Q(selected) * split_bound / split_count
                                  if selected else Q(0))
                residual_upper = (Q(0) if selected == split_count else
                                  split_bound - selected * CFG.delta)
                for amount in (whole_bound + selected_upper,
                               residual_upper):
                    point_c = amount + 3 * core.ZETA + core.INWARD
                    point_d = (Q(1, 2) - 2 * omega_value
                               - 6 * core.ZETA - core.INWARD - amount)
                    if low <= point_c <= high:
                        points.add(point_c)
                    if low <= point_d <= high:
                        points.add(point_d)
        # D(gamma)=2(S-C(gamma)) and D(gamma)=tail_j are precisely
        # the crossing-item predicate changes.
        point_double = (2 * total_b - Q(1, 2) + 2 * omega_value
                        + 12 * core.ZETA + 3 * core.INWARD)
        if low <= point_double <= high:
            points.add(point_double)
        for count, bound in (*groups, (lc + rc, total_b)):
            for j in range(1, count + 1):
                tail = ((bound - (j - 1) * CFG.delta)
                        / (count - j + 1))
                point_tail = (Q(1, 2) - 2 * omega_value
                              - 6 * core.ZETA - core.INWARD - tail)
                if low <= point_tail <= high:
                    points.add(point_tail)
    return tuple(sorted(points))


def three_bin_iib_certificate(lc: int, rc: int, lb: Q, rb: Q,
                              omega_value: Q):
    actions = three_bin_actions(lc, rc, lb, rb, omega_value)
    points = three_bin_breakpoints(omega_value, actions)
    tests = []
    for index, point in enumerate(points):
        tests.append(("endpoint", point, point, point))
        if index + 1 < len(points):
            right = points[index + 1]
            tests.append(("interval", point, right, (point + right) / 2))
    worst = None
    strategy_records = []
    mechanisms: dict[str, int] = {}
    records = nonempty = maximum_q = 0
    for kind, left, right, sample in tests:
        choices = [value for action in actions
                   if (value := three_bin_action_at(
                       omega_value, sample, action)) is not None]
        require(choices, f"uncovered IIb {kind} {lc},{rc} at {sample}")
        best = max(choices)
        item = (best[0], kind, left, right, *best[1:])
        worst = item if worst is None or item < worst else worst
        records += 1
        nonempty += best[1] + best[2] > 0
        maximum_q = max(maximum_q, best[1] + best[2])
        mechanisms[best[3]] = mechanisms.get(best[3], 0) + 1
        strategy_records.append((kind, left, right, *best))
    require(worst is not None and worst[0] > 0, "nonpositive IIb margin")
    return (worst, records, nonempty, maximum_q, mechanisms,
            hashlib.sha256(repr(strategy_records).encode("ascii")).hexdigest())


def sorted_three_block_certificate(lc: int, rc: int, lb: Q, rb: Q,
                                   capacities: tuple[Q, ...]):
    """Universal four-bin certificate using one sorted source pool.

    If p smallest entries of an n-pool have already been removed, its
    residual sum is at most B-p*delta.  Thus the next q smallest entries
    sum to at most q(B-p*delta)/(n-p).  Enumerating the three block sizes
    and their assignments to C2,C3,C4 is therefore exhaustive for this
    finite strategy family, while r*delta>S-C1 makes C1 strict.
    """
    require(len(capacities) == 4, "three-block certificate needs four bins")
    total_n, total_b = lc + rc, lb + rb
    if total_b < capacities[0]:
        return capacities[0] - total_b, "all-first", 0, (), ()
    overload = total_b - capacities[0]
    removed = int(overload // CFG.delta) + 1
    choices = []
    for pool, count, bound in (
            ("left", lc, lb), ("right", rc, rb),
            ("combined", total_n, total_b)):
        if count < removed:
            continue
        for first in range(removed + 1):
            for second in range(removed - first + 1):
                pieces = (first, second, removed - first - second)
                for order in itertools.permutations((1, 2, 3)):
                    used = 0
                    margins = [removed * CFG.delta - overload]
                    valid = True
                    for size, capacity_index in zip(pieces, order):
                        if size:
                            upper = (Q(size) * (bound - used * CFG.delta)
                                     / (count - used))
                            if upper >= capacities[capacity_index]:
                                valid = False
                                break
                            margins.append(capacities[capacity_index] - upper)
                        used += size
                    if valid:
                        choices.append((min(margins), pool, removed,
                                        pieces, order))
    require(choices, f"no sorted-three-block certificate at {lc},{rc}")
    return max(choices)


def dynamic_certificate(lc: int, rc: int, lb: Q, rb: Q,
                        capacities: tuple[Q, ...]):
    # Preserve the frozen one-alternate-bin lemma wherever it works.  Invoke
    # the new strategy only on cells for which that smaller proof fails.
    try:
        return "one-alternate", core.fixed_prefix_certificate(
            CFG.delta, lc, rc, lb, rb, capacities)
    except ArithmeticError:
        return "three-block", sorted_three_block_certificate(
            lc, rc, lb, rb, capacities)


def packing_check(lower_shift: Q = Q(0)) -> dict[str, object]:
    bands = schedules(lower_shift)
    fixed_worst = iib_worst = dynamic_worst = None
    main_pairs = near_pairs = fixed_checks = iib_records = 0
    iib_nonempty = iib_max_q = zero_left = zero_right = 0
    fixed_old_failures = fixed_enhanced_selected = 0
    fixed_mechanisms: dict[str, int] = {}
    iib_mechanisms: dict[str, int] = {}
    fixed_digest = hashlib.sha256()
    iib_hashes = []
    dynamic_digest = hashlib.sha256()
    family_inventory = {}
    for i in range(4):
        for j in range(4):
            if i == j == 0:
                continue
            pair_count = 0
            w = omega(i, j)
            for lc in core.active(bands[i], CFG.delta):
                for rc in core.active(bands[j], CFG.delta):
                    if lc + rc == 0:
                        continue
                    pair_count += 1
                    zero_left += lc == 0
                    zero_right += rc == 0
                    lb, rb = core.cap(bands[i], lc), core.cap(bands[j], rc)
                    for branch, capacities in core.fixed_capacities(CFG, w).items():
                        try:
                            core.fixed_prefix_certificate(
                                CFG.delta, lc, rc, lb, rb, capacities)
                        except ArithmeticError:
                            fixed_old_failures += 1
                        cert = enhanced_two_bin_certificate(
                            lc, rc, lb, rb, capacities)
                        fixed_enhanced_selected += cert[1] in (
                            "cross-pool", "crossing-item")
                        fixed_mechanisms[cert[1]] = (
                            fixed_mechanisms.get(cert[1], 0) + 1)
                        item = (cert[0], BAND_NAMES[i], BAND_NAMES[j],
                                lc, rc, branch, *cert[1:])
                        fixed_worst = (item if fixed_worst is None
                                       or item < fixed_worst else fixed_worst)
                        fixed_digest.update(repr(item).encode("ascii"))
                        fixed_checks += 1
                    (cert, records, nonempty, max_q, mechanisms,
                     strategy_hash) = three_bin_iib_certificate(
                         lc, rc, lb, rb, w)
                    item = (cert[0], BAND_NAMES[i], BAND_NAMES[j],
                            lc, rc, *cert[1:])
                    iib_worst = (item if iib_worst is None
                                 or item < iib_worst else iib_worst)
                    iib_records += records
                    iib_nonempty += nonempty
                    iib_max_q = max(iib_max_q, max_q)
                    for mechanism, count in mechanisms.items():
                        iib_mechanisms[mechanism] = (
                            iib_mechanisms.get(mechanism, 0) + count)
                    iib_hashes.append((BAND_NAMES[i], BAND_NAMES[j], lc, rc,
                                       strategy_hash))
            main_pairs += pair_count
            family_inventory[f"{BAND_NAMES[i]}--{BAND_NAMES[j]}"] = {
                "omega": w, "main_pairs": pair_count}

    for i in (1, 2, 3):
        for j in (1, 2, 3):
            pair_count = 0
            for lc in core.active(bands[i], CFG.delta):
                for rc in core.active(bands[j], CFG.delta):
                    if lc + rc == 0:
                        continue
                    pair_count += 1
                    lb, rb = core.cap(bands[i], lc), core.cap(bands[j], rc)
                    for branch, capacities in core.fixed_capacities(CFG, Q(0)).items():
                        try:
                            core.fixed_prefix_certificate(
                                CFG.delta, lc, rc, lb, rb, capacities)
                        except ArithmeticError:
                            fixed_old_failures += 1
                        cert = enhanced_two_bin_certificate(
                            lc, rc, lb, rb, capacities)
                        fixed_enhanced_selected += cert[1] in (
                            "cross-pool", "crossing-item")
                        fixed_mechanisms[cert[1]] = (
                            fixed_mechanisms.get(cert[1], 0) + 1)
                        item = (cert[0], f"near:{BAND_NAMES[i]}",
                                BAND_NAMES[j], lc, rc, branch, *cert[1:])
                        fixed_worst = (item if item < fixed_worst
                                       else fixed_worst)
                        fixed_digest.update(repr(item).encode("ascii"))
                        fixed_checks += 1
                    (cert, records, nonempty, max_q, mechanisms,
                     strategy_hash) = three_bin_iib_certificate(
                         lc, rc, lb, rb, Q(0))
                    item = (cert[0], f"near:{BAND_NAMES[i]}",
                            BAND_NAMES[j], lc, rc, *cert[1:])
                    iib_worst = item if item < iib_worst else iib_worst
                    iib_records += records
                    iib_nonempty += nonempty
                    iib_max_q = max(iib_max_q, max_q)
                    for mechanism, count in mechanisms.items():
                        iib_mechanisms[mechanism] = (
                            iib_mechanisms.get(mechanism, 0) + count)
                    iib_hashes.append((f"near:{BAND_NAMES[i]}",
                                       BAND_NAMES[j], lc, rc, strategy_hash))
            near_pairs += pair_count

    dynamic_pairs = dynamic_checks = one_cells = three_cells = 0
    gmin = Q(2, 5) - core.H
    for i in range(4):
        for j in range(4):
            if i == j == 0:
                continue
            w = omega(i, j)
            gmax = core.gb(CFG, w)
            if gmax < gmin:
                continue
            for lc in core.active(bands[i], CFG.delta):
                for rc in core.active(bands[j], CFG.delta):
                    if lc + rc == 0:
                        continue
                    dynamic_pairs += 1
                    lb, rb = core.cap(bands[i], lc), core.cap(bands[j], rc)
                    for iw in range(core.CELLS):
                        wl, wu = w * iw / core.CELLS, w * (iw + 1) / core.CELLS
                        for ig in range(core.CELLS):
                            gl = gmin + (gmax - gmin) * ig / core.CELLS
                            gu = gmin + (gmax - gmin) * (ig + 1) / core.CELLS
                            capacities = core.iic_capacities(
                                CFG, gl, gu, wl, wu)
                            mechanism, cert = dynamic_certificate(
                                lc, rc, lb, rb, capacities)
                            one_cells += mechanism == "one-alternate"
                            three_cells += mechanism == "three-block"
                            item = (cert[0], mechanism, BAND_NAMES[i],
                                    BAND_NAMES[j], lc, rc, iw, ig, *cert[1:])
                            dynamic_worst = (item if dynamic_worst is None
                                             or item < dynamic_worst
                                             else dynamic_worst)
                            dynamic_digest.update(repr(item).encode("ascii"))
                            dynamic_checks += 1

    require((main_pairs, near_pairs, fixed_checks) == (818, 280, 2196),
            "fixed global inventory")
    require((dynamic_pairs, dynamic_checks) == (280, 71680),
            "dynamic global inventory")
    require(one_cells + three_cells == dynamic_checks and three_cells > 0,
            "dynamic mechanism inventory")
    require(iib_nonempty > 0 and iib_max_q > 0,
            "nonempty Type-IIb third bin was not used")
    require(fixed_old_failures > 0 and
            iib_mechanisms.get("crossing-item", 0) > 0,
            "enhanced two-bin mechanisms were not genuinely used")
    require(fixed_worst is not None and fixed_worst[0] > 0,
            "fixed reserve")
    require(iib_worst is not None and iib_worst[0] > 0, "IIb reserve")
    require(dynamic_worst is not None and dynamic_worst[0] > 0,
            "dynamic reserve")
    return {
        "main_ordered_pairs": main_pairs,
        "near_ordered_pairs": near_pairs,
        "main_zero_left": zero_left,
        "main_zero_right": zero_right,
        "IIa_III_checks": fixed_checks,
        "IIa_III_old_prefix_failures": fixed_old_failures,
        "IIa_III_selected_enhanced": fixed_enhanced_selected,
        "IIa_III_selected_mechanisms": fixed_mechanisms,
        "IIa_III_strategy_sha256": fixed_digest.hexdigest(),
        "IIa_III_worst": fixed_worst,
        "IIb_endpoint_and_interval_records": iib_records,
        "IIb_selected_nonempty_third": iib_nonempty,
        "IIb_maximum_selected_q": iib_max_q,
        "IIb_selected_two_bin_mechanisms": iib_mechanisms,
        "IIb_strategy_sha256": hashlib.sha256(
            repr(iib_hashes).encode("ascii")).hexdigest(),
        "IIb_worst": iib_worst,
        "dynamic_pairs": dynamic_pairs,
        "dynamic_checks": dynamic_checks,
        "dynamic_one_alternate_cells": one_cells,
        "dynamic_required_three_block_cells": three_cells,
        "dynamic_strategy_sha256": dynamic_digest.hexdigest(),
        "dynamic_worst": dynamic_worst,
        "families": family_inventory,
    }


def targeted_open_witnesses() -> tuple[dict[str, object], ...]:
    total = (CFG.alpha1 + ENDPOINTS[1] + CFG.epsilon) / 2
    witnesses = []
    for count in (4, 5, 6, 7):
        old_cap = CFG.outer_head[count - 1]
        new_cap = LOWER_HEAD[count - 1]
        large_sum = (old_cap + new_cap) / 2
        large_coordinate = large_sum / count
        small_coordinate = (total - large_sum) / (48 - count)
        require(CFG.alpha1 < total < ENDPOINTS[1] + CFG.epsilon,
                "witness band interior")
        require(large_coordinate > CFG.delta > small_coordinate > 0,
                f"count-{count} classification")
        require(old_cap < large_sum < new_cap,
                f"count-{count} cap separation")
        witnesses.append({
            "count": count, "total_sum": total,
            "large_coordinate": large_coordinate,
            "small_coordinate": small_coordinate,
            "large_sum": large_sum, "old_cap": old_cap,
            "new_cap": new_cap,
            "old_violation": large_sum - old_cap,
            "new_slack": new_cap - large_sum,
        })
    return tuple(witnesses)


def stringify(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, tuple):
        return [stringify(item) for item in value]
    if isinstance(value, list):
        return [stringify(item) for item in value]
    if isinstance(value, dict):
        return {str(key): stringify(item) for key, item in value.items()}
    return value


def build() -> dict[str, object]:
    require(sha256(FROZEN_FILE) == FROZEN_SHA256,
            "frozen exact primitive file changed")
    require(sha256(frozen.CORE_FILE) == frozen.CORE_SHA256,
            "frozen exact core changed")
    for relative, expected in core.PINNED.items():
        require(sha256(core.REPO / relative) == expected,
                f"pinned source changed: {relative}")
    definition = definition1_check()
    source = source_geometry_check()
    packing = packing_check()
    # A small common enlargement of every broad-lower cap is checked at the
    # adverse endpoint.  Monotonicity then supplies the full open interval.
    lower_definition = definition1_check(-CAP_RADIUS)
    upper_definition = definition1_check(CAP_RADIUS)
    upper_packing = packing_check(CAP_RADIUS)
    proposition = core.proposition2_and_prop1_check(CFG)
    gains = tuple(new - old for new, old in zip(LOWER_HEAD,
                                                CFG.outer_head))
    require(all(gains[count - 1] > 0 for count in (4, 5, 6, 7)),
            "target gains disappeared")
    return stringify({
        "status": "EXACT THREE-OUTER-BAND ENERGY SUPPORT PASS",
        "scope": (
            "specialized direct-HB analytic support only; no Riesz energy "
            "lower bound, no quotient, and no bounded-gap theorem claim"),
        "checker_sha256": sha256(FILE),
        "frozen_primitive_sha256": FROZEN_SHA256,
        "parameters": {
            "k": 48, "delta": CFG.delta, "epsilon": CFG.epsilon,
            "A": (-CFG.epsilon, *ENDPOINTS),
            "alpha": tuple(value + CFG.epsilon for value in ENDPOINTS),
            "outer_width_fractions": (Q(37, 40), Q(1, 20), Q(1, 40)),
            "lower_schedule_through_first_empty": LOWER_HEAD,
            "middle_and_top_schedule_head": SMALL_HEAD,
            "lower_minus_frozen_caps": gains,
            "count_4_to_7_gains": {
                str(count): gains[count - 1] for count in (4, 5, 6, 7)},
        },
        "definition1": definition,
        "source_geometry": source,
        "ordered_pair_packing": packing,
        "proposition2_and_prop1": proposition,
        "strict_lower_cap_interval": {
            "radius": CAP_RADIUS,
            "lower_active": lower_definition["active_counts"]["lower_outer"],
            "upper_active": upper_definition["active_counts"]["lower_outer"],
            "upper_fixed_worst": upper_packing["IIa_III_worst"],
            "upper_IIb_worst": upper_packing["IIb_worst"],
            "upper_dynamic_worst": upper_packing["dynamic_worst"],
        },
        "strict_open_count_4_to_7_witnesses": targeted_open_witnesses(),
        "proof_lemmas": {
            "IIb": (
                "choose qL,qR smallest original-pool entries for E(gamma); "
                "their sum is bounded by qL*BL/nL+qR*BR/nR, residual caps "
                "are Bi-qi*delta, and all E/crossing changes are exact "
                "rational breakpoints"),
            "IIc": (
                "after p sorted removals from an n-pool of cap B, the next "
                "q smallest sum to at most q(B-p*delta)/(n-p); enumerate "
                "three consecutive block sizes and all assignments to the "
                "three alternate adverse cell capacities"),
        },
        "energy_status": (
            "cap geometry was targeted at counts 4--7, but no Riesz-shell "
            "projection or energy value is an input to this exact gate"),
        "decision": (
            "a legal broad lower band gains cap room in counts 4--7 by "
            "jointly spending the three repaired-IIc alternate capacities; "
            "two narrow upper bands are deliberately restricted"),
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"))
               + "\n").encode("ascii")
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
