#!/usr/bin/env python3
"""Exact margins for the direct Heath--Brown prime-equidistribution route."""

from fractions import Fraction as F


def pos(name: str, x: F) -> None:
    if x <= 0:
        raise AssertionError(f"{name}: {x}")
    print(f"{name}\t{x}")


def main() -> None:
    h = F(1, 10**10)
    s = h / 10
    sigma = F(1, 10) + s
    xi = F(2, 5)
    d = F(7, 250)
    w = F(3, 1000)
    total = 2 * F(889, 5000)

    # Polymath combinatorial trichotomy and containment in Definition 5.
    pos("sigma-1/10", sigma - F(1, 10))
    pos("2sigma-1/K (K=10)", 2 * sigma - F(1, 10))
    pos("TypeII lower containment", (F(1, 2) - sigma) - (xi - h))
    pos("TypeII upper containment", (1 - xi + h) - (F(1, 2) + sigma))
    pos("TypeIII lower containment", 2 * sigma - (1 - 2 * xi - h))
    pos("TypeIII upper containment", (xi + h) - (F(1, 2) - sigma))
    pos("TypeIII pair containment", (F(1, 2) + sigma) - (1 - xi - h))

    # The near-square-root Type-IIc interval is empty for all HB Type-II
    # aggregates, even after reserving s at the combinatorial endpoints.
    gc_zero = F(1, 3) + F(7, 3) * d + 3 * h
    pos("omega=0 TypeIIc gap", (F(1, 2) - sigma) - gc_zero)
    zero_type_ii_caps = {
        "IIa first-minus-total": F(2, 5) + F(7, 5) * d - 2 * h - total,
        "IIa second": F(1, 14) - 2 * h,
        "IIb first-minus-total": F(1, 3) + F(7, 3) * d - 4 * h - total,
        "IIb second": F(1, 10) - F(7, 5) * d - 4 * h,
        "IIb third": F(1, 35) + F(21, 35) * d - 4 * h,
    }
    for name, margin in zero_type_ii_caps.items():
        pos(f"omega=0 {name}", margin)

    # Apply the Type-III lemma at its natural HB parameter gamma=.4-s.
    gamma3 = F(1, 2) - sigma
    for name, omega in (("above", w), ("zero", F(0))):
        delta3 = F(1, 2) - F(7, 2) * omega - F(9, 8) * gamma3 - h
        pos(f"TypeIII-{name} delta3-d", delta3 - d)
        pos(
            f"TypeIII-{name} distribution margin",
            4 - (28 * omega + 9 * gamma3 + 8 * delta3),
        )
        cap1 = F(1, 3) + F(4, 3) * delta3 - F(4, 3) * omega
        cap2 = F(1, 6) - delta3 / 3 + F(4, 3) * omega
        # Reserve an inward endpoint perturbation eta=h in both bins.
        pos(f"TypeIII-{name} inward width", delta3 - 2 * h - d)
        pos(f"TypeIII-{name} cap1-minus-total-after-eta", cap1 - h - total)
        pos(f"TypeIII-{name} cap2-after-eta", cap2 - h)

    # Type 0 exponents: the full-convolution Poisson check, and the weaker
    # but cutoff-safe bounded-variation check N_S * Q.
    pos("Type0 full-Poisson power saving", 1 - (1 - 2 * sigma + 4 * w))
    qexp = 2 * F(253, 1000)  # harmless bound ignoring support shrink
    pos("Type0 sharp-interval power saving", 1 - ((F(1, 2) - sigma) + qexp))
    pos("higher-prime-power power saving", 1 - (qexp + F(1, 3)))

    print("DIRECT HB EXACT MARGINS PASS")


if __name__ == "__main__":
    main()
