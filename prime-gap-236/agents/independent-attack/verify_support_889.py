#!/usr/bin/env python3
"""Exact checker for support-889-proof.md (rational arithmetic only)."""

from fractions import Fraction as Q


def positive(name, x):
    if not x > 0:
        raise AssertionError(f"{name}: nonpositive margin {x}")
    print(name, x)


def main():
    h = Q(1, 10**10)
    delta = Q(7, 250)
    A = Q(253, 1000)
    xi1, xi2, xi3 = Q(19, 50), Q(2, 5), Q(2, 5)
    omega = Q(3, 1000)
    bsmall, blarge = Q(3, 20), Q(889, 5000)

    # Definition 1.
    assert A < Q(1, 2) - Q(3, 400)
    assert delta < bsmall <= bsmall <= bsmall + delta
    assert bsmall <= blarge <= bsmall + delta
    assert Q(1, 1) // delta == 35

    # Proposition 2.
    positive("P2.1", 2 - (2 * xi1 + 3 * xi2))
    assert xi2 <= xi3
    positive("P2.3", 4 - (xi1 + 9 * xi2))
    positive("P2.4", 2 * xi1 + xi2 - 1)
    positive("P2.5", 7 - 17 * xi2)
    positive("roughness", Q(1, 1) - 2 * xi2 - bsmall)

    # Proposition 3 scalar conditions.
    p3i_1 = xi1 - 4 * A + Q(2, 3)
    p3i_2 = Q(9, 7) - Q(34, 7) * A
    positive("P3.I", min(p3i_1, p3i_2) - 2 * h - delta)
    positive("P3.II.first", Q(19, 2) - 36 * A - 13 * delta + 100 * h)
    p3ii_1 = xi2 / 10 - Q(32, 10) * A + Q(8, 10)
    p3ii_2 = xi2 / 4 + Q(11, 16) - 3 * A
    positive("P3.II.second", min(p3ii_1, p3ii_2) - 2 * h - delta)
    positive("P3.III", Q(11, 8) - Q(7, 2) * A - Q(9, 8) * xi3 - 2 * h - delta)

    totalmax = 2 * blarge
    capA = xi1 - 2 * h
    capB = Q(2, 5) + Q(24, 5) * omega + Q(7, 5) * delta - 2 * h
    capC = Q(1, 3) + 8 * omega + Q(7, 3) * delta - 4 * h
    # Proof-safe Type-III cap after retaining gamma_3=xi_3+h and the full
    # delta_3 slack; this is 2h/3 smaller than the printed condition E cap.
    capE = 1 - 6 * omega - Q(3, 2) * xi3 - Q(8, 3) * h
    for name, cap in (("A", capA), ("B", capB), ("C", capC), ("E", capE)):
        positive(f"partition {name} all-in-I1", cap - totalmax)
    unused = {
        "A2": Q(1, 6) - 4 * omega - 2 * h,
        "B2": Q(1, 14) - Q(24, 7) * omega - 2 * h,
        "C2": Q(1, 10) - Q(34, 5) * omega - Q(7, 5) * delta - 4 * h,
        "C3": Q(1, 35) + Q(22, 35) * omega + Q(21, 35) * delta - 4 * h,
        "E2": Q(5, 2) * omega + Q(3, 8) * xi3 - 2 * h,
    }
    for name, cap in unused.items():
        positive(f"unused bin {name}", cap)

    # Uniform Type-IIc lower capacities on omega0 in [0,omega].
    C = Q(8, 25) - 2 * h
    D = Q(107, 1500) - 4 * h
    positive("D minimum C", C)
    positive("D minimum D", D)
    positive("D least-entry upper margin", D - blarge / 3)
    positive("D both-large lower margin", 2 * delta - (2 * blarge - C))
    positive("D both-large upper margin", D - 2 * (2 * blarge - C))

    bounds = {0: Q(0), 1: bsmall, 2: bsmall}
    bounds.update({m: blarge for m in range(3, 36)})
    checked, empty = 0, 0
    for m in range(36):
        for mp in range(36):
            if m + mp == 0:
                continue
            if m * delta > bounds[m] or mp * delta > bounds[mp]:
                empty += 1
                continue
            checked += 1
            total = bounds[m] + bounds[mp]
            if m == 0 or mp == 0 or (m <= 2 and mp <= 2):
                assert total < C
            elif m <= 2 or mp <= 2:
                assert total - C < delta
                large_count = mp if m <= 2 else m
                assert blarge / large_count <= blarge / 3 < D
            else:
                Lmax = total - C
                assert Lmax < 2 * delta
                assert 2 * Lmax < D
                assert blarge / m < D and blarge / mp < D
    print("nonempty count pairs checked", checked)
    print("empty count pairs skipped", empty)
    print("SUPPORT-889 EXACT CHECK PASS (for repaired omega0>=0 criterion)")


if __name__ == "__main__":
    main()
