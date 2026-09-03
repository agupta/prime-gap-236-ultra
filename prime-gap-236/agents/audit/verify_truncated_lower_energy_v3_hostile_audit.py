#!/usr/bin/env python3
"""Independent delta audit of the frozen truncated one-outer-band support.

No discovery module is imported.  This checker reconstructs the changed
two/three/four-bin combinatorics from exact inequalities.  Its Type-IIb
partition adds the ordinary sorted-prefix equality roots omitted by the
producer's breakpoint list, so every predicate is constant on every tested
open interval.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import stat
from dataclasses import dataclass, replace
from fractions import Fraction as F
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

PINS = {
    "agents/analytic-new-lever/verify_truncated_lower_energy_v3.py":
        "fff280573fa1bf539fe8fcba72270aa088c6d35255f39da24d7fb77fce5a75d5",
    "agents/analytic-new-lever/truncated_lower_energy_v3_exact.json":
        "c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f",
    "agents/analytic-new-lever/verify_three_outer_energy_v2.py":
        "87747ad848c502e4d0047d60ca324d77ba94c9b0f5cb2afd6b5d46b953575605",
    "agents/analytic-new-lever/verify_two_outer_band_v1.py":
        "187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001",
    "agents/analytic-new-lever/verify_adaptive_support_v1.py":
        "b8abaa8fec6f992c1071b4e550e666946444ff7c559b850960dc633836ce2c6d",
    "agents/audit/verify_adaptive_support_v1_hostile_audit.py":
        "0a6b6dbc6ab2cc1a1ec85e0e1a62e19cd6df498e97e68c8c0d5a6bd2202ed918",
    "agents/audit/results/adaptive_support_v1_hostile_audit.json":
        "eabffdc8927a50cb95fb1f8b707dd9b5c76b53778022ea039e160fb9cd2908d5",
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex":
        "60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30",
    "sources/polymath8-edz-1402.0811-src/newergap.tex":
        "fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea",
}

H = F(1, 10**10)
ZETA = H/1000
INWARD = H/10
HB_SLACK = H/10
DELTA = F(1, 60)
EPSILON = F(3, 400)
A1 = F(1, 4)
OLD_A2 = F(231241, 900000)
A2 = F(9230917, 36000000)
OUTER_HEAD = tuple(F(value, 10**6) for value in (
    140375, 157041, 168544, 174338, 185488, 190375,
    193097, 197146, 202047, 207090, 211668, 211668))
CAP_RADIUS = F(1, 10**7)
CELLS = 16


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qtext(value: F) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def encode(value):
    if isinstance(value, F):
        return qtext(value)
    if isinstance(value, tuple) or isinstance(value, list):
        return [encode(x) for x in value]
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    return value


def snap(relative: str) -> dict[str, int | str]:
    path = REPO/relative
    before = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
            f"unsafe provenance {relative}")
    digest = sha256(path)
    after = path.stat(follow_symlinks=False)
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            f"changed while hashing {relative}")
    return {"sha256": digest, "size": before.st_size, "dev": before.st_dev,
            "inode": before.st_ino, "nlink": before.st_nlink}


def strict_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, f"duplicate JSON key {key}")
        result[key] = value
    return result


def strict_json(path: Path):
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw, "noncanonical JSON text")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ArithmeticError("non-ASCII JSON") from error
    return json.loads(text, object_pairs_hook=strict_pairs,
                      parse_float=lambda token: (_ for _ in ()).throw(
                          ArithmeticError(f"JSON float {token}")),
                      parse_constant=lambda token: (_ for _ in ()).throw(
                          ArithmeticError(f"JSON constant {token}")))


def ceilq(value: F) -> int:
    return -((-value.numerator)//value.denominator)


def extend(head: tuple[F, ...]) -> tuple[F, ...]:
    return head+(head[-1],)*(int(F(1)//DELTA)-len(head))


@dataclass(frozen=True)
class Support:
    outer_head: tuple[F, ...]

    @property
    def inner(self):
        return (A1+EPSILON,)*60

    @property
    def outer(self):
        return extend(self.outer_head)

    @property
    def cross_omega(self):
        return (A2-A1)/2

    @property
    def outer_omega(self):
        return A2-A1


SUPPORT = Support(OUTER_HEAD)


def active(schedule: tuple[F, ...]) -> tuple[int, ...]:
    return (0,)+tuple(m for m, bound in enumerate(schedule, 1)
                      if m*DELTA <= bound)


def cap(schedule: tuple[F, ...], count: int) -> F:
    return F(0) if count == 0 else schedule[count-1]


def definition_one(support: Support) -> dict[str, object]:
    require(-EPSILON < A1 < A2 < F(1, 2)-EPSILON, "A ordering")
    expected = {"inner": tuple(range(16)), "outer": tuple(range(13))}
    inventories = {}
    margins = {}
    for name, schedule in (("inner", support.inner), ("outer", support.outer)):
        require(len(schedule) == 60, "schedule length")
        for index, value in enumerate(schedule):
            margins[f"{name}.B{index+1}-delta"] = value-DELTA
            require(margins[f"{name}.B{index+1}-delta"] > 0, "B <= delta")
            if index:
                step = value-schedule[index-1]
                require(F(0) <= step <= DELTA, f"bad cap step {name}:{index}")
        inventories[name] = active(schedule)
        require(inventories[name] == expected[name], f"active inventory {name}")
        first = inventories[name][-1]+1
        margins[f"{name}.first-empty"] = first*DELTA-schedule[first-1]
        require(margins[f"{name}.first-empty"] > 0, "first empty margin")
    return {"active_counts": inventories, "minimum_margin": min(margins.values()),
            "outer_first_empty_margin": margins["outer.first-empty"]}


def ga(omega: F) -> F:
    return F(2, 5)+F(24, 5)*omega+F(7, 5)*DELTA+2*H


def gb(omega: F) -> F:
    return F(1, 3)+8*omega+F(7, 3)*DELTA+3*H


def da(gamma: F, omega: F) -> F:
    return F(5, 7)*gamma-F(2, 7)-F(24, 7)*omega-H


def db(gamma: F, omega: F) -> F:
    return F(3, 7)*gamma-F(1, 7)-F(24, 7)*omega-H


def c_capacity(gamma: F) -> F:
    return gamma-3*ZETA-INWARD


def d_capacity(omega: F, gamma: F) -> F:
    return F(1, 2)-gamma-2*omega-6*ZETA-INWARD


def e_capacity(omega: F, gamma: F) -> F:
    return 2*omega+9*ZETA+db(gamma, omega)


def fixed_capacities(omega: F) -> dict[str, tuple[F, F]]:
    gamma3 = F(2, 5)-HB_SLACK
    d3 = F(1, 2)-F(7, 2)*omega-F(9, 8)*gamma3-H
    return {
        "IIa": (F(2, 5)+F(24, 5)*omega+F(7, 5)*DELTA-2*H,
                 F(1, 14)-F(24, 7)*omega-2*H),
        "III": (F(1, 3)+F(4, 3)*d3-F(4, 3)*omega-H,
                 F(1, 6)-d3/F(3)+F(4, 3)*omega-H),
    }


def ordinary_prefix(lc: int, rc: int, lb: F, rb: F,
                    capacities: tuple[F, ...]):
    total_n, total = lc+rc, lb+rb
    first = capacities[0]
    if total < first:
        return first-total, "all-first", 0, 0
    overload = total-first
    rmax = max(1, ceilq(overload/DELTA))
    choices = []
    for pool, n, bound in (("left", lc, lb), ("right", rc, rb),
                           ("combined", total_n, total)):
        if n < rmax:
            continue
        upper = (bound/n if rmax == 1 else
                 overload+(bound-overload)/(n-rmax+1))
        for slot, capacity in enumerate(capacities[1:], 1):
            if upper < capacity:
                choices.append((capacity-upper, pool, rmax, slot))
    require(choices, "ordinary prefix failed")
    return max(choices)


def cross_pool(lc: int, rc: int, lb: F, rb: F,
               capacities: tuple[F, F]):
    groups = ((lc, lb), (rc, rb))
    choices = []
    for whole_index, split_index in ((0, 1), (1, 0)):
        _, whole_bound = groups[whole_index]
        split_count, split_bound = groups[split_index]
        for first_slot, second_slot in ((0, 1), (1, 0)):
            for selected in range(split_count+1):
                selected_upper = (F(selected)*split_bound/split_count
                                  if selected else F(0))
                residual_upper = (F(0) if selected == split_count else
                                  split_bound-selected*DELTA)
                m1 = capacities[first_slot]-whole_bound-selected_upper
                m2 = capacities[second_slot]-residual_upper
                if min(m1, m2) > 0:
                    choices.append((min(m1, m2), "cross-pool", whole_index,
                                    split_index, selected, first_slot, second_slot))
    require(choices, "cross-pool failed")
    return max(choices)


def crossing_item(lc: int, rc: int, lb: F, rb: F,
                  capacities: tuple[F, F]):
    total_n, total = lc+rc, lb+rb
    first, alternate = capacities
    if total < first:
        return first-total, "crossing-all-first", 0, 0
    overload = total-first
    rmax = max(1, ceilq(overload/DELTA))
    choices = []
    for pool, n, bound in (("left", lc, lb), ("right", rc, rb),
                           ("combined", total_n, total)):
        if n < rmax:
            continue
        tails = tuple((bound-(j-1)*DELTA)/(n-j+1)
                      for j in range(1, rmax+1))
        margins = (alternate-2*overload,
                   *(alternate-tail for tail in tails))
        if min(margins) > 0:
            choices.append((min(margins), "crossing-item", pool, rmax))
    require(choices, "crossing-item failed")
    return max(choices)


def enhanced_two_bin(lc: int, rc: int, lb: F, rb: F,
                     capacities: tuple[F, F]):
    choices = []
    for function in (ordinary_prefix, cross_pool, crossing_item):
        try:
            choices.append(function(lc, rc, lb, rb, capacities))
        except ArithmeticError:
            pass
    require(choices, f"no enhanced two-bin certificate ({lc},{rc})")
    return max(choices, key=lambda value: value[0])


def third_actions(lc: int, rc: int, lb: F, rb: F, omega: F):
    maximum_e = e_capacity(omega, ga(omega))
    maximum_q = min(lc+rc, int(maximum_e//DELTA))
    actions = []
    for ql in range(lc+1):
        for qr in range(rc+1):
            if ql+qr > maximum_q:
                continue
            third = ((F(ql)*lb/lc if ql else F(0))+
                     (F(qr)*rb/rc if qr else F(0)))
            if ql+qr and third >= maximum_e:
                continue
            nl, nr = lc-ql, rc-qr
            bl = F(0) if nl == 0 else lb-ql*DELTA
            br = F(0) if nr == 0 else rb-qr*DELTA
            require(bl >= nl*DELTA and br >= nr*DELTA, "bad residual cap")
            actions.append((ql, qr, third, nl, nr, bl, br))
    require(actions and actions[0][:2] == (0, 0), "empty third action missing")
    return tuple(actions)


def action_at(omega: F, gamma: F, action):
    ql, qr, third, lc, rc, lb, rb = action
    third_margin = e_capacity(omega, gamma)-third
    if third_margin <= 0:
        return None
    total = lb+rb
    first = c_capacity(gamma)
    if total < first:
        return min(third_margin, first-total), ql, qr, "all-first", 0
    try:
        cert = enhanced_two_bin(lc, rc, lb, rb,
                                (first, d_capacity(omega, gamma)))
    except ArithmeticError:
        return None
    return min(third_margin, cert[0]), ql, qr, cert[1], cert[2:]


def producer_breakpoints(omega: F, actions) -> set[F]:
    low, high = gb(omega), ga(omega)
    points = {low, high}
    for ql, qr, third, lc, rc, lb, rb in actions:
        if ql+qr:
            root = (7*third+1+10*omega-63*ZETA+7*H)/3
            if low <= root <= high:
                points.add(root)
        total = lb+rb
        for crossing in range(lc+rc+1):
            root = total+3*ZETA+INWARD-crossing*DELTA
            if low <= root <= high:
                points.add(root)
        groups = ((lc, lb), (rc, rb))
        for whole_index, split_index in ((0, 1), (1, 0)):
            _, whole_bound = groups[whole_index]
            split_count, split_bound = groups[split_index]
            for selected in range(split_count+1):
                selected_upper = (F(selected)*split_bound/split_count
                                  if selected else F(0))
                residual_upper = (F(0) if selected == split_count else
                                  split_bound-selected*DELTA)
                for amount in (whole_bound+selected_upper, residual_upper):
                    for root in (amount+3*ZETA+INWARD,
                                 F(1, 2)-2*omega-6*ZETA-INWARD-amount):
                        if low <= root <= high:
                            points.add(root)
        double_root = (2*total-F(1, 2)+2*omega+12*ZETA+3*INWARD)
        if low <= double_root <= high:
            points.add(double_root)
        for count, bound in (*groups, (lc+rc, total)):
            for j in range(1, count+1):
                tail = (bound-(j-1)*DELTA)/(count-j+1)
                root = F(1, 2)-2*omega-6*ZETA-INWARD-tail
                if low <= root <= high:
                    points.add(root)
    return points


def completed_breakpoints(omega: F, actions):
    """Add every omitted ordinary-prefix affine equality root."""
    points = producer_breakpoints(omega, actions)
    original = set(points)
    low, high = gb(omega), ga(omega)
    K = F(1, 2)-2*omega-9*ZETA-2*INWARD  # C(gamma)+D(gamma)
    for _, _, _, lc, rc, lb, rb in actions:
        total = lb+rb
        for count, bound in ((lc, lb), (rc, rb), (lc+rc, total)):
            for r in range(2, count+1):
                # D = L+(B-L)/(n-r+1), L=S-C.
                c_root = (count-r+1)*K-(count-r)*total-bound
                gamma = c_root+3*ZETA+INWARD
                if low <= gamma <= high:
                    points.add(gamma)
    return tuple(sorted(points)), len(points-original)


def check_iib_pair(lc: int, rc: int, lb: F, rb: F, omega: F):
    actions = third_actions(lc, rc, lb, rb, omega)
    points, added = completed_breakpoints(omega, actions)
    probes = []
    for index, point in enumerate(points):
        probes.append(("endpoint", point, point, point))
        if index+1 < len(points):
            right = points[index+1]
            probes.append(("interval", point, right, (point+right)/2))
    worst = None
    nonempty = maximum_q = 0
    for kind, left, right, sample in probes:
        choices = [value for action in actions
                   if (value := action_at(omega, sample, action)) is not None]
        require(choices, f"uncovered IIb ({lc},{rc}) at {sample}")
        best = max(choices)
        item = (best[0], kind, left, right, *best[1:])
        worst = item if worst is None or item < worst else worst
        nonempty += best[1]+best[2] > 0
        maximum_q = max(maximum_q, best[1]+best[2])
    return worst, len(probes), added, nonempty, maximum_q


def sorted_three_blocks(lc: int, rc: int, lb: F, rb: F,
                        capacities: tuple[F, F, F, F]):
    total_n, total = lc+rc, lb+rb
    if total < capacities[0]:
        return capacities[0]-total, "all-first", 0, (), ()
    overload = total-capacities[0]
    removed = int(overload//DELTA)+1
    choices = []
    for pool, count, bound in (("left", lc, lb), ("right", rc, rb),
                               ("combined", total_n, total)):
        if count < removed:
            continue
        for first in range(removed+1):
            for second in range(removed-first+1):
                pieces = (first, second, removed-first-second)
                for order in itertools.permutations((1, 2, 3)):
                    used = 0
                    margins = [removed*DELTA-overload]
                    for size, slot in zip(pieces, order):
                        if size:
                            upper = F(size)*(bound-used*DELTA)/(count-used)
                            margins.append(capacities[slot]-upper)
                        used += size
                    if min(margins) > 0:
                        choices.append((min(margins), pool, removed, pieces, order))
    require(choices, f"three-block failure ({lc},{rc})")
    return max(choices)


def iic_capacities(gl: F, gu: F, wl: F, wu: F):
    answer = (gl-2*DELTA-8*wu-H,
              F(1, 2)-gu-2*wu-H,
              4*wl+DELTA-H,
              8*wl)
    require(min(answer) >= 0, "negative IIc capacity")
    return answer


def dynamic_certificate(lc: int, rc: int, lb: F, rb: F, capacities):
    try:
        return "one-alternate", ordinary_prefix(lc, rc, lb, rb, capacities)
    except ArithmeticError:
        return "three-block", sorted_three_blocks(lc, rc, lb, rb, capacities)


def packing(support: Support) -> dict[str, object]:
    bands = (support.inner, support.outer)
    families = ((0, 1, support.cross_omega, "inner", "outer"),
                (1, 0, support.cross_omega, "outer", "inner"),
                (1, 1, support.outer_omega, "outer", "outer"),
                (1, 1, F(0), "near:outer", "outer"))
    main_pairs = near_pairs = fixed_checks = old_failures = enhanced = 0
    zero_left = zero_right = zero_zero = 0
    iib_probes = iib_added = iib_nonempty = iib_max_q = 0
    worst_fixed = worst_iib = None
    for index, (i, j, omega, left_name, right_name) in enumerate(families):
        for lc in active(bands[i]):
            for rc in active(bands[j]):
                if lc == rc == 0:
                    zero_zero += 1
                    continue
                if index < 3:
                    main_pairs += 1
                    zero_left += lc == 0
                    zero_right += rc == 0
                else:
                    near_pairs += 1
                lb, rb = cap(bands[i], lc), cap(bands[j], rc)
                for branch, capacities in fixed_capacities(omega).items():
                    try:
                        ordinary_prefix(lc, rc, lb, rb, capacities)
                    except ArithmeticError:
                        old_failures += 1
                    cert = enhanced_two_bin(lc, rc, lb, rb, capacities)
                    enhanced += cert[1] in ("cross-pool", "crossing-item")
                    item = (cert[0], left_name, right_name, lc, rc,
                            branch, *cert[1:])
                    worst_fixed = item if worst_fixed is None or item < worst_fixed else worst_fixed
                    fixed_checks += 1
                cert, probes, added, nonempty, max_q = check_iib_pair(
                    lc, rc, lb, rb, omega)
                item = (cert[0], left_name, right_name, lc, rc, *cert[1:])
                worst_iib = item if worst_iib is None or item < worst_iib else worst_iib
                iib_probes += probes
                iib_added += added
                iib_nonempty += nonempty
                iib_max_q = max(iib_max_q, max_q)
    require((main_pairs, near_pairs, fixed_checks) == (582, 168, 1500),
            "fixed pair inventory")
    require((zero_left, zero_right, zero_zero) == (39, 39, 4),
            "zero-count inventory")
    require(old_failures == 18 and enhanced > 0, "enhanced fixed inventory")
    require(iib_added > 0 and iib_nonempty > 0 and iib_max_q == 1,
            "completed IIb mechanism inventory")

    omega = support.outer_omega
    gmin, gmax = F(2, 5)-H, gb(omega)
    require(gmax > gmin and gb(support.cross_omega) < gmin,
            "IIc regime classification")
    dynamic_pairs = dynamic_checks = empty_cells = one_cells = three_cells = 0
    worst_dynamic = None
    for lc in active(support.outer):
        for rc in active(support.outer):
            if lc == rc == 0:
                empty_cells += CELLS*CELLS
                continue
            dynamic_pairs += 1
            lb, rb = cap(support.outer, lc), cap(support.outer, rc)
            for iw in range(CELLS):
                wl, wu = omega*iw/CELLS, omega*(iw+1)/CELLS
                for ig in range(CELLS):
                    gl = gmin+(gmax-gmin)*ig/CELLS
                    gu = gmin+(gmax-gmin)*(ig+1)/CELLS
                    mechanism, cert = dynamic_certificate(
                        lc, rc, lb, rb, iic_capacities(gl, gu, wl, wu))
                    one_cells += mechanism == "one-alternate"
                    three_cells += mechanism == "three-block"
                    item = (cert[0], mechanism, "outer", "outer", lc, rc,
                            iw, ig, *cert[1:])
                    worst_dynamic = item if worst_dynamic is None or item < worst_dynamic else worst_dynamic
                    dynamic_checks += 1
    require((dynamic_pairs, dynamic_checks, empty_cells) == (168, 43008, 256),
            "IIc inventory")
    require(three_cells == 6081 and one_cells == 36927, "IIc mechanisms")
    return {"main_nonempty_pairs": main_pairs, "near_nonempty_pairs": near_pairs,
            "zero_zero_families": zero_zero, "main_zero_left": zero_left,
            "main_zero_right": zero_right, "fixed_checks": fixed_checks,
            "ordinary_prefix_failures": old_failures,
            "enhanced_fixed_selected": enhanced, "worst_fixed": worst_fixed,
            "IIb_completed_probes": iib_probes,
            "IIb_omitted_prefix_roots_added": iib_added,
            "IIb_selected_nonempty_third": iib_nonempty,
            "IIb_maximum_selected_q": iib_max_q, "worst_IIb": worst_iib,
            "dynamic_nonempty_pairs": dynamic_pairs,
            "dynamic_nonempty_cells": dynamic_checks,
            "dynamic_empty_tuple_cells": empty_cells,
            "dynamic_one_alternate_cells": one_cells,
            "dynamic_three_block_cells": three_cells,
            "worst_dynamic": worst_dynamic}


def source_geometry(support: Support) -> dict[str, object]:
    sigma = F(1, 10)+HB_SLACK
    gamma3 = F(2, 5)-HB_SLACK
    regimes = {}
    all_margins = []
    for name, omega in (("near", F(0)), ("mixed", support.cross_omega),
                        ("outer", support.outer_omega)):
        gamma_a, gamma_b = ga(omega), gb(omega)
        d_a_lo, d_a_hi = da(gamma_a, omega), da(F(1, 2), omega)
        d_b_lo, d_b_hi = db(gamma_b, omega), db(gamma_a, omega)
        d3 = F(1, 2)-F(7, 2)*omega-F(9, 8)*gamma3-H
        values = {
            "IIa_range": F(1, 2)-gamma_a,
            "IIa_width": d_a_lo-2*INWARD-DELTA,
            "IIa_face1": -2-(24*omega+7*d_a_lo-5*gamma_a),
            "IIa_face2": -(8*omega+3*d_a_hi-F(1, 2)),
            "IIb_range": gamma_a-gamma_b,
            "IIb_width": d_b_lo-2*INWARD-DELTA,
            "IIb_face1": -1-(24*omega+7*d_b_lo-3*gamma_b),
            "IIb_face2": -(8*omega+3*d_b_hi-gamma_a),
            "III_width": d3-2*H-DELTA,
            "III_face1": 4-(28*omega+9*gamma3+8*d3),
            "III_face2": 4-(16*omega+9*gamma3+2*d3),
            "III_face3": 4-(28*omega+9*gamma3-d3),
            "Type0_sharp": 1-((F(1, 2)-sigma)+(F(1, 2)+2*omega)),
            "Type0_Poisson": 1-(1-2*sigma+4*omega),
            "prime_square": F(1, 2)-2*omega,
            "higher_prime_powers": F(1, 6)-2*omega,
            "direct_II_face1": F(19, 2)-36*(A1+omega)-13*DELTA+100*H,
            "direct_II_face2": F(21, 25)-F(16, 5)*(A1+omega)-2*H-DELTA,
            "direct_II_face3": F(63, 80)-3*(A1+omega)-2*H-DELTA,
        }
        for key, value in values.items():
            require(value > 0, f"source non-strict {name}.{key}: {value}")
        all_margins.extend(values.values())
        regimes[name] = values
    d = DELTA+H/4
    gmin, gmax, omega = F(2, 5)-H, gb(support.outer_omega), support.outer_omega
    iic = {
        "width": d-2*INWARD-DELTA,
        "distribution1": 1-(8*omega+4*d+2*gmax),
        "distribution2": gmin-(32*omega+10*d),
        "distribution3": 4*gmin-48*omega-16*d-1,
        "proof_start": gmin-4*omega-d,
    }
    for key, value in iic.items():
        require(value > 0, f"IIc source non-strict {key}: {value}")
    all_margins.extend(iic.values())
    return {"regimes": regimes, "outer_IIc": iic,
            "minimum_margin": min(all_margins)}


def reconstruct(support: Support):
    return {"definition1": definition_one(support),
            "source_geometry": source_geometry(support),
            "packing": packing(support)}


def compare_record(record, rebuilt):
    require(record.get("status") ==
            "EXACT TRUNCATED ONE-OUTER-BAND ENERGY SUPPORT PASS", "status")
    params = record.get("parameters", {})
    require(params.get("A") == [qtext(-EPSILON), qtext(A1), qtext(A2)], "A tuple")
    require(params.get("outer_active_counts") == list(range(13)), "outer counts")
    packing_record = record.get("ordered_pair_packing", {})
    expected = {
        "main_ordered_pairs": 582, "near_ordered_pairs": 168,
        "IIa_III_checks": 1500, "IIa_III_old_prefix_failures": 18,
        "dynamic_pairs": 168, "dynamic_checks": 43008,
        "dynamic_required_three_block_cells": 6081,
    }
    for key, value in expected.items():
        require(packing_record.get(key) == value, f"producer inventory {key}")
    require(record.get("definition5_single_outer_band", {}).get(
        "eta_outer_outer") == qtext(A2-EPSILON), "Definition-5 cutoff")
    return {"embedded_tuple_and_inventories_match": True,
            "producer_IIb_probes":
                packing_record.get("IIb_endpoint_and_interval_records"),
            "audit_completed_IIb_probes": rebuilt["packing"]["IIb_completed_probes"]}


def build():
    snapshots = {}
    for relative, expected in PINS.items():
        snapshot = snap(relative)
        require(snapshot["sha256"] == expected, f"pin mismatch {relative}")
        snapshots[relative] = snapshot

    # Complete all mathematics before reading the producer result.
    rebuilt = reconstruct(SUPPORT)
    lower = replace(SUPPORT, outer_head=tuple(x-CAP_RADIUS for x in OUTER_HEAD))
    upper = replace(SUPPORT, outer_head=tuple(x+CAP_RADIUS for x in OUTER_HEAD))
    lower_definition = definition_one(lower)
    upper_rebuilt = reconstruct(upper)

    record = strict_json(REPO/"agents/analytic-new-lever/truncated_lower_energy_v3_exact.json")
    comparison = compare_record(record, rebuilt)
    for relative, expected in PINS.items():
        require(sha256(REPO/relative) == expected, f"changed during audit {relative}")

    return encode({
        "status": "TRUNCATED LOWER ENERGY V3 HOSTILE AUDIT PASS",
        "scope": "delta=1/60 direct-HB analytic support; no energy or theorem claim",
        "checker_sha256": sha256(FILE), "snapshots": snapshots,
        "retained_and_deleted_bands": {
            "retained_outer_endpoint": A2,
            "deleted_middle_endpoint": A1+F(39, 40)*(OLD_A2-A1),
            "deleted_top_endpoint": OLD_A2,
            "result_has_exactly_one_outer_band": True,
        },
        "independent_reconstruction": rebuilt,
        "strict_common_cap_translation": {
            "radius": CAP_RADIUS,
            "lower_definition": lower_definition,
            "upper_reconstruction": upper_rebuilt,
        },
        "producer_comparison": comparison,
        "continuum_completion": {
            "finding": (
                "producer breakpoint list omits ordinary-prefix affine equality "
                "roots; the independent audit inserts every such root"),
            "mathematical_counterexample": None,
            "frozen_tuple_passes_completed_partition": True,
        },
        "proposition_interface_reused_and_rechecked": {
            "base_hostile_audit_sha256":
                PINS["agents/audit/results/adaptive_support_v1_hostile_audit.json"],
            "Proposition_2": "not invoked; universal H premise is not claimed",
            "Proposition_1": "direct weighted-prime rho satisfies all four hypotheses",
            "rho": "(log n/log(3x))*1_P on [x,2x], zero outside",
            "c1": F(0), "c2": F(0), "beta": F(1, 2),
            "theorem_ready": False,
        },
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":"))+"\n").encode("ascii")
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o444)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
