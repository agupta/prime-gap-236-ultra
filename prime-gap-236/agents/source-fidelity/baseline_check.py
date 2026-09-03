#!/usr/bin/env python3
"""Exact scalar/end-point audit for Stadlmann's published parameter point.

This script deliberately checks both the valid rational margins and the
literal failure of Proposition 3(D) at omega_0=-10^-10.  It does not check a
sieve-integral certificate.
"""

from fractions import Fraction as Q


eta = Q(3, 400)
h = Q(1, 10**10)
d = Q(7, 250)
A = Q(253, 1000)
w = A - Q(1, 4)
xi1 = Q(19, 50)
xi2 = xi3 = Q(2, 5)


def positive(name: str, value: Q) -> None:
    if value <= 0:
        raise AssertionError(f"{name}: expected >0, got {value}")
    print(f"PASS {name}: {value} (~{float(value):.12g})")


def nonnegative(name: str, value: Q) -> None:
    if value < 0:
        raise AssertionError(f"{name}: expected >=0, got {value}")
    print(f"PASS {name}: {value} (~{float(value):.12g})")


assert A < Q(1, 2) - eta
assert d < Q(3, 20) <= Q(17, 100)
assert Q(3, 20) <= Q(17, 100) <= Q(3, 20) + d

# Proposition 3 scalar conditions.
p3_i = min(xi1 - 4 * A + Q(2, 3), Q(9, 7) - Q(34, 7) * A) - 2 * h - d
positive("Proposition 3(I) strict margin", p3_i)

p3_ii_first = Q(19, 2) - 36 * A - 13 * d + 100 * h
nonnegative("Proposition 3(II), first line", p3_ii_first)

p3_ii_second = min(
    xi2 / 10 - Q(32, 10) * A + Q(8, 10),
    xi2 / 4 + Q(11, 16) - 3 * A,
) - 2 * h - d
nonnegative("Proposition 3(II), min-line margin", p3_ii_second)

p3_iii = Q(11, 8) - Q(7, 2) * A - Q(9, 8) * xi3 - 2 * h - d
positive("Proposition 3(III) strict margin", p3_iii)

# First-bin capacities for A/B/C/E all dominate the maximum total budget 0.34.
total_budget = Q(17, 50)
first_caps = {
    "A": xi1 - 2 * h,
    "B": Q(2, 5) + Q(24, 5) * w + Q(7, 5) * d - 2 * h,
    "C": Q(1, 3) + 8 * w + Q(7, 3) * d - 4 * h,
    "E": 1 - 6 * w - Q(3, 2) * xi3 - 2 * h,
}
for branch, cap in first_caps.items():
    positive(f"partition {branch} all-in-first margin", cap - total_budget)

# Corrected D range omega_0 in [0,w].
gamma_low = xi2 - h
gamma_high = Q(1, 3) + 8 * w + Q(7, 3) * d + 3 * h
c1_worst = gamma_low - 2 * d - 8 * w - h
c2_worst = Q(1, 2) - gamma_high - 2 * w - h
c3_at_zero = d - h
c4_at_zero = Q(0)

positive("D bin 1 worst capacity minus 0.312", c1_worst - Q(39, 125))
positive("D bin 2 worst capacity minus 17/300", c2_worst - Q(17, 300))
positive("D bin 3 minimum capacity", c3_at_zero)
nonnegative("D bin 4 minimum capacity on corrected range", c4_at_zero)

# The Type IIc analytic estimate itself can be used with delta*=d, so that
# the partition capacities above are literal rather than a relaxation.
positive("Type IIc inequality 1 margin at delta*=d", 1 - (8 * w + 4 * d + 2 * gamma_high))
positive("Type IIc inequality 2 margin at delta*=d", gamma_low - (32 * w + 10 * d))
positive(
    "Type IIc inequality 3 margin at delta*=d",
    -1 - (48 * w + 16 * d - 4 * gamma_low),
)

# Square-root repair: at omega=0 the Type IIc gamma interval is empty, and
# every remaining near-square-root partition can put all coordinates in its
# first bin.
gc = Q(1, 3) + Q(7, 3) * d + 3 * h
positive("omega=0 Type IIc interval empty gap", (xi2 - h) - gc)
positive(
    "omega=0 Type I low-branch delta* margin",
    (xi1 - h - Q(1, 3) - h) - d,
)
positive("omega=0 Type I high-branch delta* margin", Q(1, 14) - h - d)
positive(
    "omega=0 Type IIa all-in-first margin",
    Q(2, 5) + Q(7, 5) * d - 2 * h - total_budget,
)
positive(
    "omega=0 Type IIb all-in-first margin",
    Q(1, 3) + Q(7, 3) * d - 4 * h - total_budget,
)
positive(
    "omega=0 Type III delta* margin",
    Q(1, 2) - Q(9, 8) * xi3 - h - d,
)
positive(
    "omega=0 Type III all-in-first margin",
    1 - Q(3, 2) * xi3 - 2 * h - total_budget,
)

# Literal printed endpoint obstruction.
c4_printed_endpoint = 8 * (-h)
if c4_printed_endpoint >= 0:
    raise AssertionError("expected the printed negative-omega endpoint to fail")
print(
    "EXPECTED FAIL Proposition 3(D) literal omega_0=-h endpoint: "
    f"fourth-bin capacity {c4_printed_endpoint} (~{float(c4_printed_endpoint):.12g})"
)

# Proposition 2.
positive("Harman 2xi1+3xi2<2 margin", 2 - (2 * xi1 + 3 * xi2))
nonnegative("Harman xi2<=xi3 margin", xi3 - xi2)
positive("Harman xi1+9xi2<4 margin", 4 - (xi1 + 9 * xi2))
positive("Harman 2xi1+xi2>1 margin", 2 * xi1 + xi2 - 1)
positive("Harman 17xi2<7 margin", 7 - 17 * xi2)

print("PASS exact published scalar audit; Proposition 3(D) needs the documented BV split")
