# Wide volume-ramp shell: exact large-count diagnostic

Status: **EXACT FINITE-SPACE OBSTRUCTION / AUDIT PASS**.  This calculation is
quotient-sensitive, but it concerns only constants on each large-count stratum
of the outer shell.  It contains no cross form with the BV D16 function and is
not a sieve certificate.

## Object and formulas

The already independently audited volume-ramp support has

```
k=48, delta=361/50000, epsilon=3/400,
A=(-3/400,1/4,3121/12000),
alpha1=103/400, alpha2=3211/12000, eta2=3031/12000,
B_m=min(49/625+(m-1)delta,1599/10000).
```

Its active outer counts are `R=0,...,22`.  Put

```
E_R = 1_{S(alpha2,B) \ S(alpha1,B)} 1_{#{i:t_i>delta}=R}.
```

The exact denominator matrix is diagonal.  Its `R` entry is computed as the
difference of two independently tagged support moments.  For the numerator,
each distinguished marginal branch has total count equal to the common count
or that count plus one.  Thus `48 J(E_R,E_S)=0` for `|R-S|>1`.  The surviving
entries are obtained from

```
J_shell = J(high,high) - J(high,low) - J(low,high) + J(low,low).
```

Only `HH`, `HL`, and `LL` are traversed: exact symmetry gives `LH=HL^T`.
There are 8,832 literal branch-domain integrals in each traversal, hence 26,496
total.  A representative exact `R=12` probe completed 1,104 such domains in
0.54 seconds at 21.1 MiB; the predeclared target gate was 120 seconds and
128 MiB, conditional also on at least 1.5 GiB `MemAvailable`.

## Exact result

The shell mass is overwhelmingly concentrated in the middle counts:

| R | exact-I mass fraction (decimal display) |
|---:|---:|
| 10 | 0.0765174347244345781 |
| 11 | 0.1796905913516053312 |
| 12 | 0.3125730891757922590 |
| 13 | 0.2628716082877396727 |
| 14 | 0.1107990371821310859 |

Those five strata contain exactly 94.2451760721702927% of shell I mass.  The
exact rationalized eigenvector has I-contribution order

```
11, 12, 10, 13, 9, 8, 14, ...
```

and the first six contain exactly 99.8494711091637429% of that vector's I
norm.  This makes `R=10,11,12,13` the first cross-contraction tier; `R=9,8,14`
are the natural second tier.

The Decimal100 and Decimal160 discovery solves agree at

```
0.0622741501493717194361107137352898799438946475792970...
```

The rationalized vector is then contracted with exact Fractions, giving

```
q = 0.0622741501493717194361107137352898799438946475655297...
```

and therefore does not cross one.  More strongly, exact LDL elimination of

```
(1/16) I - 48 J
```

has all 23 pivots strictly positive (the smallest pivot divided by its
corresponding I diagonal is about `0.0014739715974378`).  Hence **every nonzero
vector in this complete 23-dimensional shell tagged-constant space has
quotient strictly below `1/16`**.  This last statement is exact and does not
use the numerical eigensolve.

## Frozen artifacts and verification

- producer: `wide_shell_stratum_diagnostic.py`, SHA-256
  `dbbf990caf2c1e6bc418d525d4becdaedc82af54eec457e8eb5578da29555cc5`;
- low-k tests: `test_wide_shell_stratum_diagnostic.py`, SHA-256
  `05e27874bc9238f503b1554b712e47d66482da4216bb715839e748f07e4f2d31`;
  six tests pass normally and under `-O`, including a literal `k=2`
  piecewise-fiber integration and independent tagged `k=2,3` recurrence;
- I-only artifacts, normal and `-O`, byte-identical SHA-256
  `3bc1f4cc49a5abfe054635d846935dae94d0dcea17a494ebcb0d4a53631fef70`;
- complete pencil artifacts, normal and `-O`, byte-identical SHA-256
  `5ad7b42edfcae72b27a0e6221a1f5c1296695749c56d69309e01f0d505abdaf9`;
- read-only checker: `verify_wide_shell_stratum_artifact.py`, SHA-256
  `85d5a630e57d5bc10c5eb26bf20ad78f47676979a30ac1c35d9eff438a5812ea`.

Run:

```
python3 agents/small-delta-frontier/test_wide_shell_stratum_diagnostic.py
python3 -O agents/small-delta-frontier/test_wide_shell_stratum_diagnostic.py
python3 agents/small-delta-frontier/verify_wide_shell_stratum_artifact.py
python3 -O agents/small-delta-frontier/verify_wide_shell_stratum_artifact.py
```

The checker pins all arithmetic and analytic dependencies, requires canonical
normal/`-O` bytes, reconstructs the exact particular contraction from the
diagonal/superdiagonal, and recomputes every LDL pivot.  Both modes print
`AUDIT PASS`.

## Scope and next experiment

The result retires shell-only functions that are constant separately on each
large-count stratum.  It is not an upper bound on polynomial shell functions
or on their cross forms with the BV D16 core.  The cheapest relevant next
experiment is therefore an exact cross contraction of the BV vector with
`E_R` for `R=10,11,12,13`, followed only if useful by `R=9,8,14`; no full D16
shell matrix should be built first.
