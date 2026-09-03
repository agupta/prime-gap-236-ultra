# Fixed-vector stratum-amplitude fallback

Date: 2026-09-01.  This is a design review; no heavy traversal was launched.

## Space and exact quadratic forms

Let `F0` be any fixed symmetric polynomial and put

`R(t)=#{i:t_i>delta}`.

For amplitudes `a_R`, define the symmetric square-integrable function

`F_a(t)=a_{R(t)} F0(t)`.

The boundaries `t_i=delta` have measure zero.  The support is unchanged, so
this is a legitimate finite-dimensional subspace of the same capped support.
Write

`I_R = integral_{R(t)=R} F0(t)^2 dt`.

The `I` form is diagonal:

`I(F_a)=sum_R a_R^2 I_R`.

For `J`, fix the distinguished coordinate and let `u` denote the other `k-1`
coordinates.  On the region `R(u)=r`, split its marginal into

`S_r(u)=integral_{t<=delta} F0(u,t) dt`,

`L_r(u)=integral_{t>delta} F0(u,t) dt`.

The support restrictions on each integral are implicit.  A small distinguished
coordinate leaves the total stratum at `r`, while a large one raises it to
`r+1`.  Hence

`integral F_a(u,t)dt = a_r S_r(u)+a_{r+1}L_r(u)`

on this common-variable stratum.  Define

`S2_r=integral S_r^2 du`, `SL_r=integral S_r L_r du`, and
`L2_r=integral L_r^2 du`.

Then

`J(F_a)=sum_r [a_r^2 S2_r+2a_r a_{r+1}SL_r+a_{r+1}^2 L2_r]`.

Thus the matrix for the sieve numerator `kJ` is tridiagonal:

`B_RR=k(S2_R+L2_{R-1})`,

`B_R,R+1=B_R+1,R=k SL_R`,

with missing boundary terms interpreted as zero.  The denominator matrix is
`A_RR=I_R`, all other entries zero.  These formulas agree with the existing
pairwise `StratumSupport`: deleting the distinguished coordinate changes the
large-coordinate count by zero or one, so entries with `|R-S|>1` vanish.

## One grouped traversal is enough

The existing grouped evaluator already does almost all of the required
bookkeeping.

For `I`, `evaluate_i` dispatches one work unit for each `r`, where `r` is
exactly the number of large coordinates.  Each `evaluate_i_r` already returns
the complete scalar contribution for that stratum before the parent sums the
list.  Retaining the list as `I_r` costs no new integration and only a few
scalars.

For `J`, `evaluate_j_r` uses `r=R(u)` and the four branches

- small: `Sdelta`, `Stotal`;
- large: `Ltotal`, `Lbig`.

Keep three accumulators per `r` and classify every already-computed unordered
branch-pair integral as small/small, small/large, or large/large.  No new orbit
product, density, polygon, or monomial moment is needed.  The current
`branch_orbit_product` multiplies unequal branch pairs by two because it is
evaluating a square.  Therefore its small/large bucket is `2 SL_r`; divide that
bucket by two when storing the off-diagonal matrix entry.  The small/small and
large/large buckets are already `S2_r` and `L2_r`, including the correct factor
two between distinct branches within the same class.

The additional work is an `O(1)` branch-class test per positive-measure
intersection and storage of roughly 16 `I` values and 47 `J` values.  Relative
to the D12 polynomial contractions it is negligible (well below one percent
in operation count).  The wall time is still essentially one complete scalar
D12 traversal.

For C10, feasible total strata are expected to be `R=0,...,15`; the exact code
must discover nonempty strata rather than hardcode that range.  A putative
large distinguished coordinate above common `r=15` is rejected by the
`B_16` cap, so the boundary formulas automatically give zero.

## Safe implementation hooks

Do not change the pinned scalar certificate script merely to explore this
fallback.  Add a separate `StratumAmplitudeEvaluator(GroupedEvaluator)` with:

1. `evaluate_i_blocks`: build the ordinary fixed-vector square once, invoke
   the inherited per-`r` face evaluator, and return the ordered `I_R` list as
   well as its sum;
2. `evaluate_j_r_blocks`: mirror the audited branch loop but return
   `(S2_r, twoSL_r, L2_r, count)` instead of one sum;
3. `evaluate_j_blocks`: fork by `r` exactly as the scalar evaluator does,
   assemble the tridiagonal `kJ` matrix, and also return its all-ones sum;
4. a direct fixed-amplitude mode that multiplies each I stratum by `a_r^2`
   and each marginal branch by `a_r` or `a_{r+1}` before the square.  This is
   the preferred independent reconstruction of a winning rational amplitude
   vector because it does not trust serialized block entries.

Every output should bind the fixed-vector input, grouped script, imported
integrator, and new block-evaluator hashes; record arithmetic precision,
complete face/branch counts, all block values, runtime, and parent/child RSS.
Any face limit or missing stratum must force an incomplete status.

The same hooks should be added to future jet traversals: preserve each I
per-`r` jet and split each J per-`r` jet into the three branch classes before
summing.  This adds negligible overhead and avoids losing the block data again.

## Mandatory exact tests

1. For all-one amplitudes, check exactly
   `sum_R I_R=I(F0)` and
   `sum_R B_RR+2sum_R B_R,R+1=kJ(F0)` against the audited scalar grouped path.
2. On signed mixed-odd `k=3` and repeated-part `k=4` examples, compare every
   diagonal/tridiagonal entry with a freshly reconstructed
   `StratumSupport.stratum_matrices` entry.
3. For several signed rational amplitude vectors, compare `a^T A a` and
   `a^T B a` both with the block formula and with the direct tagged pairwise
   form.
4. Check every entry with `|R-S|>1` is exactly zero and test the factor-two
   convention by comparing the stored `twoSL_r/2` with an ordered small/large
   bilinear integral.
5. Include `k=1` and the `beta=alpha`, zero-small-dimension branch tie; the
   half-open convention must assign the boundary once.
6. Require serial and fork-by-`r` block lists to agree entry by entry, not just
   after summation.
7. Mutate an input hash, omit one `r`, swap a small/large branch tag, and alter
   the cross-term factor; each mutation must fail.

After a Decimal block discovery, solve the diagonal/tridiagonal generalized
problem in high precision (equivalently scale by `sqrt(I_R)`).  Check residuals
and repeat at a second precision.  Rationalize only the amplitude vector, then
run the direct scalar fixed-amplitude reconstruction exactly.  A Decimal block
eigenvalue remains heuristic.

## Can an existing checkpoint recover the blocks?

No.  The completed D12 I-stage stores only the summed denominator; its raw and
converted forms contain no per-`r` contributions.  The final D12 MP100 output
stores only total `I`, total `J`, face/branch counts, and timings.  In the
parent process, the per-`r` worker returns were summed and discarded.  Face and
radial caches were deliberately cleared, and no SQLite matrix or moment dump
was written.  Progress logs contain counts, not contribution values.

The existing low-degree C10 stratum matrices do not contain the moments of the
272-term D12 fixed vector, so they cannot reconstruct these blocks.  The active
20-channel jet implementation likewise sums its per-`r` returns and branch
classes under its current pinned code.  Consequently a full new scalar (or
jet) traversal is required.  The design is computationally attractive only
because that one rerun yields the entire diagonal/tridiagonal amplitude problem
at essentially the cost of evaluating one fixed vector, not 136 pairwise
forms.

## Implemented low-degree calibration

The design is implemented in `stratum_amplitude.py` (SHA-256
`d23d42315d7b518ae5d3f200a6192f47f3500d6eebd3a73fb6aa4ce7a23c7887`).
The exact test suite `tests/test_stratum_amplitude.py` has SHA-256
`37f6da2d7bd229d6dbf895e3c4e5bb1118da191c4a69296a0919f05d4e319acb`
and passes four tests, including every block against the tagged pairwise
recurrence, signed block/direct equality, serial/fork equality, and the `k=1`
boundary tie.

For the C10 full-simplex D4 rational polynomial, rationalized amplitudes give
the exact quotient

```
0.9002830597452611935374979516776897156034...
```

versus the exact all-one value
`0.8963160512159082457686602654186171135763...`, an exact gain
`0.003967008529352947768837686259072602027085...`.  The assembled
tridiagonal form and the fresh branch-scaled direct traversal agree bit for
bit.  Artifact:
`results/c10_stratum_amplitude_fullD4_exact.json`, SHA-256
`09ecb794833417e56537a43b65957ee70fc4d4c7bc17b944d9e02d12847dc87a`.

For the separately cap-optimized D4 polynomial, the corresponding exact values
are `0.9000996926830291835518753425519643662054...` from a baseline
`0.8963676783427826288116142626306203472028...`, an exact gain
`0.003732014340246554740261079921344019002610...`.  Artifact SHA-256:
`362b2b58938e3fdfdf0afd6916ddabce17cce71aa856795866f5d51f26dcb043`.
These are exact fixed rational-vector evaluations after heuristic eigendirection
selection, not floating quotient claims.  They calibrate the mechanism but do
not determine its D12 gain.
