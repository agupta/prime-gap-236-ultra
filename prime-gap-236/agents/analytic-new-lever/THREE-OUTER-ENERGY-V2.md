# Three-outer-band energy-targeted analytic support v2

This checkpoint is an exact **analytic-support** certificate.  It does not
claim a Riesz energy, a sieve quotient, or a bounded-gap theorem.  In
particular, no heuristic projection file is read or hashed by the acceptance
gate.

## Frozen rational point

The common parameters are

\[
 k=48,\qquad \delta=\frac1{60},\qquad
 \epsilon=\frac3{400},\qquad
 A_1=\frac14,
 \qquad A_4=\frac{231241}{900000}.
\]

Writing \(x=A_4-A_1=6241/900000\), the two new endpoints are

\[
 A_2=A_1+\frac{37}{40}x=\frac{9230917}{36000000},\qquad
 A_3=A_1+\frac{39}{40}x=\frac{3081133}{12000000}.
\]

Thus the three outer bands occupy fractions \(37/40,1/20,1/40\) of the
outer total-sum interval.  The broad lower schedule, through its first empty
count, is

```text
(140375,157041,168544,174338,185488,190375,
 193097,197146,202047,207090,211668,211668) / 10^6.
```

It has active counts 0 through 12.  Each narrow upper schedule is the plateau
\(1/60+2/10^6\), with active counts 0 and 1.  Against the frozen one-band
outer schedule, the broad-band cap gains at counts 4,5,6,7 are exactly

\[
 \frac{53}{20000},\quad \frac{1951}{250000},\quad
 \frac{9787}{10^6},\quad \frac{1939}{200000}.
\]

These are geometric cap gains, not energy gains.  The exact open witnesses in
the JSON show that every gain creates a positive-measure region of the stated
count in the broad band.

## Lemma 1: three consecutive sorted blocks for Type IIc

Let a candidate tuple consist of two pools of respectively \(n_L,n_R\)
entries.  Every entry is at least \(\delta\), and the pool sums are at most
\(B_L,B_R\).  Put \(S=B_L+B_R\), and let
\((C_1,C_2,C_3,C_4)\) be a positive capacity vector.

If \(S<C_1\), all entries go in the first bin.  Otherwise choose one of the
left pool, right pool, or their union.  Give it count \(n\), sum bound \(B\),
and sort its entries as \(y_1\le\cdots\le y_n\).  Set

\[
 r=\left\lfloor\frac{S-C_1}{\delta}\right\rfloor+1.
\]

Choose nonnegative \(q_2,q_3,q_4\) summing to \(r\), and assign the three
consecutive blocks of these sizes among bins 2,3,4 in any order.  If \(p\)
entries precede a block of size \(q\), its sum obeys

\[
 \sum_{h=p+1}^{p+q}y_h
 \le \frac{q}{n-p}\sum_{h=p+1}^n y_h
 \le \frac{q(B-p\delta)}{n-p}.                 \tag{1}
\]

The first inequality holds because this block comprises the \(q\) smallest
entries of the residual sorted pool; the second uses the lower bound
\(y_h\ge\delta\) on the \(p\) removed entries.  If the three rational bounds
in (1) are strictly below their assigned capacities, those bins fit.  The
unmoved entries have total at most

\[
 S-r\delta<C_1,
\]

so the first bin also fits.  The checker enumerates all three pool choices,
all compositions of \(r\), and all six assignments.  Hence an accepted cell
covers every real tuple, not merely sampled tuples.

On a closed Type-IIc cell
\([\omega_l,\omega_u]\times[\gamma_l,\gamma_u]\), the checker uses

\[
 (\gamma_l-2\delta-8\omega_u-H,
  1/2-\gamma_u-2\omega_u-H,
  4\omega_l+\delta-H,
  8\omega_l),
\]

the componentwise adverse endpoint vector.  Therefore the same displayed
partition works throughout the entire cell.  The old one-alternate-bin lemma
is tried first; Lemma 1 is invoked only where that proof fails.

## Lemma 2: crossing prefix or crossing item

For two capacities \((C,D)\), put \(L=S-C\ge0\) and sort any one of the
three pools above.  Let \(U_j\) be the least nonempty prefix with
\(U_j\ge L\) (take the first item when \(L=0\)).  Then
\(j\le r=\max(1,\lceil L/\delta\rceil)\).

If \(U_j<D\), move that prefix to the second bin.  Otherwise, because the
preceding prefix is strictly below \(L\), its crossing item satisfies

\[
 y_j=U_j-U_{j-1}>D-L>L
\]

whenever \(D>2L\).  Moreover

\[
 y_j\le\frac{B-(j-1)\delta}{n-j+1}.
\]

Consequently, if the latter upper bound is below \(D\) for every
\(1\le j\le r\), either the prefix or the crossing item alone lies in the
second bin and removes at least the required overload from the first bin.
This proves the partition for every represented tuple.  The permitted weak
first-bin equality can occur only in the prefix case; every tested alternate
capacity inequality is strict.

The checker also permits a simpler cross-pool action: put one entire pool and
the \(q\) smallest entries of the other into one bin.  Those selected entries
sum to at most \(qB/n\), while the residual sum is at most \(B-q\delta\).
Both orientations and both bin assignments are enumerated exactly.

## Lemma 3: literal three-bin Type IIb continuum

For a Type-IIb action, choose the \(q_L,q_R\) smallest entries of the two
original pools for the literal third capacity \(E(\gamma)\).  Their sum is at
most

\[
 q_L B_L/n_L+q_R B_R/n_R,
\]

and the residual pool caps are \(B_i-q_i\delta\).  Lemma 2 and the frozen
minimal-prefix lemma are applied to the residual capacities
\(C(\gamma),D(\gamma)\).

The verifier inserts every rational point where any of the following changes:

- the third-bin inequality against \(E(\gamma)\);
- a residual crossing number;
- either cross-pool inequality against \(C(\gamma)\) or \(D(\gamma)\);
- \(D(\gamma)=2(S-C(\gamma))\); or
- a sorted-tail bound equals \(D(\gamma)\).

Every predicate and the selected finite partition strategy is therefore fixed
on each resulting open interval.  The midpoint selects that fixed strategy;
every breakpoint itself is checked separately.  This proves the full
continuum without gamma sampling.  The result commits to all selected
strategies with SHA-256 digests.

## Exact inventory and strictness

The acceptance run checks 818 main ordered pairs and 280 near-root ordered
pairs, including 101 main cases with a zero left count and 101 with a zero
right count.  It checks 2,196 fixed Type-IIa/III cases.  The repaired IIc
inventory has 280 ordered pairs and 71,680 closed rational cells.  The old
one-alternate proof fails on thousands of those cells, all of which are
covered by Lemma 1; hence the new action is genuinely required.

The exact output also checks the common lower-schedule interval
\(B_m+t\), \(|t|\le10^{-7}\), at its adverse upper endpoint.  Active counts
do not change, and all fixed, Type-IIb, and Type-IIc margins remain positive.

## Reproduction

From the repository root:

```bash
python3 agents/analytic-new-lever/verify_three_outer_energy_v2.py
python3 -O agents/analytic-new-lever/verify_three_outer_energy_v2.py
python3 -m unittest agents/analytic-new-lever/test_three_outer_energy_v2.py
```

Normal and `python -O` runs are byte-identical.  Frozen hashes:

```text
checker  87747ad848c502e4d0047d60ca324d77ba94c9b0f5cb2afd6b5d46b953575605
result   bea2779a3ad4d5c5761a20ff85ca753486413e75bdf0002ea7e42be611c2a5b2
tests    857f3ad7bc3560615e5e68d568a22cc0041ad172cab028ff6552bcf63a582c8e
```
