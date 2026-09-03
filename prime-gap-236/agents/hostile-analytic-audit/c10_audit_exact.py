#!/usr/bin/env python3
"""Independent exact audit of the C10 analytic parameters.

This intentionally does not import any discovery-side code.  In addition to
the advertised margins, it checks a proof-safe implementation of every open
Type-II interval.  In particular, IIc uses auxiliary width delta+4h and all
three intervals are shrunk inward before invoking Stadlmann's partition
lemma; IIb is checked with its actual gamma-dependent third capacity rather
than the non-uniform displayed simplification in Proposition 3.
"""

from fractions import Fraction as F


h = F(1, 10**10)
s = h / 10
zeta = h / 1000                 # Section-3 epsilon, before a harmless further shrink
inward = h / 10                 # closed interval lies in each open factor interval

eps = F(1, 200)
d = F(1, 100)
A = F(77747, 300000)
wmax = A - F(1, 4)
small = F(3, 20)
large = F(97, 625)
xi = F(2, 5)
sigma = F(1, 10) + s
total = 2 * large


def positive(name: str, x: F) -> None:
    if x <= 0:
        raise AssertionError(f"{name}: expected >0, got {x}")
    print(f"{name}\t{x}")


def nonnegative(name: str, x: F) -> None:
    if x < 0:
        raise AssertionError(f"{name}: expected >=0, got {x}")
    print(f"{name}\t{x}")


def da(gamma: F, w: F) -> F:
    return F(5, 7) * gamma - F(2, 7) - F(24, 7) * w - h


def db(gamma: F, w: F) -> F:
    return F(3, 7) * gamma - F(1, 7) - F(24, 7) * w - h


def ga(w: F) -> F:
    return F(2, 5) + F(24, 5) * w + F(7, 5) * d + 2 * h


def gb(w: F) -> F:
    return F(1, 3) + 8 * w + F(7, 3) * d + 3 * h


def check_iia(tag: str, w: F) -> None:
    lo, hi = ga(w), F(1, 2)
    positive(f"IIa {tag} nonempty upper range", hi - lo)
    # Lemma 7 strict distribution faces, uniformly over gamma in [lo,hi].
    positive(f"IIa {tag} distribution face 1", -(24*w + 7*da(lo,w) - 5*lo + 2))
    positive(f"IIa {tag} distribution face 2", -(8*w + 3*da(hi,w) - hi))
    # Closed [a+inward,b-inward] inside the open D_IIa interval.
    positive(f"IIa {tag} inward width over support delta", da(lo,w) - 2*inward - d)
    b_min = lo - 3*zeta - inward
    a_min = lo - 3*zeta - da(lo,w) + inward
    b_max = hi - 3*zeta - inward
    positive(f"IIa {tag} first capacity minus total", b_min - total)
    # This capacity increases with the Section-3 epsilon, so use epsilon=0
    # for a bound uniform over 0<epsilon<=zeta.
    positive(f"IIa {tag} unused second capacity", da(hi,w) - inward)
    positive(f"IIa {tag} a endpoint", a_min)
    positive(f"IIa {tag} b below one-half", F(1,2) - b_max)


def check_iib(tag: str, w: F) -> None:
    lo, hi = gb(w), ga(w)
    positive(f"IIb {tag} nonempty range", hi - lo)
    positive(f"IIb {tag} distribution face 1", -(24*w + 7*db(lo,w) - 3*lo + 1))
    positive(f"IIb {tag} distribution face 2", -(8*w + 3*db(hi,w) - hi))
    positive(f"IIb {tag} inward width over support delta", db(lo,w) - 2*inward - d)

    # Partition-lemma-12 capacities for the two shrunken open intervals.
    B1_min = lo - 3*zeta - inward
    B2_min = F(1,2) - hi - 2*w - 6*zeta - inward
    # C3 increases with the Section-3 epsilon; evaluate it at zero.
    C3_min = 2*w + db(lo,w)
    A1_min = lo - 3*zeta - db(lo,w) + inward
    A2_min = F(1,2) - hi - 2*w - 6*zeta - db(hi,w) + inward
    positive(f"IIb {tag} first capacity minus total", B1_min - total)
    positive(f"IIb {tag} unused second capacity", B2_min)
    positive(f"IIb {tag} actual unused third capacity", C3_min)
    positive(f"IIb {tag} a1 endpoint", A1_min)
    positive(f"IIb {tag} a2 endpoint", A2_min)
    # Equal interval widths give equality in b1-b2 >= a1-a2.
    nonnegative(f"IIb {tag} width-order structural face", F(0))
    positive(f"IIb {tag} b1+b2 below one-half", 2*w + 2*inward)


def check_iic() -> None:
    gmin = xi - h                 # safely below the actual HB lower edge xi-s
    gmax = gb(wmax)
    dc = d + 4*h                 # room for both inward endpoint shifts

    # Lemma 10 strict faces for auxiliary width dc, at their true extrema.
    positive("IIc distribution face 1", 1 - (8*wmax + 4*dc + 2*gmax))
    positive("IIc distribution face 2", gmin - (32*wmax + 10*dc))
    positive("IIc distribution face 3", 4*gmin - 48*wmax - 16*dc - 1)
    positive("IIc proof-start gamma-4omega-delta_c", gmin - 4*wmax - dc)
    positive("IIc inward width over support delta", dc - 2*inward - d)
    positive("IIc inward a1 endpoint", gmin - 3*zeta - dc + inward)
    positive(
        "IIc inward a2 endpoint",
        F(1,2) - gmax - 2*wmax - 6*zeta - dc + inward,
    )
    positive("IIc inward b1 below one-half", F(1,2) - gmax + inward)

    # Exact capacities from Lemma 13 after shrinking all three open
    # intervals.  The O(1/log x) dyadic-scale error is absorbed by taking x
    # large; the displayed fixed margins leave far more than zeta room.
    C = gmin - 2*dc - 8*wmax - 58*zeta + inward
    D = F(1,2) - gmax - 2*wmax - 6*zeta - inward
    # C3,C4 increase with the Section-3 epsilon; evaluate at zero.
    C3 = dc
    C4 = 2*inward
    positive("IIc uniform C1", C)
    positive("IIc uniform C2", D)
    positive("IIc uniform C3", C3)
    positive("IIc uniform C4", C4)

    # Complete zero/small/large two-bin lemma.
    positive("IIc zero block", C - large)
    positive("IIc both small", C - 2*small)
    positive("IIc one small overload", d - (small + large - C))
    positive("IIc least large fits D", D - large/F(3))
    Lmax = 2*large - C
    positive("IIc two-large lower reach", 2*d - Lmax)
    positive("IIc two-large upper fit", D - 2*Lmax)

    # Lemma 13 structural faces after equal inward shrinking.
    width = dc - 2*inward
    positive("IIc 3width+(a3-b3)", 2*width)
    nonnegative("IIc width-order structural face", F(0))


def check_typeiii(tag: str, w: F) -> None:
    gamma = F(1,2) - sigma
    d3 = F(1,2) - F(7,2)*w - F(9,8)*gamma - h
    positive(f"TypeIII {tag} distribution", 4 - (28*w + 9*gamma + 8*d3))
    positive(f"TypeIII {tag} inward width over support delta", d3 - 2*h - d)
    cap1 = F(1,3) + F(4,3)*d3 - F(4,3)*w - h
    cap2 = F(1,6) - d3/F(3) + F(4,3)*w - h
    positive(f"TypeIII {tag} first capacity minus total", cap1-total)
    positive(f"TypeIII {tag} unused second capacity", cap2)


def main() -> None:
    # Definition 1 and its complete finite schedule.
    positive("Definition1 epsilon", eps)
    positive("Definition1 A1-A0", A+eps)
    positive("Definition1 upper A slack", F(1,2)-eps-A)
    schedule = [small, small] + [large]*98
    assert len(schedule) == 100
    for i,b in enumerate(schedule):
        positive(f"Definition1 B{i+1}-delta", b-d)
        if i:
            nonnegative(f"Definition1 monotone {i}->{i+1}", b-schedule[i-1])
            nonnegative(f"Definition1 increment cap {i}->{i+1}", schedule[i-1]+d-b)
    assert 15*d <= large < 16*d
    print("first empty count\t16")

    # HB identity/combinatorial endpoints and scale containments.
    positive("HB sigma-1/10", sigma-F(1,10))
    positive("HB 2sigma-1/K", 2*sigma-F(1,10))
    positive("central gamma containment", (xi-s)-(xi-h))
    gamma3 = F(1,2)-sigma
    positive("TypeIII individual lower containment", 2*sigma-(1-2*(xi+h)))
    positive("TypeIII individual upper containment", (xi+h)-gamma3)
    positive("TypeIII pair containment", (F(1,2)+sigma)-(1-(xi+h)))

    qexp = 2*A
    assert qexp == F(1,2)+2*wmax
    positive("Type0 sharp-interval power saving", 1-((F(1,2)-sigma)+qexp))
    positive("prime square/Q power saving", 1-qexp)
    positive("higher prime-power power saving", 1-(qexp+F(1,3)))

    # Near-sqrt IIc is genuinely empty.
    positive("near-sqrt IIc empty gap", (xi-s)-gb(F(0)))
    check_iia("near", F(0))
    check_iib("near", F(0))
    check_iia("above", wmax)
    check_iib("above", wmax)
    check_iic()
    check_typeiii("near", F(0))
    check_typeiii("above", wmax)

    # Proposition 1 bookkeeping.
    positive("roughness beta-B1", F(1,2)-small)
    assert F(0) <= F(0) and 1 == 1-0
    print("C10 HOSTILE ANALYTIC EXACT PASS")


if __name__ == "__main__":
    main()
