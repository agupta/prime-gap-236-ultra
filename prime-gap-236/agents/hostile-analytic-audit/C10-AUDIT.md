# C10 ANALYTIC AUDIT PASS WITH REPAIRS

## Scope and verdict

This is an independent hostile audit of the analytic half of the C10
candidate.  It does **not** audit the finite-dimensional quotient, a
coefficient vector, or the admissible 48-tuple.

After reconstructing the argument from the primary TeX, the following
specialized statement passes:

> For
> \[
> \varepsilon=\frac1{200},\quad \delta=\frac1{100},\quad
> (A_0,A_1)=\left(-\frac1{200},\frac{77747}{300000}\right),
> \]
> \[
> B_1=B_2=\frac3{20},\qquad B_m=\frac{97}{625}\quad(3\le m\le100),
> \]
> and
> \[
> \rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)
> \quad(x\le n\le2x),
> \]
> all four hypotheses of Stadlmann's Proposition 1 hold with
> \(c_1=c_2=0\) and \(\beta=1/2\).

The discovery dossier cannot be cited literally.  Two mandatory repairs are
made below:

1. its Type-IIb third-bin number is evaluated at the wrong endpoint of the
   \(\gamma\)-interval;
2. its Type-IIc argument uses width \(\delta\) while also informally shrinking
   both endpoints of open factor intervals.  Width \(\delta\) cannot survive
   a two-sided shrink.  I use \(\delta_c=\delta+4h\) and reconstruct every
   capacity.

Neither repair changes the support or the minorant.

## Primary text audited

The exact files used are:

```text
c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba
  agents/source-fidelity/source-tree/Bounded_Gaps_2.0.tex
fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea
  sources/polymath8-edz-1402.0811-src/newergap.tex
```

The first is Stadlmann arXiv:2608.31126v1, submitted 2026-08-31.  The source
anchors used here are:

- Definition 1: Stadlmann lines 140--150;
- relevant moduli and equidistribution: lines 155--184;
- Proposition 1: lines 228--242;
- coefficient sequences and Type II/III lemmas: lines 532--669;
- partition Lemmas 11--13: lines 1248--1391;
- the Type-II/III parameter reduction: lines 1535--1747.

The Polymath8a anchors are:

- bilinear Bombieri--Vinogradov: lines 1043--1049;
- combinatorial trichotomy: lines 1305--1395;
- exact Heath--Brown identity: lines 1425--1465;
- finer-than-dyadic decomposition: lines 1496--1589;
- coefficient-sequence facts: lines 1637--1737;
- direct Type-0 Poisson argument: lines 1780--1863.

## 1. Definition 1 and the finite schedule

There is one stratum.  The exact Definition-1 margins are

```text
A1-A0                    = 79247/300000
1/2-varepsilon-A1        = 70753/300000
B1-delta = B2-delta      = 7/50
B3-B2                    = 13/2500
B2+delta-B3              = 3/625.
```

All transitions from \(B_3\) through \(B_{100}\) are equality on the
monotonic side and have increment slack \(1/100\).  Thus the entire
\(\lfloor1/\delta\rfloor=100\) column schedule, not merely its active prefix,
is defined and checked.

For the zero-count branches I use the forced empty-product convention
\(B_0=0\).  The paper's Definition 2 includes \(m=0\) although its matrix has
no zeroth column; omitting the corresponding bound is equivalent to this
convention.

Since

\[
15\delta=\frac3{20}\le\frac{97}{625}<\frac4{25}=16\delta,
\]

every \(\Xi\) with either count at least 16 is empty.  Counts 0 through 15
are the only nonempty possibilities.  This proves every count through 100,
including all one-zero, two-zero, small-count, and large-count branches.

The total of all displayed large factors from both modulus groups is always
at most

\[
2B=\frac{194}{625}.
\]

The support half-open total-sum endpoint and the strict definition
\(t_i>\delta\) cause no loss: the modulus sets allow factor exponents
\(\ge\delta\), and every partition below is proved on the larger closed
polytope \(y_i\ge\delta\).

## 2. Proposition 1 hypotheses (1), (3), and (4)

For \(x\le n\le2x\),

\[
0\le \frac{\log n}{\log(3x)}<1.
\]

Thus \(0=-c_2\le\rho\le1_{\mathbb P}\), proving hypothesis (1).  A
nonzero value is supported on a prime \(n\ge x\), whose prime factor is
larger than \(x^{1/2}\).  Since

\[
\frac12-B_1=\frac7{20}>0,
\]

hypothesis (3) holds with \(\beta=1/2\).

The prime number theorem gives

\[
\sum_{x\le n\le2x}\rho(n;x)
=\frac{\vartheta(2x)-\vartheta(x)}{\log(3x)}
=(1+o(1))\frac{x}{\log x},
\]

which is hypothesis (4) with \(c_1=0\).  This is the density of the actual
weighted minorant; no substitution of unweighted primes is made.

## 3. The relevant modulus bound and the epsilon conventions

Four small quantities must not be conflated:

```text
support enlargement       varepsilon = 1/200
relevant-modulus shrink   varepsilon_0 > 0
fixed proof reserve       h = 1/10^10
Section-3 small parameter 0 < zeta <= h/1000, chosen sufficiently small.
```

Also put

\[
s=h/10,\qquad \sigma=1/10+s,\qquad
\omega=A_1-1/4=2747/300000.
\]

For \(0<\varepsilon_0<1\), Definition 2 gives

\[
q\le x^{(1-\varepsilon_0)((A_1-\varepsilon)+(A_1+\varepsilon))}
\le x^{2A_1},
\]

where

\[
2A_1=\frac{77747}{150000}=\frac12+2\omega.
\]

Thus the support enlargement cancels exactly.  If
\(\varepsilon_0>1\), the defining nonnegative logarithms cannot satisfy the
negative upper bounds, so the modulus set is empty.  If
\(\varepsilon_0=1\), only \(q=1\) can remain and its discrepancy is zero.
Hence the displayed reduction covers every \(\varepsilon_0>0\).

## 4. Exact Heath--Brown reduction

Use the Polymath8a identity with \(K=10\).  It is exact on \([x,2x]\).
The forbidden endpoint is avoided:

```text
sigma-1/10     = 1/100000000000
2sigma-1/K     = 5000000001/50000000000.
```

After the finer-than-dyadic partition, every term is a convolution of at
most 20 atomic coefficient sequences.  Polymath's Facts lemma proves, with
the required divisor-power bounds, that:

1. every sub-convolution is located at the product scale;
2. any atom at exponent at least \(2\sigma\) is smooth;
3. any sub-convolution at a fixed positive power scale is Siegel--Walfisz;
4. the product of all scales is comparable to \(x\).

The combinatorial lemma therefore gives exactly one of:

- a smooth atom at exponent at least \(1/2+\sigma\);
- two complementary Siegel--Walfisz aggregates, each in
  \((1/2-\sigma,1/2+\sigma)\);
- three smooth atoms in \([2\sigma,1/2-\sigma]\), with each pair sum at
  least \(1/2+\sigma\).

The finite number \(\log(x)^{O(1)}\) of scale pieces is absorbed by asking
each distribution theorem for a correspondingly stronger logarithmic
saving.

For the small-modulus bilinear theorem, one may use Polymath's own removal of
the sharp \([x,2x]\) cutoff (lines 1559--1589), rather than assume an
unstated interval theorem.  The difference is supported in two intervals of
total length \(H_x\ll x\log(x)^{-R}\) and is bounded by a fixed divisor
power.  For a primitive class modulo \(q\le Q\), the support contains
\(O(H_x/q+1)\) integers, while the divisor-moment progression bound at lines
716--743 is \(xq^{-1}\log(x)^{O(1)}+x^{o(1)}\).  Since
\(Q\le x^{77747/150000}\), the first term dominates the harmless
\(x^{o(1)}\) term.  Cauchy--Schwarz therefore gives

\[
\sum_{n\equiv a\pmod q}|\alpha(n)|
\ll \frac{x}{q}\log(x)^{-R/2+O(1)}.
\]

The coprimality average has the same bound.  Summing in \(q\), using the
standard divisor-power average, costs only another power of \(\log x\).
This is the calculation written in Polymath's commented lines 1600--1627;
it supplies the summed estimate that the too-weak per-modulus display at
line 1578 does not by itself show.  Taking \(R\) arbitrarily large rigorously
permits use of the printed bilinear theorem.

## 5. Type 0

Fix the complementary convolution variable.  The long smooth atom, cut to
the resulting interval, has total variation \(\log(x)^{O(1)}\).  Its
discrepancy between one primitive class and the coprimality average is
\(\tau(q)^{O(1)}\log(x)^{O(1)}\).  The complementary convolution has
\(\ell^1\)-norm at most
\(x^{1/2-\sigma}\log(x)^{O(1)}\).  Summing over every
\(q\le x^{2A_1}\) costs

\[
x^{(1/2-\sigma)+2A_1}\log(x)^{O(1)}.
\]

The exact exponent saving is

\[
1-\left((1/2-\sigma)+2A_1\right)
=\frac{24506000003}{300000000000}>0.
\]

This branch uses no modulus factorization and no Type-I theorem.

## 6. Central aggregate: exhaustive modulus split

Orient the smaller aggregate as \(\beta\).  It is Siegel--Walfisz and its
exponent satisfies

\[
2/5-s<\gamma\le1/2.
\]

The slightly larger closed interval \([2/5-h,1/2]\) contains it with margin
\(h-s=9/10^{11}\).

### 6.1 Small moduli

For

\[
q\le x^{1/2}\log(x)^{-L},
\]

Polymath's bilinear Bombieri--Vinogradov theorem applies to the two
aggregates: their product scale is comparable to \(x\), and the chosen
Siegel--Walfisz factor has scale at least a fixed power of \(x\).  The cutoff
removal just proved supplies precisely the interval form needed here.

### 6.2 The near-square-root strip

For

\[
x^{1/2}\log(x)^{-L}<q\le x^{1/2},
\]

use the 2026 Type-II lemmas with \(\omega=0\).  This strip exceeds the fixed
lower threshold \(x^{1/2-\varepsilon_1}\) in partition Lemmas 11--12 once
\(x\) is large.

The IIc range is empty by the exact gap

\[
\frac{12999999907}{300000000000}>0.
\]

The IIa/IIb construction and every open endpoint are included in Section
6.4 below with \(\omega_*=0\).

### 6.3 Above the square root

For \(x^{1/2}<q\le x^{1/2+2\omega}\), use the Type-II lemmas with the fixed
upper parameter \(\omega\).  IIa and IIb use partition Lemmas 11 and 12
directly.  IIc is split into dyadic modulus blocks
\(q\asymp x^{1/2+2\omega_0}\), \(0\le\omega_0\le\omega\), as required by
partition Lemma 13.  Its \(O(1/\log x)\) dyadic exponent displacement is
smaller than the fixed inward reserve for all sufficiently large \(x\).
Uniform strict distribution margins make the constants independent of the
block.

These ranges, together with Sections 6.1 and 6.2, include every modulus and
do not use the paper's erroneous negative-\(\omega_0\) endpoint.

### 6.4 Proof-safe IIa and IIb factor intervals

For either \(\omega_*=0\) or \(\omega_*=\omega\), put

\[
G_a=\frac25+\frac{24}{5}\omega_*+\frac75\delta+2h,
\qquad
G_b=\frac13+8\omega_*+\frac73\delta+3h.
\]

IIa handles \(G_a\le\gamma\le1/2\) with

\[
d_a(\gamma)=\frac57\gamma-\frac27-\frac{24}{7}\omega_*-h.
\]

Its two Section-3 strict faces have uniform minima \(7h\) and the positive
values printed by the checker.  Instead of feeding the open interval
directly to partition Lemma 11, use the closed interval obtained by moving
each endpoint inward by

\[
r_0=h/10.
\]

At \(\gamma=G_a\), the width left over beyond the support increment is

\[
d_a(G_a)-2r_0-\delta=\frac1{43750000000}>0.
\]

Putting every support coordinate in the first bin has exact worst margins

```text
near sqrt:  1036000001897/10000000000000
above sqrt: 1475520001897/10000000000000.
```

The unused second bin and all interval endpoints are strictly admissible;
the checker reconstructs their exact fractions.

IIb handles \(G_b\le\gamma\le G_a\) with

\[
d_b(\gamma)=\frac37\gamma-\frac17-\frac{24}{7}\omega_*-h.
\]

Shrink both required open factor intervals inward by the same \(r_0\).  The
width left beyond \(\delta\), at the worst endpoint, is

\[
d_b(G_b)-2r_0-\delta=\frac3{350000000000}>0.
\]

The two distribution faces again have uniform positive margins (the first
is exactly \(7h\)).  Equal shrunken widths give
\(b_1-b_2=a_1-a_2\), while
\(b_1+b_2<1/2\) is strict even at \(\omega_*=0\), because of the inward
shifts.  The first bin contains all coordinates and the other bins are
empty.

Here the dossier's advertised third-bin lower bound is wrong: the actual
third capacity is increasing, not decreasing, in \(\gamma\).  Its exact
uniform minima (also uniform as the Section-3 parameter tends to zero) are

```text
omega_*=0:      350000001/35000000000
omega_*=omega:  2972900003/105000000000.
```

Both are positive, so the erroneous larger numbers are unnecessary.  The
first-bin margins are

```text
near sqrt:  1388000008691/30000000000000
above sqrt: 1195200002897/10000000000000,
```

and the actual second capacities are also strictly positive.  Thus every
hypothesis of partition Lemma 12 is met.

### 6.5 Repaired IIc, including open endpoints

Use the closed HB rectangle

\[
2/5-h\le\gamma\le
\frac13+8\omega+\frac73\delta+3h,
\qquad 0\le\omega_0\le\omega.
\]

Choose the Type-IIc auxiliary width

\[
\boxed{\delta_c=\delta+4h=\frac{25000001}{2500000000}}.
\]

Choose the Section-3 parameter \(0<\zeta\le h/1000\) sufficiently small,
and put \(r_0=h/10\).  Before inward shrinking, the three open intervals in
Lemma 10 have exponent endpoints

\[
\begin{aligned}
a_1&=\gamma-3\zeta-\delta_c,&b_1&=\gamma-3\zeta,\\
a_2&=\tfrac12-\gamma-2\omega_0-6\zeta-\delta_c,
&b_2&=\tfrac12-\gamma-2\omega_0-6\zeta,\\
a_3&=-\gamma-8\omega_0-52\zeta-\delta_c,
&b_3&=-\gamma-8\omega_0-52\zeta.
\end{aligned}
\]

Apply partition Lemma 13 to
\([a_i+r_0,b_i-r_0]\) for all three intervals.  Every width is

\[
\delta_c-2r_0=\delta+\frac{19}{50000000000},
\]

so the required \(\ge\delta\) condition survives.  The remaining structural
conditions are

\[
3(b_1'-a_1')+(a_3'-b_3')
=\frac{500000019}{25000000000}>0,
\]

and \(b_1'-b_2'=a_1'-a_2'\).

The three strict Section-3 distribution margins, at their true worst
endpoints, are

```text
1-(8 omega+4 delta_c+2 gamma_max)
    = 403599967/15000000000
gamma_min-(32 omega+10 delta_c)
    = 209599877/30000000000
4 gamma_min-48 omega-16 delta_c-1
    = 1199983/2500000000.
```

The additional proof-start and endpoint faces are also strict:

```text
gamma_min-4 omega-delta_c       = 2120239997/6000000000
inward a1                       = 3899999995097/10000000000000
inward a2                       = 626499989641/15000000000000
1/2-inward b1                   = 7007999971/100000000000.
```

After inward shrinking, uniform lower capacities for partition Lemma 13 are

```text
C1 = 4601199986563/15000000000000
C2 =  776499995341/15000000000000
C3 =          25000001/2500000000
C4 =                    1/50000000000.
```

For \(C_1,C_2\), these use the worst allowed \(\zeta=h/1000\).  The
\(C_3,C_4\) values use \(\zeta=0\), hence are lower bounds uniform for every
allowed positive \(\zeta\).

It remains to prove a partition for the complete continuous \(\Xi\), not
just sampled points.  Let \(T\) be the total load and
\(L=\max(0,T-C_1)\).  The exact margins are

```text
C1-B                         = 2273199986563/15000000000000
C1-2B_small                  =  101199986563/15000000000000
delta-(B_small+B-C1)         =  173199986563/15000000000000
C2-B/3                       =       499995341/15000000000000
2delta-(2B-C1)               =  245199986563/15000000000000
C2-2(2B-C1)                  =   222299989489/5000000000000.
```

They prove all branches as follows.

- If one count is zero, \(T\le B<C_1\).
- If both counts are at most two, \(T\le2B_{\rm small}<C_1\).
- If exactly one count is at most two, then \(L<\delta\).  The least entry
  in the count-at-least-three group lies in
  \([\delta,B/3]\subset(L,C_2)\); put it in bin 2.
- If both counts are at least three, take the least entry in each group.  If
  either reaches \(L\), it alone lies below \(B/3<C_2\).  Otherwise their
  sum is at least \(2\delta>L\), is less than \(2L\), and hence is below
  \(2(2B-C_1)<C_2\).

Everything not put in bin 2 has load at most \(C_1\); bins 3 and 4 are
empty.  The empty tuple \((m,m')=(0,0)\) is covered by four empty bins.  This
proves every point in every nonempty count polytope for counts 0 through 15;
counts 16 through 100 are empty as proved in Section 1.

## 7. Three-atom Type III

Set

\[
\gamma_3=1/2-\sigma=2/5-s.
\]

The HB inequalities match the stated 2026 Type-III lemma exactly:

\[
N_i\gg x^{1-2\gamma_3},\qquad
N_i\ll x^{\gamma_3},\qquad
N_iN_j\gg x^{1-\gamma_3}.
\]

Equality of an exponent endpoint is permitted by the Vinogradov bounds, and
the three atoms are smooth by Polymath's Facts lemma.

For \(\omega_*=0\) and \(\omega_*=\omega\), choose

\[
\delta_3(\omega_*)=rac12-\frac72\omega_*
-\frac98\gamma_3-h.
\]

Then

\[
4-(28\omega_*+9\gamma_3+8\delta_3)=\frac1{1250000000}>0.
\]

Shrink the open Type-III factor interval inward by \(h\) at each endpoint.
The widths remaining beyond the support increment are

```text
omega_*=0:      31999999769/800000000000
omega_*=omega:  19083999307/2400000000000.
```

Put all coordinates in the first partition bin.  The first-bin margins over
\(2B\), and the unused second capacities, are respectively

```text
omega_*=0:      53759999869/600000000000,
                359999999831/2400000000000
omega_*=omega:  20795999869/600000000000,
                138313333277/800000000000.
```

Thus partition Lemma 11 places the required factor strictly inside the open
Type-III interval.  Small moduli are handled by bilinear
Bombieri--Vinogradov after grouping two smooth atoms and the residual
coefficient sequence on one side and the third smooth atom (which is
Siegel--Walfisz and has fixed positive-power scale) on the other.  The
near-square-root strip uses \(\omega_*=0\), and the above-square-root range
uses \(\omega_*=\omega\).  Every three-atom term is covered.

## 8. Prime powers and passage to rho

The preceding cases give arbitrary logarithmic saving for
\(\Lambda1_{[x,2x]}\).  Write

\[
\vartheta(n)=\log n\,1_{\mathbb P}(n),\qquad
PP(n)=\Lambda(n)-\vartheta(n),\qquad Q=x^{2A_1}.
\]

For squares, a squarefree \(q\) has at most \(2^{\omega(q)}\) roots of a
fixed primitive residue.  Summing first in the root classes gives

\[
\sum_{q\le Q}\sum_{p^2\equiv a\pmod q}\log p
\ll x^{1/2}\log^3x+Q\log^2x.
\]

For powers \(p^r\), \(r\ge3\), there are \(O(x^{1/3})\) relevant pairs;
the deliberately crude bound of at most \(Q\) moduli per pair gives

\[
\ll Qx^{1/3}\log x
=x^{127747/150000}\log x.
\]

The exponent saving is

\[
1-\frac{127747}{150000}=\frac{22253}{150000}>0.
\]

For the coprimality average, the total prime-power mass is
\(O(x^{1/2}\log x)\) and
\(\sum_{q\le Q}1/\phi(q)\ll\log Q\).  Hence prime powers are
power-saving after summing over all \(q\le Q\), uniformly in the primitive
residue.  Equidistribution follows for \(\vartheta\), and division by the
constant \(\log(3x)\) gives it for \(\rho\).  This proves Proposition 1
hypothesis (2).

## 9. Dependency-by-dependency conclusion

```text
Stadlmann Definitions 1--3
  -> valid C10 support and q <= x^(2A1)
Polymath exact HB identity + scale facts
  -> Type 0 / (SW,SW) central / smooth three-atom trichotomy
Type 0
  -> direct bounded-variation/Poisson estimate
central, q small
  -> bilinear Bombieri--Vinogradov + audited cutoff removal
central, q near sqrt
  -> omega=0 IIa/IIb; IIc empty
central, q above sqrt
  -> fixed-omega IIa/IIb + repaired dyadic IIc
three atoms
  -> corrected Type III at omega=0 or omega
Lambda minus prime powers
  -> theta, then weighted-prime rho
PNT + positivity + prime support
  -> Proposition 1 hypotheses (1), (3), (4).
```

No Type-I estimate, Proposition 2, Harman minorant, negative
\(\omega_0\), Elliott--Halberstam hypothesis, or unweighted-prime
substitution occurs.

## 10. Independent exact checker

Run from the repository root:

```bash
python3 prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
```

It must end with

```text
C10 HOSTILE ANALYTIC EXACT PASS
```

Checker SHA-256:

```text
27c1ae65e08bdc43434b26dc078257c43aeeda115286f788ad50f2baf7d37863
  prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
```

The script imports no discovery-side module.  It reconstructs all 100
schedule entries, the HB endpoints, the modulus and prime-power exponents,
both near/above-square-root IIa and IIb open-interval constructions, the
repaired IIc distribution and packing margins, corrected Type III, and the
\(c_1,c_2,\beta\) bookkeeping using `fractions.Fraction` only.

**Final analytic verdict: `C10 ANALYTIC AUDIT PASS WITH REPAIRS`.**
