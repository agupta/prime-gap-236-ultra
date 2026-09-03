# Hostile audit of Proposition 1 when \(c_1=c_2=0\)

## Verdict

**PROP1 c2=0 AUDIT PASS WITH REPAIRS.**

This verdict is for the nonnegative, full-density specialization
\(c_1=c_2=0\), not for the printed general signed-minorant statement. The
argument as printed is not literally complete: it contains several index
errors, writes an equality where only a lower bound was proved, applies the
equidistribution definition on a shifted interval without explanation, and
omits the \((m,q)>1\) part of the main term for a rough composite minorant.
There is also an avoidable uniformity gap in the stated tensor approximation.
All of these issues have rigorous repairs in the \(c_2=0\) case. The repairs
below are part of this verdict.

No claim is made here about the \(c_2>0\) argument or about the displayed
definition of \(K\), which is immaterial after multiplication by \(c_2=0\).

## Sources and audit scope

| source | SHA-256 | relevant local lines |
|---|---|---|
| sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex | c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba | Definitions 1--4, 140--217; Proposition 1 and proof, 228--515 |
| sources/polymath8b-1407.4897-src/newergap-submitted.tex | c8d4f06ad222273ee8b192059ee358e4eecb677dfe35839badb5b3fe292fd05d | multiplicative lemma, 1058--1168; non-prime asymptotic, 889--909 and 1170--1189; residue averaging, 1241--1258; coprimality subtraction, 1392--1437; smooth tensor approximation, 1636--1644 and 1729--1733 |

Line numbers below refer to the pinned Stadlmann TeX unless another source is
named. I audited the whole chain from the Proposition 1 statement at line 228
through the final implication at line 515, including its definitions.

## Repairs that must be incorporated

### R1. Truncate the minorant outside its promised interval

The hypotheses at lines 231--235 only bound \(\rho(n;x)\) on \([x,2x]\), but
the proof evaluates \(\rho(n+h_i;x)\), whose argument lies in
\([x+h_i,2x+h_i]\). Before constructing the weight, replace \(\rho\) by

\[
 \bar\rho(n;x)=\rho(n;x)1_{[x,2x]}(n).
\]

When \(c_2=0\), this gives \(0\leq\bar\rho\leq1_{\mathbb P}\) on all
integers. It leaves the mass and Definition 3 equidistribution statements
unchanged and preserves rough support. Thus it loses nothing and makes the
pointwise lower bound and final prime implication valid at shifted endpoints.
Below, \(\rho\) denotes this truncated minorant.

### R2. Make the \(m=0\) relevant-modulus convention explicit

Definition 2 takes a union over \(m,m'=0\), although \(B_{j,0}\) was not
defined. For \(m=0\), omit the corresponding \(B\)-inequality, equivalently
put \(B_{j,0}=0\). This is the natural empty-product convention.

### R3. Replace the fragile tensorization by direct local tensorization

Lines 312--368 first take a \(k\)-fold antiderivative and then invoke a local
Stone--Weierstrass decomposition. The assertion at lines 351--356 that the
discarded \(\mathcal U\times\mathcal U\) contribution is small does not follow
from small overlap measure alone: derivatives of individually localized
tensor factors need not be uniformly bounded as the box width tends to zero.
Polymath8b explicitly adds a uniform absolute-sum condition at lines
1729--1733, but that displayed condition is on the functions rather than all
mixed derivatives needed here.

For \(c_2=0\) there is a clean repair. After the affine retreat and
mollification at lines 291--311, directly approximate every smooth compactly
supported \(F_{3,j}\) by

\[
 G_j(t)=\sum_{l=1}^{L_j}c_{j,l}\prod_{s=1}^k g_{j,l,s}(t_s),                \tag{1}
\]

where every tensor is supported in a rectangle of side \(O(h)\), the
rectangles have bounded overlap, and their downward closures lie in
\(R_k^+(j,\varepsilon_0)\).  Here is an explicit construction.  Take a
nonnegative tensor-product smooth partition of unity
\(\psi_Q(t)=\prod_s\psi_{Q,s}(t_s)\), subordinate to a mesh of such
rectangles covering a fixed compact neighbourhood of
\(\operatorname{supp}F_{3,j}\), and choose \(z_Q\in Q\).  Put

\[
 G_{j,h}(t)=\sum_Q F_{3,j}(z_Q)\psi_Q(t).                                  \tag{1a}
\]

Uniform continuity and \(\sum_Q\psi_Q=1\) give
\(\|G_{j,h}-F_{3,j}\|_\infty=o(1)\).  The support cushion ensures that all
downward closures remain in the required region for small \(h\).  Moreover,

\[
 \sum_Q |F_{3,j}(z_Q)|\psi_Q(t)\leq\|F_{3,j}\|_\infty,                    \tag{1b}
\]

uniformly in \(h\).  Thus (1a) has the asserted form and absolute-sum
control.  Uniform, hence \(L^2\), convergence also gives convergence of every
one-coordinate marginal: on the fixed compact coordinate range the marginal
operator has bounded \(L^2\)-operator norm.

Define one-dimensional sieve functions by

\[
 f_{j,l,s}(t)=\int_t^\infty g_{j,l,s}(u)\,du.                              \tag{2}
\]

Then \(f'_{j,l,s}=-g_{j,l,s}\) and
\(f_{j,l,s}(0)=\int_0^\infty g_{j,l,s}\). The region \(R_k^+\) is downward
closed: if \(0\leq t_s\leq u_s\) and \(u\in R_k^+\), the total sum decreases,
while \(\{s:t_s>\delta\}\) is a subset of \(\{s:u_s>\delta\}\); the
inequalities \(B_{j,r}\leq B_{j,r+1}\leq B_{j,r}+\delta\) give the subset
bound. Thus (2) has product support in \(R_k^+(j,\varepsilon_0)\).

This construction gives exactly

\[
 \mathcal I=\int\left(\sum_jG_j\right)^2,
\]

and its \(J_i\) forms are the bilinear forms of the one-coordinate marginals
of \(G_j\). Classify a rectangle as \(\mathcal L(j,i)\) when the sum of its
upper endpoints in coordinates \(s\ne i\) is below
\((1-\varepsilon_0)(A_j-\varepsilon)\), and as \(\mathcal U(j,i)\) otherwise.
If two \(\mathcal U\)-rectangles for \(j,j'\) intersect the domain below the
larger threshold, the rectangle belonging to that threshold meets a strip of
width at most \((k-1)h\) around its threshold hyperplane. Hence the omitted
\(\mathcal U\times\mathcal U\) bilinear form lies in finitely many such
strips.  Integrating (1b) in coordinate \(i\) bounds the absolute sum of all
corresponding marginal tensors uniformly in \(h\).  The product of two such
absolute sums is therefore bounded on a fixed compact set, while the union
of threshold strips has measure \(O(h)\).  The omitted bilinear form is
accordingly \(O(h)\).

Every pair with an \(\mathcal L\) member is automatically supported inside
the relevant truncated \(J_i\) domain. Therefore the retained
\(\mathcal L\mathcal L+2\mathcal U\mathcal L\) form differs from the target
form by \(o_h(1)\). This proves the approximation needed at lines 259--274,
with no uncontrolled differentiated partition and with \(\mathcal I>0\).
It works simultaneously for all finitely many \((j,i)\).

### R4. Correct variable-index and summation errors

* At lines 262, 349 and 464, replace
  \(\sum_{s\ne i}t_i\) by \(\sum_{s\ne i}t_s\).
* At line 397 replace \(F_k(0)G_k(0)\) by
  \(F_{i_0}(0)G_{i_0}(0)\). The proof has set \(i_0=k\).
* At line 504 replace \(f_{j,l,k}(0)f_{j',l',k}(0)\) by
  \(f_{j,l,i}(0)f_{j',l',i}(0)\).
* At lines 409 and 417, sum only over \(d_r,d'_r\) with \(r<k\), or impose
  \(d_k=d'_k=1\). The displayed unused summations would otherwise be infinite.
* The symbol \(n\) is used for both the sieved integer and the number of
  support strata. Rename the latter; the maximum in hypothesis (3) is over
  support strata.
* The product at line 363 has repeated \(i\)-indices; it should have
  \(f_{j,l,s}(t_s)\). This lies in the unused \(K\)-part here.
* Repair the missing brace in \(|\mathcal A|\) at lines 447 and 452.

### R5. Restore the omitted coprimality subtraction

Definition 3 supplies the average

\[
 \frac1{\phi(q)}\sum_{(m,q)=1}\rho(m;x),
\]

but line 417 replaces it by unrestricted mass. This is automatic for a prime
of size about \(x\), but not for a rough composite. Polymath8b separates this
term as \(\Sigma_2\) at lines 1399--1405 and bounds it at lines 1430--1437.

Here \(0\leq\rho\leq1\). If \((m,q)>1\) on its support, some prime
\(p>x^\beta\) divides both \(m\) and a divisor variable forming \(q\). Taking
absolute values, using divisor-bound multiplicity and
\(1/\phi(q)\ll x^{o(1)}/q\), the omitted contribution is

\[
\begin{aligned}
 E
 &\ll x^{o(1)}\sum_{p>x^\beta}\frac{x}{p}
       \sum_{\substack{q\leq x\\p\mid q}}\frac{\tau(q)^{O(1)}}q \\
 &\ll x^{1+o(1)}\sum_{p>x^\beta}\frac1{p^2}
  \ll x^{1-\beta+o(1)}.                                                    \tag{3}
\end{aligned}
\]

Since \(\beta>\max_jB_{j,1}>0\), (3) is
\(o(x\log^{-C}x)\) for every fixed \(C\), hence negligible at the sieve
scale. With this subtraction restored, the unrestricted mass in hypothesis
(4) may be factored out before applying Polymath8b's multiplicative Lemma
4.1 (label mul-asym, lines 1058--1168).

### R6. Reduce the shifted interval to Definition 3

Lines 417, 421 and 443 use \([x+h_k,2x+h_k]\), whereas Definition 3 only
asserts equidistribution on \([x,2x]\). With R1, changing either progression
sum or coprime average changes it by \(O_{\mathcal H}(1)\) for each modulus.

This is summable because relevant moduli have a fixed power saving. For the
parameter \(\varepsilon_0/2\) used at line 429, Definition 2 gives

\[
 q\leq x^\theta,\qquad
 \theta=2(1-\varepsilon_0/2)A_n<1,                                         \tag{4}
\]

because \(A_n<1/2-\varepsilon\). There are at most \(x^\theta\) relevant
moduli. The endpoint discrepancy is \(O(x^\theta)\), or
\(O(x^\theta\log^{O(1)}x)\) with a fixed divisor-power weight. Both are
\(O_C(x\log^{-C}x)\) for every fixed \(C\). Thus Definition 3 applies after
this endpoint reduction. Shifted total mass differs by \(O_{\mathcal H}(1)\).

### R7. State the exact relevant-modulus mapping and boundaries

For a nonzero term, the \(W\)-trick makes the lcms pairwise coprime and
coprime to \(W\), so

\[
 q=W\prod_{r\ne i_0}[d_r,d'_r]
\]

is squarefree. On the side in \(\mathcal L(j,i_0)\), put divisor variables
exceeding \(x^\delta\) into \(f_1,\ldots,f_m\), and the rest with \(W\) into
\(e\). On the other side use \(d'_r/(d_r,d'_r)\), putting its large factors
into \(f'_s\) and the rest into \(e'\). The downward-subset property of the
\(B\)'s gives both \(B\)-bounds. The \(\mathcal L\) bound and full \(R_k^+\)
bound give the total-size bounds. Since \(\log_xW=o(1)\), the shrink changes
from \(\varepsilon_0\) to \(\varepsilon_0/2\), as required by Definition 2.
If an \(\mathcal L\) tensor is nonzero, \(A_j-\varepsilon>0\), so this
absorption has a positive margin.

Use \(d>x^\delta\), not \(d\geq x^\delta\), in this classification.  Work
along any unbounded sequence of real \(x\) for which \(x^\delta\notin
\mathbb N\); the asymptotics are uniform along such a sequence, and disjoint
ranges from it already suffice for the liminf conclusion.  This removes the
only equality case and resolves the mismatch with \(t_i>\delta\) in
Definition 1.  (If equality occurs and \(d=x^\delta\) is composite, it can
instead be put into the smooth factor, but that observation is not needed.)
Interpret \(m=0\) by R2.

Line 429 should conclude membership in
\(Q^*(x;\ldots,\varepsilon_0/2)\), or in a particular fully indexed \(Q\),
not in a \(Q\) whose necessary indices are suppressed.

### R8. Replace the claimed numerator equality by a lower bound

For \(c_2=0\), write the inner sieve expression as \(L_i+U_i\). Since
\(\rho\geq0\),

\[
 (L_i+U_i)^2\rho\geq(L_i^2+2L_iU_i)\rho,                                  \tag{5}
\]

because the discarded term is \(U_i^2\rho\geq0\). Therefore line 508 is not
an equality. Its corrected form is

\[
 \sum_i\sum_n\nu(n)\rho(n+h_i;x)
 \geq\left(\sum_i\mathcal J_i+o(1)\right)
       \frac{xW^{k-1}}{\phi(W)^k\log(x)^k}.                                \tag{6}
\]

R3 makes \(\sum_i\mathcal J_i\) as close as required to the target finite
integral. A lower bound is exactly what the GPY argument needs.

### R9. State denominator positivity and the last implication

The quotient hypothesis entails \(I(F)>0\). R3 preserves the strict margin
and constructs

\[
 \mathcal I=\int\left(\sum_jG_j\right)^2>0.
\]

Polymath8b's non-prime asymptotic makes the denominator
\((\mathcal I+o(1))xW^{k-1}/(\phi(W)^k\log^kx)\), positive for large \(x\).
If \(\sum_i\mathcal J_i/\mathcal I>1+\gamma\), (6) and the denominator
asymptotic give \(\widetilde N>1+\gamma/2\), not merely the ambiguous
\(>1+o(1)\) at line 512. Hence \(N>0\).

Because \(\nu\geq0\), some summand has
\(\sum_i\rho(n+h_i;x)>1\). By R1 and
\(0\leq\rho\leq1_{\mathbb P}\), at least two distinct \(n+h_i\) are prime.
Two primes in an interval of diameter \(h_k-h_1\) force a consecutive-prime
gap no larger than that diameter. Taking disjoint \(x\)-ranges makes these
gaps tend to infinity, so \(H_1\leq h_k-h_1\).

## Line-by-line dependency audit

| TeX lines | audited assertion | result |
|---|---|---|
| 228--242 | Proposition statement and hypotheses | Valid for \(c_1=c_2=0\) after R1 and explicit \(I(F)>0\); repair the shadowed stratum index. |
| 248--277 | finite smooth sieve-weight reduction | Valid after R3. Repair the wrong summand \(t_i\) by R4. |
| 282--307 | stratum split, affine retreat, continuity of \(I,J\) | Valid. Translation is strongly continuous in \(L^2\); the marginal map is bounded on fixed compact support. Half-open/closed faces are null sets. |
| 308--311 | mollification inside strict support | Valid. The affine retreat has positive cushion for \(\varepsilon_2\ll\varepsilon_1\). |
| 312--338 | antiderivative and tensor approximation | The antiderivative and downward closure are valid, but the localization lacks stated uniform derivative control. Replace by R3. |
| 339--368 | identification of forms and discarded \(\mathcal U^2\) | Algebraically correct for \(I,J\) after index fixes, but small measure alone is insufficient. R3 supplies the missing uniform proof. \(K\) is outside this specialization. |
| 369--374 | preservation of strict quotient | Valid after R3: choose approximation error below the positive margin. |
| 380--398 | rough-minorant asymptotic lemma | Correct after \(F_kG_k\to F_{i_0}G_{i_0}\). R1, R5 and R6 are required. |
| 400--410 | divisor expansion and distinguished coordinate | Valid. Rough support and \(B_{j,m}\leq B_{j,1}+(m-1)\delta\) force \(d_{i_0}=d'_{i_0}=1\). Delete dummy sums. |
| 411--415 | \(W\)-trick and primitive residue | Valid for large \(x\): \(w\) exceeds fixed tuple differences, so lcms are pairwise coprime and coprime to \(W\). CRT gives a primitive class and an integer representative avoiding every prime at most \(x\). |
| 416--426 | main/error split and main asymptotic | Incomplete as printed: repair coprime mass by R5 and the shifted interval by R6. Then Polymath8b mul-asym with \(\phi([d,d'])\) gives the displayed normalization. |
| 428--430 | map every modulus into \(Q^*\) | Valid after R2 and R7. The \(W=x^{o(1)}\) factor explains the shrink relaxation. |
| 431--444 | moving residue and \(\mathcal A\) | Valid. For large \(x\), the \(k-1\) differences are distinct and nonzero modulo every \(p>w\); CRT gives exactly \(|\mathcal A|/(k-1)^{\omega(q/W)}\) extensions. R6 handles shifts. |
| 445--454 | Cauchy--Schwarz and Definition 3 | Valid after R6. Definition 3 is uniform in \(a\). Since \(0\leq\rho\leq1\), the divisor-weighted factor is \(O(x\log^{O(1)}x)\). |
| 458--476 | finite approximation reused | Valid after R3/R4; \(\mathcal I>0\) is explicit in R9. |
| 477--490 | \(\nu\) and denominator asymptotic | Valid. Product support gives \(\sum_sS(f_s)<1/2\), so each pair satisfies the strict less-than-one hypothesis of Polymath8b Theorem 3.6. |
| 491--501 | pointwise numerator inequality | Valid for \(c_2=0\) and global nonnegativity from R1; it is (5). |
| 502--509 | termwise asymptotics and numerator | Correct after \(k\to i\), R5/R6, and changing equality at line 508 to (6). |
| 510--515 | ratio, \(N>0\), and \(H_1\) | Correct after R9. Positivity and a fixed quotient margin must precede division. |

## Independent falsification checks

1. **Uncontrolled exterior values.** Without R1, a function satisfying all
   printed hypotheses may be assigned an arbitrarily negative value at
   \(2x+h_i\), invalidating the numerator argument without changing any
   hypothesis on \([x,2x]\).
2. **Coprimality omission.** A rough minorant may be supported on composites
   sharing a prime \(p>x^\beta\) with \(q\). Bound (3), not equality, is
   necessary.
3. **Small-measure fallacy.** Functions on an interval of width \(h\) can
   have derivatives of size \(h^{-1}\); an \(O(h)\)-measure overlap alone
   does not control derivative products. R3 avoids differentiated
   localization.
4. **Equality at line 508.** Taking \(U_i\ne0\) and \(\rho>0\) makes the
   discarded \(U_i^2\rho\) positive, so the equality is false although the
   required lower bound is true.

After R1--R9, no repair leaves an unproved assertion of the same strength as
the desired finite quotient. The remaining inputs are the stated
equidistribution hypothesis and established elementary/Polymath8b sieve
lemmas.
