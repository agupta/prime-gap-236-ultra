#!/usr/bin/env python3
"""Independent exact analytic verifier for the p=.172 wide C722 support.

This reconstructs the source inequalities and continuous packing certificates
without importing either discovery-side wide-support checker.  It proves no
finite-dimensional sieve quotient.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[2]
PINNED = {
    "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex":
        "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba",
    "sources/polymath8-edz-1402.0811-src/newergap.tex":
        "fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea",
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
    "scripts/verify_bv_c722_hybrid_geometry.py":
        "ffe1904e70f6240ca0de30d6a44ad275ce84982f973374e66f2a3a2ab3025c06",
    "results/bv_c722_wide_two_band_geometry_high_plateau_v3.json":
        "e71f541136ff83ded8cbc609f875b2b98cd9ea769df878a01a56e9730edbb0fe",
}

H = Q(1, 10**10)
S = H / 10
ZETA = H / 1000
R0 = H / 10
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A1 = Q(1, 4)
A2 = Q(3121, 12000)
CROSS_W = Q(121, 24000)
OUTER_W = Q(121, 12000)
INNER_CAP = Q(103, 400)
OUTER_CAP = Q(43, 250)
IIIC_AUX = DELTA + H / 4
CELLS = 16


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArithmeticError(message)


def positive(margins: dict[str, Q], name: str, value: Q) -> Q:
    require(value > 0, f"nonpositive {name}: {value}")
    margins[name] = value
    return value


def ceilq(value: Q) -> int:
    return -((-value.numerator) // value.denominator)


def schedule_heads() -> tuple[tuple[Q, ...], tuple[Q, ...]]:
    inner = (INNER_CAP,) * 36
    outer = tuple(min(Q(11, 200) + (m - 1) * DELTA, OUTER_CAP)
                  for m in range(1, 25))
    return inner, outer


def extend(head: tuple[Q, ...]) -> tuple[Q, ...]:
    length = int(Q(1) // DELTA)
    require(len(head) <= length, "schedule head too long")
    return head + (head[-1],) * (length - len(head))


def active(head: tuple[Q, ...]) -> tuple[int, ...]:
    return (0,) + tuple(m for m, bound in enumerate(head, 1)
                        if m * DELTA <= bound)


def bound(head: tuple[Q, ...], count: int) -> Q:
    return Q(0) if count == 0 else head[count - 1]


def check_schedule(name: str, head: tuple[Q, ...], expected: tuple[int, ...],
                   margins: dict[str, Q]) -> None:
    full = extend(head)
    require(len(full) == 138, f"{name} full schedule length")
    for index, value in enumerate(full):
        positive(margins, f"{name}.B{index + 1}-delta", value - DELTA)
        if index:
            require(full[index - 1] <= value <= full[index - 1] + DELTA,
                    f"{name} transition {index}->{index + 1}")
    require(active(head) == expected, f"{name} active inventory")
    first_empty = expected[-1] + 1
    positive(margins, f"{name}.first-empty",
             first_empty * DELTA - full[first_empty - 1])
    for count in range(first_empty, 139):
        positive(margins, f"{name}.empty-{count}",
                 count * DELTA - full[count - 1])


def da(gamma: Q, omega: Q) -> Q:
    return Q(5, 7) * gamma - Q(2, 7) - Q(24, 7) * omega - H


def db(gamma: Q, omega: Q) -> Q:
    return Q(3, 7) * gamma - Q(1, 7) - Q(24, 7) * omega - H


def ga(omega: Q) -> Q:
    return Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA + 2 * H


def gb(omega: Q) -> Q:
    return Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H


def fixed_capacities(omega: Q) -> dict[str, tuple[Q, ...]]:
    gamma3 = Q(2, 5) - S
    d3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    return {
        "IIa": (Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA - 2 * H,
                 Q(1, 14) - Q(24, 7) * omega - 2 * H),
        "IIb": (Q(1, 3) + 8 * omega + Q(7, 3) * DELTA - 4 * H,
                 Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * DELTA - 4 * H,
                 DELTA + 2 * omega),
        "III": (Q(1, 3) + Q(4, 3) * d3 - Q(4, 3) * omega - H,
                 Q(1, 6) - d3 / 3 + Q(4, 3) * omega - H),
    }


def prefix_certificate(m: int, mp: int, bm: Q, bp: Q,
                       capacities: tuple[Q, ...]):
    """Universal minimal-crossing-prefix certificate, with exact slack."""
    total_count, total_bound = m + mp, bm + bp
    if total_bound < capacities[0]:
        return capacities[0] - total_bound, "all-first", 0, 0
    overload = total_bound - capacities[0]
    answers = []
    for pool, count, cap in (("left", m, bm), ("right", mp, bp),
                             ("combined", total_count, total_bound)):
        if count == 0 or count * DELTA < overload:
            continue
        crossing = ceilq(overload / DELTA)
        if not 1 <= crossing <= count:
            continue
        if crossing == 1:
            upper = cap / count
        else:
            upper = overload + ((cap - overload) /
                                (count - crossing + 1))
        for alternate, capacity in enumerate(capacities[1:], 1):
            if upper < capacity:
                answers.append((capacity - upper, pool, crossing, alternate))
    require(bool(answers), f"no prefix certificate for {m},{mp},{capacities}")
    return max(answers)


def check_fixed_family(left: tuple[Q, ...], right: tuple[Q, ...], omega: Q,
                       name: str) -> dict[str, object]:
    caps = fixed_capacities(omega)
    worst = None
    pairs = checks = 0
    for m in active(left):
        for mp in active(right):
            if m + mp == 0:
                continue
            for branch, values in caps.items():
                cert = prefix_certificate(m, mp, bound(left, m),
                                          bound(right, mp), values)
                item = (cert[0], branch, m, mp, cert[1], cert[2], cert[3])
                worst = item if worst is None or item < worst else worst
                checks += 1
            pairs += 1
    require(worst is not None, f"no fixed checks for {name}")
    return {"pairs": pairs, "checks": checks, "worst_margin": str(worst[0]),
            "worst": [worst[1], worst[2], worst[3], worst[4],
                      worst[5], worst[6]]}


def check_source_geometry(omega: Q, name: str, margins: dict[str, Q]) -> None:
    g_a, g_b = ga(omega), gb(omega)
    positive(margins, f"{name}.IIa-range", Q(1, 2) - g_a)
    positive(margins, f"{name}.IIb-range", g_a - g_b)

    # IIa: both open endpoints are moved inward by R0.
    positive(margins, f"{name}.IIa-width", da(g_a, omega) - 2 * R0 - DELTA)
    positive(margins, f"{name}.IIa-face1",
             -2 - (24 * omega + 7 * da(g_a, omega) - 5 * g_a))
    positive(margins, f"{name}.IIa-face2",
             -(8 * omega + 3 * da(Q(1, 2), omega) - Q(1, 2)))
    positive(margins, f"{name}.IIa-lower-endpoint",
             g_a - 3 * ZETA - da(g_a, omega) + R0)
    positive(margins, f"{name}.IIa-upper-endpoint",
             Q(1, 2) - (Q(1, 2) - R0))
    safe = fixed_capacities(omega)["IIa"]
    actual1 = g_a - 3 * ZETA - R0
    actual2 = Q(1, 14) - Q(24, 7) * omega - H - R0
    positive(margins, f"{name}.IIa-cap1-domination", actual1 - safe[0])
    positive(margins, f"{name}.IIa-cap2-domination", actual2 - safe[1])

    # IIb: C3 is increasing in gamma; use its lower-end value, not the
    # erroneous upper-end value printed in the paper.
    positive(margins, f"{name}.IIb-width", db(g_b, omega) - 2 * R0 - DELTA)
    positive(margins, f"{name}.IIb-face1",
             -1 - (24 * omega + 7 * db(g_b, omega) - 3 * g_b))
    positive(margins, f"{name}.IIb-face2",
             -(8 * omega + 3 * db(g_a, omega) - g_a))
    positive(margins, f"{name}.IIb-first-lower",
             g_b - 3 * ZETA - db(g_b, omega) + R0)
    positive(margins, f"{name}.IIb-second-lower",
             Q(1, 2) - g_a - 2 * omega - 6 * ZETA -
             db(g_a, omega) + R0)
    positive(margins, f"{name}.IIb-bsum",
             2 * omega + 9 * ZETA + 2 * R0)
    safe = fixed_capacities(omega)["IIb"]
    actual1 = g_b - 3 * ZETA - R0
    actual2 = Q(1, 2) - g_a - 2 * omega - 6 * ZETA - R0
    actual3 = 2 * omega + db(g_b, omega)
    positive(margins, f"{name}.IIb-cap1-domination", actual1 - safe[0])
    positive(margins, f"{name}.IIb-cap2-domination", actual2 - safe[1])
    positive(margins, f"{name}.IIb-cap3-domination", actual3 - safe[2])

    # Corrected Type III, including the fixed-factor side conditions.
    gamma3 = Q(2, 5) - S
    d3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    positive(margins, f"{name}.III-width", d3 - 2 * H - DELTA)
    positive(margins, f"{name}.III-main",
             4 - (28 * omega + 9 * gamma3 + 8 * d3))
    positive(margins, f"{name}.III-second",
             4 - (16 * omega + 9 * gamma3 + 2 * d3))
    positive(margins, f"{name}.III-third",
             4 - (28 * omega + 9 * gamma3 - d3))
    positive(margins, f"{name}.III-S-lower", 1 - 4 * omega + 4 * d3)
    positive(margins, f"{name}.III-S-upper", 1 - 2 * d3 + 8 * omega)
    positive(margins, f"{name}.III-omega", Q(1, 12) - omega)
    a3 = Q(1, 3) + d3 / 3 - Q(4, 3) * omega
    b3 = Q(1, 3) + Q(4, 3) * d3 - Q(4, 3) * omega
    positive(margins, f"{name}.III-a", a3 + H)
    positive(margins, f"{name}.III-b", Q(1, 2) - (b3 - H))

    # Type 0, cutoff repair, and prime-power removal.
    qexp = Q(1, 2) + 2 * omega
    positive(margins, f"{name}.Type0-sharp",
             1 - ((Q(1, 2) - (Q(1, 10) + S)) + qexp))
    positive(margins, f"{name}.Type0-Poisson",
             1 - (1 - 2 * (Q(1, 10) + S) + 4 * omega))
    positive(margins, f"{name}.prime-square", 1 - qexp)
    positive(margins, f"{name}.higher-prime-powers", 1 - qexp - Q(1, 3))


def cell_capacities(gl: Q, gu: Q, wl: Q, wu: Q) -> tuple[Q, ...]:
    return (gl - 2 * DELTA - 8 * wu - H,
            Q(1, 2) - gu - 2 * wu - H,
            4 * wl + DELTA - H,
            8 * wl)


def check_dynamic_outer(outer: tuple[Q, ...]) -> dict[str, object]:
    gmin, gmax = Q(2, 5) - H, gb(OUTER_W)
    worst = None
    pairs = checks = 0
    for m in active(outer):
        for mp in active(outer):
            if m + mp == 0:
                continue
            for iw in range(CELLS):
                wl, wu = OUTER_W * iw / CELLS, OUTER_W * (iw + 1) / CELLS
                for ig in range(CELLS):
                    gl = gmin + (gmax - gmin) * ig / CELLS
                    gu = gmin + (gmax - gmin) * (ig + 1) / CELLS
                    caps = cell_capacities(gl, gu, wl, wu)
                    require(min(caps) >= 0, "negative cell capacity")
                    cert = prefix_certificate(m, mp, bound(outer, m),
                                              bound(outer, mp), caps)
                    item = (cert[0], m, mp, iw, ig, cert[1], cert[2], cert[3])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
            pairs += 1
    require(worst is not None, "no dynamic checks")
    require((pairs, checks) == (575, 147200), "dynamic inventory")
    return {"pairs": pairs, "checks": checks, "worst_margin": str(worst[0]),
            "worst": list(worst[1:])}


def check_iic_source(margins: dict[str, Q]) -> None:
    gmin, gmax = Q(2, 5) - H, gb(OUTER_W)
    d = IIIC_AUX
    positive(margins, "outer.IIc-gamma-range", gmax - gmin)
    positive(margins, "outer.IIc-width", d - 2 * R0 - DELTA)
    positive(margins, "outer.IIc-face1", 1 - (8 * OUTER_W + 4 * d + 2 * gmax))
    positive(margins, "outer.IIc-face2", gmin - (32 * OUTER_W + 10 * d))
    positive(margins, "outer.IIc-face3", 4 * gmin - 48 * OUTER_W - 16 * d - 1)
    positive(margins, "outer.IIc-proof-start", gmin - 4 * OUTER_W - d)
    positive(margins, "outer.IIc-a1", gmin - 3 * ZETA - d + R0)
    positive(margins, "outer.IIc-a2",
             Q(1, 2) - gmax - 2 * OUTER_W - 6 * ZETA - d + R0)
    positive(margins, "outer.IIc-b1", Q(1, 2) - gmax + 3 * ZETA + R0)
    positive(margins, "outer.IIc-structural", 2 * (d - 2 * R0))
    # The four cell capacities are strict lower bounds for the literal
    # inward-shrunk Lemma-13 capacities at every point of their cell.
    positive(margins, "outer.IIc-cell-C1-domination",
             H - 2 * (d - DELTA) - 58 * ZETA + R0)
    positive(margins, "outer.IIc-cell-C2-domination", H - 6 * ZETA - R0)
    positive(margins, "outer.IIc-cell-C3-domination", d - DELTA + H)
    positive(margins, "outer.IIc-cell-C4-domination", 2 * R0)


def build() -> dict[str, object]:
    for relative, expected in PINNED.items():
        require(sha(REPO / relative) == expected, f"pinned hash changed: {relative}")
    margins: dict[str, Q] = {}
    positive(margins, "Definition1.epsilon", EPSILON)
    positive(margins, "Definition1.delta", DELTA)
    positive(margins, "Definition1.A1-A0", A1 + EPSILON)
    positive(margins, "Definition1.A2-A1", A2 - A1)
    positive(margins, "Definition1.upper", Q(1, 2) - EPSILON - A2)
    inner, outer = schedule_heads()
    check_schedule("inner", inner, tuple(range(36)), margins)
    check_schedule("outer", outer, tuple(range(24)), margins)
    exponents = (A1 - EPSILON + A1 + EPSILON,
                 A1 - EPSILON + A2 + EPSILON,
                 A2 - EPSILON + A1 + EPSILON,
                 A2 - EPSILON + A2 + EPSILON)
    require(exponents == (Q(1, 2), Q(6121, 12000), Q(6121, 12000),
                          Q(3121, 6000)), "ordered band exponents")

    # HB trichotomy containment is parameter-independent but checked here.
    sigma = Q(1, 10) + S
    positive(margins, "HB.sigma", sigma - Q(1, 10))
    positive(margins, "HB.K10", 2 * sigma - Q(1, 10))
    positive(margins, "HB.central-lower", (Q(2, 5) - S) - (Q(2, 5) - H))
    positive(margins, "HB.III-lower", 2 * sigma - (Q(1, 5) - H))
    positive(margins, "HB.III-upper", (Q(2, 5) + H) - (Q(1, 2) - sigma))
    positive(margins, "HB.III-pair", (Q(1, 2) + sigma) - (Q(3, 5) - H))

    check_source_geometry(CROSS_W, "mixed", margins)
    check_source_geometry(OUTER_W, "outer", margins)
    check_source_geometry(Q(0), "outer-near", margins)
    positive(margins, "mixed.IIc-empty", (Q(2, 5) - H) - gb(CROSS_W))
    positive(margins, "outer-near.IIc-empty", (Q(2, 5) - H) - gb(Q(0)))
    check_iic_source(margins)

    fixed = {
        "mixed": check_fixed_family(inner, outer, CROSS_W, "mixed"),
        "transpose": check_fixed_family(outer, inner, CROSS_W, "transpose"),
        "outer": check_fixed_family(outer, outer, OUTER_W, "outer"),
        "outer_near": check_fixed_family(outer, outer, Q(0), "outer-near"),
    }
    dynamic = check_dynamic_outer(outer)

    # Proposition 1's non-distribution hypotheses for weighted primes.
    positive(margins, "Prop1.beta-inner-B1", Q(1, 2) - inner[0])
    positive(margins, "Prop1.beta-outer-B1", Q(1, 2) - outer[0])

    return {
        "status": "AUDIT PASS",
        "scope": "analytic Proposition-1 hypotheses only; no quotient",
        "checker_sha256": sha(FILE),
        "pinned": PINNED,
        "parameters": {"k": 48, "epsilon": str(EPSILON), "delta": str(DELTA),
                       "A": [str(-EPSILON), str(A1), str(A2)],
                       "inner_active": list(active(inner)),
                       "outer_active": list(active(outer)),
                       "iic_aux_width": str(IIIC_AUX),
                       "inward": str(R0), "source_zeta_max": str(ZETA)},
        "ordered_band_exponents": [str(value) for value in exponents],
        "range_assignment": {
            "inner_inner": "BV for all q in the class",
            "mixed_below_threshold": "bilinear BV",
            "mixed_above_threshold": "fixed omega=121/24000; IIc empty",
            "outer_below_sqrt_log": "bilinear BV",
            "outer_near_sqrt": "omega=0 IIa/IIb/III; IIc empty",
            "outer_above_sqrt": "fixed omega=121/12000 plus dynamic IIc omega0 in [0,omega]",
        },
        "fixed_prefix": fixed,
        "dynamic_iic": dynamic,
        "minimum_source_margin": str(min(margins.values())),
        "margins": {key: str(value) for key, value in margins.items()},
        "rho": "(log n/log(3x))*1_P on [x,2x], zero outside",
        "c1": "0", "c2": "0", "beta": "1/2",
        "remaining": "exact k=48 quotient above one and final theorem audit",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = (json.dumps(build(), sort_keys=True, separators=(",", ":")) + "\n").encode()
    if args.output:
        target = args.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    print(payload.decode(), end="")


if __name__ == "__main__":
    main()
