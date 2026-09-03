# Wide C722 high-plateau support: hostile analytic audit

## Verdict and scope

**AUDIT PASS**, for the analytic hypotheses of Stadlmann's Proposition 1
only.  This verdict does not assert that a finite-dimensional quotient is
above one.

The audited support is

\[
k=48,\quad \varepsilon=\frac3{400},\quad
\delta=\frac{361}{50000},\quad
(A_0,A_1,A_2)=\left(-\frac3{400},\frac14,\frac{3121}{12000}\right),
\]

with inner schedule \(B_{1,m}=103/400\), and outer schedule

\[
B_{2,m}=\min\left\{\frac{11}{200}+(m-1)\delta,\frac{43}{250}\right\}.
\]

Each schedule is extended constantly through
\(m=\lfloor1/\delta\rfloor=138\).  The active counts are respectively
\(0,\ldots,35\) and \(0,\ldots,23\); every later \(\Xi\)-polytope is empty.

The producer's original blanket transfer from the C10 proof was not valid
as stated.  In particular, its IIb third capacity was evaluated at the wrong
gamma endpoint, and a blanket \(\omega=0\) treatment of the near-square-root
mixed class fails the stated prefix shortcut for 47 count pairs.  Both are
repaired below.  The repaired argument has no uncovered modulus range.

## Frozen sources and executable audit

The standalone verifier is
[`verify_wide_c722_p172_analytic.py`](verify_wide_c722_p172_analytic.py).  It
imports neither wide-support producer checker.  It reconstructs all
arithmetic using `fractions.Fraction`, including all 138 schedule entries,
all fixed branches, and every cell of the continuous IIc cover.

Run from `prime-gap-236/`:

```bash
python3 agents/audit/verify_wide_c722_p172_analytic.py
python3 -O agents/audit/verify_wide_c722_p172_analytic.py
```

Both modes exit zero and emit byte-identical output.  A frozen output is
[`results/wide_c722_p172_analytic_audit.json`](results/wide_c722_p172_analytic_audit.json).
The checker itself pins the complete source manifest.  In particular it pins
Stadlmann 2026 TeX `c0d5d231...`, Polymath8a TeX `fdffe1df...`, the C10 deep
source audit `f9ced080...`, the Proposition-1 repair audit `050702e3...`, the
repaired generic producer `ffe1904e...`, and its high-plateau artifact
`e71f5411...`.

## 1. Definition 1 and ordered band exponents

The exact total-sum endpoints are

\[
\alpha_1=A_1+\varepsilon=\frac{103}{400},\qquad
\alpha_2=A_2+\varepsilon=\frac{3211}{12000},
\]

and the marginal cutoffs are

\[
\eta_1=A_1-\varepsilon=\frac{97}{400},\qquad
\eta_2=A_2-\varepsilon=\frac{3031}{12000}.
\]

The verifier checks \(\delta<B_{j,m}\), every monotonicity/increment
condition, the first empty count, and all later empty counts.  The four
ordered relevant-modulus exponents from Definition 2 are exactly

\[
\eta_1+\alpha_1=\frac12,\quad
\eta_1+\alpha_2=\eta_2+\alpha_1=\frac{6121}{12000},\quad
\eta_2+\alpha_2=\frac{3121}{6000}.
\]

Thus inner/inner lies a fixed power below the Bombieri--Vinogradov level
after Definition 2's factor \(1-\varepsilon_0\).  The mixed and outer
Heath--Brown parameters are

\[
\omega_{12}=\frac{121}{24000},\qquad
\omega_{22}=\frac{121}{12000}.
\]

The undefined printed \(B_{j,0}\) is interpreted by the empty-product
convention: omit its inequality, equivalently set it to zero.

## 2. Prefix lemma used by every finite packing check

Let a selected pool contain \(N\) entries, each at least \(\delta\), with
pool total at most \(S_g\).  Let the total of all groups be at most \(S\),
and let the first-bin capacity be \(C\).  Put

\[
L=(S-C)_+,
\qquad r=\left\lceil\frac L\delta\right\rceil.
\]

If the pool's mandatory mass satisfies \(N\delta\ge L\), sort that pool and,
for the actual tuple, take the shortest prefix whose sum reaches the actual
overload \((T-C)_+\).  Its length is at most \(r\).  When \(r=1\), its sum
is at most \(S_g/N\).  When \(r\ge2\), its sum is at most

\[
L+\frac{S_g-L}{N-r+1}. \tag{1}
\]

Indeed, if the preceding prefix has sum \(P<L\) and the crossing entry is
\(y\), the remaining \(N-j+1\) entries are all at least \(y\), so
\(S_g\ge P+(N-j+1)y\).  This gives (1), monotonically worst at
\(P=L,j=r\).  If (1) is below any secondary capacity \(D\), that prefix goes
in the corresponding secondary bin and its complement fits in the first.
The pool may be the left group, right group, or their union.  This is a
universal continuous proof, not a grid sample.

The fixed checks use proof-safe lower capacities after inward endpoint
shrink.  They cover:

| family | ordered pairs | branch checks | least exact slack |
|---|---:|---:|---:|
| mixed | 863 | 2,589 | \(24039999/5000000000\) |
| transpose | 863 | 2,589 | \(24039999/5000000000\) |
| outer, fixed \(\omega_{22}\) | 575 | 1,725 | \(2519999869/600000000000\) |
| outer, near-square-root \(\omega=0\) | 575 | 1,725 | \(15449999/2500000000\) |

The omitted \((m,m')=(0,0)\) case has the empty partition and is immediate.

## 3. Corrected IIb capacity

With

\[
d_b(\gamma)=\frac37\gamma-\frac17-\frac{24}{7}\omega-h,
\quad
G_b=\frac13+8\omega+\frac73\delta+3h,
\]

the third Lemma-12 capacity after equal inward shifts is

\[
C_3(\gamma)=2\omega+d_b(\gamma)+9\zeta.
\]

It increases with \(\gamma\).  Therefore its uniform infimum is at
\(\gamma=G_b\) and \(\zeta\to0^+\), namely

\[
2\omega+\delta+\frac27h.
\]

The verifier uses the slightly smaller exact-safe value
\(2\omega+\delta\).  The larger value obtained at the upper IIb endpoint,
which appeared in the original producer and in the printed Proposition-3
shortcut, is not used.  This is the same mandatory repair identified in the
pinned C10 deep audit, now redone for both band parameters.

## 4. Open endpoints and the repaired IIc continuum

Write \(h=10^{-10}\), take the HB reserve \(s=h/10\), the inward endpoint
shift \(r_0=h/10\), and take the source-lemma parameter
\(0<\zeta\le h/1000\).  For outer IIc choose the auxiliary source width

\[
d_c=\delta+\frac h4.
\]

After shrinking both ends of every open interval, its remaining width is

\[
d_c-2r_0=\delta+\frac h{20}>\delta.
\]

For \(2/5-h\le\gamma\le G_b(\omega_{22})\) and
\(0\le\omega_0\le\omega_{22}\), the literal inward-shrunk Lemma-13
capacities are bounded below by

\[
\begin{aligned}
 C_1'&=\gamma-2\delta-8\omega_0-h,\\
 C_2'&=\frac12-\gamma-2\omega_0-h,\\
 C_3'&=4\omega_0+\delta-h,\\
 C_4'&=8\omega_0.
\end{aligned} \tag{2}
\]

This is not asserted by rounding.  Subtracting (2) from the actual source
capacities gives fixed positive reserves, respectively

\[
\frac{271}{500}h,\qquad
\frac{447}{500}h,\qquad
\frac54h,\qquad
\frac15h.
\]

All three repaired IIc distribution faces, the proof-start face, the three
endpoint faces, and the Lemma-13 structural relation are checked exactly.
The smallest source-side margin in the whole verifier is the genuine-width
reserve \(h/20=1/200000000000\).

The rectangle in \((\gamma,\omega_0)\) is divided into \(16\times16\)
closed rational cells.  In each cell the lower endpoints in (2) are taken in
the adverse monotone direction.  Applying the proved prefix lemma to every
ordered outer count pair checks exactly

\[
575\cdot16\cdot16=147200
\]

continuous cell/count cases.  The least slack is

\[
\boxed{\frac{2449991}{60000000000}}>0
\]

at counts \((18,18)\), cell \((8,2)\).  Since each cell certificate is for
all tuples in the corresponding \(\Xi\), adjacent closed cells cover the
entire parameter rectangle, including its endpoints.

The target Definition-3 parameter, the support \(\varepsilon\), and the
source \(\zeta\) are distinct.  The target/internal epsilon renaming,
small-prime stripping, dyadic localization, corrected
\(\Delta^*=\min\{N/(|\Lambda|x^{5e}),\Delta_1\}\), arbitrary-squarefree
second exponential bound, and every \(q_0\)-power are inherited only in the
explicit repaired form proved in the pinned C10 deep audit.  Because the
present endpoint and distribution reserves are fixed positive rationals,
the source epsilon can be chosen uniformly below all of them.  No false
\(\Delta^*=\Delta_1\) equality is used.

## 5. Disjoint modulus-range assignment

Let \(Q_0=x^{1/2}\log^{-L}x\), with \(L\) large enough for bilinear BV, and
let \(e_1>0\) be the fixed threshold from the factorization lemmas.  For
large \(x\), \(Q_0>x^{1/2-e_1}\).  The following assignment is disjoint and
exhaustive.

1. Inner/inner: every modulus is at most
   \(x^{(1-\varepsilon_0)/2}\), so classical BV applies directly.
2. Either mixed orientation:
   - \(q\le Q_0\): bilinear BV for the central/three-atom branches;
   - \(q>Q_0\): use fixed \(\omega=\omega_{12}\) IIa/IIb and Type III.
     The IIc gamma interval is empty by
     \((2/5-h)-G_b(\omega_{12})=71149997/7500000000>0\).
3. Outer/outer:
   - \(q\le Q_0\): bilinear BV;
   - \(Q_0<q\le x^{1/2}\): use \(\omega=0\) IIa/IIb and Type III.  IIc is
     empty, and every fixed partition is checked;
   - \(x^{1/2}<q\le x^{1/2+2\omega_{22}}\): use fixed
     \(\omega_{22}\) IIa/IIb and Type III, and (2) for IIc with
     \(0<\omega_0\le\omega_{22}\).

The Type-0 branch is directly power-saving over every range.  Boundary
points may be assigned to the earlier interval; overlaps from asymptotic
dyadic localization are harmless, and there is no gap.  This class-specific
assignment is essential: blindly copying the C10 sentence that every near
class uses \(\omega=0\) would leave the mixed prefix proof unsupported.

For IIa, IIb and corrected Type III, the verifier also checks the open-window
widths, endpoint locations, structural inequalities, all distribution
faces, the omitted Corollary-4.16 polynomial-size side condition through the
same large-factor argument, and the Type-III fixed-factor side conditions.
The global sharp-cutoff boundary estimate and target/internal epsilon
separation are used exactly as in the pinned deep audit; the defective
Baker--Irving role swap is excluded.

## 6. Finite ordered-band transfer and prime minorant

Definition 3 sums a nonnegative absolute discrepancy.  Restrict its union to
each of the four ordered band pairs, then to each of the finitely many count
pairs.  The corresponding BV/direct-HB bound applies to each restriction;
summing these finitely many bounds preserves arbitrary logarithmic saving.
Multiple representations only cause harmless overcounting.  Both mixed
orientations were checked separately.

The direct HB argument first establishes distribution for
\(\Lambda1_{[x,2x]}\).  At the outer exponent
\(3121/6000<1\), prime squares contribute
\(O(x^{1/2}\log^3x+x^{3121/6000}\log^2x)\), and higher powers contribute
\(O(x^{3121/6000+1/3}\log x)\); both are power-saving.  Thus distribution
passes to \(\vartheta\), and then to

\[
\rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)1_{[x,2x]}(n).
\]

This satisfies \(0\le\rho\le1_{\mathbb P}\), has PNT mass
\((1+o(1))x/\log x\), and is supported on primes at least \(x\).
Taking \(\beta=1/2\) gives
\(\beta>\max(B_{1,1},B_{2,1})=103/400\).  Hence Proposition 1 hypotheses
(1)--(4) hold with \(c_1=c_2=0\), after the pinned Proposition-1 repairs
(global truncation, shifted endpoints, coprimality subtraction, tensor
approximation, and the numerator lower bound).

## Restricted conclusion

The p=.172 two-band support is analytically legitimate for Proposition 1.
It is not a proof of \(H_1\le236\): an exact \(k=48\) quotient above one and
the final independent theorem audit are still required.
