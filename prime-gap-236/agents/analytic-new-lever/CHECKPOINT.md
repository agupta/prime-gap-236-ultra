# Gamma-correlated Type-IIb lift of the active-25 support

## Scope and outcome

This checkpoint gives a new exact analytic support certificate, not a sieve
quotient and not a theorem claim.  It keeps the audited parameters

```text
k=48, h=10^-10, delta=361/50000, varepsilon=3/400,
A=(-3/400,1/4,3121/12000),
omega_cross=121/24000, omega_outer=121/12000,
c1=c2=0.
```

The lever is to retain the literal dependence on the Type-IIb exponent
`gamma`.  The frozen active-25 audit replaces the three Type-IIb capacities
by coordinatewise minima attained at incompatible endpoints of the gamma
interval.  The specialized direct-HB Type-IIb inclusion asks for a partition
at each gamma (as does the analogous Proposition-3 condition), so the
partition may move with gamma.  The exact sliding-prefix lemma below removes
that avoidable loss without invoking the defective universal Proposition 3.

The resulting outer schedule is

```text
B1..B8 = 119469,126689,133909,141129,
          148349,155569,155569,162789  all divided by 10^6,
B9..B12 = 339/2000,
B13..B25 = 1718,1737,1752,1762,1764,1774,1782,
            1790,1796,1801,1806,1811,1815  all divided by 10^4,
B26 onward = 1815/10000.
```

It pointwise dominates the audited active-25 schedule.  The exact gains in
`B1,...,B11` are

```text
69,89,109,129,949,969,269,989 over 10^6,
3/400, 61/20000, 1/2000,
```

and every later gain is zero.  Counts `0,...,25` remain active and count 26
is still first empty, with margin `311/50000`.  Several Definition-1 steps
are deliberately saturated: `B2-B1=...=B6-B5=delta` and
`B8-B7=delta`; equality is allowed by Definition 1.

## Exact sliding-prefix lemma

For either fixed `omega=0`, `121/24000`, or `121/12000`, the audited
inward-shrunk Type-IIb construction uses

```text
G_b = 1/3 + 8 omega + (7/3) delta + 3h,
G_a = 2/5 + (24/5) omega + (7/5) delta + 2h,
G_b <= gamma <= G_a,
zeta <= Z=h/1000,  r0=h/10.
```

Two safe literal Lemma-12 capacities are

```text
C(gamma) = gamma - 3Z - r0,
D(gamma) = 1/2 - gamma - 2 omega - 6Z - r0.
```

Their sum is the constant

```text
K = 1/2 - 2 omega - 9Z - 2r0.
```

The unused third capacity is positive throughout:

```text
C3 >= 2 omega + d_b(G_b)
   = delta + 2 omega + 2h/7 > 0.
```

Indeed the shrunken factor endpoints are
`b1=gamma-3zeta-r0` and
`a2=1/2-gamma-2omega-6zeta-d_b(gamma)+r0`; hence Lemma 12's
third capacity is
`1/2-b1-a2=2omega+9zeta+d_b(gamma)`.  Since `d_b` increases in
gamma, dropping the nonnegative `9zeta` and evaluating at `G_b` gives the
displayed lower bound.  The already-audited width identity
`d_b(G_b)-2r0-delta=3/350000000000>0` ensures that the inward-shrunk factor
intervals still have the required width.

Here is the finite continuum criterion used by the checker.  Let the two
groups have counts `m,m'` and caps `B_m,B_m'`; put `S=B_m+B_m'` and
`W=K-S`.  For any gamma put `L=S-C(gamma)`.  If `L<=0`, put everything in
bin 1.  Otherwise set `r=ceil(L/delta)`.  It is sufficient that one of the
left, right, or combined pools, of count `n` and cap `S_g`, has `n>=r` and

```text
r=1:  S_g/n < W,
r>=2: (S_g-(r-1)delta)/(n-r+1) < W.              (1)
```

It suffices to check (1) for the finitely many integers

```text
1 <= r <= ceil((S-C(G_b))/delta).
```

Proof.  For an actual tuple of total `T<=S`, let
`ell=max(0,T-C(gamma))<=L`.  If `ell=0`, the empty bin-2 subset works.
Otherwise sort the selected pool increasingly and take its first prefix of
sum `U>=ell`.  Since every entry is at least `delta`, this prefix ends by its
`r`-th entry.  For `r=1`, its one entry is at most `S_g/n<W<D(gamma)`.
For `r>=2`, if the prefix ends at `j<=r`, its preceding sum is below `ell`
and hence below `L`.  The remaining entries are all at least its last entry,
so

```text
U <= L + (S_g-L)/(n-r+1)
   < L + W
    = D(gamma),
```

where the second inequality is (1) and
`L>(r-1)delta`.  Since `U>=ell`, its complement has sum at most
`C(gamma)`.  Put the prefix in bin 2, the complement in bin 1, and leave bin
3 empty.  This proves the partition for every real tuple and every gamma;
there is no gamma sampling or limiting argument.

The old coordinatewise-minimum sufficient test really rejects the lifted
point: at mixed counts `(1,9)` its fixed capacities are

```text
2928849997/7500000000,
417064997/7500000000,
5191/300000,
```

and its minimal-prefix routine has no certificate.  The sliding lemma is
therefore a distinct strengthening, not a restatement of the frozen audit.

## Exact affected-case audit

All pairs not involving an outer count in `1,...,11` are literally unchanged
from the pinned active-25 audit.  The standalone checker redoes every changed
case with `Fraction` arithmetic and imports neither that verifier nor any
active exact-computation module.

```text
changed ordered fixed-family pairs                 1694
changed IIa/III checks                             3388
least changed IIa/III margin
  186599869/600000000000   (outer III, counts 8,17)

Type-IIb crossing-number inequalities              2602
least changed Type-IIb margin
  800002897/10000000000000 (outer-near, counts 9,23)
least unused third-bin capacity
  252700001/35000000000

changed dynamic-IIc cells                        115456
least changed dynamic-IIc margin
  89993/40000000000         (counts 6,25; cell 9,1)
```

The dynamic-IIc cells retain the already-audited adverse-endpoint argument,
so each of the `16 x 16` cells is a rational continuum certificate.  The
unchanged source-level inequalities, interval endpoints, Type-0/III branches,
BV splits, prime-power removal, and Proposition-1 hypotheses are inherited
only after checking the pinned audit and dependency hashes.

Strict inclusion is geometric, not inferred from cap inequalities alone.
For example, take nine coordinates equal to `221/12000` and the other 39
equal to `29/12000`.  Their total is `13/50`, exactly nine coordinates are
larger than `delta`, and their large-coordinate sum is

```text
663/4000, with 81/500 < 663/4000 < 339/2000.
```

Thus an open neighborhood lies in the new count-9 outer stratum and outside
the old support.  The checker emits analogous exact witnesses for every
changed count `1,...,11`.

## Reusing the active exact computation

Let `T0` be the audited support and `T1` this lifted support.  For
`1<=m<=11`, define the disjoint sliver

```text
S_m = {t in the outer band: # {i:t_i>delta}=m,
       B_m(old) < sum_{t_i>delta} t_i <= B_m(new)}.
```

Extend each old-support function by zero from `T0` to `T1`.  Since `A` and
`varepsilon` did not change, every old-old `I` and `J` entry is exactly
unchanged.  Therefore the running 27-coordinate inner-plus-count pencil can
be embedded verbatim and augmented by the eleven symmetric indicators
`1_{S_m}`.  The resulting 38-coordinate denominator has the old block plus
eleven disjoint sliver diagonal entries; only new numerator rows/columns and
those eleven diagonal masses need computation.  Consequently its Rayleigh
maximum is at least the old finite-space maximum, without asserting that an
arbitrary quotient is monotone under support enlargement.

## Replay

```bash
python3 agents/analytic-new-lever/verify_correlated_iib_lift.py
python3 -O agents/analytic-new-lever/verify_correlated_iib_lift.py
```

The outputs are byte-identical.  At this checkpoint:

```text
checker SHA-256  0f95064e7da1c9f3bcc532080858b881569835b214355edf1c437ea6def67d49
output  SHA-256  5889a5b4a9e7e0e5c4bdf45ee5ea32dd1c3bbdd669c9c3ac87aa6d661f032212
```

No claim is made that the 38-coordinate quotient exceeds one.  The concrete
next computation is only the eleven sliver rows/columns after the frozen
active-25 output is available; the old block does not need reconstruction.
