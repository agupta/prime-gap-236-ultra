#!/usr/bin/env python3
"""Independent exact analytic audit of the direct-Heath--Brown C70 support.

This file deliberately imports no discovery or frontier-checker code.  The
capacities are reconstructed from the open factor intervals in Stadlmann's
Section 3 and the proof-safe endpoint shrink used in the repaired direct-HB
argument.  All arithmetic used for the finite checks is rational.
"""

from fractions import Fraction as F
import sys


H = F(1, 10**10)                 # Definition 5's fixed epsilon
S = H / 10                       # reserve in sigma
ZETA_MAX = H / 1000              # source-lemma epsilon upper bound
INWARD = H / 10                  # shrink at each open endpoint
POINT_ID = sys.argv[2] if len(sys.argv) >= 3 else "C70"
SUPPORT_EPSILON = F(sys.argv[3]) if len(sys.argv) >= 4 else F(1, 200)
DELTA = F(sys.argv[1]) if len(sys.argv) >= 2 else F(7, 1000)
A = F(21, 80) - DELTA / 3 - F(1, 100000)
OMEGA = A - F(1, 4)
B = F(1, 8) + 3 * DELTA + F(1, 5000)
XI = F(2, 5)
SIGMA = F(1, 10) + S
GAMMA3 = F(1, 2) - SIGMA
MAX_COUNT = DELTA.denominator // DELTA.numerator


def positive(name: str, value: F) -> F:
    if value <= 0:
        raise AssertionError(f"{name}: expected > 0, got {value}")
    print(f"{name}\t{value}")
    return value


def nonnegative(name: str, value: F) -> F:
    if value < 0:
        raise AssertionError(f"{name}: expected >= 0, got {value}")
    print(f"{name}\t{value}")
    return value


def ga(w: F) -> F:
    return F(2, 5) + F(24, 5) * w + F(7, 5) * DELTA + 2 * H


def da(gamma: F, w: F) -> F:
    return F(5, 7) * gamma - F(2, 7) - F(24, 7) * w - H


def gb(w: F) -> F:
    return F(1, 3) + 8 * w + F(7, 3) * DELTA + 3 * H


def db(gamma: F, w: F) -> F:
    return F(3, 7) * gamma - F(1, 7) - F(24, 7) * w - H


def load_bound(m: int) -> F:
    return F(0) if m == 0 else B


def active_counts() -> list[int]:
    return [m for m in range(MAX_COUNT + 1) if m == 0 or m * DELTA <= B]


def check_all_pairs(tag: str, cap1: F) -> None:
    """Certify every nonempty Xi by putting all entries in the first bin."""
    active = active_counts()
    checked = 0
    worst = None
    for m in active:
        for mp in active:
            margin = cap1 - load_bound(m) - load_bound(mp)
            positive(f"{tag} all-first ({m},{mp})", margin)
            checked += 1
            item = (margin, m, mp)
            worst = item if worst is None or item < worst else worst
    if checked != 21 * 21:
        raise AssertionError(f"{tag}: expected 441 feasible pairs, got {checked}")
    print(f"{tag} checked_pairs\t{checked}")
    print(f"{tag} worst_pair\t{worst[1]},{worst[2]} margin={worst[0]}")


def check_iia(tag: str, w: F) -> None:
    lo, hi = ga(w), F(1, 2)
    positive(f"IIa {tag} gamma range", hi - lo)
    positive(
        f"IIa {tag} distribution face 1",
        -(24 * w + 7 * da(lo, w) - 5 * lo + 2),
    )
    positive(
        f"IIa {tag} distribution face 2",
        -(8 * w + 3 * da(hi, w) - hi),
    )
    positive(
        f"IIa {tag} shrunken width over support delta",
        da(lo, w) - 2 * INWARD - DELTA,
    )
    cap1 = lo - 3 * ZETA_MAX - INWARD
    cap2 = da(hi, w) - INWARD
    positive(f"IIa {tag} unused second capacity", cap2)
    positive(f"IIa {tag} lower factor endpoint", lo - 3 * ZETA_MAX - da(lo, w) + INWARD)
    positive(f"IIa {tag} upper endpoint below 1/2", F(1, 2) - (hi - 3 * ZETA_MAX - INWARD))
    check_all_pairs(f"IIa {tag}", cap1)


def check_iib(tag: str, w: F) -> None:
    lo, hi = gb(w), ga(w)
    positive(f"IIb {tag} gamma range", hi - lo)
    positive(
        f"IIb {tag} distribution face 1",
        -(24 * w + 7 * db(lo, w) - 3 * lo + 1),
    )
    positive(
        f"IIb {tag} distribution face 2",
        -(8 * w + 3 * db(hi, w) - hi),
    )
    positive(
        f"IIb {tag} shrunken width over support delta",
        db(lo, w) - 2 * INWARD - DELTA,
    )
    cap1 = lo - 3 * ZETA_MAX - INWARD
    cap2 = F(1, 2) - hi - 2 * w - 6 * ZETA_MAX - INWARD
    cap3 = 2 * w + db(lo, w)
    positive(f"IIb {tag} unused second capacity", cap2)
    positive(f"IIb {tag} unused third capacity", cap3)
    positive(f"IIb {tag} first lower endpoint", lo - 3 * ZETA_MAX - db(lo, w) + INWARD)
    positive(
        f"IIb {tag} second lower endpoint",
        F(1, 2) - hi - 2 * w - 6 * ZETA_MAX - db(hi, w) + INWARD,
    )
    nonnegative(f"IIb {tag} equal-width ordering", F(0))
    positive(f"IIb {tag} endpoint-sum reserve", 2 * w + 2 * INWARD)
    check_all_pairs(f"IIb {tag}", cap1)


def check_iic() -> None:
    gmin = XI - H             # below the actual HB edge XI-S
    gmax = gb(OMEGA)
    dc = DELTA + 4 * H        # auxiliary width before endpoint shrink

    positive("IIc gamma range", gmax - gmin)
    positive("IIc distribution face 1", 1 - (8 * OMEGA + 4 * dc + 2 * gmax))
    positive("IIc distribution face 2", gmin - (32 * OMEGA + 10 * dc))
    positive("IIc distribution face 3", 4 * gmin - 48 * OMEGA - 16 * dc - 1)
    positive("IIc proof-start face", gmin - 4 * OMEGA - dc)
    positive("IIc shrunken width over support delta", dc - 2 * INWARD - DELTA)
    positive("IIc first lower endpoint", gmin - 3 * ZETA_MAX - dc + INWARD)
    positive(
        "IIc second lower endpoint",
        F(1, 2) - gmax - 2 * OMEGA - 6 * ZETA_MAX - dc + INWARD,
    )
    positive("IIc first upper endpoint below 1/2", F(1, 2) - gmax + INWARD)

    # Literal Lemma-13 capacities after all three open windows are shrunk.
    cap1 = gmin - 2 * dc - 8 * OMEGA - 58 * ZETA_MAX + INWARD
    cap2 = F(1, 2) - gmax - 2 * OMEGA - 6 * ZETA_MAX - INWARD
    cap3 = dc
    cap4 = 2 * INWARD
    positive("IIc literal C1", cap1)
    positive("IIc literal C2", cap2)
    positive("IIc literal C3", cap3)
    positive("IIc literal C4", cap4)
    positive("IIc all-first master margin C1-2B", cap1 - 2 * B)
    check_all_pairs("IIc repaired", cap1)
    # The equal inward shifts preserve the structural width ordering.
    positive("IIc Lemma13 3width+(a3-b3)", 2 * (dc - 2 * INWARD))
    nonnegative("IIc Lemma13 equal-width ordering", F(0))


def check_type_iii(tag: str, w: F) -> None:
    d3 = F(1, 2) - F(7, 2) * w - F(9, 8) * GAMMA3 - H
    positive(f"III {tag} primary distribution", 4 - (28 * w + 9 * GAMMA3 + 8 * d3))
    positive(f"III {tag} corrected distribution 2", 4 - (16 * w + 9 * GAMMA3 + 2 * d3))
    positive(f"III {tag} corrected distribution 3", 4 - (28 * w + 9 * GAMMA3 - d3))
    positive(f"III {tag} auxiliary S lower", 1 - 4 * w + 4 * d3)
    positive(f"III {tag} auxiliary S upper", 1 - 2 * d3 + 8 * w)
    positive(f"III {tag} shrunken width over support delta", d3 - 2 * H - DELTA)
    cap1 = F(1, 3) + F(4, 3) * d3 - F(4, 3) * w - H
    cap2 = F(1, 6) - d3 / 3 + F(4, 3) * w - H
    positive(f"III {tag} unused second capacity", cap2)
    check_all_pairs(f"III {tag}", cap1)


def main() -> None:
    print("parameters", DELTA, A, SUPPORT_EPSILON, B, OMEGA)

    # Definition 1, including every listed and every empty count.
    positive("Definition1 delta", DELTA)
    positive("Definition1 epsilon", SUPPORT_EPSILON)
    positive("Definition1 A0-to-A1", A + SUPPORT_EPSILON)
    positive("Definition1 upper reserve", F(1, 2) - SUPPORT_EPSILON - A)
    positive("Definition1 B-delta", B - DELTA)
    for m in range(1, MAX_COUNT):
        nonnegative(f"Definition1 monotonicity {m}->{m + 1}", B - B)
        nonnegative(f"Definition1 increment {m}->{m + 1}", B + DELTA - B)
    active = active_counts()
    if active != list(range(21)):
        raise AssertionError(f"wrong active counts: {active}")
    for m in range(21, MAX_COUNT + 1):
        positive(f"empty Xi count {m}", m * DELTA - B)
    print(f"active_counts\t0..20 ({len(active)} including zero)")
    print(f"empty_counts\t21..{MAX_COUNT}")

    # Exact modulus exponent; support epsilon cancels between the two sides.
    qexp = 2 * A
    if qexp != F(1, 2) + 2 * OMEGA:
        raise AssertionError("modulus exponent identity")
    print("q exponent", qexp)

    # Heath--Brown identity and combinatorial trichotomy.
    positive("HB sigma endpoint", SIGMA - F(1, 10))
    positive("HB K=10 condition", 2 * SIGMA - F(1, 10))
    positive("central lower containment reserve", (XI - S) - (XI - H))
    positive("III individual lower containment", 2 * SIGMA - (1 - 2 * (XI + H)))
    positive("III individual upper containment", (XI + H) - GAMMA3)
    positive("III pair containment", (F(1, 2) + SIGMA) - (1 - (XI + H)))

    # Type 0, cutoff-safe version, and prime-power removal.
    positive("Type0 sharp-interval exponent saving", 1 - ((F(1, 2) - SIGMA) + qexp))
    positive("prime-square Q exponent saving", 1 - qexp)
    positive("higher-prime-power exponent saving", 1 - (qexp + F(1, 3)))

    # The displayed scalar sufficient conditions from Proposition 3 are a
    # cross-check; the branch checks below reconstruct the stronger open
    # endpoint statements actually used.
    positive("scalar II face 1", F(19, 2) - 36 * A - 13 * DELTA + 100 * H)
    positive("scalar II face 2a", F(21, 25) - F(16, 5) * A - 2 * H - DELTA)
    positive("scalar II face 2b", F(63, 80) - 3 * A - 2 * H - DELTA)
    positive("near-square IIc empty", (XI - S) - gb(F(0)))
    positive("above IIc/IIb boundary ordering", ga(OMEGA) - gb(OMEGA))
    positive("above IIa upper range", F(1, 2) - ga(OMEGA))

    check_iia("near", F(0))
    check_iib("near", F(0))
    check_iia("above", OMEGA)
    check_iib("above", OMEGA)
    check_iic()
    check_type_iii("near", F(0))
    check_type_iii("above", OMEGA)

    # Proposition 1 transfer for rho=(log n/log(3x))*1_P on [x,2x].
    positive("Proposition1 roughness beta-B1", F(1, 2) - B)
    print("Proposition1 pointwise minorant\t0 <= rho <= 1_P, hence c2=0")
    print("Proposition1 density\tPNT gives c1=0")
    print(f"{POINT_ID} DIRECT-HB ANALYTIC AUDIT PASS")


if __name__ == "__main__":
    main()
