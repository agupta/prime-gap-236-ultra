# Low-memory fallback inside the 20-function degree-band space

Status: design only; no run was launched while the fixed C10 D12 evaluation was
active.

## 1. The finite space and its exact coordinates

Let the 272 source labels be `p=(a,lambda)` and let `c_p` be the exact D12
full-simplex discovery vector.  Define 20 rational directions:

- directions 0--11 are the twelve individual labels of total degree at most 4;
- direction `12+(d-5)` is
  `H_d=sum_(deg(p)=d) c_p G_p` for `5<=d<=12`.

Every source label belongs to exactly one direction.  Store this as

```text
owner[p]  in {0,...,19}
weight[p] = 1                         for a D4 core label
weight[p] = c_p                       for a degree d>4 label.
```

For a compressed coordinate vector `theta`, its expanded coefficient is

```text
f_p(theta) = weight[p] * theta[owner[p]].
```

The original 272-term polynomial is represented exactly by

```text
theta0[i] = c_p   for the core direction whose sole label is p,
theta0[i] = 1     for i=12,...,19.
```

Thus a capped optimization in this space cannot do worse than the fixed-vector
quotient.  Band sizes are `7,11,15,22,30,42,56,77`; their sum plus the 12 core
labels is 272.

Write

```text
D(theta) = I(F_theta)       = theta^T A theta,
N(theta) = 48 J(F_theta)    = theta^T B theta,
R(theta) = N(theta)/D(theta).
```

The goal of the fallback is discovery of a better rational `theta`; the final
sign is still checked by the already audited scalar exact reconstruction.

## 2. First tier: one-pass directional derivatives

Add a discovery-only module
`agents/structural-basis/code/band_operator.py`.  It may reuse the audited
support-face and polygon primitives, but it must not modify the scalar
certificate path.

### 2.1 A 20-gradient jet

Represent a coefficient at a fixed `theta` by

```text
Jet = (value, gradient[20]).
```

Only these operations are required:

```text
add((x,g),(y,h))       = (x+y, g+h)
scale(s,(x,g))         = (s*x, s*g)
multiply((x,g),(y,h))  = (x*y, y*g+x*h).
```

The expanded coefficient `f_p` starts as

```text
(weight[p]*theta[i], weight[p]*unit_vector(i)),  i=owner[p].
```

In `square_residual_terms`, replace the scalar product of two expanded
coefficients by `multiply`.  Keep the existing diagonal/unequal label
multiplicity and orbit structure constants unchanged.  After aggregation,
each `(nu,c)` carries one value and twenty derivatives.  The count of orbit
groups is unchanged; only its scalar payload changes.

On an I face, multiply this jet by the ordinary scalar orbit density and the
ordinary residual polynomial.  Store

```text
total_poly[(z_degree,w_degree)] = Jet.
```

Integrate all 21 channels with one geometry traversal: construct the exact or
Decimal monomial moment once for each bivariate monomial and take 21 dot
products.  Do not invoke the polygon integrator 21 separate times.

For J, `marginal_components` becomes linear-jet valued.  A branch marginal is
still linear in `theta`, so its polynomial coefficients are jets.  In
`branch_orbit_product`, use the product rule above.  Orbit densities and domain
geometry remain scalar and are shared by all channels.  Clear all face/radial
caches at the same points as the scalar evaluator.

The result of one pass is

```text
(D, grad_D, N, grad_N)
 = (theta^T A theta, 2 A theta,
    theta^T B theta, 2 B theta).
```

Required internal checks are

```text
theta dot grad_D == 2*D
theta dot grad_N == 2*N
```

exactly in Fraction mode, or to a stated Decimal tolerance in discovery mode.

### 2.2 The first correction needs only one jet and one scalar run

At the fixed vector put

```text
a = grad_D/2 = A theta0
b = grad_N/2 = B theta0
R0 = N/D
r = b - R0*a.
```

Use the 20-by-20 full-simplex compressed I matrix as a scale preconditioner
`P`.  It has a closed Dirichlet formula and can be rebuilt cheaply; no capped
cache is needed.  Solve

```text
P d = r
```

at no less than 220 Decimal digits, then remove the `P`-component along
`theta0` and normalize `d` in the `P` norm.  Repeat discovery at a second,
higher precision and require stable projected quotients and residual
coordinates.  This prevents both cancellation and the wildly different raw
scales of the core and high-degree bands from making a Euclidean gradient
useless.

The cross terms are already known:

```text
A00 = D,        B00 = N,
A01 = d dot a,  B01 = d dot b.
```

Run the ordinary scalar grouped evaluator once on `d` to get
`A11=D(d)` and `B11=N(d)`.  Solve the two-dimensional generalized problem

```text
[B00 B01; B01 B11] x = lambda [A00 A01; A01 A11] x.
```

Equivalently maximize the exact rational function

```text
(B00+2*t*B01+t^2*B11)/(A00+2*t*A01+t^2*A11).
```

Its stationary equation is quadratic because the cubic terms cancel.  Decimal
roots are discovery data.  Move the winning root a safe distance into any
positive margin, rationalize all 20 coordinates, expand to 272 exact rational
coefficients, and run the scalar exact checker.  This first attempt replaces
210 pair calculations by one 20-gradient traversal plus one scalar traversal.

### 2.3 Davidson/Ritz continuation

If one correction does not cross 1, make `apply(theta)` return
`(A theta,B theta,D,N)` from the same jet pass and run a generalized Davidson
iteration:

1. Start with `V=[theta0]` and its stored `AV,BV`.
2. Solve the small projected problem
   `(V^T B V)y=lambda(V^T A V)y`.
3. Form `v=Vy`, `r=Bv-lambda Av`.
4. Take `d=P^{-1}r`, P-orthogonalize it against V, and normalize.
5. One new jet pass at `d` supplies `Ad,Bd`; append and repeat.

All projected entries are dot products with stored 20-vectors.  No dense capped
matrix is formed.  Stop after six directions unless a measured residual or
quotient gain justifies extending the Krylov space; this costs at most six jet
passes rather than 210 fixed-vector passes.

## 3. Second tier: blocked facewise bilinear accumulation

If the residual iteration stagnates, build the complete 20-by-20 capped
matrices in one facewise traversal, but never hold 210 complete integrations or
serialized moment tables.

### 3.1 I coefficient tensor

For each compressed pair `0<=i<=j<20`, expand `phi_i phi_j` once:

- if `i<j`, loop once over every label in `phi_i` and every label in `phi_j`;
- if `i=j`, loop over unordered expanded-label pairs and multiply unequal
  pairs by two.

Apply the orbit product and residual expansion.  Store the transposed sparse
tensor

```text
I_groups[(nu,c)] -> list of (packed_cell, exact_coefficient).
```

The coefficient belongs to the bilinear matrix entry `A_ij`; do not add the
extra factor two used when writing a whole quadratic form.  Because each of the
272 labels has one owner, the initial expanded-label work is of the same order
as the 37,128 unordered pairs in the fixed D12 square, not 210 independent
272-term squares.

On each `(r,h)` face compute every needed orbit density once.  Process packed
matrix cells in blocks of 24--32:

```text
for face:
    for cell_block:
        build only the bivariate polynomials for cells in this block
        integrate them using shared polygon-monomial moments
        add to the 210-entry accumulator
        discard the block polynomials
    clear face caches
```

The density and polygon-moment caches stay alive through all cell blocks of the
face, then are cleared.  This is facewise streaming; no SQLite output is read or
required.

### 3.2 J matrix

Build marginal components separately for each of the 20 directions.  On a
face/branch, form

```text
branch_poly[direction][remaining_orbit][z,w].
```

For independence and simple factors, sum all ordered branch pairs.  For a
matrix cell `(i,j)`, multiply the marginal of direction i from the left branch
by direction j from the right branch, reconstruct the remaining-orbit product,
multiply by the shared 47-variable density, and integrate over the exact branch
intersection.  Again process only 24--32 cells at once and preflight exact
positive domain measure before polynomial multiplication.  Fill the transpose
only after the bilinear entry is complete; small exact tests must separately
compare both direction orders and establish symmetry entry by entry.

The resulting Decimal matrices are discovery objects.  Solve their generalized
eigenproblem with symmetric scaling, rationalize the particular 20-vector, and
certify that vector with the scalar exact reconstruction.  Exact matrix output
is unnecessary unless it is later useful for an independent audit.

## 4. Memory and runtime estimates

These are operation-count estimates, not measurements of D12.  They must be
replaced in the experiment ledger after a four-face calibration run.

### Gradient mode

- The group keys, orbit densities, support geometry, and polygon moments are
  exactly those of one scalar run.
- Polynomial payloads have 21 channels.  If coefficient arithmetic dominated,
  21 times scalar time is a hard naive estimate; shared orbit/density/geometry
  work should make the practical range about 6--15 scalar-run times.
- The first line search therefore costs about 7--16 scalar-run times including
  the one evaluation of `d`, versus 210 full pair runs.
- At MP220, 33,075 scalar channels for 1,575 grouped I keys occupy only a few
  megabytes before Python container overhead.  Face and J intermediates are
  larger; budget 0.3--1.0 GiB per worker in Decimal mode.  Exact Fraction jets
  can grow to roughly 0.8--2.5 GiB per worker and are not recommended for
  discovery.  Start with two fork workers only after checking available RAM.

### Blocked matrix mode

- The final two symmetric matrices contain only 420 rational/Decimal entries.
- A worst-case sparse `(group,cell)` tensor has at most
  `1575*210=330,750` coefficient slots; actual sparsity should be recorded.
- Blocking 24 cells caps live bivariate-polynomial payload near 24/210 of an
  unblocked build.  Budget about 0.3--1.0 GiB per Decimal worker and
  1--3 GiB per exact-Fraction worker.  Run one worker first on the 8 GiB host.
- It performs all 210 bilinear channels but shares orbit densities and geometry.
  A provisional range is 35--100 scalar-run times, still below 210 isolated
  runs.  Abandon it in favor of additional Davidson directions if a four-face
  calibration extrapolates beyond the remaining wall time.

The program must record calibration faces, arithmetic precision, observed
channel count, peak parent/child RSS, and extrapolated full runtime before a
full fallback launch.

## 5. Concrete code changes and fail tests

Do not alter `grouped_fixed_vector.py` while it is producing a certificate.
Implement the fallback in a separate discovery file with these entry points:

```text
BandMap.from_source_and_bands(source_json, bands_json)
BandOperator.square_residual_jets(theta)
BandOperator.marginal_component_jets(theta)
BandOperator.evaluate_i_jet(theta, workers)
BandOperator.evaluate_j_jet(theta, workers)
BandOperator.apply(theta) -> D,N,A_theta,B_theta
two_dimensional_update(theta, A_theta, B_theta, preconditioner)
davidson(theta, max_space=6)
BlockedBandMatrices.evaluate_i(cell_block=24)
BlockedBandMatrices.evaluate_j(cell_block=24)
```

Add `--limit-r` and `--limit-faces` for calibration only; outputs under either
flag are forcibly marked incomplete and can never print `margin_positive`.

Before any D12 fallback, require exact small tests:

1. jet value equals the scalar evaluator;
2. `theta.grad/2` equals matrix-vector multiplication from a freshly rebuilt
   small `k=3,4` matrix;
3. central polarization
   `(Q(theta+e_i)-Q(theta-e_i))/2` equals `grad_i` exactly;
4. Euler identities `theta dot grad=2Q`;
5. blocked matrices equal the small pairwise matrices entry by entry;
6. band expansion at `theta0` is coefficientwise identical to the 272-term
   source vector;
7. serial and fork-by-r jets agree channel by channel;
8. all incomplete/calibration artifacts fail closed if presented as a
   certificate.

Every numerically improved vector is written with the source/band/operator
hashes, precision, projected quotient, residual norm, wall time, and RSS.  Only
the subsequent scalar exact capped result can be promoted to certificate
status.
