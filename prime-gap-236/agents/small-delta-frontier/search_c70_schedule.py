#!/usr/bin/env python3
"""Exact grid search for a count-dependent C70 cap schedule.

The search criterion is the proved minimal-prefix crossing lemma.  It is a
sufficient condition, not a sampled polytope test.  Candidate schedules are
verified against the literal inward-shrunk IIa, IIb, repaired-IIc, and Type
III capacity pairs before they are printed.
"""

from __future__ import annotations

from fractions import Fraction as F
import sys


H = F(1, 10**10)
ZETA = H / 1000
INWARD = H / 10
POINT_ID = sys.argv[2] if len(sys.argv) >= 3 else "C70"
DELTA = F(sys.argv[1]) if len(sys.argv) >= 2 else F(7, 1000)
A = F(21, 80) - DELTA / 3 - F(1, 100000)
OMEGA = A - F(1, 4)
GAMMA3 = F(2, 5) - H / 10
BASE = F(1, 8) + 3 * DELTA + F(1, 5000)
DC = DELTA + 4 * H
N = 28


def ceil_fraction(x: F) -> int:
    return -((-x.numerator) // x.denominator)


def ga(w: F) -> F:
    return F(2, 5) + F(24, 5) * w + F(7, 5) * DELTA + 2 * H


def da(gamma: F, w: F) -> F:
    return F(5, 7) * gamma - F(2, 7) - F(24, 7) * w - H


def gb(w: F) -> F:
    return F(1, 3) + 8 * w + F(7, 3) * DELTA + 3 * H


def db(gamma: F, w: F) -> F:
    return F(3, 7) * gamma - F(1, 7) - F(24, 7) * w - H


def iia(w: F) -> tuple[F, F]:
    return ga(w) - 3 * ZETA - INWARD, da(F(1, 2), w) - INWARD


def iib(w: F) -> tuple[F, F]:
    return (
        gb(w) - 3 * ZETA - INWARD,
        F(1, 2) - ga(w) - 2 * w - 6 * ZETA - INWARD,
    )


def iii(w: F) -> tuple[F, F]:
    d3 = F(1, 2) - F(7, 2) * w - F(9, 8) * GAMMA3 - H
    return (
        F(1, 3) + F(4, 3) * d3 - F(4, 3) * w - H,
        F(1, 6) - d3 / 3 + F(4, 3) * w - H,
    )


def iic() -> tuple[F, F]:
    return (
        F(2, 5) - H - 2 * DC - 8 * OMEGA - 58 * ZETA + INWARD,
        F(1, 2) - gb(OMEGA) - 2 * OMEGA - 6 * ZETA - INWARD,
    )


CAPACITY_PAIRS = {
    "IIa-near": iia(F(0)),
    "IIa-above": iia(OMEGA),
    "IIb-near": iib(F(0)),
    "IIb-above": iib(OMEGA),
    "III-near": iii(F(0)),
    "III-above": iii(OMEGA),
    "IIc": iic(),
}


def bound(schedule: list[F], m: int) -> F:
    if m == 0:
        return F(0)
    return schedule[m - 1] if m <= len(schedule) else schedule[-1]


def prefix_certificate(
    schedule: list[F], m: int, mp: int, c: F, d: F
) -> tuple[F | None, str]:
    """Return a positive D-margin, or None when the empty subset works."""
    n = m + mp
    s = bound(schedule, m) + bound(schedule, mp)
    if s <= c:
        return None, "empty"
    overload = s - c
    choices: list[tuple[F, str]] = []
    for label, ng, sg in (
        ("combined", n, s),
        ("left", m, bound(schedule, m)),
        ("right", mp, bound(schedule, mp)),
    ):
        if ng == 0 or ng * DELTA < overload:
            continue
        r = ceil_fraction(overload / DELTA)
        if not 1 <= r <= ng:
            continue
        if sg < ng * DELTA:
            continue
        q = ng - r + 1
        if r == 1:
            upper = sg / ng
        else:
            upper = overload + (sg - overload) / q
        if upper < d:
            choices.append((d - upper, f"{label}:r={r}"))
    if not choices:
        return F(-1), "none"
    return max(choices)


def verify(schedule: list[F], verbose: bool = False, only_iic: bool = False):
    if len(schedule) != N:
        return False, ("length", len(schedule))
    if schedule[0] <= DELTA:
        return False, ("B1", schedule[0])
    for m in range(1, N):
        if not schedule[m - 1] <= schedule[m] <= schedule[m - 1] + DELTA:
            return False, ("transition", m, schedule[m - 1], schedule[m])

    max_count = DELTA.denominator // DELTA.numerator
    active = [m for m in range(max_count + 1) if m == 0 or m * DELTA <= bound(schedule, m)]
    if active != list(range(max(active) + 1)):
        return False, ("non-prefix active counts", active)
    worst = {}
    pairs = {"IIc": CAPACITY_PAIRS["IIc"]} if only_iic else CAPACITY_PAIRS
    for tag, (c, d) in pairs.items():
        current = None
        for m in active:
            for mp in active:
                margin, method = prefix_certificate(schedule, m, mp, c, d)
                if margin is not None and margin <= 0:
                    return False, (tag, m, mp, method)
                if margin is not None:
                    item = (margin, m, mp, method)
                    current = item if current is None or item < current else current
        worst[tag] = current
    if verbose:
        print("active", active)
        for tag, item in worst.items():
            print("worst", tag, item if item is not None else "empty-subset-always")
    return True, (active, worst)


def greedy(order: list[int]) -> list[F]:
    schedule = [BASE] * N
    for step in (F(1, 1000), F(1, 10000), F(1, 100000)):
        changed = True
        sweeps = 0
        while changed:
            changed = False
            sweeps += 1
            for start in order:
                proposal = schedule.copy()
                for index in range(start - 1, N):
                    proposal[index] += step
                ok, _ = verify(proposal, only_iic=True)
                if ok:
                    schedule = proposal
                    changed = True
            if sweeps > 1000:
                raise RuntimeError("greedy search did not terminate")
        print("step_sweeps", step, sweeps)
    return schedule


def main() -> None:
    # Repeated high-to-low suffix increments prioritize newly opened strata,
    # while retaining all lower-count caps.  A second low-to-high polishing
    # pass is deliberately omitted: it can trade away high-stratum room.
    schedule = greedy(list(range(N, 0, -1)))
    ok, details = verify(schedule, verbose=True)
    if not ok:
        raise AssertionError(details)
    if not all(value >= BASE for value in schedule):
        raise AssertionError("candidate is not a support inclusion")
    if not any(value > BASE for value in schedule):
        raise AssertionError("candidate did not enlarge the support")
    print("schedule")
    for m, value in enumerate(schedule, 1):
        print(m, value)
    print(f"{POINT_ID} COUNT-DEPENDENT PREFIX SEARCH PASS")


if __name__ == "__main__":
    main()
