#!/usr/bin/env python3
"""Independent exact checker for the simple direct-HB support frontier.

The Type-IIc proof uses a uniform two-bin least-element lemma.  Every value
is Fraction arithmetic; no serialized matrix or floating-point input is read.
"""

from fractions import Fraction as F


H = F(1, 10**10)
S = H / 10
EPS = F(1, 200)

CANDIDATES = {
    # Small-delta branch.  Here A=21/80-delta/3-1/100000 and
    # b=1/8+3delta+1/5000.  Once b<3/20, all B_m are lowered to b.
    "C60": (F(3, 500), F(26049, 100000), F(179, 1250), F(179, 1250), F(179, 1250)),
    "C65": (F(13, 2000), F(78097, 300000), F(1447, 10000), F(1447, 10000), F(1447, 10000)),
    "C662": (F(331, 50000), F(15617, 60000), F(7253, 50000), F(7253, 50000), F(7253, 50000)),
    "C70": (F(7, 1000), F(78047, 300000), F(731, 5000), F(731, 5000), F(731, 5000)),
    "C75": (F(3, 400), F(25999, 100000), F(1477, 10000), F(1477, 10000), F(1477, 10000)),
    "C80": (F(1, 125), F(77947, 300000), F(373, 2500), F(373, 2500), F(373, 2500)),
    "C85": (F(17, 2000), F(77897, 300000), F(3, 20), F(3, 20), F(1507, 10000)),
    "C90": (F(9, 1000), F(25949, 100000), F(3, 20), F(3, 20), F(761, 5000)),
    "C95": (F(19, 2000), F(77797, 300000), F(3, 20), F(3, 20), F(1537, 10000)),
    "C10": (F(1, 100), F(77747, 300000), F(3, 20), F(3, 20), F(97, 625)),
    "C12": (F(3, 250), F(25849, 100000), F(3, 20), F(3, 20), F(403, 2500)),
    "C14": (F(7, 500), F(77347, 300000), F(3, 20), F(383, 2500), F(209, 1250)),
    "C16": (F(2, 125), F(77147, 300000), F(3, 20), F(769, 5000), F(849, 5000)),
    "C20": (F(1, 50), F(1279, 5000), F(3, 20), F(19, 125), F(43, 250)),
    "C2005": (F(401, 20000), F(1279, 5000), F(3, 20), F(1521, 10000), F(1721, 10000)),
    "C24": (F(3, 125), F(25449, 100000), F(3, 20), F(188, 1250), F(109, 625)),
    "C28": (F(7, 250), F(75947, 300000), F(3, 20), F(3, 20), F(221, 1250)),
}


def pos(name, value):
    if value <= 0:
        raise AssertionError(f"{name}: {value}")
    print(name, value)


def check(name, d, A, b1, b2, b):
    print("CANDIDATE", name)
    w = A - F(1, 4)
    assert 0 < d < b1 <= b2 <= b
    assert b2 <= b1 + d and b <= b2 + d
    pos("Def1 A lower", w)
    pos("Def1 A upper", F(1, 2) - EPS - A)

    # Uniform margins in the K=10 Heath--Brown classification.  A Type-0
    # term has complementary exponent at most 1/2-sigma; summing its trivial
    # discrepancy over q<=x^(2A) is power-saving by the displayed margin.
    sigma = F(1, 10) + S
    pos("HB sigma endpoint", sigma - F(1, 10))
    pos("HB K=10 condition", 2 * sigma - F(1, 10))
    pos("HB central lower containment", (F(1, 2) - sigma) - (F(2, 5) - H))
    pos("HB Type0 direct power saving", F(1, 2) + sigma - 2 * A)
    pos("higher-prime-power saving", 1 - (2 * A + F(1, 3)))
    pos(
        "near-square-root IIc interval empty",
        F(1, 2) - sigma - (F(1, 3) + F(7, 3) * d + 3 * H),
    )

    # Scalar specialized Type-II and corrected direct-HB Type-III widths.
    pos("scalar II-1", F(19, 2) - 36 * A - 13 * d + 100 * H)
    pos("scalar II-2a", F(21, 25) - F(16, 5) * A - 2 * H - d)
    pos("scalar II-2b", F(63, 80) - 3 * A - 2 * H - d)
    gamma3 = F(2, 5) - S
    delta3 = F(1, 2) - F(7, 2) * w - F(9, 8) * gamma3 - H
    pos("corrected III width", delta3 - d)
    pos("corrected III distribution", 4 - (28 * w + 9 * gamma3 + 8 * delta3))

    # Put all large coordinates into bin 1 for IIa, IIb, and III.
    ca = F(2, 5) + F(24, 5) * w + F(7, 5) * d - 2 * H
    cb = F(1, 3) + 8 * w + F(7, 3) * d - 4 * H
    ci = F(1, 3) + F(4, 3) * delta3 - F(4, 3) * w - H
    pos("IIa first-total", ca - 2 * b)
    pos("IIb first-total", cb - 2 * b)
    pos("III first-total", ci - 2 * b)
    # The near-square-root strip invokes the same lemmas with omega=0.
    pos("omega=0 IIa first-total", F(2, 5) + F(7, 5) * d - 2 * H - 2 * b)
    pos("omega=0 IIb first-total", F(1, 3) + F(7, 3) * d - 4 * H - 2 * b)
    # Unused capacities really are nonnegative.
    for label, value in (
        ("IIa unused", F(1, 14) - F(24, 7) * w - 2 * H),
        ("IIb unused2", F(1, 10) - F(34, 5) * w - F(7, 5) * d - 4 * H),
        ("IIb unused3", F(1, 35) + F(22, 35) * w + F(3, 5) * d - 4 * H),
        ("omega=0 IIb unused3", F(1, 35) + F(3, 5) * d - 4 * H),
        ("III unused", F(1, 6) - delta3 / 3 + F(4, 3) * w - H),
        (
            "omega=0 III unused",
            F(1, 6)
            - (F(1, 2) - F(9, 8) * gamma3 - H) / 3
            - H,
        ),
    ):
        pos(label, value)

    # Uniform lower capacities for repaired Type IIc, omega_0 in [0,w].
    g0 = F(2, 5) - H
    g1 = F(1, 3) + 8 * w + F(7, 3) * d + 3 * H
    C = g0 - 2 * d - 8 * w - H
    D = F(1, 2) - g1 - 2 * w - H
    pos("IIc uniform C", C)
    pos("IIc uniform D", D)

    # Hypotheses of the exact two-bin lemma in the companion note.
    pos("zero-block b<C", C - b)
    pos("both-small 2B2<C", C - 2 * b2)
    pos("one-small overload<delta", d - (b2 + b - C))
    pos("least large<D", D - b / 3)
    Lmax = 2 * b - C
    pos("two-large Lmax<2delta", 2 * d - Lmax)
    pos("two-large 2Lmax<D", D - 2 * Lmax)

    # Constant extension B_m=b becomes empty at this first count.
    empty_at = b // d + 1
    assert empty_at * d > b
    print("first empty count", empty_at)
    print("PASS", name)


if __name__ == "__main__":
    for key, values in CANDIDATES.items():
        check(key, *values)
    print("DIRECT-HB FRONTIER EXACT CHECK PASS")
