# BV even D18 refinement and pruned D20 continuation

## Status

This is a source-bound plan only.  It does not read or mutate the active
`bv_aquarter_sourcebound_v2.sqlite3` cache, does not refine the active D18
iterate, and does not claim a D18 quotient.  Its machine-readable companion is
produced by `code/bv_d18_refinement_plan.py` solely from frozen source and the
completed D14/D16 artifacts.

The target support remains

```text
k=48, alpha=beta_m=103/400, eta=97/400, delta=7/250.
```

The exact graded even bases have dimensions 195, 307, 471, and 707 at degrees
14, 16, 18, and 20.  Thus D18 contains 111,156 symmetric matrix entries and
adds 63,878 entries beyond D16.

## What the active `run_basis.py` result can and cannot do

`run_basis.py` reconstructs the exact matrix through source-hashed version-2
cache keys.  Its initial eigensolver, however, uses Decimal precision 100 and
only 80 power iterations, then independently calls `limit_denominator(10^6)`
on every coordinate.  This was badly underconverged at D16: the run-result
seed eigenvalue was about `.9800274`, while 320 resumed iterations reached
`.9812781098`; the run-result's coarse rational vector itself had quotient
about `.237`.  Therefore the eventual 471-coordinate D18 decimal vector is a
seed and matrix-provenance token, never a certificate vector.

The existing `certify_bv_cached.py` improves the essentials: diagonal scaling,
high-precision Decimal LU, resumed iteration, a common significant-digit
rational grid, and exact quadratic contraction.  Its remaining limitation is
that it accepts the persistent cache as the source of every exact entry.  The
new workflow separates discovery from final checking rather than calling a
cache-backed contraction independent.

## Adaptive D18 refinement

After the active build exits cleanly, bind the complete run-result bytes and
verify all of the following before opening the cache read-only: exact
integrator hash, `run_basis.py` hash, `k=48`, degree 18, dimension 471, exact
graded basis, exact support parameters, and the run's canonical matrix hash.
The completed cache must have no journal/WAL sidecar and all 111,156 expected
source-hashed keys.

Use a new refiner, not an in-place edit of either frozen program:

1. Load the complete matrix from SQLite in `mode=ro`; missing entries are a
   fatal error and no insert/commit path exists.
2. At precision 180, factor the diagonally scaled denominator matrix once.
   Start from the run's decimal seed and process 40-iteration chunks, initially
   320 and at most 640 scalar iterations.
3. At every boundary record the Rayleigh quotient, its 40-step increment, the
   last increment ratios, scaled generalized residual, projective change to
   `A^-1 Bv`, and the two-vector Ritz improvement on
   `span{v,A^-1 Bv}`.  These last three cost only matrix-vector operations and
   the already available solve.
4. Rationalize only when there are at least four increasing traces, the recent
   ratio is below `.9`, the geometric-tail heuristic is at most `1e-16`, the
   scaled residual is at most `1e-28`, and the two-vector Ritz gain is at most
   `1e-18`.  These are discovery gates, not rigorous eigenvalue bounds.
5. If the ratio is at least `.9` or the projected time to these gates exceeds
   640 iterations, stop scalar power iteration.  Form a four-vector Krylov
   block and perform an A-inner-product Rayleigh--Ritz restart instead of
   spending hours extending a slow scalar iterate.
6. Replay from the normalized result for 160 iterations at precision 240.
   Require Rayleigh agreement within `1e-25` and projective vector agreement
   within `1e-20`.
7. Normalize by the largest coordinate and create common-grid rational vectors
   at 45, 60, and 75 significant digits.  Contract all three exactly against
   the cache-loaded matrix, require an exact quotient spread at most `1e-25`,
   and retain the exact best achieved particular vector.  No `limit_denominator`
   operation is permitted.

The D16 trace supplies a cheap calibrated warning.  Its last six 40-step gain
ratios stabilize near `.06977029`; at iteration 320 the last increment is
`9.5556e-12` and its geometric tail remains about `7.1670e-13`.  Thus merely
matching the old 320-iteration count is visibly underconverged.  At that
historical ratio, another 320 iterations drive the 40-step increment below
`1e-20`.  The same trace logic is evaluated from D18 data rather than assuming
that its spectral gap is identical.

## Resource estimate

The D16 extension computed 28,168 new entries in 814.363 seconds.  Linear
extrapolation gives about 1,847 seconds for D18's 63,878 new entries; the plan
reserves a factor three, about 1.54 hours.  Quadratic memory scaling from the
recorded 237,660 KiB D16 build gives about 559,400 KiB, with a 768 MiB
operational cap.

Scaling the completed D16 refinement by dimension cubed, precision, and the
iteration schedule gives roughly 14 minutes for Decimal180/640 plus 9 minutes
for Decimal240/160; the machine-readable plan records the exact rational
calculation.  Its 768 MiB cap covers the more conservative precision-weighted
quadratic memory estimate.  These are planning estimates, not runtime bounds.

## Independent cache-free checker

The certificate checker must import neither `run_basis.py` nor
`certify_bv_cached.py` and must reject any cache argument.  It independently
enumerates the 471 graded even labels and, from the pinned recurrence, rebuilds
all 111,156 lower-triangular pairs

```text
I_ij  = basis_m1(label_i,label_j),
B_ij  = 48*basis_j(label_i,label_j).
```

It streams

```text
sum_i c_i^2 M_ii + 2 sum_{i>j} c_i c_j M_ij
```

for both matrices and hashes canonical `(label_i,label_j,I_ij,B_ij)` records.
Exactly 111,156 unique records are mandatory.  It verifies the certificate's
exact denominator, numerator, quotient, and signed margin strings, with only
`I>0` assumed; no positive-definiteness or optimality claim is made.  A second
reverse-order run must produce identical exact forms and the same order-neutral
entry hash.  Normal and `-O` low-k signed tests, missing-entry, duplicate,
partial-limit, wrong-source, malformed rational, and accidental-cache tests
must all fail closed.  The conservative checker estimate is 1.54 hours and a
1 GiB peak cap.

Only this checker can promote the cache-refined output to an exact
particular-vector certificate.  It still does not certify the largest D18
generalized eigenvalue.

## Pruned D20 route

After a cache-free D18 certificate exists, there are 236 new labels in
`B20\B18`: 97 have total degree 19 and 139 have total degree 20.  The
machine-readable plan serializes every label as its exact `(a, partition)`
pair in the canonical graded `even_basis(20)` suffix order; it does not leave
the inventory implicit behind a digest.  For each new label `h`, compute exact
cached forms

```text
a01=I(F18,h), b01=48J(F18,h), a11=I(h,h), b11=48J(h,h).
```

Require `a00*a11-a01^2>0`.  The exact residual cross is
`b01-(b00/a00)a01`; the larger two-dimensional generalized root is the larger
root of

```text
det(A) lambda^2
 -(b00*a11+b11*a00-2*b01*a01) lambda
 +det(B)=0.
```

Isolate it with outward rational intervals, and independently put the
stationary scalar on a common 60-digit rational grid so every ranked achieved
gain is an exact fraction.  Overlapping algebraic-root intervals are ties and
are resolved only by the canonical graded label.

This all-label ranking needs 111,156 old/new cross pairs and 236 new
diagonals: 111,392 pairs.  Freeze the top 24 exact trial gains and compute only
their 276 missing off-diagonal pairs.  The selected extension therefore uses
111,668 incremental pairs and a 495-dimensional matrix with 122,760 total
entries, versus 139,122 incremental and 250,278 total entries for full D20.
The uncomfortable fact is explicit: exact ranking already costs about 80.3%
of the full incremental moment inventory.  Pruning chiefly saves the
generalized solve (about 34.3% of full D20 cubic work), matrix RAM (about 49%),
and cache-free checker, not the scan itself.

The D20 scan remains disabled.  It requires a cache-free D18 certificate, the
sum of the top 24 exact individual gains at least `1e-4`, and a selected-block
discovery quotient at least `.99`.  The full D20 build is never automatically
authorized.  Under the same deliberately conservative D16 calibration, the
selected incremental moments cost about 2.69 hours versus 3.35 hours for full
D20; degree-20 arithmetic can be slower, so a fresh first-row calibration is
required before launch.
