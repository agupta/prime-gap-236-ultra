#!/usr/bin/env python3
"""Exact certificate for a gamma-correlated Type-IIb active25 lift.

The frozen active25 audit used coordinatewise lower bounds for all three
Type-IIb capacities.  The first two literal capacities move in opposite
directions with gamma and have constant sum.  This checker keeps that
correlation, proves a finite minimal-prefix lemma over the entire gamma
continuum, and rechecks exactly every packing cell affected by raising B1
through B11.  It imports no producer or analytic verifier.

Scope: analytic support and finite-space embedding only; no sieve quotient.
"""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]

PINNED = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "agents/audit/verify_wide_c722_nonuniform_active25_tail_analytic.py":
        "c96b1d1c052a1fe598ac9547b46af3575bc56afb8e6050be7d9384a6861b42f7",
    "agents/audit/results/wide_c722_nonuniform_active25_tail_analytic_audit.json":
        "111a48a23dbf8bf3fdb058f30e6bc412d2eb3cd605557772d6f34056974b2bda",
    "agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md":
        "47cd11457c44aa2348e7b3d22c5615261c5af04d999414dae3d58eba16f9e80c",
    "agents/hostile-analytic-audit/C10-AUDIT.md":
        "7df85a8ca8b6ea3ab9246e018efd759e6ddf76200f895a141f2ff089da15ccc3",
    "agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md":
        "f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
}

BASELINE_JSON = REPO / (
    "agents/audit/results/"
    "wide_c722_nonuniform_active25_tail_analytic_audit.json")

H = Q(1, 10**10)
ZETA = H / 1000
R0 = H / 10
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(3121, 12000)
INNER_CAP = Q(103, 400)
CROSS_W = Q(121, 24000)
OUTER_W = Q(121, 12000)
CELLS = 16
CHANGED = frozenset(range(1, 12))

OLD_OUTER = tuple(Q(x) for x in (
    "597/5000", "633/5000", "669/5000", "141/1000",
    "737/5000", "773/5000", "1553/10000", "809/5000",
    "81/500", "3329/20000", "1690/10000", "1695/10000",
    "1718/10000", "1737/10000", "1752/10000", "1762/10000",
    "1764/10000", "1774/10000", "1782/10000", "1790/10000",
    "1796/10000", "1801/10000", "1806/10000", "1811/10000",
    "1815/10000", "1815/10000",
))
NEW_OUTER = tuple(Q(x) for x in (
    "119469/1000000", "126689/1000000", "133909/1000000",
    "141129/1000000", "148349/1000000", "155569/1000000",
    "155569/1000000", "162789/1000000",
    "339/2000", "339/2000", "339/2000",
)) + OLD_OUTER[11:]
INNER = (INNER_CAP,) * 36


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def strict_json(path: Path):
    def hook(pairs):
        answer = {}
        for key, value in pairs:
            if key in answer:
                raise ValueError(f"duplicate JSON key: {key}")
            answer[key] = value
        return answer
    return json.loads(path.read_text(encoding="ascii"), object_pairs_hook=hook)


def ceilq(value: Q) -> int:
    return -((-value.numerator) // value.denominator)


def active(head: tuple[Q, ...]) -> tuple[int, ...]:
    return (0,) + tuple(count for count, cap in enumerate(head, 1)
                        if count * DELTA <= cap)


def bound(head: tuple[Q, ...], count: int) -> Q:
    return Q(0) if count == 0 else head[count - 1]


def check_schedule(head: tuple[Q, ...]) -> dict[str, Q]:
    length = int(Q(1) // DELTA)
    full = head + (head[-1],) * (length - len(head))
    require(len(full) == 138, "Definition-1 schedule length")
    margins = {}
    for index, value in enumerate(full):
        require(value > DELTA, f"B{index + 1} <= delta")
        margins[f"B{index + 1}-delta"] = value - DELTA
        if index:
            require(full[index - 1] <= value <=
                    full[index - 1] + DELTA,
                    f"bad Definition-1 transition {index}->{index + 1}")
    require(active(head) == tuple(range(26)), "active counts changed")
    margins["first-empty"] = 26 * DELTA - full[25]
    require(margins["first-empty"] > 0, "count 26 is not empty")
    return margins


def prefix_certificate(m: int, mp: int, bm: Q, bp: Q,
                       capacities: tuple[Q, ...]):
    """Universal minimal-prefix certificate for one alternate bin."""
    total_count, total_bound = m + mp, bm + bp
    if total_bound < capacities[0]:
        return capacities[0] - total_bound, "all-first", 0, 0
    overload = total_bound - capacities[0]
    choices = []
    for label, count, cap in (("left", m, bm), ("right", mp, bp),
                              ("combined", total_count, total_bound)):
        if count == 0 or count * DELTA < overload:
            continue
        crossing = ceilq(overload / DELTA)
        if not 1 <= crossing <= count:
            continue
        if crossing == 1:
            upper = cap / count
        else:
            upper = overload + (cap - overload) / (count - crossing + 1)
        for alternate, capacity in enumerate(capacities[1:], 1):
            if upper < capacity:
                choices.append(
                    (capacity - upper, label, crossing, alternate))
    return max(choices) if choices else None


def fixed_capacities(omega: Q) -> dict[str, tuple[Q, ...]]:
    gamma3 = Q(2, 5) - H / 10
    d3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    answer = {
        "IIa": (
            Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA - 2 * H,
            Q(1, 14) - Q(24, 7) * omega - 2 * H,
        ),
        "III": (
            Q(1, 3) + Q(4, 3) * d3 - Q(4, 3) * omega - H,
            Q(1, 6) - d3 / 3 + Q(4, 3) * omega - H,
        ),
    }
    require(min(value for values in answer.values() for value in values) > 0,
            "nonpositive fixed capacity")
    return answer


def gamma_bounds(omega: Q) -> tuple[Q, Q]:
    lower = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    upper = Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA + 2 * H
    require(upper > lower, "empty Type-IIb gamma range")
    return lower, upper


def iib_sweep_certificate(m: int, mp: int, bm: Q, bp: Q,
                          omega: Q):
    """Certify literal Type-IIb packing uniformly over the gamma interval.

    After the audited inward shrink, safe first/second capacities are

        C(gamma)=gamma-3*ZETA-R0,
        D(gamma)=1/2-gamma-2*omega-6*ZETA-R0.

    Their sum is constant.  For S=bm+bp and L=S-C(gamma), a minimal
    increasing prefix from a chosen pool crosses every actual overload by
    its r-th term, r=ceil(L/delta).  The returned finite checks prove the
    construction for every real tuple and every gamma, not sample points.
    """
    gamma_min, _gamma_max = gamma_bounds(omega)
    a = 3 * ZETA + R0
    b = Q(1, 2) - 2 * omega - 6 * ZETA - R0
    total_cap = bm + bp
    window = (b - a) - total_cap  # D(gamma)-L(gamma), constant.
    require(window > 0, f"nonpositive IIb window at pair {m},{mp}")

    # The unused third capacity is at least 2w+d_b(G_b)=d+2w+2h/7.
    third_min = DELTA + 2 * omega + Q(2, 7) * H
    require(third_min > 0, "nonpositive unused third capacity")

    largest_L = total_cap - (gamma_min - a)
    if largest_L <= 0:
        return (-largest_L, "all-first", 0), 0, third_min

    pools = (("left", m, bm), ("right", mp, bp),
             ("combined", m + mp, total_cap))
    worst = None
    checks = 0
    for crossing in range(1, ceilq(largest_L / DELTA) + 1):
        choices = []
        for label, count, pool_cap in pools:
            if count < crossing:
                continue
            require(pool_cap >= count * DELTA,
                    f"infeasible active pool {label} at pair {m},{mp}")
            if crossing == 1:
                margin = window - pool_cap / count
            else:
                margin = window - (
                    pool_cap - (crossing - 1) * DELTA
                ) / (count - crossing + 1)
            if margin > 0:
                choices.append((margin, label, crossing))
        require(bool(choices),
                f"no correlated IIb prefix at pair {m},{mp}, r={crossing}")
        best = max(choices)
        worst = best if worst is None or best < worst else worst
        checks += 1
    require(worst is not None, "missing Type-IIb sweep result")
    return worst, checks, third_min


def dynamic_iic_capacities(gl: Q, gu: Q, wl: Q, wu: Q):
    answer = (
        gl - 2 * DELTA - 8 * wu - H,
        Q(1, 2) - gu - 2 * wu - H,
        4 * wl + DELTA - H,
        8 * wl,
    )
    require(min(answer) >= 0, "negative Type-IIc cell capacity")
    return answer


def changed_pair(m: int, mp: int, left_outer: bool,
                 right_outer: bool) -> bool:
    return ((left_outer and m in CHANGED) or
            (right_outer and mp in CHANGED))


def check_changed_fixed():
    families = (
        ("mixed", INNER, NEW_OUTER, CROSS_W, False, True),
        ("transpose", NEW_OUTER, INNER, CROSS_W, True, False),
        ("outer", NEW_OUTER, NEW_OUTER, OUTER_W, True, True),
        ("outer-near", NEW_OUTER, NEW_OUTER, Q(0), True, True),
    )
    fixed_worst = None
    iib_worst = None
    pair_count = fixed_checks = iib_prefix_checks = 0
    third_minimum = None
    for family, left, right, omega, left_outer, right_outer in families:
        caps = fixed_capacities(omega)
        for m in active(left):
            for mp in active(right):
                if m + mp == 0 or not changed_pair(
                        m, mp, left_outer, right_outer):
                    continue
                pair_count += 1
                bm, bp = bound(left, m), bound(right, mp)
                for branch, values in caps.items():
                    cert = prefix_certificate(m, mp, bm, bp, values)
                    require(cert is not None and cert[0] > 0,
                            f"failed {family} {branch} at {m},{mp}")
                    item = (cert[0], family, branch, m, mp,
                            cert[1], cert[2], cert[3])
                    fixed_worst = (item if fixed_worst is None or
                                   item < fixed_worst else fixed_worst)
                    fixed_checks += 1

                cert, checks, third = iib_sweep_certificate(
                    m, mp, bm, bp, omega)
                item = (cert[0], family, m, mp, cert[1], cert[2])
                iib_worst = (item if iib_worst is None or
                              item < iib_worst else iib_worst)
                iib_prefix_checks += checks
                third_minimum = (third if third_minimum is None or
                                 third < third_minimum else third_minimum)
    require((pair_count, fixed_checks) == (1694, 3388),
            "changed fixed-family inventory")
    return {
        "ordered_pairs": pair_count,
        "IIa_III_checks": fixed_checks,
        "IIa_III_worst": fixed_worst,
        "IIb_crossing_number_checks": iib_prefix_checks,
        "IIb_worst": iib_worst,
        "IIb_unused_third_capacity_minimum": third_minimum,
    }


def check_changed_dynamic_iic():
    gamma_min = Q(2, 5) - H
    gamma_max = Q(1, 3) + 8 * OUTER_W + Q(7, 3) * DELTA + 3 * H
    worst = None
    pairs = checks = 0
    for m in active(NEW_OUTER):
        for mp in active(NEW_OUTER):
            if not (m in CHANGED or mp in CHANGED):
                continue
            pairs += 1
            for iw in range(CELLS):
                wl = OUTER_W * iw / CELLS
                wu = OUTER_W * (iw + 1) / CELLS
                for ig in range(CELLS):
                    gl = gamma_min + (gamma_max - gamma_min) * ig / CELLS
                    gu = gamma_min + (gamma_max - gamma_min) * (ig + 1) / CELLS
                    caps = dynamic_iic_capacities(gl, gu, wl, wu)
                    cert = prefix_certificate(
                        m, mp, bound(NEW_OUTER, m), bound(NEW_OUTER, mp), caps)
                    require(cert is not None and cert[0] > 0,
                            f"failed dynamic IIc at {m},{mp},{iw},{ig}")
                    item = (cert[0], m, mp, iw, ig,
                            cert[1], cert[2], cert[3])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
    require((pairs, checks) == (451, 115456),
            "changed dynamic-IIc inventory")
    return {"ordered_pairs": pairs, "checks": checks, "worst": worst}


def support_witness(count: int, large_sum: Q):
    large = large_sum / count
    small_count = 48 - count
    small = (Q(13, 50) - large_sum) / small_count
    old_cap, new_cap = OLD_OUTER[count - 1], NEW_OUTER[count - 1]
    require(large > DELTA > small >= 0, "witness count classification")
    require(Q(103, 400) < Q(13, 50) < A2 + EPSILON,
            "witness is not in the outer band")
    require(old_cap < large_sum < new_cap,
            "witness does not separate the supports")
    return {
        "count": count,
        "large_coordinate": large,
        "small_coordinate": small,
        "total_sum": Q(13, 50),
        "large_sum": large_sum,
        "old_cap": old_cap,
        "new_cap": new_cap,
        "old_cap_violation": large_sum - old_cap,
        "new_cap_slack": new_cap - large_sum,
    }


def coarse_iib_failure():
    omega = CROSS_W
    capacities = (
        Q(1, 3) + 8 * omega + Q(7, 3) * DELTA - 4 * H,
        Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * DELTA - 4 * H,
        DELTA + 2 * omega,
    )
    cert = prefix_certificate(1, 9, INNER_CAP, NEW_OUTER[8], capacities)
    require(cert is None, "coarse Type-IIb test unexpectedly accepts lift")
    return {"family": "mixed", "pair": (1, 9),
            "capacities": capacities, "certificate": None}


def stringify(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, tuple):
        return [stringify(item) for item in value]
    if isinstance(value, list):
        return [stringify(item) for item in value]
    if isinstance(value, dict):
        return {key: stringify(item) for key, item in value.items()}
    return value


def build():
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected,
                f"pinned dependency changed: {relative}")
    baseline = strict_json(BASELINE_JSON)
    require(baseline.get("status") == "AUDIT PASS", "baseline audit status")
    require(tuple(Q(x) for x in baseline["parameters"][
        "outer_schedule_through_first_empty"]) == OLD_OUTER,
        "baseline schedule identity")
    require(baseline["parameters"]["outer_active"] == list(range(26)) and
            baseline["dynamic_iic"]["checks"] == 172800,
            "baseline completeness identity")

    schedule_margins = check_schedule(NEW_OUTER)
    gains = tuple(new - old for new, old in zip(NEW_OUTER, OLD_OUTER))
    require(all(gain > 0 for gain in gains[:11]) and
            all(gain == 0 for gain in gains[11:]),
            "schedule gain identity")

    fixed = check_changed_fixed()
    dynamic = check_changed_dynamic_iic()
    witnesses = tuple(
        support_witness(
            count,
            (OLD_OUTER[count - 1] + NEW_OUTER[count - 1]) / 2)
        for count in sorted(CHANGED)
    )
    coarse = coarse_iib_failure()

    result = {
        "status": "EXACT ANALYTIC SUPPORT LIFT PASS",
        "scope": "support and finite-space embedding; no quotient or theorem claim",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "parameters": {
            "k": 48, "delta": DELTA, "epsilon": EPSILON,
            "A": (-EPSILON, A1, A2),
            "correlated_iib_gamma_cells": "none: exact crossing-number sweep",
            "dynamic_iic_cells": (CELLS, CELLS),
        },
        "old_schedule": OLD_OUTER,
        "new_schedule": NEW_OUTER,
        "coordinate_gains": gains,
        "active_counts": active(NEW_OUTER),
        "definition1_least_margin": min(schedule_margins.values()),
        "changed_fixed_families": fixed,
        "changed_dynamic_iic": dynamic,
        "old_coarse_sufficient_test_failure": coarse,
        "strict_support_witnesses": witnesses,
        "finite_space_embedding": {
            "old_active25_dimension": 27,
            "append_disjoint_sliver_indicators": tuple(
                f"S{count}" for count in sorted(CHANGED)),
            "lifted_dimension": 38,
            "old_quadratic_block_unchanged": True,
            "reason": (
                "extend every old-support function by zero; A and epsilon "
                "are unchanged, so both I and every old-old J entry are "
                "identical; only eleven sliver rows/columns are new"),
        },
        "decision": (
            "retaining the literal gamma correlation in Type IIb permits "
            "a pointwise support lift in every cap B1 through B11 while "
            "preserving the audited direct-HB route"),
    }
    return stringify(result)


if __name__ == "__main__":
    print(json.dumps(build(), sort_keys=True, separators=(",", ":")))
