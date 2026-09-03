# Stadlmann 2026 paper map and dependency audit

Primary line references below are to `sources/stadlmann-2608.31126-src/Bounded_Gaps_2.0.tex` (1,885 lines). The independent full extraction is preserved in `agents/source-fidelity/paper-map.md`; exact parameter calculations are in `agents/source-fidelity/parameter-audit.md` and `baseline_check.py`.

## Definitions

- **Definition 1, support (TeX 140--147).** With `-varepsilon=A_0<A_1<...<A_n<1/2-varepsilon`, `delta>0`, and `delta<B_{j,m}<=B_{j,m+1}<=B_{j,m}+delta`, the region is
  
  ```text
  T_k = union_j {t in [0,1]^k:
    sum(t) in [A_{j-1}+varepsilon,A_j+varepsilon),
    sum_{i:t_i>delta} t_i <= B_{j,#{i:t_i>delta}}}.
  ```
  
  The total upper endpoint and the test `t_i>delta` are strict; the `B` inequality is weak. The adjacent-`B` recurrence is meaningful only through the penultimate column.

- **Definition 2, relevant moduli (TeX 155--171).** `Q*` is the finite union of moduli
  
  ```text
  q=e e' prod_i f_i prod_i f'_i,
  log_x(prod f_i) <= (1-varepsilon_0)B_{j,m},
  log_x(prod f'_i) <= (1-varepsilon_0)B_{j',m'},
  log_x(e prod f_i) <= (1-varepsilon_0)(A_j-varepsilon),
  log_x(e' prod f'_i) <= (1-varepsilon_0)(A_j'+varepsilon),
  ee' x^delta-smooth, log_x f_i,log_x f'_i >= delta.
  ```
  
  The definition includes `m=0` but never defines `B_{j,0}`. Every use here explicitly adopts the empty-product convention `B_{j,0}=0`.

- **Definition 3, equidistribution (TeX 175--184).** For every fixed `varepsilon_0,A>0` and every residue representative coprime to every prime at most `x`, the sum over squarefree `q in Q*` of the absolute progression discrepancy is `O_{A,varepsilon_0}(x log(x)^(-A))`.

- **Definition 5, integrals (TeX 210--217).** `I=int_T F^2`. For a symmetric `F`, `J` is the squared one-coordinate marginal, but only over common coordinates with sum at most `max(A_m-varepsilon,A_m'-varepsilon)`. This `A-varepsilon` cutoff is essential. The printed `K` is ill-formed: `t'_k` occurs in its domain but is absent from its integrand and differential. This does not affect the `c_2=0` route; any nontrivial-minorant route needs a corrected definition and proof.

- **Definition 9, Harman classes (TeX 1103--1114).** `H(xi_1,xi_2,xi_3)` comprises Type I smooth bilinear, Type II Siegel--Walfisz bilinear, and Type III four-fold convolutions. Its `epsilon=10^-10` is distinct from the support enlargement `varepsilon=3/400` and the arbitrary shrinkage `varepsilon_0`.

- **Definition 10, tuple polytope (TeX 1237--1241).** `Xi(B_1,B_2,m_1,m_2,delta)` contains tuples `y_i>=delta` whose first and second group sums are at most `B_1,B_2`.

## Main dependency graph

```text
Section 3 Type I/IIa/IIb/IIc/III distribution lemmas
  <- relaxed Polymath8a Theorem 5.8
  <- Polymath8a Corollary 4.16 and Lemma 1.4
  <- Baker--Irving Type I and Stadlmann 2023 Type IIc arguments
                |
Partition Lemmas 11--13 + exact scalar/partition inequalities
                v
Proposition 3: every f in H equidistributes on Q*
                |
Proposition 2: Harman minorant rho and constants c_1,c_2
                |
Definition 1 support + Definition 3 equidistribution
                v
Lemma 1 (smooth tensor approximation) + Lemma 2 (prime-weight asymptotic)
  <- Polymath8b Lemma 4.1 and Theorem 3.6(i)
                v
Proposition 1: [k(1-c_1)J-kc_2K]/I>1 => H_1<=H(k)
                |
exact Section 5 finite quadratic inequality + admissible tuple
                v
claimed Theorem 1
```

## Proposition 1 (TeX 228--242)

The four hypotheses on `rho` are:

1. `-c_2<=rho(n;x)<=1_P(n)` on `[x,2x]` for all sufficiently large `x`;
2. Definition 3 equidistribution for the chosen `T_k`;
3. every prime factor of a number on which `rho` is nonzero exceeds `x^beta` for one `beta>max_j B_{j,1}`;
4. `sum rho=(1-c_1+o(1))x/log x`.

For a symmetric square-integrable `F` supported on `T_k`, the strict inequality

```text
k(1-c_1)J(F)-k c_2 K(F) > I(F)
```

implies `H_1<=H(k)`. The proposition does not require either matrix to be invertible or positive definite; an exact inequality for one vector is sufficient.

The printed proof is not cited literally.  Its `c_1=c_2=0` specialization has
verdict **PROP1 c2=0 AUDIT PASS WITH REPAIRS** in
`agents/structural-basis/PROP1-C2ZERO-AUDIT.md`.  In particular the selected
route truncates `rho` outside `[x,2x]`, uses a direct bounded-overlap local
tensor approximation, restores the rough-composite coprimality subtraction,
reduces shifted endpoints to Definition 3 with a power saving, and replaces
the source's false numerator equality by a lower bound.  These repairs are
part of the exact proposition version used by the proof.

## Proposition 2 (TeX 1118--1165)

The Harman parameters must satisfy

```text
2xi_1+3xi_2<2, xi_2<=xi_3, xi_1+9xi_2<4,
2xi_1+xi_2>1, 17xi_2<7.
```

At `xi=(19/50,2/5,2/5)`, the two discarded configurations are empty, so `rho=1_P` and `c_1=c_2=0`. A proof sentence says `xi_2<xi_3`, conflicting with the formal weak inequality and the equality used in Section 6; the displayed ranges and `epsilon` slack support the weak endpoint, but this is recorded as a source typo.

## Proposition 3 and repairs (TeX 1397--1741)

The printed general proposition cannot be cited verbatim:

- Type IIc quantifies `omega_0 in [-epsilon,omega]` but gives its fourth bin capacity `8omega_0`; the negative endpoint makes the hypothesis impossible.
- `m=0`/`m'=0` cases from `Q*` are absent from the formal universal quantifier.
- the Type I high-`gamma` proof derives an extra two-bin condition absent from the statement.
- the Type IIc display alternates between `52epsilon` and `100epsilon` in one recalled formula.

`agents/source-fidelity/repaired-proposition3.md` gives a baseline-specific split: bilinear Bombieri--Vinogradov below `sqrt(x)/log(x)^L`, the Section 3 estimates with `omega=0` in the remaining sub-square-root strip (where the Type IIc interval is empty), and the four-factor argument only for `omega_0>=0` above the square root. It also handles both zero-index cases.  The universal repair remains blocked by the high-`gamma` Type-I role-swap defect.  The selected C10 proof instead uses the narrower direct Heath--Brown decomposition and has verdict **C10 ANALYTIC AUDIT PASS WITH REPAIRS** in `agents/hostile-analytic-audit/C10-AUDIT.md`; it tightens the Type-III auxiliary slack and repairs the IIb/IIc endpoints without invoking the defective universal Type-I branch.

The deeper predecessor chain for that specialized C10 use has the separate
verdict **C10 DEEP-DISTRIBUTION AUDIT PASS WITH MANDATORY REPAIRS** in
`agents/structural-basis/C10-DEEP-DISTRIBUTION-AUDIT.md` (SHA-256
`f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd`).
The exact dependency reading is: apply one global sharp-cutoff boundary
$L^2$ estimate; distinguish target and source epsilon parameters; restore
Polymath Corollary 4.16's omitted polynomial-size condition; in IIc use
`52e`, `q_1=u_1v_1`, the $q_0^{-2}$ scale, $|\Lambda|$, and the retained
minimum $\Delta^*=\min\{N/(|\Lambda|x^{5e}),\Delta_1\}$; use only the
squarefree second exponential estimate; and in Type III use arbitrary
residual alpha, the fixed-factor squarefree replacement, and `+2/3` in place
of the printed `-5/6`. The universal Baker--Irving role swap is genuinely
missing an SW hypothesis and remains excluded from the C10 graph.

## Section 5 exact calculation

For a finite explicit list `G_1,...,G_l`, `M_1` represents `I` and `M_2` represents `k(1-c_1)J-kc_2K`. If `F=sum v_iG_i`, the needed certificate is exactly

```text
v M_1 v^T > 0,  v(M_2-M_1)v^T > 0.
```

Numerical generalized eigenvectors are discovery aids only. The checker must reconstruct moments from the support.

The source does **not** resolve the basis convention discrepancy. The introduction says `2a+b<=21` three times; Section 5 explicitly says `B_19`. The source bundle contains no code, vector, or matrices. Moreover, the displayed set `{p(t)^2(1-sum t)^b}` is not itself a finite linear basis as written. Polymath8b supplies the concrete convention used by our experiments: `(1-P_(1))^a P_lambda` with `lambda` having even parts and `a+|lambda|<=D`. This is a defensible independent basis choice, not evidence that the paper's `19`/`21` contradiction has been resolved.

## Published rational point

```text
varepsilon=3/400, A_0=-3/400, A_1=253/1000,
delta=7/250, B_1=B_2=3/20, B_m=17/100 (m>=3),
xi_1=19/50, xi_2=xi_3=2/5, rho=1_P, c_1=c_2=0.
```

All printed scalar inequalities and the corrected baseline partitions are checked exactly by:

```bash
python3 prime-gap-236/agents/source-fidelity/baseline_check.py
```

The analytic conditions do not depend on `k`; the independently audited specialized route applies at `k=48`. The missing target ingredient remains an exact capped quotient above 1 and its final independent reconstruction.
