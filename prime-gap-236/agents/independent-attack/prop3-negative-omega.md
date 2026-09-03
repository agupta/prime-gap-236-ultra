# Printed Proposition 3 has an impossible negative-omega branch

In arXiv:2608.31126v1, Proposition 3 / `prop:tupleconditions`, condition D
quantifies

```
omega_0 in [-h, omega(j,j')]
```

with `h=10^-10`, and simultaneously requires a partition whose fourth part
satisfies

```
sum_{i in I_4} y_i <= 8 omega_0.
```

Taking `omega_0=-h` makes the right side `-8h<0`, whereas every subset sum,
including the empty subset sum, is nonnegative.  Thus no tuple satisfies D at
that endpoint.  This is not a rounding issue and the Section 6 choice
`I_3=I_4=empty` does not repair it.

The proof shows where `8 omega_0` comes from.  In Lemma 10 (the four-factor
partition lemma), it is the capacity

```
a_1 - 2 b_1 - a_3 = 8 omega_0
```

after substituting the Type-IIc factor ranges.  Hence merely replacing the
right side by zero would not be a proved application of that lemma.

The apparent intended correction is to require Type-IIc only for
`omega_0>=0`, treating moduli at or below the square-root threshold by the
ordinary level-1/2 argument.  That correction matches Section 6's use of
empty `I_3,I_4`, but a complete new proof must explicitly supply the
level-1/2 branch for every sequence class in Definition 5.  Until that is
written, this is an analytic gap in v1, not a harmless convention.

Any support certificate in this directory therefore states explicitly when
it verifies the corrected `[0,omega]` condition rather than pretending to
satisfy the proposition as printed.
