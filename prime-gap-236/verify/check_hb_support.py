#!/usr/bin/env python3
"""Exact scalar/partition checker for the direct-HB candidate support.

This checks the specialized Type II/III conditions only.  It deliberately
does not claim the printed Proposition 3 (whose Type I and negative-omega
branches are not used), and it does not check a Rayleigh certificate.
"""

from fractions import Fraction as Q


A = Q(1279, 5000)
DELTA = Q(1, 50)
SUPPORT_EPSILON = Q(1, 200)
H = Q(1, 10**10)
XI2 = Q(2, 5)
XI3 = Q(2, 5)
OMEGA = A - Q(1, 4)
B_SMALL = Q(3, 20)
B_LARGE = Q(17, 100)
MAX_COUNT = 1 // DELTA


def bound(m: int) -> Q:
    if m == 0:
        return Q(0)
    return B_SMALL if m <= 2 else B_LARGE


def main() -> None:
    # Definition 1.
    assert -SUPPORT_EPSILON < A < Q(1, 2) - SUPPORT_EPSILON
    assert DELTA < B_SMALL <= B_LARGE <= B_SMALL + DELTA
    assert MAX_COUNT == 50

    # Specialized Proposition-3 scalar conditions: Type II and Type III.
    ii_first = Q(19, 2) - 36 * A - 13 * DELTA + 100 * H
    ii_second_a = XI2 / 10 - 32 * A / 10 + Q(8, 10) - 2 * H
    ii_second_b = XI2 / 4 + Q(11, 16) - 3 * A - 2 * H
    iii = Q(11, 8) - Q(7, 2) * A - Q(9, 8) * XI3 - 2 * H
    assert ii_first >= 0
    assert min(ii_second_a, ii_second_b) >= DELTA
    assert iii > DELTA

    # Type IIa, IIb, and corrected Type III: all entries fit in bin 1.
    total = 2 * B_LARGE
    iia_1 = Q(2, 5) + 24 * OMEGA / 5 + 7 * DELTA / 5 - 2 * H
    iia_2 = Q(1, 14) - 24 * OMEGA / 7 - 2 * H
    iib_1 = Q(1, 3) + 8 * OMEGA + 7 * DELTA / 3 - 4 * H
    iib_2 = Q(1, 10) - 34 * OMEGA / 5 - 7 * DELTA / 5 - 4 * H
    iib_3 = Q(1, 35) + 22 * OMEGA / 35 + 21 * DELTA / 35 - 4 * H
    # This is the conservative capacity after restoring the lost Type-III h.
    iii_1 = 1 - 6 * OMEGA - Q(3, 2) * XI3 - Q(8, 3) * H
    iii_2 = 5 * OMEGA / 2 + 3 * XI3 / 8 - 2 * H
    assert total < iia_1 and iia_2 > 0
    assert total < iib_1 and iib_2 > 0 and iib_3 > 0
    assert total < iii_1 and iii_2 > 0

    # Uniform Type-IIc two-bin reduction for 0<=omega_0<=OMEGA.
    gamma_max = Q(1, 3) + 8 * OMEGA + 7 * DELTA / 3 + 3 * H
    c1 = XI2 - H - 2 * DELTA - 8 * OMEGA - H
    c2 = Q(1, 2) - gamma_max - 2 * OMEGA - H
    assert c1 > 0 and c2 > 0

    checked = empty = 0
    for m in range(MAX_COUNT + 1):
        for mp in range(MAX_COUNT + 1):
            if m * DELTA > bound(m) or mp * DELTA > bound(mp):
                empty += 1
                continue
            checked += 1
            if m == 0 or mp == 0:
                assert bound(m) + bound(mp) < c1
            elif m <= 2 and mp <= 2:
                assert bound(m) + bound(mp) < c1
            elif m <= 2 or mp <= 2:
                # Move the least entry of the block of cardinality >=3.
                overload = bound(m) + bound(mp) - c1
                assert overload < DELTA
                assert DELTA <= B_LARGE / 3 < c2
            else:
                # Try either least entry; if both are below the overload,
                # their pair lies between the overload and bin-2 capacity.
                overload = 2 * B_LARGE - c1
                assert overload < 2 * DELTA
                assert 2 * DELTA > overload
                assert 2 * overload < c2
                assert B_LARGE / 3 < c2

    print(f"A={A} support_epsilon={SUPPORT_EPSILON} delta={DELTA}")
    print(f"omega={OMEGA} B1=B2={B_SMALL} B3plus={B_LARGE}")
    print(f"II scalar margins: {ii_first}, {ii_second_a-DELTA}, {ii_second_b-DELTA}")
    print(f"III scalar margin: {iii-DELTA}")
    print(f"IIc uniform capacities: C1={c1} C2={c2}")
    print(f"count pairs checked={checked} empty={empty}")
    print("DIRECT-HB TYPE-II/III SUPPORT CHECK PASS")


if __name__ == "__main__":
    main()
