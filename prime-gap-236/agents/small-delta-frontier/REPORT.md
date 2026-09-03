# Small-delta direct-Heath--Brown frontier audit

## Status

**ANALYTIC AUDIT PASS** for the constant-cap C70 and C722 supports, and
**EXACT PREFIX AUDIT PASS** for the count-dependent C722 enlargement below.
These statements certify analytic support/equidistribution admissibility;
they do **not** certify a sieve quotient above one and therefore do not prove
`H_1 <= 236` by themselves.

The local degree-2 discovery proxy turns over between `delta=0.00722` and
`0.00723`.  Its best tested constant point is C722.  At that point an exact
count-dependent schedule opens four additional large-coordinate strata and
raises the order-10 proxy from `0.8901049226133916` to
`0.8965312844893856`.  This is only a low-degree heuristic; no high-degree
gain is inferred.

## Primary formulas checked

The reconstruction used the following primary source locations rather than
the preliminary frontier checker:

- Stadlmann 2026 TeX, Definition 1 at lines 140--146, Proposition 1 at
  228--241, the Type-II/III lemmas at 572--669, and Proposition 3 at
  1397--1450;
- Polymath8a TeX, the Heath--Brown identity and finer-than-dyadic
  decomposition at lines 1421--1589, the combinatorial trichotomy at
  1305--1395, the Facts lemma at 1637--1737, and Type 0 at 1780--1863;
- the repaired open-window derivation in
  `../structural-basis/PROOF-DRAFT-C10.md`, Sections 6.3a--7, checked against
  the cited primary formulas.  The fixed parameter names here are
  `h=10^-10`, `sigma=1/10+h/10`, source-lemma
  `zeta<h/1000`, and inward endpoint reserve `r0=h/10`.

Pinned SHA-256 values at this checkpoint are:

| artifact | SHA-256 |
|---|---|
| Stadlmann TeX | `c0d5d2317c77f4de7eacdef6e1d4b1eb6433e6240b5c09273b3d4eee99e6c3ba` |
| Polymath8a TeX | `fdffe1dfb7b820d8a45ecc0e07e2f7e17404e6e10b63db110c2d44afe42013ea` |
| repaired proof draft | `dda2ff3d77e2bb2ff281c6ba7f2f31acda10d9a1497a3a3e68848846d56d090b` |
| deep distribution audit | `f9ced080b78e4f4b82c804b957005b779816531e057cafa351f4e80a581b7cdd` |
| numerical proxy code | `73ed594424037f2537f31aaa5f80ef4f99a0253b9cb1384962658be98d645d66` |
| constant-point exact audit | `b01fb7ca8a571d642c24c5fc016cf112ee4b2d65e13fb719e71739fe0a2c53b0` |
| schedule search | `aca94fc6280dc3f500b00bc1a11a16659bed997e6a3ab28f43471daf568a0def` |
| independent hard-coded schedule audit | `24909fe71f3863cfb56e446c9a2ec8d25ffc90eeb2b9666a1cd3dc055a22dde3` |
| fail-closed combined audit | `4fef5565cb3e0755169801646099e568b2c35896db749139b636980ecb60d701` |
| machine-readable schedule file | `b099a63a683cbfa037af685acf3e71339201ba30f47510625862fd9b8f2213e4` |
| exact L/Z integrator | `d890ccb7b67b404411cbcaf08bf4198a04a5f69844e21ba60b2ea267b4c1914f` |
| exact C722 D2 matrix artifact | `e808a08f43a346022180aca9ea81ce468c07e535f7525b1bdf7a858637d5ba27` |
| exact C722 D2 vector certificate | `b5416260725552c3424b99af2ca16ef9fd0775b04282545ba3e8f02bf8c2d5e3` |
| reconstruction checker | `ac8f6ca9b34d3c2bd4fd17e57a413c0e8c10fee1b298f8be6dd72eb14f6ea1a7` |
| block-Decimal whitening | `66700947fa6850eda6463ceef188f2350c15723ab392d4589a0dc8125a97c1b1` |
| exact C722 D3 matrix / robust vector | `c9da4795244885613d4c04a2ca71c7ceedabf7fb7d7fdd3952d55afc9aece699` / `37260c8d0b1263ec49c5c153fa16ce4fcd724451d7ecabddcfc1c349adab4e2e` |
| exact C722 D4 matrix / robust vector | `9744efd54f94039f813a14a41a6de44d6fcb45e29ee0ce25930193331dd38c8e` / `2ec651b0358d64ddaf3d045aa62f76560104024555838fbe1f0de370b4d7ef8a` |
| exact p2 marked-moment core | `c7170d188d692aed45fe12113c6141deb7c50c6330bffafaac67a781809a5ed2` |
| pruned D4-p2 residual scan | `1adfc88890caf3a08fc94ec492c13751f39a61f22be2387eaa65860fda554822` |

## Exact constant-support audit

The rational family is

```text
tau = 1/100000,  support epsilon = 1/200,
A = 21/80-delta/3-tau,
B_m = 1/8+3delta+1/5000  for every m>=1.
```

C70 has

```text
delta=7/1000, A=78047/300000, B_m=731/5000,
omega=A-1/4=3047/300000.
```

Counts `m=0,...,20` are feasible and every count `21,...,142` is empty.
Thus there are exactly 441 feasible ordered count pairs.  The exact checker
places every such pair in the first bin in IIa, IIb, repaired IIc, and Type
III.  In the critical repaired IIc branch its literal capacities are

```text
C1 = 4571199986563/15000000000000,
C2 =  731499995341/15000000000000,
C3 =             17500001/2500000000,
C4 =                       1/50000000000,
C1-2B = 185199986563/15000000000000 > 0.
```

C722, the refined proxy winner, has

```text
delta=361/50000, A=3121/12000, B_m=7343/50000,
omega=1009/100000.
```

It again has exactly the feasible counts `0,...,20`.  Key exact margins are

| condition | exact positive margin |
|---|---:|
| Type 0 cutoff-safe exponent | `23950000003/300000000000` |
| scalar II face 1 | `4314001/100000000` |
| scalar II face 2a | `7699997/15000000000` |
| scalar II face 2b | `149999/5000000000` |
| near-square-root IIc emptiness | `4981999969/100000000000` |
| IIa inward width beyond delta | `1/43750000000` |
| IIb inward width beyond delta | `3/350000000000` |
| repaired IIc distribution faces | `143799989/5000000000`, `153999877/30000000000`, `1199983/2500000000` |
| repaired IIc inward width | `19/50000000000` |
| Type III primary face | `1/1250000000` |
| Type III inward width above square root | `17971999307/2400000000000` |
| higher-prime-power exponent | `293/2000` |

The literal repaired-IIc capacities at C722 are

```text
C1 = 4573399986563/15000000000000,
C2 =  734799995341/15000000000000,
C3 =             18050001/2500000000,
C4 =                       1/50000000000,
C1-2B = 167599986563/15000000000000 > 0.
```

The smallest fixed rational reserve in the combined constant-support audit
is the IIb inward-width margin `3/350000000000`.

### Correction to the preliminary checker

The older `verify_direct_hb_frontier.py` used shorthand IIc capacities.  At
both C70 and C722 its shorthand `C` is larger than the literal repaired
capacity by

```text
3479/5000000000000,
```

while its shorthand `D` is smaller than the literal capacity by

```text
447/5000000000000.
```

It also checked the distribution faces with `delta`, whereas the open-window
repair must use `delta_c=delta+4h`.  The new audit uses `delta_c`, all inward
endpoint losses, and every active count pair.  Every inequality remains
strictly valid.  An earlier transient message mislabeled the C72 value
`1524399995521/5000000000000` as the C722 value of `C1`; that value is
explicitly retracted.  The correct C722 value is
`4573399986563/15000000000000` as displayed above.

## Direct prime-minorant transfer

The specialized direct-HB decomposition avoids Proposition 2 and the flawed
high-gamma Type-I branch.  The exact Heath--Brown terms fall into:

1. Type 0, handled with the cutoff-safe exponent bound;
2. a central pair of Siegel--Walfisz aggregates, handled by small-modulus
   bilinear Bombieri--Vinogradov, near-square IIa/IIb, and above-square
   IIa/IIb/repaired-IIc; or
3. three smooth atoms, handled by the corrected Type-III inequalities.

For C722, put

```text
rho(n;x)=(log n/log(3x))*1_P(n)  on [x,2x].
```

Then `0<=rho<=1_P`, so `c2=0`; the prime number theorem gives `c1=0`;
and nonzero values are prime, so `beta=1/2` works.  For the constant support
the roughness margin is `17657/50000`; for the count schedule below it is
`17607/50000`.  Removing higher prime powers is power-saving by the margin
`293/2000`.  Consequently all four hypotheses of Proposition 1 hold for
these supports, subject to the already audited repaired Section-3 lemmas
recorded in the proof draft and deep audit.

For one stratum, the support-enlargement parameter does not enter the
modulus exponent:

```text
(A-epsilon)+(A+epsilon)=2A.
```

Thus the tested epsilon changes below leave this analytic audit unchanged;
Definition 1's strict upper face also has ample room.

## Exact C722 count-dependent enlargement

The machine-readable schedule is `c722_schedule.json`.  It is constant after
`B_28`; its feasible counts are exactly `0,...,24`, with first-empty margin

```text
25*delta-B_25 = 1/100000.
```

Every cap is strictly larger than the constant baseline `7343/50000`, so the
support is a strict inclusion and the new strata 21--24 are nonempty.
Definition 1's monotonicity and increment conditions hold exactly.

For a count pair, let `S=B_m+B_m'`, `L=(S-C)_+`, and
`r=ceil(L/delta)`.  The verifier applies the proved minimal-crossing-prefix
bound to the combined pool and to each individual group.  It reconstructs
seven literal capacity pairs and checks all 625 feasible ordered pairs in
each branch.  The worst certificate is

```text
branch=IIc, pair=(24,24), pool=right, r=6,
D - prefix_upper = 56499669613/285000000000000 > 0.
```

The displayed value is the remaining `D` margin.  The canonical
schedule SHA-256 is
`8c67d65544a8f6036bae6f868eb937cabe963eaec12ec59e3a9fb537a9695f17`.

## Discovery ledger

All runs below are recorded in the repository-level `experiments.tsv`.
The basis is the correctly dimensioned stratum-aligned
`1_{r=q}(L/alpha)^a(Z/alpha)^b`, `a+b<=2`; every constant-cap invocation
listed the first empty cap as well, so no stratum was silently omitted.

| delta | order | constant-cap heuristic `48J/I` |
|---:|---:|---:|
| `0.00715` | 8 | `0.8900344719688988` |
| `0.00720` | 8 | `0.8900985838661405` |
| `0.00722` | 8 | `0.8901049457280300` |
| `0.00723` | 8 | `0.8901048964852988` |
| `0.00725` | 8 | `0.8900946332583424` |
| `0.00722` | 10 | `0.8901049226133916` |

Thus the order-8 turnover is bracketed by `[0.00722,0.00723]`, and the
C722 order-8/order-10 change is only `-0.0000000231146384`.

At constant C722, the epsilon scan at order 8 gives

| support epsilon | heuristic `48J/I` |
|---:|---:|
| `3/1000` | `0.8899972105656453` |
| `7/2000` | `0.8902149038632858` |
| `1/250` | `0.8902467299201087` |
| `1/200` | `0.8901049457280300` |

The exact C722 count schedule at epsilon `1/200`, order 10 gives
`0.8965312844893856`, a same-code gain of `0.0064263618759940` over
constant C722.  Combining it with epsilon `1/250` gives
`0.8966065840562906` at order 10.  The latter is the strongest proxy point
from this study and has exact parameters

```text
delta=361/50000, A=3121/12000, epsilon=1/250,
alpha=A+epsilon=3169/12000, eta=A-epsilon=3073/12000,
B_m as in c722_schedule.json.
```

Every quotient in this section remains heuristic.  The next section replaces
the winning D2 proxy by exact integration; its small discrepancy from order-10
quadrature is a direct illustration of why the proxy was not a certificate.

## Exact C722 epsilon=1/250 L/Z D2 certificate

`exact_lz_integrator.py` independently reconstructs the finite basis

```text
1_{R=r} (L/alpha)^a (Z/alpha)^b,  a+b<=2,  r=0,...,24.
```

It uses the exact large- and small-sum densities

```text
f_r(L)=(L-r*delta)^(r-1)/(r-1)!,
g_n(Z)=sum_{j<=Z/delta} (-1)^j binom(n,j)
       (Z-j*delta)^(n-1)/(n-1)!.
```

For J, `alpha-eta=1/125>delta` makes the distinguished-small
branch a single polynomial.  The distinguished-large branch has exactly two
polynomial pieces separated at `Z=alpha-B_{r+1}`.  Hence I is block diagonal
in R and J is block tridiagonal.  Every entry is a sum of Fraction-valued
rectangle and triangle moments; no quadrature or floating decision occurs.

The production moment routine shifts to `x=L-r*delta`,
`y=Z-j*delta` before inclusion--exclusion.  A retained, algebraically separate
piecewise-expanded-density implementation gives bitwise-identical moments for
all dimensions 0 through 6, all monomials of degree at most 3, and three
domains exercising internal and external cap crossings.  Further exact tests
are:

- every k=1, D2 I and J monomial entry against its one-variable hand formula;
- k=2, D0 I volumes and a mixed-sign J vector against a direct one-variable
  geometric integral; and
- scheduled k=8, D2 and actual k=48, D2 matrix contraction against a separate
  evaluator which first sums each stratum amplitude and then squares it.

The full matrix has 150 labels, took 73.63 seconds and 36 MB in the recorded
run, and has SHA-256
`e808a08f43a346022180aca9ea81ce468c07e535f7525b1bdf7a858637d5ba27`.
A floating eigensolve was used only to select a vector.  Rationalizing that
vector to exact decimal fractions and contracting exactly proves the attained
Rayleigh quotient

```text
48 J(c)/I(c) =
39207970999598031810400523026435504665407269610125329540652190652494883395188027030610794017459734194762003310606210460026658627537042717405215495974232639198559006452777564731212387746753471456762018578599655882613414974027806256638677429147798644902210673593080500157803162216778229176041346649805323
/
43729274127124613949551786247839758966496875450406763955079525738981070070106013871729194793279509731039470979846991029474356941585942183057602325005108122756458584114932265277142192482799700535894904435482342332463307383113648405072014631965734225028167357275842694709649789212929843769303392514662500
= 0.89660694768491289... .
```

Thus this exact particular vector has shortfall
`0.10339305231508711...`; its full exact value and the positive exact
`I-48J` margin are in `c722_lz_D2_vector.json`.  This is a rigorous achieved
lower bound for the finite-space optimum, not a rigorous upper bound on that
optimum.  The numerical generalized eigenvalue
`0.8966069476947929` suggests the vector is close to optimal, but that
statement remains heuristic.  In particular this exact D2 result is
subcritical and is not an H1<=236 certificate.

### Exact D3 and D4 continuation

The same no-quadrature construction was continued only through the safe
part of the pure L/Z ladder:

| degree | labels | positive I diagonals | exact attained quotient | exact build time / peak RSS |
|---:|---:|---:|---:|---:|
| 2 | 150 | 147 | `0.89660694768491289...` | `73.63 s / 36 MB` |
| 3 | 250 | 244 | `0.91928830398447925...` | `305.23 s / 59 MB` |
| 4 | 375 | 365 | `0.92976162456957312...` | `558.00 s / 103 MB` |

The exact gains are approximately `0.02268135630` and `0.01047332059`;
D4 remains short by `0.07023837543`.  Each displayed number is the exact
quotient of a particular rational vector.  Optimality of the vector is not
claimed.

For discovery, each nonzero R block of I was diagonal-scaled and Cholesky
whitened in Decimal arithmetic before a standard symmetric eigensolve.
Independent 60- and 100-digit transformations gave identical displayed
eigenvalues:

```text
D3  0.9192883039844795, residual_inf 3.1572e-16
D4  0.9297616245695731, residual_inf 2.4980e-16.
```

The rationalized vectors attain the values in the table exactly.  This block
method avoids discarding legitimate rare-stratum directions.  For comparison,
the ill-conditioned global Gram cutoff at D4 gave:

| relative cutoff | retained rank | heuristic quotient |
|---:|---:|---:|
| `1e-12` | 299 | `0.9278385896128323` |
| `1e-13` | 315 | `0.9297354595984517` |
| `1e-14` | 329 | `0.9297618316542537` |
| `1e-15` | 339 | `0.9297618331269635` |

Those cutoff values are diagnostics, not certificates.  Both D3 and D4
rational vectors passed cache-free full reconstruction and the independent
sum-first/square-second contraction.  D4 required `554.80 s / 46 MB` in the
checker.

### First missing-orbit test and retirement gate

The pure L/Z space cannot see coordinate dispersion at fixed `(R,L,Z)`.
The smallest missing symmetric orbit was therefore tested in the concrete
family

```text
H_r = 1_{R=r} * (sum_i t_i^2) / alpha^2.
```

`p2_enrichment.py` derives exact marked slice densities for `p2` and `p2^2`
and exact small/large distinguished-coordinate marginals.  Its tests compare
mark order zero with the separate L/Z integrator, compare `p2,p2^2` on a
two-coordinate box with hand formulas, reproduce every ordinary k=8 D2 I/J
entry, and compare a genuinely mixed matrix contraction with a separate
sum-first/square-second evaluation.

An all-stratum exploratory scan identified R=4,5,6,7 as the only relevant
leading tags.  They were rerun in the durable exact-cross scan
`c722_D4_p2_residual_pruned.json`.  Cross forms and residuals are exact;
the novelty norm is a Decimal-100 block Cholesky calculation and the final
two-vector gain is heuristic:

| R | normalized residual score | two-vector gain over D4 |
|---:|---:|---:|
| 5 | `0.01095713062` | `3.48158236e-6` |
| 6 | `0.01072427323` | `2.65930084e-6` |
| 4 | `0.00894355926` | `2.82782046e-6` |
| 7 | `0.00854519798` | `1.32595957e-6` |

This is orders of magnitude below the predeclared `0.01` gain gate, while
the base quotient is below `0.96`.  The attempted four-column full append was
therefore stopped before completion.  The standalone C722 L/Z ladder and
this first p2 correction are retired as closing routes; the exact C722
artifacts remain useful as a verified correction-family implementation.

## Source-bound BV full-simplex pivot

After the C722 retirement gate, computation moved to the independent
full-simplex support

```text
k=48, A=1/4, epsilon=3/400, delta=7/250,
alpha=103/400, eta=97/400, beta_r=103/400 for every r.
```

This route uses `exact-integrator/src/exact_integrator.py` at SHA
`941ee82bc72fd8488a95eb5e536fe47f8c95d39a1b618dae7d6ef7eb27122e52`.
Because an older cache was generated by a different source revision, a fresh
version-2 cache was built with the source SHA in every key.  The cache-free
from-empty D14 principal build (`195` labels, `19110` misses) reproduced the
historical matrix SHA bit for bit:

```text
ec6d141cc89f98b64d1a77eb0f70df9b1144ca0539191dfdaacfa827fc542cb5
```

The D16 extension has `307` labels and exact matrix SHA

```text
989b60a96521fcc92e4dfc2b463b907072c22a9bd19c111bd89aa0e2238c1220
```

It reused the `19110` verified D14 entries and computed `28168` new exact
entries.  A diagonally scaled Decimal-140 LU/power calculation, resumed for
320 iterations and rationalized to 36 significant digits, gave the exact
particular-vector quotient

```text
0.981278109819760620341348914562469789134983704701037163528067...
```

and exact shortfall

```text
0.018721890180239379658651085437530210865016295298962836471933...
```

The discovery trace rose from `0.9811891389162524` at iteration 40 to
`0.9812781098197606` at iteration 320.  This convergence diagnostic is not
an optimality proof; only the particular rational-vector quadratic forms are
rigorous.  The compact certificate is
`bv_aquarter_B16_vector_exact.json` (SHA
`59715ddffa483c696c035634a81c3cc8ffe882e9d6eaceec74bea23996b72d62`).
The D14 exact historical quotient `0.975205923890446...` to D16 gain is only
about `0.00607219`, so the next mechanism under test is the richer no-ones D12
space rather than an automatic even D18 extension.

The complete 272-label no-ones D12 build gives the exact particular-vector
quotient

```text
0.9681789430016942359685633638976835496...
```

with matrix SHA
`43821d30b12312c4a42817d2c1e956183f50f8474303586c40750de6b7697280`.
It passes the read-only fail-closed checker below in normal and optimized
modes.  This is below D16; the broad odd-signature low-degree space is not an
immediate closing mechanism.

The smallest coherent hybrid appended all fourteen odd radial labels
`(1-P1)^a P3`, `0<=a<=13`, to the certified D16 vector one at a time.  Exact
two-dimensional rational contractions improve the quotient by only
`9.25998e-16` through `9.63053505328424e-16`.  The screen artifact SHA is
`7f48172a0cf4080b50c2faf83e7ae6e3b7807e14e1299afa4defae33df3bc88e`;
the full 321-dimensional append was not built.

### Exact dead-core deletion

Put `R=103/400`, `V=97/400`, and

```text
C = {t>=0: sum(t)<R and sum_{j!=i} t_j>V for every i}.
```

Every `J_i` fiber has `sum_{j!=i}t_j<=V`, so `C` is disjoint from every
fiber and `F'=F*1_{C^c}` preserves `J` exactly.  An exact slice
inclusion-exclusion computes the removed denominator mass for the D16
polynomial:

```text
I_C/I = 0.000000024209735209838010136674775950832827...,
required = 1-48J/I = 0.0187218901802393796586510854375302...,
48J/(I-I_C) = 0.981278133576244401426279108595587....
```

Thus this attractive piecewise correction is about `7.73e5` times too small
for the stored polynomial.  The exact computation expands 5,825 square terms
into 915 orbit families and uses 26,524 cached scalar slice integrals.  It
passes independent exact `k=2` shifted-triangle monomial tests and an
empty-core cancellation test.  Artifact SHA:
`2b9181be66e3171798e947c22be42a2bbf33a895fd777553bcfc29a7a84db5d6`.
Root's separately written literal-term reconstruction
`verify/dead_core_mass.py` (SHA `e4d8c55bd3380623cbc946ebd7b5e07c6b80c6e2302e3ceb64e02248688c8586`)
also reconstructs all 5,825 terms and agrees at Decimal100.  Its four exact
piecewise tests pass in normal and optimized modes.

### Exact radial kink at the J cutoff

A stronger two-dimensional piecewise family uses `a F0` on `sum(t)<=V` and
`b F0` on `V<sum(t)<R`.  Its denominator is diagonal by the two disjoint
radial regions.  On every J fiber its marginal is exactly

```text
a M_V + b (M_R-M_V).
```

Recentring both upper-radius marginal polynomials in powers of `V-U` gives an
exact 2-by-2 pencil.  The `RR` entry and amplitudes `(1,1)` reproduce the D16
certificate bit for bit.  Decimal-160 discovery followed by a 51-significant-
digit rational amplitude gives

```text
(a,b) = (1, 0.98700279610351133526471897542473812763044719082939),
48J/I = 0.9812858896095555411262925535651008306690384...,
gain  = 0.0000077797897949207849436390026310415340547....
```

The result remains negative.  Normal and optimized reruns emit identical
artifact SHA
`33fe5d555e736fe5ea3826d569477414fadd2d8a9defc2eaa35718a4f06f82ca`.
Root's independent `verify/radial_split.py` (SHA
`847f4edc6835b54637abdf21906ee8b0d0eb92c173c5ac247ff6833dd5c94403`)
reconstructs the exact `RR,VV,VR` forms, has zero baseline `M2` delta, and
agrees with this quotient at Decimal100.

### Exact outer-shell even-basis block

The next test allows an independent polynomial correction on the whole outer
shell, rather than merely rescaling `F0` there.  Starting with all 40 even
labels through degree 8, the exact single-label screens against the full
certified D16 vector have top gain

```text
label (0,(4,4)):  0.0000000042352339999365764...,
sum of all 40 positive single-label gains: 0.000000037835547604839625....
```

Because correlated nearly-dependent directions can make that sum misleading,
the complete 41-dimensional pencil

```text
span { F0, 1_{V<S<R} G : G in even_basis(8) }
```

was then rebuilt in exact rational arithmetic.  Its largest-vector discovery
used symmetric Decimal Cholesky whitening and all-spectrum Jacobi at 100 and
160 digits; the two Rayleigh values agree through 67 decimal places.  A
56-significant-digit rationalization has rigorously contracted forms

```text
48J/I = 0.981280492785219624773346179476124981107465769336337975936008...,
gain over D16 = 0.0000023829654590044319972649136551919724820646353008124...,
shortfall = 0.0187195072147803752266538205238750188925342306636620241....
```

This correlated gain is larger than the naive sum of separate gains, but is
still about 420 times below the predeclared `0.001` continuation gate and
about 7,855 times below the theorem shortfall.  Thus degree-8 outer-shell
enrichment is retired as an immediate closing mechanism; this is not a
finite-space upper bound and does not assert anything about arbitrary
piecewise functions.  Matrix SHA is
`0dfcad448f99f1d9828298586b24d2deeb9456cba4f33f5bf4d4a16ed703fa2f`;
artifact SHA is
`a69673e03933355819ad96f7ab85586f3a65a7b6abee67145d96368257c3ae27`.
Normal and optimized builders are byte-identical.  The independent
reconstruction checker (SHA
`e017dfc9b28b405310a24aabe14797455a0fb0f55ef51f878b957f04733dae2d`)
passes in both modes.

### Exact fixed-vector epsilon sensitivity

For this direct-BV family every fixed rational `0<epsilon<1/4` is
analytically valid: `R=B_m=1/4+epsilon`, `V=1/4-epsilon`, the two relevant-
modulus exponents add to `1/2`, and `beta-B_1=1/4-epsilon>0`.  A direct exact
orbit contraction scanned 29 coarse and refined rational points without
rebuilding a matrix.  The stored D16 polynomial peaks among them at

```text
epsilon = 19/2500 = 0.0076,
48J/I = 0.9812847277203190708976244750280183522892...,
gain over epsilon=3/400 = 0.00000661790055845055627556046554856....
```

This is fixed-vector sensitivity only, not the optimum at the new epsilon.
The refined artifact SHA is
`3efa2fd15f66f732be4c8e96d5c44b0647d0aa3b553a9cba95ee0b9f3e50e00b`.

## Reproduction

Run the fail-closed combined audit in normal and optimized modes:

```bash
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_all.py
python3 -O prime-gap-236/agents/small-delta-frontier/verify_c722_all.py
```

Both must end with `C722 FAIL-CLOSED COMBINED AUDIT PASS`.  The first command
checks the complete `epsilon=1/250` analytic audit and the independent
hard-coded schedule verifier; it fails on a nonzero subprocess status, a
missing success marker, a changed exact margin, or a changed schedule hash.

Run the exact finite-basis reconstruction audit (about 70 seconds, under
40 MB here) with:

```bash
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_lz.py
python3 -O prime-gap-236/agents/small-delta-frontier/verify_c722_lz.py --skip-low-k-tests
```

Both tested modes end with `C722 EXACT LZ D2 AUDIT PASS`.  The checker does
not read the serialized matrix: it reconstructs every entry, checks the
matrix quadratic against the independent sum-first/square-second contraction,
and compares all exact forms to the compact vector certificate.

For D3 or D4, pass the desired compact certificate explicitly, for example:

```bash
python3 prime-gap-236/agents/small-delta-frontier/verify_c722_lz.py \
  prime-gap-236/agents/small-delta-frontier/c722_lz_D4_vector_robust.json \
  --skip-low-k-tests
```

The BV D16 certificate has a separate read-only fail-closed checker.  It
rejects changed sources, run artifact, cache file, basis, matrix SHA, vector,
or exact quadratic forms and never repairs a missing cache row:

```bash
python3 prime-gap-236/agents/small-delta-frontier/verify_bv_vector.py \
  prime-gap-236/agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json \
  prime-gap-236/agents/exact-integrator/results/aquarter_fullsimplex_k48_B16_current.json \
  --cache prime-gap-236/agents/exact-integrator/cache/bv_aquarter_sourcebound_v2.sqlite3
```

Normal and `python3 -O` modes both print `BV VECTOR FAIL-CLOSED AUDIT PASS`.
For an expensive source-only reconstruction, replace `--cache PATH` by
`--cache-free`.

The 41-dimensional outer-shell block has its own cache-free reconstruction
checker (about ten seconds here):

```bash
python3 prime-gap-236/verify/bv_outer_shell_block.py \
  prime-gap-236/agents/small-delta-frontier/bv_D16_outer_shell_even_D8_block_exact.json \
  prime-gap-236/agents/small-delta-frontier/bv_aquarter_B16_vector_exact.json \
  --expected-artifact-sha256 a69673e03933355819ad96f7ab85586f3a65a7b6abee67145d96368257c3ae27
```

It reconstructs every matrix entry rather than reading serialized moments,
checks the dependency and matrix hashes, and prints `AUDIT PASS`.  The same
command under `python3 -O` also passes.

## Independent tagged-dyadic result-driver audit

The unlaunched independent C10 D12 result driver at SHA
`7e2ed20a68e3c3e95a9566b32cae3d403949a79a3a81adfa61b8dab833b640b9`
has a scoped pre-launch `AUDIT PASS`.  The full report is
`INDEPENDENT-DYADIC-DRIVER-AUDIT.md` (SHA
`5c42829e3d412a903f987057b67322ef389468894ab6f6c282eafb3eb0ea3a85`)
and its seven-test hostile suite has SHA
`1a62de64f491473275926a2e3616f1216c36e2c247fef01f911b2bfa841f8f6b`.
The suite checks original-to-integer provenance, all target active counts,
forward/reverse order, zero-crossing coefficient retention, independent
literal-oracle containment, stage serialization, protected paths, factor 48,
and the strict lower-margin sign gate.  It passes normal and optimized modes:

```bash
PYTHONPATH=prime-gap-236 python3 \
  prime-gap-236/agents/small-delta-frontier/test_independent_dyadic_driver_audit.py -v
PYTHONPATH=prime-gap-236 python3 -O \
  prime-gap-236/agents/small-delta-frontier/test_independent_dyadic_driver_audit.py -v
```

No D12 integral or quotient was computed, and `theorem_ready` remains false.
The corrected batched D4 benchmark rerun was terminated by explicit resource
policy while the host was swapping (SIGINT exit 130); it wrote no artifact.
Only the earlier first pass's exact arithmetic/reference equality survives,
and no new mathematical claim is inferred from the aborted rerun.

## Sparse 20-band gradient hostile audit

The frozen sparse producer SHA `e1545435...` has a scoped algebra pass but a
concrete provenance counterexample: it writes the requested output only after
performing its dependency end-hash checks and does not reject an output path
which aliases the operator, source, bands, or baseline.  The actual active
invocation is safe from this particular failure because its five resolved
paths are pairwise distinct; its output was still absent at the audit
checkpoint.

`BAND-OPERATOR-SPARSE-AUDIT.md` records the full derivation and inference
limits.  Hostile tests SHA `bbe1b56d...` pass 8/8 normal and optimized,
including fresh exact signed matrices, every serial/fork channel, the actual
695-component owner partition, and a target-support exact factor-48/count
oracle.  The separate fail-closed consumer
`band_gradient_postprocess.py` SHA `dbd0d47f...` requires a caller-supplied
gradient byte SHA, pins and rechecks every input/dependency, rejects collisions,
and emits only either an exact rational trial needing a fresh scalar
reevaluation or an explicit no-claim.  A single action `(A theta,B theta)` does
not determine any finite-step quotient, so no target sign is claimed.

## General-minorant `K`-free sliver

`GENERAL-MINORANT-K-SLIVER.md` gives an exact geometric route reopening.  At
`A=521/2000`, support `epsilon=37/10000`, `delta=7/1250`, constant
`B_m=21/2500`, and `xi=(3989,4001,4001)/10000`, the symmetric sub-support
with exactly one coordinate above `delta` and total sum below
`eta=321/1250` annihilates the repaired `K` form pointwise.  An explicit open
`J` fiber has common sum above the C10 cutoff by `299/150000`; hence genuine
`J` extension does not force a `K` loss.  The exact singleton quotient is
`.265999999999999999999999999999999999999993...`, with `c2=24` and the
rigorous adverse density bound `c1<1/299000000` retained.

This is not a sieve result.  The point enters the nonempty high-`gamma`
Type-I range where the source's role swap lacks a Siegel--Walfisz hypothesis
on `alpha`, and the signed `c2>0` Proposition-1 implication is still outside
the completed audit.  The checker SHA is `e65aa613...`; normal and optimized
modes are byte-identical and emit `THEOREM_READY=false`.
