# C10 deep distribution audit

## Verdict and scope

**C10 DEEP-DISTRIBUTION AUDIT PASS WITH MANDATORY REPAIRS.**

This verdict is deliberately narrower than an endorsement of every
equidistribution lemma as printed in Stadlmann 2026.  It covers only the
specialized direct Heath--Brown C10 route in
[PROOF-DRAFT-C10.md](PROOF-DRAFT-C10.md):

1. the exact \(K=10\) Heath--Brown decomposition;
2. the direct Type-0 branch;
3. bilinear Bombieri--Vinogradov below the square root;
4. Stadlmann 2026 Type IIa, IIb and IIc for the central aggregate; and
5. Stadlmann 2026 Type III for the three-smooth-atom branch.

The C10 route does **not** use the Baker--Irving Type-I lemma, the general
Harman minorant, or the defective high-\(\gamma\) role swap.  No
theorem-strength gap remains in the five inputs above after the repairs in
Sections 4--8 of this report are made explicit.  The most important repair is
that Stadlmann 2026, line 1000, falsely asserts
\(\Delta^*=\Delta_1\).  Equality is not true in the stated parameter range.
Keeping the original minimum
\(\Delta^*=\min\{N/(\lvert\Lambda\rvert x^{5e}),\Delta_1\}\)
and restoring the factors \(\Delta^*/\Delta_1\) nevertheless gives the same
three final IIc exponent inequalities; the corrected calculation is in
Section 7.

This report audits analytic distribution inputs only.  It does not audit the
C10 support partition arithmetic, the finite quotient, Proposition 1's sieve
proof, or the admissible tuple.  Those are separate artifacts.

## Pinned primary sources

All citations below are to local TeX line numbers.  The audited bytes are:

| source | local file | SHA-256 |
|---|---|---|
| Stadlmann 2026 | [Bounded_Gaps_2.0.tex](../../sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex) | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| Polymath8a | [newergap.tex](../../sources/polymath8-edz-1402.0811-src/newergap.tex) | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| Stadlmann 2023 | [Primes_in_arithmetic_progressions.tex](../../sources/stadlmann-2309.00425-src/Primes_in_arithmetic_progressions.tex) | `60c0440f33d9cbf504470716491fb4d45b45b26d9a960c8e34ff2af500837a30` |
| Baker--Irving | [primegaps_paper.tex](../../sources/baker-irving-1505.01815-src/primegaps_paper.tex) | `743ca0053146471648040fa1224f2177258221ded4927f8c9fe3221c35b6702e` |

The specialized support/factorization verification used as input here is
[C10-AUDIT.md](../hostile-analytic-audit/C10-AUDIT.md), SHA-256
`7df85a8ca8b6ea3ab9246e018efd759e6ddf76200f895a141f2ff089da15ccc3`,
with its [repair addendum](../hostile-analytic-audit/c10-analytic-repair-addendum.md),
SHA-256
`2fc564f6e7e87661a7769980db85889720a19d09d4e65026fa23458fb6d583d7`.
Those files establish the exact strict margins and universal support
partitions.  This report does not assume their conclusions about the deeper
source estimates; it checks those estimates below.

## 1. Actual C10 dependency chain

The analytic chain is

```text
Polymath exact HB identity + finer-than-dyadic partition
    |
    +-- global sharp-cutoff boundary term (repaired directly)
    |
    +-- Facts lemma: location / smooth atoms / SW sub-convolutions
            |
            +-- Type 0: direct one-variable summation
            |
            +-- central aggregate, beta SW, 2/5-s < gamma <= 1/2
            |       |
            |       +-- q <= sqrt(x) log^{-B} x: bilinear BV
            |       +-- remaining q: IIa / IIb / repaired IIc
            |
            +-- three smooth atoms: bilinear BV for small q,
                                    repaired fixed-factor Type III otherwise
```

This ordering matters.  The sharp indicator (1_{[x,2x]}) is removed once,
globally, before applying any full-convolution estimate.  One must not insert
an arbitrary sharp indicator into a Type-II or Type-III theorem and assume
that its coefficient hypotheses survive.

## 2. Line-by-line dependency table

### 2.1 Statements and common reduction

| Stadlmann 2026 lines | asserted step | primary-source dependency | C10 finding |
|---|---|---|---|
| 532--545 | coefficient, location, Siegel--Walfisz and smoothness definitions | Polymath8a 882--906; Stadlmann 2023 236--257 | Definitions agree in substance. Uniform divisor-power and derivative constants are required. The \(K=10\) partition has them. |
| 554--562 | equidistribution with a sharp \(n\in[x,2x]\) restriction, squarefree moduli and a residue primitive at every prime \(p\le x\) | Polymath discrepancy framework 920--973 and 1468--1589 | The cited distribution proofs naturally estimate full localized convolutions, not arbitrary sharply truncated ones. C10 is valid only with the global boundary repair in Section 4. |
| 572--583 | Type IIa statement | Polymath Type-II proof 4049--4308, reached through its Theorem 5.8 reduction | Valid for C10 after the small-prime/dyadic epsilon bookkeeping in Section 5. |
| 588 | uniformity when strict exponent inequalities have fixed reserve | all later estimates are power inequalities with \(x^{O(e)}\) losses | Valid and essential: the C10 \(\gamma\) and \(\omega_0\) values vary over compact intervals. |
| 593--608 | Type IIb statement | Polymath Type-I(ii) proof, especially 4660--4730, with the second Corollary-4.16 bound | Valid for C10. The apparently smooth \(\psi_N\) at line 849 is inserted after Cauchy--Schwarz, not assumed of the original \(\beta\). |
| 611--629 | Baker--Irving Type I | Baker--Irving 157--235 and 266--289; Polymath Type II for a role swap | Not used by C10. The printed universal statement has a genuine missing hypothesis in its middle-\(\gamma\) branch; see Section 9. |
| 633--650 | Type IIc statement | Stadlmann 2023, chiefly 526--1721 and appendix 1995--2175; Polymath's squarefree exponential bound | Valid for C10 only after the repairs in Section 7. |
| 653--669 | Type III statement | Polymath8a 6853--7607, with the factorization uses at 7345--7347 and 7469--7479 replaced | Valid for C10 after two transcription repairs and the fixed-factor check in Section 8. |
| 674--759 | alternative Theorem 5.8 reduction for arbitrary dyadic sets \(\mathcal Q,\mathcal R\) | Polymath8a's dispersion reduction through 4033 | The reduction uses roughness of \(\mathcal Q\), squarefreeness and one \(d=qr\) factorization, but no later dense divisibility. Exact dyadic endpoints require a renamed internal epsilon (Section 5). |
| 745--746 | replace the primitive class modulo \(P_I\) by a residue coprime to every \(p\le x\) | Polymath8a 920--973 | C10 Definition 3 supplies this stronger primitivity. |
| 751 | discard moduli with an exceptionally large product of \(p\le D_0\) factors | Polymath8a pages 42--43 in the Theorem 5.8 reduction | The same trivial estimate is insensitive to the later modulus subclasses. |
| 754--758 | strip the \(D_0\)-small factors from \(q\), dyadically localize \(q,r\), and continue to the exponential target | Polymath8a through 4033 | Algebraically sound, but not with identical epsilon labels at exact endpoints. Section 5 gives the required inclusion. |

### 2.2 Type IIa and IIb

| Stadlmann 2026 lines | source step checked | result |
|---|---|---|
| 762--777 | IIa fixes \(r\), enlarges the rough \(q\)-sets to complete intervals, and identifies Polymath equation (5.33) | Enlarging after fixing \(r\) is monotone because absolute values have already been linearized by 1-bounded coefficients. No modulus factorization is used afterward. |
| 777--787 | import Polymath 4049--4308 and replace the old near-square-root lower bound by two direct power inequalities | Polymath 4196--4207 gives exactly the two displayed quantities. Substitution \(N=x^\gamma\) yields \(24\omega+7\delta-5\gamma<-2\) and \(8\omega+3\delta-\gamma<0\). |
| Polymath8a 4083--4092 | control arbitrary \(\beta\) and insert a smooth majorant | The coefficient bound gives the fourth-moment estimate; a smooth \(\psi_N\ge1\) is inserted only after Cauchy--Schwarz. Thus IIa needs \(\beta\) Siegel--Walfisz, not smooth. |
| 795--800 | restate the second inequality of Polymath Corollary 4.16 | Formula agrees with Polymath 2968--2975. The restatement omits \(N\le[d_1,d_2]^{O(1)}\), but C10 nonempty modulus classes contain \(r\ge x^{\gamma-\delta-O(e)}\) inside the lcm, so this side condition holds uniformly. |
| 812--841 | IIb extracts \(u_1\) from the given fixed-size \(u\)-factor | Squarefreeness makes the factorization clean. Stripping \(D_0\)-small primes can shorten \(u\) only by \(x^{o(1)}\), absorbed by Section 5's epsilon renaming. The displayed \(q_1=u_1v_2\) at line 987 belongs to IIc and is a harmless index typo; here the IIb identity is \(q_1=u_1v_1\). |
| 842 | require the upper \(U\)-endpoint to exceed 1 | In the used C10 IIb ranges, \(\gamma<1/2-2\omega_*\) with fixed reserve. More generally, if this fails then the stated divisor window is eventually empty. |
| 844--853 | arrive at a sum containing a smooth \(\psi_N\) | Polymath 4686--4712 explicitly applies Cauchy--Schwarz and inserts this smooth majorant. No unprinted smoothness of \(\beta\) is being assumed. |
| 854--867 | apply the second Corollary-4.16 bound to squarefree \(d_1,d_2\), then sum gcds | Squarefreeness of the original modulus copies makes \(rq_0u_1[v_1,v_2]\) and \(q_2\) squarefree and coprime in the required places. Polymath's omitted polynomial-size side condition again follows from the large \(r\)-factor. |
| 868--885 | reduce to the two stated exponent inequalities | The algebra matches after \(UV\asymp Q/q_0\); all discarded \(q_0\)-powers are in denominators. The third display at line 878 contains an explicit favorable \(-6e\), so it is automatically power-saving. |

### 2.3 Type IIc

| Stadlmann 2026 lines | predecessor location | audit result |
|---|---|---|
| 963--980 | new \(r,u,d_1\) divisor windows | Line 967 says \(100e\), while the lemma statement (line 638), the set \(\mathcal R\) (line 978), and the conversion (994) use \(52e\).  The only consistent reading is `100` \(\to\) `52`. |
| 981--990 | replace Stadlmann 2023's smooth extraction of \(u\) | Stadlmann 2023 appendix 2146--2158 is the original extraction.  The supplied \(u\)-factor replaces it.  Line 987's final \(v_2\) must be \(v_1\). |
| 992--995 | replace the smooth extraction of \(d_1\) from \(r\) | Stadlmann 2023 647--698 is the original step. Substitution of \(H=x^eRQ^2/(q_0M)\) gives the displayed \(q_0^{-2}\) range. |
| 996 | describe the revised \(D\)-scale | The preceding display has \(D\asymp q_0^{-2}N/H^2\). The sentence “no longer depends on \(q_0\)” is false; it should say that the scale now *does* depend on \(q_0\). No later formula relies on the prose sentence. |
| 997--999 | propagate the enlarged \(V\) and altered \(\Delta_1,m,\Lambda\) ranges through the \(q\)-van der Corput chain | Stadlmann 2023 780--1495 | The long argument uses smoothness after factor extraction only through membership restrictions, divisor counts and the final exponential bound. Replacing the restrictions by the new \(\mathcal Q,\mathcal R\) sets and retaining squarefreeness is legitimate. The final exponential input is treated separately below. |
| 1000 | assert \(\Delta^*=\Delta_1\) | Stadlmann 2023 1292 and 1681 retain a minimum | False as written. This is not a sign-only typo. The corrected calculation in Section 7 retains the minimum and recovers the claimed final conditions. |
| 1002--1016 | first final inequality | Stadlmann 2023 1675--1693 | The factor \(\Delta^*/\Delta_1\) cancels from the first inequality, so this portion remains valid without equality. |
| 1019--1035 | second and third final inequalities | Stadlmann 2023 1695--1719 | Lines 1021 and 1028 have silently replaced \(\Delta^*\) by \(\Delta_1\), and line 1034 also drops \(q_0^2\). Use the repaired forms in Section 7 instead. |
| Stadlmann 2023 1504--1542 | two-dimensional exponential bound, including congruence restrictions | Polymath8a 8391--8414 and 8689--8779 | The bound actually used is Polymath's second bound.  Its proof at 8710--8743 uses only squarefreeness and polynomial size; dense divisibility first appears at 8761 for the unused first bound.  The congruence reduction at Stadlmann 2023 1524--1541 uses squarefreeness to write \(m=qm_1\). Hence \(m\mid P(x^\delta)\) may rigorously be weakened to “\(m\) squarefree of polynomial size” for this branch. |
| Stadlmann 2023 1648--1721 | final original exponent calculation with \(\Delta^*\) retained as a minimum | same paper | This is the correct template for repairing 2026. Its sequence hypothesis is only that \(\beta\) is Siegel--Walfisz; the smooth \(\psi_N\) is inserted after Cauchy--Schwarz at appendix 2166--2174. |

### 2.4 Type III

| Stadlmann 2026 lines | primary-source check | result |
|---|---|---|
| 1038--1044 | identify the two uses of dense divisibility in Polymath Type III | Polymath8a 7345--7347 and 7469--7479 are exactly the two proof uses after the initial reduction.  Line 1044's reference to `Lemma typeIIPoly` is a label typo; it must refer to Type III. |
| 1045--1049 | pass a fixed factor of squarefree \(q\) to \(d=q/b\) | If \(q=rs=bd\), squarefreeness gives \(d=(r/(r,b))(s/(s,b))\), and the first factor loses at most \(b\). This proves membership in \(\mathcal D'(b)\). |
| 1051--1059 | retain Polymath's reduction to hyper-Kloosterman sums with arbitrary bounded modulus weights | Polymath8a 7330--7441 | No smoothness or dense-divisibility property is used here beyond the already replaced membership statement. |
| 1061 | choose the fixed \(S=x^{1/3+4\delta/3-4\omega/3}\) | Polymath8a 7469--7497 | \(\mathcal D'(b)\) supplies \(S/(bx^\delta)\le s\le S\). The auxiliary inequalities \(4\omega-4\delta<1\) and \(2\delta-8\omega<1\) hold with large reserve in C10. |
| 1063--1077 | copy the post-factorization Cauchy and trace-function estimates | Polymath8a 7494--7607 | Those estimates allow arbitrary \(\alpha\) with the coefficient bound. They require the three \(\psi_i\) to be smooth; C10's Facts-lemma atoms are smooth. |
| 1081--1090 | substitute \(S,Q,N\) and derive the final inequality | Line 1082's third exponent \(-5/6\) contradicts line 1077 and line 1088. It must be \(+2/3\). With that correction, the first of the three inequalities is \(28\omega+9\gamma+8\delta<4\), and it implies the other two for \(\omega,\delta\ge0\). |

Polymath8a's restated Type-III theorem at lines 6872--6873 calls
\(\alpha\) smooth. That adjective is stronger than Definition 2.6 at
lines 952--971 and is not used in the proof: from line 7173 onward
\(\alpha(m)\) remains an arbitrary coefficient sequence and is handled by
divisor bounds/Cauchy--Schwarz.  The definition and proof, rather than the
over-strong restatement, justify Stadlmann's arbitrary-\(\alpha\) version.

## 3. Coefficient and smoothness hypotheses in the C10 pieces

The exact Heath--Brown identity is Polymath8a 1425--1465.  The
finer-than-dyadic partition is 1496--1589. Its Facts lemma, 1637--1737,
proves the following facts uniformly for the finitely many \(K=10\) forms:

- every atom and sub-convolution obeys the coefficient-sequence divisor
  bound and is located at its product scale;
- an atom with scale at least \(x^{2\sigma}\) cannot be a truncated Möbius
  atom (those have scale at most \(x^{1/10}\)), hence is smooth;
- a sub-convolution of any fixed positive-power scale is
  Siegel--Walfisz; and
- convolution preserves Siegel--Walfisz when one positive-power factor has
  it (Polymath8a 1675--1730).

Consequently:

| C10 branch | theorem-side sequence | discharged hypothesis |
|---|---|---|
| central IIa/IIb/IIc | the smaller aggregate is \(\beta\), with \(2/5-s<\gamma\le1/2\) | \(\beta\) is a coefficient sequence and Siegel--Walfisz; the complement is an arbitrary coefficient sequence |
| Type III | the three singled-out atoms are \(\psi_1,\psi_2,\psi_3\) | all three are smooth; each individual/pair scale satisfies the Type-III bounds; the residual \(\alpha\) need not be smooth or SW |
| small-modulus Type III | take one smooth positive-power atom as the BV \(\beta\) | smooth implies SW, and the complementary convolution is a coefficient sequence |
| Type 0 | the long atom is treated directly | only smoothness/total variation is used; no distribution lemma is invoked |

There is therefore no hidden substitution of “high-precision smooth-looking”
data for a theorem hypothesis: every required smoothness and SW property
comes from the primary Facts lemma.

For the branches assigned below the square root, the exact primary input is
Polymath8a Theorem `bvt`, lines 1043--1049. It assumes
\(MN\asymp x\), \(N\geq x^{\epsilon_0}\) for one fixed
\(\epsilon_0>0\), coefficient-sequence bounds for both factors, and
Siegel--Walfisz for the \(N\)-factor; it then sums uniformly over all
\(q\leq x^{1/2}\log^{-B}x\). The central C10 aggregate has
\(N\geq x^{2/5-s}\). In the Type-III small-modulus branch, any selected
smooth atom has \(N_i\geq x^{2\sigma}\). Thus the positive-power
hypothesis is uniform. The residue in Definition 3 is primitive modulo
every such \(q\), and Section 4 supplies the sharp-cutoff transfer. This
checks every hypothesis of the small-modulus theorem rather than invoking
“Bombieri--Vinogradov” schematically.

## 4. Sharp intervals: the printed gap and the C10 repair

Stadlmann's Definition 3 is sharp in \(n\in[x,2x]\). Polymath's imported
Type-I/II/III estimates are formulated for complete localized convolutions.
The global finer-than-dyadic reduction handles the difference, but the
printed Polymath line 1578 gives only

\[
  |\Delta(\alpha;a\bmod q)|\ll x\log^{-A_0+O(1)}x
\]

for each \(q\). That display cannot be summed over \(x^{1/2+o(1)}\)
moduli.  Thus citing line 1578 alone is a genuine proof gap.

The intended calculation is preserved in Polymath's commented lines
1600--1627 and is valid.  The boundary sequence is supported on two
intervals of total length
\(H_x\ll x\log^{-A_0}x\) and is bounded by a fixed divisor power.  For
C10, \(q\le x^{77747/150000}<x\), so for large \(x\),
\(H_x/q\to\infty\)
uniformly.  The divisor second-moment estimate in a progression and
Cauchy--Schwarz give

\[
 \sum_{n\equiv a\pmod q}|\alpha(n)|
 \ll \frac{x}{q}\log^{-A_0/2+O(1)}x.
\]

The coprimality average has the same bound, using
\(1/\phi(q)\ll \tau(q)^{O(1)}/q\). Finally,
\(\sum_{q\le Q}\tau(q)^{O(1)}/q\ll\log^{O(1)}x\). Taking \(A_0\)
after the desired saving repairs the summed boundary estimate.

The C10 proof must therefore be read as follows: apply the full-convolution
versions of IIa/IIb/IIc/III to every localized term, and add the single
global boundary estimate above.  It must not cite the literal sharp
formulation of each 2026 lemma without this reduction.

## 5. Small-prime stripping, dyadic endpoints and uniformity

Several 2026 passages use the same epsilon before and after two
\(x^{o(1)}\) operations: stripping
\(\prod_{p\mid q,\ p\le D_0}p\) and replacing a factor by its dyadic lower
endpoint.  Literal equality of epsilon labels is not justified.

Write \(e_{\mathrm t}>0\) for the small parameter in the target Definition-3
modulus class. Choose the source-lemma parameter

\[
 e_{\mathrm s}=\frac54e_{\mathrm t}.
\]

For sufficiently large \(x\), the stripped factor and the dyadic constant
cost at most \(x^{o(1)}\le x^{e_{\mathrm t}/4}\). A target factor

\[
 x^{\gamma-\delta-3e_{\mathrm t}}<r
 <x^{\gamma-3e_{\mathrm t}}
\]

then lands in an internal dyadic block satisfying

\[
 x^{\gamma-\delta-3e_{\mathrm s}}\le R
 \le x^{\gamma-2e_{\mathrm s}}.
\]

Indeed the lower endpoint has reserve
\(3(e_{\mathrm s}-e_{\mathrm t})=3e_{\mathrm t}/4\), while the upper
endpoint has reserve
\(3e_{\mathrm t}-2e_{\mathrm s}=e_{\mathrm t}/2\).

This argument alone would **not** justify applying a single
\(e_{\mathrm s}\) to every
point on every printed IIb/IIc boundary: for example, changing the
coefficient \(6e_{\mathrm t}\) to \(6e_{\mathrm s}\) moves the upper
\(u\)-endpoint inward. What makes the C10 specialization valid is the exact
support proof. Before any
source estimate is invoked, `c10_audit_exact.py` puts every selected factor
in a closed interval at distance at least

\[
 r_0=\frac h{10}
\]

from each relevant open endpoint (and Type III uses the still larger
inward shift \(h\)). Replacing \(e_{\mathrm t}\) by
\(e_{\mathrm s}=5e_{\mathrm t}/4\) moves a coefficient-\(3\),
coefficient-\(6\), or coefficient-\(52\) endpoint by at most
\(3e_{\mathrm t}/4\), \(3e_{\mathrm t}/2\), or \(13e_{\mathrm t}\),
respectively. With \(e_{\mathrm t}<h/1000\), each is strictly smaller than
\(r_0\), even after allocating another \(e_{\mathrm t}/4\) to small-prime
stripping, dyadic constants, and fixed
factors such as \(2\).  This covers, in both directions:

- removal of small primes from the IIb/IIc \(u\)-factor;
- replacement of the original modulus by dyadic \(Q,R\) in the IIc
  \(u,d_1\) windows; and
- all open/closed endpoint changes.

Thus the endpoint repair is proved for the C10 subclass with its certified
inward reserve; it is not being asserted for arbitrary points on the
boundary of the full printed \(D_{IIb}(e)\) or \(D_{IIc}(e)\) classes.
Definition 3 asks for every sufficiently small target \(e_{\mathrm t}\), so
choosing the corresponding slightly larger internal \(e_{\mathrm s}\) is
legitimate.
C10's distribution inequalities have fixed rational reserve, and
Stadlmann 2026 line 588 supplies uniform constants over the compact
\((\gamma,\omega_0)\) ranges.  The Section-3 epsilon used in IIc must
additionally satisfy

\[
 0<e_{\mathrm t}<\frac45
 \min\{h/1000,10^{-100}\delta_c,e_{\rm margin}\},
\]

so that \(e_{\mathrm s}\) obeys all three source restrictions. This is
possible because \(e_{\mathrm t}\) is an arbitrarily small theorem
parameter. In Sections 6--8, \(e\) denotes the source parameter
\(e_{\mathrm s}\), not \(e_{\mathrm t}\).

Dyadic \((Q,R)\) decompositions cost only \(\log^{O(1)}x\).  Polymath's
Type-III finer-than-dyadic modulus intervals have relative width
\(x^{-e}\), hence cost \(x^{e+o(1)}\); the proof target at Polymath8a
7140--7148 has an \(x^{-2e}\) reserve, so this cost is already budgeted.

## 6. Corollary 4.16: omitted side condition and smooth majorants

Stadlmann 2026 lines 795--800 accurately record the second numerical bound
of Polymath8a Corollary 4.16 (2968--2975), but omit the common side
condition at line 2959:

\[
 N\le[d_1,d_2]^{O(1)}.
\]

In every nonempty C10 IIa/IIb application, the lcm contains the divisor
\(r\ge x^{\gamma-\delta-O(e)}\), where the exponent has a fixed positive
lower bound. Since \(N=x^\gamma\), a fixed power of \(r\) exceeds \(N\).
Thus the omitted condition holds uniformly.  Small moduli are handled by
bilinear BV and do not create a degenerate lcm edge case.

The smooth sequence to which the corollary is applied is not the original
arbitrary \(\beta\). Polymath8a 4090--4092 (IIa) and 4686--4712 (IIb)
apply Cauchy--Schwarz first and insert a nonnegative smooth majorant
\(\psi_N\ge1\) on the support of
\(\beta(n)\overline{\beta(n+\ell r)}\). The fourth-moment factor is
controlled by the coefficient bound.  Hence the 2026 statements correctly
require SW, not smoothness, of \(\beta\).

### 6.1 Exact IIa and IIb exponent audit for C10

For IIa, Polymath8a lines 4187--4207 reduce the normalized square of the
target to three terms.  With \(N=x^\gamma\) and the lower end
\(R\gg x^{\gamma-\delta-3e}\), the first two have exponents

\[
 1+12\omega+\frac72\delta-\frac52\gamma+O(e),
 \qquad
 8\omega+3\delta-\gamma+O(e),
\]

while the third is already power-saving.  Stadlmann 2026 lines 777--787
retain the primary calculation but avoid Polymath's later
near-\(1/2\) specialization; multiplying the first exponent by two gives
exactly

\[
 24\omega+7\delta-5\gamma<-2,\qquad
 8\omega+3\delta-\gamma<0.
\]

No factorization of the modulus occurs after \(r\) is fixed: this is
visible from the primary proof at lines 4055--4308.  The only use of
smoothness is the auxiliary majorant inserted after Cauchy at lines
4090--4092.

In the C10 construction, for
\(\omega_*\in\{0,2747/300000\}\), define

\[
 d_a(\gamma,\omega_*)=
 \frac57\gamma-\frac27-\frac{24}{7}\omega_*-h,
 \qquad h=10^{-10}.
\]

On the complete IIa rectangles in C10-AUDIT.md, the first inequality
has the exact reserve \(7h=7/10^{10}\).  The second inequality is worst
at the upper \(\gamma\)-endpoint and has reserves

\[
 \frac{20000000021}{70000000000}\quad(\omega_*=0),\qquad
 \frac{64395200063}{210000000000}
 \quad\left(\omega_*=\frac{2747}{300000}\right).
\]

Thus the source parameter can be chosen so that all explicit
\(x^{O(e)}\) losses, including the conservative \(x^{100e}\) in the
2026 restatement, are smaller than \(7h\).  The auxiliary condition
\(\gamma-4\omega_* -d_a>0\) from the alternative Theorem 5.8 follows
from the second displayed inequality.

For IIb, the amended proof is Stadlmann 2026 lines 815--886, pinned to
Polymath8a lines 4635--4779.  After Cauchy and Corollary 4.16, the three
sufficient estimates are printed at 2026 lines 870--873.  Substituting
the exact \(U,V,R,Q,M\) ranges gives

\[
 24\omega+7\delta-3\gamma<-1,\qquad
 8\omega+3\delta-\gamma<0,
\]

and the third term is exactly power-saving because its exponent contains
the explicit \(-6e\) at line 878.  All powers of \(q_0\) discarded at
lines 860--878 are in denominators.  In particular, there is no hidden
assumption \(q_0=1\).

For C10 put

\[
 d_b(\gamma,\omega_*)=
 \frac37\gamma-\frac17-\frac{24}{7}\omega_*-h.
\]

The first IIb inequality again has exact reserve \(7h\).  The second has
reserves

\[
 \frac{21720000017}{70000000000}\quad(\omega_*=0),\qquad
 \frac{66918080051}{210000000000}
 \quad\left(\omega_*=\frac{2747}{300000}\right).
\]

The exact checker also verifies that the \(U\)-window is nonempty and
strictly above \(1\), and verifies the corrected third packing capacity
at the lower, not upper, \(\gamma\)-endpoint.  Consequently the same
small choice of source \(e\) handles IIb uniformly.

This closes all hypothesis transfers in IIa and IIb: coefficient bounds
control the Cauchy fourth moments, the Facts lemma supplies SW for the
central aggregate, squarefreeness supplies the CRT and lcm identities,
the large \(r\)-factor supplies the omitted
\(N\leq[d_1,d_2]^{O(1)}\) side condition, and dyadic endpoint losses are
absorbed by the target/internal-\(e\) separation in Section 5.

## 7. IIc: exhaustive minimum audit and corrected calculation

Write \(e\) for the IIc small parameter and
\(g=(v_1,v_2)\ge1\).  Every scale formula below uses
\(\lvert\Lambda\rvert\).  The 2023 source allows a signed dyadic
\(\Lambda\) (lines 1039, 1050 and 1062), but positivity of
\(\Delta^*\) forces the absolute value in the formulas where the source
prints \(N/(\Lambda x^{5e})\).  The amended ranges at Stadlmann 2026
978, 994 and 999--1000 are

\[
 \frac{N}{q_0^2x^{\delta+55e}H^2}\ll\Delta_1
 \ll\frac{N}{q_0^2x^{55e}H^2},
 \qquad
 |\Lambda|\ll\frac{q_0x^{\delta+5e}H^2}{w_1g}.
\]

The other ranges used below, also from line 1000 and the unchanged
definition of \(H\), are

\[
 \frac{RQ^2H}{q_0g\Delta_1}\ll m
 \ll\frac{x^\delta RQ^2H}{g\Delta_1},\qquad
 RQ^2=x^{-e}q_0MH,\qquad
 H\ll\frac{x^{4\omega+\delta+7e}}{q_0}.
\]

The lower \(m\)-bound retains \(q_0^{-1}\); the upper bound does not,
because the amended \(V\)-range is larger by at most \(q_0\).  Substituting
the upper \(\Delta_1\)-bound into the lower \(m\)-bound gives

\[
 m\gg\frac{q_0x^{55e}RQ^2H^3}{gN}
     =\frac{q_0^2x^{54e}MH^4}{gN}.
\]

Later we deliberately weaken this by one favorable \(q_0\), exactly as
2026 line 1012 does.

The original 2023 proof defines

\[
 \Delta^*=\min\left\{\frac{N}{|\Lambda|x^{5e}},\Delta_1\right\}.
\]

### 7.1 Smallest explicit failure of line 1000

The claim \(\Delta^*=\Delta_1\) is not implied.  The summarized ranges
allow \(q_0=w_1=g=1\),
\(|\Lambda|\asymp x^{\delta+5e}H^2\), and
\(\Delta_1\asymp N/(x^{55e}H^2)\).  Then

\[
 \frac{N/(|\Lambda|x^{5e})}{\Delta_1}
 \asymp x^{45e-\delta}\longrightarrow0
 \qquad(e<\delta/45).
\]

Thus merely reversing the final `\(\ll\)` at line 1000 does not repair the
argument.

### 7.2 Uniform lower bound that is actually true

Put

\[
 L_\Delta=\frac{N}{q_0^2x^{\delta+55e}H^2}.
\]

The \(\Lambda\)-bound gives

\[
 \frac{N}{|\Lambda|x^{5e}}
 \gg\frac{w_1gN}{q_0x^{\delta+10e}H^2}
 =L_\Delta\,(w_1gq_0x^{45e})\gg L_\Delta.
\]

Also \(\Delta_1\gg L_\Delta\).  Therefore

\[
 \boxed{\Delta^*\gg L_\Delta},
\]

which is all that the final calculation needs.

### 7.3 Exhaustive check of every later use of \(\Delta^*\)

An exhaustive search for “Delta-star” in the pinned 2023 source gives the
following logical uses.  No downstream line needs
\(\Delta^*=\Delta_1\).

| 2023 lines | exact use | property supplied by the retained minimum |
|---|---|---|
| 1225, 1292--1306 | split one \(\Delta_1\)-scale smooth sum into \(O(\Delta_1/\Delta^*)\) shifted-smooth pieces | \(0<\Delta^*\leq\Delta_1\); the cost is retained at 1247, 1306 and 1328 |
| 1310--1318 | first Taylor expansion | \(\Delta^*\leq N/(|\Lambda|x^{5e})\), so the perturbation is \(O(x^{-5e})\) |
| 1342, 1398--1406 | Möbius changes of variables and the second Taylor expansion | only \(\Delta_2\leq\Delta^*\) and the same upper arm of the minimum |
| 1465--1494 | relabel the final two smooth scales and congruence classes | only positivity and \(\Delta_2\leq\Delta^*\) |
| 1551--1584 | apply the two-dimensional exponential estimate | the factor \((\Delta_1/\Delta^*)(\Delta^*/m^{1/2}+m^{1/2})\) is kept exactly |
| 1616--1641 | normalize the gcd weights \(\xi_k\) | the preceding factor is copied unchanged |
| 1648--1679 | expand the final sufficient condition | all three occurrences of \(\Delta^*/\Delta_1\) remain explicit |
| 1681--1719 | final power calculation | uses a lower bound for \(\Delta^*\), never equality |

The Taylor steps become easier when the first arm of the minimum is
smaller.  The sole cost is the explicitly retained number of short
pieces and its corresponding ratios.  Thus the minimum in the
predecessor proof is not a theorem-strength gap.

For completeness, the other hypotheses of every intervening lemma survive
the 2026 replacement as follows.

- In the \(q\)-van der Corput portion (2023 lines 780--1025), the modulus
  \[
    m=r_1q_0u_1[v_1,v_2]q_2
  \]
  is squarefree. Indeed the two Cauchy copies
  \(q_0u_1v_i r\) and the complementary modulus \(q_0q_2r\) are
  squarefree, the imposed coprimality conditions separate \(q_2\) from
  \(u_1v_1v_2\), and the lcm \([v_1,v_2]\) removes their possible
  overlap. This is precisely what is used for CRT, for squarefree
  \(w_1\), and for the divisor count of \(w_2\mid m^*\); no bound on the
  prime sizes is used there. The sole changed diagonal estimate is the
  explicit extra \(q_0^2\) in 2026 line 997.
- Removal of \(\widetilde n\) (2023 lines 1115--1211) uses only
  \(|\lambda|,|\widetilde\lambda|\asymp|\Lambda|\), the support bound
  \(|k|\ll w_1|\Lambda|N/(x^{5e}\Delta_1)\), and
  \(\Delta_1>0\). It does not use a lower bound for \(\Delta^*\).
- The short partition and first Taylor expansion (1225--1329) use exactly
  \(0<\Delta^*\leq\Delta_1\) and
  \(\Delta^*|\Lambda|/N\leq x^{-5e}\). The factor
  \(\Delta_1/\Delta^*\) is retained.
- The Möbius/congruence reduction (1335--1495) uses
  \(\Delta_2\leq\Delta^*\), \(N_2\leq N\), \(q_3\mid m/q_0\), and
  divisor bounds for \(m,\lambda,\widetilde\lambda,w_1\). All of these
  remain true for squarefree polynomial-size \(m\); neither smoothness of
  \(m\) nor \(\Delta^*=\Delta_1\) is invoked.
- The exponential estimate (1504--1542) needs the two shifted-smooth
  sequences, squarefree polynomial-size \(m\), and a congruence modulus
  dividing \(m\). Section 7.6 proves the required squarefree
  strengthening of its second bound. If one of its positive scales is
  \(<1\), the corresponding compactly supported integer sum contains
  \(O(1)\) terms and the same second bound follows trivially; otherwise
  Polymath's \(N\geq1\) trace-function statement applies directly.
- The gcd normalization and final comparison (1548--1719) carry the
  factor \(\Delta_1/\Delta^*\) without alteration, and use only the
  displayed ranges for \(m,\Lambda,\Delta_1,H\). Sections 7.2 and 7.4
  check each of those ranges with its \(q_0\)-power retained.

This is the promised lemma-by-lemma check: there is no downstream appeal
to the false equality beyond the three final inequalities that are
repaired next.

### 7.4 Restore the original \(\Delta^*/\Delta_1\) factors

Before the false specialization, the three right sides in Stadlmann 2026
1004--1006 must be multiplied by \(\Delta^*/\Delta_1\), as in
Stadlmann 2023 lines 1677--1679.

- In the first inequality this ratio cancels against the
  \(N\Delta^*/m\) on the left.  Lines 1008--1016 remain valid and give
  \(8\omega+4\delta+2\gamma<1\).
- The second inequality is implied by

  \[
   \frac{x^{\delta+131e}}{q_0^2\Delta^*}
   \max\{q_0^2x^{\delta+10e}H^5,H^6\}\ll1.                 \tag{IIc-2}
  \]

- Using
  \(m\ll q_0x^\delta MH^2/(g\Delta_1)\), the third is implied by

  \[
   \frac{x^{1+2\delta+131e}}
        {q_0N^2\Delta^*\Delta_1}
   \max\{q_0^2x^{\delta+10e}H^7,H^8\}\ll1.                 \tag{IIc-3}
  \]

Now use \(\Delta^*,\Delta_1\gg L_\Delta\) and the exact bound

\[
 H\ll\frac{x^{4\omega+\delta+7e}}{q_0}.
\]

In (IIc-2), the two maximum branches are respectively

\[
 \ll q_0^{-5}x^{28\omega+10\delta+245e-\gamma},
 \qquad
 \ll q_0^{-8}x^{32\omega+10\delta+242e-\gamma}.
\]

Thus \(32\omega+10\delta-\gamma<0\) suffices for small enough \(e\).
In (IIc-3), the two
branches are respectively

\[
 \ll q_0^{-6}x^{1+44\omega+16\delta+328e-4\gamma},
 \qquad
 \ll q_0^{-9}x^{1+48\omega+16\delta+325e-4\gamma}.
\]

For completeness, the unsimplified substitutions are

\[
 \frac{x^{2\delta+186e}H^2}{N}
 \max\{q_0^2x^{\delta+10e}H^5,H^6\}
\]

for (IIc-2), and

\[
 \frac{q_0^3x^{1+4\delta+241e}H^4}{N^4}
 \max\{q_0^2x^{\delta+10e}H^7,H^8\}
\]

for (IIc-3).  These displays account for every \(H\)- and
\(q_0\)-power.  Thus \(48\omega+16\delta-4\gamma<-1\) suffices for
small enough \(e\).  These are exactly the second and third conditions
in the IIc lemma, and every discarded \(q_0\)-power is favorable.

The first inequality has the explicit bound from 2026 line 1014

\[
 x^{-1+8\omega+3\delta+100e}N^2.
\]

It follows from \(8\omega+4\delta+2\gamma<1\) once \(100e<\delta\).

### 7.5 Exact C10 scalar margins and choice of \(e\)

For the C10 IIc invocation, the width parameter in this lemma is

\[
 \delta_c=\frac{25000001}{2500000000},\qquad
 0\leq\omega_0\leq\omega=\frac{2747}{300000}.
\]

With \(h=10^{-10}\),
\(\gamma_{\min}=2/5-h\), and
\(\gamma_{\max}=1/3+8\omega+(7/3)(1/100)+3h\), the exact worst-face
reserves are

\[
\begin{aligned}
 \mu_1&=1-(8\omega+4\delta_c+2\gamma_{\max})
       =\frac{403599967}{15000000000},\\
 \mu_2&=\gamma_{\min}-(32\omega+10\delta_c)
       =\frac{209599877}{30000000000},\\
 \mu_3&=4\gamma_{\min}-48\omega-16\delta_c-1
       =\frac{1199983}{2500000000}.
\end{aligned}
\]

Choose the source parameter \(e\) so small that

\[
 100e<\mu_1,\qquad 245e<\mu_2,\qquad 328e<\mu_3,
\]

and also \(e<10^{-100}\delta_c\) and all C10 endpoint reserves.
Definition 3 permits every sufficiently small \(e\), so the simultaneous
choice is legitimate.  The first, second, and third repaired estimates
then have strictly negative exponents.  This removes every \(O(e)\)
placeholder from the C10 IIc verification.

### 7.6 Smooth modulus versus squarefree modulus

The original Stadlmann 2023 exponential lemma at lines 1504--1509 is
stated for \(m\mid P(x^\delta)\), but the IIc argument uses only its
second bound.  Polymath8a's corresponding bound is lines 8407--8414.
For \((\alpha l,m)=1\), its proof at lines 8710--8743 is completion plus
the squarefree trace bound at lines 6534--6562.  Dense divisibility first
appears at lines 8761--8773, solely for the other, unused first bound.

The reduction of a general \((\alpha l,m)\) at lines 8781--8874 also
preserves this distinction.  Although line 8790 notes dense divisibility
of \(m'=m/(\alpha l,m)\), the second displayed estimate at lines
8845--8850 invokes only the already proved squarefree second bound.
The inclusion--exclusion and CRT count at lines 8810--8874 need only
squarefreeness.  Finally, Stadlmann 2023's congruence-class version at
lines 1516--1542 uses only that \(m\) is squarefree, so
\(m=q(m/q)\) with coprime factors.

Therefore the exact input needed downstream is:

> \(m\) is squarefree and of polynomial size; the two coefficient
> sequences are shifted smooth; the indicated congruence modulus divides
> \(m\).

The new IIc construction satisfies all three.  The 2026 paper should have
stated this strengthened exponential lemma explicitly rather than saying
only that summation restrictions are replaced.

## 8. Type III: complete C10 hypothesis and exponent audit

### 8.1 Sequence and scale hypotheses

Polymath8a Definition 2.6 (952--971) requires arbitrary coefficient
sequences \(\alpha,\psi_1,\psi_2,\psi_3\), with smoothness imposed only on
\(\psi_1,\psi_2,\psi_3\).  Its theorem restatement at line 6872
accidentally calls \(\alpha\) smooth.  The proof itself follows the
definition: \(\alpha(m)\) remains an arbitrary coefficient at lines 7173,
7261, 7375, 7486 and 7533; every Fourier transform and derivative estimate
is applied to a \(\psi_i\).  The Cauchy and divisor estimates use only the
coefficient-sequence bound for \(\alpha\).  Thus the C10 residual
convolution need not be smooth or Siegel--Walfisz.

Put

\[
 \gamma_3=\frac12-\sigma=\frac25-s,
 \qquad \sigma=\frac1{10}+s,
 \qquad s=10^{-11}.
\]

The Polymath scale conditions at 953--965 and 6861--6870 become exactly

\[
 N_i\gg x^{1-2\gamma_3},\qquad
 N_i\ll x^{\gamma_3},\qquad
 N_iN_j\gg x^{1-\gamma_3}.
\]

Indeed \(1-2\gamma_3=2\sigma\),
\(\gamma_3=1/2-\sigma\), and
\(1-\gamma_3=1/2+\sigma\).  These are precisely the three-atom outcome of
the primary Facts/combinatorial lemma, and its Vinogradov inequalities
permit equality at an exponent endpoint.  The upstream C10 separation
from the neighboring cases has exact positive margins

\[
 \frac{11}{50000000000},\qquad
 \frac{11}{100000000000},\qquad
 \frac{11}{100000000000}
\]

for the individual lower, individual upper and pair thresholds,
respectively, as reconstructed by `c10_audit_exact.py`.  Each \(N_i\) is a
fixed positive power of \(x\), hence tends to infinity; the product-scale
identity \(MN_1N_2N_3\asymp x\) and the uniform coefficient bounds come
from the same Facts lemma.  Definition 3's residue is coprime to every
prime at most \(x\), so it is primitive for every bounded Polymath set
\(I\).

### 8.2 The only two modulus-factorization uses

Dense divisibility enters the primary Type-III proof only at Polymath8a
7345--7347, to infer membership of \(d=q/b\) in a divisible class, and at
7469--7479, to split that \(d\) at the selected scale.  Stadlmann 2026
1044--1049 replaces both uses as follows.  If the squarefree modulus has

\[
 q=rs=bd,
\]

then squarefreeness gives

\[
 d=\frac r{(r,b)}\frac s{(s,b)}.
\]

Thus, if

\[
 S=x^{1/3+4\delta_3/3-4\omega_*/3},
\]

the first factor lies strictly between
\(S/(b x^{\delta_3})\) and \(S\).  This is exactly the factorization used
after Polymath line 7469; no later line asks that \(d\), or either factor,
be densely divisible.  Squarefreeness supplies the CRT and coprimality
used at 7349--7419.  The modulus weight \(\eta'_{bd}\) is already arbitrary
and bounded at 7372--7439, so restricting it to the C10 subset changes no
coefficient hypothesis.

The primary proof requires \(1\leq S\leq x^{\delta_3}Q/2\).  Using the
lower range \(Q\gg x^{1/2-e}\), the two strict exponent conditions are

\[
 4\omega_*-4\delta_3<1,
 \qquad 2\delta_3-8\omega_*<1.
\]

For

\[
 \delta_3(\omega_*)=
 \frac12-\frac72\omega_*-\frac98\gamma_3-h,
 \qquad h=10^{-10},
\]

their exact left-over margins \(1-4\omega_*+4\delta_3\) and
\(1-2\delta_3+8\omega_*\) are respectively

| \(\omega_*\) | first margin | second margin |
|---|---:|---:|
| \(0\) | \(239999999929/200000000000\) | \(360000000071/400000000000\) |
| \(2747/300000\) | \(207035999929/200000000000\) | \(414940000071/400000000000\) |

The original sufficient side condition
\(\omega_*<1/12\) also holds, with worst-case margin
\(22253/300000\).  Hence even if one retains that stronger original
hypothesis rather than deriving only what the amended proof uses, C10 is
inside it.

### 8.3 Corrected final exponents and exact C10 reserves

Stadlmann 2026 lines 1063--1077 copy the primary Cauchy/trace-function
calculation.  After inserting the fixed \(S\), the three exponents that
must be below \(1\) are

\[
 \frac23+\frac73\omega_*+\frac34\gamma_3+
       \frac23\delta_3,
\quad
 \frac13+\frac83\omega_*+\frac32\gamma_3+
       \frac13\delta_3,
\quad
 \frac23+\frac73\omega_*+\frac34\gamma_3-
       \frac1{12}\delta_3.
\]

The `-5/6` in line 1082 is therefore a transcription error: the third
constant is `+2/3`, as already printed at line 1077 and used at line 1088.
Multiplying the three strict inequalities by \(12,6,12\), respectively,
gives

\[
\begin{aligned}
 28\omega_*+9\gamma_3+8\delta_3&<4,\\
 16\omega_*+9\gamma_3+2\delta_3&<4,\\
 28\omega_*+9\gamma_3-\delta_3&<4.
\end{aligned}
\]

The first implies the second and third because \(\omega_*,\delta_3\geq0\).
At both \(\omega_*=0\) and
\(\omega_*=2747/300000\), the exact reserve in the first inequality is

\[
 4-(28\omega_*+9\gamma_3+8\delta_3)
 =\frac1{1250000000}.
\]

For completeness, the reserves in the second inequality are
\(120000000107/400000000000\) and
\(87036000107/400000000000\), and those in the third are
\(360000000001/800000000000\) and
\(129252000001/800000000000\), at the two endpoints in that order.
The source estimate has an \(x^{3e}\) prefactor and targets
\(x^{1-3e}\), so it costs \(6e\) in exponent. Here \(e=e_{\mathrm s}\)
is already the enlarged source parameter. The choice in Section 5 gives
\(e<h/1000\), so \(6e\) is strictly below the smallest exponent
reserve \((1/1250000000)/12=1/15000000000\).

Finally, the open fixed-factor interval is shrunk inward by \(h\) at each
endpoint before applying the C10 partition lemma.  Its remaining width
over the support increment is

\[
 \frac{31999999769}{800000000000}
 \quad(\omega_*=0),\qquad
 \frac{19083999307}{2400000000000}
 \quad\left(\omega_*=\frac{2747}{300000}\right).
\]

Thus sharp endpoints, finer-than-dyadic localization, smoothness,
squarefreeness, fixed-factor availability, and every final exponent are
all discharged for the specialized C10 Type-III use.

## 9. Baker--Irving comparison and the excluded role-swap gap

Baker--Irving's new exponential Lemma (TeX 157--235) assumes a smooth
\(\beta\) and an arbitrary coefficient \(\alpha\). Its derived Type-I
Lemma at 266--289 additionally assumes that \(\alpha\) is
Siegel--Walfisz.  Stadlmann 2026 lines 611--629 omit this latter hypothesis.

The omission is fatal to the proof of the middle branch at Stadlmann 2026
940: after swapping the roles of \(\alpha\) and \(\beta\), Type IIa requires
the new second factor--the original \(\alpha\)--to be Siegel--Walfisz.
Nothing in the printed statement supplies that.

A smallest explicit hypothesis counterexample is

\[
 \alpha(m;x)=1_{M\le m\le2M}\,1_{m\equiv1\pmod3}.
\]

It is a coefficient sequence at scale \(M\), but for modulus \(3\) and
class \(1\), its discrepancy from the coprime average is
\(\asymp M\), not \(O_A(M\log^{-A}x)\). Taking the original \(\beta\)
to be any smooth scale-\(N\) bump satisfies the printed 2026 assumptions
but does not permit the role-swapped IIa invocation.

This is a genuine gap in the universal Baker--Irving lemma as printed in
2026, not a counterexample to its conclusion.  It is irrelevant to C10:
the long-factor branch is handled directly as Type 0, the central branch
uses IIa/IIb/IIc with a Facts-lemma SW aggregate, and the remaining branch
uses Type III.

## 10. Modulus class, squarefreeness and dyadic coverage

The following exact scope restrictions are all met in C10.

- Definition 3 sums only squarefree relevant moduli.  Every use of CRT,
  lcm factorization, and the trace-function estimates is therefore within
  its squarefree hypothesis.
- The arbitrary sets \(\mathcal Q,\mathcal R\) in the alternative Theorem
  5.8 may encode the C10 factor windows.  No density property is used after
  the indicated factor extraction.
- For IIc the notation \(\mathcal Q(Q,R)\), \(\mathcal R(Q,R)\) depends on
  the dyadic pair, whereas the alternative lemma writes the dependence
  schematically as \(\mathcal Q(Q)\), \(\mathcal R(R)\). The proof fixes
  \(Q,R\) before defining the sets, so this extra bookkeeping dependence is
  harmless.
- The near-square-root strip is eventually contained in every fixed
  \(q\ge x^{1/2-e_1}\) range used by the support partition. Below
  \(x^{1/2}\log^{-B}x\), bilinear BV applies. These two ranges overlap,
  so no modulus gap is hidden at the boundary.
- Above the square root, finer blocks have
  \(\omega_0\in[0,\omega]\). The source estimates are uniform because all
  C10 inequalities have fixed reserve; no negative-\(\omega_0\) branch is
  needed.

## 11. Explicit source defects and disposition

| defect | smallest failure | disposition for C10 |
|---|---|---|
| Polymath8a 1578 is only per-modulus | summing it naively over \(x^{1/2}\) moduli loses a factor \(x^{1/2}\) | repair by the boundary \(L^2\)/Cauchy calculation in Section 4 |
| 2026 exact dyadic endpoints use one epsilon label | a dyadic lower endpoint may be half the given strict factor | use target \(e\), internal \(e'=5e/4\), Section 5 |
| 2026 Corollary-4.16 restatement omits \(N\le[d_1,d_2]^{O(1)}\) | formal statement is broader than the primary corollary | large C10 \(r\)-factor implies it |
| 2026 line 967 has `100e` versus `52e` | incompatible definitions in the same proof | use `52e`, as in the lemma statement, \(\mathcal R\), and line 994 |
| 2026 line 987 writes \(q_1=u_1v_2\) | \(v_2\) has not been defined as that complementary factor | replace by \(v_1\) |
| 2026 line 996 says the revised \(D\) no longer depends on \(q_0\) | lines 994--995 display an explicit \(q_0^{-2}\) factor | replace “no longer” by “now”; downstream displays already use the \(q_0\)-dependent scale |
| 2023/2026 definitions allow signed \(\Lambda\) but print \(N/(\Lambda x^{5e})\) | the alleged positive scale is negative when \(\Lambda<0\) | use \(N/(\lvert\Lambda\rvert x^{5e})\) everywhere a scale or upper bound is meant |
| 2026 line 1000 asserts \(\Delta^*=\Delta_1\) | ratio \(x^{45e-\delta}\to0\) in an allowed range | retain the minimum and use Section 7 |
| 2026 line 1034 drops \(q_0^2\) | its stated lower bound for \(\Delta_1\) is false when \(q_0>1\) | use the \(q_0\)-exact inequalities (IIc-2), (IIc-3) |
| 2026 line 1044 cites Type II inside Type III | wrong label | read as Type III |
| 2026 line 1082 has `-5/6` | contradicts 1077 and 1088 | replace by `+2/3` and verify all three inequalities as in Section 8.3 |
| Polymath8a 6872 calls \(\alpha\) smooth | contradicts its Definition 2.6; proof never uses it | definition and proof justify arbitrary coefficient \(\alpha\) |
| 2026 Baker--Irving middle branch swaps a non-SW \(\alpha\) | explicit mod-3 sequence in Section 9 | route is excluded from C10 |

None of the repaired rows above is allowed to disappear behind a bare
citation to the 2026 lemma statement.  Sections 4--8 give the repairs that
must be incorporated into the polished analytic proof; the last row records
an excluded route rather than a repair used by C10.

## 12. Restricted final verdict

Subject to the already separate exact C10 support-partition verification,
the following specialized statement is justified by the pinned primary
sources and the explicit repairs above:

> Every complete localized convolution arising from the \(K=10\)
> Heath--Brown decomposition in the C10 proof has the required
> equidistribution over its assigned squarefree relevant-modulus subclass.
> The sum of the boundary errors caused by restoring the sharp interval is
> \(O_A(x\log^{-A}x)\). The estimates are uniform over every C10
> \(\gamma\)-interval and \(\omega_0\in[0,\omega]\).

There is no remaining deep-distribution blocker for the specialized C10
route.  This verdict does **not** validate Stadlmann 2026's Baker--Irving
lemma in its full printed generality, and it does not permit a proof to cite
the false \(\Delta^*=\Delta_1\) assertion.

### Statements that still need to be carried into the final proof/audit

1. The global sharp-cutoff boundary calculation, rather than Polymath line
   1578 alone.
2. The target/internal epsilon distinction for stripping and dyadic
   localization.
3. The omitted \(N\le[d_1,d_2]^{O(1)}\) check in both IIa and IIb.
4. The IIc strengthening of the Polymath second exponential bound from
   smooth to arbitrary squarefree polynomial-size \(m\), with the cited
   proof lines.
5. The corrected IIc minimum calculation (IIc-2), (IIc-3), including all
   \(q_0\)-powers.
6. The Type-III arbitrary-\(\alpha\) proof reading and the
   `-5/6` \(\to\) `+2/3` transcription repair.
7. An explicit sentence excluding the 2026 Baker--Irving lemma from the
   C10 dependency graph.

The classical bilinear Bombieri--Vinogradov theorem is used in the exact
form stated by Polymath8a 1043--1049, which in turn cites
Bombieri--Friedlander--Iwaniec.  A final source manifest may add that
underlying paper for maximal bibliographic completeness, but no new
hypothesis beyond the stated positive-power scale and SW property is being
silently used here.
