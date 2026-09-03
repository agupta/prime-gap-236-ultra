# Independent audit of the gamma-correlated Type-IIb lift

## Verdict

`AUDIT PASS`, with deliberately limited scope.  The proposed outer schedule is
an exact analytic enlargement of the pinned active-25 support for the existing
direct-Heath--Brown/weighted-prime equidistribution route.  This audit proves
no finite-dimensional quotient and therefore proves neither `H_1 <= 236` nor
any new bounded-gap theorem by itself.

The audit was performed in the required hostile order.  I first reconstructed
the support, modulus, Type-IIb, partition, and Proposition-3 statements from
the primary TeX, without executing or importing the proposed checker.  I then
derived and implemented the continuum lemma independently.  Only after the
independent checker passed did I execute the proposed checker and compare its
critical outputs.

The accepted outer schedule is

```text
B1..B8 = 119469,126689,133909,141129,
          148349,155569,155569,162789 / 1000000
B9..B12 = 339/2000
B13..B25 = 1718,1737,1752,1762,1764,1774,1782,
            1790,1796,1801,1806,1811,1815 / 10000
B26 onward = 1815/10000.
```

The other exact parameters remain

```text
k=48, delta=361/50000, varepsilon=3/400,
A=(-3/400,1/4,3121/12000),
omega_cross=121/24000, omega_outer=121/12000.
```

## Primary-source dependency check

The following dependencies were read directly in
`sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex` (SHA-256
`c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba`).

| Source lines | Dependency used here | Audit conclusion |
|---|---|---|
| 137--150 | Definition 1, including `delta < B_m <= B_(m+1) <= B_m+delta` | The lower inequality is strict; both transition inequalities are non-strict.  The new equalities are legal. |
| 155--172 | Relevant moduli and the two separately capped groups | The two group caps are exactly the hypotheses used by the prefix lemma. |
| 593--608, 815--886 | Type IIb and its proof | `gamma`, the auxiliary width, and both divisor windows may vary over a compact interval with uniform strict reserve. |
| 1290--1329 | Three-factor partition Lemma 12 | The partition may depend on the tuple and on `gamma`; no single partition must work for the whole interval. |
| 1397--1448, 1575--1623 | Proposition 3 and its Type-IIb proof | The printed three fixed capacities are a later coordinatewise-minimum simplification.  Lines 1607--1613 first establish the stronger literal `gamma`-dependent criterion. |
| 210--241 | Key integrals and Proposition 1 | Zero-extending old functions preserves old-old `I` and `J` entries when the `A` bands are unchanged. |

The existing direct-HB route uses an even more carefully inward-shrunk form
of the literal criterion.  I pinned and checked the prior active-25 audit and
every transitive hash serialized in it, as well as the primary 2023
Stadlmann and Polymath TeX sources.  The support-independent decomposition,
BV ranges, Type-0 removal, Type-III repairs, and weighted-prime Proposition-1
argument are unchanged.  The checker nevertheless recomputes every
support-dependent packing case, including those whose caps did not change.

## The continuum lemma, independently proved

Fix one of

```text
omega in {0, 121/24000, 121/12000}
```

and put

```text
G_b = 1/3 + 8 omega + (7/3) delta + 3h,
G_a = 2/5 + (24/5) omega + (7/5) delta + 2h,
h=10^-10, Z=h/1000, r0=h/10.
```

After shrinking both open Type-IIb divisor intervals inward by `r0`, safe
first and second capacities are

```text
C(gamma) = gamma - 3Z - r0,
D(gamma) = 1/2 - gamma - 2 omega - 6Z - r0.
```

Their sum is constant.  For group counts `m,m'`, caps `B_m,B_m'`, and an
actual tuple of total load `T`, set

```text
S = B_m+B_m',  L = S-C(gamma),
ell = max(0,T-C(gamma)),  W = C(gamma)+D(gamma)-S.
```

If `ell=0`, the whole tuple goes in bin 1.  Otherwise let
`r=ceil(L/delta)`.  Select one of the left, right, or combined pools, sort it
in increasing order, and take the shortest prefix whose sum `U` is at least
`ell`.  Every entry is at least `delta`, so the prefix has at most `r` terms.

For `r=1`, its sole term is at most `S_g/n`, where `S_g` and `n` are the
selected pool cap and count.  For `r>=2`, if the prefix has `j<=r` terms and
preceding sum `P`, then the last term is no greater than
`(S_g-P)/(n-j+1)`.  Since `P<ell<=L` and the resulting affine expression is
increasing in `P`,

```text
U <= L + (S_g-L)/(n-r+1).
```

Moreover `L>(r-1)delta`.  Thus the respective finite sufficient tests are

```text
r=1:  S_g/n < W,
r>=2: (S_g-(r-1)delta)/(n-r+1) < W.
```

They imply `U<D(gamma)`, while `U>=ell` implies `T-U<=C(gamma)`.
Consequently the prefix and its complement give the required two nonempty
bins, with the third bin empty.  As `L(gamma)` decreases linearly, its ceiling
can take only

```text
1,...,ceil((S-C(G_b))/delta).
```

Checking those integers is a proof over the full real `gamma` continuum,
not a grid or limiting argument.  The selected pool is allowed to depend on
the crossing number because Lemma 12 quantifies `for every gamma, there
exists a partition`.

The unused third Lemma-12 capacity is

```text
2 omega + 9 zeta + d_b(gamma),
d_b(gamma)=(3/7)gamma-1/7-(24/7)omega-h.
```

It is increasing in `gamma`, and hence is at least

```text
delta + 2 omega + 2h/7 > 0.
```

## Open endpoints and uniformity

The checker verifies all four Lemma-12 endpoint requirements, equal interval
widths, `b1+b2<1/2`, positivity, and both strict Type-IIb distribution faces
at their adverse endpoints.  The least width reserve, common to all three
fixed `omega` values, is

```text
d_b(G_b)-2r0-delta = 3/350000000000 > 0.
```

The first distribution-face reserve is

```text
7/10000000000 > 0.
```

All remaining source faces are also strict; the global least source margin
is the unchanged Type-IIc width reserve

```text
1/200000000000 > 0.
```

Thus the internal Section-3 small parameter can be chosen uniformly over
the closed `gamma` interval.  Checking the two boundary values is stronger
than required: the adjacent IIa/IIc assignments already cover the joins.
There is no use of a negative `omega_0` branch.

## Exhaustive exact inventories

Unlike the proposed checker, which recomputes the changed cases and inherits
the rest, the independent checker reruns every case for the lifted schedule.

| Family | Ordered pairs | IIa/III checks | Correlated-IIb crossing checks |
|---|---:|---:|---:|
| mixed | 935 | 1,870 | 4,550 |
| transpose | 935 | 1,870 | 4,550 |
| outer | 675 | 1,350 | 0 (all first-bin) |
| outer-near | 675 | 1,350 | 225 |
| **total** | **3,220** | **6,440** | **9,325** |

The least exact margins are

```text
IIa/III: 186599869/600000000000
          outer, III, counts (8,17)

IIb:     800002897/10000000000000
          outer-near, counts (9,23), all-first branch
```

The full outer Type-IIc audit covers all `675*16*16=172800` rational
continuum cells.  Its least margin is

```text
89993/40000000000
at counts (6,25), omega cell 9, gamma cell 1.
```

Zero-count and small-count cases were not discarded.  Across the fixed
families, the inventory contains 110 left-zero, 110 right-zero, 16
both-positive-at-most-two, 408 exactly-one-at-most-two, and 2,576
both-at-least-three pairs.  The corresponding Type-IIc counts are 25, 25,
4, 92, and 529, totaling 675.

The proposal's claimed changed-case values were independently reproduced:
3,388 changed IIa/III checks, 2,602 changed IIb crossings, and 115,456 changed
IIc cells, with the same two critical margins above.  Its old
coordinatewise-minimum IIb test genuinely rejects mixed counts `(1,9)`;
the correlated proof is a substantive strengthening rather than a relabeling.

## Definition-1 boundaries and support inheritance

Counts `0,...,25` are active and count 26 is the first empty count:

```text
B25-25delta = 1/1000,
26delta-B26 = 311/50000.
```

Steps `B2-B1` through `B6-B5`, and `B8-B7`, equal `delta`; several other
steps are zero.  Definition 1 explicitly permits both equalities.  Therefore
the schedule is valid but is not claimed to be an interior point of the full
independent-parameter cone.

Every new cap dominates the old cap, with strict gains exactly at counts
1 through 11.  For each changed count the checker constructs a point at total
sum `13/50`, with exactly that many coordinates strictly above `delta`, and
with its large-coordinate sum strictly between the old and new cap.  Each
point therefore has an open neighborhood in the new support but outside the
old support.

Let `T0` and `T1` be the old and new supports.  Extending an old function by
zero from `T0` to `T1` leaves its old-old `I` and `J` products unchanged,
because the total-sum bands `A` are unchanged.  The eleven count-slivers are
mutually disjoint, symmetric, positive-measure sets.  Appending their
indicators therefore embeds the old 27-dimensional pencil in a
38-dimensional pencil.  This proves only finite-space containment; it does
not supply the missing new rows, columns, or a quotient above one.

## Proposition-1 side conditions

The pinned direct-HB argument uses

```text
rho(n;x)=(log n/log(3x))*1_P(n) on [x,2x], zero outside.
```

Thus `0<=rho<=1_P`, `c1=c2=0`, and nonzero values are supported on primes.
Taking `beta=1/2`, the only support-dependent side condition has exact margin

```text
beta-max_j B_(j,1) = 1/2-103/400 = 97/400 > 0.
```

The equidistribution input is the pinned direct-HB/BV/Type-II/Type-III
derivation.  This audit does not incorrectly invoke the paper's defective
general Type-I role swap or claim that Proposition 2 alone gives raw-prime
equidistribution.

## Independent artifacts and replay

```text
agents/audit/verify_correlated_iib_lift_independent.py
  9c1d6948807c45855b9180e408a702f3f3d34d46137b111707ba3197f4ca6bc0
agents/audit/test_correlated_iib_lift_independent.py
  175c2698e5f79031524e8bce3648f48fd6df41201643a7eac3064d8304df8091
agents/audit/results/correlated_iib_lift_independent_audit.json
  0c150083373751190fd427ea561f2f4e2f2c3590e77d4c4ed6a53e456d46e564
```

From `prime-gap-236/`, run

```bash
python3 -I agents/audit/test_correlated_iib_lift_independent.py
python3 -I -O agents/audit/test_correlated_iib_lift_independent.py
python3 -I agents/audit/verify_correlated_iib_lift_independent.py
python3 -I -O agents/audit/verify_correlated_iib_lift_independent.py
```

Both seven-test runs pass.  Normal and optimized checker outputs are
byte-identical with the JSON hash printed above.

For comparison only, after the independent audit was frozen I ran the
proposal at
`agents/analytic-new-lever/verify_correlated_iib_lift.py`, SHA-256
`0f95064e7da1c9f3bcc532080858b881569835b214355edf1c437ea6def67d49`.
Its output SHA-256 is
`5889a5b4a9e7e0e5c4bdf45ee5ea32dd1c3bbdd669c9c3ac87aa6d661f032212`,
and its schedule, changed-case inventories, witnesses, and critical exact
margins agree with the independent reconstruction.

One non-mathematical hardening was added: the independent checker validates
every transitive dependency hash listed inside the frozen baseline JSON.
The proposal pins the baseline checker and JSON but does not itself traverse
that full list.  This is not a counterexample under the current frozen source
state, but the closure check is required for a fail-closed standalone audit.

## Remaining blocker

The analytic lift passes.  The theorem target remains open until an exact
`k=48` finite-dimensional vector gives positive `c(M2-M1)c^T` (or the
corresponding general-minorant expression), with independently reconstructed
matrices.  In particular, none of the margins in this report is a sieve
Rayleigh-quotient margin.
