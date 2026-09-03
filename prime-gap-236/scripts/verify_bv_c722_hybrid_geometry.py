#!/usr/bin/env python3
"""Exact geometry checker for a wide BV-core/C722-outer two-band support.

The first band is the complete direct Bombieri--Vinogradov simplex used by
the exact D16 certificate.  The second band extends the total-sum endpoint to
the C722 direct-Heath--Brown frontier but suppresses low-count shell points by
using a ramped cap schedule.  This file proves only the rational support and
factorization geometry.  It does not certify a sieve quotient or independently
reprove the cited distribution estimates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from fractions import Fraction as Q
from pathlib import Path


FILE = Path(__file__).resolve()
REPO = FILE.parents[1]

H = Q(1, 10**10)
ZETA = H / 1000
INWARD = H / 10
K = 48
DELTA = Q(361, 50000)
EPSILON = Q(3, 400)
A0 = -EPSILON
A1 = Q(1, 4)
A2 = Q(3121, 12000)
ALPHA1 = A1 + EPSILON
ETA1 = A1 - EPSILON
ALPHA2 = A2 + EPSILON
ETA2 = A2 - EPSILON

# A first empty count is included; Definition 1 extends each final value
# constantly through floor(1/delta).
INNER_HEAD = (ALPHA1,) * 36
HIGH_PLATEAU_HEAD = tuple(
    min(Q(11, 200) + (m - 1) * DELTA, Q(43, 250))
    for m in range(1, 25)
)
VOLUME_RAMP_HEAD = tuple(
    min(Q(49, 625) + (m - 1) * DELTA, Q(1599, 10000))
    for m in range(1, 24)
)
OUTER_PRESETS = {
    "high-plateau": (HIGH_PLATEAU_HEAD, 23),
    "volume-ramp": (VOLUME_RAMP_HEAD, 22),
}

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
    "agents/structural-basis/NONCONSTANT-SUPPORT-SEARCH.md":
        "3823ee1efe8618c42c88a6b297b3e8c5689fbc80699f40ac48ac147f8970ccc3",
    "agents/structural-basis/PROP1-C2ZERO-AUDIT.md":
        "050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def positive(name: str, value: Q) -> Q:
    if value <= 0:
        raise AssertionError(f"{name} is not positive: {value}")
    return value


def ceil_fraction(value: Q) -> int:
    return -((-value.numerator) // value.denominator)


def extend(head: tuple[Q, ...]) -> tuple[Q, ...]:
    count = int(1 // DELTA)
    if len(head) > count:
        raise AssertionError("schedule head exceeds Definition-1 length")
    return head + (head[-1],) * (count - len(head))


def active(head: tuple[Q, ...]) -> tuple[int, ...]:
    return (0,) + tuple(
        m for m, bound in enumerate(head, 1) if m * DELTA <= bound
    )


def bound(head: tuple[Q, ...], m: int) -> Q:
    if m == 0:
        return Q(0)
    return head[m - 1] if m <= len(head) else head[-1]


def check_schedule(name: str, head: tuple[Q, ...], expected_last: int) -> None:
    schedule = extend(head)
    for index, value in enumerate(schedule):
        positive(f"{name} B{index + 1}-delta", value - DELTA)
        if index and not schedule[index - 1] <= value <= \
                schedule[index - 1] + DELTA:
            raise AssertionError(f"{name} transition {index}->{index + 1}")
    observed = active(head)
    if observed != tuple(range(expected_last + 1)):
        raise AssertionError(f"{name} active counts changed: {observed}")
    positive(f"{name} first-empty", (expected_last + 1) * DELTA -
             bound(head, expected_last + 1))


def fixed_capacities(omega: Q) -> dict[str, tuple[Q, ...]]:
    sigma = Q(1, 10) + H / 10
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    delta_c = DELTA + 4 * H
    gamma_min = Q(2, 5) - H
    gamma_max = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    answer = {
        "IIa": (
            Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA - 2 * H,
            Q(1, 14) - Q(24, 7) * omega - 2 * H,
        ),
        "IIb": (
            Q(1, 3) + 8 * omega + Q(7, 3) * DELTA - 4 * H,
            Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * DELTA - 4 * H,
            # Uniform lower capacity at the varying gamma endpoint.  This is
            # below the repaired source capacity by 2H/7 and replaces the
            # nonuniform upper-end expression in the printed calculation.
            DELTA + 2 * omega,
        ),
        "III": (
            Q(1, 3) + Q(4, 3) * delta3 - Q(4, 3) * omega - H,
            Q(1, 6) - delta3 / 3 + Q(4, 3) * omega - H,
        ),
        "IIc": (
            gamma_min - 2 * delta_c - 8 * omega - 58 * ZETA + INWARD,
            Q(1, 2) - gamma_max - 2 * omega - 6 * ZETA - INWARD,
            delta_c,
            2 * INWARD,
        ),
    }
    for tag, values in answer.items():
        for index, value in enumerate(values):
            positive(f"{tag} fixed capacity {index + 1}", value)
    return answer


def dynamic_iic_capacities(
        gamma_lo: Q, gamma_hi: Q, omega_lo: Q, omega_hi: Q
) -> tuple[Q, Q, Q, Q]:
    # Each endpoint is chosen in the adverse monotone direction over the cell.
    answer = (
        gamma_lo - 2 * DELTA - 8 * omega_hi - H,
        Q(1, 2) - gamma_hi - 2 * omega_hi - H,
        4 * omega_lo + DELTA - H,
        8 * omega_lo,
    )
    if min(answer) < 0:
        raise AssertionError(f"negative dynamic IIc capacity: {answer}")
    return answer


def prefix_certificate(
        groups: tuple[tuple[int, Q], ...], capacities: tuple[Q, ...]
) -> tuple[Q, str, int] | None:
    """Apply the proved minimal-prefix sufficient certificate exactly.

    The first bin receives the complement.  A prefix from the combined pool,
    the left pool, or the right pool is placed into one of the remaining bins.
    The returned margin is strict.
    """
    total_count = sum(count for count, _ in groups)
    total_bound = sum(cap for _, cap in groups)
    if total_bound <= capacities[0]:
        return capacities[0] - total_bound, "empty", 0
    overload = total_bound - capacities[0]
    choices: list[tuple[Q, str, int]] = []
    pools = tuple((f"side{index}", count, cap)
                  for index, (count, cap) in enumerate(groups)) + (
        ("combined", total_count, total_bound),
    )
    for label, count, cap in pools:
        if count == 0 or count * DELTA < overload or cap < count * DELTA:
            continue
        r = ceil_fraction(overload / DELTA)
        if not 1 <= r <= count:
            continue
        q = count - r + 1
        coordinate_upper = (cap / count if r == 1 else
                            overload + (cap - overload) / q)
        for capacity in capacities[1:]:
            if coordinate_upper < capacity:
                choices.append((capacity - coordinate_upper, label, r))
    return max(choices) if choices else None


def check_fixed_pair_family(
        left: tuple[Q, ...], right: tuple[Q, ...], omega: Q, name: str,
        tags: tuple[str, ...] | None = None,
) -> dict[str, object]:
    worst: tuple[Q, str, int, int, str, int] | None = None
    pairs = 0
    branches = 0
    capacities = fixed_capacities(omega)
    for m in active(left):
        for mp in active(right):
            if m + mp == 0:
                continue
            groups = ((m, bound(left, m)), (mp, bound(right, mp)))
            for tag, caps in capacities.items():
                if tags is not None and tag not in tags:
                    continue
                certificate = prefix_certificate(groups, caps)
                if certificate is None or certificate[0] <= 0:
                    raise AssertionError(
                        f"{name} {tag} pair {m},{mp} lacks certificate")
                item = (certificate[0], tag, m, mp,
                        certificate[1], certificate[2])
                worst = item if worst is None or item < worst else worst
                branches += 1
            pairs += 1
    if worst is None:
        raise AssertionError(f"{name} checked no fixed pairs")
    return {
        "pairs": pairs,
        "branch_checks": branches,
        "worst_margin": str(worst[0]),
        "worst": [worst[1], worst[2], worst[3], worst[4], worst[5]],
    }


def check_dynamic_pair_family(
        left: tuple[Q, ...], right: tuple[Q, ...], omega: Q, name: str,
    cells: int = 16,
) -> dict[str, object]:
    gamma_lo = Q(2, 5) - H
    gamma_hi = Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H
    if gamma_hi < gamma_lo:
        return {
            "pairs": 0,
            "cells_per_pair": 0,
            "checks": 0,
            "worst_margin": None,
            "worst": None,
            "empty_gamma_interval": True,
        }
    positive(f"{name} dynamic gamma width", gamma_hi - gamma_lo)
    worst: tuple[Q, int, int, int, int, str, int] | None = None
    checks = 0
    pairs = 0
    for m in active(left):
        for mp in active(right):
            if m + mp == 0:
                continue
            groups = ((m, bound(left, m)), (mp, bound(right, mp)))
            for io in range(cells):
                omega_lo = omega * io / cells
                omega_hi = omega * (io + 1) / cells
                for ig in range(cells):
                    gl = gamma_lo + (gamma_hi - gamma_lo) * ig / cells
                    gu = gamma_lo + (gamma_hi - gamma_lo) * (ig + 1) / cells
                    caps = dynamic_iic_capacities(gl, gu, omega_lo, omega_hi)
                    certificate = prefix_certificate(groups, caps)
                    if certificate is None or certificate[0] <= 0:
                        raise AssertionError(
                            f"{name} dynamic pair {m},{mp} cell {io},{ig} "
                            "lacks certificate")
                    item = (certificate[0], m, mp, io, ig,
                            certificate[1], certificate[2])
                    worst = item if worst is None or item < worst else worst
                    checks += 1
            pairs += 1
    if worst is None:
        raise AssertionError(f"{name} checked no dynamic cells")
    return {
        "pairs": pairs,
        "cells_per_pair": cells * cells,
        "checks": checks,
        "worst_margin": str(worst[0]),
        "worst": list(worst[1:]),
        "empty_gamma_interval": False,
    }


def direct_hb_scalar_margins(omega: Q) -> dict[str, str]:
    average_a = Q(1, 4) + omega
    sigma = Q(1, 10) + H / 10
    gamma3 = Q(1, 2) - sigma
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * gamma3 - H
    raw = {
        "Type0 sharp interval": 1 - ((Q(1, 2) - sigma) + 2 * average_a),
        "Type0 full Poisson": 1 - (1 - 2 * sigma + 4 * omega),
        "prime square": 1 - 2 * average_a,
        "higher prime powers": 1 - (2 * average_a + Q(1, 3)),
        "near-sqrt IIc gap": ((Q(1, 2) - sigma) -
                              (Q(1, 3) + Q(7, 3) * DELTA + 3 * H)),
        "TypeII scalar 19/2": (Q(19, 2) - 36 * average_a -
                               13 * DELTA + 100 * H),
        "TypeII scalar first": (Q(21, 25) - Q(16, 5) * average_a -
                                 2 * H - DELTA),
        "TypeII scalar second": (Q(63, 80) - 3 * average_a -
                                  2 * H - DELTA),
        "TypeIII width": delta3 - DELTA,
        "TypeIII distribution": 4 - (28 * omega + 9 * gamma3 + 8 * delta3),
    }
    return {name: str(positive(name, value)) for name, value in raw.items()}


def build_result(schedule_id: str = "volume-ramp") -> dict[str, object]:
    outer_head, expected_outer_last = OUTER_PRESETS[schedule_id]
    for relative, expected in PINNED_ANALYTIC.items():
        observed = sha256(REPO / relative)
        if observed != expected:
            raise RuntimeError(f"pinned dependency changed: {relative}")

    positive("epsilon", EPSILON)
    positive("delta", DELTA)
    positive("A1-A0", A1 - A0)
    positive("A2-A1", A2 - A1)
    positive("Definition1 upper", Q(1, 2) - EPSILON - A2)
    check_schedule("inner", INNER_HEAD, 35)
    check_schedule("outer", outer_head, expected_outer_last)

    exponents = {
        "inner_inner": ETA1 + ALPHA1,
        "inner_outer": ETA1 + ALPHA2,
        "outer_inner": ETA2 + ALPHA1,
        "outer_outer": ETA2 + ALPHA2,
    }
    expected_exponents = {
        "inner_inner": Q(1, 2),
        "inner_outer": A1 + A2,
        "outer_inner": A1 + A2,
        "outer_outer": 2 * A2,
    }
    if exponents != expected_exponents:
        raise ArithmeticError("band-pair epsilon cancellation changed")
    cross_omega = (exponents["inner_outer"] - Q(1, 2)) / 2
    outer_omega = (exponents["outer_outer"] - Q(1, 2)) / 2
    if (cross_omega, outer_omega) != (Q(121, 24000), Q(121, 12000)):
        raise ArithmeticError("hybrid omegas changed")

    fixed = {
        "cross": check_fixed_pair_family(
            INNER_HEAD, outer_head, cross_omega, "cross"),
        "transpose": check_fixed_pair_family(
            outer_head, INNER_HEAD, cross_omega, "transpose"),
        "outer": check_fixed_pair_family(
            outer_head, outer_head, outer_omega, "outer"),
        # Mixed moduli use cross_omega throughout.  Only the outer/outer
        # near-square-root range uses omega=0; IIc is empty there, while these
        # three fixed branches give the required finite cover.
        "outer_near": check_fixed_pair_family(
            outer_head, outer_head, Q(0), "outer-near",
            ("IIa", "IIb", "III")),
    }
    dynamic = {
        "cross": check_dynamic_pair_family(
            INNER_HEAD, outer_head, cross_omega, "cross"),
        "transpose": check_dynamic_pair_family(
            outer_head, INNER_HEAD, cross_omega, "transpose"),
        "outer": check_dynamic_pair_family(
            outer_head, outer_head, outer_omega, "outer"),
    }
    expected_dynamic_outer = (len(active(outer_head)) ** 2 - 1) * 16 ** 2
    if [dynamic[key]["checks"] for key in
            ("cross", "transpose", "outer")] != [0, 0,
                                                   expected_dynamic_outer]:
        raise ArithmeticError("dynamic coverage count changed")

    return {
        "status": "bv-c722-wide-two-band-exact-geometry-pass",
        "scope": (
            "exact Definition-1 support, fixed IIa/IIb/IIc/III prefix "
            "certificates, dynamic repaired-IIc cell certificates, and "
            "direct-HB scalar margins; cited analytic theorems are pinned "
            "but not independently reproved here"
        ),
        "script_sha256": sha256(FILE),
        "pinned_analytic_dependencies": PINNED_ANALYTIC,
        "parameters": {
            "k": K, "epsilon": str(EPSILON), "delta": str(DELTA),
            "outer_schedule_id": schedule_id,
            "A": [str(A0), str(A1), str(A2)],
            "alpha": [str(ALPHA1), str(ALPHA2)],
            "eta": [str(ETA1), str(ETA2)],
            "inner_schedule_through_first_empty": [str(x) for x in INNER_HEAD],
            "outer_schedule_through_first_empty": [str(x) for x in outer_head],
            "active_inner": list(active(INNER_HEAD)),
            "active_outer": list(active(outer_head)),
            "pair_exponents": {key: str(value) for key, value in exponents.items()},
            "cross_omega": str(cross_omega),
            "outer_omega": str(outer_omega),
        },
        "bv_core_embedding": {
            "radius": str(ALPHA1),
            "marginal_cutoff": str(ETA1),
            "all_inner_caps": str(ALPHA1),
            "matches_existing_D16_BV_support": True,
        },
        "fixed_prefix_checks": fixed,
        "dynamic_iic_checks": dynamic,
        "direct_hb_scalar_margins": {
            "mixed": direct_hb_scalar_margins(cross_omega),
            "outer": direct_hb_scalar_margins(outer_omega),
        },
        "distribution_range_assignment": {
            "inner_inner": "classical Bombieri-Vinogradov",
            "mixed_all_above_BV_cutoff": "fixed cross_omega direct-HB",
            "outer_near_sqrt": "omega=0 fixed IIa/IIb/III; IIc empty",
            "outer_above_sqrt": (
                "fixed outer_omega IIa/IIb/III plus dynamic "
                "omega_0 in [0,outer_omega] repaired IIc"),
        },
        "minorant_intended": "(log n/log(3x))*1_P on [x,2x]",
        "c1_intended": "0",
        "c2_intended": "0",
        "rigorous_geometry": True,
        "theorem_ready": False,
        "missing": [
            "independent source-level analytic audit of the hybrid transfer",
            "finite-dimensional k=48 quotient strictly above one",
            "independent final certificate reconstruction and proof audit",
        ],
    }


def publish_new(path: Path, payload: bytes) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outer-schedule", choices=tuple(OUTER_PRESETS),
                        default="volume-ramp")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_result(args.outer_schedule)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
               "\n").encode("ascii")
    if args.output is not None:
        publish_new(args.output, payload)
    print(payload.decode("ascii"), end="")


if __name__ == "__main__":
    main()
