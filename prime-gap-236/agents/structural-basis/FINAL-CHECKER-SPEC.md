# Specification for the final cache-free certificate checker

Status: implementation specification, 2026-09-01.  This document does not
claim that the capped C10 D12 margin is positive; that value is still being
computed.

## 1. Trust boundary and command

The final finite certificate checker should live in `prime-gap-236/verify/` and
run as

```sh
python3 prime-gap-236/verify/check_certificate.py \
  prime-gap-236/certificate/c10-d12.json
```

It may use Python's standard library only.  It must not import the discovery
integrator, grouped evaluator, a SQLite database, a matrix file, NumPy, SymPy,
or any floating-point package.  It must never read a persistent moment cache.
Empty in-process memo tables derived solely from the checked input are allowed
for runtime, but they are initialized on every invocation and never loaded or
written.  A killed or resource-exhausted run exits without printing `PASS`.

The checker ignores all serialized eigenvalues, matrix hashes, matrix entries,
and positivity flags.  The only mathematical certificate data it consumes are
the finite basis, rational coefficient vector, exact support parameters, and
the 48-tuple.  Expected values of `I`, `J`, and the margin are comparison
targets after reconstruction, never premises.

The base-polynomial input provenance is currently

```text
agents/exact-integrator/results/hb_c10_fullsimplex_noones_D12.json
SHA-256 719c656e6e45388273b4c27f51f7a18b33e9ed1abb5f883e6fcc5de5d6d64a87
```

That file's embedded `beta` values describe the full-simplex discovery
relaxation and **must not** be used for the capped certificate.  The checker
requires the capped parameters explicitly:

```text
k=48
alpha=79247/300000       # A+epsilon
delta=1/100
eta=76247/300000         # A-epsilon
beta1=3/20
beta2=3/20
beta3plus=97/625
A=77747/300000
epsilon=1/200
c1=c2=0
```

It checks `alpha=A+epsilon`, `eta=A-epsilon`, and `alpha-eta=delta` exactly.

The active candidate also consumes the rational affine table

```text
agents/exact-integrator/results/c10_stratum_linear_cappedopt_D4_exact.json
SHA-256 ffa607e0f2a8a3b6648f248efb13dc7ac2f1e7ef5809771f31c5f04b30f53158
```

only for its canonical 48-vector indexed as
`(R,1),(R,L),(R,Z)`, `0<=R<=15`.  The effective certificate replaces the
`L` and `Z` entries by exact zero for `R>11`.  Serialized `I` blocks, `J`
entries, quotient, and positivity flags in that discovery artifact are not
inputs.

## 2. Fail-closed parser

Every rational is an ASCII string `[-]digits/digits` or `[-]digits`; parse it
directly to `fractions.Fraction`.  Reject a zero denominator, whitespace inside
a token, decimal/exponential notation, noncanonical duplicate fields, NaN-like
tokens, booleans in integer fields, and trailing unrecognized certificate
sections.  Critical conditions use explicit exceptions, not `assert`, so
`python -O` behaves identically.

Before integration verify:

1. `k=48`, degree bound 12, basis dimension 272, and vector length 272.
2. Every label is `(a,lambda)` with `a>=0`, `lambda` weakly decreasing,
   every part at least 2, `len(lambda)<=48`, and
   `a+sum(lambda)<=12`.
3. Labels are unique and equal, in the recorded order, to a locally generated
   complete no-ones basis through degree 12.  All 272 current coefficients are
   nonzero, although zero coefficients remain legal if explicitly present.
4. Recomputed SHA-256 of the source vector JSON equals the pinned source hash.
5. The compact certificate's ordered labels and parsed fractions equal the
   pinned source JSON's ordered labels and fractions coefficient by
   coefficient.  No normalization or reordering is silent.
6. The affine artifact has exactly the canonical 48 labels, every coefficient
   is parsed as a canonical rational, the cutoff is exactly 11, and the
   effective triples are exactly
   `(a_R,b_R,c_R)` below the cutoff and `(a_R,0,0)` above it.  Independently
   recompute the LCM used to clear the affine denominators and check every
   scaled entry.  The base and affine common scales are nonzero and therefore
   multiply both quadratic forms by the same positive square.

## 3. Independent symmetric-polynomial algebra

Use

\[
P_\lambda(t)=\sum_{\text{distinct permutations of }(\lambda,0^{k-|\lambda|})}
t_1^{\lambda_1}\cdots t_k^{\lambda_k}.
\]

Reconstruct every integer structure constant

\[
P_\lambda P_\mu=\sum_\nu m(\lambda,\mu;\nu)P_\nu
\]

from contingency tables of matched equal-part classes.  Do not copy a table
from either research implementation.  Check that every coefficient is a
nonnegative integer and test the routine by literal permutation expansion for
small dimensions.  Reconstruct

\[
|\mathcal O_k(\nu)|=
\frac{k!}{(k-|\nu|)!\prod_e m_e(\nu)!}
\]

locally.

Let the fixed base polynomial be

\[
P=\sum_{a,\lambda}c_{a,\lambda}(1-S)^aP_\lambda.
\]

Expand unequal basis pairs twice and use

\[
(1-S)^b=\sum_{c=0}^b {b\choose c}
(1-\alpha)^{b-c}(\alpha-S)^c.
\]

This produces exact coefficients of `P_nu (alpha-S)^c`.  The actual function
is

\[
 F(t)=1_T(t)P(t)(a_R+b_RL+c_RZ),
 \quad R=\#\{i:t_i>\delta\},
\]

with $L=\sum_{t_i>\delta}t_i$ and
$Z=\sum_{t_i\leq\delta}t_i$.  Hidden Gram-matrix invertibility or
positive-definiteness assumptions never enter.

## 4. Reconstruction of `I`

Enumerate every large-coordinate count `0<=r<=48`; do not trust a precomputed
maximum.  For each orbit exponent `nu`, enumerate all ways its padded exponent
multiset can place exponents on `r` large and `48-r` small coordinates, with
the exact binomial multiplicity.

Translate each large coordinate by `delta`.  Apply inclusion-exclusion to the
small boxes `[0,delta]`, translating `h` selected upper faces.  The checker may
implement the following two finite DPs from their definitions:

- for a large exponent `e`, expand
  `(delta+x)^e=sum_q binom(e,q) delta^(e-q) x^q` and attach `q!`;
- for a small exponent `e`, the unshifted term attaches `e!`, while selecting
  its upper face contributes
  `-sum_p binom(e,p) delta^(e-p) p!` and increases `h` by one.

After Dirichlet angular integration, the large radial power is `q+r-1` and its
coefficient is divided by `(q+r-1)!` when `r>0`; similarly the small radial
power is `p+s-1` and its coefficient is divided by `(p+s-1)!` when `s>0`.
Multiply by the exponent-split multiplicity and `|O_48(nu)|`.

For each `(r,h)`, put `L=alpha-(r+h)delta` and integrate the complete exact
polynomial over

```text
z >= 0, w >= 0, z+w <= L,
z <= beta(r)-r*delta       if r>0.
```

Empty and zero-measure faces contribute zero.  Summing all faces gives `I`.
Before the domain integration multiply the radialized base square by

\[
 \{a_r+b_r(r\delta+X)+c_r(h\delta+Y)\}^2,             \tag{I-aff}
\]

where $X$ is the translated-large aggregate and $Y$ is the unshifted-small
aggregate after the inclusion--exclusion shift.  Expanding (I-aff) only after
face radialization avoids introducing exponent-one orbit labels, but it is an
algebraic reorganization only.

## 5. Reconstruction of `J`

Use 47 shared variables `u` and one distinguished variable `t`.  Reconstruct
the identity

\[
P_\lambda(u,t)=
1_{|\lambda|_{\rm length}<48}P_\lambda(u)
+\sum_{e\in\operatorname{distinct}(\lambda)}
t^eP_{\lambda\setminus e}(u).
\]

On a face `(r,h)` let `U=(r+h)delta+z+w`.  For a component with distinguished
exponent `e` and residual exponent `a`, construct each marginal directly from

\[
\int_l^v t^e(1-U-t)^a\,dt
=\sum_{j=0}^a\frac{(-1)^j{a\choose j}}{e+j+1}
(1-U)^{a-j}\left(v^{e+j+1}-l^{e+j+1}\right).
\]

The four branches and exact additional constraints are:

| branch | lower `l` | upper `v` | constraints in addition to the outer simplex |
|---|---:|---:|---|
| `Sdelta` | `0` | `delta` | `z<=beta(r)-r delta` if `r>0`; `z+w<=alpha-(r+h)delta-delta` |
| `Stotal` | `0` | `alpha-U` | same existing-large cap; `z+w>=alpha-(r+h)delta-delta`; `z+w<=alpha-(r+h)delta` |
| `Ltotal` | `delta` | `alpha-U` | `w>=alpha-beta(r+1)-h delta`; `z+w<=alpha-(r+h)delta-delta` |
| `Lbig` | `delta` | `beta(r+1)-r delta-z` | `w<=alpha-beta(r+1)-h delta`; `z<=beta(r+1)-(r+1)delta` |

The outer domain also has
`z,w>=0` and `z+w<=eta-(r+h)delta`.

For each branch retain both the zeroth and first distinguished-coordinate
moments, denoted $M_0=\int P(u,t)\,dt$ and
$M_1=\int tP(u,t)\,dt$.  If the distinguished coordinate is small, its
weighted marginal is reconstructed as

\[
 \{a_r+b_rL_u+c_rZ_u\}M_0+c_rM_1;                    \tag{J-small}
\]

if it is large, it is

\[
 \{a_{r+1}+b_{r+1}L_u+c_{r+1}Z_u\}M_0+b_{r+1}M_1.   \tag{J-large}
\]

Here $L_u$ and $Z_u$ are the large and small sums of the 47 shared
coordinates.  Equations (J-small)--(J-large) are simply the integral of the
same multiplier $a_R+b_RL+c_RZ$ appearing in the definition of $F$; omitting
the shifted $M_1$ term is a certificate-breaking error even when a signed
zeroth marginal cancels.

For independence from the optimized producer, the checker should enumerate
all **ordered** pairs of active branches and all ordered pairs of remaining
orbit labels.  Thus it needs no factor-two convention.  Multiply their
bivariate marginal polynomials, reconstruct the orbit product, multiply by the
47-variable angular density, and integrate over the exact intersection of the
two branch domains.  Complementary branch intersections are allowed to reach
the polygon integrator and must return exact zero.

For zero shared dimensions in unit tests, use the source interval partition to
choose a single side of `Sdelta/Stotal` and `Ltotal/Lbig`; closed halfplanes
alone double-count a 0-dimensional boundary.  The production target parser
must enforce `alpha-eta=delta` and must reject
`k=1, alpha=delta=eta=1/10`.  That edge fixture is constructed only through a
private general, test-only engine entry point which bypasses the production
parser and may relax the target identity.  For constant `F` it has `J=1/100`;
it is deliberately outside the target-specialized input contract and can
never be accepted as a target certificate.

Summing the ordered terms gives `J` without a dense matrix.

## 6. Independent exact geometry

Do not copy the producer's Green-theorem polygon moment routine.  Clip the
first-quadrant triangle by rational halfplanes using exact
Sutherland--Hodgman clipping, discard polygons with fewer than three vertices
or zero signed area, and triangulate the convex result from one vertex.

For each triangle, map the standard simplex affinely to it.  Expand the two
affine coordinate powers with multinomial coefficients and use

\[
\int_{x,y\ge0,\ x+y\le1}x^i y^j\,dx\,dy
=\frac{i!j!}{(i+j+2)!}.
\]

Multiply by the absolute rational determinant.  One-dimensional degeneracies
use exact antiderivatives on the intersected interval; a zero-dimensional
domain uses point evaluation with the half-open branch convention above.  Unit
tests compare this geometry code with direct symbolic integration on small
triangles and with the producer only after those independent tests pass.

## 7. Exact or outward-interval decision and output

An all-`Fraction` run computes, reduces, and prints

```text
I=<fraction>
J=<fraction>
numerator=48*J=<fraction>
margin=48*J-I=<fraction>
quotient=(48*J)/I=<fraction>
```

Then explicitly require `I>0` and `margin>0`.  Compare all reconstructed
fractions with the certificate's expected strings and fail on any mismatch.
The sign test is performed on exact integers after common-denominator
reduction.  Do not compute an eigenvalue, invert a matrix, or assume a matrix is
positive definite.  A decimal display may be printed only after `PASS` and is
labeled informational.

A fixed-point dyadic interval run is also a rigorous decision if every input
rational is outward-rounded before entering the polynomial algebra and every
subsequent `+,-,*,/` endpoint is integer-directed.  Exact Fractions may still
be used for support-geometry branch decisions.  Such a run must print exact
dyadic rational endpoints for `I`, `48J`, `48J-I`, and the quotient, and may
accept only when

```text
I.lower > 0
(48J-I).lower > 0.
```

The lower endpoint of `48J-I` is then an exact positive certificate margin
bound, not a favorable decimal rounding.  The output records the precision,
integer endpoint numerators, total interval widths, and every arithmetic
source hash.  At least one higher-precision run in the reverse face order
must enclose the first run's result and independently retain a positive lower
margin.

Run the checker normally and with `python -O`; both must print the same exact
fractions.  A `--streaming-order reverse` regression should sum faces in reverse
order and obtain identical values, catching accidental mutable-cache state.

## 8. Non-sieve components of the final command

The top-level `verify_all.py` must also run, rather than trust status text from:

1. an exact C10 analytic-parameter checker covering every finite inequality and
   every Proposition 3 small-index/subset/partition case in the repaired
   analytic proof; mathematical invocations of primary distribution theorems
   remain justified line by line in `PROOF.md`;
2. `verify/check_tuple.py`, pinned to tuple SHA-256
   `adfe71549293c2ff0efda34397e46c72269b2895ae23fc2fdfc34ccacc579ba9`.

The tuple checker must see 48 distinct integers, minimum 0, maximum 236, and for
every prime `q<=48` exhibit a missing residue class.  It must generate the
primes itself.

Only after all three components pass may `verify_all.py` print

```text
AUDIT PASS: exact k=48 quotient > 1; admissible diameter-236 tuple verified
```

## 9. Mandatory tests and artifact manifest

Before the D12 run is accepted, the independent checker must pass:

- literal low-dimensional orbit-product tests, including repeated and odd
  parts;
- exact direct-versus-grouped `I,J` tests for signed rational vectors at
  `k=2,3,4`;
- every pair of conditional branches, including both zero-measure boundaries
  and both zero-dimensional tie cases (using the private general test path for
  any parameter set that does not satisfy the production identity
  `alpha-eta=delta`);
- malformed JSON, duplicate labels, missing coefficient, wrong `k`, wrong
  capped beta, false input hash, and truncated certificate failures;
- a fresh exact C10 D4 same-geometry regression, using the production parser
  and the same parameter identities as the D12 target (in particular
  `alpha-eta=delta`); its exact numerator, denominator, and quotient must be
  reconstructed independently and pinned in the test fixture only after the
  two implementations agree;
- optionally, the earlier exact C20 D4 value
  `0.887273520064345754675253407883...` may be retained as a regression for a
  private general-engine test path, but it is not a production-target
  regression because its `alpha-eta` is `1/100` while its `delta` is `1/50`;
- the final D12 calculation in two face orders.

A manifest records SHA-256 for the compact certificate, vector source, every
checker source file, analytic checker, and tuple.  The checker output records
these hashes alongside the exact margin.  No rigorous resume path may override
a script or dependency hash; override flags are confined to explicitly
non-rigorous discovery runs.
