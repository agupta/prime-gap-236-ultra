# General-minorant route: the `K` repair and a quantitative obstruction

Status: **active but not presently theorem-usable** (2026-09-02).

This note separates a recoverable typo in Definition 5 from the substantially
harder task of proving and exploiting the signed-minorant version of Proposition
1.  Nothing here is a `k=48` certificate.

## 1. What the source actually says

In the v1 TeX, Definition 5's displayed formula for `K` (line 215 of
`sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex`) contains `t'_k` in a
support condition, but neither integrates over `t'_k` nor evaluates either
factor of the integrand at `t'_k`.  It is therefore not a defined integral.

The proof immediately supplies the intended bilinear form.  At lines 296--302
it defines

\[
 K_i(F,G;C)=\int_{\sum_{s\ne i}t_s>C}F(t)G(t)\,dt.
\]

After decomposing `F` into the disjoint total-sum strata `F_j=F 1_{S_j}`, the
proof uses

\[
 \sum_{j,j'}K_i(F_j,F_{j'};
       \max\{A_j-\varepsilon,A_{j'}-\varepsilon\}).                 \tag{1}
\]

Because the strata are disjoint up to null boundary faces,
`F_j(t)F_{j'}(t)=0` almost everywhere when `j != j'`.  Thus (1) reduces to

\[
 \boxed{K_i(F)=\sum_j\int_{S_j\cap
       \{\sum_{s\ne i}t_s>A_j-\varepsilon\}}F(t)^2\,dt.}           \tag{2}
\]

For symmetric `F`, all `K_i` agree.  Formula (2), rather than the malformed
display at line 215, is the only candidate consistent with the subsequent
proof and with the matrix formula in Section 5.  This reconstruction is a
source-text inference and still requires an independent audit before any
`c_2>0` proof can use it.

## 2. Exact one-stratum diagnostic

Take the one-stratum full simplex

\[
 \Delta_\alpha=\{t_i\ge0:\sum_i t_i\le\alpha\},\qquad
 \alpha=A+\varepsilon,
\]

and `F=1`.  Put `eta=A-epsilon` and `v=eta/alpha`.  Then

\[
 I=\frac{\alpha^k}{k!},\qquad
 K_i=\int_\eta^\alpha\frac{s^{k-2}}{(k-2)!}(\alpha-s)\,ds,
\]

so exact integration gives

\[
 \frac{K_i}{I}=1-kv^{k-1}+(k-1)v^k.                               \tag{3}
\]

At `k=48`, Proposition 2 changes discontinuously from `c_2=0` to `c_2=24`
as soon as `xi_2>2/5`.  Hence the negative contribution to the Rayleigh
quotient in this diagnostic is

\[
 48\,c_2\frac{K_i}{I}=1152\{1-48v^{47}+47v^{48}\}.                \tag{4}
\]

All calculations below are exact rational evaluations of (3)--(4):

| `A` | `epsilon` | `K_i/I` (decimal shown only for scale) | penalty |
|---:|---:|---:|---:|
| `77747/300000` | `1/200` | `0.5468897421109179...` | `630.0169829117774...` |
| `779/3000` | `1/100000` | `0.000006675404577723527...` | `0.007690066073537503...` |
| `779/3000` | `1/1000000` | `0.00000006690071529265343...` | `0.00007706962401713674...` |

Thus the advertised Harman minorant cannot simply be inserted into the
current `epsilon=1/200` support: even the constant-simplex diagnostic pays an
enormous `K` penalty.  A viable nonzero-`c_2` construction must either

1. take `epsilon` extremely small, or
2. build `F` with very little `L^2` mass in every upper-coordinate sliver in
   (2).

This is an obstruction to the naive route, not an upper bound for arbitrary
`F`; no trace or pointwise inequality presently rules out option 2.

## 3. A scalar support envelope from Propositions 2 and 3

There is also a useful exact ceiling on how much total-sum room this route can
buy.  The first scalar inequality in condition (II) of printed Proposition 3
is

\[
 \frac{\xi_2}{10}-\frac{32A_n}{10}+\frac8{10}-2h\geq\delta,
 \qquad h=10^{-10}.
\]

Proposition 2 simultaneously requires `17 xi_2 < 7`.  Consequently every
parameter point admitted by those *printed necessary conditions* satisfies

\[
 A_n<\frac{8+7/17-10\delta-20h}{32}
      <\frac{143}{544}=0.2628676470588\ldots .                 \tag{5}
\]

Here `h` is the Harman-decomposition epsilon from Definition 6, not the
support enlargement `varepsilon`.  For comparison, the audited direct-prime
C722 point has

\[
 A=\frac{3121}{12000}=0.2600833\ldots,\qquad
 A+\varepsilon=\frac{3169}{12000}=0.2640833\ldots .
\]

Thus a nonzero-minorant point with a very small support enlargement has no
total-simplex endpoint advantage over C722 even at the unattainable limiting
ceiling in (5).  To exceed C722's endpoint it must take support enlargement
greater than about `0.0012157`; for a constant function at the optimistic
ceiling, already `varepsilon=1/1000` gives the exact diagnostic penalty
`48*24*K/I = 59.3357191230...`.  This still does not rule out functions which
vanish rapidly in the upper sliver, and (5) relies only on the printed scalar
conditions rather than repairing the universal partition statement.  It does,
however, sharpen the next falsification test: any surviving candidate must
demonstrate genuine sliver suppression, not merely a larger simplex endpoint.

## 4. Density term and remaining theorem gaps

Proposition 2 gives `c_1` as two four-dimensional Buchstab integrals and
`c_2=24` for `xi_2>2/5`.  The predecessor's special point `xi_2=0.40481`
proves a total density loss below `2*10^-5`, but a new parameter point needs
its own rigorous outward-rounded or analytic integration.

Before this route can support a theorem, all of the following are mandatory:

- independently audit (2) against every use of `K` in Proposition 1;
- repair the general signed-minorant proof's coprimality/main-term issue noted
  in `PROP1-C2ZERO-AUDIT.md` (the existing audit deliberately covers only
  `c_2=0`);
- certify both `c_1` integrals at the chosen rational `xi_2`;
- prove every Proposition 2/3 equidistribution inequality for the enlarged
  support; and
- reconstruct the `K` quadratic form exactly and retain its negative sign.

## 5. Falsification experiment

The next meaningful experiment is not a blind support enlargement.  Add the
quadratic form (2) to the exact one-stratum or capped evaluator, then solve the
generalized eigenproblem for a small sequence of rational `epsilon` values
near `10^-6` and `xi_2` just above `2/5`.  If the optimized gain in `J` is
smaller than the exact `24 K` loss already at low degree, retire this specific
minorant/support family.  If it survives, audit Proposition 2 before spending
on D12.
