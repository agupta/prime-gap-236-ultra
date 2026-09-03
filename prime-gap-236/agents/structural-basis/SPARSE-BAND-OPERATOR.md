# Sparse degree-band operator

Status: the MP100 value/gradient traversal is complete.  It is not a
certificate path; every selected vector must still be reconstructed by the
scalar grouped evaluator, and a final positive vector must be checked in
`Fraction` arithmetic.

## Coordinates and derivatives

The 272 expanded labels have one owner `o(p)` in the 20-function compressed
space and rational weight `w_p`, so

```text
f_p(theta) = w_p theta[o(p)].
```

For an unordered source-label pair `(p,q)`, the scalar coefficient in `F^2`
is `f_p^2` on the diagonal and `2 f_p f_q` off the diagonal.  Its only
possible nonzero derivatives are

```text
p=q:       d_o = 2 f_p w_p,
p!=q:      d_o(p) += 2 w_p f_q,
            d_o(q) += 2 f_p w_q.
```

Thus label-pair construction updates at most two owner slots instead of
allocating a dense 21-tuple at every multiplication.  After aggregation by
`(nu,c)`, value and gradient channels share each orbit density, residual-power
expansion, polygon, and monomial moment.

For `J`, write a branch marginal as `M` and its owner derivatives as `M_d`.
The derivative blocks partition the underlying marginal components.  The
audited unordered branch contraction has derivatives

```text
same branch:       d(M*M)       = 2 B(M,M_d),
different branches (factor 2):
                   d(2 B(L,R))  = 2 B(L_d,R) + 2 B(L,R_d).
```

Summed over all owners, those products traverse the marginal components only
one or two additional times.  This replaces the dense Jet's twenty products
per scalar product.  Geometry, branch domains, complementary-boundary skips,
and orbit structure constants remain those of grouped evaluator SHA
`47167e92a0f346e969706dc282ccb2dfd4ac31a0a75b654938ffbe8423cf4a4a`.

## Fail tests and repairs

The current sparse operator SHA is
`e1545435f0c7ad22a17115ac46c291436c1ead5101fd3de6d2a80ab65bc9c257`.
The test suite SHA is
`95e11cc7f1f5e5558b88d0b6e82b02ed9c8c8f4302197d01312fba22d9d30d4c`
and passes 9/9 tests:

1. exact value, gradient, Euler, and central-polarization equality with freshly
   rebuilt small pairwise matrices;
2. exact scalar-grouped equality;
3. exact serial/fork equality for both dense and sparse operators;
4. exact sparse/dense channelwise equality;
5. exact full-simplex compressed-I preconditioner equality;
6. coefficientwise reconstruction of all 272 D12 source terms;
7. the `k=1`, `alpha=delta` branch-boundary regression;
8. survival of a different-branch derivative when the scalar marginal on one
   side cancels at the evaluation point.

The last two tests were added from explicit hostile-audit counterexamples.

## D4 calibration and D12 gates

The C10 D4 all-core MP60 calibration used one worker and completed all 312 I
faces and 1,200 J branch intersections in 44.5485 seconds (I 6.3398 s, J
38.2088 s, peak RSS 25,716 KiB).  Its quotient was
`0.89631605121591379167...`; comparison with the exact scalar value exposes
about 45 digits of cancellation.  The decisive D12 run therefore uses MP100,
not MP90.

The D12 driver fails closed unless source/band/dependency hashes, exact C10
parameters, dimensions, all vector lengths and finite values, gradient halves,
positive I, recomputed quotient, relative Euler errors below `1e-50`, exact
312/1,200 traversal counts, by-r bucket sums, and the independently computed
scalar MP100 baseline forms all pass.  It also verifies that every code
dependency is unchanged between the start and end of the run.

## Continuation and compact output

The production traversal finished in 32,208.797 seconds (I 10,169.193 s, J
22,039.604 s) and reproduced the pinned scalar baseline quotient
`0.97096984763378957411239000413955600374...`.  The raw artifact SHA is
`0ac99ee5a72a83576eaf92ad203280dd0359b290a5c1562652bf9be1259d644d`.
It deliberately has rejected status: nine redundant serialized `gradient/2`
diagnostics differ from exact halves by one last MP100 unit.  All substantive
hash, parameter, baseline, Euler, count, and bucket gates passed.

`code/recover_band_gradient.py` SHA
`9342fa3f6d8157a4d9b8603a20bb0527b7f47087a5aa3c9d39aebef892f9fee5`
byte-pins that rejected artifact and reconstructs the two action arrays only
as exact `Fraction(gradient,2)`.  Its output SHA is
`6411f11d218e66aa8c60d22daf0513e3e4840ebd74bd54c037761e3d7af56a43`;
tests pass 3/3 in normal and optimized modes, and two independent audits found
no arithmetic false accept.  This remains approximate-form discovery data.

The frozen first-trial producer SHA
`5e999a3727b9922aac986629e6b022b08614cfcd5ab38203b5f1a8e9e806a7bc`
uses the full-simplex I preconditioner and exact projective H12 normalization.
Its manifest SHA
`c16b960004b42e0c66fd2255fd6002eed1cbcf049167fe88f1f18c124e7686e5`
contains exact 5%, 10%, and 20% near-side band trials.  Their actual
serialized-base displacement derivatives are respectively
`+0.01491013299881944...`, `+0.02982026599763889...`, and
`+0.05964053199527777...`.  These are first derivatives only: none of the
three files contains a finite denominator, numerator, or quotient.  The
producer's 6/6 normal and
optimized tests include a concurrent trial mutation between its trial write
and manifest write; the complete trusted-input and just-written-trial byte
closure is rebound immediately before the manifest is atomically installed.

The near-20 trial SHA
`88c1d26f6cf46bbdd12dc000eb802cac8efe91be0ad003d6827f2ccdc6c0ff47`
has two independent scoped pre-launch passes.  Its fresh two-worker scalar
MP100 traversal was launched at 2026-09-02 08:54+02:00; no quotient is recorded
here until its forms appear.  The fail-closed output auditor SHA
`5e704655aa6e2e91d76dab6463955f7d1bb3234cfc606af7012d55e9815f5059`
and exact-rational line postprocessor SHA
`bbbce83623550d8d92467827e9c8535e172ed05dc237c93141737e04ae9e3468`
pass 4/4 and 5/5 tests in normal and optimized modes and have an independent
delta-audit pass.  The latter's exact fractions are exact only relative to the
serialized MP100 action/forms; any positive sign still needs exact or interval
reconstruction.

The unlaunched Davidson action wrapper
`code/band_action_sparse.py` (SHA
`6e1e689a0d18a91c9575c239a2346945f9c87c5b4efcfbcb6deab5255e6fcd37`)
imports the frozen sparse traversal and independently recovers the unique 20
coordinates from an explicit ordered 272-label input.  It rejects a vector
whose coefficients are not exactly proportional within every band.  Its exact
input tests (SHA
`7eb41a785e5897293bfd9a30dff85c972a474cc3b89166db040b2347854b7a25`)
pass 2/2, and an independent static audit found no false-accept path.  This
wrapper is only for another matrix action if the first Ritz line remains below
one; it has not been used in the active run.

`code/rationalize_band_candidate.py` (SHA
`d972aaf7881f1c1c2c9d8cc8379239f504ad49b12753d502511ea8483fe5301d`)
instead produces a portable 272-label scalar-check input.  It normalizes by the
largest exact coefficient, rounds all coefficients to one common decimal grid,
and removes the integer gcd.  This avoids the huge least common denominator
created by 272 independent rational approximations.  It pins the BandMap
dependency and full byte closure, strictly rejects duplicate/noncanonical
candidate JSON, checks the candidate's exact 20-to-272 expansion before
rounding, and publishes only through a held `O_EXCL` descriptor.  Its failure
path never renames or unlinks a pathname after an ownership check; it can only
write rejection JSON through that held descriptor.  The test suite (SHA
`e8b6107c4334d7f8c3b504173f1ea5d1fbb8d31709b91fb30f267e1ca266748b`)
passes 8/8 in normal and optimized modes, including deterministic dependency,
output-byte, reservation-replacement, and lying-stat/foreign-inode mutations.
Two independent scoped audits pass on the frozen revision.  No production
compact candidate will be emitted unless the fresh projected-line computation
first gives a positive discovery sign.  The resulting projective point
generally no longer lies exactly
in the 20-dimensional band space, so it is intended for scalar MP/exact
reconstruction or the stratum-multiplier port, not as input to the Davidson
action wrapper.
