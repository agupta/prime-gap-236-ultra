#!/usr/bin/env python3
"""Fail-closed exact verifier for the hard-coded C722 cap schedule.

No optimizer or discovery module is imported.  The verifier reconstructs all
seven inward-shrunk capacity pairs and checks the minimal-prefix lemma for
every feasible count pair using Fraction arithmetic.
"""

from fractions import Fraction as F
import hashlib


H = F(1, 10**10)
ZETA = H / 1000
INWARD = H / 10
DELTA = F(361, 50000)
A = F(3121, 12000)
OMEGA = A - F(1, 4)
BASE = F(7343, 50000)
DC = DELTA + 4 * H
GAMMA3 = F(2, 5) - H / 10

SCHEDULE = [
    F(7393, 50000), F(7443, 50000), F(7493, 50000), F(7543, 50000),
    F(7593, 50000), F(7643, 50000), F(7693, 50000), F(7743, 50000),
    F(7793, 50000), F(7843, 50000), F(7893, 50000), F(7943, 50000),
    F(7993, 50000), F(8043, 50000), F(8093, 50000), F(8143, 50000),
    F(8193, 50000), F(8243, 50000), F(8293, 50000), F(2087, 12500),
    F(8403, 50000), F(4229, 25000), F(17127, 100000), F(8669, 50000),
    F(18049, 100000), F(18771, 100000), F(19493, 100000), F(4043, 20000),
]


def positive(name: str, value: F) -> None:
    if value <= 0:
        raise AssertionError(f"{name}: expected positive, got {value}")


def ceil_fraction(value: F) -> int:
    return -((-value.numerator) // value.denominator)


def bound(m: int) -> F:
    if m == 0:
        return F(0)
    return SCHEDULE[m - 1] if m <= len(SCHEDULE) else SCHEDULE[-1]


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


CAPACITY_PAIRS = {
    "IIa-near": iia(F(0)),
    "IIa-above": iia(OMEGA),
    "IIb-near": iib(F(0)),
    "IIb-above": iib(OMEGA),
    "III-near": iii(F(0)),
    "III-above": iii(OMEGA),
    "IIc": (
        F(2, 5) - H - 2 * DC - 8 * OMEGA - 58 * ZETA + INWARD,
        F(1, 2) - gb(OMEGA) - 2 * OMEGA - 6 * ZETA - INWARD,
    ),
}


def prefix_options(m: int, mp: int, c: F, d: F):
    total = bound(m) + bound(mp)
    if total <= c:
        return [(c - total, "empty", 0)]
    overload = total - c
    choices = []
    for label, count, cap in (
        ("combined", m + mp, total),
        ("left", m, bound(m)),
        ("right", mp, bound(mp)),
    ):
        if count == 0 or count * DELTA < overload:
            continue
        r = ceil_fraction(overload / DELTA)
        if not 1 <= r <= count:
            continue
        if cap < count * DELTA:
            raise AssertionError(f"infeasible active pool {label} {m},{mp}")
        q = count - r + 1
        if r == 1:
            upper = cap / count
        else:
            upper = overload + (cap - overload) / q
        if upper < d:
            choices.append((d - upper, label, r))
    return choices


def main() -> None:
    if A != F(21, 80) - DELTA / 3 - F(1, 100000):
        raise AssertionError("frontier A identity")
    if BASE != F(1, 8) + 3 * DELTA + F(1, 5000):
        raise AssertionError("frontier B identity")

    max_count = DELTA.denominator // DELTA.numerator
    for m in range(1, max_count):
        bm, bp = bound(m), bound(m + 1)
        positive(f"B{m}-delta", bm - DELTA)
        if not bm <= bp <= bm + DELTA:
            raise AssertionError(f"Definition 1 transition {m}->{m + 1}: {bm},{bp}")
    if not all(bound(m) > BASE for m in range(1, max_count + 1)):
        raise AssertionError("not a strict coordinatewise support enlargement")

    active = [m for m in range(max_count + 1) if m == 0 or m * DELTA <= bound(m)]
    if active != list(range(25)):
        raise AssertionError(f"active counts are not 0..24: {active}")
    positive("first empty count", 25 * DELTA - bound(25))

    # Capacities left empty by the two-bin certificate must be nonnegative.
    for tag, (c, d) in CAPACITY_PAIRS.items():
        positive(f"{tag} C", c)
        positive(f"{tag} D", d)
    positive("IIb near third", db(gb(F(0)), F(0)))
    positive("IIb above third", 2 * OMEGA + db(gb(OMEGA), OMEGA))
    positive("IIc third", DC)
    positive("IIc fourth", 2 * INWARD)

    worst = {}
    for tag, (c, d) in CAPACITY_PAIRS.items():
        checked = 0
        nonempty = []
        for m in active:
            for mp in active:
                options = prefix_options(m, mp, c, d)
                if not options:
                    raise AssertionError(f"{tag}: no certificate for ({m},{mp})")
                best = max(options)
                positive(f"{tag} ({m},{mp})", best[0])
                if best[1] != "empty":
                    nonempty.append((best[0], m, mp, best[1], best[2]))
                checked += 1
        if checked != 625:
            raise AssertionError(f"{tag}: checked {checked} pairs")
        worst[tag] = min(nonempty) if nonempty else None

    expected = (F(56499669613, 285000000000000), 24, 24, "right", 6)
    if worst["IIc"] != expected:
        raise AssertionError(f"unexpected IIc worst certificate: {worst['IIc']}")

    canonical = "\n".join(f"{x.numerator}/{x.denominator}" for x in SCHEDULE) + "\n"
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    print("C722 COUNT-SCHEDULE EXACT PREFIX AUDIT PASS")
    print("active_counts=0..24 first_empty=25 checked_pairs_per_branch=625")
    print(f"IIc_worst_margin={expected[0]} pair=24,24 method=right r=6")
    print(f"schedule_sha256={digest}")


if __name__ == "__main__":
    main()
