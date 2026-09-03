# Proof draft: the exact-certificate field is still pending

This is the theorem-facing argument for the frozen `k=48` candidate. At this
checkpoint the analytic implication is proved, but the ten exact mixed shards
have not all finished. Consequently the certificate hypothesis `(C)` below is
**not yet asserted**, and this file does not yet claim $H_1\le236$. Once the
aggregate and its independent replay pass, Section 5 will contain the reduced
rational certificate and this warning will be removed.

## 1. Support

Set

\[
k=48,\quad \delta={1\over60},\quad \varepsilon={3\over400},\quad
(A_0,A_1,A_2)=\left(-{3\over400},{1\over4},
{9230917\over36000000}\right).
\]

For the first band put $B_{1,m}=103/400$ for $1\le m\le60$. For the second
put

\[
\begin{split}
(B_{2,1},\ldots,B_{2,12})={}&(140375,157041,168544,174338,
185488,190375,\\
&193097,197146,202047,207090,211668,211668)/10^6,
\end{split}                                                    \tag{1}
\]

and $B_{2,m}=52917/250000$ for $13\le m\le60$. Write

\[
\alpha_1={103\over400},\qquad
\alpha_2={9500917\over36000000},\qquad
\eta={8960917\over36000000}.
\]

Apart from null boundary hyperplanes, Definition 1's support is the disjoint
union $U\mathbin{\dot\cup}V$, where

\[
U=\{t\in[0,1]^{48}:\sum_i t_i<\alpha_1\},                    \tag{2}
\]

and, with $R(t)=\#\{i:t_i>\delta\}$,

\[
V=\left\{t:\alpha_1\le\sum_i t_i<\alpha_2,
\ \sum_{i:t_i>\delta}t_i\le B_{2,R(t)}\right\}.             \tag{3}
\]

Here and below $t\in[0,1]^{48}$. We use $B_{j,0}=0$, meaning that an empty
product carries no cap. All 120 cap entries satisfy $\delta<B_{j,m}$, and
all 118 defined adjacent transitions, with $1\le m<60$, satisfy

\[
B_{j,m}\le B_{j,m+1}\le B_{j,m}+\delta.
\]

Counts $0,\ldots,12$ are the only possible outer counts, since

\[
13\delta-B_{2,13}={3749\over750000}>0.                       \tag{4}
\]

The total-band ordering reserves include

\[
A_2-A_1={230917\over36000000},\qquad
{1\over2}-\varepsilon-A_2={8499083\over36000000}>0.
\]

The independent support checker evaluates these identities and every
analytic partition case with `Fraction` arithmetic. Its checker and result
are `agents/audit/verify_truncated_lower_energy_v3_hostile_audit.py` and
`agents/audit/results/truncated_lower_energy_v3_hostile_audit.json`; canonical
hashes are in `AUDIT.md`. The distinction between strict $t_i>\delta$,
half-open total bands, and weak cap faces changes only finitely many null
hyperplanes. Every distribution inequality below has a strictly positive
rational reserve.

## 2. An unconditional prime weight

For $x\ge2$, define globally on the integers

\[
\rho(n;x)=
\begin{cases}
{\log n\over\log(3x)},& n\in\mathbb P\text{ and }x\le n\le2x,\\
0,&\text{otherwise}.
\end{cases}                                                   \tag{5}
\]

The general Harman minorant and Propositions 2 and 3 are not premises.
Clearly $0\le\rho\le1_{\mathbb P}$, so $c_2=0$. A nonzero value is
supported on a prime at least $x$, so the large-prime-factor condition holds
with $\beta=1/2>103/400$. The prime number theorem gives

\[
\sum_n\rho(n;x)={\vartheta(2x)-\vartheta(x)\over\log(3x)}+O(1)
=(1+o(1)){x\over\log x},                                   \tag{6}
\]

so $c_1=0$. The $O(1)$ allows either endpoint convention for $[x,2x]$
and for $\vartheta$.

It remains to verify Definition 3. Its asymmetric factor bounds imply for
every relevant modulus

\[
q\le x^{(1-\varepsilon_0)(A_j+A_{j'})}\le x^{2A_2},\qquad
2A_2={9230917\over18000000}<1.                              \tag{7}
\]

Write $Q^*(x)$ for the full set
$Q^*(x;\delta,A,B,\varepsilon,\varepsilon_0)$. For every fixed
$0<\varepsilon_0<1$ and $C>0$, and every integer $a$ satisfying
$(a,p)=1$ for every prime $p\le x$, the required estimate is

\[
\sum_{\substack{q\in Q^*(x)\\q\ {\rm squarefree}}}
\left|\sum_{\substack{x\le n\le2x\\n\equiv a\pmod q}}\rho(n;x)
-{1\over\phi(q)}\sum_{\substack{x\le n\le2x\\(n,q)=1}}\rho(n;x)\right|
\ll_{C,\varepsilon_0}{x\over\log^C x}.                      \tag{8}
\]

Here is the specialized unconditional proof. Apply the exact $K=10$
Heath--Brown identity and finer-than-dyadic localization of Polymath8a to
$\Lambda\,1_{[x,2x]}$, taking

\[
h=10^{-10},\quad s=h/10,\quad\sigma=1/10+s,\quad
r_0=h/10,\quad\zeta=h/1000.                                \tag{9}
\]

The combinatorial lemma puts every localized convolution into exactly one of
three classes: a long smooth atom; complementary central aggregates, the
smaller of exponent $2/5-s<\gamma\le1/2$; or three smooth atoms. The first
is summed directly, the second uses bilinear Bombieri--Vinogradov below the
square root and repaired Type IIa/IIb/IIc estimates above it, and the last
uses bilinear Bombieri--Vinogradov followed by repaired Type III. The
defective universal Baker--Irving role-swap branch in the printed paper is
not used.

For a support-band pair put
$\omega=(A_j+A_{j'}-1/2)/2$. Its only values are
$0$, $230917/72000000$, and $230917/36000000$; the first two IIc ranges
are empty. All factor allocations are certified using this sorted-factor
bound: if $n$ factors, each at least $\delta$, have total at most $B$, then
after removing the $p<n$ smallest, the next $q\le n-p$ have sum at most

\[
{q(B-p\delta)\over n-p}.                                    \tag{10}
\]

All fixed IIa/III allocations follow from (10) and the crossing-item and
cross-pool alternatives. The IIb predicates are affine in $\gamma$. Their
complete breakpoint list includes the ordinary-prefix roots

\[
\gamma=(n-r+1)K_{\rm cap}-(n-r)S-B+3\zeta+r_0,             \tag{11}
\]

where $K_{\rm cap}$ is the sum of residual capacities, $S$ is the residual
total cap, $B$ is the selected-pool cap, and $r\ge2$ is the crossing-prefix
length. Truth is constant between consecutive breakpoints. For IIc, (10) on
three consecutive blocks makes every obligation affine on a closed
$(\omega_0,\gamma)$-cell, so an adverse corner proves the entire cell.

The exact exhaustive inventory is

| case | number checked | least reserve |
|---|---:|---:|
| fixed IIa/III | 1,500 | $34448999/5000000000$ |
| complete IIb probes | 24,226 | $140008691/30000000000000$ |
| producer-omitted IIb roots added | 2,522 | all pass |
| nonempty outer IIc cells | 43,008 | $71/66000000$ |
| empty outer IIc cells | 256 | checked separately |

The smallest source-theorem reserve is the IIc factor width
$1/200000000000$. Thus this is an exact universal cell proof, not sampling.

The source repairs used in the reduction are:

1. Remove the sharp cutoff once globally using a divisor second moment in
   progressions and Cauchy--Schwarz; do not sum Polymath8a's displayed
   per-modulus boundary error naively.
2. Given target $\varepsilon_0$, choose $e_t<\varepsilon_0$, then
   $e_s=5e_t/4$, below every reserve. Monotonicity gives
   $Q^*(\varepsilon_0)\subset Q^*(e_t)$, and stripping/dyadic constants fit
   inside the separate inward reserve $r_0$.
3. The missing $N\le[d_1,d_2]^{O(1)}$ hypothesis in Polymath Corollary 4.16
   holds because the lcm contains a fixed-positive-power factor.
4. In IIc use $\delta_c=\delta+h/4$, $52e_s$, $q_1=u_1v_1$,
   $|\Lambda|$, and retain
   $\Delta^*=\min\{N/(|\Lambda|x^{5e_s}),\Delta_1\}$. The bound
   $\Delta^*\gg N/(q_0^2x^{\delta_c+55e_s}H^2)$ restores all ratio factors.
   Only the squarefree second exponential estimate is used.
5. In Type III the residual sequence is arbitrary; only the three selected
   atoms are smooth. For squarefree $q=rs=bd$, replace dense divisibility by
   $d=r/(r,b)\cdot s/(s,b)$. The printed `-5/6` is `+2/3`, giving
   $28\omega+9\gamma_3+8\delta_3<4$, with reserve $1/1250000000$.

Prime squares contribute
$O(x^{1/2}\log^3x+x^{2A_2}\log^2x)$; higher powers contribute
$O(x^{2A_2+1/3}\log^{O(1)}x)$, and

\[
1-2A_2-{1\over3}={2769083\over18000000}>0.                 \tag{12}
\]

Dividing by $\log(3x)$ proves (8). For $\varepsilon_0=1$ and $\varepsilon_0>1$,
the modulus class reduces respectively to $q=1$ and the empty set. Thus all four
Proposition-1 hypotheses hold for (5), with $c_1=c_2=0$. The line-by-line
source proof is `agents/audit/PROP1-TO-H1-ONE-BAND-AUDIT.md`.

## 3. Exact Proposition 1 used here

For symmetric $G\in L^2$, essentially supported on $U\cup V$, the
specialization just established says

\[
{48J(G)\over I(G)}>1\quad\Longrightarrow\quad H_1\le H(48). \tag{13}
\]

The audited proof corrects the printed argument as follows: use global (5)
and the empty-product convention; approximate an affinely retreated
mollification by a bounded-overlap smooth tensor partition; restore
coprimality in the main term; account for shifted endpoints; map the lcm to
fully indexed $Q^*$; and replace the printed numerator equality by

\[
(L_i+U_i)^2\rho\ge(L_i^2+2L_iU_i)\rho.                      \tag{14}
\]

The strict quotient survives retreat, mollification, and $L^2$
approximation. Marginalization is bounded because fibers have length at most
one. Equality at $d=x^\delta$ is excluded on the disjoint subsequence
$x_r=3^{60r+1}$, sufficient for a liminf.

## 4. Exact polynomials

For a partition $\lambda$, let $m_\lambda$ be the unnormalised monomial
symmetric polynomial. Put

\[
E_{a,\lambda}(t)=(1-\sum_i t_i)^a m_\lambda(t).
\]

For this certificate, define the canonical even-orbit basis $\mathcal B_D$
to contain all $(a,\lambda)$ with every part of $\lambda$ even and
$a+|\lambda|\le D$, ordered by
$(a+|\lambda|,|\lambda|,\ell(\lambda),\lambda,a)$. This is an explicit
definition of the finite basis used here. It does not silently resolve the
paper's textual discrepancy: the introduction says $2\deg(p)+b\le21$,
whereas Section 5 names $\mathcal B_{19}$, and the displayed family there
does not itself select a serialized finite basis. The present certificate
uses the literal 568 labels of $\mathcal B_{19}$ below; no degree-21
calculation is a premise.

Let $P=\sum_{\mathcal B_{19}}c_{a,\lambda}E_{a,\lambda}$, using the 568
coefficients in
`verify/results/bv_D19_krylov20_direct_exact_v2_strict.json`, and define

\[
F(t)=1_U(t)P(t).                                            \tag{15}
\]

Let $Q=\sum_{\mathcal B_{14}}d_{a,\lambda}E_{a,\lambda}$, using the 195
coefficients of `D14_grid_1e-38` in
`agents/structural-basis/results/bv_D14_fine_common_grid_candidates_exact_v2.json`.
With

\[
\gamma={\alpha_1\over\alpha_2}={9270000\over9500917},
\qquad H(t)=1_V(t)1_{R(t)\le9}Q(\gamma t),                  \tag{16}
\]

both functions are symmetric, square-integrable, and supported as required.
The stored coefficients $c_{a,\lambda}$ and $d_{a,\lambda}$ have least
common denominators $10^{87}$ and $10^{38}$, respectively. We use the
corresponding normalization scales

\[
\widehat F=10^{87}F,\qquad\widehat H=10^{38}H.              \tag{17}
\]

The second scale clears the stored coefficients of $Q$ before dilation; it
does not assert that expanding the rational substitution $Q(\gamma t)$
introduces no further denominators.

The staged exact producers and independent shard checkers expand orbit
products and distinguished-coordinate marginals and integrate the resulting
rational-polytope moments; they read no serialized matrix entry. The final
end-to-end replay is still the completion item in Section 8.

## 5. Exact finite certificate

Definition 5 uses cutoff $97/400$ for the inner-inner term and literal
$\eta=8960917/36000000$ for inner-outer and outer-outer terms. Set

\[
I=I(\widehat F),\quad D=I(\widehat F)-48J(\widehat F),\quad
A=I(\widehat H),\quad b=48J(\widehat F,\widehat H).          \tag{18}
\]

The inner reconstruction proves $I>0$ and gives an exact positive rational
$D/I$ in `verify/results/bv_D19_krylov20_direct_exact_v2_strict.json`; its
decimal expansion begins

\[
{D\over I}=0.01320691630439124434132928981396553791\ldots>0. \tag{19}
\]

The outer norm is the exact sum of $R=0,\ldots,9$. In a mixed marginal let
$r=R(u)$ count the large shared coordinates. An outer distinguished
coordinate $t\le\delta$ leaves the total count equal to $r$, whereas
$t>\delta$ makes it $r+1$. Thus common counts $r=0,\ldots,8$ retain the two
small-fiber branches `Sdelta`, `Stotal` and the two large-fiber branches
`Ltotal`, `Lbig`; at $r=9$ only `Sdelta` and `Stotal` remain; and $r\ge10$
vanishes. This is the exact fiberwise consequence of $R(t)\le9$, not an
estimate. The faces $t=\delta$ are null and use the small-side convention
from Definition 1.

The pending aggregate must prove

\[
A>0,\qquad b^2-AD>0.                                       \tag{C}
\]

The ten $b$-strata are not all complete at this checkpoint, so no values
are inserted here and `(C)` is not claimed.

## 6. Scalar certificate implies the quotient

Polarize $J$ by
$J(X,Y)=(J(X+Y)-J(X)-J(Y))/2$. For
$u=(t_1,\ldots,t_{47})$, define the distinguished-coordinate marginals

\[
M_X(u)=\int_0^\infty X(u,t)\,dt.
\]

Literal Definition 5 then gives

\[
J(F,H)=\int_{\sum u_i\le\eta}M_F(u)M_H(u)\,du.              \tag{20}
\]

Since $H$ lies in exactly one outer band,

\[
J(H)=\int_{\sum u_i\le\eta}M_H(u)^2\,du\ge0.               \tag{21}
\]

This need not hold for a union of outer bands; retaining one band is
essential. Since $U,V$ are disjoint a.e.,
$I(\widehat F+c\widehat H)=I+c^2A$. Taking $c=b/A$,

\[
\begin{aligned}
48J(\widehat F+c\widehat H)-I(\widehat F+c\widehat H)
&=-D+2cb+c^2(48J(\widehat H)-A)\\
&\ge-D+2cb-c^2A={b^2-AD\over A}>0.                         \tag{22}
\end{aligned}
\]

Thus an explicit lower bound is

\[
{48J(\widehat F+c\widehat H)\over I(\widehat F+c\widehat H)}
\ge1+{b^2-AD\over AI+b^2}>1.                               \tag{23}
\]

No matrix invertibility or positive-definiteness assumption is used.

## 7. Diameter-236 tuple

Use

```text
0,6,8,14,18,24,26,48,50,54,56,60,66,68,74,78,
80,84,90,96,98,104,110,116,120,126,134,138,144,150,158,164,
168,176,180,186,188,194,200,204,206,210,216,224,228,230,234,236
```

It has 48 distinct entries and diameter 236. For primes at most 48, missing
residues are

```text
q:       2  3  5  7 11 13 17 19 23 29 31 37 41 43 47
missing: 1  1  2  2  9 10  4 13 13 15  1  7 10  2  5
```

For $q>48$, 48 residues cannot cover all $q$ classes. Hence the tuple is
admissible and $H(48)\le236$. Once `(C)` is proved, (13) and (23) give two
primes in translates of this tuple for arbitrarily large $x_r$, hence a
consecutive-prime gap at most 236 and $H_1\le236$.

## 8. Reproduction contract

The final command will be recorded only after the compact certificate exists.
It must reconstruct the support audit, tuple, inner forms, all thirteen outer
norm strata, and all ten nonzero mixed strata; recompute `(C)` and (23) using
exact rationals; read no serialized matrix entries; bind every source and data
file by SHA-256; and pass under normal and optimized Python. Until then this
is a proof draft, not a theorem proof.
