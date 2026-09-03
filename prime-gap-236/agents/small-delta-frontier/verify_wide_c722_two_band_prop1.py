#!/usr/bin/env python3
"""Exact analytic audit for the wide C722 two-band BV-core support.

The inner/inner band is assigned to classical Bombieri--Vinogradov.  Both
ordered mixed bands and the outer/outer band are assigned to the already
source-audited direct Heath--Brown argument, at respectively omega/2 and
omega, where omega=A2-1/4=121/12000.  The mixed Type-IIc gamma range is
empty, so its whole non-small-modulus range may use the fixed mixed upper
parameter.  The outer pair is split once more: the near-square-root strip is
checked at omega=0, while the above-square-root strip uses the fixed outer
upper parameter and the repaired 0<=omega_0<=omega Type-IIc cover.  This
file independently rebuilds all of those fixed covers and every cell of the
conservative 16x16 repaired IIc cover.  It proves no sieve quotient.
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
REPO = FILE.parents[2]
IV_PATH = REPO / "agents/independent-attack/code/interval_partition_verify.py"
IV_SHA256 = "d120c5fac080d494b4876c7186f51123bba66bee5d9a04ec4d7ea79420fac564"
PINNED_ANALYTIC = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "agents/independent-attack/direct-bv-family.md":
        "4daa9590c09db003c6ebbd978ca843a26ec5fe9ab0b0260907ef37fe3a2b91e7",
    "agents/hostile-analytic-audit/direct-hb-prime-equidistribution.md":
        "47cd11457c44aa2348e7b3d22c5615261c5af04d999414dae3d58eba16f9e80c",
    "agents/hostile-analytic-audit/c10-analytic-repair-addendum.md":
        "2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7",
    "agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md":
        "f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
    "agents/small-delta-frontier/audit_c70.py":
        "b01fb7ca8a571d642c24c5fc016cf112ee4b2d65e13fb719e71739fe0a2c53b0",
    "agents/structural-basis/NONCONSTANT-SUPPORT-SEARCH.md":
        "3823ee1efe8618c42c88a6b297b3e8c5689fbc80699f40ac48ac147f8970ccc3",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha256(IV_PATH) != IV_SHA256:
    raise RuntimeError("interval-cover source hash changed")
_spec = importlib.util.spec_from_file_location("wide_c722_interval_cover", IV_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load interval-cover source")
iv = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = iv
_spec.loader.exec_module(iv)


H = Q(1, 10**10)
S = H / 10
ZETA = H / 1000
INWARD = H / 10
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(3121, 12000)
ALPHA1 = A1 + EPSILON
ETA1 = A1 - EPSILON
ALPHA2 = A2 + EPSILON
ETA2 = A2 - EPSILON
CROSS_OMEGA = (A2 - A1) / 2
OUTER_OMEGA = A2 - A1
INNER = (ALPHA1,) * 36
OUTER = tuple(min(Q(11, 200) + (m - 1) * DELTA, Q(43, 250))
              for m in range(1, 25))
XI1, XI2, XI3 = Q(19, 50), Q(2, 5), Q(2, 5)

# Every public cover helper must use this support's geometry even when called
# independently of ``build_result`` (as the hostile low-dimensional tests do).
iv.DELTA, iv.H = DELTA, H


def positive(margins: dict[str, Q], name: str, value: Q) -> None:
    if value <= 0:
        raise ArithmeticError(f"{name} is not positive: {value}")
    margins[name] = value


def ceil_q(value: Q) -> int:
    return -((-value.numerator) // value.denominator)


def active(schedule: tuple[Q, ...]) -> tuple[int, ...]:
    return (0,) + tuple(m for m, value in enumerate(schedule, 1)
                        if m * DELTA <= value)


def check_schedule(name: str, schedule: tuple[Q, ...], expected_last: int,
                   margins: dict[str, Q]) -> tuple[int, ...]:
    if len(schedule) != expected_last:
        raise ArithmeticError(f"{name} schedule does not end at first empty")
    for index, value in enumerate(schedule, 1):
        positive(margins, f"Definition1 {name} B{index}-delta", value - DELTA)
        if index > 1 and not schedule[index - 2] <= value <= \
                schedule[index - 2] + DELTA:
            raise ArithmeticError(f"{name} transition failed at {index}")
    counts = active(schedule)
    if counts != tuple(range(expected_last)):
        raise ArithmeticError(f"{name} active counts changed: {counts}")
    positive(margins, f"Definition1 {name} first-empty",
             expected_last * DELTA - schedule[-1])
    return counts


def fixed_capacities(omega: Q) -> dict[str, tuple[Q, ...]]:
    sigma = Q(1, 10) + S
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    delta_c = DELTA + 4 * H
    gamma_min = Q(2, 5) - H
    gamma_max = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    return {
        "IIa": (Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA - 2 * H,
                Q(1, 14) - Q(24, 7) * omega - 2 * H),
        "IIb": (Q(1, 3) + 8 * omega + Q(7, 3) * DELTA - 4 * H,
                Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * DELTA - 4 * H,
                # C3(gamma)=2*omega+d_b(gamma)+9*zeta increases
                # with gamma.  Its uniform infimum is at G_b and zeta->0.
                # We use the slightly smaller exact-safe lower bound delta+2omega.
                DELTA + 2 * omega),
        "III": (Q(1, 3) + Q(4, 3) * delta3 - Q(4, 3) * omega - H,
                Q(1, 6) - delta3 / 3 + Q(4, 3) * omega - H),
        "IIc": (gamma_min - 2 * delta_c - 8 * omega - 58 * ZETA + INWARD,
                Q(1, 2) - gamma_max - 2 * omega - 6 * ZETA - INWARD,
                delta_c, 2 * INWARD),
    }


def iib_c3_actual_infimum(omega: Q) -> Q:
    """Infimum after the fixed inward ``h`` shifts, before zeta->0.

    Substitution of ``G_b=1/3+8*omega+7*delta/3+3h`` into
    ``2*omega+d_b(G_b)+9*zeta`` gives
    ``delta+2*omega+2h/7+9*zeta``.  Thus the returned zeta->0 infimum
    exceeds the safe capacity used above by exactly ``2h/7``.
    """
    return DELTA + 2 * omega + 2 * H / 7


def prefix_margin(m: int, mp: int, bm: Q, bp: Q, c: Q, d: Q):
    """Exact two-bin minimal-prefix lemma; return its strict slack."""
    total_count, total_bound = m + mp, bm + bp
    if total_bound <= c:
        return c - total_bound, "all-first", 0
    overload = total_bound - c
    choices = []
    for label, count, bound in (("combined", total_count, total_bound),
                                ("left", m, bm), ("right", mp, bp)):
        if count == 0 or count * DELTA < overload:
            continue
        crossing = ceil_q(overload / DELTA)
        if not 1 <= crossing <= count:
            continue
        remaining = count - crossing + 1
        if crossing == 1:
            upper = bound / count
        else:
            upper = overload + (bound - overload) / remaining
        if d > upper:
            choices.append((d - upper, label, crossing))
    if not choices:
        raise ArithmeticError(f"prefix lemma fails at ({m},{mp})")
    return max(choices)


def fixed_prefix_family(left: tuple[Q, ...], right: tuple[Q, ...], omega: Q,
                        *, unordered: bool = False):
    counts_left, counts_right = active(left), active(right)
    caps = fixed_capacities(omega)
    worst = None
    checks = 0
    for m in counts_left:
        for mp in counts_right:
            if m + mp == 0 or (unordered and m > mp):
                continue
            bm = Q(0) if m == 0 else left[m - 1]
            bp = Q(0) if mp == 0 else right[mp - 1]
            for tag, values in caps.items():
                certificate = prefix_margin(m, mp, bm, bp, values[0], values[1])
                item = (certificate[0], tag, m, mp,
                        certificate[1], certificate[2])
                worst = item if worst is None or item < worst else worst
                checks += 1
    return {"pairs": checks // 4, "checks": checks,
            "worst_margin": str(worst[0]), "worst_type": worst[1],
            "worst_pair": [worst[2], worst[3]],
            "worst_assignment": [worst[4], worst[5]]}


def fixed_interval_family(left: tuple[Q, ...], right: tuple[Q, ...], omega: Q,
                          families: tuple[str, ...], *, unordered: bool = False):
    """Exact continuum cover using every bin in each requested family.

    Unlike :func:`fixed_prefix_family`, this is not restricted to a two-bin
    construction.  In particular it guards the omega=0 Type-IIb branch,
    whose third bin can be essential for a mixed schedule even when a
    two-bin prefix shortcut fails.  The production use below is the outer
    near-square-root strip; all of its boxes happen to admit the all-first
    assignment, but the generic interval proof is deliberately retained.
    """
    capacities = fixed_capacities(omega)
    if not families or len(set(families)) != len(families):
        raise ValueError("fixed family list must be nonempty and distinct")
    if any(name not in capacities for name in families):
        raise ValueError("unknown fixed family")
    counts_left, counts_right = active(left), active(right)
    pairs = checks = nodes = leaves = max_depth = 0
    minimum_capacity = None
    worst_all_first = None
    worst_all_first_label = None
    for m in counts_left:
        for mp in counts_right:
            if m + mp == 0 or (unordered and m > mp):
                continue
            bm = Q(0) if m == 0 else left[m - 1]
            bp = Q(0) if mp == 0 else right[mp - 1]
            groups = (iv.initial_group(m, bm), iv.initial_group(mp, bp))
            if None in groups:
                raise ArithmeticError("active fixed pair produced empty group")
            for family in families:
                caps = capacities[family]
                if min(caps) <= 0:
                    raise ArithmeticError(
                        f"nonpositive fixed capacity: {family}, omega={omega}")
                local_capacity = min(caps)
                minimum_capacity = (local_capacity if minimum_capacity is None
                                    else min(minimum_capacity, local_capacity))
                state = cover_groups(groups, caps,
                                     f"fixed {family} omega={omega} ({m},{mp})")
                nodes += state["nodes"]
                leaves += state["leaves"]
                max_depth = max(max_depth, state["max_depth"])
                margin = caps[0] - bm - bp
                item = (margin, family, m, mp)
                if worst_all_first is None or item < worst_all_first:
                    worst_all_first = item
                    worst_all_first_label = [family, m, mp]
                checks += 1
            pairs += 1
    return {"omega": str(omega), "families": list(families),
            "pairs": pairs, "checks": checks, "nodes": nodes,
            "leaves": leaves, "max_depth": max_depth,
            "minimum_capacity": str(minimum_capacity),
            "worst_all_first_margin": str(worst_all_first[0]),
            "worst_all_first_case": worst_all_first_label}


def cell_capacities(gl: Q, gu: Q, wl: Q, wu: Q) -> tuple[Q, ...]:
    return (gl - 2 * DELTA - 8 * wu - H,
            Q(1, 2) - gu - 2 * wu - H,
            4 * wl + DELTA - H, 8 * wl)


def cover_groups(groups, caps: tuple[Q, ...], label: str = "unnamed"):
    state = {"nodes": 0, "leaves": 0, "max_depth": 0,
             "node_limit": 4_000_000, "min_width": Q(1, 10**12),
             "witness_box": None}
    try:
        passed = iv.cover(groups, caps, state)
    except iv.Limit as exc:
        raise ArithmeticError(f"interval-cover node limit: {label}") from exc
    if not passed:
        raise ArithmeticError(f"interval cover unresolved: {label}: {state}")
    return state


def dynamic_iic_family(left: tuple[Q, ...], right: tuple[Q, ...], omega: Q,
                       cells: int = 16):
    gamma_min = Q(2, 5) - H
    gamma_max = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    if gamma_max < gamma_min:
        return {"checks": 0, "nodes": 0, "leaves": 0, "max_depth": 0,
                "minimum_capacity": None,
                "empty_gamma_margin": str(gamma_min - gamma_max)}
    checks = nodes = leaves = max_depth = 0
    worst_capacity = None
    for m in active(left):
        for mp in active(right):
            if m + mp == 0:
                continue
            bm = Q(0) if m == 0 else left[m - 1]
            bp = Q(0) if mp == 0 else right[mp - 1]
            groups = (iv.initial_group(m, bm), iv.initial_group(mp, bp))
            if None in groups:
                raise ArithmeticError("active pair produced an empty interval group")
            for iw in range(cells):
                wl, wu = omega * iw / cells, omega * (iw + 1) / cells
                for ig in range(cells):
                    gl = gamma_min + (gamma_max - gamma_min) * ig / cells
                    gu = gamma_min + (gamma_max - gamma_min) * (ig + 1) / cells
                    caps = cell_capacities(gl, gu, wl, wu)
                    if min(caps) < 0:
                        raise ArithmeticError("negative dynamic capacity")
                    local = min(caps)
                    worst_capacity = local if worst_capacity is None else \
                        min(worst_capacity, local)
                    state = cover_groups(groups, caps,
                                         f"dynamic IIc ({m},{mp}) cell {iw},{ig}")
                    checks += 1
                    nodes += state["nodes"]
                    leaves += state["leaves"]
                    max_depth = max(max_depth, state["max_depth"])
    return {"checks": checks, "nodes": nodes, "leaves": leaves,
            "max_depth": max_depth, "minimum_capacity": str(worst_capacity)}


def scalar_direct_hb(margins: dict[str, Q], tag: str, omega: Q) -> None:
    average_a = Q(1, 4) + omega
    sigma = Q(1, 10) + S
    qexp = 2 * average_a
    positive(margins, f"{tag} Type0 sharp", 1 - ((Q(1, 2) - sigma) + qexp))
    positive(margins, f"{tag} Type0 Poisson", 1 - (1 - 2 * sigma + 4 * omega))
    positive(margins, f"{tag} prime square", 1 - qexp)
    positive(margins, f"{tag} higher prime powers", 1 - (qexp + Q(1, 3)))
    positive(margins, f"{tag} near-square gap", (Q(1, 2) - sigma) -
             (Q(1, 3) + Q(7, 3) * DELTA + 3 * H))
    positive(margins, f"{tag} TypeII 19/2",
             Q(19, 2) - 36 * average_a - 13 * DELTA + 100 * H)
    positive(margins, f"{tag} TypeII first",
             Q(21, 25) - Q(16, 5) * average_a - 2 * H - DELTA)
    positive(margins, f"{tag} TypeII second",
             Q(63, 80) - 3 * average_a - 2 * H - DELTA)
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    positive(margins, f"{tag} TypeIII width", delta3 - DELTA)
    positive(margins, f"{tag} TypeIII distribution",
             4 - (28 * omega + 9 * gamma3 + 8 * delta3))


def build_result():
    if (CROSS_OMEGA, OUTER_OMEGA) != (Q(121, 24000), Q(121, 12000)):
        raise ArithmeticError("omega identities changed")
    for relative, expected in PINNED_ANALYTIC.items():
        actual = sha256(REPO / relative)
        if actual != expected:
            raise RuntimeError(f"pinned source changed: {relative}: {actual}")
    iv.DELTA, iv.H = DELTA, H
    margins: dict[str, Q] = {}
    positive(margins, "Definition1 epsilon", EPSILON)
    positive(margins, "Definition1 delta", DELTA)
    positive(margins, "Definition1 A1-A0", A1 + EPSILON)
    positive(margins, "Definition1 A2-A1", A2 - A1)
    positive(margins, "Definition1 upper", Q(1, 2) - EPSILON - A2)
    inner_active = check_schedule("inner", INNER, 36, margins)
    outer_active = check_schedule("outer", OUTER, 24, margins)
    exponents = {"low_low": (A1 - EPSILON) + (A1 + EPSILON),
                 "low_high": (A1 - EPSILON) + (A2 + EPSILON),
                 "high_low": (A2 - EPSILON) + (A1 + EPSILON),
                 "high_high": (A2 - EPSILON) + (A2 + EPSILON)}
    if exponents != {"low_low": Q(1, 2), "low_high": Q(6121, 12000),
                     "high_low": Q(6121, 12000),
                     "high_high": Q(3121, 6000)}:
        raise ArithmeticError("band-product exponent changed")
    scalar_direct_hb(margins, "mixed", CROSS_OMEGA)
    scalar_direct_hb(margins, "outer", OUTER_OMEGA)
    # The direct-HB square-root split is needed only for the outer pair:
    # mixed IIc is empty at its fixed upper parameter, while outer IIc is not.
    # In the outer near-square-root strip, omega=0 makes IIc empty and the
    # remaining IIa/IIb/III families are checked below with literal bins.
    scalar_direct_hb(margins, "outer near-square", Q(0))
    fixed_caps = {}
    for tag, omega in (("mixed", CROSS_OMEGA), ("outer", OUTER_OMEGA)):
        fixed_caps[tag] = fixed_capacities(omega)
        for family, capacities in fixed_caps[tag].items():
            for index, capacity in enumerate(capacities, 1):
                positive(margins, f"{tag} {family} capacity {index}", capacity)
    fixed_cross = fixed_prefix_family(INNER, OUTER, CROSS_OMEGA)
    fixed_transpose = fixed_prefix_family(OUTER, INNER, CROSS_OMEGA)
    fixed_outer = fixed_prefix_family(OUTER, OUTER, OUTER_OMEGA)
    if (fixed_cross["pairs"], fixed_transpose["pairs"], fixed_outer["pairs"]) != \
            (863, 863, 575):
        raise ArithmeticError("fixed pair inventory changed")
    fixed_outer_near = fixed_interval_family(
        OUTER, OUTER, Q(0), ("IIa", "IIb", "III"), unordered=False)
    if (fixed_outer_near["pairs"], fixed_outer_near["checks"]) != (575, 1725):
        raise ArithmeticError("outer near-square fixed inventory changed")
    if Q(fixed_outer_near["worst_all_first_margin"]) <= 0:
        raise ArithmeticError("outer near-square all-first reserve vanished")
    dynamic_cross = dynamic_iic_family(INNER, OUTER, CROSS_OMEGA)
    dynamic_transpose = dynamic_iic_family(OUTER, INNER, CROSS_OMEGA)
    dynamic_outer = dynamic_iic_family(OUTER, OUTER, OUTER_OMEGA)
    if (dynamic_cross["checks"], dynamic_transpose["checks"],
            dynamic_outer["checks"]) != (0, 0, 147200):
        raise ArithmeticError("dynamic cell inventory changed")
    sigma = Q(1, 10) + S
    positive(margins, "HB sigma endpoint", sigma - Q(1, 10))
    positive(margins, "HB K=10", 2 * sigma - Q(1, 10))
    positive(margins, "HB TypeII lower", (Q(1, 2) - sigma) - (XI2 - H))
    positive(margins, "HB TypeII upper", (1 - XI2 + H) - (Q(1, 2) + sigma))
    positive(margins, "HB TypeIII lower", 2 * sigma - (1 - 2 * XI3 - H))
    positive(margins, "HB TypeIII upper", (XI3 + H) - (Q(1, 2) - sigma))
    positive(margins, "HB TypeIII pair", (Q(1, 2) + sigma) - (1 - XI3 - H))
    for name, schedule in (("inner", INNER), ("outer", OUTER)):
        positive(margins, f"Prop1 beta-{name}-B1", Q(1, 2) - schedule[0])
        positive(margins, f"Prop1 beta-{name}-B2", Q(1, 2) - schedule[1])
    return {
        "status": "wide-c722-two-band-prop1-analytic-pass",
        "scope": "all analytic Proposition-1 hypotheses; exact quotient absent",
        "script_sha256": sha256(FILE),
        "interval_cover_sha256": IV_SHA256,
        "pinned_analytic_dependencies": PINNED_ANALYTIC,
        "parameters": {"k": 48, "epsilon": str(EPSILON),
                       "delta": str(DELTA),
                       "A": [str(-EPSILON), str(A1), str(A2)],
                       "alpha": [str(ALPHA1), str(ALPHA2)],
                       "eta": [str(ETA1), str(ETA2)],
                       "inner_schedule": [str(x) for x in INNER],
                       "outer_schedule": [str(x) for x in OUTER],
                       "active_inner": list(inner_active),
                       "active_outer": list(outer_active),
                       "pair_exponents": {k: str(v) for k, v in exponents.items()},
                       "rho": "(log n/log(3x))*1_P on [x,2x]",
                       "c1": "0", "c2": "0", "beta": "1/2"},
        "distribution_decomposition": {
            "1,1": "classical Bombieri-Vinogradov",
            "1,2": ("repaired direct-HB with fixed upper parameter "
                    "omega=121/24000; Type-IIc range empty"),
            "2,1": ("repaired direct-HB with fixed upper parameter "
                    "omega=121/24000; Type-IIc range empty"),
            "2,2": ("small moduli BV; near-square IIa/IIb/III at omega=0 "
                    "with IIc empty; above-square fixed omega=121/12000 "
                    "plus repaired 0<=omega_0<=omega IIc")},
        "margins": {k: str(v) for k, v in margins.items()},
        "fixed_prefix": {"cross": fixed_cross,
                         "transpose": fixed_transpose,
                         "outer_ordered": fixed_outer},
        "outer_near_square_fixed_interval_cover": fixed_outer_near,
        "fixed_capacities": {
            tag: {family: [str(x) for x in capacities]
                  for family, capacities in families.items()}
            for tag, families in fixed_caps.items()},
        "dynamic_iic_16x16": {"cross": dynamic_cross,
                              "transpose": dynamic_transpose,
                              "outer_ordered": dynamic_outer},
        "finite_union_transfer": (
            "nonnegative Definition-3 discrepancy is restricted to and summed "
            "over four ordered band pairs"),
        "theorem_ready": False,
        "remaining": "exact k=48 quotient above one and final independent audit",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_result()
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
