# Exact two-outer-band count-4--7 lever

## Outcome

There is an exact analytically legal two-outer-band refinement of the frozen
`delta=1/60` support.  It reallocates cap room toward counts 4--7 over the
lower 90% of the outer total-sum width, while retaining the frozen schedule
on the upper 10%.

This is an analytic support result only.  It does not compute retained D18
projection energy or a sieve quotient, and makes no bounded-gap theorem
claim.

## Rationals

Keep

```text
delta=1/60, varepsilon=3/400,
A_1=1/4, A_3=231241/900000.
```

Insert

```text
A_2 = A_1+(9/10)(A_3-A_1) = 256241/1000000.
```

Thus the total-sum bands are

```text
inner: [0,103/400),
lower outer: [103/400,263741/1000000),
upper outer: [263741/1000000,237991/900000).
```

The lower-outer schedule through count 12 is

```text
139683,156347,157797,173014,180929,183753,
186776,188864,190396,191607,192583,199985   divided by 10^6,
```

and is constant thereafter.  The upper-outer schedule is the frozen
single-band schedule

```text
138360,155020,158662,171688,177684,180588,
183402,185486,187011,188221,189137,189137   divided by 10^6.
```

Both outer schedules have active counts `0,...,11`.  The lower count-12
empty margin is `3/200000`.

Relative to the frozen schedule, the lower-band cap changes at counts 4--7
are exactly

```text
B4: +663/500000   = +0.001326
B5: +649/200000   = +0.003245
B6: +633/200000   = +0.003165
B7: +1687/500000  = +0.003374.
```

The explicit tradeoff is `B3: -173/200000=-0.000865`.  This support is not
a pointwise superset of the frozen one; it is a targeted geometric exchange.

## Complete ordered-pair check

For band endpoints `A_i,A_j`, the checker uses the exact value

```text
omega(i,j)=(A_i+A_j)/2-1/4.
```

The six distinct values and Type-IIc regimes are

```text
0                    empty
6241/2000000         empty
6241/1800000         empty
6241/1000000         nonempty
118579/18000000      nonempty
6241/900000          nonempty.
```

Every ordered pair other than inner/inner is checked on the main direct-HB
range.  Every ordered lower/upper outer pair is separately checked in the
near-square-root `omega=0` range.  Counts `m=0` and `m'=0` are included.

```text
main ordered band/count pairs         1336
near ordered outer-band/count pairs    572
main left-zero cases                     96
main right-zero cases                    96
IIa/III exact prefix checks             3816
IIb exact crossing-number checks        1726
nonempty-IIc band/count pairs            572
16x16 IIc cell checks                 146432
```

The theorem-facing IIb route is the same literal correlated empty-third
lemma proved in `ADAPTIVE-SUPPORT-V1.md`; no three-bin diagnostic is needed.
The exact worst packing reserves are

```text
IIa/III  10199831/2400000000000
IIb      290026073/90000000000000
IIc      319991/120000000000.
```

The IIa/III worst case is inner/lower Type III at counts `(1,3)`.  The IIb
worst case is inner/lower at `(1,1)`.  The IIc worst case is lower/upper at
counts `(3,9)`, omega-cell 8, gamma-cell 5.

All direct-HB source faces are re-evaluated at every one of the six omega
values.  The smallest source reserve remains the intentional IIc width
reserve `1/200000000000`.

There is also an explicit nonzero lower-cap neighborhood.  Translate all
lower-band caps by a common `t` with `|t|<=1/10^6`.  Definition-1 differences
are unchanged, both endpoints retain counts `0,...,11`, and checking the
monotone upper endpoint gives exact worst reserves

```text
IIa/III  7799831/2400000000000
IIb      200026073/90000000000000
IIc      199991/120000000000.
```

The frozen core independently checks the Proposition-2 specialization
`xi=(19/50,2/5,2/5)`, `rho=1_P` after normalization, `c1=c2=0`, and
`beta-max_j B_{j,1}=97/400` for `beta=1/2`.  The two-band checker pins that
core by SHA-256 and also rehashes every source/audit dependency in its pinned
closure.  It imports no optimizer or arithmetic producer.

## Objective boundary

The exact constant-function shell volume ratio is only

```text
two-band/single-band = 1.00000000020680608077920...
```

so raw volume is not the rationale for this construction.  The relevant
question is whether the count-4--7 cap increases preserve enough of the
natural D18 representer projection to clear the separately computed
retention threshold.  No sampling result is used here.  The next useful
calculation is an exact or rigorous-bounds comparison of `int_V G_F^2` for
this piecewise schedule against the frozen one, with the count-3 loss kept
explicit.

## Replay

```bash
python3 agents/analytic-new-lever/verify_two_outer_band_v1.py
python3 -O agents/analytic-new-lever/verify_two_outer_band_v1.py
python3 agents/analytic-new-lever/test_two_outer_band_v1.py
python3 -O agents/analytic-new-lever/test_two_outer_band_v1.py
```

The checker output is byte-identical in normal and optimized mode; all six
regression tests pass in both modes.

```text
checker  187a87f6c29532645100d9a91b94ce8038c38511dfff22326efe9722ea0f8001
result   c74da6b53d351df7df00435709bde048d50ddd5d75ff42ad631b2b029627bdee
tests    57b3ced2f04e36ae289f9faa82d47c95d87f76d545c672e1b91bdcc881e363cf
```
