# C10 proof-completeness reaudit

Date: 2026-09-02 (Europe/Berlin)

## Verdict

**AUDIT PASS EXCEPT CERT.**

For the bytes pinned below, the conditional implication in
`agents/structural-basis/PROOF-DRAFT-C10.md` is mathematically complete after
excluding exactly the named finite assertion `[CERT-C10-48]`.  In particular:

- the weighted, globally truncated prime minorant satisfies all four inputs
  needed by the repaired nonnegative specialization of Proposition 1;
- the direct Heath--Brown argument proves the required Definition-3
  equidistribution unconditionally, with the source corrections stated in
  Sections 6--7 of the draft;
- the support-boundary and shifted-interval repairs are sufficient, including
  on an explicit disjoint subsequence if one uses the audit's convenient
  exclusion of the equality `d=x^delta`;
- the BFI 2019 correction note does not invalidate the bilinear
  Bombieri--Vinogradov theorem used below the square root;
- the elementary estimates invoked in the prime-power and boundary steps are
  adequate; their missing conventional bibliography is editorial, not a
  theorem-strength gap; and
- the independent tuple reconstruction proves `H(48)<=236`.

This verdict does **not** assert `48J-I>0`, does not treat a Decimal or interval
candidate as a certificate, and therefore does not prove `H_1<=236` by itself.

## 1. Audited bytes and scope

| item | SHA-256 |
|---|---|
| current proof draft | `30532156254193456faa6f8d1c9e6ac53395d7a46d633410bb749a0557773c2f` |
| Stadlmann 2026 TeX | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| Polymath8a TeX | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| Stadlmann 2023 TeX | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| Baker--Irving TeX | `743ca0053146471648040fa1224f2177258221ded4927f8c9fe3221c35b6702e` |
| BFI 2019 correction-note PDF | `63b3515b99088d3670d31266e42e96937dc1253c7425da68831aab343608f1d4` |
| earlier hostile parameter audit | `7df85a8ca8b6ea3ab9246e018efd759e6ddf76200f895a141f2ff089da15ccc3` |
| repair addendum | `2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7` |
| deep-distribution audit | `f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd` |
| Proposition-1 `c2=0` audit | `050702e317596f4e84f2d6f085e2f22f0f35fe04f2a9e0cc05187e261befbafb` |

I reread the proof draft from line 1 through line 1138 and checked the cited
source anchors rather than inheriting the verdict lines of the earlier audits.
The recent change to the proof draft adds the pinned BFI correction-note row
and updates nonblocking citation item 5.  It does not change the analytic
formulae or Section 10.

The only excluded assertion is proof-draft lines 982--999:

\[
 I(F)>0,\qquad 48J(F)-I(F)>0.
\]

The definition and identity of that candidate have a separate static audit;
its integral sign is still absent.

## 2. Proposition-1 hypotheses

The exact statement is Stadlmann 2026 TeX lines 228--242.  The proof draft
states its four inputs at lines 154--165 and takes

\[
 \rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)1_{[x,2x]}(n),
 \qquad c_1=c_2=0,\qquad\beta=\frac12.                 \tag{A}
\]

The final indicator in (A) is essential: it is the global truncation explicitly
made at proof-draft lines 167--176 and Proposition-1 audit lines 33--47.

| hypothesis | fresh check | result |
|---|---|---|
| (1), minorant | On `[x,2x]`, `0<=log n/log(3x)<1`; outside it the chosen function is zero.  Hence the pointwise inequality is actually global, which is stronger than the printed hypothesis and remains valid after shifts by tuple entries. | PASS |
| (3), rough support | A nonzero value is supported on a prime `n>=x`; its sole prime factor is `n>x^(1/2)`, while `1/2-B_1=7/20>0` (draft lines 181--193). | PASS |
| (4), density | PNT gives `(theta(2x)-theta(x))/log(3x)=(1+o(1))x/log x` (lines 195--205).  This is the density of the actual weighted function, not of `1_P`. | PASS |
| (2), equidistribution | Sections 3--8 prove arbitrary logarithmic saving for `Lambda 1_[x,2x]`, subtract prime powers with a power saving, and divide by the constant `log(3x)` (lines 211--868).  The complete source check is below. | PASS |

For every fixed relevant-modulus shrink `epsilon_0`, Definition 2 gives

\[
 q\le x^{(1-\varepsilon_0)(\eta+\alpha)}
 \le x^{2A_1}=x^{77747/150000}<x.                    \tag{B}
\]

For `epsilon_0=1` only `q=1` occurs and its discrepancy is zero; for
`epsilon_0>1` the class is empty (the draft's allowance of a vacuous `q=1`
case is harmless).  For `0<epsilon_0<1`, choose the target/source small
parameters exactly as in draft lines 422--452.  Since
`Q*(epsilon_0)` is contained in the larger class with target shrink `e_t`,
the proof covers every shrink required by Definition 3.

## 3. Distribution chain for hypothesis (2)

### 3.1 Complete Heath--Brown alternatives

Polymath8a lines 1425--1465 give the exact `K=10` identity on `[x,2x]`.
Its localization is lines 1496--1589 and its coefficient/SW/smoothness Facts
lemma is lines 1637--1737.  The two strict prerequisites used by C10 are

\[
 \sigma-\frac1{10}=10^{-11}>0,
 \qquad 2\sigma-\frac1{10}>0.
\]

Polymath8a's combinatorial lemma, lines 1305--1395, then exhausts every
localized term by the direct long smooth atom, a central pair of complementary
SW aggregates, or three smooth atoms.  This is the actual trichotomy in draft
lines 261--305; it has no fourth branch and never invokes the defective
Baker--Irving role swap.

### 3.2 Direct and small-modulus branches

- For Type 0, after fixing the complementary variables the smooth atom cut by
  `[x,2x]` has polylogarithmic total variation.  Progression minus primitive
  average is therefore `tau(q)^O(1) log^O(1)`, and the complement has
  `l1` mass at most `x^(1/2-sigma) log^O(1)`.  Summing to (B) leaves the exact
  power reserve

  \[
   1-\{(1/2-\sigma)+2A_1\}
   =\frac{24506000003}{300000000000}>0.
  \]

  This agrees with, but does not need, the sharper Poisson estimate at
  Polymath8a lines 1780--1863.

- For `q<=x^(1/2)log^{-L}x`, Polymath8a Theorem 2.9 at lines 1043--1049
  applies: in the central branch its `N` factor has exponent at least
  `2/5-s`, and in the Type-III branch a selected smooth atom has exponent at
  least `2sigma`.  In both cases it is SW and has fixed positive-power scale.

- The full localized theorems, rather than an unproved sharp-interval variant,
  are used.  Polymath's boundary sequence has total length
  `H<<x log^{-R}x`.  The divisor second-moment progression bound and Cauchy
  give `<<(x/q)log^{-R/2+O(1)}x`; summing
  `tau(q)^O(1)/q` costs only a logarithmic power.  This repairs the
  per-modulus-only display at Polymath8a line 1578.  The argument is made once
  globally, as required at proof-draft lines 367--386.

### 3.3 Near/above-square-root Type II and Type III

The split in proof-draft lines 388--420 is exhaustive: bilinear BV ends at
`sqrt(x)log^{-L}x`, the near strip reaches `sqrt(x)`, and the upper range
reaches `x^(1/2+2omega)`.  Dyadic upper blocks above the square root have
`omega_0 in [0,omega]`; their `O(1/log x)` endpoint motion is below the fixed
inward reserves.

I checked the following source-level obligations, rather than just the final
rational margins:

1. IIa/IIb use the central SW aggregate in the correct second slot.  The two
   Polymath power conditions are those displayed at draft lines 528--544.
   The omitted Corollary-4.16 side condition
   `N<=[d_1,d_2]^O(1)` follows from the fixed-power divisor
   `r>=x^(gamma-delta-O(e))`.
2. The target/source epsilon separation at draft lines 422--452 pays for
   small-prime stripping, dyadic constants, and all coefficients 3, 6 and 52
   without consuming the inward reserve `r_0=h/10`.
3. IIc does not use the false 2026 assertion `Delta*=Delta_1`.  Retaining
   `Delta*=min(N/(|Lambda|x^(5e)),Delta_1)` gives the common lower bound
   `N/(q_0^2 x^(delta_c+55e)H^2)`.  The restored second and third terminal
   estimates are draft (25b)--(25d), with every `q_0` power favorable.  The
   primary downstream-use table is deep-audit lines 519--579.
4. The IIc exponential input uses only Polymath's second bound.  Its proof
   requires a squarefree polynomial-size modulus, not dense divisibility;
   this is checked against the primary proof at Polymath8a lines 8710--8743.
5. In Type III, only the three distinguished atoms are smooth; the residual
   coefficient remains arbitrary, consistently with Polymath8a Definition 2.6
   and its proof.  The two dense-divisibility uses are replaced by the exact
   squarefree identity

   \[
     d=\frac r{(r,b)}\frac s{(s,b)}.
   \]

   The transcription `-5/6` is replaced by `+2/3`, yielding all three strict
   inequalities at draft lines 766--783.  Their smallest displayed reserve is
   `8h=1/1250000000`; the source `6e` cost is strictly smaller.

The exact support and exponent checker was rerun in normal and optimized modes
at SHA
`27c1ae65e08bdc43434b26dc078257c43aeeda115286f788ad50f2baf7d37863`.
Both runs ended `C10 HOSTILE ANALYTIC EXACT PASS`.  This is only an arithmetic
cross-check; the source reasoning above supplies the universal quantifiers.

### 3.4 Prime powers

The passage from `Lambda` to `theta` at draft lines 829--867 is valid.
For squarefree `q`, a primitive residue has at most `2^omega(q)` square roots,
giving

\[
 x^{1/2}\log^3x+Q\log^2x=o(x\log^{-C}x).
\]

For exponents at least three, the intentionally crude `Q` possible moduli per
prime power gives `Qx^(1/3)log x`; its exact exponent reserve is
`22253/150000`.  The coprime average costs
`sum_{q<=Q}1/phi(q)<<log Q`.  Thus subtracting all prime powers preserves
arbitrary logarithmic saving, uniformly in the primitive residue.

## 4. Repaired Proposition-1 application

The printed Proposition-1 proof is not safe verbatim.  The application in the
draft correctly points to the repaired `c2=0` proof at lines 875--885.  I
rechecked the nine repairs in `PROP1-C2ZERO-AUDIT.md`, lines 33--282:

1. global truncation makes `rho` nonnegative at every shifted argument;
2. `B_{j,0}=0` is only the empty-product convention;
3. direct local tensorization of the smoothed, retreated `F` supplies uniform
   absolute-sum control and convergence of `I` and every one-coordinate
   marginal, avoiding the printed differentiated-localization gap;
4. the listed variable-index and dummy-sum errors are corrected;
5. the coprimality subtraction is restored (and vanishes even more directly
   for the prime-supported (A), since `q=o(x)`);
6. shifted endpoint errors are `O(1)` per modulus and sum to a power-saving by
   (B);
7. every lcm is mapped to the fully indexed relevant-modulus class, including
   the `W=x^o(1)` shrink loss;
8. after discarding `U_i^2 rho`, the numerator statement is the required lower
   bound, not the false printed equality; and
9. `I>0` and the fixed strict quotient margin make the denominator positive
   before division.

For the boundary convention `d>x^delta`, the audit permits working along a
subsequence with `x^delta` nonintegral.  This is sufficient, not conditional:
one explicit choice is

\[
 x_j=3^{100j+1}.
\]

Then `x_j^(1/100)=3^(j+1/100)` is nonintegral and the ranges `[x_j,2x_j]`
are disjoint.  All distribution and sieve estimates are uniform on this
subsequence.  Positivity in each sufficiently large range produces two primes
tending to infinity, so the resulting bounded consecutive gaps occur
infinitely often.  Alternatively an equality-size divisor can be put into the
`x^delta`-smooth factor, but that alternative is not needed.

The half-open total-sum face, weak cap faces, and `t_i=delta` hyperplanes have
Lebesgue measure zero.  The proof uses closed polytopes only to make the
factorization claims stronger; it does not change a positive-volume support
cell.  Affine retreat and mollification take place before tensorization, so
the piecewise-polynomial certificate function is a legitimate symmetric
`L^2` input if `[CERT-C10-48]` is later proved.

## 5. BFI correction note and standard inputs

Polymath8a Theorem 2.9 explicitly cites BFI Theorem 0 for its bilinear
Bombieri--Vinogradov statement.  The indexed 1986 statement was checked when
the source manifest was updated and agrees with Polymath's formulation.  The
pinned 2019 correction note states in its abstract that no theorem statement
of the 1986 paper is affected.  Its Section 2 replaces the last term of Lemma 1
and explains that the corrected bound remains sufficient; the only identified
nontrivial downstream edit is in original Section 10.  Its Section 3 repairs
separation arguments in original Sections 9 and 11.  None changes Theorem 0.
Thus the new correction-note row exposes, rather than hides, the relevant
errata chain.

The 1986 scan could not be archived locally, as `sources.md` records.  This is
a provenance inconvenience, not an unproved lemma: the published theorem,
Polymath's exact restatement, and the authors' correction note identify the
input unambiguously.  A release archive should still add the scan if access
becomes available.

The remaining uncited estimates at proof-draft lines 1117--1121 are standard
and adequate in precisely the forms used: PNT; fixed divisor-power averages;
`sum 1/phi(q)<<log Q`; divisor moments in a progression with
`H/q>=x^(1-2A_1)log^{-R}x`; and the elementary `2^omega(q)` square-root count.
They deserve conventional references in publication form but do not constitute
an analytic gap.

## 6. Tuple and final implication

The tuple at proof-draft lines 1016--1039 was reconstructed independently from
the pinned source (SHA
`adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9`).
The independent verifier SHA
`645d3e61f587f9f961b3c72037a0f4499ac29c85c64be601b6b14e6a4b898f78`
passes in normal and optimized modes: 48 distinct entries, minimum 0, maximum
236, and exactly the displayed missing-residue witnesses for every prime at
most 48.  For a prime larger than 48, 48 entries cannot cover all classes.
Therefore `H(48)<=236` is proved.

If and only if `[CERT-C10-48]` supplies `I>0` and `48J-I>0`, the repaired
Proposition-1 argument yields a positive GPY sum for all sufficiently large
ranges in the chosen disjoint sequence.  Since every value of (A) is at most
the prime indicator and one prime contributes strictly less than 1, a summand
with `sum_i rho(n+h_i;x)>1` contains at least two distinct primes.  Two primes
inside a translate of a diameter-236 tuple force a consecutive-prime gap at
most 236.  This proves the conditional implication

\[
 [\mathrm{CERT\mbox{-}C10\mbox{-}48}]\quad\Longrightarrow\quad H_1\le236.
\]

No other missing mathematical assertion was found.

## 7. Lightweight reproduction

From the repository root:

```bash
python3 prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
python3 -O prime-gap-236/agents/hostile-analytic-audit/c10_audit_exact.py
python3 prime-gap-236/verify/independent_tuple_verifier.py
python3 -O prime-gap-236/verify/independent_tuple_verifier.py
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/verify/test_independent_tuple_verifier.py
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/verify/test_independent_tuple_verifier.py
```

These checks are finite arithmetic and tuple cross-checks only.  They do not
evaluate the missing certificate integral.
