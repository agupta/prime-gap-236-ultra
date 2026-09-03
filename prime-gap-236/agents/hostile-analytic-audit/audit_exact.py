#!/usr/bin/env python3
"""Independent rational checks used by AUDIT.md.

This does not certify any distribution theorem.  It checks only the exact
parameter arithmetic and the continuum inequalities in the 889/5000 support
argument, including capacities omitted from the candidate checker.
"""

from fractions import Fraction as F


def pos(label: str, value: F) -> None:
    if value <= 0:
        raise AssertionError(f"{label}: {value}")
    print(f"{label}\t{value}")


def main() -> None:
    h = F(1, 10**10)
    d = F(7, 250)
    w = F(3, 1000)
    xi1 = F(19, 50)
    xi3 = F(2, 5)
    b = F(889, 5000)

    # Unused bins in A, B, C, E must accommodate the empty set.
    unused = {
        "A2": F(1, 6) - 4 * w - 2 * h,
        "B2": F(1, 14) - F(24, 7) * w - 2 * h,
        "C2": F(1, 10) - F(34, 5) * w - F(7, 5) * d - 4 * h,
        "C3": F(1, 35) + F(22, 35) * w + F(21, 35) * d - 4 * h,
        "E2": F(5, 2) * w + F(3, 8) * xi3 - 2 * h,
        "high-Type-I-2": F(1, 14) - F(68, 14) * w - 2 * h,
    }
    for label, value in unused.items():
        pos(label, value)

    # The extra two-bin condition used only in the above-square-root
    # gamma > 1/2 Type-I branch is not one of Proposition 3's labelled
    # A--E hypotheses, so check both of its bins explicitly.
    high_type_i_first = F(1, 2) - 2 * w - 2 * h
    high_type_i_second = F(1, 14) - F(68, 14) * w - 2 * h
    pos("high-Type-I first-minus-total-889", high_type_i_first - 2 * b)
    pos("high-Type-I second", high_type_i_second)

    # Correct way to fit Definition-5 Type III into the Section-3 lemma.
    gamma3 = xi3 + h
    delta3 = F(1, 2) - F(7, 2) * w - F(9, 8) * xi3 - 2 * h
    pos("TypeIII delta3-support_delta", delta3 - d)
    pos("TypeIII strict-distribution-margin", 4 - (28 * w + 9 * gamma3 + 8 * delta3))
    type3_first = 1 - 6 * w - F(3, 2) * xi3 - F(8, 3) * h
    type3_second = F(5, 2) * w + F(3, 8) * xi3 + F(2, 3) * h
    pos("TypeIII first-minus-total-889", type3_first - 2 * b)
    pos("TypeIII second", type3_second)

    # The same correction works in the omega=0 near-square-root branch and
    # for the published (17/100) support.
    baseline_total = 2 * F(17, 100)
    delta3_zero = F(1, 2) - F(9, 8) * xi3 - 2 * h
    pos("TypeIII-zero delta3-support_delta", delta3_zero - d)
    pos(
        "TypeIII-zero strict-distribution-margin",
        4 - (9 * gamma3 + 8 * delta3_zero),
    )
    pos(
        "TypeIII-zero first-minus-baseline-total",
        1 - F(3, 2) * xi3 - F(8, 3) * h - baseline_total,
    )

    # The continuous two-bin proof for condition D.
    cap1 = F(8, 25) - 2 * h
    cap2 = F(107, 1500) - 4 * h
    # At (m,m')=(0,0), all four subset sums are zero.  These are the
    # uniform lower capacities on the repaired omega0 >= 0 rectangle.
    pos("D zero-case cap1", cap1)
    pos("D zero-case cap2", cap2)
    pos("D zero-case cap3", d - h)
    if 8 * 0 < 0:
        raise AssertionError("unreachable: zero fourth capacity")
    print("D zero-case cap4\t0 (nonnegative)")
    lmax = 2 * b - cap1
    pos("D least-entry-room", cap2 - b / 3)
    pos("D two-minima-reach-L", 2 * d - lmax)
    pos("D two-minima-fit-bin2", cap2 - 2 * lmax)

    print("HOSTILE EXACT ARITHMETIC PASS")


if __name__ == "__main__":
    main()
