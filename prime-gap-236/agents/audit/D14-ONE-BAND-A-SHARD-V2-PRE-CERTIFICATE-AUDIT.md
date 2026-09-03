# Frozen D14 one-band A-v2 hostile audit

Date: 2026-09-03 (Europe/Berlin)

## Verdict

**A-STAGE AUDIT PASS** for the frozen producer, every one of the thirteen
count shards, and the strict-v2 exact aggregate.  I found no exact
counterexample to paired-face reuse, and a separate radial engine reproduced
the high endpoint, low endpoint, and band difference exactly for every count
(r=0,\ldots,12).  This verdict certifies the exact one-band (A=I(H))
prerequisite only; it makes no (b=48J(F,H)), Rayleigh-quotient, or theorem
claim.

The frozen objects audited here are:

- producer `agents/structural-basis/code/exact_d14_one_band_a_shard_v2.py`,
  SHA-256
  `2e91dbd8bcb8d0bfd102f964236d3a7d60d974bfecedab96a4a19a1124e81c2d`;
- pinned producer tests
  `agents/structural-basis/tests/test_exact_d14_one_band_a_shard_v2.py`,
  SHA-256
  `4d5402a8e9940755ca18e69c5a346426bc6081d78ea5206236191dc34e527afc`;
- pinned v1 base, SHA-256
  `6fa3c7c99735ec9eeb5817413e4dfc77dc6ae57e1cef26c720f54f33eb93896e`.

## Independent derivation of paired-face reuse

Write the already naturally dilated polynomial as

\[
 H(t)=\sum_{a,\lambda}c_{a,\lambda}(1-S)^aP_\lambda(t),
 \qquad S=\sum_{i=1}^{48}t_i.
\]

On the stratum with exactly (r) coordinates greater than \(\delta\), translate
those coordinates by \(\delta\).  Inclusion-exclusion for the remaining boxed
coordinates translates a selected set of (h) further coordinates by
\(\delta\).  If (X) and (Y) are the two resulting aggregate variables, then

\[
 S=(r+h)\delta+X+Y.
\]

For each monomial orbit \(P_\nu\), its angular density on this face is an exact
bivariate polynomial

\[
 D_{\nu,r,h}(X,Y).
\]

It is determined only by \((48,\nu,r,h,\delta)\), the selected-exponent split,
and the inclusion-exclusion small-box expansion.  In particular, it is
independent of the support endpoint \(\alpha\).  The residual factor is

\[
 (1-S)^p=(1-(r+h)\delta-X-Y)^p,
\]

which is also independent of \(\alpha\).  Thus the whole face integrand

\[
 \sum_{\nu,p} C_{\nu,p}
 D_{\nu,r,h}(X,Y)(1-(r+h)\delta-X-Y)^p
\]

can be reused.  Only its domain changes:

\[
 X,Y\ge0,\quad X+Y\le \alpha-(r+h)\delta,
 \quad X\le \beta_r-r\delta\quad(r>0).
\]

The last cap is absent for (r=0).  This gives exactly

\[
 I_r(H;\alpha_2)-I_r(H;\alpha_1)
\]

by evaluating the same face polynomial on the two nested domains and
subtracting.  No positivity assumption is needed for this equality.

For the frozen endpoints the common face inventory condition holds exactly:

\[
 \alpha_1/\delta=309/20,
 \qquad
 \alpha_2/\delta=9500917/600000,
\]

and both floors are (15).  Therefore each active (r) has (h=0,\ldots,15-r),
or (16-r) faces, at both endpoints.  The support class constructs both
endpoints with the same (k=48), delta, and schedule.  For (r>0), the reused
cap is literally the same rational \(\beta_r-r\delta\).  The active set stops at
(r=12), since

\[
 \beta_{12}-12\delta=2917/250000>0,
 \qquad
 \beta_{13}-13\delta=-3749/750000<0.
\]

Endpoint conventions do not change an integral of a polynomial density: all
disputed hyperplanes have Lebesgue measure zero.  The exact polygon/interval
integrators use the same endpoints on both evaluations.

## Line-by-line source audit

- Lines 50--66 collect (H^2).  Off-diagonal coefficient pairs receive the
  required factor two; `multiply_monomial_orbits` supplies the product-orbit
  coefficient once.  Zero terms are removed exactly.
- Lines 72--82 bind exact `Fraction` evaluators and require the frozen D14
  inventory of 3034 nonzero residual terms.
- Lines 83--97 enforce equal face floors, equal delta, and (for the selected
  positive stratum) equal positive cap before reuse.
- Lines 103--124 use the same orbit density and the correct endpoint-independent
  residual base (1-(r+h)\delta-X-Y).  The density routine includes both the
  selected-exponent multiplicity and `orbit_size(48,nu)`; the cap is imposed in
  the domain rather than in the density.
- Lines 125--132 change only the outer radius to
  \(\alpha_i-(r+h)\delta\), as the derivation requires.
- Lines 139--143 clear caches only after both endpoint integrations on a face;
  no value is discarded from either sum.
- Lines 146--176 pin every dependency, require (r\in\{0,\ldots,12\}), require
  the canonical D14 basis, clear the grid denominator by (10^{38}), and check
  natural dilation by two algebraically distinct centered expansions.
- Lines 178--199 independently compare termwise and grouped constant volumes,
  require positive nested-band volume, and require the squared-polynomial
  high, low, and difference values to be positive.
- Lines 202--204 recheck the complete source/input byte snapshots after the
  calculation.
- Lines 208--299 serialize exact rational values, scale, geometry, face
  inventories, source hashes, and the intentionally limited claim scope.  The
  band value is formed as exact high minus exact low at line 195.
- Lines 302--323 expose exactly one immutable count per invocation and publish
  through the v1 base's exclusive-output path.

One scoped API caveat was found: the reusable helper `paired_evaluate` itself
does not explicitly compare `high.k == low.k`; it uses `high.k` for both
integrations.  A free-standing caller could therefore misuse it.  This is not a
counterexample to any frozen target shard: `build_shard` constructs both
objects from the same frozen `Support` class at line 160, which fixes (k=48),
the same delta, and the same schedule.  The audit verdict is deliberately
limited to that frozen construction.

## Independent literal tests

I added
`agents/audit/test_exact_d14_one_band_a_shard_v2_independent.py`, SHA-256
`6621aa4116fb5a8cceccc19756fc1b733bbdf829d6e624f9810e8925988ad8d9`.
Its expected-value route expands named symmetric monomials into ordinary
bivariate monomials, squares them, clips the literal (k=2) support cells, and
integrates those polygons exactly.  It does not call the paired-face routine,
its orbit-density routine, or its grouped-domain integral to obtain expected
values.

Coverage includes:

- all 64 ordered pairs from eight residual/orbit basis labels;
- (r=0,1,2), including zero-large and all-large aggregate faces;
- repeated and distinct exponents, detecting cap/orbit multiplicity mistakes;
- 16 seeded random rational coefficient vectors and endpoint/schedule choices;
- endpoints varied within a common floor block, so alpha dependence is
  exercised while paired reuse remains legal;
- deliberate unequal-floor, unequal-delta, and unequal-cap cases, all of which
  must fail closed.

Final executions:

```text
python3 -m unittest -v agents/audit/test_exact_d14_one_band_a_shard_v2_independent.py
3/3 PASS; 3.292 s unittest time; 23,600 KiB peak RSS

python3 -O -m unittest -v agents/audit/test_exact_d14_one_band_a_shard_v2_independent.py
3/3 PASS; 3.496 s unittest time; 29,104 KiB peak RSS

python3 -m unittest -v agents/structural-basis/tests/test_exact_d14_one_band_a_shard_v2.py
3/3 PASS

python3 -O -m unittest -v agents/structural-basis/tests/test_exact_d14_one_band_a_shard_v2.py
3/3 PASS
```

## Completed target replay and strict aggregate audit

The separate exact checker
`agents/audit/verify_d14_one_band_a_v2_radial.py`, SHA
`e51a8719b4665dc2e38c454f467abfc8b894410d53b3882dd931c7ed82e37666`,
imports neither v1 nor v2 production A code.  It reads the pinned D14 grid38
vector, independently performs the natural dilation and orbit-square
collection, and reconstructs each stratum through the separately audited
radial support engine.  It reconstructed 508 orbit groups and 3034 residual
terms, then required equality of the high endpoint, low endpoint, and band
difference separately.  All thirteen count results passed:

```text
r00 4416e9320c820183f0e20964cafb14eef407144bac7b9be67f75a1aa72cfff80
r01 ca07908fd5161da3ec9da6efd5e43f32d4b004610b2ce13b152fd67dee4c9a13
r02 3203218c631b09fc07034c93e63342244ff4f9f9656e36571b1c4c3f9221d5e1
r03 65158a8c757159e8c8308ecaf4b86501105b2067946d4f8a3464c4dd5a52b166
r04 d66efc356891bcb443f23a29c31589596303b69247965748a0f43d78cede8646
r05 b55a90359e05014be7b8611beebdf64401b26b66a0a535a31100262edf3b9ad1
r06 dd35cbe8f5f21e8eaaf558f0141d84937bb223642edf85e06dca5ead8ff40618
r07 338cf03d1f76c804562e8b96fb981a353809ab9edc9fb03a61e0c80e9422515e
r08 d7b537b711545db759dc44bae9fa398955c67721bb3cc6422084015b4f271275
r09 bb81739f46e38fba615a1b874020a9eb3d98444f9ad2d47d29dc84983b9ca242
r10 f976412ed948526dbcbe0678b32c143cfc1a21befd27c2e3c03cfdd1d38f5db5
r11 7540ff0436af9e2cb94e2241f39ed898c23df5804efa722f06b094bc1db41fd5
r12 7db414ad1734dc03f461c8d6a98f2209524a836740b22a323b1cf6ba99809bff
```

These are hashes of the independent audit outputs, not the production
shards.  Every output embeds and checks the corresponding production-shard
hash and the independent checker/source closure.

I also added
`agents/audit/verify_d14_one_band_a_aggregate_v2_strict_audit.py`, SHA
`d034d09d2b5a9b44a891d3d9949c6e39b81780b87fae92667edbf4f2a5866b37`.
It imports no production A producer or assembler.  It strictly decodes and
pins all thirteen production shards, independently checks each support
subtraction, volume identity, (10^{76}) scaling identity, face count,
candidate quotient, live source closure, and strict-D19 provenance, and then
reconstructs every exact aggregate rational and decimal.  Mutation tests
`agents/audit/test_verify_d14_one_band_a_aggregate_v2_strict_audit.py`, SHA
`0701a4705a927af28f945ddade99afd65afe2d259185e0f581f0757c37fb7a59`,
passed 7/7 in normal and optimized modes.

The frozen production aggregate is
`agents/structural-basis/results/d14_one_band_a_aggregate_exact_v2_strict.json`,
SHA `e00feb75871e9a4f9be34e9042283f0eda1aa16d139fe27dd2c5deb044865c44`.
The final independent audit result is
`agents/audit/results/d14_one_band_a_aggregate_v2_strict_audit.json`, SHA
`9c846bb1753861f28a02209975b44dde4ab6092fdf205eef30d498d3fbf72546`.
Normal and optimized checker runs produced these same canonical result bytes.
It records `all_13_independent_radial_replays_equal=true` and
`all_13_shards_recombined=true`.  This closes the exact A-stage audit at its
stated scope.
