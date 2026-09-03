# Wide C722 volume-ramp support: hostile analytic audit

## Verdict

**AUDIT PASS**, for every analytic hypothesis of Stadlmann's Proposition 1.
This verdict is separate from the high-plateau p=.172 audit and proves no
sieve quotient.

Keep

\[
k=48,\quad \varepsilon=\frac3{400},\quad
\delta=\frac{361}{50000},\quad
(A_0,A_1,A_2)=\left(-\frac3{400},\frac14,\frac{3121}{12000}\right),
\]

and the inner schedule \(B_{1,m}=103/400\).  The independently audited outer
schedule here is instead

\[
\boxed{B_{2,m}=\min\left\{\frac{49}{625}+(m-1)\delta,
                              \frac{1599}{10000}\right\}.}
\]

Its active counts are \(0,\ldots,22\), count 23 is the first empty count,
and its final value is extended constantly through
\(\lfloor1/\delta\rfloor=138\).  It must not be conflated with the p=.172
schedule, whose start, plateau, active inventory, fixed-pair count, and IIc
cell count are all different.

## Frozen executable artifacts

The standalone schedule-specific verifier is
[`verify_wide_c722_volume_ramp_analytic.py`](verify_wide_c722_volume_ramp_analytic.py).
It pins the frozen common source engine by full hash and then replaces only
the outer schedule; it reruns every schedule-dependent fixed and dynamic
packing check from rational inputs.  It imports neither producer checker.

Run from `prime-gap-236/`:

```bash
python3 agents/audit/verify_wide_c722_volume_ramp_analytic.py
python3 -O agents/audit/verify_wide_c722_volume_ramp_analytic.py
```

Both commands exit zero and produce byte-identical output.  The immutable
output is
[`results/wide_c722_volume_ramp_analytic_audit.json`](results/wide_c722_volume_ramp_analytic_audit.json).
The manifest pins the common independent analytic checker `b0a972af...`,
the repaired generic producer `ffe1904e...`, its volume artifact
`3517533f...`, Stadlmann's TeX `c0d5d231...`, Polymath8a's TeX
`fdffe1df...`, the C10 deep repair audit `f9ced080...`, and the
Proposition-1 repair audit `050702e3...`.

## Schedule-dependent reconstruction

All 138 Definition-1 inequalities and all empty count polytopes are checked
exactly.  The ordered band exponents are unchanged:

\[
\frac12,\qquad \frac{6121}{12000},\qquad
\frac{6121}{12000},\qquad \frac{3121}{6000}.
\]

The verifier uses the proved minimal-crossing-prefix lemma from the separate
high-plateau audit.  It evaluates the IIa, repaired IIb, and corrected Type
III capacities for every schedule-dependent pair:

| family | ordered pairs | branch checks | least exact slack |
|---|---:|---:|---:|
| mixed | 827 | 2,481 | \(30549997/7500000000\) |
| transpose | 827 | 2,481 | \(30549997/7500000000\) |
| outer, fixed \(\omega=121/12000\) | 528 | 1,584 | \(11819999869/600000000000\) |
| outer, near \(\omega=0\) | 528 | 1,584 | \(75949999/2500000000\) |

In IIb it uses the true uniform third capacity

\[
C_3=2\omega+\delta
 <2\omega+\delta+\frac27h,
\]

not the invalid value obtained at the upper gamma endpoint.  Every listed
margin remains positive after that correction.  The \((0,0)\) count pair is
the trivial empty partition.

For outer IIc use exactly the same independently derived open-endpoint
repair as in the high-plateau audit:

\[
h=10^{-10},\quad r_0=h/10,\quad 0<\zeta\le h/1000,
\quad d_c=\delta+h/4.
\]

The shrunken source windows retain width \(\delta+h/20\).  Their actual four
Lemma-13 capacities exceed the rational cell capacities by, respectively,
\(271h/500,447h/500,5h/4,h/5\).  A \(16\times16\) exact rational grid in
\((\gamma,\omega_0)\), with adverse affine endpoints on each cell, and all
528 ordered nonempty count pairs gives

\[
528\cdot256=135168
\]

universal continuous prefix certificates.  The least exact slack is

\[
\boxed{\frac{629999}{8000000000}}>0
\]

at count pair \((12,12)\), cell \((14,3)\).  These are certificates for all
tuples in each \(\Xi\), not sampled tuples.  Adjacent closed cells cover the
complete IIc parameter rectangle.

## Source-level range assignment

The disjoint modulus cover is the one independently repaired in
[`WIDE-C722-P172-ANALYTIC-AUDIT.md`](WIDE-C722-P172-ANALYTIC-AUDIT.md),
and every schedule-dependent premise of it was rerun here:

1. inner/inner is wholly below the classical BV level;
2. mixed moduli below \(x^{1/2}\log^{-L}x\) use bilinear BV, while all
   larger mixed moduli use fixed \(\omega=121/24000\); mixed IIc is empty;
3. outer moduli below \(x^{1/2}\log^{-L}x\) use bilinear BV; the remaining
   moduli through \(x^{1/2}\) use the checked \(\omega=0\) IIa/IIb/III
   partitions, where IIc is empty; moduli above \(x^{1/2}\) use fixed
   \(\omega=121/12000\) and the full dynamic IIc cover.

The threshold ranges meet and have no gap for large \(x\).  Type 0 is
directly power-saving everywhere.  The exact HB trichotomy, sharp-cutoff
repair, target/internal epsilon separation, omitted Corollary-4.16 side
condition, repaired IIc minimum with all \(q_0\)-powers, arbitrary-squarefree
second exponential estimate, and corrected Type III theorem are used only
in the forms proved by the pinned primary-source audit.  The Baker--Irving
role swap is excluded.

The four ordered band pairs and finitely many count pairs transfer to
Definition 3 by restricting its nonnegative absolute discrepancy; duplicate
representations only overcount.  Prime-power removal is power-saving at
outer exponent \(3121/6000\).  Therefore

\[
\rho(n;x)=\frac{\log n}{\log(3x)}1_{\mathbb P}(n)1_{[x,2x]}(n)
\]

satisfies all Proposition-1 hypotheses with \(c_1=c_2=0\) and
\(\beta=1/2>103/400\), after the pinned Proposition-1 repairs.

## Restricted conclusion

The volume-ramp support is analytically admissible for Proposition 1.  An
exact \(k=48\) quotient above one and a final theorem-level audit remain
necessary for \(H_1\le236\).
