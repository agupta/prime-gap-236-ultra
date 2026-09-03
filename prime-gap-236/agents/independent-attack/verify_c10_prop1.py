#!/usr/bin/env python3
"""Exact analytic checker for the C10 direct-Heath--Brown candidate.

This reconstructs the one-stratum support and every rational inequality used
in the companion candidate dossier.  It contains no floating-point input and
does not read a serialized matrix or partition witness.
"""

from fractions import Fraction as F


H = F(1, 10**10)
S = H / 10
K = 10
SIGMA = F(1, 10) + S
XI = F(2, 5)

EPS = F(1, 200)
DELTA = F(1, 100)
A = F(77747, 300000)
W = A - F(1, 4)
U = V = F(3, 20)
B = F(97, 625)


def pos(name: str, value: F) -> None:
    if value <= 0:
        raise AssertionError(f"{name} is not strictly positive: {value}")
    print(f"{name}\t{value}")


def nonneg(name: str, value: F) -> None:
    if value < 0:
        raise AssertionError(f"{name} is negative: {value}")
    print(f"{name}\t{value}")


def main() -> None:
    print("C10 PARAMETERS")
    print("epsilon", EPS)
    print("delta", DELTA)
    print("A0", -EPS)
    print("A1", A)
    print("omega", W)
    print("B1=B2", U)
    print("B3=...=B100", B)

    # Definition 1, including the entire finite schedule through floor(1/d).
    schedule = [U, V] + [B] * (DELTA.denominator - 2)
    assert len(schedule) == 100 == DELTA.denominator
    pos("Definition1 epsilon", EPS)
    pos("Definition1 A1-A0", A + EPS)
    pos("Definition1 1/2-epsilon-A1", F(1, 2) - EPS - A)
    for m, bm in enumerate(schedule, 1):
        pos(f"Definition1 B{m}-delta", bm - DELTA)
        if m > 1:
            nonneg(f"Definition1 B{m}-B{m-1}", bm - schedule[m - 2])
            nonneg(f"Definition1 B{m-1}+delta-B{m}", schedule[m - 2] + DELTA - bm)
    assert all(schedule[i - 1] <= schedule[i] <= schedule[i - 1] + DELTA for i in range(1, 100))
    assert 15 * DELTA <= B < 16 * DELTA
    print("first empty count\t16")

    # Heath--Brown K=10 trichotomy and containment of its actual terms in the
    # 2026 Type-II/III hypotheses.  The forbidden sigma=1/10 endpoint is not
    # used.
    pos("HB sigma-1/10", SIGMA - F(1, 10))
    pos("HB 2sigma-1/K", 2 * SIGMA - F(1, K))
    pos("HB TypeII lower containment", (F(1, 2) - SIGMA) - (XI - H))
    pos("HB TypeII upper containment", (1 - XI + H) - (F(1, 2) + SIGMA))
    pos("HB TypeIII lower containment", 2 * SIGMA - (1 - 2 * XI - H))
    pos("HB TypeIII upper containment", (XI + H) - (F(1, 2) - SIGMA))
    pos("HB TypeIII pair containment", (F(1, 2) + SIGMA) - (1 - XI - H))

    # All relevant moduli satisfy q <= x^(2A); epsilon cancels exactly.
    qexp = (A - EPS) + (A + EPS)
    assert qexp == 2 * A == F(1, 2) + 2 * W
    print("Q-star exponent upper bound\t", qexp)
    pos("Type0 sharp-interval power saving", 1 - ((F(1, 2) - SIGMA) + qexp))
    pos("Type0 full-Poisson power saving", 1 - (1 - 2 * SIGMA + 4 * W))
    pos("prime-square modulus exponent saving", 1 - qexp)
    pos("higher-prime-power saving", 1 - (qexp + F(1, 3)))

    # Specialized Type-II scalar faces.
    pos("TypeII scalar 19/2", F(19, 2) - 36 * A - 13 * DELTA + 100 * H)
    pos("TypeII scalar first min", F(21, 25) - F(16, 5) * A - 2 * H - DELTA)
    pos("TypeII scalar second min", F(63, 80) - 3 * A - 2 * H - DELTA)

    # The Type-IIc interval is empty in the near-square-root strip omega=0.
    gmin = XI - H
    gmax = F(1, 3) + 8 * W + F(7, 3) * DELTA + 3 * H
    pos(
        "omega=0 TypeIIc empty gap",
        (F(1, 2) - SIGMA) - (F(1, 3) + F(7, 3) * DELTA + 3 * H),
    )

    # IIa and IIb: put every coordinate in the first bin.  Repeat at omega=0
    # because that near-square-root branch has smaller first capacities.
    total = 2 * B
    for tag, omega in (("above", W), ("zero", F(0))):
        ca1 = F(2, 5) + F(24, 5) * omega + F(7, 5) * DELTA - 2 * H
        ca2 = F(1, 14) - F(24, 7) * omega - 2 * H
        cb1 = F(1, 3) + 8 * omega + F(7, 3) * DELTA - 4 * H
        cb2 = F(1, 10) - F(34, 5) * omega - F(7, 5) * DELTA - 4 * H
        cb3 = F(1, 35) + F(22, 35) * omega + F(3, 5) * DELTA - 4 * H
        pos(f"IIa-{tag} first minus 2B", ca1 - total)
        pos(f"IIa-{tag} unused second", ca2)
        pos(f"IIb-{tag} first minus 2B", cb1 - total)
        pos(f"IIb-{tag} unused second", cb2)
        pos(f"IIb-{tag} unused third", cb3)

    # Corrected Type III for the actual three-atom HB alternative.  Shrink
    # both open endpoints inward by h, hence the explicit 2h width loss.
    gamma3 = F(1, 2) - SIGMA
    for tag, omega in (("above", W), ("zero", F(0))):
        delta3 = F(1, 2) - F(7, 2) * omega - F(9, 8) * gamma3 - H
        pos(f"TypeIII-{tag} width after inward shrink", delta3 - 2 * H - DELTA)
        pos(
            f"TypeIII-{tag} distribution",
            4 - (28 * omega + 9 * gamma3 + 8 * delta3),
        )
        cap1 = F(1, 3) + F(4, 3) * delta3 - F(4, 3) * omega - H
        cap2 = F(1, 6) - delta3 / 3 + F(4, 3) * omega - H
        pos(f"TypeIII-{tag} first minus 2B", cap1 - total)
        pos(f"TypeIII-{tag} unused second", cap2)

    # Repaired IIc, uniformly for omega_0 in [0,W] and gamma in [gmin,gmax].
    C = gmin - 2 * DELTA - 8 * W - H
    D = F(1, 2) - gmax - 2 * W - H
    pos("IIc uniform first capacity C", C)
    pos("IIc uniform second capacity D", D)
    # Exact hypotheses of the zero/small/large-count two-bin lemma.
    pos("IIc zero-block b<C", C - B)
    pos("IIc both-small 2V<C", C - 2 * V)
    pos("IIc one-small overload<delta", DELTA - (V + B - C))
    pos("IIc least-large<D", D - B / 3)
    lmax = 2 * B - C
    pos("IIc two-large Lmax<2delta", 2 * DELTA - lmax)
    pos("IIc two-large 2Lmax<D", D - 2 * lmax)

    # Proposition 1 constants.  The non-arithmetic assertions are proved in
    # the companion dossier; these identities prevent a c1/c2 bookkeeping
    # mistake in the final quotient.
    c1 = c2 = F(0)
    beta = F(1, 2)
    assert beta > max(schedule[0], schedule[1])
    assert 1 - c1 == 1 and c2 == 0
    print("Proposition1 c1\t0")
    print("Proposition1 c2\t0")
    print("Proposition1 beta\t1/2")
    print("C10 PROP1 EXACT MARGINS PASS")


if __name__ == "__main__":
    main()
