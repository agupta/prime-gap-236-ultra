#!/usr/bin/env python3
"""Exact audit of one nonzero-minorant, K-free support construction.

This is a structural checker, not an H_1 certificate.  It deliberately uses
Fraction throughout and explicitly fails when a required inequality changes
sign.  The finite basis consists of the indicator of the part of the support
having exactly one coordinate above delta and total sum below eta=A-epsilon.
"""

from __future__ import annotations

from decimal import Decimal, getcontext
from fractions import Fraction as Q
from hashlib import sha256
from math import comb, factorial
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex"
SOURCE_SHA256 = "c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def positive_part_power(x: Q, n: int) -> Q:
    return x**n if x > 0 else Q(0)


def tq(a: Q, upper: Q, n: int) -> Q:
    """Return integral_0^upper t*(a-t)_+^n dt exactly."""
    if a <= 0 or upper <= 0:
        return Q(0)
    u = min(a, upper)
    y = a - u
    return (
        a * (a ** (n + 1) - y ** (n + 1)) / (n + 1)
        - (a ** (n + 2) - y ** (n + 2)) / (n + 2)
    )


def one_large_forms(k: int, delta: Q, cap: Q, eta: Q) -> tuple[Q, Q, Q, Q]:
    """Exact I,J for 1_{#large=1, large<=cap, sum<eta}.

    For J, J0 is the contribution in which none of the k-1 common
    coordinates is large, and J1 is the contribution in which exactly one
    common coordinate is large.  Inclusion-exclusion only concerns the
    remaining small-coordinate cube [0,delta]^r.
    """
    require(k >= 2, "k must be at least two")
    require(Q(0) < delta < cap < eta, "invalid one-large geometry")

    isum = Q(0)
    for h in range(k):
        isum += (-1) ** h * comb(k - 1, h) * (
            positive_part_power(eta - delta - h * delta, k)
            - positive_part_power(eta - cap - h * delta, k)
        )
    I = isum / factorial(k - 1)

    j0sum = Q(0)
    for h in range(k):
        j0sum += (-1) ** h * comb(k - 1, h) * tq(
            eta - delta - h * delta, cap - delta, k - 1
        )
    J0 = Q(2, factorial(k - 1)) * j0sum

    j1sum = Q(0)
    for h in range(k - 1):
        j1sum += (-1) ** h * comb(k - 2, h) * (
            tq(eta - delta - h * delta, delta, k - 1)
            - tq(eta - cap - h * delta, delta, k - 1)
        )
    J1 = Q(2, factorial(k - 2)) * j1sum
    return I, J0 + J1, J0, J1


def decimal(x: Q, digits: int = 70) -> str:
    getcontext().prec = digits
    return str(Decimal(x.numerator) / Decimal(x.denominator))


def self_test_forms() -> None:
    """Literal inactive-total-cap checks, independent of inclusion-exclusion."""
    d = Q(1, 10)
    cap = Q(1, 5)
    eta = Q(1, 2)  # eta > cap+(k-1)d for k=2,3

    I2, J2, J20, J21 = one_large_forms(2, d, cap, eta)
    require(I2 == 2 * (cap - d) * d, "literal k=2 I mismatch")
    require(J20 == d * (cap - d) ** 2, "literal k=2 J0 mismatch")
    require(J21 == (cap - d) * d**2, "literal k=2 J1 mismatch")
    require(J2 == J20 + J21, "literal k=2 J mismatch")

    I3, J3, J30, J31 = one_large_forms(3, d, cap, eta)
    require(I3 == 3 * (cap - d) * d**2, "literal k=3 I mismatch")
    require(J30 == d**2 * (cap - d) ** 2, "literal k=3 J0 mismatch")
    require(J31 == 2 * (cap - d) * d**3, "literal k=3 J1 mismatch")
    require(J3 == J30 + J31, "literal k=3 J mismatch")


def main() -> None:
    self_test_forms()
    require(SOURCE.is_file(), f"missing pinned source: {SOURCE}")
    require(sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256,
            "Stadlmann source hash mismatch")

    # One-stratum support and Harman parameters.
    k = 48
    support_epsilon = Q(37, 10_000)
    A = Q(521, 2_000)
    alpha = A + support_epsilon
    eta = A - support_epsilon
    delta = Q(7, 1_250)
    B = Q(21, 2_500)
    xi1 = Q(3_989, 10_000)
    xi2 = xi3 = Q(4_001, 10_000)
    harman_epsilon = Q(1, 10**10)
    omega = A - Q(1, 4)
    beta = 1 - 2 * xi2

    c10_alpha = Q(79_247, 300_000)
    c10_eta = Q(76_247, 300_000)

    definition1 = {
        "support_epsilon": support_epsilon,
        "A0_to_A": A + support_epsilon,
        "A_below_half_minus_epsilon": Q(1, 2) - support_epsilon - A,
        "B_minus_delta": B - delta,
        "delta_increment_reserve": delta,  # constant B has increment zero
        "beta_minus_B": beta - B,
        "alpha_minus_C10_alpha": alpha - c10_alpha,
        "eta_minus_C10_eta": eta - c10_eta,
        "two_delta_minus_B": 2 * delta - B,
    }
    for name, value in definition1.items():
        require(value > 0, f"Definition-1/support margin failed: {name}={value}")

    # Proposition 2, lines 1123--1130.  xi2<=xi3 is non-strict.
    proposition2 = {
        "2_minus_2xi1_minus_3xi2": 2 - 2 * xi1 - 3 * xi2,
        "xi3_minus_xi2": xi3 - xi2,
        "4_minus_xi1_minus_9xi2": 4 - xi1 - 9 * xi2,
        "2xi1_plus_xi2_minus_1": 2 * xi1 + xi2 - 1,
        "7_minus_17xi2": 7 - 17 * xi2,
    }
    require(proposition2["2_minus_2xi1_minus_3xi2"] > 0, "Prop2 inequality 1")
    require(proposition2["xi3_minus_xi2"] >= 0, "Prop2 inequality 2")
    require(proposition2["4_minus_xi1_minus_9xi2"] > 0, "Prop2 inequality 3")
    require(proposition2["2xi1_plus_xi2_minus_1"] > 0, "Prop2 inequality 4")
    require(proposition2["7_minus_17xi2"] > 0, "Prop2 inequality 5")
    require(xi2 > Q(2, 5), "this construction must be in the c2=24 branch")
    c2 = Q(24)

    # Proposition 3's displayed scalar inequalities, with the proposition's
    # internal epsilon h=10^-10 (not the support enlargement).
    scalar = {
        "type_I_first": xi1 - 4 * A + Q(2, 3) - 2 * harman_epsilon - delta,
        "type_I_second": Q(9, 7) - Q(34, 7) * A - 2 * harman_epsilon - delta,
        "type_II_face0": Q(19, 2) - 36 * A - 13 * delta + 100 * harman_epsilon,
        "type_II_first": xi2 / 10 - Q(32, 10) * A + Q(8, 10)
                         - 2 * harman_epsilon - delta,
        "type_II_second": xi2 / 4 + Q(11, 16) - 3 * A
                          - 2 * harman_epsilon - delta,
        "type_III": Q(11, 8) - Q(7, 2) * A - Q(9, 8) * xi3
                    - 2 * harman_epsilon - delta,
    }
    for name, value in scalar.items():
        require(value > 0, f"Prop3 scalar margin failed: {name}={value}")

    # Since B<2 delta, a nonempty Xi tuple has m,m'<=1 and total at most
    # 2B.  Put all entries in the first bin.  These are every resulting
    # capacity reserve for the printed A/IIa/IIb/III partitions.
    partition = {
        "type_I_first_minus_2B": xi1 - 2 * harman_epsilon - 2 * B,
        "type_I_empty_second": Q(1, 6) - 4 * omega - 2 * harman_epsilon,
        "type_IIa_first_minus_2B": Q(2, 5) + Q(24, 5) * omega
                                   + Q(7, 5) * delta - 2 * harman_epsilon - 2 * B,
        "type_IIa_empty_second": Q(1, 14) - Q(24, 7) * omega
                                 - 2 * harman_epsilon,
        "type_IIb_first_minus_2B": Q(1, 3) + 8 * omega + Q(7, 3) * delta
                                   - 4 * harman_epsilon - 2 * B,
        "type_IIb_empty_second": Q(1, 10) - Q(34, 5) * omega
                                 - Q(7, 5) * delta - 4 * harman_epsilon,
        "type_IIb_empty_third": Q(1, 35) + Q(22, 35) * omega
                                + Q(21, 35) * delta - 4 * harman_epsilon,
        "type_III_first_minus_2B": 1 - 6 * omega - Q(3, 2) * xi3
                                   - 2 * harman_epsilon - 2 * B,
        "type_III_empty_second": Q(5, 2) * omega + Q(3, 8) * xi3
                                 - 2 * harman_epsilon,
        # Middle-gamma Type-I factorization in source lines 1527--1530.
        "high_gamma_I_first_minus_2B": Q(1, 2) - 2 * omega
                                       - 2 * harman_epsilon - 2 * B,
        "high_gamma_I_empty_second": Q(1, 14) - Q(34, 7) * omega
                                     - 2 * harman_epsilon,
    }
    for name, value in partition.items():
        require(value >= 0, f"partition capacity failed: {name}={value}")

    # Printed IIc is impossible for negative omega_0 because its fourth cap
    # is 8 omega_0.  On the repaired above-square-root range 0<=omega_0<=omega,
    # the same all-in-first-bin assignment has the following worst reserves.
    gamma_hi = Q(1, 3) + 8 * omega + Q(7, 3) * delta + 3 * harman_epsilon
    iic_repaired = {
        "first_minus_2B": xi2 - 2 * harman_epsilon - 2 * delta - 8 * omega - 2 * B,
        "empty_second": Q(1, 2) - gamma_hi - 2 * omega - harman_epsilon,
        "empty_third": delta - harman_epsilon,
        "empty_fourth_at_zero": Q(0),
    }
    require(gamma_hi >= xi2 - harman_epsilon, "IIc gamma interval unexpectedly empty")
    for name, value in iic_repaired.items():
        require(value >= 0, f"repaired IIc capacity failed: {name}={value}")
    require(-8 * harman_epsilon < 0,
            "expected literal negative-omega_0 Prop3 counterexample disappeared")

    # Explicit open J-fiber box.  There is one common large coordinate b,
    # 46 equal common small coordinates s, and small distinguished t,t'.
    U = Q(5_123, 20_000)
    b = Q(1, 125)
    s = Q(4_963, 920_000)
    t = Q(1, 10_000)
    require(b + 46 * s == U, "open-box common sum identity")
    open_box = {
        "b_minus_delta": b - delta,
        "B_minus_b": B - b,
        "delta_minus_s": delta - s,
        "U_minus_C10_eta": U - c10_eta,
        "eta_minus_U": eta - U,
        "eta_minus_U_minus_t": eta - U - t,
        "delta_minus_t": delta - t,
    }
    for name, value in open_box.items():
        require(value > 0, f"open J-box margin failed: {name}={value}")

    # The c1 integrals are nonnegative.  With tau=xi2-2/5 and
    # ell=1-2xi2, the first domain has four widths <=5tau and all five
    # denominator factors >=ell; the second has widths <=10tau.
    tau = xi2 - Q(2, 5)
    ell = 1 - 2 * xi2
    c1_upper = Q(10_625) * tau**4 / ell**5
    require(c1_upper < Q(1, 299_000_000), "c1 upper bound too weak")

    # Exact singleton-basis contraction.  K=0 pointwise because for every i,
    # U_i=sum_{s!=i}t_s <= sum_s t_s < eta, whereas repaired K integrates
    # only U_i>eta.
    I, J, J0, J1 = one_large_forms(k, delta, B, eta)
    require(I > 0 and J > 0 and J0 > 0 and J1 > 0, "nonpositive exact form")
    direct_quotient = k * J / I
    require(direct_quotient < Q(133, 500), "unexpected singleton quotient bound")
    K = Q(0)
    signed_lower = (1 - c1_upper) * direct_quotient - k * c2 * K / I
    signed_upper = direct_quotient  # c1>=0 and K=0
    require(signed_lower > 0, "signed lower enclosure is nonpositive")
    require(signed_upper < 1, "singleton unexpectedly passes sieve criterion")

    print("AUDIT PASS: exact K-free geometric construction; NOT a sieve result")
    print(f"source_sha256={SOURCE_SHA256}")
    print(f"alpha={alpha}; eta={eta}; delta={delta}; B={B}; omega={omega}")
    print(f"c2={c2}; c1_upper={c1_upper}; c1_upper_decimal={decimal(c1_upper)}")
    for group_name, group in (
        ("definition1", definition1),
        ("proposition2", proposition2),
        ("proposition3_scalar", scalar),
        ("partition", partition),
        ("iic_repaired", iic_repaired),
        ("open_J_box", open_box),
    ):
        for name, value in group.items():
            print(f"{group_name}.{name}={value}")
    print(f"I={I}")
    print(f"J={J}")
    print(f"J0={J0}")
    print(f"J1={J1}")
    print(f"K={K}")
    print(f"48J_over_I={direct_quotient}")
    print(f"48J_over_I_decimal={decimal(direct_quotient)}")
    print(f"criterion_lower_using_c1_bound={signed_lower}")
    print(f"criterion_lower_decimal={decimal(signed_lower)}")
    print(f"criterion_upper_from_c1_nonnegative={signed_upper}")
    print(f"exact_shortfall_lower_bound={1-Q(133,500)}")
    print("THEOREM_READY=false")
    print("blocker_1=unproved high-gamma Type-I role swap lacks Siegel--Walfisz for alpha")
    print("blocker_2=signed c2>0 Proposition-1 implication has not been independently repaired")


if __name__ == "__main__":
    main()
