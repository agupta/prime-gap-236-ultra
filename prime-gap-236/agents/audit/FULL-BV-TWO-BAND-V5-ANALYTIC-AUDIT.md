# Narrow full-BV two-band v5 hostile audit

## Verdict

**AUDIT FAIL.**  The frozen v5 package does not prove its claimed
Proposition-1 equidistribution statement.  Its outer/outer, above-square
Type-IIb branch violates a stated hypothesis of the three-factor partition
lemma on an interior (not boundary) value of the Type-II exponent.

This is a failure of the frozen analytic argument, not a numerical packing
failure and not a disproof of the underlying support.  A plausible smaller
auxiliary-width repair is recorded below, but it is outside v5 and needs a
new immutable package and fresh hostile audit.

## Frozen target and primary source

The audited producer is
`agents/small-delta-frontier/verify_full_bv_two_band_prop1_v5.py`, SHA-256
`03cc767fb8c95156afffdcc0c30c5b8811934a6a495827ff9478bb3c1323ecae`,
with artifact SHA-256
`358b5bf1528265b75afd8085da656582a58ce3e62205b9d7eb53638969686b76`.

The primary source is
`sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex`, SHA-256
`c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba`.
Its lines 1290--1298 require

\[
 a_1,a_2,b_1,b_2\in(0,1/2)
\]

before Partition Lemma `partition2` may be applied.  This is the lemma used
to convert a three-bin Type-IIb support partition into factors (r,u).

## Smallest exact failure

Use the frozen outer/outer above-square parameters

\[
 \delta=\frac7{250},\qquad \omega=\frac3{1000},\qquad
 h=10^{-10},\quad \zeta=h/1000,\quad r_0=h/10.
\]

V5 uses

\[
 G_a=\frac25+\frac{24\omega}{5}+\frac{7\delta}{5}+2h,
 \quad
 G_b=\frac13+8\omega+\frac{7\delta}{3}+3h,
\]

and the maximal Type-IIb width

\[
 d_b(\gamma)=\frac{3\gamma}{7}-\frac17-
               \frac{24\omega}{7}-h.
\]

Choose the strictly interior value

\[
 \gamma=G_a-h=\frac{4536000001}{10^{10}}.
\]

It satisfies

\[
 \gamma-G_b=\frac{463999997}{15000000000}>0,
 \qquad G_a-\gamma=h>0.
\]

After moving both open factor windows inward by (r_0), the lower exponent
of the (u)-window is

\[
\begin{aligned}
 a_2
 &=\frac12-\gamma-2\omega-6\zeta-d_b(\gamma)+r_0\\
 &=-\frac{4285714453}{5000000000000}<0.
\end{aligned}
\]

The upper exponent is positive,

\[
 b_2=\frac{201999999447}{5000000000000}>0,
\]

but that does not repair the failed premise (a_2\in(0,1/2)).  The v5
checker verifies only the derived bin capacities; it never checks this
source-side endpoint.  Its pinned C10 audit checked positivity for different
parameters and does not discharge the new outer/outer case.

Thus the invocation of Partition Lemma `partition2` is unavailable on an
open subinterval of the claimed Type-IIb range.  The small-BV, IIa, and IIc
branches do not cover this above-square slice as v5 assigns it.

## Preserved near-square regression

The omitted v4 case remains correctly diagnosed.  At near-square
Type-IIb, count pair ((1,4)), putting all coordinates in bin 1 has exact
margin

\[
 -\frac{6250003}{7500000000}<0.
\]

There is nevertheless a literal valid redistribution: sort the four outer
coordinates, move only the smallest one to bin 2, and leave the other three
outer coordinates plus the inner coordinate in bin 1.  Bin 3 is empty.  The
three exact slacks are

\[
 \frac{203749997}{7500000000},\qquad
 \frac{63249999}{2500000000},\qquad
 \frac7{250}.
\]

Accordingly, this example proves that all-first fails; it does **not** prove
that the third bin is necessary.

## Prospective repair, not part of the verdict

At the same hostile point, replacing (d_b(\gamma)) by the smaller uniform
auxiliary width

\[
 d=\delta+h/4=\frac{1120000001}{40000000000}
\]

would give (a_2=30999999711/2500000000000>0), inward width reserve
(d-2r_0-\delta=1/200000000000>0), and positive Type-IIb theorem margins
(29/40000000000) and (2764800001/8000000000).  This suggests v6 can be
repaired without changing the support or its safe third-bin capacity, but
that new choice and every dependent endpoint must be stated and re-audited.

## Independent replay

```bash
cd prime-gap-236
python3 agents/audit/verify_full_bv_two_band_prop1_v5_failure.py
python3 -O agents/audit/verify_full_bv_two_band_prop1_v5_failure.py
```

Both modes emit byte-identical `AUDIT FAIL` JSON.  The frozen machine-readable
output is `agents/audit/results/full_bv_two_band_prop1_v5_failure.json`.
