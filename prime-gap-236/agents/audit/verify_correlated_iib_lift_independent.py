#!/usr/bin/env python3
"""Independent exact audit of the gamma-correlated active-25 support lift.

This file does not import the proposed checker or any arithmetic producer.  It
reconstructs the Definition-1 geometry, all fixed packing families, the full
Type-IIc continuum cover, and the literal gamma-dependent Type-IIb cover from
explicit rational data.  Its result is an analytic support certificate only;
it is not a finite-dimensional quotient certificate.
"""

from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

# These are proof inputs, not code imported by this checker.  The baseline
# audit is pinned to preserve all support-independent parts of the direct-HB
# route; every support-dependent packing case is nevertheless rerun below.
PINNED = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex":
        "60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30",
    "sources/polymath8-edz-1402.0811-src/newergap.tex":
        "fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea",
    "agents/audit/verify_wide_c722_nonuniform_active25_tail_analytic.py":
        "c96b1d1c052a1fe598ac9547b46af3575bc56afb8e6050be7d9384a6861b42f7",
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json":
        "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    "agents/hostile-analytic-audit/c10-analytic-repair-addendum.md":
        "2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7",
    "agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md":
        "47cd11457c44aa2348e7b3d22c5615261c5af04d999414dae3d58eba16f9e80c",
    "agents/hostile-analytic-audit/C10-AUDIT.md":
        "7df85a8ca8b6ea3ab9246e018efd759e6ddf76200f895a141f2ff089da15ccc3",
    "agents/independent-attack/direct-bv-family.md":
        "4daa9590c09db003c6ebbd978ca843a26ec5fe9ab0b0260907ef37fe3a2b91e7",
    "agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md":
        "f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
}

BASELINE_JSON = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")

H = Q(1, 10**10)             # fixed reserve in the direct-HB reduction
HB_SLACK = H / 10
ZETA_MAX = H / 1000          # source-lemma epsilon upper bound
INWARD = H / 10
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(3121, 12000)
INNER_CAP = Q(103, 400)
CROSS_OMEGA = Q(121, 24000)
OUTER_OMEGA = Q(121, 12000)
IIC_AUX = DELTA + H / 4
CELLS = 16
CHANGED_COUNTS = frozenset(range(1, 12))

OLD_OUTER = tuple(Q(text) for text in (
    "597/5000", "633/5000", "669/5000", "141/1000",
    "737/5000", "773/5000", "1553/10000", "809/5000",
    "81/500", "3329/20000", "169/1000", "339/2000",
    "859/5000", "1737/10000", "219/1250", "881/5000",
    "441/2500", "887/5000", "891/5000", "179/1000",
    "449/2500", "1801/10000", "903/5000", "1811/10000",
    "363/2000", "363/2000",
))

NEW_OUTER = tuple(Q(text) for text in (
    "119469/1000000", "126689/1000000", "133909/1000000",
    "141129/1000000", "148349/1000000", "155569/1000000",
    "155569/1000000", "162789/1000000",
    "339/2000", "339/2000", "339/2000", "339/2000",
    "859/5000", "1737/10000", "219/1250", "881/5000",
    "441/2500", "887/5000", "891/5000", "179/1000",
    "449/2500", "1801/10000", "903/5000", "1811/10000",
    "363/2000", "363/2000",
))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(path: Path):
    def object_hook(pairs):
        answer = {}
        for key, value in pairs:
            if key in answer:
                raise ValueError(f"duplicate JSON key {key!r} in {path}")
            answer[key] = value
        return answer

    return json.loads(
        path.read_bytes(), object_pairs_hook=object_hook,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON token {token!r}")))


def ceil_fraction(value: Q) -> int:
    return -((-value.numerator) // value.denominator)


def extend_schedule(head: tuple[Q, ...]) -> tuple[Q, ...]:
    full_length = int(Q(1) // DELTA)
    require(0 < len(head) <= full_length, "invalid schedule-head length")
    return head + (head[-1],) * (full_length - len(head))


INNER = extend_schedule((INNER_CAP,))
OUTER = extend_schedule(NEW_OUTER)
OLD_OUTER_FULL = extend_schedule(OLD_OUTER)


def active_counts(schedule: tuple[Q, ...]) -> tuple[int, ...]:
    return (0,) + tuple(
        count for count, cap in enumerate(schedule, 1)
        if count * DELTA <= cap)


def count_cap(schedule: tuple[Q, ...], count: int) -> Q:
    return Q(0) if count == 0 else schedule[count - 1]


def record_positive(margins: dict[str, Q], name: str, value: Q) -> None:
    require(value > 0, f"nonpositive source margin {name}: {value}")
    margins[name] = value


def definition1_check() -> dict[str, object]:
    margins: dict[str, Q] = {}
    record_positive(margins, "epsilon", EPSILON)
    record_positive(margins, "delta", DELTA)
    record_positive(margins, "A1-A0", A1 + EPSILON)
    record_positive(margins, "A2-A1", A2 - A1)
    record_positive(margins, "one-half-minus-epsilon-minus-A2",
                    Q(1, 2) - EPSILON - A2)

    equality_steps: dict[str, list[int]] = {}
    for label, schedule, expected in (
            ("inner", INNER, tuple(range(36))),
            ("outer", OUTER, tuple(range(26)))):
        equal_delta = []
        equal_zero = []
        for index, value in enumerate(schedule):
            record_positive(margins, f"{label}.B{index + 1}-delta",
                            value - DELTA)
            if index:
                step = value - schedule[index - 1]
                require(Q(0) <= step <= DELTA,
                        f"Definition-1 transition fails: {label} B{index}->B{index+1}")
                if step == DELTA:
                    equal_delta.append(index + 1)
                if step == 0:
                    equal_zero.append(index + 1)
        actual = active_counts(schedule)
        require(actual == expected,
                f"{label} active counts {actual} != {expected}")
        first_empty = expected[-1] + 1
        for count in range(first_empty, len(schedule) + 1):
            record_positive(margins, f"{label}.empty-{count}",
                            count * DELTA - schedule[count - 1])
        equality_steps[label] = equal_delta
        equality_steps[f"{label}_plateau_steps"] = equal_zero

    return {
        "minimum_strict_margin": min(margins.values()),
        "minimum_strict_margin_key": min(margins, key=margins.get),
        "outer_first_empty_margin": 26 * DELTA - OUTER[25],
        "outer_last_active_margin": OUTER[24] - 25 * DELTA,
        "equality_steps_allowed_by_definition": equality_steps,
    }


def gamma_a(omega: Q) -> Q:
    return Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA + 2 * H


def gamma_b(omega: Q) -> Q:
    return Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H


def delta_a(gamma: Q, omega: Q) -> Q:
    return Q(5, 7) * gamma - Q(2, 7) - Q(24, 7) * omega - H


def delta_b(gamma: Q, omega: Q) -> Q:
    return Q(3, 7) * gamma - Q(1, 7) - Q(24, 7) * omega - H


def fixed_capacities(omega: Q) -> dict[str, tuple[Q, Q]]:
    gamma_three = Q(2, 5) - HB_SLACK
    delta_three = (Q(1, 2) - Q(7, 2) * omega
                   - Q(9, 8) * gamma_three - H)
    return {
        "IIa": (
            Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA - 2 * H,
            Q(1, 14) - Q(24, 7) * omega - 2 * H,
        ),
        "III": (
            Q(1, 3) + Q(4, 3) * delta_three
            - Q(4, 3) * omega - H,
            Q(1, 6) - delta_three / 3
            + Q(4, 3) * omega - H,
        ),
    }


def source_geometry_check() -> dict[str, object]:
    """Recheck all support-independent strict faces used by the route."""
    margins: dict[str, Q] = {}

    # Ordered-band maximum exponents in Definition 2.
    exponents = (
        (A1 - EPSILON) + (A1 + EPSILON),
        (A1 - EPSILON) + (A2 + EPSILON),
        (A2 - EPSILON) + (A1 + EPSILON),
        (A2 - EPSILON) + (A2 + EPSILON),
    )
    require(exponents == (
        Q(1, 2), Q(6121, 12000), Q(6121, 12000), Q(3121, 6000)),
        "ordered-band exponent identity changed")
    require(exponents[1] == Q(1, 2) + 2 * CROSS_OMEGA,
            "mixed omega does not match its band exponent")
    require(exponents[3] == Q(1, 2) + 2 * OUTER_OMEGA,
            "outer omega does not match its band exponent")

    sigma = Q(1, 10) + HB_SLACK
    record_positive(margins, "HB.sigma-minus-one-tenth",
                    sigma - Q(1, 10))
    record_positive(margins, "HB.K10", 2 * sigma - Q(1, 10))
    record_positive(margins, "HB.central-lower",
                    (Q(2, 5) - HB_SLACK) - (Q(2, 5) - H))
    record_positive(margins, "HB.III-lower",
                    2 * sigma - (Q(1, 5) - H))
    record_positive(margins, "HB.III-upper",
                    (Q(2, 5) + H) - (Q(1, 2) - sigma))
    record_positive(margins, "HB.III-pair",
                    (Q(1, 2) + sigma) - (Q(3, 5) - H))

    for label, omega in (
            ("near", Q(0)), ("mixed", CROSS_OMEGA),
            ("outer", OUTER_OMEGA)):
        ga = gamma_a(omega)
        gb = gamma_b(omega)
        record_positive(margins, f"{label}.IIa-range", Q(1, 2) - ga)
        record_positive(margins, f"{label}.IIb-range", ga - gb)

        # IIa exact strict distribution faces and Lemma-11 interval faces.
        record_positive(margins, f"{label}.IIa-width",
                        delta_a(ga, omega) - 2 * INWARD - DELTA)
        record_positive(margins, f"{label}.IIa-distribution-1",
                        -2 - (24 * omega + 7 * delta_a(ga, omega) - 5 * ga))
        record_positive(margins, f"{label}.IIa-distribution-2",
                        -(8 * omega + 3 * delta_a(Q(1, 2), omega)
                          - Q(1, 2)))
        record_positive(margins, f"{label}.IIa-a-positive",
                        ga - 3 * ZETA_MAX - delta_a(ga, omega) + INWARD)
        record_positive(margins, f"{label}.IIa-b-below-half", INWARD)
        safe_iia = fixed_capacities(omega)["IIa"]
        record_positive(
            margins, f"{label}.IIa-capacity-1-domination",
            ga - 3 * ZETA_MAX - INWARD - safe_iia[0])
        record_positive(
            margins, f"{label}.IIa-capacity-2-domination",
            Q(1, 14) - Q(24, 7) * omega - H - INWARD
            - safe_iia[1])

        # Literal IIb range.  All extrema are evaluated at their true end.
        db_low = delta_b(gb, omega)
        db_high = delta_b(ga, omega)
        record_positive(margins, f"{label}.IIb-width",
                        db_low - 2 * INWARD - DELTA)
        record_positive(margins, f"{label}.IIb-distribution-1",
                        -1 - (24 * omega + 7 * db_low - 3 * gb))
        record_positive(margins, f"{label}.IIb-distribution-2",
                        -(8 * omega + 3 * db_high - ga))
        record_positive(margins, f"{label}.IIb-upper-U-positive",
                        Q(1, 2) - 2 * omega - ga)

        # Endpoints after replacing each open interval [a_i,b_i] by the
        # closed inward interval [a_i+INWARD,b_i-INWARD].
        a1_min = gb - 3 * ZETA_MAX - db_low + INWARD
        b1_max = ga - INWARD                 # zeta -> 0 adverse endpoint
        a2_min = (Q(1, 2) - ga - 2 * omega - 6 * ZETA_MAX
                  - db_high + INWARD)
        b2_min = Q(1, 2) - ga - 2 * omega - 6 * ZETA_MAX - INWARD
        record_positive(margins, f"{label}.IIb-a1-positive", a1_min)
        record_positive(margins, f"{label}.IIb-b1-below-half",
                        Q(1, 2) - b1_max)
        record_positive(margins, f"{label}.IIb-a2-positive", a2_min)
        record_positive(margins, f"{label}.IIb-b2-positive", b2_min)
        record_positive(margins, f"{label}.IIb-bsum-below-half",
                        2 * omega + 2 * INWARD)
        require((db_low - 2 * INWARD) >= DELTA,
                f"{label} IIb first width below delta")
        require((db_high - 2 * INWARD) >= DELTA,
                f"{label} IIb second width below delta")
        # Equal widths give the remaining Lemma-12 structural inequality.
        b1_same_point = ga - 3 * ZETA_MAX - INWARD
        b2_same_point = (Q(1, 2) - ga - 2 * omega
                         - 6 * ZETA_MAX - INWARD)
        a1_same_point = ga - 3 * ZETA_MAX - db_high + INWARD
        a2_same_point = (Q(1, 2) - ga - 2 * omega
                         - 6 * ZETA_MAX - db_high + INWARD)
        require(b1_same_point - b2_same_point ==
                a1_same_point - a2_same_point,
                f"{label} IIb equal-width structural identity")
        record_positive(margins, f"{label}.IIb-third-bin",
                        DELTA + 2 * omega + Q(2, 7) * H)

        # Corrected fixed-factor Type III source faces.
        gamma_three = Q(2, 5) - HB_SLACK
        delta_three = (Q(1, 2) - Q(7, 2) * omega
                       - Q(9, 8) * gamma_three - H)
        record_positive(margins, f"{label}.III-width",
                        delta_three - 2 * H - DELTA)
        record_positive(margins, f"{label}.III-main",
                        4 - (28 * omega + 9 * gamma_three + 8 * delta_three))
        record_positive(margins, f"{label}.III-second",
                        4 - (16 * omega + 9 * gamma_three + 2 * delta_three))
        record_positive(margins, f"{label}.III-third",
                        4 - (28 * omega + 9 * gamma_three - delta_three))
        record_positive(margins, f"{label}.III-S-lower",
                        1 - 4 * omega + 4 * delta_three)
        record_positive(margins, f"{label}.III-S-upper",
                        1 - 2 * delta_three + 8 * omega)
        record_positive(margins, f"{label}.III-omega", Q(1, 12) - omega)
        type_three_a = Q(1, 3) + delta_three / 3 - Q(4, 3) * omega
        type_three_b = (Q(1, 3) + Q(4, 3) * delta_three
                        - Q(4, 3) * omega)
        record_positive(margins, f"{label}.III-a-positive", type_three_a + H)
        record_positive(margins, f"{label}.III-b-below-half",
                        Q(1, 2) - (type_three_b - H))

        # Type-0 cutoff and prime-power removal are independent of B_m.
        q_exponent = Q(1, 2) + 2 * omega
        record_positive(margins, f"{label}.Type0-sharp",
                        1 - ((Q(1, 2) - sigma) + q_exponent))
        record_positive(margins, f"{label}.Type0-Poisson",
                        1 - (1 - 2 * sigma + 4 * omega))
        record_positive(margins, f"{label}.prime-square", 1 - q_exponent)
        record_positive(margins, f"{label}.higher-prime-powers",
                        1 - q_exponent - Q(1, 3))

    record_positive(margins, "mixed.IIc-empty",
                    (Q(2, 5) - H) - gamma_b(CROSS_OMEGA))
    record_positive(margins, "near.IIc-empty",
                    (Q(2, 5) - H) - gamma_b(Q(0)))

    # Outer/outer IIc source rectangle and inward interval transfer.
    gmin, gmax = Q(2, 5) - H, gamma_b(OUTER_OMEGA)
    d = IIC_AUX
    record_positive(margins, "outer.IIc-gamma-range", gmax - gmin)
    record_positive(margins, "outer.IIc-width", d - 2 * INWARD - DELTA)
    record_positive(margins, "outer.IIc-distribution-1",
                    1 - (8 * OUTER_OMEGA + 4 * d + 2 * gmax))
    record_positive(margins, "outer.IIc-distribution-2",
                    gmin - (32 * OUTER_OMEGA + 10 * d))
    record_positive(margins, "outer.IIc-distribution-3",
                    4 * gmin - 48 * OUTER_OMEGA - 16 * d - 1)
    record_positive(margins, "outer.IIc-proof-start",
                    gmin - 4 * OUTER_OMEGA - d)
    record_positive(margins, "outer.IIc-a1-positive",
                    gmin - 3 * ZETA_MAX - d + INWARD)
    record_positive(margins, "outer.IIc-a2-positive",
                    Q(1, 2) - gmax - 2 * OUTER_OMEGA
                    - 6 * ZETA_MAX - d + INWARD)
    record_positive(margins, "outer.IIc-b1-below-half",
                    Q(1, 2) - gmax + 3 * ZETA_MAX + INWARD)
    record_positive(margins, "outer.IIc-structural", 2 * (d - 2 * INWARD))
    record_positive(margins, "outer.IIc-cell-C1-domination",
                    H - 2 * (d - DELTA) - 58 * ZETA_MAX + INWARD)
    record_positive(margins, "outer.IIc-cell-C2-domination",
                    H - 6 * ZETA_MAX - INWARD)
    record_positive(margins, "outer.IIc-cell-C3-domination", d - DELTA + H)
    record_positive(margins, "outer.IIc-cell-C4-domination", 2 * INWARD)

    return {
        "ordered_band_exponents": exponents,
        "minimum_margin": min(margins.values()),
        "minimum_margin_key": min(margins, key=margins.get),
        "margins": margins,
    }


def prefix_upper(pool_cap: Q, count: int, crossing: int, overload: Q) -> Q:
    """Worst upper bound for the least prefix crossing `overload`."""
    require(1 <= crossing <= count, "bad crossing index")
    if crossing == 1:
        return pool_cap / count
    return overload + (pool_cap - overload) / (count - crossing + 1)


def fixed_partition_certificate(
        left_count: int, right_count: int, left_cap: Q, right_cap: Q,
        capacities: tuple[Q, ...]):
    """A universal first-bin plus one-alternate-bin certificate.

    The tuple has two separately capped pools and every coordinate is at
    least DELTA.  This routine is an independent implementation of the
    minimal-crossing-prefix argument; it never enumerates sample tuples.
    """
    total_count = left_count + right_count
    total_cap = left_cap + right_cap
    first = capacities[0]
    if total_cap < first:
        return first - total_cap, "all-first", 0, 0
    overload = total_cap - first
    candidates = []
    pools = (
        ("left", left_count, left_cap),
        ("right", right_count, right_cap),
        ("combined", total_count, total_cap),
    )
    for pool_name, count, cap in pools:
        if count == 0 or count * DELTA < overload:
            continue
        crossing = ceil_fraction(overload / DELTA)
        if not 1 <= crossing <= count:
            continue
        upper = prefix_upper(cap, count, crossing, overload)
        for alternate_index, alternate in enumerate(capacities[1:], 1):
            if upper < alternate:
                candidates.append((alternate - upper, pool_name,
                                   crossing, alternate_index))
    require(candidates, (
        f"no fixed partition certificate at ({left_count},{right_count}) "
        f"for {tuple(map(str, capacities))}"))
    return max(candidates)


def correlated_iib_certificate(
        left_count: int, right_count: int, left_cap: Q, right_cap: Q,
        omega: Q):
    """Check every possible gamma crossing number, without gamma sampling."""
    gamma_min, gamma_max = gamma_b(omega), gamma_a(omega)
    require(gamma_min < gamma_max, "empty IIb gamma interval")
    total_cap = left_cap + right_cap

    # C=gamma-a and D=b-gamma.  Thus D-(S-C)=b-a-S is constant.
    a = 3 * ZETA_MAX + INWARD
    b = Q(1, 2) - 2 * omega - 6 * ZETA_MAX - INWARD
    constant_window = b - a - total_cap
    require(constant_window > 0,
            f"nonpositive correlated window at ({left_count},{right_count})")
    max_overload = total_cap - (gamma_min - a)
    third_capacity = DELTA + 2 * omega + Q(2, 7) * H
    require(third_capacity > 0, "nonpositive unused IIb third bin")

    if max_overload <= 0:
        return {
            "minimum_margin": -max_overload,
            "worst": ("all-first", 0),
            "crossing_checks": 0,
            "third_capacity": third_capacity,
        }

    pools = (
        ("left", left_count, left_cap),
        ("right", right_count, right_cap),
        ("combined", left_count + right_count, total_cap),
    )
    worst = None
    checks = 0
    for crossing in range(1, ceil_fraction(max_overload / DELTA) + 1):
        candidates = []
        for pool_name, count, cap in pools:
            if count < crossing:
                continue
            require(cap >= count * DELTA,
                    f"infeasible active {pool_name} pool")
            # For all L in ((crossing-1)DELTA,crossing*DELTA],
            # (cap-L)/(count-crossing+1) is worst as L decreases to the
            # left endpoint.  The strict inequality below is consequently
            # valid on the whole gamma interval, including limiting ends.
            if crossing == 1:
                tail_bound = cap / count
            else:
                tail_bound = ((cap - (crossing - 1) * DELTA)
                              / (count - crossing + 1))
            if tail_bound < constant_window:
                candidates.append((constant_window - tail_bound,
                                   pool_name, crossing))
        require(candidates,
                f"IIb sweep fails at ({left_count},{right_count}), r={crossing}")
        best = max(candidates)
        worst = best if worst is None or best < worst else worst
        checks += 1
    require(worst is not None, "missing IIb sweep worst case")
    return {
        "minimum_margin": worst[0],
        "worst": worst[1:],
        "crossing_checks": checks,
        "third_capacity": third_capacity,
    }


FAMILIES = (
    ("mixed", INNER, OUTER, CROSS_OMEGA),
    ("transpose", OUTER, INNER, CROSS_OMEGA),
    ("outer", OUTER, OUTER, OUTER_OMEGA),
    ("outer-near", OUTER, OUTER, Q(0)),
)


def classify_pair(left_count: int, right_count: int) -> str:
    if left_count == 0:
        return "left-zero"
    if right_count == 0:
        return "right-zero"
    if left_count <= 2 and right_count <= 2:
        return "both-positive-at-most-two"
    if (left_count <= 2) != (right_count <= 2):
        return "exactly-one-at-most-two"
    return "both-at-least-three"


def fixed_and_iib_check() -> dict[str, object]:
    fixed_worst = None
    iib_worst = None
    family_inventory = {}
    total_pairs = total_fixed_checks = total_iib_crossings = 0
    changed_pairs = changed_fixed_checks = changed_iib_crossings = 0
    class_inventory: dict[str, int] = {}

    for family, left, right, omega in FAMILIES:
        active_left, active_right = active_counts(left), active_counts(right)
        pairs = fixed_checks = iib_crossings = 0
        for lc in active_left:
            for rc in active_right:
                if lc + rc == 0:
                    continue
                pairs += 1
                affected = (
                    (family == "mixed" and rc in CHANGED_COUNTS) or
                    (family == "transpose" and lc in CHANGED_COUNTS) or
                    (family in ("outer", "outer-near") and
                     (lc in CHANGED_COUNTS or rc in CHANGED_COUNTS)))
                if affected:
                    changed_pairs += 1
                kind = classify_pair(lc, rc)
                class_inventory[kind] = class_inventory.get(kind, 0) + 1
                lcap, rcap = count_cap(left, lc), count_cap(right, rc)
                for branch, capacities in fixed_capacities(omega).items():
                    cert = fixed_partition_certificate(
                        lc, rc, lcap, rcap, capacities)
                    item = (cert[0], family, branch, lc, rc,
                            cert[1], cert[2], cert[3])
                    fixed_worst = (item if fixed_worst is None or
                                   item < fixed_worst else fixed_worst)
                    fixed_checks += 1
                    if affected:
                        changed_fixed_checks += 1
                iib = correlated_iib_certificate(lc, rc, lcap, rcap, omega)
                item = (iib["minimum_margin"], family, lc, rc,
                        *iib["worst"])
                iib_worst = item if iib_worst is None or item < iib_worst else iib_worst
                iib_crossings += iib["crossing_checks"]
                if affected:
                    changed_iib_crossings += iib["crossing_checks"]
        expected_pairs = len(active_left) * len(active_right) - 1
        require(pairs == expected_pairs, f"{family} pair inventory incomplete")
        require(fixed_checks == 2 * pairs,
                f"{family} fixed branch inventory incomplete")
        family_inventory[family] = {
            "pairs": pairs,
            "IIa_III_checks": fixed_checks,
            "IIb_crossing_checks": iib_crossings,
        }
        total_pairs += pairs
        total_fixed_checks += fixed_checks
        total_iib_crossings += iib_crossings

    require(total_pairs == 3220 and total_fixed_checks == 6440,
            "global fixed inventory changed")
    require((changed_pairs, changed_fixed_checks, changed_iib_crossings) ==
            (1694, 3388, 2602), "changed fixed inventory changed")
    require(fixed_worst is not None and fixed_worst[0] > 0,
            "no positive fixed worst case")
    require(iib_worst is not None and iib_worst[0] > 0,
            "no positive IIb worst case")
    require(sum(class_inventory.values()) == total_pairs,
            "small-index class inventory incomplete")
    return {
        "families": family_inventory,
        "total_pairs": total_pairs,
        "IIa_III_checks": total_fixed_checks,
        "IIa_III_worst": fixed_worst,
        "IIb_crossing_checks": total_iib_crossings,
        "IIb_worst": iib_worst,
        "changed_subset": {
            "pairs": changed_pairs,
            "IIa_III_checks": changed_fixed_checks,
            "IIb_crossing_checks": changed_iib_crossings,
        },
        "small_index_partition": class_inventory,
    }


def iic_cell_capacities(gl: Q, gu: Q, wl: Q, wu: Q) -> tuple[Q, ...]:
    capacities = (
        gl - 2 * DELTA - 8 * wu - H,
        Q(1, 2) - gu - 2 * wu - H,
        4 * wl + DELTA - H,
        8 * wl,
    )
    require(min(capacities) >= 0, "negative IIc cell capacity")
    return capacities


def dynamic_iic_check() -> dict[str, object]:
    gamma_min = Q(2, 5) - H
    gamma_max = gamma_b(OUTER_OMEGA)
    active = active_counts(OUTER)
    worst = None
    pairs = checks = changed_pairs = changed_checks = 0
    class_inventory: dict[str, int] = {}
    for lc in active:
        for rc in active:
            if lc + rc == 0:
                continue
            pairs += 1
            affected = lc in CHANGED_COUNTS or rc in CHANGED_COUNTS
            if affected:
                changed_pairs += 1
            kind = classify_pair(lc, rc)
            class_inventory[kind] = class_inventory.get(kind, 0) + 1
            for omega_cell in range(CELLS):
                wl = OUTER_OMEGA * omega_cell / CELLS
                wu = OUTER_OMEGA * (omega_cell + 1) / CELLS
                for gamma_cell in range(CELLS):
                    gl = gamma_min + (gamma_max - gamma_min) * gamma_cell / CELLS
                    gu = gamma_min + (gamma_max - gamma_min) * (gamma_cell + 1) / CELLS
                    capacities = iic_cell_capacities(gl, gu, wl, wu)
                    cert = fixed_partition_certificate(
                        lc, rc, count_cap(OUTER, lc), count_cap(OUTER, rc),
                        capacities)
                    item = (cert[0], lc, rc, omega_cell, gamma_cell,
                            cert[1], cert[2], cert[3])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
                    if affected:
                        changed_checks += 1
    require(pairs == len(active) ** 2 - 1 == 675,
            "dynamic IIc pair inventory")
    require(checks == pairs * CELLS * CELLS == 172800,
            "dynamic IIc cell inventory")
    require((changed_pairs, changed_checks) == (451, 115456),
            "changed dynamic IIc inventory")
    require(worst is not None and worst[0] > 0,
            "nonpositive dynamic IIc worst case")
    return {
        "pairs": pairs,
        "cells_per_pair": CELLS * CELLS,
        "checks": checks,
        "worst": worst,
        "changed_subset": {"pairs": changed_pairs, "checks": changed_checks},
        "small_index_partition": class_inventory,
    }


def schedule_and_embedding_check() -> dict[str, object]:
    gains = tuple(new - old for new, old in zip(NEW_OUTER, OLD_OUTER))
    require(all(gain > 0 for gain in gains[:11]),
            "not every advertised B1..B11 gain is strict")
    require(all(gain == 0 for gain in gains[11:]),
            "a supposedly inherited cap changed")
    require(all(old <= new for old, new in zip(OLD_OUTER_FULL, OUTER)),
            "old support is not contained in new support")

    witnesses = []
    for count in range(1, 12):
        large_sum = (OLD_OUTER[count - 1] + NEW_OUTER[count - 1]) / 2
        large_coordinate = large_sum / count
        small_coordinate = ((Q(13, 50) - large_sum) / (48 - count))
        require(large_coordinate > DELTA > small_coordinate >= 0,
                f"count-{count} witness classification")
        require(A1 + EPSILON < Q(13, 50) < A2 + EPSILON,
                f"count-{count} witness outer-band interior")
        require(OLD_OUTER[count - 1] < large_sum < NEW_OUTER[count - 1],
                f"count-{count} witness cap separation")
        witnesses.append({
            "count": count,
            "large_coordinate": large_coordinate,
            "small_coordinate": small_coordinate,
            "large_sum": large_sum,
            "total": Q(13, 50),
            "old_cap_violation": large_sum - OLD_OUTER[count - 1],
            "new_cap_slack": NEW_OUTER[count - 1] - large_sum,
        })

    return {
        "coordinate_gains": gains,
        "strict_open_witnesses": witnesses,
        "old_support_subset": True,
        "old_old_I_J_block_unchanged": True,
        "embedding_reason": (
            "extend old functions by zero; the A-bands are unchanged, and "
            "the key-integral definition's I/J integrands agree on old-old "
            "pairs; the eleven count-slivers are mutually disjoint"),
        "old_dimension": 27,
        "sliver_count": 11,
        "lifted_dimension": 38,
    }


def coarse_printed_iib_rejection() -> dict[str, object]:
    omega = CROSS_OMEGA
    capacities = (
        Q(1, 3) + 8 * omega + Q(7, 3) * DELTA - 4 * H,
        Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * DELTA - 4 * H,
        DELTA + 2 * omega,
    )
    failed = False
    try:
        fixed_partition_certificate(
            1, 9, INNER_CAP, NEW_OUTER[8], capacities)
    except ArithmeticError:
        failed = True
    require(failed, "coarse endpoint-minimum IIb test unexpectedly accepts")
    return {"family": "mixed", "counts": (1, 9),
            "capacities": capacities, "rejected": True}


def prop1_check() -> dict[str, object]:
    # The deeper equidistribution and weighted-PNT facts are supplied by the
    # pinned baseline proof.  The only B-dependent Prop. 1 side condition is
    # beta > max_j B_{j,1}; it is recomputed here.
    maximum_b1 = max(INNER[0], OUTER[0])
    require(Q(1, 2) > maximum_b1, "beta does not strictly exceed B_{j,1}")
    return {
        "rho": "(log n/log(3x))*1_P on [x,2x], zero outside",
        "minorant_bounds": "0 <= rho <= 1_P",
        "c1": Q(0), "c2": Q(0), "beta": Q(1, 2),
        "beta_minus_max_B1": Q(1, 2) - maximum_b1,
        "equidistribution_route": (
            "pinned direct-HB identity; bilinear BV; Stadlmann Type IIa/IIb/IIc; "
            "corrected fixed-factor Type III"),
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
    for relative, expected in PINNED.items():
        actual = sha256(REPO / relative)
        require(actual == expected,
                f"pinned dependency changed: {relative}: {actual}")
    baseline = strict_json(BASELINE_JSON)
    require(baseline.get("status") == "AUDIT PASS",
            "baseline analytic audit is not PASS")
    require(tuple(Q(text) for text in baseline["parameters"][
        "outer_schedule_through_first_empty"]) == OLD_OUTER,
        "baseline schedule does not equal OLD_OUTER")
    require(baseline["parameters"]["outer_active"] == list(range(26)),
            "baseline active inventory changed")
    # Fail closed if any transitive dependency named by the baseline JSON has
    # drifted.  This closes the otherwise easy source-rebinding hole.
    for relative, expected in baseline.get("pinned", {}).items():
        actual = sha256(REPO / relative)
        require(actual == expected,
                f"baseline transitive dependency changed: {relative}: {actual}")

    geometry = definition1_check()
    source = source_geometry_check()
    fixed = fixed_and_iib_check()
    dynamic = dynamic_iic_check()
    embedding = schedule_and_embedding_check()
    coarse = coarse_printed_iib_rejection()
    prop1 = prop1_check()

    payload = {
        "status": "AUDIT PASS",
        "scope": (
            "independent exact analytic support-lift audit; no sieve quotient "
            "and no H1 theorem claim"),
        "checker_sha256": sha256(FILE),
        "pinned": PINNED,
        "source_line_dependencies": {
            "Definition_1_support": "Bounded_Gaps_2.0.tex:137-150",
            "Definition_2_moduli": "Bounded_Gaps_2.0.tex:155-172",
            "Type_IIb_lemma": "Bounded_Gaps_2.0.tex:593-608,815-886",
            "partition_Lemma_12": "Bounded_Gaps_2.0.tex:1290-1329",
            "Proposition_3_and_literal_IIb_before_simplification":
                "Bounded_Gaps_2.0.tex:1397-1448,1575-1623",
            "key_integrals_and_Prop1": "Bounded_Gaps_2.0.tex:210-241",
        },
        "parameters": {
            "k": 48, "h": H, "delta": DELTA, "epsilon": EPSILON,
            "A": (-EPSILON, A1, A2),
            "omega": (Q(0), CROSS_OMEGA, OUTER_OMEGA),
            "zeta_max": ZETA_MAX, "inward": INWARD,
            "old_outer_schedule": OLD_OUTER,
            "new_outer_schedule": NEW_OUTER,
            "outer_active": active_counts(OUTER),
            "inner_active": active_counts(INNER),
        },
        "definition1": geometry,
        "source_geometry": source,
        "all_fixed_and_correlated_IIb": fixed,
        "all_dynamic_IIc": dynamic,
        "coarse_printed_IIb_test": coarse,
        "support_and_embedding": embedding,
        "Proposition_1": prop1,
        "lemma_statement": (
            "For S=B_m+B_m', C(g)=g-3Z-r0, D(g)=1/2-g-2w-6Z-r0, "
            "L=S-C(g), W=C(g)+D(g)-S: if L<=0 use bin 1; otherwise "
            "r=ceil(L/delta), take the least prefix of one certified pool. "
            "The exact crossing envelopes checked for every possible r put "
            "that prefix strictly below D(g) and its complement below C(g)."),
        "decision": (
            "the gamma-correlated lift is analytically valid relative to the "
            "pinned direct-HB baseline; every old and changed support-dependent "
            "case was recomputed; a separate exact quotient remains required"),
    }
    return stringify(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = (json.dumps(build(), sort_keys=True, separators=(",", ":"))
            + "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    print(data.decode("ascii"), end="")


if __name__ == "__main__":
    main()
