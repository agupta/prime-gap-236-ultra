#!/usr/bin/env python3
"""Fail-closed exact checker for the direct-BV parameter family.

This checks only the analytic rational inequalities and exponent identity.
It does not certify a sieve Rayleigh quotient.
"""

from fractions import Fraction as Q


def check(e: Q) -> None:
    A = Q(1, 4)
    delta = Q(7, 250)
    R = A + e
    V = A - e

    assert 0 < e < Q(1, 4)
    assert -e < A < Q(1, 2) - e
    assert 0 < delta < R
    # Constant B schedule: every displayed Definition-1 transition.
    M = 1 // delta
    B = [None] + [R] * M
    assert M == 35
    for m in range(1, M):
        assert delta < B[m] <= B[m + 1] <= B[m] + delta
    assert delta < B[M]
    assert Q(1, 2) > B[1]

    # Symbolic coefficient of (1-epsilon_0) in the q exponent.
    left = A - e
    right = A + e
    assert left == V and right == R
    assert left + right == 2 * A == Q(1, 2)

    print(f"epsilon={e}")
    print(f"R={R} V={V} delta={delta} floor(1/delta)={M}")
    print("Definition 1 exact checks: PASS")
    print("q exponent: (1-epsilon_0)*(A-e+A+e)=(1-epsilon_0)/2")
    print("beta=1/2>B_1 exact check: PASS")
    print("ANALYTIC PARAMETER CHECK PASS (quotient not checked)")


if __name__ == "__main__":
    for epsilon in (Q(3, 400), Q(1, 1000), Q(1, 10000), Q(1, 100000)):
        check(epsilon)
