#!/usr/bin/env python3
"""Exact sufficient-lemma audit for the count-dependent C10 schedule.

This checker does not sample a support polytope.  For each feasible count
pair it verifies the closed-form prefix-subset criterion proved in
NONCONSTANT-SUPPORT-SEARCH.md, together with Definition 1.  Every analytic
capacity is reconstructed from the proof-safe inward-shrunk endpoints in
PROOF-DRAFT-C10.md Sections 6.4--7; in particular, the IIc capacities are the
literal C_1,C_2 of its equation (27), not the slightly different frontier
shorthand.
"""

from fractions import Fraction as Q


H = Q(1, 10**10)
ZETA_MAX = H / 1000
INWARD = H / 10
DELTA = Q(1, 100)
A = Q(77747, 300000)
OMEGA = A - Q(1, 4)
GAMMA3 = Q(2, 5) - H / 10

B = {
    1: Q(3, 20),
    2: Q(3, 20),
    3: Q(97, 625),
    4: Q(15837, 100000),
    5: Q(16183, 100000),
    6: Q(8193, 50000),
    7: Q(16623, 100000),
    8: Q(16797, 100000),
    9: Q(16877, 100000),
    10: Q(17013, 100000),
    11: Q(1069, 6250),
    12: Q(17179, 100000),
    13: Q(17241, 100000),
    14: Q(17293, 100000),
    15: Q(17337, 100000),
    16: Q(543, 3125),
    17: Q(17411, 100000),
    18: Q(3489, 20000),
}


def ceil_q(x: Q) -> int:
    return -((-x.numerator) // x.denominator)


def positive(name: str, value: Q) -> None:
    if value <= 0:
        raise AssertionError(f"{name}: {value}")


def bound(m: int) -> Q:
    if m == 0:
        return Q(0)
    return B[m] if m <= 18 else B[18]


def da(gamma: Q, omega: Q) -> Q:
    return Q(5, 7) * gamma - Q(2, 7) - Q(24, 7) * omega - H


def db(gamma: Q, omega: Q) -> Q:
    return Q(3, 7) * gamma - Q(1, 7) - Q(24, 7) * omega - H


def ga(omega: Q) -> Q:
    return Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * DELTA + 2 * H


def gb(omega: Q) -> Q:
    return Q(1, 3) + 8 * omega + Q(7, 3) * DELTA + 3 * H


def caps_iia(omega: Q) -> tuple[Q, Q]:
    """Uniform Lemma-11 capacities after the Section-6.4 shrink.

    The first capacity decreases with the source epsilon zeta, so its lower
    bound uses ZETA_MAX.  The second increases with zeta, so its uniform
    lower bound uses the limiting value zero, exactly as in the hostile
    analytic audit.
    """
    return (
        ga(omega) - 3 * ZETA_MAX - INWARD,
        da(Q(1, 2), omega) - INWARD,
    )


def caps_iib(omega: Q) -> tuple[Q, Q, Q]:
    """Uniform Lemma-12 capacities after the Section-6.4 shrink."""
    lo, hi = gb(omega), ga(omega)
    return (
        lo - 3 * ZETA_MAX - INWARD,
        Q(1, 2) - hi - 2 * omega - 6 * ZETA_MAX - INWARD,
        2 * omega + db(lo, omega),
    )


def caps_iii(omega: Q) -> tuple[Q, Q]:
    delta3 = Q(1, 2) - Q(7, 2) * omega - Q(9, 8) * GAMMA3 - H
    return (
        Q(1, 3) + Q(4, 3) * delta3 - Q(4, 3) * omega - H,
        Q(1, 6) - delta3 / 3 + Q(4, 3) * omega - H,
    )


def prefix_margin(tag: str, m: int, mp: int, c: Q, d: Q):
    """Return D minus the uniform prefix upper bound, or None if empty works."""
    n = m + mp
    s = bound(m) + bound(mp)
    if s <= c:
        return None
    ell = s - c
    choices = []
    # One may take the crossing prefix from all entries or from either group.
    # For a group to work uniformly, its mandatory mass n_g*delta must reach
    # the worst-case overload ell.
    for label, ng, sg in (("combined", n, s),
                          ("left", m, bound(m)),
                          ("right", mp, bound(mp))):
        if ng == 0 or ng * DELTA < ell:
            continue
        r = ceil_q(ell / DELTA)
        if not 1 <= r <= ng:
            continue
        if sg < ng * DELTA:
            raise AssertionError(f"infeasible active {label} {m},{mp}")
        q = ng - r + 1
        if r == 1:
            # The preceding prefix is exactly empty, not merely < ell.
            upper = sg / ng
            linear_margin = ng * d - sg
            q = ng
        else:
            # If j is the first crossing index, U_{j-1}<ell and the remaining
            # ng-j+1 entries are each at least y_j.  The resulting bound is
            # increasing in j, so j<=r is controlled at j=r.
            upper = ell + (sg - ell) / q
            linear_margin = q * (d - ell) - sg + ell
        if linear_margin != q * (d - upper):
            raise AssertionError(f"{tag} linear identity {label} {m},{mp}")
        choices.append((upper, label, r, linear_margin))
    if not choices:
        raise AssertionError(f"{tag} no prefix choice {m},{mp}")
    upper, label, r, linear_margin = min(choices)
    positive(f"{tag} prefix {m},{mp} via {label}", d - upper)
    positive(f"{tag} linear {m},{mp} via {label}", linear_margin)
    return d - upper


def main() -> None:
    for m in range(1, 100):
        bm, bp = bound(m), bound(m + 1)
        positive(f"B{m}-delta", bm - DELTA)
        if not bm <= bp <= bm + DELTA:
            raise AssertionError(f"Definition 1 transition {m}->{m+1}")

    active = [m for m in range(1, 101) if m * DELTA <= bound(m)]
    if active != list(range(1, 18)):
        raise AssertionError(f"active counts {active}")
    positive("first empty count 18", 18 * DELTA - bound(18))

    cap_pairs = {
        "IIa omega": caps_iia(OMEGA),
        "IIa zero": caps_iia(Q(0)),
        "IIb omega": caps_iib(OMEGA)[:2],
        "IIb zero": caps_iib(Q(0))[:2],
        "III omega": caps_iii(OMEGA),
        "III zero": caps_iii(Q(0)),
    }
    expected_cap_pairs = {
        "IIa omega": (Q(4579520001897, 10000000000000),
                        Q(28023999923, 700000000000)),
        "IIa zero": (Q(4140000001897, 10000000000000),
                       Q(49999999923, 700000000000)),
        "IIb omega": (Q(4299200002897, 10000000000000),
                        Q(356019996841, 15000000000000)),
        "IIb zero": (Q(10700000008691, 30000000000000),
                       Q(429999998947, 5000000000000)),
        "III omega": (Q(207035999869, 600000000000),
                        Q(138313333277, 800000000000)),
        "III zero": (Q(239999999869, 600000000000),
                       Q(359999999831, 2400000000000)),
    }
    if cap_pairs != expected_cap_pairs:
        raise AssertionError(f"inward capacity mismatch: {cap_pairs}")
    if caps_iib(OMEGA)[2] != Q(2972900003, 105000000000):
        raise AssertionError("IIb omega third-capacity mismatch")
    if caps_iib(Q(0))[2] != Q(350000001, 35000000000):
        raise AssertionError("IIb zero third-capacity mismatch")
    positive("IIb omega unused third capacity", caps_iib(OMEGA)[2])
    positive("IIb zero unused third capacity", caps_iib(Q(0))[2])
    max_pair_load = 2 * bound(17)
    all_first = {name: c - max_pair_load for name, (c, _) in cap_pairs.items()}

    # Literal inward-shrunk capacities in PROOF-DRAFT-C10.md equation (27).
    c = Q(4601199986563, 15000000000000)
    d = Q(776499995341, 15000000000000)
    positive("IIc C", c)
    positive("IIc D", d)
    all_cap_pairs = dict(cap_pairs)
    all_cap_pairs["IIc uniform"] = (c, d)
    worst_by_type = {}
    for tag, (cap1, cap2) in all_cap_pairs.items():
        margins = []
        for m in [0] + active:
            for mp in range(m, 18):
                if m + mp == 0:
                    continue
                margin = prefix_margin(tag, m, mp, cap1, cap2)
                if margin is not None:
                    margins.append((margin, m, mp))
        worst_by_type[tag] = min(margins) if margins else None

    original = {1: Q(3, 20), 2: Q(3, 20)}
    for m in range(3, 101):
        original[m] = Q(97, 625)
    for m in range(1, 101):
        if bound(m) < original[m]:
            raise AssertionError(f"not an inclusion at count {m}")
    if not all(bound(m) > original[m] for m in range(4, 18)):
        raise AssertionError("expected strict enlargement at counts 4..17")

    print("C10 NONCONSTANT SCHEDULE EXACT PREFIX PASS")
    print("active_counts=1..17 first_empty=18")
    for name, caps in cap_pairs.items():
        print(f"{name}_capacities={caps[0]},{caps[1]}")
    print(f"IIb omega_unused_third={caps_iib(OMEGA)[2]}")
    print(f"IIb zero_unused_third={caps_iib(Q(0))[2]}")
    print(f"IIc uniform_capacities={c},{d}")
    for name, worst in worst_by_type.items():
        if worst is None:
            print(f"{name}_prefix=empty_subset_always")
        else:
            print(f"{name}_worst_prefix_margin={worst[0]} pair={worst[1]},{worst[2]}")
    print(f"max_pair_load={max_pair_load}")
    for name, margin in all_first.items():
        print(f"{name}_all_first_margin={margin}")


if __name__ == "__main__":
    main()
