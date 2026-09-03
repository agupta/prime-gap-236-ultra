#!/usr/bin/env python3
"""Exact analytic gate for a two-outer-band delta=1/60 support.

The lower outer band occupies nine tenths of the outer total-sum width and
has its own nonuniform cap schedule, targeted at counts 4--7.  The upper
tenth retains the frozen single-band schedule.  Every ordered band pair,
including either tuple count being zero, is checked at its exact
omega=(A_i+A_j)/2-1/4.  This is an analytic support certificate only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
CORE_FILE = FILE.with_name("verify_adaptive_support_v1.py")
CORE_SHA256 = "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d"

spec = importlib.util.spec_from_file_location("two_band_exact_core", CORE_FILE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load frozen exact core")
core = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = core
spec.loader.exec_module(core)


CFG = core.CANDIDATE
LOWER_A = core.A1 + Q(9, 10) * CFG.x       # 256241/1000000
LOWER_ALPHA = LOWER_A + CFG.epsilon        # 263741/1000000
LOWER_HEAD = tuple(Q(value, 10**6) for value in (
    139683, 156347, 157797, 173014, 180929, 183753,
    186776, 188864, 190396, 191607, 192583, 199985))
CAP_RADIUS = Q(1, 10**6)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def positive(margins: dict[str, Q], key: str, value: Q) -> None:
    require(value > 0, f"nonpositive {key}: {value}")
    margins[key] = value


def lower_schedule(shift: Q = Q(0)) -> tuple[Q, ...]:
    return core.extend(tuple(value + shift for value in LOWER_HEAD), CFG.delta)


def schedules(shift: Q = Q(0)) -> tuple[tuple[Q, ...], ...]:
    return (core.inner_schedule(CFG), lower_schedule(shift),
            core.outer_schedule(CFG))


ENDPOINTS = (core.A1, LOWER_A, CFG.a2)
BAND_NAMES = ("inner", "lower_outer", "upper_outer")


def omega(i: int, j: int) -> Q:
    return (ENDPOINTS[i] + ENDPOINTS[j]) / 2 - core.A1


def definition1_check(shift: Q = Q(0)) -> dict[str, object]:
    margins: dict[str, Q] = {}
    positive(margins, "epsilon", CFG.epsilon)
    positive(margins, "delta", CFG.delta)
    positive(margins, "A1-A0", core.A1 + CFG.epsilon)
    positive(margins, "lower-A1", LOWER_A - core.A1)
    positive(margins, "A2-lower", CFG.a2 - LOWER_A)
    positive(margins, "upper", Q(1, 2) - CFG.epsilon - CFG.a2)
    expected = (tuple(range(16)), tuple(range(12)), tuple(range(12)))
    equal_steps = {}
    for name, schedule, inventory in zip(BAND_NAMES, schedules(shift), expected):
        zeros = []
        for index, value in enumerate(schedule):
            positive(margins, f"{name}.B{index + 1}-delta",
                     value - CFG.delta)
            if index:
                step = value - schedule[index - 1]
                require(0 <= step <= CFG.delta,
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
        equal_steps[name] = zeros
    return {
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "active_counts": {name: core.active(schedule, CFG.delta)
                          for name, schedule in zip(BAND_NAMES, schedules(shift))},
        "weak_plateau_steps": equal_steps,
        "lower_first_empty_margin": 12 * CFG.delta - lower_schedule(shift)[11],
    }


def source_at_omega(label: str, w: Q, margins: dict[str, Q]) -> str:
    """Reconstruct every direct-HB source face at one exact band-pair omega."""
    g_a, g_b = core.ga(CFG, w), core.gb(CFG, w)
    positive(margins, f"{label}.IIa-range", Q(1, 2) - g_a)
    positive(margins, f"{label}.IIb-range", g_a - g_b)
    positive(margins, f"{label}.IIa-width",
             core.da(g_a, w) - 2 * core.INWARD - CFG.delta)
    positive(margins, f"{label}.IIa-face1",
             -2 - (24 * w + 7 * core.da(g_a, w) - 5 * g_a))
    positive(margins, f"{label}.IIa-face2",
             -(8 * w + 3 * core.da(Q(1, 2), w) - Q(1, 2)))
    positive(margins, f"{label}.IIa-a1",
             g_a - 3 * core.ZETA - core.da(g_a, w) + core.INWARD)
    iia = core.fixed_capacities(CFG, w)["IIa"]
    positive(margins, f"{label}.IIa-C1-domination",
             g_a - 3 * core.ZETA - core.INWARD - iia[0])
    positive(margins, f"{label}.IIa-C2-domination",
             Q(1, 14) - Q(24, 7) * w - core.H - core.INWARD - iia[1])

    db_low, db_high = core.db(g_b, w), core.db(g_a, w)
    positive(margins, f"{label}.IIb-width",
             db_low - 2 * core.INWARD - CFG.delta)
    positive(margins, f"{label}.IIb-face1",
             -1 - (24 * w + 7 * db_low - 3 * g_b))
    positive(margins, f"{label}.IIb-face2",
             -(8 * w + 3 * db_high - g_a))
    positive(margins, f"{label}.IIb-a1",
             g_b - 3 * core.ZETA - db_low + core.INWARD)
    positive(margins, f"{label}.IIb-a2",
             Q(1, 2) - g_a - 2 * w - 6 * core.ZETA
             - db_high + core.INWARD)
    positive(margins, f"{label}.IIb-bsum", 2 * w + 2 * core.INWARD)
    positive(margins, f"{label}.IIb-third-min",
             CFG.delta + 2 * w + Q(2, 7) * core.H + 9 * core.ZETA)

    gamma3 = Q(2, 5) - core.HB_SLACK
    d3 = Q(1, 2) - Q(7, 2) * w - Q(9, 8) * gamma3 - core.H
    positive(margins, f"{label}.III-width", d3 - 2 * core.H - CFG.delta)
    positive(margins, f"{label}.III-main",
             4 - (28 * w + 9 * gamma3 + 8 * d3))
    positive(margins, f"{label}.III-second",
             4 - (16 * w + 9 * gamma3 + 2 * d3))
    positive(margins, f"{label}.III-third",
             4 - (28 * w + 9 * gamma3 - d3))
    positive(margins, f"{label}.III-S-lower", 1 - 4 * w + 4 * d3)
    positive(margins, f"{label}.III-S-upper", 1 - 2 * d3 + 8 * w)
    positive(margins, f"{label}.III-omega", Q(1, 12) - w)
    a3 = Q(1, 3) + d3 / 3 - Q(4, 3) * w
    b3 = Q(1, 3) + Q(4, 3) * d3 - Q(4, 3) * w
    positive(margins, f"{label}.III-a", a3 + core.H)
    positive(margins, f"{label}.III-b", Q(1, 2) - (b3 - core.H))

    sigma = Q(1, 10) + core.HB_SLACK
    average_a = core.A1 + w
    qexp = Q(1, 2) + 2 * w
    positive(margins, f"{label}.Type0-sharp",
             1 - ((Q(1, 2) - sigma) + qexp))
    positive(margins, f"{label}.Type0-Poisson",
             1 - (1 - 2 * sigma + 4 * w))
    positive(margins, f"{label}.prime-square", 1 - qexp)
    positive(margins, f"{label}.higher-prime-powers", 1 - qexp - Q(1, 3))
    positive(margins, f"{label}.direct-II-19/2",
             Q(19, 2) - 36 * average_a - 13 * CFG.delta + 100 * core.H)
    positive(margins, f"{label}.direct-II-first",
             Q(21, 25) - Q(16, 5) * average_a - 2 * core.H - CFG.delta)
    positive(margins, f"{label}.direct-II-second",
             Q(63, 80) - 3 * average_a - 2 * core.H - CFG.delta)

    gmin = Q(2, 5) - core.H
    if g_b < gmin:
        positive(margins, f"{label}.IIc-empty", gmin - g_b)
        return "empty"
    d = CFG.iic_aux
    positive(margins, f"{label}.IIc-range", g_b - gmin)
    positive(margins, f"{label}.IIc-width", d - 2 * core.INWARD - CFG.delta)
    positive(margins, f"{label}.IIc-face1", 1 - (8 * w + 4 * d + 2 * g_b))
    positive(margins, f"{label}.IIc-face2", gmin - (32 * w + 10 * d))
    positive(margins, f"{label}.IIc-face3", 4 * gmin - 48 * w - 16 * d - 1)
    positive(margins, f"{label}.IIc-proof-start", gmin - 4 * w - d)
    positive(margins, f"{label}.IIc-a1", gmin - 3 * core.ZETA - d + core.INWARD)
    positive(margins, f"{label}.IIc-a2",
             Q(1, 2) - g_b - 2 * w - 6 * core.ZETA - d + core.INWARD)
    positive(margins, f"{label}.IIc-b1",
             Q(1, 2) - g_b + 3 * core.ZETA + core.INWARD)
    positive(margins, f"{label}.IIc-structural", 2 * (d - 2 * core.INWARD))
    positive(margins, f"{label}.IIc-C1-domination",
             core.H - 2 * (d - CFG.delta) - 58 * core.ZETA + core.INWARD)
    positive(margins, f"{label}.IIc-C2-domination",
             core.H - 6 * core.ZETA - core.INWARD)
    positive(margins, f"{label}.IIc-C3-domination", d - CFG.delta + core.H)
    positive(margins, f"{label}.IIc-C4-domination", 2 * core.INWARD)
    return "nonempty"


def source_geometry_check() -> dict[str, object]:
    # First rerun the frozen single-band source gate; this includes the HB
    # containment, Proposition-3 scalar diagnostics, and endpoint identities.
    frozen = core.source_geometry_check(CFG)
    margins: dict[str, Q] = {}
    regimes = {}
    distinct = {}
    for i in range(3):
        for j in range(3):
            if i == j == 0:
                continue
            w = omega(i, j)
            distinct.setdefault(w, f"omega_{len(distinct)}")
    distinct.setdefault(Q(0), "near")
    for w, label in distinct.items():
        regimes[label] = {"omega": w,
                          "IIc": source_at_omega(label, w, margins)}
    return {
        "frozen_core_minimum": frozen["minimum_margin"],
        "new_omega_minimum": min(margins.values()),
        "new_omega_minimum_key": min(margins, key=margins.get),
        "regimes": regimes, "margins": margins,
    }


def packing_check(shift: Q = Q(0)) -> dict[str, object]:
    bands = schedules(shift)
    fixed_worst = iib_worst = dynamic_worst = None
    fixed_checks = iib_crossings = dynamic_checks = 0
    main_pairs = near_pairs = dynamic_pairs = 0
    family_inventory = {}
    zero_left = zero_right = 0

    for i in range(3):
        for j in range(3):
            if i == j == 0:
                continue
            w = omega(i, j)
            pair_count = 0
            for m in core.active(bands[i], CFG.delta):
                for n in core.active(bands[j], CFG.delta):
                    if m + n == 0:
                        continue
                    pair_count += 1
                    zero_left += m == 0
                    zero_right += n == 0
                    bm, bn = core.cap(bands[i], m), core.cap(bands[j], n)
                    for branch, capacities in core.fixed_capacities(CFG, w).items():
                        cert = core.fixed_prefix_certificate(
                            CFG.delta, m, n, bm, bn, capacities)
                        item = (cert[0], BAND_NAMES[i], BAND_NAMES[j],
                                m, n, branch, *cert[1:])
                        fixed_worst = (item if fixed_worst is None or
                                       item < fixed_worst else fixed_worst)
                        fixed_checks += 1
                    cert = core.empty_third_uniform_iib_certificate(
                        CFG, m, n, bm, bn, w)
                    item = (cert[0], BAND_NAMES[i], BAND_NAMES[j],
                            m, n, *cert[1:])
                    iib_worst = item if iib_worst is None or item < iib_worst else iib_worst
                    max_overload = bm + bn - core.iib_c(CFG, core.gb(CFG, w))
                    iib_crossings += (0 if max_overload < 0 else
                                      max(1, core.ceilq(max_overload / CFG.delta)))
            expected = (len(core.active(bands[i], CFG.delta))
                        * len(core.active(bands[j], CFG.delta)) - 1)
            require(pair_count == expected, "main ordered pair inventory")
            main_pairs += pair_count
            family_inventory[f"{BAND_NAMES[i]}--{BAND_NAMES[j]}"] = {
                "omega": w, "main_pairs": pair_count}

    # Every ordered outer/outer band pair also occurs in the near-square-root
    # strip, where the specialized route uses omega=0 and IIc is empty.
    for i in (1, 2):
        for j in (1, 2):
            pairs = 0
            for m in core.active(bands[i], CFG.delta):
                for n in core.active(bands[j], CFG.delta):
                    if m + n == 0:
                        continue
                    pairs += 1
                    bm, bn = core.cap(bands[i], m), core.cap(bands[j], n)
                    for branch, capacities in core.fixed_capacities(CFG, Q(0)).items():
                        cert = core.fixed_prefix_certificate(
                            CFG.delta, m, n, bm, bn, capacities)
                        item = (cert[0], f"near:{BAND_NAMES[i]}",
                                BAND_NAMES[j], m, n, branch, *cert[1:])
                        fixed_worst = (item if fixed_worst is None or
                                       item < fixed_worst else fixed_worst)
                        fixed_checks += 1
                    cert = core.empty_third_uniform_iib_certificate(
                        CFG, m, n, bm, bn, Q(0))
                    item = (cert[0], f"near:{BAND_NAMES[i]}",
                            BAND_NAMES[j], m, n, *cert[1:])
                    iib_worst = item if iib_worst is None or item < iib_worst else iib_worst
                    max_overload = bm + bn - core.iib_c(CFG, core.gb(CFG, Q(0)))
                    iib_crossings += (0 if max_overload < 0 else
                                      max(1, core.ceilq(max_overload / CFG.delta)))
            near_pairs += pairs

    # Apply the exact adverse-endpoint 16x16 cover to every main pair whose
    # IIc gamma interval is nonempty; do not assume this is only top/top.
    gmin = Q(2, 5) - core.H
    for i in range(3):
        for j in range(3):
            if i == j == 0:
                continue
            w = omega(i, j)
            gmax = core.gb(CFG, w)
            if gmax < gmin:
                continue
            for m in core.active(bands[i], CFG.delta):
                for n in core.active(bands[j], CFG.delta):
                    if m + n == 0:
                        continue
                    dynamic_pairs += 1
                    bm, bn = core.cap(bands[i], m), core.cap(bands[j], n)
                    for iw in range(core.CELLS):
                        wl, wu = w * iw / core.CELLS, w * (iw + 1) / core.CELLS
                        for ig in range(core.CELLS):
                            gl = gmin + (gmax - gmin) * ig / core.CELLS
                            gu = gmin + (gmax - gmin) * (ig + 1) / core.CELLS
                            capacities = core.iic_capacities(CFG, gl, gu, wl, wu)
                            cert = core.fixed_prefix_certificate(
                                CFG.delta, m, n, bm, bn, capacities)
                            item = (cert[0], BAND_NAMES[i], BAND_NAMES[j],
                                    m, n, iw, ig, *cert[1:])
                            dynamic_worst = (item if dynamic_worst is None or
                                             item < dynamic_worst else dynamic_worst)
                            dynamic_checks += 1

    require((main_pairs, near_pairs, fixed_checks) == (1336, 572, 3816),
            "global fixed inventory")
    require((dynamic_pairs, dynamic_checks) == (572, 146432),
            "global dynamic inventory")
    require((zero_left, zero_right) == (96, 96), "zero-count main inventory")
    require(fixed_worst is not None and fixed_worst[0] > 0, "fixed reserve")
    require(iib_worst is not None and iib_worst[0] > 0, "IIb reserve")
    require(dynamic_worst is not None and dynamic_worst[0] > 0, "IIc reserve")
    return {
        "main_ordered_pairs": main_pairs, "near_ordered_pairs": near_pairs,
        "main_zero_left": zero_left, "main_zero_right": zero_right,
        "IIa_III_checks": fixed_checks, "IIa_III_worst": fixed_worst,
        "IIb_crossing_number_checks": iib_crossings,
        "IIb_uniform_empty_third_worst": iib_worst,
        "dynamic_pairs": dynamic_pairs, "dynamic_checks": dynamic_checks,
        "dynamic_worst": dynamic_worst,
        "families": family_inventory,
    }


def exact_volume_diagnostic() -> dict[str, object]:
    lower_cfg = core.Config(
        "lower_outer_volume", CFG.delta, CFG.epsilon, LOWER_A,
        LOWER_HEAD, 11)
    lower_volume, lower_rows = core.exact_shell_volume(lower_cfg)
    upper_rows = tuple(
        core.exact_stratum_volume(CFG, CFG.alpha2, count)
        - core.exact_stratum_volume(CFG, LOWER_ALPHA, count)
        for count in range(12))
    upper_volume = sum(upper_rows, Q(0))
    single_volume, single_rows = core.exact_shell_volume(CFG)
    total = lower_volume + upper_volume
    return {
        "lower_band_volume": lower_volume, "upper_band_volume": upper_volume,
        "two_band_volume": total, "single_band_volume": single_volume,
        "two_over_single": total / single_volume,
        "two_over_single_decimal": core.decimal_string(total / single_volume),
        "relative_gain_decimal": core.decimal_string(
            (total - single_volume) / single_volume),
        "meaning": (
            "exact constant-function shell Lebesgue volume only; secondary "
            "geometry diagnostic, not a D18 projection or quotient"),
        "lower_nonzero_rows": sum(value > 0 for value in lower_rows),
        "upper_nonzero_rows": sum(value > 0 for value in upper_rows),
        "single_nonzero_rows": sum(value > 0 for value in single_rows),
    }


def targeted_open_witnesses() -> tuple[dict[str, object], ...]:
    """Exhibit positive-measure new lower-band regions at counts 4--7."""
    total = (CFG.alpha1 + LOWER_ALPHA) / 2
    witnesses = []
    for count in (4, 5, 6, 7):
        old_cap = CFG.outer_head[count - 1]
        new_cap = LOWER_HEAD[count - 1]
        large_sum = (old_cap + new_cap) / 2
        large_coordinate = large_sum / count
        small_coordinate = (total - large_sum) / (48 - count)
        require(CFG.alpha1 < total < LOWER_ALPHA, "witness band interior")
        require(large_coordinate > CFG.delta > small_coordinate > 0,
                f"count-{count} witness classification")
        require(old_cap < large_sum < new_cap,
                f"count-{count} witness cap separation")
        witnesses.append({
            "count": count, "total_sum": total,
            "large_coordinate": large_coordinate,
            "small_coordinate": small_coordinate,
            "large_sum": large_sum, "frozen_cap": old_cap,
            "two_band_cap": new_cap,
            "frozen_violation": large_sum - old_cap,
            "new_slack": new_cap - large_sum,
        })
    return tuple(witnesses)


def stringify(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, tuple):
        return [stringify(x) for x in value]
    if isinstance(value, list):
        return [stringify(x) for x in value]
    if isinstance(value, dict):
        return {str(k): stringify(v) for k, v in value.items()}
    return value


def build() -> dict[str, object]:
    require(sha256(CORE_FILE) == CORE_SHA256, "frozen exact core changed")
    for relative, expected in core.PINNED.items():
        require(sha256(core.REPO / relative) == expected,
                f"pinned source dependency changed: {relative}")
    definition = definition1_check()
    source = source_geometry_check()
    packing = packing_check()
    # A common +radius move of every lower-band cap is the monotone adverse
    # endpoint for the whole interval |t|<=radius.
    lower_endpoint = definition1_check(-CAP_RADIUS)
    upper_endpoint = definition1_check(CAP_RADIUS)
    upper_packing = packing_check(CAP_RADIUS)
    prop = core.proposition2_and_prop1_check(CFG)
    gains = tuple(low - high for low, high in zip(LOWER_HEAD, CFG.outer_head))
    require(all(gains[count - 1] > 0 for count in (4, 5, 6, 7)),
            "target count gains disappeared")
    return stringify({
        "status": "EXACT TWO-OUTER-BAND ANALYTIC SUPPORT PASS",
        "scope": (
            "specialized direct-HB analytic support only; no D18 projection "
            "lower bound, no Rayleigh quotient, and no H1 theorem claim"),
        "checker_sha256": sha256(FILE), "frozen_core_sha256": CORE_SHA256,
        "parameters": {
            "k": 48, "delta": CFG.delta, "epsilon": CFG.epsilon,
            "A": (-CFG.epsilon, core.A1, LOWER_A, CFG.a2),
            "alpha": (CFG.alpha1, LOWER_ALPHA, CFG.alpha2),
            "lower_width_fraction_of_outer": Q(9, 10),
            "lower_schedule_through_first_empty": LOWER_HEAD,
            "upper_schedule_through_first_empty": CFG.outer_head,
            "lower_minus_upper_caps": gains,
            "count_4_to_7_gains": {str(count): gains[count - 1]
                                    for count in (4, 5, 6, 7)}},
        "definition1": definition, "source_geometry": source,
        "ordered_pair_packing": packing,
        "proposition2_and_prop1": prop,
        "strict_lower_cap_interval": {
            "radius": CAP_RADIUS,
            "lower_active": lower_endpoint["active_counts"]["lower_outer"],
            "upper_active": upper_endpoint["active_counts"]["lower_outer"],
            "upper_fixed_worst": upper_packing["IIa_III_worst"],
            "upper_IIb_worst": upper_packing["IIb_uniform_empty_third_worst"],
            "upper_dynamic_worst": upper_packing["dynamic_worst"],
            "reason": (
                "Definition-1 steps are invariant under common translation; "
                "packing is monotone in the lower-band tuple caps")},
        "strict_open_count_4_to_7_support_witnesses": targeted_open_witnesses(),
        "exact_volume_diagnostic_not_objective": exact_volume_diagnostic(),
        "tradeoff": (
            "the lower band raises every cap B4 through B7 but lowers B3 by "
            "865/10^6; an exact capped D18 projection calculation is still "
            "required to decide whether this geometric exchange is useful"),
        "decision": (
            "a legal two-band support reallocates analytic cap room toward "
            "counts 4--7 over nine tenths of the outer total-sum width"),
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
