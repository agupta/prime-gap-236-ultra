#!/usr/bin/env python3
"""Self-contained exact gate for the adaptive delta=1/60 support.

This script imports no producer, optimizer, frozen-v6 module, or analytic
checker.  It reconstructs the selected specialized direct Heath--Brown
route with Fraction arithmetic.  In particular it checks Definition 1,
Proposition 2's prime-indicator specialization, all ordered support-band
pairs (including one zero count), Type IIa, literal gamma-dependent Type
IIb, corrected Type III, and the full 16x16 Type-IIc continuum cover.

The theorem-facing Type-IIb gate uses the literal correlated capacities
C(gamma),D(gamma), leaves the third bin empty, and checks every possible
minimal-prefix crossing number exactly.  The stronger experimental
three-bin breakpoint oracle is deliberately kept in a separate diagnostic
script and cannot influence this script's PASS decision.

Scope is analytic feasibility and elementary volume diagnostics only.  No
sieve quotient or bounded-gap theorem is claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

PINNED = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex":
        "60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30",
    "sources/polymath8-edz-1402.0811-src/newergap.tex":
        "fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea",
    "agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md":
        "47cd11457c44aa2348e7b3d22c5615261c5af04d999414dae3d58eba16f9e80c",
    "agents/hostile-analytic-audit/c10-analytic-repair-addendum.md":
        "2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7",
    "agents/hostile-analytic-audit/C10-AUDIT.md":
        "7df85a8ca8b6ea3ab9246e018efd759e6ddf76200f895a141f2ff089da15ccc3",
    "agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md":
        "f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
}

H = Q(1, 10**10)
HB_SLACK = H / 10
ZETA = H / 1000
INWARD = H / 10
A1 = Q(1, 4)
XI1, XI2, XI3 = Q(19, 50), Q(2, 5), Q(2, 5)
CELLS = 16
K_DIM = 48


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def ceilq(value: Q) -> int:
    return -((-value.numerator) // value.denominator)


def decimal_string(value: Q, digits: int = 24) -> str:
    with localcontext() as ctx:
        ctx.prec = digits
        return str(Decimal(value.numerator) / Decimal(value.denominator))


@dataclass(frozen=True)
class Config:
    name: str
    delta: Q
    epsilon: Q
    a2: Q
    outer_head: tuple[Q, ...]
    expected_outer_last: int

    @property
    def x(self) -> Q:
        return self.a2 - A1

    @property
    def cross_omega(self) -> Q:
        return self.x / 2

    @property
    def outer_omega(self) -> Q:
        return self.x

    @property
    def alpha1(self) -> Q:
        return A1 + self.epsilon

    @property
    def alpha2(self) -> Q:
        return self.a2 + self.epsilon

    @property
    def iic_aux(self) -> Q:
        return self.delta + H / 4


AUDITED = Config(
    "audited_correlated_lift", Q(361, 50000), Q(3, 400), Q(3121, 12000),
    tuple(Q(text) for text in (
        "119469/1000000", "126689/1000000", "133909/1000000",
        "141129/1000000", "148349/1000000", "155569/1000000",
        "155569/1000000", "162789/1000000", "339/2000",
        "339/2000", "339/2000", "339/2000", "859/5000",
        "1737/10000", "219/1250", "881/5000", "441/2500",
        "887/5000", "891/5000", "179/1000", "449/2500",
        "1801/10000", "903/5000", "1811/10000", "363/2000",
        "363/2000")), 25)

CANDIDATE = Config(
    "adaptive_delta_1_over_60", Q(1, 60), Q(3, 400), Q(231241, 900000),
    tuple(Q(value, 10**6) for value in (
        138360, 155020, 158662, 171688, 177684, 180588,
        183402, 185486, 187011, 188221, 189137, 189137)), 11)


def extend(head: tuple[Q, ...], delta: Q) -> tuple[Q, ...]:
    length = int(Q(1) // delta)
    require(0 < len(head) <= length, "bad schedule-head length")
    return head + (head[-1],) * (length - len(head))


def inner_schedule(cfg: Config) -> tuple[Q, ...]:
    return extend((cfg.alpha1,), cfg.delta)


def outer_schedule(cfg: Config) -> tuple[Q, ...]:
    return extend(cfg.outer_head, cfg.delta)


def active(schedule: tuple[Q, ...], delta: Q) -> tuple[int, ...]:
    return (0,) + tuple(i for i, cap in enumerate(schedule, 1)
                        if i * delta <= cap)


def cap(schedule: tuple[Q, ...], count: int) -> Q:
    return Q(0) if count == 0 else schedule[count - 1]


def positive(margins: dict[str, Q], key: str, value: Q) -> Q:
    require(value > 0, f"nonpositive margin {key}: {value}")
    margins[key] = value
    return value


def definition1_check(cfg: Config) -> dict[str, object]:
    margins: dict[str, Q] = {}
    positive(margins, "epsilon", cfg.epsilon)
    positive(margins, "delta", cfg.delta)
    positive(margins, "A1-A0", A1 + cfg.epsilon)
    positive(margins, "A2-A1", cfg.x)
    positive(margins, "upper", Q(1, 2) - cfg.epsilon - cfg.a2)
    schedules = {"inner": inner_schedule(cfg), "outer": outer_schedule(cfg)}
    expected = {
        "inner": tuple(range(int(cfg.alpha1 // cfg.delta) + 1)),
        "outer": tuple(range(cfg.expected_outer_last + 1)),
    }
    equal_steps = {}
    for name, schedule in schedules.items():
        zero = []
        top = []
        for i, value in enumerate(schedule):
            positive(margins, f"{name}.B{i + 1}-delta", value - cfg.delta)
            if i:
                step = value - schedule[i - 1]
                require(0 <= step <= cfg.delta,
                        f"bad {name} transition B{i}->B{i + 1}: {step}")
                if step == 0:
                    zero.append(i + 1)
                if step == cfg.delta:
                    top.append(i + 1)
        actual = active(schedule, cfg.delta)
        require(actual == expected[name],
                f"{cfg.name} {name} active inventory {actual}")
        first_empty = actual[-1] + 1
        for count in range(first_empty, len(schedule) + 1):
            positive(margins, f"{name}.empty-{count}",
                     count * cfg.delta - schedule[count - 1])
        positive(margins, f"{name}.last-active",
                 schedule[actual[-1] - 1] - actual[-1] * cfg.delta)
        equal_steps[name] = {"zero": zero, "delta": top}
    return {
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "inner_active": active(schedules["inner"], cfg.delta),
        "outer_active": active(schedules["outer"], cfg.delta),
        "outer_first_empty_margin": (
            (cfg.expected_outer_last + 1) * cfg.delta
            - schedules["outer"][cfg.expected_outer_last]),
        "definition1_weak_equality_steps": equal_steps,
    }


def ga(cfg: Config, omega: Q) -> Q:
    return Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * cfg.delta + 2 * H


def gb(cfg: Config, omega: Q) -> Q:
    return Q(1, 3) + 8 * omega + Q(7, 3) * cfg.delta + 3 * H


def da(gamma: Q, omega: Q) -> Q:
    return Q(5, 7) * gamma - Q(2, 7) - Q(24, 7) * omega - H


def db(gamma: Q, omega: Q) -> Q:
    return Q(3, 7) * gamma - Q(1, 7) - Q(24, 7) * omega - H


def fixed_capacities(cfg: Config, omega: Q) -> dict[str, tuple[Q, Q]]:
    gamma3 = Q(2, 5) - HB_SLACK
    d3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    return {
        "IIa": (
            Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * cfg.delta - 2 * H,
            Q(1, 14) - Q(24, 7) * omega - 2 * H),
        "III": (
            Q(1, 3) + Q(4, 3) * d3 - Q(4, 3) * omega - H,
            Q(1, 6) - d3 / 3 + Q(4, 3) * omega - H),
    }


def source_geometry_check(cfg: Config) -> dict[str, object]:
    """Exact scalar/direct-HB and source-interval substitutions."""
    margins: dict[str, Q] = {}
    sigma = Q(1, 10) + HB_SLACK
    positive(margins, "HB.sigma", sigma - Q(1, 10))
    positive(margins, "HB.K10", 2 * sigma - Q(1, 10))
    positive(margins, "HB.central-lower",
             (Q(2, 5) - HB_SLACK) - (Q(2, 5) - H))
    positive(margins, "HB.III-lower", 2 * sigma - (Q(1, 5) - H))
    positive(margins, "HB.III-upper",
             (Q(2, 5) + H) - (Q(1, 2) - sigma))
    positive(margins, "HB.III-pair",
             (Q(1, 2) + sigma) - (Q(3, 5) - H))

    exponents = (
        (A1 - cfg.epsilon) + (A1 + cfg.epsilon),
        (A1 - cfg.epsilon) + (cfg.a2 + cfg.epsilon),
        (cfg.a2 - cfg.epsilon) + (A1 + cfg.epsilon),
        (cfg.a2 - cfg.epsilon) + (cfg.a2 + cfg.epsilon),
    )
    require(exponents == (2 * A1, A1 + cfg.a2,
                          A1 + cfg.a2, 2 * cfg.a2),
            "epsilon cancellation failed")

    for label, omega in (("near", Q(0)),
                         ("mixed", cfg.cross_omega),
                         ("outer", cfg.outer_omega)):
        g_a, g_b = ga(cfg, omega), gb(cfg, omega)
        positive(margins, f"{label}.IIa-range", Q(1, 2) - g_a)
        positive(margins, f"{label}.IIb-range", g_a - g_b)
        positive(margins, f"{label}.IIa-width",
                 da(g_a, omega) - 2 * INWARD - cfg.delta)
        positive(margins, f"{label}.IIa-face1",
                 -2 - (24 * omega + 7 * da(g_a, omega) - 5 * g_a))
        positive(margins, f"{label}.IIa-face2",
                 -(8 * omega + 3 * da(Q(1, 2), omega) - Q(1, 2)))
        positive(margins, f"{label}.IIa-a1",
                 g_a - 3 * ZETA - da(g_a, omega) + INWARD)
        safe_iia = fixed_capacities(cfg, omega)["IIa"]
        positive(margins, f"{label}.IIa-cap1-domination",
                 g_a - 3 * ZETA - INWARD - safe_iia[0])
        positive(margins, f"{label}.IIa-cap2-domination",
                 Q(1, 14) - Q(24, 7) * omega - H - INWARD
                 - safe_iia[1])

        db_lo, db_hi = db(g_b, omega), db(g_a, omega)
        positive(margins, f"{label}.IIb-width",
                 db_lo - 2 * INWARD - cfg.delta)
        positive(margins, f"{label}.IIb-face1",
                 -1 - (24 * omega + 7 * db_lo - 3 * g_b))
        positive(margins, f"{label}.IIb-face2",
                 -(8 * omega + 3 * db_hi - g_a))
        positive(margins, f"{label}.IIb-a1",
                 g_b - 3 * ZETA - db_lo + INWARD)
        positive(margins, f"{label}.IIb-a2",
                 Q(1, 2) - g_a - 2 * omega - 6 * ZETA
                 - db_hi + INWARD)
        positive(margins, f"{label}.IIb-bsum", 2 * omega + 2 * INWARD)
        positive(margins, f"{label}.IIb-third-min",
                 cfg.delta + 2 * omega + Q(2, 7) * H + 9 * ZETA)

        gamma3 = Q(2, 5) - HB_SLACK
        d3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
        positive(margins, f"{label}.III-width", d3 - 2 * H - cfg.delta)
        positive(margins, f"{label}.III-main",
                 4 - (28 * omega + 9 * gamma3 + 8 * d3))
        positive(margins, f"{label}.III-second",
                 4 - (16 * omega + 9 * gamma3 + 2 * d3))
        positive(margins, f"{label}.III-third",
                 4 - (28 * omega + 9 * gamma3 - d3))
        positive(margins, f"{label}.III-S-lower", 1 - 4 * omega + 4 * d3)
        positive(margins, f"{label}.III-S-upper", 1 - 2 * d3 + 8 * omega)
        positive(margins, f"{label}.III-omega", Q(1, 12) - omega)
        a3 = Q(1, 3) + d3 / 3 - Q(4, 3) * omega
        b3 = Q(1, 3) + Q(4, 3) * d3 - Q(4, 3) * omega
        positive(margins, f"{label}.III-a", a3 + H)
        positive(margins, f"{label}.III-b", Q(1, 2) - (b3 - H))

        average_a = A1 + omega
        qexp = Q(1, 2) + 2 * omega
        positive(margins, f"{label}.Type0-sharp",
                 1 - ((Q(1, 2) - sigma) + qexp))
        positive(margins, f"{label}.Type0-Poisson",
                 1 - (1 - 2 * sigma + 4 * omega))
        positive(margins, f"{label}.prime-square", 1 - qexp)
        positive(margins, f"{label}.higher-prime-powers",
                 1 - qexp - Q(1, 3))
        positive(margins, f"{label}.direct-II-19/2",
                 Q(19, 2) - 36 * average_a - 13 * cfg.delta + 100 * H)
        positive(margins, f"{label}.direct-II-first",
                 Q(21, 25) - Q(16, 5) * average_a - 2 * H - cfg.delta)
        positive(margins, f"{label}.direct-II-second",
                 Q(63, 80) - 3 * average_a - 2 * H - cfg.delta)

    positive(margins, "mixed.IIc-empty",
             (Q(2, 5) - H) - gb(cfg, cfg.cross_omega))
    positive(margins, "near.IIc-empty",
             (Q(2, 5) - H) - gb(cfg, Q(0)))

    gmin, gmax = Q(2, 5) - H, gb(cfg, cfg.outer_omega)
    d = cfg.iic_aux
    positive(margins, "outer.IIc-range", gmax - gmin)
    positive(margins, "outer.IIc-width", d - 2 * INWARD - cfg.delta)
    positive(margins, "outer.IIc-face1",
             1 - (8 * cfg.outer_omega + 4 * d + 2 * gmax))
    positive(margins, "outer.IIc-face2",
             gmin - (32 * cfg.outer_omega + 10 * d))
    positive(margins, "outer.IIc-face3",
             4 * gmin - 48 * cfg.outer_omega - 16 * d - 1)
    positive(margins, "outer.IIc-proof-start",
             gmin - 4 * cfg.outer_omega - d)
    positive(margins, "outer.IIc-a1", gmin - 3 * ZETA - d + INWARD)
    positive(margins, "outer.IIc-a2",
             Q(1, 2) - gmax - 2 * cfg.outer_omega - 6 * ZETA
             - d + INWARD)
    positive(margins, "outer.IIc-b1", Q(1, 2) - gmax + 3 * ZETA + INWARD)
    positive(margins, "outer.IIc-structural", 2 * (d - 2 * INWARD))
    positive(margins, "outer.IIc-C1-domination",
             H - 2 * (d - cfg.delta) - 58 * ZETA + INWARD)
    positive(margins, "outer.IIc-C2-domination", H - 6 * ZETA - INWARD)
    positive(margins, "outer.IIc-C3-domination", d - cfg.delta + H)
    positive(margins, "outer.IIc-C4-domination", 2 * INWARD)

    # Printed Proposition 3 Type I is not an input to this route.  Record its
    # scalar substitutions without silently promoting them to requirements;
    # in particular the independently audited baseline need not satisfy the
    # first one.  The universal tuple branch also has the pinned role-swap
    # defect, so neither value can authorize anything here.
    excluded_type_i_scalars = {
        "first": XI1 - 4 * cfg.a2 + Q(2, 3) - 2 * H - cfg.delta,
        "second": Q(9, 7) - Q(34, 7) * cfg.a2 - 2 * H - cfg.delta,
    }

    return {
        "ordered_band_exponents": exponents,
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "margins": margins,
        "excluded_printed_TypeI_scalar_values": excluded_type_i_scalars,
        "excluded_branch": (
            "printed universal Proposition-3 Type I tuple condition; the "
            "pinned specialized direct Heath--Brown reduction has no Type-I "
            "aggregate and does not rely on the defective role swap"),
    }


def fixed_prefix_certificate(
        delta: Q, lc: int, rc: int, lb: Q, rb: Q,
        capacities: tuple[Q, ...]):
    """Universal sorted-prefix certificate for a fixed capacity vector."""
    total_n, total_b = lc + rc, lb + rb
    first = capacities[0]
    if total_b < first:
        return first - total_b, "all-first", 0, 0
    overload = total_b - first
    # At exact equality, deliberately move one smallest coordinate to an
    # alternate bin.  This supplies a strict packing reserve instead of
    # relying on the source's permitted weak all-first equality.
    rmax = max(1, ceilq(overload / delta))
    answers = []
    for pool, n, b in (("left", lc, lb), ("right", rc, rb),
                       ("combined", total_n, total_b)):
        if n < rmax or rmax < 1:
            continue
        require(b >= n * delta, f"inactive pool passed at {lc},{rc}")
        # Sort this pool.  The least prefix exceeding the actual overload
        # ends by rmax; its sum is strictly below this exact upper bound.
        if rmax == 1:
            upper = b / n
        else:
            upper = overload + (b - overload) / (n - rmax + 1)
        for alternate, capacity in enumerate(capacities[1:], 1):
            if upper < capacity:
                answers.append((capacity - upper, pool, rmax, alternate))
    require(answers, f"no fixed prefix certificate at {lc},{rc}")
    return max(answers)


def iib_c(cfg: Config, gamma: Q) -> Q:
    return gamma - 3 * ZETA - INWARD


def iib_d(omega: Q, gamma: Q) -> Q:
    return Q(1, 2) - gamma - 2 * omega - 6 * ZETA - INWARD


def empty_third_uniform_iib_certificate(
        cfg: Config, lc: int, rc: int, lb: Q, rb: Q, omega: Q):
    """Uniform two-bin subcertificate, retained as a strict robustness gate.

    This is the empty-third correlated two-bin lemma.  If
    L=S-C(gamma)>0 and r=ceil(L/delta), the displayed tail bound is adverse
    on the whole r-cell, so its positive slack is a genuine uniform support
    perturbation reserve, not a sampled or midpoint margin.
    """
    low = gb(cfg, omega)
    total_b, total_n = lb + rb, lc + rc
    constant_window = (iib_c(cfg, low) + iib_d(omega, low) - total_b)
    require(constant_window > 0, "nonpositive empty-third constant window")
    max_overload = total_b - iib_c(cfg, low)
    pools = (("left", lc, lb), ("right", rc, rb),
             ("combined", total_n, total_b))
    if max_overload < 0:
        return (-max_overload, "all-first", 0, 0)
    max_r = max(1, ceilq(max_overload / cfg.delta))
    worst = None
    for crossing in range(1, max_r + 1):
        choices = []
        for pool, n, b in pools:
            if n < crossing:
                continue
            tail = (b / n if crossing == 1 else
                    (b - (crossing - 1) * cfg.delta)
                    / (n - crossing + 1))
            if tail < constant_window:
                choices.append((constant_window - tail, pool,
                                crossing, 0))
        require(choices,
                f"empty-third uniform IIb failure {lc},{rc},r={crossing}")
        best = max(choices)
        worst = best if worst is None or best < worst else worst
    require(worst is not None and worst[0] > 0, "empty-third IIb reserve")
    return worst


def classify(lc: int, rc: int) -> str:
    if lc == 0:
        return "left-zero"
    if rc == 0:
        return "right-zero"
    if lc <= 2 and rc <= 2:
        return "both-positive-at-most-two"
    if (lc <= 2) != (rc <= 2):
        return "exactly-one-at-most-two"
    return "both-at-least-three"


def fixed_families_check(cfg: Config) -> dict[str, object]:
    inner, outer = inner_schedule(cfg), outer_schedule(cfg)
    families = (
        ("mixed", inner, outer, cfg.cross_omega),
        ("transpose", outer, inner, cfg.cross_omega),
        ("outer", outer, outer, cfg.outer_omega),
        ("outer-near", outer, outer, Q(0)),
    )
    global_fixed = global_uniform_iib = None
    total_pairs = total_fixed = total_iib_crossings = 0
    inventory = {}
    classes: dict[str, int] = {}
    for name, left, right, omega in families:
        pairs = fixed_checks = iib_crossings = 0
        family_iib = None
        for lc in active(left, cfg.delta):
            for rc in active(right, cfg.delta):
                if lc + rc == 0:
                    continue
                pairs += 1
                classes[classify(lc, rc)] = classes.get(classify(lc, rc), 0) + 1
                lb, rb = cap(left, lc), cap(right, rc)
                for branch, capacities in fixed_capacities(cfg, omega).items():
                    cert = fixed_prefix_certificate(
                        cfg.delta, lc, rc, lb, rb, capacities)
                    item = (cert[0], name, branch, lc, rc, *cert[1:])
                    global_fixed = (item if global_fixed is None or
                                    item < global_fixed else global_fixed)
                    fixed_checks += 1
                uniform = empty_third_uniform_iib_certificate(
                    cfg, lc, rc, lb, rb, omega)
                uniform_item = (uniform[0], name, lc, rc, *uniform[1:])
                global_uniform_iib = (
                    uniform_item if global_uniform_iib is None or
                    uniform_item < global_uniform_iib else global_uniform_iib)
                family_iib = (uniform_item if family_iib is None or
                              uniform_item < family_iib else family_iib)
                # One exact adverse inequality is checked for every possible
                # crossing number in this pair's gamma continuum.
                max_overload = lb + rb - iib_c(cfg, gb(cfg, omega))
                iib_crossings += (0 if max_overload < 0 else
                                  max(1, ceilq(max_overload / cfg.delta)))
        require(pairs == len(active(left, cfg.delta)) *
                len(active(right, cfg.delta)) - 1,
                f"{cfg.name} {name} ordered pair inventory")
        require(fixed_checks == 2 * pairs, f"{name} fixed inventory")
        inventory[name] = {"pairs": pairs, "fixed_checks": fixed_checks,
                           "iib_crossing_checks": iib_crossings,
                           "uniform_empty_third_iib_worst": family_iib}
        total_pairs += pairs
        total_fixed += fixed_checks
        total_iib_crossings += iib_crossings
    require(global_fixed is not None and global_fixed[0] > 0,
            "nonpositive fixed-family margin")
    require(global_uniform_iib is not None and global_uniform_iib[0] > 0,
            "nonpositive uniform empty-third IIb reserve")
    require(sum(classes.values()) == total_pairs, "small-count classification")
    return {
        "families": inventory, "ordered_pairs": total_pairs,
        "IIa_III_checks": total_fixed, "IIa_III_worst": global_fixed,
        "IIb_crossing_number_checks": total_iib_crossings,
        "IIb_uniform_empty_third_worst": global_uniform_iib,
        "IIb_mechanism": (
            "literal C(gamma),D(gamma) with empty third bin and exact "
            "crossing-number continuum sweep"),
        "small_count_partition": classes,
    }


def iic_capacities(cfg: Config, gl: Q, gu: Q, wl: Q, wu: Q):
    answer = (gl - 2 * cfg.delta - 8 * wu - H,
              Q(1, 2) - gu - 2 * wu - H,
              4 * wl + cfg.delta - H, 8 * wl)
    require(min(answer) >= 0, "negative IIc adverse cell capacity")
    return answer


def dynamic_iic_check(cfg: Config) -> dict[str, object]:
    outer = outer_schedule(cfg)
    counts = active(outer, cfg.delta)
    gmin, gmax = Q(2, 5) - H, gb(cfg, cfg.outer_omega)
    require(gmax > gmin, "outer IIc unexpectedly empty")
    worst = None
    pairs = checks = 0
    classes: dict[str, int] = {}
    for lc in counts:
        for rc in counts:
            if lc + rc == 0:
                continue
            pairs += 1
            classes[classify(lc, rc)] = classes.get(classify(lc, rc), 0) + 1
            lb, rb = cap(outer, lc), cap(outer, rc)
            for iw in range(CELLS):
                wl = cfg.outer_omega * iw / CELLS
                wu = cfg.outer_omega * (iw + 1) / CELLS
                for ig in range(CELLS):
                    gl = gmin + (gmax - gmin) * ig / CELLS
                    gu = gmin + (gmax - gmin) * (ig + 1) / CELLS
                    capacities = iic_capacities(cfg, gl, gu, wl, wu)
                    cert = fixed_prefix_certificate(
                        cfg.delta, lc, rc, lb, rb, capacities)
                    item = (cert[0], lc, rc, iw, ig, *cert[1:])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
    require(pairs == len(counts) ** 2 - 1, "dynamic ordered pair inventory")
    require(checks == pairs * CELLS * CELLS, "dynamic cell inventory")
    require(worst is not None and worst[0] > 0, "nonpositive dynamic margin")
    return {"ordered_pairs": pairs, "cells_per_pair": CELLS * CELLS,
            "checks": checks, "worst": worst,
            "small_count_partition": classes,
            "continuum_reason": (
                "each displayed capacity is its adverse rational endpoint "
                "on one closed omega0/gamma cell; the fixed-prefix partition "
                "therefore works throughout that cell")}


def proposition2_and_prop1_check(cfg: Config) -> dict[str, object]:
    margins: dict[str, Q] = {}
    positive(margins, "2-(2xi1+3xi2)", 2 - (2 * XI1 + 3 * XI2))
    require(XI2 == XI3, "xi2=xi3 endpoint specialization changed")
    positive(margins, "4-(xi1+9xi2)", 4 - (XI1 + 9 * XI2))
    positive(margins, "2xi1+xi2-1", 2 * XI1 + XI2 - 1)
    positive(margins, "7-17xi2", 7 - 17 * XI2)
    # At xi2=xi3=2/5 both discarded Harman configurations are empty,
    # yielding exactly the prime-indicator weight in the pinned source audit.
    beta = Q(1, 2)
    maximum_b1 = max(inner_schedule(cfg)[0], outer_schedule(cfg)[0])
    positive(margins, "beta-max-Bj1", beta - maximum_b1)
    return {
        "xi": (XI1, XI2, XI3),
        "rho": "(log n/log(3x))*1_P on [x,2x], zero outside",
        "rho_reason": (
            "xi2=xi3=2/5 makes both discarded Proposition-2 configurations "
            "empty; the pinned c2=0 audit supplies the normalized prime weight"),
        "c1": Q(0), "c2": Q(0), "beta": beta,
        "maximum_Bj1": maximum_b1,
        "minimum_margin": min(margins.values()),
        "margins": margins,
    }


def exact_stratum_volume(cfg: Config, alpha: Q, count: int) -> Q:
    """Exact Lebesgue volume in the symmetric count stratum below alpha."""
    schedule = outer_schedule(cfg)
    require(0 <= count <= cfg.expected_outer_last, "inactive volume count")
    if count == 0:
        return sum((Q((-1) ** h * math.comb(K_DIM, h))
                    * max(Q(0), alpha - h * cfg.delta) ** K_DIM
                    for h in range(int(alpha // cfg.delta) + 1)), Q(0)) \
            / math.factorial(K_DIM)
    budget = schedule[count - 1] - count * cfg.delta
    require(budget >= 0, "negative cap excess")
    small = K_DIM - count
    answer = Q(0)
    for h in range(max(0, int(alpha // cfg.delta) - count) + 1):
        length = alpha - (count + h) * cfg.delta
        upper = min(budget, length)
        if upper <= 0:
            continue
        radial = sum((Q((-1) ** j * math.comb(small, j), count + j)
                      * length ** (small - j) * upper ** (count + j)
                      for j in range(small + 1)), Q(0))
        answer += (Q((-1) ** h * math.comb(small, h)) * radial
                   / (math.factorial(count - 1) * math.factorial(small)))
    return math.comb(K_DIM, count) * answer


def exact_shell_volume(cfg: Config) -> tuple[Q, tuple[Q, ...]]:
    rows = tuple(exact_stratum_volume(cfg, cfg.alpha2, count)
                 - exact_stratum_volume(cfg, cfg.alpha1, count)
                 for count in range(cfg.expected_outer_last + 1))
    require(all(value >= 0 for value in rows), "negative shell volume")
    return sum(rows, Q(0)), rows


def exact_volume_diagnostic() -> dict[str, object]:
    """Proof-grade geometry diagnostic, independent of all search records."""
    old_volume, old_rows = exact_shell_volume(AUDITED)
    new_volume, new_rows = exact_shell_volume(CANDIDATE)
    require(old_volume > 0 and new_volume > 0, "zero shell volume")
    return {
        "audited_shell_volume": old_volume,
        "candidate_shell_volume": new_volume,
        "candidate_over_audited": new_volume / old_volume,
        "candidate_over_audited_decimal": decimal_string(new_volume / old_volume),
        "audited_active_row_count": sum(value > 0 for value in old_rows),
        "candidate_active_row_count": sum(value > 0 for value in new_rows),
        "meaning": (
            "exact constant-function outer-shell I volume only; no G_F, J, "
            "projection, Rayleigh quotient, or theorem inference"),
    }


def strict_outer_cap_reserve_check() -> dict[str, object]:
    """Exhibit an exact nonzero support-cap perturbation interval.

    All active outer caps move together, so every Definition-1 difference is
    unchanged.  Packing is monotone in the tuple caps: checking the upper
    endpoint proves every intermediate schedule; the lower endpoint is a
    support subset but is also checked for its active/empty inventory.
    """
    radius = Q(1, 10**6)
    lower = Config(
        "candidate_outer_caps_lower", CANDIDATE.delta, CANDIDATE.epsilon,
        CANDIDATE.a2, tuple(x - radius for x in CANDIDATE.outer_head), 11)
    upper = Config(
        "candidate_outer_caps_upper", CANDIDATE.delta, CANDIDATE.epsilon,
        CANDIDATE.a2, tuple(x + radius for x in CANDIDATE.outer_head), 11)
    lower_def = definition1_check(lower)
    upper_def = definition1_check(upper)
    upper_fixed = fixed_families_check(upper)
    upper_dynamic = dynamic_iic_check(upper)
    return {
        "uniform_outer_cap_radius": radius,
        "interval": "B_m(candidate)+t for every outer m, |t|<=radius",
        "lower_outer_active": lower_def["outer_active"],
        "upper_outer_active": upper_def["outer_active"],
        "upper_fixed_worst": upper_fixed["IIa_III_worst"],
        "upper_uniform_IIb_worst": upper_fixed["IIb_uniform_empty_third_worst"],
        "upper_dynamic_worst": upper_dynamic["worst"],
        "reason": (
            "Definition-1 steps are invariant under a common translation; "
            "all capped tuple sets for intermediate t are subsets of the "
            "exactly verified upper-endpoint tuple sets"),
    }


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


def check_config(cfg: Config) -> dict[str, object]:
    return {
        "parameters": {
            "delta": cfg.delta, "epsilon": cfg.epsilon,
            "A": (-cfg.epsilon, A1, cfg.a2),
            "A2_minus_A1": cfg.x,
            "cross_omega": cfg.cross_omega,
            "outer_omega": cfg.outer_omega,
            "alpha": (cfg.alpha1, cfg.alpha2),
            "outer_schedule_through_first_empty": cfg.outer_head,
            "main_direct_HB_face": 3 * cfg.x + cfg.delta,
            "main_direct_HB_face_reserve": Q(3, 80) - 3 * cfg.x - cfg.delta,
        },
        "definition1": definition1_check(cfg),
        "source_geometry": source_geometry_check(cfg),
        "fixed_and_literal_IIb": fixed_families_check(cfg),
        "dynamic_IIc": dynamic_iic_check(cfg),
        "proposition2_and_prop1": proposition2_and_prop1_check(cfg),
    }


def build() -> dict[str, object]:
    for relative, expected in PINNED.items():
        actual = sha256(REPO / relative)
        require(actual == expected,
                f"pinned dependency changed: {relative}: {actual}")
    # The historical baseline audit is deliberately not read or pinned: every
    # support-dependent and scalar case is reconstructed here from rationals.
    audited = check_config(AUDITED)
    candidate = check_config(CANDIDATE)
    cap_reserve = strict_outer_cap_reserve_check()
    diagnostics = exact_volume_diagnostic()
    return stringify({
        "status": "EXACT ADAPTIVE ANALYTIC SUPPORT PASS",
        "scope": (
            "specialized direct-HB analytic feasibility only; no sieve "
            "quotient, no projection lower bound, and no H1 theorem claim"),
        "checker_sha256": sha256(FILE),
        "pinned": PINNED,
        "proof_inventory": {
            "ordered_band_pairs_include_zero_counts": True,
            "literal_IIb_gamma_sampling": False,
            "literal_IIb_cover": (
                "empty third bin; every possible exact minimal-prefix "
                "crossing number over the full gamma continuum"),
            "dynamic_IIc_cover": "16x16 adverse-endpoint rational cells",
            "inner_inner": (
                "bilinear Bombieri--Vinogradov below the square root; no "
                "Section-3 packing condition is invoked"),
            "universal_printed_TypeI": (
                "explicitly excluded by the pinned specialized direct-HB "
                "route; its known role-swap defect is not assumed")},
        "independently_audited_baseline_reconstructed": audited,
        "candidate": candidate,
        "candidate_strict_outer_cap_reserve": cap_reserve,
        "exact_volume_diagnostic_not_a_quotient": diagnostics,
        "mechanism_label": (
            "larger-delta correlated-two-bin support; no three-bin "
            "diagnostic is in the PASS dependency closure"),
        "decision": (
            "the frozen delta=1/60 rational point has positive exact source, "
            "packing, empty-range, and prime-minorant margins; heuristic "
            "energy ranking remains outside the proof boundary"),
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
