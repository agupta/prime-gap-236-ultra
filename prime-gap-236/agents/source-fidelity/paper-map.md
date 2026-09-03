# Stadlmann 2026: source-faithful paper map

Line references are to `source-tree/Bounded_Gaps_2.0.tex`. The complete TeX
was read sequentially from line 1 through line 1,885 and compared against the
34-page PDF at every key statement cited here.

## Definitions and notation

### Definition 1: the support (`tex:140--147`)

For `k in N`, `delta>0`, `varepsilon>0`, and

```text
-varepsilon = A_0 < A_1 < ... < A_n < 1/2-varepsilon,
```

the paper takes an `n x floor(1/delta)` array `B=(B_{j,m})` satisfying

```text
delta < B_{j,m} <= B_{j,m+1} <= B_{j,m}+delta
```

and defines

```text
T_k(delta,A,B,varepsilon)
 = union_{j=1}^n {t in [0,1]^k:
       sum_i t_i in [A_{j-1}+varepsilon,A_j+varepsilon),
       sum_{i in L(t)} t_i <= B_{j,|L(t)|}},
L(t)={i:t_i>delta}.
```

Endpoint fidelity matters: the total-sum interval is left closed/right open;
membership in `L(t)` is strict (`t_i>delta`); the `B` bound is non-strict.
The sentence imposing the `B` recurrence says “for any `m>=1`”, although the
matrix has only `floor(1/delta)` columns and `B_{j,m+1}` is then undefined at
the last column. The only coherent reading is to impose the two-sided adjacent
condition through the penultimate column and `delta<B` on every column.

### Definition 2: relevant moduli (`tex:155--171`)

`Q(x;...,j,j',m,m',varepsilon_0)` contains integers

```text
q = e e' prod_{i=1}^m f_i prod_{i=1}^{m'} f'_i in [1,x]
```

such that

```text
log_x(prod f_i)       <= (1-varepsilon_0) B_{j,m},
log_x(prod f'_i)      <= (1-varepsilon_0) B_{j',m'},
log_x(e prod f_i)     <= (1-varepsilon_0)(A_j-varepsilon),
log_x(e' prod f'_i)   <= (1-varepsilon_0)(A_{j'}+varepsilon),
e e' is x^delta-smooth,
log_x f_i, log_x f'_i >= delta.
```

`Q*` is the union over `j,j'` and `0<=m,m'<=floor(1/delta)`.
There is a formal omission: `B_{j,0}` is used when `m=0` but never defined.
The natural empty-product convention requires `B_{j,0}=0`; a rigorous reuse
must state that convention or split out the zero-index cases.

### Definition 3: equidistribution (`tex:175--184`)

For every `x>1`, `varepsilon_0>0`, `A>0`, and integer `a` coprime to every
prime `p<=x`, the required estimate is

```text
sum_{q in Q*, q squarefree}
 | sum_{n in [x,2x], n=a mod q} f(n;x)
   - phi(q)^(-1) sum_{n in [x,2x], (n,q)=1} f(n;x) |
 <<_{A,varepsilon_0} x/log(x)^A.
```

This is a uniform fixed-residue-class statement. The device at `tex:435--453`
averages over a constructed set of globally primitive residue classes to
handle the residue class depending on the divisor tuple.

### Definition 5: the key integrals (`tex:210--217`)

For symmetric square-integrable `F` supported on `T_k`,

```text
I(F) = integral_{T_k} F(t)^2 dt.
```

Writing `s=t_1+...+t_{k-1}`, `J` is the sum over strata `m,m'` of

```text
integral_{s <= max(A_m-varepsilon,A_m'-varepsilon)}
 F(t_1,...,t_{k-1},t_k) F(t_1,...,t_{k-1},t'_k)
 dt_1...dt_{k-1} dt_k dt'_k,
```

with `s+t_k` and `s+t'_k` in their respective stratum intervals.

The printed `K` formula is not a defined integral. Its domain contains the
condition on `s+t'_k`, but the integrand is only `F(t)^2` and neither the
integrand nor the differential list binds `t'_k`. This exact defect appears
in both TeX and PDF. The later proof (`tex:299--325`, `359--368`) indicates
that the intended negative term is a same-variable `L^2` integral over
`s>max(...)`, but the paper never gives one clean corrected formula. The
published specialization has `c_2=0`, so no `K` value is used there. Any
nontrivial-minorant calculation must first state and prove a corrected `K`.

### Other notation

| Symbol | Exact role |
|---|---|
| `varepsilon` | support enlargement; published value `3/400` |
| `epsilon` | a distinct fixed Harman slack `10^-10` in Definition 9 and Proposition 3 |
| `varepsilon_0` | arbitrary positive shrinkage in `Q*` and the sieve-weight approximation |
| `delta` | threshold distinguishing large coordinates and smooth factors |
| `A=(A_0,...,A_n)` | total-sum strata; `A_0=-varepsilon` |
| `B_{j,m}` | budget for the coordinates strictly larger than `delta` |
| `xi_1,xi_2,xi_3` | Type I, Type II, and Type III Harman decomposition cutoffs |
| `c_1` | lost prime density: `sum rho=(1-c_1+o(1))x/log x` |
| `c_2` | lower-bound penalty: `rho>=-c_2` |
| `M_1` | Gram matrix for `I` on a chosen finite list `G_i` |
| `M_2` | matrix intended to represent `k(1-c_1)J-kc_2K` |

Section 5 reuses `c_1` both for the density-loss constant and as the first
coordinate in `F=c_1G_1+...+c_lG_l` (`tex:1762--1770`). A checker should use
different names.

## Formal main propositions

### Proposition 1: GPY criterion (`tex:228--242`)

The four hypotheses on `rho` are:

1. `-c_2 <= rho(n;x) <= 1_P(n)` for all sufficiently large `x` and every
   `n in [x,2x]`.
2. Definition 3 equidistribution for the moduli corresponding to `T_k`.
3. Whenever `rho(n;x)!=0`, every prime factor of `n` exceeds `x^beta` for
   one fixed `beta>max_j B_{j,1}`.
4. `sum_{n in [x,2x]} rho(n;x)=(1-c_1+o(1))x/log x`.

If a symmetric square-integrable supported `F` has

```text
[k(1-c_1)J(F)-k c_2 K(F)]/I(F) > 1,
```

then `H_1<=H(k)`. Strictness is essential. No positive-definiteness or matrix
invertibility hypothesis appears in the proposition.

Its proof depends on:

- Lemma 1 (`tex:248--374`), which shifts, shrinks, smooths, integrates, and
  tensor-approximates `F`, preserving a strict quotient;
- Lemma 2 (`tex:380--455`), the prime/minorant-weight asymptotic;
- Polymath8b Lemma 4.1 for the exact Selberg main-term convolution (including
  its version with `phi([d,d'])` in the denominator);
- Polymath8b Theorem 3.6(i) for non-prime sums. Its exact support hypothesis is
  `sum_i(S(F_i)+S(G_i))<1`. Definition 1 gives this after shrinkage because
  each product support has total sum `<(1-varepsilon_0)(A_j+varepsilon)<1/2`.

### Proposition 2: Harman minorant (`tex:1118--1165`)

It assumes

```text
2 xi_1+3 xi_2 < 2,
xi_2 <= xi_3,
xi_1+9 xi_2 < 4,
2 xi_1+xi_2 > 1,
17 xi_2 < 7,
```

and Definition 3 equidistribution for every convolution in the three Type
classes of Definition 9. It constructs the displayed two-subtraction
minorant, its density loss `c_1`, and

```text
c_2=24 if xi_2>2/5;  c_2=0 if xi_2<=2/5.
```

At `xi_2=2/5` both bad sums are empty under the displayed strict ranges, the
two loss integrals vanish, and `rho=1_P`, `c_1=c_2=0`.

The proof sentence at `tex:1183` says `xi_2<xi_3`, while the formal proposition
(`tex:1126`), the immediately preceding explanation (`tex:1178`), and the
published application (`xi_2=xi_3=2/5`) use `xi_2<=xi_3`. With the `epsilon`
slack in Definition 9, equality is the intended endpoint, but this is an
internal strictness typo that an audit should mention.

### Proposition 3: equidistribution criterion (`tex:1397--1448`)

Its scalar conditions and five universal partition conditions are transcribed
with exact endpoints in `parameter-audit.md`. It is proved from:

- Lemmas 11--13, the two-, three-, and four-factor partition lemmas
  (`tex:1248--1391`);
- the five Section 3 distribution lemmas:
  Polymath Type IIa (`tex:572--588`), Polymath Type IIb (`593--608`),
  Baker--Irving Type I (`611--629`), Stadlmann Type IIc (`633--650`), and
  Polymath Type III (`653--672`);
- a relaxed version of Polymath8a Theorem 5.8 (`tex:690--759`);
- Polymath8a Corollary 4.16, inequality 2, and Lemma 1.4;
- for the Type IIc branch, Stadlmann 2023 Theorem 1 and its detailed proof;
- Bombieri--Vinogradov for the moduli not exceeding the square-root range.

Source-level defects relevant to citing Proposition 3 are:

1. `Q*` includes `m=0` and/or `m'=0`, but Proposition 3 quantifies only over
   `m,m' in {1,...,floor(1/delta)}` (`tex:1412`) and its proof repeats that
   range (`1451`, `1456`). It only calls the `m=m'=0` case trivial and never
   formally handles exactly one zero. The published one-row parameters make
   the omitted cases easier and they can be checked directly.
2. Condition (D) quantifies over `omega_0 in [-epsilon,omega(j,j')]` and asks
   for a fourth bin of capacity `8 omega_0`. At the included negative endpoint
   that capacity is negative, so no partition exists for a nonempty tuple.
   The proof changes the range to `[-varepsilon_0,omega_max]` (`tex:1686`),
   which is a second mismatch. A proved analytic split for the baseline point
   is in `repaired-proposition3.md`: bilinear Bombieri--Vinogradov handles
   genuinely smaller moduli; the near-square-root strip uses the distribution
   lemmas at `omega=0`, where Type IIc is empty; the four-factor lemma is used
   only for `omega_0>=0`.
3. In the Type I proof, the branch `gamma in (1/2,1/2+2 omega+...)` derives an
   additional two-bin condition at `tex:1524--1531`; that condition is not
   present in the formal proposition. It happens to hold for the published
   small total budget (put everything in its first bin), but the proposition
   as a general black box has an omitted hypothesis.
4. The Type IIc modulus definition has `52 epsilon` in the lemma statement
   (`tex:638`) but `100 epsilon` when recalled at the start of its proof
   (`tex:967`), before returning to `52 epsilon` in the constructed set
   (`tex:978`). Proposition 3 quotes the `52` version.

These do not force abandonment of the published parameter point, but they do
mean a new proof should include the short repairs rather than say merely
“Proposition 3 applies.”

## Section 5: what is and is not specified

### Rayleigh quotient

For an explicitly chosen finite list `G_1,...,G_l` and coefficient row vector
`v`, `M_1` is intended to satisfy `v M_1 v^T=I(F)` and `M_2` to satisfy
`v M_2 v^T=k(1-c_1)J(F)-kc_2K(F)`. The particular quadratic inequality is
enough; matrix invertibility and positive definiteness are not required.

The printed `M_2` display (`tex:1765--1767`) has two transcription defects:
the basis index `i` is also used as the omitted coordinate even though the
functions vary in coordinate `k`, and its `K` part repeats the unbound
`t'_k` defect from Definition 5.

### `B_19` versus degree 21

The introduction states `2a+b<=21` three times (`tex:62`, `79`, `90`). Section
5.1 defines

```text
B_D={p(t)^2(1-sum t)^b: p symmetric, deg p=a, 2a+b<=D}
```

and then explicitly says the `H_1<=240` calculation used `B_19`
(`tex:1776`). Under this displayed definition, `B_19` has polynomial degree at
most 19, not 21. There is no offset convention in the TeX, PDF, bibliography,
or arXiv manifest that changes this. Moreover, allowing arbitrary symmetric
`p` makes the displayed set nonlinear and not itself a finite linear basis;
the source never lists the finite `p` representatives.

Polymath8b's actual source convention (Section 7.1, printed pages 57--59) uses
orbit-sum polynomials `P_alpha` indexed by signatures and finite elements
`(1-P_(1))^a P_alpha`, usually restricting `alpha` to even entries. That does
not turn 19 into 21 and is not the same as the literal square of an arbitrary
symmetric polynomial. Therefore the discrepancy is unresolved source data,
not a harmless convention. Any reproduction must declare its own exact
finite basis and should test both cutoffs if attempting to identify the
published run.

### Integration sketch

The source does not provide Section 5's claimed exact recursion. It only says:

- integrals over `T_s(k)=[0,delta]^k` and `T_b(k)=[delta,1]^k`, cut by total
  sum `<=1`, are piecewise polynomials in `delta` of degree at most
  `k+sum a_i+b` (`tex:1783--1796`);
- coefficients are denoted `C_{m,i}` and `D_{m,i}`;
- an auxiliary-`s` substitution is sketched for `b>0`
  (`tex:1799--1810`);
- mixed small/large-coordinate integrals are said to be matrix contractions
  of `C` and `D` (`tex:1813--1834`).

It is not an implementable specification. Specific printed errors include:

1. “`floor(1/delta) in [m,m+1]`” should be `floor(1/delta)=m` (or
   `1/delta in [m,m+1)`).
2. The displayed infinite `l` sum has endpoints that cease to define the
   intended intervals after `l=floor(1/delta)`; no truncation rule is stated.
3. The prose recurrence passes a `(k-1)`-tuple of exponents while retaining
   dimension argument `k`.
4. The mixed region says `v_1+...+v_r<D` although there are `s` variables
   `v_1,...,v_s` (`tex:1817`).
5. The next display uses `b_1+...+b_k` although only `b_1,...,b_s` exist, has
   an apparently reversed strip inequality at `tex:1829`, and calls
   `C(...,c)` inside a sum indexed by `n` at `tex:1830`.

The author explicitly says the full code will be uploaded later
(`tex:1834`); it is absent from v1. Thus an exact implementation must be
derived and independently tested, not transcribed from this section.

## Dependency graph to the claimed theorem

```text
exact finite F quotient + admissible k-tuple
  |
  v
Proposition 1 (strict GPY criterion)
  |-- Lemma 1: epsilon enlargement / tensor approximation
  |-- Lemma 2: rho-weighted asymptotic
  |     |-- Definition 3 equidistribution
  |     |-- Polymath8b Lemma 4.1
  |     `-- the four rho hypotheses
  `-- Polymath8b Theorem 3.6(i): non-prime sums

four rho hypotheses at the published point
  |
  v
Proposition 2 with xi=(19/50,2/5,2/5)
  |-- Harman/Buchstab decomposition from Stadlmann 2023 Section 4
  |-- all f in H(xi) equidistribute on Q*
  `-- xi_2=2/5 => rho=1_P and c_1=c_2=0

all f in H(xi) equidistribute on Q*
  |
  v
Proposition 3, after the endpoint/zero-index/high-gamma repairs above
  |-- partition Lemmas 11--13
  |-- Type I / IIa / IIb / IIc / III distribution lemmas
  |     |-- Polymath8a Theorem 5.8 and Corollary 4.16
  |     |-- Baker--Irving Lemma 5
  |     `-- Stadlmann 2023 Theorem 1
  `-- Bombieri--Vinogradov for q <= x^(1/2)

claimed H_1<=240 in Section 6
  |-- published rational parameter check
  |-- asserted exact k=49 quotient (no data supplied)
  `-- asserted H(49)=240
```

The theorem environment itself contains a typo: it defines `H_1` but states
`H_m<=240` (`tex:58--60`). The abstract, introduction, proof, and final line
all clearly identify the intended claim as `H_1<=240`.

For `H_1<=236`, the analytic parameter chain is unchanged when `k` changes
from 49 to 48. The missing new ingredient is an exact `k=48` quadratic
certificate (plus the 48-tuple check), not a new `k`-dependent parameter
inequality. Every matrix combinatorial factor must nevertheless be rebuilt at
`k=48`.
