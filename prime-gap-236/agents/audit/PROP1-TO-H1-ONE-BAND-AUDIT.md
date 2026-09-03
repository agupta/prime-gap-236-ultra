# Proposition 1 to \(H_1\leq236\): one-band analytic audit

Date: 2026-09-03 (Europe/Berlin)

## Verdict

**FULL-THEOREM VERDICT: NOT `AUDIT PASS`.  CONDITIONAL ANALYTIC
IMPLICATION: PASS.**

For the source bytes and the frozen two-stratum support pinned below, the
analytic chain is complete and unconditional after the explicit source
repairs recorded here.  More precisely, the following is proved.

> **Conditional one-band implication.**  Suppose an exact, independently
> reconstructible certificate supplies real symmetric functions \(F,H\),
> with \(F\) supported on the inner stratum and nonzero \(H\) supported on
> the sole outer stratum, and proves, with literal Definition-5 cutoffs,
> \[
> A=I(H)>0,\qquad b=48J(F,H),\qquad
> D=I(F)-48J(F),\qquad b^2-AD>0.                 \tag{CERT}
> \]
> Then the repaired \(c_1=c_2=0\) specialization of Stadlmann's Proposition
> 1 applies to \(F_{\rm tot}=F+(b/A)H\), and the supplied admissible
> 48-tuple proves \(H_1\leq236\).

No exact instance of `(CERT)` was supplied to or assumed by this audit.
Monte Carlo projection estimates, a floating generalized eigenvalue, and an
exact computation of the inner quotient alone do not establish `(CERT)`.
Thus the sole theorem-strength blocker is:

```text
[ONE-BAND-EXACT-CERT]
Give exact definitions of F and H and an independent checker which
reconstructs A, b, D and proves A>0 and b^2-AD>0.
```

There is no remaining support, equidistribution, Proposition-1, boundary,
or tuple blocker for this conditional implication.  This deliberately is
not the unqualified string `AUDIT PASS`, because without
`[ONE-BAND-EXACT-CERT]` the theorem has not been proved.

## Audited bytes and independent replay

| item | SHA-256 |
|---|---|
| Stadlmann 2026 TeX | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| Polymath8a TeX | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| Polymath8b TeX | `c8d4f06ad222273ee8b192059ee358e4eecb677dfe35839badb5b3fe292fd05d` |
| Stadlmann 2023 TeX | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| BFI correction note | `63b3515b99088d3670d31266e42e96937dc1253c7425da68831aab343608f1d4` |
| project paper map | `8c61aa6b49b0836dfecace511a3da1a938a8c40a4593ba7aefe67dbbcb8e2e4c` |
| frozen one-band result | `c9be4426ece4cc50063ee64ccae72d26c66af5296d7312b2fb9ac0192ba30c9f` |
| independent hostile support checker | `b4e889ab47690fb8619342267e4259dab5b31882ef5a25b9015957d4e210394b` |
| independent hostile support result | `fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1` |
| Proposition-1 \(c_2=0\) audit | `050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb` |
| deep distribution audit | `f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd` |
| independent Riesz-shell audit | `6dc822f29b1d4af1738e4e7b523282711eecbd35fefd75a486b44eaa5f3e3e5e` |
| tuple data | `adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9` |
| independent tuple verifier | `645d3e61f587f9f961b3c72037a0f4499ac29c85c64be601b6b14e6a4b898f78` |

I read the pinned 1,885-line Stadlmann TeX from beginning to end.  The
analytic dependency used here ends at Proposition 1 plus the Section-3
distribution estimates and partition machinery.  Proposition 2, Proposition
3 as a black box, the Section-5 finite matrix calculation, and the published
\(k=49\) computation are not premises.

I also reran the independent hostile support checker from scratch.  It
finished in 85.80 seconds at 23,600 KiB RSS and produced SHA-256
`fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1`,
byte-identical to the frozen hostile result.  In particular, this replay is
not merely a parse of the producer JSON.

## 1. Literal Definition-1 support

Freeze

\[
k=48,\qquad \delta=\frac1{60},\qquad
\varepsilon=\frac3{400},
\]
\[
A_0=-\frac3{400},\qquad A_1=\frac14,\qquad
A_2=\frac{9230917}{36000000}.
\]

For the inner stratum put

\[
B_{1,m}=\frac{103}{400}\qquad(1\leq m\leq60).
\]

For the outer stratum, the first twelve entries are

\[
\begin{split}
(B_{2,1},\ldots,B_{2,12})={}&
(140375,157041,168544,174338,185488,190375,\\
&193097,197146,202047,207090,211668,211668)/10^6,
\end{split}                                                    \tag{1}
\]

and \(B_{2,m}=211668/10^6=52917/250000\) for \(13\leq m\leq60\).
This supplies every column required by
\(\lfloor1/\delta\rfloor=60\), not only the active prefix.

The exact ordering margins are

\[
A_1-A_0=\frac{103}{400},\qquad
A_2-A_1=\frac{230917}{36000000},\qquad
\frac12-\varepsilon-A_2=\frac{8499083}{36000000}.
\]

Every cap satisfies the literal non-strict chain

\[
\delta<B_{j,m}\leq B_{j,m+1}\leq B_{j,m}+\delta.
\]

The independent checker evaluates all 120 entries and all 118 transitions.
The least Definition-1 reserve is

\[
13\delta-B_{2,13}=\frac{3749}{750000}>0.       \tag{2}
\]

For the inner schedule, counts \(0,\ldots,15\) are possible and count 16
is empty, with reserve \(16\delta-B_{1,16}=11/1200\).  For the outer
schedule, counts \(0,\ldots,12\) are possible and (2) makes count 13 and
all higher counts empty.  These statements are proved on the enlarged
closed set in which every coordinate classified as large is at least
\(\delta\); hence they remain valid for Definition 1's strict condition
\(t_i>\delta\).

Write

\[
\alpha_1=A_1+\varepsilon=\frac{103}{400},\qquad
\alpha_2=A_2+\varepsilon=\frac{9500917}{36000000}.
\]

Up to null boundaries, the support is the disjoint union \(T=U\dot\cup V\),
where

\[
U=\{t\in[0,1]^{48}:0\leq\textstyle\sum_i t_i<\alpha_1\},             \tag{3}
\]

and

\[
V=\left\{t\in[0,1]^{48}:\alpha_1\leq\sum_i t_i<\alpha_2,
\ \sum_{i:t_i>\delta}t_i\leq B_{2,|\{i:t_i>\delta\}|}\right\}.       \tag{4}
\]

The inner cap is redundant in (3), since every subset sum is below the
total.  Both sets are invariant under coordinate permutations.

### Boundary convention

Definition 1 makes the total bands left-closed and right-open, uses weak cap
faces, and defines a large coordinate by \(t_i>\delta\).  Definition 5
prints closed total intervals and a weak cutoff.  The discrepancies lie in
a finite union of hyperplanes

\[
\sum t_i=\alpha_j,\qquad t_i=\delta,\qquad
\sum_{i\in S}t_i=B_{j,|S|},
\]

and therefore have Lebesgue measure zero.  Exact integration may use either
representative, but support membership is always interpreted as essential
support in the literal half-open \(T\).  This does not turn a weak source
inequality into a strict one: every distribution-theorem inequality below
has its own positive rational reserve.

## 2. Relevant moduli and the direct prime weight

Definition 2 takes \(m,m'=0\) although it does not define a zeroth cap.
The only coherent convention, used here, is

\[
B_{j,0}=0,
\]

equivalently: omit the cap inequality for an empty product.

For every \(q\in Q^*(x;\delta,A,B,\varepsilon,\varepsilon_0)\), the two
asymmetric total-factor bounds in Definition 2 give

\[
q\leq x^{(1-\varepsilon_0)(A_j-\varepsilon+A_{j'}+\varepsilon)}
   =x^{(1-\varepsilon_0)(A_j+A_{j'})}
   \leq x^{2A_2}.                                      \tag{5}
\]

Thus the support-enlargement \(\varepsilon\) cancels, rather than costing
an extra \(2\varepsilon\).  The worst exponent is

\[
2A_2=\frac{9230917}{18000000}<1,\qquad
1-2A_2=\frac{8769083}{18000000}>0.                    \tag{6}
\]

If \(\varepsilon_0=1\), only \(q=1\) can remain and its discrepancy is
zero.  If \(\varepsilon_0>1\), the class is empty because
\(A_j-\varepsilon>0\) and a nonnegative logarithm cannot obey its negative
upper bound.  It remains to prove Definition-3 equidistribution for each
fixed \(0<\varepsilon_0<1\).

Use the globally truncated weight

\[
\rho(n;x)=\frac{\log n}{\log(3x)}\,1_{\mathbb P}(n)\,1_{[x,2x]}(n).
                                                               \tag{7}
\]

The final indicator is important: the proof of Proposition 1 evaluates
\(\rho(n+h_i;x)\), sometimes outside \([x,2x]\).  With (7), nonnegativity
and the prime-minorant inequality are global.

### Proposition-1 hypotheses (1), (3), and (4)

For every integer \(n\),

\[
0\leq\rho(n;x)\leq1_{\mathbb P}(n),
\]

so hypothesis (1) holds with \(c_2=0\).  If \(\rho(n;x)\ne0\), then \(n\)
is prime and \(n\geq x>x^{1/2}\).  Since

\[
\max_j B_{j,1}=B_{1,1}=\frac{103}{400},\qquad
\frac12-\frac{103}{400}=\frac{97}{400}>0,
\]

hypothesis (3) holds with \(\beta=1/2\).  Finally, the prime number theorem
gives

\[
\sum_{x\leq n\leq2x}\rho(n;x)
=\frac{\vartheta(2x)-\vartheta(x)}{\log(3x)}
=(1+o(1))\frac{x}{\log x},                              \tag{8}
\]

which is hypothesis (4) with \(c_1=0\).  This is the mass of the actual
weighted minorant (7), not of the unweighted prime indicator.

### Hypothesis (2): unconditional direct Heath--Brown proof

The required statement is, for every fixed \(C>0\), every fixed
\(\varepsilon_0>0\), and every integer \(a\) coprime to every prime at most
\(x\),

\[
\sum_{\substack{q\in Q^*(x;\delta,A,B,\varepsilon,\varepsilon_0)\\
q\ \mathrm{squarefree}}}
\left|\sum_{\substack{x\leq n\leq2x\\n\equiv a\pmod q}}\rho(n;x)
-\frac1{\phi(q)}\sum_{\substack{x\leq n\leq2x\\(n,q)=1}}\rho(n;x)
\right|\ll_{C,\varepsilon_0}\frac{x}{\log^C x}.          \tag{9}
\]

Here is the complete specialized reduction.

1. Apply the exact \(K=10\) Heath--Brown identity from Polymath8a and its
   finer-than-dyadic localization to \(\Lambda1_{[x,2x]}\).  Put
   \[
   h=10^{-10},\quad s=h/10,\quad\sigma=1/10+s,\quad
   r_0=h/10,
   \]
   and choose the Section-3 source parameter \(\zeta=h/1000\).
   The strict endpoint \(\sigma>1/10\) is therefore not replaced by
   equality.  The Facts lemma supplies coefficient bounds, location,
   smoothness of sufficiently long atoms, and Siegel--Walfisz for every
   positive-power sub-convolution.

2. The Polymath combinatorial lemma exhausts every localized term by exactly
   one of: a long smooth atom (Type 0); two complementary central aggregates,
   the smaller of which has exponent \(2/5-s<\gamma\leq1/2\); or three
   smooth atoms.  There is no fourth case.  The long branch is summed
   directly, the central branch uses bilinear Bombieri--Vinogradov below the
   square root and the repaired IIa/IIb/IIc estimates above it, and the
   three-atom branch uses bilinear Bombieri--Vinogradov followed by the
   repaired Type III estimate.  The defective Baker--Irving Type-I role swap
   in the printed 2026 proof is never invoked.

3. For a band pair \((j,j')\), put
   \[
   \omega=\frac{A_j+A_{j'}-1/2}{2}.
   \]
   The only values are
   \[
   0,\qquad \frac{230917}{72000000},\qquad
   \frac{230917}{36000000}.                              \tag{10}
   \]
   The first two IIc ranges are empty.  The outer/outer IIc range is handled
   uniformly in its dyadic \(\omega_0\)- and \(\gamma\)-parameters.

4. The cap/factor partition is universal, not sampled.  For a pool of
   \(n\) sorted factors of total at most \(B\), after \(p\) smallest factors
   have been removed, the next \(q\) have sum at most
   \[
   \frac{q(B-p\delta)}{n-p}.                              \tag{11}
   \]
   Together with the crossing-item and cross-pool alternatives, (11)
   proves every fixed IIa/III allocation.  For IIb the selected third bin
   and residual two-bin predicates are affine in \(\gamma\).  Besides the
   producer's roots, the hostile checker inserts every ordinary-prefix root.
   Here \(K=C(\gamma)+D(\gamma)\) is the sum of the two residual bin
   capacities, \(S\) is the residual total cap, \(B\) is the cap of the
   selected pool, and \(r\geq2\) is the crossing-prefix length.  The root is
   \[
   C_{\rm root}=(n-r+1)K-(n-r)S-B,\qquad
   \gamma=C_{\rm root}+3\zeta+r_0.                       \tag{12}
   \]
   Predicate truth is constant between consecutive roots, so checking both
   endpoints and one interior rational point proves the whole continuum.
   For IIc, three consecutive sorted blocks obey (11); on each closed
   \((\omega_0,\gamma)\)-cell the checker uses the adverse affine corner for
   every capacity.  Hence a cell certificate covers every real point in the
   cell.

5. The exact finite inventory is:

   | family | exhaustive inventory | least reserve |
   |---|---:|---:|
   | main ordered nonempty pairs | 582 | included below |
   | near ordered nonempty pairs | 168 | included below |
   | fixed IIa/III checks | 1,500 | `34448999/5000000000` |
   | completed IIb endpoint/interval probes | 24,226 | `140008691/30000000000000` |
   | producer-omitted IIb roots added | 2,522 | all pass |
   | outer IIc nonempty cells | 43,008 | `71/66000000` |
   | outer IIc empty-tuple cells | 256 | checked separately |

   Eighteen cases falsify the old one-prefix proof; 283 fixed cases select
   the enhanced action.  In IIc, 6,081 cells require the three-block action.
   These are not silently declared routine.

6. All source-theorem faces are strict.  The most useful exact reserves are

   | obligation | exact least reserve |
   |---|---:|
   | direct-HB main face \(3(A_2-A_1)+\delta<3/80\) | `6361/4000000` |
   | IIa first exponent face | `7/10000000000` |
   | IIa factor-width excess | `1/43750000000` |
   | IIb first exponent face | `7/10000000000` |
   | IIb factor-width excess | `3/350000000000` |
   | Type III main exponent face | `1/1250000000` |
   | outer IIc factor-width excess | `1/200000000000` |
   | outer IIc distribution face 1 | `3144979937/90000000000` |
   | outer IIc distribution face 2 | `5053279937/180000000000` |
   | outer IIc distribution face 3 | `31804999/1250000000` |
   | outer IIc proof-start face | `25752663991/72000000000` |
   | worst direct-II scalar face | `7951249/5000000000` |
   | worst higher-prime-power exponent | `2769083/18000000` |

   The global least source reserve is the positive IIc width
   `1/200000000000`.  Monotonicity reduces the non-IIc
   \(\omega_0\)-continuum to its adverse endpoints; the IIb
   \(\gamma\)-continuum and the two-dimensional IIc continuum are covered as
   in (12) and the adverse-cell argument.

7. The following source repairs are part of the proof, not optional errata.

   - The sharp cutoff is removed once globally.  Its boundary sequence is
     supported on intervals of total length
     \(O(x\log^{-R}x)\).  The divisor second moment in a progression and
     Cauchy--Schwarz give
     \(O((x/q)\log^{-R/2+O(1)}x)\); summing the divisor weight over \(q\)
     costs only powers of \(\log x\).  The per-modulus display at Polymath8a
     line 1578 is not summed naively.
   - The target small parameter and the source-lemma parameter are distinct.
     Given \(0<\varepsilon_0<1\), choose \(0<e_t<\varepsilon_0\);
     monotonicity of every Definition-2 upper bound gives
     \(Q^*(\varepsilon_0)\subseteq Q^*(e_t)\).  Then choose
     \(e_s=5e_t/4\), with \(e_t\) also smaller than every fixed rational
     reserve.  Small-prime
     stripping and dyadic constants cost at most \(x^{e_t/4}\).  Coefficients
     3, 6, and 52 move an open endpoint by less than the certified inward
     reserve \(r_0\).  This proves every endpoint inclusion rather than
     identifying two different epsilons.
   - The omitted Polymath Corollary-4.16 hypothesis
     \(N\leq[d_1,d_2]^{O(1)}\) holds because the lcm contains
     \(r\geq x^{\gamma-\delta-O(e_s)}\), a fixed positive power.
   - In IIc, put \(\delta_c=\delta+h/4\), use \(52e\),
     \(q_1=u_1v_1\), and \(|\Lambda|\).  Retain
     \[
     \Delta^*=\min\{N/(|\Lambda|x^{5e_s}),\Delta_1\},
     \]
     rather than the false printed equality \(\Delta^*=\Delta_1\).  The
     common lower bound
     \[
     \Delta^*\gg
     \frac{N}{q_0^2x^{\delta_c+55e_s}H^2}
     \]
     (Here \(H\) is the IIc factor scale in the source, not the outer
     function used in Section 4.)
     restores all \(\Delta^*/\Delta_1\) factors and yields exactly the
     three checked IIc faces.  Every discarded \(q_0\)-power is favorable.
     The required second exponential estimate uses squarefreeness and
     polynomial size; dense divisibility appears only in the unused first
     estimate.
   - In Type III the residual \(\alpha\) is an arbitrary coefficient
     sequence; only the three distinguished atoms are smooth.  The two
     dense-divisibility uses are replaced, for squarefree \(q=rs=bd\), by
     \[
     d=\frac r{(r,b)}\frac s{(s,b)}.
     \]
     The printed `-5/6` is `+2/3`; the corrected principal inequality is
     \(28\omega+9\gamma_3+8\delta_3<4\), with reserve
     \(1/1250000000\).

8. Start with \(\Lambda\), then subtract prime powers.  For squares, a
   primitive class modulo squarefree \(q\) has at most \(2^{\omega(q)}\)
   square roots, giving
   \[
   O\bigl(x^{1/2}\log^3x+x^{2A_2}\log^2x\bigr).
   \]
   Powers of exponent at least three contribute
   \[
   O\bigl(x^{2A_2+1/3}\log^{O(1)}x\bigr),
   \]
   and
   \[
   1-2A_2-\frac13=\frac{2769083}{18000000}>0.            \tag{13}
   \]
   The coprime-average part costs only
   \(\sum_{q\leq Q}1/\phi(q)\ll\log Q\).  Dividing the resulting
   \(\vartheta\)-estimate by \(\log(3x)\) proves (9).

This proves Proposition-1 hypothesis (2) for (7).  It invokes neither the
general Harman minorant nor Proposition 2.  In particular, the unused
\((\xi_1,\xi_2,\xi_3)\) fields in a discovery artifact are not premises of
this proof, and no negative \(K\)-term has been dropped: \(c_2=0\) follows
directly from (7).

## 3. The repaired Proposition-1 application

The printed proof of Proposition 1 is not safe verbatim.  In the present
nonnegative specialization the following repairs give a complete proof.

1. Use the globally truncated (7).
2. Use the empty-product convention \(B_{j,0}=0\).
3. After the affine retreat and mollification, approximate the resulting
   smooth compactly supported function directly by a bounded-overlap smooth
   tensor partition of unity.  If \(\psi_Q\) is subordinate to small boxes
   and \(z_Q\in Q\), then
   \[
   G_h(t)=\sum_QF(z_Q)\psi_Q(t),\qquad
   \sum_Q|F(z_Q)|\psi_Q(t)\leq\|F\|_\infty.              \tag{14}
   \]
   Uniform convergence gives \(L^2\) convergence and convergence of every
   one-coordinate marginal.  The absolute-sum bound in (14) makes the
   discarded threshold strips \(O(h_{\rm mesh})\); small overlap measure is
   not used without this bound.  Downward closure follows from
   \(B_{j,m}\leq B_{j,m+1}\leq B_{j,m}+\delta\).
4. Correct the printed variable indices, delete the dummy distinguished
   divisor sums, and use \(f_{j,l,i}(0)f_{j',l',i}(0)\), not the fixed
   \(k\)-th coordinate.
5. In the main term retain the coprimality condition.  Here it disappears
   exactly for large \(x\): a nonzero (7) is a prime at least \(x\), whereas
   (6) gives \(q=o(x)\), so it cannot share a prime factor with \(q\).
6. A shift from \([x,2x]\) to \([x+h_i,2x+h_i]\) changes each progression
   and average by \(O_{\mathcal H}(1)\).  By (6), summing over all relevant
   moduli is a power saving.
7. Map the lcm modulus to the fully indexed \(Q^*\), use \(d>x^\delta\)
   for a large divisor, and absorb \(W=x^{o(1)}\) by replacing the shrink by
   a slightly smaller one.
8. If the local sieve expression is \(L_i+U_i\), then
   \[
   (L_i+U_i)^2\rho\geq(L_i^2+2L_iU_i)\rho                 \tag{15}
   \]
   because \(U_i^2\rho\geq0\).  The numerator statement is the lower bound
   (15), not the false equality printed at line 508.
9. Preserve a fixed positive quotient margin through approximation.  The
   denominator main term has positive leading constant before division.

The half-open and cap boundaries described after (4) are null.  A strict
quotient survives the affine retreat, mollification, and (14) by continuity
of translation in \(L^2\) and boundedness of the marginal operator.  Thus a
piecewise-polynomial exact certificate is a legitimate symmetric \(L^2\)
input even though Proposition 1 constructs smooth sieve weights internally.

There is one convenient way to eliminate the equality
\(d=x^\delta\) without changing any theorem.  Work along

\[
x_r=3^{60r+1}.
\]

Then \(x_r^{1/60}=3^{r+1/60}\notin\mathbb N\), and the ranges
\([x_r,2x_r]\) are disjoint.  The uniform asymptotics remain valid on this
subsequence, which is sufficient for a liminf assertion.  No conjectural
distribution hypothesis is introduced.

## 4. Literal Definition 5 and the one-band Riesz step

The three relevant Definition-5 cutoffs are

\[
\eta_{11}=A_1-\varepsilon=\frac{97}{400},
\]
\[
\eta_{12}=\eta_{21}=\eta_{22}=A_2-\varepsilon
=\frac{8960917}{36000000}.                              \tag{16}
\]

The mixed cutoff in (16) is the literal
\(\max(A_1-\varepsilon,A_2-\varepsilon)\).  It is not an untruncated
fiber integral.

Polarize Definition 5 by

\[
J(P,Q)=\frac{J(P+Q)-J(P)-J(Q)}2.
\]

For symmetric \(F\) supported on \(U\) and symmetric \(H\) supported on
\(V\), define their distinguished-coordinate marginals, with the functions
extended by zero off their supports, by

\[
M_F(u)=\int_0^\infty F(u,t)\,dt,\qquad
M_H(u)=\int_0^\infty H(u,t)\,dt,
\quad u=(t_1,\ldots,t_{47}).
\]

The fibers have length at most one, so Cauchy--Schwarz gives
\(\|M_F\|_2^2\leq I(F)\) and \(\|M_H\|_2^2\leq I(H)\).  Thus every
bilinear integral below is finite.  Moreover \(F+cH\) is symmetric,
square-integrable, and essentially supported on \(U\cup V=T\).

Then literal Definition 5 gives

\[
J(F,H)=\int_{\sum u_i\leq\eta_{12}}M_F(u)M_H(u)\,du.      \tag{17}
\]

The two ordered band terms are equal and polarization turns their sum into
the single integral (17).  Proposition 1 multiplies this one-coordinate
form by \(k=48\), so

\[
b=48J(F,H),                                               \tag{18}
\]

with no second factor of 48.

Because \(V\) is exactly one band,

\[
J(H)=\int_{\sum u_i\leq\eta_{22}}M_H(u)^2\,du\geq0.       \tag{19}
\]

This is false in general for a union of two outer bands: the intervening
kernel can have matrix \(\left(\begin{smallmatrix}0&1\\1&1\end{smallmatrix}\right)\),
of determinant \(-1\).  Deleting the other outer bands is therefore an
essential hypothesis, not a cosmetic simplification.

Let \(A,b,D\) be as in `(CERT)` and set \(c=b/A\).  The supports (3)--(4)
are disjoint almost everywhere, hence

\[
I(F+cH)=I(F)+c^2A.                                        \tag{20}
\]

By polarization, (18), and (19),

\[
\begin{aligned}
48J(F+cH)-I(F+cH)
 &=-D+2cb+c^2(48J(H)-A)\\
 &\geq-D+2cb-c^2A\\
 &=\frac{b^2-AD}{A}>0.                                   \tag{21}
\end{aligned}
\]

Also \(I(F+cH)>0\): if \(b\ne0\), the second term in (20) is positive;
if \(b=0\), `(CERT)` forces \(D<0\), hence \(F\ne0\).  Thus (21) proves
the strict Proposition-1 quotient

\[
\frac{48J(F_{\rm tot})}{I(F_{\rm tot})}>1.               \tag{22}
\]

An exact lower bound for the quotient margin, useful for a checker, is

\[
\frac{48J(F_{\rm tot})-I(F_{\rm tot})}{I(F_{\rm tot})}
\geq\frac{b^2-AD}{A I(F)+b^2}>0.                          \tag{23}
\]

No invertibility or positive definiteness of a matrix is assumed.  The only
positivity used is the particular scalar \(A>0\), the exact scalar
\(b^2-AD>0\), and the one-band identity (19).

## 5. The admissible 48-tuple

The pinned tuple is

```text
0,6,8,14,18,24,26,48,50,54,56,60,66,68,74,78,
80,84,90,96,98,104,110,116,120,126,134,138,144,150,158,164,
168,176,180,186,188,194,200,204,206,210,216,224,228,230,234,236
```

It has 48 strictly increasing distinct entries, minimum 0, maximum 236, and
diameter 236.  Independent modular reconstruction gives the following
missing residue witness for every prime at most 48:

| prime | missing residue | prime | missing residue | prime | missing residue |
|---:|---:|---:|---:|---:|---:|
| 2 | 1 | 3 | 1 | 5 | 2 |
| 7 | 2 | 11 | 9 | 13 | 10 |
| 17 | 4 | 19 | 13 | 23 | 13 |
| 29 | 15 | 31 | 1 | 37 | 7 |
| 41 | 10 | 43 | 2 | 47 | 5 |

For a prime \(q>48\), a set of 48 residues cannot cover all \(q\) residue
classes.  Hence the tuple is admissible and \(H(48)\leq236\).

Assuming `(CERT)`, (22), the four verified hypotheses for (7), and the
repaired Proposition-1 proof give a positive GPY sum for every sufficiently
large \(x_r\).  A summand with
\(\sum_{i=1}^{48}\rho(n+h_i;x_r)>1\) has at least two distinct prime
entries, since each summand is at most the corresponding prime indicator.
Between those two primes lies a consecutive-prime gap no larger than 236.
The disjoint ranges make these gaps tend to infinity.  Therefore

\[
[\mathrm{ONE\mbox{-}BAND\mbox{-}EXACT\mbox{-}CERT}]
\quad\Longrightarrow\quad H_1\leq236.                    \tag{24}
\]

## 6. Line-by-line dependency checklist

Line numbers refer to the pinned Stadlmann 2026 TeX.

| source lines | dependency used here | audit disposition |
|---|---|---|
| 140--150 | Definition 1, half-open totals, weak cap, `t_i>delta`, cap monotonicity | PASS for all 60 columns and all active/empty counts; exact parameters and margins are in Section 1. |
| 155--171 | relevant modulus class | PASS with explicit empty-product convention `B[j,0]=0`; (5) checks the asymmetric epsilon cancellation. |
| 175--184 | Definition-3 quantifiers, primitive residue, squarefree sum | PASS via (9); all `epsilon_0>0` cases are separated. |
| 188--208 | GPY weight and positivity-to-two-primes step | PASS after global truncation of rho and denominator positivity. |
| 210--217 | literal `I,J,K` | `I,J` PASS with (16)--(19); malformed/ambiguous `K` is immaterial only because `c2=0`. |
| 228--242 | Proposition 1 statement | PASS in the repaired nonnegative specialization, conditional on `(CERT)`. |
| 248--277 | smooth tensor-weight reduction | PASS after the direct bounded-overlap tensorization (14); the printed differentiated-localization argument is not cited. |
| 282--311 | band split, affine retreat, mollification | PASS; strict quotient plus null boundaries supplies the necessary cushion. |
| 312--374 | form identification and small threshold strips | PASS after (14) and printed index corrections; the general `K` discussion is unused. |
| 380--455 | prime-weight asymptotic | PASS after global truncation, coprimality restoration, shifted-endpoint reduction, and exact lcm-to-`Q*` mapping. |
| 458--515 | final Proposition-1 argument | PASS with (15) as a lower bound, not equality, and with a fixed positive denominator before division. |
| 532--669 | coefficient definitions and IIa/IIb/IIc/III statements | PASS only in the specialized direct-HB route and with every repair in Section 2.7. |
| 674--1098 | imported distribution proofs | PASS after global boundary repair, target/source epsilon separation, Corollary-4.16 side condition, corrected IIc minimum, and corrected Type III. |
| 1104--1237 (Proposition 2) | Harman decomposition/minorant construction | NOT USED.  The weight is the direct prime weight (7). |
| 1239--1391 | finite factor-partition lemmas | PASS through (11)--(12), exact continuum completion, and adverse-cell verification. |
| 1397--1753 (Proposition 3) | general equidistribution criterion and parameter cases | NOT USED AS A BLACK BOX; its universal tuple premise is not inferred from samples.  The specialized factorization and every source inequality are checked directly. |
| Section 5 | integration recurrences and finite Rayleigh quotient | OUTSIDE THIS AUDIT; exactly the missing input `[ONE-BAND-EXACT-CERT]`. |
| Section 6 | published `k=49` parameter computation | NOT USED; it cannot certify `k=48`. |

## 7. Adversarial failure checklist

| proposed failure | result |
|---|---|
| accidentally use \(k=49\) | Excluded.  The sole factor in (18), (21), and (22) is exactly 48. |
| reuse a \(k=49\) matrix/combinatorial factor | Excluded from this analytic argument; `(CERT)` must reconstruct all \(k=48\) forms. |
| favorable floating rounding | Excluded from the implication; the blocker explicitly requires exact scalars and exact sign. |
| treat an exact inner quotient as the total certificate | Rejected.  `(CERT)` also requires exact outer norm and exact mixed cutoff integral. |
| assume matrix positive definite or invertible | Not used; (21) is a particular scalar inequality. |
| lose a factor of 48 in the mixed term | Checked in (17)--(18); Definition 5 is one distinguished coordinate and Proposition 1 supplies one factor 48. |
| use the wrong mixed cutoff | Excluded; the cutoff is exactly `8960917/36000000`. |
| infer \(J(H)\geq0\) for several outer bands | Excluded.  The argument retains exactly one outer band, and (19) is the only sign claim. |
| confuse support epsilon with Definition-3 shrink or source epsilon | Excluded; \(\varepsilon=3/400\), \(\varepsilon_0\), \(e_t,e_s\), \(h\), and \(\zeta\) are kept distinct. |
| trust the incomplete producer IIb breakpoint list | Excluded; the hostile replay adds all 2,522 ordinary-prefix roots. |
| sample Proposition-3 tuples | Excluded; (11), affine interval completion, and adverse-cell monotonicity prove the universal cases. |
| cite the false `Delta*=Delta_1` | Excluded; the minimum and its ratio factors are retained. |
| apply the defective Type-I role swap | Excluded by the exact Heath--Brown trichotomy assignment. |
| silently discard the minorant density loss or \(K\) | Excluded: (8) gives `c1=0`, global nonnegativity gives `c2=0`, and only then does `K` vanish. |
| mishandle shifted endpoints or `d=x^delta` | Repaired explicitly; the disjoint subsequence removes the equality case. |
| fail to check the tuple | Excluded by the full witness table and the cardinality argument for primes above 48. |

## 8. Exact completion contract and reproduction

An acceptable completion of `[ONE-BAND-EXACT-CERT]` must make the following
checks without reading trusted serialized matrix entries:

1. parse exact rational definitions of symmetric \(F\) and nonzero symmetric
   \(H\), and prove their essential supports are contained in (3) and (4);
2. reconstruct \(I(F)\) and \(J(F)\) with cutoff \(97/400\);
3. reconstruct \(A=I(H)\) and the one-orientation mixed integral (17), then
   set \(b=48J(F,H)\) with the factor 48 exactly once;
4. prove exactly \(A>0\) and \(b^2-A(I(F)-48J(F))>0\);
5. print the reduced exact margin in `(CERT)` and preferably the quotient
   lower bound (23); and
6. fail closed on a changed source, malformed rational, incomplete basis,
   altered cutoff, altered support, or altered value of \(k\).

The analytic and tuple inputs can be replayed with

```bash
cd prime-gap-236
python3 agents/audit/verify_truncated_lower_energy_v3_hostile_audit.py \
  > /tmp/one-band-support-audit.json
sha256sum /tmp/one-band-support-audit.json \
  agents/audit/results/truncated_lower_energy_v3_hostile_audit.json
cmp /tmp/one-band-support-audit.json \
  agents/audit/results/truncated_lower_energy_v3_hostile_audit.json
python3 verify/check_tuple.py
python3 -O verify/independent_tuple_verifier.py
```

The first two hashes must both be
`fea750c78b8bc7a022d8ee7d407a59405f4f790b1729305f47b21f8d4f2117a1`.
Until the independent exact certificate checker satisfying items 1--6 also
passes, (24) remains a conditional implication rather than a proof of
\(H_1\leq236\).
