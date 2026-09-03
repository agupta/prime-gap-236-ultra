# Wide C722 hybrid: constant-shell schedule screen

## Scope

This is a discovery-only, source-bound comparison of the two analytically
audited wide C722 hybrid schedules.  It does not evaluate the target `k=48`
BV D16 quotient and cannot establish a prime-gap theorem.  The finite space
eventually intended for the target calculation is the exact certified radial
BV D16 vector on the inner band, adjoined to the constant function on the
complete outer shell.

The exact common parameters are

```text
k_target = 48
delta    = 361/50000
alpha_1  = 103/400       eta_1 = 97/400
alpha_2  = 3211/12000    eta_2 = 3031/12000
```

and the two outer schedules are

```text
high_plateau: B_m=min(11/200+(m-1)delta,43/250), active 0..23
volume_ramp:  B_m=min(49/625+(m-1)delta,1599/10000), active 0..22.
```

The independent analytic reports pinned by the gate have `AUDIT PASS` for
both supports, including `c1=c2=0`.  This package rechecks their exact
parameter and active-count fields; it does not inherit a finite quotient from
those reports.

## Exact form and independent low-k check

Write `F0` for the certified BV polynomial and let its exact radial amplitudes
on total-sum regions `S<=eta_1` and `eta_1<S<=alpha_1` be `a,b`.  For either
schedule write `H` for its capped support at total endpoint `alpha_2`, `L` for
the same capped support cut back to `alpha_1`, and `G=1_H-1_L`.  Since `F` and
`G` have disjoint total-sum interiors, their denominator cross form is zero.
The five new numerator ingredients are reconstructed as

```text
J(F,G) = b[J(R,H)-J(R,L)] + (a-b)[J(V,H)-J(V,L)],
J(G,G) = J(H,H)-2J(H,L)+J(L,L),
B_01   = k J(F,G),        B_11 = k J(G,G),
A_11   = I(H,H)-I(L,L).
```

`cross_marginal` intersects the four literal distinguished-coordinate
branches on its left and right; it does not read a producer matrix.  At
`k=2`, a separate piecewise-affine marginal-length integration gives exactly

```text
J(left,right) = 7079/3000000
signed self   = 94927012783/126000000000000
shell J       = 1/12500
k shell J     = 1/6250.
```

The tests also compare the `k=48` constant-shell denominator entries against
the separately frozen exact shell-volume artifact byte for byte.

## Why the proxy dimension is 30

The actual high-plateau shell is empty for every `k<=29`; this follows
exactly from the cap and total-sum constraints, and the test checks equality
of the high/low constant masses at `k=29`.  Both schedules have positive
shell mass at `k=30`, so `k=30` is the smallest common dimension in which a
schedule quotient comparison is meaningful.

The proxy replaces `F0` by the single radial D4 polynomial `(1-P1)^4` while
retaining the exact certified two radial amplitudes.  Its purpose is only to
measure which cap schedule has the more favorable cross/self quotient
sensitivity; it is not a surrogate proof about D16.

## Cost gate and frozen continuation rule

A source-bound exact D4 cross-form cost probe times 7,008 branch/domain calls.
The proxy has 21,690 base calls, 49,344 high-plateau schedule calls, and
48,576 volume-ramp schedule calls.  The only contemplated execution runs one
schedule per process, so each process deliberately recomputes the base and
uses 71,034 or 70,266 calls.  Its exact rational wall estimate is the measured
seconds-per-call times those counts times a `3/2` safety factor.  Launch is
disabled unless the maximum estimate is at most 900 seconds, measured peak
RSS per process is at most 131,072 KiB, and doubled aggregate RSS is at most
262,144 KiB.  It additionally requires an independent audit, completion of
session 11209, fresh output paths, and separate root authorization.

After both exact proxy results exist, a separate exact comparator must verify
their source hashes and forms.  A target continuation requires both

```text
best proxy gain over the shared base >= 1/100000
best quotient minus the other schedule >= 1/10000000.
```

Even then, the present D16 target estimate is about nine hours per schedule
and exceeds the separate 14,400-second target resource ceiling.  Hence this
gate never authorizes a `k=48` run; a new audited cost representation would be
needed.

The suggested second coordinate `F0` on the outer shell was assessed rather
than silently omitted.  Exact splitting gives 769 distinguished marginal
components and 67 rest orbits, versus one for the constant.  Before polynomial
expansion this makes a base/outer cross expose 67 times as many rest-orbit
pairs and an outer self form 4,489 times as many.  It is therefore recorded as
a valid but non-cheap later coordinate and is not allowed to delay the
constant-shell screen.

## Commands

The unit tests are lightweight:

```bash
python3 -m unittest agents/structural-basis/tests/test_wide_hybrid_outer_constant_proxy.py
python3 -O -m unittest agents/structural-basis/tests/test_wide_hybrid_outer_constant_proxy.py
python3 -m unittest agents/structural-basis/tests/test_wide_hybrid_outer_constant_proxy_gate.py
python3 -O -m unittest agents/structural-basis/tests/test_wide_hybrid_outer_constant_proxy_gate.py
```

The two proxy commands are serialized in the disabled gate.  They must not be
run until every launch prerequisite above is satisfied.  The evaluator's
default two-schedule mode is not an authorized production command.
