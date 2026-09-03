#!/usr/bin/env python3
"""Exact gate for the truncated inner-plus-one-wide-outer support.

This removes the two narrow upper bands from the v2 construction and checks
the remaining support from scratch over its complete ordered-pair inventory.
It is an analytic support certificate only; the single outer band is intended
for a separate Definition-5 Riesz-energy computation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
V2_FILE = FILE.with_name("verify_three_outer_energy_v2.py")
V2_SHA256 = "87747ad848c502e4d0047d60ca324d77ba94c9b0f5cb2afd6b5d46b953575605"

spec = importlib.util.spec_from_file_location("truncated_energy_v3_primitives",
                                              V2_FILE)
if spec is None or spec.loader is None:
    raise ImportError("cannot load v2 exact primitives")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)
core = v2.core
CFG = v2.CFG

ENDPOINT = v2.ENDPOINTS[1]
ETA_OUTER = ENDPOINT - CFG.epsilon
BAND_NAMES = ("inner", "wide_outer")
CAP_RADIUS = v2.CAP_RADIUS


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def positive(margins: dict[str, Q], key: str, value: Q) -> None:
    require(value > 0, f"nonpositive {key}: {value}")
    margins[key] = value


def schedules(shift: Q = Q(0)) -> tuple[tuple[Q, ...], ...]:
    return (core.inner_schedule(CFG),
            core.extend(tuple(value + shift for value in v2.LOWER_HEAD),
                        CFG.delta))


def omega(i: int, j: int) -> Q:
    endpoints = (core.A1, ENDPOINT)
    return (endpoints[i] + endpoints[j]) / 2 - core.A1


def definition1_check(shift: Q = Q(0)) -> dict[str, object]:
    margins: dict[str, Q] = {}
    positive(margins, "epsilon", CFG.epsilon)
    positive(margins, "delta", CFG.delta)
    positive(margins, "A1-A0", core.A1 + CFG.epsilon)
    positive(margins, "A2-A1", ENDPOINT - core.A1)
    positive(margins, "upper", Q(1, 2) - CFG.epsilon - ENDPOINT)
    expected = (tuple(range(16)), tuple(range(13)))
    actual = {}
    weak_steps = {}
    for name, schedule, inventory in zip(BAND_NAMES, schedules(shift), expected):
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
        counts = core.active(schedule, CFG.delta)
        require(counts == inventory, f"bad {name} active inventory {counts}")
        first_empty = counts[-1] + 1
        positive(margins, f"{name}.first-empty",
                 first_empty * CFG.delta - schedule[first_empty - 1])
        positive(margins, f"{name}.last-active",
                 schedule[counts[-1] - 1] - counts[-1] * CFG.delta)
        actual[name] = counts
        weak_steps[name] = zeros
    return {
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "active_counts": actual,
        "weak_plateau_steps": weak_steps,
        "margins": margins,
    }


def source_geometry_check() -> dict[str, object]:
    margins: dict[str, Q] = {}
    regimes = {}
    for index, value in enumerate((Q(0), (ENDPOINT - core.A1) / 2,
                                   ENDPOINT - core.A1)):
        label = f"omega_{index}"
        regimes[label] = {
            "omega": value,
            "IIc": v2.frozen.source_at_omega(label, value, margins),
        }
    return {
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "regimes": regimes,
        "margins": margins,
    }


def packing_check(shift: Q = Q(0)) -> dict[str, object]:
    bands = schedules(shift)
    fixed_worst = iib_worst = dynamic_worst = None
    fixed_checks = main_pairs = near_pairs = zero_left = zero_right = 0
    fixed_old_failures = fixed_enhanced = 0
    iib_records = iib_nonempty = iib_max_q = 0
    iib_mechanisms: dict[str, int] = {}
    fixed_digest = hashlib.sha256()
    iib_hashes = []
    dynamic_digest = hashlib.sha256()

    for i, j in ((0, 1), (1, 0), (1, 1)):
        w = omega(i, j)
        pair_count = 0
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
                    cert = v2.enhanced_two_bin_certificate(
                        lc, rc, lb, rb, capacities)
                    fixed_enhanced += cert[1] in ("cross-pool",
                                                   "crossing-item")
                    item = (cert[0], BAND_NAMES[i], BAND_NAMES[j], lc, rc,
                            branch, *cert[1:])
                    fixed_worst = (item if fixed_worst is None
                                   or item < fixed_worst else fixed_worst)
                    fixed_digest.update(repr(item).encode("ascii"))
                    fixed_checks += 1
                (cert, records, nonempty, max_q, mechanisms,
                 strategy_hash) = v2.three_bin_iib_certificate(
                     lc, rc, lb, rb, w)
                item = (cert[0], BAND_NAMES[i], BAND_NAMES[j], lc, rc,
                        *cert[1:])
                iib_worst = (item if iib_worst is None or item < iib_worst
                             else iib_worst)
                iib_records += records
                iib_nonempty += nonempty
                iib_max_q = max(iib_max_q, max_q)
                for mechanism, count in mechanisms.items():
                    iib_mechanisms[mechanism] = (
                        iib_mechanisms.get(mechanism, 0) + count)
                iib_hashes.append((BAND_NAMES[i], BAND_NAMES[j], lc, rc,
                                   strategy_hash))
        main_pairs += pair_count

    # The one outer/outer near-root family at omega=0.
    for lc in core.active(bands[1], CFG.delta):
        for rc in core.active(bands[1], CFG.delta):
            if lc + rc == 0:
                continue
            near_pairs += 1
            lb, rb = core.cap(bands[1], lc), core.cap(bands[1], rc)
            for branch, capacities in core.fixed_capacities(CFG, Q(0)).items():
                try:
                    core.fixed_prefix_certificate(
                        CFG.delta, lc, rc, lb, rb, capacities)
                except ArithmeticError:
                    fixed_old_failures += 1
                cert = v2.enhanced_two_bin_certificate(
                    lc, rc, lb, rb, capacities)
                fixed_enhanced += cert[1] in ("cross-pool", "crossing-item")
                item = (cert[0], "near:wide_outer", "wide_outer", lc, rc,
                        branch, *cert[1:])
                fixed_worst = item if item < fixed_worst else fixed_worst
                fixed_digest.update(repr(item).encode("ascii"))
                fixed_checks += 1
            (cert, records, nonempty, max_q, mechanisms,
             strategy_hash) = v2.three_bin_iib_certificate(
                 lc, rc, lb, rb, Q(0))
            item = (cert[0], "near:wide_outer", "wide_outer", lc, rc,
                    *cert[1:])
            iib_worst = item if item < iib_worst else iib_worst
            iib_records += records
            iib_nonempty += nonempty
            iib_max_q = max(iib_max_q, max_q)
            for mechanism, count in mechanisms.items():
                iib_mechanisms[mechanism] = (
                    iib_mechanisms.get(mechanism, 0) + count)
            iib_hashes.append(("near:wide_outer", "wide_outer", lc, rc,
                               strategy_hash))

    dynamic_pairs = dynamic_checks = one_cells = three_cells = 0
    gmin = Q(2, 5) - core.H
    for i, j in ((0, 1), (1, 0), (1, 1)):
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
                        mechanism, cert = v2.dynamic_certificate(
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

    require((main_pairs, near_pairs, fixed_checks) == (582, 168, 1500),
            "fixed inventory")
    require((zero_left, zero_right) == (39, 39), "zero-count inventory")
    require((dynamic_pairs, dynamic_checks) == (168, 43008),
            "dynamic inventory")
    require(fixed_old_failures > 0 and fixed_enhanced > 0,
            "enhanced fixed mechanism not needed")
    require(iib_nonempty > 0 and
            iib_mechanisms.get("crossing-item", 0) > 0,
            "enhanced IIb mechanisms not needed")
    require(three_cells > 0 and one_cells + three_cells == dynamic_checks,
            "three-block dynamic mechanism not needed")
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
        "IIa_III_selected_enhanced": fixed_enhanced,
        "IIa_III_worst": fixed_worst,
        "IIa_III_strategy_sha256": fixed_digest.hexdigest(),
        "IIb_endpoint_and_interval_records": iib_records,
        "IIb_selected_nonempty_third": iib_nonempty,
        "IIb_maximum_selected_q": iib_max_q,
        "IIb_selected_two_bin_mechanisms": iib_mechanisms,
        "IIb_worst": iib_worst,
        "IIb_strategy_sha256": hashlib.sha256(
            repr(iib_hashes).encode("ascii")).hexdigest(),
        "dynamic_pairs": dynamic_pairs,
        "dynamic_checks": dynamic_checks,
        "dynamic_one_alternate_cells": one_cells,
        "dynamic_required_three_block_cells": three_cells,
        "dynamic_worst": dynamic_worst,
        "dynamic_strategy_sha256": dynamic_digest.hexdigest(),
    }


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
    require(sha256(V2_FILE) == V2_SHA256, "v2 exact primitives changed")
    require(sha256(v2.FROZEN_FILE) == v2.FROZEN_SHA256,
            "frozen source evaluator changed")
    require(sha256(v2.frozen.CORE_FILE) == v2.frozen.CORE_SHA256,
            "frozen core changed")
    for relative, expected in core.PINNED.items():
        require(sha256(core.REPO / relative) == expected,
                f"pinned source changed: {relative}")
    definition = definition1_check()
    source = source_geometry_check()
    packing = packing_check()
    lower_definition = definition1_check(-CAP_RADIUS)
    upper_definition = definition1_check(CAP_RADIUS)
    upper_packing = packing_check(CAP_RADIUS)
    proposition = core.proposition2_and_prop1_check(CFG)
    require(proposition["maximum_Bj1"] == max(
        schedule[0] for schedule in schedules()), "Proposition-2 B1 maximum")
    return stringify({
        "status": "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS",
        "scope": (
            "specialized direct-HB analytic support only; no Riesz energy "
            "lower bound, no quotient, and no bounded-gap theorem claim"),
        "checker_sha256": sha256(FILE),
        "v2_primitive_sha256": V2_SHA256,
        "parameters": {
            "k": 48, "delta": CFG.delta, "epsilon": CFG.epsilon,
            "A": (-CFG.epsilon, core.A1, ENDPOINT),
            "alpha": (core.A1 + CFG.epsilon, ENDPOINT + CFG.epsilon),
            "outer_width_fraction_of_old_outer": Q(37, 40),
            "outer_schedule_through_first_empty": v2.LOWER_HEAD,
            "outer_active_counts": tuple(range(13)),
            "main_direct_HB_face": 3 * (ENDPOINT - core.A1) + CFG.delta,
            "main_direct_HB_face_reserve": (
                Q(3, 80) - 3 * (ENDPOINT - core.A1) - CFG.delta),
        },
        "definition5_single_outer_band": {
            "eta_inner_inner": core.A1 - CFG.epsilon,
            "eta_inner_outer": ETA_OUTER,
            "eta_outer_outer": ETA_OUTER,
            "eta_rule": "max(A_m-epsilon,A_mprime-epsilon)",
            "reason": (
                "there is exactly one outer band; no indefinite cross-band "
                "outer-J summation is asserted by this gate"),
        },
        "definition1": definition,
        "source_geometry": source,
        "ordered_pair_packing": packing,
        "proposition2_and_prop1": proposition,
        "strict_outer_cap_interval": {
            "radius": CAP_RADIUS,
            "lower_active": lower_definition["active_counts"]["wide_outer"],
            "upper_active": upper_definition["active_counts"]["wide_outer"],
            "upper_fixed_worst": upper_packing["IIa_III_worst"],
            "upper_IIb_worst": upper_packing["IIb_worst"],
            "upper_dynamic_worst": upper_packing["dynamic_worst"],
        },
        "proof_lemmas": {
            "IIb": (
                "literal third-bin smallest-pool selection, residual "
                "enhanced two-bin packing, and every exact affine gamma "
                "breakpoint as implemented in the hash-pinned v2 primitives"),
            "IIc": (
                "three consecutive sorted blocks obey "
                "q(B-p*delta)/(n-p) and are assigned to all three alternate "
                "adverse cell capacities by exhaustive finite enumeration"),
        },
        "decision": (
            "deleting the two narrow upper bands leaves a fully checked "
            "inner-plus-one-wide-outer support using the new finite packing "
            "actions and avoids any multiband outer-J sign assumption"),
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
