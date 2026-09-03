#!/usr/bin/env python3
"""Exact one-stratum constant-function diagnostic for the repaired K term.

This is deliberately not a sieve-certificate checker.  It reconstructs (3)
from rational inputs and prints exact fractions plus decimal scale estimates.
"""

from fractions import Fraction


def ratio(k: int, A: Fraction, epsilon: Fraction) -> Fraction:
    if k < 2 or not (Fraction(0) < epsilon < A):
        raise ValueError("require k >= 2 and 0 < epsilon < A")
    alpha = A + epsilon
    eta = A - epsilon
    v = eta / alpha
    return Fraction(1) - k * v ** (k - 1) + (k - 1) * v**k


def prop3_first_ii_A_upper(
        xi2: Fraction, delta: Fraction,
        harman_epsilon: Fraction = Fraction(1, 10**10)) -> Fraction:
    """Upper endpoint forced by the first scalar condition (II).

    Proposition 3 uses ``epsilon=10^-10`` from Definition 6 here, not the
    unrelated support-enlargement parameter denoted by ``varepsilon`` in
    Definition 1.  The displayed condition is

        xi2/10 - 32*A/10 + 8/10 - 2*epsilon >= delta.
    """
    if not (Fraction(0) < xi2 < 1 and delta >= 0 and
            harman_epsilon >= 0):
        raise ValueError("parameters must lie in their nonnegative ranges")
    return (8 + xi2 - 10 * delta - 20 * harman_epsilon) / 32


def main() -> None:
    k = 48
    c2 = 24
    cases = (
        ("C10", Fraction(77747, 300000), Fraction(1, 200)),
        ("tiny-1e-5", Fraction(779, 3000), Fraction(1, 100000)),
        ("tiny-1e-6", Fraction(779, 3000), Fraction(1, 1000000)),
    )
    for name, A, epsilon in cases:
        r = ratio(k, A, epsilon)
        p = k * c2 * r
        print(f"{name}: K/I={r}")
        print(f"{name}: k*c2*K/I={p}")
        print(f"{name}: decimal K/I={float(r):.17g}; penalty={float(p):.17g}")

    xi2_ceiling = Fraction(7, 17)
    a_ceiling = prop3_first_ii_A_upper(
        xi2_ceiling, Fraction(0), Fraction(0))
    print(f"formal delta->0, Harman-epsilon->0 A ceiling={a_ceiling}")


if __name__ == "__main__":
    main()
