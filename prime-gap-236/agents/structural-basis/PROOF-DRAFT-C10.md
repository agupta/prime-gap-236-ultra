# C10 analytic proof draft and conditional $H_1\leq236$ implication

## Status

This is a proof draft, not a theorem announcement.  It proves the analytic
part of the C10 route: all four hypotheses of Stadlmann's Proposition 1 for
the support and weighted-prime minorant below.  It then isolates the one
remaining finite-dimensional assertion as **`[CERT-C10-48]`**.  The final
implication to $H_1\leq236$ is valid only after that named assertion has
been reconstructed exactly and has received an independent certificate
audit.

The route is the specialized direct Heath--Brown route.  It does **not** use
the paper's Proposition 2, its universal Proposition 3, the defective
high-$\gamma$ Type-I role swap, or a nonzero-$c_2$ functional $K$.  The
parameter application has verdict **C10 ANALYTIC AUDIT PASS WITH REPAIRS** in
[the hostile audit](../hostile-analytic-audit/C10-AUDIT.md). Its two
parameter/partition repairs are summarized in
[the repair addendum](../hostile-analytic-audit/c10-analytic-repair-addendum.md).
The predecessor arguments behind the Type-II/III estimates have the separate,
restricted verdict **C10 DEEP-DISTRIBUTION AUDIT PASS WITH MANDATORY
REPAIRS** in
[the deep audit](C10-DEEP-DISTRIBUTION-AUDIT.md). Those source-level repairs
are incorporated explicitly in Sections 6--7 below; the proof does not cite
the affected 2026 statements verbatim.

## Pinned local sources

Line references in this draft are to the following local files.

| source | role | SHA-256 |
|---|---|---|
| [Stadlmann 2026 TeX](../../sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex) | Definitions 1--3 and 5, Proposition 1, Type-II/III and partition lemmas | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| [Polymath8a TeX](../../sources/polymath8-edz-1402.0811-src/newergap.tex) | bilinear Bombieri--Vinogradov, Heath--Brown identity, scale trichotomy and coefficient facts | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| [Stadlmann 2023 TeX](../../sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex) | repaired Type-IIc $q$-van der Corput and exponential-sum chain | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| [Baker--Irving TeX](../../sources/baker-irving-1505.01815-src/primegaps_paper.tex) | comparison showing why the unused role-swapped Type-I statement needs an extra SW hypothesis | `743ca0053146471648040fa1224f2177258221ded4927f8c9fe3221c35b6702e` |
| [BFI 2019 correction note](../../sources/bfi-corrections-1903.01371.pdf) | confirms that the corrections to the 1986 paper do not affect any theorem statement; identifies the corrected material as Lemma 1 and Sections 9--11 | `63b3515b99088d3670d31266e42e96937dc1253c7425da68831aab343608f1d4` |
| [C10 hostile audit](../hostile-analytic-audit/C10-AUDIT.md) | independent parameter and boundary audit | `7df85a8ca8b6ea3ab9246e018efd759e6ddf76200f895a141f2ff089da15ccc3` |
| [C10 repair addendum](../hostile-analytic-audit/c10-analytic-repair-addendum.md) | corrected IIb endpoint and IIc open-window repair | `2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7` |
| [C10 deep-distribution audit](C10-DEEP-DISTRIBUTION-AUDIT.md) | line-by-line predecessor audit and source-level repairs for the specialized C10 uses | `f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd` |
| [Proposition-1 $c_2=0$ audit](PROP1-C2ZERO-AUDIT.md) | line-by-line proof audit and mandatory repairs | `050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb` |
| [48-tuple](../../sources/admissible_48_236.txt) | admissible tuple of diameter 236 | `adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9` |

The source/version manifest is [sources.md](../../sources.md).  Stadlmann's
support, relevant-modulus and equidistribution definitions are at TeX lines
140--184; the key integrals and Proposition 1 are at lines 210--242.  The
Section 3 estimates used below are at lines 532--669, and the factorization
lemmas are at lines 1239--1391.  The corresponding Polymath8a anchors are
lines 1043--1049, 1305--1395, 1421--1589, 1637--1737 and 1780--1863.

## 1. The exact C10 support

Take $k=48$, one support stratum, and

\[
 \varepsilon_s=\frac1{200},\qquad
 \delta=\frac1{100},\qquad
 (A_0,A_1)=\left(-\frac1{200},\frac{77747}{300000}\right),
\]

\[
 B_1=B_2=\frac3{20},\qquad
 B_m=\frac{97}{625}\quad(3\leq m\leq100).
\]

Here $\varepsilon_s$ is the support enlargement; it is not the
relevant-modulus shrink or a small parameter in a distribution theorem.  The
same exact data are recorded in
[c10-support.json](../independent-attack/c10-support.json).

For $t=(t_1,\ldots,t_{48})$, put

\[
 L(t)=\{i:t_i>1/100\},\qquad m(t)=|L(t)|.
\]

With the vacuous convention $B_0=0$, Definition 1 specializes to

\[
 T=T_{48}(\delta,A,B,\varepsilon_s)
 =\left\{t\in[0,1]^{48}:
 0\leq\sum_i t_i<\frac{79247}{300000},\quad
 \sum_{i\in L(t)}t_i\leq B_{m(t)}
 \right\}.                                      \tag{1}
\]

The $B_0$ convention means only that the empty sum imposes no restriction.
It repairs the notational omission in Definition 2, which quantifies over
$m=0$ although the displayed $B$-matrix starts at $m=1$.

All Definition-1 conditions hold with exact margins

\[
 A_1-A_0=\frac{79247}{300000},\qquad
 \frac12-\varepsilon_s-A_1=\frac{70753}{300000},
\]

\[
 B_1-\delta=B_2-\delta=\frac7{50},\qquad
 B_3-B_2=\frac{13}{2500},\qquad
 B_2+\delta-B_3=\frac3{625}.
\]

For $3\leq m<100$, $B_{m+1}=B_m$, which is permitted by the weak
monotonic inequality and leaves upper increment slack $\delta$.  Moreover

\[
 15\delta=\frac3{20}\leq\frac{97}{625}
 <\frac4{25}=16\delta.
\]

Thus a closed tuple of large-factor exponents can have at most 15 entries:
if $m\geq16$, its sum is at least $16\delta>B_m$.  This verifies the
whole schedule through $m=100=\lfloor1/\delta\rfloor$, not merely the
nonempty prefix.  These checks are independently reconstructed in
[C10-AUDIT.md, lines 70--112](../hostile-analytic-audit/C10-AUDIT.md).

### Boundary conventions

The following conventions are used literally.

- The total-sum interval in (1) is half open: its lower endpoint is included
  and its upper endpoint is excluded, exactly as in Definition 1 (Stadlmann
  TeX lines 140--147).
- A coordinate is "large" only when $t_i>\delta$, while the corresponding
  $B_m$ inequality is weak.  On the distribution side, Definition 2 has
  factor exponents at least $\delta$.  We therefore prove the partition
  statements on the larger closed polytopes $y_i\geq\delta$; this safely
  includes all support-boundary cases.
- Replacing any of these codimension-one faces by the opposite convention
  does not change $I$ or $J$, but the exact integrator is nevertheless
  required to implement the displayed conventions and may not use this
  measure-zero observation to change a positive-volume cell.
- Since there is one stratum, the common-coordinate cutoff in Definition 5's
  $J$ is exactly
  
  \[
  \eta=A_1-\varepsilon_s=\frac{76247}{300000},                 \tag{2}
  \]
  
  with a weak inequality.  The total endpoint used for each completed
  48-tuple is
  
  \[
  \alpha=A_1+\varepsilon_s=\frac{79247}{300000}.              \tag{3}
  \]
- Every factor interval supplied to a distribution lemma is open.  Below it
  is replaced by a strictly interior closed interval with a stated positive
  reserve; no endpoint equality is silently promoted to an admissible
  factor.

## 2. Proposition 1 and the minorant

Stadlmann's Proposition 1 (TeX lines 228--242) requires the following four
properties of a function $\rho(n;x)$ and constants $c_1,c_2$.

1. $-c_2\leq\rho(n;x)\leq1_{\mathbb P}(n)$ on $[x,2x]$ for all
   sufficiently large $x$.
2. $\rho$ satisfies Definition 3's equidistribution estimate for every
   fixed relevant-modulus shrink $\varepsilon_0>0$, every logarithmic
   saving, and every residue representative coprime to all primes at most
   $x$.
3. On the nonzero support of $\rho$, every prime factor exceeds
   $x^\beta$ for some $\beta>\max_j B_{j,1}$.
4. $\sum_{x\leq n\leq2x}\rho(n;x)=(1-c_1+o(1))x/\log x$.

Define, for $x\leq n\leq2x$,

\[
 \rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n),            \tag{4}
\]

and put it equal to zero outside that interval.  Take

\[
 c_1=c_2=0,\qquad \beta=\frac12.                              \tag{5}
\]

### Hypotheses (1), (3), and (4)

For $x\leq n\leq2x$,

\[
 0\leq\frac{\log n}{\log(3x)}<1,
\]

so $0=-c_2\leq\rho\leq1_{\mathbb P}$.  If $\rho(n;x)\ne0$, then
$n$ is a prime at least $x$, hence its only prime factor is greater than
$x^{1/2}$.  Also

\[
 \beta-B_1=\frac12-\frac3{20}=\frac7{20}>0.
\]

This proves hypotheses (1) and (3).  The prime number theorem gives

\[
 \sum_{x\leq n\leq2x}\rho(n;x)
 =\frac{\vartheta(2x)-\vartheta(x)}{\log(3x)}
 =(1+o(1))\frac{x}{\log x},                                   \tag{6}
\]

which is hypothesis (4) with $c_1=0$.  Notice that (6) is the density of
the actual weighted minorant (4); the proof never substitutes the
unweighted prime indicator.  The hostile reconstruction of these three
hypotheses is at
[C10-AUDIT.md, lines 114--141](../hostile-analytic-audit/C10-AUDIT.md).

It remains to prove hypothesis (2).

## 3. Size of every relevant modulus

Let $Q^*(x;\varepsilon_0)$ be the set in Definition 2 for (1).  For
$0<\varepsilon_0<1$, its two defining total-product inequalities give

\[
 q\leq x^{(1-\varepsilon_0)\bigl((A_1-\varepsilon_s)
                              +(A_1+\varepsilon_s)\bigr)}
 \leq x^{2A_1}.                                                \tag{7}
\]

The support enlargement cancels exactly.  Put

\[
 \omega=A_1-\frac14=\frac{2747}{300000},\qquad
 Q=x^{2A_1}=x^{77747/150000}=x^{1/2+2\omega}.                 \tag{8}
\]

If $\varepsilon_0=1$, only $q=1$ can remain and its discrepancy is
zero.  If $\varepsilon_0>1$, the nonnegative logarithms in Definition 2
cannot satisfy a negative upper bound, apart from the same vacuous $q=1$
case.  Thus (7)--(8) cover every $\varepsilon_0>0$.  This point, including
the three ranges of $\varepsilon_0$, is audited at
[C10-AUDIT.md, lines 143--178](../hostile-analytic-audit/C10-AUDIT.md).

For an arithmetic function $f$, write

\[
 \Delta_q(f;a)=
 \sum_{\substack{x\leq n\leq2x\\n\equiv a\pmod q}}f(n;x)
 -\frac1{\phi(q)}
  \sum_{\substack{x\leq n\leq2x\\(n,q)=1}}f(n;x).
\]

We will prove, for every fixed $C>0$,

\[
 \sum_{\substack{q\in Q^*(x;\varepsilon_0)\\q\ {\rm squarefree}}}
 |\Delta_q(\rho;a)|
 \ll_{C,\varepsilon_0}\frac{x}{\log^C x}.                    \tag{9}
\]

## 4. Exact Heath--Brown reduction

Set

\[
 h=10^{-10},\qquad s=h/10,\qquad \sigma=1/10+s.               \tag{10}
\]

Use the exact $K=10$ Heath--Brown identity for $\Lambda$ on
$[x,2x]$, followed by Polymath8a's finer-than-dyadic partition.  The
identity and partition are in the Polymath8a TeX at lines 1421--1589.  There
are only $\log^{O(1)}x$ resulting convolutions, so this loss can be
absorbed by demanding a stronger logarithmic saving in each distribution
estimate.

For every resulting scale tuple, Polymath8a's Facts lemma (lines
1637--1737) says that:

- each sub-convolution is a coefficient sequence at its product scale;
- an atom of scale at least $x^{2\sigma}$ is smooth;
- every sub-convolution at a fixed positive-power scale is
  Siegel--Walfisz;
- the product of all atomic scales is comparable with $x$.

The outer indicator $1_{[x,2x]}$ is kept throughout.  The strict
combinatorial hypotheses are

\[
 \sigma-1/10=\frac1{100000000000}>0,
 \qquad
 2\sigma-1/10=\frac{5000000001}{50000000000}>0.               \tag{11}
\]

Consequently the combinatorial lemma at Polymath8a lines 1305--1395 places
every term into at least one of the following alternatives.

1. **Type 0:** one smooth atom has exponent at least
   $1/2+\sigma$; the complementary convolution has exponent at most
   $1/2-\sigma$.
2. **Central aggregate:** two complementary Siegel--Walfisz aggregates
   have exponents in $(1/2-\sigma,1/2+\sigma)$.  Orienting the smaller
   one as the second factor gives
   
   \[
   2/5-s<\gamma\leq1/2.                                      \tag{12}
   \]
3. **Three atoms:** there are three smooth atoms with individual exponents
   in $[2\sigma,1/2-\sigma]$ and every pair has exponent at least
   $1/2+\sigma$.

This is a trichotomy for the actual Heath--Brown pieces, not an assertion
about every sequence in the paper's broad Harman class.  In particular it
never produces the arbitrary-factor Type-I branch whose proof is defective.
The independent C10 reconstruction is at
[C10-AUDIT.md, lines 180--231](../hostile-analytic-audit/C10-AUDIT.md).

## 5. Type 0

Fix the variables of the complementary convolution.  The long atom is
smooth on the intersection of its scale support with the resulting sharp
interval and has total variation $\log^{O(1)}x$.  Poisson summation (or
summation by parts followed by the same argument) gives discrepancy
$\tau(q)^{O(1)}\log^{O(1)}x$ for this one-variable sequence.  The
complement has $\ell^1$-norm

\[
 \ll x^{1/2-\sigma}\log^{O(1)}x.
\]

Enlarging the modulus set to all $q\leq Q$ and using the standard average
bound for a fixed divisor power gives

\[
 \sum_{q\leq Q}|\Delta_q(\text{Type 0};a)|
 \ll x^{(1/2-\sigma)+2A_1}\log^{O(1)}x.
\]

The saving from exponent one is exactly

\[
 1-\{(1/2-\sigma)+2A_1\}
 =\frac{24506000003}{300000000000}>0.                         \tag{13}
\]

This case therefore contributes $O_C(x\log^{-C}x)$ for every fixed
$C$.  It requires neither a factorization of $q$ nor a Type-I theorem.
The primary model is Polymath8a lines 1780--1863; the sharp-interval C10
version is audited at
[C10-AUDIT.md, lines 233--254](../hostile-analytic-audit/C10-AUDIT.md).

## 6. The central aggregate: Type II only

The smaller factor in (12) is Siegel--Walfisz and lies, with strict reserve,
in the closed range

\[
 2/5-h\leq\gamma\leq1/2,
 \qquad (2/5-s)-(2/5-h)=9/10^{11}.                             \tag{14}
\]

We split the moduli exhaustively.

### 6.1 Small moduli

For

\[
 q\leq x^{1/2}\log^{-L}x,
\]

apply the bilinear Bombieri--Vinogradov theorem at Polymath8a lines
1043--1049.  Its second factor is exactly the Siegel--Walfisz aggregate in
(14), and its scale is a fixed positive power of $x$.

The printed theorem is for a full localized convolution.  Polymath's
finer-than-dyadic cutoff removal (lines 1559--1627), supplemented by the
divisor-moment/Cauchy--Schwarz calculation in
[the deep audit, Section 4](C10-DEEP-DISTRIBUTION-AUDIT.md),
shows that the two boundary intervals of total length
$O(x\log^{-R}x)$ contribute

\[
 \ll x\log^{-R/2+O(1)}x
\]

after summing over the moduli.  Choosing $R$ after $C$ proves the sharp
$[x,2x]$ version used here.
Indeed the source's displayed estimate at Polymath8a line 1578 is only
per modulus and cannot itself be summed. On a boundary set of length
$H\ll x\log^{-R}x$, the divisor second moment in a progression and
Cauchy--Schwarz give $\ll (x/q)\log^{-R/2+O(1)}x$; summing
$\tau(q)^{O(1)}/q$ costs only $\log^{O(1)}x$. This single global
calculation is made before applying any full-convolution Type-II/III
estimate.

### 6.2 The near-square-root strip

For

\[
 x^{1/2}\log^{-L}x<q\leq x^{1/2},
\]

use the 2026 Type-II lemmas with upper parameter $\omega_*=0$.  This
strip is above the fixed $x^{1/2-\varepsilon_1}$ threshold in the
partition lemmas when $x$ is large.  The IIc range is empty, with exact
gap

\[
 \frac{12999999907}{300000000000}>0.                          \tag{15}
\]

Thus only IIa and IIb occur.

### 6.3 The range above the square root

For

\[
 x^{1/2}<q\leq x^{1/2+2\omega},
\]

use the IIa and IIb lemmas with the fixed upper parameter $\omega$.
For IIc, split into modulus blocks
$q\asymp x^{1/2+2\omega_0}$, where
$0\leq\omega_0\leq\omega$.  The block endpoint changes the exponent by
$O(1/\log x)$, which is eventually smaller than the fixed inward reserves
below.  This uses no negative-$\omega_0$ endpoint.

### 6.3a Target and source small parameters

The source proofs strip primes at most $D_0$ and replace factors by dyadic
lower endpoints. Their combined exponent cost is $o(1)$, so one may not use
the same small parameter on both sides of an exact open endpoint. Given the
fixed Definition-3 shrink $\varepsilon_0>0$, choose $e_{\rm t}$ with

\[
 0<e_{\rm t}\leq\varepsilon_0,\qquad
 e_{\rm s}=\frac54e_{\rm t},
\]

and, more restrictively,

\[
 e_{\rm t}<\frac45
 \min\{h/1000,10^{-100}\delta_c,e_{\rm margin}\}.        \tag{15a}
\]

Here $e_{\rm margin}>0$ is the minimum of the finitely many rational
reserves in (18)--(32) and the repaired exponent reserves below. For large
$x$, small-prime stripping and dyadic constants cost at most
$x^{e_{\rm t}/4}$. Replacing $e_{\rm t}$ by $e_{\rm s}$ moves every
coefficient-$3$, coefficient-$6$, or coefficient-$52$ endpoint by at most
$3e_{\rm t}/4$, $3e_{\rm t}/2$, or $13e_{\rm t}$, respectively. Each
is smaller than the certified inward reserve $r_0=h/10$, even after the
additional $e_{\rm t}/4$ loss. Thus every target factor lands strictly
inside the corresponding source-lemma window. Since
$Q^*(x;\varepsilon_0)\subseteq Q^*(x;e_{\rm t})$, proving the larger
class proves the requested one. From now on the Section-3 source parameter
is $e=e_{\rm s}$.

### 6.4 IIa and IIb, with open endpoints treated correctly

For $\omega_*\in\{0,\omega\}$, put

\[
 G_a=\frac25+\frac{24}{5}\omega_*+\frac75\delta+2h,
 \qquad
 d_a(\gamma)=\frac57\gamma-\frac27-
              \frac{24}{7}\omega_*-h,                       \tag{16}
\]

\[
 G_b=\frac13+8\omega_*+\frac73\delta+3h,
 \qquad
 d_b(\gamma)=\frac37\gamma-\frac17-
              \frac{24}{7}\omega_*-h.                       \tag{17}
\]

IIa treats $G_a\leq\gamma\leq1/2$.  Move both endpoints of its open
factor interval inward by

\[
 r_0=h/10.
\]

At the worst endpoint the remaining width beyond the support increment is

\[
 d_a(G_a)-2r_0-\delta=\frac1{43750000000}>0.                  \tag{18}
\]

Put every large support-coordinate exponent in the first partition bin.
Since the total load is at most $2B=194/625$, the exact worst first-bin
margins are

\[
 \frac{1036000001897}{10000000000000}\quad(\omega_*=0),
 \qquad
 \frac{1475520001897}{10000000000000}\quad(\omega_*=\omega), \tag{19}
\]

and the unused second capacity is positive.

IIb treats $G_b\leq\gamma\leq G_a$.  Shrinking each of its two open
factor intervals by $r_0$ leaves

\[
 d_b(G_b)-2r_0-\delta=\frac3{350000000000}>0.                 \tag{20}
\]

Again put the full load in bin 1.  Its exact worst margins are

\[
 \frac{1388000008691}{30000000000000}\quad(\omega_*=0),
 \qquad
 \frac{1195200002897}{10000000000000}\quad(\omega_*=\omega). \tag{21}
\]

All unused capacities are positive.  In particular, the third capacity is
increasing in $\gamma$, so its uniform lower bound must be evaluated at
the **lower**, not upper, IIb endpoint.  The corrected minima are

\[
 \frac{350000001}{35000000000}\quad(\omega_*=0),
 \qquad
 \frac{2972900003}{105000000000}\quad(\omega_*=\omega),       \tag{22}
\]

both strictly positive.  Equations (18)--(22) are the first mandatory
repair; see
[the addendum, lines 7--25](../hostile-analytic-audit/c10-analytic-repair-addendum.md).
They verify every factor-width and partition-capacity hypothesis of the IIa
and IIb lemmas (Stadlmann TeX lines 572--608 and 1248--1335).

For clarity, the predecessor estimates impose more than these partition
conditions. Polymath8a lines 4187--4207 give the two IIa power conditions

\[
 24\omega_*+7\delta-5\gamma<-2,\qquad
 8\omega_*+3\delta-\gamma<0,                               \tag{22a}
\]

while the IIb calculation at lines 4635--4779 gives

\[
 24\omega_*+7\delta-3\gamma<-1,\qquad
 8\omega_*+3\delta-\gamma<0.                              \tag{22b}
\]

The definitions (16)--(17) and the reserves above verify (22a)--(22b)
uniformly; the remaining IIb term contains an explicit favorable $-6e$.
The second estimate in Polymath8a Corollary 4.16 also assumes
$N\leq[d_1,d_2]^{O(1)}$, a condition omitted by the 2026 restatement.
In every nonempty C10 application the lcm contains
$r\geq x^{\gamma-\delta-O(e)}$, whose exponent has a fixed positive
lower bound, so a fixed power of $r$ exceeds $N=x^\gamma$. Finally, the
smooth $\psi_N$ used there is inserted after Cauchy--Schwarz; the original
central factor need only have the Siegel--Walfisz property supplied by the
Facts lemma. These checks are [Sections 6 and 6.1 of the deep
audit](C10-DEEP-DISTRIBUTION-AUDIT.md).

### 6.5 Repaired IIc and the complete continuum partition

IIc needs genuine width left after its open factor windows are shrunk.  Use

\[
 \delta_c=\delta+4h=\frac{25000001}{2500000000},
 \qquad \zeta=e_{\rm s}=\frac54e_{\rm t}<h/1000,
 \qquad r_0=h/10.                                             \tag{23}
\]

Here $\zeta$ is the small parameter in the Section 3 distribution
lemma.  Start with each of the three open IIc factor windows at width
$\delta_c$, and feed the closed intervals
$[a_i+r_0,b_i-r_0]$ to partition Lemma 13.  Each resulting width is

\[
 \delta_c-2r_0
 =\delta+\frac{19}{50000000000}>\delta.                       \tag{24}
\]

Uniformly on

\[
 2/5-h\leq\gamma\leq
 \frac13+8\omega+\frac73\delta+3h,
 \qquad 0\leq\omega_0\leq\omega,
\]

the three strict distribution margins are

\[
 \frac{403599967}{15000000000},\qquad
 \frac{209599877}{30000000000},\qquad
 \frac{1199983}{2500000000}.                                 \tag{25}
\]

These three numbers also survive the actual predecessor calculation, but
only after repairing Stadlmann 2026 lines 963--1035. Line 967's $100e$
must be $52e$, as in the lemma statement and the definition of
$\mathcal R$; line 987's final factor is $v_1$, not $v_2$; and the revised
scale $D\asymp q_0^{-2}N/H^2$ now depends on $q_0$. Every positive scale
uses $|\Lambda|$. In particular, retain the 2023 definition

\[
 \Delta^*=\min\left\{\frac{N}{|\Lambda|x^{5e}},\Delta_1\right\},
 \qquad
 L_\Delta=\frac{N}{q_0^2x^{\delta_c+55e}H^2}.              \tag{25a}
\]

The printed assertion $\Delta^*=\Delta_1$ is false: the permitted extreme
scales can make their ratio $\asymp x^{45e-\delta_c}\to0$. The actual
bounds

\[
 |\Lambda|\ll\frac{q_0x^{\delta_c+5e}H^2}{w_1g},\qquad
 \frac{N}{q_0^2x^{\delta_c+55e}H^2}\ll\Delta_1
 \ll\frac{N}{q_0^2x^{55e}H^2}
\]

give instead $\Delta^*,\Delta_1\gg L_\Delta$. Keeping every
$\Delta^*/\Delta_1$ factor from Stadlmann 2023 lines 1648--1721 reduces
the second and third terminal estimates to

\[
 \frac{x^{\delta_c+131e}}{q_0^2\Delta^*}
 \max\{q_0^2x^{\delta_c+10e}H^5,H^6\}\ll1,              \tag{25b}
\]

\[
 \frac{x^{1+2\delta_c+131e}}
      {q_0N^2\Delta^*\Delta_1}
 \max\{q_0^2x^{\delta_c+10e}H^7,H^8\}\ll1.              \tag{25c}
\]

Using $H\ll x^{4\omega+\delta_c+7e}/q_0$, the two branches of
(25b) are bounded by

\[
 q_0^{-5}x^{28\omega+10\delta_c+245e-\gamma},\qquad
 q_0^{-8}x^{32\omega+10\delta_c+242e-\gamma},
\]

and the two branches of (25c) by

\[
 q_0^{-6}x^{1+44\omega+16\delta_c+328e-4\gamma},\qquad
 q_0^{-9}x^{1+48\omega+16\delta_c+325e-4\gamma}.          \tag{25d}
\]

Thus every $q_0$-power is favorable, and (25) together with (15a) makes
all four exponents strictly negative. The first terminal inequality
cancels $\Delta^*/\Delta_1$ and follows from
$8\omega+4\delta_c+2\gamma<1$ with the same reserve.

The last exponential estimate in this chain is needed only in its second
Polymath8a form. Its proof at Polymath8a 8710--8743 uses squarefreeness
and polynomial size, not dense divisibility; the latter first appears in
the unused first bound. Stadlmann 2023's congruence reduction likewise
uses only the coprime factorization of squarefree $m$. Hence the new C10
modulus satisfies the exact input even though it need not divide
$P(x^{\delta_c})$. The complete downstream-use table, including every
Taylor, Möbius, gcd, and congruence step, is in
[Sections 7.3--7.6 of the deep audit](C10-DEEP-DISTRIBUTION-AUDIT.md).

The proof-start face and the three potentially critical inward endpoints
have margins

\[
 \frac{2120239997}{6000000000},\quad
 \frac{3899999995097}{10000000000000},\quad
 \frac{626499989641}{15000000000000},\quad
 \frac{7007999971}{100000000000}.                             \tag{26}
\]

Partition Lemma 13 therefore supplies the following uniform lower
capacities:

\[
 \begin{aligned}
 C_1&=\frac{4601199986563}{15000000000000},&
 C_2&=\frac{776499995341}{15000000000000},\\
 C_3&=\frac{25000001}{2500000000},&
 C_4&=\frac1{50000000000}.
 \end{aligned}                                                \tag{27}
\]

It remains to cover every point of every continuous
$\Xi(B_m,B_{m'},m,m',\delta)$, not merely samples or vertices.  Write
$B=97/625$, $B_{\rm small}=3/20$, let $T_y$ be the total load, and
put $L=\max(0,T_y-C_1)$.  The following six exact margins are positive:

\[
 \begin{gathered}
 C_1-B=\frac{2273199986563}{15000000000000},\qquad
 C_1-2B_{\rm small}=\frac{101199986563}{15000000000000},\\
 \delta-(B_{\rm small}+B-C_1)
 =\frac{173199986563}{15000000000000},\\
 C_2-B/3=\frac{499995341}{15000000000000},\\
 2\delta-(2B-C_1)=\frac{245199986563}{15000000000000},\\
 C_2-2(2B-C_1)=\frac{222299989489}{5000000000000}.
 \end{gathered}                                                \tag{28}
\]

They give a complete partition as follows.

- If one count is zero, then $T_y\leq B<C_1$.
- If both counts are at most two, then
  $T_y\leq2B_{\rm small}<C_1$.
- If exactly one count is at most two, then $L<\delta$.  The least entry
  in the count-at-least-three group lies in
  $[\delta,B/3]\subset(L,C_2)$; place it in bin 2.
- If both counts are at least three, take the least entry from each group.
  If either one is at least $L$, place it alone in bin 2.  Otherwise their
  sum is at least $2\delta>L$ and is less than
  $2L\leq2(2B-C_1)<C_2$; place the pair in bin 2.

All remaining entries have load at most $C_1$ and go in bin 1; bins 3 and
4 are empty.  The tuple $(m,m')=(0,0)$ uses four empty bins.  Counts 16
through 100 are empty by Section 1.  Hence all count pairs and every point of
each closed polytope are covered.

Equations (23)--(28) are the second mandatory repair; see
[the addendum, lines 27--83](../hostile-analytic-audit/c10-analytic-repair-addendum.md)
and the full derivation at
[C10-AUDIT.md, lines 397--506](../hostile-analytic-audit/C10-AUDIT.md).
They establish IIc without the paper's impossible negative-$\omega_0$
branch.

Sections 6.1--6.5 therefore give (9) for every central-aggregate term.

## 7. The three-atom alternative: corrected Type III

Put

\[
 \gamma_3=\frac12-\sigma=\frac25-s,
\]

and, for $\omega_*\in\{0,\omega\}$, put

\[
 \delta_3(\omega_*)
 =\frac12-\frac72\omega_*-\frac98\gamma_3-h.                  \tag{29}
\]

The three smooth atoms delivered by the combinatorial lemma satisfy the
scale hypotheses of Stadlmann's Type-III lemma (TeX lines 653--669):

\[
 N_i\gg x^{1-2\gamma_3},\qquad
 N_i\ll x^{\gamma_3},\qquad
 N_iN_j\gg x^{1-\gamma_3}\quad(i\ne j).
\]

Polymath8a Definition 2.6 requires smoothness only for these three
distinguished atoms; the residual coefficient sequence $\alpha$ is
arbitrary. Its theorem restatement at line 6872 accidentally calls
$\alpha$ smooth, but the proof from line 7173 onward never uses that
adjective. The two dense-divisibility uses in the primary proof are exactly
at lines 7345--7347 and 7469--7479. If the C10 squarefree modulus is
$q=rs=bd$, then

\[
 d=\frac{r}{(r,b)}\frac{s}{(s,b)}.
\]

The fixed-factor interval gives the first factor in
$(S/(bx^{\delta_3}),S)$, with
$S=x^{1/3+4\delta_3/3-4\omega_*/3}$; this supplies both primary
factorizations, and no later line uses dense divisibility.

The 2026 line 1082 constant $-5/6$ must be $+2/3$, as in its own lines
1077 and 1088. The corrected three terminal inequalities are

\[
\begin{aligned}
 28\omega_*+9\gamma_3+8\delta_3&<4,\\
 16\omega_*+9\gamma_3+2\delta_3&<4,\\
 28\omega_*+9\gamma_3-\delta_3&<4.
\end{aligned}                                                \tag{29a}
\]

The first implies the other two for the present nonnegative parameters.
Its strict distribution margin is

\[
 4-(28\omega_*+9\gamma_3+8\delta_3)=8h
 =\frac1{1250000000}>0.                                      \tag{30}
\]

The source estimate spends $6e_{\rm s}$ in exponent; (15a) makes this
strictly smaller than the normalized reserve $1/15000000000$. The
auxiliary requirements $1\le S\le x^{\delta_3}Q/2$ reduce to
$4\omega_*-4\delta_3<1$ and $2\delta_3-8\omega_*<1$ and have the
positive endpoint margins recorded in
[Section 8.2 of the deep audit](C10-DEEP-DISTRIBUTION-AUDIT.md).

Shrink both endpoints of the open Type-III factor interval inward by $h$.
The widths that remain beyond the support increment are

\[
 \frac{31999999769}{800000000000}\quad(\omega_*=0),
 \qquad
 \frac{19083999307}{2400000000000}\quad(\omega_*=\omega).     \tag{31}
\]

Putting all support-coordinate loads in the first partition bin gives the
following first-bin margins over $2B$, followed by the unused second-bin
capacities:

\[
 \begin{array}{c|cc}
 \omega_* & C_1-2B & C_2\\ \hline
 0&\dfrac{53759999869}{600000000000}
  &\dfrac{359999999831}{2400000000000}\\[4pt]
 \omega&\dfrac{20795999869}{600000000000}
  &\dfrac{138313333277}{800000000000}.
 \end{array}                                                   \tag{32}
\]

All quantities in (31)--(32) are strictly positive, so partition Lemma 11
places the factor strictly inside the Type-III interval.  Small moduli are
handled by bilinear Bombieri--Vinogradov after grouping two smooth atoms and
the residual sequence on one side and using the third smooth atom, which is
Siegel--Walfisz and has positive-power scale, on the other.  The
near-square-root strip uses $\omega_*=0$; the above-square-root range uses
$\omega_*=\omega$.  Thus every three-atom term satisfies (9).  The repaired
argument and all endpoint margins are independently checked at
[C10-AUDIT.md, lines 508--564](../hostile-analytic-audit/C10-AUDIT.md).
The Baker--Irving Type-I lemma at Stadlmann 2026 lines 611--629 is not an
input: its middle branch swaps an arbitrary non-SW coefficient into the SW
slot. The direct C10 trichotomy has already assigned every term to Type 0,
SW Type II, or the repaired Type III above.

## 8. Removing prime powers

The preceding three cases prove (9), with arbitrary logarithmic saving, for
$\Lambda1_{[x,2x]}$.  Write

\[
 \vartheta(n)=\log n\,1_{\mathbb P}(n),\qquad
 PP(n)=\Lambda(n)-\vartheta(n).
\]

For squares and squarefree $q$, a fixed primitive residue has at most
$2^{\omega(q)}$ square roots.  Summing first over root classes gives

\[
 \sum_{q\leq Q}
 \sum_{\substack{x\leq p^2\leq2x\\p^2\equiv a\pmod q}}\log p
 \ll x^{1/2}\log^3x+Q\log^2x.                                \tag{33}
\]

For powers $p^r$ with $r\geq3$, the deliberately crude bound of at most
$Q$ possible moduli per prime power gives

\[
 \ll Qx^{1/3}\log x
 =x^{127747/150000}\log x,                                   \tag{34}
\]

and

\[
 1-\frac{127747}{150000}=\frac{22253}{150000}>0.              \tag{35}
\]

For the coprimality-average part, the total prime-power mass is
$O(x^{1/2}\log x)$ and
$\sum_{q\leq Q}1/\phi(q)\ll\log Q$.  Equations (33)--(35) are therefore
power-saving even after enlarging from $Q^*$ to every $q\leq Q$,
uniformly in the primitive residue.  Hence (9) holds for $\vartheta$.
Dividing by the constant $\log(3x)$ proves it for $\rho$ in (4).
This is Proposition 1 hypothesis (2).  See
[C10-AUDIT.md, lines 566--604](../hostile-analytic-audit/C10-AUDIT.md)
for the independent reconstruction.

Combining Sections 2 and 8 proves all four hypotheses of Proposition 1 with
the exact choices (1), (4), and (5).

The application uses the audited $c_1=c_2=0$ specialization, not the
printed proof without qualification.  The line-by-line
[Proposition-1 audit](PROP1-C2ZERO-AUDIT.md) repairs its variable indices,
uses the global truncation already built into (4), reduces the shifted
interval back to Definition 3 using the strict bound $q\leq x^{2A_1}<x$,
restores the coprimality subtraction for a general rough minorant, replaces
the uncontrolled differentiated tensor localization by direct local
tensorization of the smooth integrand, changes the claimed numerator
equality to the required lower bound, and makes denominator positivity
explicit.  For (4), the coprimality correction is even simpler: a prime
$m\asymp x$ cannot divide $q\leq x^{2A_1}=o(x)$.

## 9. Exact analytic verification commands

The hostile checker imports no discovery-side module and uses
`fractions.Fraction` throughout:

```bash
python3 prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
```

It must end with

```text
C10 HOSTILE ANALYTIC EXACT PASS
```

The checker SHA-256 is

```text
27c1ae65e08bdc43434b26dc078257c43aeeda115286f788ad50f2baf7d37863
```

The discovery-side closed-form and rational-box checks remain useful
cross-checks:

```bash
cd prime-gap-236/agents/independent-attack
python3 verify_c10_prop1.py
python3 verify_c10_box.py
```

Their expected final lines are, respectively,

```text
C10 PROP1 EXACT MARGINS PASS
DIRECT-HB EXACT SUPPORT COVER PASS pairs 135 nodes 2565
```

The hostile check, rather than the unrepaired discovery dossier, is the
normative parameter verification.

## 10. Named finite-dimensional placeholder `[CERT-C10-48]`

For a partition $\lambda$ with no part 1, let $P_\lambda(t)$ be the sum
of the distinct monomials obtained by permuting $\lambda$, padded with
zeros, among 48 variables.  Let

\[
 \mathcal B_{12}^{\rm no1}
 =\left\{(1-\textstyle\sum_i t_i)^aP_\lambda(t):
          a+|\lambda|\leq12,\ \lambda_i\geq2\right\};
\]

this is the explicit 272-element candidate basis.  The current integer-scaled
candidate vector is
[hb_c10_fullsimplex_noones_D12_integer_scaled.json](../exact-integrator/results/hb_c10_fullsimplex_noones_D12_integer_scaled.json).
It was discovered on the full simplex; that discovery quotient is not the
C10 capped quotient and is not evidence for the sign required here.

Let $P$ be the resulting symmetric polynomial.  The unmodified function
$P1_T$ has already been reconstructed on the actual caps and has quotient
$0.9709698476\ldots<1$; it is therefore not the certificate candidate.  Two
subsequent discovery transfers are also negative: the D4-optimal affine
stratum multiplier gives the nonrigorous D12 quotient
$0.9671692127\ldots$, and the D4-optimal quadratic multiplier gives
$0.9555961622\ldots$.  These values are falsification data, not upper bounds
for their full D12 multiplier spaces, but neither vector may be substituted
for the missing certificate.

The finite search must instead output a completely explicit rational
piecewise-polynomial $F_\star$.  Its machine-readable description must fix
the global symmetric orbit basis, every rational coefficient, all stratum or
support-cell indicators, every local polynomial channel, and all boundary
conventions.  From those data alone the final checker must establish that

\[
 F_\star(t)=0\quad(t\notin T),\qquad
 F_\star(t_{\sigma(1)},\ldots,t_{\sigma(48)})=F_\star(t)
                                                               \tag{35}
\]

for every permutation $\sigma$, apart from immaterial choices on finitely
many cell-boundary hyperplanes.  A finite piecewise polynomial on the bounded
measurable set $T$, extended by zero, is square-integrable.  Multiplying all
of its rational coefficients by one common nonzero factor scales both $I$
and $J$ by the same positive square and does not change (36).  The remaining
assertion is:

> **`[CERT-C10-48]`.** A cache-free exact reconstruction from the explicit
> machine-readable definition of $F_\star$ first verifies (35), and then
> verifies
> 
> \[
> D:=I(F_\star;\delta,A,B,\varepsilon_s)>0
> \]
> 
> and
> 
> \[
> N:=48J(F_\star;\delta,A,B,\varepsilon_s)
>       -I(F_\star;\delta,A,B,\varepsilon_s)>0.
>                                                               \tag{36}
> \]
> 
> The reconstruction must implement (1)--(3), print $D,J,N$ exactly, and
> fail closed on incomplete or malformed input.  A checker independent of
> the discovery cache must reproduce the positive sign.

No value or sign for $N$ is asserted in this draft.  Scalar inequalities
in (36) are sufficient: neither $M_1$ nor $M_2$ is assumed invertible or
positive definite.  Since $c_1=c_2=0$, the malformed printed definition of
$K$ is multiplied by zero and is not used.  Under `[CERT-C10-48]`, (36)
is exactly

\[
 \frac{48J(F_\star)}{I(F_\star)}>1,                           \tag{37}
\]

the specialized Proposition 1 criterion.  The matrix identity behind this
reduction is in the primary TeX at lines 1754--1772.

## 11. The admissible 48-tuple and the conditional final implication

The local tuple is

\[
\begin{aligned}
\mathcal H=\{&0,6,8,14,18,24,26,48,50,54,56,60,66,68,74,78,\\
&80,84,90,96,98,104,110,116,120,126,134,138,144,150,158,164,\\
&168,176,180,186,188,194,200,204,206,210,216,224,228,230,234,236\}.
\end{aligned}
\]

It contains 48 distinct integers and has diameter $236-0=236$.  For each
prime $q\leq48$, the following residue is absent from
$\mathcal H\pmod q$:

\[
\begin{array}{c|rrrrrrrrrrrrrrr}
q&2&3&5&7&11&13&17&19&23&29&31&37&41&43&47\\ \hline
\text{missing residue}&1&1&2&2&9&10&4&13&13&15&1&7&10&2&5.
\end{array}                                                    \tag{38}
\]

If $q>48$, a set of 48 integers occupies at most 48 residue classes, fewer
than all $q$ classes.  Thus (38) proves admissibility for every prime
$q$.  This is checked directly by
[check_tuple.py](../../verify/check_tuple.py), whose mathematical stopping
criterion is explained at lines 42--50:

```bash
python3 prime-gap-236/verify/check_tuple.py
```

It prints

```text
PASS size=48 min=0 max=236 diameter=236
missing_residue_witnesses=2:1 3:1 5:2 7:2 11:9 13:10 17:4 19:13 23:13 29:15 31:1 37:7 41:10 43:2 47:5
```

Consequently $H(48)\leq236$.  If `[CERT-C10-48]` is established, Sections
2--8 supply every hypothesis of Proposition 1 and (37) supplies its strict
integral inequality.  The repaired $c_2=0$ form of Proposition 1, audited
line by line in [PROP1-C2ZERO-AUDIT.md](PROP1-C2ZERO-AUDIT.md), then gives

\[
 H_1\leq H(48)\leq236.                                       \tag{39}
\]

Equation (39) is a conditional implication in the present draft.  It must
not be promoted to a theorem until `[CERT-C10-48]` and the final independent
audit pass are present.

## 12. Statements still needing a source citation or independent audit

This list is intended to be exhaustive for this draft.

### Blocking certificate and audit work

1. **The sign in `[CERT-C10-48]`.**  This is the only deliberately missing
   mathematical assertion in the displayed implication.  The capped C10
   values of $I$, $J$, and $48J-I$ have not been inserted here.  They
   need exact reconstruction and a separately implemented adversarial
   checker.
2. **Final certificate-to-function identity.**  The final checker must verify
   every basis label, rational coefficient, stratum/cell assignment, local
   channel, and boundary convention in the eventual $F_\star$ description;
   verify that any integer rescaling uses only nonzero common factors; and
   reconstruct the integrals without trusting a full-simplex moment or a
   serialized matrix entry.  Existing input and grouped-algorithm audits do
   not establish the final C10 sign.
3. **Final end-to-end audit.**  After a positive sign is obtained, an auditor
   independent of the discovery and grouped-evaluator authors must check the
   exact support parameters, $k=48$ factors, $J$-cutoff (2), tuple, and
   Proposition-1 implication together.  The current C10 audit explicitly
   excluded the finite quotient and tuple.

### Audited cited inputs (nonblocking)

The following are cited proved lemmas, so they are legitimate primary
inputs rather than unproved gaps or certificate placeholders. The separate
Proposition-1 $c_2=0$ and deep-distribution audits are complete and pinned
above; their repairs are incorporated into Sections 2, 6--8 and 11.

4. **The deep Type-IIa, Type-IIb, Type-IIc, and Type-III distribution
   estimates.** They are cited at Stadlmann TeX lines 572--669, with the
   mandatory source corrections displayed in Sections 6--7. The deep audit
   traces the specialized C10 uses line by line through Polymath8a and
   Stadlmann 2023, checks coefficient, SW, smoothness, squarefree-modulus,
   dyadic-uniformity, and sharp-interval hypotheses, and isolates the unused
   Baker--Irving defect. Its restricted verdict is PASS WITH MANDATORY
   REPAIRS; no verbatim appeal to the false $\Delta^*=\Delta_1$ line is
   permitted.
5. **Sharp-interval bilinear Bombieri--Vinogradov.**  Polymath8a Theorem 2.9
   is cited, and Sections 4 and 6.1 include the local cutoff-removal argument.
   The primary theorem in turn cites Bombieri--Friedlander--Iwaniec Theorem
   0.  Its indexed primary statement was checked against the Polymath8a
   formulation on 2026-09-02.  The pinned 2019 correction note says that no
   theorem statement in the 1986 paper changes, and its corrections concern
   Lemma 1 and Sections 9--11 rather than Theorem 0's Section-2 large-sieve
   proof.  The 1986 scan itself could not be archived locally because the
   publisher served an access page and the advertised archival PDF returned
   HTTP 500; `sources.md` records that acquisition failure explicitly.
6. **Standard analytic estimates.**  The prime number theorem,
   $\sum_{q\leq Q}1/\phi(q)\ll\log Q$, divisor-power averages, and the
   square-root count used in (33) are standard but presently have no explicit
   bibliography entry in this draft.  They need conventional citations in a
   publication-ready proof, or short self-contained lemmas where practical.

### Small independent checks still advisable

7. **Tuple implementation independence.**  Formula (38) is a direct finite
   proof and the current checker is fail-closed, but its unit test imports the
   same verifier.  A second tiny implementation, or a line-by-line human
   audit of the listed witnesses, should be included in the final adversarial
   audit.
8. **Version pin at release.**  The argument is pinned to arXiv:2608.31126v1.
   Before a final proof is released, repeat the one-time version check and
   either retain these hashes or audit any later source changes.  This is a
   provenance requirement, not a current mathematical gap.

The defects in universal Proposition 3, the high-$\gamma$ Type-I lemma,
Proposition 2, and Definition 5's $K$ are not items to repair for this
route: the proof above bypasses them.  Reintroducing any of those components
would require a new analytic audit.
