# D4 degree-three finite-space obstruction

Status: rigorous for the reconstructed D4 degree-three finite space.  This is
not a D12 theorem and it does not independently recompute any source integral.

## Result

The exact 160-coordinate pencil has Gram rank 154, with precisely the six
previously frozen `R=0` dependent coordinates discarded.  On those 154 exact
Gram-independent coordinates, `C = A - B` is positive definite.  Consequently

`v^T B v / v^T A v < 1`

for every nonzero vector in the finite-space Gram quotient.  Thus this entire
D4 degree-three space is obstructed; there is no exact positive candidate in
it.

The canonical certificate is
`results/c10_D4_degree3_finite_space_obstruction.json`, byte SHA-256
`ace35d91e3ddc1d912711e140d72e54b6ad105355a59e44b07b9f53f3b2b1424`.

## Proof certificate

The checker first reconstructs `A` and `B` from the canonical moment rows with
the frozen consumer.  Serialized matrix hashes are secondary checks.  It
replays the complete exact D2 principal matrix and contraction, then repeats
the exact Gram-rank/dependence calculation.  The reconstructed active matrix
`C` has SHA-256
`bd9c5717294d0284e755e5ca2df895ba38e4dcbf083c1f27137cb2261812b241`
under the producer's canonical rational-matrix encoding.

For conditioning, the checker constructs a positive diagonal matrix
`S = diag(2^e_i)` exactly and sets `H = S C S`.  Every diagonal of `H` is in
`[1,4)`, and exact inspection proves `H` block tridiagonal by stratum.  It then
performs block-banded LDL arithmetic with integer intervals representing
`[lo/2^768, hi/2^768]`.  Every primitive operation rounds outward.  All 154
pivot lower endpoints are strictly positive.  The ordered endpoint list is in
the artifact and has SHA-256
`ff8fb22931c5511a142456684cecdf9ee891a820bec67bda8648a2adfff03325`.

There is also an independent exact residual closure.  Let `Lhat,Dhat` be the
exact dyadic midpoints of the interval factors and
`E = H - Lhat Dhat Lhat^T`, computed with rational arithmetic.  Fixed-point
forward/backward recurrences, rounded upward after every operation, bound
`||Lhat^-1||_infinity` and `||Lhat^-1||_1`.  For symmetric `E`,

`||Lhat^-1 E Lhat^-T||_2 <= ||E||_infinity
  ||Lhat^-1||_infinity ||Lhat^-1||_1`.

The artifact proves exactly that `||E||_infinity <= 2^-725`, while

`min(Dhat) / (||Lhat^-1||_infinity ||Lhat^-1||_1) >= 2^-388`.

The explicit separation is 337 bits.  Therefore the midpoint factorization
also proves `H` positive definite.  Positive diagonal congruence transfers the
result to `C`.

## Feasibility decision

An exact `Fraction` LDL was benchmarked before choosing the certificate form.
Reconstruction took about 1.9 seconds.  The first 30 rational pivots took 16.4
seconds and had roughly 40,600-bit numerator/denominator terms; the first 50
took 90.0 seconds and reached roughly 67,900 bits.  This growth made the full
rational factorization an unattractive production certificate.  By contrast,
the final two-layer 768-bit interval/exact-residual proof took 3.86 seconds
externally and 84,256 KiB peak RSS (the artifact's internal measurement is
3.565827410 seconds and the same RSS).

## Frozen identities and invocation

- Checker: `certify_d4_degree3_finite_space.py`, SHA-256
  `d422fe7a472c61223a367c2e1cc1bb332fa79bcb2036f2e083c9ee183ed3d3d1`.
- Tests: `test_certify_d4_degree3_finite_space.py`, SHA-256
  `da96598022fb5c6db88471736ef7ee80d3540abef928328a48c014911834848c`.
- Frozen reconstruction consumer SHA-256:
  `fedf1970b197af825675fa62644aa227875487453d125ad454d213ebcdedfb7c`.
- Completed producer result SHA-256:
  `c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5`.

The canonical invocation was:

```text
python3 agents/small-delta-frontier/certify_d4_degree3_finite_space.py --result agents/small-delta-frontier/results/c10_D4_degree3_moment_exact.json --expected-result-sha256 c9cce84c8a75f231738edabfb7c0ca17e48085b2f4e27f4305866103b8d4d0f5 --expected-checker-sha256 d422fe7a472c61223a367c2e1cc1bb332fa79bcb2036f2e083c9ee183ed3d3d1 --output agents/small-delta-frontier/results/c10_D4_degree3_finite_space_obstruction.json
```

Seven tests pass under both normal Python and `python3 -O`.  They cover exact
interval enclosure, positive and indefinite synthetic pencils, illegal
off-band mutation, wrong hashes, post-read mutation, frozen-consumer loading,
and new-path-only publication.

## Trust boundary

No integration and no numerical eigensolve occurs here.  The checker executes
only the snapshotted bytes of the independently audited reconstruction
consumer and pins its SHA before import.  The checker itself and the completed
result are caller-pinned before result access and reverified at closure, along
with the authorization, producer/consumer gates, and D2 reference.

Sparse J-row omission denotes zero for reconstruction because the exact
producer established fused/unfused equality and the caller pins the complete
result bytes.  The row data alone does not prove that omitted source integrals
are zero.  This source-integral boundary is unchanged by the obstruction.
